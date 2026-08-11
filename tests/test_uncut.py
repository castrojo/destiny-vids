"""Tests for the whole-video cut list (tools/uncut.py)."""
import os
import sys

import pytest

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
        # approx: durations accumulate in float, boundaries do not.
        assert out_start == pytest.approx(
            shot["start_sec"] - cut["shots"][0]["start_sec"])


def test_an_unknown_video_id_fails_loudly():
    with pytest.raises(SystemExit):
        uncut.whole_video("yt_not_a_real_video")


def test_a_cut_window_is_excluded_from_the_cut_list():
    """The PEGI card (0-3.4s) is the whole frame, so it is cut, not boxed."""
    cut = uncut.whole_video(VIDEO_ID)
    assert cut["shots"][0]["start_sec"] == pytest.approx(3.4)
    assert all(s["start_sec"] >= 3.4 for s in cut["shots"])
    # The PEGI shot itself (0-3.37s) is entirely inside the window: dropped.
    assert not any(s["segment_id"].endswith("_0000-0003") for s in cut["shots"])


def test_a_partially_cut_shot_is_trimmed_not_dropped():
    """The gateway shot runs 148.07-173.17s but only its last ~9.6s is the
    logo card: it survives, ending where the card starts. Same at the head:
    the shot spanning the PEGI boundary is trimmed to 3.4s, not dropped."""
    cut = uncut.whole_video(VIDEO_ID)
    head = cut["shots"][0]
    assert head["segment_id"].endswith("_0003-0010")
    assert head["start_sec"] == pytest.approx(3.4)
    tail = cut["shots"][-1]
    assert tail["segment_id"].endswith("_0148-0173")
    assert tail["start_sec"] == pytest.approx(148.066667)
    assert tail["end_sec"] == pytest.approx(163.6)


def test_uncut_and_redact_agree_on_the_kept_range():
    """Plate timings are computed against the cut list and burned onto the
    redacted file, so the two must trim to exactly the same range."""
    from tools import redact

    cut = uncut.whole_video(VIDEO_ID)
    start, end = redact.kept_range(
        redact.load_redactions(VIDEO_ID)["redactions"],
        redact.video_extent(VIDEO_ID))
    assert (cut["shots"][0]["start_sec"],
            cut["shots"][-1]["end_sec"]) == (pytest.approx(start),
                                             pytest.approx(end))


def test_trimming_does_not_open_gaps_in_the_cut_list():
    """Clamping head and tail leaves the middle contiguous: no footage the
    index covers is quietly skipped."""
    cut = uncut.whole_video(VIDEO_ID)
    assert cut["gaps"] == []


def test_a_video_without_redactions_is_untrimmed(tmp_path):
    """No redactions file -> no cut windows -> the whole video, as before."""
    import json

    seg = {"segment_id": "seg_x_0000-0010", "video_id": "x",
           "start_sec": 0.0, "end_sec": 10.0}
    (tmp_path / "seg_x_0000-0010.json").write_text(json.dumps(seg))
    cut = uncut.whole_video("x", segments_dir=tmp_path,
                            redactions_dir=tmp_path / "no-such-dir")
    assert cut["shots"][0]["start_sec"] == 0.0
    assert cut["shots"][-1]["end_sec"] == 10.0
