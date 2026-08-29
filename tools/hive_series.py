#!/usr/bin/env python3
"""Season of the Blueberries: the season record and the cards it generates.

One source, twelve weekly episodes, one season cut. This module owns the
season manifest contract (`schema/hive-season.schema.json`), its validation,
and every card that can be rendered WITHOUT footage:

* the Expansion Pack opening CTA -- owner-authored copy, verbatim, on a
  KubeStellar-inspired three-panel card (Project Bluefin creative language,
  not an official-brand claim);
* one title slide per episode -- eyebrow, the publisher chapter headline
  unchanged, and the frozen candidate-1 lore subtitle;
* the Guardian dossier A contributor card -- a full uncropped square GitHub
  PFP beside a dark KubeStellar glass panel, factual fields only: display
  name (falling back to login), @login, and HIVE TASKS +N. No generated
  title, ever.

The fixed character plates are NOT drawn here: `tools/plate.py` is frozen in
Wolves delivery, so this module only builds plate.py-ready specs from the
manifest's source-evidenced seats (`plate_specs` / `plan_chapter_plates`).
A cast member whose plate copy is incomplete is omitted and recorded in
`unresolved` -- never rendered with a guessed row.

Faces come from the credits avatar cache through `tools.avatars`
(`fetch_declared_avatars` fills it; `resolve_face` reads it uncropped).
A login with no cached face renders the card without one and is reported as
an explicit unresolved entry. Avatar bytes are never committed.

    python3 tools/hive_series.py check           # validate the season manifest
    python3 tools/hive_series.py cards           # render the committed cards
    python3 tools/hive_series.py fetch-avatars   # warm the cache for the cast
    python3 tools/hive_series.py build 1         # one episode, farm-first
    python3 tools/hive_series.py build-all       # all twelve, verified
    python3 tools/hive_series.py cut             # the full-season join
    python3 tools/hive_series.py verify [N]      # probe delivered files

The episode build is ONE H.264/AAC encode per episode through
`tools.farm.run_encode` -- remote-first, memory-capped local fallback, never
a bare local run. The manifest's pinned source formats are fetched ONCE into
`media/hive/` and reused by every episode. Source seats and overlays are
converted to chapter-relative content time and offset by the front cards;
the authored source marks themselves never move. The full-season cut
concatenates the twelve episode streams without re-encoding.

Stdlib plus Pillow for the cards; ffmpeg work goes through tools/farm.py.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import avatars  # noqa: E402  (needs REPO_ROOT on sys.path first)
from tools import conform  # noqa: E402
from tools import farm  # noqa: E402
from tools import plate  # noqa: E402
from tools import render  # noqa: E402

SCHEMA = REPO_ROOT / "schema" / "hive-season.schema.json"
MANIFEST = REPO_ROOT / "stories" / "standalone" / "season-of-the-blueberries.json"

FRAME_W, FRAME_H = 1920, 1080

# The sha256 of the committed Expansion Pack card. Regenerating the card must
# reproduce these bytes exactly; a renderer change that is not a deliberate
# re-cut of owner copy fails the pin.
OPENING_CTA_SHA256 = "a96319cc13f1b8712e864f90cf1f29cc72017a947ee3cc905261d1e97cde3092"

# --- KubeStellar-inspired palette ------------------------------------------
# Project Bluefin creative language, not an official-brand claim. Green is a
# status accent only -- the HIVE TASKS tally dot and the #HIREAWOLF pill.
INK = (10, 15, 28)          # #0A0F1C near-black
INK_DEEP = (7, 11, 21)      # slightly darker, for the vertical falloff
BLUE = (26, 144, 255)       # #1A90FF
PURPLE = (99, 54, 255)      # #6236FF
CYAN = (0, 194, 255)        # #00C2FF, restrained
GREEN = (63, 185, 80)       # status accent only
GLASS = (13, 19, 36, 216)   # the dossier panel
TEXT = (245, 245, 245)
MUTED = (176, 190, 212)

FONT_CANDIDATES = {
    "regular": [
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/liberation-fonts/LiberationSans-Regular.ttf",
    ],
    "bold": [
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/liberation-fonts/LiberationSans-Bold.ttf",
    ],
    "oblique": [
        "/usr/share/fonts/dejavu/DejaVuSans-Oblique.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
        "/usr/share/fonts/liberation-fonts/LiberationSans-Italic.ttf",
    ],
}


def _font(weight, size):
    for path in FONT_CANDIDATES[weight]:
        if Path(path).exists():
            return ImageFont.truetype(path, int(round(size)))
    raise RuntimeError(
        f"no {weight} font found; tried {FONT_CANDIDATES[weight]}"
    )


# --- text primitives ---------------------------------------------------------

def _tracked_width(draw, text, font, tracking_em):
    extra = tracking_em * font.size
    return sum(draw.textlength(ch, font=font) + extra for ch in text)


def _draw_tracked(draw, xy, text, font, fill, tracking_em):
    x, y = xy
    extra = tracking_em * font.size
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + extra


def _gradient_stops(width, stops):
    """A 1xW horizontal gradient through ``stops`` ((pos, colour) pairs)."""
    row = Image.new("RGB", (width, 1))
    px = row.load()
    stops = sorted(stops)
    for x in range(width):
        t = x / max(1, width - 1)
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]
            p1, c1 = stops[i + 1]
            if p0 <= t <= p1:
                f = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
                px[x, 0] = tuple(round(a + (b - a) * f) for a, b in zip(c0, c1))
                break
        else:
            px[x, 0] = stops[0][1] if t < stops[0][0] else stops[-1][1]
    return row


def _gradient_text(text, font, stops, tracking_em=0.0):
    """Tracked text rendered through a horizontal gradient, as an RGBA tile."""
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    width = int(round(_tracked_width(probe, text, font, tracking_em)))
    ascent, descent = font.getmetrics()
    height = ascent + descent
    mask = Image.new("L", (width + 4, height + 4), 0)
    _draw_tracked(ImageDraw.Draw(mask), (2, 2), text, font, 255, tracking_em)
    gradient = _gradient_stops(mask.width, stops).resize(
        (mask.width, mask.height)
    )
    tile = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    tile.paste(gradient.convert("RGBA"), (0, 0), mask)
    return tile


def _wrap(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if current and draw.textlength(trial, font=font) > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def _wrap_hard(draw, text, font, max_width):
    """Word wrap that also splits a single token longer than the line.

    A real identity is never clipped or truncated: when no word boundary fits,
    the token breaks at the last character that does."""
    lines = []
    for line in _wrap(draw, text, font, max_width):
        while draw.textlength(line, font=font) > max_width:
            cut = len(line)
            while cut > 1 and draw.textlength(line[:cut], font=font) > max_width:
                cut -= 1
            lines.append(line[:cut])
            line = line[cut:]
        lines.append(line)
    return lines


def _line_height(font):
    return sum(font.getmetrics())


def _fit_text(draw, text, weight, max_size, min_size, max_width, max_height=None):
    """The fitted font and wrapped lines for ``text`` within ``max_width``.

    Shrink first: the largest size that keeps the text on ONE line wins.
    Only when even the floor cannot hold one line does the text wrap, at the
    largest size whose wrapped lines all fit. At the floor it hard-wraps
    instead of shrinking further: it never clips.

    ``max_height`` adds the vertical budget: a candidate whose lines stack
    taller than the budget loses to a smaller size, and a floor that still
    cannot fit raises ValueError -- an overflow is never returned."""
    for size in range(int(max_size), int(min_size) - 1, -1):
        font = _font(weight, size)
        if draw.textlength(text, font=font) <= max_width:
            if max_height is None or _line_height(font) <= max_height:
                return font, [text]
    for size in range(int(max_size), int(min_size) - 1, -1):
        font = _font(weight, size)
        lines = _wrap(draw, text, font, max_width)
        if not all(draw.textlength(line, font=font) <= max_width
                   for line in lines):
            continue
        lines = _wrap_hard(draw, text, font, max_width)
        if max_height is None or _line_height(font) * len(lines) <= max_height:
            return font, lines
    font = _font(weight, min_size)
    lines = _wrap_hard(draw, text, font, max_width)
    if max_height is not None and _line_height(font) * len(lines) > max_height:
        raise ValueError(
            f"text does not fit {max_width}x{max_height}px even at the "
            f"minimum font size {min_size}: {text[:60]!r}"
        )
    return font, lines


def _centered(draw, cx, y, text, font, fill):
    draw.text(
        (cx - draw.textlength(text, font=font) / 2, y), text, font=font, fill=fill
    )


def _centered_tracked(draw, cx, y, text, font, fill, tracking_em):
    width = _tracked_width(draw, text, font, tracking_em)
    _draw_tracked(draw, (cx - width / 2, y), text, font, fill, tracking_em)


def _centered_gradient(img, cx, y, text, font, stops, tracking_em=0.0):
    tile = _gradient_text(text, font, stops, tracking_em)
    img.alpha_composite(tile, (int(round(cx - tile.width / 2)), int(round(y))))


# --- the shared backdrop -----------------------------------------------------

def _backdrop():
    """Near-black vertical falloff with a faint blue dot grid."""
    column = Image.new("RGB", (1, FRAME_H))
    px = column.load()
    for y in range(FRAME_H):
        f = y / (FRAME_H - 1)
        px[0, y] = tuple(round(a + (b - a) * f) for a, b in zip(INK, INK_DEEP))
    img = column.resize((FRAME_W, FRAME_H)).convert("RGBA")
    grid = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(grid)
    step = 64
    for gx in range(step // 2, FRAME_W, step):
        for gy in range(step // 2, FRAME_H, step):
            draw.ellipse(
                [gx - 1, gy - 1, gx + 1, gy + 1], fill=BLUE + (16,)
            )
    img.alpha_composite(grid)
    return img


def _edge_frame(draw, inset=24):
    """The blue-purple double rule every full-frame Hive card carries."""
    draw.rectangle(
        [inset, inset, FRAME_W - inset - 1, FRAME_H - inset - 1],
        outline=PURPLE + (200,), width=3,
    )
    draw.rectangle(
        [inset + 8, inset + 8, FRAME_W - inset - 9, FRAME_H - inset - 9],
        outline=BLUE + (140,), width=1,
    )


def _hairline(img, y, x0=200, x1=FRAME_W - 200, height=3):
    """A blue-to-purple gradient rule."""
    line = _gradient_stops(x1 - x0, [(0.0, BLUE), (1.0, PURPLE)]).resize(
        (x1 - x0, height)
    )
    img.alpha_composite(line.convert("RGBA"), (x0, y))


# --- the Expansion Pack opening CTA ------------------------------------------

def render_opening_cta(lines):
    """The owner-authored Expansion Pack card, 1920x1080.

    Three panels, six lines, in the owner's order -- the copy is reproduced
    verbatim and nothing is added to it. Everything else on the card is
    chrome: the grid, the rules, the gradients.
    """
    if len(lines) != 6:
        raise ValueError(f"the Expansion Pack card is exactly 6 lines, got {len(lines)}")
    img = _backdrop()
    draw = ImageDraw.Draw(img)
    _edge_frame(draw)

    f_hero = _font("bold", 84)
    f_big = _font("bold", 64)
    f_mid = _font("bold", 52)
    f_body = _font("regular", 40)
    f_tag = _font("bold", 72)

    # Panel 1: the promise and the event.
    _centered_gradient(
        img, FRAME_W / 2, 120, lines[0], f_hero,
        [(0.0, BLUE), (1.0, CYAN)],
    )
    _centered_tracked(draw, FRAME_W / 2, 258, lines[1], f_mid, TEXT, 0.08)
    _hairline(img, 356)

    # Panel 2: the ask and the offer.
    _centered_gradient(
        img, FRAME_W / 2, 420, lines[2], f_big,
        [(0.0, PURPLE), (1.0, BLUE)],
    )
    for i, wrapped in enumerate(_wrap(draw, lines[3], f_body, 1400)):
        _centered(draw, FRAME_W / 2, 540 + i * 52, wrapped, f_body, MUTED)
    _hairline(img, 716)

    # Panel 3: the people line, then the tag as the card's one status accent.
    for i, wrapped in enumerate(_wrap(draw, lines[4], f_body, 1400)):
        _centered(draw, FRAME_W / 2, 780 + i * 52, wrapped, f_body, MUTED)
    tag = lines[5]
    tag_font = f_tag
    dot = 22
    gap = 28
    tag_w = draw.textlength(tag, font=tag_font)
    x = FRAME_W / 2 - (dot + gap + tag_w) / 2
    cy = 962
    draw.ellipse([x, cy - dot / 2, x + dot, cy + dot / 2], fill=GREEN + (255,))
    draw.text((x + dot + gap, cy - tag_font.size * 0.72), tag, font=tag_font,
              fill=TEXT)
    return img


# --- the episode title slide ---------------------------------------------------

def eyebrow(manifest, chapter):
    return manifest["title_slide"]["eyebrow_template"].format(
        roman=chapter["roman"]
    )


def title_slide_filename(chapter):
    return f"s01e{chapter['number']:02d}-{chapter['slug']}.png"


def render_title_slide(manifest, chapter):
    """One episode's title slide: eyebrow, publisher headline, frozen lore
    subtitle. Five seconds, full frame, nothing else on it."""
    img = _backdrop()
    draw = ImageDraw.Draw(img)
    _edge_frame(draw)

    # The left edge bar: blue at the top falling to purple.
    bar = _gradient_stops(FRAME_H - 200, [(0.0, BLUE), (1.0, PURPLE)]).resize(
        (12, FRAME_H - 200)
    )
    img.alpha_composite(bar.convert("RGBA"), (96, 100))

    f_eyebrow = _font("bold", 34)
    f_head = _font("bold", 120)
    f_sub = _font("regular", 46)

    x = 160
    _draw_tracked(draw, (x, 400), eyebrow(manifest, chapter), f_eyebrow,
                  CYAN + (255,), 0.18)
    draw.text((x - 6, 470), chapter["headline"], font=f_head, fill=TEXT)
    _hairline(img, 660, x0=160, x1=160 + 560)
    draw.text((x, 710), chapter["subtitle"]["text"], font=f_sub, fill=MUTED)
    return img


# --- Guardian dossier A ---------------------------------------------------------

# The dossier panel geometry and its text-fit contract. The name and handle
# shrink from their display sizes down to a tested floor and wrap -- a real
# identity is never clipped, truncated, or drawn outside the panel.
DOSSIER_PANEL = (960, 330, 810, 420)  # x, y, width, height
DOSSIER_TEXT_X = DOSSIER_PANEL[0] + 56
DOSSIER_TEXT_WIDTH = DOSSIER_PANEL[2] - 112
DOSSIER_NAME_SIZE = 68
DOSSIER_NAME_MIN = 26
DOSSIER_HANDLE_SIZE = 40
DOSSIER_HANDLE_MIN = 20
DOSSIER_ROW_GAP = 12
# The hairline and the task row under it are fixed chrome at these offsets
# below the panel top. Name and handle rows live ABOVE the hairline -- that
# is the vertical budget the fit below is held to, not only the width.
DOSSIER_TEXT_AREA_TOP = 44
DOSSIER_HAIRLINE = 250


def dossier_fields(snapshot):
    """The factual GitHub identity rows for a dossier card. Nothing else.

    The display name falls back to the login when GitHub's is empty; the
    tally is rendered as ``HIVE TASKS +N``. A generated title is never added.
    """
    name = (snapshot.get("name") or "").strip() or snapshot["login"]
    return {
        "name": name,
        "handle": f"@{snapshot['login']}",
        "tasks": f"HIVE TASKS +{int(snapshot['tasks'])}",
    }


def resolve_face(login):
    """The cached GitHub PFP for ``login``, square and UNCROPPED, or None.

    Reads the credits avatar cache through `tools.avatars` so a test
    redirecting the cache redirects this too. Unlike `tools.credits.avatar`
    this never circle-crops: Guardian dossier A shows the full profile image,
    letterboxed if it is not square.
    """
    if not login:
        return None
    path = avatars.avatar_dir() / f"{login}.png"
    if not path.exists() or path.stat().st_size < avatars.MIN_BYTES:
        return None
    try:
        img = Image.open(path)
        img.load()
    except OSError:
        return None
    return img.convert("RGB")


def _fit_entire(face, tile):
    """Scale ``face`` so it covers the ``tile`` square in its long dimension,
    aspect ratio preserved. Small PFPs are UPSCALED to fill the tile; nothing
    is ever cropped -- the short dimension is letterboxed by the caller."""
    w, h = face.size
    if w >= h:
        size = (tile, max(1, round(h * tile / w)))
    else:
        size = (max(1, round(w * tile / h)), tile)
    if size == face.size:
        return face.copy()
    return face.resize(size, Image.LANCZOS)


def dossier_text_layout(fields):
    """The name/handle rows for the dossier panel: ``(x, y, text, font,
    fill)`` tuples, fitted and wrapped so every row's bounding box stays
    inside the panel AND above the hairline. The block is centred in that
    area; the tally row below the hairline is fixed chrome.

    The budget is shared: the handle fits first at its own contract, the
    name takes what remains, and only when the name's floor still cannot fit
    does the handle give up a step. An identity that cannot fit even then
    raises ValueError -- a real name is never clipped, truncated, or drawn
    across the hairline over the task row."""
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    px, py, pw, ph = DOSSIER_PANEL
    area_top = py + DOSSIER_TEXT_AREA_TOP
    area_bottom = py + DOSSIER_HAIRLINE - 6
    budget = area_bottom - area_top

    name_rows = handle_rows = None
    for handle_cap in range(DOSSIER_HANDLE_SIZE, DOSSIER_HANDLE_MIN - 1, -1):
        handle_font, handle_lines = _fit_text(
            probe, fields["handle"], "regular",
            handle_cap, DOSSIER_HANDLE_MIN, DOSSIER_TEXT_WIDTH,
        )
        remaining = (
            budget - DOSSIER_ROW_GAP
            - _line_height(handle_font) * len(handle_lines)
        )
        try:
            name_font, name_lines = _fit_text(
                probe, fields["name"], "bold",
                DOSSIER_NAME_SIZE, DOSSIER_NAME_MIN, DOSSIER_TEXT_WIDTH,
                max_height=remaining,
            )
        except ValueError:
            continue  # the handle gives up a step so the name can fit
        name_rows = [(line, name_font) for line in name_lines]
        handle_rows = [(line, handle_font) for line in handle_lines]
        break
    if name_rows is None:
        raise ValueError(
            "dossier identity cannot fit the panel text area above the "
            f"hairline, even at the minimum sizes "
            f"({DOSSIER_NAME_MIN}/{DOSSIER_HANDLE_MIN}): "
            f"{fields['name']!r} / {fields['handle']!r}"
        )
    rows = [(text, font, TEXT) for text, font in name_rows]
    rows += [(text, font, CYAN + (255,)) for text, font in handle_rows]

    heights = [_line_height(font) for _text, font, _fill in rows]
    block_h = sum(heights) + DOSSIER_ROW_GAP
    y = area_top + (budget - block_h) // 2
    layout = []
    for i, (text, font, fill) in enumerate(rows):
        if i == len(name_rows):
            y += DOSSIER_ROW_GAP
        layout.append((DOSSIER_TEXT_X, y, text, font, fill))
        y += heights[i]
    return layout


def render_dossier(snapshot, face=None):
    """A full-frame Guardian dossier A recognition card, 1920x1080.

    Returns ``(image, unresolved)``: a missing face renders the card with an
    empty frame and is recorded -- the card ships, the gap is the punch list.
    Dossiers are full-frame cards before the chapter; they never overlay a
    body, because a dossier must not imply the person inhabits one.
    """
    fields = dossier_fields(snapshot)
    unresolved = []
    img = _backdrop()
    draw = ImageDraw.Draw(img)

    # Left: the full PFP, fit entire and letterboxed -- never cropped.
    tile = 720
    tx, ty = 150, (FRAME_H - tile) // 2
    draw.rectangle(
        [tx - 5, ty - 5, tx + tile + 4, ty + tile + 4],
        outline=PURPLE + (220,), width=3,
    )
    draw.rectangle(
        [tx - 1, ty - 1, tx + tile, ty + tile],
        outline=BLUE + (160,), width=1,
    )
    draw.rectangle([tx, ty, tx + tile - 1, ty + tile - 1], fill=INK_DEEP + (255,))
    if face is not None:
        fitted = _fit_entire(face, tile)
        fx = tx + (tile - fitted.width) // 2
        fy = ty + (tile - fitted.height) // 2
        img.paste(fitted.convert("RGB"), (fx, fy))
    else:
        unresolved.append(
            {"login": snapshot["login"], "reason": "no cached GitHub avatar"}
        )
        cx, cy, r = tx + tile // 2, ty + tile // 2, tile // 4
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     outline=BLUE + (90,), width=6)

    # Right: the dark glass panel with the blue-purple edge.
    px, py, pw, ph = DOSSIER_PANEL
    draw.rounded_rectangle([px, py, px + pw, py + ph], radius=18,
                           fill=PURPLE + (255,))
    draw.rounded_rectangle([px + 3, py + 3, px + pw - 3, py + ph - 3],
                           radius=16, fill=BLUE + (255,))
    draw.rounded_rectangle([px + 5, py + 5, px + pw - 5, py + ph - 5],
                           radius=14, fill=GLASS)

    f_tasks = _font("bold", 44)
    tx0 = px + 56
    for x, y, text, font, fill in dossier_text_layout(fields):
        draw.text((x, y), text, font=font, fill=fill)
    _hairline(img, py + DOSSIER_HAIRLINE, x0=tx0, x1=px + pw - 56, height=2)
    dot = 20
    dy = py + 306
    draw.ellipse([tx0, dy, tx0 + dot, dy + dot], fill=GREEN + (255,))
    draw.text((tx0 + dot + 24, dy - 16), fields["tasks"], font=f_tasks,
              fill=TEXT)
    return img, unresolved


# --- the fixed cast: specs for tools/plate.py -----------------------------------

PLATE_COPY_FIELDS = ("label", "class", "name", "title", "variant")
REQUIRED_PLATE_FIELDS = ("label", "name", "title")


def _plate_spec(member, seat):
    spec = {
        "id": f"{member['id']}-ch{seat['chapter']}",
        "at": seat["source_at"],
        "dur": seat["dur"],
        "position": "left",
        "why": seat["why"],
    }
    for field in PLATE_COPY_FIELDS:
        if field in member["plate"]:
            spec[field] = member["plate"][field]
    # The face rides as the cache path; plate.py draws its crest when the
    # file is not there. Avatar bytes are never committed.
    spec["avatar"] = f"renders/avatars/{member['github_login']}.png"
    return spec


def _missing_plate_copy(member):
    """The required plate copy fields a cast member is missing."""
    return [f for f in REQUIRED_PLATE_FIELDS
            if not member.get("plate", {}).get(f)]


def _incomplete_plate_entry(member, missing):
    return {
        "cast": member["id"],
        "reason": "plate copy incomplete: missing " + ", ".join(missing),
    }


def plate_specs(manifest):
    """The fixed-cast seats as plate.py-ready specs, plus what was withheld.

    Returns ``(specs, unresolved)``. A cast member whose plate copy is
    incomplete is omitted and recorded in ``unresolved`` -- the same rule
    `plan_chapter_plates` applies per chapter, so the validated manifest
    path can never hand plate.py a plate it must not draw. An unsupported
    plate is never rendered, because a plate placed without evidence is a
    claim about a real person."""
    specs, unresolved = [], []
    for member in manifest["fixed_cast"]:
        missing = _missing_plate_copy(member)
        if missing:
            if member["seats"]:
                unresolved.append(_incomplete_plate_entry(member, missing))
            continue
        specs.extend(_plate_spec(member, seat) for seat in member["seats"])
    return specs, unresolved


def plan_chapter_plates(manifest, number):
    """The plates seated in one chapter, plus what could not be seated.

    A cast member missing required plate copy is omitted and recorded in
    ``unresolved`` -- an unsupported plate is never rendered, because a plate
    placed without evidence is a claim about a real person.
    """
    plates, unresolved = [], []
    for member in manifest["fixed_cast"]:
        missing = _missing_plate_copy(member)
        seats = [s for s in member["seats"] if s["chapter"] == number]
        if missing:
            if seats:
                unresolved.append(_incomplete_plate_entry(member, missing))
            continue
        plates.extend(_plate_spec(member, seat) for seat in seats)
    plates.sort(key=lambda spec: spec["at"])
    return plates, unresolved


def declared_avatar_logins(manifest):
    """The GitHub logins whose faces the season renders."""
    return [member["github_login"] for member in manifest["fixed_cast"]]


def fetch_declared_avatars(manifest, **kwargs):
    """Warm the credits avatar cache for the fixed cast. Never raises, never
    blocks: what cannot be fetched renders as the drawn crest and is reported
    as missing."""
    return avatars.fetch(declared_avatar_logins(manifest), **kwargs)


# --- Task 3: episode and season builds ------------------------------------------
#
# One episode is ONE encode: the Expansion Pack CTA (10s, silent), the title
# slide (5s, silent), zero-to-three dossier cards (4s each, silent), the
# manifest's source chapter with its own audio, and the closing training CTA
# (10s, silent) -- joined inside one filtergraph and encoded once through
# tools.farm.run_encode. The full-season cut concatenates the twelve
# episodes' matching streams without re-encoding.

# The manifest-pinned source (formats 137+251) is fetched ONCE into this
# gitignored cache and reused by every episode.
SOURCE_CACHE_DIR = REPO_ROOT / "media" / "hive"
# Rendered dossier/plate/overlay PNGs and unresolved sidecars; gitignored.
WORK_DIR = REPO_ROOT / "renders" / "hive"

DOSSIER_DURATION = 4.0
# The owner overlays author copy and placement but no hold; the hold is a
# tooling default, clamped so the card never outruns its chapter window.
LORE_OVERLAY_DUR = 6.0

SAMPLE_RATE = 48000
AUDIO_LAYOUT = "stereo"
AUDIO_BITRATE = "320k"

# farm.SEAM_TOLERANCE_S is the encode-side check; verification allows the
# same per-episode seam, and the aggregate of twelve of them on the cut.
EPISODE_TOLERANCE_S = 0.5
CUT_TOLERANCE_S = 2.0

THUMBNAIL_MAX_BYTES = 2 * 1024 * 1024
FULL_CUT_NAME = "season-01-full.mp4"

# The same client standalone.py measured for the pinned progressive-free
# format list: `visionos` lists the full AVC + non-DRC 48 kHz Opus ladder.
PLAYER_CLIENT = "visionos"


def _t(value):
    """A filtergraph time: enough decimals to be exact, none to be noise.
    Whole seconds print bare -- ``36``, not ``36.0``."""
    text = f"{float(value):.3f}".rstrip("0")
    return text[:-1] if text.endswith(".") else text


def chapter_by_number(manifest, number):
    matches = [c for c in manifest["chapters"] if c["number"] == number]
    if len(matches) != 1:
        raise KeyError(
            f"expected one chapter numbered {number}, found {len(matches)}")
    return matches[0]


def episode_slug(chapter):
    return f"s01e{chapter['number']:02d}-{chapter['slug']}"


def episode_output_path(chapter):
    return Path(chapter["output"]).expanduser()


def thumbnail_output_path(chapter):
    return Path(chapter["thumbnail_output"]).expanduser()


def full_cut_path(manifest):
    """The season cut sits beside the episodes the manifest delivers."""
    return episode_output_path(manifest["chapters"][0]).parent / FULL_CUT_NAME


# --- fetching the source, once ----------------------------------------------------

def source_cache_path(manifest, cache_dir=None):
    """The ONE cached source file, keyed by the video id -- never by episode."""
    cache = Path(cache_dir) if cache_dir is not None else SOURCE_CACHE_DIR
    return cache / f"{manifest['source']['youtube_id']}.mkv"


def source_fetch_command(manifest, out):
    """The yt-dlp argv for the manifest's PINNED formats.

    Nothing here is "best": both format ids come from the manifest, so a
    rebuild months from now takes the same bitstreams. The audio format is
    never a -drc variant, so the sound arrives at its native rate with its
    dynamics intact (the same posture standalone.py's fetcher takes)."""
    source = manifest["source"]
    return [
        "yt-dlp",
        "--extractor-args", f"youtube:player_client={PLAYER_CLIENT}",
        "--no-playlist",
        "--no-part",
        "-f", f"{source['video_format_id']}+{source['audio_format_id']}",
        "--merge-output-format", "mkv",
        "-o", str(Path(out).resolve()),
        source["url"],
    ]


def ensure_source(manifest, cache_dir=None, runner=subprocess.run):
    """The downloaded season source, fetched once and kept.

    The only step in this module that reaches the network. A non-empty file
    already on disk is the evidence it ran, so it is never re-fetched --
    twelve episodes, one download."""
    out = source_cache_path(manifest, cache_dir).resolve()
    if out.exists() and out.stat().st_size > 0:
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    runner(source_fetch_command(manifest, out), check=True)
    return out


# --- the episode timeline -----------------------------------------------------------

def episode_segments(manifest, chapter):
    """One episode's ordered beats: the authored card sequence, the chapter,
    the closing card. Stills carry their committed asset; dossier segments
    carry the snapshot their card is rendered from at build time."""
    segments = [
        {"kind": "opening_cta",
         "asset": REPO_ROOT / manifest["opening_cta"]["asset"],
         "dur": float(manifest["opening_cta"]["duration"]),
         "audio": "silent"},
        {"kind": "title_slide",
         "asset": (REPO_ROOT / manifest["title_slide"]["output_dir"]
                   / title_slide_filename(chapter)),
         "dur": float(manifest["title_slide"]["duration"]),
         "audio": "silent"},
    ]
    for snapshot in chapter.get("dossiers") or []:
        segments.append({"kind": "dossier", "snapshot": snapshot,
                         "dur": DOSSIER_DURATION, "audio": "silent"})
    segments.append({"kind": "chapter",
                     "start": float(chapter["start"]),
                     "end": float(chapter["end"]),
                     "audio": "source"})
    segments.append({"kind": "closing_cta",
                     "asset": REPO_ROOT / manifest["closing_cta"]["asset"],
                     "dur": float(manifest["closing_cta"]["duration"]),
                     "audio": "silent"})
    return segments


def front_cards_duration(manifest, chapter):
    """Everything before the chapter: the offset source marks shift by."""
    return sum(float(s["dur"]) for s in episode_segments(manifest, chapter)
               if s["kind"] != "chapter") - \
        float(manifest["closing_cta"]["duration"])


def source_to_chapter_relative(at, chapter):
    """Absolute source time -> chapter-relative content time.

    The authored source mark never moves; only the ruler it is read against
    changes."""
    return float(at) - float(chapter["start"])


def source_to_episode_time(at, manifest, chapter):
    """Absolute source time -> where it lands in the finished episode."""
    return source_to_chapter_relative(at, chapter) + \
        front_cards_duration(manifest, chapter)


def episode_expected_duration(manifest, chapter):
    return sum(float(s["dur"]) for s in episode_segments(manifest, chapter)
               if s["kind"] != "chapter") + \
        float(chapter["end"]) - float(chapter["start"])


def cut_expected_duration(manifest):
    return sum(episode_expected_duration(manifest, c)
               for c in manifest["chapters"])


def episode_plan(manifest, number):
    """Everything one episode build needs, in chapter-relative time.

    Plates come from `plan_chapter_plates` (the omission rule included) and
    the owner overlays join them; every `at` is source time minus the
    chapter start, so the graph seats them on the trimmed chapter leg and
    the front cards' offset falls out of the concat for free. A seat whose
    copy is incomplete, and an overlay whose position this renderer does
    not know, are recorded in `unresolved` and never drawn."""
    chapter = chapter_by_number(manifest, number)
    plates, unresolved = plan_chapter_plates(manifest, number)
    for spec in plates:
        spec["at"] = source_to_chapter_relative(spec["at"], chapter)
    overlays = []
    for overlay in manifest.get("overlays") or []:
        if overlay["chapter"] != number:
            continue
        if overlay["position"] not in LORE_POSITIONS:
            unresolved.append({
                "id": overlay["id"],
                "reason": f"position {overlay['position']!r} is not one of "
                          f"{sorted(LORE_POSITIONS)}; the overlay is omitted "
                          "rather than placed by a guess",
            })
            continue
        at = source_to_chapter_relative(overlay["source_at"], chapter)
        window = float(chapter["end"]) - float(chapter["start"])
        overlays.append({
            "id": overlay["id"],
            "lines": list(overlay["lines"]),
            "position": overlay["position"],
            "at": at,
            "dur": min(LORE_OVERLAY_DUR, window - at),
        })
    return {
        "chapter": chapter,
        "segments": episode_segments(manifest, chapter),
        "plates": plates,
        "overlays": overlays,
        "unresolved": unresolved,
        "front_offset": front_cards_duration(manifest, chapter),
        "expected_duration": episode_expected_duration(manifest, chapter),
    }


# --- the project-lore overlays ---------------------------------------------------------

# The positions this renderer knows how to seat. Anything else is recorded
# and omitted, never guessed.
LORE_POSITIONS = ("bottom-right", "top-third")


def render_lore_overlay(overlay):
    """One owner-authored project-lore overlay, as a tight RGBA card.

    The card carries the authored lines VERBATIM and nothing else -- no
    label, no eyebrow, no generated word. The chrome is the season's own:
    the dark glass panel with the blue-purple edge."""
    lines = list(overlay["lines"])
    font = _font("bold", 40)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    pad_x, pad_y, gap = 36, 24, 10
    line_h = _line_height(font)
    width = max(int(round(probe.textlength(line, font=font)))
                for line in lines) + 2 * pad_x
    height = len(lines) * line_h + (len(lines) - 1) * gap + 2 * pad_y
    card = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=14,
                           fill=PURPLE + (255,))
    draw.rounded_rectangle([2, 2, width - 3, height - 3], radius=12,
                           fill=BLUE + (255,))
    draw.rounded_rectangle([4, 4, width - 5, height - 5], radius=10,
                           fill=GLASS)
    y = pad_y
    for line in lines:
        draw.text((pad_x, y), line, font=font, fill=TEXT)
        y += line_h + gap
    return card


