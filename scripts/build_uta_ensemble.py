#!/usr/bin/env python3
"""Build the ENSEMBLE cut of General of the Dark Army.

The band plays in a window at the centre of a Bluefin stage; all four kids'
drawing animations run keyed and live around it for the body of the film; the
authored weapon callouts come and go in the pockets above and below the
window.

Two things this file exists to get right, both of which have already gone
wrong once on this video:

1. **The arithmetic.** Segment lengths are frame indices that tile the
   source's 11427 frames exactly. Summing rounded durations put 0.29 s of
   A/V drift into an earlier pass, against on-camera singing.
2. **The audio is decoded once and encoded once.** Encoding it per segment
   put 20 AAC encoder-delay junctions inside continuous music.

Each kid is keyed with *its own* previously measured chain, copied from the
manifest that produced that kid's delivered video. A seed, a threshold or a
bounding box from another drawing is a wrong number.

    python3 scripts/build_uta_ensemble.py --cards --workflow
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RECORD = REPO / "stories" / "uta-general-ensemble.json"
MONTAGE = REPO / "stories" / "uta-general-dark-army.json"
LEONARDO = REPO / "stories" / "leonardo-equipment.json"
WORK = Path.home() / "Videos" / "Wolves" / "Hero" / ".work-uta-general"

FPS_NUM, FPS_DEN = 24000, 1001
CANVAS_W, CANVAS_H = 2560, 1440

# The keying chain each kid's own delivered video was rendered with, minus the
# bed-matching tpad/hold, which the ensemble replaces with its own retime.
# floodfill's d0/d1/d2 are planar G,B,R -- d0=0:d1=255:d2=0 renders BLUE, so
# the key is colorkey=0x0000FF. The fill runs on the FULL frame before the
# tight crop, and the matte goes back onto the ORIGINAL pixels.
FILL = "s0=255:s1=255:s2=255:d0=0:d1=255:d2=0"
LEONARDO_NAME_MASK = (
    "drawbox=x=1020:y=0:w=1026:h=128:color=0x0000FF@1:t=fill"
)
LEONARDO_PAPER_POCKET = f"floodfill=x=640:y=870:{FILL}"

KEY_CHAINS = {
    "RAFI_01": (
        "crop=1986:2046:0:0,"
        "drawbox=x=980:y=0:w=1006:h=300:color=white@1:t=fill,"
        "format=rgba,split[c][m];"
        "[m]format=rgb24,"
        "lutrgb=r='if(gt(val,231),255,val)':g='if(gt(val,231),255,val)'"
        ":b='if(gt(val,231),255,val)',"
        f"floodfill=x=2:y=2:{FILL},"
        "format=rgba,colorkey=0x0000FF:0.01:0.0,alphaextract[al];"
        "[c][al]alphamerge,crop=1759:1862:71:145"
    ),
    "RAFI_02": (
        "crop=1754:2046:0:0,"
        "drawbox=x=860:y=0:w=894:h=231:color=white@1:t=fill,"
        "format=rgba,split[c][m];"
        "[m]format=rgb24,"
        "lutrgb=r='if(gt(val,247),255,val)':g='if(gt(val,247),255,val)'"
        ":b='if(gt(val,247),255,val)',"
        f"floodfill=x=2:y=2:{FILL},"
        f"floodfill=x=200:y=950:{FILL},"
        f"floodfill=x=580:y=1250:{FILL},"
        f"floodfill=x=400:y=1100:{FILL},"
        f"floodfill=x=1600:y=600:{FILL},"
        "floodfill=x=500:y=1850:s0=171:s1=171:s2=171:d0=0:d1=255:d2=0,"
        "geq="
        "r='if(between(Y,1696,1942)*between(r(X,Y),160,185)"
        "*between(g(X,Y),160,185)*between(b(X,Y),160,185),0,r(X,Y))':"
        "g='if(between(Y,1696,1942)*between(r(X,Y),160,185)"
        "*between(g(X,Y),160,185)*between(b(X,Y),160,185),0,g(X,Y))':"
        "b='if(between(Y,1696,1942)*between(r(X,Y),160,185)"
        "*between(g(X,Y),160,185)*between(b(X,Y),160,185),255,b(X,Y))',"
        "format=rgba,colorkey=0x0000FF:0.01:0.0,alphaextract[al];"
        "[c][al]alphamerge,crop=1714:1714:40:231"
    ),
    "LAKSHMI": (
        "crop=1626:2048:0:0,split=2[c][m];"
        "[c]format=rgba[orig];"
        "[m]format=gray,lut=c0='if(gt(val,247),255,val)',"
        "drawbox=x=744:y=0:w=857:h=144:color=white:t=fill,format=rgb24,"
        + ",".join(
            f"floodfill=x={x}:y={y}:{FILL}"
            for x, y in [
                (2, 0), (1623, 0), (2, 2047), (1623, 2047), (2, 2),
                (1623, 2), (2, 2045), (1623, 2045), (1172, 60),
            ]
        )
        + ",colorkey=0x0000FF:similarity=0.00001:blend=0,"
        "format=rgba,alphaextract[al];"
        "[orig][al]alphamerge,crop=1414:1861:212:106"
    ),
    "LEONARDO": (
        "crop=2046:1746:0:0,"
        "format=rgba,split[c][m];"
        f"[m]format=rgb24,{LEONARDO_NAME_MASK},"
        "lutrgb=r='if(gt(val,247),255,val)':g='if(gt(val,247),255,val)'"
        ":b='if(gt(val,247),255,val)',"
        f"floodfill=x=2:y=2:{FILL},"
        f"floodfill=x=2043:y=2:{FILL},"
        f"floodfill=x=2:y=1743:{FILL},"
        f"floodfill=x=2043:y=1743:{FILL},"
        f"{LEONARDO_PAPER_POCKET},"
        "format=rgba,colorkey=0x0000FF:0.01:0.0,alphaextract[al];"
        "[c][al]alphamerge,crop=1888:1676:41:21"
    ),
}

# Union bounding box each chain crops to, so the station height follows the
# drawing's own aspect rather than a guess.
KEY_BBOX = {
    "RAFI_01": (1759, 1862),
    "RAFI_02": (1714, 1714),
    "LAKSHMI": (1414, 1861),
    "LEONARDO": (1888, 1676),
}

FETCH_BASE = "http://192.168.1.227:8877"
RECEIVER = "http://192.168.1.227:8882"
# Retained across runs: keying does not depend on the layout.
PVC = "uta-ensemble-work"

# A wide art crop scaled to the box height eats the text column.
ART_WIDTH_SHARE = 0.32

# Frames of finished drawing cloned past the retime, to cover rounding.
TAIL_PAD = 72


def t_of(frame: int) -> float:
    return frame * FPS_DEN / FPS_NUM


def even(n: float) -> int:
    return int(round(n / 2)) * 2


def load_equipment_catalog(path: Path) -> dict[str, dict]:
    return json.loads(
        Path(path).read_text(encoding="utf-8")
    )["items"]


def load():
    return (
        json.loads(RECORD.read_text(encoding="utf-8")),
        json.loads(MONTAGE.read_text(encoding="utf-8")),
        {"items": load_equipment_catalog(LEONARDO)},
    )


def equipment_catalog(
    record: dict, montage: dict, leonardo: dict
) -> dict[str, dict]:
    """Merge the RAFI and Leonardo records without changing either source."""
    merged = {}
    for item_id, callout in montage["composition"]["callouts"].items():
        if item_id not in record["equipment_assets"]:
            raise ValueError(f"missing RAFI equipment art: {item_id}")
        merged[item_id] = {
            "copy": callout["copy"],
            "evidence": callout["source"],
            "art": record["equipment_assets"][item_id],
            "presentation": {
                "font_size": callout["font_size"],
                "description_font_size": callout.get(
                    "description_font_size"
                ),
                "usage": callout["usage"],
                "min_hold_seconds": callout.get("min_hold_seconds"),
            },
        }
    for item_id, item in leonardo["items"].items():
        if item_id in merged:
            raise ValueError(f"duplicate equipment id: {item_id}")
        merged[item_id] = item
    return merged


def normalize_callout(item_id: str, item: dict) -> dict:
    """Adapt either catalog to the renderer's measured 4K contract."""
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from tools import placeholder

    source_copy = placeholder.fill_equipment_description(item_id, item["copy"])
    presentation = item["presentation"]
    return {
        "copy": {
            "label_render": source_copy.get(
                "label_render", source_copy["label"]
            ),
            "subtitle_render": source_copy.get(
                "subtitle_render", source_copy.get("subtitle")
            ),
            "description_render": source_copy.get(
                "description_render", source_copy.get("description")
            ),
        },
        "font_size": presentation["font_size"],
        "description_font_size": presentation.get(
            "description_font_size"
        ) or round(presentation["font_size"] * 0.55),
        "usage": presentation["usage"],
        "min_hold_seconds": presentation.get("min_hold_seconds"),
    }


