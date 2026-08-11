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

    # The ensemble credit is the same closed set, plus the two eyebrow variants
    # that pick between a maintainer and a contributor.
    ensemble = dict(casting["ensemble"]["plate"])
    ensemble.pop("description", None)
    assert set(ensemble) <= allowed | {"label_member", "label_unknown"}


def test_no_plate_copy_is_written_in_the_renderer():
    """Copy lives in vocab/casting.yaml so a recast changes the credit only."""
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "tools" / "plate.py").read_text()
    for phrase in ("CONTRIBUTOR // GUARDIAN", "MAINTAINER // GUARDIAN",
                   "Bluefin Blueberry"):
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
    assert img.getpixel((0, 0))[3] == 0          # chamfered corner
    assert img.getpixel((img.width // 2, img.height // 2))[3] > 0


def test_chat_copy_wraps_instead_of_running_off_the_card():
    """Long recovered dialogue must wrap to the CSS cap, not widen forever."""
    long_line = dict(CHAT, text=CHAT["text"] * 4)
    wide = plate.render_plate(long_line)
    assert wide.width <= plate.MAX_INNER_W + 2 * plate.PAD_X + 1
    assert wide.height > plate.render_plate(CHAT).height


def test_wrapping_never_breaks_a_word():
    """Hyphenating recovered dialogue would put characters nobody said on screen."""
    font = plate._font("regular", plate.FS_CLASS)
    lines = plate._wrap("supercalifragilistic and some more words here", font, 120)
    assert "supercalifragilistic" in lines
    assert all("-" not in line for line in lines)


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


REVEAL_LEADS = {"osiris": {"plate": {"label": "TRUSTEE // GUARDIAN",
                                     "name": "Bob Killen"}}}


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
                                 "sagira": {"plate": {"name": "Lindsay Gendreau"}}},
                         only="leads")
    assert sorted(e["id"] for e in entries) == ["osiris", "sagira"]
    plate.load_manifest_entries(sorted(entries, key=lambda e: e["at"]))
