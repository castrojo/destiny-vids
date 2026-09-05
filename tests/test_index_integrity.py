"""Every record committed to the index must satisfy its own schema.

The index is data, and data drifts in ways code does not: a value gets
hand-corrected during a session, the spelling is plausible, nothing re-reads
the file, and the repo carries an invalid record indefinitely. That is not
hypothetical -- one segment shipped with ``label_source: "human"``, which is
not in the enum (``manual | heuristic | model``), and the only symptom was that
the video could no longer be reassembled from its own tags.

These tests read what is actually committed rather than what a tool produces,
so a hand edit is caught by the suite instead of by the next person who tries
to rebuild a cut.
"""
import glob
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]

SEGMENT_PATHS = sorted(glob.glob(str(REPO_ROOT / "segments" / "*.json")))
VIDEO_PATHS = sorted(glob.glob(str(REPO_ROOT / "videos" / "*.json")))
TAG_PATHS = sorted(glob.glob(str(REPO_ROOT / "tags" / "*.json")))
BED_PATHS = sorted(glob.glob(str(REPO_ROOT / "music" / "*.json")))
def _is_standalone_batch(path):
    # Two record types share stories/standalone/: video batches (top-level
    # `videos`) and Hive season manifests (top-level `season`). Each is
    # validated against its own schema below.
    with open(path, encoding="utf-8") as fh:
        return "videos" in json.load(fh)


_STANDALONE_PATHS = sorted(
    glob.glob(str(REPO_ROOT / "stories" / "standalone" / "*.json"))
)
STANDALONE_BATCH_PATHS = [p for p in _STANDALONE_PATHS if _is_standalone_batch(p)]
HIVE_SEASON_PATHS = [p for p in _STANDALONE_PATHS if not _is_standalone_batch(p)]

PROVENANCE = (
    yaml.safe_load((REPO_ROOT / "vocab" / "provenance.yaml").read_text()) or {}
)

LABEL_SOURCES = set(PROVENANCE["label_source"]["values"])
"""Read from vocab/, which is the single source of truth for every enum.

Hardcoding the three values here would create a second copy that drifts from
the first -- the exact failure this file exists to catch.
"""

USAGE_CLASSES = set(PROVENANCE["usage_class"]["values"])


def _validator(name):
    with (REPO_ROOT / "schema" / name).open(encoding="utf-8") as fh:
        return Draft202012Validator(json.load(fh))


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def test_casting_vocabulary_matches_the_identity_schema():
    """GitHub IDs and role bindings are data too, not unvalidated YAML."""
    with (REPO_ROOT / "vocab" / "casting.yaml").open(encoding="utf-8") as fh:
        casting = yaml.safe_load(fh) or {}
    errors = sorted(_validator("casting.schema.json").iter_errors(casting),
                    key=lambda e: list(e.path))
    assert not errors, "\n".join(
        f"{'/'.join(str(p) for p in e.path)}: {e.message}" for e in errors
    )


@pytest.mark.parametrize("path", SEGMENT_PATHS, ids=lambda p: Path(p).stem)
def test_committed_segment_matches_the_schema(path):
    errors = sorted(_validator("segment.schema.json").iter_errors(_load(path)),
                    key=lambda e: list(e.path))
    assert not errors, "\n".join(
        f"{'/'.join(str(p) for p in e.path)}: {e.message}" for e in errors
    )


@pytest.mark.parametrize("path", VIDEO_PATHS, ids=lambda p: Path(p).stem)
def test_committed_video_matches_the_schema(path):
    errors = sorted(_validator("video.schema.json").iter_errors(_load(path)),
                    key=lambda e: list(e.path))
    assert not errors, "\n".join(
        f"{'/'.join(str(p) for p in e.path)}: {e.message}" for e in errors
    )


@pytest.mark.parametrize("path", BED_PATHS, ids=lambda p: Path(p).stem)
def test_committed_bed_matches_the_schema(path):
    # Bed records had no schema until 2026-08-13, so `tools/bed.py measure`
    # accepted any string as --usage-class and nothing ever re-read it. That is
    # how a rights bucket stops meaning anything.
    errors = sorted(_validator("bed.schema.json").iter_errors(_load(path)),
                    key=lambda e: list(e.path))
    assert not errors, "\n".join(
        f"{'/'.join(str(p) for p in e.path)}: {e.message}" for e in errors
    )


@pytest.mark.parametrize("path", BED_PATHS, ids=lambda p: Path(p).stem)
def test_bed_usage_class_is_in_the_vocabulary(path):
    # The schema's enum and vocab/provenance.yaml are two copies of one list.
    # This asserts they agree, the way the segment axes already do.
    record = _load(path)
    assert record["usage_class"] in USAGE_CLASSES, (
        f"{record['usage_class']!r} is not in vocab/provenance.yaml: "
        f"{sorted(USAGE_CLASSES)}"
    )


@pytest.mark.parametrize("path", BED_PATHS, ids=lambda p: Path(p).stem)
def test_an_attributed_bed_carries_its_credit_verbatim(path):
    # CC BY is not CC0. The licence is conditional on a credit, so a record
    # that claims the licence without carrying the credit claims a permission
    # it does not have -- and the credit must also be reproduced where a viewer
    # can see it, which is ATTRIBUTIONS.md.
    record = _load(path)
    if record["usage_class"] != "cc_by_4_0":
        return
    credit = record.get("attribution")
    assert credit, (
        f"{Path(path).stem} is CC BY 4.0 but carries no `attribution` string. "
        "Attribution is the whole condition of the licence."
    )
    attributions = (REPO_ROOT / "ATTRIBUTIONS.md").read_text(encoding="utf-8")
    for line in (ln.strip() for ln in credit.splitlines() if ln.strip()):
        assert line in attributions, (
            f"ATTRIBUTIONS.md is missing a required credit line for "
            f"{Path(path).stem}: {line!r}"
        )


