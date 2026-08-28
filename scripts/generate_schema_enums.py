#!/usr/bin/env python3
"""Generate the schemas' enum lists from vocab/, the single source of truth.

`vocab/*.yaml` defines every enum this repo uses. The JSON schemas need the
same lists so a committed record can be validated, and for a long time they
carried a hand-maintained second copy of them -- 254 values across four files,
"kept honest by a test" that in practice only checked a couple of axes.

Two had already drifted:

  * `subclass_version`: 13 values in the vocab, 7 in the segment schema. A
    D1-era segment derived as `arc_1` would be rejected by the schema meant to
    describe it.
  * video's `destination`: `mercury` missing, though the vocab and the segment
    schema both have it.

So the schemas become GENERATED files, in the same class as docs/skills/index.*
and corpus/*.json: fix a drift by re-running this, never by hand-editing either
copy. Adding an enum value is then one edit -- the vocab -- instead of two that
have to be remembered together.

Only the mapped `enum` lists have their CONTENT rewritten. Everything else in
the schema -- descriptions, types, required, $defs structure -- is hand-authored
and is preserved semantically, not byte for byte: `write()` reserialises the
whole document with `json.dumps(indent=2)`, so a hand-authored compact form like
`{"type": "number"}` on one line will be expanded on the next run. The committed
schemas are already in that canonical form, so a clean tree is a true no-op
(tests/test_schema_enums.py asserts it) -- but write compact JSON here and it
will not survive. `--check` compares only the enum lists, so it will not warn.

    python3 scripts/generate_schema_enums.py --check   # CI: exit 1 on drift
    python3 scripts/generate_schema_enums.py --write   # regenerate in place
"""

from __future__ import annotations

import argparse
import functools
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
VOCAB_DIR = REPO_ROOT / "vocab"
SCHEMA_DIR = REPO_ROOT / "schema"

# (schema file, JSON pointer to the node holding `enum`) -> (vocab file, axis).
#
# Explicit rather than inferred: matching by value would make the map derive
# from the very agreement it is supposed to enforce, so a drifted enum would
# quietly map to nothing and pass.
#
# Enums deliberately absent are schema-local, with no vocab axis behind them:
# `footage_tier` and `casting.role` are DERIVED (tools/derive.py owns them),
# `provenance.propertyNames` is a field list rather than a vocabulary, and the
# brief schema's enums describe a brief, not the footage.
MAP = {
    ("segment.schema.json", "/properties/class"): ("domain.yaml", "class"),
    ("segment.schema.json", "/properties/element"): ("domain.yaml", "element"),
    ("segment.schema.json", "/properties/faction/items"): ("domain.yaml", "faction"),
    ("segment.schema.json", "/properties/shot_scale"):
        ("cinematography.yaml", "shot_scale"),
    ("segment.schema.json", "/properties/composition/items"):
        ("cinematography.yaml", "composition"),
    ("segment.schema.json", "/properties/camera_movement/items"):
        ("cinematography.yaml", "camera_movement"),
    ("segment.schema.json", "/properties/pacing"): ("cinematography.yaml", "pacing"),
    ("segment.schema.json", "/properties/lighting"): ("cinematography.yaml", "lighting"),
    ("segment.schema.json", "/properties/overlays/items"):
        ("cleanliness.yaml", "overlays"),
    ("segment.schema.json", "/properties/identity_visibility"):
        ("identity.yaml", "identity_visibility"),
    ("segment.schema.json", "/properties/character_identifiability"):
        ("identity.yaml", "character_identifiability"),
    ("segment.schema.json", "/properties/mood/items"): ("register.yaml", "mood"),
    ("segment.schema.json", "/properties/subject_salience"):
        ("salience.yaml", "subject_salience"),
    ("segment.schema.json", "/properties/action/items"): ("action.yaml", "action"),
    ("segment.schema.json", "/$defs/era"): ("domain.yaml", "era"),
    ("segment.schema.json", "/$defs/activity"): ("domain.yaml", "activity"),
    ("segment.schema.json", "/$defs/content_type"):
        ("cinematography.yaml", "content_type"),
    ("segment.schema.json", "/$defs/destination"): ("domain.yaml", "destination"),
    ("segment.schema.json", "/$defs/subclass_version"):
        ("domain.yaml", "subclass_version"),
    ("segment.schema.json", "/$defs/provenanceEntry/properties/source"):
        ("provenance.yaml", "source"),
    ("segment.schema.json", "/$defs/provenanceEntry/properties/label_source"):
        ("provenance.yaml", "label_source"),
    ("video.schema.json", "/$defs/era"): ("domain.yaml", "era"),
    ("video.schema.json", "/$defs/activity"): ("domain.yaml", "activity"),
    ("video.schema.json", "/$defs/content_type"):
        ("cinematography.yaml", "content_type"),
    ("video.schema.json", "/$defs/destination"): ("domain.yaml", "destination"),
    ("video.schema.json", "/$defs/provenanceEntry/properties/source"):
        ("provenance.yaml", "source"),
    ("video.schema.json", "/$defs/provenanceEntry/properties/label_source"):
        ("provenance.yaml", "label_source"),
    ("bed.schema.json", "/properties/usage_class"):
        ("provenance.yaml", "usage_class"),
    ("standalone-batch.schema.json", "/$defs/source/properties/usage_class"):
        ("provenance.yaml", "usage_class"),
}


