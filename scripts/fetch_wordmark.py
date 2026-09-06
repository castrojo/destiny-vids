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

**The reversed variant.** The published mark is black with a `#4285f4` fin,
drawn for light backgrounds. The stage uses the reversed lockup: black paths
are recoloured to white and **the fin's blue is left exactly as published**.
The source digest is checked before that transformation. `--preserve-colors`
is for an already-light SVG fixture, not for the pinned website file.

Rasterised with playwright, the same browser this repo already uses for
`cards/render-cards.mjs` -- an atomic host has no rsvg/inkscape/cairosvg, and
a hand-traced approximation of a wordmark is exactly the invented mark the rule
above exists to prevent.

    python3 scripts/fetch_wordmark.py           # fetch + rasterise if missing
    python3 scripts/fetch_wordmark.py --force   # redo it
    python3 scripts/fetch_wordmark.py \
      --source-url ... --expected-sha256 ... --out ... --width 1200 \
      # the pinned website source is verified, then black lettering is
      # reversed to white while the blue fin is preserved
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
BLACK_SOURCE_FILLS = ("#000000", "#000")
FIN_FILL = "#4285f4"
WEBSITE_VIEWBOX = "0 0 105.658 43.183"
LEGACY_VIEWBOX = "0 0 105.65843 43.183342"
# Kept as an alias for callers that imported the website invariant by its
# earlier name.
EXPECTED_VIEWBOX = WEBSITE_VIEWBOX

DEFAULT_OUT = DEST / "bluefin-wordmark.png"
DEFAULT_WIDTH = 1600

# The ensemble uses a different, source-pinned contract from the legacy
# credits fetch. Keep these values separate so the no-argument defaults remain
# compatible with existing credits builds.
PINNED_WEBSITE_SOURCE_URL = (
    "https://raw.githubusercontent.com/projectbluefin/website/"
    "c03567d972bb9cf52ab0676de5068a54f62f8a48/public/brands/"
    "bluefin-wordmark-light.svg"
)
PINNED_WEBSITE_SOURCE_SHA256 = (
    "d336d743082bded58c561c2c53baf1896dae87d7346224d9d06512e6c247cf74"
)
PINNED_WEBSITE_PRESERVE_COLORS = False
PINNED_WEBSITE_RASTER_WIDTH = 1200
PINNED_WEBSITE_RASTER_SIZE = (1992, 765)
PINNED_WEBSITE_RASTER_SHA256 = (
    "e8ad8bbf657fd486a933f0ea30004817ae59cffd21fd588925b7dd0be897d44e"
)


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


def _is_website_source(source_url):
    return source_url.endswith("/public/brands/bluefin-wordmark-light.svg")


def _recolour_black(svg_text):
    return svg_text.replace(TYPE_FILL, REVERSED_FILL).replace("#000", "#fff")


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


def sha256_file(path):
    """Return the SHA-256 digest of a staged binary asset."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_png(
    path,
    *,
    expected_size=None,
    expected_sha256=None,
):
    """Validate the pinned transparent PNG contract without network access."""
    from PIL import Image

    path = Path(path)
    if not path.is_file():
        raise ValueError(f"wordmark PNG is missing: {path}")

    actual_sha256 = sha256_file(path)
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise ValueError(
            f"wordmark PNG sha256 mismatch: expected {expected_sha256}, "
            f"got {actual_sha256}"
        )

    try:
        with Image.open(path) as image:
            if image.format != "PNG":
                raise ValueError(f"wordmark asset is {image.format}, not PNG")
            image.load()
            actual_size = image.size
            if image.mode != "RGBA":
                raise ValueError(
                    f"wordmark PNG must be RGBA, got {image.mode}"
                )
            if expected_size is not None and actual_size != tuple(expected_size):
                raise ValueError(
                    f"wordmark PNG dimensions mismatch: expected "
                    f"{tuple(expected_size)}, got {actual_size}"
                )
            alpha = image.getchannel("A")
            alpha_min, alpha_max = alpha.getextrema()
            if alpha_min != 0 or alpha_max != 255:
                raise ValueError(
                    "wordmark PNG must have transparent background and "
                    "opaque core pixels"
                )
            if alpha.getbbox() is None:
                raise ValueError("wordmark PNG has no visible alpha")

            has_white = False
            has_fin = False
            has_black = False
            for red, green, blue, opacity in image.getdata():
                if not opacity:
                    continue
                has_white |= (red, green, blue) == (255, 255, 255)
                has_fin |= (red, green, blue) == (66, 133, 244)
                has_black |= (red, green, blue) == (0, 0, 0)
            if not has_white:
                raise ValueError("wordmark PNG has no white lettering")
            if not has_fin:
                raise ValueError("wordmark PNG has no #4285f4 fin")
            if has_black:
                raise ValueError("wordmark PNG contains black lettering")
    except OSError as exc:
        raise ValueError(f"could not read wordmark PNG: {exc}") from exc

    return {
        "path": path,
        "sha256": actual_sha256,
        "size": tuple(expected_size) if expected_size is not None else actual_size,
    }


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

    if not args.preserve_colors and not any(
        fill in svg for fill in BLACK_SOURCE_FILLS
    ):
        print("warning: black lettering was not found in the published SVG -- "
              "the mark may have been redrawn upstream. Not recolouring blind.",
              file=sys.stderr)
        return 1

    expected_viewbox = (
        WEBSITE_VIEWBOX
        if _is_website_source(args.source_url) or args.preserve_colors
        else LEGACY_VIEWBOX
    )
    try:
        validate_svg(
            svg,
            expected_sha256=args.expected_sha256,
            preserve_colors=args.preserve_colors,
            expected_viewbox=expected_viewbox,
        )
    except ValueError as exc:
        print(f"could not fetch the wordmark: {exc}", file=sys.stderr)
        return 1

    if not args.preserve_colors:
        svg = _recolour_black(svg)

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
