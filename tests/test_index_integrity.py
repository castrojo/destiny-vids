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

LABEL_SOURCES = set(
    (
        yaml.safe_load((REPO_ROOT / "vocab" / "provenance.yaml").read_text())
        or {}
    )["label_source"]["values"]
)
"""Read from vocab/, which is the single source of truth for every enum.

Hardcoding the three values here would create a second copy that drifts from
the first -- the exact failure this file exists to catch.
"""


def _validator(name):
    with (REPO_ROOT / "schema" / name).open(encoding="utf-8") as fh:
        return Draft202012Validator(json.load(fh))


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


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
