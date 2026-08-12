#!/usr/bin/env python3
"""Build act II of the musical -- *Endless Forms Most Beautiful*.

This is NOT ``tools/story.py``. There is no matcher and no index lookup: the
owner gave the cut as timecodes on one source, and every span below was then
snapped to a **measured** shot boundary rather than to the round number.

THE SHAPE OF THIS ACT
---------------------
One source, four unbroken runs in source order, and one bed that plays end to
end. There is no excision in the song and no pause: the picture is fitted to
the music, never the other way round.

  Source  ``yt_destiny_all_live_action_trailers`` -- a FAN compilation, 376.1 s
  Bed     ``bed_endless_forms_most_beautiful``    -- Nightwish, 308.0 s

WHAT WAS REMOVED, AND WHY
-------------------------
Three kinds of material, all of it named by the owner:

1. **The framing narration.** The man reading to his son is live action about
   the fiction rather than inside it, and the owner asked for in-universe shots.
   The visor close-ups elsewhere are NOT this: an actor's eyes seen through a
   Guardian's helmet is in-universe, and they stay.
2. **The title cards** -- the "creators of Halo" slate, the DESTINY logo card
   and the black around it, and the TAKEN KING end slate. Removing the pair
   that bracket the moon makes the opening one continuous scene, which is the
   whole point of the act.
3. **The dance section.** 4:06 -> 4:50 is cut separately as its own video, so
   this act jumps it.

MEASURED, NOT GUESSED
---------------------
Boundaries come from ``ContentDetector(threshold=27)`` over the whole source
and from ``blackdetect`` for the black spans; the frames were reviewed on a
contact sheet before anything was cut. The owner's ``4:06`` and ``4:50`` are
rounded; the numbers below are the shot boundaries nearest them, and the
difference is recorded rather than silently absorbed.

THE ONE ARITHMETIC FACT THAT GOVERNS THE ACT
--------------------------------------------
Picture after removals is SHORTER than the song. That gap is asserted below,
not hidden: if an edit changes it, the assertion fails and somebody decides
again. How the gap is closed is the owner's call (``TAIL_POLICY``).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "yt_destiny_all_live_action_trailers"
BED_ID = "bed_endless_forms_most_beautiful"

# --- the cut ---------------------------------------------------------------
# (in, out, why this boundary is here). Source timecodes, seconds.
RUNS = [
    # The moon, part one: the cold open, out at the DISSOLVE into the man
    # reading -- not at the hard cut 2.45 s later. See REMOVED, first entry.
    (0.000, 4.017, "moon cold open; out on the last frame before the dissolve"),
    # The moon, continuous: back from the framing narration to the HALO slate.
    (22.033, 52.233, "moon battle, unbroken; out on the cut back to the reading"),
    # Become Legend and Evil's Most Wanted, minus the DESTINY card.
    (62.633, 174.433, "in off the HALO slate; out on the cut to the DESTINY card"),
    (180.533, 244.833, "in off the black after the card; out before BECOME LEGEND"),
    # The tail, split in two by the mech removal below.
    (289.467, 344.000, "owner's 4:50, snapped back to the shot boundary; out before the mech"),
    (345.767, 362.200, "in off the mech; out on the cut to the DESTINY logo card"),
]

REMOVED = [
    # THE OWNER'S ":12 - :14 human pic snuck in remove it".
    #
    # This one is why the file says MEASURED, NOT GUESSED. The moon does not
    # CUT to the man reading, it DISSOLVES into him, and a dissolve is invisible
    # to ContentDetector -- which is exactly how 2.45 s of live-action framing
    # narration survived a pass whose whole purpose was removing it. The
    # boundary below was found by stepping frames at 1/30 s and looking: the
    # last clean helmet frame is 4.017, and the man's face is bleeding through
    # by 4.05. Cutting at the hard cut (6.467) keeps the dissolve; cutting mid
    # dissolve keeps a ghost of him. So the out point is the last clean frame.
    (4.017, 6.467, "the dissolve into the man reading -- the owner's ':12-:14 human pic'"),
    (6.467, 22.033, "live action: the man reading to his son, and the book"),
    (52.233, 54.267, "live action: the reading, reprised"),
    (54.267, 62.633, "title card: from the creators of Halo"),
    (174.433, 179.167, "title card: DESTINY"),
    (179.167, 180.533, "black, measured by blackdetect"),
    (244.833, 246.100, "burned-in end title: BECOME LEGEND"),
    (246.100, 289.467, "the dance section -- cut separately as its own video"),
    # THE OWNER: "we might want to cut the big enemy with the flashing gun in
    # that scene so we can highlight the heroes instead, do that this is a
    # pivotal [beat] ... unless you think it's awesome already."
    #
    # Removed WHOLE rather than trimmed. It is a discrete 1.767 s shot between
    # two hard cuts, opening on the white blowout of the gun and resolving to
    # the machine posed at camera. Trimming it to half its length would make it
    # a flash-frame -- worse than either keeping or cutting it -- and removing
    # it needs no mid-shot trim and leaves no artifact. One line to restore.
    (344.000, 345.767, "the Cabal war machine and its flashing gun -- the heroes take the screen"),
    # THE PUBLISHER END CARDS. Every other title card in this act was removed,
    # including one named above as "burned-in end title: BECOME LEGEND"; these
    # survived only because run 5 used to run to the end of the source. The act
    # was closing on an advert. Owner: "cut to black, end on the heroes".
    (362.200, 376.134, "DESTINY / DESTINY 2 logo slates, Bungie/Activision copyright, 'AVAILABLE ON PC OCTOBER 24'"),
]

# The owner's rounded marks, kept beside the measured ones so the difference
# is visible rather than absorbed.
OWNER_MARKS = {"skip_from": 246.0, "resume_at": 290.0}

# What happens to the gap between picture and song.
#
# THIS IS NO LONGER A FREE CHOICE. It used to be: the picture was 8.564 s short
# of the song, `music_first` put the whole gap at the head as black, and the
# only question was taste. Two owner decisions changed that.
#
# 1. THE SYNC. The song breaks down at 258.0 and the full band re-enters at
#    269.700 -- an exact downbeat on the bed's own grid (beat index 683,
#    downbeat_phase 3, bar 1.578957 s). On screen at that moment is a Sentinel
#    Titan raising a Void shield, and in the delivered film it arrived roughly a
#    third of a second LATE. The owner approved moving picture to fix it.
#
#    So the head lead-in is now DERIVED FROM THE MUSIC: it is whatever value
#    puts SYNC_ANCHOR_SRC on SYNC_ANCHOR_FILM, and it is asserted below. Type a
#    number here and the shield drifts off the beat the next time a run moves.
#
# 2. THE END CARDS. Cutting 13.934 s of advert off the tail freed time that
#    cannot go to the head -- the head is now spoken for by the sync, and
#    lengthening it would slide every frame against the song. So the freed time
#    goes to the TAIL: black under the song's outro, after the act ends on the
#    cathedral. Owner: "cut to black, end on the heroes".
#
# The invariant that matters: HEAD + PICTURE + TAIL == SONG, with head and tail
# both derived and neither typed.
TAIL_POLICY = "sync_anchored"

# The frame the music is cut to, and the moment it must land on.
# Source 338.200 is the Sentinel's shield at full extension (verified by eye).
SYNC_ANCHOR_SRC = 338.200
SYNC_ANCHOR_FILM = 269.700

BED_LEAD_SEC = None  # derived below, from the anchor
BED_TAIL_SEC = None  # derived below, from the remainder


def load_json(path):
    with open(path) as fh:
        return json.load(fh)


def probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def fmt(seconds):
    m, s = divmod(float(seconds), 60)
    return f"{int(m)}:{s:06.3f}"


def build():
    bed = load_json(REPO_ROOT / "music" / f"{BED_ID}.json")
    bed_sec = float(bed["duration_sec"])
    source = REPO_ROOT / "media" / f"{SOURCE_ID}.mp4"
    src_sec = probe_duration(source) if source.exists() else 376.134

    # --- invariants --------------------------------------------------------
    # 1. The runs are in source order, disjoint, and inside the source.
    last = 0.0
    for a, b, _ in RUNS:
        assert a >= last, f"run {a} starts before the previous run ends"
        assert b > a, f"run {a}->{b} is empty or inverted"
        last = b
    assert last <= src_sec + 0.01, f"run runs past the source ({last} > {src_sec})"

    # 2. Runs and removals together account for EVERY FRAME OF THE SOURCE. A
    #    frame that is neither kept nor named as removed is a frame nobody
    #    decided about. This is now the whole source, not just the part before
    #    the last out point: the publisher end cards are a decision too, and
    #    naming them is what stops them drifting back in.
    spans = sorted([(a, b) for a, b, _ in RUNS] + [(a, b) for a, b, _ in REMOVED])
    cursor = 0.0
    for a, b in spans:
        assert abs(a - cursor) < 0.001, (
            f"gap or overlap at {fmt(cursor)}: next span starts {fmt(a)}")
        cursor = b
    assert abs(cursor - src_sec) < 0.05, (
        f"spans end at {fmt(cursor)} but the source is {fmt(src_sec)}")

    # 3. The owner's rounded marks and the measured boundaries agree to within
    #    a shot. Drifting further than that means the cut moved, not the round.
    assert abs(OWNER_MARKS["resume_at"] - RUNS[4][0]) < 2.0
    assert abs(OWNER_MARKS["skip_from"] - REMOVED[7][0]) < 2.0

    picture = sum(b - a for a, b, _ in RUNS)

    # --- the head, derived from the music --------------------------------
    # Where does SYNC_ANCHOR_SRC sit in the picture, measuring only kept time?
    anchor_picture_offset = None
    elapsed = 0.0
    for a, b, _ in RUNS:
        if a <= SYNC_ANCHOR_SRC < b:
            anchor_picture_offset = elapsed + (SYNC_ANCHOR_SRC - a)
            break
        elapsed += b - a
    assert anchor_picture_offset is not None, (
        f"sync anchor {SYNC_ANCHOR_SRC} is not inside any kept run -- it was "
        "cut. Move the anchor to a frame that still plays, or restore the run.")

    # The lead-in IS whatever puts the anchor on the beat. Asserting it rather
    # than typing it is what keeps the shield on the downbeat if a run moves.
    lead = SYNC_ANCHOR_FILM - anchor_picture_offset
    assert lead >= 0, (
        f"the anchor needs a lead of {lead:.3f}s -- there is more picture "
        "before the beat than the song has room for")

    tail = bed_sec - lead - picture
    assert tail >= -0.001, (
        f"picture overruns the song by {-tail:.3f}s; something must be cut")
    assert abs((lead + picture + tail) - bed_sec) < 0.001

    gap = bed_sec - picture

    return {
        "act": "II",
        "title": "Endless Forms Most Beautiful",
        "source_id": SOURCE_ID,
        "bed_id": BED_ID,
        "source_duration_sec": round(src_sec, 3),
        "bed_duration_sec": round(bed_sec, 3),
        "picture_sec": round(picture, 3),
        "gap_sec": round(gap, 3),
        "tail_policy": TAIL_POLICY,
        "sync_anchor_src": SYNC_ANCHOR_SRC,
        "sync_anchor_film": SYNC_ANCHOR_FILM,
        "bed_lead_sec": round(lead, 3),
        "bed_tail_sec": round(tail, 3),
        "film_sec": round(lead + picture + tail, 3),
        "runs": [{"in": a, "out": b, "sec": round(b - a, 3), "why": w}
                 for a, b, w in RUNS],
        "removed": [{"in": a, "out": b, "sec": round(b - a, 3), "why": w}
                    for a, b, w in REMOVED],
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    plan = build()

    if "--json" in argv:
        out = argv[argv.index("--json") + 1] if len(argv) > argv.index("--json") + 1 else None
        text = json.dumps(plan, indent=2)
        if out and not out.startswith("-"):
            Path(out).write_text(text + "\n")
            print(f"wrote {out}")
        else:
            print(text)
        return 0

    print(f"Act II -- {plan['title']}")
    print(f"  source {plan['source_id']}  {plan['source_duration_sec']}s")
    print(f"  bed    {plan['bed_id']}  {plan['bed_duration_sec']}s\n")
    print("KEPT")
    for r in plan["runs"]:
        print(f"  {fmt(r['in'])} -> {fmt(r['out'])}  {r['sec']:7.3f}s  {r['why']}")
    print("\nREMOVED")
    for r in plan["removed"]:
        print(f"  {fmt(r['in'])} -> {fmt(r['out'])}  {r['sec']:7.3f}s  {r['why']}")
    print(f"\n  picture {plan['picture_sec']}s ({fmt(plan['picture_sec'])})")
    print(f"  song    {plan['bed_duration_sec']}s ({fmt(plan['bed_duration_sec'])})")
    sign = "SHORT of" if plan["gap_sec"] > 0 else "LONGER than"
    print(f"  picture is {abs(plan['gap_sec']):.3f}s {sign} the song")
    if plan["tail_policy"] is None:
        print("\n  TAIL_POLICY is unset -- owner decides how the gap is closed.")
    else:
        print(f"\n  tail policy: {plan['tail_policy']}")
        print(f"  sync anchor: source {plan['sync_anchor_src']}s lands on "
              f"film {fmt(plan['sync_anchor_film'])} (the downbeat)")
        print(f"  bed leads the picture by {plan['bed_lead_sec']:.3f}s")
        print(f"  black tail under the outro  {plan['bed_tail_sec']:.3f}s")
        print(f"  film {plan['film_sec']}s ({fmt(plan['film_sec'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
