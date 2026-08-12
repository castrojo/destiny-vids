"""Tests for bed measurement, excision and timeline mapping.

These are offline: they build grids by hand rather than calling ``librosa``,
which is an optional dependency needed only to *create* a record. That is the
whole reason the grid is cached in the first place.
"""

import json

import pytest

from tools.bed import (
    build_filter, downbeats, edited_downbeats, edited_duration, fmt_tc,
    guard_no_overlap, load_record, nearest_edited_downbeat, parse_tc,
    plan_excision, snap_to_downbeat, to_edited, to_source,
)

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
BED = REPO_ROOT / "music" / "bed_wish_i_had_an_angel.json"


def grid(bar=2.0, beats_per_bar=4, n_bars=40, start=0.0):
    """A perfectly regular grid: easy to reason about, exact to assert on."""
    beat = bar / beats_per_bar
    beats = [round(start + i * beat, 6) for i in range(n_bars * beats_per_bar)]
    return {"beats": beats, "beats_per_bar": beats_per_bar, "downbeat_phase": 0,
            "bar_sec": bar, "beat_interval_sec": beat, "tempo_bpm": 60.0 / beat}


def record(excisions=(), duration=80.0, **kw):
    rec = {"bed_id": "test", "media_filename": "test.wav", "duration_sec": duration,
           "grid": grid(), "excisions": list(excisions)}
    rec.update(kw)
    return rec


# --- timecodes --------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("3:48", 228.0), ("2:59", 179.0), ("0:07.5", 7.5),
    ("1:02:03", 3723.0), ("42", 42.0), (12.5, 12.5),
])
def test_parse_tc(text, expected):
    assert parse_tc(text) == pytest.approx(expected)


def test_tc_round_trips():
    assert parse_tc(fmt_tc(228.0)) == pytest.approx(228.0)


# --- snapping ---------------------------------------------------------------

def test_downbeats_are_every_fourth_beat():
    g = grid(bar=2.0, n_bars=5)
    assert downbeats(g) == [0.0, 2.0, 4.0, 6.0, 8.0]


def test_snap_picks_the_nearest_bar_line():
    g = grid(bar=2.0, n_bars=5)
    assert snap_to_downbeat(g, 3.9) == 4.0
    assert snap_to_downbeat(g, 4.1) == 4.0
    assert snap_to_downbeat(g, 5.2) == 6.0


def test_an_excision_is_snapped_to_whole_bars():
    """The property the whole design rests on: never a fractional bar."""
    g = grid(bar=2.0, n_bars=20)
    exc = plan_excision(g, 5.3, 12.4)
    assert exc["start_sec"] == 6.0
    assert exc["end_sec"] == 12.0
    assert exc["removed_bars"] == 3
    assert exc["removed_sec"] == pytest.approx(6.0)


def test_bars_are_counted_by_index_not_by_median_length():
    """Tracked bars jitter; four real bars must report as 4, not 4.07."""
    g = grid(bar=2.0, n_bars=20)
    g["beats"][8] += 0.05          # nudge the bar line at 4.0s
    g["beats"][12] -= 0.03         # and the one at 6.0s
    exc = plan_excision(g, 4.0, 12.0)   # bar index 2 -> bar index 6
    assert exc["removed_bars"] == 4
    assert isinstance(exc["removed_bars"], int)
    # the span is NOT an exact multiple of the median bar, which is the point
    assert exc["removed_sec"] != pytest.approx(4 * g["bar_sec"])


def test_a_collapsed_excision_is_refused():
    g = grid(bar=2.0, n_bars=20)
    with pytest.raises(ValueError, match="collapses"):
        plan_excision(g, 4.1, 4.2)


def test_an_overlapping_excision_is_refused():
    """build_filter coalesces the overlap, but removed_sec is summed blindly:
    a double-counted span desyncs every anchor from the audio, silently."""
    rec = record([plan_excision(grid(), 20.0, 30.0)])
    with pytest.raises(ValueError, match="overlaps existing excision 0:20.000"):
        guard_no_overlap(rec, plan_excision(grid(), 25.0, 35.0))


def test_a_duplicate_excision_is_refused():
    """Re-running the same excise must not count the span twice."""
    rec = record([plan_excision(grid(), 20.0, 30.0)])
    with pytest.raises(ValueError, match="overlaps"):
        guard_no_overlap(rec, plan_excision(grid(), 20.0, 30.0))


def test_excisions_touching_at_a_bar_line_do_not_overlap():
    """Adjacent excisions share a boundary bar line but no audio; both count."""
    rec = record([plan_excision(grid(), 20.0, 30.0)])
    guard_no_overlap(rec, plan_excision(grid(), 30.0, 40.0))
    guard_no_overlap(rec, plan_excision(grid(), 10.0, 20.0))


# --- timeline mapping -------------------------------------------------------

def test_mapping_before_an_excision_is_unchanged():
    rec = record([plan_excision(grid(), 20.0, 30.0)])
    assert to_edited(rec, 10.0) == pytest.approx(10.0)


def test_mapping_after_an_excision_shifts_left():
    rec = record([plan_excision(grid(), 20.0, 30.0)])
    assert to_edited(rec, 40.0) == pytest.approx(30.0)


