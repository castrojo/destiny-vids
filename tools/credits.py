#!/usr/bin/env python3
"""Act VIII -- the credits sequence, generated from committed data.

The owner's design is issue #51, revised in session on 2026-08-13: *"stylize
the credits to look awesome, use github PFPs for everyone, this will be a
showcase of the real people - fill in every b with bluefin blue"*.

Everything on screen is either authored copy from ``stories/08-credits.json``
or a fact pulled from an API and frozen into that manifest. **Nothing is
invented at render time**, because a credit names a real person and rule 3 says
a wrong one is not recoverable by a revert.

## Capitalization is copy

Names print **exactly as written**: ``Bazzite``, not ``BAZZITE``;
``mrbobbytables``, not ``Mrbobbytables``. A GitHub login's case is chosen by
its owner, and an uppercased project name is a different word from the one the
project uses. Only the small eyebrow labels are tracked out, and they keep
their authored case too.

## Faces, in strict order of what can be proved

1. **The authored Guardian card.** Seven people have one, written by the owner
   and living in the website's ``characters.json`` -- a full 1200x630 card with
   their nameplate, class, title and Guardian bond. Where one exists it is
   reproduced whole, because it *is* the authored identity; nothing here
   redraws it.
2. **A verified GitHub avatar.** ``vocab/casting.yaml`` carries an optional
   ``github:`` field for exactly this and says why: a login "is verifiable; a
   real name may not be", recording the ``nimbatus``/``nimbinatus`` trap where
   the account matching the *character* name belongs to a stranger.
3. **The crest.** No face at all rather than a guessed one.

Contributors are unambiguous -- the API returned the login and the avatar
together -- so the grid is every one of them.

## The blue

Every B is set in ``ACCENT``, the film's own ``#93c5fd``. Using the show's
existing accent rather than sourcing a new brand blue is what keeps act VIII
looking like acts I-VII instead of announcing itself.

Owner, this round: *"these should be more blue than gold"*. So the grade under
the type is a **blue** scrim, not a neutral one, and the wallpapers it sits on
are the dark-mode set, which are already night blues. Nothing gold survives the
grade.

## The type is Adwaita

Owner: *"Change all the fonts to adwaita, even the bluefin one."* ``plate.py``
deliberately resolves DejaVu Sans Mono, because it is matching a browser that
baked the reference plates and Adwaita Mono would silently restyle every plate
in the show. **Act VIII is not matching that deck** -- it is the desktop's own
credit roll -- so it resolves Adwaita here and nowhere else, leaving acts I-VII
exactly as they were. Adwaita Sans is a variable font, so a weight is an axis
setting rather than a second file.

## The frame is the desktop

Owner: *"Use the dinosaur artwork here instead of black, use the dark mode
wallpapers, make them go through the entire calendar order and keep switching."*
Every card sits on one of Project Bluefin's monthly **night** wallpapers,
advanced card by card in calendar order and wrapping, cached by
``scripts/fetch_wallpapers.py``. A month whose art is not installed is skipped,
and a machine with none of them falls back to the deck's ink rather than
failing.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from tools.plate import _draw_tracked, _tracked_width

W, H = 1920, 1080

BG = (8, 12, 20, 255)              # the deck's ink, opaque -- this IS the frame
TEXT = (245, 245, 245, 255)
ACCENT = (147, 197, 253, 255)      # #93c5fd -- the film's blue, and the B's
DIM = (160, 174, 192, 255)         # #a0aec0, the name gradient's bottom stop
RULE = (147, 197, 253, 90)

TRACKING = 0.18
NAME_TRACKING = 0.04

RENDERS = Path(__file__).resolve().parents[1] / "renders"
AVATAR_DIR = RENDERS / "avatars"
CAST_CARD_DIR = RENDERS / "cast-cards"
WALLPAPER_DIR = RENDERS / "wallpapers"
SUMMIT_DIR = Path(__file__).resolve().parents[1] / "media" / "summit"


# --- type ------------------------------------------------------------------

# Act VIII's own stack, and the reason it is not `plate.FONT_CANDIDATES`: that
# list exists to reproduce a browser's fallback, and Adwaita Mono is explicitly
# NOT first there because preferring it restyled every plate in the show. Here
# Adwaita is the instruction, so it is first, and DejaVu is only the machine
# that has no Adwaita installed.
ADWAITA_SANS = "/usr/share/fonts/Adwaita/AdwaitaSans-Regular.ttf"
ADWAITA_MONO = {
    "regular": "/usr/share/fonts/Adwaita/AdwaitaMono-Regular.ttf",
    "bold": "/usr/share/fonts/Adwaita/AdwaitaMono-Bold.ttf",
}
# Adwaita Sans ships as ONE variable file; a weight is an axis, not a face.
SANS_VARIATION = {"regular": "Regular", "bold": "Bold", "black": "Black",
                  "medium": "Medium", "semibold": "SemiBold"}


def _font(weight, size, mono=False):
    """Adwaita at ``size``, falling back to the deck's stack if it is absent."""
    size = int(round(size))
    if mono:
        path = ADWAITA_MONO.get(weight, ADWAITA_MONO["regular"])
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    elif Path(ADWAITA_SANS).exists():
        font = ImageFont.truetype(ADWAITA_SANS, size)
        try:
            font.set_variation_by_name(SANS_VARIATION.get(weight, "Regular"))
        except (OSError, AttributeError):
            pass
        return font
    from tools import plate
    return plate._font("bold" if weight in ("bold", "black") else "regular", size)


