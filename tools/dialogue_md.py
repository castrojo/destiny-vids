#!/usr/bin/env python3
"""Recovered dialogue <-> Markdown, so the owner can rewrite it in an editor.

Each video keeps its conversation in one folder, ``dialogue/<video_id>/``:

    DIALOGUE.md    the conversation, as the owner edits it
    dialogue.json  the provenance record the pipeline reads

``dialogue.json`` is the source of truth for every word this repo puts on
screen, but it is a provenance record first and a script second: each cue
carries source timecodes, a recovery method and per-line evidence for who is
speaking. That is the right shape for the pipeline and the wrong shape for a
person with an opinion about the wording. ``DIALOGUE.md`` is the other half.

So: ``export`` writes the conversation as Markdown, ``apply`` reads it back.
The timecodes and the evidence never appear as things to edit -- they ride
along in the heading and are restored verbatim -- and a line the owner changes
is recorded as changed rather than silently overwriting the recovered text:

    "text":           what goes on screen
    "text_source":    "recovered" (default) or "owner_supplied"
    "recovered_text": the original, kept whenever the owner replaced it

That last field is the point. The repo's rule is that on-screen copy is never
*invented by an agent*; the owner supplying their own line is allowed, and the
honest way to allow it is to keep both versions and say which is which.

    python3 tools/dialogue_md.py export <video_id>   # writes DIALOGUE.md
    python3 tools/dialogue_md.py apply  <video_id>   # reads it back
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.dialogue import (  # noqa: E402
    MARKDOWN_NAME,
    load_dialogue,
    markdown_path,
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
    rf"(?P<start>[0-9:.]+)\s*{ARROW}\s*(?P<end>[0-9:.]+)\s*$"
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
    """``Osiris (Bob Killen)`` -- the character, and who is credited for them.

    The person is shown because that is the name the chat card will carry, so
    the owner is editing what they will actually see.
    """
    character = cue.get("character") or ""
    entry = leads.get(character) or {}
    person = (entry.get("plate") or {}).get("name") or entry.get("display_name")
    pretty = character.replace("_", " ").title()
    return f"{pretty} ({person})" if person else pretty


def _resolve_character(label, leads):
    """A heading's speaker back to a canonical ``leads`` key.

    Accepts the character name, any of its ``aka`` spellings, or the credited
    person's name, so the owner can retype whichever half they remember.
    """
    name = re.sub(r"\s*\(.*?\)\s*$", "", label).strip()
    key = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    for character, entry in leads.items():
        if key == character or key in {
            re.sub(r"[^a-z0-9]+", "_", a.lower()).strip("_")
            for a in (entry.get("aka") or [])
        }:
            return character
        people = {
            (entry.get("plate") or {}).get("name"),
            entry.get("display_name"),
        }
        if name in {p for p in people if p}:
            return character
    return None


def export(data, leads):
    """Dialogue record -> Markdown."""
    lines = [
        f"# {data['video_id']} - on-screen conversation",
        "",
        "Rewrite the line under each heading. Everything else is bookkeeping:",
        "",
        "- **Keep the heading.** The id and the timecodes are what put a line",
        "  back on the right frame; change them only to re-time a line.",
        "- **Change the speaker** by renaming it in the heading (the character,",
        "  or the person credited for them).",
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
    for cue in data["cues"]:
        lines += [
            f"## {cue['id']} | {_speaker_label(cue, leads)} | "
            f"{format_tc(cue['start_sec'])} -> {format_tc(cue['end_sec'])}",
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
    flush()

    seen = set()
    for cue in cues:
        if cue["id"] in seen:
            raise ValueError(f"duplicate cue id {cue['id']!r}")
        seen.add(cue["id"])
        if cue["end_sec"] <= cue["start_sec"]:
            raise ValueError(f"cue {cue['id']!r} ends before it starts")
        if not cue["text"]:
            raise ValueError(f"cue {cue['id']!r} has no text")
    return cues


def merge(data, edited):
    """Edited cues folded back into the record, keeping every provenance field.

    Returns ``(new_data, changes)``. Nothing is discarded quietly: a cue the
    owner deleted moves to ``dropped`` with a reason, and a cue whose wording
    they changed keeps the recovered text beside the new line.
    """
    original = {cue["id"]: cue for cue in data["cues"]}
    changes, cues = [], []

    for cue in edited:
        previous = original.get(cue["id"])
        if previous is None:
            cues.append({
                "id": cue["id"],
                "start_sec": round(cue["start_sec"], 2),
                "end_sec": round(cue["end_sec"], 2),
                "character": cue["character"],
                "evidence": "owner_supplied",
                "text": cue["text"],
                "text_source": "owner_supplied",
            })
            changes.append(f"  + {cue['id']} added: {cue['text'][:56]}")
            continue

        merged = dict(previous)
        recovered = previous.get("recovered_text", previous.get("text", ""))
        if cue["text"] != previous.get("text"):
            merged["text"] = cue["text"]
            merged["text_source"] = "owner_supplied"
            merged["recovered_text"] = recovered
            changes.append(f"  ~ {cue['id']} reworded: {cue['text'][:56]}")
        if cue["character"] != previous.get("character"):
            merged["character"] = cue["character"]
            merged["evidence"] = "owner_supplied"
            changes.append(
                f"  ~ {cue['id']} speaker: {previous.get('character')} -> "
                f"{cue['character']}")
        for field, value in (("start_sec", cue["start_sec"]),
                             ("end_sec", cue["end_sec"])):
            if abs(float(previous.get(field, 0)) - value) > 0.005:
                merged[field] = round(value, 2)
                changes.append(f"  ~ {cue['id']} {field}: {value:.2f}")
        cues.append(merged)

    kept = {cue["id"] for cue in edited}
    dropped = list(data.get("dropped") or [])
    for cue_id, cue in original.items():
        if cue_id in kept:
            continue
        dropped.append({
            "id": cue_id,
            "start_sec": cue["start_sec"],
            "end_sec": cue["end_sec"],
            "raw": cue.get("recovered_text", cue.get("text", "")),
            "reason": "removed by the owner while rewriting the conversation",
        })
        changes.append(f"  - {cue_id} removed")

    cues.sort(key=lambda cue: cue["start_sec"])
    return {**data, "cues": cues, "dropped": dropped}, changes


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

    args = ap.parse_args(argv)

    from tools.derive import load_leads

    leads = load_leads()
    data = load_dialogue(args.video_id)

    if args.command == "export":
        out = Path(args.out) if args.out else markdown_path(args.video_id)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(export(data, leads), encoding="utf-8")
        print(f"wrote {out} ({len(data['cues'])} line(s))")
        return 0

    source = Path(args.markdown) if args.markdown else markdown_path(args.video_id)
    edited = parse(source.read_text(encoding="utf-8"), leads)
    updated, changes = merge(data, edited)
    for change in changes:
        print(change)
    if not changes:
        print("  no changes")
    if args.dry_run:
        return 0
    path = record_path(args.video_id)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(updated, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {path} ({len(updated['cues'])} line(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
