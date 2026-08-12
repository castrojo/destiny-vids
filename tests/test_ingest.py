"""Tests for tools/ingest.py video-default inference (offline, no network).

Run: python3 -m pytest tests/test_ingest.py -q
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import ingest  # noqa: E402


def defaults(title, description="", playlist=""):
    return {k: v["value"] for k, v in
            ingest.infer_video_defaults(title, description, playlist).items()}


def test_final_shape_launch_trailer():
    d = defaults("Destiny 2: The Final Shape | Launch Trailer")
    assert d["era"] == "the_final_shape"
    assert d["content_type"] == "trailer"
    assert d["activity"] == "cinematic"


def test_lightfall_gameplay_neomuna_destination():
    d = defaults("Destiny 2: Lightfall | Neomuna Gameplay Trailer")
    assert d["era"] == "lightfall"
    assert d["content_type"] == "gameplay"
    assert d["destination"] == "neptune_neomuna"


def test_beyond_light_europa():
    d = defaults("Destiny 2: Beyond Light | Europa Story Reveal")
    assert d["era"] == "beyond_light"
    assert d["destination"] == "europa"
    assert d["content_type"] == "cinematic"


def test_raid_activity_wins():
    d = defaults("Destiny 2: Salvation's Edge | Raid Race Trailer")
    assert d["activity"] == "raid"


def test_unknown_era_low_confidence():
    info = ingest.infer_video_defaults("Some unrelated video title")
    assert info["era"]["value"] == "unknown"
    assert info["era"]["confidence"] < 0.5


def test_keyword_match_is_whole_word():
    """``io`` must not match the middle of "Action Trailers".

    A bare substring test tagged a compilation of Earth and Moon footage as
    ``destination: io``, which is a wrong claim about what the footage shows.
    """
    info = ingest.infer_video_defaults("Destiny - All Live Action Trailers")
    assert "destination" not in info
    # the real destinations still resolve
    assert ingest.infer_video_defaults(
                "Destiny 2 | Io Gameplay")["destination"]["value"] == "io"


def test_rights_note_override_records_weak_provenance():
    """A fan compilation is not the publisher's own upload, and says so."""
    note = "Fan compilation, not an official upload."
    rec = ingest.build_video_record(
                "yt_test", "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "Destiny - All Live Action Trailers", rights_note=note)
    assert rec["source_rights_note"] == note
    assert ingest.validate_video(rec) == []


def test_parse_video_id_forms():
    for src in ["dQw4w9WgXcQ",
                        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "https://youtu.be/dQw4w9WgXcQ"]:
        url, yid = ingest.parse_video_id(src)
        assert yid == "dQw4w9WgXcQ"
        assert "dQw4w9WgXcQ" in url


def test_build_record_validates():
    rec = ingest.build_video_record(
        "yt_test", "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "Destiny 2: The Final Shape | Launch Trailer",
        playlist="Destiny 2 Trailers")
    assert rec["usage_class"] == "third_party_copyrighted"
    assert rec["era"] == "the_final_shape"
    # every inferred default has a provenance entry
    for f in ("era", "activity", "content_type"):
        assert rec["provenance"][f]["label_source"] == "heuristic"
    assert ingest.validate_video(rec) == []


def test_ingested_real_records_present_and_valid():
    """The real Bungie videos ingested via oEmbed should be on disk & valid."""
    import glob, json, yaml
    root = os.path.join(os.path.dirname(__file__), "..")
    files = glob.glob(os.path.join(root, "videos", "*.json"))
    if not files:  # ingestion is network-dependent; skip if none present
        return
    # vocab/ is the single source of truth for every enum, so the era check is
    # made against it rather than a hand-maintained list that goes stale the
    # moment a video from a new expansion is ingested.
    with open(os.path.join(root, "vocab", "domain.yaml")) as fh:
        eras = set(yaml.safe_load(fh)["era"]["values"]) | {"unknown"}
    for f in files:
        rec = json.load(open(f))
        assert ingest.validate_video(rec) == [], f
        assert rec["era"] in eras, f


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