def _art_mode(spec):
    return spec.get("mode", "components")


def _validate_art_spec(item_id, spec):
    mode = _art_mode(spec)
    if mode not in {"components", "context_crop", "text_only"}:
        raise ValueError(f"{item_id}: unsupported equipment art mode: {mode}")
    if not spec.get("file"):
        raise ValueError(f"{item_id}: equipment art has no source file")
    if mode == "components":
        if not spec.get("component_seeds"):
            raise ValueError(f"{item_id}: components art has no seeds")
    elif mode == "context_crop":
        crop = spec.get("crop")
        polygon = spec.get("mask_polygon")
        if not isinstance(crop, list) or len(crop) != 4:
            raise ValueError(f"{item_id}: context art has no crop rectangle")
        if not isinstance(polygon, list) or len(polygon) < 3:
            raise ValueError(f"{item_id}: context art has no mask polygon")
        if not str(spec.get("context_note", "")).strip():
            raise ValueError(f"{item_id}: context art has no context note")
    else:
        if not str(spec.get("degraded_reason", "")).strip():
            raise ValueError(f"{item_id}: text-only art has no degraded reason")
        if any(
            key in spec
            for key in ("component_seeds", "crop", "mask_polygon", "rotation_degrees")
        ):
            raise ValueError(
                f"{item_id}: text-only art carries display geometry"
            )


def _visible_character_count(copy):
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from render_uta_callout import visible_character_count

    return visible_character_count(copy)


def required_hold_seconds(callout):
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from tools import readtime

    return max(
        8.0,
        _visible_character_count(callout["copy"]) / readtime.DEFAULT_CPS + 1.0,
    )


def stage_windows(record):
    return [
        (t_of(start), t_of(start + frames))
        for kind, start, frames in segments(record)
        if kind == "stage"
    ]


