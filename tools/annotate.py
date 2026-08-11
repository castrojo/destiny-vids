"""Annotator pipeline scaffold for the destiny-vids index.

Stages (docs/pipeline.md):
  1. Segmentation — ``detect_beats`` uses PySceneDetect when installed, else a
     deterministic fixed-window splitter. Shot boundaries are computed BEFORE
     any model runs; the model never decides where a beat starts.
  2. Tagging — a pluggable ``Tagger`` interface. ``StubTagger`` returns
     deterministic placeholder tags so the whole pipeline runs offline.
  3. Assembly — ``assemble_segment`` merges inherited video-level defaults,
     overlays observed tagger fields, then applies the exactly-defined derived
     fields (tools/derive.py), stamping provenance on everything.
  4. Validation — ``validate_segment`` checks the record against
     schema/segment.schema.json (JSON Schema Draft 2020-12).

Pure stdlib + jsonschema + pyyaml. scenedetect/opencv are OPTIONAL: the module
imports and all tests pass without them.
"""

from __future__ import annotations

import abc
import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import derive  # noqa: E402

SEGMENT_SCHEMA_PATH = REPO_ROOT / "schema" / "segment.schema.json"

# --- Optional shot-boundary-detection backend -------------------------------
# PySceneDetect (and its opencv dependency) may not be installed; the fixed-
# window fallback keeps the pipeline runnable offline.
try:  # modern scenedetect API (>=0.6)
    from scenedetect import ContentDetector, SceneManager, open_video

    HAVE_SCENEDETECT = True
except ImportError:  # older API layout or not installed at all
    try:
        from scenedetect import SceneManager  # type: ignore
        from scenedetect.detectors import ContentDetector  # type: ignore
        from scenedetect.video_manager import VideoManager  # type: ignore

        open_video = None
        HAVE_SCENEDETECT = True
    except ImportError:
        HAVE_SCENEDETECT = False

# Video-scoped defaults every segment inherits (README / pipeline.md §2).
INHERITABLE_FIELDS = ("era", "activity", "content_type", "destination", "subclass_version")

# Fields a Tagger must populate (source = observed).
TAGGER_FIELDS = (
    "class",
    "element",
    "faction",
    "shot_scale",
    "composition",
    "camera_movement",
    "pacing",
    "content_type",
    "lighting",
    "identity_visibility",
    "character_identifiability",
    "substitutability",
    "overlays",
    "subject_salience",
    "action",
    "mood",
    "register",
    "character",
    "caption",
)

DEFAULT_WINDOW_SEC = 3.0  # gameplay fixed-window sampling (~2-4s, pipeline.md §1)


