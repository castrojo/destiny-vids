#!/usr/bin/env python3
"""Render the CNCF project wall -- act III's closing slide.

The wall is a full-frame card in the same sense as the site's `act`/`comic`
cards: tools/plate.py BURNS it but does not draw it. This builder draws it,
from the generated landscape record, never from copy written here:

    stories/cncf-projects.json   the project set (scripts/sync_landscape.py)
    assets/cncf-logos/<id>.png   the artwork, rasterized by the same sync

The TITLE is authored copy: the owner writes it in
``chapters/III-mrbobbytables.md`` and it reaches the build through that act's
``stories/<video_id>-fixed-plates.json`` entry (kind ``logowall``), which is
the manifest ``build_uncut_credited.sh`` actually reads and passes through
with ``--title``. The logos and names come from the record, so the
wall shows the right projects every time the set changes -- that is the whole
point of the sync.

SCALING. The owner expects the set to grow ("lots of logos over time"). The
grid recomputes from the count: columns follow sqrt(n) biased wide, logo
height shrinks as rows grow, and the name under each logo steps down in size
until it fits its cell. Nothing is hand-placed, so fifty projects lay out as
cleanly as five.

    python3 scripts/build_cncf_wall.py --title "CNCF Projects to Help Your Agents" \
        --fit-video media/<video>.mp4 --out renders/plates-<video>/plate_cncf-wall.png
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import plate as plate_mod  # noqa: E402  (the house typeface)

DATA = REPO / "stories" / "cncf-projects.json"

# The wall's TITLE is set in a proportional face, not the plates' mono --
# owner, 2026-08-24: "pick a non mono font for the title". DejaVu Sans is the
# portable end of the slide stack (Inter -> Arial Narrow -> DejaVu Sans; CI
# installs fonts-dejavu-core), so host and runner draw the same card.
SANS_CANDIDATES = {
    "bold": [
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/liberation-fonts/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ],
    "regular": [
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/liberation-fonts/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ],
}


def _sans(weight, size):
    from PIL import ImageFont

    for path in SANS_CANDIDATES[weight]:
        if Path(path).exists():
            return ImageFont.truetype(path, int(round(size)))
    raise RuntimeError(f"no proportional font found; tried "
                       f"{SANS_CANDIDATES[weight]}")

WHITE = (245, 248, 250, 255)
DIM = (180, 196, 210, 255)
# Every logo sits on the same light chip: brand artwork is authored
# dark-on-light about as often as light-on-dark (Lima's mark is solid black),
# and on the dimmed picture a dark mark with no chip simply vanishes.
CHIP = (245, 248, 250, 235)

# Content rect on a 1920x1080 frame, as fractions so the same layout works on
# any size the video probes to.
MARGIN_X = 0.105
TITLE_Y = 0.135
GRID_TOP = 0.30
GRID_BOTTOM = 0.93


def video_size(path):
    """Width and height of a video, probed with the ffprobe beside ffmpeg."""
    from tools.render import find_ffmpeg

    ffmpeg = find_ffmpeg()
    probe = [*ffmpeg[:-1], "ffprobe"] if ffmpeg[-1].endswith("ffmpeg") \
        else ["ffprobe"]
    out = subprocess.run(
        [*probe, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0",
         str(Path(path).resolve())],
        capture_output=True, text=True)
    w, _, h = out.stdout.strip().partition(",")
    if not w:
        raise RuntimeError(f"could not probe {path}: {out.stderr.strip()}")
    return int(w), int(h)


def grid_shape(n, area_w, area_h):
    """(cols, rows) for n cells in a wide area. Pure: the tests pin this."""
    if n <= 0:
        return 0, 0
    cols = max(1, round(math.sqrt(n * (area_w / area_h) * 0.75)))
    rows = math.ceil(n / cols)
    # A last row with a single cell reads as a mistake; rebalance upwards.
    while rows > 1 and n % cols == 1 and cols > 2:
        cols -= 1
        rows = math.ceil(n / cols)
    return cols, rows


def _fit_font(draw, text, weight, size, max_w):
    """The largest size, stepping down, at which ``text`` fits ``max_w``."""
    while size > 10:
        font = plate_mod._font(weight, size)
        if draw.textlength(text, font=font) <= max_w:
            return font
        size -= 1
    return plate_mod._font(weight, 10)


def render_wall(projects, title, size=(1920, 1080), footer=None):
    """The wall as a full-frame RGBA image. Missing artwork never removes the
    name: a project whose logo did not rasterize still takes its cell."""
    from PIL import Image, ImageDraw

    width, height = size
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # The title, in the proportional face, tracked out like the house
    # eyebrow rows.
    f_title = _sans("bold", round(height * 0.048))
    tracking = 0.04 * f_title.size
    title_w = plate_mod._tracked_width(draw, title, f_title, 0.04)
    plate_mod._draw_tracked(
        draw, ((width - title_w) / 2, round(height * TITLE_Y)),
        title, f_title, WHITE, 0.04)
    rule_y = round(height * TITLE_Y) + f_title.size + round(height * 0.035)
    rule_half = (title_w / 2) + 40
    draw.line([(width / 2 - rule_half, rule_y), (width / 2 + rule_half, rule_y)],
              fill=(245, 248, 250, 90), width=2)

    n = len(projects)
    if not n:
        return img
    area_w = width * (1 - 2 * MARGIN_X)
    area_h = height * (GRID_BOTTOM - GRID_TOP)
    cols, rows = grid_shape(n, area_w, area_h)
    cell_w = area_w / cols
    cell_h = area_h / rows
    logo_h = min(round(height * 0.155), round(cell_h * 0.58))
    name_size = max(13, min(24, round(cell_h * 0.16)))

    origin_x = width * MARGIN_X
    origin_y = height * GRID_TOP
    for idx, project in enumerate(projects):
        row, col = divmod(idx, cols)
        # Centre a short last row.
        in_row = min(cols, n - row * cols)
        row_off = (cols - in_row) * cell_w / 2
        cx = origin_x + row_off + (col + 0.5) * cell_w
        cy = origin_y + (row + 0.5) * cell_h

        chip_w = cell_w * 0.86
        chip_h = logo_h * 1.18
        chip = Image.new("RGBA", (round(chip_w), round(chip_h)), (0, 0, 0, 0))
        chip_draw = ImageDraw.Draw(chip)
        chip_draw.rounded_rectangle([0, 0, chip.width - 1, chip.height - 1],
                                    radius=round(chip_h * 0.14), fill=CHIP)
        png = project.get("logo_png") or ""
        logo_path = REPO / png if png else None
        if logo_path and logo_path.exists():
            logo = Image.open(logo_path).convert("RGBA")
            scale = min((chip_h * 0.72) / logo.height,
                        (chip_w * 0.82) / logo.width)
            logo = logo.resize((max(1, round(logo.width * scale)),
                                max(1, round(logo.height * scale))),
                               Image.LANCZOS)
            chip.alpha_composite(logo, (round((chip_w - logo.width) / 2),
                                        round((chip_h - logo.height) / 2)))
        chip_xy = (round(cx - chip_w / 2), round(cy - chip_h / 2))
        img.alpha_composite(chip, chip_xy)
        name = project.get("name") or project["id"]
        f_name = _fit_font(draw, name, "regular", name_size, cell_w * 0.92)
        name_w = draw.textlength(name, font=f_name)
        name_y = chip_xy[1] + chip_h + round(cell_h * 0.07)
        draw.text((cx - name_w / 2, name_y), name, font=f_name, fill=DIM)

    if footer:
        # The way through to the landscape, owner-dictated 2026-08-24:
        # 'add a "landscape.cncf.io" url at the bottom so people know where
        # to go'. Mono and dim: it is an address, not a headline.
        f_foot = plate_mod._font("regular", round(height * 0.021))
        foot_w = draw.textlength(footer, font=f_foot)
        draw.text(((width - foot_w) / 2, round(height * 0.955)),
                  footer, font=f_foot, fill=DIM)
    return img


def load_projects(data_path=DATA):
    doc = json.loads(Path(data_path).read_text(encoding="utf-8"))
    for item in doc.get("unresolved") or []:
        print(f"wall: UNRESOLVED {item['what']}", file=sys.stderr)
    return list(doc.get("projects") or [])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", default=str(DATA))
    ap.add_argument("--title", required=True,
                    help="the authored card copy, passed through from the "
                         "chapter file's plate entry")
    ap.add_argument("--footer", default=None,
                    help="the address line under the grid, same pass-through")
    ap.add_argument("--fit-video", default=None,
                    help="match this video's frame size (default 1920x1080)")
    ap.add_argument("--size", default=None, metavar="WxH",
                    help="frame size, given rather than probed")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    if args.size:
        width, _, height = args.size.partition("x")
        size = (int(width), int(height))
    elif args.fit_video:
        size = video_size(args.fit_video)
    else:
        size = (1920, 1080)

    projects = load_projects(args.data)
    img = render_wall(projects, args.title, size, footer=args.footer)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f"wrote {out} ({len(projects)} project(s), {size[0]}x{size[1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
