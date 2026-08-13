"""Tests for the burned-in-copy redactor (tools/redact.py)."""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools import peaks, redact  # noqa: E402


BOXED = {"id": "logo", "start_sec": 10.0, "end_sec": 20.0, "reason": "logo",
         "boxes": [{"x": 100, "y": 200, "w": 300, "h": 40}]}
FULL = {"id": "card", "start_sec": 0.0, "end_sec": 3.4, "reason": "ratings card",
        "boxes": "full"}


def test_a_box_becomes_one_timeline_gated_drawbox():
    filters = redact.drawbox_filters([BOXED])
    assert len(filters) == 1
    assert "drawbox=x=100:y=200:w=300:h=40" in filters[0]
    # FFmpeg timeline editing: the filter passes the frame through when false.
    assert "enable='between(t,10.000,20.000)'" in filters[0]


def test_full_covers_the_whole_frame():
    filters = redact.drawbox_filters([FULL])
    assert f"w={redact.FRAME_W}:h={redact.FRAME_H}" in filters[0]
    assert "x=0:y=0" in filters[0]


def test_a_backwards_window_is_rejected():
    with pytest.raises(ValueError):
        redact.drawbox_filters([dict(BOXED, start_sec=20.0, end_sec=10.0)])


def test_source_audio_is_stream_copied_when_no_bed_is_given():
    cmd = redact.build_command(["ffmpeg"], "in.mp4",
                               redact.drawbox_filters([BOXED]), "out.mp4")
    assert "-c:a" in cmd and cmd[cmd.index("-c:a") + 1] == "copy"
    assert "0:a?" in cmd


def test_a_music_bed_replaces_the_source_audio_and_never_extends_the_picture():
    cmd = redact.build_command(["ffmpeg"], "in.mp4",
                               redact.drawbox_filters([BOXED]), "out.mp4",
                               audio="bed.mp3", audio_gain=0.9)
    assert cmd.count("-i") == 2
    assert "1:a:0" in cmd, "the bed, not the source, is mapped to audio"
    assert "-shortest" in cmd, "a long track must not extend the video"
    assert "volume=0.9" in cmd[cmd.index("-af") + 1]


def test_the_checked_in_redactions_cut_the_full_frame_cards():
    """All three cards on the Osiris upload ARE the whole frame, so they are
    cut, not boxed: nothing to paint, and the kept range is the cinematic."""
    data = redact.load_redactions("yt_curse_of_osiris_opening_cinematic")
    ids = {item["id"] for item in data["redactions"]}
    assert {"pegi_card", "logo_card_title", "logo_card_legal"} <= ids
    assert all(redact.action_of(i) == "cut" for i in data["redactions"])
    assert redact.drawbox_filters(data["redactions"]) == []
    extent = redact.video_extent("yt_curse_of_osiris_opening_cinematic")
    assert redact.kept_range(data["redactions"], extent) == (3.4, 163.6)


def test_a_record_with_no_action_still_draws_a_box():
    """The field defaults to 'box', so pre-action data behaves exactly as before."""
    assert redact.action_of(BOXED) == "box"
    assert redact.drawbox_filters([BOXED])
    # And with no cut windows anywhere, nothing is trimmed.
    assert redact.kept_range([BOXED], 173.194) == (0.0, 173.194)


def test_a_cut_record_draws_no_box():
    cut = {"id": "card", "start_sec": 0.0, "end_sec": 3.4, "reason": "card",
           "action": "cut", "boxes": "full"}
    assert redact.drawbox_filters([cut, BOXED]) == redact.drawbox_filters([BOXED])


def test_an_unknown_action_is_rejected_loudly():
    with pytest.raises(ValueError):
        redact.action_of(dict(BOXED, action="blur"))


def test_a_backwards_cut_window_is_rejected():
    with pytest.raises(ValueError):
        redact.kept_range([dict(BOXED, action="cut",
                                start_sec=20.0, end_sec=10.0)], 173.194)


