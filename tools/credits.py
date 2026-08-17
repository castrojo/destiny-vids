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

1. **The authored Guardian identity.** Seven people have one, written by the
   owner and living in the website's ``characters.json`` -- ``label``,
   ``class``, ``name``, ``title``. Those strings are reproduced verbatim
   beside their face. The 1200x630 splash card they also live on is NOT used:
   *"get rid of those hero splashes they suck."*
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

Owner: *"Use the dinosaur artwork here instead of black, make them go through
the entire calendar order and keep switching"*, and then *"I just want light
colored wallpapers"*. Every card sits on one of Project Bluefin's monthly
**day** wallpapers, advanced card by card in calendar order and wrapping,
cached by ``scripts/fetch_wallpapers.py``. A month whose art is not installed
is skipped -- November ships none in either variant, so the cycle is eleven --
and a machine with none of them falls back to the deck's ink rather than
failing.

The wallpapers changed; **the presentation did not**. This is still a
white-on-dark credit roll, so the grade under the type is the same one, only
lighter: the day art keeps enough of its daylight to be recognisably the light
wallpaper while the type still reads off it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from tools import blueletters
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
    """The installed monthly **day** wallpapers, in calendar order.

    The night frames sit in the same directory under their bare ``NN.png``
    names, because the prologue's bridge reads them. The glob is anchored so
    the two sets can never mix into one cycle.
    """
    if not WALLPAPER_DIR.is_dir():
        return []
    return sorted(p for p in WALLPAPER_DIR.glob("[0-1][0-9]-day.png"))


def _graded(path):
    """One wallpaper, graded so a credit can be read off it.

    Two things now, and each is doing a job:

    * **blue** -- the green channel is pulled back and the blue lifted, which
      is the owner's *"more blue than gold"* in one operation. It cannot turn
      a warm month warm again;
    * **a centre scrim** -- a soft dark band through the middle third, where
      every card puts its name. The corners keep their dinosaurs.

    **The exposure is not touched.** The night set was darkened to 0.46 because
    its skies could still swallow white type; the day set is here because the
    owner asked for the light wallpapers, and darkening one back down is how
    you get a night wallpaper with extra steps. The scrim alone carries the
    type -- measured, not assumed, by
    ``test_the_type_can_be_read_off_every_month``.
    """
    if path in _WALLS:
        return _WALLS[path]
    img = Image.open(path).convert("RGB").resize((W, H), Image.LANCZOS)
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


def cast_identity(slug):
    """The authored Guardian identity for ``slug`` as **fields**, or ``None``.

    Owner: *"get rid of those hero splashes they suck."* The website's
    1200x630 card is a splash composite -- somebody's nameplate over a
    full-bleed Destiny still -- and it is no longer dropped into the frame
    whole.

    What was authored is the COPY, and that is reproduced verbatim: ``label``,
    ``class``, ``name``, ``title``, exactly as written in the website's
    ``characters.json``. Nothing here writes an identity, shortens one, or
    fills a row nobody authored -- a person with no ``title`` gets no title
    row. Cached by ``scripts/build_credits.py`` so the render needs neither the
    network nor the other checkout.
    """
    if not slug:
        return None
    path = CAST_CARD_DIR / "identities.json"
    if not path.exists():
        return None
    try:
        import json
        rows = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    row = rows.get(slug) if isinstance(rows, dict) else None
    return row or None


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


def blue_letters(text=None):
    """Which characters are set in the film's blue.

    **Both B and F, always**, in both cases. The owner, 2026-08-15: *"Ensure
    every b is blue, and every f is blue in all the dialogue except the chat
    bubbles and nameplates."*

    The rule used to be an either/or -- every B, *or* F instead for a string
    with no B in it, so that somebody who already had blue did not get more of
    it. That reasoning was sound for a wall of logins and it is superseded:
    the owner asked for both letters everywhere. Recorded rather than deleted,
    because the wall of names is still the place where the difference shows.

    The definition itself lives in ``tools.blueletters`` now, because three
    other surfaces draw burned copy of their own and one rule may only have one
    home. The **exclusions** -- chat bubbles and nameplates -- are enforced by
    which renderers call it.
    """
    return blueletters.blue_letters(text)


def _blue_bs(draw, xy, text, font, fill, tracking_em=0.0):
    """Draw ``text`` with its blue letters picked out."""
    return blueletters.draw(draw, xy, text, font, fill, ACCENT, tracking_em)


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


