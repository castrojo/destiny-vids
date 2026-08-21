"""Chapter-file conversation authoring (tools/chapter_md.py).

The format is the contract the owner writes against: one `## <programme
time>` heading per conversation, `Speaker: line` rows under it, readability
timing derived, pins honoured exactly with the shift recorded.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from tools import chapter_md  # noqa: E402

OFFSET = chapter_md.ACT_PROGRAMME_START["II"]


def schedule(md, seats=None):
    blocks = chapter_md.parse(md)
    assert len(blocks) == 1
    return chapter_md.schedule_block(blocks[0], OFFSET, seats=seats)


SPOKEN = {"film": 200.0, "src": 358.24,
          "matched": "I'm so proud of you kids!"}


def test_a_line_matching_the_video_is_seated_where_it_is_spoken():
    at, _, notes = schedule(
        "## 6:45\nKarena: I'm so proud of you kids!\n",
        seats=[SPOKEN])
    assert at[0] == pytest.approx(200.0, abs=1e-3)
    assert any("seated on" in n and "5:58.24" in n for n in notes)


def test_a_pin_overrides_the_speech_seat_and_says_so():
    at, _, notes = schedule(
        "## 6:45\nKarena @ 6:50: I'm so proud of you kids!\n",
        seats=[SPOKEN])
    assert at[0] == pytest.approx(410.0 - OFFSET, abs=1e-3)
    assert any("pinned away from" in n and "the pin stands" in n
               for n in notes)


def test_a_speech_seat_earlier_than_the_cascade_is_recorded():
    at, _, notes = schedule(
        "## 6:45\n"
        "Karena: A first line with some length to it\n"
        "jrsapi: I'm so proud of you kids!\n",
        seats=[None, {**SPOKEN, "film": 405.5 - OFFSET}])
    assert at[1] == pytest.approx(405.5 - OFFSET, abs=1e-3)
    assert any("overlap" in n for n in notes)


def test_seat_lines_matches_paraphrase_and_skips_cut_frames(monkeypatch):
    monkeypatch.setattr(chapter_md, "sync_seats",
                        lambda act: [(358.24, "I'm so proud of you kids!")])
    monkeypatch.setattr(chapter_md, "film_for_source",
                        lambda act, src: 200.0 if src < 359 else None)
    lines = [{"speaker": "K", "kind": "chat", "pin": None,
              "text": "I am so proud of you kids"},
             {"speaker": "K", "kind": "chat", "pin": None,
              "text": "unrelated words entirely"},
             {"speaker": "K", "kind": "chat", "pin": 400.0,
              "text": "I'm so proud of you kids!"}]
    seats = chapter_md.seat_lines("II", lines)
    assert seats[0]["film"] == 200.0
    assert seats[1] is None
    # A pinned line still gets its seat computed -- the operator is told
    # what the evidence preferred even though the pin wins.
    assert seats[2]["film"] == 200.0


def test_seat_lines_without_a_dialogue_record_is_quiet(monkeypatch):
    monkeypatch.setattr(chapter_md, "ACT_SOURCES", {})
    lines = [{"speaker": "K", "kind": "chat", "pin": None, "text": "anything"}]
    assert chapter_md.seat_lines("II", lines) == [None]


def test_one_heading_drops_a_whole_conversation():
    at, holds, notes = schedule(
        "## 6:45\n"
        "Karena: Hit 'em with your lessons learned\n"
        "Rochaporto: One reference architecture coming up!\n"
        "jrsapi: Shit are you taking notes?\n")
    # The block lands on the PROGRAMME clock: 6:45 minus act II's start.
    assert at[0] == pytest.approx(405.0 - OFFSET, abs=1e-3)
    # Every line is its own pill, chained by read time plus the beat.
    assert at[1] == pytest.approx(at[0] + holds[0] + chapter_md.GAP)
    assert at[2] == pytest.approx(at[1] + holds[1] + chapter_md.GAP)
    assert notes == []


def test_read_time_is_the_clock_and_it_is_clamped():
    assert chapter_md.hold_for("Hi") == chapter_md.MIN_HOLD
    assert chapter_md.hold_for("x" * 400) == chapter_md.MAX_HOLD
    mid = "One reference architecture coming up!"  # 37 chars
    assert chapter_md.hold_for(mid) == pytest.approx(len(mid) / 15.0,
                                                     abs=1e-3)


def test_a_pin_reseats_one_line_and_the_rest_adjust():
    at, holds, notes = schedule(
        "## 6:45\n"
        "Karena: Hit 'em with your lessons learned\n"
        "jrsapi @ 6:52: Shit are you taking notes?\n"
        "Karena: Like cardio!\n")
    # The pin is exact, on the programme clock.
    assert at[1] == pytest.approx(412.0 - OFFSET, abs=1e-3)
    # The heading still seats the first line; the slack before the pin is
    # silence, and the line after the pin cascades off it.
    assert at[0] == pytest.approx(405.0 - OFFSET, abs=1e-3)
    assert at[2] == pytest.approx(at[1] + holds[1] + chapter_md.GAP)
    assert notes == []


def test_a_pin_that_overruns_its_neighbour_is_recorded_not_raised():
    at, holds, notes = schedule(
        "## 6:45\n"
        "Karena @ 6:45: Hit 'em with your lessons learned\n"
        "jrsapi @ 6:46: Shit are you taking notes?\n")
    assert at[1] == pytest.approx(406.0 - OFFSET, abs=1e-3)
    assert any("overlap" in n for n in notes)


def test_a_pinned_first_line_disagrees_with_its_heading_and_says_so():
    at, _, notes = schedule(
        "## 6:45\n"
        "Karena @ 6:50: Hit 'em with your lessons learned\n")
    assert at[0] == pytest.approx(410.0 - OFFSET, abs=1e-3)
    assert any("the pin wins" in n for n in notes)


def test_consecutive_lines_by_one_speaker_are_separate_pills():
    blocks = chapter_md.parse(
        "## 6:45\nKarena: first\nKarena: second\nKarena: third\n")
    assert [l["speaker"] for l in blocks[0]["lines"]] == ["Karena"] * 3


def test_entries_shape_matches_the_act_build():
    md = ("## 6:45\n"
          "rochaporto: One reference architecture coming up!\n"
          "Karena: Like cardio!\n")
    blocks = chapter_md.parse(md)
    at, holds, _ = chapter_md.schedule_block(blocks[0], OFFSET)
    assert chapter_md.LOGIN_SHAPE.match("rochaporto")
    assert not chapter_md.LOGIN_SHAPE.match("Karena")


def test_entries_from_the_committed_file_are_manifest_shaped(tmp_path):
    entries, unresolved = chapter_md.entries("II")
    for e in entries:
        assert e["copy_source"] == "owner_supplied"
        assert e["dur"] >= chapter_md.MIN_HOLD
        assert e["at"] >= 0
        if e["kind"] == "chat":
            assert e["speaker"] and "text" in e
        else:
            assert e["kind"] == "miniboss" and e["name"]


def test_an_unknown_act_is_not_an_error():
    assert chapter_md.entries("IX") == ([], [])


def test_timecode_forms():
    assert chapter_md.parse_tc("6:45") == 405.0
    assert chapter_md.parse_tc("6:45.50") == 405.5
    assert chapter_md.parse_tc("1:02:03.5") == 3723.5
    assert chapter_md.parse_tc("90") == 90.0


def test_a_heading_without_a_time_is_rejected():
    with pytest.raises(ValueError):
        chapter_md.parse("## not-a-time\nKarena: hi\n")


def test_a_boss_line_authors_a_red_splash():
    blocks = chapter_md.parse("## 6:45\n! POOR TECHNICAL DECISIONS\n")
    line = blocks[0]["lines"][0]
    assert line["kind"] == "boss"
    assert line["name"] == "POOR TECHNICAL DECISIONS"
    assert line["title"] is None          # no pipe: no second row


def test_a_boss_line_pipe_keeps_the_title_slot_as_placeholder():
    blocks = chapter_md.parse("## 6:45\n! [the_id] POOR TECHNICAL DECISIONS |\n")
    line = blocks[0]["lines"][0]
    assert line["id"] == "the_id"
    assert line["title"] == ""            # the slot, not the words


def test_a_boss_line_with_title_authors_the_second_row():
    blocks = chapter_md.parse("## 6:45\n! HATERS @ 10:00 | They Hate Us\n")
    line = blocks[0]["lines"][0]
    assert line["title"] == "They Hate Us"
    assert line["pin"] == 600.0


def test_boss_entries_carry_the_miniboss_shape_and_placeholder_seed():
    # The two committed red splashes are authored in the chapter file: their
    # manifest entries must keep their ids, seats and placeholder titles, so
    # the Markdown takeover changes no pixel.
    entries, _ = chapter_md.entries("II")
    by_id = {e["id"]: e for e in entries}
    flash = by_id["late_poor_technical_decisions"]
    assert flash["kind"] == "miniboss" and flash["position"] == "boss"
    assert flash["at"] == pytest.approx(405.0 - OFFSET, abs=1e-3)
    assert flash["dur"] == chapter_md.MIN_HOLD
    assert flash["title_source"] == "placeholder"
    haters = by_id["mapped_haters"]
    assert haters["at"] == pytest.approx(600.0 - OFFSET, abs=1e-3)


def test_instructions_prose_and_indented_examples_parse_as_nothing():
    md = chapter_md.chapter_path("II").read_text()
    blocks = chapter_md.parse(md)
    # The committed file carries the two red splashes and nothing else: the
    # instructions, the indented example and the evidence notes must not
    # leak in as scheduleable lines.
    assert len(blocks) == 2
    for block in blocks:
        assert len(block["lines"]) == 1
        assert block["lines"][0]["kind"] == "boss"
