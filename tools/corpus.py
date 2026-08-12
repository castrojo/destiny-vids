#!/usr/bin/env python3
"""Character corpus: every indexed shot a named character appears in.

A segment record answers "what is this shot?". Nothing answered "what footage do
we have of Osiris, how much of it is cuttable, and who is still missing?"
without re-walking every file in ``segments/``. This builds that view once and
commits it, so an outline can be written against the cast that actually exists —
and so the next character or story extends an index instead of starting one.

The corpus is DERIVED, never authored. It reads ``segments/`` plus the lead map
in ``vocab/casting.yaml`` and rewrites ``corpus/characters.json`` and its
human-readable mirror ``corpus/README.md``. Hand-editing either is the same
mistake as hand-editing ``clean``: run ``--write``. ``--check`` fails when the
committed corpus is stale, so the index and the corpus cannot drift apart.
``clean`` and ``footage_tier`` are recomputed here through tools/derive.py
rather than read off the record, so a corpus can never launder a hand-set gate.

Gaps are reported as loudly as coverage, because a gap is the next piece of work:

  uncast_lead       — a character in the footage with no person bound to them.
  unindexed_lead    — a binding with zero shots. The cast exists, the footage
                      does not: this is what to index next.
  unbound_character — a name tagged in the footage with no entry in the lead map.
  pending_binding   — the mirror of uncast_lead, read from ``leads.pending``:
                      the PERSON is known and the character is not.

Every gap carries ``automatable`` and, when that is false, ``blocked_on``.
Casting names a real person, so "which character is this?" is a judgment for
someone who has seen the footage — it is recorded here, never guessed.

Usage:
    python3 tools/corpus.py --write             # rebuild corpus/
    python3 tools/corpus.py --check             # fail if corpus/ is stale
    python3 tools/corpus.py --character osiris  # one character, to stdout
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.derive import (  # noqa: E402  (path setup must precede the import)
    compute_clean,
    compute_footage_tier,
    compute_slots,
    evaluate_constraints,
    lead_alias_index,
    load_leads,
    snake_case,
)

DEFAULT_CASTING_PATH = REPO_ROOT / "vocab" / "casting.yaml"
SEGMENT_DIR = REPO_ROOT / "segments"
CORPUS_DIR = REPO_ROOT / "corpus"
JSON_PATH = CORPUS_DIR / "characters.json"
MD_PATH = CORPUS_DIR / "README.md"
SCHEMA_VERSION = "1.0"

# Saliences whose subject is an anonymous Guardian, i.e. an ensemble slot.
ENSEMBLE_SALIENCE = frozenset({"guardian_hero", "crowd_group"})

# What a corpus row carries about a shot: enough to write a beat against it
# without opening the segment record, and nothing that is not already indexed.
SHOT_FIELDS = (
    "shot_scale", "composition", "camera_movement", "subject_salience",
    "register", "mood", "action", "overlays", "caption",
)


def load_segments(segment_dir=None):
    """Load every segment record in a directory, in timeline order."""
    segment_dir = Path(segment_dir) if segment_dir else SEGMENT_DIR
    segments = []
    for path in sorted(segment_dir.glob("*.json")):
        with path.open(encoding="utf-8") as fh:
            segments.append(json.load(fh))
    segments.sort(key=lambda s: (s.get("video_id") or "", s.get("start_sec") or 0))
    return segments


def load_pending(path=None):
    """Load ``leads.pending`` from vocab/casting.yaml.

    Requested cast whose Destiny character is not settled yet. Derivation never
    reads this block — it is a queue, not a binding — so a pending entry casts
    nobody and plates nothing until it is promoted into ``leads.values``.
    """
    path = Path(path) if path else DEFAULT_CASTING_PATH
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return dict(((data or {}).get("leads") or {}).get("pending") or {})


def shot_row(segment, character, leads):
    """One corpus row: the shot, seen from one character's point of view.

    ``usable`` is evaluated for THIS character rather than copied from the
    record's derived ``casting``, which only ever describes the first character
    matched in a two-hander.
    """
    constraints = (leads.get(character) or {}).get("constraints") or {}
    failed = evaluate_constraints(segment, constraints)
    start, end = segment.get("start_sec"), segment.get("end_sec")
    row = {
        "segment_id": segment.get("segment_id"),
        "video_id": segment.get("video_id"),
        "start_tc": segment.get("start_tc"),
        "end_tc": segment.get("end_tc"),
        "start_sec": start,
        "end_sec": end,
        "duration": round(end - start, 3) if start is not None and end is not None else None,
        "clean": compute_clean(segment),
        "footage_tier": compute_footage_tier(segment),
        "usable": not failed,
        "constraints_failed": failed,
    }
    row.update({field: segment.get(field) for field in SHOT_FIELDS})
    return row


def character_totals(rows):
    """Coverage for one character. ``seconds`` counts CLEAN footage only —
    unclean shots are not coverage, they are shots you cannot cut."""
    return {
        "shots": len(rows),
        "clean": sum(1 for r in rows if r["clean"]),
        "unclean": sum(1 for r in rows if not r["clean"]),
        "cinematic": sum(1 for r in rows if r["footage_tier"] == "cinematic"),
        "gameplay": sum(1 for r in rows if r["footage_tier"] == "gameplay"),
        "usable": sum(1 for r in rows if r["usable"] and r["clean"]),
        "clean_seconds": round(sum(r["duration"] or 0 for r in rows if r["clean"]), 2),
    }


def video_coverage(segments):
    """Per-video coverage: what the index holds, and how much of it is cuttable."""
    by_video = {}
    for segment in segments:
        video_id = segment.get("video_id")
        entry = by_video.setdefault(video_id, {
            "video_id": video_id, "shots": 0, "clean": 0, "unclean": 0,
            "character_shots": 0, "ensemble_shots": 0, "ensemble_slots": 0,
        })
        clean = compute_clean(segment)
        entry["shots"] += 1
        entry["clean" if clean else "unclean"] += 1
        if segment.get("character"):
            entry["character_shots"] += 1
        elif clean and segment.get("subject_salience") in ENSEMBLE_SALIENCE:
            entry["ensemble_shots"] += 1
            entry["ensemble_slots"] += compute_slots(segment)
    return [by_video[k] for k in sorted(by_video)]


def build_corpus(segments, leads, pending, segment_dir="segments"):
    """Assemble the whole corpus: coverage per character, then the gaps."""
    alias_index = lead_alias_index(leads)
    rows_by_character = {}
    names_by_character = {}
    for segment in segments:
        for entry in segment.get("character") or []:
            name = entry.get("name", "")
            character = alias_index.get(snake_case(name)) or snake_case(name)
            rows_by_character.setdefault(character, []).append(
                shot_row(segment, character, leads))
            names_by_character.setdefault(character, set()).add(name)

    characters = []
    for character in sorted(rows_by_character):
        binding = leads.get(character)
        rows = rows_by_character[character]
        characters.append({
            "character": character,
            "names_in_index": sorted(names_by_character[character]),
            "bound": binding is not None,
            "person": (binding or {}).get("person"),
            "display_name": (binding or {}).get("display_name"),
            "has_plate": bool((binding or {}).get("plate")),
            "constraints": (binding or {}).get("constraints") or {},
            "videos": sorted({r["video_id"] for r in rows}),
            "totals": character_totals(rows),
            "shots": rows,
        })

    return {
        "generated_at": date.today().isoformat(),
        "schema_version": SCHEMA_VERSION,
        "segment_dir": segment_dir,
        "totals": {
            "segments": len(segments),
            "clean": sum(1 for s in segments if compute_clean(s)),
            "characters": len(characters),
            "bound": sum(1 for c in characters if c["person"]),
            "videos": len({s.get("video_id") for s in segments}),
        },
        "videos": video_coverage(segments),
        "characters": characters,
        "unresolved": build_unresolved(characters, leads, pending),
    }


def build_unresolved(characters, leads, pending):
    """Every gap, in the order you would work through them.

    A gap is not a failure of the corpus; it is the corpus doing its job. The
    footage that does not exist yet is what to index next, and the binding that
    cannot be settled without watching a video is what to ask a human about.
    """
    indexed = {c["character"] for c in characters}
    gaps = []

    for entry in characters:
        if entry["bound"] and not entry["person"]:
            gaps.append({
                "kind": "uncast_lead",
                "id": entry["character"],
                "detail": (f"{entry['totals']['clean']} clean shot(s) indexed, "
                           "no person bound"),
                "automatable": False,
                "blocked_on": "a casting decision; binding a role names a real person",
            })
        elif not entry["bound"]:
            gaps.append({
                "kind": "unbound_character",
                "id": entry["character"],
                "detail": (f"tagged in {entry['totals']['shots']} shot(s) but absent "
                           "from vocab/casting.yaml `leads.values`"),
                "automatable": False,
                "blocked_on": "whether this name is a castable role at all",
            })

    for character, binding in leads.items():
        if character in indexed:
            continue
        gaps.append({
            "kind": "unindexed_lead",
            "id": character,
            "detail": ("bound to " + binding["person"] if binding["person"]
                       else "written but not cast") + ", zero shots in the index",
            "automatable": True,
            "blocked_on": "media for a video that features them, and an indexing pass",
        })

    for person, request in pending.items():
        gaps.append({
            "kind": "pending_binding",
            "id": person,
            "detail": request.get("described_as") or "no description given",
            "automatable": bool(request.get("automatable", False)),
            "blocked_on": " ".join((request.get("blocked_on") or "").split()) or None,
            "requested_in": request.get("requested_in"),
            "source_video": request.get("source_video"),
        })

    return gaps


def format_character(entry):
    """One character's corpus, for a terminal."""
    totals = entry["totals"]
    cast = entry["person"] or ("uncast" if entry["bound"] else "not a lead binding")
    lines = [
        f"{entry['character']} — {cast}",
        f"  {totals['shots']} shot(s), {totals['clean']} clean, "
        f"{totals['usable']} usable, {totals['clean_seconds']}s of clean footage",
    ]
    for row in entry["shots"]:
        flag = "" if row["clean"] else "  UNCLEAN"
        if row["constraints_failed"]:
            flag += "  FAILS " + ",".join(row["constraints_failed"])
        lines.append(f"  {row['start_tc']}–{row['end_tc']}  {row['shot_scale']:<6} "
                     f"{row['segment_id']}{flag}")
        lines.append(f"      {row['caption']}")
    return "\n".join(lines)


