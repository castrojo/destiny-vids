"""Tests for the shared delivered-peak machinery (tools/peaks.py).

The suite is offline: every measurement and encode here is faked. What is
under test is the gain math and the loop's decisions -- when it re-runs, in
which direction, and when it stops.
"""
import math
import sys

import pytest

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
    # A CONSTANT peak is the case where the gain is not the lever: the bed is
    # being attenuated but the mix's peak comes from source audio. Correcting
    # again only loses level -- act III lost 2.2 LU that way -- so the loop
    # reverts to the derived gain instead of grinding the budget down. Still
    # no exception: degrade, never block.
    monkeypatch.setattr(peaks, "measure_true_peak", lambda *a, **k: 0.3)
    reruns = []
    gain = peaks.correct_delivered_peak("out.mp4", 1.0, -1.1,
                                        lambda g: reruns.append(g),
                                        ffmpeg=["ffmpeg"], attempts=3)
    assert gain == 1.0               # the derived gain, not an attenuated one
    assert reruns[-1] == 1.0         # and the file on disk carries it
    assert "did not move" in capsys.readouterr().out


def test_an_in_band_result_is_kept_even_when_it_barely_moved(monkeypatch):
    """The ceiling is tested BEFORE no-progress: a correction that straddles
    the target by less than NO_PROGRESS_DB (-0.75 -> -0.85 against a -0.8
    ceiling) is a pass, not a reason to re-encode back to the hot gain."""
    peaks_seen = iter([0.5, -0.85])   # hot, then in band but barely moved
    monkeypatch.setattr(peaks, "measure_true_peak",
                        lambda *a, **k: next(peaks_seen))
    reruns = []
    gain = peaks.correct_delivered_peak("out.mp4", 1.0, -0.8,
                                        lambda g: reruns.append(g),
                                        ffmpeg=["ffmpeg"], margin_db=0.0)
    assert len(reruns) == 1          # one correction, kept -- never reverted
    assert gain == reruns[0] != 1.0


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

# ---------------------------------------------------------------------------
# trim_master_peak: the lossless master gets the same delivered-peak loop as
# the deliverable (issue #82 -- Europa's FLAC shipped at +0.3 dBTP while its
# AAC copy was gated to -1.0). ffmpeg is faked throughout: the suite is
# offline, and what is under test is the file choreography and the gain math.
# ---------------------------------------------------------------------------

def _fake_measure(monkeypatch, seq):
    """Successive true-peak readings; the last one repeats once exhausted."""
    seq = list(seq)

    def fake(*a, **k):
        return seq.pop(0) if len(seq) > 1 else seq[0]

    monkeypatch.setattr(peaks, "measure_true_peak", fake)

def _fake_ffmpeg(monkeypatch, calls):
    """Pretend to encode: record the argv and 'write' the output file."""
    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if "-i" in cmd:
            peaks.Path(cmd[-1]).write_bytes(b"re-encoded")
        class Proc:
            returncode = 0
        return Proc()

    monkeypatch.setattr(peaks.subprocess, "run", fake_run)

def test_a_master_already_in_band_is_left_byte_identical(tmp_path, monkeypatch):
    """No correction, no re-encode -- and the inode survives, so a Prod/
    hardlink to the master is not silently detached."""
    master = tmp_path / "master-hq.mp4"
    master.write_bytes(b"original")
    ino = master.stat().st_ino
    _fake_measure(monkeypatch, [-1.0])
    _fake_ffmpeg(monkeypatch, calls := [])
    gain = peaks.trim_master_peak(master, ffmpeg=["ffmpeg"])
    assert gain == 1.0
    assert calls == []
    assert master.read_bytes() == b"original"
    assert master.stat().st_ino == ino
    assert not (tmp_path / "master-hq.mp4.pretrim").exists()

