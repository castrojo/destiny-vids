"""Existence is not freshness.

A builder that regenerates an intermediate only when it is MISSING will
happily consume yesterday's PNGs, produce a new master from them, and publish
a digest that says the act is current. Every delivery gate then reports green
over a video that is out of date -- which is exactly how a main title shipped
17 hours stale while `deliver.py` and `megacut.py` both passed.

These tests pin the rule: a derived file is regenerated when it is older than
what derives it, and no flag is required to make that happen.
"""

import ast
import os
from pathlib import Path

import pytest

from tools import freshness

REPO = Path(__file__).resolve().parents[1]


def test_a_missing_output_is_stale(tmp_path):
    src = tmp_path / "card.html"
    src.write_text("x")
    assert freshness.needs_render([src], [tmp_path / "plate.png"])


def test_an_output_older_than_its_source_is_stale(tmp_path):
    """THE DEFECT: `cards/maintitle.html` moved, the PNG did not."""
    src = tmp_path / "card.html"
    out = tmp_path / "plate.png"
    out.write_text("old")
    src.write_text("new")
    os.utime(out, (1_000, 1_000))
    os.utime(src, (2_000, 2_000))

    assert freshness.needs_render([src], [out])
    assert freshness.stale_outputs([src], [out]) == [out]


def test_a_current_output_is_not_rebuilt(tmp_path):
    """The guard must not become a wall that re-renders on every run."""
    src = tmp_path / "card.html"
    out = tmp_path / "plate.png"
    src.write_text("x")
    out.write_text("y")
    os.utime(src, (1_000, 1_000))
    os.utime(out, (2_000, 2_000))

    assert not freshness.needs_render([src], [out])


def test_a_directory_source_is_checked_file_by_file(tmp_path):
    """`cards/` is passed whole; a single edited template inside it counts."""
    srcdir = tmp_path / "cards"
    srcdir.mkdir()
    (srcdir / "a.html").write_text("a")
    out = tmp_path / "plate.png"
    out.write_text("y")
    os.utime(srcdir / "a.html", (3_000, 3_000))
    os.utime(out, (2_000, 2_000))

    assert freshness.needs_render([srcdir], [out])


def _gates_a_render_on_bare_existence(path):
    """Find `if ... not <something>.exists(): render...` card/plate gates.

    Looks for a bare `.exists()` test guarding a call whose name renders an
    intermediate. The fixed builders read
    `if args.cards or freshness.needs_render(...)`, which this does not match.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        calls = [c for c in ast.walk(node.test) if isinstance(c, ast.Call)]
        names = {c.func.attr for c in calls if isinstance(c.func, ast.Attribute)}
        if "exists" not in names or "needs_render" in names:
            continue
        rendered = [
            c.func.id for c in ast.walk(node)
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
            and "render" in c.func.id and "card" in c.func.id.lower()
        ]
        if rendered:
            offenders.append(f"{path.name}:{node.lineno} gates {rendered[0]}")
    return offenders


@pytest.mark.parametrize(
    "script", sorted((REPO / "scripts").glob("build_*.py")),
    ids=lambda p: p.name)
def test_no_builder_gates_a_card_render_on_bare_existence(script):
    """REGRESSION, and it shipped: see this module's docstring.

    `not plate_x.png.exists()` asks whether the file is THERE. The question a
    builder has to ask is whether it is OLDER THAN THE TEMPLATE, which is
    `tools/freshness.needs_render`.
    """
    offenders = _gates_a_render_on_bare_existence(script)
    assert not offenders, (
        "existence is not freshness -- use tools/freshness.needs_render():\n  "
        + "\n  ".join(offenders))
