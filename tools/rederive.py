#!/usr/bin/env python3
"""Recompute every derived field across the checked-in index.

`vocab/casting.yaml` promises that "a vocab edit re-casts the whole index with
no re-tagging", and `docs/skills/casting/SKILL.md` repeats it. That is true of the
*model* -- `casting` is a pure function of the tagger's `character` list plus the
vocab -- but nothing acted on it: the only path that wrote `casting` into a
segment was `tools/annotate.py index`, which needs the source video, and
`media/` is gitignored. So renaming a cast member left the derived value stale
in every checked-in segment, and the documented remedy could not be run.

This is that path. It reads each segment, re-runs `tools/derive.py`'s
`derive_all` against the tagger fields the record already carries, and rewrites
only the derived block. No video, no keyframes, no model -- the inputs are all
in the file.

It is deliberately not a general editor: it will not touch a tagger field, and
it reports every change so a vocab edit's blast radius is visible before it is
committed.

Usage:
    python3 tools/rederive.py --check          # report drift, change nothing
    python3 tools/rederive.py                  # rewrite drifted segments
    python3 tools/rederive.py --dir segments
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.derive import derive_all, load_leads  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DERIVED_FIELDS = ("clean", "footage_tier", "traversal_hero", "casting")


def _detect_format(raw, record):
    """Recover the file's own JSON layout, so a rewrite is a minimal diff.

    The checked-in segments are ``indent=1`` with no trailing newline, while
    ``tools/annotate.py`` writes ``indent=2`` with one. Imposing either on the
    other turns a one-word re-derive into a 378-line reformat, which buries the
    change this tool exists to make visible. So match whatever the file already
    uses and fall back to the writer's own style for anything new.
    """
    for indent in (1, 2, 4):
        for tail in ("\n", ""):
            if json.dumps(record, indent=indent) + tail == raw:
                return indent, tail
    return 2, "\n"


def rederive_segment(record, leads):
    """Return ``(updated_record, {field: (old, new)})`` for one segment."""
    fresh = derive_all(record, leads=leads)
    changes = {}
    for field in DERIVED_FIELDS:
        old, new = record.get(field), fresh[field]
        if old != new:
            changes[field] = (old, new)
    if not changes:
        return record, {}
    updated = dict(record)
    updated.update(fresh)
    return updated, changes


def _describe(field, old, new):
    if field == "casting":
        old, new = old or {}, new or {}
        parts = [f"{k}: {old.get(k)!r} -> {new.get(k)!r}"
                 for k in sorted(set(old) | set(new)) if old.get(k) != new.get(k)]
        return f"casting.{'; casting.'.join(parts)}" if parts else "casting changed"
    return f"{field}: {old!r} -> {new!r}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", default=str(REPO_ROOT / "segments"),
                    help="directory of segment records (default: segments/)")
    ap.add_argument("--check", action="store_true",
                    help="report drift and exit non-zero; write nothing")
    args = ap.parse_args(argv)

    paths = sorted(Path(args.dir).glob("*.json"))
    if not paths:
        print(f"no segment records in {args.dir}", file=sys.stderr)
        return 1

    leads = load_leads()
    drifted = 0
    for path in paths:
        with path.open(encoding="utf-8") as fh:
            raw = fh.read()
        record = json.loads(raw)
        updated, changes = rederive_segment(record, leads)
        if not changes:
            continue
        drifted += 1
        print(f"{path.name}")
        for field, (old, new) in changes.items():
            print(f"    {_describe(field, old, new)}")
        if not args.check:
            indent, tail = _detect_format(raw, record)
            with path.open("w", encoding="utf-8") as fh:
                fh.write(json.dumps(updated, indent=indent) + tail)

    if not drifted:
        print(f"{len(paths)} segment(s) already agree with the vocab")
        return 0
    if args.check:
        print(f"\n{drifted} segment(s) have stale derived fields; "
              f"run tools/rederive.py to update them", file=sys.stderr)
        return 1
    print(f"\nrewrote {drifted} segment(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
