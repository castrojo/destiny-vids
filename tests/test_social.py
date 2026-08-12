"""tools/social.py — a finished cut under a byte cap.

Offline: the arithmetic and the command are checked, nothing is encoded.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools import social  # noqa: E402


def test_the_video_bitrate_fills_the_cap_and_nothing_more():
    # 10 MiB, 100s, 192k audio.
    kbps = social.video_bitrate_for(10 * social.MIB, 100.0, 192)
    budget_bits = 10 * social.MIB * 8 * (1 - social.OVERHEAD)
    spent = kbps * 1000 * 100 + 192 * 1000 * 100
    assert spent <= budget_bits
    # ...and it is not leaving a whole rung on the table.
    assert spent > budget_bits * 0.99


def test_headroom_is_held_back_so_muxing_overhead_cannot_bust_the_cap():
    assert 0 < social.OVERHEAD < 0.1
    kbps = social.video_bitrate_for(10 * social.MIB, 60.0, 128)
    total_bits = (kbps + 128) * 1000 * 60
    assert total_bits < 10 * social.MIB * 8


def test_a_cap_the_audio_alone_cannot_fit_is_an_error_not_a_negative_bitrate():
    """Silently encoding at a negative or zero bitrate would produce a file
    that is somehow both broken and over the cap."""
    with pytest.raises(ValueError, match="exceeds"):
        social.video_bitrate_for(1 * social.MIB, 600.0, 256)


def test_mb_means_mebibytes():
    """Platforms quote '10MB' ambiguously; the smaller unit is the safe read."""
    assert social.MIB == 1024 * 1024


def test_the_command_is_two_pass_and_carries_the_colour_vui(tmp_path, monkeypatch):
    src = tmp_path / "in.mp4"
    src.write_bytes(b"")
    monkeypatch.setattr(social, "source_facts", lambda p: {
        "width": 1920, "height": 1080, "fps": "60000/1001", "duration": 30.0})
    _, kbps, _, cmds = social.build_commands(
        src, tmp_path / "out.mp4", target_mb=10, height=720, audio_kbps=192,
        ffmpeg=["ffmpeg"], passlog=str(tmp_path / "x264"))
    first, second = cmds
    assert "-pass" in first and first[first.index("-pass") + 1] == "1"
    assert "-an" in first, "pass 1 must not waste time on audio"
    assert second[second.index("-pass") + 1] == "2"
    # x264 copies only the matrix from the -color_* flags, so the VUI has to be
    # written explicitly or the file disagrees with every other deliverable.
    params = second[second.index("-x264-params") + 1]
    for key in ("colorprim=bt709", "transfer=bt709", "colormatrix=bt709"):
        assert key in params
    assert f"-b:v" in second and f"{kbps}k" in second


def test_no_audio_processing_is_applied():
    """Re-encoding is allowed; processing is not. A normaliser or limiter here
    would break the audio tenet in the one file most people actually hear."""
    source = open(os.path.join(os.path.dirname(__file__), "..", "tools",
                               "social.py"), encoding="utf-8").read()
    for forbidden in ("loudnorm", "dynaudnorm", "alimiter", "acompressor",
                      "equalizer", "-af "):
        assert forbidden not in source, forbidden


def test_the_picture_is_scaled_only_when_it_needs_to_be(tmp_path, monkeypatch):
    src = tmp_path / "in.mp4"
    src.write_bytes(b"")
    monkeypatch.setattr(social, "source_facts", lambda p: {
        "width": 1280, "height": 720, "fps": "30/1", "duration": 30.0})
    _, _, _, cmds = social.build_commands(
        src, tmp_path / "out.mp4", target_mb=10, height=720, audio_kbps=192,
        ffmpeg=["ffmpeg"], passlog=str(tmp_path / "x264"))
    vf = cmds[0][cmds[0].index("-vf") + 1]
    assert vf.startswith("null"), "a 720p source must not be re-scaled to 720p"
