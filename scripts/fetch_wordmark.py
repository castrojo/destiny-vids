#!/usr/bin/env python3
"""Cache the official Project Bluefin wordmark for the credits.

The owner asked for "the real wordmark" rather than the word typeset in the
deck's font, which is the right call: a brand mark set in somebody else's
typeface is an invented mark, and this repo already refuses to redraw one
(`scripts/fetch_brand_marks.py`, same reasoning).

**Where it actually is.** Not `ublue-os/artwork` -- that repository is
wallpapers only, no wordmark in any branch or release. The mark lives at
`ublue-os/universal-blue-org`, `content/ocis/bluefin.svg`: the "project
Bluefin" lockup with the blue fin ligature, as outlined paths.

**The reversed variant.** The legacy published mark is black with a
`#4285f4` fin, drawn for light backgrounds; the credits are near-black. So the
BLACK paths are recoloured to white and **the fin's blue is left exactly as
published**. The pinned website asset is already the light variant and uses
`--preserve-colors`.

Rasterised with playwright, the same browser this repo already uses for
`cards/render-cards.mjs` -- an atomic host has no rsvg/inkscape/cairosvg, and
a hand-traced approximation of a wordmark is exactly the invented mark the rule
above exists to prevent.

    python3 scripts/fetch_wordmark.py           # fetch + rasterise if missing
    python3 scripts/fetch_wordmark.py --force   # redo it
    python3 scripts/fetch_wordmark.py \
      --source-url ... --expected-sha256 ... --out ... --width 1200 \
      --preserve-colors  # for the already-correct light lockup
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEST = REPO_ROOT / "renders" / "marks"

DEFAULT_SOURCE_REPO = "ublue-os/universal-blue-org"
DEFAULT_SOURCE_PATH = "content/ocis/bluefin.svg"
DEFAULT_SOURCE_URL = (
    f"https://raw.githubusercontent.com/{DEFAULT_SOURCE_REPO}/main/"
    f"{DEFAULT_SOURCE_PATH}"
)
DEFAULT_SOURCE_REF = f"{DEFAULT_SOURCE_REPO}/{DEFAULT_SOURCE_PATH}"

# The published fill for the wordmark's type. Recoloured for a dark background;
# the fin's #4285f4 is NOT in this list and is never touched.
TYPE_FILL = "#000000"
REVERSED_FILL = "#ffffff"
WHITE_FILLS = {"#fff", "#ffffff"}
BLACK_FILLS = {"#000", "#000000"}
FIN_FILL = "#4285f4"
WEBSITE_VIEWBOX = "0 0 105.658 43.183"
LEGACY_VIEWBOX = "0 0 105.65843 43.183342"
# Kept as an alias for callers that imported the website invariant by its
# earlier name.
EXPECTED_VIEWBOX = WEBSITE_VIEWBOX

DEFAULT_OUT = DEST / "bluefin-wordmark.png"
DEFAULT_WIDTH = 1600


def _local_name(tag):
    return tag.rsplit("}", 1)[-1]


def _fill_value(elem):
    fill = elem.get("fill")
    if fill:
        return fill.strip().lower()
    style = elem.get("style", "")
    m = re.search(r"fill\s*:\s*([^;]+)", style, flags=re.I)
    if m:
        return m.group(1).strip().lower()
    return None


def _rect_covers_viewbox(elem, width, height):
    x = float(elem.get("x") or 0)
    y = float(elem.get("y") or 0)
    w = elem.get("width")
    if w is None:
        return False
    if abs(x) > 1e-3 or abs(y) > 1e-3:
        return False
    if abs(float(w) - width) > 1e-3:
        return False
    h = elem.get("height")
    if h is None:
        return True
    return abs(float(h) - height) <= 1e-3


def validate_svg(
    svg_text,
    expected_sha256=None,
    preserve_colors=False,
    expected_viewbox=WEBSITE_VIEWBOX,
):
    """Validate the pinned source SVG before rasterising it.

    The synthetic tests exercise this offline with a tiny inline SVG that keeps
    the same shape invariants as the canonical lockup.
    """
    if expected_sha256 is not None:
        actual_sha256 = hashlib.sha256(svg_text.encode("utf-8")).hexdigest()
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"sha256 mismatch: expected {expected_sha256}, got {actual_sha256}"
            )

    try:
        root = ET.fromstring(svg_text)
    except ET.ParseError as exc:
        raise ValueError(f"invalid SVG: {exc}") from exc
    if _local_name(root.tag) != "svg":
        raise ValueError("root element is not <svg>")

    view_box = root.get("viewBox")
    if expected_viewbox is not None and view_box != expected_viewbox:
        raise ValueError(
            f"unexpected viewBox {view_box!r}; expected {expected_viewbox!r}"
        )
    _, _, width, height = [float(v) for v in re.split(r"[\s,]+", view_box.strip())]

    for elem in root.iter():
        if _local_name(elem.tag) == "rect" and _rect_covers_viewbox(elem, width, height):
            raise ValueError("background rect covers the canvas")

    path_fills = []
    for elem in root.iter():
        if _local_name(elem.tag) != "path":
            continue
        fill = _fill_value(elem)
        if fill is None:
            raise ValueError("path missing fill")
        path_fills.append(fill)
    if not any(fill == FIN_FILL for fill in path_fills):
        raise ValueError("missing #4285f4 fin")

    expected_fills = WHITE_FILLS if preserve_colors else BLACK_FILLS
    lettering = [fill for fill in path_fills if fill != FIN_FILL]
    if not lettering:
        raise ValueError("missing lettering paths")
    if any(fill not in expected_fills for fill in lettering):
        colour = "white" if preserve_colors else "black"
        raise ValueError(f"non-fin paths are not {colour}")


def rasterise(svg_text, out_path, width=DEFAULT_WIDTH):
    """SVG -> transparent PNG, via the browser this repo already depends on."""
    width = int(width)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

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


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    ap.add_argument("--expected-sha256")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    ap.add_argument("--preserve-colors", action="store_true")
    ap.add_argument("--force", action="store_true")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    out = Path(args.out)
    if out.exists() and not args.force:
        print(f"{out} already cached")
        return 0

    try:
        with urllib.request.urlopen(args.source_url, timeout=30) as fh:
            svg = fh.read().decode("utf-8")
    except OSError as exc:
        print(f"could not fetch the wordmark: {exc}", file=sys.stderr)
        print("The credits degrade to the deck's own type if this is missing.",
              file=sys.stderr)
        return 1

    if not args.preserve_colors and TYPE_FILL not in svg:
        print(f"warning: {TYPE_FILL} not found in the published SVG -- the mark "
              f"may have been redrawn upstream. Not recolouring blind.",
              file=sys.stderr)
        return 1

    try:
        validate_svg(
            svg,
            expected_sha256=args.expected_sha256,
            preserve_colors=args.preserve_colors,
            expected_viewbox=(
                WEBSITE_VIEWBOX if args.preserve_colors else LEGACY_VIEWBOX
            ),
        )
    except ValueError as exc:
        print(f"could not fetch the wordmark: {exc}", file=sys.stderr)
        return 1

    if not args.preserve_colors:
        svg = svg.replace(TYPE_FILL, REVERSED_FILL)

    rasterise(svg, out, width=args.width)
    size = trim(out)
    source_label = (
        DEFAULT_SOURCE_REF if args.source_url == DEFAULT_SOURCE_URL
        else args.source_url
    )
    print(f"wrote {out} ({size[0]}x{size[1]}) from {source_label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
