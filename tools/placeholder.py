#!/usr/bin/env python3
"""Lorem ipsum placeholders: a slot with no prose still gets a plate.

The rule this implements is the owner's: *"instead of blocking when I don't
have prose use lorem ipsum so we have placeholders for everything at least"*.
A cut whose copy is half-written is still worth watching -- the timing, the
letterbox seat, the read length and the gaps between plates are all reviewable
before a single word is final, and a slot that renders nothing is a slot nobody
notices is missing.

WHAT A PLACEHOLDER MAY NEVER DO IS CREDIT SOMEBODY. This repo has the scar:
act IV's first pass put LOREM IPSUM lines on ``krook``, ``jeefy`` and
``mrbobbytables``, and all three were dropped from the film once real copy
arrived, because they had only ever "spoken" words nobody wrote. Placeholder
prose therefore carries the vocab's own uncast speaker (``ensemble.
placeholder_plate.name``, "TBD") and never a real login, exactly as the
ensemble blueberry plate has always done. The person the line is *destined*
for is recorded in ``speaker_pending`` -- kept, and not rendered.

So the three states are distinct, and only the middle one is new:

    real copy       rendered as authored, credited to whoever said it
    PLACEHOLDER     rendered as lorem, credited to nobody, listed by `list`
    invented copy   still forbidden, still forever

THE TEXT IS DETERMINISTIC. ``lorem(...)`` seeds on the plate's own id, so the
same slot yields the same words on every machine and every rerun: a manifest
does not churn, a render is reproducible, and a diff that changes shows a
placeholder actually moved rather than a random draw landing differently.

    python3 tools/placeholder.py list          # every placeholder in the show
    python3 tools/placeholder.py list --check  # exit 1 if any remain
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# The canonical opening, then the rest of the standard passage. Latin is the
# point: nobody mistakes it for English that somebody approved, which is what
# makes it safe to burn into a frame and obvious in a review.
WORDS = (
    "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod "
    "tempor incididunt ut labore et dolore magna aliqua ut enim ad minim "
    "veniam quis nostrud exercitation ullamco laboris nisi aliquip ex ea "
    "commodo consequat duis aute irure in reprehenderit voluptate velit esse "
    "cillum eu fugiat nulla pariatur excepteur sint occaecat cupidatat non "
    "proident sunt culpa qui officia deserunt mollit anim id est laborum"
).split()

# A dialogue pill is one line that must not wrap (`plate.py` shrinks to fit and
# stops at MIN_FONT), so the default length is the length of a real line in
# this show rather than a paragraph.
DEFAULT_CHARS = 34

MARKER = "placeholder"


def lorem(chars=DEFAULT_CHARS, seed=""):
    """``chars``-ish of lorem ipsum, deterministic in ``seed``.

    Always starts at a word boundary and never mid-word, so the result reads as
    a phrase rather than a truncation. ``seed`` is normally the plate id: the
    same slot draws the same words forever, which is what keeps a committed
    manifest from churning and a render reproducible.
    """
    if chars <= 0:
        return ""
    digest = hashlib.sha256(str(seed).encode("utf-8")).digest()
    start = digest[0] % len(WORDS)
    out = []
    length = 0
    i = 0
    # Walk the passage from a seeded offset, wrapping, until the line is long
    # enough. Bounded by the passage length so a huge `chars` cannot spin.
    while length < chars and i < len(WORDS) * 4:
        word = WORDS[(start + i) % len(WORDS)]
        if out and length + 1 + len(word) > chars:
            break
        length += len(word) + (1 if out else 0)
        out.append(word)
        i += 1
    if not out:                      # `chars` shorter than the first word
        out = [WORDS[start][:chars]]
    out[0] = out[0].capitalize()
    return " ".join(out)


def needs_prose(spec):
    """True when this plate's WORDS are missing and lorem should stand in.

    Deliberately narrow: a chat pill whose ``text`` is absent or blank. That
    used to render an EMPTY pill -- a plate saying nothing and reporting
    nothing, which is the state this module exists to abolish.

    It is NOT the same question as ``is_placeholder``. Act II carries *named
    placeholder badges* (``placeholder_dylan_taylor``): a person the owner
    named, credited with their real name and every unauthored row omitted.
    Those are punch-list items too, but their copy is not missing -- it is
    deliberately partial, and overwriting a real name with lorem would be the
    exact failure this module exists to prevent.
    """
    if spec.get("text_source") == "placeholder":
        # The dialogue record's own way of saying it: `dialogue_md.apply`
        # marks a cue the owner left blank rather than failing the file. The
        # words are deliberately NOT baked in there, so that the speaker swap
        # below happens once, here, at render time.
        return True
    return spec.get("kind") == "chat" and not (spec.get("text") or "").strip()


def is_placeholder(spec):
    """True when this plate is a punch-list item of ANY kind.

    The union: a pill with no prose (above) plus anything already flagged
    ``placeholder: true``, which is the named-badge convention act II
    established. ``list`` reports both because both are copy somebody still
    owes; only the first is ever filled with lorem.
    """
    return bool(spec.get(MARKER)) or needs_prose(spec)


def fill(spec, uncast_name=None):
    """Return ``spec`` with placeholder prose, crediting nobody.

    The speaker is replaced, not kept: a lorem line under a real login is the
    act IV failure. Whoever the line is *for* survives in ``speaker_pending``
    so the queue is not lost, and ``placeholder`` marks the plate so `list`
    can find it again.
    """
    if not needs_prose(spec):
        return spec
    if uncast_name is None:
        from tools.derive import load_placeholder_plate

        uncast_name = (load_placeholder_plate() or {}).get("name") or "TBD"
    out = dict(spec)
    pending = out.get("speaker_pending") or out.get("speaker")
    if pending:
        out["speaker_pending"] = pending
    out["speaker"] = uncast_name
    out["text"] = out.get("text") or lorem(
        int(out.get("placeholder_chars") or DEFAULT_CHARS),
        seed=out.get("id", ""))
    # An avatar is a photograph of a person. A slot credited to nobody shows
    # the drawn crest instead.
    out.pop("avatar", None)
    out[MARKER] = True
    return out


# --- the punch list ---------------------------------------------------------

MANIFESTS = ("stories/*.json", "stories/megacut/*.json")


def scan(root=None):
    """Every placeholder in the committed records, as a flat punch list.

    "Placeholders for everything" is only useful if you can find them all
    again, so this is the other half of the feature: one command that says
    what is still unwritten, and a ``--check`` for anyone who wants to gate on
    it. It reads committed JSON only -- no footage, no network.
    """
    root = Path(root or REPO_ROOT)
    found = []
    for pattern in MANIFESTS:
        for path in sorted(root.glob(pattern)):
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(doc, dict):
                continue
            for entry in doc.get("plates") or []:
                if isinstance(entry, dict) and is_placeholder(entry):
                    found.append({
                        "file": str(path.relative_to(root)),
                        "act": doc.get("act"),
                        "id": entry.get("id"),
                            "kind": ("prose" if needs_prose(entry)
                                 else "named-badge"),
                        "pending": entry.get("speaker_pending")
                                   or entry.get("speaker")
                                   or entry.get("name"),
                    })
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    lister = sub.add_parser("list", help="every placeholder in the show")
    lister.add_argument("--check", action="store_true",
                        help="exit 1 if any placeholder remains -- for anyone "
                             "gating a final cut, NOT for CI, which must stay "
                             "green while copy is still being written")
    args = ap.parse_args(argv)

    found = scan()
    for item in found:
        pending = f"  (for {item['pending']})" if item["pending"] else ""
        print(f"{item['act'] or '?':<4} {item['kind']:<12} {item['id']:<26} "
              f"{item['file']}{pending}")
    prose = sum(1 for i in found if i["kind"] == "prose")
    print(f"\n{len(found)} placeholder(s): {prose} with no prose (lorem stands "
          f"in), {len(found) - prose} named badge(s) with rows nobody authored")
    return 1 if (args.check and found) else 0


if __name__ == "__main__":
    raise SystemExit(main())
