"""Tests for the tagger worksheet (tools/worksheet.py).

Everything here runs offline: manifests are written into tmp_path, keyframe
stills are touched empty files, and no video, scenedetect or model is needed.
"""

import json

import pytest

from tools import annotate, worksheet

FAKE_VIDEO_RECORD = {
    "video_id": "yt_test_fake",
    "era": "beyond_light",
    "activity": "cinematic",
    "content_type": "cinematic",
    "destination": "europa",
    "subclass_version": "stasis",
}


def _manifest(keyframes_dir, count=3):
    """A beats.json of the shape index_video writes, plus empty stills."""
    keyframes_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for i in range(count):
        (keyframes_dir / f"{i:03d}.jpg").write_bytes(b"")
        manifest.append({
            "start_sec": float(i),
            "end_sec": float(i + 1),
            "start_tc": annotate.sec_to_tc(i),
            "end_tc": annotate.sec_to_tc(i + 1),
            "beat_index": i,
            "keyframe": f"{i:03d}.jpg",
        })
    (keyframes_dir / "beats.json").write_text(json.dumps(manifest))
    return manifest


def _generate(tmp_path, monkeypatch, count=3):
    """A worksheet for a fake video: record in a fake videos/, stills in a
    fake keyframes/ — both under tmp_path so the real index is untouched."""
    monkeypatch.setattr(worksheet, "REPO_ROOT", tmp_path)
    (tmp_path / "videos").mkdir(exist_ok=True)
    (tmp_path / "videos" / f"{FAKE_VIDEO_RECORD['video_id']}.json").write_text(
        json.dumps(FAKE_VIDEO_RECORD))
    keyframes_dir = tmp_path / "keyframes" / FAKE_VIDEO_RECORD["video_id"]
    manifest = _manifest(keyframes_dir, count)
    out = tmp_path / "tags" / f"{FAKE_VIDEO_RECORD['video_id']}.json"
    return manifest, keyframes_dir, out


def _fill(skeleton, manifest):
    """What a tagger produces: every null replaced by a real (stub) value."""
    tagger = annotate.StubTagger()
    filled = {}
    for i, beat in enumerate(manifest):
        entry = dict(skeleton[str(i)])
        stub = tagger.tag_beat("yt_test_fake", beat, [])
        entry.update({k: v for k, v in stub.items() if k != "provenance"})
        entry["provenance"] = stub["provenance"]
        filled[str(i)] = entry
    return filled


# --- generate ---------------------------------------------------------------


def test_skeleton_covers_every_beat(tmp_path, monkeypatch):
    manifest, keyframes_dir, out = _generate(tmp_path, monkeypatch, count=4)
    worksheet.generate(FAKE_VIDEO_RECORD["video_id"], keyframes_dir=keyframes_dir, out=out)
    tags = json.loads(out.read_text())
    assert list(tags) == ["0", "1", "2", "3"]  # every beat, in beat order
    assert len(tags) == len(manifest)


def test_skeleton_pairs_each_beat_with_its_keyframe_and_timecodes(tmp_path, monkeypatch):
    manifest, keyframes_dir, out = _generate(tmp_path, monkeypatch)
    worksheet.generate(FAKE_VIDEO_RECORD["video_id"], keyframes_dir=keyframes_dir, out=out)
    tags = json.loads(out.read_text())
    for i, beat in enumerate(manifest):
        ws = tags[str(i)][worksheet.WORKSHEET_KEY]
        assert ws["keyframe"].endswith(f"yt_test_fake/{i:03d}.jpg")
        assert (ws["start_sec"], ws["end_sec"]) == (beat["start_sec"], beat["end_sec"])
        assert (ws["start_tc"], ws["end_tc"]) == (beat["start_tc"], beat["end_tc"])


