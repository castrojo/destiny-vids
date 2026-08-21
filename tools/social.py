#!/usr/bin/env python3
"""A finished cut -> a social copy that fits a size cap.

Social platforms cap an upload by **bytes**, not by bitrate, so the only honest
way to hit one is to solve for the video bitrate from the duration and the
audio budget, then let a two-pass encode spend exactly that. Guessing a CRF and
re-rolling until the file happens to fit wastes an encode per attempt and lands
somewhere arbitrary.

    python3 tools/social.py ~/Videos/Wolves/Prod/05-nat.mp4 \
        --out ~/Videos/Wolves/10mb/05-nat.mp4

Defaults are the 10 MB / 720p shape the two existing social copies in
``~/Videos/wolves-directors-cut`` already use (both 1280x720 H.264, ~9.3 and
~9.9 MB), so this reproduces an established deliverable rather than inventing
one.

THE AUDIO TENET APPLIES HERE TOO. This re-encodes; it never *processes*. No
normaliser, no limiter, no EQ, no upmix and no downmix beyond what the cap
forces. What it does spend is bitrate, and it spends it on audio first: a
starved music bed is the one artifact people actually hear on a phone. The
default 128k AAC is a floor, not a target -- raise it with ``--audio-bitrate``
when the cap allows.

Everything it does is derived from the source and printed, so the arithmetic
can be checked before the encode runs (``--dry-run``).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import farm

# Mebibytes. Platforms quote "10MB" and mean 10 * 1024 * 1024 often enough that
# the smaller unit is the safe reading of an ambiguous limit.
MIB = 1024 * 1024

# Muxing overhead is real and not proportional to bitrate in any simple way, so
# a flat headroom fraction is kept back rather than modelled. 3% lands the two
# reference files just under their cap with room to spare.
OVERHEAD = 0.03

DEFAULT_HEIGHT = 720          # both reference social copies are 1280x720
DEFAULT_AUDIO_BITRATE = 192   # kbit/s, AAC stereo -- a floor, not a target


def probe(path, entries, stream=None):
    cmd = ["ffprobe", "-v", "error", "-print_format", "json"]
    if stream:
        cmd += ["-select_streams", stream]
    cmd += ["-show_entries", entries, str(path)]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def source_facts(path):
    """Duration from the VIDEO stream, plus the shape of the picture.

    ``format=duration`` covers the longest stream, which is the wrong number on
    a file whose audio outruns its picture -- the same trap the megacut skill
    records. The picture decides the length here for the same reason.
    """
    v = probe(path, "stream=width,height,duration,r_frame_rate", "v:0")["streams"][0]
    fmt = probe(path, "format=duration")["format"]
    duration = float(v.get("duration") or fmt["duration"])
    return {
        "width": int(v["width"]),
        "height": int(v["height"]),
        "fps": v["r_frame_rate"],
        "duration": duration,
    }


def video_bitrate_for(target_bytes, duration, audio_kbps):
    """The video bitrate, in kbit/s, that fills the cap and nothing more."""
    budget_bits = target_bytes * 8 * (1 - OVERHEAD)
    audio_bits = audio_kbps * 1000 * duration
    video_bits = budget_bits - audio_bits
    if video_bits <= 0:
        raise ValueError(
            f"{audio_kbps}k of audio over {duration:.1f}s already exceeds the "
            f"{target_bytes / MIB:.1f} MiB cap; lower --audio-bitrate or raise --target-mb"
        )
    return int(video_bits / duration / 1000)


def source_digest(path):
    """The exact Prod bytes this social derivative was encoded from."""
    digest = hashlib.md5()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_commands(src, out, *, target_mb, height, audio_kbps, ffmpeg, passlog,
                   pass1_out="/dev/null"):
    facts = source_facts(src)
    target_bytes = int(target_mb * MIB)
    v_kbps = video_bitrate_for(target_bytes, facts["duration"], audio_kbps)

    # Scale by height, width to even. -2 keeps the source aspect and guarantees
    # a mod-2 width, which yuv420p requires.
    scale = f"scale=-2:{height}:flags=lanczos" if facts["height"] != height else "null"
    common = [
        *ffmpeg, "-nostdin", "-y", "-i", str(src),
        "-vf", f"{scale},setsar=1",
        "-c:v", "libx264", "-b:v", f"{v_kbps}k",
        "-preset", "slow", "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-x264-params", f"colorprim=bt709:transfer=bt709:colormatrix=bt709:stats={passlog}",
    ]
    first = [*common, "-pass", "1", "-an", "-f", "mp4", str(pass1_out)]
    second = [*common, "-pass", "2",
              "-c:a", "aac", "-b:a", f"{audio_kbps}k", "-ar", "48000",
              "-movflags", "+faststart", str(out)]
    return facts, v_kbps, target_bytes, [first, second]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Encode a social copy under a size cap.")
    ap.add_argument("source")
    ap.add_argument("--out", required=True)
    ap.add_argument("--target-mb", type=float, default=10.0,
                    help="cap in MiB (default 10)")
    ap.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    ap.add_argument("--audio-bitrate", type=int, default=DEFAULT_AUDIO_BITRATE,
                    help="kbit/s AAC; spend what the cap allows (default 192)")
    ap.add_argument("--local", action="store_true",
                    help="force this host even when the farm is reachable")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    from tools.render import find_ffmpeg

    src, out = Path(args.source), Path(args.out)
    if not src.exists():
        raise SystemExit(f"source does not exist: {src}")
    out.parent.mkdir(parents=True, exist_ok=True)

    # The two-pass stats file sits BESIDE THE OUTPUT, not in a temp dir: the
    # ffmpeg this repo resolves is usually a container (see tools/render.py
    # find_ffmpeg), and only the paths it mounts exist inside it. The output
    # directory is mounted by definition -- it is where the file is written.
    passlog = str(out.with_suffix("")) + ".x264"
    try:
        use_farm, reason = (False, "--local given") if args.local else \
            farm.cluster_available()
        if use_farm:
            ffmpeg = ["ffmpeg"]
            remote_passlog = f"out/{out.stem}.x264"
            pass1_out = out
            print("encoder  farm (cluster reachable; two passes share one pod)")
        else:
            ffmpeg = find_ffmpeg()
            remote_passlog = passlog
            pass1_out = "/dev/null"
            print(f"encoder  local ({reason or 'farm unavailable'})")
        facts, v_kbps, target_bytes, cmds = build_commands(
            src, out, target_mb=args.target_mb, height=args.height,
            audio_kbps=args.audio_bitrate, ffmpeg=ffmpeg, passlog=remote_passlog,
            pass1_out=pass1_out)

        print(f"source   {src}")
        print(f"         {facts['width']}x{facts['height']} @ {facts['fps']}, "
              f"{facts['duration']:.3f}s")
        print(f"target   {args.target_mb} MiB ({target_bytes} bytes), "
              f"{OVERHEAD:.0%} held back for muxing")
        print(f"budget   video {v_kbps}k + audio {args.audio_bitrate}k, "
              f"scaled to {args.height}p")
        if args.dry_run:
            for cmd in cmds:
                print(" ".join(cmd))
            return 0

        if use_farm:
            farm.run_ffmpeg_commands_on_cluster(
                cmds, inputs=[src], out=out, expected_duration=facts["duration"],
                label=f"social[{out.name}]")
        else:
            for i, cmd in enumerate(cmds, start=1):
                proc = subprocess.run(cmd, capture_output=True, text=True)
                if proc.returncode != 0:
                    tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
                    raise SystemExit(f"pass {i} failed:\n{tail}")
    finally:
        for leftover in Path(passlog).parent.glob(Path(passlog).name + "*"):
            leftover.unlink(missing_ok=True)

    # The digest rides with EVERY completed encode, over cap or not: the cap
    # is a platform rule about the bytes, the digest is provenance about
    # which master they came from. Returning before writing it turned an
    # over-cap copy into a permanently missing digest, which check_social
    # reads as STALE -- and --watch re-encoded the same recipe forever.
    out.with_suffix(out.suffix + ".source.md5").write_text(
        source_digest(src) + "\n", encoding="utf-8")
    size = out.stat().st_size
    print(f"wrote    {out}  {size / MIB:.2f} MiB")
    if size > target_bytes:
        # Reported, never silently accepted: a file over the cap will be
        # rejected by the platform, and knowing by how much is what tells you
        # whether to drop the audio rung or the height.
        print(f"OVER CAP by {(size - target_bytes) / MIB:.2f} MiB -- "
              f"lower --audio-bitrate or --height and re-run")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