def test_a_hot_master_is_trimmed_by_one_derived_static_gain(tmp_path, monkeypatch):
    """+0.3 dBTP down to the -1.1 target is -1.4 dB, applied ONCE: a lossless
    codec adds no overshoot of its own."""
    master = tmp_path / "master-hq.mp4"
    master.write_bytes(b"original")
    _fake_measure(monkeypatch, [0.3, -1.1])
    _fake_ffmpeg(monkeypatch, calls := [])
    gain = peaks.trim_master_peak(master, ffmpeg=["ffmpeg"])
    assert gain == pytest.approx(10 ** (-1.4 / 20), rel=1e-6)
    assert len(calls) == 1
    assert master.read_bytes() == b"re-encoded"
    assert not (tmp_path / "master-hq.mp4.pretrim").exists()

def test_the_correction_copies_the_picture_and_scales_only_audio(tmp_path, monkeypatch):
    master = tmp_path / "master-hq.mp4"
    master.write_bytes(b"original")
    _fake_measure(monkeypatch, [0.3, -1.1])
    _fake_ffmpeg(monkeypatch, calls := [])
    peaks.trim_master_peak(master, ffmpeg=["ffmpeg"])
    (cmd,) = calls
    assert cmd[cmd.index("-c:v") + 1] == "copy"          # never re-encode video
    assert "libx264" not in cmd
    assert cmd[cmd.index("-af") + 1].startswith("volume=")
    assert cmd[cmd.index("-c:a") + 1] == "flac"
    # ... and it reads the preserved original, not the half-corrected output.
    assert cmd[cmd.index("-i") + 1].endswith(".pretrim")

def test_corrections_are_cumulative_from_the_original(tmp_path, monkeypatch):
    """rerun()'s gain is cumulative from unity, so every attempt must decode
    the ORIGINAL -- re-reading the previous attempt would apply the gain twice."""
    master = tmp_path / "master-hq.mp4"
    master.write_bytes(b"original")
    _fake_measure(monkeypatch, [0.3, 0.1, -1.0])
    _fake_ffmpeg(monkeypatch, calls := [])
    gain = peaks.trim_master_peak(master, ffmpeg=["ffmpeg"])
    first, second = calls
    g1 = 10 ** (-1.4 / 20)
    assert gain == pytest.approx(g1 * 10 ** (-1.2 / 20), rel=1e-6)
    for cmd in (first, second):
        assert cmd[cmd.index("-i") + 1].endswith(".pretrim")

def test_a_master_that_stays_hot_keeps_its_original(tmp_path, monkeypatch, capsys):
    """Degrade, never block: the corrected-best file ships with a WARNING, and
    the pristine master is not destroyed to keep the queue moving."""
    master = tmp_path / "master-hq.mp4"
    master.write_bytes(b"original")
    _fake_measure(monkeypatch, [0.3])
    _fake_ffmpeg(monkeypatch, calls := [])
    peaks.trim_master_peak(master, ffmpeg=["ffmpeg"], attempts=3)
    out = capsys.readouterr().out
    assert "WARNING" in out
    assert (tmp_path / "master-hq.mp4.pretrim").read_bytes() == b"original"

def test_trim_cli_plumbs_target_and_ffmpeg(tmp_path, monkeypatch, capsys):
    master = tmp_path / "master-hq.mp4"
    master.write_bytes(b"original")
    _fake_measure(monkeypatch, [-1.0])
    _fake_ffmpeg(monkeypatch, calls := [])
    peaks.main(["trim", str(master), "--target-dbtp", "-1.1",
                "--ffmpeg", "podman exec bluefin-thumbnailer ffmpeg"])
    assert "delivered true peak -1.0 dBTP" in capsys.readouterr().out

def test_measure_cli_prints_the_peak(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(peaks, "measure_true_peak", lambda *a, **k: 0.3)
    peaks.main(["measure", "x.mp4", "--ffmpeg", "ffmpeg"])
    assert capsys.readouterr().out.strip() == "+0.30"
