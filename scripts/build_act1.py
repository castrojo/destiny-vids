#!/usr/bin/env python3
"""Rebuild act I (the hero cold open) — the megacut's one act with no committed builder.

The chain, established 2026-07-15 from the record (`megacut.json`'s
`_sources.hero`, the shipped master's measured streams, and the manifest):

  1. `renders/title-cover.jpg` comes from `media/summit/group-007.jpg` via
     `scripts/build_summit_plates.py`'s detail-measured crop and grade
     (skipped when the jpg already exists — the crop window is a recorded
     taste call, not something a rebuild silently re-makes).
  2. `cards/render-cards.mjs` renders the full-frame title-cover photograph
     and Platform Wars card into `renders/plates-01-hero/`. Missing or stale
     cards fail closed when the sibling website checkout cannot run Playwright;
     an old PNG is never treated as current merely because it exists.
  3. `tools/plate.py render` renders the Guardian, companion, caption, context,
     and deployment-warning plates into the same directory.
  4. ffmpeg trims the Into the Light picture from 2.0 -> 113.60, including
     the first black frame of the source fade, then holds that terminal black
     frame to make the 118.2 s output. Audio comes from
     `media/yt_into_the_light_without_dialogue.webm`, beginning at
     2.0 + 1.978625 = 3.978625 s; that offset was measured against the prior
     instrumental master at 94974 samples / 48 kHz (ncorr 0.999999920). It is
     decoded once to FLAC with no normalization, EQ, compression, or limiter.
  5. `tools/plate.py burn` stamps every manifest entry over the trim in one
     pass: x264 crf 18, preset medium, audio stream-copied.

  python3 scripts/build_act1.py                  # rebuild everything
  python3 scripts/build_act1.py --print-command  # print the chain, run nothing
  python3 scripts/build_act1.py --skip-encode    # cards and plates only
  python3 scripts/build_act1.py --local          # encode legs on THIS host

The encode is REMOTE by default (AGENTS.md: "always prefer remote encoding
when available"): each encode leg goes to the farm cluster
(`tools.farm.run_ffmpeg_on_cluster`, which stages the inputs and fetches the
output back to the same local path) whenever the cluster answers.
`--local` — or a cluster that does not answer — runs the same argv here
under `tools.farm.run_capped_local`'s memory cap, with the reason printed.
Farm or not, resolve ffmpeg to a single binary —
`DESTINY_FFMPEG=/home/linuxbrew/.linuxbrew/bin/ffmpeg`
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

from tools import freshness  # noqa: E402
from tools import plate  # noqa: E402
from tools import render  # noqa: E402

MANIFEST = "stories/megacut/megacut-hero-plates.json"
PLATES_DIR = "renders/plates-01-hero"
COVER_ART = "renders/title-cover.jpg"
COVER_SOURCE = "media/summit/group-007.jpg"
TRIM = "renders/megacut-01-hero-trim.mp4"
MASTER = "renders/megacut-01-hero.mp4"
# Picture extends the established window by 0.05s to include the source fade's
# first black frame; that frame holds the new cards to 118.2. Dialogue-free
# audio needs the measured offset.
VIDEO_SRC = "media/yt_into_the_light_cinematic.mkv"
AUDIO_SRC = "media/yt_into_the_light_without_dialogue.webm"
TRIM_START = 2.0
TRIM_END = 113.60
AUDIO_SYNC_OFFSET = 1.978625
OUTPUT_DURATION = 118.2


def trim_command(ffmpeg):
    video_duration = TRIM_END - TRIM_START
    freeze_duration = OUTPUT_DURATION - video_duration
    audio_start = TRIM_START + AUDIO_SYNC_OFFSET
    # .resolve() so every path token is canonical: farm staging matches argv
    # tokens exactly, and both legs must agree when renders/ or media/ is a
    # symlink (a worktree building onto the durable stores).
    return [
        *ffmpeg, "-y",
        "-ss", f"{TRIM_START}", "-t", f"{video_duration:.2f}",
        "-i", str(Path(REPO_ROOT / VIDEO_SRC).resolve()),
        "-ss", f"{audio_start:.6f}",
        "-i", str(Path(REPO_ROOT / AUDIO_SRC).resolve()),
        "-map", "0:v", "-map", "1:a",
        "-vf", f"tpad=stop_mode=clone:stop_duration={freeze_duration:.6f}",
        "-t", f"{OUTPUT_DURATION:.3f}",
        "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p",
        "-c:a", "flac",
        str(Path(REPO_ROOT / TRIM).resolve()),
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


def render_cards(manifest=None, out_dir=None, website_modules=None):
    """Full-frame cards need the sibling website checkout (playwright).

    Rendered only when the manifest, renderer, or HTML templates have changed
    since the card PNGs were produced. Missing/stale cards are regenerated;
    if regeneration is required but the website's playwright checkout is
    absent, fail closed and name the stale outputs.
    """
    manifest = Path(manifest) if manifest else REPO_ROOT / MANIFEST
    out_dir = Path(out_dir) if out_dir else REPO_ROOT / PLATES_DIR
    website_modules = (
        Path(website_modules) if website_modules
        else Path.home() / "src/website/node_modules"
    )

    entries = plate.load_manifest(manifest)
    card_entries = [e for e in entries if e.get("kind") in plate.CARD_KINDS]
    if not card_entries:
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = [out_dir / f"plate_{e['id']}.png" for e in card_entries]
    inputs = [manifest, REPO_ROOT / "cards/render-cards.mjs",
              *sorted((REPO_ROOT / "cards").glob("*.html"))]
    stale = freshness.stale_outputs(inputs, outputs)
    if not stale:
        print(f"cards: {len(outputs)} card(s) are up to date, skipping render")
        return
    if not website_modules.is_dir():
        names = [out.name for out in stale]
        raise RuntimeError(
            "cards need rendering but the website playwright checkout is missing "
            f"({website_modules}); stale/missing cards: {', '.join(names)}. "
            "Install deps in ~/src/website or render the cards where playwright "
            "is available."
        )
    cmd = ["node", "cards/render-cards.mjs",
           "--manifest", str(manifest), "--out-dir", str(out_dir)]
    subprocess.run(cmd, check=True, cwd=REPO_ROOT,
                   env={**os.environ, "NODE_PATH": str(website_modules)})


def _farm_runner(cmd, inputs, out, expected_duration):
    from tools import farm

    def run(argv):
        # plate.burn .resolve()s every path it puts in the argv, so the
        # staging check's exact-token match only holds if the inputs are
        # resolved the same way -- a symlinked renders/ (a worktree whose
        # masters live at their durable paths) otherwise reads as "argv never
        # reads staged input". resolve() is a no-op on canonical paths.
        #
        # The fetch target is read off the ARGV, never the caller's `out`:
        # burn() rewrites the final token to a `.burntmp` sibling so an
        # interrupted encode cannot truncate the delivered master (#286), and
        # the farm refuses an `out` the argv does not name verbatim. The trim
        # leg's last token is its output outright, so one rule serves both.
        farm.run_ffmpeg_on_cluster(
            argv,
            inputs=[Path(REPO_ROOT / p).resolve() for p in inputs],
            out=Path(argv[-1]),
            expected_duration=expected_duration,
        )

    return run


def _capped_runner(reason):
    """The burn leg's local fallback: capped, and with the reason printed."""
    from tools import farm

    def run(argv):
        proc = farm.run_capped_local(argv, reason=reason,
                                     capture_output=True, text=True)
        if proc.returncode != 0:
            tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
            raise RuntimeError(f"act I burn failed:\n{tail}")

    return run


