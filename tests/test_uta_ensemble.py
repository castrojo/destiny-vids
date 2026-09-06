"""The ensemble cut's arithmetic and its geometry.

Both of the faults this file pins have already shipped once on this video: a
picture that ran 0.29 s long against on-camera singing because segment
durations were rounded and summed, and copy that was placed without checking
what it landed on.
"""

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import build_uta_ensemble as B  # noqa: E402

RECORD, MONTAGE = B.load()


def rects_overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def test_the_segments_tile_the_source_exactly():
    segs = B.segments(RECORD)
    assert sum(frames for _, _, frames in segs) == RECORD["delivery"]["source_frames"]
    # and they tile it in order, with no gap and no overlap
    at = 0
    for _, start, frames in segs:
        assert start == at
        at += frames


def test_the_programme_is_the_slide_plus_the_source_and_nothing_else():
    d = RECORD["delivery"]
    assert d["programme_frames"] == d["slide_frames"] + d["source_frames"]


def test_every_boundary_is_a_whole_frame_where_the_record_says_it_is():
    t = RECORD["timeline"]
    half = B.FPS_DEN / B.FPS_NUM / 2
    # the three the band's own film gives us are MEASURED scene changes, and
    # a boundary is the frame index nearest the measurement, not a rounded
    # second typed back in
    for frame, measured in (
        (t["intro_end_frame"], 15.057),
        (t["protect_out_frame"], 351.852),
        (t["credits_frame"], 439.272),
    ):
        assert abs(B.t_of(frame) - measured) <= half


def test_the_stage_leaves_before_the_protected_passage_and_returns_after_it():
    t = RECORD["timeline"]
    assert B.t_of(t["protect_in_frame"]) <= 320.0
    assert B.t_of(t["protect_out_frame"]) >= 350.0


def test_each_animation_is_retimed_onto_the_frames_the_stage_is_up():
    """The drawing clock is stage time, not wall clock.

    Running it against wall clock hides a drawing behind the protected
    passage and hands the audience a jump when the stage returns.
    """
    span = RECORD["kid_span"]
    assert span["frames"] == B.visible_frames(RECORD)
    assert span["frames"] < span["end_frame"] - span["start_frame"]
    for kid in RECORD["kids"]:
        factor, used = B.retime(RECORD, kid)
        assert used <= kid["source_frames"]
        # used source frames, retimed, land on the span at the output rate
        out = used * factor * (B.FPS_NUM / B.FPS_DEN) / 24
        assert abs(out - span["frames"]) < 1


def test_no_kid_covers_the_band_and_no_kid_covers_another():
    win = RECORD["band_window"]
    band = (win["x"], win["y"], win["width"], win["height"])
    boxes = [
        (k["x"], k["y"], k["scaled_width"], k["scaled_height"])
        for k in B.stations(RECORD)
    ]
    for box in boxes:
        assert not rects_overlap(box, band)
        assert box[0] >= 0 and box[1] >= 0
        assert box[0] + box[2] <= B.CANVAS_W
        assert box[1] + box[3] <= B.CANVAS_H
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            assert not rects_overlap(a, b)


def test_no_pocket_reaches_a_kid_station_or_the_bands_picture():
    kids = [
        (k["x"], k["y"], k["scaled_width"], k["scaled_height"])
        for k in B.stations(RECORD)
    ]
    win = RECORD["band_window"]
    picture = (win["x"], win["y"], win["width"], win["height"])
    for name, pocket in RECORD["callout_pockets"].items():
        if not isinstance(pocket, dict) or "bounds" not in pocket:
            continue
        x0, y0, x1, y1 = pocket["bounds"]
        area = (x0, y0, x1 - x0, y1 - y0)
        assert not rects_overlap(area, picture), name
        for kid in kids:
            assert not rects_overlap(area, kid), name


def test_every_card_is_up_while_the_stage_is_up():
    stages = [
        (B.t_of(s), B.t_of(s + n))
        for kind, s, n in B.segments(RECORD)
        if kind == "stage"
    ]
    for entry in RECORD["callout_schedule"]:
        a = entry["start_seconds"]
        b = a + entry["hold_seconds"]
        assert any(s <= a and b <= e for s, e in stages), entry


def test_no_two_cards_are_up_at_once():
    times = sorted(
        (e["start_seconds"], e["start_seconds"] + e["hold_seconds"])
        for e in RECORD["callout_schedule"]
    )
    for (_, end), (start, _) in zip(times, times[1:]):
        assert start > end


def test_the_owner_protected_passage_carries_nothing():
    for entry in RECORD["callout_schedule"]:
        a = entry["start_seconds"]
        b = a + entry["hold_seconds"]
        assert b <= 320.0 or a >= 350.0


def test_every_kid_keeps_its_own_measured_keying_chain():
    """A seed or a threshold from another drawing is a wrong number."""
    for kid in RECORD["kids"]:
        chain = B.KEY_CHAINS[kid["id"]]
        assert "alphamerge" in chain or "colorkey" in chain
        if "floodfill" in chain:
            # the fill is only ever a source for the matte, never the picture
            assert "alphaextract" in chain and "alphamerge" in chain
            assert "colorkey=0x0000FF" in chain


def test_the_workflow_is_valid_yaml_and_asks_for_the_right_frame_counts():
    yaml = pytest.importorskip("yaml")
    names = [
        B.card_name(i, e) for i, e in enumerate(RECORD["callout_schedule"])
    ]
    text = B.workflow(RECORD, MONTAGE, names)
    doc = yaml.safe_load(text)
    assert doc["kind"] == "Workflow"
    for _, start, frames in B.segments(RECORD):
        assert f"-frames:v {frames}" in text
    assert f"-frames:v {RECORD['delivery']['slide_frames']}" in text
    # the audio is decoded once and encoded once
    assert text.count("-c:a aac") == 1


def test_no_hero_step_shells_out_to_a_local_ffmpeg():
    """Every frame this repo touches for a hero video is touched on the farm."""
    src = (REPO / "scripts" / "build_uta_ensemble.py").read_text()
    assert "subprocess" not in src


def test_every_kid_stream_is_padded_past_its_retime():
    """An overlay past the end of its input does not show the last frame.

    RAFI_01 came back as a white ghost for the final second of the first
    pass, because resampling 24/1 onto 24000/1001 landed its stream a frame
    short of the span the composite asked for.
    """
    for kid in B.stations(RECORD):
        step = B.key_step(RECORD, kid)
        assert f"tpad=stop_mode=clone:stop={B.TAIL_PAD}" in step
        assert f"-frames:v {B.visible_frames(RECORD)}" in step