def place_lore_overlay(card, position, picture=None):
    """Composite a lore card onto a full 1920x1080 transparent frame.

    ``bottom-right`` mirrors the plate lane's margins on the RIGHT, so the
    card stays clear of the heroes' lower-left plates. ``top-third`` centres
    the card on the picture in the caption lane, inside the top third. Both
    measure against the PICTURE rect, so a letterboxed source keeps the card
    on the image rather than on a matte."""
    frame = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    px, py, pw, ph = picture or (0, 0, FRAME_W, FRAME_H)
    if position == "bottom-right":
        x = px + pw - int(pw * 0.05) - card.width
        y = py + int(ph * 0.90) - card.height
    elif position == "top-third":
        x = px + (pw - card.width) // 2
        y = py + int(ph * 0.06)
    else:
        raise ValueError(f"unknown lore overlay position {position!r}")
    frame.alpha_composite(card, (x, y))
    return frame


# --- the dossier safe fallback -----------------------------------------------------------


def render_dossier_safely(snapshot, face=None):
    """render_dossier, with the deferred safe fallback for a pathological
    GitHub display name: the verified login stands in for the name row and
    the substitution is recorded -- the card ships, the gap is the punch
    list. The build never aborts on a name that cannot fit."""
    try:
        return render_dossier(snapshot, face=face)
    except ValueError as exc:
        fallback = dict(snapshot, name="")
        img, unresolved = render_dossier(fallback, face=face)
        unresolved.append({
            "login": snapshot["login"],
            "reason": f"display name cannot fit the dossier panel ({exc}); "
                      "the verified login stands in",
        })
        return img, unresolved


