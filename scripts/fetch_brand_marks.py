#!/usr/bin/env python3
"""Cache the official brand artwork the plate crests draw.

`tools/plate.py` never touches the network, so a brand mark is a LOCAL file.
Bazzite's logomark is traced from its SVG in code; a brand published only as a
raster is reproduced from the publisher's own asset rather than redrawn by
hand, because a hand-drawn approximation of somebody's logo is an invented
mark.

    python3 scripts/fetch_brand_marks.py            # download what is missing
    python3 scripts/fetch_brand_marks.py --force    # re-download everything

The files land in gitignored ``renders/marks/``, like every other fetched
artifact. A missing one degrades to the drawn hex crest with a stderr note.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEST = REPO_ROOT / "renders" / "marks"

# mark name -> the publisher's own URL for it
MARKS = {
    # The Nobara Project's own site icon. Its dominant fill #3E3FC5 is the
    # brand's "Governor Bay" and is what tools/plate.py's `nobara` variant is
    # keyed to; the two were sampled from THIS file, not recalled.
    "nobara": "https://nobaraproject.org/img/nobara-icon.png",

    # ACT VIII'S UPSTREAM BADGES. Owner: *"let's snag the logos to these
    # projects and make them look GOOD."* Each one is the project's own
    # published artwork, fetched rather than redrawn -- a hand-approximated
    # logo is an invented mark, which is the rule that already governs the
    # Bluefin wordmark and the Nobara crest.
    "kde": "https://kde.org/stuff/clipart/logo/"
           "kde-logo-white-blue-rounded-source.svg",
    # Fedora's own site icon -- the SYMBOL, not the horizontal wordmark
    # lockup at /assets/images/logos/fedora-logo.svg. Owner, on the first
    # pass: *"you overdid the logos those are tacky, smaller and symbolic"*,
    # and a lockup that spells the brand out cannot be small.
    "fedora": "https://fedoraproject.org/favicon.ico",
    # GNOME OS's own site icon, from the project being credited rather than
    # from GNOME the organisation.
    "gnome": "https://os.gnome.org/assets/apple-touch-icon.png",
    # Metal3's own docs repository, for the gag on the upstream walls
    # ("Deploying CNCF Metal3").
    "metal3": "https://raw.githubusercontent.com/metal3-io/metal3-docs/"
              "main/images/metal3.svg",
}

# NEVER TAKE A BRAND MARK OFF THIS HOST'S /usr/share/pixmaps.
#
# It looks like the publisher's own delivery and it is not: Bluefin REBRANDS
# them. `fedora_whitelogo_med.png` and `gnome-boot-logo.png` on this machine
# are both the **Project Bluefin wordmark**, and the first act VIII build
# credited "Fedora CoreOS" under a Bluefin logo before anybody looked at the
# frame. A distro's installed artwork is the distro's, not the upstream's --
# fetch from the project's own site.


def fetch(force=False):
    DEST.mkdir(parents=True, exist_ok=True)
    failed = []
    for name, url in sorted(MARKS.items()):
        dest = DEST / f"{name}.png"
        if dest.exists() and not force:
            print(f"have    {dest.relative_to(REPO_ROOT)}")
            continue
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "destiny-vids"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = resp.read()
            if url.endswith(".svg"):
                # A vector mark is rasterised through the same browser the
                # wordmark uses; an atomic host has no rsvg or cairosvg.
                from fetch_wordmark import rasterise, trim
                rasterise(payload.decode("utf-8"), dest, width=900)
                trim(dest)
            else:
                dest.write_bytes(payload)
            print(f"fetched {dest.relative_to(REPO_ROOT)}  <- {url}")
        except Exception as exc:                          # noqa: BLE001
            print(f"FAILED  {name}: {exc}", file=sys.stderr)
            failed.append(name)

    return failed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true",
                    help="re-download marks that are already cached")
    args = ap.parse_args(argv)
    failed = fetch(force=args.force)
    if failed:
        print(f"\n{len(failed)} mark(s) missing: {', '.join(failed)}. "
              "Those plates render with the drawn hex crest.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