# --- the call to action ----------------------------------------------------
#
# Owner, 2026-08-14: *"noticeably larger font, more emphasis on the font -- no
# italics, I want bold and blocky, make the filled in F's and blue sear with
# heat for the big ones"*, and of FIGHT: *"HUGE BOLD FONT. BLUE F"*.
#
# Re-issued 2026-08-15 against MAKE YOUR OWN FATE and BECOME LEGEND, which is
# how we learned the first pass had not actually delivered it. The sizes were
# not the problem. **The fitter was.**
#
# `_cta_font` used to shrink a line until it fitted on ONE row, so a long cry
# could never be big: MAKE YOUR OWN FATE is eighteen characters, and at the
# `large` size that is over three thousand pixels of type being squeezed into
# 1760. It came out around the `medium` size no matter what the card asked for,
# and the ladder below was invisible because two of its three rungs collapsed
# onto the same number. FIGHT, at five characters, was the only line that ever
# rendered at the size it was given -- which is exactly the card the owner
# never complained about.
#
# So the line WRAPS now and keeps its size. A battle cry stacked over three
# rows at full height is the emphasis that was asked for; the same words set
# small on one row is the thing that kept getting shipped instead.
CTA_SCALE = {"medium": 200, "large": 320, "huge": 460, "colossal": 620}
# Below this the sear is not drawn: a seared glyph on a small card is a smudge.
CTA_SEAR_FROM = "large"

# The heat, from the core out. White-hot at the centre of the stroke, through
# the film's blue, into a cold halo that dies in the backdrop -- an F that is
# GLOWING, not an F with a blue outline.
SEAR_MID = (147, 197, 253, 255)      # ACCENT, the film's blue -- the fill
SEAR_HALO = (37, 99, 235, 255)       # a deeper blue, the wide haze
SEAR_FLARE = (196, 226, 255, 255)    # the tight flare right off the stroke


def _sear(img, glyphs, font, blur=None):
    """Burn a set of glyphs into ``img`` as if the metal were white-hot.

    ``glyphs`` is ``[(x, y, ch), ...]`` already positioned by the caller, so
    the sear lands exactly under the letters it belongs to rather than being
    re-measured with different tracking.

    The bloom is **additive**, which is what separates heat from a blue
    outline: light from a glowing thing adds to what is behind it, so the
    backdrop's dinosaurs are washed out around the letter instead of merely
    being covered by it. Three radii stacked -- a wide deep-blue haze, a
    tighter flare, and the filled letter over them. Kept RESTRAINED on the
    owner's note ("tone down the sear"): the letter should look warm, not lit
    from inside a furnace, and the backdrop's dinosaurs should still be
    visible through the haze.
    """
    w, h = img.size
    blur = blur or max(3, font.size * 0.035)

    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    for x, y, ch in glyphs:
        md.text((x, y), ch, font=font, fill=255)

    glow = Image.new("RGB", (w, h), (0, 0, 0))
    for radius, colour, gain in ((blur * 4.0, SEAR_HALO, 0.34),
                                 (blur * 1.4, SEAR_MID, 0.36),
                                 (blur * 0.5, SEAR_FLARE, 0.26)):
        layer = Image.new("RGB", (w, h), colour[:3])
        soft = mask.filter(ImageFilter.GaussianBlur(radius)).point(
            lambda v, g=gain: int(v * g))
        glow = ImageChops.add(glow, Image.composite(
            layer, Image.new("RGB", (w, h), (0, 0, 0)), soft))

    base = img.convert("RGB")
    img.paste(Image.merge("RGBA", (*ImageChops.add(base, glow).split(),
                                   Image.new("L", (w, h), 255))), (0, 0))

    # THE LETTER IS FILLED BLUE. Owner, seeing the first pass: *"the F would
    # look better filled in blue!"* -- so the glyph is solid in the film's own
    # accent and the heat is entirely in the bloom around it. There is no
    # white-hot core; a paler centre made it read as white type with a blue
    # edge, which is the opposite of a blue letter under heat.
    d = ImageDraw.Draw(img)
    for x, y, ch in glyphs:
        d.text((x, y), ch, font=font, fill=SEAR_MID)
    return img