# --- the one-pass filtergraph ------------------------------------------------------------


def episode_filtergraph(plan, source_rate=SAMPLE_RATE):
    """One graph for one episode: the stills, the chapter, one concat.

    Input order is the fixed contract with `encode_episode_command`: input 0
    is the source, the stills follow in segment order, and the overlay PNGs
    (fixed plates, then lore overlays) come last. Every still and overlay is
    a looped -- infinite -- input; the stills are trimmed to their authored
    durations and the overlays carry ``shortest=1``, so the finite chapter
    leg decides where the file ends.

    The chapter's audio is the source's own, trimmed on the same boundary
    and pinned to the delivery layout; aresample joins the chain ONLY when
    the source's rate is not already the delivery rate (megacut's rule)."""
    chain = conform.video_filter_chain()
    stills = [s for s in plan["segments"] if s["kind"] != "chapter"]
    chapter = next(s for s in plan["segments"] if s["kind"] == "chapter")
    overlays = [dict(p, overlay_kind="plate") for p in plan["plates"]] + \
        [dict(o, overlay_kind="lore") for o in plan["overlays"]]
    aformat = f"aformat=sample_fmts=fltp:channel_layouts={AUDIO_LAYOUT}"

    parts = []
    concat_inputs = []
    for index, segment in enumerate(stills):
        # Chapter segments sit among the stills in episode order, so the
        # still's INPUT index is its position among stills only; the concat
        # order below is the segment order.
        input_index = 1 + index
        parts.append(
            f"[{input_index}:v]trim=duration={_t(segment['dur'])},{chain}"
            f"[s{index}v]")
        parts.append(
            f"anullsrc=r={SAMPLE_RATE}:cl={AUDIO_LAYOUT},"
            f"atrim=duration={_t(segment['dur'])},asetpts=PTS-STARTPTS,"
            f"{aformat}[s{index}a]")
    start, end = _t(chapter["start"]), _t(chapter["end"])
    parts.append(f"[0:v]trim=start={start}:end={end},{chain}[cv0]")
    resample = (f"aresample={SAMPLE_RATE}," if source_rate is None
                or int(source_rate) != SAMPLE_RATE else "")
    parts.append(
        f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS,"
        f"{resample}{aformat}[cha]")

    current = "[cv0]"
    for position, overlay in enumerate(overlays):
        input_index = 1 + len(stills) + position
        last = position == len(overlays) - 1
        label = "[chv]" if last else f"[cv{position + 1}]"
        begin = float(overlay["at"])
        stop = begin + float(overlay["dur"])
        parts.append(
            f"{current}[{input_index}:v]overlay=0:0:"
            f"enable='between(t,{_t(begin)},{_t(stop)})':shortest=1{label}")
        current = label
    if not overlays:
        parts.append("[cv0]null[chv]")

    # The concat order is the EPISODE order: the stills before the chapter,
    # then the chapter, then the stills after it.
    before, after = [], []
    seen_chapter = False
    still_index = 0
    for segment in plan["segments"]:
        if segment["kind"] == "chapter":
            seen_chapter = True
            continue
        (after if seen_chapter else before).append(still_index)
        still_index += 1
    for index in before:
        concat_inputs += [f"[s{index}v]", f"[s{index}a]"]
    concat_inputs += ["[chv]", "[cha]"]
    for index in after:
        concat_inputs += [f"[s{index}v]", f"[s{index}a]"]
    parts.append(
        f"{''.join(concat_inputs)}concat=n={len(plan['segments'])}:v=1:a=1"
        f"[outv][outa]")
    return ";".join(parts)


