"""The skill catalog must stay in sync with docs/skills/*.md front matter.

Mirrors the pre-commit/CI check in projectbluefin/common: a stale catalog is a
router that sends agents to the wrong file.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "docs" / "skills"


def test_catalog_is_not_stale():
    result = subprocess.run(
        [sys.executable, "scripts/generate_skill_index.py", "--check"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"{result.stdout}{result.stderr}\n"
        "Run: python3 scripts/generate_skill_index.py --write"
    )


def test_every_skill_is_routed_from_the_router():
    """A skill nobody can find is a skill that does not exist."""
    router = (REPO_ROOT / "docs" / "SKILL.md").read_text()
    catalog = json.loads((SKILLS_DIR / "index.json").read_text())
    for skill in catalog["skills"]:
        link = skill["entry_point"].removeprefix("docs/")
        assert link in router, f"{skill['id']} is not linked from docs/SKILL.md"


def test_every_routed_skill_exists():
    """The reverse: a router link to a missing file is a dead end."""
    router_path = REPO_ROOT / "docs" / "SKILL.md"
    import re

    for target in re.findall(r"\]\((skills/[^)]+\.md)\)", router_path.read_text()):
        assert (REPO_ROOT / "docs" / target).exists(), target


@pytest.mark.parametrize("path", sorted(SKILLS_DIR.glob("*.md")))
def test_skill_size_budget(path):
    """Soft max 200 lines, hard max 500 (common's write-a-skill contract)."""
    if path.name == "index.md":
        return
    lines = path.read_text().splitlines()
    assert len(lines) <= 500, f"{path.name} is {len(lines)} lines; split it into references/"
