"""Tests for the Guardian nameplate renderer (tools/plate.py)."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools import plate  # noqa: E402


# The field vocabulary of the reference deck (~/Videos/nameplates.json).
GUARDIAN = {
    "id": "osiris", "at": 1.0, "dur": 5.0, "position": "left", "trustee": True,
    "label": "TRUSTEE // GUARDIAN", "class": "Dawnblade Warlock",
    "name": "Bob Killen", "title": "Reconciler of the Plane",
}
GHOST = {
    "id": "sagira", "at": 8.0, "dur": 4.0, "position": "right", "kind": "ghost",
    "label": "EMOTIONAL SUPPORT // GHOST",
    "name": "Lindsay Gendreau", "title": "Master of the Labyrinths",
}
TITLE_CARD = {
    "id": "roster", "at": 20.0, "dur": 6.0, "position": "right", "kind": "title",
    "title": "Thanks for working on Bluefin!",
    "subtitle": "Project Bluefin contributors, 2026-08",
    "body": ["hanthor", "Giklab"],
}


def test_plate_renders_to_a_transparent_rgba_image():
    img = plate.render_plate(GUARDIAN)
    assert img.mode == "RGBA"
    assert img.width > 0 and img.height > 0
    # The chamfered top-left corner is cut away, so that pixel must be clear.
    assert img.getpixel((0, 0))[3] == 0
    # ...and the middle of the plate is not.
    assert img.getpixel((img.width // 2, img.height // 2))[3] > 0


def test_render_is_deterministic():
    """A re-render must be diffable: same spec in, same bytes out."""
    assert plate.render_plate(GUARDIAN).tobytes() == plate.render_plate(GUARDIAN).tobytes()


def test_ghost_plate_has_no_class_line():
    """A Ghost is not a Guardian, so a subclass line would be nonsense on it."""
    ghost = plate.render_plate(GHOST)
    with_class = plate.render_plate(dict(GHOST, kind="guardian", **{"class": "Voidwalker Warlock"}))
    assert ghost.height < with_class.height


def test_rust_variant_changes_only_the_chrome():
    """The Rust Foundation herald's plate is oxidised, not a different card."""
    rust = plate.render_plate(dict(GUARDIAN, variant="rust", trustee=False))
    default = plate.render_plate(dict(GUARDIAN, trustee=False))
    assert rust.size == default.size            # same geometry, same copy
    assert rust.tobytes() != default.tobytes()  # different chrome


def test_placement_respects_the_row_margins():
    """bottom 10%, left/right 5% (.wolves-guardian-plate-row)."""
    p = plate.render_plate(GUARDIAN)
    left = plate.place(p, "left")
    right = plate.place(p, "right")
    assert left.size == (plate.FRAME_W, plate.FRAME_H)

    def bbox_of(frame):
        return frame.getchannel("A").getbbox()

    lx0, ly0, lx1, ly1 = bbox_of(left)
    rx0, _, rx1, _ = bbox_of(right)
    assert lx0 == pytest.approx(plate.FRAME_W * plate.MARGIN_X, abs=2)
    assert rx1 == pytest.approx(plate.FRAME_W * (1 - plate.MARGIN_X), abs=2)
    assert ly1 == pytest.approx(plate.FRAME_H * (1 - plate.MARGIN_BOTTOM), abs=2)
    assert lx0 < rx0  # left-anchored really is further left


# --- group rows (the reference deck's roll call, gp_* entries) --------------

def test_a_group_plate_sits_at_its_absolute_x_on_the_picture():
    """position: "group" places the card at an absolute x against the PICTURE,
    shrunk by its scale -- the deck's gp_* entries carry both."""
    picture = (40, 140, 1840, 800)
    card = plate.render_plate(GUARDIAN)
    frame = plate.place(card, "group", picture, x=51, scale=0.78)
    x0, _, x1, y1 = frame.getchannel("A").getbbox()
    assert x0 == 40 + 51  # x is measured from the picture's left edge
    assert x1 - x0 == pytest.approx(card.width * 0.78, abs=2)
    # ...and the bottom row rule still holds against the picture, so the card
    # cannot hang onto the letterbox bar.
    assert y1 == pytest.approx(140 + int(800 * (1 - plate.MARGIN_BOTTOM)), abs=1)


def test_a_group_plate_without_an_x_is_a_bug_not_a_default():
    with pytest.raises(ValueError, match="x"):
        plate.place(plate.render_plate(GUARDIAN), "group")


def test_group_row_members_may_be_visible_together():
    """Members of the same group row share a `group` key and are one row by
    construction -- the roll call is *meant* to be seen together."""
    row = [dict(GUARDIAN, id="g1", at=10.0, dur=5.0, position="group",
                group="r1", x=51, scale=0.78),
           dict(GHOST, id="g2", at=10.4, dur=4.6, position="group",
                group="r1", x=461, scale=0.78)]
    assert [e["id"] for e in plate.load_manifest_entries(row)] == ["g1", "g2"]


def test_a_group_member_still_may_not_overlap_a_plate_outside_its_row():
    """The exception is narrow: overlapping anything but your own row fails."""
    with pytest.raises(ValueError, match="same time"):
        plate.load_manifest_entries([
            dict(GUARDIAN, id="g1", at=10.0, dur=5.0, position="group",
                 group="r1", x=51),
            dict(GHOST, id="solo", at=12.0, dur=4.0),
        ])


def test_two_different_group_rows_may_not_overlap():
    with pytest.raises(ValueError, match="same time"):
        plate.load_manifest_entries([
            dict(GUARDIAN, id="g1", at=10.0, dur=5.0, position="group",
                 group="r1", x=51),
            dict(GHOST, id="g2", at=12.0, dur=4.0, position="group",
                 group="r2", x=461),
        ])


def test_an_exempt_pair_does_not_shield_a_later_collider():
    """The overlap check stays pairwise: A and B sharing a row must not hide
    that A also overlaps C, a plate outside the row."""
    with pytest.raises(ValueError, match="same time"):
        plate.load_manifest_entries([
            dict(GUARDIAN, id="g1", at=10.0, dur=10.0, position="group",
                 group="r1", x=51),
            dict(GUARDIAN, id="g2", at=11.0, dur=1.0, position="group",
                 group="r1", x=461),
            dict(GHOST, id="solo", at=15.0, dur=1.0),
        ])


def test_overlapping_plates_are_rejected(tmp_path):
    """One plate at a time: two visible at once is a bug, not a style choice."""
    path = tmp_path / "m.json"
    path.write_text(json.dumps([
        dict(GUARDIAN, at=0.0, dur=5.0),
        dict(GHOST, at=3.0, dur=4.0),
    ]))
    with pytest.raises(ValueError, match="same time"):
        plate.load_manifest(path)


def test_duplicate_ids_are_rejected(tmp_path):
    path = tmp_path / "m.json"
    path.write_text(json.dumps([
        dict(GUARDIAN, at=0.0, dur=2.0),
        dict(GUARDIAN, at=5.0, dur=2.0),
    ]))
    with pytest.raises(ValueError, match="duplicate"):
        plate.load_manifest(path)


def test_non_positive_duration_is_rejected(tmp_path):
    path = tmp_path / "m.json"
    path.write_text(json.dumps([dict(GUARDIAN, dur=0)]))
    with pytest.raises(ValueError, match="dur"):
        plate.load_manifest(path)


def test_manifest_accepts_a_plates_wrapper(tmp_path):
    path = tmp_path / "m.json"
    path.write_text(json.dumps({"plates": [GUARDIAN, GHOST]}))
    assert [e["id"] for e in plate.load_manifest(path)] == ["osiris", "sagira"]


def test_render_all_writes_one_png_per_plate(tmp_path):
    written = plate.render_all([GUARDIAN, GHOST], tmp_path)
    assert [p.name for p in written] == ["plate_osiris.png", "plate_sagira.png"]
    assert all(p.exists() for p in written)


def test_burn_builds_one_enable_gated_overlay_per_plate(tmp_path):
    """The burn is a single ffmpeg pass; each plate is gated to its own window."""
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd

        class R:
            returncode = 0
            stderr = ""
        return R()

    import subprocess
    real = subprocess.run
    subprocess.run = fake_run
    try:
        plate.burn("in.mp4", [GUARDIAN, GHOST], tmp_path, tmp_path / "out.mp4",
                   ffmpeg=["ffmpeg"])
    finally:
        subprocess.run = real

    chain = captured["cmd"][captured["cmd"].index("-filter_complex") + 1]
    assert chain.count("overlay=") == 2
    assert "between(t,1.000,6.000)" in chain
    assert "between(t,8.000,12.000)" in chain
    # audio is carried through, not re-encoded
    assert "-c:a" in captured["cmd"] and "copy" in captured["cmd"]


# --- planning -----------------------------------------------------------

LEADS = {
    "osiris": {"person": "mrbobbytables", "display_name": "mrbobbytables", "aka": [],
               "constraints": {},
               "plate": {"label": "TRUSTEE // GUARDIAN", "class": "Dawnblade Warlock",
                         "name": "Bob Killen", "title": "Reconciler of the Plane",
                         "trustee": True}},
    "sagira": {"person": "lindsay_gendreau", "display_name": "Lindsay Gendreau",
               "aka": [], "constraints": {},
               "plate": {"label": "EMOTIONAL SUPPORT // GHOST",
                         "name": "Lindsay Gendreau", "title": "Master of the Labyrinths",
                         "kind": "ghost"}},
    "zavala": {"person": "kelsey_hightower", "display_name": "Kelsey Hightower",
               "aka": [], "constraints": {}, "plate": None},
    "ikora_rey": {"person": None, "display_name": None, "aka": [],
                  "constraints": {}, "plate": None},
}