def encode_episode_command(ffmpeg, source, stills, overlays, graph, out):
    """The one argv: decode the source once, loop the PNGs, encode once.

    The video recipe is the delivery spec's own (conform.video_encode_args)
    so an episode's bitstream is what the full cut's concat can join blind;
    the sound is one AAC generation at the delivery rate."""
    argv = [*ffmpeg, "-v", "error", "-y", "-i", str(source)]
    for still in stills:
        argv += ["-loop", "1", "-framerate", conform.DELIVERY.fps,
                 "-i", str(still)]
    for overlay in overlays:
        argv += ["-loop", "1", "-framerate", conform.DELIVERY.fps,
                 "-i", str(overlay)]
    argv += [
        "-filter_complex", graph,
        "-map", "[outv]",
        "-map", "[outa]",
        *conform.video_encode_args(),
        "-c:a", "aac",
        "-b:a", AUDIO_BITRATE,
        "-ar", str(SAMPLE_RATE),
        "-movflags", "+faststart",
        str(out),
    ]
    return argv


def encode_episode(argv, *, inputs, out, expected_duration, local=False,
                   label=None):
    """The episode's one encode, on the farm whenever the farm answers.

    The posture is tools/farm.py's, taken identically by every builder:
    cluster when reachable, memory-capped local with the reason printed
    otherwise, ``--local`` as the explicit escape hatch."""
    return farm.run_encode(
        argv, inputs=inputs, out=out, local=local,
        expected_duration=expected_duration,
        label=label or "Hive episode")