@pytest.mark.parametrize(
    "path", STANDALONE_BATCH_PATHS, ids=lambda path: Path(path).stem
)
def test_committed_standalone_batch_matches_the_schema(path):
    errors = sorted(
        _validator("standalone-batch.schema.json").iter_errors(_load(path)),
        key=lambda error: list(error.path),
    )
    assert not errors, "\n".join(
        f"{'/'.join(str(part) for part in error.path)}: {error.message}"
        for error in errors
    )


@pytest.mark.parametrize(
    "path", HIVE_SEASON_PATHS, ids=lambda path: Path(path).stem
)
def test_committed_hive_season_matches_the_schema(path):
    errors = sorted(
        _validator("hive-season.schema.json").iter_errors(_load(path)),
        key=lambda error: list(error.path),
    )
    assert not errors, "\n".join(
        f"{'/'.join(str(part) for part in error.path)}: {error.message}"
        for error in errors
    )


@pytest.mark.parametrize(
    "path", STANDALONE_BATCH_PATHS, ids=lambda path: Path(path).stem
)
def test_committed_standalone_chat_holds_are_readable(path):
    from tools.readtime import required_hold

    manifest = _load(path)
    short = []
    for video in manifest["videos"]:
        for overlay in video["overlays"]:
            text = overlay.get("text")
            if not text:
                continue
            visible = text.replace("_", "")
            need = required_hold(visible)
            if overlay["dur"] + 1e-9 < need:
                short.append(
                    f"{video['slug']}/{overlay['id']}: "
                    f"{overlay['dur']:.2f}s < {need:.2f}s"
                )
    assert not short, "\n".join(short)


@pytest.mark.parametrize("path", TAG_PATHS, ids=lambda p: Path(p).stem)
def test_tag_file_uses_only_real_label_sources(path):
    # A tag file is the input to assembly, so an out-of-enum value here does
    # not surface until someone re-runs pass 2 -- often months later, and
    # looking like a tool regression rather than a typo.
    bad = {}
    for beat, tags in _load(path).items():
        for field, entry in (tags.get("provenance") or {}).items():
            source = entry.get("label_source")
            if source not in LABEL_SOURCES:
                bad[f"beat {beat} / {field}"] = source
    assert not bad, f"label_source must be one of {sorted(LABEL_SOURCES)}: {bad}"


@pytest.mark.parametrize("path", TAG_PATHS, ids=lambda p: Path(p).stem)
def test_a_beat_with_no_overlays_stays_out_of_every_cut(path):
    # `clean` is the primary gate and derives false when overlays is untagged.
    # A long archive is reviewed incrementally, so a beat with no `overlays` is
    # legitimate -- it means "nobody has looked at this frame yet". What is
    # never legitimate is such a beat reaching a cut: the gate only works if the
    # missing tag actually derives clean = false. Assert the consequence, not
    # the absence, or an inherited "clean" puts a HUD in a finished cut.
    tags = _load(path)
    video_id = Path(path).stem
    segments = sorted(
        (json.loads(Path(p).read_text()) for p in SEGMENT_PATHS),
        key=lambda s: s["start_sec"],
    )
    segments = [s for s in segments if s["video_id"] == video_id]
    if not segments:
        pytest.skip(f"{video_id} has no assembled segments")

    beats = [tags[k] for k in sorted(tags, key=int)]
    assert len(beats) == len(segments), (
        f"{video_id}: {len(beats)} tagged beats but {len(segments)} segments -- "
        "the two passes disagree, so no per-beat claim below can be trusted"
    )

    leaked = [
        seg["segment_id"]
        for beat, seg in zip(beats, segments)
        if "overlays" not in beat and seg.get("clean")
    ]
    assert not leaked, (
        f"segments derived clean from an unreviewed beat: {leaked}. "
        "An untagged beat must derive clean = false and leave every cut."
    )


@pytest.mark.parametrize("path", TAG_PATHS, ids=lambda p: Path(p).stem)
def test_a_tag_file_never_carries_a_derived_field(path):
    from tools.annotate import TAGGER_FIELDS

    allowed = set(TAGGER_FIELDS) | {"provenance"}
    offenders = {}
    for beat, tags in _load(path).items():
        # Underscore-prefixed keys are worksheet scaffolding (tools/worksheet.py
        # records the keyframe and timecodes each judgement was made from). They
        # are metadata about the tagging task, not tags about the shot, and
        # JsonTagger strips them at replay so they never reach a segment.
        extra = sorted(k for k in set(tags) - allowed if not k.startswith("_"))
        if extra:
            offenders[beat] = extra
    assert not offenders, (
        f"tag files may only carry tagger fields; derived fields are computed "
        f"by tools/derive.py at assembly: {offenders}"
    )


def test_every_segment_points_at_a_video_that_exists():
    known = {_load(p)["video_id"] for p in VIDEO_PATHS}
    orphans = sorted({
        _load(p)["video_id"] for p in SEGMENT_PATHS
        if _load(p)["video_id"] not in known
    })
    assert not orphans, f"segments reference missing video records: {orphans}"
