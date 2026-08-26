"""Tests for the DIALOGUE.md round trip (tools/dialogue_md.py).

The Markdown is an authoring surface over a provenance record, so the tests
that matter are the ones that pin what must survive the trip: the timecodes,
the evidence, and the fact that an owner's rewrite is *recorded* as theirs
rather than quietly replacing the recovered wording.
"""
import json
from pathlib import Path

import pytest

from tools import dialogue, dialogue_md  # noqa: E402

RECOVERY_FIXTURE = Path(__file__).with_name("fixtures") / "acts_ii_iii_recovery.json"
VIDEO_ID = "yt_curse_of_osiris_opening_cinematic"

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
PRESENTATION = {
    "video_id": "vid",
    "mode": "script",
    "start_sec": 0.0,
    "sequence": ["d01", "d02"],
    "pins": {},
}


def recovery_fixture():
    return json.loads(RECOVERY_FIXTURE.read_text(encoding="utf-8"))


def load_fixture_source_tuples():
    return {
        item["id"]: tuple(item["source_tuple"])
        for item in recovery_fixture()["act_iii"]["active"]
    }


def source_tuples(record):
    return {
        cue["id"]: (
            cue["character"],
            cue["text"],
            cue["start_sec"],
            cue["end_sec"],
            cue.get("recovered_text"),
        )
        for cue in record["cues"]
    }

def test_export_round_trips_without_changing_anything():
    """A file opened and saved untouched must be a no-op on the record."""
    edited = dialogue_md.parse(dialogue_md.export(DATA, LEADS, PRESENTATION), LEADS)
    updated, changes = dialogue_md.merge(DATA, edited)
    presentation, presentation_changes = dialogue_md.merge_presentation(
        PRESENTATION, edited)
    assert changes == []
    assert presentation_changes == []
    assert updated["cues"] == DATA["cues"]
    assert presentation == PRESENTATION


def test_a_pin_segment_round_trips_through_the_markdown():
    """`| pin 1:57.00` in a heading lands on the record as film seconds, and
    export writes it back verbatim so the checked-in file cannot drift."""
    pinned = {**PRESENTATION, "pins": {"d02": 117.0}}
    text = dialogue_md.export(DATA, LEADS, pinned)
    assert "| pin 1:57.00" in text
    cues = dialogue_md.parse(text, LEADS)
    assert next(c for c in cues if c["id"] == "d02")["pin_sec"] == 117.0
    updated, changes = dialogue_md.merge(DATA, cues)
    presentation, presentation_changes = dialogue_md.merge_presentation(
        pinned, cues)
    assert changes == []
    assert presentation_changes == []
    assert updated["cues"] == DATA["cues"]
    assert presentation == pinned


def test_apply_preserves_presentation_only_hold_overrides():
    preserved = {**PRESENTATION, "holds": {"d02": 3.65}}
    cues = dialogue_md.parse(dialogue_md.export(DATA, LEADS, preserved), LEADS)
    updated, changes = dialogue_md.merge(DATA, cues)
    presentation, presentation_changes = dialogue_md.merge_presentation(
        preserved, cues)
    assert updated["cues"] == DATA["cues"]
    assert changes == []
    assert presentation_changes == []
    assert presentation == preserved


def test_removing_the_pin_segment_unpins_the_cue():
    pinned = {**PRESENTATION, "pins": {"d02": 117.0}}
    cues = dialogue_md.parse(dialogue_md.export(DATA, LEADS, PRESENTATION), LEADS)
    updated, changes = dialogue_md.merge(DATA, cues)
    presentation, presentation_changes = dialogue_md.merge_presentation(
        pinned, cues)
    assert updated["cues"] == DATA["cues"]
    assert changes == []
    assert presentation == PRESENTATION
    assert any("unpinned" in c for c in presentation_changes)

def test_timecodes_survive_the_trip_exactly():
    text = dialogue_md.export(DATA, LEADS, PRESENTATION)
    assert "0:10.00 -> 0:14.00" in text
    cues = dialogue_md.parse(text, LEADS)
    assert [c["start_sec"] for c in cues] == [10.0, 14.0]