# --- thumbnails -------------------------------------------------------------------------


def make_thumbnail(slide_path, out_path):
    """The episode's thumbnail: its committed title slide as a JPEG.

    From the title slide, not a frame grab: deterministic, identical across
    rebuilds, and consistent across the series. Sized under the 2 MB ceiling
    by stepping the JPEG quality down from 92 -- a 1920x1080 card lands far
    below it at the first step."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(slide_path).convert("RGB")
    if img.size != (FRAME_W, FRAME_H):
        img = img.resize((FRAME_W, FRAME_H), Image.LANCZOS)
    for quality in (92, 85, 75, 65):
        img.save(out_path, "JPEG", quality=quality)
        if out_path.stat().st_size < THUMBNAIL_MAX_BYTES:
            return out_path
    raise RuntimeError(
        f"thumbnail {out_path} cannot fit under {THUMBNAIL_MAX_BYTES} bytes")


# --- building ----------------------------------------------------------------------------


def _source_audio_rate(source, ffmpeg):
    """The source's audio sample rate, or None when it cannot be probed --
    in which case the graph pins the rate explicitly rather than trusting."""
    ffprobe = conform.ffprobe_for(ffmpeg)
    try:
        out = subprocess.run(
            [*ffprobe, "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=sample_rate", "-of", "csv=p=0",
             str(source)],
            capture_output=True, text=True, check=True)
        return int(out.stdout.strip())
    except (subprocess.SubprocessError, ValueError):
        return None


def _write_unresolved(work_dir, slug, unresolved):
    path = Path(work_dir) / f"{slug}-unresolved.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(unresolved, indent=1) + "\n", encoding="utf-8")
    return path


# --- content-derived freshness --------------------------------------------------


def episode_input_digest(plan, staged, source=None):
    """The content an existing episode is fresh AGAINST, as one digest.

    Media verification answers "is this file a well-formed delivery"; it
    cannot answer "is this file the current CUT" -- a title slide with new
    copy encodes to the same 5.0 seconds and verifies clean. So freshness
    is derived from the content itself: the plan (chapter bounds, dossier
    snapshots, plate specs, lore overlay copy, the timeline's durations),
    the manifest's pinned source block, and every staged input the encode
    consumes, in graph order. Same digest, same episode -- a skip is then
    a content statement, not a duration coincidence.

    Staged inputs are hashed as DECODED PIXELS, not file bytes: Pillow's
    PNG output shifts with the process-global `ImageFile.MAXBLOCK` (which
    `tools/thumbnail.py` raises at import), so byte hashing would make the
    same pixels look changed across processes. Pixels are what the encoder
    decodes the PNGs back to, so pixel content is exactly the input.

    Deterministic by construction: the plan is manifest-derived, and the
    card renderers are pinned pixel-identical by their own tests."""
    h = hashlib.sha256()

    def note(kind, payload):
        h.update(kind.encode("utf-8"))
        h.update(b"\0")
        h.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
        h.update(b"\0")

    if source is not None:
        note("source", source)
    chapter = plan["chapter"]
    note("chapter", {"number": chapter["number"],
                     "start": chapter["start"], "end": chapter["end"]})
    for segment in plan["segments"]:
        entry = {"kind": segment["kind"]}
        if segment["kind"] == "chapter":
            entry["start"] = segment["start"]
            entry["end"] = segment["end"]
        else:
            entry["dur"] = segment["dur"]
        if "snapshot" in segment:
            entry["snapshot"] = segment["snapshot"]
        note("segment", entry)
    for spec in plan["plates"]:
        note("plate", spec)
    for overlay in plan["overlays"]:
        note("overlay", overlay)
    note("offsets", {"front_offset": plan["front_offset"],
                     "expected_duration": plan["expected_duration"]})
    for path in staged:
        path = Path(path)
        h.update(b"image\0")
        h.update(path.name.encode("utf-8"))
        h.update(b"\0")
        with Image.open(path) as img:
            rgba = img.convert("RGBA")
            h.update(f"{rgba.width}x{rgba.height}".encode("utf-8"))
            h.update(b"\0")
            h.update(rgba.tobytes())
        h.update(b"\0")
    return h.hexdigest()


def _read_input_digest(path):
    """The digest on record, or None when the sidecar is absent or unreadable
    -- an unreadable record is treated as no record, never as a match."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))["sha256"]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _write_input_digest(path, digest, staged):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "sha256": digest,
        "inputs": [Path(p).name for p in staged],
    }, indent=1) + "\n", encoding="utf-8")
    return path