CTA_TRACKING = 0.05
CTA_MARGIN = 160           # the type never comes closer than 80 px to an edge
CTA_HEIGHT_ROOM = 900      # the block never fills the frame edge to edge
CTA_LINE_SPACING = 1.14    # of the font size, centre to centre
CTA_MAX_LINES = 3
CTA_TIE = 0.92             # within this much of the best size, fewer lines win


def _cta_step(font):
    """Baseline-to-baseline distance for stacked cries."""
    return font.size * CTA_LINE_SPACING


def _cta_split(draw, words, font, n):
    """Break ``words`` into ``n`` contiguous lines, as evenly as possible.

    Greedy wrapping produced ``MAKE / YOUR / OWN FATE`` -- three lines, two of
    them one word. A battle cry set that way reads as a list. This minimises
    the WIDEST line instead, which is what makes a stacked cry look like a
    block: ``MAKE YOUR / OWN FATE``.

    The copy here is a handful of words, so every split is enumerated rather
    than solved cleverly.
    """
    if n <= 1:
        return [" ".join(words)]
    if n > len(words):
        return None

    import itertools
    best, best_width = None, None
    for cuts in itertools.combinations(range(1, len(words)), n - 1):
        bounds = (0,) + cuts + (len(words),)
        lines = [" ".join(words[a:b]) for a, b in zip(bounds, bounds[1:])]
        widest = max(_tracked_width(draw, ln, font, CTA_TRACKING) for ln in lines)
        if best_width is None or widest < best_width:
            best, best_width = lines, widest
    return best


def _cta_fit(probe, words, size, n):
    """The largest size at or below ``size`` that sets ``words`` on ``n`` lines.

    ``None`` when ``n`` lines cannot be made to fit at all.
    """
    while size > 60:
        font = _font("black", size)
        lines = _cta_split(probe, words, font, n)
        if lines is None:
            return None
        wide = max(_tracked_width(probe, ln, font, CTA_TRACKING) for ln in lines)
        tall = _cta_step(font) * (n - 1) + font.size
        if wide <= W - CTA_MARGIN and tall <= CTA_HEIGHT_ROOM:
            return font, lines
        size = int(size * 0.98)
    return None


def _cta_layout(text, scale):
    """The blocky face at its full size, and the line breaks that let it stay.

    Adwaita Sans **Black** upright -- no italics, per the instruction -- and
    never a synthesised oblique.

    **Wrapping comes before shrinking**, which is the whole fix. Every line
    count up to ``CTA_MAX_LINES`` is fitted, and the biggest type wins -- so a
    long cry is stacked at full height instead of being squeezed onto one row.
    That is the difference between MAKE YOUR OWN FATE reading as a battle cry
    and reading as a caption.

    **Ties go to fewer lines.** Three lines bought MAKE YOUR OWN FATE twelve
    pixels over two, and spent them on ``MAKE / YOUR / OWN FATE`` -- a cry set
    as a list. Within ``CTA_TIE`` of the best size the shorter stack wins, so
    it sets ``MAKE YOUR / OWN FATE`` instead.

    Returns ``(font, [line, ...])``.
    """
    target = CTA_SCALE.get(scale, CTA_SCALE["large"])
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    words = text.split() or [text]

    fits = []
    for n in range(1, CTA_MAX_LINES + 1):
        got = _cta_fit(probe, words, target, n)
        if got:
            fits.append((n, got))
    if not fits:
        return _font("black", 60), [text]

    best = max(font.size for _, (font, _) in fits)
    for n, (font, lines) in fits:
        if font.size >= best * CTA_TIE:
            return font, lines
    return fits[-1][1]


def render_cta_card(text, scale="large", index=0):
    """One line of the call to action, blocky and seared.

    The F's are FILLED and glowing -- the owner's *"make the filled in F's and
    blue sear with heat for the big ones"*. Every other letter is the deck's
    pale type, so the heat has something to be hot against, except the B's,
    which take the film's blue under the b/f rule. On the smallest tier the
    sear is skipped and the F simply takes the blue: a bloom at 200px is a
    smudge.

    Long copy is **stacked, not shrunk** -- see ``_cta_layout``.
    """
    img = backdrop(index)
    d = ImageDraw.Draw(img)
    font, lines = _cta_layout(text, scale)
    seared = CTA_SCALE.get(scale, 0) >= CTA_SCALE[CTA_SEAR_FROM]

    extra = CTA_TRACKING * font.size
    step = _cta_step(font)
    y = H / 2 - font.size * 0.72 - step * (len(lines) - 1) / 2

    hot, cold = [], []
    lit = blue_letters()
    for line in lines:
        x = _centre(d, line, font, CTA_TRACKING)
        for ch in line:
            (hot if ch in "Ff" else cold).append((x, y, ch))
            x += d.textlength(ch, font=font) + extra
        y += step

    if hot and seared:
        _sear(img, hot, font)
    else:
        for gx, gy, ch in hot:
            d.text((gx, gy), ch, font=font, fill=ACCENT)
    for gx, gy, ch in cold:
        # The b/f rule still applies to the letters that are not on fire, so
        # BECOME LEGEND keeps its blue B.
        d.text((gx, gy), ch, font=font, fill=ACCENT if ch in lit and ch not in "Ff" else TEXT)
    return img


