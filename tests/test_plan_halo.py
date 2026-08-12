"""The Halo campaign plan must stay navigable while it exists.

A plan is only useful if its map matches the files on disk: an issue nobody can
find never gets filed, and a dead link sends the next agent to a file that does
not exist. Mirrors the contract tests/test_skill_catalog.py enforces for the
skill router. Per the `docs/plans/` lifecycle in `AGENTS.md`, nothing here
asserts the tree *exists*: every check iterates over glob results, so deleting
the tree when its issues are filed is always green.
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


def _slugify(heading):
    """GitHub's heading anchor rule: lowercase, drop punctuation, spaces to '-'."""
    text = heading.lstrip("#").strip().lower()
    text = re.sub(r"[^\w\s-]", "", text.replace("_", ""))
    return text.replace(" ", "-")


def _anchors(path):
    return {_slugify(line) for line in path.read_text().splitlines()
            if re.match(r"#{1,6}\s", line)}


@pytest.mark.parametrize("path", PLAN_DOCS, ids=lambda p: p.name)
def test_no_dead_section_anchors(path):
    """A renumbered section silently breaks every link that pointed at it."""
    for target, anchor in re.findall(r"\]\((?!https?:)([^)#]*?(?:\.md)?)#([^)]+)\)", path.read_text()):
        doc = (path.parent / target) if target else path
        if not doc.exists():
            continue  # dead file links are the other test's job
        assert anchor in _anchors(doc), f"{path.name} -> {target}#{anchor}"


@pytest.mark.parametrize("path", PLAN_DOCS, ids=lambda p: p.name)
def test_every_referenced_plan_id_exists(path):
    """A `Depends on: H-14` pointing at nothing is a plan that cannot be worked."""
    known = {p.name.split("-", 1)[0] for p in ISSUES}
    for number in re.findall(r"\bH-(\d\d)\b", path.read_text()):
        assert number in known, f"{path.name} references H-{number}, which has no issue file"
