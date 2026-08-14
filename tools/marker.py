#!/usr/bin/env python3
"""Black marker cards for a timing pass.

A timing pass does not remove the material it is going to remove. It **blacks
it out in place**, at exactly its original duration, with a card saying what is
going to happen there. The picture stays legible against the music, so the cut
can be judged before a single frame is actually taken out -- see
``docs/skills/editing/SKILL.md``, "Mark, don't cut".

Two kinds, and the distinction is the whole point:

    COMIC PLACEHOLDER   a slot artwork will be dropped into later
    REMOVE -- <reason>  this is coming out; it is here so the timing reads

These are **production markers, not credits**. They deliberately share nothing
with ``tools/plate.py``'s chrome beyond the font: a marker must never be
mistakable for a finished nameplate, and it carries no claim about any person.
Nothing here writes on-screen copy about a real human being, so none of the
nameplate vocabulary rules apply -- and none of its shapes are reused either.

    python3 tools/marker.py "COMIC PLACEHOLDER" --sub "4:34 enemy CU" \
        --out renders/markers/comic.png
"""
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

from PIL import Image, ImageDraw

from tools.plate import _draw_tracked, _font, _tracked_width

REPO_ROOT = Path(__file__).resolve().parents[1]

# Markers are build artifacts, not committed records: renders/ is gitignored.
DEFAULT_DIR = REPO_ROOT / "renders" / "markers"

W, H = 1920, 1080
FS_TEXT = 64
FS_SUB = 30
TRACKING = 0.22          # wide, so it reads as a slate rather than a title
INK = (236, 240, 245, 255)
SUB_INK = (140, 150, 162, 255)
RULE = (70, 78, 88, 255)


def slug(text):
    """A stable filename for a marker, so a rebuild reuses the same card."""
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    return f"{base or 'marker'}-{digest}"


def render_marker(text, sub=None):
    """A black frame with one centred line, and an optional smaller line under.

    Full-frame and fully opaque: this *replaces* the picture for its duration
    rather than overlaying it, which is what keeps the timing honest -- the
    marked span is exactly as long as the material it stands in for.
    """
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    f_text = _font("bold", FS_TEXT)
    label = text.upper()
    tw = _tracked_width(draw, label, f_text, TRACKING)
    y = H / 2 - FS_TEXT
    _draw_tracked(draw, ((W - tw) / 2, y), label, f_text, INK, TRACKING)

    rule_y = y + FS_TEXT * 1.7
    draw.line([(W / 2 - tw / 2, rule_y), (W / 2 + tw / 2, rule_y)],
              fill=RULE, width=2)

    if sub:
        f_sub = _font("regular", FS_SUB)
        sw = _tracked_width(draw, sub, f_sub, 0.06)
        _draw_tracked(draw, ((W - sw) / 2, rule_y + FS_SUB), sub, f_sub,
                      SUB_INK, 0.06)
    return img


def marker_path(text, sub=None):
    """Render ``text`` to a cached PNG and return its path.

    Cached on (text, sub) so a builder can ask for the same marker in a loop
    without re-rendering it, and so a rebuild is byte-identical.
    """
    out_dir = DEFAULT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{slug(text + '|' + (sub or ''))}.png"
    if not path.exists():
        render_marker(text, sub).save(path)
    return path


def title_card_path(title, subtitle=None, body=None):
    """The opening title card, as a full-frame still the cut can concatenate.

    The card itself is ``tools/plate.py``'s existing ``kind: "title"`` shape --
    the deck's ``title`` / ``subtitle`` / ``body`` and nothing else -- composited
    onto black so it can stand in the timeline as a shot rather than being
    burned over one. This is what blacks out the source's own logo: the picture
    underneath is not dimmed, it is simply not there.
    """
    from tools.plate import render_plate

    out_dir = DEFAULT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    key = "|".join([title, subtitle or "", *(body or [])])
    path = out_dir / f"title-{slug(key)}.png"
    if path.exists():
        return path

    spec = {"kind": "title", "title": title}
    if subtitle:
        spec["subtitle"] = subtitle
    if body:
        spec["body"] = list(body)
    card = render_plate(spec)

    frame = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    frame.alpha_composite(card, ((W - card.width) // 2, (H - card.height) // 2))
    frame.save(path)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text", help="the marker's headline, e.g. COMIC PLACEHOLDER")
    ap.add_argument("--sub", default=None, help="smaller second line")
    ap.add_argument("--out", default=None, help="output PNG (default: cached)")
    args = ap.parse_args(argv)

    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        render_marker(args.text, args.sub).save(path)
    else:
        path = marker_path(args.text, args.sub)
    print(path)
    return 0


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(REPO_ROOT))
    raise SystemExit(main())
