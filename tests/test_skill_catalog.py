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


def _skill_docs():
    """Flat skills, migrated `<name>/SKILL.md`, and every reference file.

    The glob used to cover only `docs/skills/*.md`. That let a skill escape its
    own budget simply by being migrated into a directory — which is backwards,
    since migration exists to enforce the budget.
    """
    paths = [p for p in SKILLS_DIR.glob("*.md") if p.name != "index.md"]
    paths += SKILLS_DIR.glob("*/SKILL.md")
    paths += SKILLS_DIR.glob("*/references/*.md")
    paths += SKILLS_DIR.glob("references/*.md")
    return sorted(paths)


@pytest.mark.parametrize("path", _skill_docs(), ids=lambda p: str(p.relative_to(SKILLS_DIR)))
def test_skill_size_budget(path):
    """Soft max 200 lines, hard max 500 (common's write-a-skill contract)."""
    lines = path.read_text().splitlines()
    assert len(lines) <= 500, f"{path.name} is {len(lines)} lines; split it into references/"


@pytest.mark.parametrize("path", sorted(SKILLS_DIR.glob("*/SKILL.md")),
                         ids=lambda p: p.parent.name)
def test_migrated_skill_points_at_its_references(path):
    """A migrated skill must route to every reference beside it.

    `common`'s migrate-on-sight rule says SKILL.md keeps a table pointing at
    each reference file. A reference nobody links is a file agents never load.
    """
    body = path.read_text()
    for ref in sorted((path.parent / "references").glob("*.md")):
        assert f"references/{ref.name}" in body, (
            f"{path.parent.name}/SKILL.md does not link references/{ref.name}"
        )
