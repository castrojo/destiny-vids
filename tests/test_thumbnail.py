import random

import pytest
from PIL import Image

from tools import credits, thumbnail


def test_bluefin_prefix_becomes_the_eyebrow():
    assert thumbnail.split_bluefin_title("Bluefin: Your Final Trial") == (
        "BLUEFIN",
        "YOUR FINAL TRIAL",
    )
    assert thumbnail.split_bluefin_title("Bluefin and Saint 14") == (
        "BLUEFIN",
        "AND SAINT 14",
    )


def test_split_rejects_a_title_without_the_bluefin_prefix():
    with pytest.raises(ValueError):
        thumbnail.split_bluefin_title("Saint 14 and the Blueberries")


def test_split_preserves_later_colons_and_every_title_word():
    assert thumbnail.split_bluefin_title("Bluefin and Saint 14: A Toast") == (
        "BLUEFIN",
        "AND SAINT 14: A TOAST",
    )


def test_jungle_thumbnail_is_youtube_sized(tmp_path):
    source = tmp_path / "source.jpg"
    Image.new("RGB", (480, 360), "#6b4423").save(source)
    out = tmp_path / "thumb.jpg"
    thumbnail.save_jungle_thumbnail(
        source, "Bluefin: Care for a Drink?", out
    )
    assert Image.open(out).size == (1920, 1080)
    assert out.stat().st_size < 2_000_000


def test_render_returns_a_full_size_rgb_frame():
    source = Image.new("RGB", (1280, 720), "#a66a3f")
    card = thumbnail.render_jungle_thumbnail(
        source, "Bluefin and the Blueberries"
    )
    assert card.size == (1920, 1080)
    assert card.mode == "RGB"


def test_letterbox_bars_are_cropped_before_fitting():
    content = Image.new("RGB", (480, 360), "#6b4423")
    boxed = Image.new("RGB", (480, 480), "black")
    boxed.paste(content, (0, 60))
    from_boxed = thumbnail.render_jungle_thumbnail(
        boxed, "Bluefin: Care for a Drink?"
    )
    from_bare = thumbnail.render_jungle_thumbnail(
        content, "Bluefin: Care for a Drink?"
    )
    assert from_boxed.tobytes() == from_bare.tobytes()


def test_all_dark_frame_renders_the_original_frame():
    source = Image.new("RGB", (1280, 720), "black")
    card = thumbnail.render_jungle_thumbnail(
        source, "Bluefin: Care for a Drink?"
    )
    assert card.size == (1920, 1080)
    assert card.getpixel((5, 5)) == (0, 0, 0)
    assert card.getpixel((1914, 1074)) == (0, 0, 0)


def test_narrow_bright_band_does_not_zoom_into_the_sliver():
    source = Image.new("RGB", (1280, 720), "black")
    band = Image.new("RGB", (1280, 30), "#a66a3f")
    source.paste(band, (0, 345))
    card = thumbnail.render_jungle_thumbnail(
        source, "Bluefin: Care for a Drink?"
    )
    assert card.size == (1920, 1080)
    bright = sum(
        1 for pixel in card.convert("L").getdata() if pixel > 100
    )
    # The band covers ~4% of the frame; a sliver crop would fill all of it.
    assert bright / (1920 * 1080) < 0.25


def test_listing_size_keeps_visible_title_ink(tmp_path):
    source = Image.new("RGB", (1280, 720), "#a66a3f")
    full = thumbnail.render_jungle_thumbnail(
        source, "Bluefin and the Blueberries"
    )
    listing = full.resize((336, 189), Image.Resampling.LANCZOS)
    top = listing.crop((0, 0, 336, 95))
    assert max(pixel[0] for pixel in top.getdata()) > 240


def test_long_title_still_fits_above_the_midpoint():
    source = Image.new("RGB", (1280, 720), "#a66a3f")
    full = thumbnail.render_jungle_thumbnail(
        source,
        "Bluefin: The Absolutely Final Trial of the Fittest "
        "Guardian in the Whole Wide Jungle",
    )
    assert full.size == (1920, 1080)
    listing = full.resize((336, 189), Image.Resampling.LANCZOS)
    top = listing.crop((0, 0, 336, 95))
    assert max(pixel[0] for pixel in top.getdata()) > 240


def _title_row_bands(card, threshold=240):
    """Count contiguous row bands holding near-white (title) ink."""
    gray = card.convert("L")
    w, h = gray.size
    bands = 0
    in_band = False
    for y in range(h):
        if gray.crop((0, y, w, y + 1)).getextrema()[1] > threshold:
            if not in_band:
                bands += 1
                in_band = True
        else:
            in_band = False
    return bands


def test_long_title_sits_on_at_most_two_baselines():
    source = Image.new("RGB", (1280, 720), "#a66a3f")
    card = thumbnail.render_jungle_thumbnail(
        source,
        "Bluefin: The Absolutely Final Trial of the Fittest "
        "Guardian in the Whole Wide Jungle",
    )
    assert _title_row_bands(card) <= 2


