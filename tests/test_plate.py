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
    "title": "The Ensemble", "subtitle": "Project Bluefin contributors, 2026-08",
    "body": ["castrojo", "hanthor"],
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


def test_placement_respects_the_row_margins():
    """bottom 10%, left/right 5% (.wolves-guardian-plate-row).

    The bottom margin is the site's, i.e. what a full-frame 16:9 cut gets;
    letterboxed footage is placed against the bar instead (below).
    """
    p = plate.render_plate(GUARDIAN)
    left = plate.place(p, "left", aspect=None)
    right = plate.place(p, "right", aspect=None)
    assert left.size == (plate.FRAME_W, plate.FRAME_H)

    def bbox_of(frame):
        return frame.getchannel("A").getbbox()

    lx0, ly0, lx1, ly1 = bbox_of(left)
    rx0, _, rx1, _ = bbox_of(right)
    assert lx0 == pytest.approx(plate.FRAME_W * plate.MARGIN_X, abs=2)
    assert rx1 == pytest.approx(plate.FRAME_W * (1 - plate.MARGIN_X), abs=2)
    assert ly1 == pytest.approx(plate.FRAME_H * (1 - plate.MARGIN_BOTTOM), abs=2)
    assert lx0 < rx0  # left-anchored really is further left


def test_letterbox_bar_is_zero_for_full_frame_footage():
    """16:9 (or wider) content is padded into nothing, so there is no bar."""
    assert plate.letterbox_bar(16 / 9) == 0.0
    assert plate.letterbox_bar(None) == 0.0
    # 2.39:1 in a 1920x1080 frame: ~138px of bar, picture edge at ~942.
    assert plate.letterbox_bar(2.39) == pytest.approx(138.3, abs=0.5)


@pytest.mark.parametrize("spec", [GUARDIAN, GHOST, TITLE_CARD])
def test_plate_text_sits_below_the_letterbox(spec):
    """The card is anchored to the bar, not to the frame.

    The site's 10% row margin is measured against a full-bleed player; over
    2.39:1 footage it lands the row under the name straddling the picture edge,
    half on the image and half on the bar. Placement is measured from the
    letterbox so those rows read on black.
    """
    p = plate.render_plate(spec)
    frame = plate.place(p, spec.get("position", "left"))
    _, _, _, bottom = frame.getchannel("A").getbbox()

    bar = plate.letterbox_bar()
    picture_edge = plate.FRAME_H - bar
    assert bottom > picture_edge          # seated on the bar...
    assert bottom <= plate.FRAME_H        # ...and never off the frame

    # ...far enough onto it that the plate's last row — the deck's `title` /
    # `subtitle` line — clears the picture entirely.
    last_row = plate.PAD_BOTTOM + max(plate.FS_TITLE, plate.FS_CLASS) * 1.25
    assert bottom - picture_edge >= last_row


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


def _credits(entries):
    """The contributor plates, in order — not the tail roster card."""
    return [e for e in entries
            if e["id"].startswith("ensemble_") and e.get("kind") != "title"]


def test_contributor_plates_are_spread_across_the_cut():
    """A month's credits stacked back to back read as a crawl, not casting.

    The ensemble anchors in a Destiny cinematic cluster in its opening
    firefight, so first-come placement puts every contributor in the intro.
    """
    shots = [_shot(f"s{i}", i * 3.0, i * 3.0 + 3.0, "ensemble", None, slots=1)
             for i in range(10)]
    entries = plate.plan(shots, LEADS, ROSTER)
    credits = _credits(entries)
    assert len(credits) > 1
    for earlier, later in zip(credits, credits[1:]):
        assert later["at"] - (earlier["at"] + earlier["dur"]) >= plate.MIN_SPACING


def test_spacing_holds_contributors_back_rather_than_dropping_them():
    """Whoever the cadence skips is still credited on the tail roster card."""
    shots = [_shot(f"s{i}", i * 3.0, i * 3.0 + 3.0, "ensemble", None, slots=1)
             for i in range(10)]
    spread = plate.plan(shots, LEADS, ROSTER)
    stacked = plate.plan(shots, LEADS, ROSTER, spacing=0)
    assert len(_credits(spread)) < len(_credits(stacked))  # the rule bites...

    named = {e.get("name") for e in spread} | {
        line for e in spread for line in e.get("body", [])}
    for contributor in ROSTER["contributors"]:  # ...and nobody is dropped for it
        assert contributor["display_name"] in named, contributor


def test_a_contributor_plate_shortens_rather_than_yields_to_a_later_lead():
    """A collision is not a lost credit: the plate leaves before the lead arrives."""
    shots = [
        _shot("s1", 0, 3, "ensemble", None, slots=1),
        _shot("s2", 3, 12, "lead", "osiris"),
        _shot("s3", 12, 30),
    ]
    entries = plate.plan(shots, LEADS, ROSTER)
    credit = _credits(entries)[0]
    osiris = next(e for e in entries if e["id"] == "osiris")
    assert credit["at"] == pytest.approx(plate.LEAD_IN)          # still on its anchor
    assert credit["dur"] < plate.DEFAULT_HOLD                    # ...but cut short
    assert credit["at"] + credit["dur"] <= osiris["at"]


def test_a_contributor_plate_waits_out_an_earlier_lead():
    """When the screen is already taken, the credit arrives once it clears."""
    shots = [
        _shot("s1", 0, 3, "lead", "osiris"),   # plate rides across the cut
        _shot("s2", 3, 12, "ensemble", None, slots=1),
        _shot("s3", 12, 30),
    ]
    entries = plate.plan(shots, LEADS, ROSTER)
    osiris = next(e for e in entries if e["id"] == "osiris")
    credit = _credits(entries)[0]
    assert credit["at"] >= osiris["at"] + osiris["dur"]
    assert credit["at"] < 12                  # and while its anchor is still up
    assert credit["dur"] == pytest.approx(plate.DEFAULT_HOLD)


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


def test_title_card_renders_its_body_lines():
    card = plate.render_plate(TITLE_CARD)
    fewer = plate.render_plate(dict(TITLE_CARD, body=["castrojo"]))
    assert card.height > fewer.height
