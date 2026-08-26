"""`tools/readtime.py`: which plates go by faster than anybody can read them.

The tool reports; it never re-times anything. That is pinned here as firmly
as the arithmetic -- moving an authored beat is the owner's call (`AGENTS.md`,
on copy the owner already placed), so the default exit is 0 and only
`--check`, for somebody gating a final cut, is allowed to fail.
"""
import json
from collections import Counter

import pytest

from tools import readtime
from tools.plate import MIN_HOLD


def plate(**kw):
    base = {"id": "p1", "kind": "chat", "at": 10.0, "dur": 5.0,
            "text": "hello", "speaker": "someone"}
    base.update(kw)
    return base


def write(tmp_path, *plates, name="act.json"):
    path = tmp_path / name
    path.write_text(json.dumps({"plates": list(plates)}), encoding="utf-8")
    return path


def short_rows(tmp_path, *plates, **kw):
    rows, _, _ = readtime.audit_manifest(write(tmp_path, *plates), **kw)
    return rows


# -- the reading model ------------------------------------------------------

def test_a_long_line_needs_longer_than_a_short_one():
    assert readtime.required_hold("A" * 170) == pytest.approx(10.0)
    assert readtime.required_hold("A" * 170) > readtime.required_hold("Fine")


def test_no_line_is_ever_allowed_less_than_the_floor():
    """`MIN_HOLD` is a floor for ANY plate, however few words it carries.

    A four-character pill is readable in a quarter-second and still needs
    long enough to be noticed at all, which is what `tools/plate.py`'s
    MIN_HOLD already encodes. The rate model must not undercut it.
    """
    assert readtime.required_hold("Hi") == MIN_HOLD
    assert readtime.required_hold("") == MIN_HOLD


def test_the_rate_is_adjustable():
    assert readtime.required_hold("A" * 100, cps=10.0) == pytest.approx(10.0)
    assert readtime.required_hold("A" * 100, cps=50.0) == MIN_HOLD


def test_the_floor_binds_below_about_thirty_seven_characters():
    """Which is why the report separates 'short of the floor' from 'short of
    its own copy' -- only the second is this tool's own finding."""
    assert readtime.required_hold("A" * 37) == MIN_HOLD
    assert readtime.required_hold("A" * 38) > MIN_HOLD


# -- the two windows --------------------------------------------------------

def test_a_plate_with_no_fades_is_up_for_its_whole_duration():
    assert readtime.windows(plate(at=2.0, dur=3.0)) == (3.0, 3.0, None)


def test_a_fade_in_eats_the_opaque_window_but_not_the_on_screen_one():
    """Act V's `p6-nick-docs1`, exactly as committed: 1.2s of `dur` with a
    0.6s fade-in and a `fade_out_at` 0.25s before the end, so the words are
    at full strength for 0.35s of their own 1.2s life."""
    on_screen, opaque, quirk = readtime.windows(
        plate(at=16.4, dur=1.2, fade_in=0.6, fade_out_at=17.35, fade_out=0.25))
    assert on_screen == pytest.approx(1.2)
    assert opaque == pytest.approx(0.35)
    assert quirk is None


def test_at_plus_dur_is_a_hard_end_even_when_a_fade_runs_past_it():
    """Both renderers gate the overlay on `at + dur` -- actbuild.py with
    `enable=between(t,at,at+dur)`, build_europa.py with
    `gte(t,at)*lt(t,at+dur)`. A fade tail scheduled past it is CLIPPED, so
    crediting it would invent legibility that never reaches the screen.
    """
    on_screen, _, _ = readtime.windows(
        plate(at=0.0, dur=2.0, fade_out_at=2.0, fade_out=0.5))
    assert on_screen == pytest.approx(2.0)


def test_a_fade_out_before_the_plate_starts_is_reported_as_a_quirk():
    """Such a plate renders invisible while reading as comfortably long."""
    _, _, quirk = readtime.windows(plate(at=10.0, dur=2.0, fade_out_at=3.0))
    assert quirk and "outside its own window" in quirk