@functools.lru_cache(maxsize=None)
def vocab_values(filename, key):
    """One axis's values, in the vocabulary's own order.

    Order is preserved deliberately: the vocab files are read by people, and an
    ordinal axis (identity.yaml's `substitutability`) means nothing sorted.
    Keys are stringified because YAML parses `0:` as an int.
    """
    data = yaml.safe_load((VOCAB_DIR / filename).read_text()) or {}
    return [str(v) for v in (data[key].get("values") or {})]


def resolve_pointer(doc, pointer):
    """The node at a JSON pointer, e.g. `/$defs/era`."""
    node = doc
    for token in pointer.split("/")[1:]:
        node = node[token.replace("~1", "/").replace("~0", "~")]
    return node


def drifted(schema_dir=SCHEMA_DIR):
    """Every mapped enum whose committed copy is not the vocabulary's."""
    out = []
    for (schema_file, pointer), (vocab_file, key) in sorted(MAP.items()):
        doc = json.loads((Path(schema_dir) / schema_file).read_text())
        if resolve_pointer(doc, pointer).get("enum") != vocab_values(vocab_file, key):
            out.append((schema_file, pointer))
    return out


def write(schema_dir=SCHEMA_DIR):
    """Rewrite every mapped enum from the vocabulary. Returns what changed.

    A file whose text does not change is not rewritten at all, so a clean tree
    is a true no-op and nothing gets a new mtime for no reason.
    """
    schema_dir = Path(schema_dir)
    changed = []
    by_file = {}
    for (schema_file, pointer), source in MAP.items():
        by_file.setdefault(schema_file, []).append((pointer, source))

    for schema_file, entries in by_file.items():
        path = schema_dir / schema_file
        before = path.read_text()
        doc = json.loads(before)
        for pointer, (vocab_file, key) in entries:
            node = resolve_pointer(doc, pointer)
            values = vocab_values(vocab_file, key)
            if node.get("enum") != values:
                node["enum"] = values
                changed.append((schema_file, pointer))
        after = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
        if after != before:
            path.write_text(after, encoding="utf-8")
    return changed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true",
                      help="exit 1 if any schema enum has drifted from vocab/")
    mode.add_argument("--write", action="store_true",
                      help="regenerate every mapped enum from vocab/")
    args = ap.parse_args(argv)

    if args.check:
        bad = drifted()
        for schema_file, pointer in bad:
            vocab_file, key = MAP[(schema_file, pointer)]
            print(f"{schema_file}{pointer} != vocab/{vocab_file}:{key}",
                  file=sys.stderr)
        if bad:
            print(f"\n{len(bad)} enum(s) have drifted. Regenerate:\n"
                  f"  python3 scripts/generate_schema_enums.py --write",
                  file=sys.stderr)
            return 1
        print(f"{len(MAP)} schema enum(s) agree with vocab/")
        return 0

    changed = write()
    for schema_file, pointer in changed:
        print(f"updated {schema_file}{pointer}")
    print(f"{len(changed)} enum(s) regenerated from vocab/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
