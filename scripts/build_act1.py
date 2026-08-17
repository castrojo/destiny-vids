#!/usr/bin/env python3
"""Rebuild act I (the hero cold open) — the megacut's one act with no committed builder.

The chain, established 2026-07-15 from the record (`megacut.json`'s
`_sources.hero`, the shipped master's measured streams, and the manifest):

  1. `renders/title-cover.jpg` comes from `media/summit/group-007.jpg` via
     `scripts/build_summit_plates.py`'s detail-measured crop and grade
     (skipped when the jpg already exists — the crop window is a recorded
     taste call, not something a rebuild silently re-makes).
  2. `cards/render-cards.mjs` renders the full-frame cards (the title-cover
     photograph) into `renders/plates-01-hero/`. It needs the sibling website
     checkout for playwright, like every card stage — skipped with a warning
     when that checkout is absent, because an already-rendered
     `plate_title-cover.png` in the plates dir is still burnable.
  3. `tools/plate.py render` renders the Guardian plates into the same dir.
  4. ffmpeg trims the Into the Light capture: `-ss 2.0` on BOTH inputs, so
     with input seeking the `-t 111.55` output duration lands the window at
     2.0 -> 113.55 exactly as `_sources.hero` records. Video is x264
     crf 14; audio is the capture's OFFICIAL 251 Opus rung — Ikora's VO
     included — decoded to FLAC, picture-aligned (both legs `-ss 2.0`).
     An earlier delivery note claimed the without-dialogue capture with a
     +1.979 s offset; the rebuilt audio cross-correlates with the shipped
     master at lag 0.0, ncorr 1.0, so the record is what this builds.
  5. `tools/plate.py burn` stamps every manifest entry over the trim in one
     pass: x264 crf 18, preset medium, audio stream-copied.

  python3 scripts/build_act1.py                  # rebuild everything
  python3 scripts/build_act1.py --print-command  # print the chain, run nothing
  python3 scripts/build_act1.py --skip-encode    # cards and plates only
  python3 scripts/build_act1.py --farm           # encode legs on the farm

The encode is local by default (`tools.render.find_ffmpeg()` — brew first),
matching the other committed builders. `--farm` submits each encode leg to
the farm cluster instead (`tools.farm.run_ffmpeg_on_cluster`, which stages
the inputs and fetches the output back to the same local path). Farm or not,
resolve ffmpeg to a single binary — `DESTINY_FFMPEG=/home/linuxbrew/.linuxbrew/bin/ffmpeg`
— because the farm rewrites argv[0] only, and a `podman exec ...` prefix
would leak its middle tokens into the pod's argv.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import plate  # noqa: E402
from tools import render  # noqa: E402

MANIFEST = "stories/megacut/megacut-hero-plates.json"
PLATES_DIR = "renders/plates-01-hero"
COVER_ART = "renders/title-cover.jpg"
COVER_SOURCE = "media/summit/group-007.jpg"
TRIM = "renders/megacut-01-hero-trim.mp4"
MASTER = "renders/megacut-01-hero.mp4"
# megacut.json `_sources.hero`: trim 2.0 -> 113.55 of the Into the Light
# capture, official audio (the plain 251 Opus rung — NOT 251-drc).
VIDEO_SRC = "media/yt_into_the_light_cinematic.mkv"
AUDIO_SRC = "media/yt_into_the_light_cinematic-audio.webm"
TRIM_START = 2.0
TRIM_END = 113.55


def trim_command(ffmpeg):
    return [
        *ffmpeg, "-y",
        "-ss", f"{TRIM_START}", "-i", str(REPO_ROOT / VIDEO_SRC),
        "-ss", f"{TRIM_START}", "-i", str(REPO_ROOT / AUDIO_SRC),
        "-map", "0:v", "-map", "1:a",
        "-t", f"{TRIM_END - TRIM_START:.2f}",
        "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p",
        "-c:a", "flac",
        str(REPO_ROOT / TRIM),
    ]


def cover_art():
    """Render the title-cover photograph with the summit detail crop/grade.

    Skipped when the jpg exists: the crop window was a taste call and a
    rebuild must not silently re-make it.
    """
    if (REPO_ROOT / COVER_ART).exists():
        print(f"cover art: {COVER_ART} exists, kept")
        return
    from scripts.build_summit_plates import build
    written = build(COVER_SOURCE, COVER_ART)
    print(f"cover art: rendered {written}")


def render_cards():
    """Full-frame cards need the sibling website checkout (playwright)."""
    website_modules = Path.home() / "src/website/node_modules"
    if not website_modules.is_dir():
        print(
            "cards: ~/src/website/node_modules not found — skipping the card "
            f"render (an already-rendered {PLATES_DIR}/plate_title-cover.png "
            "is still burnable; render the cards where playwright is "
            "installed)",
            file=sys.stderr,
        )
        return
    cmd = ["node", "cards/render-cards.mjs",
           "--manifest", MANIFEST, "--out-dir", PLATES_DIR]
    subprocess.run(cmd, check=True, cwd=REPO_ROOT,
                   env={**os.environ, "NODE_PATH": str(website_modules)})


def _farm_runner(cmd, inputs, out, expected_duration):
    from tools import farm

    def run(argv):
        farm.run_ffmpeg_on_cluster(
            argv,
            inputs=[REPO_ROOT / p for p in inputs],
            out=REPO_ROOT / out,
            expected_duration=expected_duration,
        )

    return run


def build_act1(skip_encode=False, use_farm=False):
    ffmpeg = render.find_ffmpeg()
    print(f"ffmpeg: {' '.join(ffmpeg)}" + (" (farm legs)" if use_farm else ""))

    cover_art()
    render_cards()

    entries = plate.load_manifest(REPO_ROOT / MANIFEST)
    written = plate.render_all(entries, REPO_ROOT / PLATES_DIR)
    print(f"plates: {len(written)} rendered (full-frame cards come from "
          "cards/render-cards.mjs)")

    if skip_encode:
        print("--skip-encode: trim and burn not run")
        return

    duration = TRIM_END - TRIM_START
    trim_cmd = trim_command(ffmpeg)
    if use_farm:
        _farm_runner(trim_cmd, [VIDEO_SRC, AUDIO_SRC], TRIM, duration)(trim_cmd)
    else:
        subprocess.run(trim_cmd, check=True, cwd=REPO_ROOT)

    runner = None
    if use_farm:
        # The farm stages exact argv tokens, so the burn leg lists the plate
        # PNGs themselves, not their directory.
        burn_inputs = [TRIM] + [
            str(Path(PLATES_DIR) / f"plate_{u['id']}.png")
            for u in plate._burn_units(entries)
        ]
        runner = _farm_runner(None, burn_inputs, MASTER, duration)
    plate.burn(
        REPO_ROOT / TRIM,
        entries,
        REPO_ROOT / PLATES_DIR,
        REPO_ROOT / MASTER,
        ffmpeg=ffmpeg,
        runner=runner,
    )
    print(f"wrote {MASTER}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--print-command", action="store_true",
                        help="print the chain and exit (runs nothing)")
    parser.add_argument("--skip-encode", action="store_true",
                        help="stop after the cards and plates")
    parser.add_argument("--farm", action="store_true",
                        help="submit the encode legs to the farm cluster")
    args = parser.parse_args()

    if args.print_command:
        print(" ".join(trim_command(["<ffmpeg>"])))
        print("python3 tools/plate.py burn "
              f"{TRIM} --manifest {MANIFEST} --plates-dir {PLATES_DIR} "
              f"{MASTER}   # x264 crf 18, -c:a copy")
        return

    build_act1(skip_encode=args.skip_encode, use_farm=args.farm)


if __name__ == "__main__":
    main()