def test_overlays_is_never_prefilled(tmp_path, monkeypatch):
    """The single guarantee this tool exists around: a skeleton must not make
    an untagged beat look clean. null is 'nobody has looked'; [] is the
    positive judgement the clean gate requires, and only a looked-at frame
    earns it."""
    _, keyframes_dir, out = _generate(tmp_path, monkeypatch)
    worksheet.generate(FAKE_VIDEO_RECORD["video_id"], keyframes_dir=keyframes_dir, out=out)
    tags = json.loads(out.read_text())
    assert all(entry["overlays"] is None for entry in tags.values())


def test_character_is_never_prefilled(tmp_path, monkeypatch):
    """A character tag credits a real person for a shot; the skeleton may not
    even suggest one."""
    _, keyframes_dir, out = _generate(tmp_path, monkeypatch)
    worksheet.generate(FAKE_VIDEO_RECORD["video_id"], keyframes_dir=keyframes_dir, out=out)
    tags = json.loads(out.read_text())
    assert all(entry["character"] is None for entry in tags.values())


def test_no_derived_field_appears(tmp_path, monkeypatch):
    """clean/footage_tier/traversal_hero/casting are computed at assembly;
    their presence in a tag file is an error by design, so the skeleton must
    not even carry them as placeholders."""
    from tools import derive

    _, keyframes_dir, out = _generate(tmp_path, monkeypatch)
    worksheet.generate(FAKE_VIDEO_RECORD["video_id"], keyframes_dir=keyframes_dir, out=out)
    tags = json.loads(out.read_text())
    derived = set(derive.derive_all({}, derive.load_leads()))
    assert derived == {"clean", "footage_tier", "traversal_hero", "casting"}
    for entry in tags.values():
        assert not (derived & set(entry))
        assert not (derived & set(entry["provenance"]))


def test_every_tagger_field_starts_null_with_no_prefills(tmp_path, monkeypatch):
    """Nothing is pre-filled — not even content_type, which looks video-scoped
    but is judged per shot in the committed corpus and feeds footage_tier."""
    _, keyframes_dir, out = _generate(tmp_path, monkeypatch)
    worksheet.generate(FAKE_VIDEO_RECORD["video_id"], keyframes_dir=keyframes_dir, out=out)
    tags = json.loads(out.read_text())
    for entry in tags.values():
        assert all(entry[field] is None for field in annotate.TAGGER_FIELDS)
        assert entry["provenance"] == {}
        assert set(entry) == set(annotate.TAGGER_FIELDS) | {"provenance", worksheet.WORKSHEET_KEY}


def test_generate_refuses_to_overwrite_a_tag_file(tmp_path, monkeypatch):
    _, keyframes_dir, out = _generate(tmp_path, monkeypatch)
    worksheet.generate(FAKE_VIDEO_RECORD["video_id"], keyframes_dir=keyframes_dir, out=out)
    with pytest.raises(FileExistsError, match="already exists"):
        worksheet.generate(FAKE_VIDEO_RECORD["video_id"], keyframes_dir=keyframes_dir, out=out)
    # ... unless the caller says the judgements in it are disposable
    worksheet.generate(FAKE_VIDEO_RECORD["video_id"], keyframes_dir=keyframes_dir,
                       out=out, force=True)


def test_generate_needs_the_pass_one_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(worksheet, "REPO_ROOT", tmp_path)
    (tmp_path / "videos").mkdir()
    (tmp_path / "videos" / "yt_test_fake.json").write_text(json.dumps(FAKE_VIDEO_RECORD))
    with pytest.raises(FileNotFoundError, match="pass 1"):
        worksheet.generate("yt_test_fake", keyframes_dir=tmp_path / "absent")


def test_generate_needs_a_video_record(tmp_path, monkeypatch):
    """A worksheet for a video with no record can never be assembled."""
    monkeypatch.setattr(worksheet, "REPO_ROOT", tmp_path)
    with pytest.raises(FileNotFoundError, match="no video record"):
        worksheet.generate("yt_nobody_ingested_this", keyframes_dir=tmp_path)


