#!/usr/bin/env python3
"""The RAFI hero overlay: one card, in the right margin, drawn from the record.

The encode composites this over the finished picture. It is a full-frame RGBA
PNG that is transparent everywhere except the card, so the filter graph needs
one `overlay=0:0` and no arithmetic of its own -- the arithmetic lives here,
where a test can pin it.

    python3 scripts/build_rafi_hero_overlay.py --video rafi01 \
        --out renders/rafi01-overlay.png

The record carries one `videos` map keyed by video id (rafi01, rafi02), each
with its own `character` block -- the sources are different widths and the
character's tight crop is measured per video. `--video` defaults to rafi01 so
every existing call site keeps working unchanged.

WHERE THE MARGIN COMES FROM. RAFI_01's character is cropped to 1759x1862 out
of its source and scaled to 1224 tall, so it lands 1156 wide and centred:
x 702..1858. The right margin is what is left, 1858..2560, and the card sits
in it. Change the character's height in the record and the card follows,
because the margin is derived and not typed in.

    python3 -m pytest tests/test_rafi_hero_overlay.py -q
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts import qrcard as qr  # noqa: E402
from tools import plate as plate_mod  # noqa: E402  (the house mono)

RECORD = REPO / "stories" / "rafi-hero-qr.json"


def load(record=RECORD):
    return json.loads(Path(record).read_text(encoding="utf-8"))


def character(doc, video="rafi01"):
    """The per-video character block out of the record's `videos` map."""
    try:
        return doc["videos"][video]["character"]
    except KeyError:
        known = ", ".join(sorted(doc.get("videos", {}))) or "none"
        raise KeyError(
            f"no character block for video {video!r} (record knows: {known})"
        ) from None


def even(value):
    """ffmpeg's `scale=-2:H` rounds the derived width to an even number."""
    return int(round(value / 2)) * 2


def character_box(doc, video="rafi01"):
    """(x0, x1) of the scaled character on the frame. Pure: the tests pin it."""
    frame = doc["frame"]["width"]
    char = character(doc, video)
    width = even(char["crop_w"] * char["height"] / char["crop_h"])
    x0 = (frame - width) // 2
    return x0, x0 + width


def card_box(doc, spec, video="rafi01"):
    """(x, y) of one card's top-left corner.

    A corner, not a centre. The archers card was vertically centred in the
    margin first, which never overlapped the character and still competed with
    him because it sat at his eye level -- owner: "why are you blocking art?".
    `margin` is the gap to the frame edges.
    """
    frame_w = doc["frame"]["width"]
    frame_h = doc["frame"]["height"]
    place = doc["placement"]
    card_w = place["width"]
    card_h = int(round(card_w * (1 + qr.STRIP_FRAC)))
    margin = place.get("margin", 48)

    x = margin if spec.get("side", "right") == "left" else frame_w - margin - card_w

    valign = place.get("valign", "bottom")
    if valign == "bottom":
        y = frame_h - margin - card_h
    elif valign == "top":
        y = margin
    else:
        y = (frame_h - card_h) // 2

    left, right = character_box(doc, video)
    if x < right and x + card_w > left:
        raise RuntimeError(
            f"the {spec['id']} card (x {x}..{x + card_w}) would sit over the "
            f"character (x {left}..{right}); shrink the card or the character")
    return x, y


def static_cards(doc, video):
    """Persistent cards, using a video's override when its record supplies one."""
    return doc["videos"][video].get("cards", doc["cards"])


def track_cards(doc, video):
    """Validated, frame-addressable cards for a video's fixed playlist."""
    cards = doc["videos"][video].get("track_cards", [])
    if not cards:
        return []

    required = ("id", "start_frame", "end_frame", "url", "name")
    for spec in cards:
        missing = [key for key in required if key not in spec]
        if missing:
            raise ValueError(f"track card {spec.get('id', '<unknown>')!r} is missing "
                             f"{', '.join(missing)}")
        if spec["start_frame"] < 0 or spec["end_frame"] <= spec["start_frame"]:
            raise ValueError(f"track card {spec['id']!r} has an invalid frame range")
        if not spec["url"].startswith("https://"):
            raise ValueError(f"track card {spec['id']!r} needs an HTTPS URL")

    if cards[0]["start_frame"] != 0:
        raise ValueError("the first track card must start on frame zero")
    for left, right in zip(cards, cards[1:]):
        if left["end_frame"] != right["start_frame"]:
            raise ValueError("track card intervals must be contiguous")
    return cards


