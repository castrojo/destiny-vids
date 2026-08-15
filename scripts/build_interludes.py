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
no limiter, no EQ, no gain (docs/skills/audio/SKILL.md). The
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


ARTWORK_DIR = REPO_ROOT / "renders" / "artwork"


def load():
    return json.loads(MANIFEST.read_text())


def art_path(name):
    """One cached wallpaper frame, or ``None`` if it was never fetched.

    Missing art DEGRADES: the replacement that wanted it is skipped and the
    source shot plays, which is a note in the log rather than a failed render.
    """
    path = ARTWORK_DIR / f"{name}.png"
    return path if path.exists() else None


def usable_replacements(movement, log=None):
    """The movement's replacements that have all of their artwork cached.

    Replacements are returned in play order and are checked for overlap: two
    that overlap would make the concat arithmetic silently wrong, which is
    exactly the class of bug duration-locking exists to prevent.
    """
    out = []
    last_end = 0.0
    for repl in movement.get("replacements", []):
        wanted = list(repl["art"]) + ([repl["flash"]["art"]]
                                      if repl.get("flash") else [])
        missing = [n for n in wanted if art_path(n) is None]
        if missing:
            if log is not None:
                log.append(f"{repl['id']}: skipped, artwork not cached: "
                           f"{', '.join(missing)}")
            continue
        at, dur = float(repl["at"]), float(repl["dur"])
        if at < last_end:
            raise SystemExit(
                f"{repl['id']}: starts at {at:.3f} but the previous "
                f"replacement runs to {last_end:.3f} -- replacements must not "
                "overlap, or the concat arithmetic is wrong")
        last_end = at + dur
        out.append(repl)
    if last_end > float(movement["duration"]) + 1e-6:
        raise SystemExit(
            f"a replacement runs to {last_end:.3f}, past the movement's "
            f"{movement['duration']:.3f}")
    return out


# THE ARTWORK IS NEVER STRETCHED AND NEVER CROPPED.
#
# Two faults were shipped here in one pass and the owner caught both:
# ``scale=1920:804`` squashed every wallpaper vertically to fit the film's
# scope window, and the fetcher had already centre-cropped them to 16:9 and
# downscaled them to 1920x1080 first -- *"YOU ARE FUCKING UP THE IMAGES"*, and
# *"why are you using the 10xx versions use the high rez versions"*.
#
# So: art is cached at its published resolution (scripts/fetch_artwork.py) and
# fitted here with ``force_original_aspect_ratio=decrease``, which scales on
# the drawing's OWN aspect and never distorts it, then padded to the delivery
# frame. Letterboxing the difference is the owner's call -- *"letter box is
# fine"* -- and it happens to sit close to the film's own scope bars, because
# most of these wallpapers are ultrawide.
#
# This is also the ONLY resample the artwork gets: master resolution straight
# to the delivery frame, once.
FIT = f"scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos"
PAD = f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black"


def _still_chain(idx, dur, label, letterbox=None):
    """One cached wallpaper as a clip of exactly ``dur``, on the delivery clock.

    Fitted, never stretched; padded, never cropped. See ``FIT`` above.
    """
    return (f"[{idx}:v]{FIT},{PAD},setsar=1,fps={FPS},format=yuv420p,"
            f"trim=0:{dur:.3f},setpts=PTS-STARTPTS[{label}]")


def _replacement_chain(repl, first_input, out_label, letterbox):
    """The filter chain for one replacement, and the inputs it consumes.

    The artwork is laid end to end and **cross-faded**, so a replacement that
    carries several wallpapers reads as one held image turning rather than as
    a slideshow. ``turn_sec`` is the overlap.

    ``xfade`` shortens its output by the transition, so each leg is grown by
    that amount and the whole lands on ``dur`` exactly. Duration-locking is
    the point: the movement's length must not move.
    """
    parts = []
    arts = list(repl["art"])
    dur = float(repl["dur"])
    turn = float(repl.get("turn_sec", 0.0)) if len(arts) > 1 else 0.0
    n = len(arts)

    # n legs, n-1 overlaps: leg = (dur + (n-1)*turn) / n
    leg = (dur + (n - 1) * turn) / n
    labels = []
    for i in range(n):
        label = f"{repl['id']}_a{i}".replace("-", "_")
        parts.append(_still_chain(first_input + i, leg, label, letterbox))
        labels.append(label)

    cur = labels[0]
    for i in range(1, n):
        nxt = f"{repl['id']}_x{i}".replace("-", "_")
        offset = leg * i - turn * i
        parts.append(f"[{cur}][{labels[i]}]xfade=transition=fade:"
                     f"duration={turn:.3f}:offset={offset:.3f}[{nxt}]")
        cur = nxt

    used = n
    flash = repl.get("flash")
    if flash:
        # THE JUMP SCARE IS A CUT, NOT A DISSOLVE. It is overlaid full-frame
        # and opaque, gated by `enable`, so what is underneath is replaced
        # outright for its few frames.
        fl = f"{repl['id']}_f".replace("-", "_")
        fat, fdur = float(flash["at"]), float(flash["dur"])
        parts.append(f"[{first_input + n}:v]{FIT},{PAD},setsar=1,fps={FPS},"
                     f"format=yuv420p,trim=0:{fdur:.3f},setpts=PTS-STARTPTS,"
                     f"tpad=start_duration={fat:.3f}:start_mode=add:"
                     f"color=black[{fl}]")
        parts.append(f"[{cur}][{fl}]overlay=eof_action=pass:"
                     f"enable='between(t,{fat:.3f},{fat + fdur:.3f})'"
                     f"[{out_label}]")
        used += 1
    else:
        parts.append(f"[{cur}]null[{out_label}]")

    return parts, used