def _shot(seg, start, end, role=None, character=None, slots=0, usable=True):
    return {
        "segment_id": seg, "video_id": "yt_v", "start_sec": start, "end_sec": end,
        "duration": end - start, "start_tc": "0:00", "end_tc": "0:01",
        "casting": {"role": role, "character": character, "person": None,
                    "usable": usable, "constraints_failed": [], "slots": slots},
    }


def test_plan_plates_each_lead_once_on_first_appearance():
    shots = [
        _shot("s1", 0, 8, "lead", "osiris"),
        _shot("s2", 8, 16, "lead", "osiris"),   # second appearance: no second plate
        _shot("s3", 16, 24, "lead", "sagira"),
    ]
    entries = plate.plan(shots, LEADS)
    assert [e["id"] for e in entries] == ["osiris", "sagira"]
    assert entries[0]["name"] == "Bob Killen"
    assert entries[0]["at"] == pytest.approx(plate.LEAD_IN)
    assert entries[1]["at"] == pytest.approx(16 + plate.LEAD_IN)


def test_plan_skips_a_lead_with_no_plate_copy():
    """A binding without `plate:` in the vocab simply gets no plate."""
    assert plate.plan([_shot("s1", 0, 8, "lead", "zavala")], LEADS) == []


def test_plan_reports_an_unplated_lead_instead_of_dropping_them():
    """A credit that vanishes without a word is how a real person goes uncredited.

    Neither reason is fixable by a tool: writing plate copy and casting a person
    are both owner decisions, so the punch-list asks rather than guesses.
    """
    shots = [_shot("s1", 0, 8, "lead", "zavala"),
             _shot("s2", 8, 16, "lead", "ikora_rey")]
    unresolved = []
    assert plate.plan(shots, LEADS, unresolved=unresolved) == []

    by_id = {u["id"]: u for u in unresolved}
    assert by_id["zavala"]["reason"] == "no_plate_copy"
    assert by_id["zavala"]["display_name"] == "Kelsey Hightower"
    assert by_id["ikora_rey"]["reason"] == "uncast"
    assert by_id["ikora_rey"]["person"] is None
    for entry in unresolved:
        assert entry["automatable"] is False
        assert entry["blocked_on"]


def test_plan_reports_a_lead_the_cut_never_gave_a_window():
    """Unlike the copy-shaped reasons, this one a re-plan can actually fix."""
    shots = [_shot("s1", 0, 0.5, "lead", "sagira"), _shot("s2", 0.5, 20.0)]
    unresolved = []
    assert plate.plan(shots, LEADS, unresolved=unresolved) == []
    assert [(u["id"], u["reason"]) for u in unresolved] == [("sagira", "no_window")]
    assert unresolved[0]["automatable"] is True


def test_plan_does_not_report_a_lead_a_later_shot_carried():
    """A first appearance too short to plate is not a miss if a later one holds."""
    shots = [_shot("s1", 0, 0.5, "lead", "osiris"), _shot("s2", 0.5, 20, "lead", "osiris")]
    unresolved = []
    entries = plate.plan(shots, LEADS, unresolved=unresolved)
    assert [e["id"] for e in entries] == ["osiris"]
    assert unresolved == []


def test_plan_skips_a_shot_that_fails_its_binding_constraints():
    """A shot excluded from a character's retrieval is not a reveal."""
    shots = [_shot("s1", 0, 8, "lead", "osiris", usable=False)]
    assert plate.plan(shots, LEADS) == []


def test_plan_lets_a_plate_ride_across_a_cut():
    """Anchored to a short reveal shot, but not confined to it."""
    shots = [_shot("s1", 0, 2.0, "lead", "sagira"), _shot("s2", 2.0, 20.0)]
    entries = plate.plan(shots, LEADS)
    assert len(entries) == 1
    # the plate outlives its 2s anchor shot
    assert entries[0]["at"] + entries[0]["dur"] > 2.0


def test_plan_rejects_an_anchor_too_short_to_register():
    shots = [_shot("s1", 0, 0.5, "lead", "sagira"), _shot("s2", 0.5, 20.0)]
    assert plate.plan(shots, LEADS) == []


def test_plan_respects_the_render_hold_cap():
    """Plate timings must land on the rendered file, not the source timeline."""
    shots = [_shot("s1", 0, 30, "lead", "osiris"), _shot("s2", 30, 38, "lead", "sagira")]
    entries = plate.plan(shots, LEADS, max_shot_sec=9)
    sagira = next(e for e in entries if e["id"] == "sagira")
    assert sagira["at"] == pytest.approx(9 + plate.LEAD_IN)


ROSTER = {
    "month": "2026-08",
    "contributors": [{"login": f"user{i}", "commits": 1, "display_name": f"user{i}"}
                     for i in range(4)],
}


def test_plan_credits_every_contributor_somewhere():
    """The month's contributors are the ensemble; dropping them silently is the
    one unacceptable outcome."""
    shots = [
        _shot("s1", 0, 8, "ensemble", None, slots=2),
        _shot("s2", 8, 10, "ensemble", None, slots=2),   # too short for its own plate
        _shot("s3", 10, 30),                             # tail
    ]
    entries = plate.plan(shots, LEADS, ROSTER)
    named = {e.get("name") for e in entries} | {
        line for e in entries for line in e.get("body", [])}
    for c in ROSTER["contributors"]:
        assert c["display_name"] in named, c


# A contributor whose Guardian identity is genuinely authored in the reference
# deck. Injected rather than taken from vocab/casting.yaml, because the only
# real authored identity (castrojo) belongs to someone CAST AS A LEAD, and a
# lead is excluded from the ensemble pool entirely -- see
# test_a_person_cast_as_a_lead_is_never_an_anonymous_guardian.
AUTHORED = {
    "label": "TRUSTEE // GUARDIAN", "class": "Harbinger Titan",
    "name": "Jorge Castro", "title": "Upender of Antipatterns | The First Disciple",
    "trustee": True,
}
AUTHORED_ROSTER = {
    "month": "2026-08",
    "contributors": [{"login": "titled", "commits": 3,
                      "display_name": "titled", "org_member": True}],
}


@pytest.fixture
def authored(monkeypatch):
    """Give the login `titled` an authored deck identity for one test."""
    import tools.derive

    monkeypatch.setattr(tools.derive, "load_ensemble_titles",
                        lambda *a, **k: {"titled": dict(AUTHORED)})
    return AUTHORED


def test_a_contributor_with_an_authored_deck_plate_gets_it_verbatim(authored):
    """A specially-titled person: the generic copy must not stand in for it."""
    shots = [_shot("s1", 0, 8, "ensemble", None, slots=1), _shot("s2", 8, 30)]
    entries = plate.plan(shots, LEADS, AUTHORED_ROSTER)
    entry = next(e for e in entries if e["id"] == "ensemble_titled")
    assert entry["label"] == "TRUSTEE // GUARDIAN"
    assert entry["class"] == "Harbinger Titan"
    assert entry["name"] == "Jorge Castro"
    assert entry["title"] == "Upender of Antipatterns | The First Disciple"
    assert entry["trustee"] is True


def test_an_unlisted_contributor_still_gets_the_generic_ensemble_copy():
    """Nobody has authored a seal for a passing contributor, so the credit
    falls back to the generic copy -- an unknown title is a Bluefin
    Blueberry, never an invented one."""
    roster = {"month": "2026-08", "contributors": [
        {"login": "hanthor", "commits": 1, "display_name": "hanthor",
         "org_member": False}]}
    shots = [_shot("s1", 0, 8, "ensemble", None, slots=1), _shot("s2", 8, 30)]
    entries = plate.plan(shots, LEADS, roster)
    entry = next(e for e in entries if e["id"] == "ensemble_hanthor")
    assert entry["label"] == "CONTRIBUTOR // GUARDIAN"
    assert entry["name"] == "hanthor"
    assert entry["title"] == "Bluefin Blueberry"
    assert "class" not in entry and "trustee" not in entry


def test_an_authored_identity_is_not_reduced_to_a_roster_card_line(authored):
    """A specially-titled contributor who would land on the tail card gets the
    real plate in the tail instead, while the cut still has room for it."""
    shots = [
        _shot("s1", 0, 1.0, "ensemble", None, slots=1),  # too short to anchor
        _shot("s2", 1.0, 30.0),                          # tail
    ]
    entries = plate.plan(shots, LEADS, AUTHORED_ROSTER)
    entry = next(e for e in entries if e["id"] == "ensemble_titled")
    assert entry["name"] == "Jorge Castro"
    assert entry["title"] == "Upender of Antipatterns | The First Disciple"
    # ...and the sign-off card still plays, with nobody left to list on it.
    card = next(e for e in entries if e["id"] == "ensemble_roster")
    assert "body" not in card


def test_the_authored_plate_never_pushes_anyone_off_the_card(authored):
    """...but when the tail cannot hold both the plate and the card, the card
    credits everyone: dropping a contributor is the one unacceptable outcome,
    and a name line is a truer credit than none."""
    shots = [
        _shot("s1", 0, 1.0, "ensemble", None, slots=2),  # too short to anchor
        _shot("s2", 1.0, 8.0),                           # tail fits ONE window
    ]
    roster = {"month": "2026-08", "contributors": [
        {"login": "titled", "commits": 3, "display_name": "titled",
         "org_member": True},
        {"login": "hanthor", "commits": 1, "display_name": "hanthor",
         "org_member": None}]}
    entries = plate.plan(shots, LEADS, roster)
    card = next(e for e in entries if e["id"] == "ensemble_roster")
    assert card["title"] == "Thanks for working on Bluefin!"
    assert set(card["body"]) == {"titled", "hanthor"}
    plate.load_manifest_entries(entries)