def render_birthday_card(eyebrow, name, body, index=0):
    """The one card in the call to action that is not a battle cry.

    Set in the credit treatment -- the same shape as a role card -- because it
    is a birthday card. Every string is the owner's, reproduced, and nothing is
    added: no age row, no second name.
    """
    img = backdrop(index)
    d = ImageDraw.Draw(img)

    f_eye = _font("regular", 44)
    f_name = _font("black", 128)
    f_body = _font("regular", 38)

    block = 78 + 150 + 96
    y = (H - block) / 2
    _draw_tracked(d, (_centre(d, eyebrow, f_eye, TRACKING), y), eyebrow, f_eye,
                  ACCENT, TRACKING)
    y += 92
    _blue_bs(d, (_centre(d, name, f_name, 0.03), y), name, f_name, TEXT, 0.03)
    y += 178
    d.line([(W / 2 - 120, y - 26), (W / 2 + 120, y - 26)], fill=RULE, width=2)
    _draw_tracked(d, (_centre(d, body, f_body, 0.04), y), body, f_body, DIM, 0.04)
    return img


def render_cast_placard(person, character, card=None, login=None, photo=None,
                        index=0):
    """One member of the cast: their face, their Guardian identity, their role.

    **One layout for everybody.** The website's 1200x630 card used to be
    dropped in whole for the seven people who have one, which put a full-bleed
    Destiny splash behind half the cast and made two different-looking placards
    in one roll. Owner: *"get rid of those hero splashes they suck."*

    The authored copy survives that intact, because the copy is what was
    authored: ``label``, ``class`` and ``title`` are reproduced verbatim from
    ``characters.json`` and a row nobody wrote is simply not drawn. A ``photo``
    -- an owner-drawn crop out of a CNCF summit photograph -- still beats the
    avatar, because it is the thing the owner asked for.
    """
    img = backdrop(index)
    d = ImageDraw.Draw(img)

    # A redaction suppresses the FACE and the identity too. Printing
    # "[ REDACTED ]" over somebody's avatar, or over the Guardian identity that
    # names them, is not a redaction -- it is a caption on a reveal.
    if person == REDACTED:
        card, login, photo = None, None, None

    portrait = summit_portrait(photo, 380)
    identity = cast_identity(card) or {}

    f_label = _font("regular", 26)
    f_class = _font("semibold", 34)
    f_person = _font("bold", 68)
    f_title = _font("regular", 34)
    f_as = _font("regular", 24)
    f_char = _font("regular", 44)

    label = identity.get("label")
    guardian_class = identity.get("class")
    title = identity.get("title")
    # The authored spelling of a person's own name wins over the manifest's.
    name = identity.get("name") or person

    size = 380 if portrait is not None else 300
    block = size + 40 + (44 if label else 0) + (52 if guardian_class else 0) \
        + 94 + (52 if title else 0) + 70
    top = (H - block) / 2

    face = portrait if portrait is not None else avatar(login, size)
    img.alpha_composite(face if face is not None else _empty_circle(size),
                        (int((W - size) / 2), int(top)))
    if face is None and person != REDACTED:
        f_i = _font("bold", 110)
        initial = (person or "?")[0]
        _blue_bs(d, (_centre(d, initial, f_i), top + size / 2 - 78), initial, f_i, DIM)

    y = top + size + 40
    if label:
        _draw_tracked(d, (_centre(d, label, f_label, TRACKING), y), label,
                      f_label, ACCENT, TRACKING)
        y += 44
    if guardian_class:
        _draw_tracked(d, (_centre(d, guardian_class, f_class, 0.02), y),
                      guardian_class, f_class, DIM, 0.02)
        y += 52
    _blue_bs(d, (_centre(d, name, f_person, NAME_TRACKING), y),
             name, f_person, TEXT, NAME_TRACKING)
    y += 94
    if title:
        _draw_tracked(d, (_centre(d, title, f_title, 0.04), y), title, f_title,
                      DIM, 0.04)
        y += 52
    d.line([(W / 2 - 90, y + 6), (W / 2 + 90, y + 6)], fill=RULE, width=2)
    y += 26
    _draw_tracked(d, (_centre(d, "as", f_as, TRACKING), y), "as", f_as, ACCENT, TRACKING)
    y += 46
    _blue_bs(d, (_centre(d, character, f_char, NAME_TRACKING), y),
             character, f_char, TEXT, NAME_TRACKING)
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
# badge lockup above the section name, and a rule the full width of the block
# rather than a 600px dash.
UPSTREAM_COLS, UPSTREAM_ROWS = 6, 3