# --- chrome ----------------------------------------------------------------

_INK = None
_WALLS = {}


def _ink():
    """The fallback frame: the deck's vignette, for a host with no wallpapers."""
    global _INK
    if _INK is None:
        small = Image.new("RGB", (64, 36), BG[:3])
        d = ImageDraw.Draw(small)
        for i in range(20, 0, -1):
            v = int(7 + i * 0.85)
            d.ellipse([32 - i * 1.9, 18 - i * 1.15, 32 + i * 1.9, 18 + i * 1.15],
                      fill=(v, v + 4, v + 13))
        _INK = (small.resize((W, H), Image.BICUBIC)
                .filter(ImageFilter.GaussianBlur(26)).convert("RGBA"))
    return _INK


def wallpapers():
    """The installed monthly night wallpapers, in calendar order."""
    if not WALLPAPER_DIR.is_dir():
        return []
    return sorted(p for p in WALLPAPER_DIR.glob("[0-1][0-9].png"))


def _graded(path):
    """One wallpaper, graded so a credit can be read off it.

    Three things, in order, and each is doing a job:

    * **darken** -- the art is night-lit but its skies are bright enough to
      swallow white type;
    * **blue** -- the green channel is pulled back and the blue lifted, which
      is the owner's *"more blue than gold"* in one operation. It cannot turn
      a warm month warm again;
    * **a centre scrim** -- a soft dark band through the middle third, where
      every card puts its name. The corners keep their dinosaurs.
    """
    if path in _WALLS:
        return _WALLS[path]
    img = Image.open(path).convert("RGB").resize((W, H), Image.LANCZOS)
    img = ImageEnhance.Brightness(img).enhance(0.46)
    r, g, b = img.split()
    img = Image.merge("RGB", (r.point(lambda v: int(v * 0.80)),
                              g.point(lambda v: int(v * 0.86)),
                              b.point(lambda v: min(255, int(v * 1.12)))))
    scrim = Image.new("L", (1, H), 0)
    for y in range(H):
        t = abs(y - H / 2) / (H / 2)
        scrim.putpixel((0, y), int(150 * (1 - t) ** 1.5))
    veil = Image.new("RGBA", (W, H), (4, 8, 16, 255))
    veil.putalpha(scrim.resize((W, H), Image.BICUBIC))
    out = img.convert("RGBA")
    out.alpha_composite(veil)
    _WALLS[path] = out
    return out


def backdrop(index=0):
    """The frame a card is built on: its month's wallpaper, or the deck's ink.

    ``index`` is the card's position in the sequence, so consecutive cards get
    consecutive months and the roll cycles the calendar as it plays -- *"make
    them go through the entire calendar order and keep switching"*.
    """
    walls = wallpapers()
    if not walls:
        return _ink().copy()
    return _graded(walls[index % len(walls)]).copy()