def test_long_title_uses_two_baselines_inside_the_title_margins():
    source = Image.new("RGB", (1280, 720), "#a66a3f")
    card = thumbnail.render_jungle_thumbnail(
        source,
        "Bluefin: The Absolutely Final Trial of the Fittest "
        "Guardian in the Whole Wide Jungle",
    )
    # A single overflowing line must not pass: exactly two baselines.
    assert _title_row_bands(card) == 2
    # ...and every near-white (title) column stays inside the horizontal
    # title margins, so no line can spill past _MAX_LINE_WIDTH. The floor's
    # mandated minimum-overflow split may exceed the budget by less than a
    # stroke width (the 8px outline is part of the title treatment), so the
    # tolerance is exactly _STROKE; a single overflowing line spills by
    # hundreds of pixels and cannot pass.
    gray = card.convert("L")
    w, h = gray.size
    inked_x = [
        x for x in range(w)
        if gray.crop((x, 0, x + 1, h)).getextrema()[1] > 240
    ]
    margin = (thumbnail.SIZE[0] - thumbnail._MAX_LINE_WIDTH) // 2
    margin -= thumbnail._STROKE
    assert min(inked_x) >= margin
    assert max(inked_x) < thumbnail.SIZE[0] - margin


def test_long_title_fits_inside_margins_without_adwaita(monkeypatch):
    """CI font regression: DejaVu Sans Mono is wider than Adwaita, so the
    72px floor's best split overflows _MAX_LINE_WIDTH there; the fitter must
    shrink below the floor instead of letting the title spill its margins."""
    monkeypatch.setattr(
        credits, "ADWAITA_SANS", "/nonexistent/AdwaitaSans-Regular.ttf"
    )
    source = Image.new("RGB", (1280, 720), "#a66a3f")
    card = thumbnail.render_jungle_thumbnail(
        source,
        "Bluefin: The Absolutely Final Trial of the Fittest "
        "Guardian in the Whole Wide Jungle",
    )
    # A single overflowing line must not pass: exactly two baselines.
    assert _title_row_bands(card) == 2
    # Every near-white (title fill) column stays strictly inside the
    # horizontal title margins; the fill excludes the near-black stroke, so
    # no stroke tolerance is needed here.
    gray = card.convert("L")
    w, h = gray.size
    inked_x = [
        x for x in range(w)
        if gray.crop((x, 0, x + 1, h)).getextrema()[1] > 240
    ]
    margin = (thumbnail.SIZE[0] - thumbnail._MAX_LINE_WIDTH) // 2
    assert min(inked_x) >= margin
    assert max(inked_x) < thumbnail.SIZE[0] - margin


def _noisy_source(path):
    """A deterministic frame noisy enough that quality 95 crosses the cap."""
    rng = random.Random(1337)
    noise = Image.frombytes("RGB", (1920, 1080), rng.randbytes(1920 * 1080 * 3))
    blended = Image.blend(Image.new("RGB", (1920, 1080), "#6b4423"), noise, 0.25)
    blended.save(path, "JPEG", quality=92)
    return blended


def test_quality_retry_genuinely_crosses_the_q95_boundary(tmp_path):
    source = tmp_path / "source.jpg"
    rendered = _noisy_source(source)
    title = "Bluefin: Care for a Drink?"
    q95 = tmp_path / "q95.jpg"
    thumbnail.render_jungle_thumbnail(rendered, title).save(
        q95, "JPEG", quality=95, subsampling=0, optimize=True, progressive=True
    )
    assert q95.stat().st_size > thumbnail.BYTE_CAP
    out = thumbnail.save_jungle_thumbnail(source, title, tmp_path / "thumb.jpg")
    assert out.stat().st_size <= thumbnail.BYTE_CAP


def test_impossible_cap_raises(tmp_path, monkeypatch):
    source = tmp_path / "source.jpg"
    Image.new("RGB", (800, 450), "#6b4423").save(source)
    monkeypatch.setattr(thumbnail, "BYTE_CAP", 1)
    with pytest.raises(ValueError):
        thumbnail.save_jungle_thumbnail(
            source, "Bluefin: Care for a Drink?", tmp_path / "thumb.jpg"
        )


def test_extract_source_frame_seeks_before_the_input(tmp_path):
    calls = []

    def fake_runner(argv, check):
        calls.append((argv, check))

    source = tmp_path / "src.mp4"
    source.touch()
    out = tmp_path / "frames" / "frame.png"
    result = thumbnail.extract_source_frame(
        ["ffmpeg"], source, 12.3456, out, runner=fake_runner
    )
    assert result == out
    argv, check = calls[0]
    assert check is True
    assert argv[argv.index("-ss") + 1] == "12.346"
    assert argv.index("-ss") < argv.index("-i")
    assert argv[argv.index("-frames:v") + 1] == "1"
    assert argv[argv.index("-i") + 1] == str(source.resolve())
    assert argv[-1] == str(out.resolve())
    assert out.parent.is_dir()
