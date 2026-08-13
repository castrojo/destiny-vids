#!/usr/bin/env python3
"""Build act V (Natali) from ``stories/05-natali-plates.json``.

A front end for ``scripts/actbuild.py``, which does the work and documents it.
Act V is the second act to get a committed record, and the one that made the
builder general: it starts 357.45 s into a longer source, resolves into its
own fade to black, and carries a rejected hybrid-SFX variant beside the
delivered bed-only cut.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import actbuild  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(actbuild.main("V"))
