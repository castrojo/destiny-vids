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

CONTACT_COLUMNS = 4
CONTACT_CELL_WIDTH = 640
CONTACT_CELL_HEIGHT = 440
CONTACT_PREVIEW_WIDTH = 600
PREFLIGHT_COLUMNS = 4
PREFLIGHT_CELL_WIDTH = 640
PREFLIGHT_CELL_HEIGHT = 420
PREFLIGHT_PREVIEW_HEIGHT = 360
WORDMARK_ASSET_PATH = Path(".work-uta-general/assets/bluefin-wordmark.png")
PREVIEW_SLICES = (
    {
        "name": "preview-day",
        "start_seconds": 46.0,
        "duration_seconds": 12.0,
        "purpose": "day stage, real band, top-rail child edge, placeholder-description callout",
    },
    {
        "name": "preview-night",
        "start_seconds": 398.0,
        "duration_seconds": 20.0,
        "purpose": "night stage, real band, top-rail child edge, longest authored night description",
    },
)


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


def _fetch_wordmark_module():
    if str(REPO / "scripts") not in sys.path:
        sys.path.insert(0, str(REPO / "scripts"))
    import fetch_wordmark

    return fetch_wordmark


def validate_wordmark_record(record):
    """Validate the ensemble's source and derived wordmark contract."""
    fetch_wordmark = _fetch_wordmark_module()
    spec = record["wordmark"]
    expected = {
        "source_url": fetch_wordmark.PINNED_WEBSITE_SOURCE_URL,
        "sha256": fetch_wordmark.PINNED_WEBSITE_SOURCE_SHA256,
        "preserve_colors": fetch_wordmark.PINNED_WEBSITE_PRESERVE_COLORS,
        "raster_width": fetch_wordmark.PINNED_WEBSITE_RASTER_WIDTH,
        "raster_size": list(fetch_wordmark.PINNED_WEBSITE_RASTER_SIZE),
        "raster_sha256": fetch_wordmark.PINNED_WEBSITE_RASTER_SHA256,
        "display_width": 600,
        "x": 980,
        "y": 48,
    }
    for key, value in expected.items():
        if spec.get(key) != value:
            raise ValueError(
                f"wordmark.{key} is not pinned: expected {value!r}, "
                f"got {spec.get(key)!r}"
            )
    return spec


def wordmark_asset_path(record, hero_root):
    spec = validate_wordmark_record(record)
    return Path(hero_root) / spec.get("asset_path", WORDMARK_ASSET_PATH)


def wordmark_stage_name(record):
    spec = validate_wordmark_record(record)
    return Path(spec.get("asset_path", WORDMARK_ASSET_PATH)).name


def validate_wordmark_asset(record, path):
    """Validate a staged wordmark and return its measured digest and size."""
    fetch_wordmark = _fetch_wordmark_module()
    spec = validate_wordmark_record(record)
    return fetch_wordmark.validate_png(
        path,
        expected_size=spec["raster_size"],
        expected_sha256=spec["raster_sha256"],
    )


def prepare_wordmark_asset(record, hero_root):
    """Fetch the pinned wordmark only when absent, then validate it strictly."""
    fetch_wordmark = _fetch_wordmark_module()
    spec = validate_wordmark_record(record)
    path = wordmark_asset_path(record, hero_root)
    if not path.exists():
        args = [
            "--source-url",
            spec["source_url"],
            "--expected-sha256",
            spec["sha256"],
            "--out",
            str(path),
            "--width",
            str(spec["raster_width"]),
            "--force",
        ]
        if spec["preserve_colors"]:
            args.append("--preserve-colors")
        if fetch_wordmark.main(args) != 0:
            raise ValueError("fetch_wordmark failed to create the pinned PNG")
    return validate_wordmark_asset(record, path)


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
            "source_character": "RAFI",
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
        merged[item_id] = {**item, "source_character": "LEONARDO"}
    return merged


