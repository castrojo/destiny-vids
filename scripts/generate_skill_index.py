#!/usr/bin/env python3
"""Generate and validate the docs/skills catalog from skill front matter."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "docs" / "skills"
CATALOG_JSON = SKILLS_DIR / "index.json"
CATALOG_MD = SKILLS_DIR / "index.md"
SCHEMA_PATH = SKILLS_DIR / "index.schema.json"
CATALOG_SCHEMA_VERSION = "1.0"


def find_skill_files(skills_dir: Path) -> list[Path]:
    files = sorted(p for p in skills_dir.glob("*.md") if p.name != "index.md")
    files += sorted(skills_dir.glob("*/SKILL.md"))
    return files


def parse_front_matter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing YAML front matter")
    try:
        _, raw, _ = text.split("---\n", 2)
    except ValueError as exc:
        raise ValueError(f"{path}: unterminated YAML front matter") from exc
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: front matter must parse to a mapping")
    return data


def build_skill_entry(path: Path, repo_root: Path) -> dict[str, object]:
    fm = parse_front_matter(path)
    rel = path.relative_to(repo_root).as_posix()
    required = (
        "id",
        "name",
        "one_line_purpose",
        "entry_point",
        "category",
        "status",
        "tags",
        "description",
        "version",
        "last_updated",
    )
    missing = [key for key in required if key not in fm]
    if missing:
        raise ValueError(f"{rel}: missing required front-matter key(s): {missing}")
    if fm["id"] != fm["name"]:
        raise ValueError(f"{rel}: id and name must match")
    if fm["entry_point"] != rel:
        raise ValueError(
            f"{rel}: entry_point front-matter value "
            f"({fm['entry_point']!r}) does not match actual path ({rel!r})"
        )
    entry = {
        "id": fm["id"],
        "name": fm["name"],
        "one_line_purpose": fm["one_line_purpose"],
        "entry_point": fm["entry_point"],
        "category": fm["category"],
        "status": fm["status"],
        "tags": fm["tags"],
        "description": " ".join(str(fm["description"]).split()),
        "version": str(fm["version"]),
        "last_updated": str(fm["last_updated"]),
    }
    doc_type = (fm.get("metadata") or {}).get("type")
    if doc_type:
        entry["doc_type"] = doc_type
    return entry


def build_catalog(repo_root: Path, generated_at: date | None = None) -> dict[str, object]:
    repo_root = Path(repo_root)
    skills_dir = repo_root / "docs" / "skills"
    catalog_date = generated_at or date.today()
    return {
        "schema_version": CATALOG_SCHEMA_VERSION,
        "generated_at": catalog_date.isoformat(),
        "skills": [
            build_skill_entry(path, repo_root)
            for path in find_skill_files(skills_dir)
        ],
    }


def pin_unchanged_generated_at(catalog: dict, existing: dict | None) -> None:
    if not existing:
        return
    current = dict(catalog)
    previous = dict(existing)
    current.pop("generated_at", None)
    previous.pop("generated_at", None)
    if current == previous:
        catalog["generated_at"] = existing.get("generated_at", catalog["generated_at"])


def validate_catalog(catalog: dict, schema_path: Path) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:  # pragma: no cover - CI installs it
        raise RuntimeError("jsonschema is required to validate the skill catalog") from exc
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(catalog)


def render_markdown(catalog: dict) -> str:
    lines = [
        "# Skill catalog",
        "",
        f"Generated {catalog['generated_at']}.",
        "",
        "| Skill | Category | Type | One-line purpose |",
        "|---|---|---|---|",
    ]
    for skill in catalog["skills"]:
        target = Path(skill["entry_point"]).relative_to("docs/skills").as_posix()
        lines.append(
            f"| [{skill['id']}]({target}) | {skill['category']} | "
            f"{skill.get('doc_type', '')} | {skill['one_line_purpose']} |"
        )
    lines.append("")
    return "\n".join(lines)


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_text(path: Path, text: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def _catalog_texts(catalog: dict) -> tuple[str, str]:
    return (
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
        render_markdown(catalog),
    )


def write_catalog(repo_root: Path = REPO_ROOT) -> int:
    catalog = build_catalog(repo_root)
    existing = _load_json(Path(repo_root) / "docs" / "skills" / "index.json")
    pin_unchanged_generated_at(catalog, existing)
    validate_catalog(catalog, Path(repo_root) / "docs" / "skills" / "index.schema.json")
    json_text, md_text = _catalog_texts(catalog)
    _write_text(Path(repo_root) / "docs" / "skills" / "index.json", json_text)
    _write_text(Path(repo_root) / "docs" / "skills" / "index.md", md_text)
    print(
        f"wrote docs/skills/index.json and index.md ({len(catalog['skills'])} skills)"
    )
    return 0


def check_catalog(repo_root: Path = REPO_ROOT) -> int:
    catalog = build_catalog(repo_root)
    existing = _load_json(Path(repo_root) / "docs" / "skills" / "index.json")
    pin_unchanged_generated_at(catalog, existing)
    validate_catalog(catalog, Path(repo_root) / "docs" / "skills" / "index.schema.json")
    json_text, md_text = _catalog_texts(catalog)
    current_json = (
        Path(repo_root) / "docs" / "skills" / "index.json"
    ).read_text(encoding="utf-8") if (Path(repo_root) / "docs" / "skills" / "index.json").exists() else None
    current_md = (
        Path(repo_root) / "docs" / "skills" / "index.md"
    ).read_text(encoding="utf-8") if (Path(repo_root) / "docs" / "skills" / "index.md").exists() else None
    if current_json != json_text or current_md != md_text:
        print("docs/skills/index.json and index.md are out of date", file=sys.stderr)
        print("Regenerate with:", file=sys.stderr)
        print("  python3 scripts/generate_skill_index.py --write", file=sys.stderr)
        return 1
    print(f"{len(catalog['skills'])} skill(s) agree with docs/skills/index.json")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.write:
        return write_catalog()
    return check_catalog()


if __name__ == "__main__":
    raise SystemExit(main())
