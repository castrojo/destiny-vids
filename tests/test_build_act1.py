"""Tests for the act I builder (scripts/build_act1.py)."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_act_one_gates_its_delivered_master_peak():
    """Issue #219: every scripts/ builder must end with the same peak gate
    act VII uses, so a rebuild cannot put a clipping master back."""
    source = (REPO_ROOT / "scripts" / "build_act1.py").read_text()
    assert "peaks.trim_master_peak((REPO_ROOT / MASTER).resolve())" in source