def validate_equipment_schedule(record, catalog, montage=None):
    """Reject missing, repeated, unreadable, or badly seated equipment cards."""
    scheduled = [entry.get("item") for entry in record["callout_schedule"]]
    if any(item_id is None for item_id in scheduled):
        raise ValueError("every equipment schedule entry must use an item id")
    if len(scheduled) != len(set(scheduled)):
        raise ValueError("equipment schedule contains a repeated item")
    if set(scheduled) != set(catalog):
        missing = sorted(set(catalog) - set(scheduled))
        extra = sorted(set(scheduled) - set(catalog))
        raise ValueError(
            f"equipment schedule/catalog mismatch: missing={missing}, extra={extra}"
        )

    normalized = {}
    for item_id, item in catalog.items():
        _validate_art_spec(item_id, item["art"])
        normalized[item_id] = normalize_callout(item_id, item)
        source_copy = item["copy"]
        render_copy = normalized[item_id]["copy"]
        if source_copy.get("description_source") == "placeholder":
            if not (render_copy.get("description_render") or "").strip():
                raise ValueError(
                    f"{item_id}: placeholder description rendered empty"
                )
        if source_copy.get("description_source") == "authored":
            if render_copy.get("description_render") != source_copy["description"]:
                raise ValueError(
                    f"{item_id}: authored description changed during normalization"
                )

    previous_end = None
    windows = stage_windows(record)
    protected = (
        (montage or {})
        .get("composition", {})
        .get("protected", [{"start_seconds": 320.0, "end_seconds": 350.0}])
    )
    for entry in sorted(
        record["callout_schedule"], key=lambda row: row["start_seconds"]
    ):
        item_id = entry["item"]
        start = float(entry["start_seconds"])
        hold = float(entry["hold_seconds"])
        end = start + hold
        if hold <= 0:
            raise ValueError(f"{item_id}: equipment hold must be positive")
        if hold + 1e-9 < required_hold_seconds(normalized[item_id]):
            raise ValueError(
                f"{item_id}: hold {hold:g}s is shorter than its readable "
                f"minimum {required_hold_seconds(normalized[item_id]):.3f}s"
            )
        minimum = normalized[item_id].get("min_hold_seconds")
        if minimum is not None and hold + 1e-9 < minimum:
            raise ValueError(
                f"{item_id}: hold {hold:g}s is shorter than its presentation "
                f"minimum {minimum:g}s"
            )
        if not any(
            stage_start - 1e-9 <= start and end <= stage_end + 1e-9
            for stage_start, stage_end in windows
        ):
            raise ValueError(f"{item_id}: card is outside a stage window")
        if previous_end is not None and start - previous_end < 1.0 - 1e-9:
            raise ValueError(
                f"{item_id}: cards need at least 1.0s between fade windows"
            )
        for passage in protected:
            passage_start = float(passage["start_seconds"])
            passage_end = float(passage["end_seconds"])
            if not (end <= passage_start + 1e-9 or start >= passage_end - 1e-9):
                raise ValueError(f"{item_id}: card touches protected passage")
        previous_end = end
    return normalized


def stations(record):
    """Station geometry, derived from each drawing's measured bounding box."""
    out = []
    for kid in record["kids"]:
        bw, bh = KEY_BBOX[kid["id"]]
        w = even(kid["width"])
        h = even(w * bh / bw)
        out.append({**kid, "scaled_width": w, "scaled_height": h})
    return out


def segments(record):
    """Whole programme as (kind, start_frame, frames), tiling 11427 exactly."""
    t = record["timeline"]
    bounds = [
        0,
        t["intro_end_frame"],
        t["protect_in_frame"],
        t["protect_out_frame"],
        t["credits_frame"],
        record["delivery"]["source_frames"],
    ]
    kinds = ["clean", "stage", "clean", "stage", "clean"]
    return [
        (kind, a, b - a)
        for kind, a, b in zip(kinds, bounds, bounds[1:])
    ]


def visible_frames(record):
    """Frames the stage is actually up -- the drawings' whole clock."""
    return sum(f for kind, _, f in segments(record) if kind == "stage")


def retime(record, kid):
    """Uniform factor mapping a 24/1 animation onto the kid span at 24000/1001."""
    span = visible_frames(record)
    n = kid.get("use_frames", kid["source_frames"])
    return span / n * (24 * FPS_DEN / FPS_NUM), n


# --------------------------------------------------------------------------
# cards


def card_name(i, entry):
    return f"card{i:02d}-{entry['item']}-{entry['pocket']}.png"


def stage_background(record):
    """The day and night faces as the stage actually composites them."""
    from PIL import Image

    hero = Path.home() / "Videos" / "Wolves" / "Hero"
    faces = []
    for key in ("day", "night"):
        im = Image.open(hero / record["stage"][key]).convert("RGB")
        scale = max(CANVAS_W / im.width, CANVAS_H / im.height)
        im = im.resize(
            (round(im.width * scale), round(im.height * scale)), Image.LANCZOS
        )
        left = (im.width - CANVAS_W) // 2
        top = (im.height - CANVAS_H) // 2
        faces.append(im.crop((left, top, left + CANVAS_W, top + CANVAS_H)))
    return faces


def plate_luma(record, faces, box, seconds):
    """Mean luma of the stage under a pocket, at the second the card is up.

    The plate here is our own background, not somebody else's frame, so this
    is arithmetic on the two wallpaper faces rather than a farm measurement --
    but the polarity still gets chosen from a number, never assumed.
    """
    from PIL import Image

    s = record["stage"]
    a, b = s["crossfade_start_seconds"], s["crossfade_end_seconds"]
    w = 1.0 if seconds <= a else 0.0 if seconds >= b else 1 - (seconds - a) / (b - a)
    day, night = faces
    blend = Image.blend(night, day, w)
    crop = blend.crop(
        (box["x"], box["y"], box["x"] + box["width"], box["y"] + box["height"])
    ).convert("L")
    px = list(crop.getdata())
    return sum(px) / len(px), w


APERTURE_MASK = "aperture-mask.png"


def render_aperture_mask(record, out_dir):
    """A rounded-corner alpha for the band aperture.

    alphamerge takes its matte from the second input's LUMA, so this is a
    white rounded rectangle on black, drawn at 4x and resampled down for an
    edge that does not stair-step at 1440p.
    """
    from PIL import Image, ImageDraw

    win = record["band_window"]
    w, h, r = win["width"], win["height"], win["corner_radius"]
    ss = 4
    big = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(big).rounded_rectangle(
        (0, 0, w * ss - 1, h * ss - 1), radius=r * ss, fill=255
    )
    mask = big.resize((w, h), Image.LANCZOS)
    out_dir.mkdir(parents=True, exist_ok=True)
    mask.save(out_dir / APERTURE_MASK)
    return mask.size


