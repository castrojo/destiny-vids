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

Stdlib plus Pillow only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import avatars  # noqa: E402  (needs REPO_ROOT on sys.path first)

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


def _fit_text(draw, text, weight, max_size, min_size, max_width):
    """The fitted font and wrapped lines for ``text`` within ``max_width``.

    Shrink first: the largest size that keeps the text on ONE line wins.
    Only when even the floor cannot hold one line does the text wrap, at the
    largest size whose wrapped lines all fit. At the floor it hard-wraps
    instead of shrinking further: it never clips."""
    for size in range(int(max_size), int(min_size) - 1, -1):
        font = _font(weight, size)
        if draw.textlength(text, font=font) <= max_width:
            return font, [text]
    for size in range(int(max_size), int(min_size) - 1, -1):
        font = _font(weight, size)
        lines = _wrap(draw, text, font, max_width)
        if all(draw.textlength(line, font=font) <= max_width for line in lines):
            return font, _wrap_hard(draw, text, font, max_width)
    font = _font(weight, min_size)
    return font, _wrap_hard(draw, text, font, max_width)


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
    inside the panel. The block is centred in the space above the hairline;
    the tally row below it is fixed chrome."""
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    px, py, pw, ph = DOSSIER_PANEL
    name_font, name_lines = _fit_text(
        probe, fields["name"], "bold",
        DOSSIER_NAME_SIZE, DOSSIER_NAME_MIN, DOSSIER_TEXT_WIDTH,
    )
    handle_font, handle_lines = _fit_text(
        probe, fields["handle"], "regular",
        DOSSIER_HANDLE_SIZE, DOSSIER_HANDLE_MIN, DOSSIER_TEXT_WIDTH,
    )
    rows = [(line, name_font, TEXT) for line in name_lines]
    rows += [(line, handle_font, CYAN + (255,)) for line in handle_lines]

    gap = 12
    heights = [sum(font.getmetrics()) for _text, font, _fill in rows]
    block_h = sum(heights) + gap
    area_top, area_bottom = py + 44, py + 246  # above the hairline
    y = area_top + max(0, (area_bottom - area_top - block_h) // 2)
    layout = []
    for i, (text, font, fill) in enumerate(rows):
        if i == len(name_lines):
            y += gap
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
    _hairline(img, py + 250, x0=tx0, x1=px + pw - 56, height=2)
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


def plate_specs(manifest):
    """Every fixed-cast seat as a plate.py-ready spec, in manifest order."""
    return [
        _plate_spec(member, seat)
        for member in manifest["fixed_cast"]
        for seat in member["seats"]
    ]


def plan_chapter_plates(manifest, number):
    """The plates seated in one chapter, plus what could not be seated.

    A cast member missing required plate copy is omitted and recorded in
    ``unresolved`` -- an unsupported plate is never rendered, because a plate
    placed without evidence is a claim about a real person.
    """
    plates, unresolved = [], []
    for member in manifest["fixed_cast"]:
        missing = [f for f in REQUIRED_PLATE_FIELDS
                   if not member.get("plate", {}).get(f)]
        seats = [s for s in member["seats"] if s["chapter"] == number]
        if missing:
            if seats:
                unresolved.append({
                    "cast": member["id"],
                    "reason": "plate copy incomplete: missing "
                              + ", ".join(missing),
                })
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="validate the season manifest")
    sub.add_parser("cards", help="render the committed cards (CTA + slides)")
    sub.add_parser("fetch-avatars", help="warm the avatar cache for the cast")
    args = parser.parse_args(argv)
    return {
        "check": _cmd_check,
        "cards": _cmd_cards,
        "fetch-avatars": _cmd_fetch_avatars,
    }[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