# The floor a login is allowed to shrink to before it would rather overlap
# than be readable. No login in the four projects reaches it; it exists so the
# fitter terminates, not as a design choice.
CELL_MIN_SIZE = 12
UPSTREAM_PER_WALL = UPSTREAM_COLS * UPSTREAM_ROWS

# THE EYEBROW IS A CALL TO ACTION NOW. Owner, 2026-08-14: *"Change Upstream to
# #UPSTREAMFIRST call to action at the top."*
UPSTREAM_EYEBROW = "#UPSTREAMFIRST"

# AND EVERY TEAM WALL CARRIES ONE ALONG THE BOTTOM. Owner: *"When we're
# shoting the team credits Let's add huge hashtags #linuxforever at the bottom
# as a call to action."*
WALL_HASHTAG = "#linuxforever"

# How much longer an upstream wall holds than a Bluefin one. It carries 18
# faces against 48, so at a flat rate it would flick past nearly three times
# as fast as the tier it outranks.
UPSTREAM_WALL_WEIGHT = 1.25

# THE BADGES. Owner: *"make these badges be AWESOME. For the elite"*, and
# *"let's snag the logos to these projects and make them look GOOD."* Each
# value is a mark cached by scripts/fetch_brand_marks.py from the project's
# OWN published artwork. A section with no mark -- bootc publishes none --
# keeps the type-only heading, which is the degrade rather than a redrawn
# approximation of somebody's logo.
SECTION_MARKS = {
    "Fedora CoreOS": "fedora",
    "GNOME OS": "gnome",
    "KDE Linux": "kde",
}
MARKS_DIR = RENDERS / "marks"


def section_mark(section, height):
    """The project's own logo at ``height`` px, or ``None``.

    Capped by WIDTH as well: Fedora publishes a wide horizontal lockup and
    KDE a square badge, and matching them on height alone made one badge twice
    the width of the other.
    """
    name = SECTION_MARKS.get(section)
    if not name:
        return None
    return _mark(name, height, max_width=120)


def _badge(section, mark):
    """The section's name with its project's symbol beside it.

    RESTRAINED, on the owner's correction of the first pass: *"you overdid the
    logos those are tacky, smaller and symbolic."* So there is no plate, no rim
    and no glow -- a small symbol at cap height, a gap, and the name. The mark
    is the project's icon rather than its horizontal wordmark, because a lockup
    that spells the brand out cannot be small.
    """
    f_head = _font("bold", 68)
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    text_w = _tracked_width(probe, section, f_head, 0.02)
    gap = 22
    mark_w = mark.width if mark is not None else 0
    w = int(mark_w + (gap if mark is not None else 0) + text_w) + 4
    h = 96

    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    x = 0
    if mark is not None:
        out.alpha_composite(mark, (0, int((h - mark.height) / 2)))
        x = mark.width + gap
    _draw_tracked(d, (x, (h - f_head.size) / 2 - 10), section, f_head, TEXT, 0.02)
    return out


