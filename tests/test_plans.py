"""The Wolves plan must stay navigable: no orphan epics, no dead links.

These are planning documents, not code — but an epic nobody can find is an epic
that never gets filed, and the same failure mode the skill catalog guards
against (`tests/test_skill_catalog.py`) applies to a plan with ten parts.
"""
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_DIR = REPO_ROOT / "docs" / "plans" / "wolves"
EPICS_DIR = PLAN_DIR / "epics"

PLAN_DOCS = sorted(PLAN_DIR.rglob("*.md"))
EPIC_FILES = sorted(EPICS_DIR.glob("*.md"))

# "](target)" for targets that are not absolute URLs.
RELATIVE_LINK = re.compile(r"\]\((?!\w+:)([^)#]+)(#[^)]*)?\)")
# "## A1 — Title": one sub-issue.
SUB_ISSUE = re.compile(r"^## ([A-J])(\d+) — .+$", re.MULTILINE)


@pytest.mark.parametrize("path", PLAN_DOCS, ids=lambda p: p.name)
def test_relative_links_resolve(path):
    """A dead link in a plan is a sub-issue nobody opens."""
    for target, _anchor in RELATIVE_LINK.findall(path.read_text()):
        resolved = (path.parent / target).resolve()
        assert resolved.exists(), f"{path.name} links to missing {target}"


@pytest.mark.parametrize("path", EPIC_FILES, ids=lambda p: p.name)
def test_every_epic_is_listed_in_the_readme(path):
    """The reverse of the skill-router check: no orphan epics."""
    readme = (PLAN_DIR / "README.md").read_text()
    assert f"epics/{path.name}" in readme, f"{path.name} is not in the epic map"


@pytest.mark.parametrize("path", EPIC_FILES, ids=lambda p: p.name)
def test_every_epic_declares_sub_issues(path):
    """An epic with no sub-issues is a wish, not a plan."""
    subs = SUB_ISSUE.findall(path.read_text())
    assert subs, f"{path.name} declares no '## X<n> — Title' sub-issues"

    letter = path.name[0]
    assert all(prefix == letter for prefix, _ in subs), (
        f"{path.name} contains sub-issues from another epic"
    )
    numbers = [int(n) for _, n in subs]
    assert numbers == list(range(1, len(numbers) + 1)), (
        f"{path.name} sub-issues are not numbered 1..n: {numbers}"
    )


@pytest.mark.parametrize("path", EPIC_FILES, ids=lambda p: p.name)
def test_every_epic_points_at_the_design(path):
    """The design is the system; the epics are only how it gets built."""
    assert "../design.md" in path.read_text(), f"{path.name} does not link the design"
