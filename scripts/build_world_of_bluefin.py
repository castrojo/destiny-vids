#!/usr/bin/env python3
"""'The World of Bluefin' as a map-reduce farm encode.

The 2001 Dawn of Man
sequence from the fade up (86.0 s) to the last frame of the sun-over-the-monolith shot (679.2333 s)
with the title card swapped for "A World before Kubernetes", then the Darwin
evolution clip (``renders/efmb-front.mkv`` 4.0 -> 70.4667) -- but encoded the
way ``tools/farm.py`` was designed to be used: the output timeline is cut into
frame-exact chunks, every chunk is its OWN Workflow (so the scheduler spreads
them over exo-0 and ghost instead of one 24-thread x264 on one node), and the
pieces are joined with ``-c copy``. This is the Argo fan-out/reduce pattern
(``withItems`` map, single join) expressed through the farm's per-job API.

  map     N video-only chunks, each ``-ss``-seeked into its own source span,
          conformed to 3840x2160 letterboxed 30 fps, ``-frames:v`` exact.
  audio   one pass over both spans' audio, concatenated in order, no mixing.
  reduce  concat demuxer, picture and sound stream-copied, never re-encoded.

The 2001 span and the Darwin span never share a chunk, so the cut between the
two films is a chunk seam by construction.

    python3 scripts/build_world_of_bluefin.py [--chunks 7] [--local] [--deliver]
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import farm  # noqa: E402

SOURCE_2001 = Path.home() / "Videos" / (
    "2001： A Space Odyssey ｜ Dawn of Man： Opening Monolith Scene ｜ "
    "Warner Classics [5NShEY1ScSY].webm")
SOURCE_DARWIN = REPO_ROOT / "renders/efmb-front.mkv"
WORK = REPO_ROOT / "renders/world-of-bluefin-chunks"
PLATE_SCRIPT = REPO_ROOT / "scripts/build_world_of_bluefin_plate.mjs"
PLATE_DIR = REPO_ROOT / "renders/plates-world-of-bluefin"
PLATE_TEXT = PLATE_DIR / "text.png"
PLATE_BOX = PLATE_DIR / "box.png"
PLATEAU_FRAME = PLATE_DIR / "plateau-4k.png"
OUTPUT = REPO_ROOT / "renders/world-of-bluefin-4k.mp4"
DELIVER = (Path.home() / "Videos/Wolves/The World of Bluefin.mp4",
           Path.home() / "Videos/Wolves/review/The World of Bluefin.mp4")

FPS = 30
# (source, in, out) on each source's own clock, in programme order.
# The Warner upload's name carries "[5NShEY1ScSY]". kubectl cp glob-expands
# its source, so farm.Kubectl.cp hardlinks bracketed names to a per-PROCESS
# temp name -- and parallel chunks are threads of one process, so they race on
# that one link. The chunks read a bracket-free hardlink made once, up front.
SOURCE_2001_LINK = WORK / "src-2001-dawn-of-man.webm"
# Out on the last frame of the sun-over-the-monolith shot: the next shot
# (a desert dawn) cuts in at 679.262, measured with select=gt(scene,0.3).
SPAN_2001 = (SOURCE_2001_LINK, 86.0, 679.2333)
SPAN_DARWIN = (SOURCE_DARWIN, 4.0, 70.4667)
# Title swap, in 2001-span time. The source card is up 92.4 -> 93.8, held,
# down 97.6 -> 100.2, and the shot cuts at 100.768 (select=gt(scene,0.2)).
# Owner: "render the world before kubernetes longer than the original so you
# hide it entirely". Box and words are fully up before the old words begin to
# show; the box holds until the frame before the cut and leaves WITH the cut
# (it carries the old shot's tone, so it must never outlive the shot); the
# words fade over the last 2 s of the shot -- on screen longer than the card.
SWAP_IN, SWAP_IN_D = 5.0, 1.4
SHOT_CUT = 14.75            # last card-shot frame is t=14.7333 on the 30 fps grid
TEXT_OUT_D = 2.0
LAYER_SECONDS = 16
# The card's ink on the 4K conform (1080p x=516..1396, y=670..736), padded
# for the print's softness; the box covers exactly this.
BOX = (1016, 1324, 2808, 1488)
BOX_FEATHER = 10

# Both sources are 2.39:1 inside a 16:9 frame (1920x804 active picture).
CONFORM = ("crop=1920:804:0:138,scale=3840:1608:flags=lanczos,"
           "pad=3840:2160:0:(oh-ih)/2:color=black,format=yuv420p")
VIDEO_ARGS = ("-c:v", "libx264", "-preset", "slow", "-crf", "18",
              "-pix_fmt", "yuv420p", "-r", str(FPS),
              "-video_track_timescale", "15360")


def frames(seconds):
    return round(seconds * FPS)


def plan_chunks(n_2001):
    """[(source, src_start, n_frames, has_plate)] in programme order."""
    src, a, b = SPAN_2001
    total = frames(b - a)
    bounds = [round(i * total / n_2001) for i in range(n_2001 + 1)]
    chunks = [(src, a + lo / FPS, hi - lo, lo == 0)
              for lo, hi in zip(bounds, bounds[1:])]
    src, a, b = SPAN_DARWIN
    chunks.append((src, a, frames(b - a), False))
    return chunks


def chunk_argv(ffmpeg, src, start, n_frames, has_plate, out):
    dur = n_frames / FPS
    argv = [ffmpeg, "-y", "-ss", f"{start:.6f}", "-t", f"{dur + 1.0:.6f}",
            "-i", str(src)]
    if has_plate:
        for layer in (PLATE_BOX, PLATE_TEXT):
            argv += ["-loop", "1", "-t", str(LAYER_SECONDS), "-i", str(layer)]

        def layer(i, name, fade_out=""):
            return (f"[{i}:v]trim=duration={LAYER_SECONDS},setpts=PTS-STARTPTS,"
                    f"format=rgba,fade=t=in:st={SWAP_IN}:d={SWAP_IN_D}:alpha=1"
                    f"{fade_out}[{name}]")
        on = f"enable='between(t,{SWAP_IN},{SHOT_CUT})'"
        text_out = (f",fade=t=out:st={SHOT_CUT - TEXT_OUT_D:.2f}"
                    f":d={TEXT_OUT_D}:alpha=1")
        graph = (f"[0:v]fps={FPS},{CONFORM}[b];"
                 + layer(1, "bx") + ";" + layer(2, "tx", text_out) + ";"
                 f"[b][bx]overlay=0:0:{on}:eof_action=pass:format=auto[b1];"
                 f"[b1][tx]overlay=0:0:{on}:eof_action=pass:format=auto[v]")
    else:
        graph = f"[0:v]fps={FPS},{CONFORM}[v]"
    return argv + ["-filter_complex", graph, "-map", "[v]", "-an",
                   "-frames:v", str(n_frames), *VIDEO_ARGS, str(out)]


def audio_argv(ffmpeg, out):
    parts = []
    for i, (_src, a, b) in enumerate((SPAN_2001, SPAN_DARWIN)):
        parts.append(f"[{i}:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS,"
                     f"aresample=48000,aformat=sample_fmts=fltp:"
                     f"channel_layouts=stereo[a{i}]")
    graph = ";".join(parts) + ";[a0][a1]concat=n=2:v=0:a=1[a]"
    return [ffmpeg, "-y", "-i", str(SOURCE_2001_LINK), "-i", str(SOURCE_DARWIN),
            "-filter_complex", graph, "-map", "[a]", "-vn",
            "-c:a", "aac", "-b:a", "320k", str(out)]


def join_argv(ffmpeg, listing, audio, out):
    return [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
            "-i", str(audio), "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "copy", "-movflags", "+faststart",
            str(out)]


def _frame_count(path):
    """Exact decoded frame count of a fetched chunk, or None."""
    probe = subprocess.run(
        [*farm.native_ffprobe(), "-v", "error", "-select_streams", "v:0",
         "-count_packets", "-show_entries", "stream=nb_read_packets",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return int(probe.stdout.strip())
    except ValueError:
        return None


def grab_plateau_frame(ffmpeg):
    """The card's plateau frame (source 96.0 s) on the 4K conform: what the
    box samples its tone from. A still decode, not an encode."""
    PLATE_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run([ffmpeg, "-v", "error", "-y", "-ss", "96",
                    "-i", str(SOURCE_2001_LINK), "-frames:v", "1",
                    "-vf", CONFORM.replace(",format=yuv420p", ""),
                    "-update", "1", str(PLATEAU_FRAME)], check=True)


def build_box(mode):
    """The box over the old words, exactly BOX, edges feathered.

    ``black`` is the owner's literal ask. ``matched`` fills the same box with
    the frame's own tone: each column interpolated between the sky sampled
    just above and just below the card, so the box carries the dawn gradient
    and the left-to-right fall-off instead of one flat colour.
    """
    from PIL import Image
    x0, y0, x1, y1 = BOX
    w, h = x1 - x0, y1 - y0
    box = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    if mode == "matched":
        frame = Image.open(PLATEAU_FRAME).convert("RGB")
        px, out = frame.load(), box.load()

        def band(x, ya, yb):
            vals = [px[xx, yy] for xx in range(max(0, x - 6), min(frame.width, x + 7))
                    for yy in range(ya, yb)]
            return [sum(v[c] for v in vals) / len(vals) for c in range(3)]
        for i in range(w):
            top, bot = band(x0 + i, y0 - 14, y0 - 4), band(x0 + i, y1 + 4, y1 + 14)
            for j in range(h):
                t = j / (h - 1)
                t = t * t * (3 - 2 * t)
                out[i, j] = (*(round(a + (b - a) * t) for a, b in zip(top, bot)), 255)
    alpha = box.getchannel("A").load()
    for i in range(w):
        for j in range(h):
            e = min(i, j, w - 1 - i, h - 1 - j)
            if e < BOX_FEATHER:
                alpha[i, j] = round(255 * (e + 1) / (BOX_FEATHER + 1))
    layer = Image.new("RGBA", (3840, 2160), (0, 0, 0, 0))
    layer.paste(box, (x0, y0), box)
    layer.save(PLATE_BOX)


def render_plate(ffmpeg, mode):
    """Redraw both title-swap layers every run, so nothing burned can be older
    than the code that draws it -- but replace a layer only when its pixels
    changed, so an unchanged card does not re-encode its chunk."""
    old = {p: (p.read_bytes(), p.stat().st_mtime)
           for p in (PLATE_BOX, PLATE_TEXT) if p.is_file()}
    grab_plateau_frame(ffmpeg)
    build_box(mode)
    env = dict(os.environ, NODE_PATH=str(Path.home() /
                                         "src/website/node_modules"))
    subprocess.run(["node", str(PLATE_SCRIPT), str(PLATE_DIR)], check=True,
                   env=env)
    for p, (before, mtime) in old.items():
        if p.read_bytes() == before:
            os.utime(p, (p.stat().st_atime, mtime))


def encode_chunks(ffmpeg, chunks, *, local):
    """Map: one farm Workflow per chunk, all submitted at once."""
    if local:
        ok, why = False, "--local"
    else:
        ok, why = farm.cluster_available()
    if not ok:
        print(f"farm unavailable ({why}); encoding chunks locally, capped",
              file=sys.stderr)
    outs = []

    def one(i, chunk):
        src, start, n, has_plate = chunk
        out = WORK / f"chunk_{i:02d}.mp4"
        # Reused only when the SAME argv already produced a chunk of the right
        # length from inputs no newer than it: a card tweak re-encodes the one
        # chunk that carries the card, not the film.
        stamp = out.with_suffix(".argv")
        argv = chunk_argv(ffmpeg, src, start, n, has_plate, out)
        deps = [src] + ([PLATE_BOX, PLATE_TEXT] if has_plate else [])
        if (out.is_file() and stamp.is_file()
                and stamp.read_text() == "\0".join(argv)
                and _frame_count(out) == n
                and out.stat().st_mtime > max(d.stat().st_mtime for d in deps)):
            print(f"chunk {i:02d}: unchanged ({n} frames), reused")
            return out
        stamp.unlink(missing_ok=True)
        inputs = [src, PLATE_BOX, PLATE_TEXT] if has_plate else [src]
        if ok:
            farm.run_ffmpeg_on_cluster(
                argv, inputs=inputs, out=out,
                name=farm.farm_name(f"wob-chunk-{i:02d}"),
                limit_cpu="8", expected_duration=n / FPS,
                label=f"farm[wob chunk {i:02d}]")
        else:
            farm.run_capped_local(argv, reason=why)
        stamp.write_text("\0".join(argv))
        return out

    with ThreadPoolExecutor(max_workers=len(chunks)) as pool:
        outs = list(pool.map(lambda ic: one(*ic), enumerate(chunks)))
    return outs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--chunks", type=int, default=7,
                    help="chunks for the 2001 span (Darwin is one more)")
    ap.add_argument("--local", action="store_true")
    ap.add_argument("--box", choices=("black", "matched"), default="black",
                    help="the box over THE DAWN OF MAN: black, or the sky's tone")
    ap.add_argument("--deliver", action="store_true",
                    help="copy the joined file to ~/Videos/Wolves")
    args = ap.parse_args(argv)

    for p in (SOURCE_2001, SOURCE_DARWIN):
        if not p.is_file():
            sys.stderr.write(f"missing source: {p}\n")
            return 1
    ffmpeg = os.environ.get("DESTINY_FFMPEG",
                            "/home/linuxbrew/.linuxbrew/bin/ffmpeg")
    WORK.mkdir(parents=True, exist_ok=True)
    if not (SOURCE_2001_LINK.is_file()
            and SOURCE_2001_LINK.stat().st_ino == SOURCE_2001.stat().st_ino):
        SOURCE_2001_LINK.unlink(missing_ok=True)
        SOURCE_2001_LINK.hardlink_to(SOURCE_2001)
    render_plate(ffmpeg, args.box)

    chunks = plan_chunks(args.chunks)
    total = sum(c[2] for c in chunks)
    print(f"{len(chunks)} chunks, {total} frames, {total / FPS:.3f} s")
    outs = encode_chunks(ffmpeg, chunks, local=args.local)

    # Audio and join are local by nature: the audio pass carries no picture
    # (the farm verifier requires a video stream) and the join is a remux.
    audio = WORK / "audio.m4a"
    farm.run_capped_local(audio_argv(ffmpeg, audio),
                          reason="audio-only pass; no picture to farm")
    listing = WORK / "chunks.txt"
    listing.write_text("".join(f"file '{p}'\n" for p in outs))
    farm.run_capped_local(join_argv(ffmpeg, listing, audio, OUTPUT),
                          reason="stream-copy join; nothing is encoded")

    print(f"built {OUTPUT}")
    if not args.deliver:
        return 0
    for dest in DELIVER:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUTPUT, dest)
        print(f"delivered {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