def test_the_roster_card_carries_the_owner_supplied_thank_you():
    """The tail card's headline is authored copy from vocab/casting.yaml."""
    shots = [
        _shot("s1", 0, 1.0, "ensemble", None, slots=1),  # too short for a plate
        _shot("s2", 1.0, 30.0),                          # tail
    ]
    roster = {"month": "2026-08", "contributors": [
        {"login": "hanthor", "commits": 1, "display_name": "hanthor",
         "org_member": None}]}
    entries = plate.plan(shots, LEADS, roster)
    card = next(e for e in entries if e["id"] == "ensemble_roster")
    assert card["title"] == "Thanks for working on Bluefin!"
    assert card["subtitle"] == "Project Bluefin contributors, 2026-08"
    assert card["body"] == ["hanthor"]


def test_no_invented_title_survives_in_the_vocab():
    """Tombstones for copy the repo once made up for real people.

    A person's Guardian identity is reference-deck data
    (~/Videos/nameplates.json), never a lore call: Bob Killen is a Voidwalker
    Warlock (np_bob) even though he plays Osiris, and a person with no
    authored seal is a Bluefin Blueberry, per the owner's standing rule.
    """
    import yaml
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "vocab" / "casting.yaml"
    casting = yaml.safe_load(path.read_text())
    values = casting["leads"]["values"]
    assert values["osiris"]["plate"]["class"] == "Voidwalker Warlock"
    assert values["sagira"]["plate"]["title"] == "Bluefin Blueberry"
    raw = path.read_text()
    assert "Master of the Labyrinths" not in raw
    # "Dawnblade Warlock" was once invented for Bob and is banned from every
    # binding — EXCEPT zavala's, where the owner authored it for Kelsey
    # Hightower verbatim in #8. Pin exactly that one occurrence.
    dawnblade = [k for k, v in values.items()
                 if (v.get("plate") or {}).get("class") == "Dawnblade Warlock"]
    assert dawnblade == ["zavala"]


def test_plan_output_never_double_books_the_screen():
    shots = [
        _shot("s1", 0, 6, "lead", "osiris"),
        _shot("s2", 6, 9, "ensemble", None, slots=2),
        _shot("s3", 9, 13, "lead", "sagira"),
        _shot("s4", 13, 30),
    ]
    entries = plate.plan(shots, LEADS, ROSTER)
    assert len(entries) > 2
    plate.load_manifest_entries(entries)  # raises if any two overlap


SIX_ROSTER = {
    "month": "2026-08",
    "contributors": [{"login": f"user{i}", "commits": 1,
                      "display_name": f"user{i}", "org_member": False}
                     for i in range(6)],
}


def test_a_crowded_shot_spreads_its_slots_into_one_staggered_row():
    """The owner's ask: ensemble plates staggered to each of the Guardians --
    spread across the frame like the reference deck's roll call, not queued
    one after another in the right-hand corner."""
    shots = [_shot("s1", 0, 9, "ensemble", None, slots=6), _shot("s2", 9, 30)]
    entries = plate.plan(shots, LEADS, SIX_ROSTER)
    row = [e for e in entries if e.get("position") == "group"]
    assert len(row) == 6
    assert len({e["group"] for e in row}) == 1, "six slots are still one row"

    # Doubly staggered, like the deck: entrances cascade GROUP_STAGGER apart...
    starts = [e["at"] for e in row]
    assert starts == sorted(starts)
    assert starts[1] - starts[0] == pytest.approx(plate.GROUP_STAGGER)
    # ...and every card ends together.
    assert len({round(e["at"] + e["dur"], 3) for e in row}) == 1
    # The last, latest-arriving card is still on screen long enough to read.
    assert row[-1]["dur"] >= plate.MIN_HOLD

    # Spatially: an even spread inside the row margins, computed from the
    # actual rendered widths -- never off the picture, never mush.
    scale = row[0]["scale"]
    assert plate.GROUP_MIN_SCALE <= scale <= plate.GROUP_SCALE
    xs = [e["x"] for e in row]
    assert xs == sorted(xs)
    for e in row:
        assert e["scale"] == scale
        w = plate.render_plate(e).width * e["scale"]
        assert e["x"] >= plate.FRAME_W * plate.GROUP_MARGIN_X - 1
        assert e["x"] + w <= plate.FRAME_W * (1 - plate.GROUP_MARGIN_X) + 1
    plate.load_manifest_entries(entries)  # same-row overlap validates


def test_a_single_ensemble_slot_keeps_the_right_hand_plate():
    """A row of one is not a row; the solo credit stays where it was."""
    shots = [_shot("s1", 0, 9, "ensemble", None, slots=1), _shot("s2", 9, 30)]
    entries = plate.plan(shots, LEADS, ROSTER)
    assert entries[0]["position"] == "right"
    assert "group" not in entries[0]


def test_a_row_too_wide_for_one_line_splits_into_balanced_rows(authored):
    """An authored plate is much wider than the generic card; six slots
    including it split 3+3 rather than shrinking past readability. Rows never
    overlap each other -- the one-plate-at-a-time rule holds BETWEEN rows."""
    roster = {"month": "2026-08", "contributors": [
        {"login": "titled", "commits": 5, "display_name": "titled",
         "org_member": True},
        *[{"login": f"user{i}", "commits": 1, "display_name": f"user{i}",
           "org_member": False} for i in range(5)]]}
    shots = [_shot("s1", 0, 9, "ensemble", None, slots=6), _shot("s2", 9, 40)]
    entries = plate.plan(shots, LEADS, roster)
    groups = {}
    for e in entries:
        if e.get("position") == "group":
            groups.setdefault(e["group"], []).append(e)
    assert sorted(len(g) for g in groups.values()) == [3, 3]
    # the authored identity renders verbatim inside the row, not flattened
    titled = next(e for e in entries if e["id"] == "ensemble_titled")
    assert titled["name"] == "Jorge Castro"
    assert titled["title"] == "Upender of Antipatterns | The First Disciple"
    plate.load_manifest_entries(entries)


def test_a_row_that_cannot_stagger_readably_falls_back_to_sequential():
    """Room for one plate but not for a cascaded row: the shot degrades to the
    old one-after-another behaviour rather than showing an unreadable row."""
    shots = [_shot("s1", 0, 27), _shot("s2", 27, 30, "ensemble", None, slots=2)]
    entries = plate.plan(shots, LEADS, ROSTER)
    assert not any(e.get("position") == "group" for e in entries)
    assert any(e.get("position") == "right" for e in entries)
    plate.load_manifest_entries(entries)


def test_an_impossibly_wide_row_degrades_to_sequential_plates():
    """A card that would have to shrink past GROUP_MIN_SCALE is no credit at
    that size; the shot falls back to sequential right-hand plates."""
    roster = {"month": "2026-08", "contributors": [
        {"login": "aaaaaa", "commits": 1, "display_name": "x" * 130,
         "org_member": False},
        {"login": "bbbbbb", "commits": 1, "display_name": "bbbbbb",
         "org_member": False}]}
    shots = [_shot("s1", 0, 15, "ensemble", None, slots=2), _shot("s2", 15, 40)]
    entries = plate.plan(shots, LEADS, roster)
    plated = [e for e in entries if e["id"].startswith("ensemble_")]
    assert plated and all(e["position"] == "right" for e in plated)
    plate.load_manifest_entries(entries)


def test_group_rows_still_never_drop_a_contributor():
    """Six slots on one shot name six contributors, on the row or not at all."""
    shots = [_shot("s1", 0, 9, "ensemble", None, slots=6), _shot("s2", 9, 30)]
    entries = plate.plan(shots, LEADS, SIX_ROSTER)
    named = {e.get("name") for e in entries} | {
        line for e in entries for line in e.get("body", [])}
    for c in SIX_ROSTER["contributors"]:
        assert c["display_name"] in named, c


def test_render_all_handles_group_entries(tmp_path):
    """The render path reads x/scale/group straight off the manifest entry."""
    shots = [_shot("s1", 0, 9, "ensemble", None, slots=3), _shot("s2", 9, 30)]
    entries = plate.plan(shots, LEADS, ROSTER)
    row = [e for e in entries if e.get("position") == "group"]
    assert len(row) == 3
    written = plate.render_all(row, tmp_path, picture=(0, 140, 1920, 800))
    assert all(p.exists() for p in written)


def test_a_pool_smaller_than_the_slot_count_names_nobody_twice():
    """Round-robin assigns the same login twice into one shot when the pool is
    smaller than the crowd; the row still credits a person only once."""
    roster = {"month": "2026-08", "contributors": [
        {"login": "hanthor", "commits": 1, "display_name": "hanthor",
         "org_member": False}]}
    shots = [_shot("s1", 0, 9, "ensemble", None, slots=3), _shot("s2", 9, 30)]
    entries = plate.plan(shots, LEADS, roster)
    credits = [e["id"] for e in entries if e["id"].startswith("ensemble_")
               and e.get("kind") != "title"]
    assert credits == ["ensemble_hanthor"]
    plate.load_manifest_entries(entries)

PLACEHOLDER = {"label": "CONTRIBUTOR // GUARDIAN", "name": "TBD",
               "title": "Project Bluefin"}


def _placeholder_shots():
    return [
        _shot("s1", 0, 8, "ensemble", None, slots=3),
        _shot("s2", 8, 16, "ensemble", None, slots=2),
        _shot("s3", 16, 24, "lead", "osiris"),
        _shot("s4", 24, 40, "ensemble", None, slots=4),
    ]


def _placeholders_of(entries):
    return [e for e in entries if e["id"].startswith("ensemble_placeholder_")]


def test_placeholders_plate_ensemble_shots_with_the_uncast_copy():
    entries = _placeholders_of(plate.plan(_placeholder_shots(), LEADS, placeholders=2,
                                          placeholder_copy=PLACEHOLDER))
    assert len(entries) == 2
    assert [e["id"] for e in entries] == ["ensemble_placeholder_01",
                                          "ensemble_placeholder_02"]
    assert all(e["name"] == "TBD" for e in entries)


