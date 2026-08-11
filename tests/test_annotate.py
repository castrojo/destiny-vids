"""Tests for the annotator pipeline scaffold (tools/annotate.py).

Everything here runs offline: the StubTagger needs no model and the
fixed-window fallback needs no video file or scenedetect install."""

import re

import pytest

from tools import annotate, derive

TC_PATTERN = re.compile(r"^([0-9]{1,2}:)?[0-9]{1,2}:[0-9]{2}$")

FAKE_VIDEO_RECORD = {
    "video_id": "yt_test_fake",
    "era": "beyond_light",
    "activity": "cinematic",
    "content_type": "cinematic",
    "destination": "europa",
    "subclass_version": "stasis",
    "provenance": {
        "era": {"source": "observed", "label_source": "model", "confidence": 0.99},
        "destination": {"source": "observed", "label_source": "model", "confidence": 0.7},
    },
}


def test_module_imports_without_scenedetect():
    # The module is already imported by the time this runs; just assert the
    # availability flag is a real boolean (False in the test env).
    assert isinstance(annotate.HAVE_SCENEDETECT, bool)


def test_detect_beats_fixed_window_fallback():
    beats = annotate.detect_beats(video_path=None, fps_or_duration=10.0, window_sec=3.0)
    assert [(b["start_sec"], b["end_sec"]) for b in beats] == [
        (0.0, 3.0),
        (3.0, 6.0),
        (6.0, 9.0),
        (9.0, 10.0),
    ]
    for beat in beats:
        assert beat["end_sec"] > beat["start_sec"]
        assert TC_PATTERN.match(beat["start_tc"])
        assert TC_PATTERN.match(beat["end_tc"])
    assert beats[0]["start_tc"] == "0:00"
    assert beats[1]["start_tc"] == "0:03"


def test_detect_beats_accepts_fps_frame_pair():
    beats = annotate.detect_beats(None, (24.0, 240), window_sec=5.0)  # 10 s
    assert beats[-1]["end_sec"] == 10.0
    assert len(beats) == 2


def test_sec_to_tc():
    assert annotate.sec_to_tc(0) == "0:00"
    assert annotate.sec_to_tc(62) == "1:02"
    assert annotate.sec_to_tc(3723) == "1:02:03"


def test_stub_tagger_is_deterministic():
    tagger = annotate.StubTagger()
    beat = {"start_sec": 0.0, "end_sec": 3.0, "start_tc": "0:00", "end_tc": "0:03"}
    assert tagger.tag_beat("v", beat, []) == tagger.tag_beat("v", beat, [])


def test_stub_pipeline_assembles_valid_segments():
    beats = annotate.detect_beats(None, 12.0)
    tagger = annotate.StubTagger()
    leads = derive.load_leads()
    segments = [
        annotate.validate_segment(
            annotate.assemble_segment(FAKE_VIDEO_RECORD, beat, tagger.tag_beat("yt_test_fake", beat, []), leads)
        )
        for beat in beats
    ]
    assert len(segments) == len(beats) == 4

    for segment in segments:
        # inherited video-level defaults came through with provenance
        for field in ("era", "activity", "destination", "subclass_version"):
            assert segment[field] == FAKE_VIDEO_RECORD[field]
            assert segment["provenance"][field]["source"] == "inherited"
        # content_type is also a tagger field: the observed tag overlays the
        # inherited default (spec'd override path, pipeline.md §2)
        assert segment["provenance"]["content_type"]["source"] == "observed"
        # derived fields are heuristics and consistent with derive.py
        for field, value in derive.derive_all(segment, leads).items():
            assert segment["provenance"][field]["label_source"] == "heuristic"
            assert segment[field] == value
        # The stub tags overlays, so its output is CLEAN and therefore usable —
        # a tagger that skipped overlays would silently produce clean=False.
        assert segment["clean"] is True

    # Deterministic stub: beat 0 is a wide traversal shot -> traversal_hero
    # and an ensemble casting; beat 1 is a static idle CU.
    assert segments[0]["traversal_hero"] is True
    assert segments[0]["casting"]["role"] == "ensemble"
    assert segments[1]["traversal_hero"] is False


def test_assembled_segment_provenance_keys_are_taggable_fields():
    # Every provenance key must name a taggable field (schema propertyNames).
    import json

    schema = json.loads(annotate.SEGMENT_SCHEMA_PATH.read_text())
    allowed = set(schema["properties"]["provenance"]["propertyNames"]["enum"])
    beat = {"start_sec": 0.0, "end_sec": 3.0, "start_tc": "0:00", "end_tc": "0:03"}
    segment = annotate.assemble_segment(
        FAKE_VIDEO_RECORD, beat, annotate.StubTagger().tag_beat("yt_test_fake", beat, [])
    )
    annotate.validate_segment(segment)
    assert set(segment["provenance"]) <= allowed


def test_assemble_segment_rejects_non_taggable_tagger_field():
    beat = {"start_sec": 0.0, "end_sec": 3.0, "start_tc": "0:00", "end_tc": "0:03"}
    with pytest.raises(ValueError, match="non-taggable"):
        annotate.assemble_segment(FAKE_VIDEO_RECORD, beat, {"not_a_field": 1})


def test_validate_segment_rejects_invalid():
    with pytest.raises(ValueError):
        annotate.validate_segment({"segment_id": "x"})  # missing required fields


def test_cli_demo_runs(capsys):
    assert annotate.main(["--duration", "6.0"]) == 0
    out = capsys.readouterr().out
    assert "shot detection backend:" in out
    assert "2 segment(s) validated" in out
