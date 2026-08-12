#!/usr/bin/env python3
"""Assemble a story from clean shots — outline in, cut list out.

This is the point of the whole index. You write the story as an ORDERED LIST OF
BEATS in plain language; this walks the beats in order, pulls the best CLEAN
shot for each out of the index, refuses to reuse a shot twice, and emits an
ordered cut list you can hand to an NLE.

The fiction bends to the footage: if a beat has no clean match, that is a real
answer — rewrite the beat rather than cutting a HUD into the sequence. Unmatched
beats are reported, never silently dropped.

Outline formats (both accepted):
  * a text file, one beat per line, ``#`` for comments;
  * a JSON file: ``{"title": ..., "fps": 30, "beats": [{"beat": "...",
    "duration": 4.0}, ...]}`` — or just a list of strings.

Usage:
    python3 tools/story.py outline.txt
    python3 tools/story.py outline.txt --dir examples --format edl --out cut.edl
    python3 tools/story.py outline.txt --format json --out shotlist.json
    python3 tools/story.py outline.txt --allow-gameplay
    python3 tools/story.py outline.txt --from-video <video_id> --forward-only
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.search import (  # noqa: E402
    lead_weight_for, load_segments, parse_query, relaxed_filter, score_segment,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_FPS = 30

# A beat is a specific instruction, not a browse. Weighting literal relevance
# well above the standing editorial boosts stops a merely well-rated shot (a
# named lead, say) from hijacking a beat that plainly describes something else.
BEAT_CAPTION_WEIGHT = 3.0


def read_outline(path):
    """Parse an outline file into ``(title, fps, [{beat, duration}])``."""
    with open(path) as fh:
        raw = fh.read()
    stripped = raw.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        data = json.loads(raw)
        if isinstance(data, list):
            return os.path.basename(path), DEFAULT_FPS, [_beat(b) for b in data]
        beats = [_beat(b) for b in data.get("beats", [])]
        return data.get("title", os.path.basename(path)), data.get("fps", DEFAULT_FPS), beats
    beats = [_beat(line) for line in raw.splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    return os.path.basename(path), DEFAULT_FPS, beats


def _beat(entry):
    if isinstance(entry, str):
        return {"beat": entry.strip(), "duration": None}
    return {"beat": entry.get("beat", "").strip(), "duration": entry.get("duration")}


def pick_shot(beat, candidates, used_ids, after_sec=None):
    """Best-scoring unused candidate for one beat, or None.

    Reuse is blocked because a story that cuts the same shot twice reads as
    padding; the caller reports the miss so the beat can be rewritten.

    ``after_sec`` is the forward-only floor: a candidate that starts before it
    would run the source cinematic backwards, so it is not a candidate.
    """
    parsed = parse_query(beat)
    survivors, active, dropped = relaxed_filter(candidates, parsed["filters"])
    weights = {"lead": lead_weight_for(parsed["filters"])}
    scored = []
    for seg in survivors:
        if seg.get("segment_id") in used_ids:
            continue
        if after_sec is not None and (seg.get("start_sec") or 0) < after_sec:
            continue
        # A blocked constrained lead does not read as the character, so it can
        # never carry a beat — even one that never named that character.
        if (seg.get("casting") or {}).get("usable") is False and \
                (seg.get("casting") or {}).get("role") == "lead":
            continue
        score, reasons = score_segment(seg, parsed["caption_terms"], weights=weights,
                                       caption_weight=BEAT_CAPTION_WEIGHT)
        scored.append((score, seg, reasons))
    if not scored:
        return None
    scored.sort(key=lambda r: (r[0], r[1].get("substitutability") or 0), reverse=True)
    score, seg, reasons = scored[0]
    return {"segment": seg, "score": score, "reasons": reasons,
            "relaxed": [f for f, _ in dropped], "filters": {k: sorted(v) for k, v in active.items()}}


def build_story(outline_beats, segments, allow_gameplay=False, from_video=None,
                forward_only=False):
    """Walk the beats in order, casting each to a distinct clean shot.

    ``from_video`` narrows the pool to one source cinematic and ``forward_only``
    makes the cut advance along that cinematic's own timeline — each beat may
    only take a shot at or after the end of the last one, so the story skips
    forward and never doubles back. Together they are the whole "one cinematic,
    skipped forward" shape: no timeline object, no sequencer, just the pool and
    a floor that moves.

    ``forward_only`` without ``from_video`` is refused: the playhead is seconds
    on ONE cinematic's timeline, and compared across different sources it would
    silently exclude shots and report a skip measured between unrelated
    timelines.
    """
    if forward_only and not from_video:
        raise ValueError("forward_only needs from_video: a forward-only "
                         "playhead only has meaning on one cinematic's "
                         "timeline")

    # THE gate: only clean footage is eligible. Gameplay is opt-in coverage.
    pool = [s for s in segments if s.get("clean")]
    if not allow_gameplay:
        pool = [s for s in pool if s.get("footage_tier") != "gameplay"]
    if from_video:
        pool = [s for s in pool if s.get("video_id") == from_video]

    shots = []
    misses = []
    used = set()
    playhead = 0.0 if forward_only else None
    for index, item in enumerate(outline_beats, start=1):
        pick = pick_shot(item["beat"], pool, used, after_sec=playhead)
        if pick is None:
            misses.append({"index": index, "beat": item["beat"]})
            continue
        seg = pick["segment"]
        used.add(seg.get("segment_id"))
        source_duration = (seg.get("end_sec", 0) or 0) - (seg.get("start_sec", 0) or 0)
        duration = item["duration"] or source_duration
        shot = {
            "index": index,
            "beat": item["beat"],
            "segment_id": seg.get("segment_id"),
            "video_id": seg.get("video_id"),
            "start_sec": seg.get("start_sec"),
            "end_sec": seg.get("end_sec"),
            "start_tc": seg.get("start_tc"),
            "end_tc": seg.get("end_tc"),
            "duration": duration,
            "footage_tier": seg.get("footage_tier"),
            "casting": seg.get("casting"),
            "caption": seg.get("caption"),
            "score": round(pick["score"], 3),
            "why": pick["reasons"],
            "segment": seg,
        }
        if playhead is not None:
            # How far the cinematic was skipped forward to reach this beat.
            shot["skip_sec"] = round((seg.get("start_sec") or 0) - playhead, 3)
            playhead = seg.get("end_sec") or 0
        shots.append(shot)
    return {"shots": shots, "misses": misses,
            "pool_size": len(pool), "index_size": len(segments)}


def tc(seconds, fps=DEFAULT_FPS):
    """Seconds -> ``HH:MM:SS:FF`` timecode."""
    total_frames = int(round((seconds or 0) * fps))
    frames = total_frames % fps
    total_seconds = total_frames // fps
    return (f"{total_seconds // 3600:02d}:{(total_seconds // 60) % 60:02d}:"
            f"{total_seconds % 60:02d}:{frames:02d}")


def to_edl(story, title, fps=DEFAULT_FPS):
    """CMX3600-style EDL: source in/out against a running record timeline."""
    lines = [f"TITLE: {title}", "FCM: NON-DROP FRAME", ""]
    record = 0.0
    for n, shot in enumerate(story["shots"], start=1):
        src_in = shot["start_sec"] or 0
        src_out = src_in + shot["duration"]
        rec_in, rec_out = record, record + shot["duration"]
        record = rec_out
        lines.append(
            f"{n:03d}  AX       V     C        "
            f"{tc(src_in, fps)} {tc(src_out, fps)} {tc(rec_in, fps)} {tc(rec_out, fps)}"
        )
        lines.append(f"* FROM CLIP NAME: {shot['video_id']}")
        lines.append(f"* BEAT: {shot['beat']}")
        lines.append("")
    return "\n".join(lines)


def to_csv(story):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["#", "beat", "video_id", "segment_id", "start_tc", "end_tc",
                     "duration", "tier", "role", "character", "score"])
    for shot in story["shots"]:
        casting = shot.get("casting") or {}
        writer.writerow([shot["index"], shot["beat"], shot["video_id"], shot["segment_id"],
                         shot["start_tc"], shot["end_tc"], f"{shot['duration']:g}",
                         shot["footage_tier"], casting.get("role"), casting.get("character"),
                         shot["score"]])
    return buf.getvalue()


def to_text(story, title):
    lines = [f"STORY: {title}",
             f"{len(story['shots'])} shot(s) from a clean pool of "
             f"{story['pool_size']}/{story['index_size']} indexed segment(s)", ""]
    for shot in story["shots"]:
        casting = shot.get("casting") or {}
        who = casting.get("character") or (
            f"ensemble x{casting.get('slots')}" if casting.get("role") == "ensemble" else "—")
        lines.append(f"{shot['index']:>3}. {shot['beat']}")
        skip = ""
        if shot.get("skip_sec") is not None:
            skip = f"  [skip +{shot['skip_sec']:g}s]"
        lines.append(f"     {shot['video_id']}  {shot['start_tc']}–{shot['end_tc']}  "
                     f"({shot['duration']:g}s, {shot['footage_tier']}, {who}){skip}")
        lines.append(f"     {shot['segment_id']}  [{shot['score']:+.2f}] "
                     f"{', '.join(shot['why'])}")
        cap = (shot.get("caption") or "").strip()
        if cap:
            lines.append(f"     “{cap[:110]}{'…' if len(cap) > 110 else ''}”")
        lines.append("")
    if story["misses"]:
        lines.append("UNMATCHED BEATS — no clean shot covers these; rewrite them:")
        for miss in story["misses"]:
            lines.append(f"  {miss['index']:>3}. {miss['beat']}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("outline", help="outline file: one beat per line, or JSON")
    ap.add_argument("--dir", default=os.path.join(REPO_ROOT, "examples"),
                    help="directory of segment records (default: examples/)")
    ap.add_argument("--format", choices=["text", "json", "edl", "csv"], default="text")
    ap.add_argument("--out", help="write output here instead of stdout")
    ap.add_argument("--allow-gameplay", action="store_true",
                    help="let gameplay-tier shots into the pool as coverage")
    ap.add_argument("--from-video", metavar="VIDEO_ID",
                    help="cut from ONE source cinematic only")
    ap.add_argument("--forward-only", action="store_true",
                    help="each beat must sit at or after the last one on the "
                         "source timeline — the cut skips forward, never back "
                         "(requires --from-video)")
    args = ap.parse_args(argv)
    if args.forward_only and not args.from_video:
        ap.error("--forward-only skips forward within ONE source cinematic; "
                 "pass --from-video VIDEO_ID with it")

    title, fps, beats = read_outline(args.outline)
    segments = load_segments(args.dir)
    if not segments:
        print(f"No segment records found in {args.dir}", file=sys.stderr)
        return 1
    story = build_story(beats, segments, allow_gameplay=args.allow_gameplay,
                        from_video=args.from_video, forward_only=args.forward_only)

    if args.format == "json":
        payload = dict(story)
        payload["title"] = title
        text = json.dumps(payload, indent=2)
    elif args.format == "edl":
        text = to_edl(story, title, fps)
    elif args.format == "csv":
        text = to_csv(story)
    else:
        text = to_text(story, title)

    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text if text.endswith("\n") else text + "\n")
        print(f"wrote {args.out} ({len(story['shots'])} shot(s), "
              f"{len(story['misses'])} unmatched beat(s))")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
