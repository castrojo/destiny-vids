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


def test_cli_demo_subcommand_runs(capsys):
    """The demo keeps working now that `index` exists beside it."""
    assert annotate.main(["demo", "--duration", "6.0"]) == 0
    assert "2 segment(s) validated" in capsys.readouterr().out


def _fake_beats(monkeypatch, count=3):
    beats = [
        {"start_sec": float(i), "end_sec": float(i + 1),
         "start_tc": annotate.sec_to_tc(i), "end_tc": annotate.sec_to_tc(i + 1)}
        for i in range(count)
    ]
    monkeypatch.setattr(annotate, "detect_beats", lambda *a, **k: beats)
    return beats


def _stub_tags(beats):
    tagger = annotate.StubTagger()
    return {
        str(i): tagger.tag_beat("yt_test_fake", beat, [])
        for i, beat in enumerate(beats)
    }


def test_index_video_first_pass_writes_keyframes_and_a_beat_manifest(tmp_path, monkeypatch):
    """Pass one produces the stills a tagger reads, and the timecodes with them."""
    import json

    beats = _fake_beats(monkeypatch)
    written = []

    def fake_extract(video, bts, out_dir, ffmpeg=None):
        from pathlib import Path
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        for i in range(len(bts)):
            p = out_dir / f"{i:03d}.jpg"
            p.write_bytes(b"")
            written.append(p)
        return written

    monkeypatch.setattr(annotate, "extract_keyframes", fake_extract)
    kf = tmp_path / "kf"
    got_beats, segments = annotate.index_video(
        "fake.mp4", FAKE_VIDEO_RECORD, keyframes_dir=kf, log=lambda *a: None)

    assert got_beats == beats
    assert segments == []  # no tags yet: nothing is assembled
    manifest = json.loads((kf / "beats.json").read_text())
    assert [m["beat_index"] for m in manifest] == [0, 1, 2]
    assert [m["keyframe"] for m in manifest] == ["000.jpg", "001.jpg", "002.jpg"]


def test_index_video_second_pass_writes_validated_segments(tmp_path, monkeypatch):
    import json

    beats = _fake_beats(monkeypatch)
    tags = tmp_path / "tags.json"
    tags.write_text(json.dumps(_stub_tags(beats)))

    out_dir = tmp_path / "segments"
    _, segments = annotate.index_video(
        "fake.mp4", FAKE_VIDEO_RECORD, tags_path=tags, out_dir=out_dir,
        log=lambda *a: None)

    assert len(segments) == 3
    files = sorted(p.name for p in out_dir.glob("*.json"))
    assert len(files) == 3
    for segment in segments:
        annotate.validate_segment(segment)
        # derived fields are computed here, never replayed from the tag file
        assert "clean" in segment and "casting" in segment


def test_index_video_tag_file_must_cover_every_beat(tmp_path, monkeypatch):
    """A tag file is only valid against the shot list its own pass produced."""
    import json

    beats = _fake_beats(monkeypatch)
    tags = tmp_path / "tags.json"
    partial = _stub_tags(beats)
    partial.pop("2")
    tags.write_text(json.dumps(partial))

    # Caught up front, on the count, before a single segment is written.
    with pytest.raises(ValueError, match="tagged beat"):
        annotate.index_video("fake.mp4", FAKE_VIDEO_RECORD, tags_path=tags,
                             out_dir=tmp_path / "segments", log=lambda *a: None)


def test_a_tag_file_of_the_right_size_but_wrong_keys_still_fails(tmp_path, monkeypatch):
    import json

    beats = _fake_beats(monkeypatch)
    tags = tmp_path / "tags.json"
    renamed = _stub_tags(beats)
    renamed["99"] = renamed.pop("2")
    tags.write_text(json.dumps(renamed))

    with pytest.raises(KeyError, match="no tags for beat 2"):
        annotate.index_video("fake.mp4", FAKE_VIDEO_RECORD, tags_path=tags,
                             out_dir=tmp_path / "segments", log=lambda *a: None)