def _open_equipment_source(spec, hero_root):
    from PIL import Image

    path = Path(hero_root) / spec["file"]
    with Image.open(path) as opened:
        if opened.mode != "RGBA":
            raise ValueError(f"equipment source must be RGBA: {spec['file']}")
        source = opened.copy()
    alpha = source.getchannel("A")
    if alpha.getextrema()[0] == 255:
        raise ValueError(f"equipment source has no transparency: {spec['file']}")
    return source


def _finish_equipment_art(art, spec, out_path):
    alpha = art.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox:
        raise ValueError(f"equipment extraction is empty: {spec['file']}")
    art = art.crop(bbox)
    rotation = spec.get("rotation_degrees", 0)
    if rotation not in (0, 90, 180, 270):
        raise ValueError(f"equipment rotation must be a quarter turn: {rotation}")
    if rotation:
        art = art.rotate(rotation, expand=True)
        rotated_bbox = art.getchannel("A").getbbox()
        if not rotated_bbox:
            raise ValueError(f"equipment rotation emptied the art: {spec['file']}")
        art = art.crop(rotated_bbox)

    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        art.save(out_path)
    return art


def _extract_components(source, spec):
    from PIL import Image, ImageChops, ImageDraw

    alpha = source.getchannel("A")
    binary = alpha.point(lambda a: 255 if a > 16 else 0)
    selected = Image.new("L", source.size, 0)
    for seed in spec["component_seeds"]:
        point = tuple(seed)
        if not (
            0 <= point[0] < source.width and 0 <= point[1] < source.height
        ):
            raise ValueError(
                f"equipment seed {point} is out of bounds in {spec['file']}"
            )
        if binary.getpixel(point) == 0:
            raise ValueError(
                f"equipment seed {point} is transparent in {spec['file']}"
            )
        marked = binary.copy()
        ImageDraw.floodfill(marked, point, 128, thresh=0)
        component = marked.point(lambda a: 255 if a == 128 else 0)
        selected = ImageChops.lighter(selected, component)

    source.putalpha(ImageChops.multiply(alpha, selected))
    return source


def _extract_context_crop(source, spec):
    from PIL import Image, ImageChops, ImageDraw

    crop_x, crop_y, crop_w, crop_h = spec["crop"]
    if (
        crop_x < 0
        or crop_y < 0
        or crop_w <= 0
        or crop_h <= 0
        or crop_x + crop_w > source.width
        or crop_y + crop_h > source.height
    ):
        raise ValueError(f"context crop is out of bounds in {spec['file']}")

    for point in spec["mask_polygon"]:
        if len(point) != 2:
            raise ValueError(f"context polygon point is invalid in {spec['file']}")
        point_x, point_y = point
        if not (
            0 <= point_x < source.width
            and 0 <= point_y < source.height
            and crop_x <= point_x < crop_x + crop_w
            and crop_y <= point_y < crop_y + crop_h
        ):
            raise ValueError(
                f"context polygon point {tuple(point)} is out of bounds "
                f"in {spec['file']}"
            )

    crop = source.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))
    polygon = [
        (point_x - crop_x, point_y - crop_y)
        for point_x, point_y in spec["mask_polygon"]
    ]
    mask = Image.new("L", crop.size, 0)
    ImageDraw.Draw(mask).polygon(polygon, fill=255)
    crop.putalpha(ImageChops.multiply(crop.getchannel("A"), mask))
    bbox = crop.getchannel("A").getbbox()
    if not bbox:
        raise ValueError(f"context crop mask is empty: {spec['file']}")
    if (
        bbox[0] == 0
        and bbox[1] == 0
        and bbox[2] == crop.width
        and bbox[3] == crop.height
    ):
        raise ValueError(
            f"context crop alpha touches every edge of its crop: {spec['file']}"
        )
    return crop


def extract_equipment(spec, hero_root, out_path):
    """Extract reviewed art using the mode recorded beside the source."""
    mode = _art_mode(spec)
    _validate_art_spec(spec.get("file", "<unknown>"), spec)
    source = _open_equipment_source(spec, hero_root)
    if mode == "text_only":
        return None
    if mode == "context_crop":
        art = _extract_context_crop(source, spec)
    else:
        art = _extract_components(source, spec)
    return _finish_equipment_art(art, spec, out_path)


def audit_assets(record, montage, leonardo, hero_root):
    """Audit Leonardo sources and render their final cards without video I/O."""
    from PIL import Image

    errors = []
    root = Path(hero_root)
    catalog = equipment_catalog(record, montage, leonardo)
    pocket = dict(record["callout_pockets"]["bottom"])
    bounds = pocket.pop("bounds")
    with tempfile.TemporaryDirectory(prefix="uta-equipment-audit-") as temp:
        out_dir = Path(temp)
        for item_id, item in sorted(leonardo["items"].items()):
            spec = item["art"]
            mode = _art_mode(spec)
            source_path = root / spec["file"]
            note = (
                spec.get("context_note")
                or spec.get("degraded_reason")
                or "none recorded"
            )
            try:
                _validate_art_spec(item_id, spec)
                with Image.open(source_path) as source:
                    source_mode = source.mode
                    source_size = source.size
                if source_mode != "RGBA":
                    raise ValueError(f"source mode is {source_mode}, not RGBA")
                expected_size = spec.get("source_size")
                if expected_size and tuple(expected_size) != source_size:
                    raise ValueError(
                        f"catalog source_size {tuple(expected_size)} disagrees "
                        f"with supplied {source_size}"
                    )
                output = None
                output_path = None
                if mode != "text_only":
                    output_path = out_dir / f"{item_id}.png"
                    output = extract_equipment(
                        spec, root, output_path
                    )
                    if output is None:
                        raise ValueError("extraction returned no art")
                    final_bounds = output.getchannel("A").getbbox()
                    if not final_bounds:
                        raise ValueError("extraction returned an empty image")
                else:
                    _open_equipment_source(spec, root)
                    final_bounds = None
                callout = normalize_callout(item_id, catalog[item_id])
                image, rendered, attempts = render_card(
                    callout,
                    item,
                    pocket,
                    bounds,
                    output_path,
                    plate_mean=64,
                )
                print(
                    f"{item_id} source={spec['file']} mode={mode} "
                    f"source_dimensions={source_size[0]}x{source_size[1]} "
                    f"final_alpha_bounds={final_bounds or 'none'} "
                    f"rotation={spec.get('rotation_degrees', 'n/a')} "
                    f"card_alpha_bounds={ink_bbox(image) or 'none'} "
                    f"card_label_size={rendered['font_size']} "
                    f"card_shrinks={attempts} note={note}"
                )
            except (OSError, ValueError) as exc:
                errors.append(f"{item_id}: {exc}")
                print(f"{item_id} ERROR: {exc}", file=sys.stderr)
    return errors


