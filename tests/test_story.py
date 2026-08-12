"""Tests for the story assembler: outline in, ordered clean cut list out."""

import json
from pathlib import Path

import pytest

from tools.search import load_segments
from tools.story import build_story, main, read_outline, tc, to_csv, to_edl

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = str(REPO_ROOT / "examples")

OUTLINE = [
    "wide establishing shot of the Traveler",
    "a crowd of guardians gathered beneath it",
    "close up on a lone titan helmet",
    "Elsie Bray hero shot",
    "guardians parkouring across a bridge toward the light",
]


def beats(*lines):
    return [{"beat": line, "duration": None} for line in lines]


@pytest.fixture(scope="module")
def segments():
    return load_segments(EXAMPLES)


def test_story_casts_every_beat(segments):
    story = build_story(beats(*OUTLINE), segments)
    assert len(story["shots"]) == len(OUTLINE)
    assert story["misses"] == []


def test_story_only_uses_clean_shots(segments):
    story = build_story(beats("show us Hunters with Arc", *OUTLINE), segments)
    assert all(shot["segment"]["clean"] for shot in story["shots"])


def test_unmatched_beat_is_reported_not_dropped(segments):
    """No clean coverage is a real answer: rewrite the beat, don't cut a HUD in."""
    story = build_story(beats("show us Hunters with Arc"), segments)
    assert story["shots"] == []
    assert story["misses"][0]["beat"] == "show us Hunters with Arc"


def test_gameplay_excluded_unless_opted_in(segments):
    story = build_story(beats("a hunter in the crucible"), segments)
    assert all(shot["footage_tier"] != "gameplay" for shot in story["shots"])


def test_allow_gameplay_widens_the_pool(segments):
    default = build_story(beats("guardians"), segments)
    widened = build_story(beats("guardians"), segments, allow_gameplay=True)
    assert widened["pool_size"] >= default["pool_size"]


def test_no_shot_is_reused(segments):
    """A story that cuts the same shot twice reads as padding."""
    repeated = beats(*(["guardians"] * 4))
    story = build_story(repeated, segments)
    ids = [shot["segment_id"] for shot in story["shots"]]
    assert len(ids) == len(set(ids))


def test_beats_keep_outline_order(segments):
    story = build_story(beats(*OUTLINE), segments)
    assert [shot["index"] for shot in story["shots"]] == list(range(1, len(OUTLINE) + 1))
    assert [shot["beat"] for shot in story["shots"]] == OUTLINE


def test_lead_beat_gets_its_lead(segments):
    story = build_story(beats("Elsie Bray hero shot"), segments)
    assert story["shots"][0]["casting"]["character"] == "elsie_bray"


def test_unnamed_beat_is_not_hijacked_by_a_lead(segments):
    """'a lone titan helmet' must not pull a named lead just for being a lead."""
    story = build_story(beats("close up on a lone titan helmet"), segments)
    assert story["shots"][0]["segment_id"] == "seg_titan_helmet_cu_0112-0118"


def test_crowd_beat_picks_the_biggest_ensemble(segments):
    story = build_story(beats("a crowd of guardians gathered beneath it"), segments)
    assert story["shots"][0]["casting"]["slots"] == 6


# --- one cinematic, skipped forward -----------------------------------------

def test_from_video_cuts_from_one_cinematic_only(segments):
    story = build_story(beats(*OUTLINE), segments,
                        from_video="yt_final_shape_launch_trailer")
    assert story["shots"], "no shot matched inside the chosen cinematic"
    assert {s["video_id"] for s in story["shots"]} == {"yt_final_shape_launch_trailer"}


def test_from_video_reports_beats_the_cinematic_cannot_cover(segments):
    """Narrowing to one cinematic does not license reaching into another."""
    story = build_story(beats(*OUTLINE), segments,
                        from_video="yt_final_shape_launch_trailer")
    assert story["misses"], "a 6-beat outline cannot come out of two shots"


