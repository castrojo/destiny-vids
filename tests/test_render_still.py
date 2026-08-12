"""A still shot renders and concatenates with a cut clip.

The failure this guards is specific: an artwork card takes the slot a dropped
shot left behind, and the concat demuxer requires identical stream properties
across inputs. If a still ever disagrees with a cut clip on size, rate, pixel
format or *whether it has an audio stream at all*, the join fails — and the
audio disposition flips with ``--audio``, which is exactly how the cut is
rendered.
"""
import re
import subprocess

import pytest

from tools import render


def _ffmpeg():
    try:
        ffmpeg = render.find_ffmpeg(prefer_container=False)
    except RuntimeError:
        pytest.skip("no ffmpeg available")
    # Resolving a command is not the same as being able to run it: CI has no
    # ffmpeg at all, and DESTINY_FFMPEG can name a path that does not exist.
    try:
        subprocess.run(list(ffmpeg) + ["-version"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("ffmpeg is not runnable here")
    return ffmpeg


def _streams(ffmpeg, path):
    """Stream types in a file, read with the *same* binary the renderer uses.

    Deliberately not ``ffprobe`` from PATH: on this host that is a shim into a
    container which bind-mounts only ``$HOME``, so it reports a file under
    pytest's ``/var/tmp`` tmp_path as "No such file or directory" — a
    confusing failure that has nothing to do with the code under test.
    """
    out = subprocess.run(list(ffmpeg) + ["-hide_banner", "-i", str(path)],
                         capture_output=True, text=True)
    return set(re.findall(r"Stream #\d+:\d+.*?: (Video|Audio)", out.stderr))


@pytest.mark.parametrize("keep_audio", [True, False])
def test_still_matches_cut_clip_and_concats(tmp_path, keep_audio):
    ffmpeg = _ffmpeg()

    # A synthetic source stands in for footage: the repo ships no media.
    src = tmp_path / "src.mp4"
    subprocess.run(list(ffmpeg) + [
        "-v", "error", "-y",
        "-f", "lavfi", "-i", "testsrc=size=1920x1080:rate=30:duration=3",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-map", "0:v:0", "-map", "1:a:0", "-t", "3",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(src)], check=True)
    assert "Audio" in _streams(ffmpeg, src), "fixture source must carry audio"

    image = tmp_path / "art.png"
    subprocess.run(list(ffmpeg) + [
        "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=red:size=1600x900",
        "-frames:v", "1", str(image)], check=True)

    cut = tmp_path / "cut.mp4"
    still = tmp_path / "still.mp4"
    render.cut_clip(ffmpeg, src, 0.5, 1.0, cut, keep_audio=keep_audio)
    render.still_clip(ffmpeg, image, 1.0, still, keep_audio=keep_audio)

    # Same stream set, or the concat below cannot join them.
    assert _streams(ffmpeg, still) == _streams(ffmpeg, cut)
    assert ("Audio" in _streams(ffmpeg, still)) is keep_audio

    out = tmp_path / "joined.mp4"
    render.concat(ffmpeg, [cut, still], out, workdir=tmp_path)
    assert out.exists() and out.stat().st_size > 0


def test_still_shot_survives_the_hold_clamp():
    """A still has no out-point, so its authored hold is not clamped away."""
    shot = {"still": "/tmp/x.jpg", "duration": 6.0, "segment_id": "card_1"}
    assert render.resolve_duration(shot) == 6.0
    # ...and a cap leaves it alone: a card's length is a musical decision.
    assert render.cap_holds([shot], max_shot_sec=2.0)[0]["duration"] == 6.0


def test_render_reports_a_missing_still_instead_of_crashing(tmp_path):
    """A missing artwork file is reported like any missing source.

    ``ffmpeg`` is passed explicitly so this stays in the offline suite: no clip
    ever resolves, so the binary is never invoked, and resolving one would
    otherwise fail on a runner that has none.
    """
    shots = [{"still": str(tmp_path / "nope.jpg"), "duration": 1.0, "segment_id": "card_1"}]
    with pytest.raises(RuntimeError, match="nothing to render"):
        render.render(shots, str(tmp_path), tmp_path / "out.mp4", verbose=False,
                      ffmpeg=["ffmpeg-not-invoked"])


def test_a_millisecond_rounded_shot_does_not_report_as_clamped(capsys):
    """The CLAMPED warning must name a REAL overrun, and nothing else.

    A shotlist rounds its endpoints to milliseconds, so `end - start`
    reconstructs the duration with a few femtoseconds of float error:
    85.996 - 72.94 is 13.055999999999997, not 13.056. Compared exactly, every
    shot "overruns" and every shot warns -- which is what the Wolves feature
    did, 33 times per render. A warning that fires on everything is a warning
    nobody reads, and this one exists to flag a `clean`-gate violation: a hold
    that decodes past the out-point into footage no tagger ever vetted.
    """
    from tools.render import resolve_duration

    shot = {"segment_id": "s", "start_sec": 72.94, "end_sec": 85.996,
            "duration": 13.056}
    assert shot["end_sec"] - shot["start_sec"] < shot["duration"]  # the trap
    assert resolve_duration(shot) == 13.056
    assert "CLAMPED" not in capsys.readouterr().err


def test_a_real_overrun_still_clamps_and_says_so(capsys):
    """The tolerance is a microsecond -- far under a frame at any frame rate --
    so a hold that genuinely runs past the vetted out-point is unaffected."""
    from tools.render import resolve_duration

    shot = {"segment_id": "greedy", "start_sec": 10.0, "end_sec": 14.2,
            "duration": 600.0}
    assert resolve_duration(shot) == pytest.approx(4.2)
    assert "CLAMPED" in capsys.readouterr().err