def _ghost(size):
    """The outline of a maintainer who does not exist yet.

    Owner: *"put a outline of a ghost maintainer 'The Next KyleGospo' and then
    put a title under it 'Curse of Maintainership'"* -- an easter egg and a
    call for a volunteer. It is drawn, not fetched: there is no such person, so
    there is no face, and it must never be mistaken for a contributor row.
    """
    img = Image.new("RGBA", (size * 4, size * 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size * 4
    ink = (147, 197, 253, 150)
    d.ellipse([3, 3, s - 4, s - 4], outline=ink, width=7)
    # A head and shoulders inside the ring: the silhouette a missing avatar
    # would have had.
    d.ellipse([s * 0.34, s * 0.20, s * 0.66, s * 0.52], outline=ink, width=7)
    d.arc([s * 0.20, s * 0.52, s * 0.80, s * 1.02], start=180, end=360,
          fill=ink, width=7)
    out = img.resize((size, size), Image.LANCZOS)
    return out


BUBBLE_LINES = ("So many. Running out of metal.", "Deploying CNCF Metal3")


def _metal3_green():
    """Metal3's own brand green, sampled from its published mark.

    Not recalled and not eyedropped from a screenshot: the most common opaque
    colour in the logo file this repo cached from the project's docs.
    """
    path = MARKS_DIR / "metal3.png"
    if not path.exists():
        return (0, 210, 160, 255)
    img = Image.open(path).convert("RGBA").resize((64, 64), Image.LANCZOS)
    counts = {}
    for r, g, b, a in img.getdata():
        if a > 200 and not (r > 230 and g > 230 and b > 230):
            counts[(r, g, b)] = counts.get((r, g, b), 0) + 1
    if not counts:
        return (0, 210, 160, 255)
    return (*max(counts, key=counts.get), 255)


def _bubble(text, stylise_three=False, alpha=255):
    """A side bubble: the gag that rides the upstream walls.

    Owner: *"a side bubble for comedic effect: 'So many. Running out of
    metal.' have that fade to 'Deploying CNCF Metal3' with the 3 being
    stylized like the cncf."* The 3 is set in Metal3's own brand green beside
    its cube, which is what makes it read as the project rather than as a
    digit somebody coloured in.
    """
    f = _font("semibold", 29)
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    mark = None
    if stylise_three:
        mark = _mark("metal3", 38)
    text_w = probe.textlength(text, font=f)
    pad = 28
    w = int(text_w + pad * 2 + ((mark.width + 12) if mark is not None else 0))
    h = 88

    img = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 12], radius=52,
                        fill=(12, 20, 38, 205), outline=(147, 197, 253, 150),
                        width=5)
    # The tail, so it reads as somebody speaking rather than as a caption.
    d.polygon([(w * 0.30, h * 2 - 14), (w * 0.46, h * 2 - 14),
               (w * 0.33, h * 2 - 1)], fill=(12, 20, 38, 205))
    img = img.resize((w, h), Image.LANCZOS)

    d = ImageDraw.Draw(img)
    x = pad
    y = (h - 24) / 2 - 18
    if stylise_three:
        head, tail = text[:-1], text[-1]
        d.text((x, y), head, font=f, fill=TEXT)
        x += probe.textlength(head, font=f)
        d.text((x, y), tail, font=_font("black", 34), fill=_metal3_green())
        if mark is not None:
            img.alpha_composite(mark, (int(x + 28), int(y - 5)))
    else:
        d.text((x, y), text, font=f, fill=TEXT)

    if alpha < 255:
        img.putalpha(img.getchannel("A").point(lambda v: int(v * alpha / 255)))
    return img


def _mark(name, height, max_width=None):
    path = MARKS_DIR / f"{name}.png"
    if not path.exists():
        return None
    try:
        mark = Image.open(path).convert("RGBA")
    except OSError:
        return None
    box = mark.getbbox()
    if box:
        mark = mark.crop(box)
    width = max(1, int(mark.width * height / mark.height))
    if max_width and width > max_width:
        height = max(1, int(height * max_width / width))
        width = max_width
    return mark.resize((width, height), Image.LANCZOS)