def test_generate_warns_when_a_still_is_missing(tmp_path, monkeypatch, capsys):
    _, keyframes_dir, out = _generate(tmp_path, monkeypatch)
    (keyframes_dir / "001.jpg").unlink()
    worksheet.generate(FAKE_VIDEO_RECORD["video_id"], keyframes_dir=keyframes_dir, out=out)
    assert 'first: beat 1' in capsys.readouterr().out


# --- check ------------------------------------------------------------------


def test_check_reports_every_skeleton_beat_unfilled(tmp_path, monkeypatch):
    _, keyframes_dir, out = _generate(tmp_path, monkeypatch)
    worksheet.generate(FAKE_VIDEO_RECORD["video_id"], keyframes_dir=keyframes_dir, out=out)
    report = worksheet.audit(out, json.loads((keyframes_dir / "beats.json").read_text()))
    assert report["complete"] is False
    assert report["filled"] == 0
    assert sorted(report["unfilled"], key=int) == ["0", "1", "2"]
    # every field on every beat — overlays among them, first in the report
    for fields in report["unfilled"].values():
        assert "overlays" in fields and "character" in fields


def test_check_passes_a_fully_filled_file(tmp_path, monkeypatch):
    manifest, keyframes_dir, out = _generate(tmp_path, monkeypatch)
    worksheet.generate(FAKE_VIDEO_RECORD["video_id"], keyframes_dir=keyframes_dir, out=out)
    out.write_text(json.dumps(_fill(json.loads(out.read_text()), manifest)))
    assert worksheet.check(out, keyframes_dir=keyframes_dir, log=lambda *a: None) is True


def test_check_names_the_exact_fields_still_missing(tmp_path, monkeypatch):
    manifest, keyframes_dir, out = _generate(tmp_path, monkeypatch)
    worksheet.generate(FAKE_VIDEO_RECORD["video_id"], keyframes_dir=keyframes_dir, out=out)
    tags = _fill(json.loads(out.read_text()), manifest)
    tags["1"]["overlays"] = None   # unfilled: nobody has looked
    del tags["2"]["caption"]       # absent: equivalent to unfilled
    out.write_text(json.dumps(tags))

    report = worksheet.audit(out, json.loads((keyframes_dir / "beats.json").read_text()))
    assert report["complete"] is False
    assert report["unfilled"] == {"1": ["overlays"], "2": ["caption"]}
    assert report["filled"] == 1


def test_an_explicit_empty_list_is_a_positive_judgement(tmp_path, monkeypatch):
    """overlays: [] and character: [] are filled — they assert 'clean' and
    'nobody identifiable'. Only null/absent means unlooked."""
    manifest, keyframes_dir, out = _generate(tmp_path, monkeypatch)
    worksheet.generate(FAKE_VIDEO_RECORD["video_id"], keyframes_dir=keyframes_dir, out=out)
    tags = _fill(json.loads(out.read_text()), manifest)
    assert all(e["overlays"] == [] and e["character"] == [] for e in tags.values())
    out.write_text(json.dumps(tags))
    assert worksheet.check(out, keyframes_dir=keyframes_dir, log=lambda *a: None) is True


def test_check_flags_fields_assembly_would_refuse(tmp_path, monkeypatch):
    manifest, keyframes_dir, out = _generate(tmp_path, monkeypatch)
    worksheet.generate(FAKE_VIDEO_RECORD["video_id"], keyframes_dir=keyframes_dir, out=out)
    tags = _fill(json.loads(out.read_text()), manifest)
    tags["0"]["overlyas"] = []     # the typo a quiet check exists to catch
    out.write_text(json.dumps(tags))
    report = worksheet.audit(out, json.loads((keyframes_dir / "beats.json").read_text()))
    assert report["complete"] is False
    assert report["unknown_fields"] == {"0": ["overlyas"]}


