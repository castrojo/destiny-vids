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