def test_forward_only_never_runs_the_cinematic_backwards(segments):
    story = build_story(beats(*(["guardians"] * 4)), segments,
                        from_video="yt_final_shape_launch_trailer",
                        forward_only=True)
    starts = [s["start_sec"] for s in story["shots"]]
    ends = [s["end_sec"] for s in story["shots"]]
    assert all(start >= prev_end for start, prev_end in zip(starts[1:], ends[:-1]))


def test_forward_only_stays_inside_one_cinematic(segments):
    """The playhead is seconds on ONE timeline: a forward-only cut can never
    mix sources, or one cinematic's out-point would silently exclude another
    cinematic's shots."""
    story = build_story(beats(*(["guardians"] * 4)), segments,
                        from_video="yt_final_shape_launch_trailer",
                        forward_only=True)
    assert {s["video_id"] for s in story["shots"]} == {"yt_final_shape_launch_trailer"}


def test_forward_only_without_from_video_is_refused(segments):
    """A playhead with no single timeline would compare seconds across
    unrelated cinematics — refuse, never produce the misleading cut."""
    with pytest.raises(ValueError, match="from_video"):
        build_story(beats("guardians"), segments, forward_only=True)


def test_forward_only_flag_alone_is_a_cli_error(tmp_path, capsys):
    outline = tmp_path / "o.txt"
    outline.write_text("guardians\n")
    with pytest.raises(SystemExit) as exc:
        main([str(outline), "--forward-only"])
    assert exc.value.code == 2
    assert "--from-video" in capsys.readouterr().err


def test_forward_only_records_how_far_the_cut_skipped(segments):
    story = build_story(beats(*(["guardians"] * 2)), segments,
                        from_video="yt_final_shape_launch_trailer",
                        forward_only=True)
    assert all(shot["skip_sec"] >= 0 for shot in story["shots"])


def test_skip_is_absent_unless_the_cut_is_forward_only(segments):
    story = build_story(beats("guardians"), segments)
    assert "skip_sec" not in story["shots"][0]


# --- the shipped cuts -------------------------------------------------------

DANCE_CINEMATIC = "yt_destiny_2_the_final_shape_launch_trailer"


@pytest.fixture(scope="module")
def indexed():
    return load_segments(str(REPO_ROOT / "segments"))


def test_dance_cut_assembles_from_one_cinematic_skipped_forward(indexed):
    """The shipped Dance cut (docs/cuts/01-dance.md) must stay reproducible.

    Every beat lands, all of it comes out of one cinematic, and the cut only
    ever moves forward along that cinematic's timeline.
    """
    _, _, outline = read_outline(str(REPO_ROOT / "stories" / "01-dance.txt"))
    story = build_story(outline, indexed, from_video=DANCE_CINEMATIC, forward_only=True)
    assert story["misses"] == []
    assert len(story["shots"]) == len(outline)
    assert {s["video_id"] for s in story["shots"]} == {DANCE_CINEMATIC}
    assert all(shot["segment"]["clean"] for shot in story["shots"])
    playhead = 0.0
    for shot in story["shots"]:
        assert shot["start_sec"] >= playhead
        playhead = shot["end_sec"]


def test_dance_cut_is_a_hero_cut(indexed):
    """Heroes carry it; the antagonist is coverage, held wide and brief."""
    _, _, outline = read_outline(str(REPO_ROOT / "stories" / "01-dance.txt"))
    story = build_story(outline, indexed, from_video=DANCE_CINEMATIC, forward_only=True)
    salience = [shot["segment"]["subject_salience"] for shot in story["shots"]]
    assert salience.count("enemy_threat") <= 1
    for shot in story["shots"]:
        if shot["segment"]["subject_salience"] == "enemy_threat":
            assert shot["segment"]["shot_scale"] in {"ELS", "LS", "MLS"}


# --- outline parsing --------------------------------------------------------

def test_read_text_outline(tmp_path):
    path = tmp_path / "o.txt"
    path.write_text("# a comment\n\nfirst beat\nsecond beat\n")
    title, fps, parsed = read_outline(str(path))
    assert [b["beat"] for b in parsed] == ["first beat", "second beat"]
    assert fps == 30


