"""Tests for scripts/efmb_beats.py -- act II's beat map.

Offline first: the mapping, the ranking, the phase check and the detector all
run against synthetic plans, grids and envelopes. The real-file tests are
guarded the way test_bed.py guards theirs -- ``media/`` is gitignored, so CI
has no WAV, and a missing file must skip, never fail.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import efmb_beats  # noqa: E402

WAV = efmb_beats.WAV_PATH
GRID_JSON = efmb_beats.BED_PATH
HOP = 0.02  # matches efmb_beats.HOP_SEC


# --- synthetic fixtures ------------------------------------------------------

def synth_plan(run_secs=(10.03, 20.5, 5.0), lead=0.0, anchor=40.0):
    runs = []
    t = 0.0
    for i, sec in enumerate(run_secs):
        runs.append({"in": t, "out": t + sec, "sec": sec, "why": f"run {i}"})
        t += sec + 1.0  # a removed second between runs; film time ignores it
    return {"act": "II", "title": "test", "bed_lead_sec": lead,
            "picture_sec": sum(run_secs), "sync_anchor_src": 99.0,
            "sync_anchor_film": anchor, "runs": runs}


def synth_grid(beat=0.5, n=400, phase=0, strength=None):
    beats = [round(i * beat, 6) for i in range(n)]
    return {"beats": beats, "beats_per_bar": 4, "bar_sec": beat * 4,
            "tempo_bpm": 60.0 / beat, "downbeat_phase": phase,
            "downbeat_strength": strength or [1.0, 1.0, 1.0, 1.0]}


def synth_envelope():
    """120 s at 0 dB with a 10 s hole at 51-61 that ramps back up into a hit.

    The ramp matters: the sustain gate is measured on the smoothed level, and
    an instant step recovers through the smoother too slowly to pass at the
    true downbeat. The real song behaves the same way -- the riser lifts the
    level into the slam.
    """
    db = []
    for k in range(int(120.0 / HOP)):
        t = k * HOP
        if t < 51.0:
            db.append(0.0)
        elif t < 59.9:
            db.append(-8.0)
        elif t < 60.9:
            db.append(-8.0 + 8.0 * (t - 59.9))  # the ramp back
        else:
            db.append(0.0)
    # the confirming hit: a 2-window transient just before the 60.9 downbeat
    for k in range(int(60.86 / HOP), int(60.90 / HOP)):
        db[k] = 3.0
    return db


# --- the mapping -------------------------------------------------------------

def test_boundaries_are_lead_plus_cumulative_picture():
    plan = synth_plan(run_secs=(4.0, 30.0, 10.0), lead=10.0)
    rows = efmb_beats.film_boundaries(plan)
    assert [r["film_sec"] for r in rows] == [14.0, 44.0]
    assert len(rows) == len(plan["runs"]) - 1


def test_nearest_error_is_signed():
    # + means the cut lands after the grid point: the picture is late.
    near, err = efmb_beats.nearest([10.0], 10.3)
    assert near == 10.0 and err == pytest.approx(0.3)
    near, err = efmb_beats.nearest([10.0], 9.7)
    assert err == pytest.approx(-0.3)


def test_opportunities_rank_by_downbeat_error_anchor_first():
    plan = synth_plan(anchor=40.0)          # 40.0 is beats[80], a phase-0 downbeat
    grid = synth_grid(phase=0)
    rep = efmb_beats.analyze(plan=plan, grid=grid, envelope=None)
    errs = [abs(r["downbeat_err_sec"]) for r in rep["opportunities"]]
    assert errs == sorted(errs)
    assert rep["opportunities"][0]["label"].startswith("SYNC ANCHOR")
    assert rep["opportunities"][0]["downbeat_err_sec"] == pytest.approx(0.0)


def test_without_the_wav_the_grid_analysis_still_ships():
    """Degrade, never block: no WAV means no events, not no report."""
    rep = efmb_beats.analyze(plan=synth_plan(), grid=synth_grid(), envelope=None)
    assert rep["events"]["note"]
    assert rep["opportunities"]


# --- the phase check -----------------------------------------------------------

def test_phase_is_the_stored_phase_when_anchor_and_grid_agree():
    # Since #89 the stored phase is itself evidence-backed; the check is a
    # guard, and agreement is the quiet case.
    grid = synth_grid(phase=3, strength=[1.0, 2.0, 1.0, 2.2])
    phase, note = efmb_beats.verify_downbeat_phase(grid, anchor_film=41.5)
    assert phase == 3 and "agree" in note


def test_anchor_off_the_stored_phase_warns_and_still_reports_stored():
    # The guard's job is to say so, loudly -- never to re-phase behind the
    # record's back. The stored phase is reported either way.
    grid = synth_grid(phase=3, strength=[1.0, 2.0, 1.0, 2.2])
    phase, note = efmb_beats.verify_downbeat_phase(grid, anchor_film=40.0)
    assert phase == 3
    assert "WARNING" in note and "residue 0" in note


def test_anchor_off_every_beat_is_grid_drift_not_a_phase_question():
    grid = synth_grid(phase=3, strength=[1.0, 2.0, 1.0, 2.2])
    phase, note = efmb_beats.verify_downbeat_phase(grid, anchor_film=40.25)
    assert phase == 3
    assert "WARNING" in note and "drifted" in note


# --- the detector, synthetic ---------------------------------------------------

def test_detector_finds_the_drop_and_the_slam():
    db = synth_envelope()
    level = efmb_beats.smooth(db, efmb_beats.SMOOTH_SEC, HOP)
    baseline = efmb_beats.baseline_of(level)
    drops = efmb_beats.find_drops(level, HOP, baseline)
    assert len(drops) == 1
    drop = drops[0]
    assert drop["drop_sec"] == pytest.approx(51.0, abs=0.6)
    downbeats = [0.1 + 1.6 * k for k in range(75)]  # bar lines; 60.9 is one
    re = efmb_beats.find_reentry(level, HOP, db, downbeats, drop, baseline)
    assert re["downbeat_sec"] == pytest.approx(60.9)
    # the measured hit sits on the transient, a hair before the bar line
    assert abs(re["onset_offset_sec"]) < 0.1


def test_an_intro_and_an_outro_are_not_drops():
    db = [-8.0] * int(10.0 / HOP) + [0.0] * int(100.0 / HOP) \
         + [-30.0] * int(10.0 / HOP)
    level = efmb_beats.smooth(db, efmb_beats.SMOOTH_SEC, HOP)
    baseline = efmb_beats.baseline_of(level)
    drops = efmb_beats.find_drops(level, HOP, baseline)
    kinds = {d["kind"] for d in drops}
    assert kinds == {"intro", "outro"}
    outro = next(d for d in drops if d["kind"] == "outro")
    assert efmb_beats.find_reentry(level, HOP, db, [0.1 + 1.6 * k for k in range(75)],
                                   outro, baseline) is None


# --- the real song ---------------------------------------------------------------

needs_files = pytest.mark.skipif(
    not (WAV.exists() and GRID_JSON.exists()),
    reason="bed WAV/grid not present (media/ is gitignored)")


@pytest.fixture(scope="module")
def report():
    if not (WAV.exists() and GRID_JSON.exists()):
        pytest.skip("bed WAV/grid not present")
    return efmb_beats.analyze(envelope=efmb_beats.load_envelope_db(WAV))


@needs_files
def test_the_real_boundaries_tile_the_plan(report):
    import build_efmb
    plan = build_efmb.build()
    rows = [r for r in efmb_beats.film_boundaries(plan)]
    elapsed = 0.0
    for r, run in zip(rows, plan["runs"]):
        elapsed += run["sec"]
        assert r["film_sec"] == pytest.approx(plan["bed_lead_sec"] + elapsed)
    # and the last boundary plus the last run lands exactly on the picture end
    assert rows[-1]["film_sec"] + plan["runs"][-1]["sec"] == \
        pytest.approx(plan["bed_lead_sec"] + plan["picture_sec"])


@needs_files
def test_the_shipped_anchor_shows_near_zero_error(report):
    anchor = next(r for r in report["opportunities"]
                  if r["label"].startswith("SYNC ANCHOR"))
    assert abs(anchor["beat_err_sec"]) < 0.01
    assert abs(anchor["downbeat_err_sec"]) < 0.01


@needs_files
def test_the_detector_finds_the_breakdown_the_act_is_built_on(report):
    """Breaks down at 258.0, stays down to 268.0, band back at 269.700 --
    an exact downbeat. The detector that misses this one is wrong."""
    drop = next(d for d in report["events"]["drops"]
                if abs(d["drop_sec"] - 258.0) < 1.0)
    assert drop["down_until_sec"] == pytest.approx(268.0, abs=0.6)
    re = drop["reentry"]
    assert re is not None
    assert re["downbeat_sec"] == pytest.approx(269.700, abs=0.01)
    assert abs(re["onset_offset_sec"]) < 0.25
