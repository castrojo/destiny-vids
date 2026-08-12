#!/usr/bin/env python3
"""Guardian nameplates -> RGBA stills -> burned into a rendered cut.

The index names the cast; this is what puts the name on screen. A plate is the
Project Bluefin Guardian nameplate from the website's Wolves intro overlay,
rendered as a transparent PNG and composited over a cut for a timed window.

Two subcommands:

    python3 tools/plate.py render --manifest plates.json --out-dir renders/plates
    python3 tools/plate.py burn  --video renders/cut.mp4 --manifest plates.json \
                                 --out renders/cut-plated.mp4

A manifest entry follows the authoring contract in the
``authoring-interview-chat-plates`` skill -- timed, authored metadata, never
improvised text:

    {"id": "osiris", "at": 12.4, "dur": 6.0, "position": "left",
     "label": "TRUSTEE // GUARDIAN", "class": "Voidwalker Warlock",
     "name": "Bob Killen", "title": "Reconciler of the Plane", "trustee": true}

The four text fields plus ``trustee`` are exactly the vocabulary of the
reference deck (``~/Videos/nameplates.json``); nothing is invented on top of it.

``kind: "ghost"`` drops the class line (a Ghost is not a Guardian, so a subclass
would be nonsense on it) and shrinks the plate. ``kind: "title"`` is the deck's
other card -- ``title`` / ``subtitle`` / ``body`` -- used here to credit the
month's ensemble.

Before a month's roster exists, ``plan --placeholders N`` plates ensemble shots
with the uncast blueberry copy from ``vocab/casting.yaml``. It names nobody: a
placeholder is for timing and review, and a real contributor replaces it.

``plan`` writes ``{"plates": [...], "unresolved": [...]}``: the manifest the
other two subcommands read, plus a punch-list of everyone the cut could not
credit -- a lead, or a contributor even the tail roster card had no room for --
and why. It never blocks on one -- an uncast character and a binding with no
plate copy are owner decisions -- but it never swallows one either.

Styling is ported from ``projectbluefin/website``
``src/components/wolves/WolvesIntroOverlay.vue`` -- ``.wolves-guardian-plate``
and friends. The CSS is the source of truth; the constants below name the rule
each value came from so the two can be diffed by eye. Entrance animation is
deliberately NOT reproduced: a still plate that cuts in cleanly reads better at
this length than a 0.6s CSS transform ported by hand, and it keeps the burn a
single ffmpeg overlay rather than an image sequence.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FRAME_W, FRAME_H = 1920, 1080

# The site sizes everything in rem. 1rem = 16px reproduces the desktop layout
# at 1080p, which is what these plates are composited over.
REM = 16.0

# --- palette (WolvesIntroOverlay.vue, as baked by wolves-*/render/reveal.html) -
INK = (8, 12, 20, 209)          # background: rgb(8 12 20 / 82%)
CREST_FILL = (8, 12, 20, 242)   # .wolves-guardian-plate-crest-inner
TEXT = (245, 245, 245, 255)     # .wolves-guardian-plate-name color
# .name's gradient has a MIDDLE stop: #fff 0%, #e2e8f0 60%, #a0aec0 100%.
NAME_MID = (226, 232, 240, 255)      # #e2e8f0 at 60%
NAME_BOTTOM = (160, 174, 192, 255)   # #a0aec0

# text-shadow: 0 2px 10px rgb(0 0 0 / 80%) -- a CSS blur radius of 10px is
# roughly a Gaussian sigma of 5. Without it the type sits flat on a translucent
# plate that has footage showing through it.
SHADOW = (0, 0, 0, 204)
SHADOW_OFFSET = (0, 2)
SHADOW_BLUR = 5

# Default (blue) chrome vs the burnished-silver trustee treatment.
VARIANTS = {
    "default": {
        "border": (147, 197, 253, 115),   # rgb(147 197 253 / 45%)
        "accent": (147, 197, 253, 255),   # #93c5fd
        "label": (147, 197, 253, 255),
        "klass": (203, 213, 245, 255),    # #cbd5f5 (reveal.html .class)
        "title": (147, 197, 253, 255),    # #93c5fd (reveal.html .title)
        "glow": (147, 197, 253, 140),
    },
    "trustee": {
        "border": (203, 213, 225, 140),   # rgb(203 213 225 / 55%)
        "accent": (209, 213, 219, 255),   # #d1d5db
        "label": (229, 231, 235, 255),    # #e5e7eb
        "klass": (226, 232, 240, 255),
        "title": (203, 213, 225, 255),    # #cbd5e1
        "glow": (226, 232, 240, 140),
    },
    "leader": {
        "border": (250, 204, 21, 140),    # rgb(250 204 21 / 55%)
        "accent": (250, 204, 21, 255),    # #facc15
        "label": (250, 204, 21, 255),
        # The leader block overrides the label and the title but NOT the class
        # row, so the subclass keeps the default colour on the gold plate.
        # Christoph Blecker's "Broodweaver Warlock" renders exactly this way.
        "klass": (203, 213, 245, 255),    # #cbd5f5, as default
        "title": (253, 230, 138, 255),    # #fde68a
        "glow": (250, 204, 21, 140),
    },
}

# --- type ramp (clamp() upper bounds, i.e. the desktop sizes) ---------------
FS_LABEL = 1.8 * REM     # .wolves-guardian-plate-label
FS_CLASS = 2.1 * REM     # .wolves-guardian-plate-class
FS_NAME = 3.6 * REM      # .wolves-guardian-plate-name
FS_TITLE = 1.9 * REM     # .wolves-guardian-plate-title

LS_LABEL = 0.35          # letter-spacing: 0.35em
LS_CLASS = 0.05
LS_TITLE = 0.08          # reveal.html .title; the site leaves the title untracked

PAD_X = 2.0 * REM        # padding: 1.75rem 2rem 1.5rem
PAD_TOP = 1.75 * REM
PAD_BOTTOM = 1.5 * REM
CHAMFER = 16             # clip-path: polygon(16px ...)
CORNER_RADIUS = 12       # border-radius: 0.75rem, on the two corners not cut
CREST = 2.5 * REM        # .wolves-guardian-plate-crest

# --- chat card (wolves-*/render/plate.html -- the baked dialogue pill) -------
# The other videos' talking card is neither the reveal plate nor the site's
# .wc-nameplate: it is the one-line pill plate.html bakes -- [crest] SPEAKER |
# message, shrink-to-fit, never wrapped. plate.html renders at 2x for the 4K
# master, so every constant here is the 1x half, named after the rule it came
# from. Where plate.html and the site disagree (pill vs chamfered box, one
# line vs stacked rows, gradient message vs solid uppercase label) the baked
# reference wins: it is what the videos were actually rendered from
# (docs/skills/plates.md: where the site and the videos disagree, the videos win).
CHAT_AVATAR = 42         # .avatar/.pfp: 84px circle; the crest is the no-pfp fallback
CHAT_GAP = 13            # .plate { gap: 26px }
CHAT_PAD_L = 12          # .plate { padding: 20px 44px 20px 24px }
CHAT_PAD_R = 22
CHAT_PAD_Y = 10
CHAT_MAX_W = 1550        # .plate { max-width: 3100px }
CHAT_FS_SPEAKER = 17     # .eyebrow { font-size: 34px }
CHAT_LS_SPEAKER = 0.28   # .eyebrow { letter-spacing: 0.28em }
CHAT_FS_TEXT_MAX = 28    # render script MAX_FONT 56px -- the preferred size
CHAT_FS_TEXT_MIN = 19    # ...MIN_FONT 38px -- the shrink-to-fit floor
CHAT_RULE_W = 2          # .rule { width: 3px } -- 1.5px at 1x, rounded up
CHAT_RULE_H = 23         # .rule { height: 46px }

# Row placement: bottom 10%, left/right 5% (.wolves-guardian-plate-row).
MARGIN_X = 0.05
MARGIN_BOTTOM = 0.10

# --- group rows (the reference deck's roll call, ~/Videos/nameplates.json) ---
# The deck's gp_* entries are one row of credits, doubly staggered: spatially,
# each card carries an absolute `x` measured against the picture; temporally,
# entrances cascade GROUP_STAGGER seconds apart and every card ends together.
# They are deliberately NOT aimed at individual bodies: the casting model says
# the anonymous crowd is fillable by anyone (vocab/casting.yaml `ensemble`), so
# an even spread reads as a row of credits rather than arrows at people.
GROUP_SCALE = 0.78      # the deck's gp_* scale
GROUP_MIN_SCALE = 0.4   # below this the type is too small to be a credit
GROUP_GAP = 24          # px between cards in a row
GROUP_STAGGER = 0.4     # the cascade between entrances; the row ends together
# The roll call spans nearly the whole picture width (the deck's row runs
# x=51 -> ~1920, ~2.7% margins), wider than a corner plate's 5%.
GROUP_MARGIN_X = 0.03

# The CSS stack is `ui-monospace, 'SFMono-Regular', 'Cascadia Mono', monospace`
# (wolves-*/render/reveal.html, and --wc-font-mono on the site). Neither Apple's
# SF Mono nor Cascadia Mono ships on a Fedora atomic host, so the browser that
# baked the reference plates fell through to the fontconfig generic -- which is
# DejaVu Sans Mono. Match that resolution order exactly.
#
# Adwaita Mono is deliberately NOT first: it is the desktop's mono and it is
# installed here, so preferring it silently rendered every plate in a typeface
# that appears nowhere in the stack, and none of the other videos.
FONT_CANDIDATES = {
    "regular": [
        "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/liberation-fonts/LiberationMono-Regular.ttf",
    ],
    "bold": [
        "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/liberation-fonts/LiberationMono-Bold.ttf",
    ],
}


def _font(weight, size):
    for path in FONT_CANDIDATES[weight]:
        if Path(path).exists():
            return ImageFont.truetype(path, int(round(size)))
    raise RuntimeError(
        f"no {weight} monospace font found; tried {FONT_CANDIDATES[weight]}"
    )


def _tracked_width(draw, text, font, tracking_em):
    """Width of ``text`` with CSS-style letter-spacing applied."""
    extra = tracking_em * font.size
    return sum(draw.textlength(ch, font=font) + extra for ch in text)


def _draw_tracked(draw, xy, text, font, fill, tracking_em):
    """Letter-spaced text. Pillow has no tracking, so glyphs are placed by hand."""
    x, y = xy
    extra = tracking_em * font.size
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + extra


def _gradient_text(size, text, font, stops):
    """The name's vertical gradient (background-clip: text).

    ``stops`` is ``[(offset, rgba), ...]`` with offsets in 0..1, mirroring the
    CSS: `#fff 0%, #e2e8f0 60%, #a0aec0 100%`. The middle stop matters -- a
    straight white->slate ramp washes the centre of the name out.
    """
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).text((0, 0), text, font=font, fill=255)
    grad = Image.new("RGBA", size)
    for y in range(size[1]):
        t = y / max(1, size[1] - 1)
        lower = max(i for i, (offset, _) in enumerate(stops) if offset <= t) \
            if any(offset <= t for offset, _ in stops) else 0
        upper = min(lower + 1, len(stops) - 1)
        (o0, c0), (o1, c1) = stops[lower], stops[upper]
        k = 0.0 if o1 == o0 else (t - o0) / (o1 - o0)
        grad.paste(
            tuple(int(c0[i] + (c1[i] - c0[i]) * k) for i in range(4)),
            (0, y, size[0], y + 1),
        )
    layer.paste(grad, (0, 0), mask)
    return layer


def _with_text_shadow(layer):
    """`text-shadow: 0 2px 10px rgb(0 0 0 / 80%)` under a text layer.

    The plate is translucent, so footage shows through it; without the shadow
    the type has no separation from whatever is moving behind the card.
    """
    shadow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    shadow.paste(SHADOW, (0, 0), layer.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(SHADOW_BLUR))
    out = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    out.alpha_composite(shadow, SHADOW_OFFSET)
    out.alpha_composite(layer)
    return out


def _chamfered(size, fill, border, radius=CHAMFER, corner=CORNER_RADIUS):
    """The plate box: two chamfered corners, two rounded, one hairline rule.

    The CSS applies `border-radius` *and* a `clip-path`, so the polygon wins on
    the top-left and bottom-right (diagonal cuts) while the other two corners
    keep their radius. Built from a supersampled mask because Pillow will not
    antialias a polygon edge, and a hard-aliased diagonal is exactly the sort of
    thing that reads as "not the same card" next to a browser-rendered plate.
    """
    w, h = size
    scale = 4
    big = (w * scale, h * scale)
    r, c = radius * scale, corner * scale

    mask = Image.new("L", big, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, big[0] - 1, big[1] - 1],
                                           radius=c, fill=255)
    # Cut the two chamfers back out of the rounded box.
    cut = ImageDraw.Draw(mask)
    cut.polygon([(0, 0), (r, 0), (0, r)], fill=0)
    cut.polygon([(big[0] - 1, big[1] - 1 - r), (big[0] - 1, big[1] - 1),
                 (big[0] - 1 - r, big[1] - 1)], fill=0)
    mask = mask.resize(size, Image.LANCZOS)

    img = Image.new("RGBA", size, (0, 0, 0, 0))
    img.paste(fill, (0, 0, w, h), mask)

    # The 1px rule is the mask minus its own inset, so it follows every corner.
    inner = mask.filter(ImageFilter.MinFilter(3))
    edge = ImageChops.subtract(mask, inner)
    rule = Image.new("RGBA", size, (0, 0, 0, 0))
    rule.paste(border, (0, 0, w, h), edge)
    img.alpha_composite(rule)
    return img


def _crest(size, accent, glow):
    """The hex crest with its chevron (inline SVG in the Vue component)."""
    scale = 4  # supersampled, then downscaled: Pillow has no antialiased strokes
    s = int(size * scale)
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def pts(coords):
        return [(x / 100 * s, y / 100 * s) for x, y in coords]

    d.polygon(pts([(50, 5), (85, 20), (95, 55), (50, 95), (5, 55), (15, 20)]),
              outline=accent, width=int(2 * scale))
    d.polygon(pts([(50, 12), (78, 25), (87, 52), (50, 85), (13, 52), (22, 25)]),
              fill=CREST_FILL, outline=TEXT, width=int(1 * scale))
    d.line(pts([(35, 45), (50, 60), (65, 45)]), fill=accent,
           width=int(4 * scale), joint="curve")
    return img.resize((int(size), int(size)), Image.LANCZOS)


def _horizon(width, height, accent, to_left=False):
    """A header rule: transparent -> accent -> white, with a soft glow."""
    img = Image.new("RGBA", (max(1, int(width)), max(1, int(height))), (0, 0, 0, 0))
    w = img.width
    for x in range(w):
        t = (w - 1 - x) / max(1, w - 1) if to_left else x / max(1, w - 1)
        if t < 0.6:
            k = t / 0.6
            px = (*accent[:3], int(255 * k))
        else:
            k = (t - 0.6) / 0.4
            px = tuple(int(accent[i] + (255 - accent[i]) * k) for i in range(3)) + (255,)
        img.paste(px, (x, 0, x + 1, img.height))
    return img


def _pill(size, fill, border):
    """plate.html's `.plate`: `border-radius: 999px` under a 1px (2px at 2x) rule.

    The fill is a supersampled mask so the round caps antialias. The hairline
    is STROKED, not mask-minus-eroded: `_chamfered`'s erosion trick only shows
    where its mask slopes, but a pill is all straight runs between the caps and
    the browser's border is visible the whole way around.
    """
    w, h = size
    scale = 4
    big = (w * scale, h * scale)
    mask = Image.new("L", big, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, big[0] - 1, big[1] - 1],
                                           radius=big[1] // 2, fill=255)
    mask = mask.resize(size, Image.LANCZOS)

    img = Image.new("RGBA", size, (0, 0, 0, 0))
    img.paste(fill, (0, 0, w, h), mask)

    ring = Image.new("RGBA", big, (0, 0, 0, 0))
    ImageDraw.Draw(ring).rounded_rectangle([0, 0, big[0] - 1, big[1] - 1],
                                           radius=big[1] // 2,
                                           outline=border, width=scale)
    img.alpha_composite(ring.resize(size, Image.LANCZOS))
    return img


def _render_chat(spec):
    """The dialogue pill from wolves-*/render/plate.html: `[crest] SPEAKER | message`.

    One horizontal line on a pill -- the small talking card the other videos
    use, not the Guardian reveal's centered stack. The reveal names the person
    once; every line after that rides in this. Both fields are recovered copy:
    `speaker` from vocab/casting.yaml, `text` from dialogue/<id>/dialogue.json.
    """
    chrome = VARIANTS["default"]  # plate.html bakes only the blue chrome
    # .eyebrow { text-transform: uppercase } -- the speaker is chrome.
    speaker = (spec.get("speaker") or "").upper()
    # NOT uppercased. The site's .wc-nameplate-label shouts its label, but
    # plate.html's .message carries no text-transform and the baked plates
    # prove it ("I guess I'm taking the long way around."): recovered dialogue
    # is real speech, and shouting it would put an emphasis on it nobody said.
    text = spec.get("text") or ""

    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    f_speaker = _font("regular", CHAT_FS_SPEAKER)
    speaker_w = _tracked_width(probe, speaker, f_speaker, CHAT_LS_SPEAKER)

    def pill_width(f_text):
        # the flex row: pad, avatar, gap, eyebrow, gap, rule, gap, message, pad
        return (CHAT_PAD_L + CHAT_AVATAR + CHAT_GAP + speaker_w + CHAT_GAP
                + CHAT_RULE_W + CHAT_GAP
                + probe.textlength(text, font=f_text) + CHAT_PAD_R)

    # plate.html's shrink-to-fit: start at MAX_FONT and step down until the
    # pill fits max-width -- one wide line, never a wrap ("Prefer one wide
    # line", authoring-interview-chat-plates). The loop stops at MIN_FONT just
    # like the browser's, so a line that still overflows renders whole rather
    # than clipping recovered dialogue.
    size = CHAT_FS_TEXT_MAX
    f_text = _font("bold", size)
    while size > CHAT_FS_TEXT_MIN and pill_width(f_text) > CHAT_MAX_W:
        size -= 1
        f_text = _font("bold", size)

    box_w = int(math.ceil(pill_width(f_text)))
    # border-box: the avatar is the tallest item, padding above and below.
    box_h = int(round(CHAT_AVATAR + 2 * CHAT_PAD_Y))
    img = _pill((box_w, box_h), INK, chrome["border"])
    mid = box_h / 2

    # The avatar slot holds a pfp in the videos; with no pfp in the field set,
    # the crest is plate.html's own fallback.
    img.alpha_composite(_crest(CHAT_AVATAR, chrome["accent"], chrome["glow"]),
                        (CHAT_PAD_L, int(mid - CHAT_AVATAR / 2)))

    # Text goes on its own layer so one text-shadow sits under all of it
    # (plate.html: text-shadow: 0 4px 20px at 2x == 0 2px 10px here). The rule
    # is chrome, not type, so it stays out from under the shadow layer.
    text_layer = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)

    x = CHAT_PAD_L + CHAT_AVATAR + CHAT_GAP
    if speaker:
        a, d = f_speaker.getmetrics()
        _draw_tracked(draw, (x, mid - (a + d) / 2), speaker, f_speaker,
                      chrome["label"], CHAT_LS_SPEAKER)
    x += speaker_w + CHAT_GAP
    img.alpha_composite(
        Image.new("RGBA", (CHAT_RULE_W, CHAT_RULE_H), chrome["border"]),
        (int(x), int(mid - CHAT_RULE_H / 2)))
    x += CHAT_RULE_W + CHAT_GAP

    if text:
        a, d = f_text.getmetrics()
        layer = _gradient_text(
            (int(math.ceil(probe.textlength(text, font=f_text))) + 4,
             int(f_text.size * 1.4)),
            text, f_text,
            [(0.0, (255, 255, 255, 255)), (0.6, NAME_MID), (1.0, NAME_BOTTOM)])
        text_layer.alpha_composite(layer, (int(x), int(mid - (a + d) / 2)))

    img.alpha_composite(_with_text_shadow(text_layer))
    return img


def _variant_for(spec):
    """The reference deck flags chrome with `trustee`; `variant` adds `leader`.

    `leader` is checked first because the CSS does the same:
    `.wolves-guardian-plate-trustee:not(.wolves-guardian-plate-leader)` means
    the gold leader treatment takes precedence over burnished silver, so a
    binding can carry both flags and be plated as the leader.
    """
    if spec.get("variant"):
        return VARIANTS[spec["variant"]]
    if spec.get("kind") == "title":
        return VARIANTS["trustee"]  # the title card uses the silver treatment
    return VARIANTS["trustee" if spec.get("trustee") else "default"]


def render_plate(spec):
    """One plate spec -> a tight RGBA image (no frame padding).

    Three card shapes. Two come straight from ~/Videos/nameplates.json: the
    Guardian plate (`label` / `class` / `name` / `title`) and the title card
    (`title` / `subtitle` / `body`). The third is the chat card (`speaker` /
    `text`), added to the data model deliberately so a cut can show a recovered
    conversation without a plate line anybody had to invent. The chat card is
    a different component -- the plate.html dialogue pill -- so it dispatches
    to `_render_chat` instead of sharing the reveal's centered stack.
    """
    if spec.get("kind") == "chat":
        return _render_chat(spec)
    variant = _variant_for(spec)
    ghost = spec.get("kind") == "ghost"
    card = spec.get("kind") == "title"
    scale = 0.82 if ghost else 1.0

    f_label = _font("regular", FS_LABEL * scale)
    f_class = _font("regular", FS_CLASS * scale)
    f_name = _font("bold", FS_NAME * scale)
    f_title = _font("regular", FS_TITLE * scale)

    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    if card:
        # The title card has no eyebrow and no class: its `title` is the display
        # line and `subtitle` sits under it, with `body` beneath both.
        label, klass = "", ""
        name = spec.get("title") or ""
        title = spec.get("subtitle") or ""
        body = list(spec.get("body") or [])
    else:
        label = (spec.get("label") or "").upper()
        # NOT uppercased. The site stylesheet puts `text-transform: uppercase`
        # on .wolves-guardian-plate-class, but the baked reveal that the other
        # videos actually use does not -- "Behemoth Titan", not "BEHEMOTH
        # TITAN". The videos are the thing being matched.
        klass = "" if ghost else (spec.get("class") or "")
        name = spec.get("name") or ""
        title = spec.get("title") or ""
        body = []

    widths = [
        _tracked_width(probe, label, f_label, LS_LABEL),
        _tracked_width(probe, klass, f_class, LS_CLASS),
        probe.textlength(name, font=f_name),
        _tracked_width(probe, title, f_title, LS_TITLE),
        *(probe.textlength(line, font=f_class) for line in body),
        CREST * scale * 3,  # the header never collapses below crest + two rules
    ]
    # The CSS caps the plate at 44rem and lets the browser wrap; nothing here
    # wraps, so the box sizes to its longest line instead of clipping it.
    inner = max(widths)
    box_w = int(round(inner + 2 * PAD_X * scale))

    gap = 0.35 * REM * scale
    crest_h = CREST * scale
    stack = [(label, f_label), (klass, f_class), (name, f_name), (title, f_title)]
    stack += [(line, f_class) for line in body]
    text_h = sum(f.size * 1.25 + gap for text, f in stack if text)
    box_h = int(round(PAD_TOP * scale + crest_h + gap + text_h + PAD_BOTTOM * scale))

    img = _chamfered((box_w, box_h), INK, variant["border"])

    # Text goes on its own layer so one text-shadow can sit under all of it,
    # matching CSS (the shadow applies to type, not to the crest or the rules).
    text_layer = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)

    # Header: rule, crest, rule.
    y = PAD_TOP * scale
    cx = box_w / 2
    rule_w = (inner - crest_h - 2 * gap) / 2
    rule_y = int(y + crest_h / 2 - 1)
    if rule_w > 8:
        img.alpha_composite(_horizon(rule_w, 2, variant["accent"]),
                            (int(PAD_X * scale), rule_y))
        img.alpha_composite(_horizon(rule_w, 2, variant["accent"], to_left=True),
                            (int(box_w - PAD_X * scale - rule_w), rule_y))
    img.alpha_composite(_crest(crest_h, variant["accent"], variant["glow"]),
                        (int(cx - crest_h / 2), int(y)))
    y += crest_h + gap

    for text, font, colour, tracking in (
        (label, f_label, variant["label"], LS_LABEL),
        (klass, f_class, variant["klass"], LS_CLASS),
    ):
        if not text:
            continue
        w = _tracked_width(draw, text, font, tracking)
        _draw_tracked(draw, (cx - w / 2, y), text, font, colour, tracking)
        y += font.size * 1.25 + gap

    if name:
        w = int(math.ceil(draw.textlength(name, font=f_name)))
        layer = _gradient_text((w + 4, int(f_name.size * 1.4)), name, f_name,
                               [(0.0, (255, 255, 255, 255)),
                                (0.6, NAME_MID),
                                (1.0, NAME_BOTTOM)])
        text_layer.alpha_composite(layer, (int(cx - w / 2), int(y)))
        y += f_name.size * 1.25 + gap

    if title:
        w = _tracked_width(draw, title, f_title, LS_TITLE)
        _draw_tracked(draw, (cx - w / 2, y), title, f_title, variant["title"],
                      LS_TITLE)
        y += f_title.size * 1.25 + gap

    # The title card's body copy: one authored line per row.
    for line in body:
        w = draw.textlength(line, font=f_class)
        draw.text((cx - w / 2, y), line, font=f_class, fill=variant["klass"])
        y += f_class.size * 1.25 + gap

    img.alpha_composite(_with_text_shadow(text_layer))
    return img


def place(plate, position="left", picture=None, x=None, scale=1.0):
    """Composite a plate onto a full 1920x1080 transparent frame.

    ``picture`` is the real image area ``(x, y, w, h)`` inside the frame. The
    row margins are measured against *it*, not the frame, so on a letterboxed
    2.39:1 cinematic the plate sits on the picture instead of hanging onto the
    black bar. Defaults to the whole frame.

    ``position: "group"`` is the reference deck's roll call: the card carries
    an absolute ``x`` measured from the *picture's* left edge (never the raw
    frame's, so it cannot drift onto a letterbox bar) and a ``scale`` that
    shrinks the rendered card, the same lever ``render_plate``'s ghost scale
    pulls. A group plate without an ``x`` is a bug, not a default.
    """
    frame = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    if scale != 1.0:
        plate = plate.resize((max(1, int(round(plate.width * scale))),
                              max(1, int(round(plate.height * scale)))),
                             Image.LANCZOS)
    px, py, pw, ph = picture or (0, 0, FRAME_W, FRAME_H)
    y = py + int(ph * (1 - MARGIN_BOTTOM)) - plate.height
    if position == "group":
        if x is None:
            raise ValueError("a group plate needs an absolute x")
        x = px + int(round(x))
    elif position == "right":
        x = px + int(pw * (1 - MARGIN_X)) - plate.width
    elif position == "center":
        x = px + (pw - plate.width) // 2
    else:
        x = px + int(pw * MARGIN_X)
    frame.alpha_composite(plate, (x, y))
    return frame


# --- Planning a cut's plates -------------------------------------------------

# A plate the viewer cannot finish reading is worse than no plate: below this
# hold the shot is skipped and the person waits for their next appearance.
MIN_HOLD = 2.2
# ...but a plate still has to be anchored to a shot the viewer can tie it to.
MIN_ANCHOR = 1.5
LEAD_IN = 0.4     # let the cut land before the plate arrives
TAIL_OUT = 0.25   # ...and clear before the next one
DEFAULT_HOLD = 5.0
# The roster card is a credit, not an end board: on a long final shot the
# remaining room can be half a minute, which reads as a stuck frame.
MAX_ROSTER_HOLD = 10.0
# A reveal reads better on the character's hero move than on the static insert
# they happen to appear in first -- Osiris's name arriving as he climbs the
# stairwell, not while the camera sits on his mask. `traversal_hero` is already
# derived (wide, stable, in motion), so the index says which shot that is.
#
# Bounded, though: a lead the audience has been watching for this long is not
# being revealed any more, they are being belatedly captioned. Past it, the
# reveal goes back to the first appearance that can hold it.
MAX_REVEAL_DEFERRAL = 30.0

# The fields schema/brief.schema.json allows in a brief plate's `copy` -- the
# reference deck's closed on-screen vocabulary, the same set a lead binding's
# `plate:` block carries. brief.py's schema validation is optional (it no-ops
# without jsonschema installed), so the planner defends the set itself: a
# field outside it is an invented row on a card that names a real person, and
# that is an error, never something to accommodate.
BRIEF_COPY_FIELDS = {"label", "class", "name", "title", "trustee", "kind",
                     "variant"}


def _tc_seconds(tc):
    """``mm:ss`` or ``HH:MM:SS`` -> seconds (the shape the brief schema pins)."""
    parts = [int(p) for p in str(tc).split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def _source_moment_on_timeline(timeline, at_sec, video_id=None):
    """A source-time moment -> (its time on the rendered cut, the shot), or
    (None, None) when the moment is not in the cut.

    A brief's `at` is in SOURCE time ("drop her nameplate right after she
    removes her helmet, 0:14"); the plate has to land on the CUT's clock, so
    the moment is mapped through the shot that carries it. A moment no
    selected shot covers -- or one the render's hold cap trimmed away --
    returns None, and the caller reports rather than relocates it: the owner
    pointed at a moment, and quietly moving their credit to a moment they did
    not choose is the same failure as inventing the copy.
    """
    for start, duration, shot in timeline:
        if video_id and shot.get("video_id") != video_id:
            continue
        s0, s1 = shot.get("start_sec"), shot.get("end_sec")
        if s0 is None or s1 is None or not (s0 <= at_sec < s1):
            continue
        if at_sec - s0 > duration:  # trimmed by the render's max_shot_sec cap
            continue
        return round(start + (at_sec - s0), 3), shot
    return None, None


def _plan_brief_plates(brief, timeline, total, hold, leads, busy, log):
    """A brief's `plates[]` -> fixed manifest entries, before anything derived.

    Returns ``(entries, plated_characters, reveal_copy)``: the fixed plates,
    the characters they already credit (so the reveal pass does not plate them
    again), and copy to hand the reveal pass for a character whose binding has
    no `plate:` block of its own.

    The owner authored these, so they pin the timeline: each entry with an
    `at` takes its window first and everything derived routes around it. Three
    rules keep that safe:

    * **Copy is closed.** A field outside BRIEF_COPY_FIELDS is refused.
    * **The vocab wins a conflict.** When the character's binding in
      vocab/casting.yaml already has a `plate:` block, that copy is used and
      the brief's copy is reported as deferred -- the vocab is the project's
      durable record of claims about real people, changed by reviewed PR,
      while a brief is one video's request in an editable issue body. Letting
      a brief override it would let two videos disagree about a person's
      credit, which is the drift the vocab exists to prevent. A brief that
      disagrees with the record is a signal the record needs an edit, so the
      conflict is logged rather than adjudicated silently.
    * **The owner's `at` is honoured, not re-derived.** The moment is mapped
      from source time onto the cut; when it is not in the cut (or lands on a
      shot the character's constraints exclude) that is reported, and a plate
      naming a character falls back to the derived reveal rather than
      vanishing.

    Every entry carries `copy_source` -- "brief" or "casting" -- so a reader
    of the manifest can tell owner-authored copy from the vocab's.
    """
    entries, plated, reveal_copy = [], set(), {}

    def note(msg):
        if log:
            log(msg)

    requested = {}  # character -> placed fixed?
    for index, req in enumerate(brief.get("plates") or [], start=1):
        copy = dict(req.get("copy") or {})
        extra = sorted(set(copy) - BRIEF_COPY_FIELDS)
        if extra:
            raise ValueError(
                f"brief plate #{index} has copy field(s) outside the "
                f"reference deck's closed set: {', '.join(extra)}. The deck "
                "has no row for them, and inventing one puts unauthored text "
                "on a card that names a real person -- see "
                "docs/skills/plates.md."
            )
        character = req.get("character")
        if not character and not copy:
            note(f"  brief plate #{index}: no character and no copy -- "
                 f"direction, not a plate ({(req.get('note') or '').strip()}); "
                 "nothing to plan. An ensemble credit at a moment is a beat "
                 "with `ensemble: true`, not a plate.")
            continue

        binding = (leads.get(character) or {}) if character else {}
        binding_copy = binding.get("plate")
        if binding_copy:
            if copy and copy != binding_copy:
                note(f"  {character:<10} brief copy differs from the binding's "
                     "plate: block -- the vocab's copy wins (it is the durable "
                     "record; edit vocab/casting.yaml if the brief is right)")
            use, provenance = binding_copy, "casting"
        else:
            use, provenance = copy, "brief"
        if character:
            requested.setdefault(character, False)

        at_tc = req.get("at")
        placed = False
        if at_tc and use:
            t, shot = _source_moment_on_timeline(timeline, _tc_seconds(at_tc),
                                                 req.get("video_id"))
            if (t is not None and character
                    and (shot.get("casting") or {}).get("character") == character
                    and not (shot.get("casting") or {}).get("usable", True)):
                note(f"  {character:<10} the owner's moment {at_tc} lands on a "
                     "shot the binding's constraints exclude -- not a reveal; "
                     "falling back to the derived one")
                t = None
            if t is None:
                note(f"  {character or copy.get('name', index):<10} the owner's "
                     f"moment {at_tc} is not in this cut -- reported, not moved")
            else:
                dur = round(min(hold, total - t), 3)
                if dur < MIN_HOLD:
                    note(f"  {character or copy.get('name', index):<10} the "
                         f"owner's moment {at_tc} leaves {dur:.1f}s -- less "
                         "than a readable hold; honouring it anyway, it is "
                         "their call")
                if character:
                    plate_id = character
                    if plate_id in plated:
                        plate_id = f"{character}_2"  # "again here" -- the owner
                else:                                # may repeat a plate
                    from tools.derive import snake_case
                    plate_id = snake_case(copy.get("name") or "") or f"brief_{index}"
                    while plate_id in plated:
                        plate_id += "_2"
                entries.append({"id": plate_id, "at": t, "dur": dur,
                                "position": "left", "copy_source": provenance,
                                **use})
                busy.append((t, t + dur))
                plated.add(plate_id)
                if character:
                    requested[character] = True
                placed = True
                if log:
                    whose = ("owner-authored" if provenance == "brief"
                             else "the binding's")
                    log(f"  {plate_id:<10} {t:6.2f}s +{dur:.1f}s  "
                        f"{use.get('name')} (brief plate, {whose} copy, at "
                        f"the owner's moment {at_tc})")
        if placed:
            continue
        if character and not binding_copy and copy:
            reveal_copy[character] = copy  # the reveal pass plates them with it

    # A character the owner asked to plate who never (usably) appears is
    # reported, never dropped: the brief asked for them by name. A character
    # whose fixed placement failed above is NOT reported again here -- their
    # reveal falls back to the derived path, which is about to run.
    in_cut = {(s.get("casting") or {}).get("character")
              for _, _, s in timeline
              if (s.get("casting") or {}).get("role") == "lead"
              and (s.get("casting") or {}).get("usable", True)}
    for character, was_placed in requested.items():
        if not was_placed and character not in in_cut:
            note(f"  {character:<10} the brief asks to plate them, but they "
                 "are not in this cut -- reported, not dropped")
    return entries, plated, reveal_copy


def _brief_ensemble_beats(brief, timeline, log):
    """A brief's ensemble direction -> fixed moments on the cut.

    ``beats[].ensemble`` is the owner asking for a contributor credit at a
    particular moment -- "4:03 put a bluefin maintainer in here". It requests a
    SLOT, not a person: who fills it is the month's rotation in
    tools/ensemble.py, and the note stays direction rather than becoming plate
    copy. That is the whole reason this is safe to execute -- an ensemble
    credit says "one of the anonymous Guardians in this film", which is true
    wherever it lands, while naming who is in a frame would be a casting
    decision the brief does not get to make.

    Returns ``[(timeline_seconds, note, shot)]`` for the moments that can take
    a pin, earliest first. A moment outside the cut is reported and dropped,
    the same way a lead plate's is: the direction is about a frame this cut
    does not contain. So is a moment inside a shot with no ensemble role: the
    round-robin and the re-home pass both require ``casting.role ==
    "ensemble"``, and a pin may not anchor a credit anywhere they could not.
    """
    out = []
    for index, beat in enumerate(brief.get("beats") or [], start=1):
        if not beat.get("ensemble"):
            continue
        note = (beat.get("note") or "").strip()
        at_tc = beat.get("at")
        if not at_tc:
            if log:
                log(f"  brief beat #{index}: asks for an ensemble credit but "
                    f"carries no `at` -- nothing to pin it to ({note})")
            continue
        t, shot = _source_moment_on_timeline(timeline, _tc_seconds(at_tc),
                                             beat.get("video_id"))
        if t is None:
            if log:
                log(f"  {'ensemble':<10} the owner's moment {at_tc} is not in "
                    f"this cut -- reported, not moved ({note})")
            continue
        if (shot.get("casting") or {}).get("role") != "ensemble":
            if log:
                log(f"  {'ensemble':<10} the owner's moment {at_tc} lands on "
                    "a shot with no ensemble role -- an ensemble credit "
                    f"cannot anchor there; reported, not moved ({note})")
            continue
        out.append((t, note, shot))
    return sorted(out)

# Why a lead who made the cut carries no plate. A credit that disappears without
# a word is how a real person goes uncredited, so an unplated lead is REPORTED,
# never dropped -- and reporting is all it does, because the two copy-shaped
# reasons are owner decisions that no derivation can make.
UNPLATED = {
    "uncast": {
        "reason": "uncast",
        "detail": "no person is bound to this character in vocab/casting.yaml",
        "automatable": False,
        "blocked_on": "an owner casting decision (leads.<character>.person)",
    },
    "no_plate_copy": {
        "reason": "no_plate_copy",
        "detail": "the binding carries no `plate:` copy, and plate copy is never invented",
        "automatable": False,
        "blocked_on": "owner-authored plate copy (leads.<character>.plate)",
    },
    "no_window": {
        "reason": "no_window",
        "detail": "no appearance in the cut was long enough, or free, to hold a plate",
        "automatable": True,
        "blocked_on": None,
    },
}


def cut_timeline(shots, max_shot_sec=None):
    """Cut list -> [(start_on_timeline, duration, shot)] on the rendered cut.

    Mirrors what render.py actually produced, including its hold cap, so plate
    timings land on the finished file rather than on the source timeline.
    """
    out, t = [], 0.0
    for shot in shots:
        duration = shot.get("duration") or (shot["end_sec"] - shot["start_sec"])
        if max_shot_sec:
            duration = min(duration, float(max_shot_sec))
        out.append((t, duration, shot))
        t += duration
    return out


def _window(start, duration, hold=DEFAULT_HOLD, room=None):
    """A readable plate window anchored to a shot.

    The plate is *anchored* to the shot that reveals the subject, but it is not
    confined to it: a lower third routinely rides across a cut, and Destiny
    cinematics are full of two-second shots that could otherwise never carry a
    reveal. What must hold is that the shot is long enough to register as the
    anchor, and that the plate has room to be read before the cut ends.
    """
    if duration < MIN_ANCHOR:
        return None
    room = duration if room is None else room
    usable = room - LEAD_IN - TAIL_OUT
    if usable < MIN_HOLD:
        return None
    return round(start + LEAD_IN, 3), round(min(hold, usable), 3)


def _first_free_window(start, duration, hold, total, busy, cursor=None):
    """First readable window inside a shot that nothing else has taken.

    Walks forward from the shot's head: if dialogue or an earlier plate holds
    it, the next candidate starts as soon as the *blocking* window clears --
    not a whole plate-length later, which used to step straight over the gap it
    was looking for. Leads, ensemble slots and re-homed contributors all share
    this, so "the head of the shot is busy" never means "not credited at all".
    """
    cursor = start if cursor is None else cursor
    while True:
        candidate = _window(cursor, duration - (cursor - start), hold,
                            room=total - cursor)
        if not candidate:
            return None
        at, dur = candidate
        blockers = [b_end for b_start, b_end in busy
                    if at < b_end and at + dur > b_start]
        if not blockers:
            return candidate
        cursor = max(blockers) + TAIL_OUT


def _ensemble_entry(item, at, dur, copy):
    """One contributor's credit plate.

    The eyebrow distinguishes a maintainer from a passing contributor, because
    a credit that flattens the two says something untrue about a real person.
    Which one applies comes from the roster's ``org_member``; the words come
    from vocab/casting.yaml, never from here.

    A contributor whose Guardian identity is genuinely authored -- recorded
    under ``ensemble.titles`` in vocab/casting.yaml, straight from the
    reference deck -- gets that plate verbatim instead of the generic copy.
    """
    from tools.derive import ensemble_label, load_ensemble_titles

    authored = load_ensemble_titles().get(item["login"])
    if authored:
        return {"id": f"ensemble_{item['login']}", "at": at, "dur": dur,
                "position": "right", "copy_source": "casting", **authored}
    entry = {
        "id": f"ensemble_{item['login']}", "at": at, "dur": dur,
        "position": "right", "copy_source": "casting",
        "label": ensemble_label(copy, item.get("org_member")),
        "name": item["display_name"],
    }
    if copy.get("title"):
        entry["title"] = copy["title"]
    return entry


def _ensemble_group_rows(items, start, duration, hold, total, busy, copy):
    """A shot's ensemble slots as staggered rows of credits across the frame.

    The reference deck's roll call (~/Videos/nameplates.json gp_*) is staggered
    twice: spatially, each card gets an absolute ``x``; temporally, entrances
    cascade GROUP_STAGGER apart and every card in the row ends together. ``x``
    here is an EVEN SPREAD across the frame width, never a pointer at a body:
    the casting model says the anonymous crowd is fillable by anyone, so a
    plate that appears to single out a specific Guardian overclaims it. Each
    row is centred on the frame -- ``place()`` anchors that ``x`` to the
    picture's left edge, and Bungie's letterboxed cinematics are full-width, so
    the two coincide.

    The layout is computed from the actual rendered card widths (``render`` is
    deterministic, so what ``plan`` measures is what ``burn`` draws): a row
    starts at GROUP_SCALE and shrinks until it fits inside the row margins.
    When one row of all the shot's slots would have to shrink past
    GROUP_MIN_SCALE, the slots split into the fewest balanced rows that each
    fit (six cards is still one row; an unusually wide mix may go 3+3). Rows
    after the first take the next free window, and a row whose last,
    latest-arriving card could not be read stops the cascade -- anything
    unplaced is returned for the caller's sequential fallback, so nobody is
    dropped over a layout.
    """
    n = len(items)
    if n < 2:
        return [], items
    cards = [_ensemble_entry(item, 0.0, 0.0, copy) for item in items]
    widths = [render_plate(card).width for card in cards]
    usable_w = FRAME_W * (1 - 2 * GROUP_MARGIN_X)

    def chunk_scale(i, j):
        """The scale a row of cards ``i..j`` needs to fit the row margins."""
        k = j - i
        fit = (usable_w - (k - 1) * GROUP_GAP) / sum(widths[i:j])
        return math.floor(min(GROUP_SCALE, fit) * 100) / 100  # never wider than fits

    def balanced_chunks(r):
        """``r`` contiguous rows, sizes differing by at most one card."""
        base, extra = divmod(n, r)
        spans, i = [], 0
        for row_i in range(r):
            j = i + base + (1 if row_i < extra else 0)
            spans.append((i, j))
            i = j
        return spans

    layout = None
    for r in range(1, n):
        spans = balanced_chunks(r)
        scales = [chunk_scale(i, j) for i, j in spans]
        if all(s >= GROUP_MIN_SCALE for s in scales):
            layout = list(zip(spans, scales))
            break
    if layout is None:
        return [], items

    entries, cursor = [], start
    for row_i, ((i, j), scale) in enumerate(layout):
        stagger = (j - i - 1) * GROUP_STAGGER
        window = _first_free_window(start, duration, hold + stagger, total,
                                    busy, cursor)
        if not window or window[1] - stagger < MIN_HOLD:
            break  # the last card in would arrive too late to be read
        at, dur = window
        end = round(at + dur, 3)
        scaled = [int(round(w * scale)) for w in widths[i:j]]
        row_w = sum(scaled) + (j - i - 1) * GROUP_GAP
        x = (FRAME_W - row_w) / 2
        row_id = f"ensemble_row:{items[i]['segment_id']}:{row_i}"
        for k, (card, w) in enumerate(zip(cards[i:j], scaled)):
            card_at = round(at + k * GROUP_STAGGER, 3)
            card.update({"at": card_at, "dur": round(end - card_at, 3),
                         "position": "group", "group": row_id,
                         "x": int(round(x)), "scale": scale})
            x += w + GROUP_GAP
        entries.extend(cards[i:j])
        busy.append((at, end))
        cursor = end + TAIL_OUT
    return entries, items[len(entries):]


def plan(shots, leads, roster=None, max_shot_sec=None, hold=DEFAULT_HOLD, log=None,
         busy=None, only="all", soft_busy=None, brief=None,
         placeholders=0, placeholder_copy=None, unresolved=None):
    """Cut list -> plate manifest.

    Leads are plated on their first appearance long enough to read, using the
    `plate:` copy in vocab/casting.yaml. Ensemble contributors are plated from
    the deterministic assignment in tools/ensemble.py; anyone whose assigned
    shot is too short to hold a plate is credited over the final shot instead,
    so the month's contributors are never silently dropped.

    ``brief`` is a parsed brief (tools/brief.py) whose ``plates[]`` are
    planned FIRST, as fixed owner-authored credits -- see
    ``_plan_brief_plates`` for the precedence and timing rules. They are part
    of THIS pass, not a post-hoc `merge` step, for two reasons: a brief's
    `at` is in source time and only the shot list here can map it onto the
    cut's clock, and a brief plate that names a character IS that character's
    one plate -- planned anywhere else it would double-plate the reveal or die
    on merge's overlap check. Brief plates are lead-tier: with
    ``only="ensemble"`` they are expected to arrive via ``busy`` (the
    ``--around`` manifest), the same way dialogue does.

    A brief's ``beats[].ensemble`` direction is the ensemble-tier equivalent --
    "put a bluefin maintainer in here" -- and is planned in the ensemble pass,
    so it is honoured under ``only="ensemble"`` too. See
    ``_brief_ensemble_beats``.

    Every entry carries ``copy_source`` -- "brief" for owner-authored copy,
    "casting" for vocab/casting.yaml -- so the manifest says where each claim
    about a real person came from.

    ``busy`` seeds the occupied windows with something already fixed on the
    timeline. ``soft_busy`` is a *preference*: windows a plate should avoid if
    it can (in practice a dialogue pre-pass), but which it may take rather than
    not being placed at all. A reveal that yields until it disappears is worse
    than a reveal that costs one line -- so the preference is tried first for
    every shot, and only then the fallback.

    ``only`` (``leads`` / ``ensemble`` / ``all``) runs one tier at a time,
    which is what lets a scored cut be planned in priority order: the lead
    reveals are placed first because they are the credit the whole index exists
    to get right, the dialogue is fitted around them, and the ensemble then
    takes what is left.

    A reveal also prefers the character's first ``traversal_hero`` beat over
    their literal first appearance -- see ``MAX_REVEAL_DEFERRAL``.

    ``placeholders`` plates that many ensemble shots with the UNCAST blueberry
    copy from vocab/casting.yaml instead — for a cut being timed and reviewed
    before a roster exists. It is mutually exclusive with ``roster``: once real
    contributors are known, they are who the plate is for.

    Anyone the cut could not credit gets the same treatment: pass a list as
    ``unresolved`` and it is appended a punch-list entry saying who went
    unplated and why (see ``UNPLATED``) -- a lead, and also a contributor whom
    even the tail roster card had no room for. Nothing blocks -- an uncast
    character and a binding with no plate copy are both owner decisions, so the
    manifest is written either way and the punch-list is what asks for the
    decision. An empty ``unresolved`` therefore means exactly what it says:
    nobody on screen went uncredited. A shot that fails its binding's
    constraints is not an appearance at all: it is already excluded from that
    character's retrieval, so it is not a reveal.
    """
    if roster and placeholders:
        raise ValueError("pass a roster or placeholders, not both: a cut with a "
                         "roster credits real contributors, not placeholders")
    timeline = cut_timeline(shots, max_shot_sec)
    total = sum(duration for _, duration, _ in timeline)
    entries, plated = [], set()
    busy = list(busy or [])  # occupied windows, so nothing double-books the screen
    soft_busy = list(soft_busy or [])

    # The brief's owner-authored plates take their windows first; everything
    # derived routes around them.
    brief_reveal_copy = {}
    if brief and only != "ensemble":
        brief_entries, brief_plated, brief_reveal_copy = _plan_brief_plates(
            brief, timeline, total, hold, leads, busy, log)
        entries.extend(brief_entries)
        plated |= brief_plated

    unplated = {}  # character -> UNPLATED key, in first-appearance order

    def free(start, duration):
        end = start + duration
        return all(end <= b_start or start >= b_end for b_start, b_end in busy)

    def first_appearance():
        """Timeline start of each character's first plateable shot."""
        first = {}
        for start, duration, shot in timeline:
            casting = shot.get("casting") or {}
            character = casting.get("character")
            if (casting.get("role") == "lead" and character
                    and casting.get("usable", True)
                    and character not in first):
                first[character] = start
        return first

    debut = first_appearance()

    def place_leads(avoid, hero_only=False):
        for start, duration, shot in timeline:
            casting = shot.get("casting") or {}
            character = casting.get("character")
            if casting.get("role") != "lead" or not character or character in plated:
                continue
            if not casting.get("usable", True):
                continue  # a shot failing its binding's constraints is no reveal
            if hero_only:
                # Hold the reveal for the character's hero move -- but only if
                # it lands close enough to their debut to still read as an
                # introduction rather than a late caption.
                if not shot.get("traversal_hero"):
                    continue
                if start - debut.get(character, start) > MAX_REVEAL_DEFERRAL:
                    continue
            # The reportable reasons, in order: nobody cast, no copy to plate,
            # no window to plate it in. The first two are owner decisions; the
            # third a re-plan can fix. The hero filter above is none of these --
            # it defers to a later pass, it does not report.
            binding = leads.get(character) or {}
            if not binding.get("person"):
                unplated[character] = "uncast"
                continue
            copy = binding.get("plate")
            provenance = "casting"
            if not copy:
                copy = brief_reveal_copy.get(character)
                provenance = "brief" if copy else provenance
            if not copy:
                unplated[character] = "no_plate_copy"
                continue
            # Walk forward through the shot: if dialogue (or an earlier plate)
            # holds its head, the reveal waits for the next opening inside its
            # own anchor rather than being lost for the whole cut.
            window = _first_free_window(start, duration, hold, total, avoid)
            if not window:
                unplated.setdefault(character, "no_window")
                continue
            at, dur = window
            entries.append({"id": character, "at": at, "dur": dur,
                            "position": "left", "copy_source": provenance,
                            **copy})
            busy.append((at, at + dur))
            plated.add(character)
            unplated.pop(character, None)  # a later appearance carried it after all
            if log:
                notes = "".join([
                    " (on the hero move)" if hero_only else "",
                    " (clear of dialogue)" if avoid is not busy else "",
                ])
                log(f"  {character:<10} {at:6.2f}s +{dur:.1f}s  "
                    f"{copy.get('name')}{notes}")

    if only != "ensemble":
        # Preference order, most wanted first. A reveal that yields until it
        # disappears is worse than one that costs a line of dialogue, so every
        # preference is tried across the whole timeline before its fallback.
        for hero_only in (True, False):
            if soft_busy:
                place_leads(busy + soft_busy, hero_only=hero_only)
            place_leads(busy, hero_only=hero_only)

    # Every lead the passes above could not plate is REPORTED, never dropped:
    # a credit that disappears without a word is how a real person goes
    # uncredited. (Under --only ensemble the leads pass never ran, so this
    # list is empty and the loop says nothing.)
    for character, why in unplated.items():
        binding = leads.get(character) or {}
        if unresolved is not None:
            unresolved.append({
                "id": character,
                "person": binding.get("person"),
                "display_name": binding.get("display_name"),
                **UNPLATED[why],
            })
        if log:
            log(f"  UNPLATED   {character:<10} {why}: {UNPLATED[why]['detail']}")

    if not roster or only == "leads":
        # These paths never run the ensemble pass, so a brief's pinned
        # ensemble beats cannot be honoured here. That is reported, never
        # silently dropped: the direction was the owner's.
        if brief and log:
            pins = [b for b in (brief.get("beats") or []) if b.get("ensemble")]
            if pins:
                why = ("no roster was given" if not roster
                       else "--only leads plans no ensemble tier")
                log(f"  {'ensemble':<10} the brief pins {len(pins)} ensemble "
                    f"moment(s), but {why} -- reported, not honoured")
        if placeholders:
            # No roster yet: the blueberry plates hold the ensemble's places so
            # a cut can be timed and reviewed before anybody is credited.
            entries.extend(_placeholder_entries(
                timeline, total, placeholders, placeholder_copy, hold, free, busy, log))
        return sorted(entries, key=lambda e: e["at"])

    from tools.derive import load_ensemble_plate
    from tools.ensemble import assign

    ensemble_copy = load_ensemble_plate()
    result = assign(roster, [s for _, _, s in timeline])
    by_segment = {}
    for item in result["assignments"]:
        by_segment.setdefault(item["segment_id"], []).append(item)

    credited, pending = set(), []

    # The owner's ensemble direction is a FIXED POINT: "put a bluefin
    # maintainer in here" pins one slot to one moment, and the rotation below
    # routes around it exactly as it routes around a lead reveal or a line of
    # dialogue. It is honoured before the round-robin runs, because a moment
    # the owner chose outranks a moment the assignment happened to produce --
    # and because taking its window first is what makes the rest route around
    # it at all.
    #
    # WHO fills the slot still comes from the rotation, never from the note.
    # The note is direction ("a bluefin maintainer"), and turning it into copy
    # would put words on whichever real contributor landed there.
    #
    # Fixed does not mean above the one-plate-at-a-time rule: the pin takes
    # only windows nothing earlier claimed (brief plates, lead reveals,
    # --around dialogue, earlier pins). It is shortened to fit ahead of the
    # next plate when it can be, and reported and skipped when it cannot --
    # it is never MOVED, because the owner pointed at a frame.
    if brief:
        rotation = list({item["login"]: item
                         for item in result["assignments"]}.values())
        for t, note, _ in _brief_ensemble_beats(brief, timeline, log):
            item = next((i for i in rotation if i["login"] not in credited), None)
            if item is None:
                if log:
                    log(f"  {'ensemble':<10} the owner asks for a credit at "
                        f"{t:.2f}s, but every contributor in the rotation is "
                        f"already credited -- reported, not duplicated ({note})")
                continue
            dur = round(min(hold, total - t), 3)
            if dur < MIN_HOLD:
                # A pin on the trim boundary maps to the cut's final instant
                # (dur == 0), and one near it to an unreadable flash. Neither
                # may be emitted -- validation rejects a non-positive dur, and
                # a plate below MIN_HOLD cannot be read.
                if log:
                    log(f"  {'ensemble':<10} the owner's moment {t:.2f}s "
                        f"leaves {dur:.1f}s on the cut -- no readable hold "
                        f"remains; reported, not emitted ({note})")
                continue
            # The moment is a fixed point, but the screen may already be
            # booked: an earlier pin, a brief plate, a lead reveal, or
            # dialogue via --around. The pin never MOVES -- the owner pointed
            # at this frame -- so a moment already covered is reported and
            # skipped, and a partly free window is shortened to end where the
            # next plate begins (when what remains can still be read).
            overlapping = sorted(
                (b_start, b_end) for b_start, b_end in busy
                if t < b_end and b_start < t + dur)
            if overlapping and overlapping[0][0] <= t:
                if log:
                    log(f"  {'ensemble':<10} the owner's moment {t:.2f}s is "
                        "already covered by another plate -- reported, not "
                        f"moved ({note})")
                continue
            if overlapping:
                trimmed = round(overlapping[0][0] - t, 3)
                if trimmed < MIN_HOLD:
                    if log:
                        log(f"  {'ensemble':<10} the owner's moment {t:.2f}s "
                            f"has only {trimmed:.1f}s before the next plate "
                            f"-- reported, not moved ({note})")
                    continue
                if log:
                    log(f"  {'ensemble':<10} the owner's moment {t:.2f}s "
                        f"holds {dur:.1f}s, shortened to {trimmed:.1f}s ahead "
                        f"of the next plate ({note})")
                dur = trimmed
            entries.append(_ensemble_entry(item, t, dur, ensemble_copy))
            busy.append((t, t + dur))
            credited.add(item["login"])
            if log:
                log(f"  {'ensemble':<10} {t:6.2f}s +{dur:.1f}s  "
                    f"{item['display_name']} (the owner's moment: {note})")

    for start, duration, shot in timeline:
        items = [item for item in by_segment.get(shot.get("segment_id"), [])
                 if item["login"] not in credited]
        # One credit per person per shot: a pool smaller than the slot count
        # assigns the same login twice, and a row cannot name someone twice.
        items = list({item["login"]: item for item in items}.values())
        if not items:
            continue
        # A shot with several ensemble slots credits them as staggered rows
        # spread across the frame -- the reference deck's roll call -- instead
        # of a queue of right-hand plates arriving one at a time in the same
        # corner. Each row shares one busy window, so the rest of the cut
        # still sees one plate at a time outside the row.
        row, leftover = _ensemble_group_rows(items, start, duration, hold,
                                             total, busy, ensemble_copy)
        if row:
            entries.extend(row)
            for item in items[:len(row)]:
                credited.add(item["login"])
            if log:
                for card, item in zip(row, items):
                    log(f"  {'ensemble':<10} {card['at']:6.2f}s +{card['dur']:.1f}s  "
                        f"{item['display_name']} (group row x={card['x']})")
        # Single slot, or a row that cannot fit/readably stagger: the plates
        # ride across the cut one after another instead, so a six-Guardian
        # firefight can still name six contributors rather than burning five of
        # them onto the roster card for want of a start time.
        cursor = start
        for item in leftover:
            window = _first_free_window(start, duration, hold, total, busy, cursor)
            if not window:
                pending.append(item)
                continue
            at, dur = window
            cursor = at + dur + TAIL_OUT
            entries.append(_ensemble_entry(item, at, dur, ensemble_copy))
            busy.append((at, at + dur))
            credited.add(item["login"])
            if log:
                log(f"  {'ensemble':<10} {at:6.2f}s +{dur:.1f}s  {item['display_name']}")

    # Second pass: anyone their own shot could not hold is re-homed onto another
    # ensemble shot that still has room. An ensemble credit is not a claim about
    # a particular body in a particular frame the way a lead binding is -- the
    # slot formula says the crowd is fillable, and vocab/casting.yaml assigns it
    # programmatically -- so "one of the anonymous Guardians in this film" stays
    # true wherever the plate lands. It is still a real credit, and a named
    # contributor reads better than a line on a roster card.
    #
    # Whoever the body of the cut still could not hold is credited together on
    # one roster plate over the tail, in rotation order. The month's
    # contributors are the ensemble; dropping them silently would be the one
    # unacceptable outcome -- so when even the tail has no room, every name the
    # cut could not credit goes on the punch-list, not just into a log line.
    pending = [item for item in pending if item["login"] not in credited]
    still_pending = []
    for item in pending:
        placed = False
        for start, duration, shot in timeline:
            if (shot.get("casting") or {}).get("role") != "ensemble":
                continue
            window = _first_free_window(start, duration, hold, total, busy)
            if not window:
                continue
            at, dur = window
            entries.append(_ensemble_entry(item, at, dur, ensemble_copy))
            busy.append((at, at + dur))
            credited.add(item["login"])
            placed = True
            if log:
                log(f"  {'ensemble':<10} {at:6.2f}s +{dur:.1f}s  "
                    f"{item['display_name']} (re-homed)")
            break
        if not placed:
            still_pending.append(item)

    # The sign-off card over the tail. It has two jobs, and they are separable:
    #
    #   1. It is the cut's LAST BEAT -- the card's headline (roster_title in
    #      vocab/casting.yaml) is how the video says goodbye, so it plays
    #      whether or not anyone is left to credit. Gating it on leftovers
    #      meant that crediting everyone in the body silently deleted the
    #      ending.
    #   2. Its `body` credits whoever the body of the cut could not hold, in
    #      rotation order. That list may be empty; the card still plays.
    #
    # Dropping a contributor silently remains the one unacceptable outcome.
    pending = [item for item in still_pending if item["login"] not in credited]
    if timeline:
        tail_start, tail_dur, _ = timeline[-1]
        cursor = max([tail_start + LEAD_IN] + [b_end + TAIL_OUT for b_start, b_end in busy
                                               if b_end > tail_start])
        # A contributor whose Guardian identity is authored (ensemble.titles in
        # vocab/casting.yaml) is never reduced to a name line on the card while
        # the cut still has room for the real plate: they get first claim on
        # the tail the card was about to occupy -- but not at the price of
        # pushing anyone else off the card, since dropping a contributor is the
        # one unacceptable outcome. When the tail cannot hold both, the card
        # credits everyone and the authored plate waits for a cut with room.
        from tools.derive import load_ensemble_titles
        titled = load_ensemble_titles()

        def card_waiting(extra_credited=()):
            seen, waiting = set(), []
            for item in pending:
                if (item["login"] not in seen and item["login"] not in credited
                        and item["login"] not in extra_credited):
                    seen.add(item["login"])
                    waiting.append(item)
            return waiting

        def card_names(extra_credited=()):
            return [item["display_name"] for item in card_waiting(extra_credited)]

        def tail_room(at_cursor):
            return min(tail_start + tail_dur - TAIL_OUT - at_cursor,
                       MAX_ROSTER_HOLD)

        for item in pending:
            if item["login"] in credited or item["login"] not in titled:
                continue
            window = _first_free_window(tail_start, tail_dur, hold, total, busy, cursor)
            if not window:
                continue  # no room for the real plate; the card carries them
            at, dur = window
            would_cursor = at + dur + TAIL_OUT
            rest = card_names(extra_credited={item["login"]})
            if rest and tail_room(would_cursor) < MIN_HOLD <= tail_room(cursor):
                continue  # plating them would strand the rest off the card
            cursor = would_cursor
            entries.append(_ensemble_entry(item, at, dur, ensemble_copy))
            busy.append((at, at + dur))
            credited.add(item["login"])
            if log:
                log(f"  {'ensemble':<10} {at:6.2f}s +{dur:.1f}s  "
                    f"{item['display_name']} (authored plate)")
        remaining = tail_room(cursor)
        waiting = card_waiting()
        names = [item["display_name"] for item in waiting]
        if remaining >= MIN_HOLD:
            card = {
                "id": "ensemble_roster", "at": round(cursor, 3),
                "dur": round(remaining, 3), "position": "right", "kind": "title",
                "copy_source": "casting",
                "title": ensemble_copy["roster_title"],
                "subtitle": f"Project Bluefin contributors, {result['month']}",
            }
            if names:
                card["body"] = names
            entries.append(card)
            if log:
                log(f"  {'sign-off':<10} {cursor:6.2f}s +{remaining:.1f}s  "
                    f"{', '.join(names) if names else '(everyone credited in the cut)'}")
        elif names:
            # Even the tail had no room: every name the cut could not credit
            # goes on the punch-list, not just into a log line nobody reads.
            if unresolved is not None:
                for item in waiting:
                    unresolved.append({
                        "id": f"ensemble_{item['login']}",
                        "person": item["login"],
                        "display_name": item["display_name"],
                        **UNPLATED["no_window"],
                    })
            if log:
                log(f"  UNCREDITED (no room in the cut): {', '.join(names)}")
        elif log:
            log("  NO SIGN-OFF: the tail has no room for the card")

    return sorted(entries, key=lambda e: e["at"])


def _placeholder_entries(timeline, total, wanted, copy, hold, free, busy, log=None):
    """Blueberry plates: the first ``wanted`` ensemble shots that can hold one.

    A placeholder credits nobody, so there is no assignment to be deterministic
    about — it just proves the plate lands, reads, and clears before the next
    one, on a cut whose cast is not decided yet.
    """
    if not copy:
        from tools.derive import load_placeholder_plate

        copy = load_placeholder_plate()
    if not copy:
        raise ValueError("no ensemble.placeholder_plate copy in vocab/casting.yaml")

    entries = []
    for start, duration, shot in timeline:
        if len(entries) >= wanted:
            break
        if (shot.get("casting") or {}).get("role") != "ensemble":
            continue
        window = _window(start, duration, hold, room=total - start)
        if not window or not free(*window):
            continue
        at, dur = window
        entries.append({"id": f"ensemble_placeholder_{len(entries) + 1:02d}",
                        "at": at, "dur": dur, "position": "right", **copy})
        busy.append((at, at + dur))
        if log:
            log(f"  {'placeholder':<10} {at:6.2f}s +{dur:.1f}s  {copy.get('name')}")
    if log and len(entries) < wanted:
        log(f"  only {len(entries)}/{wanted} placeholder(s) fit — the rest of the "
            f"ensemble shots are too short or already busy")
    return entries


def load_manifest(path):
    with Path(path).open(encoding="utf-8") as fh:
        entries = json.load(fh)
    if isinstance(entries, dict):
        entries = entries["plates"]
    return load_manifest_entries(entries)


def load_manifest_entries(entries):
    """Validate plate entries: unique ids, real durations, one plate at a time."""
    seen, windows = set(), []
    for e in entries:
        if e["id"] in seen:
            raise ValueError(f"duplicate plate id {e['id']!r}")
        seen.add(e["id"])
        if float(e["dur"]) <= 0:
            raise ValueError(f"plate {e['id']!r} has non-positive dur")
        start = float(e["at"])
        windows.append((start, start + float(e["dur"]), e["id"],
                        e.get("group")))

    # One plate at a time (authoring-interview-chat-plates): overlapping visible
    # windows are a bug, not a style choice. One narrow exception: members of
    # the same group row share a `group` key and are one row by construction --
    # the reference deck's roll call is *meant* to be visible together. A group
    # member overlapping anything outside its own row is still an error, so the
    # check is pairwise rather than the old adjacent-pair scan (an exempt pair
    # must not shield a later collider behind it).
    ordered = sorted(windows)
    for i, (a_start, a_end, a_id, a_group) in enumerate(ordered):
        for b_start, b_end, b_id, b_group in ordered[i + 1:]:
            if b_start >= a_end:
                break
            if a_group and a_group == b_group:
                continue
            raise ValueError(
                f"plates {a_id!r} and {b_id!r} are visible at the same time "
                f"({b_start:.2f}s < {a_end:.2f}s)"
            )
    return entries


def render_all(entries, out_dir, picture=None):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for e in entries:
        dest = out_dir / f"plate_{e['id']}.png"
        place(render_plate(e), e.get("position", "left"), picture,
              x=e.get("x"), scale=float(e.get("scale", 1.0))).save(dest)
        written.append(dest)
    return written


def burn(video, entries, plates_dir, out_path, ffmpeg=None):
    """Composite every plate onto ``video`` in one ffmpeg pass.

    Audio is stream-copied: this stage titles a cut, it does not re-cut it, and
    re-encoding audio here would be a second generation for no reason.
    """
    if ffmpeg is None:
        from tools.render import find_ffmpeg

        ffmpeg = find_ffmpeg()
    video = Path(video).resolve()
    out_path = Path(out_path).resolve()
    plates_dir = Path(plates_dir).resolve()

    cmd = [*ffmpeg, "-nostdin", "-y", "-i", str(video)]
    for e in entries:
        cmd += ["-i", str(plates_dir / f"plate_{e['id']}.png")]

    steps, last = [], "0:v"
    for i, e in enumerate(entries, start=1):
        start = float(e["at"])
        end = start + float(e["dur"])
        label = f"v{i}"
        steps.append(
            f"[{last}][{i}:v]overlay=0:0:enable='between(t,{start:.3f},{end:.3f})'[{label}]"
        )
        last = label
    if not steps:
        raise ValueError("no plates to burn")

    cmd += [
        "-filter_complex", ";".join(steps),
        "-map", f"[{last}]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "copy",
        str(out_path),
    ]
    print("ffmpeg:", " ".join(ffmpeg))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
        raise RuntimeError(f"plate burn failed:\n{tail}")
    return out_path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render and burn Guardian nameplates.")
    sub = parser.add_subparsers(dest="command", required=True)

    r = sub.add_parser("render", help="manifest -> transparent PNG per plate")
    r.add_argument("--manifest", required=True)
    r.add_argument("--out-dir", default=str(REPO_ROOT / "renders" / "plates"))
    r.add_argument("--fit-video", default=None,
                   help="keep plates on the picture of this letterboxed video "
                        "instead of the raw 16:9 frame")

    b = sub.add_parser("burn", help="composite rendered plates onto a cut")
    b.add_argument("--video", required=True)
    b.add_argument("--manifest", required=True)
    b.add_argument("--plates-dir", default=str(REPO_ROOT / "renders" / "plates"))
    b.add_argument("--out", required=True)
    b.add_argument("--fit-picture", action="store_true",
                   help="re-render the plates onto the video's picture area first, "
                        "so nothing sits on a letterbox bar")

    p = sub.add_parser("plan", help="cut list (+ roster) -> timed plate manifest")
    p.add_argument("shotlist", help="JSON shot list from tools/story.py --format json")
    who = p.add_mutually_exclusive_group()
    who.add_argument("--roster", default=None, help="roster.json from tools/ensemble.py")
    who.add_argument("--placeholders", type=int, default=0, metavar="N",
                     help="plate N ensemble shots with the uncast blueberry copy "
                          "from vocab/casting.yaml, for a cut with no roster yet")
    p.add_argument("--max-shot-sec", type=float, default=None,
                   help="the same hold cap render.py was given, so timings line up")
    p.add_argument("--hold", type=float, default=DEFAULT_HOLD)
    p.add_argument("--around", default=None,
                   help="a manifest of already-fixed windows (e.g. dialogue) that "
                        "the plates must not collide with")
    p.add_argument("--prefer-clear-of", default=None,
                   help="a manifest (e.g. a dialogue pre-pass) that plates should "
                        "avoid if they can, but may overlap rather than be dropped")
    p.add_argument("--only", choices=("all", "leads", "ensemble"), default="all",
                   help="plan one tier at a time, so a scored cut can be planned "
                        "in priority order: leads, then dialogue, then ensemble")
    p.add_argument("--brief", default=None,
                   help="issue number or brief YAML file: the brief's plates[] "
                        "are planned first as fixed, owner-timed credits (see "
                        "docs/skills/plates.md). Lead-tier: with --only ensemble "
                        "they are expected via --around, like dialogue")
    p.add_argument("--out", required=True)

    m = sub.add_parser("merge", help="combine planned manifests into one, validated")
    m.add_argument("manifests", nargs="+")
    m.add_argument("--out", required=True)

    args = parser.parse_args(argv)

    if args.command == "merge":
        entries = []
        for path in args.manifests:
            entries.extend(load_manifest(path))
        entries.sort(key=lambda e: float(e["at"]))
        load_manifest_entries(entries)  # rejects overlaps across the whole deck
        with Path(args.out).open("w", encoding="utf-8") as fh:
            json.dump(entries, fh, indent=2)
            fh.write("\n")
        print(f"wrote {args.out} ({len(entries)} plate(s))")
        return 0

    if args.command == "plan":
        from tools.derive import load_leads
        from tools.render import load_shots

        roster = None
        if args.roster:
            with Path(args.roster).open(encoding="utf-8") as fh:
                roster = json.load(fh)
        busy = []
        if args.around:
            busy = [(float(e["at"]), float(e["at"]) + float(e["dur"]))
                    for e in load_manifest(args.around)]
        soft = []
        if args.prefer_clear_of:
            soft = [(float(e["at"]), float(e["at"]) + float(e["dur"]))
                    for e in load_manifest(args.prefer_clear_of)]
        brief = None
        if args.brief:
            from tools.brief import (BriefError, fetch_issue, has_block,
                                     parse_brief, parse_issue_body)
            try:
                if args.brief.isdigit():
                    brief = parse_issue_body(
                        fetch_issue(int(args.brief)).get("body"))
                else:
                    text = Path(args.brief).read_text(encoding="utf-8")
                    brief = (parse_issue_body(text) if has_block(text)
                             else parse_brief(text))
            except BriefError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 2
        unresolved = []
        entries = plan(load_shots(args.shotlist), load_leads(), roster,
                       max_shot_sec=args.max_shot_sec, hold=args.hold, log=print,
                       busy=busy, only=args.only, soft_busy=soft, brief=brief,
                       placeholders=args.placeholders, unresolved=unresolved)
        load_manifest_entries(entries)  # same validation the burn path applies
        with Path(args.out).open("w", encoding="utf-8") as fh:
            json.dump({"plates": entries, "unresolved": unresolved}, fh, indent=2)
            fh.write("\n")
        print(f"wrote {args.out} ({len(entries)} plate(s), "
              f"{len(unresolved)} unresolved)")
        return 0

    entries = load_manifest(args.manifest)

    if args.command == "render":
        picture = None
        if args.fit_video:
            from tools.render import detect_picture

            picture = detect_picture(args.fit_video)
            if picture:
                print(f"picture area: {picture[2]}x{picture[3]} at "
                      f"+{picture[0]}+{picture[1]}")
        written = render_all(entries, args.out_dir, picture)
        for path in written:
            print(f"wrote {path}")
        return 0

    picture = None
    if getattr(args, "fit_picture", False):
        from tools.render import detect_picture

        picture = detect_picture(args.video)
    render_all(entries, args.plates_dir, picture)
    out = burn(args.video, entries, args.plates_dir, args.out)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