def test_a_rewritten_line_keeps_the_recovered_wording_beside_it():
    """The owner may supply copy; the recovery is never overwritten."""
    text = dialogue_md.export(DATA, LEADS, PRESENTATION).replace(
        "Fatigue is a distraction.", "Rest is for the unfocused.")
    updated, changes = dialogue_md.merge(DATA, dialogue_md.parse(text, LEADS))
    cue = next(c for c in updated["cues"] if c["id"] == "d02")
    assert cue["text"] == "Rest is for the unfocused."
    assert cue["text_source"] == "owner_supplied"
    assert cue["recovered_text"] == "Fatigue is a distraction."
    assert cue["evidence"] == "vocative"  # who spoke it did not change
    assert any("reworded" in c for c in changes)

def test_rewriting_twice_still_points_at_the_original_recovery():
    text = dialogue_md.export(DATA, LEADS, PRESENTATION).replace(
        "Fatigue is a distraction.", "First rewrite.")
    once, _ = dialogue_md.merge(DATA, dialogue_md.parse(text, LEADS))
    text = dialogue_md.export(once, LEADS, PRESENTATION).replace(
        "First rewrite.", "Second.")
    twice, _ = dialogue_md.merge(once, dialogue_md.parse(text, LEADS))
    cue = next(c for c in twice["cues"] if c["id"] == "d02")
    assert cue["text"] == "Second."
    assert cue["recovered_text"] == "Fatigue is a distraction."

def test_the_speaker_can_be_renamed_by_character_or_by_person():
    for spelling in ("clubanderson", "sagira_ghost"):
        text = dialogue_md.export(DATA, LEADS, PRESENTATION).replace(
            "## d02 | osiris", f"## d02 | {spelling}")
        cues = dialogue_md.parse(text, LEADS)
        assert next(c for c in cues if c["id"] == "d02")["character"] == "sagira"


def test_a_shared_login_cannot_choose_between_two_characters():
    leads = {
        "elsie_bray": {"person": "nimbinatus", "aka": []},
        "nimbatus": {"person": "nimbinatus", "aka": []},
    }
    data = {"video_id": "vid", "cues": [
        {"id": "d01", "start_sec": 0.0, "end_sec": 2.0,
         "character": "elsie_bray", "text": "Hi"},
        {"id": "d02", "start_sec": 2.0, "end_sec": 4.0,
         "character": "nimbatus", "text": "Bye"},
    ]}
    exported = dialogue_md.export(data, leads, PRESENTATION)
    assert "## d01 | elsie_bray" in exported
    assert "## d02 | nimbatus" in exported
    ambiguous = exported.replace("## d01 | elsie_bray", "## d01 | nimbinatus")
    with pytest.raises(ValueError, match="ambiguous GitHub login"):
        dialogue_md.parse(ambiguous, leads)


def test_display_names_are_not_dialogue_aliases():
    text = dialogue_md.export(DATA, LEADS, PRESENTATION).replace(
        "## d02 | osiris", "## d02 | Doctor Andy Anderson")
    with pytest.raises(ValueError, match="not a cast character"):
        dialogue_md.parse(text, LEADS)

def test_an_uncast_speaker_is_refused_rather_than_silently_dropped():
    """An unresolvable name would render no card at all; fail loudly instead."""
    text = dialogue_md.export(DATA, LEADS, PRESENTATION).replace(
        "## d02 | osiris", "## d02 | Ikora Rey")
    with pytest.raises(ValueError, match="not a cast character"):
        dialogue_md.parse(text, LEADS)

def test_replacing_a_complete_conversation_discards_obsolete_recovery():
    edited = dialogue_md.parse(dialogue_md.export(DATA, LEADS, PRESENTATION), LEADS)
    updated = dialogue_md.replace(DATA, edited)

    assert updated["text_source"]["method"] == "owner_supplied"
    assert updated["speaker_source"]["method"] == "owner_supplied"
    assert updated["dropped"] == []
    assert all(cue["evidence"] == "owner_supplied" for cue in updated["cues"])
    assert all(cue["text_source"] == "owner_supplied" for cue in updated["cues"])
    assert all("recovered_text" not in cue for cue in updated["cues"])


def test_replacing_a_complete_conversation_also_refuses_source_window_edits():
    text = dialogue_md.export(DATA, LEADS, PRESENTATION).replace(
        "## d02 | osiris | 0:14.00 -> 0:17.00",
        "## d02 | osiris | 0:09.00 -> 0:17.00")
    with pytest.raises(
        ValueError,
        match=r"d02: source timecodes are evidence; restore them from a git ref",
    ):
        dialogue_md.replace(DATA, dialogue_md.parse(text, LEADS))