def test_placeholders_never_land_on_a_shot_with_no_ensemble_in_it():
    shots = [_shot("s1", 0, 20, "lead", "osiris"), _shot("s2", 20, 40)]
    assert _placeholders_of(plate.plan(shots, LEADS, placeholders=3)) == []


def test_placeholders_degrade_when_the_cut_has_no_room_for_them_all():
    """Asking for more plates than fit is not an error; you get what reads."""
    entries = plate.plan(_placeholder_shots(), LEADS, placeholders=99,
                         placeholder_copy=PLACEHOLDER)
    assert 0 < len(_placeholders_of(entries)) < 99
    plate.load_manifest_entries(entries)  # raises if any two overlap


def test_placeholders_do_not_double_book_a_lead_plate():
    entries = plate.plan(_placeholder_shots(), LEADS, placeholders=99,
                         placeholder_copy=PLACEHOLDER)
    plate.load_manifest_entries(entries)
    assert any(e["id"] == "osiris" for e in entries)


def test_a_roster_and_placeholders_are_mutually_exclusive():
    """Once real contributors are known, they are who the plate is for."""
    with pytest.raises(ValueError):
        plate.plan(_placeholder_shots(), LEADS, ROSTER, placeholders=2)


def test_placeholder_copy_comes_from_the_vocab_not_the_tool():
    from tools.derive import load_placeholder_plate

    copy = load_placeholder_plate()
    entry = _placeholders_of(plate.plan(_placeholder_shots(), LEADS, placeholders=1))[0]
    assert {k: v for k, v in entry.items()
            if k not in {"id", "at", "dur", "position"}} == copy


def test_plan_reports_contributors_the_tail_could_not_hold():
    """An empty `unresolved` must mean nobody was missed: when the tail has no
    room even for the roster card, every name the cut drops goes on the
    punch-list -- a log line nobody reads is still a silent drop."""
    shots = [
        _shot("s1", 0, 2, "ensemble", None, slots=2),
        _shot("s2", 2, 4, "ensemble", None, slots=2),  # no room for the roster card
    ]
    unresolved, logs = [], []
    entries = plate.plan(shots, LEADS, ROSTER, log=logs.append,
                         unresolved=unresolved)

    plated = {e["name"] for e in entries}
    # s1's two slots ride the cut as one staggered group row; nothing after
    # them fits -- not the other contributors, not even the roster card.
    assert len(entries) == 2
    assert {e.get("position") for e in entries} == {"group"}
    assert {u["display_name"] for u in unresolved} == {
        c["display_name"] for c in ROSTER["contributors"]} - plated
    for entry in unresolved:
        assert entry["reason"] == "no_window"
        assert entry["automatable"] is True
    # the human-readable line stays -- the log and the punch-list both tell it
    assert any("UNCREDITED (no room in the cut)" in line for line in logs)


def test_plan_reports_each_lead_reason():
    """The reason table a reader of `unresolved` relies on: uncast and missing
    copy are owner decisions; a missing window is not."""
    shots = [
        _shot("s1", 0, 0.5, "lead", "sagira"),       # never a window
        _shot("s2", 0.5, 8.5, "lead", "zavala"),      # binding has no plate copy
        _shot("s3", 8.5, 16.5, "lead", "ikora_rey"),  # nobody cast
        _shot("s4", 16.5, 30),
    ]
    unresolved = []
    assert plate.plan(shots, LEADS, unresolved=unresolved) == []

    by_id = {u["id"]: u for u in unresolved}
    assert by_id["ikora_rey"]["reason"] == "uncast"
    assert by_id["zavala"]["reason"] == "no_plate_copy"
    assert by_id["sagira"]["reason"] == "no_window"
    for entry in unresolved:
        assert entry["reason"] in plate.UNPLATED
        vocab_entry = plate.UNPLATED[entry["reason"]]
        assert entry["detail"] == vocab_entry["detail"]
        assert entry["automatable"] == vocab_entry["automatable"]


def test_plan_cli_reports_the_whole_punch_list(tmp_path, capsys):
    """The count the CLI prints is the list it writes: a reader who sees
    '0 unresolved' must be able to trust that nobody went uncredited."""
    shotlist = tmp_path / "shots.json"
    shotlist.write_text(json.dumps({"shots": [
        _shot("s1", 0, 2, "ensemble", None, slots=2),
        _shot("s2", 2, 4, "ensemble", None, slots=2),
    ]}))
    roster = tmp_path / "roster.json"
    roster.write_text(json.dumps(ROSTER))
    out = tmp_path / "plates.json"

    assert plate.main(["plan", str(shotlist), "--roster", str(roster),
                       "--out", str(out)]) == 0

    written = json.loads(out.read_text())
    assert len(written["unresolved"]) == len(ROSTER["contributors"]) - len(written["plates"])
    summary = capsys.readouterr().out.strip().splitlines()[-1]
    assert f"{len(written['plates'])} plate(s)" in summary
    assert f"{len(written['unresolved'])} unresolved" in summary


# --- holding a reveal (#33: "do not reveal until 1:50") ---------------------
#
# The floor is a request about the FINISHED cut's clock -- the clock the owner
# is reading off while watching it -- and it outranks the derived preference
# for a first appearance. What it must never do is buy itself the moment by
# plating somebody over a shot they are not in.

GOLD_LEADS = dict(LEADS, zavala=dict(
    LEADS["zavala"], plate={"name": "Kelsey Hightower", "variant": "leader"}))


def test_a_reveal_floor_holds_the_plate_until_the_moment_asked_for():
    shots = [_shot("s1", 0, 10, "lead", "zavala"),
             _shot("s2", 10, 20),
             _shot("s3", 20, 30, "lead", "zavala")]
    entries = plate.plan(shots, GOLD_LEADS, reveal_after=18)
    assert [e["id"] for e in entries] == ["zavala"]
    assert entries[0]["at"] == pytest.approx(20 + plate.LEAD_IN)
    assert entries[0]["variant"] == "leader"


def test_a_reveal_floor_inside_a_shot_starts_the_plate_at_the_floor():
    """The anchor may straddle the moment; the plate still lands at or after it."""
    shots = [_shot("s1", 0, 30, "lead", "zavala")]
    entries = plate.plan(shots, GOLD_LEADS, reveal_after=12)
    assert entries[0]["at"] == pytest.approx(12 + plate.LEAD_IN)


def test_a_reveal_the_footage_cannot_reach_degrades_to_the_latest_appearance():
    """Held back rather than credited is how a real person goes uncredited.

    So the reveal falls back to the closest the footage comes to the moment
    asked for -- their LAST appearance, not their first -- and the shortfall is
    reported for an owner decision.
    """
    shots = [_shot("s1", 0, 10, "lead", "zavala"),
             _shot("s2", 10, 20, "lead", "zavala"),
             _shot("s3", 20, 40)]
    unresolved = []
    entries = plate.plan(shots, GOLD_LEADS, reveal_after=110,
                         unresolved=unresolved)
    assert entries[0]["at"] == pytest.approx(10 + plate.LEAD_IN)

    assert [u["reason"] for u in unresolved] == ["reveal_floor_missed"]
    report = unresolved[0]
    assert report["id"] == "zavala"
    assert report["display_name"] == "Kelsey Hightower"
    assert report["requested_reveal_after"] == 110
    assert report["revealed_at"] == entries[0]["at"]
    assert report["automatable"] is False and report["blocked_on"]


def test_a_reveal_floor_never_moves_a_credit_onto_another_shot():
    """The one thing the floor may not buy: a name over somebody else's shot."""
    shots = [_shot("s1", 0, 10, "lead", "zavala"),
             _shot("s2", 10, 30, "lead", "osiris")]
    entries = plate.plan(shots, GOLD_LEADS, reveal_after=110)
    by_id = {e["id"]: e for e in entries}
    assert by_id["zavala"]["at"] < 10, "zavala is only in the first shot"
    assert by_id["osiris"]["at"] >= 10


def test_a_reveal_floor_does_not_report_a_character_it_could_honour():
    shots = [_shot("s1", 0, 10, "lead", "zavala"),
             _shot("s2", 10, 30, "lead", "zavala")]
    unresolved = []
    plate.plan(shots, GOLD_LEADS, reveal_after=12, unresolved=unresolved)
    assert unresolved == []


def test_reveal_after_accepts_a_timecode_on_the_cli(tmp_path):
    shotlist = tmp_path / "shots.json"
    shotlist.write_text(json.dumps({"shots": [
        _shot("s1", 0, 10, "lead", "osiris"),
        _shot("s2", 10, 30, "lead", "osiris"),
    ]}))
    out = tmp_path / "plates.json"
    assert plate.main(["plan", str(shotlist), "--reveal-after", "0:12",
                       "--out", str(out)]) == 0
    written = json.loads(out.read_text())
    assert written["plates"][0]["at"] == pytest.approx(12 + plate.LEAD_IN)


