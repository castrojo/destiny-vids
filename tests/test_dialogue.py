"""Tests for the recovered-dialogue planner (tools/dialogue.py)."""
import json
from pathlib import Path

import pytest

from tools import dialogue, plate  # noqa: E402

LEADS = {
    "osiris": {"person": "mrbobbytables", "display_name": "mrbobbytables",
               "github": "mrbobbytables",
               "plate": {"label": "TRUSTEE // GUARDIAN", "name": "Bob Killen"}},
    "sagira": {"person": "clubanderson", "display_name": "clubanderson",
               "github": "clubanderson",
               "plate": {"label": "MAINTAINER // GUARDIAN",
                         "name": "Doctor Andy Anderson"}},
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
    assert first["speaker"] == "Doctor Andy Anderson"
    assert first["kind"] == "chat"
    assert first["avatar"] == "renders/avatars/clubanderson.png"

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
    assert [e["speaker"] for e in entries] == ["Doctor Andy Anderson",
                                               "Bob Killen"]
    assert [e["avatar"] for e in entries] == [
        "renders/avatars/clubanderson.png",
        "renders/avatars/mrbobbytables.png",
    ]

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

def test_script_mode_can_begin_at_the_first_authored_display_cue():
    entries, _ = dialogue.plan_script(
        CUES, [shot("long", 0.0, 100.0)], LEADS, start_at=32.56)
    assert entries[0]["at"] == pytest.approx(32.56)

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
    assert data["text_source"]["method"] == "owner_supplied"
    assert data["speaker_source"]["method"] == "owner_supplied"
    assert data["display"] == {
        "mode": "script",
        "start_sec": 32.56,
        "standalone_leads": False,
        "note": (
            "The owner replaced the complete conversation. Script layout keeps "
            "all 25 lines readable in order; standalone lead plates are omitted "
            "because every dialogue pill identifies Doctor Andy Anderson or "
            "Bob Killen."
        ),
    }


@pytest.mark.parametrize(
    "cue_id, expected",
    [
        ("d20a", (121.44, 124.91, "osiris")),
        ("d20b", (124.92, 128.91, "osiris")),
        ("d21", (128.92, 133.95, "osiris")),
        ("d23a", (134.64, 136.11, "sagira")),
        ("d23b", (136.12, 137.59, "sagira")),
    ],
)
def test_act3_review_cues_pin_exact_timing_and_speaker(cue_id, expected):
    data = dialogue.load_dialogue("yt_curse_of_osiris_opening_cinematic")
    cue = next(cue for cue in data["cues"] if cue["id"] == cue_id)
    assert (cue["start_sec"], cue["end_sec"], cue["character"]) == expected


def test_act3_review_cue_splits_keep_the_owner_marked_hundredth_adjacency():
    data = dialogue.load_dialogue("yt_curse_of_osiris_opening_cinematic")
    cues = {cue["id"]: cue for cue in data["cues"]}
    for earlier, later in (("d20a", "d20b"), ("d20b", "d21"), ("d23a", "d23b")):
        assert cues[later]["start_sec"] == cues[earlier]["end_sec"] + 0.01


def test_act3_fixed_gold_bob_plate_matches_complete_authored_entry():
    manifest = json.loads(
        Path("stories/yt_curse_of_osiris_opening_cinematic-fixed-plates.json")
        .read_text(encoding="utf-8")
    )
    gold = next(plate for plate in manifest["plates"] if plate["id"] == "mrbobbytables-gold")
    assert gold == {
        "id": "mrbobbytables-gold",
        "at": 43.96,
        "dur": 4.0,
        "position": "left",
        "copy_source": "casting",
        "label": "TRUSTEE // GUARDIAN",
        "class": "Voidwalker Warlock",
        "name": "Bob Killen",
        "title": "Reconciler of the Plane",
        "trustee": True,
        "variant": "leader",
    }


def test_the_retirement_conversation_no_longer_opens_act_three():
    """Moved verbatim to act II on 2026-08-24 at the owner's word; the
    verbatim act II copy is pinned in test_efmb_act.py."""
    path = Path("stories/yt_curse_of_osiris_opening_cinematic-fixed-plates.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    plate.load_manifest_entries(data["plates"])
    assert not [p for p in data["plates"] if p["id"].startswith("retirement-")]
    assert data["_anchor"] == "immediately before the wolf day shot appears"

    builder = Path("scripts/build_uncut_credited.sh").read_text(encoding="utf-8")
    assert 'FIXED_MANIFEST="stories/$VIDEO_ID-fixed-plates.json"' in builder
    assert 'FIXED_INPUTS+=("$FIXED_MANIFEST")' in builder
    assert 'display.get("standalone_leads", True)' in builder
    assert 'python3 tools/plate.py merge "${FIXED_INPUTS[@]}" --out "$WORK/fixed.json"' in builder
    assert '    --around "$WORK/fixed.json"' in builder


def test_act_three_review_copy_and_splits_are_exact():
    data = dialogue.load_dialogue("yt_curse_of_osiris_opening_cinematic")
    by_id = {c["id"]: c for c in data["cues"]}
    assert by_id["d01"]["text"] == "What a shitshow"
    assert by_id["d20a"]["text"] == "Everyone forgot how to use KVM! We need to split up"
    assert by_id["d20b"]["text"] == "Everyone's making their own and it's all bad!"
    assert by_id["d21"]["text"] == "They've broken out of the sandbox"
    assert by_id["d23a"]["text"] == "The open rate of maintainer emails is 7%"
    assert by_id["d23b"]["text"] == "I don't like this plan"
    ids = [c["id"] for c in data["cues"]]
    assert ids.index("d20a") < ids.index("d20b") < ids.index("d21")
    assert ids.index("d23a") < ids.index("d23b") < ids.index("d24")