def render_cards(record, montage, leonardo, out_dir):
    """One full-canvas RGBA card per scheduled appearance.

    Every card is measured after it is drawn and shrunk until its own alpha
    fits the pocket. Copy that runs out of its pocket lands on the band, and
    a card that covers the band is the one thing this layout may never do.
    """
    catalog = equipment_catalog(record, montage, leonardo)
    validate_equipment_schedule(record, catalog, montage)
    faces = stage_background(record)
    out_dir.mkdir(parents=True, exist_ok=True)
    hero_root = Path.home() / "Videos" / "Wolves" / "Hero"
    equipment_paths = {}
    for item_id, item in catalog.items():
        spec = item["art"]
        if _art_mode(spec) == "text_only":
            equipment_paths[item_id] = None
            continue
        path = out_dir / f"equipment-{item_id}.png"
        extract_equipment(spec, hero_root, path)
        equipment_paths[item_id] = path

    written = []
    for i, entry in enumerate(record["callout_schedule"]):
        item_id = entry["item"]
        item = catalog[item_id]
        callout = normalize_callout(item_id, item)
        pocket = dict(record["callout_pockets"][entry["pocket"]])
        bounds = pocket.pop("bounds")
        mean, weight = plate_luma(record, faces, pocket, entry["start_seconds"])
        art_path = (
            str(equipment_paths[item_id])
            if equipment_paths[item_id] is not None
            else None
        )
        img, rendered, attempt = render_card(
            callout,
            item,
            pocket,
            bounds,
            art_path,
            plate_mean=mean,
            plate_weight=weight,
        )
        name = card_name(i, entry)
        img.save(out_dir / name)
        written.append(
            (name, round(mean, 1), weight, rendered["font_size"], attempt)
        )
    return written


def render_card(
    callout,
    item,
    pocket,
    bounds,
    art_path,
    plate_mean,
    plate_weight=None,
):
    """Render one card with the same fit loop used by delivery rendering."""
    scale = CANVAS_W / 3840
    art_width_share = item["art"].get("art_width_share", ART_WIDTH_SHARE)
    rendered = dict(callout)
    rendered["plate_luma"] = {
        "mean": plate_mean,
        "measured_by": "stage background under the card's own second",
    }
    if plate_weight is not None:
        rendered["plate_luma"]["day_weight"] = plate_weight

    title0 = rendered["font_size"] * scale
    body0 = rendered.get("description_font_size", 0) * scale
    bbox = None
    last_overflow = None
    for attempt in range(12):
        shrink = 0.94 ** attempt
        rendered["label_box"] = pocket
        rendered["font_size"] = even(title0 * shrink)
        if body0:
            rendered["description_font_size"] = even(body0 * shrink)
        try:
            image = _render_callout(
                rendered,
                art_path=art_path,
                canvas=(CANVAS_W, CANVAS_H),
                frame_map=1920 / CANVAS_W,
                art_width_share=art_width_share,
            )
        except ValueError as exc:
            if "exceeds its label_box" in str(exc):
                last_overflow = str(exc)
                continue
            raise
        bbox = ink_bbox(image)
        if fits(bbox, bounds):
            return image, rendered, attempt
    raise ValueError(
        f"card will not fit its pocket at a readable size: "
        f"{bbox if bbox is not None else last_overflow} outside {bounds}"
    )


