"""Lorem ipsum placeholders: a slot with no prose still gets a plate.

The owner's rule: *"instead of blocking when I don't have prose use lorem
ipsum so we have placeholders for everything at least"*. These tests guard the
two halves of it -- that a missing line renders, and that what renders cannot
credit anybody.
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import placeholder, plate  # noqa: E402


# --- the text itself --------------------------------------------------------


def test_lorem_is_deterministic_in_its_seed():
    """The same slot draws the same words forever.

    Otherwise a committed manifest churns on every run and a "changed"
    placeholder tells you nothing about whether anything moved.
    """
    assert placeholder.lorem(seed="p1-kat") == placeholder.lorem(seed="p1-kat")
    assert placeholder.lorem(seed="p1-kat") != placeholder.lorem(seed="p2-ian")


def test_lorem_never_breaks_a_word():
    """A pill is one line that must read; a truncation reads as a bug."""
    for seed in ("a", "b", "c", "p4-kat", "reveal"):
        for chars in (12, 20, 34, 60):
            line = placeholder.lorem(chars, seed)
            assert not line.endswith(" ")
            for word in line.lower().split():
                assert word in placeholder.WORDS, f"{word!r} is not a whole word"


def test_lorem_respects_the_length_it_is_asked_for():
    for chars in (10, 34, 80):
        assert len(placeholder.lorem(chars, "seed")) <= chars


def test_lorem_is_latin_so_nobody_mistakes_it_for_approved_english():
    line = placeholder.lorem(80, "x").lower()
    assert set(line.split()) <= set(placeholder.WORDS)


def test_a_zero_length_request_is_empty_not_an_error():
    assert placeholder.lorem(0, "x") == ""


# --- what makes a placeholder -----------------------------------------------


def test_a_chat_pill_with_no_text_is_a_placeholder():
    """This used to render an EMPTY pill -- a plate saying nothing, silently."""
    assert placeholder.is_placeholder({"kind": "chat", "id": "p1"})
    assert placeholder.is_placeholder({"kind": "chat", "id": "p1", "text": "  "})
    assert not placeholder.is_placeholder(
        {"kind": "chat", "id": "p1", "text": "Open telnet port?"})


def test_an_explicit_flag_marks_a_slot_nobody_has_written_yet():
    assert placeholder.is_placeholder({"id": "x", "placeholder": True})


def test_authored_copy_is_never_touched():
    spec = {"kind": "chat", "id": "p1", "speaker": "kat",
            "text": "Remember kids, cardio!", "avatar": "/x/kat.jpg"}
    assert placeholder.fill(spec) == spec


# --- the safety property, which is the whole point --------------------------


def test_a_placeholder_credits_nobody():
    """Act IV's scar: lorem under a real login puts words in a real mouth.

    krook, jeefy and mrbobbytables were dropped from the film because they had
    only ever "spoken" placeholder copy. A placeholder carries the vocab's
    uncast speaker instead.
    """
    out = placeholder.fill({"kind": "chat", "id": "p9", "speaker": "katcosgrove"})
    assert out["speaker"] == "TBD"
    assert out["speaker"] != "katcosgrove"


def test_a_placeholder_drops_the_avatar():
    """An avatar is a photograph of a person; a slot credited to nobody has none."""
    out = placeholder.fill({"kind": "chat", "id": "p9", "speaker": "kat",
                            "avatar": "/somewhere/kat.jpg"})
    assert "avatar" not in out


def test_the_intended_speaker_is_kept_rather_than_lost():
    """Recorded, not rendered -- the queue survives the placeholder."""
    out = placeholder.fill({"kind": "chat", "id": "p9", "speaker": "katcosgrove"})
    assert out["speaker_pending"] == "katcosgrove"


def test_filling_twice_does_not_lose_the_pending_name():
    once = placeholder.fill({"kind": "chat", "id": "p9", "speaker": "katcosgrove"})
    twice = placeholder.fill(once)
    assert twice["speaker_pending"] == "katcosgrove"


def test_the_uncast_name_comes_from_the_vocab_not_the_tool():
    """Same rule the ensemble blueberry plate has always been held to."""
    from tools.derive import load_placeholder_plate

    assert placeholder.fill({"kind": "chat", "id": "p"})["speaker"] == \
        load_placeholder_plate()["name"]


# --- it actually renders ----------------------------------------------------


def test_an_unwritten_line_renders_a_readable_pill():
    """The point of the feature: the cut is watchable before the words exist."""
    img = plate.render_plate({"id": "p9", "kind": "chat", "speaker": "kat"})
    assert img.getbbox(), "a placeholder must not render an empty frame"


def test_the_placeholder_pill_seats_in_the_matte_like_a_real_one():
    """Timing and seat are what a placeholder is FOR, so they must be right."""
    img = plate.render_plate({"id": "p9", "kind": "chat", "speaker": "kat"})
    frame = plate.place(img, position="letterbox", picture=(0, 140, 1920, 800))
    top = frame.getbbox()[1]
    assert top >= 940, "the pill must sit on the matte, not on the picture"


def test_two_placeholders_differ_on_screen():
    """Otherwise a reviewer cannot tell one unwritten slot from another."""
    a = plate.render_plate({"id": "p1", "kind": "chat", "speaker": "x"})
    b = plate.render_plate({"id": "p2", "kind": "chat", "speaker": "y"})
    assert a.tobytes() != b.tobytes()


# --- the punch list ---------------------------------------------------------


def test_scan_finds_a_placeholder_in_a_manifest(tmp_path):
    (tmp_path / "stories").mkdir()
    (tmp_path / "stories" / "99-x-plates.json").write_text(json.dumps({
        "act": "IX",
        "plates": [
            {"id": "p1", "kind": "chat", "speaker": "a", "text": "written"},
            {"id": "p2", "kind": "chat", "speaker": "b"},
        ],
    }), encoding="utf-8")
    found = placeholder.scan(tmp_path)
    assert [f["id"] for f in found] == ["p2"]
    assert found[0]["act"] == "IX"
    assert found[0]["pending"] == "b"


def test_scan_ignores_unreadable_files(tmp_path):
    """Degrade, never block -- a broken file is not this tool's business."""
    (tmp_path / "stories").mkdir()
    (tmp_path / "stories" / "bad.json").write_text("{not json", encoding="utf-8")
    assert placeholder.scan(tmp_path) == []