def test_no_plate_field_is_invented_beyond_the_reference_deck():
    """The reference (~/Videos/nameplates.json) has exactly these text fields.

    An earlier pass invented an `AS <CHARACTER>` casting line; this pins the
    vocabulary so copy cannot drift away from the deck again.
    """
    import yaml
    from pathlib import Path

    allowed = {"label", "class", "name", "title", "trustee",  # guardian plate
               "kind", "variant",                             # local chrome flags
               "title", "subtitle", "body"}                   # title card
    casting = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "vocab" / "casting.yaml").read_text())
    for character, entry in casting["leads"]["values"].items():
        copy = (entry or {}).get("plate")
        if not copy:
            continue
        assert set(copy) <= allowed, (character, set(copy) - allowed)
    assert set(casting["ensemble"]["placeholder_plate"]) <= allowed

    # The ensemble credit is the same closed set, plus the two eyebrow variants
    # that pick between a maintainer and a contributor, and `roster_title` --
    # the owner-supplied headline of the tail roster card (a title card's
    # `title`, looked up by purpose like the eyebrow variants).
    ensemble = dict(casting["ensemble"]["plate"])
    ensemble.pop("description", None)
    assert set(ensemble) <= allowed | {"label_member", "label_unknown", "roster_title"}

    # `ensemble.titles` maps a GitHub login to that person's AUTHORED Guardian
    # plate (an np_* entry in the reference deck); each value obeys the plate's
    # closed field set exactly like a lead's `plate:` block.
    titles = dict(casting["ensemble"].get("titles") or {})
    titles.pop("description", None)
    for login, copy in titles.items():
        assert set(copy) <= allowed, (login, set(copy) - allowed)


def test_no_plate_copy_is_written_in_the_renderer():
    """Copy lives in vocab/casting.yaml so a recast changes the credit only."""
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "tools" / "plate.py").read_text()
    for phrase in ("CONTRIBUTOR // GUARDIAN", "MAINTAINER // GUARDIAN",
                   "Bluefin Blueberry",
                   # the roster card's owner-supplied headline, and the
                   # made-up one it replaced
                   "Thanks for working on Bluefin!", "The Ensemble"):
        assert phrase not in source, f"{phrase!r} is hardcoded in tools/plate.py"


def test_title_card_renders_its_body_lines():
    card = plate.render_plate(TITLE_CARD)
    fewer = plate.render_plate(dict(TITLE_CARD, body=["castrojo"]))
    assert card.height > fewer.height


CHAT = {
    "id": "d01", "at": 3.0, "dur": 4.0, "position": "center", "kind": "chat",
    "speaker": "Lindsay Gendreau",
    "text": "Ominous rocks, killer robots, people in mortal danger.",
}