def sec_to_tc(seconds):
    """Seconds -> 'm:ss' or 'h:mm:ss' (schema start_tc/end_tc pattern)."""
    total = max(0, int(round(float(seconds))))
    m, s = divmod(total, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _coerce_duration_sec(fps_or_duration):
    """Accept a duration in seconds, or a (fps, total_frames) pair."""
    if isinstance(fps_or_duration, (tuple, list)) and len(fps_or_duration) == 2:
        fps, frames = fps_or_duration
        if not fps:
            raise ValueError("fps must be non-zero")
        return float(frames) / float(fps)
    return float(fps_or_duration)


def _fixed_window_beats(duration_sec, window_sec=DEFAULT_WINDOW_SEC):
    beats = []
    start = 0.0
    while start < duration_sec:
        end = min(start + window_sec, duration_sec)
        beats.append(
            {
                "start_sec": start,
                "end_sec": end,
                "start_tc": sec_to_tc(start),
                "end_tc": sec_to_tc(end),
            }
        )
        start = end
    return beats


def _scenedetect_beats(video_path):
    video = open_video(str(video_path))
    manager = SceneManager()
    manager.add_detector(ContentDetector())
    manager.detect_scenes(video)
    scenes = manager.get_scene_list()
    if not scenes:  # no cuts found: the whole video is one beat
        scenes = [(video.base_timecode, video.duration)]
    return [
        {
            "start_sec": start.get_seconds(),
            "end_sec": end.get_seconds(),
            "start_tc": sec_to_tc(start.get_seconds()),
            "end_tc": sec_to_tc(end.get_seconds()),
        }
        for start, end in scenes
    ]


def detect_beats(video_path, fps_or_duration, window_sec=DEFAULT_WINDOW_SEC):
    """Shot-boundary detection -> list of {start_sec, end_sec, start_tc, end_tc}.

    Uses PySceneDetect's content detector when scenedetect is installed AND
    ``video_path`` points at a real file; otherwise falls back to deterministic
    fixed-window sampling over the duration implied by ``fps_or_duration``
    (seconds, or a ``(fps, total_frames)`` pair).
    """
    if HAVE_SCENEDETECT and open_video is not None and video_path and Path(video_path).exists():
        return _scenedetect_beats(video_path)
    return _fixed_window_beats(_coerce_duration_sec(fps_or_duration), window_sec)


# --- Tagging interface -------------------------------------------------------


class Tagger(abc.ABC):
    """Pluggable per-beat tagging interface (the model seam).

    Implementations return a partial segment dict: the observed tag fields in
    TAGGER_FIELDS plus a ``provenance`` map with a per-field
    {source, label_source, confidence} entry. They must NOT set derived fields
    (clean, footage_tier, traversal_hero, casting) — assembly computes those via
    tools/derive.py.

    ``overlays`` is a required tagger field, not an optional one: `clean` is the
    index's primary gate and derives False when overlays are untagged, so a
    tagger that skips it silently marks its whole output unusable.
    """

    @abc.abstractmethod
    def tag_beat(self, video_id, beat, keyframe_paths):
        """Return a partial segment dict for one beat."""


class StubTagger(Tagger):
    """Deterministic offline stand-in for the flash-tier vision model.

    Output is a pure function of (video_id, beat): even-indexed beats are
    wide traversal shots (so the demo exercises traversal_hero), odd beats are
    static idle shots. All values are schema-valid placeholders.
    """

    _SCALE_CYCLE = ("LS", "MS", "CU", "ELS")

    def tag_beat(self, video_id, beat, keyframe_paths=()):
        idx = int(round(float(beat["start_sec"])))
        traversal = idx % 2 == 0
        fields = {
            "class": "unknown",
            "element": "unknown",
            "faction": [],
            "shot_scale": self._SCALE_CYCLE[idx % len(self._SCALE_CYCLE)],
            "composition": ["single"],
            "camera_movement": ["track"] if traversal else ["static"],
            "pacing": "medium",
            "content_type": "cinematic",
            "lighting": "UNKNOWN",
            "identity_visibility": "back_only",
            "character_identifiability": "unidentifiable",
            "substitutability": 4,
            "overlays": [],
            "subject_salience": "guardian_hero",
            "action": ["traversal"] if traversal else ["idle"],
            "mood": ["serene"],
            "register": 1,
            "character": [],
            "caption": (
                f"[stub] placeholder caption for {video_id} "
                f"{beat['start_tc']}-{beat['end_tc']}"
            ),
        }
        provenance = {
            name: {"source": "observed", "label_source": "model", "confidence": 0.5}
            for name in fields
        }
        out = dict(fields)
        out["provenance"] = provenance
        return out


class JsonTagger(Tagger):
    """Replays tags produced out-of-band (a vision model, or a human) from JSON.

    The file maps a beat index (as a string) to the same partial segment dict a
    live Tagger would return. Beat index is positional: it is the order
    ``detect_beats`` returned, so a tag file is only valid against the shot list
    the same detector settings produce.
    """

    def __init__(self, tag_map):
        self._tags = tag_map
        self._i = -1

    @classmethod
    def from_file(cls, path):
        with Path(path).open(encoding="utf-8") as fh:
            return cls(json.load(fh))

    def tag_beat(self, video_id, beat, keyframe_paths=()):
        self._i += 1
        key = str(beat.get("beat_index", self._i))
        if key not in self._tags:
            raise KeyError(f"no tags for beat {key} of {video_id}")
        return dict(self._tags[key])


# --- Assembly ----------------------------------------------------------------


def assemble_segment(video_record, beat, tagger_output, leads=None):
    """Merge inherited defaults + observed tags + derived fields into a segment.

    - era/activity/content_type/destination/subclass_version are copied from
      the video record with provenance source='inherited' (label_source and
      confidence carried over from the video's own provenance when present).
    - Tagger fields overlay as source='observed' with the tagger's provenance.
    - clean, footage_tier, traversal_hero and casting are computed by
      tools/derive.py and stamped label_source='heuristic'.
    """
    video_id = video_record["video_id"]
    segment = {
        "segment_id": beat.get(
            "segment_id",
            f"seg_{video_id}_{int(beat['start_sec']):04d}-{int(beat['end_sec']):04d}",
        ),
        "video_id": video_id,
        "start_sec": beat["start_sec"],
        "end_sec": beat["end_sec"],
        "start_tc": beat["start_tc"],
        "end_tc": beat["end_tc"],
    }
    provenance = {}

    video_prov = video_record.get("provenance") or {}
    for field in INHERITABLE_FIELDS:
        if field in video_record:
            segment[field] = video_record[field]
            vp = video_prov.get(field) or {}
            provenance[field] = {
                "source": "inherited",
                "label_source": vp.get("label_source", "model"),
                "confidence": vp.get("confidence", 0.5),
            }

    tags = dict(tagger_output)
    tag_prov = tags.pop("provenance", None) or {}
    for field, value in tags.items():
        if field not in TAGGER_FIELDS:
            raise ValueError(f"tagger returned non-taggable field: {field!r}")
        segment[field] = value
        tp = tag_prov.get(field) or {}
        provenance[field] = {
            "source": "observed",
            "label_source": tp.get("label_source", "model"),
            "confidence": tp.get("confidence", 0.5),
        }

    for field, value in derive.derive_all(segment, leads).items():
        segment[field] = value
        provenance[field] = {"source": "observed", "label_source": "heuristic",
                             "confidence": 1.0}

    segment["provenance"] = provenance
    return segment


# --- Validation --------------------------------------------------------------


def _load_segment_schema():
    with SEGMENT_SCHEMA_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def validate_segment(segment):
    """Validate a segment against schema/segment.schema.json (Draft 2020-12).

    Returns the segment unchanged on success; raises ValueError listing every
    validation error on failure.
    """
    validator = Draft202012Validator(_load_segment_schema())
    errors = sorted(validator.iter_errors(segment), key=lambda e: list(e.absolute_path))
    if errors:
        details = "; ".join(
            f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errors
        )
        raise ValueError(f"segment {segment.get('segment_id')!r} failed validation: {details}")
    return segment


# --- CLI demo ----------------------------------------------------------------

_DEMO_VIDEO_RECORD = {
    "video_id": "yt_demo_fake_video",
    "era": "the_final_shape",
    "activity": "cinematic",
    "content_type": "trailer",
    "destination": "the_pale_heart",
    "subclass_version": "prismatic",
    "provenance": {
        "era": {"source": "observed", "label_source": "model", "confidence": 0.99},
        "activity": {"source": "observed", "label_source": "model", "confidence": 0.9},
        "content_type": {"source": "observed", "label_source": "model", "confidence": 0.95},
        "destination": {"source": "observed", "label_source": "model", "confidence": 0.7},
        "subclass_version": {"source": "observed", "label_source": "heuristic", "confidence": 0.5},
    },
}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run the stub annotator pipeline end-to-end on a fake video."
    )
    parser.add_argument("--duration", type=float, default=12.0, help="fake video duration (sec)")
    parser.add_argument("--window", type=float, default=DEFAULT_WINDOW_SEC, help="fallback window (sec)")
    parser.add_argument("--video", default=None, help="real video path (uses scenedetect if installed)")
    args = parser.parse_args(argv)

    backend = "scenedetect" if HAVE_SCENEDETECT else "fixed-window fallback (scenedetect not installed)"
    print(f"shot detection backend: {backend}")

    beats = detect_beats(args.video, args.duration, window_sec=args.window)
    tagger = StubTagger()
    leads = derive.load_leads()
    for beat in beats:
        segment = assemble_segment(_DEMO_VIDEO_RECORD, beat, tagger.tag_beat(_DEMO_VIDEO_RECORD["video_id"], beat, []), leads)
        validate_segment(segment)
        print(json.dumps(segment, indent=2))
    print(f"OK: {len(beats)} segment(s) validated against schema/segment.schema.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
