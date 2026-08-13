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
}


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
                dest.write_bytes(resp.read())
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
