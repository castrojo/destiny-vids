#!/usr/bin/env python3
"""Render the act-V interstitial card from ``stories/megacut/megacut-cards.json``.

Owner 2026-08-14: *"let the nat scene keep fading to black then put up a
title card 'On the Linux Desktop' 'No one can hear you scream' - in a
terryfing overlay."* The copy is the owner's, reproduced verbatim from the
manifest; the treatment is the homage the second line invokes -- the Alien
one-sheet: widely letterspaced cold capitals, isolated on black, a faint
glow the only thing keeping them company.

Output: ``renders/plates-megacut-cards/plate_scream.png`` -- a full-frame
1920x1080 still flattened onto OPAQUE BLACK (a card that keeps its alpha and
is then concatenated as a still is the megacut skill's standing red flag).

Offline: Pillow only. Re-runs are byte-identical.
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "stories" / "megacut" / "megacut-cards.json"
OUT = REPO / "renders" / "plates-megacut-cards" / "plate_scream.png"

FRAME_W, FRAME_H = 1920, 1080

SERIF = [
    "/usr/share/fonts/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/dejavu-serif-fonts/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
]
SANS = [
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _font(paths, size):
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    raise SystemExit(f"no font found among {paths}")


def _tracked_width(draw, text, font, tracking):
    return sum(draw.textlength(c, font=font) for c in text) \
        + tracking * (len(text) - 1)


def _draw_tracked(draw, xy, text, font, tracking, fill):
    """Letterspaced text: per-character advance plus a fixed tracking gap."""
    x, y = xy
    for c in text:
        draw.text((x, y), c, font=font, fill=fill)
        x += draw.textlength(c, font=font) + tracking


def render():
    doc = json.loads(MANIFEST.read_text())
    card = next(p for p in doc["plates"] if p.get("id") == "scream")
    kicker = card["kicker"].upper()
    line = card["line"].upper()

    frame = Image.new("RGB", (FRAME_W, FRAME_H), (0, 0, 0))

    # Text layer, drawn once and blurred for the glow, then drawn sharp.
    layer = Image.new("RGB", (FRAME_W, FRAME_H), (0, 0, 0))
    d = ImageDraw.Draw(layer)

    f_kick = _font(SANS, 30)
    f_line = _font(SERIF, 58)
    tr_kick, tr_line = 18, 14

    w_kick = _tracked_width(d, kicker, f_kick, tr_kick)
    w_line = _tracked_width(d, line, f_line, tr_line)
    y_kick, y_line = 448, 516

    _draw_tracked(d, ((FRAME_W - w_kick) / 2, y_kick), kicker, f_kick,
                  tr_kick, (108, 118, 128))
    _draw_tracked(d, ((FRAME_W - w_line) / 2, y_line), line, f_line,
                  tr_line, (226, 231, 236))

    # The glow: the same layer, softened and weighted down, under the sharp
    # pass -- cold breath on the glass rather than neon.
    glow = layer.filter(ImageFilter.GaussianBlur(10)).point(lambda v: v * 0.55)
    frame = Image.composite(layer, glow, layer.convert("L").point(
        lambda v: 255 if v > 24 else 0))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    frame.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    render()
