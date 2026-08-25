#!/usr/bin/env python3
"""Build the frame-exact, video-only mission pause before the asteroid."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import conform
from tools.render import ffmpeg_for_printing, find_ffmpeg

MANIFEST = REPO / "stories" / "megacut" / "ending-cards.json"
CARDS = REPO / "renders" / "ending" / "cards"
OUT = REPO / "renders" / "ending" / "mission-pause.mp4"
FPS = 60000 / 1001


def frame_count(doc):
    spec = doc["pause"]
    by_id = {plate["id"]: plate for plate in doc["plates"]}
    return (
        sum(by_id[id_]["frames"] for id_ in spec["plate_ids"])
        + spec["gap_frames"] * (len(spec["plate_ids"]) - 1)
        + spec["black_hold_frames"]
    )


def duration(doc):
    return round(frame_count(doc) / FPS, 6)


def command(doc, cards_dir, out, ffmpeg=None):
    spec = doc["pause"]
    by_id = {plate["id"]: plate for plate in doc["plates"]}
    cards = [by_id[id_] for id_ in spec["plate_ids"]]
    paths = [Path(cards_dir) / f"plate_{card['id']}.png" for card in cards]
    missing = [path for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing ending card: {missing[0]}")

    fade = spec["fade_frames"] / FPS
    graph = []
    labels = []
    for i, card in enumerate(cards):
        frames = card["frames"]
        out_start = (frames - spec["fade_frames"]) / FPS
        graph.append(
            f"[{i}:v]scale=1920:1080,setsar=1,fps={spec['fps']},"
            f"format=yuv420p,trim=end_frame={frames},setpts=PTS-STARTPTS,"
            f"fade=t=in:st=0:d={fade:.6f},"
            f"fade=t=out:st={out_start:.6f}:d={fade:.6f}[card{i}]"
        )
        labels.append(f"[card{i}]")
        black_frames = (
            spec["black_hold_frames"] if i == len(cards) - 1
            else spec["gap_frames"]
        )
        graph.append(
            f"color=c=black:s=1920x1080:r={spec['fps']},"
            f"trim=end_frame={black_frames},setpts=PTS-STARTPTS[black{i}]"
        )
        labels.append(f"[black{i}]")
    graph.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0[vout]")

    return [
        *(ffmpeg or find_ffmpeg()),
        "-hide_banner", "-y",
        *sum((["-loop", "1", "-framerate", spec["fps"], "-i", str(path)]
              for path in paths), []),
        "-filter_complex", ";".join(graph),
        "-map", "[vout]",
        "-frames:v", str(frame_count(doc)),
        *conform.video_encode_args(),
        "-an", "-movflags", "+faststart", str(out),
    ]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", default=str(MANIFEST))
    ap.add_argument("--cards-dir", default=str(CARDS))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--print-command", action="store_true")
    ap.add_argument("--local", action="store_true",
                    help="encode on THIS host even when the farm cluster is "
                         "reachable (the escape hatch; the encode runs under "
                         "tools.farm.run_capped_local's memory cap)")
    args = ap.parse_args(argv)

    doc = json.loads(Path(args.manifest).read_text())
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = command(doc, args.cards_dir, out,
                  ffmpeg=ffmpeg_for_printing() if args.print_command
                  else None)
    if args.print_command:
        print(" ".join(cmd))
        return 0
    # Remote by default (AGENTS.md): the card concat encode runs on the farm
    # when the cluster answers; a local run is the stated, memory-capped
    # fallback.
    from tools import farm
    farm.run_encode(cmd,
                    inputs=[Path(cmd[i + 1]) for i, tok in enumerate(cmd)
                            if tok == "-i"],
                    out=out, local=args.local,
                    expected_duration=duration(doc))
    print(f"wrote {out} ({frame_count(doc)} frames, video only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