def normalize_callout(item_id: str, item: dict) -> dict:
    """Adapt either catalog to the renderer's measured 4K contract."""
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from tools import placeholder

    source_copy = placeholder.fill_equipment_description(item_id, item["copy"])
    presentation = item["presentation"]
    description = source_copy.get(
        "description_render", source_copy.get("description")
    )
    if source_copy.get("description_source") == placeholder.MARKER and description:
        description = f"[PLACEHOLDER] {description}"
    return {
        "copy": {
            "label_render": source_copy.get(
                "label_render", source_copy["label"]
            ),
            "subtitle_render": source_copy.get(
                "subtitle_render", source_copy.get("subtitle")
            ),
            "description_render": description,
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


def visible_offset_for_source_frame(record, source_frame: int) -> int:
    """Return the drawing-clock frame at a source frame in a stage segment."""
    offset = 0
    for kind, start, frames in segments(record):
        if kind == "stage":
            if start <= source_frame < start + frames:
                return offset + source_frame - start
            offset += frames
    raise ValueError(
        f"source frame {source_frame} is not inside a stage segment"
    )


def scheduled_cards(record, card_names, start_seconds, duration_seconds):
    """Return cards wholly contained in a stage slice."""
    end_seconds = start_seconds + duration_seconds
    return [
        (name, entry["start_seconds"], entry["hold_seconds"])
        for entry, name in zip(record["callout_schedule"], card_names)
        if (
            start_seconds <= entry["start_seconds"]
            and entry["start_seconds"] + entry["hold_seconds"] <= end_seconds
        )
    ]


def review_frame_plan(record):
    """Build the exact programme-frame review plan used by Argo extraction."""
    rows = []

    def add(label, source_seconds, kind, item=None):
        source_frame = round(source_seconds * FPS_NUM / FPS_DEN)
        rows.append(
            {
                "label": label,
                "kind": kind,
                "item": item or "",
                "source_seconds": source_seconds,
                "source_frame": source_frame,
                "programme_frame": (
                    record["delivery"]["slide_frames"] + source_frame
                ),
                "programme_pts": (
                    record["delivery"]["slide_frames"] + source_frame
                ) * FPS_DEN,
            }
        )

    add("intro-logo", 3.0, "intro")
    add("intro-title", 14.0, "intro")
    add("wordmark-day", 42.0, "wordmark")
    add("wordmark-transition-mid", 217.5, "wordmark")
    add("wordmark-night", 402.0, "wordmark")
    for index, entry in enumerate(record["callout_schedule"]):
        add(
            f"callout-{index:02d}-{entry['item']}",
            entry["start_seconds"] + entry["hold_seconds"] / 2,
            "callout",
            entry["item"],
        )
    add("protected-start", 320.2, "protected")
    add("protected-mid", 335.0, "protected")
    add("protected-end", 349.8, "protected")
    add("credits-start", 458.0, "credits")
    add("credits-mid", 466.0, "credits")
    add("cta", 445.0, "cta")
    add("ending", 474.0, "ending")

    rows.sort(key=lambda row: row["programme_frame"])
    frames = [row["programme_frame"] for row in rows]
    if len(frames) != len(set(frames)):
        raise ValueError("review frame plan contains duplicate programme frames")
    return rows


def review_plan_tsv(plan):
    lines = [
        "label\tkind\titem\tsource_seconds\tsource_frame\tprogramme_frame\tprogramme_pts\tprogramme_seconds"
    ]
    for row in plan:
        programme_seconds = row["programme_frame"] * FPS_DEN / FPS_NUM
        lines.append(
            "\t".join(
                [
                    row["label"],
                    row["kind"],
                    row["item"],
                    f"{row['source_seconds']:.6f}",
                    str(row["source_frame"]),
                    str(row["programme_frame"]),
                    str(row["programme_pts"]),
                    f"{programme_seconds:.6f}",
                ]
            )
        )
    return "\n".join(lines) + "\n"


def validate_equipment_schedule(record, catalog, montage=None):
    """Reject missing, repeated, unreadable, or badly seated equipment cards."""
    for entry in record["callout_schedule"]:
        if entry.get("pocket") != "bottom":
            raise ValueError(
                f"{entry.get('item', '<missing>')}: equipment cards must use "
                "the bottom pocket"
            )

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


def band_box(record):
    win = record["band_window"]
    return win["x"], win["y"], win["width"], win["height"]


def station_box(kid):
    return kid["x"], kid["y"], kid["scaled_width"], kid["scaled_height"]


def pocket_box(record, pocket):
    bounds = record["callout_pockets"][pocket]["bounds"]
    x0, y0, x1, y1 = bounds
    return x0, y0, x1 - x0, y1 - y0


def fit_wordmark(record, wordmark):
    """Return the pinned mark scaled to its recorded display width."""
    from PIL import Image

    mark = wordmark.convert("RGBA")
    bbox = mark.getchannel("A").getbbox()
    if not bbox:
        raise ValueError("wordmark has no visible alpha")
    mark = mark.crop(bbox)
    width = int(record["wordmark"]["display_width"])
    if width <= 0:
        raise ValueError("wordmark display_width must be positive")
    height = max(1, round(mark.height * width / mark.width))
    return mark.resize((width, height), Image.Resampling.LANCZOS)


def wordmark_box(record, wordmark):
    mark = fit_wordmark(record, wordmark)
    spec = record["wordmark"]
    return spec["x"], spec["y"], mark.width, mark.height


def layout_review_frame(record, background, wordmark, cards=()):
    """Composite only supplied RGBA stills onto a still background."""
    frame = background.convert("RGBA")
    if frame.size != (CANVAS_W, CANVAS_H):
        raise ValueError(
            f"layout review background must be {CANVAS_W}x{CANVAS_H}, "
            f"got {frame.size}"
        )
    mark = fit_wordmark(record, wordmark)
    spec = record["wordmark"]
    frame.alpha_composite(mark, (spec["x"], spec["y"]))
    for card in cards:
        if card.mode != "RGBA":
            raise ValueError("layout review cards must be RGBA")
        if card.size != frame.size:
            raise ValueError("layout review cards must match the canvas")
        alpha = card.getchannel("A")
        if alpha.getextrema()[0] == 255 and alpha.getbbox() == (
            0,
            0,
            *frame.size,
        ):
            raise ValueError("layout review card is an opaque full-frame overlay")
        frame.alpha_composite(card)
    return frame


def card_name(i, entry):
    return f"card{i:02d}-{entry['item']}-{entry['pocket']}.png"


def stage_background(record, hero_root=None):
    """The day and night faces as the stage actually composites them."""
    from PIL import Image

    hero = Path(hero_root) if hero_root is not None else (
        Path.home() / "Videos" / "Wolves" / "Hero"
    )
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
    try:
        wordmark = validate_wordmark_asset(
            record,
            wordmark_asset_path(record, root),
        )
        print(
            f"wordmark source={record['wordmark']['source_url']} "
            f"dimensions={wordmark['size'][0]}x{wordmark['size'][1]} "
            f"sha256={wordmark['sha256']}"
        )
    except (OSError, ValueError) as exc:
        errors.append(f"wordmark: {exc}")
        print(f"wordmark ERROR: {exc}", file=sys.stderr)

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


def render_cards(
    record,
    montage,
    leonardo,
    out_dir,
    *,
    hero_root=None,
    faces=None,
):
    """One full-canvas RGBA card per scheduled appearance.

    Every card is measured after it is drawn and shrunk until its own alpha
    fits the pocket. Copy that runs out of its pocket lands on the band, and
    a card that covers the band is the one thing this layout may never do.
    """
    catalog = equipment_catalog(record, montage, leonardo)
    validate_equipment_schedule(record, catalog, montage)
    hero_root = Path(hero_root) if hero_root is not None else (
        Path.home() / "Videos" / "Wolves" / "Hero"
    )
    faces = stage_background(record, hero_root) if faces is None else faces
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale_card in out_dir.glob("card*.png"):
        stale_card.unlink()
    equipment_paths = {}
    equipment_bounds = {}
    for item_id, item in catalog.items():
        spec = item["art"]
        if _art_mode(spec) == "text_only":
            equipment_paths[item_id] = None
            equipment_bounds[item_id] = None
            continue
        path = out_dir / f"equipment-{item_id}.png"
        art = extract_equipment(spec, hero_root, path)
        if art is None:
            raise ValueError(f"{item_id}: art extraction returned no image")
        equipment_paths[item_id] = path
        equipment_bounds[item_id] = art.getchannel("A").getbbox()

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
        path = out_dir / name
        img.save(path)
        written.append(
            {
                "name": name,
                "item_id": item_id,
                "source_character": item["source_character"],
                "description_source": item["copy"].get(
                    "description_source",
                    "authored" if item["copy"].get("description") else "placeholder",
                ),
                "hold_seconds": entry["hold_seconds"],
                "art_bounds": equipment_bounds[item_id],
                "path": path,
                "plate_mean": round(mean, 1),
                "day_weight": weight,
                "font_size": rendered["font_size"],
                "shrinks": attempt,
            }
        )
    return written


def render_layout_previews(record, faces, wordmark, out_dir, cards=()):
    """Write day/night stills for the local layout preflight."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for theme, face in zip(("day", "night"), faces):
        path = out_dir / f"stage-{theme}-wordmark.png"
        layout_review_frame(record, face, wordmark, cards=cards).save(path)
        paths.append(path)
    return paths


def render_card_preflight_sheet(record, face, wordmark, rows, out_path, theme):
    """Render one actual day/night stage composite per card into a sheet."""
    from PIL import Image, ImageDraw, ImageFont

    if not rows:
        raise ValueError("card preflight sheet requires rendered cards")
    title_height = 52
    sheet_height = title_height + (
        (len(rows) + PREFLIGHT_COLUMNS - 1) // PREFLIGHT_COLUMNS
    ) * PREFLIGHT_CELL_HEIGHT
    sheet = Image.new(
        "RGBA",
        (PREFLIGHT_COLUMNS * PREFLIGHT_CELL_WIDTH, sheet_height),
        (18, 23, 31, 255),
    )
    draw = ImageDraw.Draw(sheet)
    title_font = ImageFont.truetype(
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", 24
    )
    meta_font = ImageFont.truetype(
        "/usr/share/fonts/dejavu/DejaVuSans.ttf", 14
    )
    draw.text(
        (18, 14),
        f"GENERAL OF THE DARK ARMY - {theme.upper()} PER-CARD PREFLIGHT "
        f"({len(rows)})",
        font=title_font,
        fill=(240, 244, 248, 255),
    )

    for index, row in enumerate(rows):
        col = index % PREFLIGHT_COLUMNS
        grid_row = index // PREFLIGHT_COLUMNS
        x = col * PREFLIGHT_CELL_WIDTH + 20
        y = title_height + grid_row * PREFLIGHT_CELL_HEIGHT + 10
        with Image.open(row["path"]) as opened:
            card = opened.convert("RGBA").copy()
        composite = layout_review_frame(
            record,
            face,
            wordmark,
            cards=(card,),
        )
        thumb = composite.resize(
            (PREFLIGHT_CELL_WIDTH - 40, PREFLIGHT_PREVIEW_HEIGHT),
            Image.Resampling.LANCZOS,
        )
        sheet.alpha_composite(thumb, (x, y))
        metadata = (
            f'{row["item_id"]} | {row["source_character"]} | '
            f'desc={row["description_source"]} | '
            f'hold={row["hold_seconds"]:g}s'
        )
        draw.text(
            (x, y + PREFLIGHT_PREVIEW_HEIGHT + 6),
            metadata,
            font=meta_font,
            fill=(226, 232, 240, 255),
        )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    return out_path


def render_card_preflight_sheets(record, faces, wordmark, rows, out_dir):
    """Write the day and night per-card still-image review sheets."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for theme, face in zip(("day", "night"), faces):
        paths.append(
            render_card_preflight_sheet(
                record,
                face,
                wordmark,
                rows,
                out_dir / f"stage-{theme}-cards.png",
                theme,
            )
        )
    return paths


def render_contact_sheet(record, montage, leonardo, rows, out_path):
    """Lay out every catalog item and its final card in catalog order."""
    from PIL import Image, ImageDraw, ImageFont

    catalog = equipment_catalog(record, montage, leonardo)
    if len(rows) != len(catalog) or {row["item_id"] for row in rows} != set(catalog):
        raise ValueError("contact sheet requires exactly one card per catalog item")
    by_item = {row["item_id"]: row for row in rows}
    ordered = [by_item[item_id] for item_id in catalog]

    title_height = 48
    preview_height = round(
        CONTACT_PREVIEW_WIDTH * CANVAS_H / CANVAS_W
    )
    sheet_height = title_height + (
        (len(ordered) + CONTACT_COLUMNS - 1) // CONTACT_COLUMNS
    ) * CONTACT_CELL_HEIGHT
    sheet = Image.new(
        "RGBA",
        (CONTACT_COLUMNS * CONTACT_CELL_WIDTH, sheet_height),
        (18, 23, 31, 255),
    )
    draw = ImageDraw.Draw(sheet)
    title_font = ImageFont.truetype(
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", 24
    )
    meta_font = ImageFont.truetype(
        "/usr/share/fonts/dejavu/DejaVuSans.ttf", 15
    )
    draw.text(
        (18, 12),
        "GENERAL OF THE DARK ARMY - COMPLETE EQUIPMENT CONTACT SHEET (26)",
        font=title_font,
        fill=(240, 244, 248, 255),
    )

    for index, row in enumerate(ordered):
        col = index % CONTACT_COLUMNS
        grid_row = index // CONTACT_COLUMNS
        x = col * CONTACT_CELL_WIDTH + 20
        y = title_height + grid_row * CONTACT_CELL_HEIGHT + 12
        panel = Image.new(
            "RGBA",
            (CONTACT_PREVIEW_WIDTH, preview_height),
            (42, 50, 62, 255),
        )
        with Image.open(row["path"]) as card:
            thumb = card.convert("RGBA").resize(
                (CONTACT_PREVIEW_WIDTH, preview_height),
                Image.Resampling.LANCZOS,
            )
        panel.alpha_composite(thumb)
        sheet.alpha_composite(panel, (x, y))

        art_bounds = row["art_bounds"] or "none"
        metadata = (
            f'{row["item_id"]} | {row["source_character"]} | '
            f'desc={row["description_source"]} | '
            f'hold={row["hold_seconds"]:g}s'
        )
        draw.text(
            (x, y + preview_height + 8),
            metadata,
            font=meta_font,
            fill=(226, 232, 240, 255),
        )
        draw.text(
            (x, y + preview_height + 25),
            f"art_alpha={art_bounds}",
            font=meta_font,
            fill=(190, 200, 214, 255),
        )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    return out_path


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


def stage_segment(
    record,
    idx,
    start_frame,
    frames,
    cards,
    kid_offset,
    output_name=None,
):
    kids = stations(record)
    win = record["band_window"]
    wordmark = record["wordmark"]
    wordmark_name = wordmark_stage_name(record)
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

    inputs.append(
        f"-loop 1 -framerate {FPS_NUM}/{FPS_DEN} -i /work/{wordmark_name}"
    )
    wordmark_idx = n
    n += 1
    chain.append(
        f"[{wordmark_idx}:v]format=rgba,"
        f"scale={wordmark['display_width']}:-2:flags=lanczos,setsar=1[mark]"
    )

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

    chain.append(
        f"[{prev}][mark]overlay=x={wordmark['x']}:y={wordmark['y']}:"
        f"eof_action=repeat[wordmarked]"
    )
    prev = "wordmarked"

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
    output_name = output_name or f"s{idx:02d}"
    return (
        f"ffmpeg -hide_banner -v error -y {' '.join(inputs)} \\\n"
        f'  -filter_complex "{";".join(chain)}" \\\n'
        f'  -map "[v]" -an -frames:v {frames} $V /work/{output_name}.mp4\n'
        f'echo "{output_name} stage {start_frame} {frames}f"'
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


def workflow(record, montage, card_names, wordmark_sha256=None):
    kids = stations(record)
    segs = segments(record)
    src = montage["source"]
    output = record["delivery"]["output"]
    plan = review_frame_plan(record)
    wordmark = validate_wordmark_record(record)
    wordmark_sha256 = wordmark_sha256 or wordmark.get("raster_sha256")
    wordmark_name = Path(
        wordmark.get("asset_path", WORDMARK_ASSET_PATH)
    ).name
    wordmark_source = wordmark.get("asset_path", str(WORDMARK_ASSET_PATH))
    if not wordmark_sha256:
        raise ValueError("wordmark raster sha256 is required for workflow generation")
    frame_expr = "+".join(
        f"eq(pts\\,{row['programme_pts']})" for row in plan
    )
    review_paths = " ".join(f"/work/{row['label']}.jpg" for row in plan)

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
    fetch.append(
        f"curl -fsSL -o /work/{wordmark_name} "
        f"$base/{wordmark_source}"
    )
    fetch.append(
        f'echo "{wordmark_sha256}  /work/{wordmark_name}" | sha256sum -c -'
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

    body = [
        f'V="-r {FPS_NUM}/{FPS_DEN} -c:v libx264 -preset medium '
        f'-crf 18 -pix_fmt yuv420p"',
        'MODE="{{workflow.parameters.render_mode}}"',
        "",
        "# Preview mode uses the same stage graph as the full render but only",
        "# two representative source slices. It never substitutes a mock.",
        'if [ "$MODE" = "preview" ]; then',
    ]
    for preview in PREVIEW_SLICES:
        start_frame = round(
            preview["start_seconds"] * FPS_NUM / FPS_DEN
        )
        frames = round(preview["duration_seconds"] * FPS_NUM / FPS_DEN)
        kid_offset = visible_offset_for_source_frame(record, start_frame)
        cards = scheduled_cards(
            record,
            card_names,
            preview["start_seconds"],
            preview["duration_seconds"],
        )
        command = stage_segment(
            record,
            90 if preview["name"] == "preview-day" else 91,
            start_frame,
            frames,
            cards,
            kid_offset,
            output_name=preview["name"],
        )
        body.extend(f"  {line}" for line in command.splitlines())
        sample_indices = [0, frames // 2, frames - 1]
        preview_expr = "+".join(
            f"eq(n\\,{index})" for index in sample_indices
        )
        body.append(
            f'  ffmpeg -xerror -hide_banner -v error -y -i '
            f'/work/{preview["name"]}.mp4 -vf '
            f'"select=\'{preview_expr}\',scale=1280:720" '
            f"-fps_mode vfr -frames:v 3 -q:v 2 "
            f'/work/{preview["name"]}-frame-%02d.jpg'
        )
        body.append(
            f'  ffmpeg -xerror -v error -i /work/{preview["name"]}.mp4 '
            f'-f null - 2> /work/{preview["name"]}-decode.txt'
        )
    body.extend(
        [
            "  exit 0",
            "fi",
            "",
            "# 0. the intro we already made: 132 frames on black, so the",
            "#    programme is the slide plus the source's own 11427 and",
            "#    nothing is invented at a junction.",
            "ffmpeg -hide_banner -v error -y \\\n"
            f"  -f lavfi -i \"color=c=black:s={CANVAS_W}x{CANVAS_H}"
            f":r={FPS_NUM}/{FPS_DEN}\" \\\n"
            f"  -loop 1 -framerate {FPS_NUM}/{FPS_DEN} -i /work/INTRO_BLUEFIN.png \\\n"
            f'  -filter_complex "[1:v]scale={CANVAS_W}:{CANVAS_H}:flags=lanczos,'
            "format=rgba,setsar=1,fade=in:st=0.3:d=1.0:alpha=1,"
            'fade=out:st=4.7:d=0.8:alpha=1[c];[0:v][c]overlay=x=0:y=0[v]" \\\n'
            f"  -map \"[v]\" -frames:v {record['delivery']['slide_frames']} "
            "-an $V /work/s00.mp4",
            'echo "s00 head slide"',
        ]
    )

    kid_offset = 0
    for i, (kind, start, frames) in enumerate(segs, start=1):
        if kind == "clean":
            body.append(clean_segment(i, start, frames))
            continue
        cards = scheduled_cards(
            record,
            card_names,
            t_of(start),
            t_of(frames),
        )
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
        'ffmpeg -xerror -v error -i "$out" -f null - 2> /work/ens-decode.txt\n'
        "printf 'decode stderr bytes: %s\\n' \"$(wc -c < /work/ens-decode.txt)\"\n"
        'sha256sum "$out" > /work/ens-sha256.txt\n'
        'ffmpeg -hide_banner -nostats -y -i "$out" -af ebur128=peak=true '
        "-f null - 2> /work/ens-ebur128.txt\n"
        "tail -12 /work/ens-ebur128.txt\n"
        "cat > /work/frame-plan.tsv <<'EOF'\n"
        f"{review_plan_tsv(plan)}"
        "EOF\n"
        "sed -i 's/^[[:space:]]*//' /work/frame-plan.tsv\n"
        f'ffmpeg -hide_banner -v error -y -i "$out" -vf '
        f'"select=\'{frame_expr}\',scale=1280:720" -fps_mode vfr '
        f"-frames:v {len(plan)} -q:v 2 /work/review-%03d.jpg\n"
        "i=1\n"
        "tail -n +2 /work/frame-plan.tsv | cut -f1 | while IFS= "
        "read -r label; do\n"
        '  mv "/work/review-$(printf \'%03d\' "$i").jpg" "/work/$label.jpg"\n'
        "  i=$((i + 1))\n"
        "done\n"
        f"sha256sum {review_paths} > /work/review-sha256.txt\n"
        ": > /work/ens-gates.txt\n"
        "printf 'render_mode=full\\n' >> /work/ens-gates.txt\n"
        "printf 'expected_frames="
        f"{record['delivery']['programme_frames']}\\n' >> /work/ens-gates.txt\n"
        "v_frames=$(ffprobe -v error -select_streams v:0 -count_frames "
        "-show_entries stream=nb_read_frames -of default=nw=1:nk=1 \"$out\")\n"
        "printf 'video_frames=%s\\n' \"$v_frames\" >> /work/ens-gates.txt\n"
        f'[ "$v_frames" = "{record["delivery"]["programme_frames"]}" ]\n'
        "stream_types=$(ffprobe -v error -show_entries stream=codec_type "
        "-of csv=p=0 \"$out\" | tr '\\n' ' ')\n"
        "printf 'stream_types=%s\\n' \"$stream_types\" >> /work/ens-gates.txt\n"
        '[ "$(printf "%s" "$stream_types" | wc -w | tr -d " ")" = "2" ]\n'
        '[ "$(printf "%s" "$stream_types" | grep -c "video")" = "1" ]\n'
        '[ "$(printf "%s" "$stream_types" | grep -c "audio")" = "1" ]\n'
        "v_meta=$(ffprobe -v error -select_streams v:0 "
        "-show_entries stream=codec_name,width,height,r_frame_rate "
        "-of default=nw=1 \"$out\")\n"
        "printf '%s\\n' \"$v_meta\" >> /work/ens-gates.txt\n"
        'printf "%s\\n" "$v_meta" | grep -q "codec_name=h264"\n'
        f'printf "%s\\n" "$v_meta" | grep -q "width={CANVAS_W}"\n'
        f'printf "%s\\n" "$v_meta" | grep -q "height={CANVAS_H}"\n'
        f'printf "%s\\n" "$v_meta" | grep -q "r_frame_rate={FPS_NUM}/{FPS_DEN}"\n'
        "a_meta=$(ffprobe -v error -select_streams a:0 "
        "-show_entries stream=codec_name,sample_rate,channels,bit_rate "
        "-of default=nw=1 \"$out\")\n"
        "printf '%s\\n' \"$a_meta\" >> /work/ens-gates.txt\n"
        'printf "%s\\n" "$a_meta" | grep -q "codec_name=aac"\n'
        'printf "%s\\n" "$a_meta" | grep -q "sample_rate=48000"\n'
        'printf "%s\\n" "$a_meta" | grep -q "channels=2"\n'
        "a_bitrate=$(printf '%s\\n' \"$a_meta\" | "
        "sed -n 's/^bit_rate=//p')\n"
        "printf 'audio_bitrate_target=%sk\\naudio_bitrate_actual=%s\\n' "
        f'"{bitrate}" "$a_bitrate" >> /work/ens-gates.txt\n'
        f"awk -v actual=\"$a_bitrate\" -v target=\"{bitrate}000\" "
        "'BEGIN { if (actual < target * 0.90 || actual > target * 1.05) exit 1 }'\n"
        "duration=$(ffprobe -v error -show_entries format=duration "
        "-of default=nw=1:nk=1 \"$out\")\n"
        f'expected_duration=$(awk "BEGIN {{printf \\"%.9f\\", '
        f'{record["delivery"]["programme_frames"]}*{FPS_DEN}/{FPS_NUM}}}")\n'
        "printf 'duration=%s\\nexpected_duration=%s\\n' \"$duration\" "
        "\"$expected_duration\" >> /work/ens-gates.txt\n"
        "awk -v actual=\"$duration\" -v expected=\"$expected_duration\" "
        "'BEGIN { if (actual < expected - 0.05 || actual > expected + 0.05) exit 1 }'\n"
        f"printf 'audio_policy=static_gain={gain:g}dB; no_normalization; no_eq\\n' "
        ">> /work/ens-gates.txt\n"
        "printf 'all_gates=PASS\\n' >> /work/ens-gates.txt"
    )

    preview_upload_paths = " ".join(
        [
            f"/work/{preview['name']}.mp4"
            for preview in PREVIEW_SLICES
        ]
        + [
            f"/work/{preview['name']}-decode.txt"
            for preview in PREVIEW_SLICES
        ]
        + [
            f"/work/{preview['name']}-frame-{index:02d}.jpg"
            for preview in PREVIEW_SLICES
            for index in range(1, 4)
        ]
    )
    upload = [
        'MODE="{{workflow.parameters.render_mode}}"',
        'if [ "$MODE" = "preview" ]; then',
        f"  for f in {preview_upload_paths}; do",
        f'    curl -fsS -T "$f" {RECEIVER}/$(basename $f)',
        "  done",
        "else",
        f"  for f in /work/{output} /work/ens-probe.json /work/ens-decode.txt \\",
        "           /work/ens-sha256.txt /work/ens-ebur128.txt "
        "/work/ens-gates.txt /work/frame-plan.tsv "
        f"/work/review-sha256.txt {review_paths} /work/ens-t*.jpg "
        "/work/*-proof.png; do",
        f'    curl -fsS -T "$f" {RECEIVER}/$(basename $f)',
        "  done",
        "fi",
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
        "  arguments:",
        "    parameters:",
        "      - name: render_mode",
        "        value: full",
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
        "--contact-sheet",
        action="store_true",
        help="render the complete equipment contact sheet and still previews",
    )
    ap.add_argument(
        "--prepare-wordmark",
        action="store_true",
        help="fetch and validate the pinned staged wordmark PNG",
    )
    ap.add_argument(
        "--hero-root",
        default=str(Path.home() / "Videos" / "Wolves" / "Hero"),
        help="Hero asset root used by asset audits and still generation",
    )
    ap.add_argument("--out-dir", default=str(WORK))
    args = ap.parse_args()

    record, montage, leonardo = load()
    wordmark_info = None
    if args.prepare_wordmark or args.cards or args.contact_sheet or args.workflow:
        try:
            wordmark_info = prepare_wordmark_asset(record, args.hero_root)
            print(
                f"wordmark {wordmark_info['size'][0]}x{wordmark_info['size'][1]} "
                f"sha256={wordmark_info['sha256']}"
            )
        except (OSError, ValueError) as exc:
            print(f"wordmark ERROR: {exc}", file=sys.stderr)
            return 1

    if args.audit_assets:
        errors = audit_assets(record, montage, leonardo, args.hero_root)
        if errors:
            return 1
        if not (
            args.cards
            or args.contact_sheet
            or args.workflow
            or args.prepare_wordmark
        ):
            return 0
    if args.prepare_wordmark and not (
        args.cards or args.contact_sheet or args.workflow
    ):
        return 0

    catalog = equipment_catalog(record, montage, leonardo)
    validate_equipment_schedule(record, catalog, montage)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    names = [
        card_name(i, e) for i, e in enumerate(record["callout_schedule"])
    ]

    rows = None
    if args.cards or args.contact_sheet:
        print(f"{APERTURE_MASK}  {render_aperture_mask(record, out / 'cards')}")
        rows = render_cards(
            record,
            montage,
            leonardo,
            out / "cards",
            hero_root=args.hero_root,
        )
        for row in rows:
            print(
                f"{row['name']}  plate luma {row['plate_mean']}  "
                f"day {row['day_weight']:.2f}  label {row['font_size']}px  "
                f"shrinks {row['shrinks']}"
            )
        from PIL import Image

        hero_root = Path(args.hero_root)
        wordmark_path = wordmark_asset_path(record, hero_root)
        with Image.open(wordmark_path) as opened:
            wordmark = opened.convert("RGBA").copy()
            faces = stage_background(record, hero_root)
            previews = render_layout_previews(
                record,
                faces,
                wordmark,
                out / "review",
            )
            preflight = render_card_preflight_sheets(
                record,
                faces,
                wordmark,
                rows,
                out / "review",
            )
        for path in previews:
            print(f"wrote {path}")
        for path in preflight:
            print(f"wrote {path}")
        if args.contact_sheet:
            path = render_contact_sheet(
                record,
                montage,
                leonardo,
                rows,
                out / "review" / "equipment-contact-sheet.png",
            )
            print(f"wrote {path}")

    if args.workflow:
        path = out / "uta-ensemble.yaml"
        path.write_text(
            workflow(
                record,
                montage,
                names,
                wordmark_sha256=wordmark_info["sha256"],
            )
        )
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