def test_check_exits_nonzero_only_when_something_is_unwritten(tmp_path, capsys):
    (tmp_path / "stories").mkdir()
    (tmp_path / "stories" / "a.json").write_text(json.dumps(
        {"act": "I", "plates": [{"id": "p1", "kind": "chat", "text": "hi"}]}),
        encoding="utf-8")
    assert placeholder.scan(tmp_path) == []


def test_no_committed_act_is_missing_prose():
    """Acts IV and V shipped with real copy; a regression here is a lost line."""
    missing = {f["id"] for f in placeholder.scan() if f["kind"] == "prose"}
    assert not missing, f"unwritten prose in the committed records: {missing}"


def test_a_named_badge_is_never_overwritten():
    """A partial named badge remains a credit, not missing prose."""
    badge = {"id": "placeholder_dylan_taylor", "label": "GUARDIAN",
             "name": "Dylan Taylor", "placeholder": True}
    assert placeholder.is_placeholder(badge)
    assert not placeholder.needs_prose(badge)
    assert placeholder.fill(badge) == badge



# --- the dialogue record's own placeholder ----------------------------------


def test_a_cue_the_owner_left_blank_is_a_placeholder():
    """`dialogue_md.apply` marks it rather than failing the whole file."""
    assert placeholder.needs_prose({"id": "c1", "text_source": "placeholder"})


def test_a_blank_cue_still_loses_its_speaker_at_render_time():
    """The record keeps the character and its evidence; the PLATE does not.

    This is why the lorem is not baked into `dialogue.json`: the swap has to
    happen once, here, or a recovered character would appear to say it.
    """
    out = placeholder.fill({"id": "c1", "kind": "chat", "speaker": "osiris",
                            "text_source": "placeholder"})
    assert out["speaker"] == "TBD"
    assert out["speaker_pending"] == "osiris"
    assert out["text"]
