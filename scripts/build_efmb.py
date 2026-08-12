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
    # The moon, part one: the cold open, up to the cut into the reading.
    (0.000, 6.467, "moon cold open; out on the cut to the man reading"),
    # The moon, continuous: back from the framing narration to the HALO slate.
    (22.033, 52.233, "moon battle, unbroken; out on the cut back to the reading"),
    # Become Legend and Evil's Most Wanted, minus the DESTINY card.
    (62.633, 174.433, "in off the HALO slate; out on the cut to the DESTINY card"),
    (180.533, 244.833, "in off the black after the card; out before BECOME LEGEND"),
    # The tail. The owner's 4:50 lands mid-shot; 289.467 is the boundary before it.
    (289.467, 376.134, "owner's 4:50, snapped back to the shot boundary; to end"),
]

REMOVED = [
    (6.467, 22.033, "live action: the man reading to his son, and the book"),
    (52.233, 54.267, "live action: the reading, reprised"),
    (54.267, 62.633, "title card: from the creators of Halo"),
    (174.433, 179.167, "title card: DESTINY"),
    (179.167, 180.533, "black, measured by blackdetect"),
    (244.833, 246.100, "burned-in end title: BECOME LEGEND"),
    (246.100, 289.467, "the dance section -- cut separately as its own video"),
]

# The owner's rounded marks, kept beside the measured ones so the difference
# is visible rather than absorbed.
OWNER_MARKS = {"skip_from": 246.0, "resume_at": 290.0}

# What happens to the gap between picture and song.
#
# The owner asked to see the numbers first and was unavailable when they came
# in, so this is a decision made under `AGENTS.md`'s degrade rule, and it is
# the reversible one: **the song starts first**. Nothing is truncated, nothing
# is frozen, and no removed material is quietly restored -- the picture simply
# joins a song already playing, which is what the other three options all cost
# something to avoid. In the megacut the act slide covers that lead-in; played
# alone the act opens on black with the music under it.
#
# Changing this to any other policy changes no run above.
TAIL_POLICY = "music_first"
BED_LEAD_SEC = None  # derived below: exactly the gap


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

    # 2. Runs and removals together account for every frame of the source that
    #    precedes the final out point. A frame that is neither kept nor named
    #    as removed is a frame nobody decided about.
    spans = sorted([(a, b) for a, b, _ in RUNS] + [(a, b) for a, b, _ in REMOVED])
    cursor = 0.0
    for a, b in spans:
        assert abs(a - cursor) < 0.001, (
            f"gap or overlap at {fmt(cursor)}: next span starts {fmt(a)}")
        cursor = b
    assert abs(cursor - RUNS[-1][1]) < 0.001

    # 3. The owner's rounded marks and the measured boundaries agree to within
    #    a shot. Drifting further than that means the cut moved, not the round.
    assert abs(OWNER_MARKS["resume_at"] - RUNS[-1][0]) < 2.0
    assert abs(OWNER_MARKS["skip_from"] - REMOVED[-1][0]) < 2.0

    picture = sum(b - a for a, b, _ in RUNS)
    gap = bed_sec - picture

    # The lead-in IS the gap, by construction. Asserting it rather than typing
    # a number is what keeps the song whole if a run boundary ever moves.
    lead = gap if TAIL_POLICY == "music_first" else 0.0
    assert lead >= 0, "picture is longer than the song; TAIL_POLICY cannot absorb it"
    assert abs((lead + picture) - bed_sec) < 0.001

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
        "bed_lead_sec": round(lead, 3),
        "film_sec": round(lead + picture, 3),
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
        print(f"  bed leads the picture by {plan['bed_lead_sec']:.3f}s")
        print(f"  film {plan['film_sec']}s ({fmt(plan['film_sec'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
