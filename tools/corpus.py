#!/usr/bin/env python3
"""Per-character corpus: every indexed shot a Destiny character appears in.

The index is organised by video; a cut is organised by *who is in it*. This
pivots one into the other and writes it down, so the next story about the same
character starts from a catalog instead of a re-read of 119 segment files:

    python3 tools/corpus.py build cayde_6 --dir segments --out corpus/cayde_6.json
    python3 tools/corpus.py check

The amount of Destiny footage is finite, so the corpus is built to accumulate:
one file per character in ``corpus/``, extended a character (or a video) at a
time. ``check`` rebuilds every committed corpus and fails if one is stale, the
same contract ``scripts/generate_skill_index.py --check`` applies to the skill
catalog.

Two halves, and the split is the point:

``shots`` / ``coverage`` are DERIVED — a projection of the segment records, with
    no judgement of their own. Regenerating overwrites them, so they can never
    drift from the index.
``unresolved`` is AUTHORED — the gaps: a beat the footage cannot cover, a source
    the index does not have, a call that needs a human. It is read back off the
    existing file and preserved verbatim on every rebuild, because "we do not
    have this" is knowledge that no amount of re-scanning segments can produce.

A gap is recorded, never guessed. `automatable: false` plus a `blocked_on`
reason is the honest answer for a visual judgement, a claim about a real person,
or a licensing decision — all three of which are somebody else's call.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.derive import lead_alias_index, load_leads, snake_case  # noqa: E402
from tools.search import load_segments  # noqa: E402

DEFAULT_SEGMENTS_DIR = REPO_ROOT / "segments"
DEFAULT_CORPUS_DIR = REPO_ROOT / "corpus"
DEFAULT_VIDEOS_DIR = REPO_ROOT / "videos"

# Copied onto every corpus shot. Cinematography and identity travel with the
# shot because they are what an editor picks between; `overlays` travels with it
# because it is why `clean` says what it says.
SHOT_FIELDS = (
    "segment_id", "video_id", "start_tc", "end_tc", "start_sec", "end_sec",
    "clean", "overlays", "footage_tier", "shot_scale", "composition",
    "camera_angle", "camera_movement", "pacing", "lighting",
    "identity_visibility", "character_identifiability", "subject_salience",
    "action", "mood", "register", "casting", "caption",
)

# An authored gap says what is missing and who has to answer for it.
GAP_FIELDS = ("id", "need", "status", "automatable")
GAP_STATUSES = frozenset({"unresolved", "todo", "blocked"})


def character_shots(character, segments, leads=None):
    """Every segment featuring ``character``, in source order.

    Matches the derived ``casting.character`` first — the authoritative answer —
    and falls back to normalising the raw ``character[]`` names through the same
    alias index derivation uses, so a corpus never disagrees with a cut.
    """
    aliases = lead_alias_index(leads or load_leads())
    hits = []
    for seg in segments:
        cast = (seg.get("casting") or {}).get("character")
        named = {aliases.get(snake_case(entry.get("name", "")))
                 for entry in seg.get("character") or []}
        if cast == character or character in named:
            hits.append(seg)
    return sorted(hits, key=lambda s: (s.get("video_id") or "", s.get("start_sec") or 0))


def _shot(seg):
    shot = {field: seg[field] for field in SHOT_FIELDS if field in seg}
    shot["seconds"] = round((seg.get("end_sec") or 0) - (seg.get("start_sec") or 0), 3)
    return shot


def _coverage(shots, titles):
    videos = {}
    for shot in shots:
        entry = videos.setdefault(shot["video_id"], {
            "video_id": shot["video_id"], "title": titles.get(shot["video_id"]),
            "shots": 0, "clean_shots": 0, "seconds": 0.0,
        })
        entry["shots"] += 1
        entry["clean_shots"] += 1 if shot.get("clean") else 0
        entry["seconds"] = round(entry["seconds"] + shot["seconds"], 3)
    return {
        "videos": [videos[key] for key in sorted(videos)],
        "shots": len(shots),
        "clean_shots": sum(1 for s in shots if s.get("clean")),
        "seconds": round(sum(s["seconds"] for s in shots), 3),
    }


def video_titles(videos_dir=DEFAULT_VIDEOS_DIR):
    titles = {}
    for path in sorted(Path(videos_dir).glob("*.json")):
        with path.open(encoding="utf-8") as fh:
            record = json.load(fh)
        if "video_id" in record:
            titles[record["video_id"]] = record.get("title")
    return titles


def validate_gaps(gaps):
    """An authored gap that does not say who is blocked is not a gap, it is a shrug."""
    for gap in gaps:
        missing = [field for field in GAP_FIELDS if field not in gap]
        if missing:
            raise ValueError(f"gap {gap.get('id', '?')!r} is missing {missing}")
        if gap["status"] not in GAP_STATUSES:
            raise ValueError(f"gap {gap['id']!r} has status {gap['status']!r}, "
                             f"expected one of {sorted(GAP_STATUSES)}")
        if not gap["automatable"] and not gap.get("blocked_on"):
            raise ValueError(f"gap {gap['id']!r} is not automatable and must say "
                             "what it is blocked_on")
    return gaps


def read_gaps(path):
    """Carry the authored half of an existing corpus forward across a rebuild."""
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return validate_gaps(json.load(fh).get("unresolved") or [])


def build(character, segments_dir=DEFAULT_SEGMENTS_DIR, unresolved=None,
          videos_dir=DEFAULT_VIDEOS_DIR):
    leads = load_leads()
    if character not in leads:
        raise KeyError(f"{character!r} is not a lead in vocab/casting.yaml; "
                       f"add the binding there first")
    entry = leads[character]
    shots = [_shot(seg) for seg in
             character_shots(character, load_segments(str(segments_dir)), leads)]
    return {
        "character": character,
        "aka": entry["aka"],
        "cast": {
            "person": entry["person"],
            "display_name": entry["display_name"],
            "has_plate_copy": bool(entry.get("plate")),
        },
        "generated_by": "tools/corpus.py",
        "source_dir": Path(segments_dir).name,
        "coverage": _coverage(shots, video_titles(videos_dir)),
        "shots": shots,
        "unresolved": validate_gaps(list(unresolved or [])),
    }


def write(corpus, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(corpus, fh, indent=2)
        fh.write("\n")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="write one character's corpus")
    b.add_argument("character", help="a lead key from vocab/casting.yaml, e.g. cayde_6")
    b.add_argument("--dir", default=str(DEFAULT_SEGMENTS_DIR),
                   help="directory of segment records (default: segments/)")
    b.add_argument("--out", default=None,
                   help="default: corpus/<character>.json")

    c = sub.add_parser("check", help="fail if any committed corpus is stale")
    c.add_argument("--dir", default=str(DEFAULT_SEGMENTS_DIR))
    c.add_argument("--corpus-dir", default=str(DEFAULT_CORPUS_DIR))

    args = parser.parse_args(argv)

    if args.command == "build":
        out = Path(args.out) if args.out else DEFAULT_CORPUS_DIR / f"{args.character}.json"
        corpus = build(args.character, args.dir, unresolved=read_gaps(out))
        write(corpus, out)
        coverage = corpus["coverage"]
        print(f"wrote {out}: {coverage['shots']} shot(s) "
              f"({coverage['clean_shots']} clean, {coverage['seconds']:g}s) across "
              f"{len(coverage['videos'])} video(s), "
              f"{len(corpus['unresolved'])} unresolved")
        return 0

    stale = []
    for path in sorted(Path(args.corpus_dir).glob("*.json")):
        with path.open(encoding="utf-8") as fh:
            committed = json.load(fh)
        fresh = build(committed["character"], args.dir,
                      unresolved=committed.get("unresolved"))
        if fresh != committed:
            stale.append(path.name)
        print(f"{'STALE' if fresh != committed else 'ok':>5}  {path.name}")
    if stale:
        print(f"\nstale corpus file(s): {', '.join(stale)}\n"
              f"Run: python3 tools/corpus.py build <character>", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
