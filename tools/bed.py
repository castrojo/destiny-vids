#!/usr/bin/env python3
"""Measure a music bed, cut sections out of it, and cache its beat grid.

A scored cut needs three things this repo had no answer for: the bed's real
duration, where its bars fall, and what happens to every timecode when a
section is removed. All three live in a checked-in record, `music/<bed_id>.json`,
which is to a bed what `videos/<video_id>.json` is to a source video: provenance
plus the measurements, never the media.

**The grid is cached deliberately, and that is a correctness requirement rather
than an optimisation.** Beat tracking is a heuristic; re-running it after a
library upgrade can shift the downbeat phase by a beat, which would silently
move every cut in a finished piece. Committing the grid makes a re-render
reproducible and keeps the whole suite offline -- `librosa` is an optional
dependency, needed only to *create* a record, exactly as `scenedetect` is needed
only to index a video.

**Excisions are snapped to downbeats, and that is what keeps the grid whole.**
Cutting an arbitrary 13 seconds lands mid-bar: the music stumbles, and every
downbeat after the splice sits at a new phase, so a single (tempo, offset) pair
no longer describes the timeline. Snapping both endpoints to downbeats makes the
removed span a whole number of bars, and a whole number of bars is exactly the
condition under which the grid continues in phase across the splice. One grid,
no discontinuity, no special case downstream.

Usage:
    python3 tools/bed.py measure media/<bed>.wav --id <bed_id> \
        --source-url <url> --title <title> --artist <artist> --out music/
    python3 tools/bed.py excise music/<bed_id>.json --from 2:59 --to 3:12
    python3 tools/bed.py render music/<bed_id>.json --media media --out out.wav
    python3 tools/bed.py map music/<bed_id>.json --at 3:48 --edited
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO_ROOT = Path(__file__).resolve().parents[1]
MUSIC_DIR = REPO_ROOT / "music"
DEFAULT_BEATS_PER_BAR = 4


# --- timecodes --------------------------------------------------------------

def parse_tc(value):
    """``3:48``, ``3:48.5``, ``1:02:03`` or a bare number of seconds -> float."""
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if ":" not in text:
        return float(text)
    parts = [float(p) for p in text.split(":")]
    total = 0.0
    for part in parts:
        total = total * 60 + part
    return total


def fmt_tc(seconds):
    """Seconds -> ``M:SS.mmm``, the form the outline and the owner both use."""
    seconds = max(0.0, float(seconds))
    minutes, rest = divmod(seconds, 60)
    if minutes >= 60:
        hours, minutes = divmod(int(minutes), 60)
        return f"{hours}:{int(minutes):02d}:{rest:06.3f}"
    return f"{int(minutes)}:{rest:06.3f}"


# --- measurement ------------------------------------------------------------

def probe_duration(path, ffmpeg=None):
    """Exact duration in seconds, via ffprobe."""
    exe = ffmpeg or "ffprobe"
    out = subprocess.run(
        [exe, "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(Path(path).resolve())],
        capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def analyze_grid(path, beats_per_bar=DEFAULT_BEATS_PER_BAR, sr=22050,
                 beat_multiple=1):
    """Detect tempo, beats and the downbeat phase. Requires ``librosa``.

    Returns the grid dict that gets cached in the record.

    Beat trackers routinely lock onto a metrical level other than the one a
    listener taps -- most often double time, which is what this bed does (161.5
    bpm detected for a song that is felt at ~80.75). Snapping an edit to that
    grid snaps to half-bars, which is a weaker musical boundary than a bar line.

    ``beat_multiple`` selects the level: 2 keeps every other detected beat, so
    the tracked pulse becomes the half-note. It is a deliberate operator choice
    rather than a heuristic, because getting it wrong is not subtle and no
    amount of cleverness beats listening once. Both the raw detection and the
    chosen level are recorded so a later reader can tell what happened.

    The downbeat phase is the offset whose beats carry the most onset strength:
    a bar line is where the music pushes.
    """
    try:
        import librosa
        import numpy as np
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "beat analysis needs librosa: pip install librosa"
        ) from exc

    y, sr = librosa.load(str(path), sr=sr, mono=True)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, trim=False)
    onset = librosa.onset.onset_strength(y=y, sr=sr)

    if beat_multiple > 1:
        # Keep the phase that lands on the stronger onsets, then thin.
        scores = [float(onset[np.clip(beat_frames[off::beat_multiple], 0,
                                      len(onset) - 1)].mean())
                  for off in range(beat_multiple)]
        beat_frames = beat_frames[int(np.argmax(scores))::beat_multiple]

    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    if len(beat_times) < beats_per_bar * 2:
        raise RuntimeError(f"too few beats detected in {path}")

    onset_at_beat = onset[np.clip(beat_frames, 0, len(onset) - 1)]
    strength = [float(onset_at_beat[phase::beats_per_bar].mean())
                for phase in range(beats_per_bar)]
    phase = int(np.argmax(strength))

    interval = float(np.median(np.diff(beat_times)))
    return {
        "detected_tempo_bpm": round(float(np.atleast_1d(tempo)[0]), 3),
        "beat_multiple": beat_multiple,
        "beat_interval_sec": round(interval, 6),
        "tempo_bpm": round(60.0 / interval, 3),
        "beats_per_bar": beats_per_bar,
        "bar_sec": round(interval * beats_per_bar, 6),
        "downbeat_phase": phase,
        "downbeat_strength": [round(s, 4) for s in strength],
        "first_beat_sec": round(float(beat_times[0]), 6),
        "beats": [round(float(t), 6) for t in beat_times],
    }


def downbeats(grid):
    """The bar lines, in source-timeline seconds."""
    beats = grid["beats"]
    return [beats[i] for i in range(grid["downbeat_phase"], len(beats),
                                    grid["beats_per_bar"])]


def snap_to_downbeat(grid, seconds):
    """Nearest bar line to ``seconds``."""
    bars = downbeats(grid)
    return min(bars, key=lambda b: abs(b - seconds))


# --- excisions --------------------------------------------------------------

def plan_excision(grid, start, end):
    """Snap an excision to bar lines and report what moved.

    Returns a dict recording both the requested and the snapped span. Removing a
    whole number of bars is what lets the grid survive the splice, so the snap is
    not a nicety: an excision that is 4.37 bars long re-phases everything after
    it.

    Bars are counted by *index* rather than by dividing the span by the median
    bar length. Tracked downbeats carry a little jitter, so four real bars
    measure 4.07 median bars -- and reporting that would suggest a fractional
    excision where the cut is in fact exactly four bars of music. The index is
    the musical truth; the median is only an average.
    """
    bars = downbeats(grid)
    start_i = min(range(len(bars)), key=lambda i: abs(bars[i] - start))
    end_i = min(range(len(bars)), key=lambda i: abs(bars[i] - end))
    if end_i <= start_i:
        raise ValueError(
            f"excision collapses after snapping: {fmt_tc(start)}-{fmt_tc(end)} "
            f"both snap to bar {start_i}"
        )
    snapped_start, snapped_end = bars[start_i], bars[end_i]
    return {
        "requested_start_sec": round(float(start), 6),
        "requested_end_sec": round(float(end), 6),
        "start_sec": round(snapped_start, 6),
        "end_sec": round(snapped_end, 6),
        "start_bar": start_i,
        "end_bar": end_i,
        "removed_sec": round(snapped_end - snapped_start, 6),
        "removed_bars": end_i - start_i,
        "start_moved_sec": round(snapped_start - start, 6),
        "end_moved_sec": round(snapped_end - end, 6),
    }


def edited_duration(record):
    """Source duration minus everything excised."""
    removed = sum(e["removed_sec"] for e in record.get("excisions", []))
    return record["duration_sec"] - removed


def to_edited(record, source_sec):
    """Map a source timecode onto the edited timeline.

    Returns ``None`` for a moment that was cut out -- it has no edited position,
    and silently returning a neighbouring one would be a lie an anchor could be
    built on.
    """
    shift = 0.0
    for exc in sorted(record.get("excisions", []), key=lambda e: e["start_sec"]):
        if source_sec >= exc["end_sec"]:
            shift += exc["removed_sec"]
        elif source_sec >= exc["start_sec"]:
            return None
    return source_sec - shift


def to_source(record, edited_sec):
    """Map an edited timecode back onto the source timeline."""
    result = edited_sec
    for exc in sorted(record.get("excisions", []), key=lambda e: e["start_sec"]):
        if result >= exc["start_sec"]:
            result += exc["removed_sec"]
    return result


def edited_downbeats(record):
    """Bar lines on the *edited* timeline.

    Because every excision spans a whole number of bars, these are exactly the
    surviving source downbeats shifted left -- the grid does not re-phase at a
    splice, so there is no second grid to reconcile.
    """
    out = []
    for bar in downbeats(record["grid"]):
        mapped = to_edited(record, bar)
        if mapped is not None:
            out.append(round(mapped, 6))
    return out


def nearest_edited_downbeat(record, edited_sec):
    bars = edited_downbeats(record)
    return min(bars, key=lambda b: abs(b - edited_sec))


# --- rendering --------------------------------------------------------------

def build_filter(record):
    """An ffmpeg filter that concatenates the surviving spans."""
    spans = []
    cursor = 0.0
    for exc in sorted(record.get("excisions", []), key=lambda e: e["start_sec"]):
        if exc["start_sec"] > cursor:
            spans.append((cursor, exc["start_sec"]))
        cursor = exc["end_sec"]
    if cursor < record["duration_sec"]:
        spans.append((cursor, record["duration_sec"]))

    parts = []
    for n, (start, end) in enumerate(spans):
        parts.append(
            f"[0:a]atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS[a{n}]"
        )
    chain = "".join(f"[a{n}]" for n in range(len(spans)))
    parts.append(f"{chain}concat=n={len(spans)}:v=0:a=1[out]")
    return ";".join(parts), spans


def probe_codec(path, ffmpeg=None):
    """The source's PCM codec name, so a re-cut does not quietly downgrade it."""
    exe = ffmpeg or "ffprobe"
    out = subprocess.run(
        [exe, "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=codec_name", "-of", "csv=p=0",
         str(Path(path).resolve())],
        capture_output=True, text=True, check=True).stdout.strip()
    return out or "pcm_s16le"