def test_check_cross_references_the_manifest(tmp_path, monkeypatch):
    """Beat index is positional: a file short a beat, or carrying one the
    detection never produced, disagrees with pass 1 — say so."""
    manifest, keyframes_dir, out = _generate(tmp_path, monkeypatch)
    worksheet.generate(FAKE_VIDEO_RECORD["video_id"], keyframes_dir=keyframes_dir, out=out)
    tags = _fill(json.loads(out.read_text()), manifest)
    del tags["2"]
    tags["7"] = dict(tags["1"])
    out.write_text(json.dumps(tags))
    report = worksheet.audit(out, json.loads((keyframes_dir / "beats.json").read_text()))
    assert report["missing_entries"] == ["2"]
    assert report["extra_entries"] == ["7"]
    assert report["complete"] is False


def test_check_tolerates_a_missing_manifest(tmp_path, monkeypatch):
    """Videos indexed before the manifest existed have no beats.json; their
    tag files are still checkable field by field."""
    manifest, keyframes_dir, out = _generate(tmp_path, monkeypatch)
    worksheet.generate(FAKE_VIDEO_RECORD["video_id"], keyframes_dir=keyframes_dir, out=out)
    out.write_text(json.dumps(_fill(json.loads(out.read_text()), manifest)))
    assert worksheet.check(out, keyframes_dir=None, log=lambda *a: None) is True


# --- the skeleton and the pipeline agree ------------------------------------


def test_a_filled_worksheet_replays_through_assembly(tmp_path, monkeypatch):
    """The scaffolding keys the tagger worked from must not reach a segment:
    assemble_segment raises on non-taggable fields, so this fails loudly if
    JsonTagger ever stops stripping them."""
    manifest, keyframes_dir, out = _generate(tmp_path, monkeypatch)
    worksheet.generate(FAKE_VIDEO_RECORD["video_id"], keyframes_dir=keyframes_dir, out=out)
    out.write_text(json.dumps(_fill(json.loads(out.read_text()), manifest)))

    tagger = annotate.JsonTagger.from_file(out)
    leads = annotate.derive.load_leads()
    for i, beat in enumerate(manifest):
        segment = annotate.assemble_segment(
            FAKE_VIDEO_RECORD, dict(beat, beat_index=i),
            tagger.tag_beat("yt_test_fake", beat, []), leads)
        annotate.validate_segment(segment)
        assert worksheet.WORKSHEET_KEY not in segment
        assert segment["clean"] is True  # stub tags overlays: [], positively


# --- CLI --------------------------------------------------------------------


def test_cli_generate_then_check(tmp_path, monkeypatch, capsys):
    _, keyframes_dir, out = _generate(tmp_path, monkeypatch)
    assert worksheet.main(["generate", "yt_test_fake",
                           "--keyframes-dir", str(keyframes_dir)]) == 0
    assert out.exists()
    assert worksheet.main(["check", str(out), "--keyframes-dir", str(keyframes_dir)]) == 1
    assert "0/3 beats filled" in capsys.readouterr().out


def test_cli_check_convention_finds_the_manifest(tmp_path, monkeypatch):
    """check tags/<id>.json with no flags audits against keyframes/<id>/."""
    manifest, keyframes_dir, out = _generate(tmp_path, monkeypatch)
    worksheet.generate(FAKE_VIDEO_RECORD["video_id"], keyframes_dir=keyframes_dir, out=out)
    out.write_text(json.dumps(_fill(json.loads(out.read_text()), manifest)))
    assert worksheet.main(["check", str(out)]) == 0


def test_cli_generate_refuses_to_clobber(tmp_path, monkeypatch, capsys):
    _, keyframes_dir, out = _generate(tmp_path, monkeypatch)
    worksheet.main(["generate", "yt_test_fake", "--keyframes-dir", str(keyframes_dir)])
    assert worksheet.main(["generate", "yt_test_fake",
                           "--keyframes-dir", str(keyframes_dir)]) == 1
    assert "already exists" in capsys.readouterr().err