def test_a_deleted_section_is_recorded_as_dropped_not_lost():
    text = dialogue_md.export(DATA, LEADS, PRESENTATION)
    head, _, _ = text.partition("## d02")
    updated, changes = dialogue_md.merge(DATA, dialogue_md.parse(head, LEADS))
    assert [c["id"] for c in updated["cues"]] == ["d01"]
    assert updated["dropped"][0]["id"] == "d02"
    assert "owner" in updated["dropped"][0]["reason"]
    assert any("removed" in c for c in changes)

def test_a_restored_section_leaves_the_dropped_list():
    """Restoring is dropping in reverse, and has to be as complete: a line
    recorded as both spoken and retired contradicts itself about words in a
    real person's mouth."""
    text = dialogue_md.export(DATA, LEADS, PRESENTATION)
    head, _, _ = text.partition("## d02")
    dropped_data, _ = dialogue_md.merge(DATA, dialogue_md.parse(head, LEADS))
    assert [c["id"] for c in dropped_data["dropped"]] == ["d02"]

    restored, changes = dialogue_md.merge(
        dropped_data, dialogue_md.parse(text, LEADS))
    assert [c["id"] for c in restored["cues"]] == ["d01", "d02"]
    assert restored["dropped"] == []
    assert any("restored" in c for c in changes)


def test_a_restored_section_keeps_the_wording_it_was_retired_with():
    """The owner is owed the same view of a restored line as of a reworded
    one: what it used to say, kept beside what it says now."""
    text = dialogue_md.export(DATA, LEADS, PRESENTATION)
    head, _, _ = text.partition("## d02")
    dropped_data, _ = dialogue_md.merge(DATA, dialogue_md.parse(head, LEADS))

    reworded = text.replace("Fatigue is a distraction.", "Fatigue is a choice.")
    restored, _ = dialogue_md.merge(
        dropped_data, dialogue_md.parse(reworded, LEADS))
    d02 = next(c for c in restored["cues"] if c["id"] == "d02")
    assert d02["text"] == "Fatigue is a choice."
    assert d02["recovered_text"] == "Fatigue is a distraction."
    assert restored["dropped"] == []


def test_a_restored_section_unchanged_carries_no_recovered_text():
    """Bringing a line back verbatim is not a rewrite, so there is nothing
    to keep beside it."""
    text = dialogue_md.export(DATA, LEADS, PRESENTATION)
    head, _, _ = text.partition("## d02")
    dropped_data, _ = dialogue_md.merge(DATA, dialogue_md.parse(head, LEADS))
    restored, _ = dialogue_md.merge(
        dropped_data, dialogue_md.parse(text, LEADS))
    d02 = next(c for c in restored["cues"] if c["id"] == "d02")
    assert "recovered_text" not in d02


