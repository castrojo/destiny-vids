from datetime import date
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from scripts import generate_skill_index as catalog

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "docs" / "skills" / "index.schema.json"

MINIMAL = """\
---
name: demo-skill
version: "1.0"
last_updated: "2026-08-19"
id: demo-skill
one_line_purpose: Demonstrate catalog generation.
entry_point: docs/skills/demo-skill.md
category: meta
status: active
dependencies: []
tags: [demo]
description: >-
  Demonstrates catalog generation. Use when testing skill metadata.
metadata:
  type: procedure
---

# Demo
"""


def _skill_text(skill_id: str, entry_point: str, doc_type: str = "procedure") -> str:
    return f"""\
---
name: {skill_id}
version: "1.0"
last_updated: "2026-08-19"
id: {skill_id}
one_line_purpose: Demonstrate catalog generation.
entry_point: {entry_point}
category: meta
status: active
dependencies: []
tags: [demo]
description: >-
  Demonstrates catalog generation. Use when testing skill metadata.
metadata:
  type: {doc_type}
---

# Demo
"""


def test_schema_is_valid_json_schema():
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    Draft202012Validator.check_schema(json.loads(schema))


def test_find_skill_files_returns_flat_and_nested_skill_files(tmp_path: Path):
    skills_dir = tmp_path / "docs" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "demo-skill.md").write_text(MINIMAL, encoding="utf-8")
    nested = skills_dir / "nested"
    nested.mkdir()
    (nested / "SKILL.md").write_text(
        _skill_text("nested-skill", "docs/skills/nested/SKILL.md", "runbook"),
        encoding="utf-8",
    )
    (skills_dir / "index.md").write_text("ignored", encoding="utf-8")

    files = catalog.find_skill_files(skills_dir)

    assert [p.relative_to(skills_dir).as_posix() for p in files] == [
        "demo-skill.md",
        "nested/SKILL.md",
    ]


def test_build_skill_entry_reads_required_metadata(tmp_path: Path):
    path = tmp_path / "docs" / "skills" / "demo-skill.md"
    path.parent.mkdir(parents=True)
    path.write_text(MINIMAL, encoding="utf-8")

    entry = catalog.build_skill_entry(path, tmp_path)

    assert entry["id"] == "demo-skill"
    assert entry["category"] == "meta"
    assert entry["entry_point"] == "docs/skills/demo-skill.md"
    assert entry["doc_type"] == "procedure"


def test_entry_point_must_match_actual_path(tmp_path: Path):
    path = tmp_path / "docs" / "skills" / "demo-skill.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        MINIMAL.replace("docs/skills/demo-skill.md", "docs/skills/wrong.md"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="does not match actual path"):
        catalog.build_skill_entry(path, tmp_path)


def test_build_catalog_collects_and_validates_fixture_skills(tmp_path: Path):
    skills_dir = tmp_path / "docs" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "demo-skill.md").write_text(MINIMAL, encoding="utf-8")
    nested = skills_dir / "nested"
    nested.mkdir()
    (nested / "SKILL.md").write_text(
        _skill_text("nested-skill", "docs/skills/nested/SKILL.md", "runbook"),
        encoding="utf-8",
    )

    catalog_data = catalog.build_catalog(tmp_path, generated_at=date(2026, 8, 19))

    assert catalog_data["generated_at"] == "2026-08-19"
    assert [skill["id"] for skill in catalog_data["skills"]] == [
        "demo-skill",
        "nested-skill",
    ]
    catalog.validate_catalog(catalog_data, SCHEMA_PATH)


def test_unchanged_catalog_keeps_previous_generated_date():
    current = {
        "generated_at": "2026-08-19",
        "schema_version": "1.0",
        "skills": [{"id": "demo"}],
    }
    rebuilt = {
        "generated_at": "2026-08-20",
        "schema_version": "1.0",
        "skills": [{"id": "demo"}],
    }

    catalog.pin_unchanged_generated_at(rebuilt, current)

    assert rebuilt["generated_at"] == "2026-08-19"


def test_markdown_catalog_links_to_entry_point():
    rendered = catalog.render_markdown(
        {
            "generated_at": "2026-08-19",
            "schema_version": "1.0",
            "skills": [
                {
                    "id": "demo-skill",
                    "entry_point": "docs/skills/demo-skill.md",
                    "category": "meta",
                    "status": "active",
                    "one_line_purpose": "Demonstrate catalog generation.",
                }
            ],
        }
    )

    assert "[demo-skill](demo-skill.md)" in rendered
