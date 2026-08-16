#!/usr/bin/env python3
"""Build TRAILER 1 from its record.

    python3 scripts/build_trailer1.py --print-command   # the ffmpeg call, no render
    python3 scripts/build_trailer1.py --cards           # re-render the card PNGs
    python3 scripts/build_trailer1.py                   # the master

What this is
------------
A promotional cut derived from the PROLOGUE, at the owner's request: *"Now make
a new video: Trailer 1 - make a copy of this video and then ..."*. It is **not**
a ninth act. It takes no numeral, no chapter marker and no entry in
``stories/megacut/megacut.json``; the programme is unchanged by it.

Everything it shares with ``scripts/build_prologue.py`` it shares by taking the
same measured constants -- the burst, the out point, the title cues -- because
those were read off the file with ``ffprobe`` once and re-measuring them here
would only give two answers to the same question.

The four departures from the prologue
-------------------------------------
1. **The tank is cut.** Owner: *"you can even go to :36 actually and skip the
   shot of the tank and go right to the iguana again"*. Scene detection on the
   source puts the book at 24.880, the empty specimen jar at 33.640 and the
   iguana at 36.320, so ``CUT_OUT``/``CUT_IN`` excise the jar and the two
   halves are joined with a short dissolve.

   **The audio is not cut there.** The song runs continuously, so the music
   carries over the picture edit rather than announcing it -- which means
   picture and sound run ``GAP`` seconds apart for the rest of the film. Every
   constant below is in FILM time; ``source_at()`` converts.

2. **Two owner lines over the book**, seated on the printed lyric they replace
   and walked along its drift. See ``stories/trailer-1-plates.json``.

3. **A longer, more dramatic wolves fade.** Owner: *"make the wolves fade
   longer and more dramatic"*. The bridge goes 10.000 -> 14.000, and the four
   extra seconds are spent on the TURN and the SINK rather than the holds --
   the sun takes longer to go down and the night takes longer to take the
   frame. Lengthening the holds would have made it longer without making it
   more dramatic.

4. **A KubeCon end card**, and the music plays out under it. Owner: *"Let the
   music play out longer than the original video, look up how long movie
   trailers should be given the things we have"*. The MPA and NATO cap a
   theatrical trailer at **2:30**; teasers run 0:30-1:30. The owner set the
   target at **1:50**, which is where this lands, exactly.

The arithmetic
--------------
::

    picture 0.000  -> 33.640      33.640
    picture 36.320 -> 91.200      54.880   (the tank excised)
                                  ------
                                  88.520
    wolves bridge                 14.000
    end card                       7.500
                                  ------
                                 110.020   = 1:50.0
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
from tools import footage  # noqa: E402
from tools.render import find_ffmpeg  # noqa: E402

MANIFEST = REPO_ROOT / "stories" / "trailer-1-plates.json"
SOURCE_ID = "yt_nightwish_perfume_of_the_timeless"
SOURCE = footage.resolve(SOURCE_ID) or REPO_ROOT / "media" / f"{SOURCE_ID}.mkv"
PLATES_DIR = REPO_ROOT / "renders" / "plates-trailer-1"
OUT = REPO_ROOT / "renders" / "trailer-1.mp4"
DELIVER = Path.home() / "Videos" / "Wolves" / "trailer-1.mp4"

# --- the picture, in SOURCE seconds -------------------------------------------
# Taken from build_prologue, which measured them.
OUT_POINT = 91.200          # the luma minimum at the end of the borrowed span
BURST = 12.200              # the explosion the picture blooms out of
TITLE_IN = 2.000
TITLE_FADE = 1.400
STAGE_SWAP = 15.400
TITLE_OUT = 22.600

# THE TANK. Detected with `select='gt(scene,0.20)'` on the source: 24.880 (the
# book), 33.640 (the jar), 36.320 (the iguana), 40.720 (underwater). The owner
# named ":36" and the shot boundary is 36.320, so the join is put on the cut
# rather than a fifth of a second inside the previous shot.
CUT_OUT = 33.640
CUT_IN = 36.320
GAP = CUT_IN - CUT_OUT                                 # 2.680
# Long enough not to read as a dropped frame, short enough not to read as a
# dissolve. The book's last frame is bright page and the iguana's first is a
# dark close-up, so there is plenty of contrast across it.
JOIN_FADE = 0.320

# The join COSTS runtime: xfade emits d1 + d2 - duration, so the dissolve eats
# JOIN_FADE out of the picture rather than sitting between the halves for free.
# Counting it here is the difference between a 110.020 s film and a 109.700 s
# film with 0.320 s of frozen tail, because `-t` would still be asking for the
# longer one.
PICTURE = CUT_OUT + (OUT_POINT - CUT_IN) - JOIN_FADE   # 88.200

# --- the bridge, in bridge seconds --------------------------------------------
# The prologue's 10.000 s bridge, given four more seconds -- all of them to the
# turn and the sink.
BRIDGE_UP = 1.400           # black -> day        (prologue: 1.400)
BRIDGE_DAY_HOLD = 1.000     #                     (prologue: 1.200)
BRIDGE_TURN = 4.400         # day -> night        (prologue: 2.600)
BRIDGE_NIGHT_HOLD = 1.400   #                     (prologue: 1.600)
BRIDGE_DOWN = 5.800         # night -> black      (prologue: 3.200)
BRIDGE = (BRIDGE_UP + BRIDGE_DAY_HOLD + BRIDGE_TURN
          + BRIDGE_NIGHT_HOLD + BRIDGE_DOWN)           # 14.000
# The underwater-to-day handoff needs a beat of clear daylight before the
# wolves start sinking. The rest of the 14-second bridge is the one long fade.
BRIDGE_DAY_SETTLE = 4.000
BRIDGE_MONTH = 3            # the owner named 03-bluefin-day.jxl

# --- the end card -------------------------------------------------------------
# 7.820 rather than a round 7.500: the end card is where the 0.320 s the join
# dissolve spends is given back, so the delivered runtime is exactly the
# owner's 1:50.0 instead of 1:49.7.
ENDCARD = 7.820
ENDCARD_FADE = 1.200
# The existing music tail is loud on entry, falls from roughly -18 to -19.6 dB
# RMS through 1-3 s, then rises back to -17.4 dB at 3-4 s. The visual does not
# change the mix: it lets the day image breathe on the opening hit, darkens
# through the musical breath, brings the event in during that turn, and lands
# the CTA as the energy returns.
ENDCARD_DAY_HOLD = 0.800
ENDCARD_DARKEN = 2.400
ENDCARD_EVENT_IN = 1.200
ENDCARD_EVENT_FADE = 1.100
ENDCARD_CTA_IN = 3.100
ENDCARD_CTA_FADE = 0.600

TOTAL = PICTURE + BRIDGE + ENDCARD                     # 110.020

# --- sound --------------------------------------------------------------------
# The prologue fades from 93.000, under a bridge that ends its film. This one
# has an end card after the bridge and the owner asked for the music to play
# out longer, so the fade is the LAST few seconds of the whole thing and the
# song is still going when the venue card arrives.
AUDIO_FADE = 5.000
AUDIO_FADE_START = TOTAL - AUDIO_FADE                  # 105.020

# The prologue's opening level ride, kept verbatim: it is a measured fix for a
# real complaint ("tone down the spark noise at the beginning of the song so my
# ears don't explode"), not prologue dressing.
RIDE_START_DB = -12.0
RIDE_TO = 15.000

FPS = conform.DELIVERY.fps
W, H = conform.DELIVERY.width, conform.DELIVERY.height
PAD_Y = (H - 804) // 2      # the source is 1920x804 scope


def source_at(film_t):
    """Film seconds -> source seconds, across the excised tank."""
    return film_t if film_t <= CUT_OUT else film_t + GAP


def load():
    return json.loads(MANIFEST.read_text())


def plate(manifest, plate_id):
    for entry in manifest["plates"]:
        if entry["id"] == plate_id:
            return entry
    raise KeyError(plate_id)


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
         "--manifest", str(MANIFEST), "--out-dir", str(PLATES_DIR)],
        cwd=REPO_ROOT, check=True)


def wallpaper(variant):
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import fetch_wallpapers

    return fetch_wallpapers.cached(BRIDGE_MONTH, variant)


def _still(source, label, extra=""):
    """A PNG as a stream on the film's own clock, BOUNDED to the film.

    ``loop=loop=-1`` is an INFINITE stream and ``overlay``'s framesync will
    happily keep running once the main input ends, repeating its last frame --
    the prologue's first build emitted its film and then eight seconds of
    frozen final frame, and ffmpeg exited 0. Every still here is trimmed.

    ``source`` is normally an input index, but the day wallpaper is split
    before it serves the bridge and the end-card's two poster legs. ffmpeg
    documents `split` as the way one input feeds more than one filter branch;
    referencing `[5:v]` independently made the graph work by accident rather
    than stating that contract. Source: Context7 `/websites/ffmpeg_documentation`,
    "Split input streams".
    """
    stream = f"[{source}:v]" if isinstance(source, int) else f"[{source}]"
    return (f"{stream}format=rgba,loop=loop=-1:size=1:start=0,"
            f"fps={FPS},setpts=N/({FPS})/TB{extra}[{label}]")


def _walk(a, b, at, dur):
    """An `overlay` coordinate expression that walks from ``a`` to ``b``.

    The card is a full 1920x1080 canvas with the line in its middle, so the
    overlay offset is the anchor's displacement from frame centre rather than
    the anchor itself -- which is why these read as differences.

    Clamped at both ends with `min`/`max` so the expression is still correct on
    the frames either side of the window; `enable=` gates the drawing, but a
    coordinate that keeps extrapolating is a coordinate somebody will one day
    widen a window onto and find has flown off frame. The clamp is also what
    lets a line KEEP TRACKING the page for part of its life and then hold: pass
    a ``dur`` shorter than the beat and the walk finishes early.
    """
    span = max(dur, 1e-6)
    return (f"({a:.1f})+(({b:.1f})-({a:.1f}))*"
            f"max(0\\,min(1\\,(t-{at:.3f})/{span:.3f}))")


def filtergraph(manifest):
    # --- the picture ---------------------------------------------------------
    # PADDED rather than scaled: the source already carries the delivery width
    # at native pixels, so 138 px of black top and bottom seats it in 16:9
    # without resampling one of them.
    #
    # THE GATE. `fade=t=in:st=X` holds every frame before X fully black, so one
    # filter both blacks out the void and lets the burst bloom out of it.
    head = (f"[0:v]trim=0:{CUT_OUT:.3f},setpts=PTS-STARTPTS,"
            f"pad={W}:{H}:0:{PAD_Y}:color=black,setsar=1,fps={FPS},"
            f"fade=t=in:st={BURST:.3f}:d={2 * 1001 / 60000:.4f},"
            f"format=rgba[head]")
    tail = (f"[0:v]trim={CUT_IN:.3f}:{OUT_POINT:.3f},setpts=PTS-STARTPTS,"
            f"pad={W}:{H}:0:{PAD_Y}:color=black,setsar=1,fps={FPS},"
            f"format=rgba[tail]")
    # xfade's output runs d1 + d2 - duration, so the join costs JOIN_FADE of
    # runtime; PICTURE is the sum of the two trims and the offset is set so the
    # dissolve straddles the cut rather than following it.
    join = (f"[head][tail]xfade=transition=fade:duration={JOIN_FADE:.3f}:"
            f"offset={CUT_OUT - JOIN_FADE:.3f},format=rgba[film]")

    parts = [head, tail, join]
    # Input 0 is the source; every card and wallpaper below takes the next
    # index in the order `command()` passes them. The first build had this
    # counter starting at 1, which fed the SECOND title card into the first
    # overlay and asked for an input that did not exist.
    inputs = 0
    last = "film"

    # --- the main title, two staged cards ------------------------------------
    a = plate(manifest, "maintitle-a")
    b = plate(manifest, "maintitle-b")
    parts.append(_still(inputs + 1, "ta",
                        f",trim=0:{PICTURE:.3f},setpts=PTS-STARTPTS,"
                        f"fade=t=in:st={TITLE_IN:.3f}:d={TITLE_FADE}:alpha=1"))
    parts.append(f"[{last}][ta]overlay=0:0:shortest=1:"
                 f"enable=between(t\\,{TITLE_IN:.3f}\\,{STAGE_SWAP:.3f})[v1]")
    parts.append(_still(inputs + 2, "tb",
                        f",trim=0:{PICTURE:.3f},setpts=PTS-STARTPTS,"
                        f"fade=t=out:st={TITLE_OUT - TITLE_FADE:.3f}:"
                        f"d={TITLE_FADE}:alpha=1"))
    parts.append(f"[v1][tb]overlay=0:0:shortest=1:"
                 f"enable=between(t\\,{STAGE_SWAP:.3f}\\,{TITLE_OUT:.3f})[v2]")
    inputs += 2
    last = "v2"

    # --- the two book lines --------------------------------------------------
    # `enable=between(t\,a\,b)` with ESCAPED commas, not the quoted form the
    # docs show: tools/plate.py records a build that failed to parse the quoted
    # spelling, disabled the overlay and still exited 0 -- a silent no-op.
    for n, entry_id in enumerate(("book-a", "book-b")):
        entry = plate(manifest, entry_id)
        at, dur = entry["at"], entry["dur"]
        fade = min(0.45, dur / 4)
        idx = inputs + 1
        parts.append(_still(idx, f"bk{n}",
                            f",trim=0:{PICTURE:.3f},setpts=PTS-STARTPTS,"
                            f"fade=t=in:st={at:.3f}:d={fade:.3f}:alpha=1,"
                            f"fade=t=out:st={at + dur - fade:.3f}:"
                            f"d={fade:.3f}:alpha=1"))
        ax, ay = entry["anchor"]
        bx, by = entry["anchor_out"]
        # A line may track the page for less time than it is on screen: book-b
        # rides the book, then the picture cuts to the iguana under it and
        # there is no longer a page to track, so it holds.
        walk = entry.get("walk", dur)
        x = _walk(ax - W / 2, bx - W / 2, at, walk)
        y = _walk(ay - H / 2, by - H / 2, at, walk)
        out = f"v{3 + n}"
        parts.append(f"[{last}][bk{n}]overlay=x='{x}':y='{y}':shortest=1:"
                     f"enable=between(t\\,{at:.3f}\\,{at + dur:.3f})[{out}]")
        inputs += 1
        last = out

    parts.append(f"[{last}]format=yuv420p[picture]")

    # --- the bridge ----------------------------------------------------------
    day_len = BRIDGE_UP + BRIDGE_DAY_HOLD + BRIDGE_TURN
    night_len = BRIDGE - day_len + BRIDGE_TURN
    day_input = inputs + 1
    parts.append(f"[{inputs + 2}:v]split=2[bridgenightsrc][endnightsrc]")
    parts.append(_still(day_input, "day",
                        f",trim=0:{BRIDGE:.3f},setpts=PTS-STARTPTS,"
                        f"format=yuv420p"))
    parts.append(_still("bridgenightsrc", "bridgenight",
                        f",trim=0:{BRIDGE - BRIDGE_DAY_SETTLE:.3f},"
                        f"setpts=PTS-STARTPTS,"
                        f"format=yuv420p"))
    # One continuous fade: bright day wolves settle into the original night
    # wolves. The end card reuses that same night art, so no black reset or
    # colour jump interrupts the climax.
    parts.append(f"[day][bridgenight]xfade=transition=fade:"
                 f"duration={BRIDGE - BRIDGE_DAY_SETTLE:.3f}:"
                 f"offset={BRIDGE_DAY_SETTLE:.3f}[bridgepre]")
    parts.append(_still(9, "daycard",
                        f",trim=0:{BRIDGE:.3f},setpts=PTS-STARTPTS,"
                        "fade=t=in:st=0.600:d=0.400:alpha=1,"
                        "fade=t=out:st=3.600:d=0.400:alpha=1"))
    parts.append("[bridgepre][daycard]overlay=0:0:shortest=1:"
                 "enable=between(t\\,0.600\\,4.000)[bridge]")
    inputs += 2

    # --- the end card, day falling into dark ---------------------------------
    # Owner, 2026-08-16: "start the wallpaper at day and then as it fades into
    # dark bring in the text". Input 5 is already the March day wallpaper for
    # the bridge, and ffmpeg permits it to feed both end-card legs as well --
    # no duplicate input, no second asset choice.
    #
    # The bridge and the card share the original night image: the handoff is
    # one continuous wolves fade and the event text remains legible.
    parts.append(_still("endnightsrc", "endnight",
                        f",trim=0:{ENDCARD:.3f},setpts=PTS-STARTPTS,"
                        f"format=yuv420p"))
    parts.append("[endnight]null[endbg]")

    # The event and venue enter midway through the daylight-to-dark transition.
    # The CTA is a second transparent card: it hides the repeated event rows
    # and arrives at the music's returning swell, not at the same time.
    parts.append(_still(inputs + 1, "ecevent",
                        f",trim=0:{ENDCARD:.3f},setpts=PTS-STARTPTS,"
                        f"fade=t=in:st={ENDCARD_EVENT_IN:.3f}:"
                        f"d={ENDCARD_EVENT_FADE:.3f}:alpha=1,"
                        f"fade=t=out:st={ENDCARD - ENDCARD_FADE:.3f}:"
                        f"d={ENDCARD_FADE:.3f}:alpha=1"))
    parts.append("[endbg][ecevent]overlay=0:0:shortest=1[endv1]")
    parts.append(_still(inputs + 2, "eccta",
                        f",trim=0:{ENDCARD:.3f},setpts=PTS-STARTPTS,"
                        f"fade=t=in:st={ENDCARD_CTA_IN:.3f}:"
                        f"d={ENDCARD_CTA_FADE:.3f}:alpha=1,"
                        f"fade=t=out:st={ENDCARD - ENDCARD_FADE:.3f}:"
                        f"d={ENDCARD_FADE:.3f}:alpha=1"))
    parts.append("[endv1][eccta]overlay=0:0:shortest=1,"
                 "format=yuv420p[endcard]")
    inputs += 2

    parts.append("[picture][bridge][endcard]concat=n=3:v=1:a=0[vout]")

    # --- sound ---------------------------------------------------------------
    # The ride, as an evaluated `volume` expression: level automation, which is
    # a mix decision, rather than a dynamics filter, which would be a rewrite
    # of what Nightwish mastered.
    ride = (f"volume=eval=frame:volume="
            f"'if(lt(t,{RIDE_TO:.3f}),"
            f"pow(10,({RIDE_START_DB:.1f}*(1-pow(t/{RIDE_TO:.3f},2)))/20),1)'")
    parts.append(f"[0:a]atrim=0:{TOTAL:.3f},asetpts=PTS-STARTPTS,"
                 f"afade=t=in:st=4.000:d=1.000,{ride},"
                 f"afade=t=out:st={AUDIO_FADE_START:.3f}:"
                 f"d={AUDIO_FADE:.3f},aresample=48000[aout]")

    return ";".join(parts)


def command(manifest, day_png, night_png):
    return find_ffmpeg() + [
        "-hide_banner", "-y",
        "-i", str(SOURCE),
        "-i", str(PLATES_DIR / "plate_maintitle-a.png"),
        "-i", str(PLATES_DIR / "plate_maintitle-b.png"),
        "-i", str(PLATES_DIR / "plate_book-a.png"),
        "-i", str(PLATES_DIR / "plate_book-b.png"),
        "-i", str(day_png),
        "-i", str(night_png),
        "-i", str(PLATES_DIR / "plate_endcard-event.png"),
        "-i", str(PLATES_DIR / "plate_endcard-cta.png"),
        "-i", str(PLATES_DIR / "plate_daytime-kindness.png"),
        "-filter_complex", filtergraph(manifest),
        "-map", "[vout]", "-map", "[aout]",
        *conform.video_encode_args(),
        "-c:a", "flac", "-sample_fmt", "s32",
        "-t", f"{TOTAL:.3f}",
        "-movflags", "+faststart",
        str(OUT),
    ]


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--print-command", action="store_true",
                    help="print the ffmpeg call and exit")
    ap.add_argument("--cards", action="store_true",
                    help="re-render the card PNGs first")
    ap.add_argument("--no-deliver", action="store_true",
                    help="render to renders/ without copying to ~/Videos")
    args = ap.parse_args(argv)

    manifest = load()

    if not SOURCE.exists():
        sys.exit(f"footage is never committed; missing: {SOURCE}")

    if args.cards or not (PLATES_DIR / "plate_endcard-cta.png").exists():
        render_cards()

    day, night = wallpaper("day"), wallpaper("night")
    if not (day and night):
        sys.exit(f"month {BRIDGE_MONTH:02d}'s wallpaper pair is not installed "
                 f"on this host; the bridge has no picture.")

    argv_ff = command(manifest, day, night)
    if args.print_command:
        print(" ".join(argv_ff))
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(argv_ff, check=True)

    delivered = None
    if not args.no_deliver:
        # ~/Videos is a Syncthing folder and a directory can vanish mid-session.
        DELIVER.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(OUT, DELIVER)
        delivered = str(DELIVER)

    print(json.dumps({
        "out": str(OUT),
        "delivered": delivered,
        "duration": round(TOTAL, 3),
        "picture": round(PICTURE, 3),
        "bridge": BRIDGE,
        "end_card": ENDCARD,
        "excised": [CUT_OUT, CUT_IN],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
