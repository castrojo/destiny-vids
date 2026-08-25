#!/usr/bin/env python3
"""Act VII's Jupiter tail: the held frame, the company, the two cards.

Owner direction, 2026-08-23, verbatim (preserved in commit b9d9d03):

    "After the jupiter fade hold Jupiter and slice up Screenshot From
    2026-08-23 05-10-23.png for the characters and place them on the
    jupiter nightway. Try to make it dramatic. Then add in
    title-appropriate text

    For other wolves, some will give all

    Bluefin and the Forbidden Factory
    KubeCon + CloudNativeCon EU 2027
    Maintainer Summit

    Then roll the credits."

This renders the three things that direction needs, all regenerated on every
build -- existence is not freshness:

1. ``jupiter-hold.png`` -- a frame of the wrap video (the Jupiter/Europa
   nightway) carrying the three full-body figures from the owner's concept
   sheet, cut out and treated as WHITE-INK APPARITIONS: the sheet's pencil
   luminance keyed off its paper, recoloured to the act's plate ink, with a
   cool halo. The fourth figure on the sheet (a portrait bust) is dropped --
   a floating head reads as a mistake beside three full-body wolves.
2. ``plate_tail-dedication.png`` -- the memorial line, an RGBA overlay card.
3. ``plate_tail-event.png`` -- the event card, three lines, RGBA overlay.

The copy is the owner's, verbatim from the record's ``tail`` block, casing
included (KubeCon + CloudNativeCon are brand casing; the scream card's
uppercase homage is not this card). The cards keep their alpha: they ride
the cue plumbing as OVERLAYS on the held frame, never concatenated stills,
so the megacut skill's opaque-card red flag does not apply.

Degrades, never blocks: a missing or changed screenshot ships the BARE held
frame (the direction's first sentence stands alone) and records the gap on
stderr. Offline except one ffmpeg FRAME EXTRACTION (-ss, single frame) --
never an encode; the encode is the farm's.

    python3 scripts/build_europa_tail.py            # render all three
    python3 scripts/build_europa_tail.py --print    # report paths only
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import actbuild  # noqa: E402
from tools.render import find_ffmpeg  # noqa: E402

ACT = "VII"
SCRATCH = REPO_ROOT / "renders" / "act7-tail"  # gitignored intermediates

FRAME_W, FRAME_H = 1920, 1080
INK = (232, 238, 246)          # the house plate ink, matched to the pills
HALO = (150, 175, 215)         # the cold glow, figures and cards alike

# --- the cutout -----------------------------------------------------------
#
# The sheet is pencil on white paper with annotation labels wired to the
# figures by thin leader lines. The key is luminance (L < THRESH is ink).
# Two passes clean what a plain area filter cannot: erase rects take the
# labels that sit ON dark masses, and erase_thin_lines takes the leaders --
# including the segments that TOUCH a figure and so belong to its connected
# component -- by run geometry: a pixel dies if it sits in a run >= MIN_LEN
# along one axis and <= MAX_THICK across the other. Organic figure masses
# are thick in both directions and survive.

THRESH = 215
MIN_LEN, MAX_THICK = 25, 6
MIN_AREA = 300
GAIN = 1.8

FIGURES = {
    # crop on the 854x1279 sheet, then erase rects (sheet coords) holding
    # annotation text that sits ON dark masses and so survives area filtering
    "standing": {"crop": (20, 115, 445, 600), "erase": [
        (300, 118, 430, 162),    # KUBE OF DESTINY + leader head
        (28, 372, 115, 415),     # 2 LITERS HIDRATION BAG
        (88, 455, 235, 570),     # DIY HIPPERSHELL block
        (240, 538, 335, 568),    # PROVISION BAG
        (408, 438, 445, 452),    # katana-label leader stub
    ]},
    "kneeling": {"crop": (0, 590, 392, 1185), "erase": [
        (262, 995, 392, 1050),   # AI CORTOL MODULE WITH GPS, to the crop edge
        (170, 1015, 280, 1040),  # leader horizontal to that label
        (168, 860, 190, 1030),   # leader vertical above it
        (348, 1003, 425, 1016),  # leader horizontal, right of the figure
        (412, 1000, 424, 1095),  # leader vertical below it
        (95, 588, 108, 650),     # stray leader from the standing column
        (290, 1095, 392, 1185),  # crouching figure's overlap, bottom-right
    ]},
    "crouching": {"crop": (390, 620, 854, 1030), "erase": [
        (440, 628, 515, 695),    # GRAY WOLF'S HEAD
        (472, 695, 486, 762),    # its leader down to the cowl
        (680, 945, 854, 1015),   # HIDDEN MECHANICAL BLADE TUNGSTEN ALLOY
        (615, 975, 695, 990),    # its horizontal leader stub
        (520, 912, 548, 965),    # tungsten leader upper stub
        (528, 965, 590, 1035),   # tungsten leader lower run
    ]},
}

# Seating on the nightway, frozen on the composite review (renders/act7-tail/
# comp-3.png): the trio stands on the deck line in the starfield gap between
# Jupiter (left) and Europa (right), the standing figure a half-step upslope.
# Sizes are dramatic scale -- small against two worlds, not pasted over them.
PLACEMENT = [
    ("kneeling", 830, 330, 930),
    ("standing", 1130, 410, 916),
    ("crouching", 1470, 265, 930),
]


def erase_thin_lines(mask, min_len=MIN_LEN, max_thick=MAX_THICK):
    """Kill axis-aligned thin lines (leader lines, ruled paper): pixels in a
    run >= min_len along one axis and <= max_thick across the other."""
    import numpy as np
    m = mask.copy()
    h, w = m.shape
    hrun = np.zeros((h, w), np.int32)
    for y in range(h):
        x = 0
        while x < w:
            if m[y, x]:
                x0 = x
                while x < w and m[y, x]:
                    x += 1
                hrun[y, x0:x] = x - x0
            else:
                x += 1
    vrun = np.zeros((h, w), np.int32)
    for x in range(w):
        y = 0
        while y < h:
            if m[y, x]:
                y0 = y
                while y < h and m[y, x]:
                    y += 1
                vrun[y0:y, x] = y - y0
            else:
                y += 1
    kill = ((hrun >= min_len) & (vrun <= max_thick)) | \
           ((vrun >= min_len) & (hrun <= max_thick))
    m[kill] = False
    return m


def components(mask, min_area=MIN_AREA):
    """Keep only connected components of at least min_area pixels."""
    import numpy as np
    h, w = mask.shape
    lab = np.zeros((h, w), np.int32)
    cur = 0
    keep = set()
    for yy in range(h):
        for xx in range(w):
            if mask[yy, xx] and lab[yy, xx] == 0:
                cur += 1
                q = deque([(yy, xx)])
                lab[yy, xx] = cur
                n = 0
                while q:
                    cy, cx = q.popleft()
                    n += 1
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if (0 <= ny < h and 0 <= nx < w
                                and mask[ny, nx] and lab[ny, nx] == 0):
                            lab[ny, nx] = cur
                            q.append((ny, nx))
                if n >= min_area:
                    keep.add(cur)
    return np.isin(lab, list(keep))


def cutout(spec, sheet):
    """One figure as an RGBA white-ink apparition, from the sheet."""
    import numpy as np
    box = spec["crop"]
    g = np.array(sheet.crop(box)).astype(np.int32)
    x0, y0 = box[0], box[1]
    ink = 255 - g
    mask = g < THRESH
    for (ex0, ey0, ex1, ey1) in spec["erase"]:
        mask[ey0 - y0:ey1 - y0, ex0 - x0:ex1 - x0] = False
    mask = erase_thin_lines(mask)
    mask = components(mask)
    # dilate to catch the faint strokes attached to the kept masses
    km = Image.fromarray((mask * 255).astype(np.uint8)).filter(
        ImageFilter.MaxFilter(5))
    mask = np.array(km) > 0
    alpha = np.where(mask, np.clip(ink * GAIN, 0, 255), 0).astype(np.uint8)
    a = Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(0.6))
    out = Image.new("RGBA", (a.width, a.height), INK + (0,))
    out.putalpha(a)
    return out


# --- the composite ---------------------------------------------------------

def extract_frame(ffmpeg, wrap_path, at, out):
    """One frame of the wrap video. EXTRACTION ONLY -- never an encode."""
    cmd = [*ffmpeg, "-y", "-ss", f"{at:g}", "-i", str(wrap_path),
           "-frames:v", "1", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


def composite_hold(backdrop, sheet, out):
    """The held nightway frame with the company seated on the deck line."""
    frame = Image.open(backdrop).convert("RGBA")
    if frame.size != (FRAME_W, FRAME_H):
        frame = frame.resize((FRAME_W, FRAME_H), Image.LANCZOS)
    if sheet is not None:
        for name, cx, h, gy in PLACEMENT:
            fig = cutout(FIGURES[name], sheet)
            w = round(fig.width * h / fig.height)
            fig = fig.resize((w, h), Image.LANCZOS)
            halo = fig.filter(ImageFilter.GaussianBlur(4))
            r, g, b, a = halo.split()
            halo = Image.merge("RGBA", (
                Image.new("L", fig.size, HALO[0]),
                Image.new("L", fig.size, HALO[1]),
                Image.new("L", fig.size, HALO[2]),
                a.point(lambda p: int(p * 0.7))))
            x, y = cx - w // 2, gy - h
            frame.alpha_composite(halo, (x, y))
            frame.alpha_composite(fig, (x, y))
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.convert("RGB").save(out)
    return out


# --- the cards -------------------------------------------------------------
#
# Style lives here (chrome is the renderer's); the WORDS live in the record.
# Lines are styled by role: a dedication is one letterspaced serif-italic
# line; the event card tiers headline / sub-line / kicker. Both are RGBA
# overlays, transparent off the text, seated in the clean starfield above
# the company and clear of Jupiter's crescent.

FONTS = {
    "serif_italic": ["/usr/share/fonts/dejavu/DejaVuSerif-Italic.ttf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"],
    "sans_bold": ["/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "sans": ["/usr/share/fonts/dejavu/DejaVuSans.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}

# role: (font key, size, tracking, fill, y)
CARD_STYLE = {
    "tail-dedication": [("serif_italic", 64, 10, INK + (255,), 285)],
    "tail-event": [("sans_bold", 58, 6, INK + (255,), 240),
                   ("sans", 44, 8, (190, 200, 212, 255), 330),
                   ("sans", 38, 12, (160, 172, 186, 255), 400)],
}


def _font(kind, size):
    for p in FONTS[kind]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    raise SystemExit(f"no font found among {FONTS[kind]}")


def _draw_tracked(draw, cx, y, text, font, tracking, fill):
    """Letterspaced text, centred: per-character advance plus a fixed gap."""
    w = sum(draw.textlength(c, font=font) for c in text) \
        + tracking * (len(text) - 1)
    x = cx - w / 2
    for c in text:
        draw.text((x, y), c, font=font, fill=fill)
        x += draw.textlength(c, font=font) + tracking


def render_card(card, out):
    """One RGBA overlay card: the record's lines, this renderer's chrome."""
    layer = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    style = CARD_STYLE[card["id"]]
    if len(card["lines"]) != len(style):
        raise SystemExit(f"card {card['id']}: {len(card['lines'])} lines "
                         f"against {len(style)} styled rows -- the record "
                         "and the renderer disagree")
    for line, (kind, size, tracking, fill, y) in zip(card["lines"], style):
        _draw_tracked(d, FRAME_W // 2, y, line, _font(kind, size),
                      tracking, fill)
    # the same cool halo the figures carry, from the text's own alpha
    a = layer.split()[3]
    glow = Image.merge("RGBA", (
        Image.new("L", (FRAME_W, FRAME_H), HALO[0]),
        Image.new("L", (FRAME_W, FRAME_H), HALO[1]),
        Image.new("L", (FRAME_W, FRAME_H), HALO[2]),
        a.point(lambda p: int(p * 0.55))))
    glow = glow.filter(ImageFilter.GaussianBlur(6))
    out_im = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    out_im.alpha_composite(glow)
    out_im.alpha_composite(layer)
    out.parent.mkdir(parents=True, exist_ok=True)
    out_im.save(out)
    return out


# --- orchestration ----------------------------------------------------------

def render_tail(doc, project, plates_dir, ffmpeg=None):
    """Render the hold composite and both cards; return what was unresolved.

    Degrades, never blocks: a missing or changed screenshot ships the bare
    held frame and says so on stderr -- the direction's first sentence
    ("hold Jupiter") stands alone, and the gap is recorded, not hidden.
    """
    project = Path(project).expanduser()
    plates_dir = Path(plates_dir)
    tail = doc["tail"]
    hold = tail["hold"]
    unresolved = []

    src = hold.get("source_screenshot", {})
    sheet = None
    sheet_path = Path(src.get("path", "")).expanduser()
    if not sheet_path.exists():
        unresolved.append(
            "tail: source screenshot missing "
            f"({sheet_path}) -- the hold ships BARE, no company on the "
            "nightway. Restore the sheet and rebuild to seat the figures.")
    else:
        digest = hashlib.sha256(sheet_path.read_bytes()).hexdigest()
        if src.get("sha256") and digest != src["sha256"]:
            unresolved.append(
                "tail: source screenshot sha256 drifted "
                f"({digest[:12]}... != {src['sha256'][:12]}...) -- the "
                "figure crops were tuned on the recorded sheet; verify the "
                "composite before shipping.")
        sheet = Image.open(sheet_path).convert("L")

    wrap_rel = doc["picture"]["inputs"][hold["backdrop"]["from"]]
    wrap_path = (Path(wrap_rel).expanduser() if Path(wrap_rel).is_absolute()
                 else project / wrap_rel)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    backdrop = SCRATCH / "hold-backdrop.png"
    extract_frame(ffmpeg or find_ffmpeg(), wrap_path,
                  hold["backdrop"]["at"], backdrop)

    hold_out = project / hold["composite_out"]
    composite_hold(backdrop, sheet, hold_out)
    print(f"tail: hold composite -> {hold_out}", file=sys.stderr)

    for card in tail["cards"]:
        out = plates_dir / f"plate_{card['id']}.png"
        render_card(card, out)
        print(f"tail: card -> {out}", file=sys.stderr)

    for note in unresolved:
        print(f"build_europa_tail: {note}", file=sys.stderr)
    return unresolved


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", default=None,
                    help="where the footage lives (never committed)")
    ap.add_argument("--plates-dir", default=None)
    args = ap.parse_args(argv)
    doc, default_project, default_plates = actbuild.load_act(ACT)
    project = args.project or str(default_project)
    plates_dir = args.plates_dir or str(default_plates)
    render_tail(doc, project, plates_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
