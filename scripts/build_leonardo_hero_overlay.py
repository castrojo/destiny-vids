#!/usr/bin/env python3
"""Build the 2560x1440 RGBA hero overlay for Leonardo.

Composites:
1. Bottom-left text wordmark: wolves.projectbluefin.io (white text with blue dots).
2. Bottom-right QR card: Support Unleash The Archers (slate style, 280px wide).
3. Left-column Bluefin HUD container for the band lyric video:
   - Inset video window: 896x504 at x=80, y=190.
   - Bluefin HUD frame with 2px #4285f4 rule, corner chamfers, and header plate.
   - Window interior is transparent (alpha=0) so the video renders cleanly beneath.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts import qrcard as qr  # noqa: E402
from tools import plate as plate_mod  # noqa: E402

# Frame specification
FRAME_W = 2560
FRAME_H = 1440
MARGIN = 48

# Band video window geometry
BAND_VID_X = 80
BAND_VID_Y = 190
BAND_VID_W = 896
BAND_VID_H = 504

# Bluefin Brand Colors
COLOR_BLUE = (66, 133, 244, 255)       # #4285f4
COLOR_DARK_SLATE = (12, 16, 23, 220)    # Translucent glass
COLOR_WHITE = (255, 255, 255, 255)
COLOR_TEXT_DIM = (180, 195, 215, 255)


def draw_wordmark(height: int = 44) -> Image.Image:
    """Draw 'wolves.projectbluefin.io' with blue dots and white text."""
    text = "wolves.projectbluefin.io"
    font = plate_mod._font("bold", height)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    tracking = 0.06
    width = plate_mod._tracked_width(probe, text, font, tracking)

    img = Image.new("RGBA", (int(width) + 4, int(height * 1.6)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 0.0
    extra = tracking * font.size

    for ch in text:
        d.text((x, 0), ch, font=font,
               fill=COLOR_BLUE if ch == "." else COLOR_WHITE)
        x += probe.textlength(ch, font=font) + extra
    return img


def draw_hud_frame() -> Image.Image:
    """Draw the Bluefin HUD container around the band video area."""
    overlay = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    # Frame outer bounds with 10px outer margin
    fx0 = BAND_VID_X - 10
    fy0 = BAND_VID_Y - 38
    fx1 = BAND_VID_X + BAND_VID_W + 10
    fy1 = BAND_VID_Y + BAND_VID_H + 10
    chamfer = 12

    # Draw header bar backdrop
    header_pts = [
        (fx0, fy0 + chamfer),
        (fx0 + chamfer, fy0),
        (fx1 - chamfer, fy0),
        (fx1, fy0 + chamfer),
        (fx1, BAND_VID_Y),
        (fx0, BAND_VID_Y),
    ]
    d.polygon(header_pts, fill=COLOR_DARK_SLATE)
    d.line([(fx0, fy0 + chamfer), (fx0 + chamfer, fy0),
            (fx1 - chamfer, fy0), (fx1, fy0 + chamfer)],
           fill=COLOR_BLUE, width=2)

    # Header text
    font_header = plate_mod._font("bold", 15)
    header_title = "UNLEASH THE ARCHERS"
    header_sub = "TEN THOUSAND AGAINST ONE"
    d.text((fx0 + 16, fy0 + 8), header_title, font=font_header, fill=COLOR_WHITE)
    d.text((fx0 + 260, fy0 + 8), f"// {header_sub}", font=font_header, fill=COLOR_BLUE)

    # Draw lower and side border lines around the video window
    # Left border
    d.line([(fx0, BAND_VID_Y), (fx0, fy1 - chamfer), (fx0 + chamfer, fy1)],
           fill=COLOR_BLUE, width=2)
    # Bottom border
    d.line([(fx0 + chamfer, fy1), (fx1 - chamfer, fy1)],
           fill=COLOR_BLUE, width=2)
    # Right border
    d.line([(fx1 - chamfer, fy1), (fx1, fy1 - chamfer), (fx1, BAND_VID_Y)],
           fill=COLOR_BLUE, width=2)

    # Corner accent ticks (Bluefin HUD style)
    tick_len = 20
    d.line([(BAND_VID_X, BAND_VID_Y), (BAND_VID_X + tick_len, BAND_VID_Y)], fill=COLOR_BLUE, width=2)
    d.line([(BAND_VID_X, BAND_VID_Y), (BAND_VID_X, BAND_VID_Y + tick_len)], fill=COLOR_BLUE, width=2)
    d.line([(BAND_VID_X + BAND_VID_W, BAND_VID_Y), (BAND_VID_X + BAND_VID_W - tick_len, BAND_VID_Y)], fill=COLOR_BLUE, width=2)
    d.line([(BAND_VID_X + BAND_VID_W, BAND_VID_Y), (BAND_VID_X + BAND_VID_W, BAND_VID_Y + tick_len)], fill=COLOR_BLUE, width=2)
    d.line([(BAND_VID_X, BAND_VID_Y + BAND_VID_H), (BAND_VID_X + tick_len, BAND_VID_Y + BAND_VID_H)], fill=COLOR_BLUE, width=2)
    d.line([(BAND_VID_X, BAND_VID_Y + BAND_VID_H), (BAND_VID_X, BAND_VID_Y + BAND_VID_H - tick_len)], fill=COLOR_BLUE, width=2)
    d.line([(BAND_VID_X + BAND_VID_W, BAND_VID_Y + BAND_VID_H), (BAND_VID_X + BAND_VID_W - tick_len, BAND_VID_Y + BAND_VID_H)], fill=COLOR_BLUE, width=2)
    d.line([(BAND_VID_X + BAND_VID_W, BAND_VID_Y + BAND_VID_H), (BAND_VID_X + BAND_VID_W, BAND_VID_Y + BAND_VID_H - tick_len)], fill=COLOR_BLUE, width=2)

    return overlay


def build_overlay() -> Image.Image:
    """Build the complete 2560x1440 RGBA overlay image."""
    canvas = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))

    # 1. Band video HUD container
    hud = draw_hud_frame()
    canvas.alpha_composite(hud, (0, 0))

    # 2. Bottom-left wordmark
    wordmark = draw_wordmark(height=44)
    wm_x = MARGIN
    card_h = int(round(280 * (1 + qr.STRIP_FRAC)))
    wm_y = FRAME_H - MARGIN - card_h + card_h - wordmark.height
    canvas.alpha_composite(wordmark, (wm_x, wm_y))

    # 3. Bottom-right QR card
    qr_card = qr.card(
        width=280,
        url="https://www.unleashthearchers.com/",
        style="slate",
        eyebrow="SUPPORT",
        name="UNLEASH THE ARCHERS"
    )
    if not (qr.decodes(qr_card, "https://www.unleashthearchers.com/", qr.DAY_PLATE) and
            qr.decodes(qr_card, "https://www.unleashthearchers.com/", qr.NIGHT_PLATE)):
        raise RuntimeError("QR card failed decode gate")

    qr_x = FRAME_W - MARGIN - 280
    qr_y = FRAME_H - MARGIN - card_h
    canvas.alpha_composite(qr_card, (qr_x, qr_y))

    return canvas


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="renders/leonardo01-overlay.png",
                        help="Output path for the overlay PNG")
    args = parser.parse_args(argv)

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = REPO / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    img = build_overlay()
    img.save(out_path)
    print(f"Rendered Leonardo hero overlay -> {out_path} ({out_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
