#!/usr/bin/env python3
"""Render a weapon/component callout as a 4K transparent RGBA overlay.

The design sheets are 6447x9410 print art: their type is unreadable once
scaled into a 2048-wide video frame, which is why the presentation is
reconstructed rather than cropped. The *wording* still comes from the record
(`copy.*_render`, which `validate_callout_copy` has already proven is the
sheet's own wording plus recorded corrections).

Legibility over a light misty plate comes from a feathered halo behind the
glyphs, never a filled rectangle -- the owner rejected pasted boxes, and a
soft glow keeps the source frame visible through the negative space it sits
in.

    python3 scripts/render_uta_callout.py spear --out /tmp/spear.png
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO = Path(__file__).resolve().parents[1]
EDIT = REPO / "stories" / "uta-general-dark-army.json"

BOLD = "/usr/share/fonts/dejavu/DejaVuSansMono-Bold.ttf"
BOOK = "/usr/share/fonts/dejavu/DejaVuSansMono.ttf"

# Type is authored in 4K-canvas pixels but READ in the delivered frame, so the
# sizes that matter are the mapped ones. docs/skills/plates/SKILL.md sets the
# house band for body copy over picture at 19-28 px on a 1080p frame
# (tools/plate.py CHAT_FS_TEXT_MIN/MAX); a dedicated readable hold sits at the
# top of it. 3840 -> 2048 is a 0.533 map, so 4K sizes are the frame size
# divided by that.
CANVAS_TO_FRAME = 2048 / 3840
BODY_MIN_FRAME_PX = 19
BODY_MAX_FRAME_PX = 30

# Polarity is measured, not guessed. The W4 plate looks like bright mist and
# is actually YAVG 92.9 (max 153) -- laying dark type on a light core there
# would have built exactly the bright pasted panel the owner rejected. Type
# goes light on a dark protection over a dark plate, and dark on a light
# protection over a bright one.
LUMA_MIDPOINT = 128
INK_ON_DARK = (240, 244, 248, 255)
PROTECT_ON_DARK = (10, 12, 15, 255)
INK_ON_LIGHT = (24, 28, 33, 255)
PROTECT_ON_LIGHT = (247, 249, 251, 255)


def _font(path, size):
    return ImageFont.truetype(path, size)


def _tracked(draw, xy, text, font, fill, tracking=0):
    """Draw with letter spacing; the sheet sets its display type wide."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking
    return x


def _tracked_width(draw, text, font, tracking=0):
    if not text:
        return 0
    return sum(
        draw.textlength(c, font=font) for c in text
    ) + tracking * (len(text) - 1)


