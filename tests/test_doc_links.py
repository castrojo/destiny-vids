"""Every relative Markdown link in the docs tree must resolve.

A skill that was split into `<name>/SKILL.md` + `references/` is only an
improvement if the links survived the move. This is the check that proves it:
the migration that inspired this file rewired 25 files, and a single stale
`skills/plates.md` would have sent an agent to a file that no longer exists.

Only *relative* links are checked. External URLs are somebody else's uptime.
Links inside fenced code blocks are not links at all -- they are example
content (a plan doc's sample output, a test snippet) and clicking nothing,
so fences are skipped.
"""
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_ROOTS = ["docs", "README.md", "AGENTS.md"]

LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
FENCE = re.compile(r"^\s*```")


def _prose_lines(text):
    """The document's own lines: fenced code blocks excluded."""
    fenced = False
    for line in text.splitlines():
        if FENCE.match(line):
            fenced = not fenced
            continue
        if not fenced:
            yield line


def _markdown_files():
    seen = []
    for root in DOC_ROOTS:
        p = REPO_ROOT / root
        if p.is_file():
            seen.append(p)
        else:
            seen.extend(sorted(p.rglob("*.md")))
    return seen


@pytest.mark.parametrize("path", _markdown_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_relative_links_resolve(path):
    broken = []
    for line in _prose_lines(path.read_text()):
        for target in LINK.findall(line):
            target = target.strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            # Strip an anchor: docs/foo.md#section -> docs/foo.md
            target = target.split("#", 1)[0]
            if not target:
                continue
            if not (path.parent / target).resolve().exists():
                broken.append(target)
    assert not broken, f"{path.relative_to(REPO_ROOT)} links to missing: {broken}"