def _render_overlay_pngs(plan, source, ffmpeg, work_dir, slug, unresolved,
                         log):
    """The episode's overlay inputs, in graph order: the fixed plates through
    tools/plate.py (unmodified), then the project-lore overlays drawn here.

    Seats are measured against the PICTURE, never the raw frame (issue
    #161's rule, taken from standalone.py): an undecodable source drops the
    seats and records why -- the unplated episode still ships."""
    overlay_pngs = []
    if not plan["plates"] and not plan["overlays"]:
        return overlay_pngs
    picture, status = render.detect_picture_status(source, ffmpeg=ffmpeg)
    if status == "undecodable":
        unresolved.extend(
            {"id": item["id"],
             "reason": "the source picture area could not be decoded, so "
                       "the seat could not be measured against the picture "
                       "and was not placed"}
            for item in [*plan["plates"], *plan["overlays"]])
        return overlay_pngs
    if plan["plates"]:
        plates_dir = Path(work_dir) / f"{slug}-plates"
        plate.render_all(plan["plates"], plates_dir, picture=picture)
        for spec in plan["plates"]:
            png = plates_dir / f"plate_{spec['id']}.png"
            if not png.exists():
                unresolved.append(
                    {"id": spec["id"],
                     "reason": f"no plate was rendered at {png}"})
                continue
            overlay_pngs.append(png.resolve())
    for overlay in plan["overlays"]:
        card = render_lore_overlay(overlay)
        frame = place_lore_overlay(card, overlay["position"], picture)
        png = Path(work_dir) / f"{slug}-overlay-{overlay['id']}.png"
        frame.save(png)
        overlay_pngs.append(png.resolve())
    return overlay_pngs


def build_episode(manifest_path, episode_number, local=False, ffmpeg=None,
                  log=print, work_dir=None):
    """One episode, built and delivered: cards, one farm-first encode,
    thumbnail, unresolved sidecar.

    Freshness is content-derived, never duration-derived: the plan and the
    pixel content of every staged input hash to a digest kept in
    ``<slug>-inputs.json`` beside the unresolved sidecar, and an existing
    output is kept only when it verifies AND the digest still matches -- a
    same-duration copy change rebuilds. A verified output with NO digest on
    record is adopted: the digest is initialized from the current content
    and the file kept, so deliveries from before this check are not
    re-encoded for want of a sidecar. Either way the skip rewrites the
    unresolved sidecar from the CURRENT plan before returning -- it can
    never be left missing or stale."""
    manifest = load_manifest(manifest_path)
    ffmpeg = ffmpeg or render.find_ffmpeg()
    plan = episode_plan(manifest, episode_number)
    chapter = plan["chapter"]
    slug = episode_slug(chapter)
    out = episode_output_path(chapter)
    thumb = thumbnail_output_path(chapter)
    work = Path(work_dir) if work_dir is not None else WORK_DIR
    work.mkdir(parents=True, exist_ok=True)

    source = Path(ensure_source(manifest)).resolve()
    unresolved = list(plan["unresolved"])

    stills = []
    for segment in plan["segments"]:
        if segment["kind"] == "chapter":
            continue
        if segment["kind"] == "dossier":
            snapshot = segment["snapshot"]
            img, gaps = render_dossier_safely(
                snapshot, face=resolve_face(snapshot["login"]))
            unresolved.extend(gaps)
            png = work / f"{slug}-dossier-{snapshot['login']}.png"
            img.convert("RGB").save(png)
            stills.append(png.resolve())
        else:
            stills.append(Path(segment["asset"]).resolve())

    overlay_pngs = _render_overlay_pngs(
        plan, source, ffmpeg, work, slug, unresolved, log)
    staged = [*stills, *overlay_pngs]
    digest = episode_input_digest(plan, staged, source=manifest["source"])
    digest_path = work / f"{slug}-inputs.json"

    if out.exists() and not verify_episode(manifest, episode_number,
                                           ffmpeg=ffmpeg):
        stored = _read_input_digest(digest_path)
        if stored == digest:
            log(f"  {slug}: already built and verified -- {out}")
        elif stored is None:
            log(f"  {slug}: verified delivery with no digest on record; "
                f"adopting the current content as its digest")
            _write_input_digest(digest_path, digest, staged)
        if stored is None or stored == digest:
            _write_unresolved(work, slug, unresolved)
            if not thumb.exists():
                make_thumbnail(plan["segments"][1]["asset"], thumb)
                log(f"  thumbnail: {thumb}")
            return out
        log(f"  {slug}: content changed since the delivered encode "
            f"({stored[:12]}... -> {digest[:12]}...) -- rebuilding")

    out.parent.mkdir(parents=True, exist_ok=True)
    out = out.resolve()
    graph = episode_filtergraph(
        plan, source_rate=_source_audio_rate(source, ffmpeg))
    argv = encode_episode_command(
        ffmpeg, source, stills, overlay_pngs, graph, out)
    where = encode_episode(
        argv, inputs=[source, *stills, *overlay_pngs], out=out,
        expected_duration=plan["expected_duration"], local=local,
        label=f"Hive {slug}")
    log(f"  {slug}: encoded on {where} -- {out}")

    _write_input_digest(digest_path, digest, staged)
    _write_unresolved(work, slug, unresolved)
    for item in unresolved:
        log(f"  unresolved: {item}")

    make_thumbnail(plan["segments"][1]["asset"], thumb)
    log(f"  thumbnail: {thumb}")

    problems = verify_episode(manifest, episode_number, ffmpeg=ffmpeg)
    for problem in problems:
        log(f"  verify: {problem}")
    return out


