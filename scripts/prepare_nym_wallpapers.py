#!/usr/bin/env python3
"""Prepare 2560x1440 wallpapers for Bluefin: Not Your Monster.

Decodes Project Bluefin's monthly wallpapers in calendar order (01-10, 12)
and extra wallpapers (xe_sunset, xe_space_needle, xe_clouds, xe_red_tulip,
xe_foothills, chicken), centre-cropping each to 16:9 and scaling to 2560x1440.
"""

from pathlib import Path
import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf
from PIL import Image

SRC_DIR = Path("/usr/share/backgrounds/bluefin")
OUT_DIR = Path("/var/home/jorge/Videos/Wolves/Hero/.work-not-your-monster/assets/wallpapers")
OUT_DIR.mkdir(parents=True, exist_ok=True)

CANVAS_W, CANVAS_H = 2560, 1440

MONTHLY_LIST = [
    (1, "01-bluefin-night.jxl", "month-01"),
    (2, "02-bluefin-night.jxl", "month-02"),
    (3, "03-bluefin-night.jxl", "month-03"),
    (4, "04-bluefin-night.jxl", "month-04"),
    (5, "05-bluefin-night.jxl", "month-05"),
    (6, "06-bluefin-night.jxl", "month-06"),
    (7, "07-bluefin-night.jxl", "month-07"),
    (8, "08-bluefin-night.jxl", "month-08"),
    (9, "09-bluefin-night.jxl", "month-09"),
    (10, "10-bluefin-night.jxl", "month-10"),
    (12, "12-bluefin-night.jxl", "month-12"),
]

EXTRA_LIST = [
    ("xe_sunset.jxl", "extra-sunset"),
    ("xe_space_needle.jxl", "extra-space-needle"),
    ("xe_clouds.jxl", "extra-clouds"),
    ("xe_red_tulip.jxl", "extra-red-tulip"),
    ("xe_foothills.jxl", "extra-foothills"),
    ("chicken.jxl", "extra-chicken"),
]


def decode_jxl_or_image(path: Path) -> Image.Image:
    if path.suffix.lower() not in {".jxl", ".svg"}:
        return Image.open(path).convert("RGB")
    pb = GdkPixbuf.Pixbuf.new_from_file(str(path))
    mode = "RGBA" if pb.get_has_alpha() else "RGB"
    img = Image.frombytes(
        mode,
        (pb.get_width(), pb.get_height()),
        bytes(pb.get_pixels()),
        "raw",
        mode,
        pb.get_rowstride(),
    )
    return img.convert("RGB")


def crop_16x9_scale(img: Image.Image, w: int, h: int) -> Image.Image:
    want = w / h
    have = img.width / img.height
    if have > want:
        side = int(round(img.height * want))
        box = ((img.width - side) // 2, 0, (img.width + side) // 2, img.height)
    else:
        side = int(round(img.width / want))
        box = (0, (img.height - side) // 2, img.width, (img.height + side) // 2)
    return img.crop(box).resize((w, h), Image.LANCZOS)


def main():
    print(f"Generating 2560x1440 wallpapers into {OUT_DIR}...")
    manifest = []
    
    # Process monthly
    for m, filename, label in MONTHLY_LIST:
        src = SRC_DIR / filename
        out = OUT_DIR / f"{label}.png"
        if not src.exists():
            print(f"Skipping missing {src}")
            continue
        if not out.exists():
            img = decode_jxl_or_image(src)
            scaled = crop_16x9_scale(img, CANVAS_W, CANVAS_H)
            scaled.save(out)
            print(f"Wrote {out.name} ({scaled.size})")
        else:
            print(f"Cached {out.name}")
        manifest.append({"type": "monthly", "month": m, "label": label, "file": out.name})

    # Process extras
    for filename, label in EXTRA_LIST:
        src = SRC_DIR / filename
        out = OUT_DIR / f"{label}.png"
        if not src.exists():
            print(f"Skipping missing {src}")
            continue
        if not out.exists():
            img = decode_jxl_or_image(src)
            scaled = crop_16x9_scale(img, CANVAS_W, CANVAS_H)
            scaled.save(out)
            print(f"Wrote {out.name} ({scaled.size})")
        else:
            print(f"Cached {out.name}")
        manifest.append({"type": "extra", "label": label, "file": out.name})

    print(f"All {len(manifest)} wallpapers prepared.")


if __name__ == "__main__":
    main()
