#!/usr/bin/env python3
"""Cache the **extra** Project Bluefin wallpapers the owner named, as frames.

    python3 scripts/fetch_artwork.py            # fetch what is missing
    python3 scripts/fetch_artwork.py --force    # re-fetch everything
    python3 scripts/fetch_artwork.py --list     # what is cached, and from where

Owner, 2026-08-15, on the Perfume interludes: *"replace all the 'ghost'
renditions of the band in this section with pictures of bluefin from the extra
wallpapers"*, naming seven of them -- **bluefin, prey, dusk, huntress,
leafcollector, eyes, lazydays** -- plus, for the shot at 4:19, *"bluefin at
dusk fading from day to night"*.

Where these differ from ``fetch_wallpapers.py``
-----------------------------------------------
That script caches the **monthly dinosaur pair** that ships with the desktop,
from ``/usr/share/backgrounds/bluefin``. These are the *other* wallpapers, and
they are not installed on this host at all -- they live in **ublue-os/artwork**
and are fetched from the project's own repository. Same reasoning as
``fetch_brand_marks.py``: a publisher's own asset, never redrawn and never
taken off this machine's ``/usr/share`` (Bluefin rebrands what is installed
there, which has already produced one wrong credit).

TWO OF THE OWNER'S NAMES ARE NOT THE DIRECTORY NAMES, and guessing wrong just
fails to fetch, so the mapping is written down rather than inferred:

    leafcollector -> leaf-collector        lazydays -> lazy-days

Three source formats, all of which this host can decode
--------------------------------------------------------
* **JPEG XL** -- Pillow cannot open it and the containerised ffmpeg has no
  ``jpegxl`` decoder. GdkPixbuf can, and is what ``fetch_wallpapers.decode``
  already uses; it is reused here rather than reimplemented.
* **SVG** -- rasterised through the same headless browser the wordmark uses,
  because an atomic host has no rsvg or cairosvg.
* **PNG** -- opened directly.

CACHED AT NATIVE RESOLUTION, and that is deliberate
---------------------------------------------------
The first pass centre-cropped every wallpaper to 16:9 and downscaled it to
1920x1080 here, then the renderer scaled it AGAIN into the movement's frame --
two resamples and a crop, on artwork that is published at up to 7680x4320. The
owner caught it: *"why are you using the 10xx versions use the high rez
versions"*.

So nothing is cropped and nothing is downscaled at fetch time. The art is
cached exactly as published and resampled ONCE, at render time, straight from
the master resolution to the delivery frame. Several of these are ultrawide
(``huntress`` 2.37:1, ``lazy-days`` and the monthly ``bluefin`` pair 2.33:1)
while ``dusk`` is natively 16:9 -- the renderer fits each one inside the frame
on its own aspect and letterboxes the difference rather than cropping into
somebody's drawing.

DEGRADES. A wallpaper that cannot be fetched is reported and skipped; the
consumer replaces one shot fewer rather than failing. A cut does not stop
because a PNG is missing.

Rights
------
ublue-os/artwork is **Project Bluefin's own artwork** -- this film's own
project, not a third party's. It is recorded in ``ATTRIBUTIONS.md`` with the
repository's licence so the claim is checkable rather than assumed.
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
sys.path.insert(0, str(REPO_ROOT / "scripts"))

OUT_DIR = REPO_ROOT / "renders" / "artwork"
RAW = "https://raw.githubusercontent.com/ublue-os/artwork/main/wallpapers"

# Vector art is rasterised on its own aspect with this long edge -- 4K, well
# above the 1920-wide delivery frame, so render time only ever downscales.
RASTER_LONG_EDGE = 3840

# The owner's word -> the file that actually carries it.
#
# `day`/`night` are separate entries where the artwork ships a pair, because
# the 4:19 replacement is specifically a DAY going to NIGHT and needs both
# halves of `dusk`. Where only one drawing exists it is cached under its own
# name with no variant.
ARTWORK = {
    "dusk-day":            f"{RAW}/dusk/dusk-day.jxl",
    "dusk-night":          f"{RAW}/dusk/dusk-night.jxl",
    "prey-day":            f"{RAW}/prey/prey-day.svg",
    "prey-night":          f"{RAW}/prey/prey-night.svg",
    "leaf-collector-day":  f"{RAW}/leaf-collector/leaf-collector-day.svg",
    "leaf-collector-night": f"{RAW}/leaf-collector/leaf-collector-night.svg",
    "huntress":            f"{RAW}/huntress/huntress.jxl",
    "eyes":                f"{RAW}/eyes/eyes.svg",
    "lazy-days":           f"{RAW}/lazy-days/lazy.jxl",
    # `bluefin` in the owner's list is the MONTHLY set, which ships with the
    # desktop and is already cached by scripts/fetch_wallpapers.py. It is
    # fetched here too so the interlude pass has one place to look and does not
    # depend on which months happen to be installed on the machine rendering.
    "bluefin-night":       f"{RAW}/bluefin/png/03-bluefin-night.png",
    "bluefin-day":         f"{RAW}/bluefin/png/03-bluefin-day.png",
}

# THE JUMP SCARE. Owner: *"when there's a ROAR jump scare: [angry.webp] use a
# high quality one from ublue-os/artwork"* -- so the mark comes from the
# artwork repository rather than the website's web-optimised header copy.
ROAR = "roar"
ROAR_CANDIDATES = [
    f"{RAW}/huntress/huntress.jxl",
]


def _fetch_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": "destiny-vids"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def _svg_size(svg_text):
    """The SVG's own intrinsic size, from width/height or the viewBox.

    Needed so the raster keeps the drawing's ASPECT. The first pass forced a
    16:9 viewport with ``object-fit: cover``, which silently cropped into
    artwork whose aspect was not 16:9.
    """
    import re

    box = re.search(r'viewBox\s*=\s*["\']([^"\']+)["\']', svg_text)
    if box:
        nums = [float(v) for v in re.split(r'[\s,]+', box.group(1).strip())]
        if len(nums) == 4 and nums[2] > 0 and nums[3] > 0:
            return nums[2], nums[3]
    w = re.search(r'\bwidth\s*=\s*["\']([\d.]+)', svg_text)
    h = re.search(r'\bheight\s*=\s*["\']([\d.]+)', svg_text)
    if w and h:
        return float(w.group(1)), float(h.group(1))
    return 3840.0, 2160.0


def _rasterise_svg(svg_text, out_path, long_edge=RASTER_LONG_EDGE):
    """SVG -> PNG through the headless browser this repo already depends on.

    NOT ``fetch_wordmark.rasterise``: that wraps the SVG in a ``<div id="m">``
    and screenshots that locator, and several of these wallpapers contain their
    own gradients with ``id="m"``/``id="M"``, so the locator matches three
    elements and Playwright refuses in strict mode.

    HIGH FIDELITY, AND NO CROP. A vector has no native resolution, so it is
    rasterised on its OWN aspect at ``long_edge`` -- comfortably above the
    1920-wide delivery frame, so the one resample that happens at render time
    is a downscale. Nothing is cover-fitted and nothing is cropped.
    """
    import base64

    sw, sh = _svg_size(svg_text)
    scale = long_edge / max(sw, sh)
    width, height = int(round(sw * scale)), int(round(sh * scale))

    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
        tmp = Path(tmp)
        data = base64.b64encode(svg_text.encode("utf-8")).decode("ascii")
        script = tmp / "shot.mjs"
        script.write_text(f"""
