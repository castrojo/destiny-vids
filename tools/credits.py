#!/usr/bin/env python3
"""Act VIII -- the credits sequence, generated from committed data.

The owner's design is issue #51. Everything on screen here is either authored
copy from ``stories/08-credits.json`` or a fact pulled from an API and frozen
into that manifest -- **nothing is invented at render time**, which is the
whole point: a credit names a real person, and rule 3 of the contract says a
wrong one is not recoverable by a revert.

Three card shapes, and that is all:

* **role card** -- "Produced by" over a name. The four fixed credits.
* **cast placard** -- a person and the character they played, in running order.
* **name wall** -- a project's contributors, a screenful at a time. 454 names
  across four sections cannot be placards; a wall is what a large crew gets,
  and it is what the owner asked for ("$ list of all the contributors").

Then the wordmark, which is the last frame of the film.

**Every B is set in the film's own blue.** The owner asked for "all B's filled
in with bluefin blue"; the blue is ``ACCENT`` below, which is ``#93c5fd`` --
the same chrome every plate in the show already uses. Reproducing the film's
accent rather than sourcing a new brand blue is deliberate: act VIII has to
look like acts I-VII, and a second blue would read as a mistake.

Stills, not a scroll. Each card is a PNG held for its own duration and joined
by the concat demuxer, exactly like the act slides -- so a rebuild is
deterministic, diffable, and costs no per-frame render.
"""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw

from tools.plate import _draw_tracked, _font, _tracked_width

W, H = 1920, 1080

BG = (8, 12, 20, 255)              # the deck's ink, fully opaque -- this is the frame
TEXT = (245, 245, 245, 255)        # .wolves-guardian-plate-name
ACCENT = (147, 197, 253, 255)      # #93c5fd -- the film's blue, and the B's
DIM = (160, 174, 192, 255)         # #a0aec0, the name gradient's bottom stop
RULE = (147, 197, 253, 90)

TRACKING = 0.18                    # the deck's eyebrow tracking
NAME_TRACKING = 0.04


def _blue_bs(draw, xy, text, font, fill, tracking_em):
    """Draw ``text``, setting every B in the film's blue.

    The owner's instruction is "all B's filled in with bluefin blue". Both
    cases: a wall of GitHub logins is mostly lower-case, and colouring only the
    capitals would leave the effect invisible exactly where the names are.

    Placed glyph by glyph because Pillow has no letter-spacing, which is the
    same reason ``plate.py`` hand-places its tracked type.
    """
    x, y = xy
    extra = tracking_em * font.size
    for ch in text:
        draw.text((x, y), ch, font=font, fill=ACCENT if ch in "Bb" else fill)
        x += draw.textlength(ch, font=font) + extra


def _centre(draw, text, font, tracking_em):
    return (W - _tracked_width(draw, text, font, tracking_em)) / 2


def render_role_card(role, names):
    """One fixed credit: the role in blue small caps, the name(s) under it."""
    img = Image.new("RGBA", (W, H), BG)
    d = ImageDraw.Draw(img)

    f_role = _font("regular", 34)
    f_name = _font("bold", 72)

    label = role.upper()
    y = H / 2 - 110
    _draw_tracked(d, (_centre(d, label, f_role, TRACKING), y),
                  label, f_role, ACCENT, TRACKING)

    y += 92
    for name in names:
        _blue_bs(d, (_centre(d, name, f_name, NAME_TRACKING), y),
                 name, f_name, TEXT, NAME_TRACKING)
        y += 96
    return img


def render_cast_placard(person, character):
    """One member of the cast: who they are, and who they played.

    Both strings come from ``vocab/casting.yaml`` via the manifest. A cast
    placard is a claim about a real person, so it is reproduced, never
    composed.
    """
    img = Image.new("RGBA", (W, H), BG)
    d = ImageDraw.Draw(img)

    f_person = _font("bold", 76)
    f_as = _font("regular", 28)
    f_char = _font("regular", 44)

    y = H / 2 - 120
    _blue_bs(d, (_centre(d, person, f_person, NAME_TRACKING), y),
             person, f_person, TEXT, NAME_TRACKING)

    y += 108
    d.line([(W / 2 - 90, y), (W / 2 + 90, y)], fill=RULE, width=2)

    y += 30
    _draw_tracked(d, (_centre(d, "AS", f_as, TRACKING), y),
                  "AS", f_as, ACCENT, TRACKING)

    y += 56
    _blue_bs(d, (_centre(d, character, f_char, NAME_TRACKING), y),
             character, f_char, DIM, NAME_TRACKING)
    return img


def wall_layout(count):
    """Columns and rows for ``count`` names on one screen.

    Four columns is the widest that keeps a long GitHub login from colliding
    with its neighbour at this size; the row count follows from it.
    """
    cols = 4
    rows = -(-count // cols)
    return cols, rows


def render_name_wall(section, names, page=1, pages=1):
    """A screenful of a project's contributors, four columns.

    ``page``/``pages`` are shown only when a section needs more than one
    screen, so a small section is not labelled "1 of 1".
    """
    img = Image.new("RGBA", (W, H), BG)
    d = ImageDraw.Draw(img)

    f_head = _font("bold", 40)
    f_name = _font("regular", 30)

    head = section.upper()
    _draw_tracked(d, (_centre(d, head, f_head, TRACKING), 96),
                  head, f_head, ACCENT, TRACKING)
    d.line([(W / 2 - 260, 168), (W / 2 + 260, 168)], fill=RULE, width=2)

    if pages > 1:
        f_pg = _font("regular", 20)
        tag = f"{page} / {pages}"
        _draw_tracked(d, (_centre(d, tag, f_pg, TRACKING), 186),
                      tag, f_pg, DIM, TRACKING)

    cols, rows = wall_layout(len(names))
    col_w = (W - 240) / cols

    # The block is centred in the space under the rule rather than pinned to a
    # fixed line height: a full 48-name wall and a 9-name tail wall then sit in
    # the same place instead of the short one hugging the top of the frame.
    top, bottom = 260, H - 90
    line_h = min(58, (bottom - top) / max(1, rows))
    y0 = top + ((bottom - top) - rows * line_h) / 2
    for i, name in enumerate(names):
        c, r = i // rows, i % rows
        _blue_bs(d, (120 + c * col_w, y0 + r * line_h), name, f_name, TEXT, 0.0)
    return img


def render_wordmark(text="Bluefin"):
    """The last frame of the film: the wordmark, large.

    Its B is blue like every other B in the sequence -- the instruction applied
    to the one word it was most obviously about.
    """
    img = Image.new("RGBA", (W, H), BG)
    d = ImageDraw.Draw(img)
    f = _font("bold", 190)
    y = H / 2 - 130
    _blue_bs(d, (_centre(d, text, f, 0.06), y), text, f, TEXT, 0.06)
    return img


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-") or "card"


def paginate(names, per_page):
    """Split a section into screens of at most ``per_page`` names.

    The last screen is not padded: a wall with eight names on it is honest
    about how many contributors that section has.
    """
    return [names[i:i + per_page] for i in range(0, len(names), per_page)] or [[]]
