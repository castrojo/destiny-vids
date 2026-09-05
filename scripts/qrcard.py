#!/usr/bin/env python3
"""QR cards for the hero videos: a code, a label, and a decode gate.

Two styles, because the two cards say different things and belong to different
houses:

  slate  engraved dark modules on brushed steel, dark strip beneath. The
         Unleash the Archers card -- it matches the film's own plate chrome.
  dots   blue circular modules on white, the URL beneath in blue. The Wolves
         card -- it matches projectbluefin.io, whose blue is #4285f4.

    python3 scripts/qrcard.py --style slate --url https://example.com/ \
        --eyebrow SUPPORT --name "SOME BAND" --out renders/card.png

THE DECODE GATE IS THE POINT. A QR that looks right and does not scan is a
failed design, not a rendering problem, so the card is decoded before it is
written -- at the width it actually runs at, over both the day and the night
wallpaper. `main` exits non-zero if it does not read.

TWO MEASURED LIMITS, both found by sweeping against the gate rather than
guessed, and both easy to trip again by "tidying" the drawing:

  * FINDER_RADIUS_MAX. Rounding a finder's corners past 0.13 of its 7-module
    width reads at 1024px and FAILS at 280px. The finder carries the 1:1:3:1:1
    run the locator hunts for, and a generous radius eats the ratio at the
    corners first. Rounding the *data* modules is free.
  * Module gaps. Inset squares look tidier at 1024 and lose the code at 280:
    the gaps plus LANCZOS soften the edges until the sampler cannot find a
    module boundary. The modules here overlap slightly on purpose.

NO BAND ARTWORK. The card sets the band's name in the film's own typeface. It
does not reproduce their logo or any other trademark.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import segno
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import plate as plate_mod  # noqa: E402  (the house mono)

# Defaults for the CLI; the overlay builder passes its own from the record.
URL = "https://www.unleashthearchers.com/"
# Two lines, not one, when there is an eyebrow. A bare wordmark under a code
# does not say what the code is FOR, and 27 characters set across a 280px card
# is unreadable anyway. The eyebrow carries the ask; the name carries the band.
EYEBROW = "SUPPORT"
NAME = "UNLEASH THE ARCHERS"

BORDER = 4              # quiet zone, in modules -- the spec minimum
SS = 3                  # supersample factor; drawn big, resampled down
IN_FRAME_W = 280        # the card's width in the 2560x1440 frame
STRIP_FRAC = 0.30       # name strip height, as a fraction of the card's width

# The ceiling on rounding a finder's corners, as a fraction of its 7-module
# width. FINDER_RADIUS_MAX is where a FLAT design stops decoding; this design's
# modules are engraved, and the light bevel along two edges of every finder
# eats into the ratio before the radius does. It sits well under the ceiling
# for that reason -- the ceiling is a limit, not a licence.
FINDER_RADIUS_MAX = 0.13
FINDER_RADIUS = 0.05

# The two wallpapers the picture crossfades between, sampled flat. The card is
# opaque, so these only have to be right about what surrounds it.
DAY_PLATE = (198, 186, 170)
NIGHT_PLATE = (26, 30, 44)

SLATE = (196, 202, 210)         # the brushed plate
ENGRAVED = (18, 20, 23, 255)    # the modules
BEVEL_LIT = (228, 233, 239, 245)
BEVEL_SHADE = (4, 5, 7, 245)

# projectbluefin.io's blue, lifted from the site rather than guessed:
# `--color-blue: #4285f4` in website/src/style/setup/_variables.scss.
BLUEFIN = (66, 133, 244)
# ...and a deeper one for the modules. #4285f4 on white is about 3.2:1, which
# is fine for a button and thin for a QR: the decoder is thresholding a
# camera's view of a compressed frame, not reading a stylesheet. The brand blue
# stays on the finders and the URL, where it is seen; the data modules take the
# darker shade, where it is read.
BLUEFIN_DEEP = (21, 68, 168)
PAPER = (250, 251, 253)

STYLES = ("slate", "dots")


STRIP = {
    "slate": {
        "bg": (18, 20, 23),
        "fg": (222, 228, 235),
        "eyebrow": (150, 160, 172),
        "rule": (140, 148, 158),
    },
    "dots": {
        "bg": PAPER,
        "fg": BLUEFIN_DEEP,
        "eyebrow": (120, 132, 150),
        "rule": BLUEFIN,
    },
}


def matrix(url=URL):
    """The module grid as a bool array, quiet zone excluded. ECC H throughout."""
    qr = segno.make(url, error="h")
    return np.array([list(row) for row in qr.matrix], dtype=bool)


def finder_cells(n):
    """The three 7x7 finder patterns. Everything else is data or timing."""
    cells = set()
    for r0, c0 in ((0, 0), (0, n - 7), (n - 7, 0)):
        for r in range(r0, r0 + 7):
            for c in range(c0, c0 + 7):
                cells.add((r, c))
    return cells


class Geom:
    """Pixel geometry for one render. Pure arithmetic; the tests pin it."""

    def __init__(self, n, size, border=BORDER, ss=SS):
        self.n = n
        self.border = border
        self.ss = ss
        self.px = size * ss
        self.total = n + 2 * border
        self.mod = self.px / self.total

    def rect(self, r, c, inset=0.0):
        """The box of module (r, c), optionally shrunk by a fraction."""
        x0 = (c + self.border) * self.mod
        y0 = (r + self.border) * self.mod
        d = self.mod * inset
        return (x0 + d, y0 + d, x0 + self.mod - d, y0 + self.mod - d)


def brushed_metal(size, base=SLATE, amount=15, seed=7):
    """Horizontal brush strokes: noise smeared along x, kept subtle."""
    rng = np.random.default_rng(seed)
    width = max(3, size // 24)
    noise = rng.normal(0.0, 1.0, (size, size))
    kernel = np.ones(width) / width
    smeared = np.apply_along_axis(
        lambda row: np.convolve(row, kernel, mode="same"), 1, noise)
    smeared = smeared / (np.abs(smeared).max() or 1.0) * amount
    arr = np.clip(np.array(base, dtype=float)[None, None, :]
                  + smeared[:, :, None], 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def plate_mask(px, radius):
    """The plate's silhouette: rounded on top, square where the strip meets it.

    A rounded bottom edge leaves the strip's colour showing through in two
    little wedges, which reads as a misprint rather than a seam.
    """
    m = Image.new("L", (px, px), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, px - 1, px - 1], radius=radius, fill=255)
    d.rectangle([0, px - 1 - radius, px - 1, px - 1], fill=255)
    return m


def draw_slate(mat, size):
    """The QR itself: engraved modules on brushed slate, with corner ticks."""
    n = mat.shape[0]
    g = Geom(n, size)
    px = g.px
    finders = finder_cells(n)

    out = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    out.paste(brushed_metal(px), (0, 0), plate_mask(px, px * 0.03))
    d = ImageDraw.Draw(out)
    bevel = max(1, int(g.mod * 0.20))

    def engrave(box):
        d.rectangle(box, fill=ENGRAVED)
        d.line([(box[0], box[3]), (box[0], box[1]), (box[2], box[1])],
               fill=BEVEL_SHADE, width=bevel)
        d.line([(box[2], box[1]), (box[2], box[3]), (box[0], box[3])],
               fill=BEVEL_LIT, width=bevel)

    for r in range(n):
        for c in range(n):
            if mat[r, c] and (r, c) not in finders:
                engrave(g.rect(r, c, inset=-0.02))

    for r0, c0 in ((0, 0), (0, n - 7), (n - 7, 0)):
        ox0, oy0, _, _ = g.rect(r0, c0)
        _, _, ox1, oy1 = g.rect(r0 + 6, c0 + 6)
        d.rounded_rectangle([ox0, oy0, ox1, oy1],
                            radius=g.mod * 7 * FINDER_RADIUS,
                            outline=ENGRAVED,
                            width=max(1, int(round(g.mod))))
        cx0, cy0, _, _ = g.rect(r0 + 2, c0 + 2)
        _, _, cx1, cy1 = g.rect(r0 + 4, c0 + 4)
        engrave((cx0, cy0, cx1, cy1))

    # Frame and corner ticks, entirely inside the quiet zone.
    inset = g.mod * 1.1
    d.rectangle([inset, inset, px - inset, px - inset],
                outline=(72, 78, 86, 190), width=max(1, int(g.mod * 0.12)))
    tick = g.mod * 2.0
    for x, y, dx, dy in ((inset, inset, 1, 1), (px - inset, inset, -1, 1),
                         (inset, px - inset, 1, -1),
                         (px - inset, px - inset, -1, -1)):
        d.line([(x, y), (x + dx * tick, y)], fill=(28, 31, 35, 255),
               width=max(1, int(g.mod * 0.28)))
        d.line([(x, y), (x, y + dy * tick)], fill=(28, 31, 35, 255),
               width=max(1, int(g.mod * 0.28)))
    return out.resize((size, size), Image.LANCZOS)


def draw_dots(mat, size):
    """Blue circular modules on white -- the Wolves card, in the site's palette.

    The circles OVERLAP by design. Inset dots look tidier at 1024px and lose the
    code at 280px, the same trap the slate card fell into: the gaps plus LANCZOS
    soften every edge until the sampler cannot find a module boundary.
    """
    n = mat.shape[0]
    g = Geom(n, size)
    px = g.px
    finders = finder_cells(n)

    out = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    out.paste(Image.new("RGB", (px, px), PAPER), (0, 0),
              plate_mask(px, px * 0.03))
    d = ImageDraw.Draw(out)

    for r in range(n):
        for c in range(n):
            if mat[r, c] and (r, c) not in finders:
                d.ellipse(g.rect(r, c, inset=-0.02), fill=(*BLUEFIN_DEEP, 255))

    # The finders carry the brand blue: they are the part of a QR anyone
    # actually looks at, and they are solid enough to take the lighter shade.
    for r0, c0 in ((0, 0), (0, n - 7), (n - 7, 0)):
        ox0, oy0, _, _ = g.rect(r0, c0)
        _, _, ox1, oy1 = g.rect(r0 + 6, c0 + 6)
        d.rounded_rectangle([ox0, oy0, ox1, oy1],
                            radius=g.mod * 7 * FINDER_RADIUS,
                            outline=(*BLUEFIN, 255),
                            width=max(1, int(round(g.mod))))
        cx0, cy0, _, _ = g.rect(r0 + 2, c0 + 2)
        _, _, cx1, cy1 = g.rect(r0 + 4, c0 + 4)
        d.rounded_rectangle([cx0, cy0, cx1, cy1], radius=g.mod * 0.5,
                            fill=(*BLUEFIN, 255))
    return out.resize((size, size), Image.LANCZOS)


RENDERERS = {"slate": draw_slate, "dots": draw_dots}


def card(width, url=URL, style="slate", eyebrow=EYEBROW, name=NAME):
    """The QR art with its label under it, as one object.

    The code alone does not say whose it is or what it wants. A stranger will
    not scan an unlabelled square.
    """
    if style not in RENDERERS:
        raise ValueError(f"unknown style {style!r}; have {sorted(RENDERERS)}")
    art = RENDERERS[style](matrix(url), width)
    skin = STRIP[style]
    strip_h = int(round(width * STRIP_FRAC))
    out = Image.new("RGBA", (width, width + strip_h), (0, 0, 0, 0))

    mask = Image.new("L", out.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, out.width - 1, out.height - 1],
        radius=int(width * 0.045), fill=255)
    out.paste(Image.new("RGB", out.size, skin["bg"]), (0, 0), mask)
    out.alpha_composite(art, (0, 0))

    d = ImageDraw.Draw(out)
    d.line([(width * 0.10, width + strip_h * 0.05),
            (width * 0.90, width + strip_h * 0.05)],
           fill=(*skin["rule"], 110), width=max(1, int(width * 0.004)))

    if eyebrow:
        _fit_line(d, eyebrow, "regular", strip_h * 0.24, 0.22, width,
                  width + strip_h * 0.19, skin["eyebrow"])
        _fit_line(d, name, "bold", strip_h * 0.36, 0.08, width,
                  width + strip_h * 0.51, skin["fg"])
    else:
        # One line, so it gets the whole strip and sits on its centre line.
        _fit_line(d, name, "bold", strip_h * 0.40, 0.06, width,
                  width + strip_h * 0.32, skin["fg"])
    return out


def _fit_line(d, text, weight, size, tracking, width, y, colour):
    """One centred, letter-spaced line, stepped down until it fits the card."""
    while size > 6:
        font = plate_mod._font(weight, size)
        if plate_mod._tracked_width(d, text, font, tracking) <= width * 0.86:
            break
        size -= 1
    font = plate_mod._font(weight, size)
    w = plate_mod._tracked_width(d, text, font, tracking)
    plate_mod._draw_tracked(d, ((width - w) / 2, y), text, font,
                            (*colour, 255), tracking)


def decodes(img, expect=URL, plate=(255, 255, 255)):
    """True when OpenCV reads `expect` back out of `img` over `plate`."""
    import cv2

    flat = Image.new("RGB", img.size, plate)
    flat.paste(img, (0, 0), img)
    arr = np.array(flat)[:, :, ::-1].copy()
    try:
        text, _, _ = cv2.QRCodeDetector().detectAndDecode(arr)
    except cv2.error:
        return False
    return text == expect


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="renders/uta-qr/uta-card.png")
    ap.add_argument("--width", type=int, default=1024,
                    help="the card's width; the strip is added below it")
    ap.add_argument("--url", default=URL)
    ap.add_argument("--style", default="slate", choices=sorted(RENDERERS))
    ap.add_argument("--eyebrow", default=EYEBROW,
                    help="the small line above the name; empty for one line")
    ap.add_argument("--name", default=NAME)
    args = ap.parse_args(argv)

    out = Path(args.out)
    if not out.is_absolute():
        out = REPO / out

    kw = dict(style=args.style, eyebrow=args.eyebrow or None, name=args.name)
    full = card(args.width, args.url, **kw)
    small = card(IN_FRAME_W, args.url, **kw)
    checks = {
        f"{args.width}px": decodes(full, args.url),
        f"{IN_FRAME_W}px on the day wallpaper":
            decodes(small, args.url, DAY_PLATE),
        f"{IN_FRAME_W}px on the night wallpaper":
            decodes(small, args.url, NIGHT_PLATE),
    }

    n = matrix(args.url).shape[0]
    print(f"{args.url}  ->  version {(n - 17) // 4} at ECC H, {n}x{n} modules, "
          f"style {args.style}")
    for what, ok in checks.items():
        print(f"  {'ok  ' if ok else 'FAIL'} decodes at {what}")
    if not all(checks.values()):
        print("card NOT written: it does not scan", file=sys.stderr)
        return 1

    out.parent.mkdir(parents=True, exist_ok=True)
    full.save(out)
    print(f"wrote {out} ({full.width}x{full.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
