#!/usr/bin/env python3
"""Cache the official Project Bluefin wordmark for the credits.

The owner asked for "the real wordmark" rather than the word typeset in the
deck's font, which is the right call: a brand mark set in somebody else's
typeface is an invented mark, and this repo already refuses to redraw one
(``scripts/fetch_brand_marks.py``, same reasoning).

**Where it actually is.** Not ``ublue-os/artwork`` -- that repository is
wallpapers only, no wordmark in any branch or release. The mark lives at
``ublue-os/universal-blue-org``, ``content/ocis/bluefin.svg``: the "project
Bluefin" lockup with the blue fin ligature, as outlined paths.

**The reversed variant.** The published mark is black with a ``#4285f4`` fin,
drawn for light backgrounds; the credits are near-black. So the BLACK paths are
recoloured to white and **the fin's blue is left exactly as published**. That is
the standard reversed lockup every brand ships for dark backgrounds, not a
recolour of the brand: the one coloured element keeps its value, and no
geometry is touched.

Rasterised with playwright, the same browser this repo already uses for
``cards/render-cards.mjs`` -- an atomic host has no rsvg/inkscape/cairosvg, and
a hand-traced approximation of a wordmark is exactly the invented mark the rule
above exists to prevent.

    python3 scripts/fetch_wordmark.py           # fetch + rasterise if missing
    python3 scripts/fetch_wordmark.py --force   # redo it
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEST = REPO_ROOT / "renders" / "marks"
OUT = DEST / "bluefin-wordmark.png"

SOURCE_REPO = "ublue-os/universal-blue-org"
SOURCE_PATH = "content/ocis/bluefin.svg"
SOURCE_URL = (f"https://raw.githubusercontent.com/{SOURCE_REPO}/main/{SOURCE_PATH}")

# The published fill for the wordmark's type. Recoloured for a dark background;
# the fin's #4285f4 is NOT in this list and is never touched.
TYPE_FILL = "#000000"
REVERSED_FILL = "#ffffff"

RENDER_WIDTH = 1600


def rasterise(svg_text, out_path, width=RENDER_WIDTH):
    """SVG -> transparent PNG, via the browser this repo already depends on."""
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
        tmp = Path(tmp)
        (tmp / "mark.svg").write_text(svg_text, encoding="utf-8")
        script = tmp / "shot.mjs"
        script.write_text(f"""
import {{ chromium }} from 'playwright';
import {{ readFileSync }} from 'fs';
const svg = readFileSync({json.dumps(str(tmp / "mark.svg"))}, 'utf8')
  .replace(/width="[^"]*"/, 'width="{width}"')
  .replace(/height="[^"]*"/, '');
const b = await chromium.launch();
const p = await b.newPage({{ viewport: {{ width: {width + 100}, height: 900 }},
                            deviceScaleFactor: 2 }});
await p.setContent(`<body style="margin:0;background:transparent">
  <div id="m" style="width:{width}px">${{svg}}</div></body>`);
await p.locator('#m').screenshot({{ path: {json.dumps(str(out_path))},
                                    omitBackground: true }});
await b.close();
""", encoding="utf-8")
        # cwd is the repo root so node resolves the vendored playwright.
        subprocess.run(["node", str(script)], cwd=REPO_ROOT, check=True)


def trim(path):
    """Crop to the mark's own ink, so layout can position it by its real box."""
    from PIL import Image
    img = Image.open(path).convert("RGBA")
    box = img.getbbox()
    if box:
        img.crop(box).save(path)
    return img.size


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    DEST.mkdir(parents=True, exist_ok=True)
    if OUT.exists() and not args.force:
        print(f"{OUT} already cached")
        return 0

    try:
        with urllib.request.urlopen(SOURCE_URL, timeout=30) as fh:
            svg = fh.read().decode("utf-8")
    except OSError as exc:
        print(f"could not fetch the wordmark: {exc}", file=sys.stderr)
        print("The credits degrade to the deck's own type if this is missing.",
              file=sys.stderr)
        return 1

    if TYPE_FILL not in svg:
        print(f"warning: {TYPE_FILL} not found in the published SVG -- the mark "
              f"may have been redrawn upstream. Not recolouring blind.",
              file=sys.stderr)
        return 1

    rasterise(svg.replace(TYPE_FILL, REVERSED_FILL), OUT)
    size = trim(OUT)
    print(f"wrote {OUT} ({size[0]}x{size[1]}) from {SOURCE_REPO}/{SOURCE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