def test_a_fade_in_longer_than_the_hold_is_reported_as_a_quirk():
    on_screen, opaque, quirk = readtime.windows(
        plate(at=0.0, dur=1.0, fade_in=3.0))
    assert opaque == 0.0
    assert on_screen == pytest.approx(1.0)
    assert quirk and "longer than" in quirk


def test_a_plate_with_no_timing_cannot_be_timed():
    assert readtime.windows({"text": "x"}) is None


def test_a_non_numeric_timing_field_is_unmeasurable_not_a_crash(tmp_path):
    """Degrade, never block: one bad field costs its own plate a measurement,
    never the audit of every other plate."""
    assert readtime.windows(plate(at="1.0")) is None
    rows, _, problems = readtime.audit_manifest(
        write(tmp_path, plate(id="bad", at="1.0"), plate(id="ok", dur=0.5)))
    assert [row["id"] for row in rows] == ["ok"]
    assert any("bad" in p and "cannot be timed" in p for p in problems)


# -- the verdict is taken on the GENEROUS window ----------------------------

def test_a_plate_readable_only_thanks_to_its_fades_is_not_reported(tmp_path):
    """Judging on the strict window would overstate the problem.

    A viewer finishes a line that is on its way out, so the verdict uses
    `on_screen`. This calls the auditor, not just `windows`, because that
    choice is the single most consequential thing in the tool.
    """
    p = plate(at=0.0, dur=3.0, fade_in=1.5, text="Fine")
    _, opaque, _ = readtime.windows(p)
    assert opaque < MIN_HOLD             # the strict window would flag it...
    assert short_rows(tmp_path, p) == []  # ...and the tool does not.


def test_a_short_plate_is_reported_with_both_numbers(tmp_path):
    rows = short_rows(tmp_path, plate(id="tight", at=0.0, dur=1.0,
                                      text="Fine"))
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == "tight"
    assert row["on_screen"] == pytest.approx(1.0)
    assert row["need"] == MIN_HOLD
    assert row["deficit"] == pytest.approx(MIN_HOLD - 1.0)
    assert row["rate_driven"] is False


def test_a_plate_short_of_its_own_copy_is_marked_rate_driven(tmp_path):
    rows = short_rows(tmp_path, plate(at=0.0, dur=3.0, text="A" * 90))
    assert rows[0]["rate_driven"] is True


def test_a_generous_plate_is_not_reported(tmp_path):
    assert short_rows(tmp_path, plate(at=0.0, dur=30.0, text="Fine")) == []


def test_a_plate_with_no_words_is_not_reported(tmp_path):
    """A card with no prose has nothing to read; not a timing defect."""
    assert short_rows(tmp_path, plate(text="", at=0.0, dur=0.2)) == []


def test_a_non_prose_kind_carrying_prose_is_counted_not_judged(tmp_path):
    """A title card is read differently -- usually it is the only thing up --
    but the reader is told it was declined rather than left to assume it
    passed."""
    rows, skipped, _ = readtime.audit_manifest(
        write(tmp_path, plate(kind="maintitle", at=0.0, dur=0.5,
                              text="SEVEN DAYS")))
    assert rows == []
    assert skipped["maintitle"] == 1


def test_ending_cards_are_prose_and_are_judged(tmp_path):
    rows = short_rows(tmp_path,
                      plate(kind="ending", at=0.0, dur=0.5, text="Fine"))
    assert len(rows) == 1


def test_a_kindless_plate_carrying_prose_is_judged(tmp_path):
    rows = short_rows(tmp_path, plate(kind=None, at=0.0, dur=0.5))
    assert len(rows) == 1


def test_plate_text_falls_back_through_message_and_body():
    assert readtime.plate_text({"body": "words"}) == "words"
    assert readtime.plate_text({"message": "words"}) == "words"
    assert readtime.plate_text({"text": "a", "body": "b"}) == "a"
    assert readtime.plate_text({"text": "   "}) == ""


