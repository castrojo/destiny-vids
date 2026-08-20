"""Annotator pipeline scaffold for the destiny-vids index.

Stages:
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
import subprocess
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
        open_video = None
        HAVE_SCENEDETECT = True
    except ImportError:
        HAVE_SCENEDETECT = False

# Video-scoped defaults every segment inherits (README).
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

DEFAULT_WINDOW_SEC = 3.0  # gameplay fixed-window sampling (~2-4s)

# Shots shorter than this are merged into their neighbour by the detector. See
# the Destiny false-cut hazard: a teleport flash reads as a boundary.
DEFAULT_MIN_SHOT_SEC = 0.5


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


def _scenedetect_beats(video_path, min_shot_sec=DEFAULT_MIN_SHOT_SEC):
    video = open_video(str(video_path))
    manager = SceneManager()
    # Destiny is full of super activations, explosions and muzzle flash, all of
    # which read to a frame-difference detector as a cut.
    # A minimum shot length merges those sub-threshold "shots" back into their
    # neighbours instead of littering the index with 3-frame beats.
    min_len = max(1, int(round(min_shot_sec * (video.frame_rate or 30.0))))
    manager.add_detector(ContentDetector(min_scene_len=min_len))
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


def detect_beats(video_path, fps_or_duration, window_sec=DEFAULT_WINDOW_SEC,
                 min_shot_sec=DEFAULT_MIN_SHOT_SEC):
    """Shot-boundary detection -> list of {start_sec, end_sec, start_tc, end_tc}.

    Uses PySceneDetect's content detector when scenedetect is installed AND
    ``video_path`` points at a real file; otherwise falls back to deterministic
    fixed-window sampling over the duration implied by ``fps_or_duration``
    (seconds, or a ``(fps, total_frames)`` pair).
    """
    if HAVE_SCENEDETECT and open_video is not None and video_path and Path(video_path).exists():
        return _scenedetect_beats(video_path, min_shot_sec)
    if video_path and Path(video_path).exists() and not HAVE_SCENEDETECT:
        # Falling back on a REAL video is worth saying out loud. The fixed-window
        # pass returns uniform slices that look like a plausible shot list and are
        # not one, so the failure is invisible in the output and only shows up
        # much later as cuts that land mid-shot.
        print(
            f"WARNING: scenedetect is not installed, so {Path(video_path).name} "
            f"is being sliced into fixed {window_sec:g}s windows instead of real "
            f"shots.\n         Install it before indexing: "
            f"pip install scenedetect opencv-python-headless",
            file=sys.stderr,
        )
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


def verify_tags_match_detection(tags_path, beats, manifest_path=None):
    """Refuse tags that were written against a different shot list.

    Beat index is positional, so a tag file and a detection pass agree only if
    they describe the same shots. Nothing in the data says so, which makes the
    dangerous case silent: re-fetch a video at a different resolution, or bump
    ``--min-shot-sec``, and every tag slides onto a neighbouring shot. The
    result still validates, still assembles, and now says a HUD-bearing beat is
    clean and names a real person in a shot they are not in.

    Two checks, cheapest first: the number of beats, and -- when the manifest
    from pass 1 is still on disk -- the actual boundaries. The manifest is the
    stronger signal, because a re-detection can easily land on the same count
    with different cuts.
    """
    with Path(tags_path).open(encoding="utf-8") as fh:
        tags = json.load(fh)

    if len(tags) != len(beats):
        raise ValueError(
            f"{tags_path} has {len(tags)} tagged beat(s) but this detection "
            f"found {len(beats)}. Beat index is positional, so these tags "
            "describe different shots. Re-tag against the current keyframes, "
            "or restore the detector settings the tags were written for "
            ""
        )

    manifest_path = Path(manifest_path) if manifest_path else None
    if not (manifest_path and manifest_path.exists()):
        return
    with manifest_path.open(encoding="utf-8") as fh:
        recorded = json.load(fh)
    drifted = [
        i for i, (was, now) in enumerate(zip(recorded, beats))
        if abs(float(was["start_sec"]) - float(now["start_sec"])) > 0.05
        or abs(float(was["end_sec"]) - float(now["end_sec"])) > 0.05
    ]
    if drifted:
        raise ValueError(
            f"detection no longer matches {manifest_path}: {len(drifted)} beat "
            f"boundar(ies) moved, first at index {drifted[0]}. The tags were "
            "written against the keyframes of the earlier pass, so replaying "
            "them now would tag the wrong shots. Re-run pass 1 and re-tag."
        )


class JsonTagger(Tagger):
    """Replays tags produced out-of-band (a vision model, or a human) from JSON.

    The file maps a beat index (as a string) to the same partial segment dict a
    live Tagger would return. Beat index is positional: it is the order
    ``detect_beats`` returned, so a tag file is only valid against the shot list
    the same detector settings produce.

    Underscore-prefixed keys (``_worksheet``) are
    scaffolding — the keyframe a tagger looked at, the timecodes it saw — and
    are stripped here, so ``assemble_segment``'s tagger-fields strictness keeps
    catching genuine mistakes instead of metadata.
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
        return {k: v for k, v in self._tags[key].items() if not k.startswith("_")}


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


