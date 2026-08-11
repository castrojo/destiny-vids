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
     "label": "TRUSTEE // GUARDIAN", "class": "Dawnblade Warlock",
     "name": "Bob Killen", "title": "Reconciler of the Plane", "trustee": true}

The four text fields plus ``trustee`` are exactly the vocabulary of the
reference deck (``~/Videos/nameplates.json``); nothing is invented on top of it.

``kind: "ghost"`` drops the class line (a Ghost is not a Guardian, so a subclass
would be nonsense on it) and shrinks the plate. ``kind: "title"`` is the deck's
other card -- ``title`` / ``subtitle`` / ``body`` -- used here to credit the
month's ensemble.

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

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FRAME_W, FRAME_H = 1920, 1080

# The site sizes everything in rem. 1rem = 16px reproduces the desktop layout
# at 1080p, which is what these plates are composited over.
REM = 16.0

# --- palette (WolvesIntroOverlay.vue) ---------------------------------------
INK = (8, 12, 20, 209)          # background: rgb(8 12 20 / 82%)
CREST_FILL = (8, 12, 20, 242)   # .wolves-guardian-plate-crest-inner
TEXT = (245, 245, 245, 255)     # .wolves-guardian-plate-name color
NAME_BOTTOM = (160, 174, 192, 255)   # name gradient tail (#a0aec0)

