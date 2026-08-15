#!/usr/bin/env python3
"""Measure the transitions between acts on a BUILT programme.

Issue #105: every act join was the same shape -- the outgoing act faded to
digital silence, the slide held several seconds of absolute ``-inf``, and the
next act entered hot. This tool turns that prose into a table, measured on the
assembled file rather than derived from the plan, so a treatment can be
checked after assembly instead of asserted.

    python3 tools/transitions.py stories/megacut/megacut.json \
        --measure ~/Videos/Wolves/megacut/seven-days-to-the-wolves-v0.6.mp4

TWO CLOCKS, and this tool keeps them apart (issue #109 paid for mixing them
twice):

* every row of the report is on the **programme (megacut) clock** -- the
  timecode you would write down while watching the assembled file;
* the act's own film time never appears here. To fix something the report
  shows, run ``tools/megacut.py --locate <stamp>`` and work in that act's
  project.

What a "join" is
----------------
The plan is a flat list of cards (act slides) and clips (acts). A join is
every place the sound can go to nothing:

* ``slide``  -- clip -> card -> clip: the outgoing act's tail, the slide's
  generated silence, the incoming act's head. Acts IV and V share one slide,
  so there is no slide join between them;
* ``direct`` -- clip -> clip with no card (IV -> V): the only place two acts
  touch with nothing between;
* ``head``   -- the opening card -> act I;
* ``tail``   -- the last act's tail running out to the end of the programme.

Per join the report prints one RMS row per second (decoded f32 PCM, all
channels summed, 1.0 s buckets aligned to integer programme seconds) and three
summary numbers: the longest run of buckets at or below ``SILENCE_DB`` (true
digital silence reads about -91 dB through AAC; -80 dB is already inaudible on
a room PA), the outgoing act's level one second before it goes silent, and the
incoming act's first non-silent second -- the "entry level" whose 13 dB spread
the issue flags.

The tool never writes anything. It is the measurement half of the fix; the
treatment half is ``fade_in``/``fade_out`` on plan clips in
``tools/megacut.py``, which is what makes a join stop entering dry out of
digital silence. Whether the slides themselves should carry a bed is a
licensing decision and stays with the owner -- this tool only reports how long
the silence is.
"""

from __future__ import annotations

import argparse
import math
import os
import statistics
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import megacut  # noqa: E402

# A bucket at or below this RMS counts as silence. AAC digital silence
# measures about -91 dB; -80 dB leaves margin for encoder noise without
# calling a quiet room tone "silence".
SILENCE_DB = -80.0

# Seconds of context measured on each side of a join.
PRE = 6.0
POST = 4.0

BUCKET = 1.0


def db(mean_square):
    """RMS level in dBFS of a mean square. True zero is -inf, not a floor."""
    if mean_square <= 0.0:
        return float("-inf")
    return 10.0 * math.log10(mean_square)


def bucket_rms(pcm, channels, rate):
    """Per-bucket RMS (dBFS) of interleaved f32le PCM.

    Pure arithmetic, so the tests exercise it with no ffmpeg and no footage.
    Buckets are counted from the first sample, so callers align them to the
    programme clock by decoding from an integer second. A short tail bucket
    (the file ended mid-second) is dropped: it would read loud or quiet
    depending on how much of the bucket is real.
    """
    n = len(pcm) // 4
    samples = struct.unpack(f"<{n}f", pcm[: n * 4])
    per = int(rate * BUCKET) * channels
    out = []
    for start in range(0, n - per + 1, per):
        chunk = samples[start : start + per]
        out.append(db(statistics.fmean(s * s for s in chunk)))
    return out


