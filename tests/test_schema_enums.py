"""The schemas' enums are generated from vocab/, not maintained beside it.

`vocab/` is the single source of truth for every enum (AGENTS.md). The schemas
used to carry a second, hand-maintained copy of 254 of those values, and two of
them had already drifted before anybody noticed:

* `subclass_version` -- the vocab declares 13 values, the segment schema
  allowed 7. A D1-era segment derived as `arc_1` would have been rejected by
  the schema that is supposed to describe it.
* video's `destination` -- missing `mercury`, which the vocab and the segment
  schema both allow.

Neither was caught, because "the tests assert they agree" was only ever true of
the handful of axes something happened to check. This file checks all of them,
and the generator makes the agreement structural.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import generate_schema_enums as gen  # noqa: E402

def test_every_mapping_points_at_a_real_vocab_axis():
    for (schema_file, pointer), (vocab_file, key) in gen.MAP.items():
        values = gen.vocab_values(vocab_file, key)
        assert values, f"{vocab_file}:{key} (for {schema_file}{pointer}) is empty"

def test_every_mapping_points_at_a_real_schema_enum():
    for (schema_file, pointer), _ in gen.MAP.items():
        doc = json.loads((REPO_ROOT / "schema" / schema_file).read_text())
        node = gen.resolve_pointer(doc, pointer)
        assert "enum" in node, f"{schema_file}{pointer} has no enum"

@pytest.mark.parametrize("schema_file,pointer", sorted(gen.MAP))
def test_the_committed_schema_matches_the_vocabulary(schema_file, pointer):
    """The gate. A hand-edit to either copy fails here."""
    vocab_file, key = gen.MAP[(schema_file, pointer)]
    doc = json.loads((REPO_ROOT / "schema" / schema_file).read_text())
    node = gen.resolve_pointer(doc, pointer)
    assert node["enum"] == gen.vocab_values(vocab_file, key), (
        f"{schema_file}{pointer} has drifted from vocab/{vocab_file}:{key}. "
        f"Regenerate: python3 scripts/generate_schema_enums.py --write")

def test_check_mode_exits_zero_when_the_tree_is_clean():
    proc = subprocess.run(
        [sys.executable, "scripts/generate_schema_enums.py", "--check"],
        cwd=REPO_ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr

def test_check_mode_fails_on_a_drifted_enum(tmp_path):
    """A hand-edited schema must be reported, not silently accepted."""
    schema_dir = tmp_path / "schema"
    schema_dir.mkdir()
    for src in (REPO_ROOT / "schema").glob("*.json"):
        (schema_dir / src.name).write_text(src.read_text())

    victim = schema_dir / "segment.schema.json"
    doc = json.loads(victim.read_text())
    doc["properties"]["class"]["enum"] = ["titan"]     # the hand-edit
    victim.write_text(json.dumps(doc, indent=2) + "\n")

    drifted = gen.drifted(schema_dir)
    assert ("segment.schema.json", "/properties/class") in drifted

def test_writing_repairs_a_drifted_enum(tmp_path):
    schema_dir = tmp_path / "schema"
    schema_dir.mkdir()
    for src in (REPO_ROOT / "schema").glob("*.json"):
        (schema_dir / src.name).write_text(src.read_text())

    victim = schema_dir / "segment.schema.json"
    doc = json.loads(victim.read_text())
    doc["properties"]["class"]["enum"] = ["titan"]
    victim.write_text(json.dumps(doc, indent=2) + "\n")

    gen.write(schema_dir)

    assert not gen.drifted(schema_dir)
    repaired = json.loads(victim.read_text())
    assert repaired["properties"]["class"]["enum"] == gen.vocab_values(
        "domain.yaml", "class")

def test_writing_changes_nothing_else_in_the_file(tmp_path):
    """The generator edits enum lists and touches nothing around them."""
    schema_dir = tmp_path / "schema"
    schema_dir.mkdir()
    for src in (REPO_ROOT / "schema").glob("*.json"):
        (schema_dir / src.name).write_text(src.read_text())

    before = {p.name: p.read_text() for p in schema_dir.glob("*.json")}
    gen.write(schema_dir)
    after = {p.name: p.read_text() for p in schema_dir.glob("*.json")}
    assert before == after, "a clean tree must be a no-op"

def test_a_vocab_addition_reaches_the_schema(tmp_path, monkeypatch):
    """Adding a value to vocab/ is the ONE edit. The schema follows."""
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    for src in (REPO_ROOT / "vocab").glob("*.yaml"):
        (vocab_dir / src.name).write_text(src.read_text())
    schema_dir = tmp_path / "schema"
    schema_dir.mkdir()
    for src in (REPO_ROOT / "schema").glob("*.json"):
        (schema_dir / src.name).write_text(src.read_text())

    domain = vocab_dir / "domain.yaml"
    domain.write_text(domain.read_text().replace(
        "    unknown:       Activity not determinable.\n",
        "    unknown:       Activity not determinable.\n"
        "    lost_sector:   Solo lost sector gameplay.\n", 1))

    monkeypatch.setattr(gen, "VOCAB_DIR", vocab_dir)
    gen.vocab_values.cache_clear()
    gen.write(schema_dir)

    doc = json.loads((schema_dir / "segment.schema.json").read_text())
    assert "lost_sector" in doc["$defs"]["activity"]["enum"]
