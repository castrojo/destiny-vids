#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
tool_root="$(cd "$script_dir/.." && pwd)"
repo_root="${1:-$tool_root}"

python3 - "$tool_root" "$repo_root" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path

tool_root = Path(sys.argv[1]).resolve()
repo_root = Path(sys.argv[2]).resolve()
if str(tool_root) not in sys.path:
    sys.path.insert(0, str(tool_root))

from scripts.generate_skill_index import find_skill_files

LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

router = repo_root / "docs" / "SKILL.md"
if not router.exists():
    print(f"error: missing router {router.relative_to(repo_root)}",
          file=sys.stderr)
    raise SystemExit(1)

targets = {
    target.strip().split("#", 1)[0]
    for target in LINK.findall(router.read_text(encoding="utf-8"))
}

missing = []
for path in find_skill_files(repo_root / "docs" / "skills"):
    rel = path.relative_to(repo_root / "docs" / "skills").as_posix()
    target = f"skills/{rel}"
    if target not in targets:
        missing.append(target)
        print(
            f"error: docs/SKILL.md is missing route for {target}",
            file=sys.stderr,
        )

if missing:
    raise SystemExit(1)

print(f"{len(find_skill_files(repo_root / 'docs' / 'skills'))} skill route(s) covered")
PY