def test_kept_range_is_the_complement_of_the_cut_window_union():
    # Overlapping cut windows merge before the range is computed, so two
    # records sharing the logo-card window cut it once.
    records = [dict(BOXED, id="a", action="cut", start_sec=0.0, end_sec=3.4),
               dict(BOXED, id="b", action="cut", start_sec=163.6, end_sec=173.194),
               dict(BOXED, id="c", action="cut", start_sec=163.6, end_sec=173.194)]
    assert redact.kept_range(records, 173.194) == (3.4, 163.6)
    # Head-only and tail-only cuts leave the other end alone.
    assert redact.kept_range(records[:1], 173.194) == (3.4, 173.194)
    assert redact.kept_range(records[1:], 173.194) == (0.0, 163.6)


def test_a_cut_window_in_the_middle_is_rejected():
    """A middle cut would split the video in two, which one trimmed encode
    cannot express -- fail loudly instead of disagreeing with uncut.py."""
    records = [dict(BOXED, id="mid", action="cut", start_sec=50.0, end_sec=60.0)]
    with pytest.raises(ValueError):
        redact.kept_range(records, 173.194)


def test_a_tail_window_must_reach_the_end_of_the_video():
    """A 'tail' window ending early leaves a hole, not a trim."""
    records = [dict(BOXED, id="tail", action="cut",
                    start_sec=163.6, end_sec=170.0)]
    with pytest.raises(ValueError):
        redact.kept_range(records, 173.194)
    # ...but a frame or two of authoring slop still counts as reaching it.
    records[0]["end_sec"] = 173.194 - redact.EDGE_SLOP / 2
    assert redact.kept_range(records, 173.194) == (0.0, 163.6)


def test_a_trimmed_encode_trims_video_after_the_boxes():
    cmd = redact.build_command(["ffmpeg"], "in.mp4",
                               redact.drawbox_filters([BOXED]), "out.mp4",
                               trim=(3.4, 163.6))
    vf = cmd[cmd.index("-vf") + 1]
    # The trim follows the drawboxes, so box windows stay in source seconds.
    assert vf.endswith("trim=start=3.400:end=163.600,setpts=PTS-STARTPTS")
    assert vf.index("drawbox") < vf.index("trim")


def test_a_trimmed_encode_without_a_bed_reencodes_a_trimmed_audio():
    """A trimmed source track cannot be stream-copied."""
    cmd = redact.build_command(["ffmpeg"], "in.mp4", [], "out.mp4",
                               trim=(3.4, 163.6))
    assert "atrim=start=3.400:end=163.600,asetpts=PTS-STARTPTS" \
        in cmd[cmd.index("-af") + 1]
    assert cmd[cmd.index("-c:a") + 1] == "aac"


def test_a_trimmed_encode_with_a_bed_starts_the_bed_at_the_trimmed_picture():
    """The bed maps from its own beginning; the video trim must not skip its
    head, and -shortest stops it where the trimmed picture ends."""
    cmd = redact.build_command(["ffmpeg"], "in.mp4", [], "out.mp4",
                               audio="bed.mp3", audio_gain=0.9,
                               trim=(3.4, 163.6))
    assert "-shortest" in cmd
    af = cmd[cmd.index("-af") + 1]
    assert "atrim" not in af and af == "volume=0.9"
    assert "trim=start=3.400:end=163.600" in cmd[cmd.index("-vf") + 1]


# --- music bed headroom ------------------------------------------------------

def test_gain_is_derived_from_the_beds_true_peak(monkeypatch):
    """A hot master is scaled to leave headroom, by a STATIC gain.

    Intersample peaks exceed sample peaks, so a bed that measures +1.5 dBTP
    clips on lossy playback even though no sample is over. The fix is a gain,
    never a normaliser: loudnorm would rewrite the dynamics the artist chose.
    """
    monkeypatch.setattr(peaks, "measure_true_peak", lambda *a, **k: 1.5)
    gain, peak = redact.gain_for_headroom("bed.mp3", target_dbtp=-1.1)
    assert peak == 1.5
    # 1.5 dBTP down to -1.1 dBTP is -2.6 dB.
    assert gain == pytest.approx(10 ** (-2.6 / 20), rel=1e-6)
    # ...and applying it lands on the target.
    assert 1.5 + 20 * math.log10(gain) == pytest.approx(-1.1)


