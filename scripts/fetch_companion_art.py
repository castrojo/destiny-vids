#!/usr/bin/env python3
"""Cache the bonded-dinosaur artwork the companion plates draw.

The species art is the website's, not this repo's: it lives in
``~/src/website/public/characters/`` beside the authored bond records that name
it (``src/data/wolves-dinosaur-species.ts``). This copies it into
``renders/companions/`` -- gitignored, exactly like the avatar cache -- so the
renderer never reaches outside the repo and never touches the network, and so a
missing sibling checkout degrades to a card without its picture instead of a
crash.

    python3 scripts/fetch_companion_art.py            # copy what is missing
    python3 scripts/fetch_companion_art.py --force    # re-copy everything

The map below is reproduced from ``wolves-dinosaur-species.ts``'s ``artwork``
fields. It is deliberately a small explicit list rather than a TypeScript
parser: four bonds appear in this show, and a wrong path here would put the
wrong animal beside a real person's name.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WEBSITE = Path.home() / "src" / "website" / "public"
DEST = REPO_ROOT / "renders" / "companions"

# species id -> the website's `artwork` path, relative to public/
ARTWORK = {
    "karl": "characters/karl.webp",
    "alamosaurus": "characters/alamosaurus.webp",
    "kentrosaurus": "characters/header/katharina.webp",
    "bob-torosaurus": "characters/bob-torosaurus.webp",
}


def fetch(force=False):
    DEST.mkdir(parents=True, exist_ok=True)
    missing = []
    for species, rel in sorted(ARTWORK.items()):
        src = WEBSITE / rel
        dest = DEST / f"{species}.webp"
        if dest.exists() and not force:
            print(f"have    {dest.relative_to(REPO_ROOT)}")
            continue
        if not src.exists():
            print(f"MISSING {src}", file=sys.stderr)
            missing.append(species)
            continue
        shutil.copyfile(src, dest)
        print(f"cached  {dest.relative_to(REPO_ROOT)}  <- {src}")
    return missing


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true",
                    help="re-copy artwork that is already cached")
    args = ap.parse_args(argv)
    missing = fetch(force=args.force)
    if missing:
        print(f"\n{len(missing)} species have no artwork here: "
              f"{', '.join(missing)}. Their plates render without a picture.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
