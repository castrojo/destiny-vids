#!/usr/bin/env python3
"""Render act VI's interruption slides from their manifest (issue #104).

Input:  ``stories/06-wolves-interruption-cards.json`` -- owner-authored copy,
        reproduced verbatim; never invent or silently correct a string.
Output: ``renders/interruption/<id>.png`` -- full-frame 1920x1080 stills,
        flattened onto OPAQUE BLACK. A card PNG that keeps its alpha and is
        then concatenated as a still is the megacut skill's standing red
        flag; these are the picture, not overlays.

Three shapes, all drawn with tools/plate.py's own components:

  * ``black``        -- the held beat of the realization (A); pure black.
  * ``title``        -- the Ambassadors' slide (B); the owner-authored line as
                        a title card, centred. The CNCF mark is NOT on it
                        (rights -- see the manifest's _rights).
  * ``introduction`` -- "Introducing ..." above a Guardian plate (C). The
                        plate reproduces Cortney Nickerson's authored act-I
                        identity verbatim, class row omitted as there (#90).

Offline: Pillow only, no network, no footage. Re-runs are byte-identical.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.plate import FRAME_H, FRAME_W, place, render_plate  # noqa: E402

MANIFEST = REPO / "stories" / "06-wolves-interruption-cards.json"
OUT_DIR = REPO / "renders" / "interruption"


def _flatten_black(card):
    """A tight RGBA card -> the full frame, centred, on opaque black."""
    frame = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 255))
    frame.alpha_composite(card, ((FRAME_W - card.width) // 2,
                                 (FRAME_H - card.height) // 2))
    return frame


def render_card(entry):
    """One manifest entry -> a full-frame opaque-black still."""
    shape = entry.get("shape")
    if shape == "black":
        return Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 255))
    if shape == "title":
        return _flatten_black(render_plate({"kind": "title",
                                            "title": entry["title"]}))
    if shape == "introduction":
        frame = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 255))
        intro = render_plate({"kind": "title", "title": entry["intro"]})
        # The framing line sits at the top-centre toast slot, shrunk so the
        # nameplate below it is unmistakably the thing being introduced.
        frame.alpha_composite(place(intro, "toast", scale=0.6))
        plate = dict(entry["plate"])
        frame.alpha_composite(
            place(render_plate(plate), plate.get("position", "left")))
        return frame
    raise ValueError(f"{entry.get('id')!r}: unknown interruption card shape "
                     f"{shape!r}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", default=str(MANIFEST))
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    args = ap.parse_args(argv)

    entries = json.loads(Path(args.manifest).read_text())["cards"]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ids = set()
    for entry in entries:
        if entry["id"] in ids:
            raise ValueError(f"duplicate interruption card id {entry['id']!r}")
        ids.add(entry["id"])
        if not entry.get("dur", 0) > 0:
            raise ValueError(f"{entry['id']!r}: an interruption card needs a "
                             "positive dur (act-film seconds)")
        dest = out_dir / f"{entry['id']}.png"
        render_card(entry).save(dest)
        print(f"  {entry['id']:14s} {entry['dur']:5.1f}s -> {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
