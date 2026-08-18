"""Tests for the DIALOGUE.md round trip (tools/dialogue_md.py).

The Markdown is an authoring surface over a provenance record, so the tests
that matter are the ones that pin what must survive the trip: the timecodes,
the evidence, and the fact that an owner's rewrite is *recorded* as theirs
rather than quietly replacing the recovered wording.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools import dialogue, dialogue_md  # noqa: E402


LEADS = {
    "osiris": {"person": "mrbobbytables", "display_name": "mrbobbytables",
               "dialogue_label": "mrbobbytables", "aka": [],
               "plate": {"name": "Bob Killen"}},
    "sagira": {"person": "clubanderson", "display_name": "clubanderson",
               "dialogue_label": "clubanderson", "aka": ["sagira_ghost"],
               "plate": {"name": "Doctor Andy Anderson"}},
}

DATA = {
    "video_id": "vid",
    "cues": [
        {"id": "d01", "start_sec": 10.0, "end_sec": 14.0, "character": "sagira",
         "evidence": "alternation", "text": "Aren't you tired of this?"},
        {"id": "d02", "start_sec": 14.0, "end_sec": 17.0, "character": "osiris",
         "evidence": "vocative", "text": "Fatigue is a distraction."},
    ],
    "dropped": [],
}


def test_export_round_trips_without_changing_anything():
    """A file opened and saved untouched must be a no-op on the record."""
    edited = dialogue_md.parse(dialogue_md.export(DATA, LEADS), LEADS)
    updated, changes = dialogue_md.merge(DATA, edited)
    assert changes == []
    assert updated["cues"] == DATA["cues"]


def test_timecodes_survive_the_trip_exactly():
    text = dialogue_md.export(DATA, LEADS)
    assert "0:10.00 -> 0:14.00" in text
    cues = dialogue_md.parse(text, LEADS)
    assert [c["start_sec"] for c in cues] == [10.0, 14.0]


def test_a_rewritten_line_keeps_the_recovered_wording_beside_it():
    """The owner may supply copy; the recovery is never overwritten."""
    text = dialogue_md.export(DATA, LEADS).replace(
        "Fatigue is a distraction.", "Rest is for the unfocused.")
    updated, changes = dialogue_md.merge(DATA, dialogue_md.parse(text, LEADS))
    cue = next(c for c in updated["cues"] if c["id"] == "d02")
    assert cue["text"] == "Rest is for the unfocused."
    assert cue["text_source"] == "owner_supplied"
    assert cue["recovered_text"] == "Fatigue is a distraction."
    assert cue["evidence"] == "vocative"  # who spoke it did not change
    assert any("reworded" in c for c in changes)


def test_rewriting_twice_still_points_at_the_original_recovery():
    text = dialogue_md.export(DATA, LEADS).replace(
        "Fatigue is a distraction.", "First rewrite.")
    once, _ = dialogue_md.merge(DATA, dialogue_md.parse(text, LEADS))
    text = dialogue_md.export(once, LEADS).replace("First rewrite.", "Second.")
    twice, _ = dialogue_md.merge(once, dialogue_md.parse(text, LEADS))
    cue = next(c for c in twice["cues"] if c["id"] == "d02")
    assert cue["text"] == "Second."
    assert cue["recovered_text"] == "Fatigue is a distraction."


def test_the_speaker_can_be_renamed_by_character_or_by_person():
    for spelling in ("clubanderson", "sagira_ghost", "Doctor Andy Anderson"):
        text = dialogue_md.export(DATA, LEADS).replace(
            "## d02 | mrbobbytables", f"## d02 | {spelling}")
        cues = dialogue_md.parse(text, LEADS)
        assert next(c for c in cues if c["id"] == "d02")["character"] == "sagira"


def test_owner_facing_dialogue_labels_round_trip_after_normalization():
    leads = {
        **LEADS,
        "sagira": {
            **LEADS["sagira"],
            "dialogue_label": "Doctor Andy Anderson",
        },
    }
    text = dialogue_md.export(DATA, leads)
    cues = dialogue_md.parse(text, leads)
    assert next(c for c in cues if c["id"] == "d01")["character"] == "sagira"


def test_an_uncast_speaker_is_refused_rather_than_silently_dropped():
    """An unresolvable name would render no card at all; fail loudly instead."""
    text = dialogue_md.export(DATA, LEADS).replace(
        "## d02 | mrbobbytables", "## d02 | Ikora Rey")
    with pytest.raises(ValueError, match="not a cast character"):
        dialogue_md.parse(text, LEADS)


def test_replacing_a_complete_conversation_discards_obsolete_recovery():
    edited = dialogue_md.parse(dialogue_md.export(DATA, LEADS), LEADS)
    updated = dialogue_md.replace(DATA, edited)

    assert updated["text_source"]["method"] == "owner_supplied"
    assert updated["speaker_source"]["method"] == "owner_supplied"
    assert updated["dropped"] == []
    assert all(cue["evidence"] == "owner_supplied" for cue in updated["cues"])
    assert all(cue["text_source"] == "owner_supplied" for cue in updated["cues"])
    assert all("recovered_text" not in cue for cue in updated["cues"])


def test_a_deleted_section_is_recorded_as_dropped_not_lost():
    text = dialogue_md.export(DATA, LEADS)
    head, _, _ = text.partition("## d02")
    updated, changes = dialogue_md.merge(DATA, dialogue_md.parse(head, LEADS))
    assert [c["id"] for c in updated["cues"]] == ["d01"]
    assert updated["dropped"][0]["id"] == "d02"
    assert "owner" in updated["dropped"][0]["reason"]
    assert any("removed" in c for c in changes)


def test_duplicate_ids_and_backwards_timecodes_are_refused():
    text = dialogue_md.export(DATA, LEADS).replace("## d02 |", "## d01 |")
    with pytest.raises(ValueError, match="duplicate cue id"):
        dialogue_md.parse(text, LEADS)

    text = dialogue_md.export(DATA, LEADS).replace(
        "0:14.00 -> 0:17.00", "0:17.00 -> 0:14.00")
    with pytest.raises(ValueError, match="ends before it starts"):
        dialogue_md.parse(text, LEADS)


def test_a_line_left_empty_is_kept_as_a_placeholder():
    """REVERSED, on the owner's instruction: *"instead of blocking when I
    don't have prose use lorem ipsum so we have placeholders for everything at
    least"*.

    This test used to assert the opposite -- that a blank line was refused,
    because "a blank line would burn an empty card; that is a mistake, not an
    edit". The reasoning was half right: an empty card IS a mistake. The
    conclusion was wrong, because refusing the file cost every OTHER edit in
    it, and an owner who does not have the words yet had nowhere to put the
    beat. The empty card is now solved by rendering lorem instead
    (`tools/placeholder.py`), so refusing the file buys nothing.
    """
    text = dialogue_md.export(DATA, LEADS).replace(
        "Fatigue is a distraction.", "")
    cues = dialogue_md.parse(text, LEADS)
    assert next(c for c in cues if c["id"] == "d02")["text_source"] == "placeholder"


def test_a_wrapped_paragraph_rejoins_into_one_line():
    """Markdown editors reflow; a soft-wrapped line is still one line."""
    text = dialogue_md.export(DATA, LEADS).replace(
        "Fatigue is a distraction.", "Fatigue is\na distraction.")
    cues = dialogue_md.parse(text, LEADS)
    assert next(c for c in cues if c["id"] == "d02")["text"] == \
        "Fatigue is a distraction."


def test_each_video_keeps_its_conversation_in_its_own_folder(tmp_path):
    """DIALOGUE.md sits beside the record it authors, one folder per video."""
    assert dialogue.markdown_path("vid", tmp_path).name == "DIALOGUE.md"
    assert dialogue.markdown_path("vid", tmp_path).parent.name == "vid"
    assert dialogue.record_path("vid", tmp_path).name == "dialogue.json"

    path = dialogue.record_path("vid", tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(DATA), encoding="utf-8")
    assert dialogue.load_dialogue("vid", tmp_path)["cues"] == DATA["cues"]


def test_the_checked_in_markdown_matches_the_checked_in_record():
    """DIALOGUE.md is checked in, so it must not drift from dialogue.json."""
    from tools.derive import load_leads

    video_id = "yt_curse_of_osiris_opening_cinematic"
    data = dialogue.load_dialogue(video_id)
    on_disk = dialogue.markdown_path(video_id).read_text(encoding="utf-8")
    assert on_disk == dialogue_md.export(data, load_leads()), (
        "DIALOGUE.md is stale -- run "
        f"`python3 tools/dialogue_md.py export {video_id}`"
    )


# --- a line the owner has not written yet -----------------------------------


def test_a_blank_line_no_longer_fails_the_whole_file():
    """One unwritten line used to cost every other edit in the file.

    `parse` raised on a cue with no text, so an owner blocking out a beat --
    or simply not having the words yet -- lost the entire round of edits.
    That is the block the lorem-placeholder rule exists to remove.
    """
    md = dialogue_md.export(DATA, LEADS).replace("Fatigue is a distraction.", "")
    cues = dialogue_md.parse(md, LEADS)
    blank = next(c for c in cues if c["id"] == "d02")
    assert blank["text"] == ""
    assert blank["text_source"] == "placeholder"
    # and the edit that WAS made survives
    assert next(c for c in cues if c["id"] == "d01")["text"] == \
        "Aren't you tired of this?"


def test_clearing_a_line_keeps_what_was_recovered():
    """Handing a slot back is not the same as rewording it to nothing."""
    md = dialogue_md.export(DATA, LEADS).replace("Fatigue is a distraction.", "")
    updated, changes = dialogue_md.merge(DATA, dialogue_md.parse(md, LEADS))
    cue = next(c for c in updated["cues"] if c["id"] == "d02")
    assert cue["text"] == ""
    assert cue["text_source"] == "placeholder"
    assert cue["recovered_text"] == "Fatigue is a distraction."
    assert any("placeholder" in c for c in changes)


def test_a_new_blank_cue_is_a_slot_not_an_owner_supplied_line():
    """`owner_supplied` would claim they wrote something. They did not."""
    cues = [{"id": "d03", "start_sec": 20.0, "end_sec": 22.0,
             "character": "osiris", "text": ""}]
    updated, _ = dialogue_md.merge(DATA, cues)
    added = next(c for c in updated["cues"] if c["id"] == "d03")
    assert added["text_source"] == "placeholder"


def test_the_placeholder_cue_renders_credited_to_nobody():
    """End to end: a blank line in DIALOGUE.md never puts lorem on Osiris."""
    from tools.placeholder import fill

    md = dialogue_md.export(DATA, LEADS).replace("Fatigue is a distraction.", "")
    cue = next(c for c in dialogue_md.parse(md, LEADS) if c["id"] == "d02")
    plate_spec = fill({"id": cue["id"], "kind": "chat",
                       "speaker": cue["character"],
                       "text_source": cue["text_source"]})
    assert plate_spec["speaker"] == "TBD"
    assert plate_spec["speaker_pending"] == "osiris"
    assert plate_spec["text"]
