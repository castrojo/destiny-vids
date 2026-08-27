#!/usr/bin/env python3
"""Generate the Excision HUD and fireteam plate manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.identity import load_people, person_for_character  # noqa: E402

OUT = REPO_ROOT / "stories" / "excision-plates.json"


def _lead(character, plate_id, at, position, why):
    person = person_for_character(character)
    if person is None or person.plate is None:
        raise ValueError(f"{character} has no authored plate copy")
    return {
        "id": plate_id,
        "at": at,
        "dur": 4.0,
        "position": position,
        **person.plate,
        "copy_source": "casting",
        "why": why,
    }


def _person(login, plate_id, at, position, why):
    person = load_people().get(login)
    if person is None or person.plate is None:
        raise ValueError(f"{login} has no authored plate copy")
    return {
        "id": plate_id,
        "at": at,
        "dur": 4.0,
        "position": position,
        **person.plate,
        "copy_source": "casting",
        "why": why,
    }


def build():
    plates = [
        {
            "id": "excision-welcome",
            "kind": "warning",
            "at": 0.5,
            "dur": 3.0,
            "position": "warning",
            "text": "[ WELCOME TO YOUR FIRST BATTLE ]",
            "copy_source": "owner_supplied",
            "why": "owner brief: the viewer enters the Excision fireteam",
        },
        {
            "id": "excision-hud-player",
            "kind": "status",
            "at": 4.0,
            "dur": 30.0,
            "position": "status",
            "detail": "FIRETEAM // FIRST BATTLE",
            "label": "John Bazzite",
            "copy_source": "owner_supplied",
            "why": "owner brief: the viewer's in-game HUD identity",
        },
        {
            "id": "excision-sky-caption",
            "kind": "caption",
            "at": 4.0,
            "dur": 8.0,
            "position": "caption",
            "text": "BRING THE SKY DOWN ON THEM",
            "copy_source": "owner_supplied",
            "why": "owner-requested Osiris epigraph; chrome, not scene dialogue",
        },
        _lead(
            "saint_14",
            "excision-kat",
            4.0,
            "left",
            "Saint-14 is visibly framed at source 44-48; the binding names Kat",
        ),
        _lead(
            "osiris",
            "excision-bob",
            8.0,
            "right",
            "Osiris is visibly framed beside Saint-14 at source 48-52",
        ),
        _person(
            "castrojo",
            "excision-jorge",
            54.0,
            "left",
            "owner brief: authored Guardian identity on the no-HUD fireteam",
        ),
        _person(
            "angellk",
            "excision-karena",
            60.0,
            "right",
            "owner brief: authored Guardian identity on the no-HUD fireteam",
        ),
        _person(
            "LoriLorusso",
            "excision-lori",
            66.0,
            "left",
            "owner brief: authored Guardian identity on the no-HUD fireteam",
        ),
    ]
    return {
        "_what": "GENERATED Excision segment plate manifest. Edit scripts/build_excision_plates.py, never this file.",
        "_provenance": "HUD strings are owner-supplied in epic #371. Guardian identity fields resolve verbatim from vocab/casting.yaml through tools.identity.",
        "act": "excision",
        "source_ids": [
            "yt_excision_chezvii_4k",
            "yt_excision_nohud_hoople",
        ],
        "film_sec": 152.5,
        "letterbox": {
            "active_height": 1080,
            "active_y": 0,
            "matte_px": 0,
            "_note": "The segment mixes a letterboxed rally with full-frame gameplay; plates use the common 1920x1080 delivery frame.",
        },
        "plates": plates,
        "unresolved": [
            "The Season of Dawn super beat is omitted because the available capture carries gameplay HUD; the clean Excision rally replaces it rather than widening the pool to unclean footage.",
            "Zavala, Ikora Rey and Crow are visibly present in the rally but have no current authored person binding; they are omitted rather than guessed.",
            "Ana Bray has a binding but no authored plate copy, so her rally shot ships without a credit row.",
            "The Ward source is no-HUD third-person footage; Kat is credited on the clearly visible Saint-14 rally shot rather than on an indistinct figure inside the bubble.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    expected = json.dumps(build(), indent=2) + "\n"
    if args.write:
        OUT.write_text(expected, encoding="utf-8")
        print(f"wrote {OUT}")
        return 0
    actual = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    if actual != expected:
        print(f"stale: {OUT}", file=sys.stderr)
        return 1
    print(f"ok: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
