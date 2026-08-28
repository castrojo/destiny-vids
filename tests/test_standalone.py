import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tools import standalone


def _drc_manifest():
    return {
        "version": 1,
        "cta_asset": "assets/cta/linux-foundation-training-forest.png",
        "videos": [{
            "slug": "bad",
            "source": {
                "url": "https://www.youtube.com/watch?v=example",
                "youtube_id": "example",
                "video_format_id": "137",
                "audio_format_id": "251-drc",
                "usage_class": "third_party_copyrighted",
                "source_rights_note": "Non-commercial fan creation.",
            },
            "title": "Bad",
            "output": "~/Videos/Bad.mp4",
            "thumbnail_output": "~/Videos/Bad-thumbnail.jpg",
            "thumbnail": {"source_at": 1.0},
            "audio_probes": [{"source_at": 2.0, "duration": 1.0}],
            "overlays": [],
        }],
    }


def test_source_time_maps_through_the_blueberries_excision():
    cuts = [{"start_sec": 46.0, "end_sec": 54.0}]
    assert standalone.source_to_output(45.0, cuts) == 45.0
    assert standalone.source_to_output(97.0, cuts) == 89.0
    with pytest.raises(ValueError, match="inside removed source range"):
        standalone.source_to_output(50.0, cuts)


def test_kept_ranges_remove_exactly_the_authored_span():
    assert standalone.kept_ranges(
        120.0, [{"start_sec": 46.0, "end_sec": 54.0}]
    ) == [(0.0, 46.0), (54.0, 120.0)]


def test_manifest_rejects_drc_audio_format(tmp_path):
    path = tmp_path / "batch.json"
    path.write_text(json.dumps(_drc_manifest()))
    with pytest.raises(ValueError, match="DRC"):
        standalone.load_manifest(path)


def test_the_schema_itself_rejects_drc_audio_format():
    """The committed-record gate validates against the raw schema, not the
    loader, so a `-drc` audio format must fail schema validation on its own."""
    schema = json.loads(standalone.SCHEMA.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(_drc_manifest()))
    assert errors, "schema accepted audio_format_id '251-drc'"
    assert any(
        list(error.path)[:3] == ["videos", 0, "source"] for error in errors
    )

    clean = _drc_manifest()
    clean["videos"][0]["source"]["audio_format_id"] = "251"
    assert not list(Draft202012Validator(schema).iter_errors(clean))


def test_training_cta_is_the_approved_1080p_asset():
    import hashlib
    from PIL import Image

    path = standalone.REPO_ROOT / "assets/cta/linux-foundation-training-forest.png"
    assert Image.open(path).size == (1920, 1080)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        "46d05d65973f64c4811a02f64673db547cb2d403c58caa9fdbddc7b0da5883c5"
    )
