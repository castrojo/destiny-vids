#!/usr/bin/env python3
"""Render the PROJECT BLUEFIN font options over the frame they will live on.

    python3 scripts/build_font_options.py

Owner, 2026-08-16: *"the Project Bluefin is a tad too thin on the font, give me
some options, the title itself is perfect"*.

Five variants of the eyebrow -- and only the eyebrow -- are rendered from
``stories/font-options.json`` by ``cards/render-cards.mjs``, then composited
over the SOURCE FRAME THE CARD ACTUALLY SITS ON. That last part is the point of
this script existing at all: the prologue's title is not on black, it is over
Nightwish's picture at 15.400 s, and a weight that looks solid on a swatch can
disappear over moving footage. `docs/skills/plates/SKILL.md` has the scar --
"the prologue's main title was cued over a near-black void and the source cut
to a white starburst 1.3 s later, inside the same card".

15.400 is not a round number either: it is ``build_prologue.STAGE_SWAP``, the
frame where the credit rows appear, so every option is judged on the busiest
version of the card.

The options are also stacked into one contact sheet, because five separate PNGs
make a viewer compare from memory.

Nothing here is a deliverable. It renders to ``renders/font-options/`` and
copies to ``~/Videos/Wolves/font-options/`` so the owner can flick through
them; no committed value changes until they pick one.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import footage  # noqa: E402
from tools.render import find_ffmpeg  # noqa: E402

MANIFEST = REPO_ROOT / "stories" / "font-options.json"
OUT_DIR = REPO_ROOT / "renders" / "font-options"
DELIVER = Path.home() / "Videos" / "Wolves" / "font-options"

SOURCE_ID = "yt_nightwish_perfume_of_the_timeless"
# The frame the card is judged on: build_prologue.STAGE_SWAP.
AT = 15.400
# The source is 1920x804 scope and the prologue pads it into 1080; the card is
# composited over the PADDED frame, so the still has to be padded the same way
# or the type would be measured against a picture 138 px taller than the one it
# ships over.
PAD_Y = (1080 - 804) // 2


def render_cards():
    node_modules = REPO_ROOT / "node_modules"
    if not node_modules.exists():
        website = Path.home() / "src" / "website" / "node_modules"
        if not website.exists():
            sys.exit("playwright is not vendored here; point node_modules at a "
                     "checkout that has it (~/src/website/node_modules)")
        node_modules.symlink_to(website)
    subprocess.run(
        ["node", str(REPO_ROOT / "cards" / "render-cards.mjs"),
         "--manifest", str(MANIFEST), "--out-dir", str(OUT_DIR)],
        cwd=REPO_ROOT, check=True)


def backdrop(source, dest):
    """The one source frame, padded into the delivery frame."""
    subprocess.run(find_ffmpeg() + [
        "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{AT:.3f}", "-i", str(source), "-frames:v", "1",
        "-vf", f"pad=1920:1080:0:{PAD_Y}:color=black",
        str(dest)], check=True)


def composite(backdrop_png, card_png, dest):
    subprocess.run(find_ffmpeg() + [
        "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(backdrop_png), "-i", str(card_png),
        "-filter_complex", "[0:v][1:v]overlay=0:0",
        "-frames:v", "1", str(dest)], check=True)


def contact_sheet(shots, dest):
    """All five, stacked, so they are compared side by side and not from memory.

    Cropped to the lockup's own band rather than shown whole: the difference
    between these options is a few hundred pixels of one line, and five full
    frames stacked would be five thousand pixels of picture around it.

    LABELS ARE ONE CHARACTER, and that is not laziness. `drawtext`'s value is
    parsed out of the filtergraph string, so a comma or a colon inside it ends
    the option early -- the first pass wrote the variants' prose notes in here
    and ffmpeg rejected the whole graph. The prose lives in
    stories/font-options.json, which is where it can carry punctuation safely.
    """
    args = find_ffmpeg() + ["-hide_banner", "-loglevel", "error", "-y"]
    for shot in shots:
        args += ["-i", str(shot)]
    crops = "".join(f"[{i}:v]crop=1920:300:0:330,"
                    f"drawtext=text='{label}':x=44:y=20:fontsize=54:"
                    f"fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=14"
                    f"[c{i}];"
                    for i, label in enumerate(shots.values()))
    stack = "".join(f"[c{i}]" for i in range(len(shots)))
    args += ["-filter_complex",
             f"{crops}{stack}vstack=inputs={len(shots)}[out]",
             "-map", "[out]", "-frames:v", "1", str(dest)]
    subprocess.run(args, check=True)


def main():
    source = footage.resolve(SOURCE_ID)
    if not source or not source.exists():
        sys.exit(f"footage is never committed; {SOURCE_ID} is not on this host")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    render_cards()

    back = OUT_DIR / "backdrop.png"
    backdrop(source, back)

    manifest = json.loads(MANIFEST.read_text())
    shots = {}
    for plate in manifest["plates"]:
        card = OUT_DIR / f"plate_{plate['id']}.png"
        dest = OUT_DIR / f"{plate['id']}.png"
        composite(back, card, dest)
        shots[dest] = plate["id"].split("-")[-1].upper()

    sheet = OUT_DIR / "font-options-contact-sheet.png"
    contact_sheet(shots, sheet)

    DELIVER.mkdir(parents=True, exist_ok=True)
    delivered = []
    for path in list(shots) + [sheet]:
        shutil.copy2(path, DELIVER / path.name)
        delivered.append(str(DELIVER / path.name))

    print(json.dumps({"frame_sec": AT, "delivered": delivered}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