def _circle(img, size, ring_alpha=120):
    """An avatar cropped to a circle with a thin accent ring.

    The ring is what makes a grid of thirty-six faces read as a designed wall
    rather than a contact sheet. Masked at 4x and downsampled so the edge is
    smooth without Pillow's antialiased-ellipse gaps.
    """
    img = img.convert("RGBA").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size * 4 - 1, size * 4 - 1], fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask.resize((size, size), Image.LANCZOS))
    ring = Image.new("RGBA", (size * 4, size * 4), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse([3, 3, size * 4 - 4, size * 4 - 4],
                                 outline=(147, 197, 253, ring_alpha), width=7)
    out.alpha_composite(ring.resize((size, size), Image.LANCZOS))
    return out


def _empty_circle(size):
    """The stand-in for a face nobody has verified. Not a broken image: a ring."""
    ring = Image.new("RGBA", (size * 4, size * 4), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse([3, 3, size * 4 - 4, size * 4 - 4],
                                 outline=(147, 197, 253, 70), width=7)
    return ring.resize((size, size), Image.LANCZOS)


def avatar(login, size):
    """The cached face for ``login``, or ``None``.

    Never fetched at render time: a credit roll that needs the network to build
    breaks when the network is down, and the manifest exists so the render is
    reproducible offline.
    """
    if not login:
        return None
    path = AVATAR_DIR / f"{login}.png"
    if not path.exists() or path.stat().st_size < 512:
        return None
    try:
        return _circle(Image.open(path), size)
    except OSError:
        return None


def cast_card(slug):
    """An authored Guardian card, reproduced whole, or ``None``."""
    if not slug:
        return None
    path = CAST_CARD_DIR / f"{slug}.png"
    if not path.exists():
        return None
    try:
        return Image.open(path).convert("RGBA")
    except OSError:
        return None


def summit_portrait(photo, size):
    """A principal's portrait, cropped out of a CNCF summit photograph.

    Owner: *"For the principal actors - remove the pfp icon and instead use a
    good shot of them from the CNCF contributor summit flickr feed."*

    ``photo`` is ``{"file": ..., "box": [x, y, w, h]}`` -- the photograph, and
    the rectangle **the owner drew** around that person. The box is not
    computed and never will be: picking a face out of a group photograph and
    saying whose it is is a claim about a real person made from a visual
    judgement, which is the one thing AGENTS.md says an agent may not do. With
    no box the placard falls back to the avatar, which is verified.

    The crop is square and rendered as a rounded portrait rather than a circle,
    so a photograph of a person does not read as a second, larger PFP.
    """
    if not photo or not photo.get("box"):
        return None
    path = Path(photo["file"])
    if not path.is_absolute():
        path = SUMMIT_DIR.parents[1] / path
    if not path.exists():
        return None
    try:
        src = Image.open(path).convert("RGBA")
    except OSError:
        return None
    x, y, w, h = (int(v) for v in photo["box"])
    side = max(w, h)
    cx, cy = x + w / 2, y + h / 2
    box = (int(cx - side / 2), int(cy - side / 2),
           int(cx + side / 2), int(cy + side / 2))
    face = src.crop(box).resize((size, size), Image.LANCZOS)

    radius = int(size * 0.14)
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size * 4 - 1, size * 4 - 1], radius=radius * 4, fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(face, (0, 0), mask.resize((size, size), Image.LANCZOS))
    ring = Image.new("RGBA", (size * 4, size * 4), (0, 0, 0, 0))
    ImageDraw.Draw(ring).rounded_rectangle(
        [4, 4, size * 4 - 5, size * 4 - 5], radius=radius * 4,
        outline=(147, 197, 253, 150), width=8)
    out.alpha_composite(ring.resize((size, size), Image.LANCZOS))
    return out


def blue_letters(text):
    """Which characters of ``text`` are set in the film's blue.

    The owner's rule, in two parts:

    * every **B** is blue -- the original instruction;
    * **F** is blue instead, but *only for a name with no B in it*, so
      somebody who already has blue does not get more of it.

    The unit is the whole credit as it appears on screen, which is why this
    takes a string rather than a character: "Jeefy" has no B, so its f lights
    up; "Bob Killen" has two B's already and its name stays as it is.

    Both cases throughout. A wall of GitHub logins is mostly lower-case, and
    matching only capitals would leave the effect invisible exactly where the
    names are.
    """
    return "Bb" if ("B" in text or "b" in text) else "Ff"


def _blue_bs(draw, xy, text, font, fill, tracking_em=0.0):
    """Draw ``text`` with its blue letters picked out.

    Glyph by glyph because Pillow has no letter-spacing -- the same reason
    ``plate.py`` hand-places its tracked type.
    """
    lit = blue_letters(text)
    x, y = xy
    extra = tracking_em * font.size
    for ch in text:
        draw.text((x, y), ch, font=font, fill=ACCENT if ch in lit else fill)
        x += draw.textlength(ch, font=font) + extra


def _centre(draw, text, font, tracking_em=0.0):
    return (W - _tracked_width(draw, text, font, tracking_em)) / 2


def _eyebrow(d, text, y):
    """A tracked-out label. Its case is the author's, never forced."""
    f = _font("regular", 30)
    _draw_tracked(d, (_centre(d, text, f, TRACKING), y), text, f, ACCENT, TRACKING)
    return y + 62


# --- cards -----------------------------------------------------------------

def render_role_card(role, names, index=0):
    """One fixed credit: the role over the name(s)."""
    img = backdrop(index)
    d = ImageDraw.Draw(img)
    f_name = _font("bold", 78)

    block = 62 + 104 * len(names)
    y = (H - block) / 2
    y = _eyebrow(d, role, y)
    d.line([(W / 2 - 74, y - 20), (W / 2 + 74, y - 20)], fill=RULE, width=2)
    for name in names:
        _blue_bs(d, (_centre(d, name, f_name, NAME_TRACKING), y),
                 name, f_name, TEXT, NAME_TRACKING)
        y += 104
    return img


REDACTED = "[ REDACTED ]"


def render_cast_placard(person, character, card=None, login=None, photo=None,
                        index=0):
    """One member of the cast.

    With an authored Guardian card, the card IS the placard: it already carries
    their label, class, name, title and bond, all owner-written, and the only
    thing added is the character they played. Redrawing that copy here would be
    a second source of truth for words somebody already authored.

    A ``photo`` -- an owner-drawn crop out of a CNCF summit photograph -- beats
    both the card and the avatar, because it is the thing the owner asked for.
    """
    img = backdrop(index)
    d = ImageDraw.Draw(img)

    # A redacted name suppresses the FACE and the authored card too. Printing
    # "[ REDACTED ]" over somebody's avatar, or over a Guardian card that has
    # their real name set into the art, is not a redaction -- it is a caption
    # on a reveal.
    if person == REDACTED:
        card, login, photo = None, None, None

    portrait = summit_portrait(photo, 420)
    art = None if portrait is not None else cast_card(card)

    if art is not None:
        target_w = 1500
        scaled = art.resize((target_w, int(art.height * target_w / art.width)),
                            Image.LANCZOS)
        top = (H - scaled.height) / 2 - 70
        img.alpha_composite(scaled, (int((W - target_w) / 2), int(top)))
        y = top + scaled.height + 40
        f_as = _font("regular", 24)
        _draw_tracked(d, (_centre(d, "as", f_as, TRACKING), y), "as", f_as, ACCENT, TRACKING)
        f_char = _font("bold", 52)
        _blue_bs(d, (_centre(d, character, f_char, NAME_TRACKING), y + 44),
                 character, f_char, TEXT, NAME_TRACKING)
        return img

    size = 420 if portrait is not None else 300
    face = portrait if portrait is not None else avatar(login, size)
    top = (H - (size + 250)) / 2
    img.alpha_composite(face if face is not None else _empty_circle(size),
                        (int((W - size) / 2), int(top)))
    if face is None and person != REDACTED:
        f_i = _font("bold", 110)
        initial = (person or "?")[0]
        _blue_bs(d, (_centre(d, initial, f_i), top + size / 2 - 78), initial, f_i, DIM)

    y = top + size + 54
    f_person = _font("bold", 68)
    _blue_bs(d, (_centre(d, person, f_person, NAME_TRACKING), y),
             person, f_person, TEXT, NAME_TRACKING)
    y += 94
    f_as = _font("regular", 24)
    _draw_tracked(d, (_centre(d, "as", f_as, TRACKING), y), "as", f_as, ACCENT, TRACKING)
    y += 46
    f_char = _font("regular", 44)
    _blue_bs(d, (_centre(d, character, f_char, NAME_TRACKING), y),
             character, f_char, DIM, NAME_TRACKING)
    return img


GRID_COLS, GRID_ROWS = 9, 4
NAMES_PER_WALL = GRID_COLS * GRID_ROWS

# THE UPSTREAM TIER.
#
# Owner: *"Add Fedora CoreOS and bootc upstream groups to the credits and have
# them top tier in the credits before bluefin - make theirs larger and more
# distinguished."*
#
# "Larger" is not a font size on the same grid -- a bigger name over the same
# 116px face reads as a typo. It is a different grid: six across, three down,
# so eighteen people get the room forty-eight had. "More distinguished" is the
# eyebrow above the section name saying what they are, and a rule the full
# width of the block rather than a 600px dash.
UPSTREAM_COLS, UPSTREAM_ROWS = 6, 3
UPSTREAM_PER_WALL = UPSTREAM_COLS * UPSTREAM_ROWS
UPSTREAM_EYEBROW = "UPSTREAM"
# How much longer an upstream wall holds than a Bluefin one. It carries 18
# faces against 48, so at a flat rate it would flick past nearly three times
# as fast as the tier it outranks.
UPSTREAM_WALL_WEIGHT = 1.25


def render_name_wall(section, names, page=1, pages=1, tier=None, index=0):
    """A screenful of one project's contributors: their faces and their logins.

    Nine across, four down -- six by three for the upstream tier, which is the
    whole of what "larger" means here. A login prints exactly as its owner
    writes it, and is truncated with an ellipsis rather than allowed to collide
    with its neighbour: a name running into the next one is worse than a
    shortened one.
    """
    img = backdrop(index)
    d = ImageDraw.Draw(img)

    up = tier == "upstream"
    cols = UPSTREAM_COLS if up else GRID_COLS
    f_head = _font("bold", 68 if up else 46)
    f_name = _font("regular", 30 if up else 21, mono=not up)

    head_y = 54
    if up:
        f_eye = _font("regular", 26)
        _draw_tracked(d, (_centre(d, UPSTREAM_EYEBROW, f_eye, TRACKING), head_y),
                      UPSTREAM_EYEBROW, f_eye, ACCENT, TRACKING)
        head_y += 46
    _blue_bs(d, (_centre(d, section, f_head, 0.02), head_y), section, f_head,
             TEXT, 0.02)
    rule_y = head_y + (96 if up else 76)
    half = 460 if up else 300
    d.line([(W / 2 - half, rule_y), (W / 2 + half, rule_y)],
           fill=(147, 197, 253, 170) if up else RULE, width=3 if up else 2)
    if pages > 1:
        f_pg = _font("regular", 19)
        tag = f"{page} / {pages}"
        _draw_tracked(d, (_centre(d, tag, f_pg, TRACKING), rule_y + 16), tag,
                      f_pg, DIM, TRACKING)

    size, row_h = (180, 262) if up else (116, 196)
    col_w = (W - (260 if up else 200)) / cols
    rows = -(-len(names) // cols) if names else 0
    # The block is centred in what is LEFT under the heading, and the reserve
    # at the bottom is the label's own line -- an upstream login sets at 30px
    # and a bottom row laid out on face height alone loses its descenders.
    top = rule_y + 46 + max(0, (H - rule_y - 46 - 60) - (rows * row_h)) / 2

    for i, login in enumerate(names):
        c, r = i % cols, i // cols
        cx = (130 if up else 100) + c * col_w + col_w / 2
        y = top + r * row_h
        face = avatar(login, size)
        img.alpha_composite(face if face is not None else _empty_circle(size),
                            (int(cx - size / 2), int(y)))
        label = login
        while d.textlength(label, font=f_name) > col_w - 14 and len(label) > 4:
            label = label[:-1]
        if label != login:
            label = label[:-1] + "\u2026"
        _blue_bs(d, (cx - d.textlength(label, font=f_name) / 2, y + size + 16),
                 label, f_name, TEXT)
    return img


WORDMARK = RENDERS / "marks" / "bluefin-wordmark.png"


def render_wordmark(text="Bluefin", sub=None, index=0):
    """The last frame of the film: the REAL Project Bluefin wordmark.

    Not the word typeset in the deck's mono. A brand mark set in somebody
    else's typeface is an invented mark, which is the same rule that stops
    ``plate.py`` redrawing a logo it can fetch. The published lockup is cached
    by ``scripts/fetch_wordmark.py``; its own blue fin is untouched and only the
    black type is reversed for this background.

    Falls back to type if the mark has not been cached -- degrade, never block --
    and says so on stderr rather than silently shipping the wrong thing.
    """
    img = backdrop(index)
    d = ImageDraw.Draw(img)

    if WORDMARK.exists():
        mark = Image.open(WORDMARK).convert("RGBA")
        width = 1180
        mark = mark.resize((width, int(mark.height * width / mark.width)),
                           Image.LANCZOS)
        top = (H - mark.height) / 2 - 40
        img.alpha_composite(mark, (int((W - width) / 2), int(top)))
        y = top + mark.height + 70
    else:
        print(f"note: {WORDMARK} is missing; setting the wordmark in type. "
              f"Run scripts/fetch_wordmark.py", file=sys.stderr)
        f = _font("bold", 200)
        y = H / 2 - 150
        _blue_bs(d, (_centre(d, text, f, 0.06), y), text, f, TEXT, 0.06)
        y += 262

    if sub:
        f_sub = _font("regular", 26)
        _draw_tracked(d, (_centre(d, sub, f_sub, TRACKING), y), sub, f_sub, DIM, TRACKING)
    return img


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-") or "card"


def paginate(names, per_page):
    """Split a section into screens. The last screen is not padded: a wall with
    eight names on it is honest about how many that section has."""
    return [names[i:i + per_page] for i in range(0, len(names), per_page)] or [[]]