def test_an_excised_moment_has_no_edited_position():
    """Returning a neighbour would be a lie an anchor could be built on."""
    rec = record([plan_excision(grid(), 20.0, 30.0)])
    assert to_edited(rec, 25.0) is None


def test_source_and_edited_round_trip():
    rec = record([plan_excision(grid(), 20.0, 30.0)])
    for edited in (0.0, 5.0, 19.9, 20.0, 45.0):
        assert to_edited(rec, to_source(rec, edited)) == pytest.approx(edited)


def test_edited_duration_subtracts_every_excision():
    rec = record([plan_excision(grid(), 10.0, 14.0),
                  plan_excision(grid(), 20.0, 30.0)])
    assert edited_duration(rec) == pytest.approx(80.0 - 4.0 - 10.0)


# --- the property that makes one grid enough --------------------------------

def test_the_grid_stays_in_phase_across_a_splice():
    """A whole-bar excision leaves the bar lines evenly spaced.

    This is why there is one grid rather than two joined at a discontinuity: cut
    a whole number of bars and the surviving downbeats are still a bar apart.
    """
    rec = record([plan_excision(grid(), 20.0, 30.0)])
    bars = edited_downbeats(rec)
    gaps = [round(b - a, 6) for a, b in zip(bars, bars[1:])]
    assert set(gaps) == {2.0}


def test_nearest_edited_downbeat_is_on_the_edited_timeline():
    rec = record([plan_excision(grid(), 20.0, 30.0)])
    assert nearest_edited_downbeat(rec, 31.2) in edited_downbeats(rec)


# --- rendering --------------------------------------------------------------

def test_the_filter_keeps_only_the_surviving_spans():
    rec = record([plan_excision(grid(), 20.0, 30.0)])
    filt, spans = build_filter(rec)
    assert spans == [(0.0, 20.0), (30.0, 80.0)]
    assert "concat=n=2" in filt
    assert "atrim=start=0.000000:end=20.000000" in filt


def test_an_unexcised_bed_is_a_single_span():
    filt, spans = build_filter(record())
    assert spans == [(0.0, 80.0)]
    assert "concat=n=1" in filt


# --- the real record --------------------------------------------------------

@pytest.mark.skipif(not BED.exists(), reason="bed record not present")
def test_the_checked_in_bed_record_is_coherent():
    rec = load_record(BED)
    assert rec["grid"]["beats_per_bar"] == 4
    assert 70 < rec["grid"]["tempo_bpm"] < 95, "felt tempo, not the double-time lock"
    assert rec["grid"]["beat_multiple"] == 2
    for exc in rec["excisions"]:
        assert isinstance(exc["removed_bars"], int) and exc["removed_bars"] > 0


@pytest.mark.skipif(not BED.exists(), reason="bed record not present")
def test_the_anchor_lands_where_the_cut_was_designed_for():
    """3:48 on the edited timeline must still leave a tail to hold on."""
    rec = load_record(BED)
    tail = edited_duration(rec) - parse_tc("3:48")
    assert 3.0 < tail < 8.0, f"anchor sits {tail:.2f}s from the end"


@pytest.mark.skipif(not BED.exists(), reason="bed record not present")
def test_the_real_grid_stays_in_phase_across_the_real_splice():
    rec = load_record(BED)
    bars = edited_downbeats(rec)
    gaps = [b - a for a, b in zip(bars, bars[1:])]
    median = sorted(gaps)[len(gaps) // 2]
    assert max(abs(g - median) for g in gaps) < 0.12, "a splice re-phased the grid"


# --- a diegetic insert's own peaks -------------------------------------------

def test_source_gain_attenuates_only_the_insert_regions():
    """An insert is somebody else's mix, and it brings its own peaks.

    Measured on this cut: the bed region sat at -3.2 dBTP and the whole file at
    -0.4, over the -1.0 headroom gate -- 8.7 s of insert in 432 s of film. The
    fix is the same static gain the bed already gets, applied to the insert
    only. Pulling the whole film down would also work and is worse: it quietly
    re-levels music whose gain was already decided and documented.
    """
    from tools.audiomix import build_filter

    regions = [
        {"kind": "bed", "wall_start": 0.0, "wall_end": 10.0,
         "bed_start": 0.0, "bed_end": 10.0},
        {"kind": "source", "wall_start": 10.0, "wall_end": 12.0},
        {"kind": "bed", "wall_start": 12.0, "wall_end": 20.0,
         "bed_start": 10.0, "bed_end": 18.0},
    ]
    graph = build_filter(regions, bed_gain_db=-3.5, source_gain_db=-1.5)

    assert "volume=-1.5dB" in graph, "the insert is not attenuated"
    assert graph.count("volume=-1.5dB") == 1, "applied once, not per region"
    # It rides on the source input, never on a bed piece.
    source_chain = next(p for p in graph.split(";") if p.startswith("[0:a]"))
    assert "volume=-1.5dB" in source_chain
    for piece in graph.split(";"):
        if piece.startswith("[1:a]"):
            assert "volume=-3.5dB" in piece and "-1.5dB" not in piece


def test_source_gain_defaults_to_no_change():
    """Silence is not a level decision. A cut that never asked for one gets
    its source audio exactly as rendered."""
    from tools.audiomix import build_filter

    regions = [{"kind": "source", "wall_start": 0.0, "wall_end": 5.0}]
    assert "volume=" not in build_filter(regions).replace("volume=0:", "")