def test_duplicate_ids_and_backwards_timecodes_are_refused():
    text = dialogue_md.export(DATA, LEADS, PRESENTATION).replace("## d02 |", "## d01 |")
    with pytest.raises(ValueError, match="duplicate cue id"):
        dialogue_md.parse(text, LEADS)

    text = dialogue_md.export(DATA, LEADS, PRESENTATION).replace(
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
    text = dialogue_md.export(DATA, LEADS, PRESENTATION).replace(
        "Fatigue is a distraction.", "")
    cues = dialogue_md.parse(text, LEADS)
    assert next(c for c in cues if c["id"] == "d02")["text_source"] == "placeholder"

def test_a_wrapped_paragraph_rejoins_into_one_line():
    """Markdown editors reflow; a soft-wrapped line is still one line."""
    text = dialogue_md.export(DATA, LEADS, PRESENTATION).replace(
        "Fatigue is a distraction.", "Fatigue is\na distraction.")
    cues = dialogue_md.parse(text, LEADS)
    assert next(c for c in cues if c["id"] == "d02")["text"] == \
        "Fatigue is a distraction."

def test_each_video_keeps_its_conversation_in_its_own_folder(tmp_path):
    """DIALOGUE.md sits beside the record it authors, one folder per video."""
    assert dialogue.markdown_path("vid", tmp_path).name == "DIALOGUE.md"
    assert dialogue.markdown_path("vid", tmp_path).parent.name == "vid"
    assert dialogue.record_path("vid", tmp_path).name == "dialogue.json"
    assert dialogue.presentation_path("vid", tmp_path).name == "presentation.json"

    path = dialogue.record_path("vid", tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(DATA), encoding="utf-8")
    dialogue.presentation_path("vid", tmp_path).write_text(
        json.dumps(PRESENTATION), encoding="utf-8")
    assert dialogue.load_dialogue("vid", tmp_path)["cues"] == DATA["cues"]
    assert dialogue.load_presentation("vid", tmp_path) == PRESENTATION

def test_the_checked_in_markdown_matches_the_checked_in_record():
    """DIALOGUE.md is checked in, so it must not drift from dialogue.json."""
    from tools.derive import load_leads

    data = dialogue.load_dialogue(VIDEO_ID)
    presentation = dialogue.load_presentation(VIDEO_ID)
    on_disk = dialogue.markdown_path(VIDEO_ID).read_text(encoding="utf-8")
    assert on_disk == dialogue_md.export(data, load_leads(), presentation), (
        "DIALOGUE.md is stale -- run "
        f"`python3 tools/dialogue_md.py export {VIDEO_ID}`"
    )


def test_act3_export_apply_preserves_every_recovered_source_cue(tmp_path):
    from tools.derive import load_leads

    target = dialogue.record_path(VIDEO_ID, root=tmp_path)
    plan_target = dialogue.presentation_path(VIDEO_ID, root=tmp_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        dialogue.record_path(VIDEO_ID).read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    plan_target.write_text(
        dialogue.presentation_path(VIDEO_ID).read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    before = load_fixture_source_tuples()
    data = dialogue.load_dialogue(VIDEO_ID, root=tmp_path)
    presentation = dialogue.load_presentation(VIDEO_ID, root=tmp_path)
    text = dialogue_md.export(data, load_leads(), presentation)
    dialogue.markdown_path(VIDEO_ID, root=tmp_path).write_text(
        text, encoding="utf-8")
    edited = dialogue_md.parse(text, load_leads())
    updated, changes = dialogue_md.merge(data, edited)
    updated_presentation, presentation_changes = dialogue_md.merge_presentation(
        presentation, edited)
    assert changes == []
    assert presentation_changes == []
    target.write_text(
        json.dumps(updated, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    plan_target.write_text(
        json.dumps(updated_presentation, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    after = source_tuples(dialogue.load_dialogue(VIDEO_ID, root=tmp_path))
    assert after == before

# --- a line the owner has not written yet -----------------------------------

def test_a_blank_line_no_longer_fails_the_whole_file():
    """One unwritten line used to cost every other edit in the file.

    `parse` raised on a cue with no text, so an owner blocking out a beat --
    or simply not having the words yet -- lost the entire round of edits.
    That is the block the lorem-placeholder rule exists to remove.
    """
    md = dialogue_md.export(DATA, LEADS, PRESENTATION).replace(
        "Fatigue is a distraction.", "")
    cues = dialogue_md.parse(md, LEADS)
    blank = next(c for c in cues if c["id"] == "d02")
    assert blank["text"] == ""
    assert blank["text_source"] == "placeholder"
    # and the edit that WAS made survives
    assert next(c for c in cues if c["id"] == "d01")["text"] == \
        "Aren't you tired of this?"

def test_clearing_a_line_keeps_what_was_recovered():
    """Handing a slot back is not the same as rewording it to nothing."""
    md = dialogue_md.export(DATA, LEADS, PRESENTATION).replace(
        "Fatigue is a distraction.", "")
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

    md = dialogue_md.export(DATA, LEADS, PRESENTATION).replace(
        "Fatigue is a distraction.", "")
    cue = next(c for c in dialogue_md.parse(md, LEADS) if c["id"] == "d02")
    plate_spec = fill({"id": cue["id"], "kind": "chat",
                       "speaker": cue["character"],
                       "text_source": cue["text_source"]})
    assert plate_spec["speaker"] == "TBD"
    assert plate_spec["speaker_pending"] == "osiris"
    assert plate_spec["text"]


def test_act_three_fixed_deck_has_gold_bob_and_top_right_email_sign():
    doc = json.loads(Path("stories/yt_curse_of_osiris_opening_cinematic-fixed-plates.json").read_text())
    by_id = {p["id"]: p for p in doc["plates"]}
    bob = by_id["mrbobbytables-gold"]
    assert bob["name"] == "Bob Killen"
    assert bob["variant"] == "leader"
    ghost = by_id["clubanderson-ghost"]
    assert ghost["kind"] == "ghost"
    assert ghost["name"] == "Doc Anderson"
    assert ghost["copy_source"] == "casting"
    sign = by_id["maintainer-emails"]
    assert sign["position"] == "top-right"
    assert sign["title"] == "Maintainers Reading Emails"
    assert sign["subtitle"] == "And Other Preposterous Tales"
    assert sign["body"] == ["Summer 2027"]


def test_a_source_window_edit_is_refused():
    text = dialogue_md.export(DATA, LEADS, PRESENTATION).replace(
        "## d02 | osiris | 0:14.00 -> 0:17.00",
        "## d02 | osiris | 0:09.00 -> 0:17.00")
    with pytest.raises(
        ValueError,
        match=r"d02: source timecodes are evidence; restore them from a git ref",
    ):
        dialogue_md.merge(DATA, dialogue_md.parse(text, LEADS))


def test_section_order_and_pins_update_presentation_not_source():
    text = dialogue_md.export(DATA, LEADS, PRESENTATION).replace(
        "## d01 | sagira | 0:10.00 -> 0:14.00\n\nAren't you tired of this?\n\n"
        "## d02 | osiris | 0:14.00 -> 0:17.00\n\nFatigue is a distraction.\n",
        "## d02 | osiris | 0:14.00 -> 0:17.00 | pin 0:40.00\n\nFatigue is a distraction.\n\n"
        "## d01 | sagira | 0:10.00 -> 0:14.00\n\nAren't you tired of this?\n",
    )
    edited = dialogue_md.parse(text, LEADS)
    updated, changes = dialogue_md.merge(DATA, edited)
    presentation, presentation_changes = dialogue_md.merge_presentation(
        PRESENTATION, edited)
    assert updated["cues"] == DATA["cues"]
    assert changes == []
    assert presentation["sequence"] == ["d02", "d01"]
    assert presentation["pins"] == {"d02": 40.0}
    assert presentation_changes == ["  ~ d02 pin_sec: 40.00", "  ! sequence: d02 d01"]


def test_restore_source_times_copies_only_timecodes():
    current = {
        **DATA,
        "cues": [
            {**DATA["cues"][0], "start_sec": 11.0, "end_sec": 15.0},
            {**DATA["cues"][1], "start_sec": 16.0, "end_sec": 19.0,
             "text": "Changed", "character": "sagira"},
        ],
    }
    source = {
        "video_id": "vid",
        "cues": [
            {**DATA["cues"][0], "text": "Ignored"},
            {**DATA["cues"][1], "character": "ignored"},
        ],
    }
    restored, changes = dialogue_md.restore_source_times(current, source)
    assert restored["cues"][0]["start_sec"] == 10.0
    assert restored["cues"][0]["end_sec"] == 14.0
    assert restored["cues"][1]["start_sec"] == 14.0
    assert restored["cues"][1]["end_sec"] == 17.0
    assert restored["cues"][1]["text"] == "Changed"
    assert restored["cues"][1]["character"] == "sagira"
    assert changes == [
        "  ~ d01 source: 11.00-15.00 -> 10.00-14.00",
        "  ~ d02 source: 16.00-19.00 -> 14.00-17.00",
    ]


def test_restore_source_times_rejects_missing_or_duplicate_ids():
    with pytest.raises(ValueError, match=r"duplicate cue id 'd01' in current record"):
        dialogue_md.restore_source_times(
            {"video_id": "vid", "cues": [DATA["cues"][0], DATA["cues"][0]]},
            {"video_id": "vid", "cues": DATA["cues"]},
        )

    with pytest.raises(ValueError, match=r"duplicate cue id 'd01' in restore source"):
        dialogue_md.restore_source_times(
            DATA,
            {"video_id": "vid", "cues": [DATA["cues"][0], DATA["cues"][0]]},
        )

    with pytest.raises(ValueError, match=r"d02: missing from restore source"):
        dialogue_md.restore_source_times(
            DATA,
            {"video_id": "vid", "cues": [DATA["cues"][0]]},
        )
