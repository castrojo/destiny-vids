#!/usr/bin/env python3
"""Burn a movement's plates into its DERIVATIVE -- overlays, never the clean render.

    python3 scripts/build_ending_overlays.py --print-command
    python3 scripts/build_ending_overlays.py
    python3 scripts/build_ending_overlays.py --movement perfume-4 --print-command

What this builds
----------------
Movement 5: the eleven closing lines of ``stories/megacut/ending-cards.json``
(``underwater``) revealed one at a time over the underwater pullback:
``renders/perfume-5-ending.mp4``.

Movement 4: Rafael's early ``chat_wolf`` cue followed by the six ``chat``
lines over the whale-skeleton shot, all from
``stories/00-perfume-4-plates.json`` into ``renders/perfume-4-overlays.mp4``.
This is the generalisation the movement-5 pattern predicted: ONE derivative
per movement, and movement 4's ALSO composes the movement's own
``replacements`` in the same encode -- the base chain is
``build_interludes.video_chain`` itself, so a naive copy of the old pattern
(plates over a bare base) can never ship the chat WITHOUT the wallpapers.
One source read, one encode: swaps and words together.

Which movement, which plates
----------------------------
``--movement`` names the movement; its ``ending_derivative`` block in the
thread record supplies the defaults: ``out_file`` for ``--out``,
``overlay_manifest`` for ``--manifest``, ``overlay_section`` for
``--section``, and the optional ``plates_dir`` for ``--cards-dir``.
``overlay_section`` may be one section name or an ordered list; list order is
input and overlay order in the same one-source encode. Every
default still resolves to the movement-5 values above, so an unflagged run
is byte-for-byte the command this script has always printed.

Why a DERIVATIVE, not a treatment on the clean movement
-------------------------------------------------------
``renders/perfume-5.mp4`` stays clean -- the thread's own rule
(``stories/00-perfume-thread.json``, ``_clean_renders``): no fades, no
overlays, no cards, because the dinosaur pass edits these files. The coda is
a separately named output, recorded on the movement as ``ending_derivative``.

And it is rebuilt DIRECTLY FROM THE ORIGINAL SOURCE -- the same in point,
the same window, the same ``media/`` .mkv -- rather than by re-encoding the
clean render. Overlaying onto the clean render would stack a second x264
generation on the picture before megacut assembly; encoding once from the
source keeps the derivative at the same generation as the clean movement.
The encode settings are exactly ``build_interludes.py``'s: native-width pad
into the 16:9 delivery frame, delivery FPS, BT.709 written into the VUI,
closed-GOP x264, one ``-t``.

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
from tools import chapter_md  # noqa: E402
from tools.render import ffmpeg_for_printing, find_ffmpeg  # noqa: E402
from scripts import build_interludes  # noqa: E402

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
    sections = [section] if isinstance(section, str) else list(section)
    by_id = {plate["id"]: plate for plate in doc["plates"]}
    cards = []
    for sec in sections:
        cards.extend(by_id[id_] for id_ in doc[sec]["plate_ids"])
    return cards


def card_path(cards_dir, card):
    return Path(cards_dir) / f"plate_{card['id']}.png"


def missing_cards(doc, cards_dir, section=SECTION):
    """Every plate PNG the render needs but does not have. A missing plate
    blocks the render -- a line that silently never appears is exactly the
    failure 'each line replaces the previous one' exists to prevent."""
    return [card_path(cards_dir, card)
            for card in underwater_cards(doc, section)
            if not card_path(cards_dir, card).exists()]


def filtergraph(spec, movement, cards, repls=()):
    """The clean movement's own chain, then the plates in manifest order.

    The base IS ``build_interludes.video_chain`` -- with the movement's
    replacements composed in when it carries any -- so the derivative
    differs from the clean render ONLY in the overlaid lines, and the
    swaps and the plates can never ship in separate encodes. Each still is
    shifted onto the output clock (``setpts=PTS-STARTPTS+at/TB``) so its
    alpha fades are expressed in output time, and gated half-open so two
    lines never share a frame.
    """
    dur = float(movement["duration"])

    parts = [build_interludes.video_chain(spec, movement, repls,
                                          out_label="base")]
    audio = (f"[0:a]atrim=0:{dur:.3f},asetpts=PTS-STARTPTS,"
             f"aresample=48000[aout]")

    # Plate inputs are numbered after the source (0) and the artwork loops.
    first_plate = 1 + build_interludes.replacement_input_count(repls)
    prev = "base"
    for i, card in enumerate(cards):
        at = float(card["at"])
        end = at + float(card["dur"])
        fade_in = float(card.get("fade_in", 0))
        fade_out = float(card.get("fade_out", 0))
        chain = f"[{i + first_plate}:v]format=rgba,setpts=PTS-STARTPTS+{at:.3f}/TB"
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


def command(doc, thread_path, cards_dir, out, ffmpeg=None,
            movement_id=MOVEMENT_ID, section=SECTION, repls=None):
    spec = load_thread(thread_path)
    movement = find_movement(spec, movement_id)
    cards = underwater_cards(doc, section)
    if repls is None:
        repls = build_interludes.usable_replacements(movement)
    source = REPO / spec["source"]

    # The artwork loops come first: the filtergraph numbers its plate inputs
    # after them, and the two orders must be the same list.
    inputs = list(build_interludes._replacement_inputs(repls))
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
        "-filter_complex", filtergraph(spec, movement, cards, repls),
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
    ap.add_argument("--movement", default=MOVEMENT_ID,
                    help="the movement whose derivative to build")
    ap.add_argument("--manifest", default=None,
                    help="the authored plate record (default: the movement's "
                         "ending_derivative overlay_manifest)")
    ap.add_argument("--thread", default=str(THREAD),
                    help="the Perfume thread manifest")
    ap.add_argument("--section", default=None,
                    help="the plate_ids section in the manifest (default: the "
                         "movement's ending_derivative overlay_section)")
    ap.add_argument("--cards-dir", default=None,
                    help="where the rendered plate PNGs live (default: the "
                         "movement's ending_derivative plates_dir, else "
                         f"{CARDS})")
    ap.add_argument("--out", default=None,
                    help="the derivative to write (default: the movement's "
                         "ending_derivative out_file)")
    ap.add_argument("--print-command", action="store_true",
                    help="print the ffmpeg call and exit")
    args = ap.parse_args(argv)

    spec = load_thread(args.thread)
    movement = find_movement(spec, args.movement)
    deriv = movement.get("ending_derivative")
    if deriv is None and (args.manifest is None or args.out is None):
        sys.exit(f"{movement['id']} declares no ending_derivative in "
                 f"{args.thread}; pass --manifest and --out explicitly")

    manifest = Path(args.manifest or REPO / deriv["overlay_manifest"])
    section = args.section or (deriv or {}).get("overlay_section", SECTION)
    cards_dir = Path(args.cards_dir
                     or (deriv or {}).get("plates_dir") or CARDS)
    if not cards_dir.is_absolute():
        # ffmpeg may run inside a container whose CWD is not the repo, so
        # every path handed to it is anchored -- a repo-relative plates_dir
        # resolves here, not over there.
        cards_dir = REPO / cards_dir
    out = Path(args.out or REPO / deriv["out_file"])

    for note in chapter_md.sync_manifest(manifest):
        print(f"chapter: {note}", file=sys.stderr)
    doc = json.loads(manifest.read_text())

    source = REPO / spec["source"]
    if not source.exists():
        sys.exit(f"footage is never committed; missing: {source}")
    missing = missing_cards(doc, cards_dir, section)
    if missing:
        sys.exit("missing rendered ending plates: "
                 + ", ".join(str(p) for p in missing))

    notes = []
    repls = build_interludes.usable_replacements(movement, notes)
    cmd = command(doc, args.thread, cards_dir, out,
                  ffmpeg=ffmpeg_for_printing() if args.print_command
                  else None,
                  movement_id=args.movement, section=section, repls=repls)
    for note in notes:
        print(f"note: {note}", file=sys.stderr)
    if args.print_command:
        print(" ".join(cmd))
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(cmd, check=True)
    section_label = section if isinstance(section, str) else "+".join(section)
    print(f"wrote {out} ({movement['duration']:.3f} s, "
          f"{len(underwater_cards(doc, section))} {section_label} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