def render_markdown(corpus):
    """Human-readable mirror of characters.json."""
    totals = corpus["totals"]
    lines = [
        "# Character corpus (generated)",
        "",
        "Every indexed shot a named character appears in, plus the gaps. This file",
        "and `characters.json` are generated by `tools/corpus.py` — do not hand-edit",
        "either; run `python3 tools/corpus.py --write`.",
        "",
        f"Generated: {corpus['generated_at']} · schema {corpus['schema_version']} · "
        f"{totals['characters']} characters across {totals['videos']} videos · "
        f"{totals['clean']}/{totals['segments']} shots clean",
        "",
        "## Coverage by video",
        "",
        "| video | shots | clean | named-character shots | ensemble shots | ensemble slots |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for video in corpus["videos"]:
        lines.append(
            f"| `{video['video_id']}` | {video['shots']} | {video['clean']} | "
            f"{video['character_shots']} | {video['ensemble_shots']} | "
            f"{video['ensemble_slots']} |")

    lines += ["", "## Cast coverage", ""]
    lines += ["| character | cast as | shots | clean | usable | clean seconds |",
              "|---|---|---:|---:|---:|---:|"]
    for entry in corpus["characters"]:
        cast = entry["display_name"] or ("*uncast*" if entry["bound"] else "*unbound*")
        t = entry["totals"]
        lines.append(f"| `{entry['character']}` | {cast} | {t['shots']} | {t['clean']} | "
                     f"{t['usable']} | {t['clean_seconds']} |")

    for entry in corpus["characters"]:
        cast = entry["display_name"] or ("uncast" if entry["bound"] else "not a lead binding")
        lines += ["", f"### `{entry['character']}` — {cast}", ""]
        lines += ["| shot | in–out | scale | camera | clean | tier | usable | caption |",
                  "|---|---|---|---|---|---|---|---|"]
        for row in entry["shots"]:
            camera = ", ".join(row["camera_movement"] or []) or "—"
            failed = ", ".join(row["constraints_failed"])
            usable = "yes" if row["usable"] else f"no ({failed})"
            lines.append(
                f"| `{row['segment_id']}` | {row['start_tc']}–{row['end_tc']} | "
                f"{row['shot_scale']} | {camera} | {'yes' if row['clean'] else '**no**'} | "
                f"{row['footage_tier']} | {usable} | {row['caption']} |")

    lines += ["", "## Unresolved", "",
              "Recorded, not guessed. `automatable: no` means the next step needs a",
              "human who has seen the footage — casting names real people.",
              "",
              "| kind | id | automatable | detail | blocked on |",
              "|---|---|---|---|---|"]
    for gap in corpus["unresolved"]:
        lines.append(
            f"| {gap['kind']} | `{gap['id']}` | {'yes' if gap['automatable'] else '**no**'} | "
            f"{gap['detail']} | {gap['blocked_on'] or '—'} |")
    lines.append("")
    return "\n".join(lines)


def pin_unchanged_generated_at(corpus, existing):
    """Reuse the committed ``generated_at`` when nothing else changed.

    Same reasoning as scripts/generate_skill_index.py: the stamp records when the
    corpus last actually changed, so ``--check`` must not fail on calendar drift.
    """
    if existing is None:
        return
    a = {k: v for k, v in corpus.items() if k != "generated_at"}
    b = {k: v for k, v in existing.items() if k != "generated_at"}
    if a == b:
        corpus["generated_at"] = existing.get("generated_at", corpus["generated_at"])


def load_existing():
    if not JSON_PATH.exists():
        return None
    try:
        return json.loads(JSON_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", default=str(SEGMENT_DIR),
                    help="directory of segment records (default: segments/)")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="rebuild corpus/")
    mode.add_argument("--check", action="store_true", help="fail if corpus/ is stale")
    mode.add_argument("--character", help="print one character's corpus")
    args = ap.parse_args(argv)

    leads = load_leads()
    corpus = build_corpus(load_segments(args.dir), leads, load_pending(),
                          segment_dir=Path(args.dir).name)
    pin_unchanged_generated_at(corpus, load_existing())

    if args.character:
        wanted = snake_case(args.character)
        wanted = lead_alias_index(leads).get(wanted, wanted)
        for entry in corpus["characters"]:
            if entry["character"] == wanted:
                print(format_character(entry))
                return 0
        print(f"no indexed footage for {wanted!r}", file=sys.stderr)
        return 1

    json_text = json.dumps(corpus, indent=2) + "\n"
    md_text = render_markdown(corpus)

    if args.write:
        CORPUS_DIR.mkdir(exist_ok=True)
        JSON_PATH.write_text(json_text, encoding="utf-8")
        MD_PATH.write_text(md_text, encoding="utf-8")
        print(f"wrote {JSON_PATH.relative_to(REPO_ROOT)} and "
              f"{MD_PATH.relative_to(REPO_ROOT)} "
              f"({corpus['totals']['characters']} characters, "
              f"{len(corpus['unresolved'])} unresolved)")
        return 0

    stale = [p for p, text in ((JSON_PATH, json_text), (MD_PATH, md_text))
             if not p.exists() or p.read_text(encoding="utf-8") != text]
    if stale:
        for path in stale:
            print(f"error: {path.relative_to(REPO_ROOT)} is stale. Run "
                  "`python3 tools/corpus.py --write`.", file=sys.stderr)
        return 1
    print(f"corpus/ is up to date ({corpus['totals']['characters']} characters, "
          f"{len(corpus['unresolved'])} unresolved)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