def _wrap(draw, text, font, max_width, tracking=0):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if _tracked_width(draw, trial, font, tracking) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_callout(callout, art_path=None, canvas=(3840, 2160)):
    copy = callout["copy"]
    box = callout["label_box"]
    card = Image.new("RGBA", canvas, (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)

    title_size = callout["font_size"]
    body_size = callout.get("description_font_size", int(title_size * 0.55))
    sub_size = int(title_size * 0.5)

    # The band is a property of the delivered frame, not the canvas.
    read_px = body_size * CANVAS_TO_FRAME
    if not BODY_MIN_FRAME_PX <= read_px <= BODY_MAX_FRAME_PX:
        raise ValueError(
            f"description_font_size {body_size} maps to {read_px:.1f}px in "
            f"the delivered frame, outside the documented "
            f"{BODY_MIN_FRAME_PX}-{BODY_MAX_FRAME_PX}px band for body copy "
            f"over picture (docs/skills/plates/SKILL.md). Size the type for "
            f"the frame it is read in, not the canvas it is drawn on."
        )

    plate = callout.get("plate_luma")
    if plate is None:
        raise ValueError(
            "callout has no plate_luma: measure the luma under the card's "
            "whole window with signalstats -> YAVG before rendering it "
            "(docs/skills/plates/references/full-frame-cards.md). Polarity "
            "is measured, never assumed."
        )
    dark_plate = plate["mean"] < LUMA_MIDPOINT
    INK = INK_ON_DARK if dark_plate else INK_ON_LIGHT
    CORE = PROTECT_ON_DARK if dark_plate else PROTECT_ON_LIGHT
    RULE = INK[:3] + (220,)

    f_title = _font(BOLD, title_size)
    f_sub = _font(BOOK, sub_size)
    f_body = _font(BOOK, body_size)

    x0, y0 = box["x"], box["y"]
    text_w = box["width"]

    # Side-by-side art narrows the text column, matching the sheet's habit of
    # setting a label beside the thing it names.
    art = None
    if art_path:
        art = Image.open(art_path).convert("RGBA")
        art_h = box["height"]
        art_w = max(1, int(art.width * art_h / art.height))
        art = art.resize((art_w, art_h), Image.LANCZOS)
        text_w = box["width"] - art_w - int(title_size * 0.9)

    y = y0
    tracking = max(2, title_size // 22)
    for line in _wrap(draw, copy["label_render"], f_title, text_w, tracking):
        _tracked(draw, (x0, y), line, f_title, INK, tracking)
        y += int(title_size * 1.16)

    y += int(title_size * 0.10)
    rule_y = y
    rule_end = x0 + int(text_w * 0.42)
    draw.line([(x0, y), (rule_end, y)], fill=RULE,
              width=max(3, title_size // 24))
    y += int(title_size * 0.28)

    if copy.get("subtitle_render"):
        _tracked(draw, (x0, y), copy["subtitle_render"], f_sub, INK,
                 max(1, sub_size // 18))
        y += int(sub_size * 1.7)

    if copy.get("description_render"):
        y += int(body_size * 0.35)
        for line in _wrap(draw, copy["description_render"], f_body, text_w):
            draw.text((x0, y), line, font=f_body, fill=INK)
            y += int(body_size * 1.42)

    if art is not None:
        ax = x0 + box["width"] - art.width
        card.alpha_composite(art, (ax, y0))
        # Leader line from the text column to the art it describes.
        ly = y0 + box["height"] // 2
        draw.line([(x0 + text_w + int(title_size * 0.18), ly),
                   (ax - int(title_size * 0.22), ly)],
                  fill=RULE, width=max(3, title_size // 26))
        draw.ellipse(
            [ax - int(title_size * 0.22) - 9, ly - 9,
             ax - int(title_size * 0.22) + 9, ly + 9],
            fill=RULE,
        )

    # Protect the glyphs, never with a scrim panel: a tight near-opaque core
    # hugging the letters plus a wider soft falloff, so the protection travels
    # with the type and has no edge an owner can point at.
    # (docs/skills/plates/references/full-frame-cards.md)
    alpha = card.split()[3]
    solid = alpha.point(lambda a: 255 if a > 10 else 0)
    core_a = solid.filter(ImageFilter.MaxFilter(5)).filter(
        ImageFilter.GaussianBlur(radius=max(2, title_size // 40))
    )
    fall_a = solid.filter(ImageFilter.MaxFilter(9)).filter(
        ImageFilter.GaussianBlur(radius=max(8, title_size // 5))
    )

    out = Image.new("RGBA", canvas, (0, 0, 0, 0))
    falloff = Image.new("RGBA", canvas, CORE[:3] + (0,))
    falloff.putalpha(fall_a.point(lambda a: int(a * 0.55)))
    core = Image.new("RGBA", canvas, CORE[:3] + (0,))
    core.putalpha(core_a.point(lambda a: int(a * 0.94)))
    out = Image.alpha_composite(out, falloff)
    out = Image.alpha_composite(out, core)
    out = Image.alpha_composite(out, card)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("callout")
    ap.add_argument("--out", required=True)
    ap.add_argument("--art", default=None)
    args = ap.parse_args()

    edit = json.loads(EDIT.read_text())
    callouts = edit["composition"]["callouts"]
    if args.callout not in callouts:
        raise SystemExit(
            f"{args.callout!r} is not in composition/callouts: "
            f"{sorted(callouts)}"
        )
    img = render_callout(callouts[args.callout], art_path=args.art)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    img.save(args.out)
    print(f"wrote {args.out} {img.size}")


if __name__ == "__main__":
    main()
