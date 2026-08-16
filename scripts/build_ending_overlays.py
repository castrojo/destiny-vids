#!/usr/bin/env python3
"""Burn the underwater closing passage into a movement-5 DERIVATIVE.

    python3 scripts/build_ending_overlays.py --print-command
    python3 scripts/build_ending_overlays.py

What this builds
----------------
The seven closing lines of ``stories/megacut/ending-cards.json``
(``underwater``) revealed one at a time over the underwater pullback:
``renders/perfume-5-ending.mp4``.

Why a DERIVATIVE, not a treatment on the clean movement
-------------------------------------------------------
``renders/perfume-5.mp4`` stays clean -- the thread's own rule
(``stories/00-perfume-thread.json``, ``_clean_renders``): no fades, no
overlays, no cards, because the dinosaur pass edits these files. The coda is
a separately named output, recorded on the movement as ``ending_derivative``.

And it is rebuilt DIRECTLY FROM THE ORIGINAL SOURCE -- the same 389.800 in
point, the same 117.221 s window, the same ``media/`` .mkv -- rather than by
re-encoding the clean render. Overlaying onto ``perfume-5.mp4`` would stack a
second x264 generation on the picture before megacut assembly; encoding once
from the source keeps the derivative at the same generation as the clean
movement. The encode settings are exactly ``build_interludes.py``'s:
native-width pad into the 16:9 delivery frame, delivery FPS, BT.709 written
into the VUI, closed-GOP x264, one ``-t``.

Audio is FLAC and untouched
---------------------------
The same audio window as the clean movement, decoded once to FLAC s32 at
48 kHz: no fades, no gain, no normaliser, no EQ, no compression
(docs/skills/audio/SKILL.md). Decoded PCM is bit-identical to the clean
movement's.

The plates
----------
Each ``renders/ending/cards/plate_<id>.png`` is REQUIRED -- a missing plate
is a failed render, not a silently skipped line. Each still is opened at the
delivery frame rate, alpha-faded in and out entirely INSIDE its half-open
``[at, at + dur)`` window (``gte(t,...)*lt(t,...)``; ``between()`` includes
its upper bound and would ghost the previous line onto the next line's first
frame), and overlaid in manifest order.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import conform  # noqa: E402
from tools.render import find_ffmpeg  # noqa: E402

THREAD = REPO / "stories" / "00-perfume-thread.json"
MANIFEST = REPO / "stories" / "megacut" / "ending-cards.json"
CARDS = REPO / "renders" / "ending" / "cards"
MOVEMENT_ID = "perfume-5"
SECTION = "underwater"

FPS = conform.DELIVERY.fps
W, H = conform.DELIVERY.width, conform.DELIVERY.height


def load_thread(path=THREAD):
    return json.loads(Path(path).read_text())


def find_movement(spec, movement_id=MOVEMENT_ID):
    for movement in spec["movements"]:
        if movement["id"] == movement_id:
            return movement
    raise SystemExit(f"no movement with id {movement_id!r} in the thread")


def underwater_cards(doc, section=SECTION):
    by_id = {plate["id"]: plate for plate in doc["plates"]}
    return [by_id[id_] for id_ in doc[section]["plate_ids"]]


def card_path(cards_dir, card):
    return Path(cards_dir) / f"plate_{card['id']}.png"


def missing_cards(doc, cards_dir, section=SECTION):
    """Every plate PNG the render needs but does not have. A missing plate
    blocks the render -- a line that silently never appears is exactly the
    failure 'each line replaces the previous one' exists to prevent."""
    return [card_path(cards_dir, card)
            for card in underwater_cards(doc, section)
            if not card_path(cards_dir, card).exists()]


def filtergraph(spec, movement, cards):
    """The clean movement's own chain, then the plates in manifest order.

    Base, pad, clock and audio are byte-for-byte ``build_interludes.py``'s
    movement chain, so the derivative differs from the clean render ONLY in
    the overlaid lines. Each still is shifted onto the output clock
    (``setpts=PTS-STARTPTS+at/TB``) so its alpha fades are expressed in
    output time, and gated half-open so two lines never share a frame.
    """
    src_h = int(spec["source_height"])
    pad_y = (H - src_h) // 2
    dur = float(movement["duration"])

    parts = [f"[0:v]pad={W}:{H}:0:{pad_y}:color=black,setsar=1,"
             f"fps={FPS},format=yuv420p,trim=0:{dur:.3f},"
             f"setpts=PTS-STARTPTS[base]"]
    audio = (f"[0:a]atrim=0:{dur:.3f},asetpts=PTS-STARTPTS,"
             f"aresample=48000[aout]")

    prev = "base"
    for i, card in enumerate(cards):
        at = float(card["at"])
        end = at + float(card["dur"])
        fade_in = float(card.get("fade_in", 0))
        fade_out = float(card.get("fade_out", 0))
        chain = f"[{i + 1}:v]format=rgba,setpts=PTS-STARTPTS+{at:.3f}/TB"
        if fade_in:
            chain += f",fade=t=in:st={at:.3f}:d={fade_in:.3f}:alpha=1"
        if fade_out:
            chain += (f",fade=t=out:st={end - fade_out:.3f}:"
                      f"d={fade_out:.3f}:alpha=1")
        chain += f"[ov{i}]"
        parts.append(chain)
        parts.append(f"[{prev}][ov{i}]overlay=0:0:eof_action=pass:"
                     f"enable='gte(t,{at:.3f})*lt(t,{end:.3f})'[v{i}]")
        prev = f"v{i}"

    parts.append(f"[{prev}]format=yuv420p[vout]")
    return ";".join(parts) + ";" + audio


def command(doc, thread_path, cards_dir, out, ffmpeg=None):
    spec = load_thread(thread_path)
    movement = find_movement(spec)
    cards = underwater_cards(doc)
    source = REPO / spec["source"]

    inputs = []
    for card in cards:
        end = float(card["at"]) + float(card["dur"])
        inputs += ["-loop", "1", "-framerate", FPS,
                   "-t", f"{end:.3f}", "-i", str(card_path(cards_dir, card))]

    return [
        *(ffmpeg or find_ffmpeg()),
        "-hide_banner", "-y",
        # Accurate seek, as in build_interludes.py: -ss before -i decodes
        # from the preceding keyframe, so the in point is the frame the
        # manifest names, not the nearest keyframe to it.
        "-ss", f"{float(movement['in']):.3f}",
        "-i", str(source),
        *inputs,
        "-filter_complex", filtergraph(spec, movement, cards),
        "-map", "[vout]", "-map", "[aout]",
        *conform.video_encode_args(),
        "-c:a", "flac", "-sample_fmt", "s32",
        "-t", f"{float(movement['duration']):.3f}",
        "-movflags", "+faststart",
        str(out),
    ]


def _ffmpeg_for_printing():
    """The ffmpeg to print when we are only PRINTING.

    `--print-command` exists to be read, diffed and pasted, and CI has no
    H.264-capable ffmpeg -- so resolving one is a precondition of RUNNING the
    command, never of showing it. Falling back to the bare name keeps the
    offline suite offline instead of making a print depend on an encoder.
    """
    try:
        return find_ffmpeg()
    except Exception:
        return ["ffmpeg"]


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", default=str(MANIFEST),
                    help="the authored ending record")
    ap.add_argument("--thread", default=str(THREAD),
                    help="the Perfume thread manifest")
    ap.add_argument("--cards-dir", default=str(CARDS),
                    help="where the rendered plate PNGs live")
    ap.add_argument("--out", default=str(REPO / "renders" /
                                         "perfume-5-ending.mp4"))
    ap.add_argument("--print-command", action="store_true",
                    help="print the ffmpeg call and exit")
    args = ap.parse_args(argv)

    doc = json.loads(Path(args.manifest).read_text())
    spec = load_thread(args.thread)
    movement = find_movement(spec)

    source = REPO / spec["source"]
    if not source.exists():
        sys.exit(f"footage is never committed; missing: {source}")
    missing = missing_cards(doc, args.cards_dir)
    if missing:
        sys.exit("missing rendered ending plates: "
                 + ", ".join(str(p) for p in missing))

    cmd = command(doc, args.thread, args.cards_dir, args.out,
                  ffmpeg=_ffmpeg_for_printing() if args.print_command
                  else None)
    if args.print_command:
        print(" ".join(cmd))
        return 0
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(cmd, check=True)
    print(f"wrote {out} ({movement['duration']:.3f} s, "
          f"{len(underwater_cards(doc))} underwater lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
