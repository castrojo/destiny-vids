"""Frame-derived programme countdown tests."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts import build_countdown  # noqa: E402
from tools import plate  # noqa: E402



def test_countdown_first_zero_is_exactly_programme_444():
    entries = build_countdown.countdown_entries(217.6, 46.6, target=264.0)
    zero = next(e for e in entries if e["text"] == "00:00")
    assert zero["programme_at"] == pytest.approx(264.0, abs=1e-9)
    assert all(e["text"] != "00:00" for e in entries[:entries.index(zero)])



def test_countdown_values_are_derived_not_authored():
    entries = build_countdown.countdown_entries(260.2, 4.8, target=264.0)
    assert [e["text"] for e in entries] == ["00:04", "00:03", "00:02", "00:01", "00:00"]



def test_countdown_plate_uses_the_lower_matte_safe_area():
    spec = {"kind": "countdown", "text": "00:00"}
    card = plate.render_plate(spec)
    assert card.mode == "RGBA"
    assert card.getchannel("A").getbbox() == (0, 0, card.width, card.height)
    frame = plate.place(card, "countdown-bottom", (0, 138, 1920, 804))
    x0, y0, x1, y1 = frame.getchannel("A").getbbox()
    assert x0 + x1 == plate.FRAME_W - 1
    assert y0 > 942
    assert y1 <= plate.FRAME_H
