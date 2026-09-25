#!/usr/bin/env python3
"""'The World of Bluefin' as a map-reduce farm encode.

2001's Dawn of Man, cut down to its story beats (``EDIT_2001``: the fade up
with "THE DAWN OF MAN" swapped for "A WORLD BEFORE KUBERNETES", one shot or
one sound event per beat of Clarke's "Primeval Night", then the dawn, the
monolith and the sun over it untouched), hard cut to the Darwin evolution clip
(``renders/efmb-front.mkv`` 4.0 -> 70.4667).

  map     every span is its own chunk (long spans split at MAX_CHUNK_S), each
          its own farm Workflow, ``-ss``-seeked into the source, conformed to
          3840x2160 letterboxed 30 fps, ``-frames:v`` exact; 8 at a time so
          both nodes are full and every pod schedules.
  audio   each span's own sound, concatenated in order, 12 ms de-click fades
          at the 2001 edits, nothing mixed across an edit.
  reduce  concat demuxer, picture and sound stream-copied, never re-encoded.

A chunk is reused when the same argv already produced it, so a change to one
span re-encodes that span only.

    python3 scripts/build_world_of_bluefin.py [--box black|matched] [--local] [--deliver]
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

# THE CUT. Owner: "compress the first segment to capture the best of the
# first parts of the film and cut out the monotonous ones ... ensure we are
# capturing 2001 story beats as outlined by the book", "we want to preserve
# the music so anything without sound is on the table", and "7m-11m is
# finished". Source seconds on the Warner upload; every in/out is a measured
# shot cut (ffprobe select=gt(scene,0.25)) or a point picked from per-second
# RMS inside a long take. The beats are Clarke's "Primeval Night".
EDIT_2001 = [
    (86.0, 100.768),     # the fade up; carries the title swap
    (110.611, 115.490),  # the world before: one sunrise
    (169.961, 174.091),  # the road to extinction: the tusked skull
    (197.5, 203.578),    # beside the tapirs: an ape grunts at a tapir
    (214.756, 219.0),    #   foraging, the tribe's calls
    (237.5, 242.534),    #   an ape shoves a tapir off the scrub
    (242.534, 249.249),  #   ...and the tapirs keep feeding
    (259.0, 274.8),      # the leopard takes one of them (out before the fade)
    (291.5, 299.8),      # the water hole: drinking
    (324.5, 326.660),    #   the Others arrive
    (326.660, 338.171),  #   the screaming stand-off
    (338.171, 348.2),    #   display, no blow struck
    (360.402, 362.613),  #   face to face
    (381.0, 391.5),      #   the tribe gives the water up
    (416.791, 425.5),    # night: the leopard on its kill
    (479.0, 504.295),    # terror in the cave: the growl, then Moon-Watcher
    (504.295, 679.2333), # dawn, the monolith, the sun over it: FINISHED, untouched
]
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


MAX_CHUNK_S = 90


def span_frames(a, b):
    """Frames a span keeps on the 30 fps grid. Floored, so a span that ends ON
    a shot cut never samples the incoming shot's first frame."""
    return int((b - a) * FPS + 1e-6)


def spans():
    """[(source, in, n_frames)] in programme order."""
    out = [(SOURCE_2001_LINK, a, span_frames(a, b)) for a, b in EDIT_2001]
    src, a, b = SPAN_DARWIN
    return out + [(src, a, span_frames(a, b))]


def plan_chunks():
    """[(source, src_start, n_frames, has_plate)]: every span is its own chunk,
    split further when it is longer than MAX_CHUNK_S. Only the first chunk of
    the first span carries the title swap."""
    chunks = []
    for k, (src, a, n) in enumerate(spans()):
        parts = max(1, -(-n // (MAX_CHUNK_S * FPS)))
        bounds = [round(i * n / parts) for i in range(parts + 1)]
        chunks += [(src, a + lo / FPS, hi - lo, k == 0 and lo == 0)
                   for lo, hi in zip(bounds, bounds[1:])]
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
    """Every span's own sound, trimmed to its frames and concatenated in
    order. A 12 ms fade at each 2001 edit keeps the hard cuts click-free;
    nothing is mixed across an edit."""
    edit = spans()
    n2001 = len(edit) - 1
    parts = [f"[0:a]asplit={n2001}" + "".join(f"[s{i}]" for i in range(n2001))]
    for i, (_src, a, n) in enumerate(edit[:-1]):
        d = n / FPS
        parts.append(f"[s{i}]atrim=start={a:.6f}:duration={d:.6f},"
                     f"asetpts=PTS-STARTPTS,aresample=48000,"
                     f"aformat=sample_fmts=fltp:channel_layouts=stereo,"
                     f"afade=t=in:d=0.012,afade=t=out:st={d - 0.012:.6f}:d=0.012"
                     f"[a{i}]")
    _src, a, n = edit[-1]
    parts.append(f"[1:a]atrim=start={a:.6f}:duration={n / FPS:.6f},"
                 f"asetpts=PTS-STARTPTS,aresample=48000,"
                 f"aformat=sample_fmts=fltp:channel_layouts=stereo[a{n2001}]")
    graph = ";".join(parts) + ";" + "".join(
        f"[a{i}]" for i in range(len(edit))) + f"concat=n={len(edit)}:v=0:a=1[a]"
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
                limit_cpu="8", memory="2Gi", expected_duration=n / FPS,
                label=f"farm[wob chunk {i:02d}]")
        else:
            farm.run_capped_local(argv, reason=why)
        stamp.write_text("\0".join(argv))
        return out

    # 8 x 8 cpu fills both nodes; submitting every chunk at once asks for more
    # memory than the cluster can schedule, and the farm fails an
    # unschedulable pod rather than queueing it.
    with ThreadPoolExecutor(max_workers=min(8, len(chunks))) as pool:
        outs = list(pool.map(lambda ic: one(*ic), enumerate(chunks)))
    return outs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
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

    chunks = plan_chunks()
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
