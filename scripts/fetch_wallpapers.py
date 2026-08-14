#!/usr/bin/env python3
"""Cache Project Bluefin's monthly wallpapers as frames.

Owner instruction for act VIII: *"Use the dinosaur artwork here instead of
black, use the dark mode wallpapers, make them go through the entire calendar
order and keep switching."* That is the ``night`` half, and it is still the
default.

The ``day`` half was added for the **prologue's bridge**, where the owner asked
for *"a 03-bluefin-day.jxl and fade to the dark version so that that replaces
the black part"* — the handoff out of the main title sequence is a March
wallpaper turning from day to night rather than a cut to black.

The wallpapers ship with the desktop, in ``/usr/share/backgrounds/bluefin`` --
``NN-bluefin-{day,night}.jxl``, one pair per month. They are **JPEG XL at
6300x2700**, which is two problems for a render:

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


def months(variant="night"):
    """The calendar, in order, for every month whose art is installed.

    ``variant`` is ``night`` or ``day``. The night half is act VIII's; the day
    half exists for the **prologue's bridge**, which puts March up and turns it
    to dark rather than cutting to black.
    """
    out = []
    for m in range(1, 13):
        for ext in ("jxl", "png", "jpg", "svg"):
            path = SOURCE_DIR / f"{m:02d}-bluefin-{variant}.{ext}"
            if path.exists():
                out.append((m, path))
                break
    return out


def cached(month, variant="night"):
    """Path of one cached frame, decoding it on demand. None if not installed.

    The night frames keep their bare ``NN.png`` names because act VIII's build
    already reads them; the day half is suffixed. Renaming the night frames to
    match the day ones would be tidier and would silently invalidate act VIII's
    cache, so it is deliberately not done.
    """
    out = cached_name(month, variant)
    if out.exists():
        return out
    for m, path in months(variant):
        if m == month:
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            crop_16x9(decode(path)).save(out)
            return out
    return None


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
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--variant", choices=("night", "day", "both"),
                    default="night",
                    help="which half of each month's pair to cache "
                         "(default: night, act VIII's)")
    args = ap.parse_args(argv)
    wanted = ("night", "day") if args.variant == "both" else (args.variant,)

    for variant in wanted:
        found = months(variant)
        if not found:
            print(f"note: no Bluefin {variant} wallpapers under {SOURCE_DIR}; "
                  f"the consumer falls back to the deck's flat ink.",
                  file=sys.stderr)
            continue
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        for month, path in found:
            out = OUT_DIR / (f"{month:02d}.png" if variant == "night"
                             else f"{month:02d}-{variant}.png")
            if out.exists():
                print(f"have {out.name}")
                continue
            crop_16x9(decode(path)).save(out)
            print(f"wrote {out.name}  <- {path.name}")
        missing = [m for m in range(1, 13) if not cached_name(m, variant).exists()]
        if missing:
            print(f"note: no {variant} art installed for month(s) "
                  f"{', '.join(f'{m:02d}' for m in missing)}; "
                  f"the cycle skips them.", file=sys.stderr)
    return 0


def cached_name(month, variant="night"):
    return OUT_DIR / (f"{month:02d}.png" if variant == "night"
                      else f"{month:02d}-{variant}.png")


if __name__ == "__main__":
    raise SystemExit(main())
