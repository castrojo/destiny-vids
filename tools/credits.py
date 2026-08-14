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
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from tools.plate import _draw_tracked, _font, _tracked_width

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


# --- chrome ----------------------------------------------------------------

_BACKDROP = None


def backdrop():
    """The frame every card is built on.

    A vignette rather than flat ink: the deck's plates sit over footage, and a
    dead-flat field behind 1080p type reads as a slide instead of as film. One
    small radial gradient, blurred and scaled up -- cached, because it is the
    same image on all thirty-odd cards.
    """
    global _BACKDROP
    if _BACKDROP is None:
        small = Image.new("RGB", (64, 36), BG[:3])
        d = ImageDraw.Draw(small)
        for i in range(20, 0, -1):
            v = int(7 + i * 0.85)
            d.ellipse([32 - i * 1.9, 18 - i * 1.15, 32 + i * 1.9, 18 + i * 1.15],
                      fill=(v, v + 4, v + 13))
        _BACKDROP = (small.resize((W, H), Image.BICUBIC)
                     .filter(ImageFilter.GaussianBlur(26)).convert("RGBA"))
    return _BACKDROP.copy()


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


def _blue_bs(draw, xy, text, font, fill, tracking_em=0.0):
    """Draw ``text``, setting every B in the film's blue.

    Both cases: a wall of GitHub logins is mostly lower-case, and colouring
    only the capitals would leave the effect invisible exactly where the names
    are. Glyph by glyph because Pillow has no letter-spacing -- the same reason
    ``plate.py`` hand-places its tracked type.
    """
    x, y = xy
    extra = tracking_em * font.size
    for ch in text:
        draw.text((x, y), ch, font=font, fill=ACCENT if ch in "Bb" else fill)
        x += draw.textlength(ch, font=font) + extra


def _centre(draw, text, font, tracking_em=0.0):
    return (W - _tracked_width(draw, text, font, tracking_em)) / 2


def _eyebrow(d, text, y):
    """A tracked-out label. Its case is the author's, never forced."""
    f = _font("regular", 30)
    _draw_tracked(d, (_centre(d, text, f, TRACKING), y), text, f, ACCENT, TRACKING)
    return y + 62


# --- cards -----------------------------------------------------------------

def render_role_card(role, names):
    """One fixed credit: the role over the name(s)."""
    img = backdrop()
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


def render_cast_placard(person, character, card=None, login=None):
    """One member of the cast.

    With an authored Guardian card, the card IS the placard: it already carries
    their label, class, name, title and bond, all owner-written, and the only
    thing added is the character they played. Redrawing that copy here would be
    a second source of truth for words somebody already authored.
    """
    img = backdrop()
    d = ImageDraw.Draw(img)

    # A redacted name suppresses the FACE and the authored card too. Printing
    # "[ REDACTED ]" over somebody's avatar, or over a Guardian card that has
    # their real name set into the art, is not a redaction -- it is a caption
    # on a reveal.
    if person == REDACTED:
        card, login = None, None

    art = cast_card(card)

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

    size = 300
    face = avatar(login, size)
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


def render_name_wall(section, names, page=1, pages=1):
    """A screenful of one project's contributors: their faces and their logins.

    Nine across, four down. A login prints exactly as its owner writes it, and
    is truncated with an ellipsis rather than allowed to collide with its
    neighbour -- a name running into the next one is worse than a shortened one.
    """
    img = backdrop()
    d = ImageDraw.Draw(img)

    f_head = _font("bold", 46)
    f_name = _font("regular", 21)

    _blue_bs(d, (_centre(d, section, f_head, 0.02), 66), section, f_head, TEXT, 0.02)
    d.line([(W / 2 - 300, 142), (W / 2 + 300, 142)], fill=RULE, width=2)
    if pages > 1:
        f_pg = _font("regular", 19)
        tag = f"{page} / {pages}"
        _draw_tracked(d, (_centre(d, tag, f_pg, TRACKING), 158), tag, f_pg, DIM, TRACKING)

    size, row_h = 116, 196
    col_w = (W - 200) / GRID_COLS
    rows = -(-len(names) // GRID_COLS) if names else 0
    top = 214 + max(0, (H - 214 - 40) - rows * row_h) / 2

    for i, login in enumerate(names):
        c, r = i % GRID_COLS, i // GRID_COLS
        cx = 100 + c * col_w + col_w / 2
        y = top + r * row_h
        face = avatar(login, size)
        img.alpha_composite(face if face is not None else _empty_circle(size),
                            (int(cx - size / 2), int(y)))
        label = login
        while d.textlength(label, font=f_name) > col_w - 14 and len(label) > 4:
            label = label[:-1]
        if label != login:
            label = label[:-1] + "\u2026"
        _blue_bs(d, (cx - d.textlength(label, font=f_name) / 2, y + size + 14),
                 label, f_name, TEXT)
    return img


WORDMARK = RENDERS / "marks" / "bluefin-wordmark.png"


def render_wordmark(text="Bluefin", sub=None):
    """The last frame of the film: the REAL Project Bluefin wordmark.

    Not the word typeset in the deck's mono. A brand mark set in somebody
    else's typeface is an invented mark, which is the same rule that stops
    ``plate.py`` redrawing a logo it can fetch. The published lockup is cached
    by ``scripts/fetch_wordmark.py``; its own blue fin is untouched and only the
    black type is reversed for this background.

    Falls back to type if the mark has not been cached -- degrade, never block --
    and says so on stderr rather than silently shipping the wrong thing.
    """
    img = backdrop()
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
