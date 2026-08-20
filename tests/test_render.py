"""ffmpeg resolution order for tools/render.py.

The order matters more than it looks: on Bluefin the ffmpeg on PATH is
``ffmpeg-free``, which has no H.264 decoder and fails only once decoding
starts. PATH must therefore rank last, and the container must rank first.
See docs/rendering.md.
"""

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
    
from tools import render  # noqa: E402

@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for var in ("DESTINY_FFMPEG", "DESTINY_FFMPEG_CONTAINER", "DESTINY_FFMPEG_IMAGE"):
        monkeypatch.delenv(var, raising=False)

def test_find_ffmpeg_returns_argv_prefix_list(monkeypatch):
    """A list, never a bare string: a container ffmpeg is multiple argv words."""
    monkeypatch.setenv("DESTINY_FFMPEG", "/usr/bin/ffmpeg")
    assert render.find_ffmpeg() == ["/usr/bin/ffmpeg"]

def test_env_override_is_shell_split_and_wins(monkeypatch):
    monkeypatch.setattr(render, "_container_running", lambda name: True)
    monkeypatch.setenv("DESTINY_FFMPEG", "podman exec other ffmpeg")
    assert render.find_ffmpeg() == ["podman", "exec", "other", "ffmpeg"]

def test_running_container_is_preferred_over_path(monkeypatch):
    monkeypatch.setattr(render.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(render, "_container_running", lambda name: True)
    assert render.find_ffmpeg() == ["podman", "exec", render.DEFAULT_CONTAINER, "ffmpeg"]

def test_container_name_is_configurable(monkeypatch):
    monkeypatch.setattr(render.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(render, "_container_running", lambda name: name == "custom-ff")
    monkeypatch.setenv("DESTINY_FFMPEG_CONTAINER", "custom-ff")
    assert render.find_ffmpeg() == ["podman", "exec", "custom-ff", "ffmpeg"]

def test_no_container_flag_skips_podman(monkeypatch):
    monkeypatch.setattr(render.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(render, "_container_running", lambda name: True)
    assert render.find_ffmpeg(prefer_container=False)[0] != "podman"

def test_ephemeral_run_used_when_image_set_and_no_container(monkeypatch):
    monkeypatch.setattr(render.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(render, "_container_running", lambda name: False)
    monkeypatch.setenv("DESTINY_FFMPEG_IMAGE", "example.org/ffmpeg:1")
    cmd = render.find_ffmpeg()
    assert cmd[:3] == ["podman", "run", "--rm"]
    assert "example.org/ffmpeg:1" in cmd
    home = str(Path.home())
    assert f"{home}:{home}" in cmd, "home must be bind-mounted at the same path"

def test_path_ffmpeg_is_last_resort(monkeypatch):
    monkeypatch.setattr(render.shutil, "which",
                        lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None)
    monkeypatch.setitem(sys.modules, "imageio_ffmpeg", None)
    assert render.find_ffmpeg() == ["/usr/bin/ffmpeg"]

def test_raises_when_nothing_available(monkeypatch):
    monkeypatch.setattr(render.shutil, "which", lambda name: None)
    monkeypatch.setitem(sys.modules, "imageio_ffmpeg", None)
    with pytest.raises(RuntimeError, match="no ffmpeg found"):
        render.find_ffmpeg()

def test_resolve_media_returns_absolute_path(tmp_path, monkeypatch):
    """Relative paths break under `podman exec`: it has a different cwd."""
    media = tmp_path / "media"
    media.mkdir()
    (media / "yt_x.mp4").write_bytes(b"")
    monkeypatch.chdir(tmp_path)
    found = render.resolve_media("yt_x", "media")
    assert found.is_absolute()
    assert found == (media / "yt_x.mp4").resolve()

def test_resolve_media_missing_returns_none(tmp_path):
    assert render.resolve_media("nope", tmp_path) is None

def test_concat_list_is_written_beside_output_not_tmp(tmp_path, monkeypatch):
    """A containerized ffmpeg only sees the bind-mounted home, never /tmp."""
    seen = {}

    def fake_run(cmd, check=False):
        idx = cmd.index("-i")
        list_path = Path(cmd[idx + 1])
        seen["dir"] = list_path.parent
        seen["contents"] = list_path.read_text()
        return None

    monkeypatch.setattr(render.subprocess, "run", fake_run)
    workdir = tmp_path / "work"
    workdir.mkdir()
    clips = [tmp_path / "a.mp4", tmp_path / "b.mp4"]
    render.concat(["ffmpeg"], clips, tmp_path / "out.mp4", workdir=workdir)

    assert seen["dir"] == workdir
    assert seen["dir"] != Path(os.environ.get("TMPDIR", "/tmp"))
    assert str(clips[0].resolve()) in seen["contents"]
    assert not list(workdir.glob("concat_list.txt")), "list file must be cleaned up"

def test_cap_holds_trims_from_the_tail_only():
    """The in-point is what the index worked to find; trims come off the end."""
    shots = [
        {"segment_id": "a", "start_sec": 10.0, "end_sec": 35.0, "duration": 25.0},
        {"segment_id": "b", "start_sec": 4.0, "end_sec": 6.0, "duration": 2.0},
    ]
    capped = render.cap_holds(shots, 8.0)
    assert capped[0]["start_sec"] == 10.0
    assert capped[0]["end_sec"] == 18.0
    assert capped[0]["duration"] == 8.0
    assert capped[1] == shots[1]          # under the cap, untouched
    assert shots[0]["duration"] == 25.0   # input list is not mutated

def test_cap_holds_without_a_cap_is_a_passthrough():
    shots = [{"segment_id": "a", "start_sec": 0.0, "end_sec": 30.0, "duration": 30.0}]
    assert render.cap_holds(shots, None) == shots

def test_cap_holds_derives_duration_when_absent():
    shots = [{"segment_id": "a", "start_sec": 2.0, "end_sec": 22.0}]
    assert render.cap_holds(shots, 5.0)[0]["end_sec"] == 7.0

def test_resolve_duration_clamps_a_hold_past_the_out_point(capsys):
    """build_story clamps a hold at the cut, but a shotlist it never produced
    (hand-edited, or from a future producer) can still arrive holding past
    ``end_sec`` — the same clean-gate hole. The render is the last gate."""
    shot = {"segment_id": "seg_a", "start_sec": 10.0, "end_sec": 14.2,
            "duration": 600.0}
    assert render.resolve_duration(shot) == pytest.approx(4.2)
    err = capsys.readouterr().err
    assert "CLAMPED" in err
    assert "seg_a" in err

def test_resolve_duration_within_the_span_is_quiet(capsys):
    shot = {"segment_id": "seg_a", "start_sec": 10.0, "end_sec": 14.2,
            "duration": 3.0}
    assert render.resolve_duration(shot) == 3.0
    assert capsys.readouterr().err == ""

def test_resolve_duration_derives_the_span_when_duration_is_absent(capsys):
    shot = {"segment_id": "seg_a", "start_sec": 10.0, "end_sec": 14.2}
    assert render.resolve_duration(shot) == pytest.approx(4.2)
    assert capsys.readouterr().err == ""

def test_cap_holds_keeps_the_clamp_so_the_render_does_not_warn_twice(capsys):
    """cap_holds and render both resolve the duration; the clamp must be
    written back or the same shot is warned about once per pass."""
    shots = [{"segment_id": "a", "start_sec": 0.0, "end_sec": 4.0, "duration": 30.0}]
    capped = render.cap_holds(shots, 8.0)
    assert capped[0]["duration"] == 4.0
    assert capped[0]["end_sec"] == 4.0        # the clamp is to the vetted span
    assert render.resolve_duration(capped[0]) == 4.0
    assert capsys.readouterr().err.count("CLAMPED") == 1

# --- delivered true-peak trim (issue #44) ------------------------------------

def _one_shot_render(monkeypatch, tmp_path, delivered_peaks, **render_kwargs):
    """Run render() with every encode and every measurement faked.

    Returns the list of ``audio_gain`` values concat() was called with, in
    order -- None for the first (ungained) pass, a float for a correction.
    """
    media = tmp_path / "media"
    media.mkdir()
    (media / "yt_x.mp4").write_bytes(b"")
    shots = [{"segment_id": "a", "video_id": "yt_x", "start_sec": 1.0,
              "end_sec": 3.0, "start_tc": "0:01", "end_tc": "0:03"}]
    monkeypatch.setattr(render, "cut_clip", lambda *a, **k: None)
    readings = iter(delivered_peaks)
    monkeypatch.setattr(render.peaks, "measure_true_peak",
                        lambda *a, **k: next(readings))
    gains = []

    def fake_concat(ffmpeg, clips, out_path, audio_bed=None, workdir=None,
                    audio_gain=None):
        gains.append(audio_gain)

    monkeypatch.setattr(render, "concat", fake_concat)
    render.render(shots, media, tmp_path / "out.mp4",
                  ffmpeg=["ffmpeg-not-invoked"], verbose=False, **render_kwargs)
    return gains

def test_a_cut_above_the_band_is_re_concatenated_at_a_static_gain(monkeypatch, tmp_path):
    """Issue #44: a cut measured -0.7 dBTP is 0.4 dB over the -1.1 target, so
    the concat is re-run with a STATIC volume gain -- never a limiter, never a
    normaliser -- and only the concat, not the clip cuts."""
    gains = _one_shot_render(monkeypatch, tmp_path, [-0.7, -1.0])
    assert gains[0] is None, "the first pass carries no gain filter"
    assert len(gains) == 2, "one corrective concat, then in band"
    assert gains[1] == pytest.approx(10 ** (-0.4 / 20), rel=1e-6)
    assert gains[1] < 1.0, "corrections only ever go down"

def test_a_cut_inside_the_band_is_not_re_concatenated(monkeypatch, tmp_path):
    gains = _one_shot_render(monkeypatch, tmp_path, [-1.0])
    assert gains == [None]

def test_the_peak_check_also_covers_a_music_bed(monkeypatch, tmp_path):
    """--audio replaces the source audio at the concat; the delivered file is
    still measured and corrected there."""
    bed = tmp_path / "bed.wav"
    bed.write_bytes(b"")
    gains = _one_shot_render(monkeypatch, tmp_path, [-0.4, -1.2], audio_bed=bed)
    assert len(gains) == 2 and gains[1] < 1.0

def test_a_muted_render_is_never_measured(monkeypatch, tmp_path):
    """No audio stream means nothing to measure -- the loop must not run."""
    monkeypatch.setattr(render.peaks, "measure_true_peak",
                        lambda *a, **k: pytest.fail("measured a muted file"))
    gains = _one_shot_render(monkeypatch, tmp_path, [], keep_audio=False)
    assert gains == [None]

def test_concat_applies_the_correction_as_a_static_volume_filter(monkeypatch, tmp_path):
    """The corrective pass is a plain volume= scale, not a dynamics filter."""
    seen = []

    def fake_run(cmd, check=False):
        seen.append(cmd)
        return None

    monkeypatch.setattr(render.subprocess, "run", fake_run)
    render.concat(["ffmpeg"], [tmp_path / "a.mp4"], tmp_path / "out.mp4",
                  workdir=tmp_path, audio_gain=0.95)
    cmd = seen[0]
    assert cmd[cmd.index("-af") + 1] == "volume=0.95"
    joined = " ".join(cmd)
    assert "loudnorm" not in joined and "acompressor" not in joined \
        and "alimiter" not in joined

def test_concat_with_a_bed_gains_the_bed(monkeypatch, tmp_path):
    seen = []

    def fake_run(cmd, check=False):
        seen.append(cmd)
        return None

    monkeypatch.setattr(render.subprocess, "run", fake_run)
    render.concat(["ffmpeg"], [tmp_path / "a.mp4"], tmp_path / "out.mp4",
                  audio_bed=tmp_path / "bed.wav", workdir=tmp_path,
                  audio_gain=0.95)
    cmd = seen[0]
    assert "volume=0.95" in cmd[cmd.index("-af") + 1]
    assert cmd[cmd.index("-map") + 1] == "0:v:0"
    assert "1:a:0" in cmd

# --- the chain stays lossless (issue #144) -----------------------------------
#
# render.py encoded AAC 192k at three places INSIDE a chain the audio standard
# requires to be lossless. The loss was invisible where it happened -- the file
# plays fine -- and permanent for everything built from the output.

def test_a_cut_clip_carries_pcm_not_a_lossy_generation(monkeypatch):
    calls = []
    monkeypatch.setattr(render.subprocess, "run",
                        lambda cmd, **kw: calls.append(cmd))
    render.cut_clip(["ffmpeg"], "src.mp4", 1.0, 2.0, "out.mkv", keep_audio=True)
    cmd = calls[0]
    assert cmd[cmd.index("-c:a") + 1] == "pcm_s24le"
    assert "aac" not in cmd and "-b:a" not in cmd

def test_a_still_carries_pcm_too(monkeypatch):
    """A still takes the slot a dropped shot left behind, so its audio has to
    be indistinguishable from a cut clip's to the concat demuxer."""
    calls = []
    monkeypatch.setattr(render.subprocess, "run",
                        lambda cmd, **kw: calls.append(cmd))
    render.still_clip(["ffmpeg"], "a.png", 2.0, "out.mkv", keep_audio=True)
    cmd = calls[0]
    assert cmd[cmd.index("-c:a") + 1] == "pcm_s24le"
    assert "aac" not in cmd

def test_intermediates_are_not_flac(monkeypatch):
    """Measured, not theoretical: FLAC's STREAMINFO lives in extradata and the
    concat demuxer binds the FIRST file's extradata to the whole joined stream,
    so every later segment fails to decode. PCM has none to mismatch."""
    assert render.INTERMEDIATE_AUDIO_ARGS[1] != "flac"
    assert render.INTERMEDIATE_SUFFIX == ".mkv"

def test_the_join_delivers_a_lossless_bed(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(render.subprocess, "run",
                        lambda cmd, **kw: calls.append(cmd))
    render.concat(["ffmpeg"], [tmp_path / "clip_001.mkv"], tmp_path / "out.mp4",
                  audio_bed=tmp_path / "bed.wav", workdir=tmp_path)
    # concat is no longer the only thing that shells out: the bed-length check
    # probes first, and `find_ffprobe` asks podman whether the container is up.
    # That probe degrades to a no-op here (no ffprobe is reachable), but it is
    # still a recorded call, so pick the join rather than assuming it is first.
    cmd = next(c for c in calls if "concat" in c)
    assert cmd[cmd.index("-c:a") + 1] == "flac"
    assert "-b:a" not in cmd, "a lossless codec has no bitrate to state"

def test_the_join_states_the_codec_even_with_no_bed(monkeypatch, tmp_path):
    """The clips now carry PCM, so leaving the codec to the container's default
    would put the lossy generation straight back."""
    calls = []
    monkeypatch.setattr(render.subprocess, "run",
                        lambda cmd, **kw: calls.append(cmd))
    render.concat(["ffmpeg"], [tmp_path / "clip_001.mkv"], tmp_path / "out.mp4",
                  workdir=tmp_path)
    cmd = calls[0]
    assert cmd[cmd.index("-c:a") + 1] == "flac"

# --- the picture probe reads the cut it was given (issue #161) ---------------
#
# The probe seeked to a fixed 40 s. Act IV is 34.0 s long, so it decoded
# nothing, cropdetect reported nothing, and the function returned None -- which
# is ALSO the answer for an un-letterboxed source. The caller could not tell
# them apart and placed plates against the raw frame; measured on that act, the
# pill landed 18 px onto the active picture.

def test_a_short_cut_is_probed_inside_itself():
    """34 s: every window must start before the end and fit inside it."""
    windows = render.probe_windows(34.0)
    assert windows, "a short cut got no window at all -- the #161 bug"
    for start, length in windows:
        assert 0 <= start < 34.0
        assert start + length <= 34.0 + 1e-9

def test_a_very_short_cut_still_gets_one_window():
    windows = render.probe_windows(2.0)
    for start, length in windows:
        assert start + length <= 2.0 + 1e-9

def test_a_long_cut_is_read_at_several_points():
    """One window can land on a fade, a title card, or a shot letterboxed
    differently; three readings across the body outvote one."""
    windows = render.probe_windows(600.0)
    assert len(windows) == 3
    starts = [s for s, _ in windows]
    assert starts == sorted(starts)
    # The head and the tail are avoided deliberately.
    assert starts[0] > 0.0
    assert starts[-1] + windows[-1][1] < 600.0

def test_an_unprobeable_duration_falls_back_to_the_old_offset():
    """No worse than before, and stated rather than crashing."""
    assert render.probe_windows(None) == [(render.PROBE_AT, render.PROBE_LEN)]
    assert render.probe_windows(0) == [(render.PROBE_AT, render.PROBE_LEN)]

def _fake_probe(monkeypatch, stderr_by_call):
    calls = {"n": 0}

    class R:
        def __init__(self, stderr):
            self.stderr = stderr

    def fake_run(cmd, **kw):
        i = calls["n"]
        calls["n"] += 1
        return R(stderr_by_call[min(i, len(stderr_by_call) - 1)])
    monkeypatch.setattr(render.subprocess, "run", fake_run)
    monkeypatch.setattr(render, "find_ffmpeg", lambda *a, **k: ["ffmpeg"])
    monkeypatch.setattr(render, "probe_media_duration", lambda *a, **k: 100.0)

def test_no_matte_and_never_looked_are_different_answers(monkeypatch):
    """This is the whole of #161: one of these is safe to place against and
    the other is not, and they used to be the same None."""
    _fake_probe(monkeypatch, ["Parsed_cropdetect crop=1920:800:0:140\n"])
    assert render.detect_picture_status("x.mp4") == ((0, 140, 1920, 800),
                                                     "letterboxed")

    _fake_probe(monkeypatch, ["frame= 120 fps=0.0 nothing here\n"])
    rect, status = render.detect_picture_status("x.mp4")
    assert rect is None and status == "undecodable"

def test_the_steadiest_reading_wins_across_windows(monkeypatch):
    """A single window landing on a title card must not outvote the body."""
    _fake_probe(monkeypatch, [
        "crop=1920:1080:0:0\n",           # a full-frame title card
        "crop=1920:800:0:140\ncrop=1920:800:0:140\n",
        "crop=1920:800:0:140\n",
    ])
    rect, status = render.detect_picture_status("x.mp4")
    assert rect == (0, 140, 1920, 800)
    assert status == "letterboxed"

# --- `-shortest` cuts the PICTURE too (the bed-length check) -----------------
#
# concat() muxes an --audio bed with `-shortest`, which stops the whole output
# at the shorter of the two mapped streams. A bed longer than the cut is the
# intended use. A bed SHORTER than the cut silently truncated the film: ffmpeg
# exited 0 and nothing said the render had ended early.

def test_a_bed_shorter_than_the_cut_stops_the_render(monkeypatch, tmp_path):
    monkeypatch.setattr(render.subprocess, "run",
                        lambda cmd, **kw: None)
    lengths = {"bed.wav": 3.0, "a.mp4": 6.0, "b.mp4": 4.0}
    monkeypatch.setattr(render, "probe_media_duration",
                        lambda p, ffmpeg=None: lengths[Path(p).name])

    with pytest.raises(RuntimeError, match=r"bed is 3\.000s but the cut is 10\.000s"):
        render.concat(["ffmpeg"], [tmp_path / "a.mp4", tmp_path / "b.mp4"],
                      tmp_path / "out.mp4", audio_bed=tmp_path / "bed.wav",
                      workdir=tmp_path)

def test_a_bed_longer_than_the_cut_is_fine(monkeypatch, tmp_path):
    """`-shortest` trimming the bed's tail is the whole point of it."""
    calls = []
    monkeypatch.setattr(render.subprocess, "run",
                        lambda cmd, **kw: calls.append(cmd))
    lengths = {"bed.wav": 600.0, "a.mp4": 6.0}
    monkeypatch.setattr(render, "probe_media_duration",
                        lambda p, ffmpeg=None: lengths[Path(p).name])

    render.concat(["ffmpeg"], [tmp_path / "a.mp4"], tmp_path / "out.mp4",
                  audio_bed=tmp_path / "bed.wav", workdir=tmp_path)
    assert any("concat" in c for c in calls)

def test_a_bed_a_frame_short_is_rounding_not_a_truncation(monkeypatch, tmp_path):
    """The sum is per-clip, so the comparison carries a little slack."""
    monkeypatch.setattr(render.subprocess, "run", lambda cmd, **kw: None)
    lengths = {"bed.wav": 5.98, "a.mp4": 6.0}
    monkeypatch.setattr(render, "probe_media_duration",
                        lambda p, ffmpeg=None: lengths[Path(p).name])

    render.concat(["ffmpeg"], [tmp_path / "a.mp4"], tmp_path / "out.mp4",
                  audio_bed=tmp_path / "bed.wav", workdir=tmp_path)

def test_an_unmeasurable_bed_does_not_block_the_render(monkeypatch, tmp_path):
    """No ffprobe is not the same as a wrong length -- degrade, never block."""
    monkeypatch.setattr(render.subprocess, "run", lambda cmd, **kw: None)
    monkeypatch.setattr(render, "probe_media_duration",
                        lambda p, ffmpeg=None: None)

    render.concat(["ffmpeg"], [tmp_path / "a.mp4"], tmp_path / "out.mp4",
                  audio_bed=tmp_path / "bed.wav", workdir=tmp_path)

def test_no_bed_means_no_length_check(monkeypatch, tmp_path):
    """Without a bed there is no `-shortest`, so nothing to check."""
    def boom(*a, **kw):
        raise AssertionError("probed with no bed")

    monkeypatch.setattr(render.subprocess, "run", lambda cmd, **kw: None)
    monkeypatch.setattr(render, "probe_media_duration", boom)

    render.concat(["ffmpeg"], [tmp_path / "a.mp4"], tmp_path / "out.mp4",
                  workdir=tmp_path)