def build_act1(skip_encode=False, use_farm=None):
    from tools import farm

    if use_farm is None:
        use_farm, farm_why = farm.cluster_available()
        if not use_farm:
            farm_why = f"the cluster is not reachable ({farm_why})"
    else:
        farm_why = "--farm given" if use_farm else "--local given"
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

    duration = OUTPUT_DURATION
    trim_cmd = trim_command(ffmpeg)
    if use_farm:
        _farm_runner(trim_cmd, [VIDEO_SRC, AUDIO_SRC], TRIM, duration)(trim_cmd)
    else:
        farm.run_capped_local(trim_cmd, reason=farm_why, check=True,
                              cwd=REPO_ROOT)

    if use_farm:
        # The farm stages exact argv tokens, so the burn leg lists the plate
        # PNGs themselves, not their directory.
        burn_inputs = [TRIM] + [
            str(Path(PLATES_DIR) / f"plate_{u['id']}.png")
            for u in plate._burn_units(entries)
        ]
        runner = _farm_runner(None, burn_inputs, MASTER, duration)
    else:
        runner = _capped_runner(farm_why)
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
                        help="encode on the farm cluster. ALREADY the default "
                             "whenever the cluster is reachable; the flag "
                             "only pins the posture")
    parser.add_argument("--local", action="store_true",
                        help="encode on THIS host even when the cluster is "
                             "reachable (the escape hatch; the encodes run "
                             "under tools.farm.run_capped_local's memory cap)")
    args = parser.parse_args()
    if args.farm and args.local:
        raise SystemExit("--farm and --local are mutually exclusive: the "
                         "farm is already the default when the cluster is "
                         "reachable; --local is the escape hatch from it")

    if args.print_command:
        print(" ".join(trim_command(["<ffmpeg>"])))
        print("python3 tools/plate.py burn "
              f"{TRIM} --manifest {MANIFEST} --plates-dir {PLATES_DIR} "
              f"{MASTER}   # x264 crf 18, -c:a copy")
        return

    build_act1(skip_encode=args.skip_encode,
               use_farm=True if args.farm else (False if args.local else None))


if __name__ == "__main__":
    main()