# Default (blue) chrome vs the burnished-silver trustee treatment.
VARIANTS = {
    "default": {
        "border": (147, 197, 253, 115),   # rgb(147 197 253 / 45%)
        "accent": (147, 197, 253, 255),   # #93c5fd
        "label": (147, 197, 253, 255),
        "klass": (191, 219, 254, 255),    # #bfdbfe
        "title": (148, 163, 184, 255),    # #94a3b8
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
        # The leader block overrides the label and the title but NOT
        # .wolves-guardian-plate-class, so the subclass row stays the default
        # blue even on the gold plate. Christoph Blecker's "Broodweaver Warlock"
        # renders exactly this way in the wolves trailer.
        "klass": (191, 219, 254, 255),    # #bfdbfe
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

PAD_X = 2.0 * REM        # padding: 1.75rem 2rem 1.5rem
PAD_TOP = 1.75 * REM
PAD_BOTTOM = 1.5 * REM
CHAMFER = 16             # clip-path: polygon(16px ...)
CREST = 2.5 * REM        # .wolves-guardian-plate-crest

# The CSS caps the plate at 44rem and lets the browser wrap. Only the chat card
# carries copy long enough to need it, so it is the only shape that wraps.
MAX_INNER_W = 44 * REM

# Row placement: bottom 10%, left/right 5% (.wolves-guardian-plate-row).
MARGIN_X = 0.05
MARGIN_BOTTOM = 0.10

FONT_CANDIDATES = {
    "regular": [
        "/usr/share/fonts/Adwaita/AdwaitaMono-Regular.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/liberation-fonts/LiberationMono-Regular.ttf",
    ],
    "bold": [
        "/usr/share/fonts/Adwaita/AdwaitaMono-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono-Bold.ttf",
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


def _wrap(text, font, max_width):
    """Greedy word wrap to ``max_width``, mirroring the CSS 44rem cap.

    A word longer than the line box is left over-long rather than broken: the
    copy is recovered dialogue, and hyphenating it would put characters on
    screen that nobody said.
    """
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    lines, current = [], ""
    for word in (text or "").split():
        trial = f"{current} {word}".strip()
        if current and probe.textlength(trial, font=font) > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def _gradient_text(size, text, font, top, bottom):
    """The name's white -> slate vertical gradient (background-clip: text)."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).text((0, 0), text, font=font, fill=255)
    grad = Image.new("RGBA", size)
    for y in range(size[1]):
        t = y / max(1, size[1] - 1)
        grad.paste(
            tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(4)),
            (0, y, size[0], y + 1),
        )
    layer.paste(grad, (0, 0), mask)
    return layer


def _chamfered(size, fill, border, radius=CHAMFER):
    """The plate box: clipped top-left and bottom-right corners, 1px rule."""
    w, h = size
    points = [(radius, 0), (w - 1, 0), (w - 1, h - 1 - radius),
              (w - 1 - radius, h - 1), (0, h - 1), (0, radius)]
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(img).polygon(points, fill=fill, outline=border)
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
    conversation without a plate line anybody had to invent.
    """
    variant = _variant_for(spec)
    ghost = spec.get("kind") == "ghost"
    card = spec.get("kind") == "title"
    chat = spec.get("kind") == "chat"
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
    elif chat:
        # The chat card names the PERSON speaking and shows what they said.
        # It deliberately carries no character row: who plays whom is
        # established by the Guardian reveal, not restated on every line.
        label = (spec.get("speaker") or "").upper()
        klass, name, title = "", "", ""
        body = _wrap(spec.get("text") or "", f_class, MAX_INNER_W)
    else:
        label = (spec.get("label") or "").upper()
        klass = "" if ghost else (spec.get("class") or "").upper()
        name = spec.get("name") or ""
        title = spec.get("title") or ""
        body = []

    widths = [
        _tracked_width(probe, label, f_label, LS_LABEL),
        _tracked_width(probe, klass, f_class, LS_CLASS),
        probe.textlength(name, font=f_name),
        probe.textlength(title, font=f_title),
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
    draw = ImageDraw.Draw(img)

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
                               (255, 255, 255, 255), NAME_BOTTOM)
        img.alpha_composite(layer, (int(cx - w / 2), int(y)))
        y += f_name.size * 1.25 + gap

    if title:
        w = draw.textlength(title, font=f_title)
        draw.text((cx - w / 2, y), title, font=f_title, fill=variant["title"])
        y += f_title.size * 1.25 + gap

    # The title card's body copy: one authored line per row.
    for line in body:
        w = draw.textlength(line, font=f_class)
        draw.text((cx - w / 2, y), line, font=f_class, fill=variant["klass"])
        y += f_class.size * 1.25 + gap

    return img


def place(plate, position="left", picture=None):
    """Composite a plate onto a full 1920x1080 transparent frame.

    ``picture`` is the real image area ``(x, y, w, h)`` inside the frame. The
    row margins are measured against *it*, not the frame, so on a letterboxed
    2.39:1 cinematic the plate sits on the picture instead of hanging onto the
    black bar. Defaults to the whole frame.
    """
    frame = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    px, py, pw, ph = picture or (0, 0, FRAME_W, FRAME_H)
    y = py + int(ph * (1 - MARGIN_BOTTOM)) - plate.height
    if position == "right":
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


def plan(shots, leads, roster=None, max_shot_sec=None, hold=DEFAULT_HOLD, log=None,
         busy=None, only="all", soft_busy=None):
    """Cut list -> plate manifest.

    Leads are plated on their first appearance long enough to read, using the
    `plate:` copy in vocab/casting.yaml. Ensemble contributors are plated from
    the deterministic assignment in tools/ensemble.py; anyone whose assigned
    shot is too short to hold a plate is credited over the final shot instead,
    so the month's contributors are never silently dropped.

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
    """
    timeline = cut_timeline(shots, max_shot_sec)
    total = sum(duration for _, duration, _ in timeline)
    entries, plated = [], set()
    busy = list(busy or [])  # occupied windows, so nothing double-books the screen
    soft_busy = list(soft_busy or [])

    def free(start, duration):
        end = start + duration
        return all(end <= b_start or start >= b_end for b_start, b_end in busy)

    def place_leads(avoid):
        for start, duration, shot in timeline:
            casting = shot.get("casting") or {}
            character = casting.get("character")
            if casting.get("role") != "lead" or not character or character in plated:
                continue
            if not casting.get("usable", True):
                continue  # a shot failing its binding's constraints is no reveal
            copy = (leads.get(character) or {}).get("plate")
            if not copy:
                continue
            # Walk forward through the shot: if dialogue (or an earlier plate)
            # holds its head, the reveal waits for the next opening inside its
            # own anchor rather than being lost for the whole cut.
            window = _first_free_window(start, duration, hold, total, avoid)
            if not window:
                continue
            at, dur = window
            entries.append({"id": character, "at": at, "dur": dur,
                            "position": "left", **copy})
            busy.append((at, at + dur))
            plated.add(character)
            if log:
                note = " (clear of dialogue)" if avoid is not busy else ""
                log(f"  {character:<10} {at:6.2f}s +{dur:.1f}s  "
                    f"{copy.get('name')}{note}")

    if only != "ensemble":
        # Preferred: a reveal that does not land on top of a line of dialogue.
        if soft_busy:
            place_leads(busy + soft_busy)
        # Fallback: a reveal that costs a line still beats no reveal at all.
        place_leads(busy)

    if not roster or only == "leads":
        return sorted(entries, key=lambda e: e["at"])

    from tools.ensemble import assign

    result = assign(roster, [s for _, _, s in timeline])
    by_segment = {}
    for item in result["assignments"]:
        by_segment.setdefault(item["segment_id"], []).append(item)

    credited, pending = set(), []
    for start, duration, shot in timeline:
        # A shot with several ensemble slots credits several people, one after
        # another rather than all at its head: the plate rides across the cut,
        # so a six-Guardian firefight can name six contributors instead of
        # burning five of them onto the roster card for want of a start time.
        cursor = start
        for item in by_segment.get(shot.get("segment_id"), []):
            if item["login"] in credited:
                continue
            window = _first_free_window(start, duration, hold, total, busy, cursor)
            if not window:
                pending.append(item)
                continue
            at, dur = window
            cursor = at + dur + TAIL_OUT
            entries.append({
                "id": f"ensemble_{item['login']}", "at": at, "dur": dur,
                "position": "right", "label": "CONTRIBUTOR // GUARDIAN",
                "name": item["display_name"],
                "title": f"Project Bluefin, {result['month']}",
            })
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
            entries.append({
                "id": f"ensemble_{item['login']}", "at": at, "dur": dur,
                "position": "right", "label": "CONTRIBUTOR // GUARDIAN",
                "name": item["display_name"],
                "title": f"Project Bluefin, {result['month']}",
            })
            busy.append((at, at + dur))
            credited.add(item["login"])
            placed = True
            if log:
                log(f"  {'ensemble':<10} {at:6.2f}s +{dur:.1f}s  "
                    f"{item['display_name']} (re-homed)")
            break
        if not placed:
            still_pending.append(item)

    # Whoever the body of the cut could not hold is credited together on one
    # roster plate over the tail, in rotation order. The month's contributors
    # are the ensemble; dropping them silently would be the one unacceptable
    # outcome.
    pending = [item for item in still_pending if item["login"] not in credited]
    if pending and timeline:
        tail_start, tail_dur, _ = timeline[-1]
        cursor = max([tail_start + LEAD_IN] + [b_end + TAIL_OUT for b_start, b_end in busy
                                               if b_end > tail_start])
        remaining = min(tail_start + tail_dur - TAIL_OUT - cursor, MAX_ROSTER_HOLD)
        seen, names = set(), []
        for item in pending:
            if item["login"] not in seen:
                seen.add(item["login"])
                names.append(item["display_name"])
        if remaining >= MIN_HOLD:
            entries.append({
                "id": "ensemble_roster", "at": round(cursor, 3),
                "dur": round(remaining, 3), "position": "right", "kind": "title",
                "title": "The Ensemble",
                "subtitle": f"Project Bluefin contributors, {result['month']}",
                "body": names,
            })
            credited.update(seen)
            if log:
                log(f"  {'roster':<10} {cursor:6.2f}s +{remaining:.1f}s  "
                    f"{', '.join(names)}")
        elif log:
            log(f"  UNCREDITED (no room in the cut): {', '.join(names)}")

    return sorted(entries, key=lambda e: e["at"])


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
        windows.append((start, start + float(e["dur"]), e["id"]))

    # One plate at a time (authoring-interview-chat-plates): overlapping visible
    # windows are a bug, not a style choice.
    for (a_start, a_end, a_id), (b_start, b_end, b_id) in zip(
            sorted(windows), sorted(windows)[1:]):
        if b_start < a_end:
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
        place(render_plate(e), e.get("position", "left"), picture).save(dest)
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
    p.add_argument("--roster", default=None, help="roster.json from tools/ensemble.py")
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
        entries = plan(load_shots(args.shotlist), load_leads(), roster,
                       max_shot_sec=args.max_shot_sec, hold=args.hold, log=print,
                       busy=busy, only=args.only, soft_busy=soft)
        load_manifest_entries(entries)  # same validation the burn path applies
        with Path(args.out).open("w", encoding="utf-8") as fh:
            json.dump(entries, fh, indent=2)
            fh.write("\n")
        print(f"wrote {args.out} ({len(entries)} plate(s))")
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
