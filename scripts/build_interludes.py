#!/usr/bin/env python3
"""Cut the Perfume thread's movements 2-5 out of their source, clean.

    python3 scripts/build_interludes.py --print-command   # the ffmpeg calls, no render
    python3 scripts/build_interludes.py                   # all four
    python3 scripts/build_interludes.py --only perfume-3  # one of them

What this builds
----------------
Nightwish's **"Perfume Of The Timeless"** (``oHCaZmIzr0o``) plays from the
first frame of the show to the last frame before the credits, and the eight
acts live inside it. Movement 1 is the PROLOGUE, built by
``scripts/build_prologue.py``; movements 2-5 are the rest of the same video,
in source order and without gaps, seated between the acts. The record is
``stories/00-perfume-thread.json`` and every timecode in it was measured off
the file rather than taken from the owner's round numbers.

Why these come out CLEAN
------------------------
No fades, no overlays, no cards. Two reasons, and they point the same way:

* This repo puts join treatment in the megacut plan, in act-film time
  (``stories/megacut/megacut.json``, ``_transitions``), so a re-order never
  moves a fade. Burning one here would put the same decision in two places.
* The owner asked for these snippets in ``renders/`` **because they are going
  to be edited** -- "we will be editing them in the future with dino artwork".
  A dinosaur pass wants unfaded picture, not footage with a dip already baked
  into it.

Why these do NOT go to Prod/
----------------------------
``~/Videos/Wolves/Prod`` means "a finished act". These are work-in-progress
elements with a pass still to come, so the megacut plan points at ``renders/``
directly and no ``delivery.json`` key, hardlink, README row or checksum is
created for them. Promoting them is a later decision, not this script's.

Rights
------
Third-party copyrighted -- Nuclear Blast's recording, Nightwish's own official
music video. The rights records are ``music/bed_perfume_of_the_timeless.json``
and ``videos/yt_nightwish_perfume_of_the_timeless.json``, written for the
prologue and not restated here. Like the prologue these are **prototype
output**: the shipping presentation embeds the video rather than re-hosting
it, so no social copy is ever cut from them.

Picture is padded, never scaled
-------------------------------
The source is 1920x804 scope, so it already carries the delivery width at
native pixels; 138 px of black top and bottom seats it in 16:9 without
resampling a single one of them. Same treatment as the prologue, so the thread
looks identical across all five movements.

Audio is FLAC and untouched
---------------------------
Decoded to FLAC s32 and resampled to 48 kHz, and that is all: no normaliser,
no limiter, no EQ, no gain (docs/skills/references/audio-standard.md). The
source is lossy Opus, so this is the best that exists rather than the best
possible -- exactly what act I and the prologue record for the same reason.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import conform  # noqa: E402
from tools.render import find_ffmpeg  # noqa: E402

MANIFEST = REPO_ROOT / "stories" / "00-perfume-thread.json"

FPS = conform.DELIVERY.fps
W, H = conform.DELIVERY.width, conform.DELIVERY.height


def load():
    return json.loads(MANIFEST.read_text())


def filtergraph(spec, movement):
    """One movement: trimmed, padded to 16:9, put on the delivery clock.

    ``trim`` runs on the DECODED stream and the input is opened with an
    accurate ``-ss``, so the in point is frame-exact rather than snapped to
    the nearest keyframe -- the distinction docs/rendering.md records.
    """
    src_h = int(spec["source_height"])
    pad_y = (H - src_h) // 2
    dur = float(movement["duration"])

    video = (f"[0:v]trim=0:{dur:.3f},setpts=PTS-STARTPTS,"
             f"pad={W}:{H}:0:{pad_y}:color=black,setsar=1,"
             f"fps={FPS},format=yuv420p[vout]")
    audio = (f"[0:a]atrim=0:{dur:.3f},asetpts=PTS-STARTPTS,"
             f"aresample=48000[aout]")
    return f"{video};{audio}"


def command(spec, movement):
    source = REPO_ROOT / spec["source"]
    out = REPO_ROOT / movement["out_file"]
    return find_ffmpeg() + [
        "-hide_banner", "-y",
        # Accurate seek: -ss BEFORE -i is fast, and modern ffmpeg decodes from
        # the preceding keyframe rather than snapping the cut to it, so the
        # in point below is the frame the manifest names.
        "-ss", f"{float(movement['in']):.3f}",
        "-i", str(source),
        "-filter_complex", filtergraph(spec, movement),
        "-map", "[vout]", "-map", "[aout]",
        *conform.video_encode_args(),
        "-c:a", "flac", "-sample_fmt", "s32",
        "-t", f"{float(movement['duration']):.3f}",
        "-movflags", "+faststart",
        str(out),
    ]


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--print-command", action="store_true",
                    help="print the ffmpeg calls and exit")
    ap.add_argument("--only", metavar="ID",
                    help="build one movement by its manifest id")
    args = ap.parse_args(argv)

    spec = load()
    source = REPO_ROOT / spec["source"]
    if not source.exists():
        sys.exit(f"footage is never committed; missing: {source}")

    movements = spec["movements"]
    if args.only:
        movements = [m for m in movements if m["id"] == args.only]
        if not movements:
            sys.exit(f"no movement with id {args.only!r} in {MANIFEST}")

    built = []
    for movement in movements:
        argv_ff = command(spec, movement)
        if args.print_command:
            print(" ".join(argv_ff))
            continue
        out = REPO_ROOT / movement["out_file"]
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(argv_ff, check=True)
        built.append({"id": movement["id"], "out": str(out),
                      "in": movement["in"], "out_point": movement["out"],
                      "duration": movement["duration"]})

    if built:
        print(json.dumps(built, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
