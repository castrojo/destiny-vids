#!/usr/bin/env python3
"""Build act IV (Kat Cosgrove) from ``stories/04-kat-plates.json``.

A front end for ``scripts/actbuild.py``, which does the work and documents it.
Act IV is the act that proved the shape: its rebuild from the committed record
matches the delivered master's audio bit for bit, and 1167 of its 2040 frames
are bit-identical, every difference falling inside a dialogue window because
the pills are re-rendered by ``tools/plate.py`` rather than screenshotted from
``plate.html``.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import actbuild  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(actbuild.main("IV"))
