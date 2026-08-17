#!/usr/bin/env python3
"""Every shot in the show, as one picture per act.

Watching the programme end to end costs half an hour, so a note like "the card
sits on the wrong shot" is expensive to check and expensive to re-check. A
contact sheet is the cheap version: one frame per detected shot, labelled with
its timecode on the ACT's own clock, tiled into a single image per act.

    python3 tools/shots.py                      # every act in Prod/
    python3 tools/shots.py --act II --act VI    # just these
    python3 tools/shots.py --video renders/efmb-hq.mp4 --out /tmp/sheet

The timecode under each frame is the act's own clock, which is the clock
`stories/*-plates.json` uses -- so a plate's `at` can be read straight off the
sheet. It is NOT the programme clock; `tools/megacut.py --locate` converts.

DETECTION IS `ContentDetector`, the same detector the index uses, so a shot
here is the same object a segment is. Frames are pulled with ffmpeg rather
than OpenCV: the delivered acts are H.264, and on an atomic host the system
ffmpeg cannot decode that (docs/rendering.md), so the resolved container
ffmpeg does the work. OpenCV is used only to find the cuts, never to decode
for output -- it silently reports one scene for AV1, which is the trap
docs/skills/indexing.md records.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

WOLVES = Path.home() / "Videos" / "Wolves"
PROD = WOLVES / "Prod"

# Wide enough to read a face and a nameplate, small enough that a 400-shot act
# is still one openable picture.
THUMB_W = 480
COLUMNS = 5

# ContentDetector's threshold. 27 is the value every measured boundary in this
# repo was found with (scripts/build_efmb.py), so a sheet and a cut list agree.
THRESHOLD = 27.0


def tc(seconds):
    """`M:SS.mmm` -- the spelling stories/*.json uses for an act-clock mark."""
    m, s = divmod(float(seconds), 60)
    return f"{int(m)}:{s:06.3f}"


def detect(video, threshold=THRESHOLD):
    """Shot boundaries as (start_sec, end_sec), via ContentDetector.

    Returns a single whole-file span when scenedetect finds nothing, which is
    the honest answer for an act that really is one continuous take -- and
    also what AV1-through-OpenCV looks like, so the caller prints the count and
    lets a human notice.
    """
    from scenedetect import open_video, SceneManager
    from scenedetect.detectors import ContentDetector

    video_stream = open_video(str(video))
    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=threshold))
    manager.detect_scenes(video_stream, show_progress=False)
    scenes = manager.get_scene_list()
    if not scenes:
        duration = float(video_stream.duration.get_seconds())
        return [(0.0, duration)]
    return [(s.get_seconds(), e.get_seconds()) for s, e in scenes]


def _label_font(size=15):
    """DejaVu Sans Mono, the same face tools/plate.py resolves first.

    A monospaced label keeps every timecode the same width, so a column of
    them scans. Falls back to Pillow's built-in bitmap face rather than
    failing: a sheet with plain labels beats no sheet.
    """
    from PIL import ImageFont

    for candidate in ("/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono.ttf",
                      "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
                      "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def sheet(video, out_path, ffmpeg, threshold=THRESHOLD, columns=COLUMNS):
    """One labelled frame per shot, tiled into `out_path`. Returns the count.

    The frame taken is a little INSIDE the shot, not its first frame: a cut
    that lands on a dissolve or a flash-frame makes the boundary frame the
    least representative one in the shot. A twelfth of a second in is past the
    join and still unambiguously that shot.

    Labelling and tiling are Pillow, not ffmpeg's `drawtext` and `tile`. The
    container ffmpeg this repo resolves has no fontconfig configuration and no
    writable cache, so `drawtext` fails outright on it -- and Pillow is already
    a dependency here for the same reason tools/plate.py uses it.
    """
    from PIL import Image, ImageDraw

    shots = detect(video, threshold)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    work = out_path.parent / f".{out_path.stem}-frames"
    work.mkdir(parents=True, exist_ok=True)
    for stale in work.glob("*.png"):
        stale.unlink()

    for i, (start, _end) in enumerate(shots):
        # `-ss` before `-i` here: this is a still, not a cut, so input-side
        # seeking is both correct and hundreds of times faster than decoding
        # from zero for every shot in a nine-minute act.
        subprocess.run(
            list(ffmpeg) + [
                "-nostdin", "-v", "error", "-y", "-ss", f"{start + 0.08:.3f}",
                "-i", str(video), "-frames:v", "1",
                "-vf", f"scale={THUMB_W}:-2",
                str(work / f"f_{i:05d}.png")],
            check=True, capture_output=True)

    frames = sorted(work.glob("f_*.png"))
    if not frames:
        raise RuntimeError(f"no frames extracted from {video}")

    font = _label_font()
    tiles = []
    for (start, _end), path in zip(shots, frames):
        img = Image.open(path).convert("RGB")
        draw = ImageDraw.Draw(img)
        text = tc(start)
        box = draw.textbbox((0, 0), text, font=font)
        w, h = box[2] - box[0], box[3] - box[1]
        draw.rectangle((4, img.height - h - 12, 12 + w, img.height - 2),
                       fill=(0, 0, 0))
        draw.text((8, img.height - h - 10), text, font=font, fill=(255, 255, 255))
        tiles.append(img)

    pad, margin = 4, 8
    tw, th = tiles[0].size
    rows = (len(tiles) + columns - 1) // columns
    sheet_img = Image.new(
        "RGB",
        (margin * 2 + columns * tw + pad * (columns - 1),
         margin * 2 + rows * th + pad * (rows - 1)),
        (0, 0, 0))
    for i, tile in enumerate(tiles):
        r, c = divmod(i, columns)
        sheet_img.paste(tile, (margin + c * (tw + pad), margin + r * (th + pad)))
    sheet_img.save(out_path)

    for frame in frames:
        frame.unlink()
    work.rmdir()
    return len(shots)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="One frame per shot, per act, as a contact sheet.")
    parser.add_argument("--act", action="append", dest="acts", metavar="NUMERAL",
                        help="limit to these acts by numeral (repeatable)")
    parser.add_argument("--video", help="a single file instead of Prod/")
    parser.add_argument("--out", default=str(WOLVES / "shots"),
                        help="output directory (default ~/Videos/Wolves/shots)")
    parser.add_argument("--threshold", type=float, default=THRESHOLD)
    parser.add_argument("--columns", type=int, default=COLUMNS)
    args = parser.parse_args(argv)

    from tools.render import find_ffmpeg
    ffmpeg = find_ffmpeg()
    out_dir = Path(args.out)

    if args.video:
        video = Path(args.video)
        target = out_dir / f"{video.stem}-shots.png"
        count = sheet(video, target, ffmpeg, args.threshold, args.columns)
        print(f"{video.name}: {count} shot(s) -> {target}")
        return 0

    from tools import deliver
    acts = deliver.parse_running_order(REPO_ROOT / "docs" / "running-order.md")
    chosen = [a for a in acts if not args.acts or a.numeral in args.acts]
    if not chosen:
        parser.error(f"no such act: {', '.join(args.acts or [])}")

    for act in chosen:
        if not act.prod_file:
            print(f"{act.numeral:>4}  no Prod/ entry by design -- skipped")
            continue
        video = PROD / act.prod_file
        if not video.exists():
            # A missing master is a delivery fact, not this tool's business:
            # say so and keep going, so one absent act cannot cost the others.
            print(f"{act.numeral:>4}  no master at {video} -- skipped")
            continue
        target = out_dir / f"{video.stem}-shots.png"
        count = sheet(video, target, ffmpeg, args.threshold, args.columns)
        print(f"{act.numeral:>4}  {count:4d} shot(s)  {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
