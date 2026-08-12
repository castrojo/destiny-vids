"""The timing pass: marker cards, two clocks, and the rules the builder asserts.

These are the guarantees that stop the second cut regressing into the first:
nothing repeated, no Osiris, no anchor drifting off the music, and a marker card
that stays a slate rather than growing into a nameplate.
"""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.audiomix import build_filter, plan_regions, total_bed  # noqa: E402

SHOTLIST = REPO / "stories/seven-days-timing-pass.json"


@pytest.fixture(scope="module")
def cut():
    return json.loads(SHOTLIST.read_text())


def test_bed_is_consumed_exactly(cut):
    """The song must be used end to end: a short act slides every later anchor."""
    regions = plan_regions(cut["shots"], cut["bed_offset_sec"])
    bed = json.loads((REPO / "music/bed_seven_days_to_the_wolves.json").read_text())
    assert total_bed(regions) == pytest.approx(bed["duration_sec"], abs=0.02)


def test_film_is_longer_than_its_song(cut):
    """A musical with a pre-roll and a pause is longer than the record it uses.

    This is the whole point of the two clocks; if these are ever equal, someone
    has quietly gone back to asserting against wall time.
    """
    regions = plan_regions(cut["shots"], cut["bed_offset_sec"])
    wall = sum(s["duration"] for s in cut["shots"])
    assert wall > total_bed(regions) + 20


def test_anchors_land_on_bed_time(cut):
    """The gallop and the flute entry are the cut's only hard obligations."""
    anchors = cut["anchors"]
    bed = 0.0
    hits = set()
    for shot in cut["shots"]:
        if shot["audio"] != "source":
            bed += shot["duration"]
        for name in ("act2_gallop_in", "act3_flute_change"):
            if abs(bed - anchors[name]) < 0.02:
                hits.add(name)
    assert hits == {"act2_gallop_in", "act3_flute_change"}


def test_artwork_returns_on_the_downbeat_after_the_silence(cut):
    """The one interior silence in the bed is where the artwork holds.

    Measured: the band stops at 278.64 and returns on the downbeat at 279.661.
    The artwork must be up across that gap and end ON the slam, or the picture
    comes back over silence and the beat is lost.
    """
    gap_in, slam = cut["anchors"]["howl_silence"]
    bed = 0.0
    covering = None
    for shot in cut["shots"]:
        if shot["audio"] == "source":
            continue
        start, bed = bed, bed + shot["duration"]
        if start <= gap_in and bed >= slam - 0.01:
            covering = shot
    assert covering is not None, "nothing covers the song's only silence"
    assert covering.get("still"), "the silence must be covered by the artwork"
    assert "ARTWORK" in covering["beat"]


def test_no_shot_is_used_twice(cut):
    """The first cut replayed 25 shots to fill a span. Never again."""
    seen = set()
    for shot in cut["shots"]:
        if "video_id" not in shot:
            continue
        key = (shot["video_id"], shot["start_sec"])
        assert key not in seen, f"shot reused: {key}"
        seen.add(key)


def test_osiris_is_not_in_the_feature(cut):
    sources = {s.get("video_id") for s in cut["shots"]}
    assert "yt_curse_of_osiris_opening_cinematic" not in sources


def test_every_run_is_a_forward_run(cut):
    """A run's out-point must follow its in-point, and match its duration."""
    for shot in cut["shots"]:
        if "video_id" not in shot:
            continue
        assert shot["end_sec"] > shot["start_sec"]
        assert shot["end_sec"] - shot["start_sec"] == pytest.approx(
            shot["duration"], abs=0.002)


def test_act_one_stops_at_the_end_of_the_cinematic(cut):
    """The capture ends at source 3:23; past it lie the fade and another trailer."""
    act1 = [s for s in cut["shots"] if s.get("video_id") == "wolves_act1"]
    assert act1, "Act I lost its source"
    assert max(s["end_sec"] for s in act1) == pytest.approx(203.0, abs=0.01)


def test_the_pause_consumes_no_bed_time(cut):
    """`audio: source` is the whole mechanic: it advances wall and not bed."""
    paused = [s for s in cut["shots"] if s["audio"] == "source"]
    assert paused, "the cut has no source-audio moment"
    regions = plan_regions(cut["shots"], cut["bed_offset_sec"])
    src = [r for r in regions if r["kind"] == "source"]
    assert len(src) == 2, "expected a pre-roll and one pause"
    assert "bed_start" not in src[0] and "bed_start" not in src[1]


def test_bed_resumes_where_it_stopped(cut):
    """The bed pieces must be contiguous in bed time across the pause."""
    regions = [r for r in plan_regions(cut["shots"], cut["bed_offset_sec"])
               if r["kind"] == "bed"]
    for before, after in zip(regions, regions[1:]):
        assert after["bed_start"] == pytest.approx(before["bed_end"], abs=0.001)


def test_plan_rejects_a_disagreeing_offset(cut):
    with pytest.raises(ValueError):
        plan_regions(cut["shots"], bed_offset=0.0)


def test_filter_delays_each_bed_piece_to_its_wall_position(cut):
    regions = plan_regions(cut["shots"], cut["bed_offset_sec"])
    graph = build_filter(regions, bed_gain_db=-3.5)
    assert "adelay=20166|20166" in graph
    assert "volume=-3.5dB" in graph
    # The source is muted under the bed, never mixed with it.
    assert "volume=0:enable=" in graph
    assert "normalize=0" in graph


def test_marker_cards_carry_no_nameplate_vocabulary(cut):
    """A marker is a slate. It must never grow a name, a role, or a class.

    Nameplate copy is a closed set naming real people (docs/skills/plates.md);
    a production marker is not a credit and may not borrow that vocabulary.
    """
    from tools.marker import render_marker

    img = render_marker("COMIC PLACEHOLDER", "4:33-4:37  enemy CU")
    assert img.size == (1920, 1080)
    assert img.getpixel((10, 10))[:3] == (0, 0, 0), "a marker is full-frame black"

    for shot in cut["shots"]:
        beat = shot["beat"].upper()
        for banned in ("GUARDIAN //", "TRUSTEE //", "VOIDWALKER", "SUBCLASS"):
            assert banned not in beat


def test_the_uncast_shot_is_unplated_and_says_so(cut):
    """A name nobody authored is omitted and recorded -- never invented."""
    named = [s for s in cut["shots"] if "Cortney Nickerson" in s["beat"]]
    assert len(named) == 1, "the casting request should be recorded on one shot"
    assert "UNPLATED" in named[0]["beat"]
    assert not named[0].get("plate")


def test_plate_slots_are_flagged_for_the_nameplate_pass(cut):
    slots = [s for s in cut["shots"] if s.get("plate_slot")]
    assert len(slots) >= 3, "Guardians-together runs should be flagged"
    for shot in slots:
        assert shot["duration"] >= 5.0, "a plate needs time to be read"
