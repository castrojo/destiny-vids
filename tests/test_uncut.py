"""Tests for the whole-video cut list (tools/uncut.py)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools import uncut  # noqa: E402

VIDEO_ID = "yt_curse_of_osiris_opening_cinematic"


def test_the_whole_video_is_every_segment_in_source_order():
    cut = uncut.whole_video(VIDEO_ID)
    starts = [s["start_sec"] for s in cut["shots"]]
    assert starts == sorted(starts)
    assert all(s["video_id"] == VIDEO_ID for s in cut["shots"])


def test_an_uncut_list_has_no_gaps_so_nothing_is_quietly_skipped():
    """A gap would mean "uncut" silently drops footage. It is reported."""
    cut = uncut.whole_video(VIDEO_ID)
    assert cut["gaps"] == []


def test_timings_on_an_uncut_list_are_source_timings():
    """No re-ordering and no cap, so the finished file shares the source clock."""
    from tools.plate import cut_timeline

    cut = uncut.whole_video(VIDEO_ID)
    timeline = cut_timeline(cut["shots"], None)
    for out_start, _, shot in timeline:
        assert out_start == shot["start_sec"] - cut["shots"][0]["start_sec"]


def test_an_unknown_video_id_fails_loudly():
    import pytest

    with pytest.raises(SystemExit):
        uncut.whole_video("yt_not_a_real_video")
