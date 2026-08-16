"""The no-narration rule applies to records, not just docs.

``AGENTS.md`` says documentation describes the current state, never the sequence
of states that produced it -- "if a sentence would start 'v2.6 made...', it does
not belong in a doc". Nothing enforced that in ``stories/*.json`` and
``music/*.json``, which carry far more prose than the docs tree does, so
narration flowed downhill into the ungated path: at the time this test was
written the records held ~114,000 characters of long-form prose and
``megacut.json`` was 71% prose by bytes.

The prose itself is wanted. A record that says *"Owner 2026-08-14, verbatim:
'...'"* or *"FRAME-PINNED: frames 373-445"* is the audit trail proving copy was
reproduced rather than invented, and it belongs beside the data it describes.
What is banned is the same thing that is banned in a doc: how the file came to
look this way. That is git's job.

The one sanctioned exception is ``_version`` -- ``AGENTS.md`` names it as where
build history goes.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Keys whose value is prose a human reads, rather than data a tool consumes.
PROSE_KEYS = {"note", "notes", "detail", "why", "rationale", "comment"}

# Where build history is allowed to live, per AGENTS.md.
EXEMPT_KEYS = {"_version"}

NARRATION = [
    (re.compile(r"\bv\d+\.\d+\b"),
     "a version number: build history belongs in git and in `_version`"),
    (re.compile(r"\bAS OF v", re.I),
     "'AS OF v...': state what is true, not when it became true"),
    (re.compile(r"\b(used to|it used to)\b", re.I),
     "'used to': describes a previous state"),
    (re.compile(r"\bformerly\b", re.I), "'formerly': describes a previous state"),
    (re.compile(r"\bpreviously\b", re.I), "'previously': describes a previous state"),
    (re.compile(r"\bfirst shipped\b", re.I),
     "'first shipped': describes a previous state"),
    (re.compile(r"\bwas REPLACED\b"),
     "'was REPLACED': say what the value is now"),
]


def record_files() -> list[Path]:
    files = sorted((REPO_ROOT / "stories").rglob("*.json"))
    files += sorted((REPO_ROOT / "music").glob("*.json"))
    return files


def prose_fields(path: Path):
    """Yield (json_path, text) for every long prose string in a record."""
    try:
        doc = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):  # validated by test_index_integrity
        return

    def walk(node, key, trail):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, k, trail + [k])
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, key, trail + [str(i)])
        elif isinstance(node, str) and key is not None:
            if key in EXEMPT_KEYS:
                return
            is_prose = key.startswith("_") or key in PROSE_KEYS
            # Short strings are values (a title, a path), not prose.
            if is_prose and len(node) > 200:
                yield_to.append((".".join(trail), node))

    yield_to: list[tuple[str, str]] = []
    walk(doc, None, [])
    return yield_to


@pytest.mark.parametrize(
    "path", record_files(), ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_record_prose_describes_the_current_state(path: Path):
    """A record's prose says what is true, never how it got that way."""
    offences = []
    for trail, text in prose_fields(path) or []:
        for pattern, why in NARRATION:
            m = pattern.search(text)
            if not m:
                continue
            i = m.start()
            offences.append(
                f"  [{trail}] {why}\n"
                f"    ...{text[max(0, i - 90):i + 110]}..."
            )
    assert not offences, (
        f"{path.relative_to(REPO_ROOT)} narrates its own history:\n"
        + "\n".join(offences)
        + "\n\nAGENTS.md: docs and records describe the CURRENT state. Say what is"
        "\ntrue now; the change that made it true is in git and in the issue that"
        "\nasked for it. Keep the owner quotes and the measurements -- those are"
        "\nprovenance, and they are the point of these fields."
    )
