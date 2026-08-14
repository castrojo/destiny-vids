#!/usr/bin/env python3
"""Build the PROLOGUE -- the feature's main title sequence -- from its record.

    python3 scripts/build_prologue.py --print-command   # the ffmpeg call, no render
    python3 scripts/build_prologue.py --cards           # re-render the title PNGs
    python3 scripts/build_prologue.py                   # the master

What this act is
----------------
The owner chose Nightwish's official music video **"Perfume Of The Timeless"**
(``oHCaZmIzr0o``) to open the film. Its first 1:31 carries the main title at
0:11 and then hands into the programme. It is a **cold open in front of act I**
and it takes NO NUMERAL: ``AGENTS.md`` makes the eight act numerals
load-bearing, and inserting a ninth act at the front would move every chapter
marker, every ``Prod/NN-*.mp4`` name and every key in
``stories/megacut/delivery.json``. So it delivers as ``00-prologue`` and, like
act VIII, carries no slide and no chapter marker -- a card announcing the main
title sequence would step on the main title sequence.

Everything on screen is committed
---------------------------------
The copy is ``stories/00-prologue-plates.json`` (reproduced from the website's
own prologue cue, not authored here) and the cards are rendered from
``cards/maintitle.html`` by ``cards/render-cards.mjs``. **Footage is never
committed**: the source is read from gitignored ``media/`` and this script
reports what is missing rather than substituting anything.

The three measured numbers
--------------------------
None of these are the owner's timestamps taken on trust; each was read off the
actual file, and the exact commands are in ``docs/cuts/00-prologue.md``.

* **TITLE at 2.000, over black.** The owner: *"just show black at the beginning
  of the prologue but have the bluefin logo fade straight in ... it should be
  all black in the beginning then 'explode' into the burst behind the logo."*
  So the picture is **gated to black** until the burst and the lockup fades up
  from the top, alone, on nothing.
* **BURST at 12.200.** The source's void sits on a flat luma plateau -- 45.9,
  45.8, 46.0 across 12.08-12.16 -- and then departs it: 54.3 at 12.200, 62.5,
  103.2, and blown out at 195.9 by 12.320. 12.200 is the first frame that
  leaves the plateau, so cutting there lets the flare **bloom out of black**
  instead of popping in half-lit. `fade=t=in:st=` holds every frame before its
  start time fully black, which is the gate; verified on this host rather than
  assumed.
* **OUT at 91.200.** The owner said "stop at 1:31". The picture's mean luma
  falls from 46.9 at 88.8 s to a minimum of **30.0 at 91.2 s** and is climbing
  again by 91.4, so 1:31 sits one frame off a natural fade-to-black. The out
  point is moved to the actual minimum rather than the round number.
* **BRIDGE of 8.000.** The owner: *"put up a 03-bluefin-day.jxl and fade to the
  dark version so that that replaces the black part, make it seem like one
  movie"*. March's pair is the same drawing at two times of day -- pink sunset
  with a white sun, then blue night with a crescent moon and fireflies -- and
  in both of them the pack is closing on the herd. Crossfading one to the other
  is a sun going down over the hunt, immediately before a film called *Seven
  Days to the Wolves*. It is a turn, not a dissolve, so it is given 2.6 s.

The audio does not stop where the picture does
----------------------------------------------
The owner asked for source audio "faded out under the join". The song therefore
runs **past** the picture's out point, under the whole bridge, and fades there:
the music is what carries the viewer across a change of medium, and cutting it
at 91.2 would announce the seam this act exists to hide.

FLAC, from the plain Opus rung
------------------------------
Delivered audio is FLAC, decoded from format 251 -- **never** ``251-drc``,
which is dynamic-range compressed and forbidden by this repo's audio standard.
The source is lossy, so this is the best that exists rather than the best
possible, exactly as act I records for the same reason.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import conform  # noqa: E402
from tools.render import find_ffmpeg  # noqa: E402

MANIFEST = REPO_ROOT / "stories" / "00-prologue-plates.json"
SOURCE = REPO_ROOT / "media" / "yt_nightwish_perfume_of_the_timeless.mkv"
PLATES_DIR = REPO_ROOT / "renders" / "plates-00-prologue"
WALLPAPERS = REPO_ROOT / "renders" / "wallpapers"
OUT = REPO_ROOT / "renders" / "00-prologue.mp4"

# --- the measured timeline, in source seconds --------------------------------
OUT_POINT = 91.200          # the luma minimum; the owner's "1:31" is 91.0
BURST = 12.200              # the explosion, MEASURED -- see below
TITLE_IN = 2.000            # the logo fades in over black, from the top
TITLE_FADE = 1.400
STAGE_SWAP = 15.400         # hard cut A -> B: only the credit pair appears
TITLE_OUT = 22.600          # clear of the 24.88 cut
BRIDGE_MONTH = 3            # the owner named 03-bluefin-day.jxl

# --- the bridge, in bridge seconds -------------------------------------------
BRIDGE_UP = 1.400           # black -> day
BRIDGE_DAY_HOLD = 1.200
BRIDGE_TURN = 2.600         # day -> night, the sun going down
BRIDGE_NIGHT_HOLD = 1.600
BRIDGE_DOWN = 1.200         # night -> black, so act I's slide rises out of it
BRIDGE = (BRIDGE_UP + BRIDGE_DAY_HOLD + BRIDGE_TURN
          + BRIDGE_NIGHT_HOLD + BRIDGE_DOWN)          # 8.000

AUDIO_FADE_START = 93.000
TOTAL = OUT_POINT + BRIDGE                             # 99.200
AUDIO_FADE = TOTAL - AUDIO_FADE_START                  # 6.200

# --- the opening level ride ---------------------------------------------------
# The owner, on the first cut: "the sparks in the beginning of the video is
# jarring audio for the audience, tone them down the best you can", and then
# "just tone down the spark noise at the beginning of the song so my ears don't
# explode".
#
# MEASURED, on the built act. Across the first 13 s the sustained level sits at
# -13 to -18 dB RMS while the spark transients hit repeatedly at ~0 dBFS -- they
# stand 13 to 18 dB above the bed they arrive on. And the source is clipped
# before this build touches it: decoded samples reach +1.9 dBFS. That is
# Nightwish's master, and nothing here un-clips it.
#
# NOT A LIMITER, AND NOT A COMPRESSOR. The audio tenet forbids dynamics
# processing on finished music, because it rewrites the dynamics the artist
# chose -- and it is the wrong tool anyway: squashing these transients would
# dull the crackle into mush. The sanctioned lever is LEVEL. Every spark stays
# exactly as mixed; it simply does not arrive at the listener at full scale.
#
# THE SHAPE IS THE CUT'S. The picture is a dark void until the 12.28 shot change,
# so the ride reaches unity exactly there: the sparks are held down precisely
# where they live, and full level lands on the film's biggest visual event
# instead of on a black screen. Nothing after 12.28 is touched.
RIDE_START_DB = -12.0
RIDE_TO = 12.280

FPS = conform.DELIVERY.fps
W, H = conform.DELIVERY.width, conform.DELIVERY.height


def render_cards():
    """Render the two staged title PNGs with the site's own CSS in a browser."""
    node_modules = REPO_ROOT / "node_modules"
    if not node_modules.exists():
        website = Path.home() / "src" / "website" / "node_modules"
        if not website.exists():
            sys.exit("playwright is not vendored here; point node_modules at a "
                     "checkout that has it (~/src/website/node_modules)")
        node_modules.symlink_to(website)
    subprocess.run(
        ["node", str(REPO_ROOT / "cards" / "render-cards.mjs"),
         "--manifest", str(MANIFEST), "--out-dir", str(PLATES_DIR)],
        cwd=REPO_ROOT, check=True)


