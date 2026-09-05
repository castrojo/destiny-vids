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
  name (falling back to login), @login, and the window's COMMITS +N. No
  generated title, ever;
* the Expansion Pack authoring pass -- the owner-authored cue files under
  `stories/standalone/authoring/season-of-the-blueberries/`, parsed by
  `tools/hive_authoring.py` into chat pills (drawn by plate.py's `kind:
  chat` renderer), verbatim lore cards in the supported lanes, and an
  `unresolved` record for every cue this renderer cannot seat faithfully.

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
    python3 tools/hive_series.py build 1         # one episode ROUGH, farm-first
    python3 tools/hive_series.py build-all       # all twelve roughs, verified
    python3 tools/hive_series.py cut             # the full-season ROUGH join
    python3 tools/hive_series.py verify [N]      # probe the roughs (--final: the promoted files)
    python3 tools/hive_series.py promote 1       # copy an APPROVED rough to its final
    python3 tools/hive_series.py promote-cut     # copy the approved rough cut to final
    python3 tools/hive_series.py contributors    # this window's candidates (no writes)
    python3 tools/hive_series.py select-next     # issue the next episode's dossiers
    python3 tools/hive_series.py status          # issued/unissued, delivered/missing

Rough-first delivery (Hive AGENTS.md): build/cut write only
`rough/s01eNN-<slug>.mp4`, their rough thumbnails, and
`season-01-full-rough.mp4`. The top-level finals and the final cut are
written by `promote`/`promote-cut` alone -- a pure file copy after local
approval, never by a build, so a rebuild can never overwrite a released
episode.

The episode build is ONE H.264/AAC encode per episode through
`tools.farm.run_encode` -- farm ONLY, per the Hive workspace contract: no
local ffmpeg/ffprobe at all, not even preflight probes, picture detection,
or validation (all farm-side), and no local fallback -- an unreachable farm
fails the build visibly before any render. The source is the workspace's
supplied immutable file (`~/Videos/Hive/source-<youtube_id>.mp4`), or the
previously cached copy of it; when neither exists the build refuses with
instructions, because a local yt-dlp fetch would run a local ffmpeg merge
-- never mutated, never downloaded-and-muxed on the host. Source seats and
overlays are converted to chapter-relative content time and offset by the
front cards; the authored source marks themselves never move. The
full-season rough cut concatenates the twelve episode roughs without
re-encoding, also on the farm.

Stdlib plus Pillow for the cards; all media work goes through
tools/farm.py.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import avatars  # noqa: E402  (needs REPO_ROOT on sys.path first)
from tools import conform  # noqa: E402
from tools import farm  # noqa: E402
from tools import hive_authoring  # noqa: E402
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
# status accent only -- the COMMITS tally dot and the #HIREAWOLF pill.
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
    tally is the window's commit count, rendered as ``COMMITS +N``. A
    generated title is never added.
    """
    name = (snapshot.get("name") or "").strip() or snapshot["login"]
    return {
        "name": name,
        "handle": f"@{snapshot['login']}",
        "tasks": f"COMMITS +{int(snapshot['commits'])}",
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


def declared_avatar_logins(manifest, authoring_dir=None):
    """The GitHub logins whose faces the season renders: the fixed cast
    plus every authoring-pass chat speaker whose identity the season's own
    records prove (a fixed-cast seat or a contributor-ledger candidacy).
    A speaker the record does not vouch for renders avatarless by design
    and is never warmed. Logins are returned once each, fixed cast first,
    then authoring speakers in chapter order."""
    logins = [member["github_login"] for member in manifest["fixed_cast"]]
    seen = {login.lower() for login in logins}
    for chapter in manifest["chapters"]:
        chats, cards, _lore, _unresolved, _gaps = hive_authoring.plan_authoring(
            hive_authoring.load_chapter_authoring(
                authoring_dir or AUTHORING_DIR, chapter),
            manifest, chapter)
        for spec in [*chats, *cards]:
            avatar = spec.get("avatar")
            if not avatar:
                continue
            login = Path(avatar).stem
            if login.lower() not in seen:
                seen.add(login.lower())
                logins.append(login)
    return logins


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
# The owner-authored Expansion Pack copy, one Markdown file per episode
# (`NN-<slug>.md`), parsed by tools/hive_authoring.py. A module constant so
# tests can redirect it.
AUTHORING_DIR = hive_authoring.AUTHORING_DIR
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
# Rough-first delivery (Hive AGENTS.md): `build`/`build-all`/`cut` write
# ONLY reviewable artifacts -- episodes and their thumbnails under the
# season folder's `rough/` directory, and the season assembly as
# `season-01-full-rough.mp4`. The top-level `s01eNN-*.mp4`, their paired
# `-thumbnail.jpg`, and `season-01-full.mp4` are promotion-only: the one
# boundary that writes them is `promote_episode`/`promote_cut` (a pure file
# copy after local approval), never a build.
ROUGH_DIR_NAME = "rough"
ROUGH_CUT_NAME = "season-01-full-rough.mp4"

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
    """The FINAL, promoted episode path (top level of the season folder).
    Builds never write here -- see the rough-first note above."""
    return Path(chapter["output"]).expanduser()


def thumbnail_output_path(chapter):
    """The FINAL, promoted thumbnail path. Builds never write here."""
    return Path(chapter["thumbnail_output"]).expanduser()


def episode_rough_path(chapter):
    """The reviewable rough: the episode's filename under ``rough/``."""
    final = episode_output_path(chapter)
    return final.parent / ROUGH_DIR_NAME / final.name


def thumbnail_rough_path(chapter):
    """The rough's paired thumbnail, beside the rough episode."""
    final = thumbnail_output_path(chapter)
    return final.parent / ROUGH_DIR_NAME / final.name


def full_cut_path(manifest):
    """The FINAL season cut sits beside the episodes the manifest
    delivers. Builds never write here."""
    return episode_output_path(manifest["chapters"][0]).parent / FULL_CUT_NAME


def full_cut_rough_path(manifest):
    """The reviewable season assembly, beside the final cut's name."""
    return full_cut_path(manifest).with_name(ROUGH_CUT_NAME)


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


def supplied_source_path(manifest):
    """The Hive workspace's immutable hand-placed source for this manifest
    (``~/Videos/Hive/source-<youtube_id>.mp4``). Read-only, always: nothing
    in this module ever writes to it."""
    return Path(
        f"~/Videos/Hive/source-{manifest['source']['youtube_id']}.mp4"
    ).expanduser()


def ensure_source(manifest, cache_dir=None, runner=subprocess.run,
                  supplied=None, allow_fetch=False):
    """The season source: the Hive workspace's SUPPLIED immutable file when
    it is present (never mutated, never re-downloaded), else the one
    already-cached copy. When neither exists the build FAILS VISIBLY: a
    local `yt-dlp -f 137+251 --merge-output-format mkv` fetch would invoke
    a local ffmpeg merge, and the Hive workspace forbids any local media
    execution -- the source must be staged at
    ``~/Videos/Hive/source-<youtube_id>.mp4`` (e.g. by a remote job), never
    downloaded-and-muxed on the host. The fetch remains reachable only for
    non-Hive callers that pass ``allow_fetch=True`` explicitly; the Hive
    build path never does."""
    supplied = Path(supplied).expanduser() if supplied is not None \
        else supplied_source_path(manifest)
    if supplied.exists() and supplied.stat().st_size > 0:
        return supplied.resolve()
    out = source_cache_path(manifest, cache_dir).resolve()
    if out.exists() and out.stat().st_size > 0:
        return out
    if not allow_fetch:
        raise FileNotFoundError(
            f"no season source: the Hive build requires the immutable "
            f"supplied source at {supplied} (stage it from a remote job); "
            "a local yt-dlp fetch would run a local ffmpeg merge, which "
            "this workspace forbids")
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
    not know, are recorded in `unresolved` and never drawn.

    The Expansion Pack authoring pass (`tools/hive_authoring.py`, parsed
    from AUTHORING_DIR) adds the episode's `chats` (plate.py `kind: chat`
    pills) and any supported authoring lore cards, and records every cue it
    cannot seat faithfully in `unresolved`."""
    chapter = chapter_by_number(manifest, number)
    plates, unresolved = plan_chapter_plates(manifest, number)
    for spec in plates:
        spec["at"] = source_to_chapter_relative(spec["at"], chapter)
    window = float(chapter["end"]) - float(chapter["start"])
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
        overlays.append({
            "id": overlay["id"],
            "lines": list(overlay["lines"]),
            "position": overlay["position"],
            "at": at,
            "dur": min(LORE_OVERLAY_DUR, window - at),
        })
    # The owner-authored Expansion Pack pass (tools/hive_authoring.py): chat
    # pills through plate.py's `kind: chat` renderer, verbatim lore cards in
    # the supported lanes, and every cue that cannot be seated faithfully
    # recorded in `unresolved` -- never dropped, never rendered by a guess.
    # An authoring lore card the manifest already carries verbatim (same
    # position, same absolute source mark, same lines) is rendered by the
    # manifest's overlay record, so the duplicate authoring cue is covered,
    # not double-drawn.
    chats, authoring_cards, authoring_lore, authoring_unresolved, protected_gaps = \
        hive_authoring.plan_authoring(
            hive_authoring.load_chapter_authoring(AUTHORING_DIR, chapter),
            manifest, chapter)
    unresolved.extend(authoring_unresolved)
    covered = {(o["position"], float(o["source_at"]), tuple(o["lines"]))
               for o in manifest.get("overlays") or []
               if o["chapter"] == number
               and o["position"] in LORE_POSITIONS}
    for card in authoring_lore:
        key = (card["position"], float(card["source_at"]),
               tuple(card["lines"]))
        if key in covered:
            continue
        at = source_to_chapter_relative(card["source_at"], chapter)
        overlays.append({
            "id": card["id"],
            "lines": list(card["lines"]),
            "position": card["position"],
            "at": at,
            "dur": min(LORE_OVERLAY_DUR, window - at),
        })
    overlays.sort(key=lambda o: o["at"])  # stable: ties keep manifest first
    overlays = _clamp_lore_lanes(overlays, unresolved)
    # A protected gap is a no-draw window for EVERY card, lore included.
    overlays = _clear_of_protected_gaps(overlays, protected_gaps,
                                        unresolved)
    return {
        "chapter": chapter,
        "segments": episode_segments(manifest, chapter),
        "plates": plates,
        "chats": chats,
        "cards": authoring_cards,
        "overlays": overlays,
        "protected_gaps": protected_gaps,
        "unresolved": unresolved,
        "front_offset": front_cards_duration(manifest, chapter),
        "expected_duration": episode_expected_duration(manifest, chapter),
    }


# --- the project-lore overlays ---------------------------------------------------------

# The positions this renderer knows how to seat. Anything else is recorded
# and omitted, never guessed.
LORE_POSITIONS = ("bottom-right", "top-third")


def _clamp_lore_lanes(overlays, unresolved):
    """No two lore cards share a lane at the same time.

    ``overlays`` is the episode's at-sorted lore list (manifest records and
    authoring cards together). A card's hold is clamped to end when the NEXT
    rendered card in the SAME lane begins -- deterministic, and the later
    card's authored anchor never moves. A card left under the project's
    minimum readable hold (plate.MIN_HOLD) by that clamp is recorded in
    ``unresolved`` and omitted instead of flashing unreadably or overlapping.
    Different lanes never constrain each other."""
    kept = []
    for index, overlay in enumerate(overlays):
        later = next((o for o in overlays[index + 1:]
                      if o["position"] == overlay["position"]), None)
        if later is None:
            kept.append(overlay)
            continue
        room = float(later["at"]) - float(overlay["at"])
        if room < plate.MIN_HOLD - 1e-6:
            unresolved.append({
                "id": overlay["id"],
                "reason": f"the next {overlay['position']} card "
                          f"({later['id']}) begins {room:.2f}s after it, "
                          f"under the {plate.MIN_HOLD}s minimum readable "
                          "hold; the card is recorded rather than "
                          "overlapped or flashed unreadably",
            })
            continue
        overlay["dur"] = round(min(float(overlay["dur"]), room), 3)
        kept.append(overlay)
    return kept


def _clear_of_protected_gaps(overlays, protected_gaps, unresolved):
    """No lore card covers a protected gap. ``protected_gaps`` is the
    chapter-relative no-draw windows from the authoring pass (the owner's
    "leave the picture alone" beat); a card whose window intersects one is
    recorded and omitted, never drawn over a protected beat. Unlike a
    merely unsupported cue, a protected gap is unrenderable AND binding."""
    if not protected_gaps:
        return overlays
    kept = []
    for overlay in overlays:
        at = float(overlay["at"])
        end = at + float(overlay["dur"])
        hit = next(((g0, g1) for g0, g1 in protected_gaps
                    if not (end <= g0 + 1e-6 or at >= g1 - 1e-6)), None)
        if hit is None:
            kept.append(overlay)
            continue
        unresolved.append({
            "id": overlay["id"],
            "reason": f"its window {at:g}-{end:g}s would cover the "
                      f"protected gap {hit[0]:g}-{hit[1]:g}s (the owner "
                      "leaves the picture alone there); recorded, never "
                      "drawn over a protected beat",
        })
    return kept


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


def _plan_overlay_descriptors(plan):
    """The overlay/plate descriptor list AS PLANNED, in render order: fixed
    plates, authoring cards, authoring chat pills, then project-lore overlays.
    The fixed cast stays ahead of the authoring overlays in the encoded order.

    This is only the PLAN's view -- what the season manifest asks for.
    `_render_overlay_pngs` walks this same order but may PRUNE it (an
    undecodable source drops every seat; a plate whose PNG never
    materialised drops just that one). The pruned list is what actually got
    rendered, so it -- never this planned one -- is what
    `episode_filtergraph`, `encode_episode_command`, and
    `episode_input_digest` must all agree on. This helper exists only to
    give a caller with no rendered list yet (a plan-only test, a digest
    computed before rendering) the same default derivation, so it never
    has to duplicate the zip-order rule."""
    return [dict(p, overlay_kind="plate") for p in plan["plates"]] + \
        [dict(c, overlay_kind="card") for c in plan.get("cards", [])] + \
        [dict(c, overlay_kind="chat") for c in plan.get("chats", [])] + \
        [dict(o, overlay_kind="lore") for o in plan["overlays"]]


def episode_filtergraph(plan, overlays=None, source_rate=SAMPLE_RATE):
    """One graph for one episode: the stills, the chapter, one concat.

    Input order is the fixed contract with `encode_episode_command`: input 0
    is the source, the stills follow in segment order, and the overlay PNGs
    (fixed plates, then authoring chat pills, then lore overlays) come last.
    Every still and overlay is
    a looped -- infinite -- input; the stills are trimmed to their authored
    durations and the overlays carry ``shortest=1``, so the finite chapter
    leg decides where the file ends.

    ``overlays`` MUST be the actually-rendered, already-pruned descriptor
    list from `_render_overlay_pngs` -- the same list, in the same order,
    that `encode_episode_command` loops as PNG inputs. An undecodable
    source or a missing plate PNG drops entries from that list; indexing
    against the PLANNED list instead (the default, used only when a caller
    has nothing rendered yet) would seat an overlay on an input ffmpeg was
    never given.

    The chapter's audio is the source's own, trimmed on the same boundary
    and pinned to the delivery layout; aresample joins the chain ONLY when
    the source's rate is not already the delivery rate (megacut's rule)."""
    chain = conform.video_filter_chain()
    stills = [s for s in plan["segments"] if s["kind"] != "chapter"]
    chapter = next(s for s in plan["segments"] if s["kind"] == "chapter")
    if overlays is None:
        overlays = _plan_overlay_descriptors(plan)
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


def encode_episode(argv, *, inputs, out, expected_duration, label=None):
    """The episode's one encode -- farm ONLY, farm-verified.

    The Hive workspace contract forbids local ffmpeg outright, so unlike
    the legacy builders this takes no `--local` escape and no fallback:
    `farm.run_encode` with `fallback=False` raises FarmError before any
    render when the cluster is unreachable, and `local_probe=False` keeps
    the post-fetch verification on the pod's own probe, never the host's
    ffprobe."""
    return farm.run_encode(
        argv, inputs=inputs, out=out, fallback=False, local_probe=False,
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


# --- farm-side preflight and validation (Hive: NO local ffmpeg/ffprobe) ---------
#
# The Hive workspace contract forbids local media tooling entirely --
# including preflight probes, picture detection, and validation. All of it
# runs on the render farm through `farm.run_analysis_on_cluster`, which
# stages the file in a pod and captures the pod-side ffprobe/ffmpeg output.
# The host only ever parses text.


def _probe_streams_farm(path, label=None):
    """The full ffprobe JSON document for ``path``, produced ON the farm.

    A garbled or truncated capture is normalized to FarmError here, so every
    verification call path can turn it into a visible problem instead of an
    unhandled JSONDecodeError abort."""
    path = Path(path).resolve()
    text = farm.run_analysis_on_cluster(
        [["ffprobe", "-v", "error", "-print_format", "json",
          "-show_format", "-show_streams", str(path)]],
        inputs=[path], label=label or f"Hive probe {path.name}")
    try:
        return json.loads(text)
    except ValueError as exc:
        raise farm.FarmError(
            f"the farm's probe of {path.name} returned unreadable output "
            f"({exc}); the capture begins: {text[:120]!r}") from exc


def _facts_from_probe_doc(doc):
    """``(duration, video_props, audio_props)`` from an ffprobe document.

    video_props carries exactly the keys `conform.probe_video` selects, so
    `conform.mismatches` judges it unchanged; audio_props is the first audio
    stream ({} when there is none)."""
    streams = doc.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise RuntimeError("no video stream in the probed file")
    audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
    return float(doc["format"]["duration"]), video, audio


def _source_preflight_farm(source, log=print):
    """The source preflight, entirely on the farm:
    ``(audio_sample_rate, picture_rect, picture_status)``.

    One pod probe for the stream facts (audio rate for the filtergraph,
    duration for the cropdetect windows), one for the cropdetect readings;
    the readings are judged by `render.picture_status_from_cropdetect` --
    the same parsing the legacy local detection applies. ``audio_rate`` is
    None when the source has no audio stream, so the graph pins the rate
    explicitly rather than trusting."""
    source = Path(source).resolve()
    doc = _probe_streams_farm(source, label=f"Hive preflight {source.name}")
    streams = doc.get("streams") or []
    audio = next((s for s in streams if s.get("codec_type") == "audio"),
                 None)
    rate = None
    if audio and audio.get("sample_rate"):
        rate = int(audio["sample_rate"])
    try:
        duration = float((doc.get("format") or {})["duration"])
    except (KeyError, TypeError, ValueError):
        duration = None
    argvs = [
        ["ffmpeg", "-nostdin", "-hide_banner",
         "-ss", str(start), "-t", str(length), "-i", str(source),
         "-vf", "cropdetect=24:2:0", "-f", "null", "-"]
        for start, length in render.probe_windows(duration)
    ]
    text = farm.run_analysis_on_cluster(
        argvs, inputs=[source], label=f"Hive picture detect {source.name}")
    picture, status = render.picture_status_from_cropdetect(text)
    return rate, picture, status


def _cached_avatar_present(avatar):
    """Whether the declared avatar path resolves to a usable cached face.
    A seam of its own so tests decide "cache warm/cold" without depending on
    the host's avatar cache (bytes are never committed)."""
    face = Path(avatar).expanduser()
    if not face.is_absolute():
        face = REPO_ROOT / face
    return face.exists() and face.stat().st_size >= avatars.MIN_BYTES


def _write_unresolved(work_dir, slug, unresolved):
    path = Path(work_dir) / f"{slug}-unresolved.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(unresolved, indent=1) + "\n", encoding="utf-8")
    return path


# --- content-derived freshness --------------------------------------------------


def episode_input_digest(plan, staged, overlays=None, source=None):
    """The content an existing episode is fresh AGAINST, as one digest.

    Media verification answers "is this file a well-formed delivery"; it
    cannot answer "is this file the current CUT" -- a title slide with new
    copy encodes to the same 5.0 seconds and verifies clean. So freshness
    is derived from the content itself: the plan (chapter bounds, dossier
    snapshots, plate specs, lore overlay copy, the timeline's durations),
    the manifest's pinned source block, and every staged input the encode
    consumes, in graph order. Same digest, same episode -- a skip is then
    a content statement, not a duration coincidence.

    ``overlays`` MUST be the same rendered/pruned descriptor list handed to
    `episode_filtergraph` -- the encode DECODES only what actually got
    rendered, so an episode whose overlays were pruned (an undecodable
    source, a missing plate PNG) must digest differently from one whose
    overlays rendered clean, even on an identical plan. It defaults to the
    full planned list only for a caller with nothing rendered yet.

    Staged inputs are hashed as DECODED PIXELS, not file bytes: Pillow's
    PNG output shifts with the process-global `ImageFile.MAXBLOCK` (which
    `tools/thumbnail.py` raises at import), so byte hashing would make the
    same pixels look changed across processes. Pixels are what the encoder
    decodes the PNGs back to, so pixel content is exactly the input.

    Deterministic by construction: the plan is manifest-derived, and the
    card renderers are pinned pixel-identical by their own tests."""
    if overlays is None:
        overlays = _plan_overlay_descriptors(plan)
    h = hashlib.sha256()

    def note(kind, payload):
        h.update(kind.encode("utf-8"))
        h.update(b"\0")
        h.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
        h.update(b"\0")

    if source is not None:
        note("source", source)
    # The encode contract: the SAME plan and pixels encoded under a different
    # delivery spec or audio recipe are a different episode, so the settings
    # the encode actually consumes are freshness inputs too.
    note("encode", {
        "spec_version": conform.SPEC_VERSION,
        "video_filter": conform.video_filter_chain(),
        "video_args": conform.video_encode_args(),
        "audio": {"codec": "aac", "bitrate": AUDIO_BITRATE,
                  "rate": SAMPLE_RATE, "layout": AUDIO_LAYOUT},
    })
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
    for spec in overlays:
        payload_spec = {k: v for k, v in spec.items() if k != "overlay_kind"}
        # Every spec field but the renderer tag is hashed, so an authoring
        # Copy or Next line edit is a digest change and forces a rebuild.
        note({"plate": "plate", "card": "card", "chat": "chat"}.get(
            spec["overlay_kind"], "overlay"),
             payload_spec)
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
    """``(digest, state)`` for the sidecar on record.

    ``state`` is ``"ok"`` with a usable digest, ``"missing"`` when no
    sidecar exists, and ``"corrupt"`` when one exists but cannot be read as
    a digest. Missing and corrupt both mean REBUILD -- freshness fails
    closed: an episode whose inputs cannot be accounted for is re-encoded,
    never adopted and never skipped."""
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError:
        return None, "missing"
    try:
        digest = json.loads(raw)["sha256"]
        if not isinstance(digest, str) or not digest:
            raise KeyError("sha256")
    except (ValueError, KeyError, TypeError):
        return None, "corrupt"
    return digest, "ok"


def _write_input_digest(path, digest, staged):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "sha256": digest,
        "inputs": [Path(p).name for p in staged],
    }, indent=1) + "\n", encoding="utf-8")
    return path


def _render_overlay_pngs(plan, picture_info, work_dir, slug, unresolved,
                         log):
    """The episode's overlay inputs, in graph order: the fixed plates and the
    authoring pass's chat pills through tools/plate.py (unmodified), then the
    project-lore overlays drawn here.

    ``picture_info`` is ``(picture_rect, status)`` from the farm preflight
    (`_source_preflight_farm`) -- detection never runs on the host.

    Returns ``(pngs, descriptors)`` in LOCKSTEP -- ``descriptors[i]`` is the
    plan entry (plate spec or lore overlay, each tagged ``overlay_kind``)
    that produced ``pngs[i]``. This pair, not `plan["plates"]` /
    `plan["overlays"]`, is the single source `build_episode` must hand to
    `episode_filtergraph`, `encode_episode_command`, and
    `episode_input_digest`: an entry this function cannot place is recorded
    in ``unresolved`` and dropped from BOTH lists together, so a caller
    that only ever sees the rendered pair can never build a graph that
    indexes an input the argv does not loop.

    Seats are measured against the PICTURE, never the raw frame (issue
    #161's rule, taken from standalone.py): an undecodable source drops the
    seats and records why -- the unplated episode still ships."""
    overlay_pngs = []
    rendered = []
    descriptors = _plan_overlay_descriptors(plan)
    if not descriptors:
        return overlay_pngs, rendered
    picture, status = picture_info
    if status == "undecodable":
        unresolved.extend(
            {"id": item["id"],
             "reason": "the source picture area could not be decoded, so "
                       "the seat could not be measured against the picture "
                       "and was not placed"}
            for item in descriptors)
        return overlay_pngs, rendered
    drawable = [dict(spec, overlay_kind="plate") for spec in plan["plates"]] + \
        [dict(spec, overlay_kind="card") for spec in plan.get("cards", [])] + \
        [dict(spec, overlay_kind="chat") for spec in plan.get("chats", [])]
    if drawable:
        plates_dir = Path(work_dir) / f"{slug}-plates"
        # Fixed plates and the authoring chat pills both draw through
        # tools/plate.py, unmodified; the chat pills carry `kind: chat`.
        plate.render_all(drawable, plates_dir, picture=picture)
        for spec in drawable:
            png = plates_dir / f"plate_{spec['id']}.png"
            if not png.exists():
                unresolved.append(
                    {"id": spec["id"],
                     "reason": f"no plate was rendered at {png}"})
                continue
            # An identity-proven chat speaker whose cached face is absent
            # renders plate.py's drawn crest -- degrade, never block -- but
            # the gap is a punch-list item, not silence.
            if spec["overlay_kind"] in ("chat", "card") and spec.get("avatar"):
                if not _cached_avatar_present(spec["avatar"]):
                    unresolved.append({
                        "id": spec["id"],
                        "reason": f"the cached avatar {spec['avatar']} for "
                                  f"speaker {spec['speaker']!r} is absent; "
                                  "the drawn crest stands in -- warm the "
                                  "cache (`fetch-avatars`) before delivery",
                    })
            overlay_pngs.append(png.resolve())
            rendered.append(spec)
    for overlay in plan["overlays"]:
        card = render_lore_overlay(overlay)
        frame = place_lore_overlay(card, overlay["position"], picture)
        png = Path(work_dir) / f"{slug}-overlay-{overlay['id']}.png"
        frame.save(png)
        overlay_pngs.append(png.resolve())
        rendered.append(dict(overlay, overlay_kind="lore"))
    return overlay_pngs, rendered


def build_episode(manifest_path, episode_number, log=print, work_dir=None):
    """One episode, built for REVIEW: cards, one farm-only encode, rough
    thumbnail, unresolved sidecar. Writes only the rough paths
    (`rough/s01eNN-<slug>.mp4` and its thumbnail); the top-level final and
    its thumbnail are promotion-only and never touched here.

    The Hive workspace runs NO local ffmpeg/ffprobe, not even preflight:
    the source's stream facts and picture area are probed on the farm
    (`_source_preflight_farm`), the encode runs there or the build raises
    farm.FarmError before any render (`encode_episode` permits no local
    fallback), and validation probes the fetched rough on the farm.

    Freshness is content-derived, never duration-derived: the plan, the
    encode contract, and the pixel content of every staged input hash to a
    digest kept in ``<slug>-inputs.json`` beside the unresolved sidecar, and
    an existing output is kept only when it verifies AND the digest still
    matches -- a same-duration copy change rebuilds. Freshness fails CLOSED:
    a missing or corrupt digest sidecar is a rebuild, never an adoption and
    never a skip. Either way the skip rewrites the unresolved sidecar from
    the CURRENT plan and prints the items before returning -- it can never
    be left missing or stale."""
    manifest = load_manifest(manifest_path)
    plan = episode_plan(manifest, episode_number)
    chapter = plan["chapter"]
    slug = episode_slug(chapter)
    # Rough-first: the build writes the reviewable rough and its thumbnail
    # only; the top-level final is promotion's job, never a build's.
    out = episode_rough_path(chapter)
    thumb = thumbnail_rough_path(chapter)
    work = Path(work_dir) if work_dir is not None else WORK_DIR
    work.mkdir(parents=True, exist_ok=True)

    source = Path(ensure_source(manifest)).resolve()
    unresolved = list(plan["unresolved"])

    # Preflight ON THE FARM: the source's audio rate (for the graph) and
    # picture area (for overlay seats). An unreachable farm raises here,
    # before any render -- the Hive workspace permits no local fallback.
    audio_rate, picture, picture_status = _source_preflight_farm(
        source, log=log)

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

    overlay_pngs, overlay_descriptors = _render_overlay_pngs(
        plan, (picture, picture_status), work, slug, unresolved, log)
    staged = [*stills, *overlay_pngs]
    digest = episode_input_digest(plan, staged, overlays=overlay_descriptors,
                                  source=manifest["source"])
    digest_path = work / f"{slug}-inputs.json"

    if out.exists() and not verify_episode(manifest, episode_number):
        stored, state = _read_input_digest(digest_path)
        if state == "ok" and stored == digest:
            log(f"  {slug}: already built and verified -- {out}")
            _write_unresolved(work, slug, unresolved)
            for item in unresolved:
                log(f"  unresolved: {item}")
            if not thumb.exists():
                make_thumbnail(plan["segments"][1]["asset"], thumb)
                log(f"  thumbnail: {thumb}")
            return out
        if state == "ok":
            log(f"  {slug}: content changed since the delivered encode "
                f"({stored[:12]}... -> {digest[:12]}...) -- rebuilding")
        elif state == "corrupt":
            log(f"  {slug}: the digest sidecar {digest_path} is unreadable "
                f"-- rebuilding (freshness fails closed)")
        else:
            log(f"  {slug}: no digest sidecar on record at {digest_path} "
                f"-- rebuilding (freshness fails closed)")

    out.parent.mkdir(parents=True, exist_ok=True)
    out = out.resolve()
    graph = episode_filtergraph(
        plan, overlay_descriptors, source_rate=audio_rate)
    argv = encode_episode_command(
        ["ffmpeg"], source, stills, overlay_pngs, graph, out)
    where = encode_episode(
        argv, inputs=[source, *stills, *overlay_pngs], out=out,
        expected_duration=plan["expected_duration"],
        label=f"Hive {slug}")
    log(f"  {slug}: encoded on {where} -- {out}")

    _write_input_digest(digest_path, digest, staged)
    _write_unresolved(work, slug, unresolved)
    for item in unresolved:
        log(f"  unresolved: {item}")

    make_thumbnail(plan["segments"][1]["asset"], thumb)
    log(f"  thumbnail: {thumb}")

    problems = verify_episode(manifest, episode_number)
    for problem in problems:
        log(f"  verify: {problem}")
    return out


def build_all(manifest_path=None, log=print, work_dir=None):
    """All twelve episodes, in chapter order. The source fetch happens once:
    the supplied file (or cache) is the evidence it ran."""
    manifest = load_manifest(manifest_path)
    return [build_episode(manifest_path or MANIFEST, chapter["number"],
                          log=log, work_dir=work_dir)
            for chapter in manifest["chapters"]]


# --- the full-season cut ---------------------------------------------------------------


def concat_list_lines(manifest, paths=None):
    """The concat-demuxer list: the ROUGH episodes, in order. ``paths``
    overrides the episode set -- the cut joins what is actually joinable,
    which can be fewer than twelve (see build_cut). The default is the
    rough lane on purpose: no helper defaults to reading or writing a
    final."""
    if paths is None:
        paths = [episode_rough_path(c) for c in manifest["chapters"]]
    return [f"file '{Path(p).resolve()}'" for p in paths]


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


def concat_episodes(manifest, out_path=None, work_dir=None, paths=None):
    """Concatenate the built episodes into the full-season ROUGH cut.

    A pure remux -- the picture and sound are both stream-copied -- but even
    a remux is a media command, and the Hive workspace forbids local
    ffmpeg: the join ships to the farm through `farm.run_encode` with the
    concat list travelling as a pod-side text file (the same mechanism
    megacut's assemble uses), farm-only and farm-verified. ``paths`` is the
    ordered join set when the caller has conformed or omitted episodes; the
    defaults are the ROUGH lanes (all twelve roughs into
    `season-01-full-rough.mp4`), so a bare call can never touch a final."""
    out_path = Path(out_path) if out_path else full_cut_rough_path(manifest)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    work = Path(work_dir) if work_dir is not None else WORK_DIR
    work.mkdir(parents=True, exist_ok=True)
    list_path = work / "season-01-concat.txt"
    content = "\n".join(concat_list_lines(manifest, paths)) + "\n"
    list_path.write_text(content, encoding="utf-8")
    farm.run_encode(
        concat_command(["ffmpeg"], list_path, out_path),
        inputs=list(paths) if paths is not None
        else [episode_rough_path(c) for c in manifest["chapters"]],
        out=out_path, text_files={str(list_path): content},
        fallback=False, local_probe=False,
        label="Hive season cut")
    return out_path


def _conform_for_join(path, log):
    """``conform.ensure`` with the delivery-fps container-rounding verdict.

    The cut joins blind, so a non-conformant episode is substituted with its
    conformed copy through the repo's one conformance path. The ONE
    adjustment is the known container rounding: whole-second card durations
    never divide 60000/1001 evenly, so a correct delivery's avg_frame_rate
    lands outside conform's 1e-3 fps tolerance (`_fps_is_delivery`). Without
    the override every delivered episode would "need" a re-encode on every
    cut.

    The probe is the farm's (`_probe_streams_farm`), and the conform encode
    is farm-only as well (`allow_local=False`): the Hive workspace runs no
    local ffmpeg even as a repair path -- an unreachable farm fails the cut
    visibly."""
    def probe(p):
        _duration, video, _audio = _facts_from_probe_doc(
            _probe_streams_farm(p, label=f"Hive conform probe "
                                         f"{Path(p).name}"))
        props, _fps_ok = _fps_with_delivery_rounding(video)
        return props

    return conform.ensure(path, ffmpeg=["ffmpeg"], _probe=probe, log=log,
                          use_farm=True, allow_local=False,
                          local_probe=False)


def build_cut(manifest_path=None, log=print):
    """The ONE way to the full-season REVIEW cut: build every episode, then
    join what is joinable. Reads and writes rough artifacts only (the
    season assembly lands at `season-01-full-rough.mp4`);
    `season-01-full.mp4` exists only through `promote_cut`. Every probe and
    encode is the farm's; an unreachable farm fails the cut visibly before
    any render.

    Returns ``(out_path, problems)`` -- every finding, episode-level and
    post-join, empty when everything verified. Findings REPORT, they never
    withhold the film (AGENTS.md: nothing blocks a release): an episode
    that fails verification is logged and still considered for the join;
    one that is missing or undecodable is reported and left out, and the
    cut is the best reachable join of the episodes that remain. Before the
    blind stream-copy join, every present and decodable episode goes through
    the repo's one conformance path (`conform.ensure`), which substitutes a
    spec-conformant copy when the delivered file is not joinable as-is --
    the substitution is logged. Picture conformance is followed by an audio
    check: an episode whose sound is not the delivery codec/rate/layout is
    reported and omitted from the join, because the concat stream-copies
    audio and there is no second audio encode path. The CLI and the
    justfile both go through here; there is no second path to a cut."""
    manifest = load_manifest(manifest_path)
    build_all(manifest_path, log=log)
    problems = []
    joinable = []
    for chapter in manifest["chapters"]:
        slug = episode_slug(chapter)
        findings = verify_episode(manifest, chapter["number"])
        for finding in findings:
            log(f"  verify: {finding}")
        problems.extend(findings)
        # The review assembly joins the ROUGH episodes, never the finals.
        path = episode_rough_path(chapter)
        if not path.exists() or path.stat().st_size == 0:
            problems.append(
                f"{slug}: no episode at {path} -- the cut joins without it")
            log(f"  cut: {problems[-1]}")
            continue
        try:
            joined, status = _conform_for_join(path, log)
            bad_audio = _audio_problems(_probe_audio_farm(joined))
        except Exception as exc:
            problems.append(
                f"{slug}: {path.name} could not be probed or conformed "
                f"({exc}) -- the cut joins without it")
            log(f"  cut: {problems[-1]}")
            continue
        if bad_audio:
            problems.append(
                f"{slug}: {Path(joined).name} audio cannot join "
                f"({'; '.join(bad_audio)}) -- the cut joins without it")
            log(f"  cut: {problems[-1]}")
            continue
        if status != "conforms":
            log(f"  cut: {slug}: joining the conformed copy {joined} "
                f"({status}) in place of the delivered file")
        joinable.append((chapter, Path(joined)))
    if not joinable:
        raise RuntimeError(
            "no episode is present and decodable -- there is nothing to join")
    out = concat_episodes(manifest, out_path=full_cut_rough_path(manifest),
                          paths=[p for _c, p in joinable])
    log(f"  full cut: {out} ({len(joinable)} of "
        f"{len(manifest['chapters'])} episodes)")
    expected = sum(episode_expected_duration(manifest, c)
                   for c, _p in joinable)
    cut_problems = _probe_delivery_streams_farm(out, expected,
                                                CUT_TOLERANCE_S)
    for problem in cut_problems:
        log(f"  verify: {problem}")
    problems.extend(cut_problems)
    return out, problems


# --- verification ---------------------------------------------------------------------


def _probe_audio_farm(path):
    """The first audio stream's delivery-relevant props, probed ON the farm
    (the join stream-copies sound, so this check gates it)."""
    _duration, _video, audio = _facts_from_probe_doc(
        _probe_streams_farm(path, label=f"Hive audio probe "
                                        f"{Path(path).name}"))
    return audio


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


def _implied_frame_pad(props):
    """Seconds the video track's duration overstates its frame content --
    when that overstatement is exactly a whole number of delivery-rate
    frame periods; otherwise None.

    ffprobe's ``avg_frame_rate`` is nb_frames over TRACK duration, so a
    track padded by k frame periods (muxer flush/edit-list slop at the
    file's tail) reads low by exactly r×k/(N+k) while the encoded clock is
    the delivery rate. That is the only shape this accepts, and every guard
    matters:

    * the pad must be non-negative -- a genuinely FASTER clock (60/1) packs
      more frames than delivery slots and reads negative;
    * it must be a whole number of frame periods (to 0.01 frame) -- a wrong
      constant clock almost never lands on one;
    * it must fit inside the episode duration tolerance -- a slower clock
      (30/1) needs a pad far past it;
    * it needs nb_frames and the stream duration, which only the farm's
      full-stream probe supplies -- the legacy local probe lacks them and
      keeps the old verdict.

    Example that motivated this: episode 12's rough probed
    avg_frame_rate=330240000/5514509, which factors EXACTLY as
    (60000/1001) x (5504/5509) -- 5504 frames on a 5509-frame-period track:
    the delivery clock, padded by 5 frame periods (0.083s), not a wrong
    rate."""
    try:
        frames = int(str(props.get("nb_frames")))
        duration = float(str(props.get("duration")))
    except (TypeError, ValueError):
        return None
    if frames <= 0 or duration <= 0:
        return None
    wnum, _, wden = conform.DELIVERY.fps.partition("/")
    period = float(wden) / float(wnum)
    pad = duration - frames * period
    if pad < -1e-9 or pad > EPISODE_TOLERANCE_S:
        return None
    slots = pad / period
    if abs(slots - round(slots)) > 1e-2:
        return None
    return pad


def _fps_with_delivery_rounding(props):
    """``(props, fps_ok)`` with the container-rounding verdict applied once.

    The ONE shared override for the known mp4 rounding (`_fps_is_delivery`):
    the verdict is decided on the MEASURED ``avg_frame_rate`` alone.
    ``r_frame_rate`` is the container's nominal/declared cadence, not what
    was actually encoded -- accepting a file because its ``r_frame_rate``
    reads correct would launder a genuinely wrong average (a real 30/1
    encode muxed with a 60000/1001 nominal rate, say) into a pass, which is
    exactly backwards: the average is the number this check exists to
    verify. When the measured average lands inside the slack, the returned
    props carry the exact delivery fps so downstream rational comparisons
    agree; otherwise the measured props are returned UNCHANGED, so a real
    mismatch is reported at its own measured value, never laundered. Both
    the join probe (`_conform_for_join`) and the delivery report
    (`_delivery_stream_problems`) go through here, so the two can never
    drift apart.

    The one extension, still decided on the measured average alone: when
    the average misses the slack, `_implied_frame_pad` re-judges it as
    frame arithmetic -- nb_frames and track duration from the SAME measured
    stream, so a track merely PADDED by a few frame periods (the episode-12
    case) passes, while a wrong clock still fails."""
    if _fps_is_delivery(props.get("avg_frame_rate")):
        return dict(props, avg_frame_rate=conform.DELIVERY.fps), True
    if _implied_frame_pad(props) is not None:
        return dict(props, avg_frame_rate=conform.DELIVERY.fps), True
    return props, False


def _audio_problems(audio):
    """The ways a probed audio stream cannot join the cut, as strings.

    The join stream-copies sound, so codec, sample rate and channel layout
    must all be the delivery spec; anything else is reported and the
    episode is omitted -- there is no second audio encode path."""
    bad = []
    if audio.get("codec_name") != "aac":
        bad.append(f"audio codec {audio.get('codec_name')!r} is not aac")
    if int(audio.get("sample_rate", 0)) != SAMPLE_RATE:
        bad.append(f"sample rate {audio.get('sample_rate')!r} "
                   f"is not {SAMPLE_RATE}")
    if audio.get("channel_layout") != AUDIO_LAYOUT:
        bad.append(f"channel layout {audio.get('channel_layout')!r} "
                   f"is not {AUDIO_LAYOUT}")
    return bad


def _delivery_stream_problems(name, duration, video, audio, expected,
                              tolerance):
    """The problems a delivered file has, as a list -- empty means verified.
    Pure: the facts arrive already probed (on the farm, for Hive), and this
    judges them.

    The stream checks ARE `conform.mismatches`: pixel format, color,
    profile and level ride along with codec/size/rate because the full cut
    joins these files blind. The ONE override is the frame rate: conform's
    rational comparison cannot know the mp4 container-rounding verdict
    (`_fps_is_delivery`), so a conform frame-rate mismatch is kept only
    when `_fps_is_delivery` also fails. A report, never a gate: the caller
    logs the problems and ships anyway (AGENTS.md: nothing blocks a
    release)."""
    problems = []
    if abs(duration - expected) > tolerance:
        problems.append(
            f"{name}: duration {duration:.3f}s is "
            f"{duration - expected:+.3f}s from the expected "
            f"{expected:.3f}s (tolerance {tolerance}s)")
    video, fps_ok = _fps_with_delivery_rounding(video)
    for bad in conform.mismatches(video):
        if fps_ok and bad.startswith("frame rate"):
            continue
        problems.append(f"{name}: {bad}")
    for bad in _audio_problems(audio):
        problems.append(f"{name}: {bad}")
    return problems


def _probe_delivery_streams_farm(path, expected, tolerance):
    """Delivered-file validation with the probe ON THE FARM.

    The rough/final file is staged to a pod and ffprobed there; the host
    only parses the returned JSON. An unreachable farm or an unreadable
    probe answer is a visible problem entry -- never a local ffprobe
    fallback, which the Hive workspace forbids."""
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return [f"{path}: missing or empty"]
    try:
        doc = _probe_streams_farm(path, label=f"Hive verify {path.name}")
    except farm.FarmError as exc:
        return [f"{path.name}: remote validation failed ({exc}); the Hive "
                "workspace probes on the farm, never on the host"]
    try:
        duration, video, audio = _facts_from_probe_doc(doc)
    except (RuntimeError, KeyError, TypeError, ValueError) as exc:
        return [f"{path.name}: the farm's probe could not be read ({exc})"]
    return _delivery_stream_problems(path.name, duration, video, audio,
                                     expected, tolerance)


def verify_episode(manifest, number, stage="rough"):
    """Probe one episode's file ON THE FARM. ``stage="rough"`` (the
    default: what the build commands produce and what review watches)
    targets the rough; ``stage="final"`` targets the promoted delivery."""
    chapter = chapter_by_number(manifest, number)
    path = episode_output_path(chapter) if stage == "final" \
        else episode_rough_path(chapter)
    return _probe_delivery_streams_farm(
        path, episode_expected_duration(manifest, chapter),
        EPISODE_TOLERANCE_S)


def verify_cut(manifest, stage="rough"):
    """Twelve episodes in order, then the cut at the aggregate duration --
    the rough assembly by default, the promoted delivery with
    ``stage="final"``. All probing happens on the farm."""
    cut = full_cut_path(manifest) if stage == "final" \
        else full_cut_rough_path(manifest)
    problems = []
    for chapter in manifest["chapters"]:
        problems.extend(
            verify_episode(manifest, chapter["number"], stage=stage))
    problems.extend(_probe_delivery_streams_farm(
        cut, cut_expected_duration(manifest), CUT_TOLERANCE_S))
    return problems


# --- promotion: the ONLY write path to the finals ---------------------------------


def promote_episode(manifest, number, log=print):
    """Promote one reviewed rough to its final delivery paths.

    This is the ONLY boundary that writes the top-level `s01eNN-<slug>.mp4`
    and its `-thumbnail.jpg`, and it is a pure file copy -- no media work,
    no re-encode -- run by a human after local approval of the rough. A
    released episode always carries its paired thumbnail, so a missing
    rough (or missing rough thumbnail) refuses rather than releasing an
    incomplete pair. Nothing calls this automatically."""
    chapter = chapter_by_number(manifest, number)
    rough = episode_rough_path(chapter)
    if not rough.exists() or rough.stat().st_size == 0:
        raise FileNotFoundError(
            f"no reviewed rough at {rough} -- build and approve it first")
    rough_thumb = thumbnail_rough_path(chapter)
    if not rough_thumb.exists() or rough_thumb.stat().st_size == 0:
        raise FileNotFoundError(
            f"no rough thumbnail at {rough_thumb} -- a released episode "
            "always carries its thumbnail")
    final = episode_output_path(chapter)
    final_thumb = thumbnail_output_path(chapter)
    final.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(rough, final)
    shutil.copy2(rough_thumb, final_thumb)
    log(f"  promoted: {final}")
    log(f"  promoted: {final_thumb}")
    return final


def promote_cut(manifest, log=print):
    """Promote the reviewed season assembly to `season-01-full.mp4`.

    Same boundary rule as `promote_episode`: a pure copy of the approved
    rough cut, refusing when no rough cut exists."""
    rough = full_cut_rough_path(manifest)
    if not rough.exists() or rough.stat().st_size == 0:
        raise FileNotFoundError(
            f"no reviewed rough cut at {rough} -- build and approve it "
            "first")
    final = full_cut_path(manifest)
    shutil.copy2(rough, final)
    log(f"  promoted: {final}")
    return final


# --- Task 4: weekly contributor recognition ---------------------------------
#
# Recognition is public GitHub activity, not Hive calendar metrics, and not
# calendar-week precise: the season ships roughly every seven days, so each
# selection run counts commit authors in the configured repositories between
# the prior snapshot's captured_at and now. The no-repeat ledger in the
# manifest is canonical and singular -- prior IDs are derived from it, never
# kept in a second list. A run that cannot read a configured repository
# fails WITHOUT touching the ledger. Profile resolution is sharper: a
# definitive GitHub HTTP 404 for a durable account ID means the profile no
# longer exists, and that candidate is recorded as excluded -- one suspended
# account can never wedge every future weekly snapshot. Anything ambiguous
# (a 5xx, a reset connection, an unparsable body) is retried exactly once
# and then fails the whole run BEFORE any mutation: a candidate is never
# silently demoted on a maybe-transient error. A run with no eligible
# contributor still issues the next episode with an empty dossier list and
# a recorded note (AGENTS.md: degrade, never block).

RECOGNITION_PAGE_SIZE = 100
RECOGNITION_LIMIT = 3


class RecognitionError(RuntimeError):
    """The selection cannot vouch for its result -- an unreadable
    repository, an unresolvable profile, or a profile returned for the
    wrong account ID. The manifest and ledger are untouched."""


class ProfileNotFound(RecognitionError):
    """A definitive GitHub HTTP 404 for a durable account ID: the profile
    no longer exists. Never a run failure -- the caller records it as the
    candidate's exclusion reason."""


def _utcnow():
    return datetime.now(timezone.utc).replace(microsecond=0) \
        .isoformat().replace("+00:00", "Z")


def commits_command(repo, since, until):
    """The paginated commit-listing call for one configured repository."""
    return [
        "gh", "api", "--paginate",
        f"repos/{repo}/commits?since={since}&until={until}"
        f"&per_page={RECOGNITION_PAGE_SIZE}",
    ]


def profile_command(account_id):
    """The user-by-ID call that resolves a candidate's profile snapshot.

    The durable numeric account ID, never the renameable login: a freed and
    recycled login would otherwise attach the new owner's name, avatar and
    URL to the original author's commits."""
    return ["gh", "api", f"user/{account_id}"]


def parse_paginated_json(text):
    """Every object in ``gh api --paginate`` output.

    `--paginate` prints each page's body back to back, so the stdout of one
    command is zero or more concatenated JSON arrays -- not one document.
    Pages are flattened; a non-array body (e.g. a single-object endpoint)
    yields itself."""
    decoder = json.JSONDecoder()
    items, idx = [], 0
    while True:
        while idx < len(text) and text[idx].isspace():
            idx += 1
        if idx >= len(text):
            return items
        page, idx = decoder.raw_decode(text, idx)
        items.extend(page if isinstance(page, list) else [page])


def _live_runner(cmd):
    """The real `gh` call. Live GitHub access lives behind this and
    `fixture_runner` only, so the whole selection is testable offline."""
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode != 0:
        raise RecognitionError(
            f"{' '.join(cmd)} failed: {(done.stderr or '').strip()}")
    return done.stdout


def _fragment_matches(fragment, token):
    """Exact endpoint matching for canned responses: a fragment matches a
    whole command token, or a token it prefixes at a path/query boundary --
    so ``user/8100`` can never answer for ``user/81000``."""
    if token == fragment:
        return True
    return token.startswith(fragment) and token[len(fragment)] in "?/&"


def fixture_runner(fixture):
    """A runner over canned responses: ``{url-fragment: {"pages": [...]} or
    {"body": ...} or {"status": 404}}``. Pages are re-serialized concatenated
    so the paginated parser is exercised exactly as with live `gh`; a
    ``{"status": 404}`` payload is the definitive not-found case and raises
    ProfileNotFound. A command matching no key is the failed-repo case."""
    def run(cmd):
        for fragment, payload in fixture.items():
            if any(_fragment_matches(fragment, token) for token in cmd):
                if payload.get("status") == 404:
                    raise ProfileNotFound(
                        f"gh api {fragment} failed: gh: Not Found "
                        f"(HTTP 404)")
                if "pages" in payload:
                    return "".join(json.dumps(p) for p in payload["pages"])
                return json.dumps(payload["body"])
        raise RecognitionError(f"fixture has no response for: "
                               f"{' '.join(cmd)}")
    return run


def collect_activity(repositories, since, until, runner):
    """Distinct commit authors per durable numeric account ID, with the
    repo/SHA evidence. Commits are deduplicated by SHA across pages and
    repositories; a commit with no linked GitHub account has no durable ID
    to key the ledger on and is skipped. Any unreadable repository raises
    RecognitionError -- the caller leaves the ledger untouched."""
    authors = {}
    for repo in repositories:
        try:
            out = runner(commits_command(repo, since, until))
        except Exception as exc:
            raise RecognitionError(
                f"{repo}: cannot read commits ({exc})") from exc
        for commit in parse_paginated_json(out):
            author = commit.get("author") or {}
            account_id = author.get("id")
            sha = commit.get("sha")
            if not account_id or not sha:
                continue
            entry = authors.setdefault(
                account_id, {"author": author, "evidence": {}, "seen": set()})
            # One SHA is one commit however many pages or repositories
            # return it (shared history shows up in every repo that has it);
            # it is evidence in the FIRST configured repo that reported it.
            if sha in entry["seen"]:
                continue
            entry["seen"].add(sha)
            entry["evidence"].setdefault(repo, []).append(sha)
    for entry in authors.values():
        del entry["seen"]
    return authors


def _fetch_profile(account_id, runner):
    """One profile-resolution attempt by durable numeric account ID.

    A runner error whose text carries a definitive HTTP 404 is translated
    to ProfileNotFound; every other failure propagates unchanged."""
    try:
        return json.loads(runner(profile_command(account_id)))
    except RecognitionError as exc:
        if "HTTP 404" in str(exc):
            raise ProfileNotFound(
                f"profile for account id {account_id} no longer exists "
                f"({exc})") from exc
        raise


def _resolve_profile(account_id, runner):
    """The candidate's profile, with exactly one retry on ambiguity.

    A definitive HTTP 404 (ProfileNotFound) is never retried: the account
    is gone, and the caller records the exclusion. Anything else -- a 5xx,
    a reset connection, an unparsable body -- is ambiguous, so it is
    retried once; a second failure propagates and aborts the whole
    selection before anything is written. A candidate is never silently
    demoted on a maybe-transient error."""
    try:
        return _fetch_profile(account_id, runner)
    except ProfileNotFound:
        raise
    except Exception:
        return _fetch_profile(account_id, runner)


def _exclusion(candidate, fixed_ids, credited_ids):
    """Why this account cannot be dossiered, or None. Bots and non-User
    accounts, the fixed cast, and every ID already in the no-repeat ledger
    are all exclusions -- the ledger keys on the durable numeric ID, so a
    renamed login is still the same credited person."""
    if candidate["type"] != "User":
        return f"account type {candidate['type']!r} is not a User"
    if candidate["id"] in fixed_ids:
        return "fixed cast"
    if candidate["id"] in credited_ids:
        return "already credited in the no-repeat ledger"
    return None


def recognition_snapshot(manifest, since, until, runner=_live_runner,
                         now=None):
    """The full candidate evidence for one window, plus the selection.

    Every distinct commit author is recorded with an exclusion reason or
    resolved through the user-by-ID API (which carries the public `name`
    the commit listing does not). Profiles resolve by the durable numeric
    account ID and the returned `id` must match exactly: anything less
    could attach a recycled login's new owner -- their name, avatar, URL --
    to somebody else's commits, a false claim about real people. A profile
    that cannot be resolved because GitHub definitively says the account is
    gone (HTTP 404) is recorded with the exclusion "profile no longer
    exists" -- a suspended or deleted profile never wedges the selection.
    A profile that fails ambiguously even after one retry, or resolves to
    the wrong ID, fails the whole
    run like an unreadable repository: a candidate is never silently
    demoted on a transient error. Selection is up to RECOGNITION_LIMIT by
    commit count descending, normalized login ascending, numeric ID
    ascending."""
    captured = now or _utcnow()
    ledger = manifest.get("contributor_ledger") or {}
    repositories = ledger.get("repositories") or []
    if not repositories:
        raise RecognitionError(
            "contributor_ledger.repositories is empty: no recognition "
            "repositories are configured")
    fixed_ids = {m["github_id"] for m in manifest.get("fixed_cast") or []
                 if m.get("github_id")}
    credited_ids = set(ledger.get("credited_github_ids") or [])
    activity = collect_activity(repositories, since, until, runner)
    candidates = []
    for account_id in sorted(activity):
        entry = activity[account_id]
        author = entry["author"]
        candidate = {
            "id": account_id,
            "node_id": author.get("node_id"),
            "login": author.get("login") or "",
            "name": None,
            "html_url": author.get("html_url"),
            "avatar_url": author.get("avatar_url"),
            "type": author.get("type") or "",
            "fetched_at": captured,
            "commits": sum(len(s) for s in entry["evidence"].values()),
            "evidence": [
                {"repo": repo, "shas": sorted(shas)}
                for repo, shas in sorted(entry["evidence"].items())
            ],
        }
        reason = _exclusion(candidate, fixed_ids, credited_ids)
        if reason:
            candidate["excluded"] = reason
        candidates.append(candidate)
    for candidate in candidates:
        if "excluded" in candidate:
            continue
        try:
            profile = _resolve_profile(candidate["id"], runner)
        except ProfileNotFound:
            candidate["excluded"] = "profile no longer exists"
            continue
        except Exception as exc:
            raise RecognitionError(
                f"profile for account id {candidate['id']} could not be "
                f"resolved ({exc}); aborting the whole selection before "
                f"anything is written") from exc
        if profile.get("id") != candidate["id"]:
            raise RecognitionError(
                f"user/{candidate['id']} returned id "
                f"{profile.get('id')!r}: refusing to attach another "
                f"account's identity to these commits")
        for field in ("node_id", "login", "name", "html_url", "avatar_url",
                      "type"):
            if field in profile:
                candidate[field] = profile[field]
        reason = _exclusion(candidate, fixed_ids, credited_ids)
        if reason:
            candidate["excluded"] = reason
    eligible = [c for c in candidates if "excluded" not in c]
    eligible.sort(key=lambda c: (-c["commits"], c["login"].lower(), c["id"]))
    selected = eligible[:RECOGNITION_LIMIT]
    return {
        "captured_at": captured,
        "window": {"since": since, "until": until},
        "candidates": candidates,
        "selected_github_ids": [c["id"] for c in selected],
    }


def _dossier_entry(candidate):
    """The chapter's committed profile snapshot for one selected contributor:
    factual GitHub fields only, plus the window's commit count."""
    entry = {
        "login": candidate["login"],
        "github_id": candidate["id"],
        "name": candidate.get("name"),
        "commits": candidate["commits"],
    }
    for field in ("node_id", "html_url", "avatar_url", "type", "fetched_at"):
        if candidate.get(field):
            entry[field] = candidate[field]
    return entry


def _atomic_write_json(path, data):
    """Write-then-rename beside the target: a reader never sees half a
    manifest, and a failed validation earlier leaves the file untouched."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def select_next_episode(manifest_path=None, since=None, runner=_live_runner,
                        now=None, log=print):
    """Issue the next episode's contributor dossiers, atomically with the
    snapshot and ledger update.

    The window runs from the prior snapshot's ``captured_at`` (or an explicit
    ``since`` for the first run) to ``now``. The next UNISSUED chapter -- the
    first with no ``dossiers`` key -- is filled; a chapter that already has
    dossiers is never overwritten. An empty selection still issues the
    chapter, with an empty list and a recorded note: the release is never
    held for a quiet week. The updated manifest is validated BEFORE it is
    written, and any repository-read or profile-resolution failure raises
    before anything is written. Returns ``(snapshot, chapter_or_none)``."""
    path = Path(manifest_path or MANIFEST)
    manifest = load_manifest_data(json.loads(path.read_text("utf-8")))
    ledger = manifest["contributor_ledger"]
    snapshots = ledger.setdefault("snapshots", [])
    if since is None:
        if not snapshots:
            raise RecognitionError(
                "no prior snapshot to start the window from; pass --since "
                "for the first selection")
        since = snapshots[-1]["captured_at"]
    until = now or _utcnow()
    snapshot = recognition_snapshot(manifest, since, until, runner=runner,
                                    now=until)
    chapter = next((c for c in manifest["chapters"] if "dossiers" not in c),
                   None)
    snapshot["episode"] = chapter["number"] if chapter else None
    if chapter is None:
        snapshot["note"] = ("every chapter is already issued; the window is "
                            "recorded and no episode changes")
    else:
        order = {cid: i for i, cid in
                 enumerate(snapshot["selected_github_ids"])}
        selected = sorted((c for c in snapshot["candidates"]
                           if c["id"] in order), key=lambda c: order[c["id"]])
        chapter["dossiers"] = [_dossier_entry(c) for c in selected]
        if selected:
            ledger.setdefault("credited_github_ids", []).extend(
                snapshot["selected_github_ids"])
        else:
            note = (f"no eligible contributors in the window {since} .. "
                    f"{until}: the episode ships without dossier cards")
            chapter["dossier_note"] = note
            snapshot["note"] = note
        log(f"episode {chapter['number']} ({chapter['slug']}): "
            f"{len(selected)} contributor(s) selected"
            + ("" if selected else " -- none eligible, recorded"))
    snapshots.append(snapshot)
    # The write happens only after the updated record validates; a failure
    # above -- including any unreadable repository -- leaves the file as it
    # was.
    load_manifest_data(manifest)
    _atomic_write_json(path, manifest)
    return snapshot, chapter


def recognition_status(manifest):
    """Per-episode issue/delivery state: ``dossiers`` present means issued,
    the output file existing means delivered."""
    rows = []
    for chapter in manifest["chapters"]:
        issued = "dossiers" in chapter
        out = episode_output_path(chapter)
        rows.append({
            "number": chapter["number"],
            "slug": chapter["slug"],
            "issued": issued,
            "dossiers": len(chapter.get("dossiers") or []) if issued
                        else None,
            "delivered": out.exists(),
            "output": str(out),
        })
    return rows


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
    # The ledger is the union of everyone ever credited; each chapter's
    # dossiers reference it. So a dossier ID is expected ONCE in the ledger
    # and at most once across all chapters -- never twice on screen.
    credited = set(ledger)
    dossier_seen = set()
    for chapter in chapters:
        for dossier in chapter.get("dossiers") or []:
            github_id = dossier.get("github_id")
            if github_id in dossier_seen:
                repeats.add(github_id)
            dossier_seen.add(github_id)
            if github_id not in credited:
                errors.append(
                    f"chapter {chapter.get('number')}: dossier "
                    f"{dossier.get('login')} ({github_id}) is not in the "
                    "no-repeat ledger"
                )
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
    out = build_episode(MANIFEST, args.number)
    problems = verify_episode(load_manifest(), args.number)
    print(f"episode {args.number}: {out}")
    return _report_verify(problems)


def _cmd_build_all(args):
    manifest = load_manifest()
    build_all(MANIFEST)
    problems = []
    for chapter in manifest["chapters"]:
        problems.extend(verify_episode(manifest, chapter["number"]))
    return _report_verify(problems)


def _cmd_cut(args):
    """The full-season rough cut, through the one interface that owns it.
    The cut always ships; the exit code is the report's cleanliness."""
    out, problems = build_cut(MANIFEST)
    print(f"full cut: {out}")
    return _report_verify(problems)


def _cmd_verify(args):
    manifest = load_manifest()
    stage = "final" if args.final else "rough"
    if args.number is not None:
        return _report_verify(verify_episode(manifest, args.number,
                                             stage=stage))
    return _report_verify(verify_cut(manifest, stage=stage))


def _cmd_promote(args):
    final = promote_episode(load_manifest(), args.number)
    print(f"promoted episode {args.number}: {final}")
    return 0


def _cmd_promote_cut(args):
    final = promote_cut(load_manifest())
    print(f"promoted cut: {final}")
    return 0


def _recognition_runner(args):
    if args.fixture:
        fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
        return fixture_runner(fixture)
    return _live_runner


def _recognition_since(manifest, args):
    if args.since:
        return args.since
    snapshots = (manifest.get("contributor_ledger") or {}).get("snapshots") \
        or []
    if not snapshots:
        raise RecognitionError(
            "no prior snapshot to start the window from; pass --since for "
            "the first selection")
    return snapshots[-1]["captured_at"]


def _cmd_contributors(args):
    """Compute and print this window's candidate evidence. Reads only --
    nothing here touches the manifest."""
    manifest = load_manifest()
    runner = _recognition_runner(args)
    since = _recognition_since(manifest, args)
    snapshot = recognition_snapshot(manifest, since, _utcnow(),
                                    runner=runner)
    print(json.dumps(snapshot, indent=2))
    return 0


def _cmd_select_next(args):
    snapshot, chapter = select_next_episode(
        MANIFEST, since=args.since, runner=_recognition_runner(args))
    if chapter is None:
        print("select-next: every chapter is already issued; "
              "the window was recorded")
    else:
        print(f"select-next: episode {chapter['number']} "
              f"({chapter['slug']}) now carries "
              f"{len(chapter['dossiers'])} dossier(s); "
              f"selected ids {snapshot['selected_github_ids']}")
    return 0


def _cmd_status(_args):
    manifest = load_manifest()
    ledger = manifest["contributor_ledger"]
    snapshots = ledger.get("snapshots") or []
    print(f"ledger: {len(ledger.get('credited_github_ids') or [])} credited, "
          f"{len(snapshots)} snapshot(s)"
          + (f", last captured {snapshots[-1]['captured_at']}"
             if snapshots else ""))
    for row in recognition_status(manifest):
        issued = (f"issued ({row['dossiers']} dossier(s))"
                  if row["issued"] else "unissued")
        delivered = "delivered" if row["delivered"] else "missing"
        print(f"  e{row['number']:02d} {row['slug']}: {issued}, {delivered}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="validate the season manifest")
    sub.add_parser("cards", help="render the committed cards (CTA + slides)")
    sub.add_parser("fetch-avatars", help="warm the avatar cache for the cast")
    build = sub.add_parser(
        "build", help="build one episode's ROUGH (farm only; the Hive "
                      "workspace never encodes locally)")
    build.add_argument("number", type=int)
    build_all_p = sub.add_parser(
        "build-all", help="build and verify all twelve episode roughs "
                          "(farm only)")
    cut = sub.add_parser(
        "cut", help="build, verify, and join the roughs into the "
                    "full-season ROUGH cut (farm only)")
    verify = sub.add_parser(
        "verify", help="probe the rough files (one episode, or all+cut)")
    verify.add_argument("number", type=int, nargs="?", default=None)
    verify.add_argument("--final", action="store_true",
                        help="probe the promoted finals instead of the "
                             "roughs")
    promote = sub.add_parser(
        "promote", help="copy an APPROVED rough episode+thumbnail to the "
                        "final delivery paths (the only write to finals)")
    promote.add_argument("number", type=int)
    sub.add_parser("promote-cut", help="copy the APPROVED rough season cut "
                                       "to season-01-full.mp4")
    contributors = sub.add_parser(
        "contributors", help="print this window's candidate evidence "
                             "(reads only, no writes)")
    contributors.add_argument("--since", default=None,
                              help="window start (UTC ISO-8601); defaults to "
                                   "the last snapshot's captured_at")
    contributors.add_argument("--fixture", default=None,
                              help="canned gh responses JSON instead of live "
                                   "GitHub calls")
    select = sub.add_parser(
        "select-next", help="issue the next episode's contributor dossiers "
                            "and record the snapshot, atomically")
    select.add_argument("--since", default=None,
                        help="window start (UTC ISO-8601); defaults to the "
                             "last snapshot's captured_at")
    select.add_argument("--fixture", default=None,
                        help="canned gh responses JSON instead of live "
                             "GitHub calls")
    sub.add_parser("status", help="issued/unissued and delivered/missing "
                                  "per episode")
    args = parser.parse_args(argv)
    return {
        "check": _cmd_check,
        "cards": _cmd_cards,
        "fetch-avatars": _cmd_fetch_avatars,
        "build": _cmd_build,
        "build-all": _cmd_build_all,
        "cut": _cmd_cut,
        "verify": _cmd_verify,
        "promote": _cmd_promote,
        "promote-cut": _cmd_promote_cut,
        "contributors": _cmd_contributors,
        "select-next": _cmd_select_next,
        "status": _cmd_status,
    }[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