def test_read_json_outline(tmp_path):
    path = tmp_path / "o.json"
    path.write_text(json.dumps({"title": "My Cut", "fps": 24,
                                "beats": [{"beat": "one", "duration": 2.5}]}))
    title, fps, parsed = read_outline(str(path))
    assert title == "My Cut" and fps == 24
    assert parsed[0]["duration"] == 2.5


def test_read_json_list_outline(tmp_path):
    path = tmp_path / "o.json"
    path.write_text(json.dumps(["one", "two"]))
    _, _, parsed = read_outline(str(path))
    assert [b["beat"] for b in parsed] == ["one", "two"]


def test_outline_duration_overrides_source_length(segments):
    story = build_story([{"beat": "Elsie Bray hero shot", "duration": 2.0}], segments)
    assert story["shots"][0]["duration"] == 2.0


# --- output formats ---------------------------------------------------------

@pytest.mark.parametrize("seconds,fps,expected", [
    (0, 30, "00:00:00:00"),
    (47, 30, "00:00:47:00"),
    (3661, 30, "01:01:01:00"),
    (1.5, 30, "00:00:01:15"),
    (1.5, 24, "00:00:01:12"),
])
def test_timecode(seconds, fps, expected):
    assert tc(seconds, fps) == expected


def test_edl_record_timeline_is_contiguous(segments):
    story = build_story(beats(*OUTLINE), segments)
    edl = to_edl(story, "Test", 30)
    events = [line for line in edl.splitlines() if line.startswith("0")]
    assert len(events) == len(OUTLINE)
    # each event's record-in equals the previous event's record-out
    rec_out = None
    for line in events:
        fields = line.split()
        if rec_out is not None:
            assert fields[-2] == rec_out
        rec_out = fields[-1]


def test_csv_has_a_row_per_shot(segments):
    story = build_story(beats(*OUTLINE), segments)
    rows = to_csv(story).strip().splitlines()
    assert len(rows) == len(OUTLINE) + 1  # + header


# --- holds are clamped to the vetted material -------------------------------
#
# An outline-supplied duration is a legitimate authoring control, but an
# unclamped one cuts straight through the `clean` gate: render.py cuts
# `-ss start_sec -t duration`, so a hold longer than the segment keeps decoding
# into the NEXT shot -- footage no beat selected and no tagger vetted.

def _shot(**over):
    seg = {"segment_id": "s1", "video_id": "v", "start_sec": 10.0, "end_sec": 14.0,
           "start_tc": "00:00:10:00", "end_tc": "00:00:14:00", "clean": True,
           "footage_tier": "cinematic", "caption": "a lone figure on a bridge"}
    seg.update(over)
    return seg


def test_hold_is_clamped_to_the_shot_it_was_vetted_on():
    seg = _shot()
    story = build_story([{"beat": seg["caption"], "duration": 900.0}], [seg])
    assert story["shots"][0]["duration"] == 4.0


def test_clamped_hold_is_reported_not_swallowed():
    seg = _shot()
    story = build_story([{"beat": seg["caption"], "duration": 900.0}], [seg])
    assert len(story["overruns"]) == 1
    over = story["overruns"][0]
    assert over["requested"] == 900.0
    assert over["clamped_to"] == 4.0
    assert over["segment_id"] == "s1"


def test_a_hold_inside_the_shot_is_left_alone():
    seg = _shot()
    story = build_story([{"beat": seg["caption"], "duration": 2.0}], [seg])
    assert story["shots"][0]["duration"] == 2.0
    assert story["overruns"] == []


def test_no_hold_falls_back_to_the_full_shot():
    seg = _shot()
    story = build_story([{"beat": seg["caption"], "duration": None}], [seg])
    assert story["shots"][0]["duration"] == 4.0
    assert story["overruns"] == []


def test_a_clamped_hold_never_runs_past_the_out_point(segments):
    """The property that matters: no shot may be cut beyond its own end_sec."""
    outline = [{"beat": line, "duration": 600.0} for line in OUTLINE]
    story = build_story(outline, segments)
    for shot in story["shots"]:
        source = shot["end_sec"] - shot["start_sec"]
        assert shot["duration"] <= source + 1e-9, shot["segment_id"]
        assert shot["start_sec"] + shot["duration"] <= shot["end_sec"] + 1e-9
