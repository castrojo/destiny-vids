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
