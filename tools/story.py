#!/usr/bin/env python3
"""Assemble a story from clean shots — outline in, cut list out.

This is the point of the whole index. You write the story as an ORDERED LIST OF
BEATS in plain language; this walks the beats in order, pulls the best CLEAN
shot for each out of the index, refuses to reuse a shot twice, and emits an
ordered cut list you can hand to an NLE.

The fiction bends to the footage: if a beat has no clean match, that is a real
answer — rewrite the beat rather than cutting a HUD into the sequence. Unmatched
beats are reported, never silently dropped.

``--forward-only`` builds the cut as ONE cinematic played once through: every
beat after the first must come from the same source video and start at or after
the previous beat's out point, so the cut only ever advances by SKIPPING
FORWARD. The skipped stretches are reported as ``skips``. This is deliberately
not an edit graph — one source, one direction, and the outline is the only
place a cut is authored.

Outline formats (both accepted):
  * a text file, one beat per line, ``#`` for comments;
  * a JSON file: ``{"title": ..., "fps": 30, "beats": [{"beat": "...",
    "duration": 4.0}, ...]}`` — or just a list of strings.

Usage:
    python3 tools/story.py outline.txt
    python3 tools/story.py outline.txt --dir examples --format edl --out cut.edl
    python3 tools/story.py outline.txt --format json --out shotlist.json
    python3 tools/story.py outline.txt --allow-gameplay
    python3 tools/story.py outline.txt --dir segments --forward-only \\
        --video yt_destiny_2_the_final_shape_launch_trailer
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.annotate import sec_to_tc  # noqa: E402
from tools.search import (  # noqa: E402
    lead_weight_for, load_segments, parse_query, relaxed_filter, score_segment,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_FPS = 30

# Float slack for "starts at or after the playhead": segment boundaries come
# from a frame-difference detector, so they are never exactly equal.
FORWARD_EPS = 1e-6

# Gaps below this are rounding, not an editorial skip.
MIN_SKIP_SEC = 0.01

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


def pick_shot(beat, candidates, used_ids):
    """Best-scoring unused candidate for one beat, or None.

    Reuse is blocked because a story that cuts the same shot twice reads as
    padding; the caller reports the miss so the beat can be rewritten.
    """
    parsed = parse_query(beat)
    survivors, active, dropped = relaxed_filter(candidates, parsed["filters"])
    weights = {"lead": lead_weight_for(parsed["filters"])}
    scored = []
    for seg in survivors:
        if seg.get("segment_id") in used_ids:
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


def build_story(outline_beats, segments, allow_gameplay=False, video_id=None,
                forward_only=False):
    """Walk the beats in order, casting each to a distinct clean shot.

    ``video_id`` pins the cut to ONE source video. ``forward_only`` plays that
    one video through once: a beat may only take a shot starting at or after the
    previous beat's out point, so the cut advances by skipping forward and never
    doubles back. With no ``video_id``, the first matched beat locks the cut to
    its own video and the rest of the outline follows it — one cinematic, one
    direction, no stitching layer.
    """
    # THE gate: only clean footage is eligible. Gameplay is opt-in coverage.
    pool = [s for s in segments if s.get("clean")]
    if not allow_gameplay:
        pool = [s for s in pool if s.get("footage_tier") != "gameplay"]
    if video_id:
        pool = [s for s in pool if s.get("video_id") == video_id]

    shots = []
    misses = []
    used = set()
    locked = video_id      # the one cinematic, once something has chosen it
    cursor = 0.0           # playhead on that cinematic's own timeline
    for index, item in enumerate(outline_beats, start=1):
        candidates = pool
        if forward_only and locked:
            candidates = [s for s in candidates
                          if s.get("video_id") == locked
                          and (s.get("start_sec") or 0) >= cursor - FORWARD_EPS]
        pick = pick_shot(item["beat"], candidates, used)
        if pick is None:
            misses.append({"index": index, "beat": item["beat"]})
            continue
        seg = pick["segment"]
        used.add(seg.get("segment_id"))
        source_duration = (seg.get("end_sec", 0) or 0) - (seg.get("start_sec", 0) or 0)
        duration = item["duration"] or source_duration
        if forward_only:
            locked = seg.get("video_id")
            cursor = (seg.get("start_sec") or 0) + duration
        shots.append({
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
        })
    story = {"shots": shots, "misses": misses,
             "pool_size": len(pool), "index_size": len(segments)}
    if forward_only:
        story["video_id"] = locked
        story["skips"] = find_skips(shots, segments, locked)
    return story


def find_skips(shots, segments, video_id):
    """The stretches of the one cinematic this cut skips over.

    Derived, never authored: a skip is simply the gap between one beat's out
    point and the next beat's in point, plus the head and tail the cut never
    reaches. Counting the segments inside each gap says what was passed over —
    including the shots the clean gate already removed, such as a title card.
    """
    if not video_id or not shots:
        return []
    source = sorted((s for s in segments if s.get("video_id") == video_id),
                    key=lambda s: s.get("start_sec") or 0)
    if not source:
        return []
    video_end = max((s.get("end_sec") or 0) for s in source)

    def gap(after, start, end):
        skipped = [s for s in source
                   if (s.get("start_sec") or 0) >= start - FORWARD_EPS
                   and (s.get("end_sec") or 0) <= end + FORWARD_EPS]
        return {"after_shot": after, "from_sec": round(start, 3), "to_sec": round(end, 3),
                "from_tc": sec_to_tc(start), "to_tc": sec_to_tc(end),
                "seconds": round(end - start, 3), "segments_skipped": len(skipped)}

    skips = []
    cursor = 0.0
    previous = 0
    for shot in shots:
        start = shot.get("start_sec") or 0
        if start - cursor > MIN_SKIP_SEC:
            skips.append(gap(previous, cursor, start))
        cursor = start + shot["duration"]
        previous = shot["index"]
    if video_end - cursor > MIN_SKIP_SEC:
        skips.append(gap(previous, cursor, video_end))
    return skips


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
             f"{story['pool_size']}/{story['index_size']} indexed segment(s)"]
    if story.get("video_id"):
        lines.append(f"one cinematic, played forward: {story['video_id']}")
    lines.append("")
    for shot in story["shots"]:
        casting = shot.get("casting") or {}
        who = casting.get("character") or (
            f"ensemble x{casting.get('slots')}" if casting.get("role") == "ensemble" else "—")
        lines.append(f"{shot['index']:>3}. {shot['beat']}")
        lines.append(f"     {shot['video_id']}  {shot['start_tc']}–{shot['end_tc']}  "
                     f"({shot['duration']:g}s, {shot['footage_tier']}, {who})")
        lines.append(f"     {shot['segment_id']}  [{shot['score']:+.2f}] "
                     f"{', '.join(shot['why'])}")
        cap = (shot.get("caption") or "").strip()
        if cap:
            lines.append(f"     “{cap[:110]}{'…' if len(cap) > 110 else ''}”")
        lines.append("")
    if story.get("skips"):
        lines.append("SKIPPED FORWARD — stretches of the cinematic this cut passes over:")
        for skip in story["skips"]:
            after = f"after shot {skip['after_shot']}" if skip["after_shot"] else "head"
            lines.append(f"  {after:>13}: {skip['from_tc']}–{skip['to_tc']} "
                         f"({skip['seconds']:g}s, {skip['segments_skipped']} segment(s))")
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
    ap.add_argument("--video", help="pin the cut to one source video_id")
    ap.add_argument("--forward-only", action="store_true",
                    help="one cinematic, played through once: every beat starts at "
                         "or after the previous beat's out point")
    args = ap.parse_args(argv)

    title, fps, beats = read_outline(args.outline)
    segments = load_segments(args.dir)
    if not segments:
        print(f"No segment records found in {args.dir}", file=sys.stderr)
        return 1
    story = build_story(beats, segments, allow_gameplay=args.allow_gameplay,
                        video_id=args.video, forward_only=args.forward_only)

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
