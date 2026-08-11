"""Tests for the burned-in-copy redactor (tools/redact.py)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools import redact  # noqa: E402


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


def test_the_checked_in_redactions_cover_both_burned_in_cards():
    data = redact.load_redactions("yt_curse_of_osiris_opening_cinematic")
    ids = {item["id"] for item in data["redactions"]}
    assert {"pegi_card", "logo_card_title", "logo_card_legal"} <= ids
    # Every window must be real, and the filter graph must build.
    assert redact.drawbox_filters(data["redactions"])