def build_all(manifest_path=None, local=False, ffmpeg=None, log=print,
              work_dir=None):
    """All twelve episodes, in chapter order. The source fetch happens once:
    the cache file is the evidence it ran."""
    manifest = load_manifest(manifest_path)
    return [build_episode(manifest_path or MANIFEST, chapter["number"],
                          local=local, ffmpeg=ffmpeg, log=log,
                          work_dir=work_dir)
            for chapter in manifest["chapters"]]


# --- the full-season cut ---------------------------------------------------------------


def concat_list_lines(manifest):
    """The concat-demuxer list: the twelve delivered episodes, in order."""
    return [f"file '{episode_output_path(c).resolve()}'"
            for c in manifest["chapters"]]


def concat_command(ffmpeg, list_path, out_path):
    """Join the episodes: copy BOTH streams.

    Every episode was encoded from the same delivery recipe, so the join is
    a remux -- no second generation of picture or sound, and the streams'
    SPS agree by construction."""
    return [
        *ffmpeg, "-nostdin", "-hide_banner",
        "-f", "concat", "-safe", "0", "-i", str(list_path),
        "-map", "0:v:0", "-map", "0:a:0",
        "-c:v", "copy", "-c:a", "copy",
        "-movflags", "+faststart",
        str(out_path), "-y",
    ]


def concat_episodes(manifest, out_path=None, ffmpeg=None, work_dir=None,
                    runner=subprocess.run):
    """Concatenate the built episodes into the full-season cut.

    A pure remux -- the picture and sound are both stream-copied -- so it
    runs here, the same posture as megacut's assemble: the encodes were the
    farm's work; the join is I/O."""
    ffmpeg = ffmpeg or render.find_ffmpeg()
    out_path = Path(out_path) if out_path else full_cut_path(manifest)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    work = Path(work_dir) if work_dir is not None else WORK_DIR
    work.mkdir(parents=True, exist_ok=True)
    list_path = work / "season-01-concat.txt"
    list_path.write_text("\n".join(concat_list_lines(manifest)) + "\n",
                         encoding="utf-8")
    runner(concat_command(ffmpeg, list_path, out_path), check=True)
    return out_path


class UnverifiedEpisodes(RuntimeError):
    """The cut refused its inputs: one or more episodes did not verify.

    Carries the full ``problems`` report. The join is a blind stream copy,
    so an episode that fails verification goes NOWHERE near it -- the cut
    is only ever concatenated from verified episodes."""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__(
            f"{len(self.problems)} episode verification problem(s)")


def build_cut(manifest_path=None, local=False, ffmpeg=None, log=print):
    """The ONE way to the full-season cut: build every episode, verify each
    one, and only then join.

    Returns ``(out_path, problems)`` -- the cut's own post-join report,
    empty when the delivered file verifies. An episode that does not verify
    is never concatenated: the report is logged and raised as
    `UnverifiedEpisodes` before the join runs. The CLI and the justfile
    both go through here; there is no second path to a cut."""
    manifest = load_manifest(manifest_path)
    build_all(manifest_path, local=local, ffmpeg=ffmpeg, log=log)
    problems = []
    for chapter in manifest["chapters"]:
        problems.extend(
            verify_episode(manifest, chapter["number"], ffmpeg=ffmpeg))
    if problems:
        for problem in problems:
            log(f"  verify: {problem}")
        raise UnverifiedEpisodes(problems)
    out = concat_episodes(manifest, ffmpeg=ffmpeg)
    log(f"  full cut: {out}")
    problems = _probe_delivery_streams(
        full_cut_path(manifest), cut_expected_duration(manifest),
        ffmpeg or render.find_ffmpeg(), CUT_TOLERANCE_S)
    for problem in problems:
        log(f"  verify: {problem}")
    return out, problems


# --- verification ---------------------------------------------------------------------


