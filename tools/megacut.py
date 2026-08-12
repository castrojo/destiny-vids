#!/usr/bin/env python3
"""Ordered cuts and chapter cards -> one continuous programme, in a single pass.

This is the assembly stage: it takes finished deliverables that already exist
and joins them into one file, with the reference deck's title cards between
them. It edits nothing. Every segment it is handed is either a rendered cut
from this repo or an owner-approved deliverable from ``~/Videos``, and the
cards are PNGs rendered by ``tools/plate.py render``.

    python3 tools/megacut.py renders/megacut.json --out renders/megacut.mp4

Why one ffmpeg pass
-------------------
The obvious implementation normalises each segment to a temporary file and then
concatenates the temporaries. That re-encodes every frame twice. This builds a
single ``filter_complex`` instead, so a source frame is decoded once and encoded
once -- one generation of loss, not two.

What "normalise" means here, and why each choice
------------------------------------------------
The segments genuinely disagree, so a re-encode is unavoidable:

* **Frame rate.** Sources run at 30/1, 60/1 and 60000/1001. ``concat`` requires
  one rate, and picking 60000/1001 keeps the 59.94 material untouched while the
  integer-rate material resamples predictably. Choosing 30 would throw away the
  60fps Guardian intros; choosing 60/1 would make the 59.94 cut drift against
  its own audio.
* **Audio.** Everything is 48 kHz 5.1, and it is passed through **unprocessed**
  -- no normaliser, no limiter, no EQ (the audio tenet). Silent segments get
  generated 5.1 silence of exactly matching length rather than being left with
  no stream, because ``concat`` needs every segment to carry both.
* **Colour.** BT.709 SDR is tagged explicitly. Untagged 1080p is *assumed* to be
  BT.709 by most players, but "most" is not a guarantee, and a mis-tagged master
  is invisible until someone grades against it.

Audio is re-encoded once to AAC. That is one generation of lossy-to-lossy loss
on segments whose deliverables are already AAC; it is recorded rather than
hidden, and the lossless-master path (see ``~/Videos/AUDIO.md``) is the upgrade
if a delivered master is ever wanted.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# 59.94, as a rational so ffmpeg never rounds it to 60.
DEFAULT_FPS = "60000/1001"
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080
DEFAULT_SAMPLE_RATE = 48000
DEFAULT_LAYOUT = "5.1"


def ffmpeg_bin():
    """The ffmpeg that can actually decode H.264.

    On an atomic Fedora/Bluefin host the ``ffmpeg`` on PATH is ``ffmpeg-free``,
    which has no H.264 decoder and fails only once decoding starts -- which
    reads like a corrupt input file. Prefer the linuxbrew build, then the local
    container shim, and fall back to PATH.

    This never raises when no ffmpeg exists: *building* a command is pure
    string work, and the offline test suite has to be able to do it on a
    machine with no ffmpeg at all. A missing binary surfaces when the command
    is actually run, which is the only place it matters.
    """
    for candidate in ("/home/linuxbrew/.linuxbrew/bin/ffmpeg",
                      str(Path.home() / ".local/bin/ffmpeg")):
        if Path(candidate).exists():
            return candidate
    return shutil.which("ffmpeg") or "ffmpeg"


def ffprobe_bin():
    """The ffprobe beside the chosen ffmpeg."""
    ffmpeg = ffmpeg_bin()
    head, sep, tail = ffmpeg.rpartition("ffmpeg")
    return f"{head}ffprobe{tail}" if sep else "ffprobe"


def load_plan(path):
    plan = json.loads(Path(path).read_text())
    items = plan.get("items")
    if not items:
        raise ValueError("plan has no items")
    for i, item in enumerate(items):
        kind = item.get("kind")
        if kind not in ("card", "clip"):
            raise ValueError(f"item {i}: kind must be 'card' or 'clip', got {kind!r}")
        src = item.get("image") if kind == "card" else item.get("path")
        if not src:
            raise ValueError(f"item {i}: missing {'image' if kind == 'card' else 'path'}")
        if not (REPO_ROOT / src).exists() and not Path(src).exists():
            raise ValueError(f"item {i}: source does not exist: {src}")
        if kind == "card" and float(item.get("dur", 0)) <= 0:
            raise ValueError(f"item {i}: card needs a positive dur")
        if kind == "clip" and item.get("audio") not in ("source", "silent"):
            raise ValueError(
                f"item {i}: clip audio must be 'source' or 'silent' -- state it "
                f"explicitly, so a segment is never silently dropped to silence"
            )
    return plan


def resolve(src):
    p = Path(src)
    return str(p if p.is_absolute() or p.exists() else REPO_ROOT / src)


def build_inputs(plan):
    """ffmpeg input arguments, in item order."""
    args = []
    fps = plan.get("fps", DEFAULT_FPS)
    for item in plan["items"]:
        if item["kind"] == "card":
            args += ["-loop", "1", "-framerate", fps,
                     "-t", str(item["dur"]), "-i", resolve(item["image"])]
        else:
            args += ["-i", resolve(item["path"])]
    return args


def build_filtergraph(plan):
    """One filter_complex that normalises every segment and concatenates once."""
    fps = plan.get("fps", DEFAULT_FPS)
    w = int(plan.get("width", DEFAULT_WIDTH))
    h = int(plan.get("height", DEFAULT_HEIGHT))
    rate = int(plan.get("sample_rate", DEFAULT_SAMPLE_RATE))
    layout = plan.get("layout", DEFAULT_LAYOUT)

    chains, labels = [], []
    for i, item in enumerate(plan["items"]):
        v, a = f"v{i}", f"a{i}"
        if item["kind"] == "card":
            dur = float(item["dur"])
            # The card is a transparent PNG in the deck's own geometry. Flatten
            # it onto real black rather than relying on yuv420p to drop alpha:
            # the colour under a fully transparent pixel is undefined, so
            # dropping alpha alone can reveal white fringing.
            chains.append(
                f"color=c=black:s={w}x{h}:r={fps}:d={dur}[bg{i}]"
            )
            chains.append(
                f"[{i}:v]scale={w}:{h}:flags=lanczos,format=rgba[fg{i}]"
            )
            chains.append(
                f"[bg{i}][fg{i}]overlay=0:0:shortest=1,"
                f"fps={fps},format=yuv420p,setsar=1,setpts=PTS-STARTPTS[{v}]"
            )
            chains.append(
                f"anullsrc=channel_layout={layout}:sample_rate={rate}:d={dur},"
                f"asetpts=PTS-STARTPTS[{a}]"
            )
        else:
            chains.append(
                f"[{i}:v]scale={w}:{h}:flags=lanczos,setsar=1,"
                f"fps={fps},format=yuv420p,setpts=PTS-STARTPTS[{v}]"
            )
            if item["audio"] == "silent":
                # Length is taken from the clip itself, not guessed: a silence
                # source that is a frame short desynchronises everything after
                # it in the concat.
                dur = item.get("dur")
                if dur is None:
                    dur = probe_duration(resolve(item["path"]))
                chains.append(
                    f"anullsrc=channel_layout={layout}:sample_rate={rate}:d={dur},"
                    f"asetpts=PTS-STARTPTS[{a}]"
                )
            else:
                # aresample only where the rate differs; aformat pins the layout
                # so concat sees one shape. No gain is applied anywhere.
                chains.append(
                    f"[{i}:a]aresample={rate},"
                    f"aformat=sample_fmts=fltp:channel_layouts={layout},"
                    f"asetpts=PTS-STARTPTS[{a}]"
                )
        labels += [f"[{v}][{a}]"]

    n = len(plan["items"])
    chains.append(f"{''.join(labels)}concat=n={n}:v=1:a=1[vout][aout]")
    return ";".join(chains)


def probe_duration(path):
    out = subprocess.run(
        [ffprobe_bin(), "-v", "error",
         "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def build_command(plan, out_path):
    crf = str(plan.get("crf", 16))
    preset = plan.get("preset", "slow")
    abitrate = plan.get("audio_bitrate", "640k")
    return [
        ffmpeg_bin(), "-nostdin", "-hide_banner",
        *build_inputs(plan),
        "-filter_complex", build_filtergraph(plan),
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", preset, "-crf", crf,
        "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        # The three -color_* flags above describe the *frames*, and x264 only
        # copies the matrix from them -- primaries and transfer come out
        # `unknown`, which is a silent mismatch against every other deliverable
        # in ~/Videos/UPLOAD. Writing the VUI directly is the only way all three
        # actually land in the bitstream. Verified by ffprobe, not assumed.
        "-x264-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709",
        "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", abitrate, "-ar", str(plan.get("sample_rate", DEFAULT_SAMPLE_RATE)),
        str(out_path), "-y",
    ]


def expected_duration(plan):
    total = 0.0
    for item in plan["items"]:
        if item["kind"] == "card":
            total += float(item["dur"])
        else:
            total += float(item.get("dur") or probe_duration(resolve(item["path"])))
    return total


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("plan", help="JSON assembly plan")
    ap.add_argument("--out", help="output file (overrides the plan's `output`)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the command and the expected duration, encode nothing")
    args = ap.parse_args(argv)

    plan = load_plan(args.plan)
    out_path = args.out or plan.get("output")
    if not out_path:
        raise SystemExit("no output: pass --out or set `output` in the plan")

    cmd = build_command(plan, out_path)
    if args.dry_run:
        print(" ".join(cmd))
        print(f"# expected duration: {expected_duration(plan):.3f}s "
              f"across {len(plan['items'])} items")
        return 0

    print(f"assembling {len(plan['items'])} items -> {out_path}", file=sys.stderr)
    subprocess.run(cmd, check=True)
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
