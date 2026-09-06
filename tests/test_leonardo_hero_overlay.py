"""Tests for the Leonardo hero overlay geometry and decodability."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

pytest.importorskip("segno", reason="QR layout is a frame-touching extra")
pytest.importorskip("numpy", reason="QR layout is a frame-touching extra")
pytest.importorskip("cv2", reason="the decode gate needs OpenCV")

from scripts import build_leonardo_hero_overlay as overlay  # noqa: E402
from scripts import qrcard as qr  # noqa: E402


@pytest.fixture(scope="module")
def built_overlay():
    return overlay.build_overlay()


def test_overlay_dimensions_and_mode(built_overlay):
    assert built_overlay.size == (2560, 1440)
    assert built_overlay.mode == "RGBA"


def test_qr_card_decodes_in_overlay(built_overlay):
    # QR card box at bottom right
    card_w = 280
    card_h = int(round(card_w * (1 + qr.STRIP_FRAC)))
    x0 = 2560 - 48 - card_w
    y0 = 1440 - 48 - card_h
    qr_crop = built_overlay.crop((x0, y0, x0 + card_w, y0 + card_h))

    assert qr.decodes(qr_crop, "https://www.unleashthearchers.com/", qr.DAY_PLATE)
    assert qr.decodes(qr_crop, "https://www.unleashthearchers.com/", qr.NIGHT_PLATE)


def test_band_video_window_is_transparent(built_overlay):
    # Window interior (x=80..976, y=190..694) must be transparent so video shows through
    center_pixel = built_overlay.getpixel((80 + 448, 190 + 252))
    assert center_pixel[3] == 0, f"Expected transparent center pixel in video window, got {center_pixel}"


def test_wordmark_presence(built_overlay):
    # Bottom left margin should have non-transparent pixels for the wordmark
    x0, y0 = 48, 1440 - 48 - 44
    sample = built_overlay.crop((x0, y0 - 30, x0 + 400, y0 + 30))
    alpha = sample.split()[-1]
    assert alpha.getbbox() is not None
