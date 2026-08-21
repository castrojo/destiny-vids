#!/usr/bin/env python3
"""Check the docs tree for broken relative Markdown links."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if len(sys.argv) > 1:
    REPO_ROOT = Path(sys.argv[1]).resolve()

DOC_ROOTS = ["docs", "README.md", "AGENTS.md"]
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
FENCED_BLOCK = re.compile(r"^(```|~~~).*?^\1\s*$", re.MULTILINE | re.DOTALL)


def markdown_files() -> list[Path]:
    seen: list[Path] = []
    for root in DOC_ROOTS:
        path = REPO_ROOT / root
        if path.is_file():
            seen.append(path)
        elif path.exists():
            seen.extend(sorted(path.rglob("*.md")))
    return seen


broken = []
for source in markdown_files():
    text = FENCED_BLOCK.sub("", source.read_text(encoding="utf-8"))
    for target in LINK.findall(text):
        target = target.strip()
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target = target.split("#", 1)[0]
        if target and not (source.parent / target).resolve().exists():
            broken.append((source, target))
            print(
                f"error: broken link in {source.relative_to(REPO_ROOT)} -> {target}",
                file=sys.stderr,
            )

if broken:
    raise SystemExit(1)

print(f"{len(markdown_files())} Markdown file(s) checked; no broken links")
