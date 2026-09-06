"""The ensemble cut's arithmetic and its geometry.

Both of the faults this file pins have already shipped once on this video: a
picture that ran 0.29 s long against on-camera singing because segment
durations were rounded and summed, and copy that was placed without checking
what it landed on.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import build_uta_ensemble as B  # noqa: E402
import render_uta_callout as C  # noqa: E402

RECORD, MONTAGE, LEONARDO = B.load()
CATALOG = B.equipment_catalog(RECORD, MONTAGE, LEONARDO)


def _wordmark_image():
    image = Image.new("RGBA", (1200, 300), (0, 0, 0, 0))
    ImageDraw.Draw(image).rounded_rectangle(
        (0, 0, 1199, 299), radius=24, fill=(255, 255, 255, 255)
    )
    return image


WORDMARK_IMAGE = _wordmark_image()


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


def test_ensemble_catalog_contains_all_rafi_and_leonardo_items():
    assert set(CATALOG) == (
        set(MONTAGE["composition"]["callouts"])
        | set(LEONARDO["items"])
    )


def test_every_unique_equipment_item_appears_once():
    scheduled = [entry["item"] for entry in RECORD["callout_schedule"]]
    assert len(scheduled) == len(set(scheduled))
    assert set(scheduled) == set(CATALOG)


def test_schedule_invariants_are_enforced():
    B.validate_equipment_schedule(RECORD, CATALOG, MONTAGE)


def test_every_hold_clears_copy_readability_floor():
    for entry in RECORD["callout_schedule"]:
        callout = B.normalize_callout(entry["item"], CATALOG[entry["item"]])
        assert entry["hold_seconds"] >= B.required_hold_seconds(callout)


def test_normalized_callouts_preserve_rafi_render_copy():
    normalized = B.normalize_callout("spear", CATALOG["spear"])
    assert normalized["copy"] == {
        "label_render": "DIY MAGICAL / HI-TECH SPEAR",
        "subtitle_render": "TUNGSTEN ALLOY",
        "description_render": (
            "A SPEAR THAT CAN BE SHORTENED OR LENGTHENED FOR TACTICAL "
            "PURPOSES, WHETHER FOR CLOSE-QUARTERS INDIVIDUAL COMBAT OR "
            "CAVALRY COMBAT."
        ),
    }
    assert normalized["font_size"] == 96
    assert normalized["description_font_size"] == 54


def test_normalized_callouts_fill_only_placeholder_descriptions():
    placeholder = B.normalize_callout(
        "leonardo_regular_hunting_arrow",
        CATALOG["leonardo_regular_hunting_arrow"],
    )
    authored = B.normalize_callout(
        "leonardo_hi_tech_sword",
        CATALOG["leonardo_hi_tech_sword"],
    )
    assert placeholder["copy"]["description_render"].strip()
    assert placeholder["copy"]["description_render"] != "REGULAR HUNTING ARROW"
    assert authored["copy"]["description_render"] == (
        "FEATURING A SHOCK-WAVE AIR BLAST WITH A COCKING/PUMPING SYSTEM"
    )


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


def test_character_visual_weight_is_measured_and_balanced():
    measured = RECORD["character_balance"]["measured_final_opaque_pixels"]
    assert max(measured.values()) / min(measured.values()) < 1.01
    leonardo = next(k for k in B.stations(RECORD) if k["id"] == "LEONARDO")
    assert leonardo["scaled_width"] == 640


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
    assert RECORD["callout_pockets"]["bottom"]["height"] == 425


def test_wordmark_is_centered_and_above_the_band():
    mark = RECORD["wordmark"]
    assert mark["x"] == (B.CANVAS_W - mark["display_width"]) // 2
    assert mark["y"] >= 0
    assert mark["y"] < RECORD["band_window"]["y"]


def test_wordmark_does_not_overlap_kids_band_or_equipment():
    box = B.wordmark_box(RECORD, WORDMARK_IMAGE)
    assert not rects_overlap(box, B.band_box(RECORD))
    for kid in B.stations(RECORD):
        assert not rects_overlap(box, B.station_box(kid))
    assert not rects_overlap(box, B.pocket_box(RECORD, "bottom"))


def test_all_equipment_uses_the_bottom_rail():
    assert {entry["pocket"] for entry in RECORD["callout_schedule"]} == {"bottom"}


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
        assert start >= end + 1.0


def test_solid_card_alpha_stays_inside_bottom_bounds(tmp_path):
    from PIL import Image, ImageDraw

    art_path = tmp_path / "synthetic-art.png"
    art = Image.new("RGBA", (240, 160), (0, 0, 0, 0))
    ImageDraw.Draw(art).rounded_rectangle(
        (24, 20, 215, 139), radius=18, fill=(255, 255, 255, 220)
    )
    art.save(art_path)

    pocket = dict(RECORD["callout_pockets"]["bottom"])
    bounds = pocket.pop("bounds")
    for item_id, item in CATALOG.items():
        callout = B.normalize_callout(item_id, item)
        art = (
            str(art_path)
            if item["art"].get("mode", "components") != "text_only"
            else None
        )
        image, _, _ = B.render_card(
            callout,
            item,
            pocket,
            bounds,
            art_path=art,
            plate_mean=64,
        )
        assert B.fits(B.ink_bbox(image), bounds), item_id


def test_audit_assets_propagates_failure_to_cli_exit_code(tmp_path):
    script = REPO / "scripts" / "build_uta_ensemble.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--audit-assets",
            "--hero-root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "ERROR" in result.stderr


def test_every_callout_uses_clean_equipment_not_review_crops():
    equipment = CATALOG
    for entry in RECORD["callout_schedule"]:
        assert "art" not in entry
        assert entry["item"] in equipment
    assert all(
        not spec["art"]["file"].startswith(".work-uta-general/review/")
        for spec in equipment.values()
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


def test_equipment_extraction_masks_context_crop_and_keeps_rgba(tmp_path):
    from PIL import Image, ImageDraw

    source = Image.new("RGBA", (120, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(source)
    draw.rectangle((30, 25, 75, 75), fill=(0, 0, 255, 255))
    path = tmp_path / "pose.png"
    source.save(path)

    art = B.extract_equipment(
        {
            "file": "pose.png",
            "mode": "context_crop",
            "crop": [20, 15, 70, 70],
            "mask_polygon": [[25, 20], [80, 20], [80, 80], [25, 80]],
            "context_note": "synthetic attached context",
            "rotation_degrees": 90,
        },
        tmp_path,
        tmp_path / "art.png",
    )

    assert art.mode == "RGBA"
    assert art.width > art.height
    assert art.getchannel("A").getbbox()


def test_context_crop_rejects_alpha_touching_every_crop_edge(tmp_path):
    from PIL import Image, ImageDraw

    source = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
    ImageDraw.Draw(source).rectangle((10, 10, 69, 69), fill=(255, 0, 0, 255))
    source.save(tmp_path / "pose.png")

    with pytest.raises(ValueError, match="touches every edge"):
        B.extract_equipment(
            {
                "file": "pose.png",
                "mode": "context_crop",
                "crop": [10, 10, 60, 60],
                "mask_polygon": [[10, 10], [69, 10], [69, 69], [10, 69]],
                "context_note": "invalid synthetic context",
                "rotation_degrees": 0,
            },
            tmp_path,
            tmp_path / "art.png",
        )


def test_text_only_equipment_has_no_display_art(tmp_path):
    from PIL import Image

    Image.new("RGBA", (32, 32), (255, 0, 0, 0)).save(tmp_path / "pose.png")
    assert B.extract_equipment(
        {
            "file": "pose.png",
            "mode": "text_only",
            "degraded_reason": "synthetic degraded source",
        },
        tmp_path,
        tmp_path / "not-written.png",
    ) is None
    assert not (tmp_path / "not-written.png").exists()


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


def test_callout_renderer_rejects_clipped_copy():
    callout = json.loads(json.dumps(
        MONTAGE["composition"]["callouts"]["spear"]
    ))
    callout["label_box"] = {"x": 0, "y": 0, "width": 300, "height": 120}
    callout["plate_luma"] = {"mean": 64}

    with pytest.raises(ValueError, match="exceeds its label_box"):
        C.render_callout(callout, canvas=(1280, 720))


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
    assert chain.index("split[c][m]") < chain.index(B.LEONARDO_NAME_MASK)
    assert chain.index(B.LEONARDO_NAME_MASK) < chain.index("floodfill")


def test_leonardos_enclosed_spear_gap_is_removed():
    chain = B.KEY_CHAINS["LEONARDO"]
    assert B.LEONARDO_PAPER_POCKET in chain
    assert chain.index(B.LEONARDO_PAPER_POCKET) > chain.index(
        B.LEONARDO_NAME_MASK
    )


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
    assert f"volume={RECORD['delivery']['audio_gain_db']:g}dB" in text
    assert f"-b:a {RECORD['delivery']['audio_bitrate_kbps']}k" in text
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


def test_stage_segments_add_the_wordmark_but_clean_segments_do_not():
    stage = B.stage_segment(
        RECORD,
        1,
        RECORD["timeline"]["intro_end_frame"],
        10,
        [],
        0,
    )
    assert "-i /work/bluefin-wordmark.png" in stage
    assert (
        f"scale={RECORD['wordmark']['display_width']}:-2:flags=lanczos"
        in stage
    )
    assert (
        f"overlay=x={RECORD['wordmark']['x']}:y={RECORD['wordmark']['y']}"
        in stage
    )

    clean = B.clean_segment(0, 0, 10)
    assert "bluefin-wordmark.png" not in clean
    assert "overlay=x=980:y=48" not in clean


def test_workflow_fetches_the_wordmark_only_for_stage_graphs():
    names = [
        B.card_name(i, e) for i, e in enumerate(RECORD["callout_schedule"])
    ]
    text = B.workflow(RECORD, MONTAGE, names)
    assert "$base/.work-uta-general/assets/bluefin-wordmark.png" in text
    assert text.count("-i /work/bluefin-wordmark.png") == sum(
        kind == "stage" for kind, _, _ in B.segments(RECORD)
    )


def test_layout_review_frame_composites_transparent_stills_only():
    background = Image.new("RGB", (B.CANVAS_W, B.CANVAS_H), (23, 31, 42))
    card = Image.new("RGBA", (B.CANVAS_W, B.CANVAS_H), (0, 0, 0, 0))
    ImageDraw.Draw(card).rectangle(
        (700, 1100, 1850, 1280), fill=(255, 255, 255, 220)
    )

    frame = B.layout_review_frame(
        RECORD,
        background,
        WORDMARK_IMAGE,
        cards=(card,),
    )

    assert frame.mode == "RGBA"
    assert frame.size == (B.CANVAS_W, B.CANVAS_H)
    assert frame.getpixel((0, 0))[:3] == background.getpixel((0, 0))
    assert frame.getchannel("A").getbbox()
    assert card.getchannel("A").getextrema()[0] == 0


def test_image_level_layout_gate_renders_all_26_cards_and_previews(
    monkeypatch, tmp_path
):
    def fake_extract(spec, hero_root, out_path):
        if B._art_mode(spec) == "text_only":
            return None
        art = Image.new("RGBA", (96, 64), (0, 0, 0, 0))
        ImageDraw.Draw(art).rounded_rectangle(
            (8, 8, 87, 55), radius=8, fill=(230, 240, 255, 235)
        )
        art.save(out_path)
        return art

    monkeypatch.setattr(B, "extract_equipment", fake_extract)
    day = Image.new("RGB", (B.CANVAS_W, B.CANVAS_H), (232, 240, 246))
    night = Image.new("RGB", (B.CANVAS_W, B.CANVAS_H), (18, 24, 34))
    cards_dir = tmp_path / "cards"
    rows = B.render_cards(
        RECORD,
        MONTAGE,
        LEONARDO,
        cards_dir,
        hero_root=tmp_path,
        faces=(day, night),
    )

    assert len(rows) == 26
    assert {row["item_id"] for row in rows} == set(CATALOG)
    pocket = B.pocket_box(RECORD, "bottom")
    bounds = (
        pocket[0],
        pocket[1],
        pocket[0] + pocket[2],
        pocket[1] + pocket[3],
    )
    for row in rows:
        with Image.open(row["path"]) as card:
            assert card.mode == "RGBA"
            assert card.getchannel("A").getbbox()
            assert B.fits(B.ink_bbox(card), bounds), row["item_id"]
        assert row["art_bounds"] is None or len(row["art_bounds"]) == 4

    mark = B.fit_wordmark(RECORD, WORDMARK_IMAGE)
    box = B.wordmark_box(RECORD, WORDMARK_IMAGE)
    assert mark.mode == "RGBA"
    assert mark.getchannel("A").getbbox()
    assert box[0] == (B.CANVAS_W - box[2]) // 2

    preview_paths = B.render_layout_previews(
        RECORD,
        (day, night),
        WORDMARK_IMAGE,
        tmp_path / "review",
    )
    assert [path.name for path in preview_paths] == [
        "stage-day-wordmark.png",
        "stage-night-wordmark.png",
    ]
    for path, face in zip(preview_paths, (day, night)):
        with Image.open(path) as preview:
            assert preview.mode == "RGBA"
            assert preview.getpixel((0, 0))[:3] == face.getpixel((0, 0))

    contact = B.render_contact_sheet(
        RECORD,
        MONTAGE,
        LEONARDO,
        rows,
        tmp_path / "review" / "equipment-contact-sheet.png",
    )
    assert contact.exists()
    with Image.open(contact) as sheet:
        assert sheet.mode == "RGBA"
        assert sheet.size[0] == 4 * B.CONTACT_CELL_WIDTH


def test_context_crop_items_keep_transparency_notes_and_no_sheet_art():
    for item_id, item in LEONARDO["items"].items():
        spec = item["art"]
        assert "Cha Design_LEONARDO.jpg" not in spec["file"], item_id
        if spec["mode"] == "context_crop":
            assert spec["context_note"].strip(), item_id
        assert not spec["file"].endswith(".jpg"), item_id
