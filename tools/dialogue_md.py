#!/usr/bin/env python3
"""Recovered dialogue <-> Markdown, so the owner can rewrite it in an editor.

Each video keeps its conversation in one folder, ``dialogue/<video_id>/``:

    DIALOGUE.md         the conversation, as the owner edits it
    dialogue.json       the immutable source-evidence record
    presentation.json   sequence, film start, delivered holds and owner pins

``dialogue.json`` is the source of truth for every word this repo puts on
screen, but it is a provenance record first and a script second: each cue
carries source timecodes, a recovery method and per-line evidence for who is
speaking. That is the right shape for the pipeline and the wrong shape for a
person with an opinion about the wording. ``DIALOGUE.md`` is the other half.

So: ``export`` writes the conversation as Markdown, ``apply`` reads it back.
The source timecodes and the evidence never appear as things to edit -- they
ride along in the heading and ``apply`` refuses any change to them -- and a
line the owner changes is recorded as changed rather than silently
overwriting the recovered text:

    "text":           what goes on screen
    "text_source":    "recovered" (default), "owner_supplied", or
                      "placeholder" -- a beat blocked out before its words
                      exist. A blank line is NOT an error: it used to fail the
                      whole file, so one unwritten line cost every other edit
                      in it. It is kept, marked, and rendered as lorem
                      credited to nobody (`tools/placeholder.py`).
    "recovered_text": the original, kept whenever the owner replaced it --
                      including when they cleared the line back to a slot

That last field is the point. The repo's rule is that on-screen copy is never
*invented by an agent*; the owner supplying their own line is allowed, and the
honest way to allow it is to keep both versions and say which is which.

    python3 tools/dialogue_md.py export <video_id>   # writes DIALOGUE.md
    python3 tools/dialogue_md.py apply  <video_id>   # reads it back
    python3 tools/dialogue_md.py restore-source-times <video_id> --from-ref <ref>
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.dialogue import (  # noqa: E402
    MARKDOWN_NAME,
    load_dialogue,
    load_presentation,
    markdown_path,
    ordered_cues,
    presentation_path,
    presentation_pin,
    record_path,
)

# "## d02 | Osiris (Bob Killen) | 0:42.00 -> 0:45.55"
#
# Tolerant on purpose: a Markdown editor, a phone keyboard and a copy-paste all
# produce slightly different dashes and arrows, and losing an edit to a typo in
# punctuation the owner was not asked to preserve would be absurd.
DASH = r"[|\u2014\u2013-]"
ARROW = r"(?:->|\u2192|\u2013|\u2014|to)"
HEADING = re.compile(
    rf"^\#\#\s+(?P<id>\S+)\s*{DASH}\s*(?P<speaker>[^|\u2014\u2013]+?)\s*{DASH}\s*"
    rf"(?P<start>[0-9:.]+)\s*{ARROW}\s*(?P<end>[0-9:.]+?)"
    rf"(?:\s*{DASH}\s*pin\s+(?P<pin>[0-9:.]+))?\s*$"
)


def format_tc(seconds):
    """Seconds -> ``M:SS.ss``. Readable, and parsed back without loss."""
    seconds = float(seconds)
    return f"{int(seconds // 60)}:{seconds % 60:05.2f}"


def parse_tc(text):
    """``M:SS.ss`` or bare seconds -> float."""
    text = text.strip()
    if ":" not in text:
        return float(text)
    minutes, _, rest = text.partition(":")
    return int(minutes) * 60 + float(rest)


def _speaker_label(cue, leads):
    """The character key is the stable, unambiguous dialogue identity."""
    return cue.get("character") or ""


def _resolve_character(label, leads):
    """A heading's speaker back to a canonical ``leads`` key.

    Accepts the character name, any ``aka`` spelling, or an unambiguous bound
    login.
    """
    name = re.sub(r"\s*\(.*?\)\s*$", "", label).strip()
    key = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    for character, entry in leads.items():
        if key == character or key in {
            re.sub(r"[^a-z0-9]+", "_", a.lower()).strip("_")
            for a in (entry.get("aka") or [])
        }:
            return character
    matches = [
        character for character, entry in leads.items()
        if key == re.sub(r"[^a-z0-9]+", "_",
                         str(entry.get("person") or "").lower()).strip("_")
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(
            f"{label.strip()!r} is an ambiguous GitHub login for "
            f"{', '.join(sorted(matches))}; use the character key"
        )
    return None


def replace(data, edited):
    """Replace a recovered conversation with owner-authored copy."""
    current = _cue_index(data["cues"], "current record")
    edited_by_id = _cue_index(edited, "edited markdown")

    for previous in data["cues"]:
        cue = edited_by_id.get(previous["id"])
        if cue is None:
            continue
        if (abs(float(cue["start_sec"]) - float(previous["start_sec"])) > 0.005
                or abs(float(cue["end_sec"]) - float(previous["end_sec"])) > 0.005):
            raise ValueError(
                f"{cue['id']}: source timecodes are evidence; "
                "restore them from a git ref"
            )

    cues = []
    for cue in edited:
        previous = current.get(cue["id"])
        entry = {
            "id": cue["id"],
            "start_sec": previous["start_sec"] if previous else round(cue["start_sec"], 2),
            "end_sec": previous["end_sec"] if previous else round(cue["end_sec"], 2),
            "character": cue["character"],
            "evidence": "owner_supplied",
            "text": cue["text"],
            "text_source": "owner_supplied",
        }
        cues.append(entry)
    return {
        **data,
        "source_rights_note": (
            "Dialogue and speaker assignments supplied by the project owner. "
            "This file stores timed metadata, not audio."
        ),
        "text_source": {
            "method": "owner_supplied",
            "note": "The project owner replaced the complete conversation.",
        },
        "speaker_source": {
            "method": "owner_supplied",
            "note": "The project owner supplied both speaker bindings.",
        },
        "cues": cues,
        "dropped": [],
    }


def export(data, leads, presentation=None):
    """Dialogue record -> Markdown."""
    cues = ordered_cues(data["cues"], presentation) if presentation else data["cues"]
    lines = [
        f"# {data['video_id']} - on-screen conversation",
        "",
        "Rewrite the line under each heading. Everything else is bookkeeping:",
        "",
        "- **Keep the heading.** The id and the source timecodes are evidence;",
        "  `apply` refuses edits to them. Restore them from a git ref instead.",
        "- **Change the speaker** by renaming it in the heading (the character,",
        "  or the person credited for them).",
        "- **Reorder sections** to change the conversation sequence. The source",
        "  record stays put; `presentation.json` carries the order.",
        "- **Pin a line to an exact film moment** with a fourth heading",
        "  segment: `| pin 1:57.00`. The pin lives in `presentation.json` and",
        "  sets where the line starts on the film; any explicit delivered-hold",
        "  preservation lives there too. Remove the segment to",
        "  unpin. Only pin the lines that must land exactly -- an unpinned line",
        "  flows with the conversation and rides out every card move.",
        "- **Delete a whole section** to drop that line from the cut.",
        "- A line you change is recorded as yours; the recovered wording is kept",
        "  beside it, never overwritten.",
        "",
        "Re-apply with:",
        "",
        "```",
        f"python3 tools/dialogue_md.py apply {data['video_id']}",
        "```",
        "",
    ]
    for cue in cues:
        heading = (f"## {cue['id']} | {_speaker_label(cue, leads)} | "
                   f"{format_tc(cue['start_sec'])} -> {format_tc(cue['end_sec'])}")
        pin = presentation_pin(cue["id"], presentation) if presentation else cue.get("pin_sec")
        if pin is not None:
            heading += f" | pin {format_tc(pin)}"
        lines += [
            heading,
            "",
            (cue.get("text") or "").strip(),
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"


def parse(text, leads):
    """Markdown -> ``[{id, character, start_sec, end_sec, text}]``.

    Raises on a heading whose speaker is not a cast character: an uncast name
    would silently produce no card at render time, which is exactly the kind of
    quiet loss this repo refuses.
    """
    cues, current, body = [], None, []

    def flush():
        if current is not None:
            current["text"] = " ".join(
                line.strip() for line in body if line.strip()
            ).strip()
            cues.append(current)

    for line in text.splitlines():
        match = HEADING.match(line)
        if not match:
            if current is not None:
                body.append(line)
            continue
        flush()
        body = []
        character = _resolve_character(match["speaker"], leads)
        if character is None:
            raise ValueError(
                f"{match['id']}: {match['speaker'].strip()!r} is not a cast "
                f"character in vocab/casting.yaml"
            )
        current = {
            "id": match["id"].strip(),
            "character": character,
            "start_sec": parse_tc(match["start"]),
            "end_sec": parse_tc(match["end"]),
        }
        if match["pin"]:
            current["pin_sec"] = parse_tc(match["pin"])
    flush()

    seen = set()
    placeholders = []
    for cue in cues:
        if cue["id"] in seen:
            raise ValueError(f"duplicate cue id {cue['id']!r}")
        seen.add(cue["id"])
        if cue["end_sec"] <= cue["start_sec"]:
            raise ValueError(f"cue {cue['id']!r} ends before it starts")
        if not cue["text"]:
            # A line the owner has not written yet is NOT an error, and used
            # to fail the whole file -- so one blank line cost every other
            # edit in it. It becomes a placeholder: the timecodes and the
            # speaker evidence are kept, the words are left empty, and
            # `text_source` says so. The lorem is NOT baked in here on
            # purpose. `tools/placeholder.py` fills it at render time, which
            # is also where it swaps the speaker for `TBD` -- bake the words
            # in and the plate would render lorem under this cue's real
            # character, which is the one thing a placeholder may never do.
            cue["text_source"] = "placeholder"
            placeholders.append(cue["id"])
    if placeholders:
        print(f"dialogue: {len(placeholders)} cue(s) with no words yet -- "
              f"kept as placeholders: {', '.join(placeholders)}",
              file=sys.stderr)
    return cues


def _cue_index(cues, label):
    index = {}
    for cue in cues:
        cue_id = cue["id"]
        if cue_id in index:
            raise ValueError(f"duplicate cue id {cue_id!r} in {label}")
        index[cue_id] = cue
    return index


def merge(data, edited):
    """Edited cues folded back into the record, keeping every provenance field.

    Returns ``(new_data, changes)``. Nothing is discarded quietly: a cue the
    owner deleted moves to ``dropped`` with a reason, and a cue whose wording
    they changed keeps the recovered text beside the new line.

    Restoring is the same move backwards, and it has to be just as complete: a
    line the owner brings back leaves ``dropped`` entirely. Leaving the entry
    behind would record one line as both spoken and retired, which is a record
    that contradicts itself about a real person's words.
    """
    original = _cue_index(data["cues"], "current record")
    retired = _cue_index(data.get("dropped") or [], "dropped cues")
    edited_by_id = _cue_index(edited, "edited markdown")
    changes, cues, restored = [], [], set()

    for previous in data["cues"]:
        cue_id = previous["id"]
        cue = edited_by_id.get(cue_id)
        if cue is None:
            continue

        if (abs(float(cue["start_sec"]) - float(previous["start_sec"])) > 0.005
                or abs(float(cue["end_sec"]) - float(previous["end_sec"])) > 0.005):
            raise ValueError(
                f"{cue['id']}: source timecodes are evidence; "
                "restore them from a git ref"
            )

        merged = dict(previous)
        recovered = previous.get("recovered_text", previous.get("text", ""))
        if cue["text"] != previous.get("text"):
            merged["text"] = cue["text"]
            merged["text_source"] = ("placeholder" if not cue["text"]
                                     else "owner_supplied")
            merged["recovered_text"] = recovered
            changes.append(
                f"  ~ {cue['id']} "
                + ("cleared to a placeholder" if not cue["text"]
                   else f"reworded: {cue['text'][:56]}"))
        if cue["character"] != previous.get("character"):
            merged["character"] = cue["character"]
            merged["evidence"] = "owner_supplied"
            changes.append(
                f"  ~ {cue['id']} speaker: {previous.get('character')} -> "
                f"{cue['character']}")
        cues.append(merged)

    dropped = []
    for cue in data.get("dropped") or []:
        if cue["id"] not in edited_by_id:
            dropped.append(cue)

    current_ids = {cue["id"] for cue in data["cues"]}
    for cue in edited:
        if cue["id"] in current_ids:
            continue

        blank = not cue["text"]
        added = {
            "id": cue["id"],
            "start_sec": round(cue["start_sec"], 2),
            "end_sec": round(cue["end_sec"], 2),
            "character": cue["character"],
            "evidence": "owner_supplied",
            "text": cue["text"],
            "text_source": "placeholder" if blank else "owner_supplied",
        }
        was_dropped = retired.get(cue["id"])
        if was_dropped is not None:
            restored.add(cue["id"])
            raw = was_dropped.get("raw", "")
            if raw and raw != cue["text"]:
                added["recovered_text"] = raw
            changes.append(
                f"  ^ {cue['id']} restored from dropped: {cue['text'][:56]}")
        else:
            changes.append(
                f"  + {cue['id']} added: "
                f"{'(placeholder -- no words yet)' if blank else cue['text'][:56]}")
        cues.append(added)

    for cue in data["cues"]:
        if cue["id"] in edited_by_id:
            continue
        dropped.append({
            "id": cue["id"],
            "start_sec": cue["start_sec"],
            "end_sec": cue["end_sec"],
            "raw": cue.get("recovered_text", cue.get("text", "")),
            "reason": "removed by the owner while rewriting the conversation",
        })
        changes.append(f"  - {cue['id']} removed")

    dropped = [cue for cue in dropped if cue["id"] not in restored]
    return {**data, "cues": cues, "dropped": dropped}, changes


def merge_presentation(presentation, edited):
    """Edited headings folded back into presentation.json."""
    previous_sequence = presentation.get("sequence") or []
    next_sequence = [cue["id"] for cue in edited]
    previous_pins = presentation.get("pins") or {}
    next_pins = {
        cue["id"]: round(cue["pin_sec"], 2)
        for cue in edited if cue.get("pin_sec") is not None
    }

    changes = []
    for cue_id in next_sequence:
        before = previous_pins.get(cue_id)
        after = next_pins.get(cue_id)
        if before is None and after is None:
            continue
        if before is None and after is not None:
            changes.append(f"  ~ {cue_id} pin_sec: {after:.2f}")
            continue
        if before is not None and after is None:
            changes.append(f"  ~ {cue_id} unpinned")
            continue
        if abs(float(before) - float(after)) > 0.005:
            changes.append(f"  ~ {cue_id} pin_sec: {after:.2f}")
    for cue_id in previous_pins:
        if cue_id in next_sequence:
            continue
        if cue_id not in next_pins:
            changes.append(f"  ~ {cue_id} unpinned")
    if next_sequence != previous_sequence:
        changes.append(f"  ! sequence: {' '.join(next_sequence)}")
    return {**presentation, "sequence": next_sequence, "pins": next_pins}, changes


def restore_source_times(data, source):
    """Copy only source windows by cue id from another dialogue record."""
    source_by_id = _cue_index(source["cues"], "restore source")
    _cue_index(data["cues"], "current record")
    cues, changes = [], []
    for cue in data["cues"]:
        source_cue = source_by_id.get(cue["id"])
        if source_cue is None:
            raise ValueError(f"{cue['id']}: missing from restore source")
        updated = dict(cue)
        start = round(float(source_cue["start_sec"]), 2)
        end = round(float(source_cue["end_sec"]), 2)
        if (round(float(cue["start_sec"]), 2), round(float(cue["end_sec"]), 2)) != (start, end):
            changes.append(
                f"  ~ {cue['id']} source: {float(cue['start_sec']):.2f}-"
                f"{float(cue['end_sec']):.2f} -> {start:.2f}-{end:.2f}"
            )
            updated["start_sec"] = start
            updated["end_sec"] = end
        cues.append(updated)
    return {**data, "cues": cues}, changes


def load_dialogue_from_ref(video_id, from_ref):
    relpath = f"dialogue/{video_id}/dialogue.json"
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", f"{from_ref}:{relpath}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip() or (
            f"could not load {relpath} from {from_ref}"
        )
        raise ValueError(message)
    return json.loads(result.stdout)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Round-trip recovered dialogue through Markdown.")
    sub = ap.add_subparsers(dest="command", required=True)

    e = sub.add_parser("export", help=f"dialogue.json -> {MARKDOWN_NAME}")
    e.add_argument("video_id")
    e.add_argument("--out", default=None,
                   help=f"default: dialogue/<video_id>/{MARKDOWN_NAME}")

    a = sub.add_parser("apply", help=f"{MARKDOWN_NAME} -> dialogue.json")
    a.add_argument("video_id")
    a.add_argument("markdown", nargs="?", default=None,
                   help=f"default: dialogue/<video_id>/{MARKDOWN_NAME}")
    a.add_argument("--dry-run", action="store_true",
                   help="report what would change without writing")
    a.add_argument("--replace", action="store_true",
                   help="replace the complete recovered conversation with owner-authored copy")

    r = sub.add_parser(
        "restore-source-times",
        help="copy only start_sec/end_sec from dialogue.json at a git ref",
    )
    r.add_argument("video_id")
    r.add_argument("--from-ref", required=True)

    args = ap.parse_args(argv)

    from tools.derive import load_leads

    if args.command == "export":
        leads = load_leads()
        data = load_dialogue(args.video_id)
        presentation = load_presentation(args.video_id)
        out = Path(args.out) if args.out else markdown_path(args.video_id)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(export(data, leads, presentation), encoding="utf-8")
        print(f"wrote {out} ({len(data['cues'])} line(s))")
        return 0

    data = load_dialogue(args.video_id)
    if args.command == "restore-source-times":
        updated, changes = restore_source_times(
            data, load_dialogue_from_ref(args.video_id, args.from_ref))
        for change in changes:
            print(change)
        if not changes:
            print("  no changes")
        path = record_path(args.video_id)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(updated, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        print(f"wrote {path} ({len(updated['cues'])} line(s))")
        return 0

    leads = load_leads()
    presentation = load_presentation(args.video_id)
    source = Path(args.markdown) if args.markdown else markdown_path(args.video_id)
    edited = parse(source.read_text(encoding="utf-8"), leads)
    if args.replace:
        updated = replace(data, edited)
        changes = ["  replaced complete conversation with owner-authored copy"]
    else:
        updated, changes = merge(data, edited)
    updated_presentation, presentation_changes = merge_presentation(
        presentation, edited)
    changes = [*changes, *presentation_changes]
    for change in changes:
        print(change)
    if not changes:
        print("  no changes")
    if args.dry_run:
        return 0
    record = record_path(args.video_id)
    with record.open("w", encoding="utf-8") as fh:
        json.dump(updated, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    plan = presentation_path(args.video_id)
    with plan.open("w", encoding="utf-8") as fh:
        json.dump(updated_presentation, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {record} ({len(updated['cues'])} line(s))")
    print(f"wrote {plan}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