import {{ chromium }} from 'playwright';
const b = await chromium.launch();
const p = await b.newPage({{ viewport: {{ width: {width}, height: {height} }} }});
await p.setContent(`<body style="margin:0">
  <img src="data:image/svg+xml;base64,{data}"
       style="width:100vw;height:100vh;display:block">
</body>`);
await p.waitForLoadState('networkidle');
await p.screenshot({{ path: {json.dumps(str(out_path))} }});
await b.close();
""", encoding="utf-8")
        subprocess.run(["node", str(script)], cwd=REPO_ROOT, check=True)


def _decode(payload, suffix):
    """One fetched wallpaper as a Pillow RGB image."""
    from PIL import Image
    import fetch_wallpapers

    if suffix == ".svg":
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            png = Path(tmp) / "art.png"
            _rasterise_svg(payload.decode("utf-8"), png)
            return Image.open(png).convert("RGB")

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as fh:
        fh.write(payload)
        tmp = Path(fh.name)
    try:
        return fetch_wallpapers.decode(tmp)
    finally:
        tmp.unlink(missing_ok=True)


def cached(name):
    """Path of one cached frame, or ``None`` if it is not there."""
    out = OUT_DIR / f"{name}.png"
    return out if out.exists() else None


def fetch(force=False, only=None):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    failed = []
    for name, url in sorted(ARTWORK.items()):
        if only and name not in only:
            continue
        out = OUT_DIR / f"{name}.png"
        if out.exists() and not force:
            print(f"have    {out.relative_to(REPO_ROOT)}")
            continue
        try:
            img = _decode(_fetch_bytes(url), Path(url).suffix.lower())
            # NATIVE RESOLUTION, NATIVE ASPECT. No crop, no downscale -- see
            # the module docstring. The renderer resamples once.
            img.save(out)
            print(f"fetched {out.relative_to(REPO_ROOT)}  ({img.width}x{img.height})"
                  f"  <- {url}")
        except Exception as exc:                            # noqa: BLE001
            print(f"FAILED  {name}: {exc}", file=sys.stderr)
            failed.append(name)
    return failed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true",
                    help="re-fetch artwork that is already cached")
    ap.add_argument("--only", nargs="+", help="fetch only these names")
    ap.add_argument("--list", action="store_true",
                    help="print what is cached and where it came from")
    args = ap.parse_args(argv)

    if args.list:
        for name, url in sorted(ARTWORK.items()):
            have = "have" if cached(name) else "MISSING"
            print(f"{have:8} {name:22} {url}")
        return 0

    failed = fetch(force=args.force, only=args.only)
    if failed:
        print(f"\n{len(failed)} wallpaper(s) missing: {', '.join(failed)}. "
              "The interlude pass replaces that many shots fewer.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
