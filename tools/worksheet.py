#!/usr/bin/env python3
"""The tagger's worksheet: scaffold ``tags/<video_id>.json``, then say when it is done.

Why this is a separate module and not a subcommand of tools/annotate.py:
annotate.py owns the pipeline's side of the tagging seam — it detects beats,
writes keyframes, and replays a *finished* tag file into segments. This module
owns the tagger's side of the same seam: the file a person or a vision model
actually edits. The two change for different reasons (detector settings vs.
tagging ergonomics), annotate.py already carries three stages, and the repo's
convention is one tool per stage (brief.py, ingest.py, gaps.py, story.py).
What is genuinely shared — ``TAGGER_FIELDS``, ``keyframes_dir_for`` — is
imported from annotate rather than copied, so the skeleton can never drift
from what assembly will accept.

The worksheet removes the mechanical half of tagging. Before it, the tagger —
the most expensive stage in the loop — had to reconstruct the file's shape by
hand before making a single visual judgement: 60-70 beat-index string keys,
the keyframe each one refers to, the provenance map's shape. Now the skeleton
arrives with every beat present and paired with its keyframe path and
timecodes (from ``keyframes/<video_id>/beats.json``), and the tagger's time
goes to the part that cannot be automated: looking at frames.

What the skeleton pre-fills is the point, so read this before extending it:

* ``overlays`` is null, never ``[]``. It is the input to the ``clean`` gate,
  which must be POSITIVELY established — an untagged ``overlays`` derives
  ``clean = false`` (tools/derive.py). A skeleton that shipped ``overlays: []``
  would silently mark every untagged beat clean, and that is how a HUD ends up
  in a finished cut. ``[]`` must be earned by looking at the frame.
* ``character`` is null, never ``[]``. A character tag credits a real person
  for a shot they are in; it may only be set where someone is visibly in that
  frame.
* No derived field (``clean``, ``footage_tier``, ``traversal_hero``,
  ``casting``) can appear: ``assemble_segment`` raises on them by design.
* Nothing else is pre-filled either. The one tempting candidate,
  ``content_type``, looks video-scoped but is not: it feeds the footage_tier
  derivation (vocab/cleanliness.yaml), and the committed corpus shows taggers
  overriding the video record on most beats (the Final Shape launch trailer's
  record says ``trailer``; all 69 beats were judged ``cinematic``). Pre-filling
  it would anchor the tagger, and a lazily accepted anchor silently re-tiers
  footage. Null keeps the judgement with the judge. Nothing is lost: assembly
  still inherits the record's value for any field a finished file omits.

``check`` is the done-ness signal. A beat is unfilled while any tagger field
is absent or null — an explicitly empty list is a positive judgement ("no
overlays", "nobody identifiable"); null is "nobody has looked". It reports
which beats still need which fields, ``overlays`` first because it gates
everything, so a tagger knows when it is finished and scripts/make_video.sh
can report progress instead of a binary "no tags yet".

Per-beat ``_worksheet`` blocks (keyframe path, timecodes) are scaffolding, not
tags: JsonTagger strips underscore-prefixed keys at replay, so they never
reach a segment. They stay in the file afterwards as evidence of which frame
each judgement was made from.

Usage:
    python3 tools/worksheet.py generate <video_id> [--keyframes-dir DIR] [--out FILE] [--force]
    python3 tools/worksheet.py check tags/<video_id>.json [--keyframes-dir DIR] [--verbose]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.annotate import TAGGER_FIELDS, keyframes_dir_for  # noqa: E402

WORKSHEET_KEY = "_worksheet"
"""Per-beat scaffolding key. Underscore-prefixed keys are metadata about the
tagging task, never tags about the shot; JsonTagger strips them at replay."""


def load_manifest(keyframes_dir):
    """The beat manifest pass 1 wrote beside the stills.

    The worksheet is built from this file and no other source: a tag file is
    only valid against the shot list its own detection pass produced, and the
    manifest is the record of that pass.
    """
    manifest = Path(keyframes_dir) / "beats.json"
    if not manifest.exists():
        raise FileNotFoundError(
            f"no beat manifest at {manifest} — run pass 1 first:\n"
            "    python3 tools/annotate.py index --video media/<video_id>.mp4 "
            "--video-record videos/<video_id>.json"
        )
    with manifest.open(encoding="utf-8") as fh:
        return json.load(fh)


def _display_path(path):
    """Repo-relative where possible: the tagger reads this path, not a script."""
    path = Path(path)
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def build_worksheet(video_id, manifest, keyframes_dir):
    """Beat index (as a string) -> skeleton entry, one per beat in the manifest.

    Every tagger field starts null. See the module docstring for why null and
    not a default: ``overlays`` gates ``clean`` and must be positively
    established per frame, ``character`` credits a real person, and the one
    plausible video-scoped pre-fill (``content_type``) is shot-level in
    practice and feeds footage_tier, so anchoring it would guess past a visual
    judgement.
    """
    worksheet = {}
    for position, beat in enumerate(manifest):
        index = int(beat.get("beat_index", position))
        worksheet[str(index)] = {
            WORKSHEET_KEY: {
                "keyframe": _display_path(Path(keyframes_dir) / beat["keyframe"]),
                "start_sec": beat["start_sec"],
                "end_sec": beat["end_sec"],
                "start_tc": beat["start_tc"],
                "end_tc": beat["end_tc"],
            },
            **{field: None for field in TAGGER_FIELDS},
            "provenance": {},
        }
    return worksheet


def generate(video_id, keyframes_dir=None, out=None, force=False, log=print):
    """Write the skeleton tag file for a video. Returns the path written.

    Refuses to overwrite an existing file without ``force``: a tag file is
    hours of someone's visual judgement, and the worksheet is the *start* of
    that work, not a regeneration target.
    """
    record_path = REPO_ROOT / "videos" / f"{video_id}.json"
    if not record_path.exists():
        # A worksheet for a video with no record can never be assembled, so a
        # typo here would surface hours of tagging later. Fail fast instead.
        raise FileNotFoundError(
            f"no video record at {record_path} — ingest the video first "
            "(stage 2 of scripts/make_video.sh)"
        )
    keyframes_dir = Path(keyframes_dir) if keyframes_dir else keyframes_dir_for({"video_id": video_id})
    manifest = load_manifest(keyframes_dir)

    out = Path(out) if out else REPO_ROOT / "tags" / f"{video_id}.json"
    if out.exists() and not force:
        raise FileExistsError(
            f"{out} already exists — a tag file is finished or in-progress "
            "judgement, not something to regenerate over. Pass --force to "
            "replace it, or run `check` to see what is left."
        )

    worksheet = build_worksheet(video_id, manifest, keyframes_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        json.dump(worksheet, fh, indent=2)
        fh.write("\n")

    missing_stills = []
    for beat, entry in worksheet.items():
        keyframe = entry[WORKSHEET_KEY]["keyframe"]
        if not (REPO_ROOT / keyframe).exists() and not Path(keyframe).exists():
            missing_stills.append(beat)
    log(f"wrote {out}: {len(worksheet)} beats to fill")
    if missing_stills:
        log(f"WARNING: {len(missing_stills)} keyframe(s) named by the manifest are "
            f"missing on disk (first: beat {missing_stills[0]}) — the tagger "
            "cannot judge a frame it cannot see.")
    return out


def audit(tags_path, manifest=None):
    """Measure a tag file's completeness. Pure data in, report dict out.

    A field is unfilled when it is absent or null. An explicitly empty list is
    filled: ``overlays: []`` is the positive "this frame is clean" judgement
    the gate requires, and ``character: []`` is "nobody identifiable here".
    """
    with Path(tags_path).open(encoding="utf-8") as fh:
        tags = json.load(fh)

    unfilled, unknown_fields, bad_keys = {}, {}, []
    for key, entry in tags.items():
        if not key.isdigit():
            # A top-level key that is not a beat index inflates the count
            # verify_tags_match_detection relies on, so the file would be
            # refused at pass 2 even when every real beat is filled.
            bad_keys.append(key)
            continue
        missing = [f for f in TAGGER_FIELDS if entry.get(f) is None]
        if missing:
            unfilled[key] = missing
        extra = sorted(
            k for k in entry
            if k not in TAGGER_FIELDS and k != "provenance" and not k.startswith("_")
        )
        if extra:
            unknown_fields[key] = extra

    missing_entries, extra_entries = [], []
    if manifest is not None:
        expected = [str(int(b.get("beat_index", i))) for i, b in enumerate(manifest)]
        have = set(tags)
        missing_entries = [k for k in expected if k not in have]
        extra_entries = sorted((k for k in have if k not in expected),
                               key=lambda k: (not k.isdigit(), int(k) if k.isdigit() else 0))

    unready = set(unfilled) | set(unknown_fields)
    filled = len(tags) - len(bad_keys) - len(unready)
    return {
        "beats": len(tags) - len(bad_keys),
        "filled": filled,
        "unfilled": unfilled,
        "unknown_fields": unknown_fields,
        "bad_keys": bad_keys,
        "missing_entries": missing_entries,
        "extra_entries": extra_entries,
        "complete": not (unfilled or unknown_fields or bad_keys
                         or missing_entries or extra_entries),
    }


def check(tags_path, keyframes_dir=None, verbose=False, log=print):
    """Print the audit and return True when the tag file is ready for pass 2.

    The manifest is used when it is on disk, but its absence is not an error:
    videos indexed before the manifest existed have no beats.json, and their
    committed tag files are still checkable field by field.
    """
    manifest = None
    if keyframes_dir and (Path(keyframes_dir) / "beats.json").exists():
        manifest = load_manifest(keyframes_dir)
    report = audit(tags_path, manifest)

    total = report["beats"]
    log(f"{tags_path}: {report['filled']}/{total} beats filled")

    if report["complete"]:
        log("ready for pass 2: python3 tools/annotate.py index --video "
            "media/<video_id>.mp4 --video-record videos/<video_id>.json "
            f"--tags {tags_path}")
        return True

    # Field-frequency first: a tagger batching by axis ("I am doing overlays
    # for every beat now") reads this; overlays leads because it gates clean.
    counts = {}
    for fields in report["unfilled"].values():
        for field in fields:
            counts[field] = counts.get(field, 0) + 1
    if counts:
        ranked = sorted(counts, key=lambda f: (f != "overlays", -counts[f]))
        log("  still needed, by field: "
            + ", ".join(f"{f} ({counts[f]} beats)" for f in ranked))

    unfilled_keys = sorted(report["unfilled"], key=int)
    shown = unfilled_keys if verbose else unfilled_keys[:10]
    for key in shown:
        fields = report["unfilled"][key]
        if len(fields) == len(TAGGER_FIELDS):
            # The common case on a fresh skeleton; the by-field summary above
            # already lists what "everything" means.
            log(f'  beat "{key}": untouched')
        else:
            log(f'  beat "{key}": needs {", ".join(fields)}')
    if len(unfilled_keys) > len(shown):
        log(f"  ... and {len(unfilled_keys) - len(shown)} more beats (--verbose to list)")

    for key, fields in sorted(report["unknown_fields"].items(), key=lambda kv: int(kv[0])):
        log(f'  beat "{key}": {", ".join(fields)} is not a tagger field — '
            "assembly will refuse it (docs/taxonomy.md)")
    for key in report["bad_keys"]:
        log(f'  "{key}" is not a beat index — beat keys are strings "0".."{total - 1}"')
    if report["missing_entries"]:
        log(f"  no entry at all for beat(s): {', '.join(report['missing_entries'])}")
    if report["extra_entries"]:
        log(f"  beyond the manifest's {total} beats: {', '.join(report['extra_entries'])}")

    if "overlays" in counts or report["missing_entries"]:
        log("  `overlays` is the clean gate: a beat without it derives "
            "clean = false and leaves every cut. Use [] for a clean frame.")
    return False


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Scaffold a tag file for the tagger, then audit its completeness."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="write a skeleton tags/<video_id>.json")
    gen.add_argument("video_id", help="the video record's video_id")
    gen.add_argument("--keyframes-dir", default=None,
                     help="override keyframes/<video_id>/ (where beats.json lives)")
    gen.add_argument("--out", default=None,
                     help="override tags/<video_id>.json (e.g. to demonstrate without "
                          "touching a real tag file)")
    gen.add_argument("--force", action="store_true",
                     help="overwrite an existing tag file (their judgements are lost)")

    chk = sub.add_parser("check", help="report which beats are still unfilled")
    chk.add_argument("tags", help="the tag file to audit")
    chk.add_argument("--keyframes-dir", default=None,
                     help="cross-check against this dir's beats.json when present")
    chk.add_argument("--verbose", action="store_true", help="list every unfilled beat")

    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            generate(args.video_id, keyframes_dir=args.keyframes_dir,
                     out=args.out, force=args.force)
            return 0
        keyframes_dir = args.keyframes_dir
        if keyframes_dir is None:
            # Convention: tags/<video_id>.json audits against keyframes/<video_id>/.
            stem = Path(args.tags).stem
            candidate = keyframes_dir_for({"video_id": stem})
            if (candidate / "beats.json").exists():
                keyframes_dir = candidate
        return 0 if check(args.tags, keyframes_dir=keyframes_dir, verbose=args.verbose) else 1
    except (FileNotFoundError, FileExistsError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
