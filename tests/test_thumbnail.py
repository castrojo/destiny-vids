import pytest
from PIL import Image

from tools import thumbnail


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


def test_save_retries_quality_until_under_cap(tmp_path, monkeypatch):
    source = tmp_path / "source.jpg"
    Image.new("RGB", (800, 450), "#6b4423").save(source)
    monkeypatch.setattr(thumbnail, "BYTE_CAP", 100_000)
    out = thumbnail.save_jungle_thumbnail(
        source, "Bluefin: Care for a Drink?", tmp_path / "thumb.jpg"
    )
    assert out.stat().st_size <= 100_000


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
