#!/usr/bin/env python3
"""Cache Project Bluefin's **dark-mode** monthly wallpapers as frames.

Owner instruction for act VIII: *"Use the dinosaur artwork here instead of
black, use the dark mode wallpapers, make them go through the entire calendar
order and keep switching."*

The wallpapers ship with the desktop, in ``/usr/share/backgrounds/bluefin`` --
``NN-bluefin-night.jxl``, one pair per month, and the ``-night`` half is the
dark mode one. They are **JPEG XL at 6300x2700**, which is two problems for a
render:

* Pillow cannot open JPEG XL, and the containerized ffmpeg on this host has no
  ``jpegxl`` decoder either (``no decoder found for: jpegxl``). GdkPixbuf
  *can* -- the desktop is drawing them right now -- so that is what decodes
  them here. It needs no install and no network.
* They are 21:9 and the film is 16:9, so each is centre-cropped to 16:9 and
  scaled to 1920x1080 once, cached, and never touched again at render time.

The cache lands in gitignored ``renders/wallpapers/``, like every other fetched
artifact. **A missing month degrades**: November ships only the XML on this
host (it points at ``11-bluefin-night.svg``, which is not installed), so the
cycle is eleven wallpapers rather than twelve and says so. A credit roll does
not stop because one month's art is not on the disk.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIR = Path("/usr/share/backgrounds/bluefin")
OUT_DIR = REPO_ROOT / "renders" / "wallpapers"
W, H = 1920, 1080


def months():
    """The calendar, in order, for every month whose night art is installed."""
    out = []
    for m in range(1, 13):
        for ext in ("jxl", "png", "jpg", "svg"):
            path = SOURCE_DIR / f"{m:02d}-bluefin-night.{ext}"
            if path.exists():
                out.append((m, path))
                break
    return out


def decode(path):
    """One wallpaper as a Pillow image, via GdkPixbuf's JPEG XL loader."""
    from PIL import Image

    if path.suffix.lower() not in {".jxl", ".svg"}:
        return Image.open(path).convert("RGB")
    import gi

    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import GdkPixbuf

    pb = GdkPixbuf.Pixbuf.new_from_file(str(path))
    mode = "RGBA" if pb.get_has_alpha() else "RGB"
    img = Image.frombytes(mode, (pb.get_width(), pb.get_height()),
                          bytes(pb.get_pixels()), "raw", mode, pb.get_rowstride())
    return img.convert("RGB")


def crop_16x9(img):
    """Centre-crop to 16:9 and scale to the delivery frame."""
    from PIL import Image

    want = W / H
    have = img.width / img.height
    if have > want:
        side = int(round(img.height * want))
        box = ((img.width - side) // 2, 0, (img.width + side) // 2, img.height)
    else:
        side = int(round(img.width / want))
        box = (0, (img.height - side) // 2, img.width, (img.height + side) // 2)
    return img.crop(box).resize((W, H), Image.LANCZOS)


def main(argv=None):
    found = months()
    if not found:
        print(f"note: no Bluefin wallpapers under {SOURCE_DIR}; act VIII will "
              f"fall back to the deck's flat ink.", file=sys.stderr)
        return 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for month, path in found:
        out = OUT_DIR / f"{month:02d}.png"
        if out.exists():
            print(f"have {out.name}")
            continue
        crop_16x9(decode(path)).save(out)
        print(f"wrote {out.name}  <- {path.name}")
    missing = [m for m in range(1, 13) if not (OUT_DIR / f"{m:02d}.png").exists()]
    if missing:
        print(f"note: no dark-mode art installed for month(s) "
              f"{', '.join(f'{m:02d}' for m in missing)}; the cycle skips them.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
