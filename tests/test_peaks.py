"""Tests for the shared delivered-peak machinery (tools/peaks.py).

The suite is offline: every measurement and encode here is faked. What is
under test is the gain math and the loop's decisions -- when it re-runs, in
which direction, and when it stops.
"""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools import peaks  # noqa: E402


def test_gain_is_derived_from_the_measured_true_peak(monkeypatch):
    """A hot source is scaled to leave headroom, by a STATIC gain."""
    monkeypatch.setattr(peaks, "measure_true_peak", lambda *a, **k: 1.5)
    gain, peak = peaks.gain_for_headroom("src.mp3", target_dbtp=-1.1)
    assert peak == 1.5
    # 1.5 dBTP down to -1.1 dBTP is -2.6 dB.
    assert gain == pytest.approx(10 ** (-2.6 / 20), rel=1e-6)
    assert 1.5 + 20 * math.log10(gain) == pytest.approx(-1.1)


def test_a_quiet_source_is_never_pushed_up_to_the_target(monkeypatch):
    """The target is a ceiling, not a loudness mandate."""
    monkeypatch.setattr(peaks, "measure_true_peak", lambda *a, **k: -8.0)
    gain, peak = peaks.gain_for_headroom("src.mp3", target_dbtp=-1.1)
    assert gain == 1.0 and peak == -8.0


def test_true_peak_is_read_from_the_last_ebur128_summary(monkeypatch):
    """ebur128 prints running peaks; only the final summary is the answer."""
    class Proc:
        stderr = ("Peak: -6.0 dBFS\n"
                  "  True peak:\n    Peak:        0.5 dBFS\n")
    monkeypatch.setattr(peaks.subprocess, "run", lambda *a, **k: Proc())
    assert peaks.measure_true_peak("x.mp3", ffmpeg=["ffmpeg"]) == 0.5


def test_an_unmeasurable_file_is_an_error_not_a_silent_pass(monkeypatch):
    class Proc:
        stderr = "not a measurement at all"
    monkeypatch.setattr(peaks.subprocess, "run", lambda *a, **k: Proc())
    with pytest.raises(RuntimeError, match="could not measure"):
        peaks.measure_true_peak("x.mp4", ffmpeg=["ffmpeg"])


def test_a_delivered_peak_inside_the_band_needs_no_correction(monkeypatch):
    monkeypatch.setattr(peaks, "measure_true_peak", lambda *a, **k: -1.0)
    reruns = []
    gain = peaks.correct_delivered_peak("out.mp4", 1.0, -1.1,
                                        lambda g: reruns.append(g),
                                        ffmpeg=["ffmpeg"])
    assert gain == 1.0
    assert reruns == []


def test_an_overshooting_file_is_re_run_at_a_lower_static_gain(monkeypatch):
    """The encoder added headroom-eating overshoot; the correction is another
    STATIC gain on top of the first, and it only ever goes down."""
    delivered = iter([0.3, -1.4])
    monkeypatch.setattr(peaks, "measure_true_peak", lambda *a, **k: next(delivered))
    reruns = []
    gain = peaks.correct_delivered_peak("out.mp4", 0.8, -1.1,
                                        lambda g: reruns.append(g),
                                        ffmpeg=["ffmpeg"])
    assert reruns == [gain]
    assert gain < 0.8
    # 0.3 dBTP is 1.4 dB over the -1.1 target: scale by exactly that.
    assert gain == pytest.approx(0.8 * 10 ** (-1.4 / 20), rel=1e-6)


def test_corrections_stop_at_the_first_safe_result(monkeypatch):
    """The overshoot is not monotonic in the gain, so the loop does not chase
    a narrow window: the first in-band result is kept, even an odd one."""
    delivered = iter([0.3, -2.5])
    monkeypatch.setattr(peaks, "measure_true_peak", lambda *a, **k: next(delivered))
    reruns = []
    peaks.correct_delivered_peak("out.mp4", 1.0, -1.1, lambda g: reruns.append(g),
                                 ffmpeg=["ffmpeg"])
    assert len(reruns) == 1


def test_a_file_that_stays_hot_is_warned_about_not_blocked(monkeypatch, capsys):
    """Degrade, never block: after the attempt budget the file ships with a
    WARNING, not an exception."""
    monkeypatch.setattr(peaks, "measure_true_peak", lambda *a, **k: 0.3)
    reruns = []
    gain = peaks.correct_delivered_peak("out.mp4", 1.0, -1.1,
                                        lambda g: reruns.append(g),
                                        ffmpeg=["ffmpeg"], attempts=3)
    assert len(reruns) == 2          # measured 3 times, corrected twice
    assert "WARNING" in capsys.readouterr().out


def test_a_very_quiet_result_is_noted_but_accepted(monkeypatch, capsys):
    monkeypatch.setattr(peaks, "measure_true_peak", lambda *a, **k: -5.0)
    reruns = []
    peaks.correct_delivered_peak("out.mp4", 1.0, -1.1, lambda g: reruns.append(g),
                                 ffmpeg=["ffmpeg"])
    assert reruns == []
    assert "quieter than the other cuts" in capsys.readouterr().out


def test_the_render_ceiling_is_the_top_of_the_delivered_band():
    """-0.9 dBTP (in band) passes and -0.7 dBTP (issue #44) is corrected.

    redact.py's wider margin accepts what already shipped; a fresh cut is held
    to the band ~/Videos/audio-check.sh enforces."""
    ceiling = peaks.DEFAULT_TARGET_DBTP + peaks.DELIVERED_BAND_MARGIN_DB
    assert ceiling == pytest.approx(-0.9)
    assert ceiling - -0.9 < 1e-9       # -0.9 dBTP (in band) passes
    assert -0.7 > ceiling              # -0.7 dBTP (issue #44) is corrected