def render_card(doc, spec):
    """Build one decode-gated card at the record's exact in-frame width."""
    width = doc["placement"]["width"]
    art = qr.card(width, spec["url"], style=spec.get("style", "slate"),
                  eyebrow=spec.get("eyebrow"), name=spec["name"])
    if not (qr.decodes(art, spec["url"], qr.DAY_PLATE)
            and qr.decodes(art, spec["url"], qr.NIGHT_PLATE)):
        raise RuntimeError(
            f"the {spec['id']} card does not scan at {width}px; "
            f"see scripts/qrcard.py")
    return art


def build_track_cards(doc, video):
    """Return decode-gated card images in playback order for one video."""
    return [(spec, render_card(doc, spec)) for spec in track_cards(doc, video)]


def wordmark_box(doc, img):
    """(x, y) of the URL wordmark, sat on the same baseline as the cards.

    The wordmark is TEXT, not a code. It was built as a QR twice before the
    instruction -- "add wolves.projectbluefin.io bottom left as a URL" -- was
    read properly.
    """
    place = doc["placement"]
    margin = place.get("margin", 48)
    card_h = int(round(place["width"] * (1 + qr.STRIP_FRAC)))
    frame_w = doc["frame"]["width"]
    frame_h = doc["frame"]["height"]

    x = margin if doc["wordmark"]["side"] == "left" else \
        frame_w - margin - img.width
    # Bottom-aligned with the cards, so the corner furniture shares a baseline.
    y = frame_h - margin - card_h + card_h - img.height
    return x, y


def draw_wordmark(doc, height=44):
    """`wolves.projectbluefin.io` in white, with the dots in the brand blue."""
    text = doc["wordmark"]["text"]
    font = plate_mod._font("bold", height)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    tracking = 0.06
    width = plate_mod._tracked_width(probe, text, font, tracking)

    img = Image.new("RGBA", (int(width) + 4, int(height * 1.6)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 0.0
    extra = tracking * font.size
    for ch in text:
        # The dots are the only blue thing in it -- the separators, picked out
        # the way the site picks them out.
        d.text((x, 0), ch, font=font,
               fill=(*qr.BLUEFIN, 255) if ch == "." else (255, 255, 255, 255))
        x += probe.textlength(ch, font=font) + extra
    return img


def build(doc=None, video="rafi01"):
    """The full-frame overlay, transparent but for the corner furniture."""
    doc = doc or load()
    frame = (doc["frame"]["width"], doc["frame"]["height"])
    out = Image.new("RGBA", frame, (0, 0, 0, 0))
    width = doc["placement"]["width"]

    if "wordmark" in doc:
        mark = draw_wordmark(doc)
        out.alpha_composite(mark, wordmark_box(doc, mark))

    # A timed playlist owns RAFI_02's right card; the static overlay carries
    # only the persistent wordmark. Other videos use their recorded static card.
    if not track_cards(doc, video):
        for spec in static_cards(doc, video):
            out.alpha_composite(render_card(doc, spec), card_box(doc, spec, video))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--record", default=str(RECORD))
    ap.add_argument("--video", default="rafi01",
                    help="key into the record's videos map (default rafi01)")
    ap.add_argument("--out", default=None,
                    help="default renders/<video>-overlay.png")
    ap.add_argument("--cards-dir", default=None,
                    help="write timed track cards here when the video has them")
    args = ap.parse_args(argv)

    doc = load(args.record)
    out = Path(args.out or f"renders/{args.video}-overlay.png")
    if not out.is_absolute():
        out = REPO / out

    img = build(doc, video=args.video)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)

    if args.cards_dir:
        cards_dir = Path(args.cards_dir)
        if not cards_dir.is_absolute():
            cards_dir = REPO / cards_dir
        cards_dir.mkdir(parents=True, exist_ok=True)
        for spec, art in build_track_cards(doc, args.video):
            art.save(cards_dir / f"{spec['id']}.png")

    left, right = character_box(doc, args.video)
    print(f"wrote {out} ({img.width}x{img.height})")
    print(f"  character  x {left}..{right}  ({right - left} wide, "
          f"{character(doc, args.video)['height']} tall)")
    if track_cards(doc, args.video):
        for spec in track_cards(doc, args.video):
            x, y = card_box(doc, spec, args.video)
            print(f"  {spec['id']:<28} frames {spec['start_frame']}.."
                  f"{spec['end_frame'] - 1}  x {x}.."
                  f"{x + doc['placement']['width']}  y {y}  ({spec['url']})")
    else:
        for spec in static_cards(doc, args.video):
            x, y = card_box(doc, spec, args.video)
            print(f"  {spec['id']:<8} x {x}..{x + doc['placement']['width']}  "
                  f"y {y}  ({spec['style']}, {spec['url']})")
    print(f"  every card decodes at {doc['placement']['width']}px on both "
          f"wallpapers, or this would have raised")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
