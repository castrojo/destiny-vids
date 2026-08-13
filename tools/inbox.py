#!/usr/bin/env python3
"""Which dictated Whisp notes have been seen, filed, or landed -- as a query.

The owner dictates work orders into the Whisp flatpak
(``~/.var/app/io.github.tanaybhomia.Whisp/data/whisp/notes/*.md``), one file
per dictation. Whisp is a microphone, not a backlog: a note has no queue, no
state, and no acknowledgement, so a note no agent happened to read was silently
lost -- the 2026-08-12->13 night lost a full dialogue round and a plate round
this way (the audit is #118/#119/#120; the rule it produced lives in
``docs/skills/intake.md``: a dictated note is not submitted until it is a
GitHub issue).

This tool is the receipt book. It scans the notes directory and keeps a
committed ledger (``inbox/ledger.json``) of ``note-id -> {sha256, mtime,
status}``, so "did an agent see this dictation?" is a file lookup instead of
an archaeology dig. Statuses:

* ``filed #N``   -- the note became GitHub issue N. The issue is the
  acknowledgement; the work may still be open, and that is fine.
* ``landed``     -- the work the note ordered is in the repo or delivered.
* ``superseded`` -- a later note or cut replaced it.
* ``ignored``    -- read, and deliberately not acted on (an empty note, the
  app's bundled welcome note).
* ``out-of-scope`` -- not destiny-vids work (the owner dictates everything
  into the same app).

A note whose content changed after its status was recorded is surfaced again:
an edit may carry new orders, and the old receipt says nothing about them.

The ledger commits a hash, an mtime and a status -- never the note's text.
The notes are the owner's words, and issue #121's ``blocked_on`` (owner
sign-off on committing identifying excerpts) is deliberately NOT waited on:
shipping the excerpt-free ledger needs no sign-off because it commits none of
the owner's words.

    python3 tools/inbox.py                     # report
    python3 tools/inbox.py --check             # unstatused/changed notes, exit 1
    python3 tools/inbox.py --json
    python3 tools/inbox.py --write             # add newly-dictated notes (unstatused)
    python3 tools/inbox.py --set faec "filed #118"   # record a status
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_NOTES_DIR = Path.home() / ".var/app/io.github.tanaybhomia.Whisp/data/whisp/notes"
DEFAULT_LEDGER = REPO_ROOT / "inbox" / "ledger.json"

LEDGER_VERSION = 1

PLAIN_STATUSES = ("landed", "superseded", "ignored", "out-of-scope")
STATUS_RE = re.compile(r"^(filed #\d+|" + "|".join(PLAIN_STATUSES) + r")$")

# TODO(owner): issue #121 is `blocked_on: owner sign-off that a committed
# ledger naming note excerpts is acceptable`. The ledger schema reserves an
# `excerpt` key on every entry so a short identifying excerpt can be recorded
# if the owner signs off; until then the writer emits null and nothing in this
# tool reads note contents into the ledger. Do not populate it speculatively.
ENTRY_KEYS = ("sha256", "mtime", "status", "excerpt")


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mtime(path):
    stamp = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return stamp.isoformat(timespec="seconds")


def scan_notes(notes_dir):
    """Every ``*.md`` in the Whisp notes dir, keyed by note id (filename stem).

    Read-only: the notes directory is the owner's data. Returns None when the
    directory does not exist (a machine without the flatpak), which callers
    treat as "cannot scan" rather than "every note is gone".
    """
    notes_dir = Path(notes_dir)
    if not notes_dir.is_dir():
        return None
    return {
        path.stem: {"sha256": _hash(path), "mtime": _mtime(path)}
        for path in sorted(notes_dir.glob("*.md"))
    }


def load_ledger(path):
    """The committed ledger, or an empty skeleton when none exists yet."""
    path = Path(path)
    if not path.exists():
        return {"version": LEDGER_VERSION, "notes": {}}
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def write_ledger(ledger, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = {k: ledger["notes"][k] for k in sorted(ledger["notes"])}
    out = {**ledger, "notes": ordered}
    with path.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=2) + "\n")


def _new_entry(observed):
    return {"sha256": observed["sha256"], "mtime": observed["mtime"],
            "status": None, "excerpt": None}


def find_unstatused(notes, ledger):
    """Scanned notes with no status in the ledger -- the punch list."""
    entries = ledger.get("notes", {})
    return sorted(nid for nid in notes
                  if not (entries.get(nid) or {}).get("status"))


def find_changed(notes, ledger):
    """Statused notes whose content no longer matches the recorded hash.

    A note edited after it was filed may carry new orders; the receipt only
    covers the content it was recorded against.
    """
    entries = ledger.get("notes", {})
    return sorted(
        nid for nid, observed in notes.items()
        if (entries.get(nid) or {}).get("status")
        and entries[nid].get("sha256") != observed["sha256"]
    )


def find_absent(notes, ledger):
    """Ledger entries whose note file is gone from the notes directory."""
    return sorted(nid for nid in ledger.get("notes", {}) if nid not in notes)


def reconcile(notes, ledger):
    """Add newly-dictated notes to the ledger, unstatused. Never mutates an
    existing entry: a recorded hash is the content a status was set against,
    and refreshing it silently would erase the evidence ``find_changed``
    reports on."""
    added = []
    entries = ledger.setdefault("notes", {})
    for nid, observed in notes.items():
        if nid not in entries:
            entries[nid] = _new_entry(observed)
            added.append(nid)
    return added


def resolve_note_id(prefix, notes, ledger):
    """The one known note id starting with ``prefix`` (like a git short hash)."""
    known = sorted(set(notes) | set(ledger.get("notes", {})))
    exact = [nid for nid in known if nid == prefix]
    if exact:
        return exact[0]
    matches = [nid for nid in known if nid.startswith(prefix)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValueError(f"no note id matches {prefix!r}")
    raise ValueError(f"{prefix!r} is ambiguous: {', '.join(matches)}")


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------

def _status_group(entry):
    status = entry.get("status")
    if not status:
        return "unstatused"
    return status.split()[0] if status.startswith("filed #") else status


def format_report(notes, ledger):
    """The inbox as text: what needs attention first, then the ledger by status."""
    entries = ledger.get("notes", {})
    unstatused = find_unstatused(notes, ledger)
    changed = find_changed(notes, ledger)
    absent = find_absent(notes, ledger)

    lines = []
    if not unstatused and not changed:
        lines.append(f"every dictated note has a status ({len(entries)} ledgered).")
    else:
        if unstatused:
            lines.append(f"unstatused ({len(unstatused)})")
            for nid in unstatused:
                lines.append(f"  {nid} (mtime {notes[nid]['mtime']})")
        if changed:
            lines.append(f"changed since statused ({len(changed)})")
            for nid in changed:
                lines.append(f"  {nid} (status: {entries[nid]['status']})")
    if absent:
        lines.append(f"ledgered but absent from the notes dir ({len(absent)})")
        for nid in absent:
            lines.append(f"  {nid} (status: {entries[nid].get('status')})")

    by_status = {}
    for nid, entry in sorted(entries.items()):
        if entry.get("status"):
            by_status.setdefault(_status_group(entry), []).append(
                f"  {nid} ({entry['status']})")
    if by_status:
        lines.append("")
        for group in ("filed",) + PLAIN_STATUSES:
            if group in by_status:
                lines.append(f"{group} ({len(by_status[group])})")
                lines.extend(by_status[group])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true",
                        help="machine-readable inbox state")
    parser.add_argument("--check", action="store_true",
                        help="list notes with no status (or edited since their "
                             "status was recorded) and exit non-zero")
    parser.add_argument("--write", action="store_true",
                        help="add newly-dictated notes to the ledger, unstatused")
    parser.add_argument("--set", nargs=2, metavar=("NOTE_ID", "STATUS"),
                        help="record a status for a note, e.g. --set faec 'filed #118'")
    parser.add_argument("--notes-dir", default=str(DEFAULT_NOTES_DIR))
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    args = parser.parse_args(argv)

    notes = scan_notes(args.notes_dir)
    scannable = notes is not None
    if not scannable:
        # A machine without the flatpak is not a notes dir full of deletions:
        # report from the ledger alone and never mark its entries absent.
        print(f"no Whisp notes directory at {args.notes_dir} -- nothing to scan",
              file=sys.stderr)
        notes = {}
    ledger = load_ledger(args.ledger)

    if args.set:
        prefix, status = args.set
        if not STATUS_RE.match(status):
            print(f"invalid status {status!r}: expected 'filed #N' or one of "
                  f"{', '.join(PLAIN_STATUSES)}", file=sys.stderr)
            return 2
        try:
            nid = resolve_note_id(prefix, notes, ledger)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        if nid not in notes:
            print(f"note {nid} is absent from {args.notes_dir}; refusing to "
                  "status content that cannot be hashed", file=sys.stderr)
            return 2
        ledger.setdefault("notes", {})[nid] = _new_entry(notes[nid])
        ledger["notes"][nid]["status"] = status
        write_ledger(ledger, args.ledger)
        print(f"{nid}: {status}")
        return 0

    if args.write:
        added = reconcile(notes, ledger)
        write_ledger(ledger, args.ledger)
        for nid in added:
            print(f"new: {nid}")
        if not added:
            print(f"ledger already covers every note in {args.notes_dir}")
        return 0

    state = {
        "unstatused": find_unstatused(notes, ledger),
        "changed": find_changed(notes, ledger),
        "absent": find_absent(notes, ledger) if scannable else [],
        "notes": ledger.get("notes", {}),
    }
    if args.json:
        print(json.dumps(state, indent=2))
    elif not scannable:
        entries = ledger.get("notes", {})
        print(f"cannot scan; ledger holds {len(entries)} note(s), "
              "their statuses unchanged since last scan")
    else:
        print(format_report(notes, ledger))
    if args.check and (state["unstatused"] or state["changed"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
