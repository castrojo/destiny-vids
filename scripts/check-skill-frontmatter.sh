#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
tool_root="$(cd "$script_dir/.." && pwd)"
repo_root="${1:-$tool_root}"

python3 - "$tool_root" "$repo_root" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

tool_root = Path(sys.argv[1]).resolve()
repo_root = Path(sys.argv[2]).resolve()
if str(tool_root) not in sys.path:
    sys.path.insert(0, str(tool_root))

from scripts.generate_skill_index import find_skill_files, parse_front_matter

ALLOWED_CATEGORIES = {
    "editorial",
    "media-production",
    "metadata",
    "operations",
    "meta",
}
ALLOWED_DOC_TYPES = {"procedure", "reference", "runbook", "policy"}
REQUIRED_KEYS = (
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
)


def _expected_name(path: Path) -> str:
    return path.parent.name if path.name == "SKILL.md" else path.stem


rc = 0
skills = find_skill_files(repo_root / "docs" / "skills")
for path in skills:
    rel = path.relative_to(repo_root).as_posix()
    expected = _expected_name(path)
    line_count = len(path.read_text(encoding="utf-8").splitlines())

    try:
        fm = parse_front_matter(path)
    except ValueError as exc:
        print(f"error: {rel} {exc}", file=sys.stderr)
        rc = 1
        continue

    for key in REQUIRED_KEYS:
        if key not in fm:
            print(f"error: {rel} missing required key '{key}'", file=sys.stderr)
            rc = 1

    if fm.get("name") != expected:
        print(f"error: {rel} name must equal {expected!r}", file=sys.stderr)
        rc = 1
    if fm.get("id") != expected:
        print(f"error: {rel} id must equal {expected!r}", file=sys.stderr)
        rc = 1
    if fm.get("entry_point") != rel:
        print(
            f"error: {rel} entry_point must equal {rel!r}",
            file=sys.stderr,
        )
        rc = 1
    if fm.get("category") not in ALLOWED_CATEGORIES:
        print(f"error: {rel} invalid category {fm.get('category')!r}",
              file=sys.stderr)
        rc = 1

    metadata = fm.get("metadata")
    doc_type = metadata.get("type") if isinstance(metadata, dict) else None
    if doc_type is None:
        print(f"error: {rel} missing metadata.type", file=sys.stderr)
        rc = 1
    elif doc_type not in ALLOWED_DOC_TYPES:
        print(f"error: {rel} invalid metadata.type {doc_type!r}",
              file=sys.stderr)
        rc = 1

    description = str(fm.get("description", ""))
    if len(description) > 256:
        print(f"error: {rel} description exceeds 256 characters",
              file=sys.stderr)
        rc = 1

    purpose = str(fm.get("one_line_purpose", ""))
    if len(purpose) > 120:
        print(f"error: {rel} one_line_purpose exceeds 120 characters",
              file=sys.stderr)
        rc = 1

    if line_count > 500:
        print(f"error: {rel} has {line_count} lines (over 500)",
              file=sys.stderr)
        rc = 1
    elif line_count > 200:
        print(f"warning: {rel} has {line_count} lines", file=sys.stderr)

if rc:
    raise SystemExit(1)

print(f"{len(skills)} skill file(s) satisfy the front-matter contract")
PY
