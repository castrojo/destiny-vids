#!/usr/bin/env python3
"""One indexed video -> a cut list of the whole thing, in source order.

Some pieces are not edits: the source cinematic already tells the story, and
the job is to credit the cast on it and clean the frame, not to re-cut it. The
planners (tools/plate.py, tools/dialogue.py) all speak "cut list", so the
cheapest way to run them over an uncut video is to hand them one whose shots
are simply every segment of that video, end to end.

The output is a normal cut list, so timings on it are source timings: with no
re-ordering and no hold cap, the finished file and the source share a clock.
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.search import load_segments  # noqa: E402


def whole_video(video_id, segments_dir=None):
    """Every segment of ``video_id``, in source order, as a cut list."""
    segments_dir = str(segments_dir or (REPO_ROOT / "segments"))
    shots = [s for s in load_segments(segments_dir)
             if s.get("video_id") == video_id]
    if not shots:
        raise SystemExit(f"no segments found for {video_id!r} in {segments_dir}")
    shots.sort(key=lambda s: s["start_sec"])

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
