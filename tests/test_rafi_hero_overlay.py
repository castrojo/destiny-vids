"""The overlay's arithmetic, and the one thing that actually matters: it scans.

Two properties are worth a test here. The first is that the corner furniture
lands in the margin the character leaves rather than on top of him -- the
margin is derived from the character's scale, so a change to one has to move
the other. The second is that every QR in the finished overlay decodes back to
the URL in the record. A placement test that passes while the code is
unreadable would be worse than no test at all.

Both recorded videos are pinned: rafi01 to the numbers its shipped v3/v4
encodes were built against, rafi02 to the union bbox measured from
RAFI_02_SP.mp4 (x 40..1753, y 231..1944 of the 1754x2046 depadded frame).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts import build_rafi_hero_overlay as overlay  # noqa: E402
from scripts import qrcard as qr  # noqa: E402

VIDEOS = ["rafi01", "rafi02"]


@pytest.fixture(scope="module")
def doc():
    return overlay.load()


@pytest.fixture(scope="module", params=VIDEOS)
def built(request):
    return request.param, overlay.build(overlay.load(), video=request.param)


def card_spec(doc, card_id="archers"):
    return next(c for c in doc["cards"] if c["id"] == card_id)


def test_every_recorded_video_scales_its_character_off_the_frame_edges(doc):
    """The whole point of the pass: 1224 tall in a 1440 frame, not 1440."""
    for video in VIDEOS:
        char = overlay.character(doc, video)
        assert char["height"] == 1224, video
        air = (doc["frame"]["height"] - char["height"]) / 2
        assert air == 108, video


def test_character_box_is_centred_and_even(doc):
    for video in VIDEOS:
        left, right = overlay.character_box(doc, video)
        assert (right - left) % 2 == 0, "ffmpeg's scale=-2 yields even widths"
        assert left == doc["frame"]["width"] - right, f"{video}: centred"


def test_rafi01_character_box_matches_the_shipped_build(doc):
    """The numbers RAFI_01's shipped encode was built against."""
    assert overlay.character_box(doc, "rafi01") == (702, 1858)


def test_rafi02_character_box_matches_the_measured_union_bbox(doc):
    """RAFI_02's crop is square (1714x1714), so he lands 1224x1224 centred."""
    assert overlay.character(doc, "rafi02")["crop_w"] == 1714
    assert overlay.character(doc, "rafi02")["crop_h"] == 1714
    assert overlay.character_box(doc, "rafi02") == (668, 1892)


def test_card_sits_in_the_bottom_right_corner(doc):
    """A corner, not a centre.

    The card was vertically centred in the right margin first. It never
    overlapped the character and it still competed with him, because it sat at
    his eye level. Owner: "why are you blocking art?"
    """
    spec = card_spec(doc)
    for video in VIDEOS:
        x, y = overlay.card_box(doc, spec, video)
        place = doc["placement"]
        width = place["width"]
        height = int(round(width * (1 + qr.STRIP_FRAC)))
        margin = place["margin"]
        assert x + width == doc["frame"]["width"] - margin, video
        assert y + height == doc["frame"]["height"] - margin, video
        assert y > doc["frame"]["height"] // 2, "in the lower half"


def test_card_never_overlaps_the_character(doc):
    spec = card_spec(doc)
    for video in VIDEOS:
        left, right = overlay.character_box(doc, video)
        x, _ = overlay.card_box(doc, spec, video)
        assert x >= right, f"{video}: the card starts where the character ends"
        assert x + doc["placement"]["width"] <= doc["frame"]["width"]
        assert x > left


def test_a_card_that_would_cover_the_character_is_refused(doc):
    """The guarantee has to be enforced, not just currently true."""
    spec = card_spec(doc)
    fat = {**doc, "placement": {**doc["placement"], "width": 1200}}
    for video in VIDEOS:
        with pytest.raises(RuntimeError, match="over the character"):
            overlay.card_box(fat, spec, video)


def test_overlay_is_frame_sized_and_otherwise_transparent(built, doc):
    video, img = built
    assert img.size == (doc["frame"]["width"], doc["frame"]["height"])
    assert img.mode == "RGBA"
    assert img.getpixel((10, 10))[3] == 0, "the picture shows through"
    assert img.getpixel((1280, 720))[3] == 0, "nothing over the character"


def test_every_card_in_the_overlay_decodes_back_to_its_recorded_url(built, doc):
    video, img = built
    width = doc["placement"]["width"]
    height = int(round(width * (1 + qr.STRIP_FRAC)))
    for spec in doc["cards"]:
        x, y = overlay.card_box(doc, spec, video)
        crop = img.crop((x, y, x + width, y + height))
        assert qr.decodes(crop, spec["url"], qr.DAY_PLATE), (video, spec["id"])
        assert qr.decodes(crop, spec["url"], qr.NIGHT_PLATE), (video, spec["id"])


def test_the_wordmark_is_drawn_with_blue_dots(built, doc):
    """wolves.projectbluefin.io: white glyphs, the dots in the brand blue."""
    video, img = built
    mark = overlay.draw_wordmark(doc)
    x, y = overlay.wordmark_box(doc, mark)
    region = img.crop((x, y, x + mark.width, y + mark.height))
    opaque = [p for p in region.getdata() if p[3] > 0]
    assert opaque, f"{video}: the wordmark is on the frame"
    assert any(p[:3] == qr.BLUEFIN for p in opaque), "the dots are blue"


def test_an_unknown_video_is_refused(doc):
    with pytest.raises(KeyError, match="no character block"):
        overlay.character_box(doc, "rafi99")


def test_the_copy_comes_from_the_record_not_the_builder(doc):
    spec = card_spec(doc)
    assert spec["eyebrow"] == "SUPPORT"
    assert spec["name"] == "UNLEASH THE ARCHERS"
    assert spec["url"].startswith("https://")
    assert doc["wordmark"]["text"] == "wolves.projectbluefin.io"


def test_an_unscannable_card_is_refused_rather_than_written(doc):
    """The gate is the design's referee, so it has to be able to say no."""
    broken = {**doc, "placement": {**doc["placement"], "width": 60}}
    with pytest.raises(RuntimeError, match="does not scan"):
        overlay.build(broken)