def _render_callout(*args, **kwargs):
    """Import the renderer lazily so catalog and audit tests stay lightweight."""
    import sys

    scripts = str(REPO / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from render_uta_callout import render_callout

    return render_callout(*args, **kwargs)


def fits(bbox, bounds):
    if bbox is None:
        return False
    x0, y0, x1, y1 = bbox
    bx0, by0, bx1, by1 = bounds
    return x0 >= bx0 and y0 >= by0 and x1 <= bx1 and y1 <= by1


def ink_bbox(img):
    """Where the card is actually drawn, ignoring its soft halo.

    The protection is a feathered glow with no edge; measuring it instead of
    the type would shrink every card to pay for a gradient nobody can see.
    """
    solid = img.split()[3].point(lambda a: 255 if a > 96 else 0)
    return solid.getbbox()


# --------------------------------------------------------------------------
# workflow


def stage_bg_chain(record, seg_start_t, dur):
    """Background chain for one stage segment, and how many inputs it takes.

    The crossfade completes inside the first stage act, so the second one is
    night only and no junction carries a background jump.
    """
    s = record["stage"]
    cover = (
        f"scale={CANVAS_W}:{CANVAS_H}:force_original_aspect_ratio=increase,"
        f"crop={CANVAS_W}:{CANVAS_H},setsar=1,format=rgba"
    )
    if seg_start_t >= s["crossfade_end_seconds"]:
        return f"[1:v]{cover}[bg]", ["night"]
    fade_st = max(0.0, s["crossfade_start_seconds"] - seg_start_t)
    fade_d = s["crossfade_end_seconds"] - s["crossfade_start_seconds"]
    return (
        f"[1:v]{cover}[day];[2:v]{cover}[night];"
        f"[day]fade=t=out:st={fade_st:.3f}:d={fade_d:.3f}:alpha=1[dayf];"
        f"[night][dayf]overlay=0:0[bg]"
    ), ["day", "night"]


def stage_segment(record, idx, start_frame, frames, cards, kid_offset):
    kids = stations(record)
    win = record["band_window"]
    t0 = t_of(start_frame)
    # the drawings' clock counts stage frames only, so a segment resumes at
    # the frame the previous stage act stopped on, not at wall clock
    kid_t = t_of(kid_offset)
    dur = t_of(frames)

    bg_chain, faces = stage_bg_chain(record, t0, dur)
    inputs = [f"-ss {t0:.6f} -i /work/source.webm"]
    for face in faces:
        inputs.append(
            f"-loop 1 -framerate {FPS_NUM}/{FPS_DEN} -i /work/bg-{face}.png"
        )
    n = 1 + len(faces)

    chain = [bg_chain]
    inputs.append(
        f"-loop 1 -framerate {FPS_NUM}/{FPS_DEN} -i /work/cards/{APERTURE_MASK}"
    )
    mask_idx = n
    n += 1
    chain.append(
        f"[0:v]{win['letterbox_crop']},"
        f"scale={win['width']}:{win['height']}:flags=lanczos,setsar=1,"
        f"format=rgba[bandpix]"
    )
    chain.append(f"[{mask_idx}:v]format=gray[amask]")
    chain.append("[bandpix][amask]alphamerge[band]")
    chain.append(f"[bg][band]overlay=x={win['x']}:y={win['y']}[stage0]")

    prev = "stage0"
    for kid in kids:
        inputs.append(f"-ss {kid_t:.6f} -i /work/{kid['id']}-keyed.mov")
        lbl = f"k{n}"
        chain.append(
            f"[{n}:v]format=rgba,setsar=1,setpts=PTS-STARTPTS,"
            f"fade=t=in:st=0:d=0.5:alpha=1,"
            f"fade=t=out:st={dur - 0.5:.3f}:d=0.5:alpha=1[{lbl}]"
        )
        chain.append(
            f"[{prev}][{lbl}]overlay=x={kid['x']}:y={kid['y']}"
            f":eof_action=repeat[s{n}]"
        )
        prev = f"s{n}"
        n += 1

    for name, start, hold in cards:
        a = start - t0
        b = a + hold
        inputs.append(
            f"-loop 1 -framerate {FPS_NUM}/{FPS_DEN} -i /work/cards/{name}"
        )
        lbl = f"c{n}"
        chain.append(
            f"[{n}:v]format=rgba,setsar=1,"
            f"fade=t=in:st={a:.3f}:d=0.5:alpha=1,"
            f"fade=t=out:st={b - 0.5:.3f}:d=0.5:alpha=1[{lbl}]"
        )
        chain.append(
            f"[{prev}][{lbl}]overlay=x=0:y=0:"
            f"enable='between(t,{a:.3f},{b:.3f})'[s{n}]"
        )
        prev = f"s{n}"
        n += 1

    chain.append(f"[{prev}]format=yuv420p[v]")
    return (
        f"ffmpeg -hide_banner -v error -y {' '.join(inputs)} \\\n"
        f'  -filter_complex "{";".join(chain)}" \\\n'
        f'  -map "[v]" -an -frames:v {frames} $V /work/s{idx:02d}.mp4\n'
        f'echo "s{idx:02d} stage {start_frame} {frames}f"'
    )


def clean_segment(idx, start_frame, frames):
    return (
        f"ffmpeg -hide_banner -v error -y -ss {t_of(start_frame):.6f} "
        f"-i /work/source.webm -frames:v {frames} \\\n"
        f'  -vf "scale={CANVAS_W}:{CANVAS_H}:flags=lanczos,setsar=1,'
        f'format=yuv420p" $V -an /work/s{idx:02d}.mp4\n'
        f'echo "s{idx:02d} clean {start_frame} {frames}f"'
    )


def key_step(record, kid):
    """Key a kid, unless the PVC already holds one from this exact command.

    Keying is 25 of this cut's 35 minutes and it does not depend on the
    layout, so a change to the stage should not pay for it again. The stamp
    is the command itself: any change to a seed, a threshold, a station size,
    a trim or the retime misses the cache by construction.
    """
    factor, use = retime(record, kid)
    span = visible_frames(record)
    pre = []
    if use != kid["source_frames"]:
        pre.append(f"trim=end_frame={use},setpts=PTS-STARTPTS")
    pre.append(f"setpts={factor:.9f}*PTS")
    pre.append(f"fps={FPS_NUM}/{FPS_DEN}")
    chain = KEY_CHAINS[kid["id"]]
    head, _, tail = chain.partition(";")
    # the retime goes in front of the measured chain, so the fill only ever
    # runs on the frames the programme actually shows
    graph = f"[0:v]{','.join(pre)},{head}"
    if tail:
        graph = f"{graph};{tail}"
    # Resampling 24/1 onto 24000/1001 can land a frame or two short, and the
    # frame an overlay shows past the end of its input is not the finished
    # drawing -- RAFI_01 rendered as a white ghost for the last second of the
    # first pass. Clone the finished frame to cover any shortfall; -frames:v
    # still cuts it to the exact span.
    post = (
        f"tpad=stop_mode=clone:stop={TAIL_PAD},"
        f"scale={kid['scaled_width']}:{kid['scaled_height']}:flags=lanczos"
    )
    if kid["flip"]:
        post += ",hflip"
    graph += f",{post},setsar=1,format=yuva420p[k]"
    cmd = (
        f"ffmpeg -hide_banner -v error -y -i /work/{kid['id']}-src.mp4 \\\n"
        f'  -filter_complex "{graph}" -map "[k]" -frames:v {span} \\\n'
        f"  -c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le "
        f"-qscale:v 11 -vendor apl0 \\\n"
        f"  /work/{kid['id']}-keyed.mov\n"
        f"ffmpeg -hide_banner -v error -y -ss 60 "
        f"-i /work/{kid['id']}-keyed.mov -frames:v 1 -pix_fmt rgba "
        f"/work/{kid['id']}-proof.png\n"
        f'echo "{kid["id"]} keyed {span}f"'
    )
    stamp = hashlib.sha256(cmd.encode()).hexdigest()[:16]
    mov = f"/work/{kid['id']}-keyed.mov"
    return (
        f"stamp={stamp}\n"
        f'if [ -f {mov} ] && [ "$(cat {mov}.stamp 2>/dev/null)" = "$stamp" ]; then\n'
        f'  echo "{kid["id"]} cached"\n'
        f"else\n"
        + "\n".join("  " + line for line in cmd.splitlines())
        + f"\n  echo $stamp > {mov}.stamp\n"
        f"fi"
    )


def container(image, cpu_req, cpu_lim, mem_req, mem_lim, script):
    body = "\n".join("            " + line for line in script.splitlines())
    return (
        f"      securityContext: {{fsGroup: 100}}\n"
        f"      container:\n"
        f"        image: {image}\n"
        f"        imagePullPolicy: IfNotPresent\n"
        f"        resources:\n"
        f"          requests: {{cpu: \"{cpu_req}\", memory: {mem_req}}}\n"
        f"          limits: {{cpu: \"{cpu_lim}\", memory: {mem_lim}}}\n"
        f"        command: [sh, -c]\n"
        f"        args:\n"
        f"          - |\n"
        f"            set -e\n"
        f"{body}\n"
        f"        volumeMounts: [{{name: work, mountPath: /work}}]\n"
    )


def workflow(record, montage, card_names):
    kids = stations(record)
    segs = segments(record)
    src = montage["source"]
    output = record["delivery"]["output"]

    fetch = ["base=" + FETCH_BASE]
    fetch.append(
        "[ -f /work/source.webm ] || curl -fsSL -o /work/source.webm "
        "$base/.work-uta-general/source.webm"
    )
    fetch.append(
        f'echo "{src["sha256"]}  /work/source.webm" | sha256sum -c -'
    )
    fetch.append(
        "curl -fsSL -o /work/INTRO_BLUEFIN.png "
        "$base/.work-uta-general/assets/INTRO_BLUEFIN.png"
    )
    for face in ("day", "night"):
        fetch.append(
            f"curl -fsSL -o /work/bg-{face}.png "
            f"$base/{record['stage'][face]}"
        )
    for kid in kids:
        fetch.append(
            f"[ -f /work/{kid['id']}-src.mp4 ] || "
            f"curl -fsSL -o /work/{kid['id']}-src.mp4 "
            f"$base/{kid['source'].replace(' ', '%20')}"
        )
    fetch.append("mkdir -p /work/cards")
    for name in card_names + [APERTURE_MASK]:
        fetch.append(
            f"curl -fsSL -o /work/cards/{name} "
            f"$base/.work-uta-general/cards/{name}"
        )

    body = []
    body.append(f'V="-r {FPS_NUM}/{FPS_DEN} -c:v libx264 -preset medium '
                f'-crf 18 -pix_fmt yuv420p"')
    body.append("")
    body.append("# 0. the intro we already made: 132 frames on black, so the")
    body.append("#    programme is the slide plus the source's own 11427 and")
    body.append("#    nothing is invented at a junction.")
    body.append(
        "ffmpeg -hide_banner -v error -y \\\n"
        f"  -f lavfi -i \"color=c=black:s={CANVAS_W}x{CANVAS_H}"
        f":r={FPS_NUM}/{FPS_DEN}\" \\\n"
        f"  -loop 1 -framerate {FPS_NUM}/{FPS_DEN} -i /work/INTRO_BLUEFIN.png \\\n"
        f'  -filter_complex "[1:v]scale={CANVAS_W}:{CANVAS_H}:flags=lanczos,'
        "format=rgba,setsar=1,fade=in:st=0.3:d=1.0:alpha=1,"
        'fade=out:st=4.7:d=0.8:alpha=1[c];[0:v][c]overlay=x=0:y=0[v]" \\\n'
        f"  -map \"[v]\" -frames:v {record['delivery']['slide_frames']} "
        "-an $V /work/s00.mp4"
    )
    body.append('echo "s00 head slide"')

    schedule = list(zip(record["callout_schedule"], card_names))
    kid_offset = 0
    for i, (kind, start, frames) in enumerate(segs, start=1):
        if kind == "clean":
            body.append(clean_segment(i, start, frames))
            continue
        a, b = t_of(start), t_of(start + frames)
        cards = [
            (name, e["start_seconds"], e["hold_seconds"])
            for e, name in schedule
            if a <= e["start_seconds"] and e["start_seconds"] + e["hold_seconds"] <= b
        ]
        body.append(stage_segment(record, i, start, frames, cards, kid_offset))
        kid_offset += frames

    names = " ".join(f"{i:02d}" for i in range(len(segs) + 1))
    body.append(
        f": > /work/list.txt\n"
        f"for i in {names}; do echo \"file '/work/s$i.mp4'\" >> /work/list.txt; done\n"
        "ffmpeg -hide_banner -v error -y -f concat -safe 0 -i /work/list.txt "
        "-c copy /work/picture.mp4"
    )
    delay = record["delivery"]["slide_frames"] * FPS_DEN / FPS_NUM * 1000
    gain = record["delivery"]["audio_gain_db"]
    bitrate = record["delivery"]["audio_bitrate_kbps"]
    body.append(
        "# ONE gapless audio pass: the music is continuous, so per-segment\n"
        "# encoding would put an AAC encoder-delay junction inside it at every\n"
        "# cut. adelay seats the film's audio behind the head slide.\n"
        "ffmpeg -hide_banner -v error -y -i /work/source.webm \\\n"
        f'  -af "adelay={delay:.1f}|{delay:.1f},volume={gain:g}dB" '
        f"-c:a aac -b:a {bitrate}k "
        "-ar 48000 -ac 2 /work/programme-audio.m4a"
    )
    body.append(
        "ffmpeg -hide_banner -v error -y -i /work/picture.mp4 "
        "-i /work/programme-audio.m4a \\\n"
        "  -map 0:v -map 1:a -c copy -movflags +faststart "
        f"/work/{output}"
    )
    body.append(
        f"out=/work/{output}\n"
        'ffprobe -v error -count_frames -show_format -show_streams -of json "$out" '
        "> /work/ens-probe.json\n"
        'ffmpeg -v error -i "$out" -f null - 2> /work/ens-decode.txt\n'
        "printf 'decode stderr bytes: %s\\n' \"$(wc -c < /work/ens-decode.txt)\"\n"
        'sha256sum "$out" > /work/ens-sha256.txt\n'
        'ffmpeg -hide_banner -nostats -y -i "$out" -af ebur128=peak=true '
        "-f null - 2> /work/ens-ebur128.txt || true\n"
        "tail -12 /work/ens-ebur128.txt\n"
        "for t in 3 20 40 80 122 160 200 240 276 305 330 360 376 408 445; do\n"
        '  ffmpeg -hide_banner -v error -y -ss $t -i "$out" -frames:v 1 '
        '-vf "scale=1280:720" -q:v 2 /work/ens-t$t.jpg\n'
        "done"
    )

    upload = [
        f"for f in /work/{output} /work/ens-probe.json /work/ens-decode.txt \\",
        "         /work/ens-sha256.txt /work/ens-ebur128.txt "
        "/work/ens-t*.jpg /work/*-proof.png; do",
        f'  curl -fsS -T "$f" {RECEIVER}/$(basename $f)',
        "done",
    ]

    key_tasks = "\n".join(
        f"          - {{name: key-{k['id'].lower().replace('_','-')}, "
        f"template: key-{k['id'].lower().replace('_','-')}, "
        "dependencies: [fetch]}"
        for k in kids
    )
    key_names = ", ".join(
        f"key-{k['id'].lower().replace('_', '-')}" for k in kids
    )

    yaml = [
        "apiVersion: argoproj.io/v1alpha1",
        "kind: Workflow",
        "metadata:",
        "  generateName: uta-ensemble-",
        "  namespace: argo",
        "spec:",
        "  entrypoint: main",
        "  podGC: {strategy: OnWorkflowSuccess}",
        "  volumes:",
        f"    - name: work",
        f"      persistentVolumeClaim: {{claimName: {PVC}}}",
        "  templates:",
        "    - name: main",
        "      dag:",
        "        tasks:",
        "          - {name: fetch, template: fetch}",
        key_tasks,
        f"          - {{name: composite, template: composite, "
        f"dependencies: [{key_names}]}}",
        "          - {name: upload, template: upload, dependencies: [composite]}",
        "    - name: fetch",
        container(
            "curlimages/curl:latest", "200m", "1", "256Mi", "512Mi",
            "\n".join(fetch),
        ).rstrip("\n"),
    ]
    for kid in kids:
        yaml.append(f"    - name: key-{kid['id'].lower().replace('_', '-')}")
        yaml.append(
            container(
                "linuxserver/ffmpeg:latest", "2", "8", "2Gi", "8Gi",
                key_step(record, kid),
            ).rstrip("\n")
        )
    yaml.append("    - name: composite")
    yaml.append(
        container(
            "linuxserver/ffmpeg:latest", "8", "24", "6Gi", "20Gi",
            "\n".join(body),
        ).rstrip("\n")
    )
    yaml.append("    - name: upload")
    yaml.append(
        container(
            "curlimages/curl:latest", "200m", "1", "256Mi", "1Gi",
            "\n".join(upload),
        ).rstrip("\n")
    )
    return "\n".join(yaml) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cards", action="store_true", help="render the callout cards")
    ap.add_argument("--workflow", action="store_true", help="emit the Argo workflow")
    ap.add_argument(
        "--audit-assets",
        action="store_true",
        help="audit supplied Leonardo RGBA display assets without video decoding",
    )
    ap.add_argument(
        "--hero-root",
        default=str(Path.home() / "Videos" / "Wolves" / "Hero"),
        help="Hero asset root used by --audit-assets",
    )
    ap.add_argument("--out-dir", default=str(WORK))
    args = ap.parse_args()

    record, montage, leonardo = load()
    if args.audit_assets:
        errors = audit_assets(record, montage, leonardo, args.hero_root)
        if errors:
            return 1
        if not args.cards and not args.workflow:
            return 0
    catalog = equipment_catalog(record, montage, leonardo)
    validate_equipment_schedule(record, catalog, montage)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    names = [
        card_name(i, e) for i, e in enumerate(record["callout_schedule"])
    ]

    if args.cards:
        print(f"{APERTURE_MASK}  {render_aperture_mask(record, out / 'cards')}")
        for name, mean, weight, size, tries in render_cards(
            record, montage, leonardo, out / "cards"
        ):
            print(
                f"{name}  plate luma {mean}  day {weight:.2f}  "
                f"label {size}px  shrinks {tries}"
            )

    if args.workflow:
        path = out / "uta-ensemble.yaml"
        path.write_text(workflow(record, montage, names))
        total = sum(f for _, _, f in segments(record))
        print(f"wrote {path}")
        print(
            f"segments tile {total} source frames + "
            f"{record['delivery']['slide_frames']} slide = "
            f"{total + record['delivery']['slide_frames']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