def test_chat_card_renders_the_speaker_and_the_line():
    img = plate.render_plate(CHAT)
    assert img.mode == "RGBA"
    assert img.getpixel((0, 0))[3] == 0          # the pill's rounded cap is clear
    # ...and just inside the left edge at mid-height is solid fill.
    assert img.getpixel((3, img.height // 2))[3] > 200


def test_chat_card_is_a_small_wide_lower_third_not_a_reveal():
    """The other videos' talking card is a one-line pill; the reveal chrome is
    a different, bigger component and the two must not drift back together."""
    chat = plate.render_plate(CHAT)
    reveal = plate.render_plate(GUARDIAN)
    assert chat.height < reveal.height / 2
    assert chat.width > chat.height * 4


def test_chat_card_keeps_the_blue_accent_edge():
    """The pill's hairline is the videos' blue (rgb(147 197 253 / 45%)), the
    accent the whole Wolves treatment hangs on. Over the dark fill that reads
    as a blue-tinted edge; the bare fill has b - r of 12."""
    img = plate.render_plate(CHAT)
    r, g, b, a = img.getpixel((0, img.height // 2))
    assert a > 200
    assert b - r > 25 and b > g > r


def test_chat_card_text_is_left_aligned_from_the_badge():
    """The row is laid out left-to-right from the badge: the speaker starts at
    a fixed left offset and a longer line extends rightward, never re-centres."""
    def eyebrow_left_edge(img):
        # the eyebrow is the only solid-alpha deep-blue ink right of the badge
        for x in range(plate.CHAT_PAD_L + plate.CHAT_AVATAR + 1, img.width):
            column = [img.getpixel((x, y)) for y in range(img.height)]
            if any(px[3] > 200 and px[2] - px[0] > 80 for px in column):
                return x
        return None

    short = plate.render_plate(dict(CHAT, text="Ha!"))
    long = plate.render_plate(CHAT)
    # pad + badge + gap, plus the first glyph's left side bearing
    expected = plate.CHAT_PAD_L + plate.CHAT_AVATAR + plate.CHAT_GAP
    assert eyebrow_left_edge(short) == pytest.approx(expected, abs=4)
    assert eyebrow_left_edge(long) == eyebrow_left_edge(short)


def test_chat_copy_shrinks_to_fit_instead_of_wrapping():
    """plate.html's auto-fit: the font steps down to keep one wide line --
    wrapping or hyphenating recovered dialogue would put line breaks (or
    characters) on screen that nobody said."""
    one = plate.render_plate(CHAT)
    # 80 chars: ~1690px at full size -- must shrink ~6 steps to fit the cap
    long_line = plate.render_plate(
        dict(CHAT, text=CHAT["text"] + " And they just keep coming."))
    assert long_line.height == one.height, "the card stays a single line"
    assert long_line.width > one.width
    assert long_line.width <= plate.CHAT_MAX_W + 2  # .plate max-width: 3100px at 2x


def test_chat_copy_past_the_shrink_floor_still_renders_whole():
    """plate.html stops shrinking at MIN_FONT too; a line that long renders
    whole on a wide pill rather than being clipped or broken."""
    huge = plate.render_plate(dict(CHAT, text=CHAT["text"] * 6))
    assert huge.height == plate.render_plate(CHAT).height
    assert huge.width > plate.CHAT_MAX_W


def test_a_chat_card_carries_no_guardian_rows():
    """It names the person and the line; who plays whom is the reveal's job."""
    card = plate.render_plate(CHAT)
    with_ignored_rows = plate.render_plate(
        dict(CHAT, label="TRUSTEE // GUARDIAN", **{"class": "Dawnblade Warlock"}))
    assert card.size == with_ignored_rows.size


def test_plates_sit_on_the_picture_not_on_the_letterbox_bar():
    """A 2.39:1 cinematic in a 16:9 file has ~140px of baked-in black.

    Measuring the row margin against the frame drops the plate onto that bar,
    which reads as a mistake rather than a style.
    """
    picture = (0, 140, 1920, 800)
    card = plate.render_plate(GUARDIAN)
    framed = plate.place(card, "left")
    fitted = plate.place(card, "left", picture)

    def lowest_opaque_row(img):
        alpha = img.split()[3]
        return max(y for y in range(img.height)
                   if alpha.crop((0, y, img.width, y + 1)).getextrema()[1] > 0)

    picture_bottom = picture[1] + picture[3]
    assert lowest_opaque_row(framed) > picture_bottom, "baseline hangs off the picture"
    assert lowest_opaque_row(fitted) <= picture_bottom, "fitted plate must stay on it"


def test_a_right_hand_plate_stays_inside_the_picture_width():
    picture = (0, 140, 1920, 800)
    img = plate.place(plate.render_plate(GHOST), "right", picture)
    alpha = img.split()[3]
    right_most = max(x for x in range(img.width)
                     if alpha.crop((x, 0, x + 1, img.height)).getextrema()[1] > 0)
    assert right_most <= picture[0] + picture[2]


def test_the_gold_leader_treatment_beats_trustee_silver():
    """`variant: leader` is the wolves trailer's gold plate (Christoph Blecker).

    The CSS reads `.wolves-guardian-plate-trustee:not(.wolves-guardian-plate-leader)`,
    so a cue carrying BOTH flags renders gold, not silver. Bob Killen's binding
    carries both, and this pins which one wins.
    """
    leader = plate._variant_for(dict(GUARDIAN, variant="leader"))
    assert leader is plate.VARIANTS["leader"]
    assert leader["accent"] == (250, 204, 21, 255)      # #facc15
    assert leader["label"] == (250, 204, 21, 255)
    assert leader["title"] == (253, 230, 138, 255)      # #fde68a
    # ...but the leader block never overrides .wolves-guardian-plate-class, so
    # the subclass row keeps the default blue.
    assert leader["klass"] == plate.VARIANTS["default"]["klass"]
    assert plate._variant_for(GUARDIAN) is plate.VARIANTS["trustee"]


def test_osiris_is_plated_gold():
    """The casting vocabulary, not a render, is what makes Bob Killen gold."""
    import yaml
    from pathlib import Path

    casting = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "vocab" / "casting.yaml").read_text())
    copy = casting["leads"]["values"]["osiris"]["plate"]
    assert copy["variant"] == "leader"
    assert plate._variant_for(copy) is plate.VARIANTS["leader"]


def test_the_gold_plate_actually_renders_gold_pixels():
    silver = plate.render_plate(GUARDIAN)
    gold = plate.render_plate(dict(GUARDIAN, variant="leader"))
    assert silver.size == gold.size, "chrome must not change the layout"
    assert silver.tobytes() != gold.tobytes()


def test_the_font_stack_resolves_the_way_the_browser_did():
    """`ui-monospace, SFMono-Regular, Cascadia Mono, monospace` on this host.

    Neither Apple's SF Mono nor Cascadia Mono ships on Fedora atomic, so the
    headless browser that baked the reference plates
    (~/Videos/wolves-*/render/reveal.html) fell through to the fontconfig
    generic: DejaVu Sans Mono. Preferring the desktop's Adwaita Mono instead
    rendered every plate in a typeface that is in neither the stack nor any of
    the other videos, which is what "the fonts don't look right" was.
    """
    preferred = plate.FONT_CANDIDATES["regular"][0]
    assert "DejaVuSansMono" in preferred
    assert not any("Adwaita" in path
                   for paths in plate.FONT_CANDIDATES.values()
                   for path in paths)
    for weight in ("regular", "bold"):
        assert plate._font(weight, 20) is not None


def test_the_subclass_row_keeps_its_authored_case():
    """The baked reveal reads "Behemoth Titan", not "BEHEMOTH TITAN".

    The site stylesheet uppercases .wolves-guardian-plate-class; the reveal the
    other videos actually use does not. The videos are what is being matched.
    """
    mixed = plate.render_plate(dict(GUARDIAN, **{"class": "Dawnblade Warlock"}))
    upper = plate.render_plate(dict(GUARDIAN, **{"class": "DAWNBLADE WARLOCK"}))
    assert mixed.tobytes() != upper.tobytes(), "the class row was uppercased"


def test_the_default_title_is_the_blue_the_reference_bakes():
    """reveal.html's .title is #93c5fd and tracked, not untracked slate."""
    assert plate.VARIANTS["default"]["title"] == (147, 197, 253, 255)
    assert plate.VARIANTS["default"]["klass"] == (203, 213, 245, 255)
    assert plate.LS_TITLE == 0.08


def test_the_plate_corners_are_antialiased_and_only_two_are_cut():
    """clip-path cuts top-left and bottom-right; border-radius rounds the rest."""
    img = plate.render_plate(GUARDIAN)
    w, h = img.size
    assert img.getpixel((0, 0))[3] == 0            # chamfered
    assert img.getpixel((w - 1, h - 1))[3] == 0    # chamfered
    # The rounded corners are cut back too, just far less than the chamfers.
    assert img.getpixel((w - 1, 0))[3] == 0
    assert img.getpixel((2, h - 2))[3] < 255
    # ...and a chamfer is a soft edge, not a staircase: the diagonal has
    # partially-transparent pixels along it.
    diagonal = [img.getpixel((i, plate.CHAMFER - i))[3]
                for i in range(1, plate.CHAMFER)]
    assert any(0 < a < 255 for a in diagonal), "chamfer edge is aliased"


# --- reveals wait for the hero move -----------------------------------------

def _lead_shot(segment_id, start, end, character="osiris", traversal_hero=False):
    return {"segment_id": segment_id, "start_sec": start, "end_sec": end,
            "traversal_hero": traversal_hero,
            "casting": {"role": "lead", "character": character, "usable": True,
                        "slots": 0}}


REVEAL_LEADS = {"osiris": {"person": "mrbobbytables",  # an uncast lead is
                           "plate": {"label": "TRUSTEE // GUARDIAN",
                                     "name": "Bob Killen"}}}  # reported, never plated


def test_a_reveal_waits_for_the_characters_hero_move():
    """Osiris is named as he climbs the stairwell, not on the static insert.

    The index already says which shot that is: `traversal_hero` is a derived
    "wide, stable, in motion" beat. The reveal prefers it over the character's
    literal first appearance.
    """
    shots = [_lead_shot("insert", 0.0, 8.0),
             _lead_shot("stairs", 8.0, 12.0, traversal_hero=True)]
    entries = plate.plan(shots, REVEAL_LEADS, only="leads")
    assert len(entries) == 1
    assert entries[0]["at"] == pytest.approx(8.0 + plate.LEAD_IN)


def test_a_reveal_falls_back_when_there_is_no_hero_move():
    """Sagira is a Ghost and never traverses; she is still revealed."""
    shots = [_lead_shot("insert", 0.0, 8.0), _lead_shot("more", 8.0, 12.0)]
    entries = plate.plan(shots, REVEAL_LEADS, only="leads")
    assert len(entries) == 1
    assert entries[0]["at"] == pytest.approx(plate.LEAD_IN)


def test_a_reveal_is_not_deferred_past_the_point_of_being_an_introduction():
    """Waiting too long stops being a reveal and becomes a late caption.

    The deferral is measured on the finished cut, not on source timecodes --
    cut_timeline lays shots end to end, so what matters is how long the viewer
    has actually been looking at an unnamed lead.
    """
    long_insert = plate.MAX_REVEAL_DEFERRAL + 10.0
    shots = [_lead_shot("insert", 0.0, long_insert),
             _lead_shot("stairs", long_insert, long_insert + 6.0,
                        traversal_hero=True)]
    entries = plate.plan(shots, REVEAL_LEADS, only="leads")
    assert entries[0]["at"] == pytest.approx(plate.LEAD_IN)


def test_the_hero_move_still_has_to_be_long_enough_to_read():
    """A two-second hero beat is not worth losing the reveal over."""
    shots = [_lead_shot("insert", 0.0, 8.0),
             _lead_shot("blink", 8.0, 8.3, traversal_hero=True)]
    entries = plate.plan(shots, REVEAL_LEADS, only="leads")
    assert entries[0]["at"] == pytest.approx(plate.LEAD_IN)


def test_each_lead_is_still_plated_exactly_once():
    shots = [_lead_shot("a", 0.0, 8.0),
             _lead_shot("b", 8.0, 14.0, traversal_hero=True),
             _lead_shot("c", 14.0, 20.0, traversal_hero=True),
             _lead_shot("d", 20.0, 26.0, character="sagira")]
    entries = plate.plan(shots, {**REVEAL_LEADS,
                                 "sagira": {"person": "lindsay_gendreau",
                                            "plate": {"name": "Lindsay Gendreau"}}},
                         only="leads")
    assert sorted(e["id"] for e in entries) == ["osiris", "sagira"]
    plate.load_manifest_entries(sorted(entries, key=lambda e: e["at"]))


def test_a_person_cast_as_a_lead_is_never_an_anonymous_guardian():
    """castrojo is Cayde-6, so he is not in the blueberry crowd.

    A person cannot be a named character and a nameless Guardian in the same
    project: crediting him as an anonymous contributor contradicts his casting
    and puts him in a video his character is not in. The exclusion is a rule
    over lead bindings, not a hardcoded login.
    """
    from tools.derive import load_leads
    from tools.ensemble import assign, lead_people

    leads = load_leads()
    assert "castrojo" in lead_people(leads)

    roster = {"month": "2026-08", "contributors": [
        {"login": "castrojo", "commits": 9, "display_name": "castrojo",
         "org_member": True},
        {"login": "hanthor", "commits": 1, "display_name": "hanthor",
         "org_member": True}]}
    shots = [_shot("s1", 0, 9, "ensemble", None, slots=4), _shot("s2", 9, 40)]

    result = assign(roster, [s for s in shots])
    assert "castrojo" not in {a["login"] for a in result["assignments"]}
    assert result["cast_as_lead"] == ["castrojo"]  # reported, not silent

    entries = plate.plan(shots, LEADS, roster)
    assert not any("castrojo" in e["id"] for e in entries)
    assert any(e["id"] == "ensemble_hanthor" for e in entries)


def test_castrojos_authored_plate_lives_on_his_lead_binding():
    """His identity is not lost by leaving the ensemble -- it moved to Cayde-6,
    so he is credited wherever Cayde is actually on screen."""
    from tools.derive import load_leads

    copy = load_leads()["cayde_6"]["plate"]
    assert copy["name"] == "Jorge Castro"
    assert copy["class"] == "Harbinger Titan"
    assert copy["title"] == "Upender of Antipatterns | The First Disciple"
    assert copy["label"] == "TRUSTEE // GUARDIAN"
    assert copy["trustee"] is True


def test_the_sign_off_card_plays_even_when_everyone_is_credited():
    """The card is the cut's last beat, not just an overflow list.

    Gating it on leftovers meant that crediting every contributor in the body
    silently deleted the ending the owner asked for.
    """
    roster = {"month": "2026-08", "contributors": [
        {"login": "hanthor", "commits": 1, "display_name": "hanthor",
         "org_member": True}]}
    shots = [_shot("s1", 0, 9, "ensemble", None, slots=1), _shot("s2", 9, 40)]
    entries = plate.plan(shots, LEADS, roster)
    assert any(e["id"] == "ensemble_hanthor" for e in entries)  # credited in body
    card = next(e for e in entries if e["id"] == "ensemble_roster")
    assert card["title"] == "Thanks for working on Bluefin!"
    assert "body" not in card          # nobody left to list
    assert card["at"] > entries[0]["at"]  # ...and it is the last beat
    plate.load_manifest_entries(entries)


# --- plates from a brief (the issue #1 bridge) -------------------------------
#
# A brief's plates[] are the owner speaking: copy they authored, at a moment
# they chose. The fixture below is issue #1's actual copy -- Paris Pittman is
# not a binding in vocab/casting.yaml, and a brief is the one place such a new
# claim about a real person may enter.

PARIS = {
    "label": "TRUSTEE // GUARDIAN", "name": "Paris Pittman",
    "class": "Harbringer Titan", "title": "Kolossus of Kubernetes",
    "trustee": True,
}


def _brief(*plates):
    return {"automatable": "partly", "plates": list(plates)}


def test_owner_authored_copy_reaches_a_planned_plate():
    """Paris Pittman has no binding; the brief's copy is the whole credit."""
    shots = [_shot("s1", 0, 30, "lead", "osiris")]
    brief = _brief({"at": "0:14", "copy": dict(PARIS)})
    entries = plate.plan(shots, LEADS, brief=brief)
    paris = next(e for e in entries if e["id"] == "paris_pittman")
    assert paris["label"] == "TRUSTEE // GUARDIAN"
    assert paris["name"] == "Paris Pittman"
    assert paris["class"] == "Harbringer Titan"
    assert paris["title"] == "Kolossus of Kubernetes"
    assert paris["trustee"] is True
    plate.load_manifest_entries(entries)


def test_a_copy_field_outside_the_closed_set_is_refused():
    """The deck has no pronoun row; accommodating one would invent copy."""
    shots = [_shot("s1", 0, 30, "lead", "osiris")]
    brief = _brief({"at": "0:14",
                    "copy": {**PARIS, "pronouns": "she/her"}})
    with pytest.raises(ValueError, match="closed set"):
        plate.plan(shots, LEADS, brief=brief)


def test_the_vocab_wins_a_conflict_and_says_so():
    """A brief that disagrees with a binding's `plate:` block loses to it.

    The vocab is the project's durable record of claims about real people --
    changed by reviewed PR -- while a brief is one video's request in an
    editable issue body. The conflict is reported, never adjudicated silently.
    """
    shots = [_shot("s1", 0, 30, "lead", "osiris")]
    brief = _brief({"character": "osiris", "at": "0:14",
                    "copy": {**PARIS, "name": "Not Bob Killen"}})
    lines = []
    entries = plate.plan(shots, LEADS, brief=brief, log=lines.append)
    osiris = next(e for e in entries if e["id"] == "osiris")
    assert osiris["name"] == "Bob Killen"          # the binding's copy
    assert osiris["copy_source"] == "casting"
    assert any("vocab" in line and "wins" in line for line in lines)


def test_the_owners_at_is_honoured_not_re_derived():
    """'Drop her nameplate right after she removes her helmet, 0:14.'

    The `at` is SOURCE time; the plate lands at that moment on the cut's
    clock, exactly -- no LEAD_IN, because the owner pointed at a moment inside
    the footage, not at a shot head.
    """
    shots = [_shot("s1", 10, 40, "lead", "osiris")]  # cut starts at source 10s
    brief = _brief({"at": "0:14", "copy": dict(PARIS)})
    entries = plate.plan(shots, LEADS, brief=brief)
    paris = next(e for e in entries if e["id"] == "paris_pittman")
    # source 14s is 4s into the shot, which opens the cut -> timeline 4.0
    assert paris["at"] == pytest.approx(4.0)
    assert paris["dur"] == pytest.approx(plate.DEFAULT_HOLD)


def test_an_owner_moment_that_is_not_in_the_cut_is_reported_not_moved():
    shots = [_shot("s1", 0, 30, "lead", "osiris")]
    brief = _brief({"at": "9:59", "copy": dict(PARIS)})
    lines = []
    entries = plate.plan(shots, LEADS, brief=brief, log=lines.append)
    assert not any(e["id"] == "paris_pittman" for e in entries)
    assert any("not in this cut" in line for line in lines)


def test_a_character_plate_whose_moment_is_cut_falls_back_to_the_reveal():
    """The owner's timing failed, not the credit: with a `character` named,
    the derived reveal still plates them rather than vanishing."""
    shots = [_shot("s1", 0, 30, "lead", "osiris")]
    brief = _brief({"character": "osiris", "at": "9:59"})
    lines = []
    entries = plate.plan(shots, LEADS, brief=brief, log=lines.append)
    osiris = next(e for e in entries if e["id"] == "osiris")
    assert osiris["at"] == pytest.approx(plate.LEAD_IN)  # the derived reveal
    assert any("not in this cut" in line for line in lines)


def test_a_brief_plate_for_a_binding_without_copy_uses_the_briefs():
    """zavala's binding has no `plate:` block, so the brief's copy is the one
    source that may introduce the claim -- marked as the owner's, not the
    vocab's."""
    shots = [_shot("s1", 0, 30, "lead", "zavala")]
    brief = _brief({"character": "zavala",
                    "copy": {"label": "MAINTAINER // GUARDIAN",
                             "name": "Jeffrey Sica",
                             "class": "Stormbreaker Titan",
                             "title": "Forgemaster of Kubernetes"}})
    entries = plate.plan(shots, LEADS, brief=brief)
    zavala = next(e for e in entries if e["id"] == "zavala")
    assert zavala["name"] == "Jeffrey Sica"
    assert zavala["copy_source"] == "brief"
    assert zavala["at"] == pytest.approx(plate.LEAD_IN)  # no at -> the reveal


def test_brief_plates_pin_the_timeline_and_reveals_route_around_them():
    """The owner's fixed window is taken first; the derived reveal waits for
    the next free opening rather than double-booking the screen."""
    shots = [_shot("s1", 0, 30, "lead", "osiris")]
    brief = _brief({"at": "0:01", "copy": dict(PARIS)})  # busy 1.0..6.0
    entries = plate.plan(shots, LEADS, brief=brief)
    paris = next(e for e in entries if e["id"] == "paris_pittman")
    osiris = next(e for e in entries if e["id"] == "osiris")
    assert paris["at"] == pytest.approx(1.0)
    assert osiris["at"] >= paris["at"] + paris["dur"]
    plate.load_manifest_entries(entries)  # raises if any two overlap


def test_every_planned_plate_says_where_its_copy_came_from():
    """Provenance is uniform: a reader never has to know the convention that
    an unmarked plate is the vocab's."""
    shots = [
        _shot("s1", 0, 30, "lead", "osiris"),
        _shot("s2", 30, 40, "ensemble", None, slots=1),
    ]
    brief = _brief({"at": "0:14", "copy": dict(PARIS)})
    entries = plate.plan(shots, LEADS, ROSTER, brief=brief)
    assert entries
    for e in entries:
        assert e["copy_source"] in ("brief", "casting"), e["id"]
    assert next(e for e in entries
                if e["id"] == "paris_pittman")["copy_source"] == "brief"
    assert next(e for e in entries
                if e["id"] == "osiris")["copy_source"] == "casting"


def test_a_plate_asking_for_a_character_who_is_not_in_the_cut_is_reported():
    shots = [_shot("s1", 0, 30, "lead", "osiris")]
    brief = _brief({"character": "sagira"})
    lines = []
    entries = plate.plan(shots, LEADS, brief=brief, log=lines.append)
    assert not any(e["id"] == "sagira" for e in entries)
    assert any("not in this cut" in line for line in lines)


def test_the_issue_1_brief_end_to_end_through_the_parser():
    """The real shape of issue #1's copy, parsed as a brief and planned.

    Written as the confirmed block would read; the parse path (not a hand-
    built dict) is what proves the bridge meets the brief as filed.
    """
    from tools.brief import parse_brief

    brief = parse_brief(
        "automatable: partly\n"
        "blocked_on: Paris Pittman and Jeffrey Sica are not cast in "
        "vocab/casting.yaml yet.\n"
        "plates:\n"
        "  - at: '0:14'\n"
        "    copy:\n"
        "      label: TRUSTEE // GUARDIAN\n"
        "      name: Paris Pittman\n"
        "      class: Harbringer Titan\n"
        "      title: Kolossus of Kubernetes\n"
        "      trustee: true\n"
    )
    shots = [_shot("s1", 0, 30, "lead", "osiris")]
    entries = plate.plan(shots, LEADS, brief=brief)
    paris = next(e for e in entries if e["id"] == "paris_pittman")
    assert paris["at"] == pytest.approx(14.0)
    assert paris["name"] == "Paris Pittman"
    assert paris["title"] == "Kolossus of Kubernetes"
    assert paris["copy_source"] == "brief"

# --- a lead's plate carries only what was authored ---------------------------
#
# A real person's subclass is deck data, never a lore call about the character
# they play. Karena's binding is the case where the owner supplied the class
# (Warlock) but no subclass, so the row is short a word -- and shipping it short
# is correct, because the alternative is an agent choosing a subclass for a real
# person. These pin the shape so nobody "completes" it later.

def test_the_mara_sov_plate_is_exactly_what_was_authored():
    from tools.derive import load_leads
    spec = load_leads()["mara_sov"]["plate"]
    assert spec["class"] == "Warlock", (
        "the owner supplied the class only; a subclass must come from the owner, "
        "never from an agent picking a plausible one"
    )
    assert spec["name"] == "Karena Angell"
    assert spec["title"] == "Archon of the Consensus"
    assert spec["variant"] == "leader"


def test_the_mara_sov_plate_renders():
    from tools.derive import load_leads
    img = plate.render_plate(load_leads()["mara_sov"]["plate"])
    assert img.width > 0 and img.height > 0


def test_a_lead_plate_renders_without_a_class_row():
    """The standing fallback when no class is authored at all."""
    spec = {"label": "ARCHITECT // GENERAL", "name": "Karena Angell",
            "title": "Archon of the Consensus", "variant": "leader"}
    without = plate.render_plate(spec)
    with_class = plate.render_plate(dict(spec, **{"class": "Voidwalker Warlock"}))
    assert without.height < with_class.height


def test_a_classless_lead_still_takes_its_variant_chrome():
    """Dropping a row must not drop the gold treatment with it."""
    spec = {"label": "ARCHITECT // GENERAL", "name": "Karena Angell",
            "title": "Archon of the Consensus", "variant": "leader"}
    assert plate._variant_for(spec) == plate.VARIANTS["leader"]


# Kelsey Hightower has no entry in the reference deck, but he does not need
# one: the owner authored all four rows in issue #8, and the issue IS the
# authorisation. #33's "make his nameplate golden" is then chrome ON TOP OF the
# authored copy, not instead of it -- `variant: leader`, the same treatment
# Osiris and Mara Sov carry. These pin both halves, so the copy is never
# "simplified" back to a name-only card and the chrome is never dropped.

def test_the_zavala_plate_is_gold_and_carries_the_authored_copy():
    from tools.derive import load_leads
    binding = load_leads()["zavala"]
    spec = binding["plate"]
    assert spec["variant"] == "leader"
    assert plate._variant_for(spec) is plate.VARIANTS["leader"]
    assert (spec["label"], spec["class"], spec["name"], spec["title"]) == (
        "ARCHITECT // GUARDIAN", "Dawnblade Warlock",
        "Kelsey Hightower", "Evangelist of the Open Sky"), (
        "issue #8 is the authorisation -- the owner wrote these rows, so they "
        "are reproduced verbatim; dropping them to a name-only card is the "
        "generic fallback for an authored identity, which is as wrong as an "
        "invented one")


def test_the_zavala_plate_renders_gold_with_the_authored_copy():
    from tools.derive import load_leads
    spec = load_leads()["zavala"]["plate"]
    gold = plate.render_plate(spec)
    assert gold.width > 0 and gold.height > 0
    blue = plate.render_plate({k: v for k, v in spec.items() if k != "variant"})
    assert gold.size == blue.size, "chrome must not change the layout"
    assert gold.tobytes() != blue.tobytes()


# --- ensemble direction from a brief (the issue #18 bridge) ------------------
#
# "4:03 put a bluefin maintainer in here" is the owner pinning ONE ensemble
# slot to ONE moment. The rotation still decides who fills it -- the note is
# direction, and a note that became copy would put words on whichever real
# contributor landed there.


def _ensemble_brief(*beats):
    return {"automatable": "partly", "beats": list(beats)}


def test_the_owners_ensemble_moment_is_credited_at_that_moment():
    shots = [_shot("s1", 0, 30, "ensemble", None, slots=1)]
    brief = _ensemble_brief({"at": "0:10", "note": "put a bluefin maintainer "
                                                   "in here", "ensemble": True})
    entries = plate.plan(shots, LEADS, ROSTER, brief=brief)
    fixed = next(e for e in entries
                 if e["id"].startswith("ensemble_") and e["at"] == pytest.approx(10.0))
    assert fixed["copy_source"] == "casting"
    assert "bluefin maintainer" not in json.dumps(fixed)  # the note is not copy
    plate.load_manifest_entries(entries)


def test_the_rotation_routes_around_the_owners_fixed_ensemble_moment():
    """The fixed point takes its window first; nothing double-books it, and
    nobody is credited twice."""
    shots = [_shot("s1", 0, 30, "ensemble", None, slots=2),
             _shot("s2", 30, 60, "ensemble", None, slots=2)]
    brief = _ensemble_brief({"at": "0:02", "note": "a maintainer here",
                             "ensemble": True})
    entries = plate.plan(shots, LEADS, ROSTER, brief=brief)
    assert any(e["at"] == pytest.approx(2.0) for e in entries)
    ids = [e["id"] for e in entries if e["id"].startswith("ensemble_")
           and e["id"] != "ensemble_roster"]
    assert len(ids) == len(set(ids))
    plate.load_manifest_entries(entries)


def test_the_ensemble_moment_is_honoured_when_only_the_ensemble_is_planned():
    """`--only ensemble` runs after the leads; the owner's ensemble direction
    belongs to that pass, so it must survive it."""
    shots = [_shot("s1", 0, 30, "ensemble", None, slots=1)]
    brief = _ensemble_brief({"at": "0:10", "note": "a maintainer here",
                             "ensemble": True})
    entries = plate.plan(shots, LEADS, ROSTER, brief=brief, only="ensemble")
    assert any(e["at"] == pytest.approx(10.0) for e in entries)


def test_an_ensemble_moment_outside_the_cut_is_reported_not_moved():
    shots = [_shot("s1", 0, 30, "ensemble", None, slots=1)]
    brief = _ensemble_brief({"at": "9:59", "note": "a maintainer here",
                             "ensemble": True})
    lines = []
    entries = plate.plan(shots, LEADS, ROSTER, brief=brief, log=lines.append)
    assert any("not in this cut" in line for line in lines)
    assert entries  # the rest of the cut is still planned


def test_a_beat_without_a_timecode_cannot_be_pinned_and_says_so():
    shots = [_shot("s1", 0, 30, "ensemble", None, slots=1)]
    brief = _ensemble_brief({"note": "a maintainer somewhere", "ensemble": True})
    lines = []
    plate.plan(shots, LEADS, ROSTER, brief=brief, log=lines.append)
    assert any("no `at`" in line for line in lines)


def test_an_ordinary_beat_is_still_only_direction():
    """A beat without `ensemble: true` plans nothing -- the field is how the
    owner says "this one is a request", so inferring it would execute prose."""
    shots = [_shot("s1", 0, 30, "ensemble", None, slots=1)]
    plain = plate.plan(shots, LEADS, ROSTER,
                       brief=_ensemble_brief({"at": "0:10", "note": "awesome"}))
    none = plate.plan(shots, LEADS, ROSTER)
    assert [e["at"] for e in plain] == [e["at"] for e in none]


def test_two_pinned_moments_do_not_double_book_the_screen():
    """Two pins 2s apart: the second moment lands inside the first pin's
    window. The owner's moment is never moved, so the colliding pin is
    reported and skipped -- not overlapped, and not allowed to sink the plan."""
    shots = [_shot("s1", 0, 30, "ensemble", None, slots=2),
             _shot("s2", 30, 60, "ensemble", None, slots=2)]
    brief = _ensemble_brief({"at": "0:02", "note": "first", "ensemble": True},
                            {"at": "0:04", "note": "second", "ensemble": True})
    lines = []
    entries = plate.plan(shots, LEADS, ROSTER, brief=brief, log=lines.append)
    plate.load_manifest_entries(entries)  # raises if any two overlap
    assert any(e["at"] == pytest.approx(2.0) for e in entries)
    assert not any(e["at"] == pytest.approx(4.0) for e in entries)
    assert any("already covered" in line and "second" in line
               for line in lines)


def test_a_pin_inside_a_leads_reveal_window_is_reported_not_double_booked():
    """The reveal rides across the cut (0.4s-5.4s); a pin at 0:04 lands on an
    ensemble shot but inside that window. The pin cannot move, so it is
    reported and skipped and the plan still validates."""
    shots = [_shot("s1", 0, 2, "lead", "osiris"),
             _shot("s2", 2, 30, "ensemble", None, slots=1)]
    brief = _ensemble_brief({"at": "0:04", "note": "a maintainer here",
                             "ensemble": True})
    lines = []
    entries = plate.plan(shots, LEADS, ROSTER, brief=brief, log=lines.append)
    plate.load_manifest_entries(entries)
    assert any(e["id"] == "osiris" for e in entries)
    assert not any(e["at"] == pytest.approx(4.0) for e in entries)
    assert any("already covered" in line for line in lines)


def test_a_pin_routes_around_dialogue_windows_from_around():
    """`--around` seeds `busy` with fixed windows (e.g. dialogue). A pin whose
    hold would run into one is shortened to end where it begins; one left with
    less than a readable hold is reported and skipped instead."""
    shots = [_shot("s1", 0, 30, "ensemble", None, slots=1)]
    brief = _ensemble_brief({"at": "0:10", "note": "a maintainer here",
                             "ensemble": True})
    # dialogue at 13.0-16.0: the 5s hold trims to 3.0s and the moment stands
    lines = []
    entries = plate.plan(shots, LEADS, ROSTER, brief=brief,
                         busy=[(13.0, 16.0)], log=lines.append)
    plate.load_manifest_entries(entries)
    pinned = next(e for e in entries if e["at"] == pytest.approx(10.0))
    assert pinned["dur"] == pytest.approx(3.0)
    assert any("shortened to 3.0s" in line for line in lines)
    # dialogue at 12.0-15.0: 2.0s is left -- not readable, so reported
    lines = []
    entries = plate.plan(shots, LEADS, ROSTER, brief=brief,
                         busy=[(12.0, 15.0)], log=lines.append)
    plate.load_manifest_entries(entries)
    assert not any(e["at"] == pytest.approx(10.0) for e in entries)
    assert any("only 2.0s before the next plate" in line for line in lines)


def test_a_pin_on_the_trim_boundary_has_no_hold_left_to_emit():
    """_source_moment_on_timeline accepts at_sec - s0 == duration, so a pin on
    the hold cap's edge maps to the cut's final instant, where dur rounds to
    0. That entry would fail validation; it is reported and skipped instead."""
    shots = [_shot("s1", 0, 30, "ensemble", None, slots=1)]
    brief = _ensemble_brief({"at": "0:09", "note": "edge", "ensemble": True})
    lines = []
    entries = plate.plan(shots, LEADS, ROSTER, max_shot_sec=9,
                         brief=brief, log=lines.append)
    plate.load_manifest_entries(entries)
    assert not any(e["at"] == pytest.approx(9.0) for e in entries)
    assert any("no readable hold" in line and "edge" in line
               for line in lines)


def test_pinned_beats_are_reported_when_no_ensemble_pass_will_run():
    """No roster, or --only leads: the ensemble pass never runs, so the
    brief's pinned beats produce no entry -- but they must still say why,
    not vanish silently."""
    shots = [_shot("s1", 0, 30, "lead", "osiris"),
             _shot("s2", 30, 60, "ensemble", None, slots=1)]
    brief = _ensemble_brief({"at": "0:40", "note": "a maintainer here",
                             "ensemble": True})
    lines = []
    entries = plate.plan(shots, LEADS, None, brief=brief, log=lines.append)
    plate.load_manifest_entries(entries)
    assert any(e["id"] == "osiris" for e in entries)
    assert not any(e["id"].startswith("ensemble_") for e in entries)
    assert any("no roster was given" in line and "not honoured" in line
               for line in lines)

    lines = []
    entries = plate.plan(shots, LEADS, ROSTER, brief=brief, only="leads",
                         log=lines.append)
    plate.load_manifest_entries(entries)
    assert any("--only leads" in line and "not honoured" in line
               for line in lines)


def test_a_pin_on_a_shot_with_no_ensemble_role_is_reported_not_anchored():
    """An ensemble credit may only anchor where the round-robin and the
    re-home pass could place one -- a shot with `casting.role == "ensemble"`.
    A pin on a lead shot is reported and skipped, never relocated."""
    shots = [_shot("s1", 0, 30, "lead", "osiris"),
             _shot("s2", 30, 60, "ensemble", None, slots=1)]
    brief = _ensemble_brief({"at": "0:10", "note": "a maintainer here",
                             "ensemble": True})
    lines = []
    entries = plate.plan(shots, LEADS, ROSTER, brief=brief, log=lines.append)
    plate.load_manifest_entries(entries)
    assert not any(e["at"] == pytest.approx(10.0) for e in entries)
    assert any("no ensemble role" in line and "not moved" in line
               for line in lines)
