"""The Halo campaign plan must stay navigable.

A plan is only useful if its map matches the files on disk: an issue nobody can
find never gets filed, and a dead link sends the next agent to a file that does
not exist. Mirrors the contract tests/test_skill_catalog.py enforces for the
skill router.
"""
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_DIR = REPO_ROOT / "docs" / "plans" / "halo"
ISSUES_DIR = PLAN_DIR / "issues"

ISSUES = sorted(ISSUES_DIR.glob("*.md"))
PLAN_DOCS = sorted(PLAN_DIR.glob("*.md")) + ISSUES

# The shape every issue file carries, so a file can be pasted into GitHub as-is.
REQUIRED_SECTIONS = ("**What:**", "**Scope:**", "**Acceptance:**", "**Automatable:**")


def test_the_plan_has_issues_to_file():
    assert ISSUES, "docs/plans/halo/issues/ is empty"


@pytest.mark.parametrize("path", ISSUES, ids=lambda p: p.name)
def test_every_issue_is_listed_in_the_epic_map(path):
    """An issue missing from README.md is an issue nobody files."""
    readme = (PLAN_DIR / "README.md").read_text()
    assert f"issues/{path.name}" in readme


@pytest.mark.parametrize("path", ISSUES, ids=lambda p: p.name)
def test_every_issue_carries_the_repo_issue_shape(path):
    text = path.read_text()
    for section in REQUIRED_SECTIONS:
        assert section in text, f"{path.name} is missing {section}"
    assert text.startswith("# H-"), f"{path.name} must open with its plan id"


def test_plan_ids_match_the_filenames_and_are_unique():
    """`H-07` in the heading and `07-` in the name must be the same issue."""
    seen = set()
    for path in ISSUES:
        number = path.name.split("-", 1)[0]
        heading = path.read_text().splitlines()[0]
        assert heading.startswith(f"# H-{number} "), (path.name, heading)
        assert number not in seen, f"duplicate plan id {number}"
        seen.add(number)


@pytest.mark.parametrize("path", PLAN_DOCS, ids=lambda p: p.name)
def test_no_dead_relative_links(path):
    for target in re.findall(r"\]\((?!https?:)([^)#]+?\.md)(?:#[^)]*)?\)", path.read_text()):
        assert (path.parent / target).exists(), f"{path.name} -> {target}"