def render_name_wall(section, names, page=1, pages=1, tier=None, index=0,
                     ghost=None, bubble_mix=None):
    """A screenful of one project's contributors: their faces and their logins.

    Nine across, four down -- six by three for the upstream tier, which is the
    whole of what "larger" means here. A login prints exactly as its owner
    writes it, **whole**: a name too wide for its cell is set smaller, never
    cut short.

    ``ghost`` puts the outlined maintainer in the last cell. ``bubble_mix``
    dissolves the side gag from its first line to its second: 0 is all of the
    first, 1 is all of the second, and a wall in between carries both at half
    strength, which is how a still-based film fades.
    """
    img = backdrop(index)
    d = ImageDraw.Draw(img)

    up = tier == "upstream"
    cols = UPSTREAM_COLS if up else GRID_COLS
    f_head = _font("bold", 68 if up else 46)
    f_name = _font("regular", 30 if up else 21, mono=not up)

    head_y = 54
    if up:
        f_eye = _font("bold", 30)
        _draw_tracked(d, (_centre(d, UPSTREAM_EYEBROW, f_eye, TRACKING), head_y),
                      UPSTREAM_EYEBROW, f_eye, ACCENT, TRACKING)
        head_y += 52
        badge = _badge(section, section_mark(section, 54))
        img.alpha_composite(badge, (int((W - badge.width) / 2), int(head_y)))
        rule_y = head_y + badge.height + 18
    else:
        _blue_bs(d, (_centre(d, section, f_head, 0.02), head_y), section, f_head,
                 TEXT, 0.02)
        rule_y = head_y + 76
    half = 460 if up else 300
    d.line([(W / 2 - half, rule_y), (W / 2 + half, rule_y)],
           fill=(147, 197, 253, 170) if up else RULE, width=3 if up else 2)
    if pages > 1:
        f_pg = _font("regular", 19)
        tag = f"{page} / {pages}"
        _draw_tracked(d, (_centre(d, tag, f_pg, TRACKING), rule_y + 16), tag,
                      f_pg, DIM, TRACKING)

    size, row_h = (150, 216) if up else (116, 196)
    col_w = (W - (260 if up else 200)) / cols
    cells = list(names) + ([ghost] if ghost else [])
    rows = -(-len(cells) // cols) if cells else 0
    # The block is centred in what is LEFT under the heading, and the reserve
    # at the bottom is the HASHTAG's own band -- 150 px of it. The first pass
    # reserved 60 and the call to action landed on top of the last row of
    # faces, which is the sort of thing only a rendered frame tells you.
    top = rule_y + 36 + max(0, (H - rule_y - 36 - 168) - (rows * row_h)) / 2

    for i, cell in enumerate(cells):
        c, r = i % cols, i // cols
        cx = (130 if up else 100) + c * col_w + col_w / 2
        y = top + r * row_h
        if isinstance(cell, dict):
            # THE GHOST. No avatar is fetched and none ever will be: there is
            # nobody to fetch. Its two rows are the owner's copy.
            img.alpha_composite(_ghost(size), (int(cx - size / 2), int(y)))
            f_g = _font("semibold", 26 if up else 20)
            f_t = _font("regular", 21 if up else 17)
            label = cell["name"]
            _draw_tracked(d, (cx - _tracked_width(d, label, f_g, 0.02) / 2,
                              y + size + 14), label, f_g, ACCENT, 0.02)
            title = cell["title"]
            _draw_tracked(d, (cx - _tracked_width(d, title, f_t, 0.06) / 2,
                              y + size + 48), title, f_t, DIM, 0.06)
            continue
        login = cell
        face = avatar(login, size)
        img.alpha_composite(face if face is not None else _empty_circle(size),
                            (int(cx - size / 2), int(y)))
        # A LOGIN IS SET WHOLE. Long names come down in size until they fit
        # their cell -- the ellipsis that used to do this printed
        # "angelcerverarold...", which is nobody's name.
        f_cell = f_name
        while (d.textlength(login, font=f_cell) > col_w - 14
               and f_cell.size > CELL_MIN_SIZE):
            f_cell = _font("regular", f_cell.size - 1, mono=not up)
        _blue_bs(d, (cx - d.textlength(login, font=f_cell) / 2, y + size + 16),
                 login, f_cell, TEXT)

    # THE CALL TO ACTION ALONG THE BOTTOM, on every team wall.
    f_tag = _font("black", 76)
    tag_y = H - 118
    _blue_bs(d, (_centre(d, WALL_HASHTAG, f_tag, 0.02), tag_y), WALL_HASHTAG,
             f_tag, (147, 197, 253, 235), 0.02)

    if bubble_mix is not None:
        # BOTTOM RIGHT, beside the hashtag rather than over the badge. The
        # first pass put it top-right, where it sat straight across the
        # section's own name.
        for line, weight, three in ((BUBBLE_LINES[0], 1.0 - bubble_mix, False),
                                    (BUBBLE_LINES[1], bubble_mix, True)):
            if weight <= 0.01:
                continue
            bub = _bubble(line, stylise_three=three, alpha=int(255 * weight))
            img.alpha_composite(bub, (W - bub.width - 40, H - bub.height - 6))
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