def render_bed(record, media_dir, out_path, ffmpeg="ffmpeg"):
    """Write the edited bed.

    Lossless by construction: the spans are concatenated at the source's own
    codec, sample rate and bit depth, with no EQ, no resample and no loudness
    processing. Cutting a section out of a bed is an edit, not a mastering pass,
    and a 24-bit source that comes back 16-bit has been quietly mastered.
    """
    src = Path(media_dir) / record["media_filename"]
    if not src.exists():
        raise FileNotFoundError(f"bed media not found: {src}")
    filt, spans = build_filter(record)
    codec = probe_codec(src)
    cmd = [ffmpeg, "-v", "error", "-y", "-i", str(src.resolve()),
           "-filter_complex", filt, "-map", "[out]",
           "-c:a", codec, str(Path(out_path).resolve())]
    subprocess.run(cmd, check=True)
    return spans


# --- records ----------------------------------------------------------------

def load_record(path):
    with Path(path).open(encoding="utf-8") as fh:
        return json.load(fh)


def save_record(record, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
        fh.write("\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("measure", help="create a bed record from a media file")
    m.add_argument("media")
    m.add_argument("--id", required=True)
    m.add_argument("--source-url", default="")
    m.add_argument("--title", default="")
    m.add_argument("--artist", default="")
    m.add_argument("--usage-class", default="third_party_copyrighted")
    m.add_argument("--rights-note", default="")
    m.add_argument("--beats-per-bar", type=int, default=DEFAULT_BEATS_PER_BAR)
    m.add_argument("--beat-multiple", type=int, default=1,
                   help="keep every Nth detected beat; 2 undoes a double-time "
                        "lock, which beat trackers do routinely")
    m.add_argument("--out", default=str(MUSIC_DIR))

    e = sub.add_parser("excise", help="snap and record a section to remove")
    e.add_argument("record")
    e.add_argument("--from", dest="start", required=True)
    e.add_argument("--to", dest="end", required=True)

    r = sub.add_parser("render", help="write the edited bed")
    r.add_argument("record")
    r.add_argument("--media", default=str(REPO_ROOT / "media"))
    r.add_argument("--out", required=True)

    mp = sub.add_parser("map", help="translate a timecode between timelines")
    mp.add_argument("record")
    mp.add_argument("--at", required=True)
    mp.add_argument("--edited", action="store_true",
                    help="--at is on the edited timeline (default: source)")

    args = ap.parse_args(argv)

    if args.cmd == "measure":
        media = Path(args.media)
        grid = analyze_grid(media, beats_per_bar=args.beats_per_bar,
                            beat_multiple=args.beat_multiple)
        record = {
            "bed_id": args.id,
            "media_filename": media.name,
            "source_url": args.source_url,
            "title": args.title,
            "artist": args.artist,
            "usage_class": args.usage_class,
            "source_rights_note": args.rights_note,
            "duration_sec": round(probe_duration(media), 6),
            "grid": grid,
            "excisions": [],
        }
        out = Path(args.out)
        dest = out / f"{args.id}.json" if out.is_dir() or not out.suffix else out
        save_record(record, dest)
        print(f"wrote {dest}")
        print(f"  duration {record['duration_sec']:.3f}s ({fmt_tc(record['duration_sec'])})")
        print(f"  tempo {grid['tempo_bpm']} bpm, bar {grid['bar_sec']:.4f}s, "
              f"{len(downbeats(grid))} bars")
        return 0

    record = load_record(args.record)

    if args.cmd == "excise":
        start, end = parse_tc(args.start), parse_tc(args.end)
        exc = plan_excision(record["grid"], start, end)
        record.setdefault("excisions", []).append(exc)
        record["excisions"].sort(key=lambda x: x["start_sec"])
        save_record(record, args.record)
        print(f"excision snapped to bar lines:")
        print(f"  requested {fmt_tc(start)} -> {fmt_tc(end)}")
        print(f"  snapped   {fmt_tc(exc['start_sec'])} -> {fmt_tc(exc['end_sec'])}"
              f"  ({exc['start_moved_sec']:+.3f}s / {exc['end_moved_sec']:+.3f}s)")
        print(f"  removes   {exc['removed_sec']:.3f}s = {exc['removed_bars']:g} bars")
        print(f"  edited duration {edited_duration(record):.3f}s "
              f"({fmt_tc(edited_duration(record))})")
        return 0

    if args.cmd == "render":
        spans = render_bed(record, args.media, args.out)
        print(f"wrote {args.out} from {len(spans)} span(s)")
        for start, end in spans:
            print(f"  {fmt_tc(start)} -> {fmt_tc(end)}")
        return 0

    if args.cmd == "map":
        at = parse_tc(args.at)
        if args.edited:
            src = to_source(record, at)
            near = nearest_edited_downbeat(record, at)
            print(f"edited {fmt_tc(at)}  ->  source {fmt_tc(src)}")
            print(f"  nearest edited downbeat {fmt_tc(near)} ({near - at:+.3f}s)")
            print(f"  {edited_duration(record) - at:.3f}s from the end")
        else:
            mapped = to_edited(record, at)
            if mapped is None:
                print(f"source {fmt_tc(at)} was excised; it has no edited position")
                return 1
            print(f"source {fmt_tc(at)}  ->  edited {fmt_tc(mapped)}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
