import hashlib
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import fetch_wordmark  # noqa: E402

MANIFEST = REPO_ROOT / "stories" / "uta-general-ensemble.json"
WEBSITE_SHA256 = "4ae1d486e6e73743fad1e1ef625615c4a28e72bbcc0a966ba3c5294303e4e380"


def _svg(
    fill="#000000",
    fin="#4285f4",
    rect="",
    viewbox=fetch_wordmark.WEBSITE_VIEWBOX,
):
    return (
        f'<svg viewBox="{viewbox}">'
        f"{rect}"
        f'<path fill="{fill}" d="M0 0h10v10z"/>'
        f'<path fill="{fin}" d="M12 0h10v10z"/>'
        "</svg>"
    )


def test_validate_svg_accepts_the_pinned_website_mark():
    svg = _svg(fill="#fff")
    fetch_wordmark.validate_svg(
        svg,
        expected_sha256=hashlib.sha256(svg.encode()).hexdigest(),
        preserve_colors=True,
        expected_viewbox=fetch_wordmark.WEBSITE_VIEWBOX,
    )
    assert "#4285f4" in svg
    assert fetch_wordmark.WEBSITE_VIEWBOX in svg


def test_manifest_uses_the_verified_website_asset_hash():
    import json

    wordmark = json.loads(MANIFEST.read_text())["wordmark"]
    assert wordmark["source_path"] == "public/brands/bluefin-wordmark-light.svg"
    assert wordmark["sha256"] == WEBSITE_SHA256


def test_validate_svg_accepts_the_legacy_default_shape():
    svg = _svg(viewbox=fetch_wordmark.LEGACY_VIEWBOX)
    fetch_wordmark.validate_svg(
        svg,
        preserve_colors=False,
        expected_viewbox=fetch_wordmark.LEGACY_VIEWBOX,
    )
    assert fetch_wordmark.LEGACY_VIEWBOX in svg


def test_validate_svg_rejects_background_rect_or_wrong_hash():
    with pytest.raises(ValueError, match="sha256"):
        fetch_wordmark.validate_svg("<svg/>", expected_sha256="0" * 64)

    with pytest.raises(ValueError, match="background"):
        fetch_wordmark.validate_svg(
            _svg(rect='<rect width="105.658"/>'),
            expected_sha256=None,
        )


def test_parser_defaults_preserve_existing_credits_behavior():
    args = fetch_wordmark.build_parser().parse_args([])
    assert args.source_url == fetch_wordmark.DEFAULT_SOURCE_URL
    assert args.expected_sha256 is None
    assert args.out == fetch_wordmark.DEFAULT_OUT
    assert args.width == 1600
    assert args.preserve_colors is False


def test_main_recolors_the_default_wordmark_and_keeps_the_default_width(
    monkeypatch, tmp_path
):
    svg = _svg(viewbox=fetch_wordmark.LEGACY_VIEWBOX)
    out_path = tmp_path / "bluefin-wordmark.png"
    seen = {}

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return self.payload

    def fake_urlopen(url, timeout=30):
        seen["url"] = url
        seen["timeout"] = timeout
        return FakeResponse(svg.encode())

    def fake_rasterise(svg_text, out, width=1600):
        seen["rasterised_svg"] = svg_text
        seen["out"] = Path(out)
        seen["width"] = width

    monkeypatch.setattr(fetch_wordmark, "DEFAULT_OUT", out_path)
    monkeypatch.setattr(fetch_wordmark.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(fetch_wordmark, "rasterise", fake_rasterise)
    monkeypatch.setattr(fetch_wordmark, "trim", lambda path: (12, 34))

    assert fetch_wordmark.main([]) == 0
    assert seen["url"] == fetch_wordmark.DEFAULT_SOURCE_URL
    assert seen["timeout"] == 30
    assert seen["out"] == out_path
    assert seen["width"] == 1600
    assert fetch_wordmark.LEGACY_VIEWBOX in seen["rasterised_svg"]
    assert 'fill="#ffffff"' in seen["rasterised_svg"]
    assert '#000000' not in seen["rasterised_svg"]


def test_main_preserves_colors_when_requested_and_honors_custom_width(
    monkeypatch, tmp_path
):
    svg = _svg(fill="#fff", viewbox=fetch_wordmark.WEBSITE_VIEWBOX)
    out_path = tmp_path / "assets" / "bluefin-wordmark.png"
    seen = {}

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return self.payload

    def fake_urlopen(url, timeout=30):
        seen["url"] = url
        return FakeResponse(svg.encode())

    def fake_rasterise(svg_text, out, width=1600):
        seen["rasterised_svg"] = svg_text
        seen["out"] = Path(out)
        seen["width"] = width

    monkeypatch.setattr(fetch_wordmark.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(fetch_wordmark, "rasterise", fake_rasterise)
    monkeypatch.setattr(fetch_wordmark, "trim", lambda path: (12, 34))

    assert fetch_wordmark.main(
        [
            "--source-url",
            "https://raw.githubusercontent.com/projectbluefin/website/"
            "c03567d972bb9cf52ab0676de5068a54f62f8a48/public/brands/"
            "bluefin-wordmark-light.svg",
            "--expected-sha256",
            hashlib.sha256(svg.encode()).hexdigest(),
            "--out",
            str(out_path),
            "--width",
            "1200",
            "--preserve-colors",
        ]
    ) == 0
    assert seen["url"].endswith("bluefin-wordmark-light.svg")
    assert seen["out"] == out_path
    assert seen["width"] == 1200
    assert seen["rasterised_svg"] == svg