def wallpaper(variant):
    """One cached bridge frame, decoding it from the desktop's JPEG XL if new.

    Degrades rather than blocks: a month whose art is not installed on this
    host leaves the bridge without its picture, which is reported.
    """
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import fetch_wallpapers

    return fetch_wallpapers.cached(BRIDGE_MONTH, variant)


def _still(index, label, extra=""):
    """A PNG as a stream on the film's own clock, BOUNDED to the film.

    A PNG is a one-frame input; looping it and re-stamping PTS puts it on the
    same timeline as the picture, so every `st=`/`enable=` below can be written
    in FILM time rather than in an offset nobody can check against the cut.

    The `trim` is not decoration. ``loop=loop=-1`` makes the stream INFINITE,
    and ``overlay``'s framesync will happily keep running once the *main* input
    ends, repeating its last frame for as long as the secondary still has one.
    The first build of this act did exactly that: it emitted 91.2 s of film and
    then 8 s of frozen final frame, the bridge never played, and ffmpeg exited
    0. Bounding the still is what makes the overlay end when the picture does.
    """
    return (f"[{index}:v]format=rgba,loop=loop=-1:size=1:start=0,"
            f"fps={FPS},setpts=N/({FPS})/TB{extra}[{label}]")


def filtergraph():
    # The picture: trimmed, and PADDED rather than scaled. The source is
    # 1920x804 scope, so it already carries the delivery width at native
    # pixels; 138 px of black top and bottom seats it in 16:9 without
    # resampling a single one of them.
    #
    # THE GATE. `fade=t=in:st=X` holds every frame before X fully black -- it
    # is not only a ramp -- so one filter both blacks out the void and lets the
    # burst bloom out of it. The duration is two frames: long enough not to be
    # a hard-edged pop on the first bright pixel, short enough that this reads
    # as an explosion rather than a dissolve.
    film = (f"[0:v]trim=0:{OUT_POINT:.3f},setpts=PTS-STARTPTS,"
            f"pad={W}:{H}:0:{(H - 804) // 2}:color=black,setsar=1,"
            f"fps={FPS},fade=t=in:st={BURST:.3f}:d={2 * 1001 / 60000:.4f},"
            f"format=rgba[film]")

    # `enable=between(t\,a\,b)` with ESCAPED commas, not the quoted form the
    # docs show: tools/plate.py records a build that failed to parse the quoted
    # spelling, disabled the overlay and still exited 0 -- a silent no-op.
    title_a = _still(1, "ta",
                     f",trim=0:{OUT_POINT:.3f},setpts=PTS-STARTPTS,"
                     f"fade=t=in:st={TITLE_IN:.3f}:d={TITLE_FADE}:alpha=1")
    over_a = (f"[film][ta]overlay=0:0:shortest=1:"
              f"enable=between(t\\,{TITLE_IN:.3f}\\,{STAGE_SWAP:.3f})[v1]")
    title_b = _still(2, "tb",
                     f",trim=0:{OUT_POINT:.3f},setpts=PTS-STARTPTS,"
                     f"fade=t=out:st={TITLE_OUT - TITLE_FADE:.3f}:"
                     f"d={TITLE_FADE}:alpha=1")
    over_b = (f"[v1][tb]overlay=0:0:shortest=1:"
              f"enable=between(t\\,{STAGE_SWAP:.3f}\\,{TITLE_OUT:.3f})"
              f"[v2pre]")
    v2 = f"[v2pre]format=yuv420p[v2]"

    # The bridge. xfade's output runs d1 + d2 - duration, so the two legs are
    # sized to land the total exactly on BRIDGE rather than trusting a trim
    # after the fact.
    day_len = BRIDGE_UP + BRIDGE_DAY_HOLD + BRIDGE_TURN
    night_len = BRIDGE - day_len + BRIDGE_TURN
    day = _still(3, "day", f",trim=0:{day_len:.3f},setpts=PTS-STARTPTS,"
                           f"format=yuv420p")
    night = _still(4, "night", f",trim=0:{night_len:.3f},setpts=PTS-STARTPTS,"
                               f"format=yuv420p")
    turn = (f"[day][night]xfade=transition=fade:duration={BRIDGE_TURN:.3f}:"
            f"offset={BRIDGE_UP + BRIDGE_DAY_HOLD:.3f}[turned]")
    bridge = (f"[turned]fade=t=in:st=0:d={BRIDGE_UP:.3f},"
              f"fade=t=out:st={BRIDGE - BRIDGE_DOWN:.3f}:d={BRIDGE_DOWN:.3f}"
              f"[bridge]")

    join = "[v2][bridge]concat=n=2:v=1:a=0[vout]"

    # The ride, as an evaluated `volume` expression: level automation, which is
    # a mix decision, rather than a dynamics filter, which would be a rewrite.
    # gain(t) = RIDE_START_DB * (1 - (t/RIDE_TO)^2) dB -- it holds near the
    # start value through the spark-dense early seconds and opens up late, then
    # is exactly 0 dB from RIDE_TO onward.
    ride = (f"volume=eval=frame:volume="
            f"'if(lt(t,{RIDE_TO:.3f}),"
            f"pow(10,({RIDE_START_DB:.1f}*(1-pow(t/{RIDE_TO:.3f},2)))/20),1)'")

    audio = (f"[0:a]atrim=0:{TOTAL:.3f},asetpts=PTS-STARTPTS,{ride},"
             f"afade=t=out:st={AUDIO_FADE_START:.3f}:d={AUDIO_FADE:.3f},"
             f"aresample=48000[aout]")

    return ";".join([film, title_a, over_a, title_b, over_b, v2,
                     day, night, turn, bridge, join, audio])


