"""Tests for Bluefin: Not Your Monster ensemble cut."""

import json
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parents[1]
RECORD_PATH = REPO / "stories" / "not-your-monster-ensemble.json"
INTRO_PATH = REPO / "stories" / "not-your-monster-intro-cards.json"


@pytest.fixture
def record():
    return json.loads(RECORD_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def intro_record():
    return json.loads(INTRO_PATH.read_text(encoding="utf-8"))


def test_manifest_loads_and_has_required_keys(record):
    assert record["edit_id"] == "not-your-monster-ensemble"
    assert record["delivery"]["width"] == 2560
    assert record["delivery"]["height"] == 1440
    assert record["delivery"]["frame_rate"] == "25/1"
    assert record["delivery"]["output"] == "BLUEFIN_NOT_YOUR_MONSTER.mp4"
    assert record["delivery"]["programme_frames"] == 9754


def test_source_metadata_matches_probed_facts(record):
    src = record["source"]
    assert src["youtube_id"] == "uJvh7Ku7K6Q"
    assert src["frame_count"] == 9616
    assert src["frame_rate"] == "25/1"
    assert src["audio_sample_rate_hz"] == 48000
    assert len(src["sha256"]) == 64


def test_kids_stations_and_geometry(record):
    kids = record["kids"]
    assert len(kids) == 4
    kid_ids = {k["id"] for k in kids}
    assert kid_ids == {"LAKSHMI", "RAFI_01", "LEONARDO", "RAFI_02"}
    for k in kids:
        assert k["use_frames"] > 0
        assert k["width"] > 0


def test_callout_schedule_covers_26_items(record):
    schedule = record["callout_schedule"]
    assert len(schedule) == 26
    # All items must be in the bottom pocket
    for item in schedule:
        assert item["pocket"] == "bottom"
        assert item["start_seconds"] >= 0
        assert item["hold_seconds"] > 0
        assert item["start_seconds"] + item["hold_seconds"] <= record["source"]["duration_seconds"]


def test_intro_cards_manifest(intro_record):
    plates = intro_record["plates"]
    assert len(plates) == 1
    p = plates[0]
    assert p["kind"] == "maintitle"
    assert p["label"] == "PROJECT BLUEFIN"
    assert "Not Your Monster" in p["title"]


def test_background_graph_generator():
    from scripts.build_not_your_monster_ensemble import build_background_graph, WALLPAPERS
    inputs, chain = build_background_graph(WALLPAPERS, 384.64)
    assert len(WALLPAPERS) == 17
    assert inputs.count("-loop 1") == 17
    assert chain.count("xfade=transition=fade") == 16
    assert "[bg_out]" in chain