def _replacement_inputs(repls):
    """The ``-loop 1 -i art.png`` arguments, in the order the graph expects."""
    args = []
    for repl in repls:
        names = list(repl["art"])
        if repl.get("flash"):
            names.append(repl["flash"]["art"])
        for name in names:
            args += ["-loop", "1", "-framerate", str(FPS),
                     "-t", f"{float(repl['dur']):.3f}", "-i", str(art_path(name))]
    return args


def filtergraph(spec, movement, repls=()):
    """One movement: trimmed, padded to 16:9, put on the delivery clock.

    ``trim`` runs on the DECODED stream and the input is opened with an
    accurate ``-ss``, so the in point is frame-exact rather than snapped to
    the nearest keyframe -- the distinction docs/rendering.md records.

    WITH REPLACEMENTS the picture is CONCATENATED rather than overlaid: the
    source's own segments and the replacement clips are laid end to end in
    order. Concatenation is what makes the arithmetic checkable -- every piece
    has a stated length and they must sum to the movement's duration -- where
    an overlay would hide a mistimed shot behind a correct-looking runtime.

    THE AUDIO IS NEVER CUT. It is taken whole from the source across the whole
    movement, so the song plays straight through a replaced shot. That is the
    whole point of the thread: one continuous performance the acts interrupt.
    """
    src_h = int(spec["source_height"])
    pad_y = (H - src_h) // 2
    dur = float(movement["duration"])

    base = (f"[0:v]pad={W}:{H}:0:{pad_y}:color=black,setsar=1,"
            f"fps={FPS},format=yuv420p")
    audio = (f"[0:a]atrim=0:{dur:.3f},asetpts=PTS-STARTPTS,"
             f"aresample=48000[aout]")

    if not repls:
        return f"{base},trim=0:{dur:.3f},setpts=PTS-STARTPTS[vout];{audio}"

    # The source survives in the gaps between replacements.
    keeps, cursor = [], 0.0
    for repl in repls:
        at = float(repl["at"])
        if at - cursor > 1e-6:
            keeps.append((cursor, at))
        cursor = at + float(repl["dur"])
    if dur - cursor > 1e-6:
        keeps.append((cursor, dur))

    parts = [f"{base},split={len(keeps)}" + "".join(f"[k{i}]"
                                                    for i in range(len(keeps)))]
    for i, (a, b) in enumerate(keeps):
        parts.append(f"[k{i}]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS[s{i}]")

    next_input = 1
    repl_labels = {}
    for repl in repls:
        label = f"{repl['id']}_v".replace("-", "_")
        chain, used = _replacement_chain(repl, next_input, label,
                                         (src_h, pad_y))
        parts += chain
        repl_labels[repl["id"]] = label
        next_input += used

    # Interleave the kept source segments and the replacements, in time order.
    order, ki, cursor = [], 0, 0.0
    for repl in repls:
        if float(repl["at"]) - cursor > 1e-6:
            order.append(f"[s{ki}]"); ki += 1
        order.append(f"[{repl_labels[repl['id']]}]")
        cursor = float(repl["at"]) + float(repl["dur"])
    if dur - cursor > 1e-6:
        order.append(f"[s{ki}]")

    parts.append("".join(order) + f"concat=n={len(order)}:v=1:a=0[vout]")
    return ";".join(parts) + ";" + audio


def command(spec, movement, repls=()):
    source = REPO_ROOT / spec["source"]
    out = REPO_ROOT / movement["out_file"]
    return find_ffmpeg() + [
        "-hide_banner", "-y",
        # Accurate seek: -ss BEFORE -i is fast, and modern ffmpeg decodes from
        # the preceding keyframe rather than snapping the cut to it, so the
        # in point below is the frame the manifest names.
        "-ss", f"{float(movement['in']):.3f}",
        "-i", str(source),
        *_replacement_inputs(repls),
        "-filter_complex", filtergraph(spec, movement, repls),
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
    notes = []
    for movement in movements:
        repls = usable_replacements(movement, notes)
        argv_ff = command(spec, movement, repls)
        if args.print_command:
            print(" ".join(argv_ff))
            continue
        out = REPO_ROOT / movement["out_file"]
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(argv_ff, check=True)
        built.append({"id": movement["id"], "out": str(out),
                      "in": movement["in"], "out_point": movement["out"],
                      "duration": movement["duration"],
                      "replaced": [r["id"] for r in repls]})

    for note in notes:
        print(f"note: {note}", file=sys.stderr)
    if built:
        print(json.dumps(built, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