def command(day_png, night_png):
    return find_ffmpeg() + [
        "-hide_banner", "-y",
        "-i", str(SOURCE),
        "-i", str(PLATES_DIR / "plate_maintitle-a.png"),
        "-i", str(PLATES_DIR / "plate_maintitle-b.png"),
        "-i", str(day_png),
        "-i", str(night_png),
        "-filter_complex", filtergraph(),
        "-map", "[vout]", "-map", "[aout]",
        *conform.video_encode_args(),
        "-c:a", "flac", "-sample_fmt", "s32",
        "-t", f"{TOTAL:.3f}",
        "-movflags", "+faststart",
        str(OUT),
    ]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--print-command", action="store_true",
                    help="print the ffmpeg call and exit")
    ap.add_argument("--cards", action="store_true",
                    help="re-render the title PNGs first")
    args = ap.parse_args(argv)

    missing = [p for p in (SOURCE,) if not p.exists()]
    if missing:
        sys.exit("footage is never committed; missing: "
                 + ", ".join(str(p) for p in missing))

    if args.cards or not (PLATES_DIR / "plate_maintitle-b.png").exists():
        render_cards()

    day, night = wallpaper("day"), wallpaper("night")
    if not (day and night):
        sys.exit(f"month {BRIDGE_MONTH:02d}'s wallpaper pair is not installed on "
                 f"this host; the bridge has no picture. Install the Bluefin "
                 f"backgrounds or choose another month.")

    argv_ff = command(day, night)
    if args.print_command:
        print(" ".join(argv_ff))
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(argv_ff, check=True)
    print(json.dumps({"out": str(OUT), "duration": round(TOTAL, 3),
                      "out_point": OUT_POINT, "bridge": BRIDGE}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