# -- an unreadable manifest must never look like a clean one ----------------

def test_a_missing_manifest_is_a_problem_not_an_all_clear(tmp_path, capsys):
    """The one direction this tool must never be quietly wrong in.

    A typo'd path returning "0 plates" green-lights the exact thing `--check`
    exists to gate.
    """
    missing = tmp_path / "nope.json"
    rows, _, problems = readtime.audit_manifest(missing)
    assert rows == []
    assert any("cannot be read" in p for p in problems)

    assert readtime.main([str(missing), "--check"]) == 1
    out = capsys.readouterr().out
    assert "read 0 of 1 manifest(s)" in out
    assert "NOT the same as nothing being wrong" in out


def test_invalid_json_is_a_problem_not_an_all_clear(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    _, _, problems = readtime.audit_manifest(broken)
    assert any("not valid JSON" in p for p in problems)


def test_a_record_that_is_not_a_plate_list_is_simply_not_a_plate_file(tmp_path):
    """`stories/` holds records of several shapes; that is not a fault."""
    other = tmp_path / "other.json"
    other.write_text("[1, 2, 3]", encoding="utf-8")
    assert readtime.audit_manifest(other) == ([], Counter(), [])


# -- it reports; it does not gate -------------------------------------------

def test_the_default_run_exits_zero_even_with_short_plates(tmp_path, capsys):
    """Re-timing an authored beat is the owner's call, never a tool's."""
    path = write(tmp_path, plate(at=0.0, dur=0.5, text="Fine"))
    assert readtime.main([str(path)]) == 0
    out = capsys.readouterr().out
    assert "1 plate(s)" in out
    assert "the owner's, not a tool's" in out


def test_check_mode_exits_one_for_whoever_is_gating_a_final_cut(tmp_path):
    path = write(tmp_path, plate(at=0.0, dur=0.5, text="Fine"))
    assert readtime.main([str(path), "--check"]) == 1


def test_check_mode_still_exits_zero_when_nothing_is_short(tmp_path, capsys):
    path = write(tmp_path, plate(at=0.0, dur=30.0, text="Fine"))
    assert readtime.main([str(path), "--check"]) == 0
    assert "0 plate(s)" in capsys.readouterr().out


def test_the_cps_flag_reaches_the_model(tmp_path, capsys):
    """A 30-character line clears the floor at 17 cps and not at 5 cps."""
    path = write(tmp_path, plate(at=0.0, dur=2.5, text="A" * 30))
    assert readtime.main([str(path)]) == 0
    assert "0 plate(s)" in capsys.readouterr().out

    assert readtime.main([str(path), "--cps", "5", "--check"]) == 1


def test_a_manifest_outside_the_repo_is_named_not_crashed_on(tmp_path):
    """`_display` must degrade: naming a file is never what fails."""
    rows = short_rows(tmp_path, plate(at=0.0, dur=0.5, text="Fine"))
    assert rows[0]["manifest"] == str(tmp_path / "act.json")


def test_the_committed_manifests_never_gate():
    """The repo's own plates are reported, never asserted.

    Every one is an authored beat whose neighbours move if it widens, so
    discovering them is free and fixing them is a decision. If this ever
    returns non-zero, the tool has become the thing `AGENTS.md` forbids.
    """
    assert readtime.main([]) == 0


# -- acts whose pills come from a dialogue record ---------------------------

def cue(**kw):
    base = {"id": "d01", "start_sec": 10.0, "end_sec": 12.0,
            "character": "osiris", "text": "hello"}
    base.update(kw)
    return base


def write_record(tmp_path, *cues):
    path = tmp_path / "dialogue.json"
    path.write_text(json.dumps({"video_id": "vid", "cues": list(cues)}),
                    encoding="utf-8")
    return path


def test_a_dialogue_record_is_audited_by_the_hold_plan_script_will_give_it(tmp_path):
    """Read time is a question about the hold, not the seat.

    `plan_script` holds a cue for `max(MIN_HOLD, min(spoken, MAX_CHAT_HOLD))`,
    so the same arithmetic answers "can this be read" without a cut list,
    footage or a plan -- and therefore works offline, before anything is
    built. All three regimes are pinned here so the two cannot drift.
    """
    from tools.dialogue import MAX_CHAT_HOLD
    long_line = "A" * 400
    for start, end, expected in (
            (0.0, 0.5, MIN_HOLD),                 # under the floor
            (0.0, 4.0, 4.0),                      # its own spoken window
            (0.0, 40.0, MAX_CHAT_HOLD),           # over the cap
    ):
        path = write_record(tmp_path, cue(start_sec=start, end_sec=end,
                                          text=long_line))
        rows, _, _ = readtime.audit_dialogue(path)
        assert rows[0]["on_screen"] == expected


def test_a_short_cue_is_reported_against_the_markdown_the_owner_edits(tmp_path):
    """Naming dialogue.json would point the owner at an output."""
    path = write_record(tmp_path, cue(text="A" * 80))
    rows, _, problems = readtime.audit_dialogue(path)
    assert problems == []
    assert len(rows) == 1
    assert rows[0]["id"] == "d01"
    assert rows[0]["manifest"].endswith("DIALOGUE.md")
    assert rows[0]["grep"] == "## d01 |"
    assert rows[0]["on_screen"] == MIN_HOLD


def test_a_cue_with_room_to_be_read_is_not_reported(tmp_path):
    path = write_record(tmp_path, cue(start_sec=0.0, end_sec=6.0, text="Hi"))
    rows, _, _ = readtime.audit_dialogue(path)
    assert rows == []


def test_the_spoken_window_is_capped_the_way_plan_script_caps_it(tmp_path):
    """A 40s window does not buy 40s of reading: the plan caps the hold."""
    from tools.dialogue import MAX_CHAT_HOLD
    path = write_record(tmp_path, cue(start_sec=0.0, end_sec=40.0,
                                      text="A" * 200))
    rows, _, _ = readtime.audit_dialogue(path)
    assert rows[0]["on_screen"] == MAX_CHAT_HOLD


def test_a_cue_with_no_words_yet_is_placeholder_business_not_this_tools(tmp_path):
    path = write_record(tmp_path, cue(text=""))
    rows, skipped, problems = readtime.audit_dialogue(path)
    assert rows == [] and problems == []
    assert skipped["placeholder"] == 1


def test_an_untimeable_cue_is_a_problem_not_an_all_clear(tmp_path):
    """The one direction this tool must never be quietly wrong in."""
    path = write_record(tmp_path, cue(start_sec=5.0, end_sec=5.0,
                                      text="A" * 80))
    rows, _, problems = readtime.audit_dialogue(path)
    assert rows == []
    assert any("cannot be timed" in p for p in problems)


def test_the_default_run_reaches_the_dialogue_records():
    """The acts built through `build_uncut_credited.sh` keep their words in
    `dialogue/`, not in `stories/`, so auditing only `stories/` reported them
    as having nothing wrong in them."""
    found = readtime.dialogue_records(readtime.REPO_ROOT)
    assert found, "the repo has at least one dialogue record"
    assert all(p.name == "dialogue.json" for p in found)
    assert readtime.REPO_ROOT / "dialogue" in {p.parent.parent for p in found}


def test_act3_priority_now_dialogue_holds_clear_the_audit():
    """The owner approved these five re-seats; none may regress unreadable."""
    path = (readtime.REPO_ROOT / "dialogue"
            / "yt_curse_of_osiris_opening_cinematic" / "dialogue.json")
    rows, _, problems = readtime.audit_dialogue(path)
    assert problems == []
    assert not ({row["id"] for row in rows} &
                {"d02", "d03", "d06", "d22", "d28"})
