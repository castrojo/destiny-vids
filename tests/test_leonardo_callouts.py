"""Tests for Leonardo weapon callout generation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts import build_leonardo_callouts as callouts  # noqa: E402


def test_callout_specs_count():
    assert len(callouts.CALLOUTS) == 6


def test_callout_spec_fields():
    for spec in callouts.CALLOUTS:
        assert "id" in spec
        assert "title" in spec
        assert "subtitle" in spec
        assert "description" in spec
        assert "weapon_key" in spec
        assert spec["start_time"] >= 0
        assert spec["duration"] > 0


def test_render_callout_card(tmp_path):
    # Create a small dummy weapon image
    w_dir = tmp_path / "weapons"
    w_dir.mkdir()
    dummy = Image.new("RGBA", (100, 200), (255, 0, 0, 255))
    dummy.save(w_dir / "spear.png")

    spec = callouts.CALLOUTS[0]
    img = callouts.render_callout_card(spec, w_dir)
    assert img.size == (2560, 1440)
    assert img.mode == "RGBA"

    # Verify callout container area has content
    crop = img.crop((80, 740, 80 + 896, 740 + 520))
    alpha = crop.split()[-1]
    assert alpha.getbbox() is not None
