#!/usr/bin/env python3
"""Character corpus — every indexed shot one cast subject appears in.

An outline is written against the footage that exists, so the first question a
cut asks is always "what has this character actually got?". This answers it in
one file per subject: the shots, what they are tagged with, and — just as
importantly — the coverage that is MISSING, so a beat nobody can shoot is
recorded as ``unresolved`` instead of guessed at.

A subject is a casting subject, because casting is how this index says who is
in a shot:

  * a lead key from ``vocab/casting.yaml`` (``osiris``, ``zavala``, ...);
  * ``ensemble`` — the anonymous Guardian, i.e. every blueberry in the crowd.

The corpus is DERIVED and regenerable: everything in it is copied or counted
from ``segments/``, nothing is authored. Hand-editing a corpus file is the same
mistake as hand-editing ``clean`` — rerun the tool instead. Editorial
unknowns that are not derivable (a music cue, a licensing call) belong in the
cut's own doc under ``docs/cuts/``, never here.

Usage:
    python3 tools/corpus.py ensemble --dir segments
    python3 tools/corpus.py ensemble --dir segments --out corpus/ensemble.json
    python3 tools/corpus.py --write          # rebuild every committed corpus
    python3 tools/corpus.py --check          # ...and fail if one is stale
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml  # noqa: E402

from tools.search import load_segments  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SEGMENT_DIR = os.path.join(REPO_ROOT, "segments")
DEFAULT_CORPUS_DIR = os.path.join(REPO_ROOT, "corpus")
VOCAB_DIR = os.path.join(REPO_ROOT, "vocab")

ENSEMBLE = "ensemble"

# Axes worth counting for an author choosing shots.
COVERAGE_AXES = {
    "action": ("action.yaml", "action"),
    "shot_scale": ("cinematography.yaml", "shot_scale"),
    "composition": ("cinematography.yaml", "composition"),
    "subject_salience": ("salience.yaml", "subject_salience"),
}

# Axes a gap on is an editorial fact — "there is no clean shot of this subject
# doing X / framed like Y", which is exactly what makes a beat unwritable.
# `subject_salience` is deliberately absent: it is what DEFINES a subject
# (ensemble is derived from guardian_hero/crowd_group), so a "gap" there would
# report the model's own shape as missing footage.
GAP_AXES = ["action", "shot_scale"]

# Sentinels meaning "not determinable", not a kind of coverage anyone can shoot.
NOT_COVERAGE = frozenset({"unknown", "UNKNOWN"})

# Tagged fields carried into the corpus, so an outline can be written from the
# corpus alone without reopening every segment record.
CARRIED = ["class", "element", "shot_scale", "composition", "camera_movement",
           "pacing", "lighting", "identity_visibility",
           "subject_salience", "action", "mood", "register", "faction"]


def vocab_values(filename, key):
    """Enum values for one axis, straight out of vocab/ — the only source."""
    with open(os.path.join(VOCAB_DIR, filename)) as fh:
        data = yaml.safe_load(fh)
    return list((data[key].get("values") or {}).keys())


def subject_of(segment):
    """The casting subject a segment belongs to, or None.

    Reads the DERIVED casting object rather than re-deriving it: a lead shot
    belongs to its character, an anonymous Guardian shot to the ensemble.
    """
    casting = segment.get("casting") or {}
    role = casting.get("role")
    if role == "lead":
        return casting.get("character")
    if role == ENSEMBLE:
        return ENSEMBLE
    return None


def blocking_overlays(segment):
    """The overlays that cost this shot its `clean` gate, if any."""
    from tools.derive import DISQUALIFYING_OVERLAYS

    return sorted(set(segment.get("overlays") or []) & DISQUALIFYING_OVERLAYS)


def shot_entry(segment):
    casting = segment.get("casting") or {}
    entry = {
        "segment_id": segment.get("segment_id"),
        "video_id": segment.get("video_id"),
        "start_tc": segment.get("start_tc"),
        "end_tc": segment.get("end_tc"),
        "start_sec": segment.get("start_sec"),
        "end_sec": segment.get("end_sec"),
        "duration": round((segment.get("end_sec") or 0) - (segment.get("start_sec") or 0), 3),
        "clean": bool(segment.get("clean")),
        "footage_tier": segment.get("footage_tier"),
        "traversal_hero": bool(segment.get("traversal_hero")),
        "casting": {"role": casting.get("role"), "character": casting.get("character"),
                    "usable": casting.get("usable"), "slots": casting.get("slots")},
        "caption": segment.get("caption"),
    }
    entry.update({field: segment.get(field) for field in CARRIED})
    if not entry["clean"]:
        # An unclean shot stays in the corpus: knowing the footage exists and
        # why it cannot be cut is what stops the next person re-finding it.
        entry["blocked_by"] = blocking_overlays(segment)
    return entry


def _values(entry, axis):
    value = entry.get(axis)
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def coverage(shots, axis):
    counts = {}
    for shot in shots:
        for value in _values(shot, axis):
            counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def gaps(shots, axis, values):
    """Enum values this subject has no CLEAN coverage of.

    Reported per value, with the unclean shots that would have covered it, so
    "there is no footage" and "the footage exists but is barred by the gate"
    stay distinguishable — they have different fixes.
    """
    clean_counts = coverage([s for s in shots if s["clean"]], axis)
    out = []
    for value in values:
        if value in NOT_COVERAGE or clean_counts.get(value):
            continue
        blocked = [{"segment_id": s["segment_id"], "blocked_by": s.get("blocked_by", [])}
                   for s in shots if not s["clean"] and value in _values(s, axis)]
        out.append({
            "axis": axis,
            "value": value,
            "status": "unresolved",
            "note": ("no clean shot of this subject carries this value"
                     + ("; the shots that do are barred by the clean gate"
                        if blocked else "; no shot carries it at all")),
            "blocked_candidates": blocked,
        })
    return out


def build(subject, segments):
    """Catalog one casting subject: its shots, its coverage, and its gaps."""
    shots = [shot_entry(s) for s in segments if subject_of(s) == subject]
    shots.sort(key=lambda s: (s["video_id"] or "", s["start_sec"] or 0))
    clean = [s for s in shots if s["clean"]]
    record = {
        "subject": subject,
        "generated_by": "tools/corpus.py",
        "counts": {
            "shots": len(shots),
            "clean": len(clean),
            "blocked": len(shots) - len(clean),
            "videos": len({s["video_id"] for s in shots}),
            "clean_seconds": round(sum(s["duration"] for s in clean), 3),
        },
        "videos": sorted({s["video_id"] for s in shots if s["video_id"]}),
        "coverage": {axis: coverage(clean, axis) for axis in COVERAGE_AXES},
        "gaps": [],
        "shots": shots,
    }
    for axis in GAP_AXES:
        filename, key = COVERAGE_AXES[axis]
        record["gaps"].extend(gaps(shots, axis, vocab_values(filename, key)))
    return record


def to_text(record):
    lines = [f"CORPUS: {record['subject']}",
             f"{record['counts']['clean']}/{record['counts']['shots']} clean shot(s), "
             f"{record['counts']['clean_seconds']:g}s across "
             f"{record['counts']['videos']} video(s)", ""]
    for shot in record["shots"]:
        flag = " " if shot["clean"] else "!"
        lines.append(f"{flag} {shot['start_tc']}–{shot['end_tc']} "
                     f"({shot['duration']:g}s, {shot['shot_scale']}, "
                     f"{','.join(shot['action'] or []) or '—'})  {shot['segment_id']}")
        lines.append(f"    “{(shot['caption'] or '')[:100]}”")
        if not shot["clean"]:
            lines.append(f"    BLOCKED BY {', '.join(shot['blocked_by']) or 'untagged overlays'}")
    if record["gaps"]:
        lines.append("")
        lines.append("UNRESOLVED — no clean coverage; do not write a beat against these:")
        for gap in record["gaps"]:
            blocked = gap["blocked_candidates"]
            tail = f" ({len(blocked)} unclean candidate(s))" if blocked else ""
            lines.append(f"  {gap['axis']}={gap['value']}{tail}")
    return "\n".join(lines)


def corpus_path(subject, corpus_dir):
    return os.path.join(corpus_dir, f"{subject}.json")


def dumps(record):
    return json.dumps(record, indent=2, ensure_ascii=False) + "\n"


def committed_subjects(corpus_dir):
    if not os.path.isdir(corpus_dir):
        return []
    subjects = []
    for name in sorted(os.listdir(corpus_dir)):
        if name.endswith(".json"):
            subjects.append(os.path.splitext(name)[0])
    return subjects


def refresh(segments, corpus_dir, write):
    """Rebuild every committed corpus. Returns the subjects that were stale."""
    stale = []
    for subject in committed_subjects(corpus_dir):
        path = corpus_path(subject, corpus_dir)
        fresh = dumps(build(subject, segments))
        with open(path, encoding="utf-8") as fh:
            current = fh.read()
        if current == fresh:
            continue
        stale.append(subject)
        if write:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(fresh)
    return stale


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("subject", nargs="?",
                    help="a lead key from vocab/casting.yaml, or 'ensemble'")
    ap.add_argument("--dir", default=DEFAULT_SEGMENT_DIR,
                    help="directory of segment records (default: segments/)")
    ap.add_argument("--corpus-dir", default=DEFAULT_CORPUS_DIR)
    ap.add_argument("--out", help="write the corpus JSON here")
    ap.add_argument("--write", action="store_true",
                    help="rebuild every committed corpus in place")
    ap.add_argument("--check", action="store_true",
                    help="fail if any committed corpus is out of date")
    args = ap.parse_args(argv)

    segments = load_segments(args.dir)
    if not segments:
        print(f"No segment records found in {args.dir}", file=sys.stderr)
        return 1

    if args.write or args.check:
        stale = refresh(segments, args.corpus_dir, write=args.write)
        if args.check and stale:
            print("stale corpus: " + ", ".join(stale)
                  + "\nrun: python3 tools/corpus.py --write", file=sys.stderr)
            return 1
        print(f"{'rewrote' if args.write else 'checked'} "
              f"{len(committed_subjects(args.corpus_dir))} corpus file(s)"
              + (f", {len(stale)} stale" if stale else ""))
        return 0

    if not args.subject:
        ap.error("a subject is required unless --write or --check is given")

    record = build(args.subject, segments)
    if not record["shots"]:
        print(f"No indexed shots cast to subject {args.subject!r} — check the "
              f"key against vocab/casting.yaml", file=sys.stderr)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(dumps(record))
        print(f"wrote {args.out} ({record['counts']['shots']} shot(s), "
              f"{len(record['gaps'])} unresolved gap(s))")
    else:
        print(to_text(record))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