def test_a_quiet_bed_is_never_pushed_up_to_the_target(monkeypatch):
    """The target is a ceiling, not a loudness mandate."""
    monkeypatch.setattr(peaks, "measure_true_peak", lambda *a, **k: -8.0)
    gain, peak = redact.gain_for_headroom("bed.mp3", target_dbtp=-1.1)
    assert gain == 1.0 and peak == -8.0


def test_true_peak_is_read_from_the_last_ebur128_summary(monkeypatch):
    """ebur128 prints running peaks; only the final summary is the answer."""
    class Proc:
        stderr = ("Peak: -6.0 dBFS\n"
                  "  True peak:\n    Peak:        0.5 dBFS\n")
    monkeypatch.setattr(peaks.subprocess, "run", lambda *a, **k: Proc())
    assert redact.measure_true_peak("x.mp3", ffmpeg=["ffmpeg"]) == 0.5


def test_flac_deliverable_gets_no_bitrate():
    """A bitrate is meaningless for a lossless codec, so it is not passed.

    ``flac`` exists so a later re-encode -- a stereo fold-down for streaming, a
    different container -- starts from the bed rather than from a lossy file.
    """
    assert redact.audio_encode_opts("aac") == ["-c:a", "aac", "-b:a", "192k"]
    assert redact.audio_encode_opts("flac") == ["-c:a", "flac"]


def test_the_default_deliverable_codec_is_unchanged():
    """Adding the lossless option must not move the shipped default."""
    cmd = redact.build_command(["ffmpeg"], "in.mp4", [], "out.mp4",
                               audio="bed.wav", audio_gain=0.8)
    assert "-c:a" in cmd and cmd[cmd.index("-c:a") + 1] == "aac"
    assert "192k" in cmd


def test_a_lossless_deliverable_is_requested_by_codec():
    cmd = redact.build_command(["ffmpeg"], "in.mp4", [], "out.mp4",
                               audio="bed.wav", audio_gain=0.8,
                               audio_codec="flac")
    assert cmd[cmd.index("-c:a") + 1] == "flac"
    assert "192k" not in cmd


def test_delivered_peak_is_corrected_when_the_encoder_overshoots(monkeypatch, tmp_path):
    """The bed landing on target is not the same as the FILE landing on target.

    A lossy encoder reconstructs inter-sample peaks above the samples it was
    given, so a -1.1 dBTP mix came back from AAC at +0.3 dBTP -- clipping, from
    a chain correct at every earlier step. The correction is another static
    gain, and it only ever goes down.
    """
    peaks_iter = iter([0.3, -1.4])
    monkeypatch.setattr(peaks, "measure_true_peak", lambda *a, **k: next(peaks_iter))
    gains = []

    def fake_run(cmd, **kwargs):
        if "volume=" in " ".join(cmd):
            gains.append(float(
                [c for c in cmd if c.startswith("volume=")][0].split("=")[1]))

        class P:
            returncode = 0
            stderr = ""
        return P()

    monkeypatch.setattr(redact.subprocess, "run", fake_run)
    redact.apply("in.mp4", [], str(tmp_path / "out.mp4"), audio="bed.wav",
                 audio_gain=0.8, ffmpeg=["ffmpeg"], target_dbtp=-1.1)
    # One corrective pass, quieter than the first: 0.3 dBTP is 1.4 dB over.
    assert len(gains) == 2
    assert gains[1] < gains[0]
    assert gains[1] == pytest.approx(0.8 * 10 ** (-1.4 / 20), rel=1e-6)


def test_a_delivered_file_with_headroom_is_not_re_encoded(monkeypatch, tmp_path):
    """Corrections stop at the first safe result -- the overshoot is not
    monotonic in the gain, so chasing a narrow window oscillates."""
    monkeypatch.setattr(peaks, "measure_true_peak", lambda *a, **k: -2.4)
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)

        class P:
            returncode = 0
            stderr = ""
        return P()

    monkeypatch.setattr(redact.subprocess, "run", fake_run)
    redact.apply("in.mp4", [], str(tmp_path / "out.mp4"), audio="bed.wav",
                 audio_gain=0.8, ffmpeg=["ffmpeg"], target_dbtp=-1.1)
    assert len(calls) == 1