def probe_audio_shape(path):
    """(sample_rate, channels) of the first audio stream, for bucketing."""
    probe = megacut.ffprobe_bin()
    out = subprocess.run(
        [probe, "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=sample_rate,channels",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    rate, channels = out.split(",")
    return int(rate), int(channels)


def decode(path, start, dur, ffmpeg=None):
    """PCM f32le of ``dur`` seconds from ``start`` (programme clock).

    Input seeking is accurate (docs/rendering.md) and this is measurement, not
    a cut: no frames are duplicated or dropped that the report would read.
    """
    ffmpeg = ffmpeg or megacut.ffmpeg_bin()
    return subprocess.run(
        [ffmpeg, "-nostdin", "-v", "error",
         "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(path),
         "-map", "a:0", "-f", "f32le", "-acodec", "pcm_f32le", "-"],
        capture_output=True, check=True,
    ).stdout


def find_joins(plan, durations=None):
    """The programme's joins, in order, all times on the PROGRAMME clock.

    Pure once durations are known, so the tests build plans by hand. Each join
    is a dict with ``kind`` (head/tail/slide/direct), the outgoing and
    incoming labels, and the window of interest: for a slide, the card's
    [start, end); for a direct join, the boundary point as [t, t).
    """
    if durations is None:
        durations = [megacut.item_duration(item) for item in plan["items"]]
    items = plan["items"]
    starts, t = [], 0.0
    for dur in durations:
        starts.append(t)
        t += dur
    total = t

    joins = []
    for i, item in enumerate(items):
        if item["kind"] != "card":
            continue
        nxt = items[i + 1] if i + 1 < len(items) else None
        if i == 0:
            joins.append({
                "kind": "head", "label": item.get("chapter") or item.get("label"),
                "out_label": None,
                "in_label": nxt.get("label") if nxt else None,
                "silent_start": starts[i], "silent_end": starts[i] + durations[i],
            })
            continue
        prev = items[i - 1]
        joins.append({
            "kind": "slide", "label": item.get("chapter") or item.get("label"),
            "out_label": prev.get("label"),
            "in_label": nxt.get("label") if nxt else None,
            "silent_start": starts[i], "silent_end": starts[i] + durations[i],
        })
    for i in range(len(items) - 1):
        if items[i]["kind"] == "clip" and items[i + 1]["kind"] == "clip":
            boundary = starts[i] + durations[i]
            joins.append({
                "kind": "direct",
                "label": f"{items[i].get('label')} -> {items[i + 1].get('label')}",
                "out_label": items[i].get("label"),
                "in_label": items[i + 1].get("label"),
                "silent_start": boundary, "silent_end": boundary,
            })
    joins.append({
        "kind": "tail", "label": "end of programme",
        "out_label": items[-1].get("label"), "in_label": None,
        "silent_start": total, "silent_end": total,
    })
    joins.sort(key=lambda j: j["silent_start"])
    return joins


def silence_run(buckets, start_idx, end_idx):
    """Longest run of consecutive buckets <= SILENCE_DB within [start, end).

    Indices are bucket offsets into ``buckets``. This is the number the issue
    quotes as "about 7 seconds of true digital silence".
    """
    best = run = 0
    for i in range(start_idx, min(end_idx, len(buckets))):
        if buckets[i] == float("-inf") or buckets[i] <= SILENCE_DB:
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best


def measure_join(path, join, rate, channels, decode_fn=decode, pre=PRE, post=POST):
    """One join's per-second RMS rows plus its summary, programme clock.

    The window runs from ``pre`` seconds before the silent stretch (or
    boundary) to ``post`` seconds after it, aligned DOWN to an integer second
    so bucket N is programme second N -- the same alignment the issue's hand
    table used, so the numbers compare row for row.

    ``pre``/``post`` default to the module's PRE/POST, which is what every
    caller wanted; they are parameters because ``--pre``/``--post`` exist on
    the CLI, and issue #204 was exactly this signature not accepting them --
    ``main()`` passed them, ``measure_join()`` did not take them, and every
    invocation of the CLI died with a TypeError. The tests called
    ``measure_join`` directly, so CI never walked the path that crashed.
    """
    win_start = max(0, math.floor(join["silent_start"] - pre))
    win_end = math.ceil(join["silent_end"] + post)
    pcm = decode_fn(path, win_start, win_end - win_start)
    buckets = bucket_rms(pcm, channels, rate)
    rows = [(win_start + i, level) for i, level in enumerate(buckets)]

    silent_from = int(round(join["silent_start"])) - win_start
    silent_to = int(round(join["silent_end"])) - win_start
    run = silence_run(buckets, silent_from, max(silent_to, silent_from + 1))

    def nearest(idx, direction):
        """First bucket at/above the threshold, walking in `direction`."""
        i = idx
        while 0 <= i < len(buckets):
            if buckets[i] > SILENCE_DB:
                return win_start + i, buckets[i]
            i += direction
        return None, None

    exit_level = nearest(silent_from - 1, -1)
    entry_level = nearest(max(silent_to, silent_from), +1)
    return {
        **join,
        "window": (win_start, win_end),
        "rows": rows,
        "silence_seconds": run * BUCKET,
        "exit": exit_level,
        "entry": entry_level,
    }


def fmt_db(level):
    return "  -inf" if level == float("-inf") else f"{level:6.1f}"


def print_report(results, measured_file, stream=None):
    stream = stream or sys.stdout
    print(f"# transitions on {measured_file}", file=stream)
    print(f"# all times PROGRAMME (megacut) clock; bucket = {BUCKET:.1f}s RMS, "
          f"dBFS; silence = <= {SILENCE_DB:.0f} dB", file=stream)
    for r in results:
        print(f"\n## {r['kind'].upper()}  {r['label']}", file=stream)
        print(f"   silent stretch (slide or boundary): "
              f"{r['silent_start']:.3f} -> {r['silent_end']:.3f}", file=stream)
        for second, level in r["rows"]:
            mark = "  " if level > SILENCE_DB else " *"
            print(f"   {second:6d}s  {fmt_db(level)}{mark}", file=stream)
        out_s, out_l = r["exit"]
        in_s, in_l = r["entry"]
        print(f"   => silence run: {r['silence_seconds']:.0f} s", file=stream)
        if out_s is not None:
            print(f"   => outgoing ({r['out_label']}): last non-silent "
                  f"second {out_s}s at {fmt_db(out_l)} dB", file=stream)
        if in_s is not None and r["in_label"] is not None:
            print(f"   => incoming ({r['in_label']}): first non-silent "
                  f"second {in_s}s at {fmt_db(in_l)} dB", file=stream)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("plan", help="JSON assembly plan (the programme's order)")
    ap.add_argument("--measure", metavar="FILE", required=True,
                    help="the BUILT programme to listen to; nothing is written")
    ap.add_argument("--pre", type=float, default=PRE,
                    help="seconds of context before each join")
    ap.add_argument("--post", type=float, default=POST,
                    help="seconds of context after each join")
    args = ap.parse_args(argv)

    plan = megacut.load_plan(args.plan, require_sources=False)
    measured = Path(args.measure)
    if not measured.exists():
        raise SystemExit(f"nothing to measure: {measured} does not exist")
    rate, channels = probe_audio_shape(measured)
    results = [measure_join(measured, j, rate, channels, decode_fn=decode,
                            pre=args.pre, post=args.post)
               for j in find_joins(plan)]
    print_report(results, measured)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
