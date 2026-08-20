from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS = REPO_ROOT / "docs" / "skills"


def _canonical_skills() -> list[Path]:
    return (
        sorted(p for p in SKILLS.glob("*.md") if p.name != "index.md")
        + sorted(SKILLS.glob("*/SKILL.md"))
    )


def _front_matter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} has no YAML front matter"
    raw = text.split("---\n", 2)[1]
    data = yaml.safe_load(raw)
    assert isinstance(data, dict), f"{path} front matter must parse to a mapping"
    return data


def test_every_skill_has_common_compatible_front_matter():
    required = {
        "name",
        "version",
        "last_updated",
        "id",
        "one_line_purpose",
        "entry_point",
        "category",
        "status",
        "dependencies",
        "tags",
        "description",
        "metadata",
    }
    for path in _canonical_skills():
        fm = _front_matter(path)
        assert required <= fm.keys(), f"{path}: {required - fm.keys()}"
        assert fm["metadata"]["type"] in {
            "procedure",
            "reference",
            "runbook",
            "policy",
        }


def test_no_canonical_skill_exceeds_hard_limit():
    oversized = {
        str(path.relative_to(REPO_ROOT)): len(path.read_text(encoding="utf-8").splitlines())
        for path in _canonical_skills()
        if len(path.read_text(encoding="utf-8").splitlines()) > 500
    }
    assert not oversized


def test_agent_contract_is_not_duplicated():
    forbidden = [
        REPO_ROOT / "CLAUDE.md",
        REPO_ROOT / "GEMINI.md",
        REPO_ROOT / ".github" / "copilot-instructions.md",
    ]
    assert not [str(path.relative_to(REPO_ROOT))
                for path in forbidden if path.exists()]
    assert not list((REPO_ROOT / ".github" / "agents").glob("**/*"))


def test_validator_scripts_parse_cleanly():
    subprocess.run(["bash", "-n", str(REPO_ROOT / "scripts" / "check-skill-frontmatter.sh")],
                   check=True)
    subprocess.run(["bash", "-n", str(REPO_ROOT / "scripts" / "check-skill-index.sh")],
                   check=True)
    subprocess.run([sys.executable, "-m", "py_compile",
                    str(REPO_ROOT / "scripts" / "check-doc-links.sh")],
                   check=True)


def _write_fixture_skill(path: Path, *, doc_type: str = "procedure") -> None:
    repo_root = path.parents[2] if path.name != "SKILL.md" else path.parents[3]
    entry_point = path.relative_to(repo_root).as_posix()
    skill_name = path.stem if path.name != "SKILL.md" else path.parent.name
    path.write_text(
        f"""\
---
name: {skill_name}
version: "1.0"
last_updated: "2026-08-19"
id: {skill_name}
one_line_purpose: Demonstrate contract validation.
entry_point: {entry_point}
category: meta
status: active
dependencies: []
tags: [demo]
description: >-
  Demonstrates contract validation. Use when testing the skill contract.
metadata:
  type: {doc_type}
---

# Demo
""",
        encoding="utf-8",
    )


def test_validator_scripts_work_on_fixture_repo(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "docs" / "skills").mkdir(parents=True)

    flat = repo / "docs" / "skills" / "demo.md"
    _write_fixture_skill(flat)
    nested_dir = repo / "docs" / "skills" / "nested"
    nested_dir.mkdir()
    _write_fixture_skill(nested_dir / "SKILL.md", doc_type="runbook")

    (repo / "docs" / "SKILL.md").write_text(
        """\
# Skill router

- [`demo`](skills/demo.md)
- [`nested`](skills/nested/SKILL.md)
""",
        encoding="utf-8",
    )
    (repo / "docs" / "guide.md").write_text(
        """\
# Guide

See [README](../README.md).
""",
        encoding="utf-8",
    )
    (repo / "README.md").write_text("# Readme\n", encoding="utf-8")
    (repo / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")

    subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "check-skill-frontmatter.sh"),
         str(repo)],
        check=True,
    )
    subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "check-skill-index.sh"),
         str(repo)],
        check=True,
    )
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "check-doc-links.sh"),
         str(repo)],
        check=True,
    )