# --- Keyframes ---------------------------------------------------------------


def extract_keyframes(video_path, beats, out_dir, ffmpeg=None):
    """One representative still per beat, written as ``<index>.jpg``.

    The frame is taken from the *middle* of the beat, not its first frame: a
    cut's opening frames are frequently mid-dissolve or mid-flash, which is
    exactly the material a tagger reads wrong.

    Returns the list of written paths, ordered by beat.
    """
    if ffmpeg is None:
        from tools.render import find_ffmpeg

        ffmpeg = find_ffmpeg()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    video_path = Path(video_path).resolve()

    written = []
    for i, beat in enumerate(beats):
        mid = (float(beat["start_sec"]) + float(beat["end_sec"])) / 2.0
        dest = (out_dir / f"{i:03d}.jpg").resolve()
        cmd = [*ffmpeg, "-nostdin", "-y", "-ss", f"{mid:.3f}", "-i", str(video_path),
               "-frames:v", "1", "-q:v", "3", str(dest)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0 or not dest.exists():
            raise RuntimeError(
                f"keyframe extraction failed for beat {i} at {mid:.3f}s: "
                f"{proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else 'no output'}"
            )
        written.append(dest)
    return written


# --- Indexing a real video ---------------------------------------------------


def keyframes_dir_for(video_record, root=None):
    """Where one video's stills belong: ``keyframes/<video_id>/``.

    Derived from the record rather than chosen at the command line, because
    choosing was the bug. ``--keyframes-dir keyframes/`` puts one video's
    ``000.jpg`` at the root of the tree, where the next video's ``000.jpg``
    overwrites it and the beats manifest with it -- silently, since the stills
    are gitignored and nothing downstream reads a filename. One directory per
    video_id makes that collision impossible and makes "which video is this
    frame from" answerable from the path.
    """
    root = Path(root) if root else REPO_ROOT / "keyframes"
    return root / video_record["video_id"]


def index_video(video_path, video_record, tags_path=None, keyframes_dir=None,
                out_dir=None, min_shot_sec=DEFAULT_MIN_SHOT_SEC, log=print):
    """Detect beats, optionally extract keyframes, optionally assemble segments.

    Deliberately runs in two passes, because tagging happens out-of-band:

      1. no ``tags_path``  -> detect + write keyframes, and stop. This is the
         pass whose output a vision model or human reads.
      2. ``tags_path`` set -> replay those tags through ``JsonTagger`` and write
         schema-valid segments.

    Both passes run the *same* detector settings, so beat indices line up. A
    tag file is only ever valid against the shot list its own detection pass
    produced.
    """
    beats = detect_beats(video_path, 0.0, min_shot_sec=min_shot_sec)
    log(f"{len(beats)} beat(s) detected in {video_path}")
    if len(beats) == 1:
        log("WARNING: exactly 1 beat for the whole video. On a cut-heavy source "
            "this means OpenCV could not decode it -- check for AV1 "
            "(docs/rendering.md).")

    if keyframes_dir:
        paths = extract_keyframes(video_path, beats, keyframes_dir)
        # The beat list travels with the stills: a tag file is only valid
        # against the shot list its own detection pass produced, and whoever
        # tags these frames needs their timecodes.
        manifest = Path(keyframes_dir) / "beats.json"
        with manifest.open("w", encoding="utf-8") as fh:
            json.dump([dict(b, beat_index=i, keyframe=str(Path(p).name))
                       for i, (b, p) in enumerate(zip(beats, paths))], fh, indent=2)
            fh.write("\n")
        log(f"wrote {len(paths)} keyframe(s) to {keyframes_dir}")

    if not tags_path:
        return beats, []

    # Before replaying a single tag: do these tags describe THESE shots?
    verify_tags_match_detection(
        tags_path, beats,
        manifest_path=keyframes_dir_for(video_record) / "beats.json",
    )

    tagger = JsonTagger.from_file(tags_path)
    leads = derive.load_leads()
    out_dir = Path(out_dir or REPO_ROOT / "segments")
    out_dir.mkdir(parents=True, exist_ok=True)

    segments = []
    for i, beat in enumerate(beats):
        beat = dict(beat, beat_index=i)
        segment = assemble_segment(video_record, beat, tagger.tag_beat(
            video_record["video_id"], beat, []), leads)
        validate_segment(segment)
        segments.append(segment)

    # Every segment is built and validated before anything is written, and the
    # video's previous segments are cleared first. A segment_id encodes its own
    # timecodes, so a re-index with different boundaries writes new filenames
    # and leaves the old ones behind -- orphans that are still schema-valid,
    # still loaded by search and by story.py's clean pool, and now describing
    # shots that no longer exist. Replacing the set is the only way the index
    # can be said to reflect one detection pass.
    written = set()
    for stale in out_dir.glob(f"seg_{video_record['video_id']}_*.json"):
        stale.unlink()
    for segment in segments:
        dest = out_dir / f"{segment['segment_id']}.json"
        with dest.open("w", encoding="utf-8") as fh:
            json.dump(segment, fh, indent=2)
            fh.write("\n")
        written.add(dest.name)

    clean = sum(1 for s in segments if s.get("clean"))
    log(f"wrote {len(segments)} segment(s) to {out_dir} ({clean} clean, "
        f"{len(segments) - clean} rejected by the clean gate)")
    return beats, segments


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


def _demo(args):
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


def _index(args):
    if not HAVE_SCENEDETECT:
        print("scenedetect is not installed: beats would be fixed-window, not shot "
              "boundaries. pip install scenedetect opencv-python-headless", file=sys.stderr)
        return 2
    with Path(args.video_record).open(encoding="utf-8") as fh:
        record = json.load(fh)
    index_video(
        args.video,
        record,
        tags_path=args.tags,
        # Pass 1 is the one that writes stills, and its destination is the
        # record's own video_id unless someone deliberately overrides it.
        keyframes_dir=(args.keyframes_dir
                       or (None if args.tags else keyframes_dir_for(record))),
        out_dir=args.out_dir,
        min_shot_sec=args.min_shot_sec,
    )
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Annotator pipeline: index a real video, or run the stub demo."
    )
    sub = parser.add_subparsers(dest="command")

    demo = sub.add_parser("demo", help="run the stub pipeline on a fake video")
    for target in (parser, demo):
        target.add_argument("--duration", type=float, default=12.0, help="fake video duration (sec)")
        target.add_argument("--window", type=float, default=DEFAULT_WINDOW_SEC, help="fallback window (sec)")
        target.add_argument("--video", default=None, help="real video path (uses scenedetect if installed)")

    idx = sub.add_parser(
        "index",
        help="detect beats + keyframes for a real video, and assemble segments once tagged",
    )
    idx.add_argument("--video", required=True, help="source media file")
    idx.add_argument("--video-record", required=True, help="videos/<video_id>.json")
    idx.add_argument("--keyframes-dir", default=None,
                     help="override the still destination (default: keyframes/<video_id>/)")
    idx.add_argument("--tags", default=None,
                     help="tag file to replay; omit for the detect+keyframe pass")
    idx.add_argument("--out-dir", default=None, help="segment output dir (default: segments/)")
    idx.add_argument("--min-shot-sec", type=float, default=DEFAULT_MIN_SHOT_SEC,
                     help="merge shots shorter than this (Destiny false-cut mitigation)")

    args = parser.parse_args(argv)
    return _index(args) if args.command == "index" else _demo(args)


if __name__ == "__main__":
    raise SystemExit(main())
