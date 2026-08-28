"""Build standalone videos from one committed batch manifest.

A manifest in stories/standalone/<batch>.json records, per video: the pinned
yt-dlp source formats, authored excisions in source time, overlays, an
optional full-frame CTA takeover, a thumbnail pick, and audio probes. This
module owns the contract (schema/standalone-batch.schema.json) and the
source-time -> output-time mapping every later stage relies on.
"""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = REPO_ROOT / "schema" / "standalone-batch.schema.json"


def load_manifest(path):
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    for video in data.get("videos", []):
        source = video.get("source") or {}
        audio_id = source.get("audio_format_id", "")
        if audio_id.endswith("-drc"):
            raise ValueError(f"{video['slug']}: DRC audio format is forbidden")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(data),
        key=lambda error: list(error.path),
    )
    if errors:
        raise ValueError("\n".join(
            f"{'/'.join(map(str, error.path))}: {error.message}"
            for error in errors
        ))
    return data


def entry_by_slug(manifest, slug):
    matches = [video for video in manifest["videos"] if video["slug"] == slug]
    if len(matches) != 1:
        raise KeyError(f"expected one video named {slug!r}, found {len(matches)}")
    return matches[0]


def _sorted_cuts(cuts):
    ordered = sorted(cuts or [], key=lambda cut: cut["start_sec"])
    previous_end = 0.0
    for cut in ordered:
        start, end = cut["start_sec"], cut["end_sec"]
        if start < previous_end or end <= start:
            raise ValueError(f"invalid or overlapping cut {start}-{end}")
        previous_end = end
    return ordered


def source_to_output(source_sec, cuts):
    removed = 0.0
    for cut in _sorted_cuts(cuts):
        start, end = cut["start_sec"], cut["end_sec"]
        if start <= source_sec < end:
            raise ValueError(
                f"{source_sec:.3f} is inside removed source range {start}-{end}"
            )
        if end <= source_sec:
            removed += end - start
    return source_sec - removed


def kept_ranges(duration_sec, cuts):
    cursor = 0.0
    kept = []
    for cut in _sorted_cuts(cuts):
        if cursor < cut["start_sec"]:
            kept.append((cursor, cut["start_sec"]))
        cursor = cut["end_sec"]
    if cursor < duration_sec:
        kept.append((cursor, duration_sec))
    return kept