def _probe_duration(path, ffmpeg):
    ffprobe = conform.ffprobe_for(ffmpeg)
    out = subprocess.run(
        [*ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True)
    text = out.stdout.strip()
    if not text:
        raise RuntimeError(f"ffprobe reported no duration for {path}")
    return float(text)


def _probe_audio(path, ffmpeg):
    ffprobe = conform.ffprobe_for(ffmpeg)
    out = subprocess.run(
        [*ffprobe, "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=codec_name,sample_rate,channels",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True)
    streams = json.loads(out.stdout).get("streams") or []
    return streams[0] if streams else {}


def _fps_is_delivery(reported):
    """The delivered cadence, with room for container rounding.

    The card/chapter durations are whole seconds, which 60000/1001 never
    divides evenly, so the mp4 container carries the nearest representable
    duration and ffprobe's ``avg_frame_rate`` (frames over that duration)
    lands a few thousandths off -- 32640000/544621 instead of 60000/1001 on
    a real 59.94 encode. 0.02 fps of slack covers that rounding and still
    cannot confuse 60/1 or 30/1 for the delivery rate (they are 0.06 and
    29.97 away)."""
    try:
        num, _, den = str(reported).partition("/")
        value = float(num) / float(den or 1)
    except (TypeError, ValueError, ZeroDivisionError):
        return False
    wnum, _, wden = conform.DELIVERY.fps.partition("/")
    return abs(value - float(wnum) / float(wden)) < 0.02


def _probe_delivery_streams(path, expected, ffmpeg, tolerance):
    """The problems a delivered file has, as a list -- empty means verified.

    The stream checks ARE `conform.mismatches`: pixel format, color,
    profile and level ride along with codec/size/rate because the full cut
    joins these files blind. The ONE override is the frame rate: conform's
    rational comparison cannot know the mp4 container-rounding verdict
    (`_fps_is_delivery`), so a conform frame-rate mismatch is kept only
    when `_fps_is_delivery` also fails. A report, never a gate: the caller
    logs the problems and ships anyway (AGENTS.md: nothing blocks a
    release)."""
    problems = []
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return [f"{path}: missing or empty"]
    try:
        duration = _probe_duration(path, ffmpeg)
        if abs(duration - expected) > tolerance:
            problems.append(
                f"{path.name}: duration {duration:.3f}s is "
                f"{duration - expected:+.3f}s from the expected "
                f"{expected:.3f}s (tolerance {tolerance}s)")
        video = conform.probe_video(path, conform.ffprobe_for(ffmpeg))
        fps_ok = video.get("r_frame_rate") == conform.DELIVERY.fps or \
            _fps_is_delivery(video.get("avg_frame_rate"))
        for bad in conform.mismatches(video):
            if fps_ok and bad.startswith("frame rate"):
                continue
            problems.append(f"{path.name}: {bad}")
        audio = _probe_audio(path, ffmpeg)
        if audio.get("codec_name") != "aac":
            problems.append(
                f"{path.name}: audio codec {audio.get('codec_name')!r} "
                "is not aac")
        if int(audio.get("sample_rate", 0)) != SAMPLE_RATE:
            problems.append(
                f"{path.name}: sample rate {audio.get('sample_rate')!r} "
                f"is not {SAMPLE_RATE}")
    except (subprocess.SubprocessError, RuntimeError, KeyError) as exc:
        problems.append(f"{path.name}: probe failed ({exc})")
    return problems


def verify_episode(manifest, number, ffmpeg=None):
    ffmpeg = ffmpeg or render.find_ffmpeg()
    chapter = chapter_by_number(manifest, number)
    return _probe_delivery_streams(
        episode_output_path(chapter), episode_expected_duration(manifest,
                                                                chapter),
        ffmpeg, EPISODE_TOLERANCE_S)


def verify_cut(manifest, ffmpeg=None):
    """Twelve episodes in order, then the cut at the aggregate duration."""
    ffmpeg = ffmpeg or render.find_ffmpeg()
    problems = []
    for chapter in manifest["chapters"]:
        problems.extend(
            verify_episode(manifest, chapter["number"], ffmpeg=ffmpeg))
    problems.extend(_probe_delivery_streams(
        full_cut_path(manifest), cut_expected_duration(manifest),
        ffmpeg, CUT_TOLERANCE_S))
    return problems



# --- manifest loading and validation ---------------------------------------------

def _schema_errors(data):
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    return sorted(
        Draft202012Validator(schema).iter_errors(data),
        key=lambda e: list(e.path),
    )


def _semantic_errors(data):
    """The checks a JSON schema cannot express: bounds, contiguity, and the
    no-repeat contributor ledger."""
    errors = []
    chapters = data.get("chapters") or []
    numbers = [c.get("number") for c in chapters]
    if numbers != list(range(1, len(chapters) + 1)):
        errors.append(f"chapter numbers must be 1..{len(chapters)} in order")
    windows = {c["number"]: (c["start"], c["end"]) for c in chapters
               if isinstance(c.get("number"), int)}
    for prev, nxt in zip(chapters, chapters[1:]):
        if prev.get("end") != nxt.get("start"):
            errors.append(
                f"chapter {prev.get('number')} ends at {prev.get('end')} but "
                f"chapter {nxt.get('number')} starts at {nxt.get('start')}"
            )

    for member in data.get("fixed_cast") or []:
        for seat in member.get("seats") or []:
            window = windows.get(seat.get("chapter"))
            if window is None:
                errors.append(
                    f"{member.get('id')}: seat references chapter "
                    f"{seat.get('chapter')}, which does not exist"
                )
                continue
            start, end = window
            if not (start <= seat["source_at"]
                    and seat["source_at"] + seat["dur"] <= end):
                errors.append(
                    f"{member.get('id')}: seat at {seat['source_at']}+"
                    f"{seat['dur']}s is outside chapter {seat['chapter']} "
                    f"({start}-{end})"
                )

    for overlay in data.get("overlays") or []:
        window = windows.get(overlay.get("chapter"))
        if window is None:
            errors.append(
                f"overlay {overlay.get('id')}: chapter "
                f"{overlay.get('chapter')} does not exist"
            )
        elif not (window[0] <= overlay["source_at"] <= window[1]):
            errors.append(
                f"overlay {overlay.get('id')}: {overlay['source_at']} is "
                f"outside chapter {overlay['chapter']} {window}"
            )

    seen, repeats = set(), set()
    ledger = (data.get("contributor_ledger") or {}).get("credited_github_ids") or []
    for github_id in ledger:
        (repeats if github_id in seen else seen).add(github_id)
    for chapter in chapters:
        for dossier in chapter.get("dossiers") or []:
            github_id = dossier.get("github_id")
            if github_id in seen:
                repeats.add(github_id)
            seen.add(github_id)
    if repeats:
        errors.append(
            "contributor GitHub IDs repeat across the season: "
            + ", ".join(str(i) for i in sorted(repeats))
        )
    return errors


def load_manifest_data(data):
    """Validate already-parsed manifest data against the schema and the
    season's own rules. Raises ValueError listing every problem found.

    Schema problems are reported on their own: the semantic checks assume the
    fields the schema requires, so running them against a schema-invalid
    document would surface a KeyError instead of the real problem list."""
    problems = [
        f"{'/'.join(str(p) for p in e.path) or '/'}: {e.message}"
        for e in _schema_errors(data)
    ]
    if not problems:
        problems.extend(_semantic_errors(data))
    if problems:
        raise ValueError(
            "season manifest is invalid:\n" + "\n".join(problems)
        )
    return data


def load_manifest(path=None):
    with open(path or MANIFEST, encoding="utf-8") as fh:
        return load_manifest_data(json.load(fh))


# --- CLI ---------------------------------------------------------------------

def _cmd_check(_args):
    manifest = load_manifest()
    seats = sum(len(m["seats"]) for m in manifest["fixed_cast"])
    print(f"season {manifest['season']}: {len(manifest['chapters'])} chapters, "
          f"{len(manifest['fixed_cast'])} fixed cast, {seats} seats, "
          f"{len(manifest['overlays'])} owner overlays -- valid")
    return 0


def _cmd_cards(args):
    manifest = load_manifest()
    out_dir = REPO_ROOT / manifest["title_slide"]["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    cta_path = REPO_ROOT / manifest["opening_cta"]["asset"]
    cta_path.parent.mkdir(parents=True, exist_ok=True)
    render_opening_cta(manifest["opening_cta"]["lines"]).save(cta_path)
    digest = hashlib.sha256(cta_path.read_bytes()).hexdigest()
    print(f"{cta_path.relative_to(REPO_ROOT)}  sha256:{digest}")
    for chapter in manifest["chapters"]:
        path = out_dir / title_slide_filename(chapter)
        render_title_slide(manifest, chapter).save(path)
        print(path.relative_to(REPO_ROOT))
    return 0


def _cmd_fetch_avatars(_args):
    manifest = load_manifest()
    _tally, missing = fetch_declared_avatars(manifest)
    for login in missing:
        print(f"unresolved: {login}: no cached GitHub avatar", file=sys.stderr)
    return 0


def _report_verify(problems, log=print):
    """Verification is a report, never a gate: the files are already
    delivered. The exit code tells `just` whether the report was clean."""
    if problems:
        for problem in problems:
            print(f"  verify: {problem}", file=sys.stderr)
        return 1
    log("  verified")
    return 0


def _cmd_build(args):
    out = build_episode(MANIFEST, args.number, local=args.local)
    problems = verify_episode(load_manifest(), args.number)
    print(f"episode {args.number}: {out}")
    return _report_verify(problems)


def _cmd_build_all(args):
    manifest = load_manifest()
    build_all(MANIFEST, local=args.local)
    problems = []
    for chapter in manifest["chapters"]:
        problems.extend(verify_episode(manifest, chapter["number"]))
    return _report_verify(problems)


def _cmd_cut(args):
    """The full-season cut, through the one interface that owns it."""
    try:
        out, problems = build_cut(MANIFEST, local=args.local)
    except UnverifiedEpisodes as exc:
        return _report_verify(exc.problems)
    print(f"full cut: {out}")
    return _report_verify(problems)


def _cmd_verify(args):
    manifest = load_manifest()
    if args.number is not None:
        return _report_verify(verify_episode(manifest, args.number))
    return _report_verify(verify_cut(manifest))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="validate the season manifest")
    sub.add_parser("cards", help="render the committed cards (CTA + slides)")
    sub.add_parser("fetch-avatars", help="warm the avatar cache for the cast")
    build = sub.add_parser("build", help="build one episode (farm-first)")
    build.add_argument("number", type=int)
    build.add_argument("--local", action="store_true",
                       help="encode here, memory-capped, instead of the farm")
    build_all_p = sub.add_parser(
        "build-all", help="build and verify all twelve episodes")
    build_all_p.add_argument("--local", action="store_true")
    cut = sub.add_parser(
        "cut", help="build, verify, and join the episodes into the full cut")
    cut.add_argument("--local", action="store_true",
                     help="encode here, memory-capped, instead of the farm")
    verify = sub.add_parser(
        "verify", help="probe the delivered files (one episode, or all+cut)")
    verify.add_argument("number", type=int, nargs="?", default=None)
    args = parser.parse_args(argv)
    return {
        "check": _cmd_check,
        "cards": _cmd_cards,
        "fetch-avatars": _cmd_fetch_avatars,
        "build": _cmd_build,
        "build-all": _cmd_build_all,
        "cut": _cmd_cut,
        "verify": _cmd_verify,
    }[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
