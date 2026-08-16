#!/usr/bin/env python3
"""One indexed video -> a cut list of the whole thing, in source order.

Some pieces are not edits: the source cinematic already tells the story, and
the job is to credit the cast on it and clean the frame, not to re-cut it. The
planners (tools/plate.py, tools/dialogue.py) all speak "cut list", so the
cheapest way to run them over an uncut video is to hand them one whose shots
are simply every segment of that video, end to end.

The output is a normal cut list, so timings on it are source timings: with no
re-ordering and no hold cap, the finished file and the source share a clock.

One exception: windows that ``redactions/<video_id>.json`` marks ``cut`` are
not in the finished video at all, so they leave the cut list too. A shot fully
inside a cut window drops out; a shot one overlaps is trimmed to the kept
range, not dropped. The range comes from tools.redact.kept_range -- the same
function the redaction pass trims the encode to -- so the cut list and the
redacted file agree on where the picture is, and plates timed against one land
on the other.
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.annotate import sec_to_tc  # noqa: E402
from tools.redact import REDACTIONS_DIR, kept_range, load_redactions  # noqa: E402
from tools.search import load_segments  # noqa: E402


def _clamp(shot, start, end):
    """The part of ``shot`` inside the kept range, or None if it is all cut."""
    s = max(float(shot["start_sec"]), start)
    e = min(float(shot["end_sec"]), end)
    if e - s < 0.001:
        return None
    trimmed = dict(shot, start_sec=s, end_sec=e)
    trimmed["start_tc"], trimmed["end_tc"] = sec_to_tc(s), sec_to_tc(e)
    return trimmed


def whole_video(video_id, segments_dir=None, redactions_dir=None):
    """Every segment of ``video_id``, in source order, as a cut list."""
    segments_dir = str(segments_dir or (REPO_ROOT / "segments"))
    shots = [s for s in load_segments(segments_dir)
             if s.get("video_id") == video_id]
    if not shots:
        raise SystemExit(f"no segments found for {video_id!r} in {segments_dir}")
    shots.sort(key=lambda s: s["start_sec"])

    try:
        data = load_redactions(video_id, root=redactions_dir or REDACTIONS_DIR)
    except FileNotFoundError:
        pass  # nothing redacted, so nothing to cut
    else:
        video_end = max(float(s["end_sec"]) for s in shots)
        start, end = kept_range(data["redactions"], video_end)
        if start > 0 or end < video_end:
            kept = []
            for shot in shots:
                trimmed = _clamp(shot, start, end)
                if trimmed is not None:
                    kept.append(trimmed)
            shots = kept
            if not shots:
                # The emptiness check above runs BEFORE the clamp, and
                # `kept_range` only refuses a kept span of <= 0 -- so a
                # redaction leaving a sub-frame sliver passes it and then
                # clamps every shot away. Report it the same way, rather than
                # letting main() raise IndexError off an empty list.
                raise SystemExit(
                    f"nothing survives the redaction for {video_id!r}: the "
                    f"kept range {start:.3f}s-{end:.3f}s leaves no shot longer "
                    f"than a frame")

    gaps = [(a["end_sec"], b["start_sec"]) for a, b in zip(shots, shots[1:])
            if abs(b["start_sec"] - a["end_sec"]) > 0.001]
    return {
        "title": video_id,
        "shots": shots,
        "misses": [],
        "pool_size": len(shots),
        "index_size": len(shots),
        # A gap means the index does not actually cover the video end to end,
        # so "uncut" would quietly skip footage. Reported, never swallowed.
        "gaps": [{"from_sec": a, "to_sec": b} for a, b in gaps],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Whole indexed video -> cut list.")
    ap.add_argument("video_id")
    ap.add_argument("--dir", default=str(REPO_ROOT / "segments"))
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    cut = whole_video(args.video_id, args.dir)
    with Path(args.out).open("w", encoding="utf-8") as fh:
        json.dump(cut, fh, indent=2)
        fh.write("\n")
    total = cut["shots"][-1]["end_sec"] - cut["shots"][0]["start_sec"]
    print(f"wrote {args.out}: {len(cut['shots'])} shot(s), {total:.2f}s")
    for gap in cut["gaps"]:
        print(f"  GAP in the index: {gap['from_sec']:.2f}s -> {gap['to_sec']:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