def test_tags_from_a_different_detection_are_refused(tmp_path, monkeypatch):
    """The silent case: same count, shifted boundaries.

    Re-fetching a video at another resolution or changing --min-shot-sec can
    land on the same number of beats with different cuts. Replaying old tags
    then slides every label onto a neighbouring shot -- and the result still
    validates, now calling a HUD-bearing beat clean.
    """
    import json

    from tools.annotate import verify_tags_match_detection

    beats = _fake_beats(monkeypatch)
    tags = tmp_path / "tags.json"
    tags.write_text(json.dumps(_stub_tags(beats)))

    manifest = tmp_path / "beats.json"
    shifted = [dict(b, start_sec=float(b["start_sec"]) + 5.0,
                    end_sec=float(b["end_sec"]) + 5.0) for b in beats]
    manifest.write_text(json.dumps(shifted))

    with pytest.raises(ValueError, match="no longer matches"):
        verify_tags_match_detection(tags, beats, manifest_path=manifest)


def test_matching_detection_passes_verification(tmp_path, monkeypatch):
    import json

    from tools.annotate import verify_tags_match_detection

    beats = _fake_beats(monkeypatch)
    tags = tmp_path / "tags.json"
    tags.write_text(json.dumps(_stub_tags(beats)))
    manifest = tmp_path / "beats.json"
    manifest.write_text(json.dumps([dict(b) for b in beats]))

    verify_tags_match_detection(tags, beats, manifest_path=manifest)


def test_verification_without_a_manifest_still_checks_the_count(tmp_path, monkeypatch):
    import json

    from tools.annotate import verify_tags_match_detection

    beats = _fake_beats(monkeypatch)
    tags = tmp_path / "tags.json"
    tags.write_text(json.dumps(_stub_tags(beats)))

    verify_tags_match_detection(tags, beats, manifest_path=tmp_path / "absent.json")


def test_keyframes_land_under_their_own_video_id(tmp_path):
    from tools.annotate import keyframes_dir_for

    record = {"video_id": "yt_some_trailer"}
    assert keyframes_dir_for(record, root=tmp_path) == tmp_path / "yt_some_trailer"


def test_two_videos_cannot_collide_on_the_same_still(tmp_path):
    from tools.annotate import keyframes_dir_for

    a = keyframes_dir_for({"video_id": "yt_a"}, root=tmp_path)
    b = keyframes_dir_for({"video_id": "yt_b"}, root=tmp_path)
    assert a != b


def test_re_indexing_replaces_the_videos_segments(tmp_path, monkeypatch):
    """A shorter or shifted detection must not leave orphans behind.

    segment_id encodes timecodes, so new boundaries mean new filenames. The
    stale files stay schema-valid and keep being loaded by search and by
    story.py's clean pool, describing shots that no longer exist.
    """
    import json

    beats = _fake_beats(monkeypatch)
    tags = tmp_path / "tags.json"
    tags.write_text(json.dumps(_stub_tags(beats)))
    out = tmp_path / "segments"
    out.mkdir()

    orphan = out / f"seg_{FAKE_VIDEO_RECORD['video_id']}_9999-9999.json"
    orphan.write_text("{}")
    other = out / "seg_yt_another_video_0000-0001.json"
    other.write_text("{}")

    annotate.index_video("fake.mp4", FAKE_VIDEO_RECORD, tags_path=tags,
                         out_dir=out, log=lambda *a: None)

    assert not orphan.exists(), "a stale segment of this video survived"
    assert other.exists(), "another video's segments must not be touched"

def test_missing_scenedetect_warns_instead_of_failing_quietly(tmp_path, capsys,
                                                              monkeypatch):
    """Fixed-window fallback on a real video must say so.

    The slices it returns look like a plausible shot list and are not one, so
    the mistake is invisible in the output and only surfaces much later as cuts
    that land mid-shot.
    """
    video = tmp_path / "fake.mp4"
    video.write_bytes(b"not really a video")
    monkeypatch.setattr(annotate, "HAVE_SCENEDETECT", False)

    beats = annotate.detect_beats(str(video), 12.0)
    err = capsys.readouterr().err
    assert beats, "the fallback must still produce beats"
    assert "scenedetect" in err
    assert "fixed" in err


def test_no_warning_when_there_is_no_video_to_detect(tmp_path, capsys, monkeypatch):
    """The offline/demo path is a legitimate use of fixed windows, not a fault."""
    monkeypatch.setattr(annotate, "HAVE_SCENEDETECT", False)
    annotate.detect_beats(None, 12.0)
    assert "scenedetect" not in capsys.readouterr().err
