"""Tests for the story assembler: outline in, ordered clean cut list out."""

import json
from pathlib import Path

import pytest

from tools.search import load_segments
from tools.story import build_story, read_outline, tc, to_csv, to_edl

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


# --- one cinematic, played forward ------------------------------------------

def test_video_pins_the_cut_to_one_source(segments):
    story = build_story(beats(*OUTLINE), segments,
                        video_id="yt_final_shape_launch_trailer")
    assert story["shots"], "expected the pinned video to cover some beats"
    assert {shot["video_id"] for shot in story["shots"]} == {"yt_final_shape_launch_trailer"}


def test_forward_only_locks_the_cut_to_one_cinematic(segments):
    """The first matched beat chooses the cinematic; the rest follow it."""
    story = build_story(beats("close up on a lone titan helmet",
                              "wide establishing shot of the Traveler"), segments,
                        forward_only=True)
    assert story["video_id"] == "yt_beyond_light_story_trailer"
    assert {shot["video_id"] for shot in story["shots"]} == {"yt_beyond_light_story_trailer"}


def test_forward_only_never_doubles_back(segments):
    story = build_story(beats(*OUTLINE), segments, forward_only=True)
    starts = [shot["start_sec"] for shot in story["shots"]]
    assert starts == sorted(starts)
    for previous, following in zip(story["shots"], story["shots"][1:]):
        assert following["start_sec"] >= previous["start_sec"] + previous["duration"]


def test_forward_only_reports_a_beat_it_cannot_reach(segments):
    """A beat whose only shot is behind the playhead is a miss, not a rewind."""
    forward = build_story(beats("close up on a lone titan helmet",
                                "Elsie Bray hero shot"), segments, forward_only=True)
    assert [m["beat"] for m in forward["misses"]] == ["Elsie Bray hero shot"]
    free = build_story(beats("close up on a lone titan helmet",
                             "Elsie Bray hero shot"), segments)
    assert free["misses"] == []


def test_skips_cover_the_stretches_the_cut_passes_over(segments):
    story = build_story(beats("close up on a lone titan helmet"), segments,
                        forward_only=True)
    assert len(story["skips"]) == 1             # head only: the cut ends on the
    head = story["skips"][0]                    # last indexed shot of that video
    assert head["after_shot"] == 0
    assert head["from_sec"] == 0.0 and head["to_sec"] == 72
    assert head["seconds"] == 72
    assert head["segments_skipped"] == 1        # the Elsie hero shot at 62-68s


def test_tail_skip_is_reported_when_the_cut_stops_early(segments):
    story = build_story(beats("Elsie Bray hero shot"), segments, forward_only=True)
    tail = story["skips"][-1]
    assert tail["after_shot"] == 1              # named by the shot it follows
    assert tail["from_sec"] == 68 and tail["to_sec"] == 78
    assert tail["segments_skipped"] == 1        # the titan helmet close-up


def test_no_skips_reported_without_forward_only(segments):
    story = build_story(beats(*OUTLINE), segments)
    assert "skips" not in story and "video_id" not in story


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
