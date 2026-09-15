"""Tests for YouTube metadata generator."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts import generate_youtube_metadata as gen  # noqa: E402


def test_metadata_entries_have_required_hashtags():
    for item in gen.METADATA:
        desc = gen.format_description(item)
        assert "#7wolves" in desc
        assert "#k8s" in desc
        assert "#linux" in desc


def test_metadata_tags_include_required():
    for item in gen.METADATA:
        tags = item["tags"]
        assert "7wolves" in tags
        assert "k8s" in tags
        assert "linux" in tags
        assert "bluefin" in tags


def test_music_videos_have_full_band_credits():
    for item in gen.METADATA:
        if "music" in item and "artist" in item["music"]:
            assert len(item["music"]["artist"]) > 0
            assert len(item["music"]["song"]) > 0
            desc = gen.format_description(item)
            assert "Music & Band Credits" in desc
            assert item["music"]["artist"] in desc


def test_generated_json_file_validity(tmp_path, monkeypatch):
    out_dir = tmp_path / "youtube-metadata"
    json_out = tmp_path / "bluefin-youtube-metadata.json"
    monkeypatch.setattr(gen, "VIDEOS_DIR", tmp_path)
    monkeypatch.setattr(gen, "OUT_DIR", out_dir)
    monkeypatch.setattr(gen, "JSON_OUT", json_out)
    gen.main()
    assert json_out.exists()
    data = json.loads(json_out.read_text(encoding="utf-8"))
    assert len(data) >= 15
    for vid, item in data.items():
        assert "id" in item
        assert "title" in item
        assert "description" in item
        assert "#7wolves" in item["description"]
        assert "#k8s" in item["description"]
        assert "#linux" in item["description"]
