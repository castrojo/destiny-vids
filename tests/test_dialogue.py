"""Tests for the recovered-dialogue planner (tools/dialogue.py)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools import dialogue, plate  # noqa: E402


LEADS = {
    "osiris": {"person": "mrbobbytables", "display_name": "mrbobbytables",
               "plate": {"label": "TRUSTEE // GUARDIAN", "name": "Bob Killen"}},
    "sagira": {"person": "lindsay_gendreau", "display_name": "Lindsay Gendreau",
               "plate": {"label": "EMOTIONAL SUPPORT // GHOST",
                         "name": "Lindsay Gendreau", "kind": "ghost"}},
    "ikora_rey": {"person": None, "display_name": None, "plate": None},
}

CUES = [
    {"id": "d01", "start_sec": 10.0, "end_sec": 14.0, "character": "sagira",
     "evidence": "alternation", "text": "Aren't you tired of this?"},
    {"id": "d02", "start_sec": 14.0, "end_sec": 17.0, "character": "osiris",
     "evidence": "alternation", "text": "Fatigue is a distraction."},
    {"id": "d03", "start_sec": 40.0, "end_sec": 44.0, "character": "sagira",
     "evidence": "uncertain", "text": "Ouch."},
]


def shot(segment_id, start, end, role="none", character=None):
    return {"segment_id": segment_id, "start_sec": start, "end_sec": end,
            "casting": {"role": role, "character": character, "slots": 0,
                        "usable": True}}


# The cut holds the first cue's footage but not the third's.
SHOTS = [shot("a", 8.0, 18.0), shot("b", 60.0, 70.0)]


def test_speaker_is_the_credited_person_not_the_character():
    """The chat card names the person, using the same copy as their reveal."""
    assert dialogue._speaker_for("osiris", LEADS) == "Bob Killen"


def test_an_uncast_character_gets_no_card():
    assert dialogue._speaker_for("ikora_rey", LEADS) is None
    entries, dropped = dialogue.plan_chat(
        [{"id": "x", "start_sec": 9.0, "end_sec": 12.0, "character": "ikora_rey",
          "text": "..."}], SHOTS, LEADS)
    assert entries == []
    assert "not cast" in dropped[0]["reason"]


def test_anchored_lines_land_where_their_footage_landed():
    entries, _ = dialogue.plan_chat(CUES, SHOTS, LEADS)
    first = next(e for e in entries if e["id"] == "d01")
    # Shot "a" starts at 8.0 of source and at 0.0 of the cut, so the cue at
    # 10.0 lands 2.0s in.
    assert first["at"] == pytest.approx(2.0)
    assert first["speaker"] == "Lindsay Gendreau"
    assert first["kind"] == "chat"


def test_a_line_whose_footage_is_not_in_the_cut_is_reported_not_dropped_silently():
    # d03 is also the fixture's `uncertain` cue, and chat mode now drops that
    # at the earlier gate (see the attribution test below). This test is about
    # the FOOTAGE check, so keep the cue alive long enough to reach it.
    _, dropped = dialogue.plan_chat(CUES, SHOTS, LEADS, skip_uncertain=False)
    assert any(d["id"] == "d03" and "not in this cut" in d["reason"]
               for d in dropped)


def test_chat_mode_skips_a_speaker_the_anchors_do_not_settle():
    """An unsettled line names one of two real people; it must not be shown.

    `plan_script` has always dropped these. `plan_chat` -- the DEFAULT mode,
    and the one the skill docs recommend -- did not check at all, so a cue the
    recovered record explicitly says it cannot attribute was burned on screen
    crediting whichever person the character happened to be bound to.
    """
    entries, dropped = dialogue.plan_chat(CUES, SHOTS, LEADS)
    assert all(e["id"] != "d03" for e in entries)
    assert any(d["id"] == "d03" and "not settled" in d["reason"] for d in dropped)


def test_chat_mode_still_places_the_settled_lines():
    """The fix drops the unsettled line only -- not the conversation."""
    entries, _ = dialogue.plan_chat(CUES, SHOTS, LEADS)
    assert [e["id"] for e in entries] == ["d01", "d02"]
    assert [e["speaker"] for e in entries] == ["Lindsay Gendreau",
                                               "Bob Killen"]


def test_dialogue_never_double_books_the_screen():
    entries, _ = dialogue.plan_chat(CUES, SHOTS, LEADS)
    plate.load_manifest_entries(entries)  # raises if any two overlap


def test_a_reveal_already_holding_the_screen_wins():
    """Reveals are planned first: an anchored line cannot slide, so it drops."""
    entries, dropped = dialogue.plan_chat(CUES, SHOTS, LEADS,
                                          busy=[(1.5, 6.0)])
    assert all(e["id"] != "d01" for e in entries)
    assert any(d["id"] == "d01" and "reveal" in d["reason"] for d in dropped)


def test_script_mode_keeps_the_exchange_in_spoken_order():
    entries, _ = dialogue.plan_script(CUES, SHOTS, LEADS)
    assert [e["id"] for e in entries] == ["d01", "d02"]
    assert entries[0]["at"] < entries[1]["at"]


def test_script_mode_skips_a_speaker_the_anchors_do_not_settle():
    entries, dropped = dialogue.plan_script(CUES, SHOTS, LEADS)
    assert all(e["id"] != "d03" for e in entries)
    assert any(d["id"] == "d03" and "not settled" in d["reason"] for d in dropped)
    kept, _ = dialogue.plan_script(CUES, SHOTS, LEADS, skip_uncertain=False)
    assert any(e["id"] == "d03" for e in kept)


def test_script_mode_flows_around_a_reveal():
    busy = [(0.0, 6.0)]
    entries, _ = dialogue.plan_script(CUES, SHOTS, LEADS, busy=busy)
    assert entries[0]["at"] >= 6.0
    plate.load_manifest_entries(entries)


def test_the_indexed_dialogue_file_is_loadable_and_attributed():
    """The checked-in recovery must stay machine-readable and fully attributed."""
    data = dialogue.load_dialogue("yt_curse_of_osiris_opening_cinematic")
    assert data["cues"], "no cues recovered"
    for cue in data["cues"]:
        assert cue["character"] in ("osiris", "sagira")
        assert cue["evidence"] in ("vocative", "alternation", "uncertain",
                                   "owner_supplied")
        assert cue["end_sec"] > cue["start_sec"]
        assert cue["text"].strip()
    # Provenance is the point: the copy is recovered, not authored here.
    assert data["text_source"]["method"] == "youtube_auto_captions"
    assert data["speaker_source"]["method"] == "vocative_alternation"
