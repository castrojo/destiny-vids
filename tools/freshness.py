#!/usr/bin/env python3
"""Refuse to build a video out of intermediates that predate their sources.

WHY THIS EXISTS
---------------
The delivery graph (``tools/deliver.py``) watches an act master against its
committed inputs, and ``tools/megacut.py`` refuses to seat a stale act. Both
were satisfied while a stale programme shipped anyway, because the staleness
was one rung further down: a builder re-rendered its act and quietly consumed
**cached PNGs** for the cards.

The pattern that did it:

    if args.cards or not (PLATES_DIR / "plate_maintitle-b.png").exists():
        render_cards()

The card template moved at 16:56, the PNGs were from 23:24 the night before,
and the file existed -- so the rebuild ran, produced a new master, published a
matching digest, and delivered a main title with none of the day's changes.
Every gate was green. The act really had been rebuilt; it had just been
rebuilt *from yesterday*.

The lesson is one line: **existence is not freshness.** An intermediate is a
derived file, so the only question worth asking is whether it is older than
what derives it.

THE RULE
--------
A builder never chooses whether to regenerate a stale intermediate. Anything
older than its own source is regenerated, always, and a flag may only force
*extra* work (``--cards``), never skip required work. Fail closed: if the
freshness of an intermediate cannot be established, regenerate it.
"""

from __future__ import annotations

from pathlib import Path


def _newest(paths):
    """The newest mtime across `paths`, recursing into directories."""
    newest = None
    for p in paths:
        p = Path(p)
        if p.is_dir():
            times = [c.stat().st_mtime for c in p.rglob("*") if c.is_file()]
        elif p.exists():
            times = [p.stat().st_mtime]
        else:
            times = []
        for t in times:
            if newest is None or t > newest:
                newest = t
    return newest


def stale_outputs(inputs, outputs):
    """The outputs that are missing, or older than the newest input.

    Missing counts as stale, so one call answers both "is it there?" and "is
    it current?" -- the two questions the old `exists()` checks conflated.
    """
    cutoff = _newest(inputs)
    stale = []
    for out in outputs:
        out = Path(out)
        if not out.exists():
            stale.append(out)
        elif cutoff is not None and out.stat().st_mtime < cutoff:
            stale.append(out)
    return stale


def needs_render(inputs, outputs):
    """True when anything in `outputs` is missing or predates `inputs`.

    The replacement for `not some_output.exists()`. Use it as the WHOLE
    condition; an explicit `--cards` flag ORs on top to force a re-render that
    is not otherwise required.
    """
    return bool(stale_outputs(inputs, outputs))
