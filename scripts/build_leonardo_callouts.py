#!/usr/bin/env python3
"""Render weapon callout cards for Leonardo's hero video.

Outputs 6 full-frame 2560x1440 RGBA overlays (or positioned panels)
placed in the lower-left zone below the band lyric video (x=80..976, y=730..1300).
Each card features:
- Bluefin HUD glass container with #4285f4 border and corner chamfers
- Weapon title, subtitle, and transcribed description from the design sheet
- Cropped weapon asset from CHA_LEONARDO_WEAPONS.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import plate as plate_mod  # noqa: E402

FRAME_W = 2560
FRAME_H = 1440

COLOR_BLUE = (66, 133, 244, 255)         # #4285f4
COLOR_DARK_SLATE = (12, 16, 23, 225)      # Translucent glass
COLOR_WHITE = (255, 255, 255, 255)
COLOR_TEXT_DIM = (200, 215, 235, 255)
COLOR_RULE = (66, 133, 244, 200)

CALLOUTS = [
    {
        "id": "spear",
        "title": "DIY MAGICAL / HI-TECH SPEAR",
        "subtitle": "TUNGSTEN ALLOY",
        "description": "Tactical spear capable of lengthening or shortening for close-quarters engagement or cavalry combat.",
        "weapon_key": "spear",
        "start_time": 20.0,
        "duration": 40.0,
    },
    {
        "id": "sword",
        "title": "DIY HI-TECH SWORD",
        "subtitle": "TUNGSTEN ALLOY",
        "description": "Features pneumatic shock-wave air blast with an integrated manual cocking and pumping mechanism.",
        "weapon_key": "sword",
        "start_time": 70.0,
        "duration": 45.0,
    },
    {
        "id": "shield",
        "title": "AUTOMATIC FOLDING SHIELD",
        "subtitle": "0.12-INCH TITANIUM ALLOY",
        "description": "Segmented rapid-deploying ballistic shield balancing extreme lightweight maneuverability with high impact protection.",
        "weapon_key": "shield",
        "start_time": 125.0,
        "duration": 45.0,
    },
    {
        "id": "crossbow",
        "title": "DIY TACTICAL CROSSBOW",
        "subtitle": "MIXED COMPOSITE MATERIALS",
        "description": "Silent high-tension mechanical crossbow firing precision bolts for stealth interdiction and long-range engagement.",
        "weapon_key": "crossbow",
        "start_time": 180.0,
        "duration": 45.0,
    },
    {
        "id": "chili_grenade",
        "title": "CHILI SMOKE GRENADE",
        "subtitle": "TACTICAL INCENDIARY / IRRITANT",
        "description": "Generates dense sensory-disrupting smoke causing intense skin and eye irritation. Triggers combustion upon contact with electronics.",
        "weapon_key": "chili_grenade",
        "start_time": 235.0,
        "duration": 40.0,
    },
    {
        "id": "hippershell",
        "title": "DIY HIPPERSHELL EXO-X",
        "subtitle": "TUNGSTEN ALLOY // 100K MAH BATTERY",
        "description": "Powered exoskeleton suit improving muscular performance by 50% with an extra 47 kg payload load capacity.",
        "weapon_key": "hippershell",
        "start_time": 285.0,
        "duration": 40.0,
    },
]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=font) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_callout_card(spec: dict, weapons_dir: Path) -> Image.Image:
    card = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)

    # Positioned above terminal in bottom-right (x=1660, y=530), leaving upper sky clear for comet
    bx0 = 1660
    by0 = 530
    bw = 854
    bh = 320
    bx1 = bx0 + bw
    by1 = by0 + bh
    chamfer = 14

    # Backing polygon
    pts = [
        (bx0 + chamfer, by0),
        (bx1 - chamfer, by0),
        (bx1, by0 + chamfer),
        (bx1, by1 - chamfer),
        (bx1 - chamfer, by1),
        (bx0 + chamfer, by1),
        (bx0, by1 - chamfer),
        (bx0, by0 + chamfer),
    ]
    d.polygon(pts, fill=COLOR_DARK_SLATE)

    # Border lines
    d.line([(bx0 + chamfer, by0), (bx1 - chamfer, by0), (bx1, by0 + chamfer),
            (bx1, by1 - chamfer), (bx1 - chamfer, by1), (bx0 + chamfer, by1),
            (bx0, by1 - chamfer), (bx0, by0 + chamfer), (bx0 + chamfer, by0)],
           fill=COLOR_BLUE, width=2)

    # Header plate / eyebrow
    font_eyebrow = plate_mod._font("bold", 12)
    d.text((bx0 + 20, by0 + 14), "// BLUEFIN TACTICAL ARSENAL", font=font_eyebrow, fill=COLOR_BLUE)

    # Title
    font_title = plate_mod._font("bold", 20)
    d.text((bx0 + 20, by0 + 36), spec["title"], font=font_title, fill=COLOR_WHITE)

    # Subtitle
    font_sub = plate_mod._font("regular", 14)
    d.text((bx0 + 20, by0 + 68), spec["subtitle"], font=font_sub, fill=COLOR_BLUE)

    # Accent rule
    d.line([(bx0 + 20, by0 + 92), (bx0 + 440, by0 + 92)], fill=COLOR_RULE, width=2)

    # Description text
    font_body = plate_mod._font("regular", 16)
    text_width = 460
    desc_lines = wrap_text(d, spec["description"], font_body, text_width)
    dy = by0 + 108
    for line in desc_lines:
        d.text((bx0 + 20, dy), line, font=font_body, fill=COLOR_TEXT_DIM)
        dy += 26

    # Weapon Image on right side
    weap_path = weapons_dir / f"{spec['weapon_key']}.png"
    if weap_path.exists():
        weap_img = Image.open(weap_path).convert("RGBA")
        max_art_w = 300
        max_art_h = 240
        scale = min(max_art_w / weap_img.width, max_art_h / weap_img.height)
        new_w = max(1, int(round(weap_img.width * scale)))
        new_h = max(1, int(round(weap_img.height * scale)))
        scaled_weap = weap_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        ax = bx1 - 20 - new_w
        ay = by0 + 30 + (bh - 40 - new_h) // 2
        card.alpha_composite(scaled_weap, (ax, ay))

        # Vertical separator rule between text and weapon
        d.line([(bx0 + 510, by0 + 30), (bx0 + 510, by1 - 20)], fill=COLOR_RULE, width=1)

    return card


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weapons-dir",
                        default="/var/home/jorge/Videos/Wolves/Hero/.work-leonardo01/weapons",
                        help="Directory with cropped weapon PNGs")
    parser.add_argument("--out-dir",
                        default="/var/home/jorge/Videos/Wolves/Hero/.work-leonardo01/callouts",
                        help="Directory to write rendered callout PNGs")
    args = parser.parse_args()

    w_dir = Path(args.weapons_dir)
    o_dir = Path(args.out_dir)
    o_dir.mkdir(parents=True, exist_ok=True)

    for spec in CALLOUTS:
        out_p = o_dir / f"callout-{spec['id']}.png"
        img = render_callout_card(spec, w_dir)
        img.save(out_p)
        print(f"Rendered {spec['id']} -> {out_p} ({out_p.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
