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
import render_uta_callout as C  # noqa: E402

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


def test_each_animation_has_its_own_retime_factor():
    factors = [B.retime(RECORD, kid)[0] for kid in RECORD["kids"]]
    assert len(set(factors)) == len(RECORD["kids"])


def test_builder_uses_the_declared_delivery_name():
    names = [B.card_name(i, e) for i, e in enumerate(RECORD["callout_schedule"])]
    text = B.workflow(RECORD, MONTAGE, names)
    assert f"/work/{RECORD['delivery']['output']}" in text


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


def test_leonardos_spear_faces_inward():
    leonardo = next(k for k in RECORD["kids"] if k["id"] == "LEONARDO")
    assert leonardo["station"] == "right-top"
    assert leonardo["flip"] is False


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


def test_band_is_raised_to_give_bottom_equipment_room():
    assert RECORD["band_window"]["y"] == 407
    assert RECORD["callout_pockets"]["bottom"]["height"] == 400


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


def test_every_callout_uses_clean_equipment_not_review_crops():
    equipment = RECORD["equipment_assets"]
    for entry in RECORD["callout_schedule"]:
        assert "art" not in entry
        assert entry["equipment"] in equipment
    assert all(
        not spec["file"].startswith(".work-uta-general/review/")
        for name, spec in equipment.items()
        if name != "_what"
    )


def test_tall_bottom_equipment_is_rotated_sideways():
    equipment = RECORD["equipment_assets"]
    assert equipment["spear"]["rotation_degrees"] == 90
    assert equipment["double_kopis"]["rotation_degrees"] == 90
    for name, spec in equipment.items():
        if name != "_what":
            assert spec["rotation_degrees"] in (0, 90, 180, 270)


def test_equipment_extraction_selects_only_reviewed_components(tmp_path):
    from PIL import Image, ImageDraw

    source = Image.new("RGBA", (80, 60), (0, 0, 0, 0))
    draw = ImageDraw.Draw(source)
    draw.rectangle((5, 5, 20, 25), fill=(255, 0, 0, 255))
    draw.rectangle((50, 10, 58, 45), fill=(0, 255, 0, 255))
    path = tmp_path / "source.png"
    source.save(path)

    art = B.extract_equipment(
        {
            "file": "source.png",
            "component_seeds": [[54, 20]],
            "rotation_degrees": 90,
        },
        tmp_path,
        tmp_path / "art.png",
    )

    assert art.width > art.height
    colors = {
        art.getpixel((x, y))[:3]
        for y in range(art.height)
        for x in range(art.width)
        if art.getpixel((x, y))[3]
    }
    assert colors == {(0, 255, 0)}


def test_callout_renderer_rejects_an_opaque_sheet_crop(tmp_path):
    from PIL import Image

    crop = tmp_path / "sheet-crop.png"
    Image.new("RGB", (100, 100), "white").save(crop)
    callout = json.loads(json.dumps(
        MONTAGE["composition"]["callouts"]["bomb_10mm"]
    ))
    callout["label_box"] = {"x": 0, "y": 0, "width": 800, "height": 300}
    callout["plate_luma"] = {"mean": 64}

    with pytest.raises(ValueError, match="extracted RGBA"):
        C.render_callout(callout, art_path=crop, canvas=(1280, 720))


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


def test_leonardo_preserves_enclosed_white_paper():
    """Only Leonardo's connected outer paper is transparent.

    A global colorkey removed enclosed white regions inside his silhouette,
    leaving the top-right drawing dark against the stage.
    """
    chain = B.KEY_CHAINS["LEONARDO"]
    assert "split[c][m]" in chain
    assert "floodfill" in chain
    assert "alphaextract[al]" in chain
    assert "[c][al]alphamerge" in chain


def test_leonardos_name_is_masked_before_keying():
    chain = B.KEY_CHAINS["LEONARDO"]
    assert B.LEONARDO_NAME_MASK in chain
    assert chain.index(B.LEONARDO_NAME_MASK) < chain.index("floodfill")


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
    assert ": > /work/list.txt" in text
    assert "-v error -y -i \"$out\" -af ebur128" not in text


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


def test_no_kid_carries_its_sources_closing_white_flash():
    """Every one of these animations ends by flashing to white.

    All four sources append the same ~49 frame flourish: a jump to pure
    white that decays back. Carried into the cut it puts a white ghost of
    the child on screen in the last second of the stage.
    """
    for kid in RECORD["kids"]:
        assert "use_frames" in kid, kid["id"]
        assert kid["use_frames"] < kid["source_frames"] - 40, kid["id"]
        assert "flash" in kid["use_frames_note"] or "dim" in kid["use_frames_note"]


def test_only_the_aperture_is_rounded():
    """The corners are rounded on the band's window, not on the delivery.

    Rounding the delivered frame would put black corners on a television,
    and the full-frame segments include an interval the owner protected
    from any filter at all.
    """
    names = [B.card_name(i, e) for i, e in enumerate(RECORD["callout_schedule"])]
    text = B.workflow(RECORD, MONTAGE, names)
    # the kids' own keying chains alphamerge too, so count the aperture's
    assert text.count("[bandpix][amask]alphamerge") == sum(
        1 for kind, _, _ in B.segments(RECORD) if kind == "stage"
    )
    # the clean segments carry no mask and no alpha work at all
    for kind, start, frames in B.segments(RECORD):
        if kind == "clean":
            assert B.APERTURE_MASK not in B.clean_segment(0, start, frames)


def test_the_aperture_mask_matches_the_aperture():
    from PIL import Image

    win = RECORD["band_window"]
    path = B.WORK / "cards" / B.APERTURE_MASK
    if not path.exists():
        pytest.skip("mask not rendered in this checkout")
    mask = Image.open(path)
    assert mask.size == (win["width"], win["height"])
    assert mask.mode == "L"
    # opaque in the middle, cut away at the corner, and soft in between
    assert mask.getpixel((win["width"] // 2, win["height"] // 2)) == 255
    assert mask.getpixel((0, 0)) == 0
    assert 0 < mask.getpixel((win["corner_radius"], 0)) <= 255
