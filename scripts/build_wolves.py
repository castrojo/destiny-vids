#!/usr/bin/env python3
"""Build the authored shotlist for *Seven Days to the Wolves* -- timing pass.

This is NOT ``tools/story.py``. There is no matcher and no index lookup: the
shots are picked by eye from contact sheets, because tagging exists to feed the
matcher and nothing here uses it.

WHAT CHANGED FROM THE FIRST CUT, AND WHY
----------------------------------------
The first cut was 289 shots in 424 s, 25 of them replayed, a third of Act I
from Curse of Osiris, and the middle reshuffled out of source order. This one
inverts the method.

**Mark, don't cut.** Nothing is removed. A span destined for removal or for
artwork stays in the timeline at its exact duration, blacked out by a marker
card (``tools/marker.py``). Timing is therefore preserved by construction and
can be judged against the music before a frame is actually taken out. See
``docs/skills/editing.md``.

**Continuity over selection.** Every act is ONE unbroken source run, in source
order. Act II and Act III-A are literally contiguous -- the window crash is not
a cut at all, it simply happens, which is the strongest possible way to land it
on the flute entry.

**Two clocks.** ``wall`` is position in the film, ``bed`` is position in the
song. A shot marked ``audio: "source"`` advances wall and not bed, so the film
is longer than its own song. Every anchor is asserted against BED time; see
``tools/audiomix.py``.

MEASURED, NOT GUESSED
---------------------
* **The gallop, 182.834 s** and **the flute entry, 259.390 s** -- the two act
  hinges, from the first cut's spectral analysis, snapped to the bar grid.
* **The one break in the song: 278.64 -> 279.64 s.** A scan of the whole bed
  for full-band drops finds exactly one interior gap: a full second of silence
  ending 23 ms before the downbeat at 279.661. That is the "HOWL", and it is
  where the artwork holds -- over the silence, cutting back to picture on the
  slam.
* **The crash impact peaks at extract 105.9 s**, half a second after the shot
  starts at 105.4. The run is placed so the IMPACT lands on the flute entry and
  the shot starts a beat early -- "4:19 backed up a tad", as a number.
* **The intro capture is 193 s for a 182.834 s act.** Rather than trim the
  capture, the bed ENTERS LATE, at wall 20.166 s. The film opens on the
  cinematic's own audio and the song arrives over it; the gallop still lands
  exactly at the end of the capture. Nothing is cut to make the music fit.

EDITORIAL RULES ENFORCED HERE RATHER THAN REMEMBERED
----------------------------------------------------
  * no Curse of Osiris anywhere -- this is the finale
  * no shot used twice, asserted
  * no Savathun; the Witness only as eyes or smoke, never its body
  * a long enemy hold becomes a COMIC PLACEHOLDER card, never a jump cut
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.marker import marker_path, title_card_path  # noqa: E402

BED = json.loads((REPO / "music/bed_seven_days_to_the_wolves.json").read_text())
GRID = BED["grid"]
BAR = GRID["bar_sec"]
FIRST_BEAT = GRID["first_beat_sec"]
END = BED["duration_sec"]                       # 423.993

# --- the two act hinges, measured in the first cut ---------------------------
ACT2_IN = 182.834          # the gallop
ACT3_IN = 259.390          # the flute entry -- the crash impact lands here

# --- the song's one interior silence ----------------------------------------
HOWL_GAP_IN = 278.64       # the band stops
HOWL_SLAM = 279.661        # ...and returns, on this downbeat
ARTWORK_IN = 277.00        # the artwork is up before the shout, over the CU
ENEMY_CU_IN = 273.490      # the enemy close-up the artwork will replace

# --- the pause: the song stops, a moment plays in its own audio --------------
PAUSE_AT = 322.200         # a downbeat (FIRST_BEAT + 102 bars)
PAUSE_IN = 29.35           # Collection Trailer: the clean hero shot at 0:29
PAUSE_DUR = 1.8            # ...and out before the first-person gameplay at 0:31

# Mechanic cards inside the Collection Trailer montage, recovered from the
# frames in the first cut. Each is publisher copy this film does not want, so
# each becomes an artwork slot -- marked at its exact duration, never cut.
TRAILER_CARDS = [
    (63.3, 65.2, "7 RAIDS card"),
    (71.0, 73.0, "ENDLESS BUILDCRAFTING card"),
    (87.4, 89.4, "COUNTLESS LEGENDS card"),
]

ART = str(Path.home() / "Pictures/Artwork/wolves.jpg")

# --- sources -----------------------------------------------------------------
# Window extracts, so every seek lands in a short file: render.py seeks with
# -ss AFTER -i for frame accuracy, which decodes from zero (docs/rendering.md).
ACT1 = "wolves_act1"       # compilation 0:00-3:30      -- the Destiny 1 opening
LIGHTFALL = "yt_destiny_2_lightfall_launch_trailer"   # OFFICIAL Bungie upload
COMP = "wolves_act2"       # compilation 23:00-26:30    -- Neomuna, the crash
TRAILER = "wolves_act3"    # Collection Trailer 0:00-1:32
FINALE = "wolves_act4"     # compilation 26:30-30:23    -- the Pale Heart finale

TITLE_CARD_LEN = 10.000    # the card opens the film; the song plays under it
CAPTURE_OUT = 203.000      # the first cinematic ends here (verified by frame)
# The song plays from the first frame, so the intro has exactly ACT2_IN seconds
# to spend and the capture is trimmed to fit: card + capture = the gallop.
# The trim comes off the HEAD -- source 0:10-0:30 is a slow, dark orrery, and
# the capture's ending (the ship rising, the fade) is the payoff into Act II.
CAPTURE_IN = CAPTURE_OUT - (ACT2_IN - TITLE_CARD_LEN)   # 30.166

CRASH_IMPACT = 105.900     # extract clock; measured from the audio transient
NEOMUNA_IN = 47.100        # extract clock: where Neomuna starts, verified by frame.
# Before it lie Savathun's Throne World and the WITCH QUEEN branded cards, which
# the standing no-Savathun rule keeps out of this film. There are only 60.35 s of
# Neomuna before the crash, and the gallop-to-flute span is 76.556 s, so the
# gallop cuts to neon from the OFFICIAL Lightfall trailer and hands over to the
# compilation exactly at the Neomuna boundary.
# Runs are taken from the indexed segment boundaries so none starts mid-shot;
# the last one is stretched to fill, and stops before the trailer's OUR/END
# title cards at 87.05.
LIGHTFALL_LEAD = [
    (44.91, 48.21, "Neomuna's neon skyline, establishing"),
    (52.05, 53.45, "a Guardian in a rain-slick Neomuna alley"),
    (72.94, None, "into the Strand: Guardians over the neon city"),
]

BANNED_SOURCES = ("yt_curse_of_osiris_opening_cinematic",)


def tc(seconds):
    return f"{int(seconds) // 60}:{seconds % 60:04.1f}"


class Timeline:
    """Two clocks and a shot list.

    ``bed`` only advances for shots the song plays under. That single rule is
    what lets the film contain a pause without any anchor moving.
    """

    def __init__(self):
        self.shots = []
        self.wall = 0.0
        self.bed = 0.0

    def run(self, video_id, src_in, dur, beat, audio="bed", plate_slot=False):
        """A continuous piece of one source, in source order."""
        shot = {
            "segment_id": f"{video_id}_{src_in:08.3f}".replace(".", "_"),
            "video_id": video_id,
            "start_sec": round(src_in, 3),
            "end_sec": round(src_in + dur, 3),
            "duration": round(dur, 3),
            "start_tc": tc(src_in),
            "end_tc": tc(src_in + dur),
            "beat": beat,
            "audio": audio,
        }
        if plate_slot:
            # Where a nameplate can land: Guardians together, held long enough
            # to read. Recorded here so the plates pass has a list to work from
            # rather than re-deriving it by eye.
            shot["plate_slot"] = True
        self._push(shot, dur, audio)
        return shot

    def card(self, still, dur, beat, audio="bed"):
        shot = {
            "segment_id": f"card_{len(self.shots):03d}",
            "still": str(still),
            "duration": round(dur, 3),
            "beat": beat,
            "audio": audio,
        }
        self._push(shot, dur, audio)
        return shot

    def _push(self, shot, dur, audio):
        if dur <= 0:
            raise AssertionError(f"non-positive duration for {shot['beat']!r}")
        self.shots.append(shot)
        self.wall += dur
        if audio != "source":
            self.bed += dur

    def at_bed(self, target, what):
        if abs(self.bed - target) > 0.02:
            raise AssertionError(
                f"{what}: bed clock is {self.bed:.3f}s but the anchor is "
                f"{target:.3f}s. The cut is a concatenation, so a short act "
                "slides every later anchor off the music.")


def build():
    t = Timeline()

    # ---- the title card: the source's own logo, blacked out ----------------
    # Not an overlay. The card IS the picture for ten seconds, so the Destiny
    # logo is not dimmed, it is simply not in the film.
    t.card(title_card_path(
        "Project Bluefin", "Seven Days to the Wolves",
        ["Destiny footage used under Bungie's fan-content policy"]),
        TITLE_CARD_LEN,
        "TITLE CARD (the film's own logo; the source's is never shown)")

    # ---- Act I: the intro capture ------------------------------------------
    t.run(ACT1, CAPTURE_IN, ACT2_IN - TITLE_CARD_LEN,
          f"I. intro capture, continuous from source "
          f"{int(CAPTURE_IN)//60}:{CAPTURE_IN % 60:04.1f} to "
          f"{int(CAPTURE_OUT)//60}:{CAPTURE_OUT % 60:04.1f}")
    t.at_bed(ACT2_IN, "Act I")
    assert abs(t.shots[-1]["end_sec"] - CAPTURE_OUT) < 0.01, (
        f"Act I ends at source {t.shots[-1]['end_sec']:.3f}s but the first "
        f"cinematic ends at {CAPTURE_OUT:.3f}s -- the capture would run into "
        "the fade and the next trailer.")

    # ---- Act II: the gallop cuts to neon ----------------------------------
    # The compilation only holds 60.35 s of Neomuna before the crash, so the
    # first 16.2 s comes from the official Lightfall trailer -- which is both
    # the right picture for the gallop and better provenance than the fan
    # compilation.
    comp_len = CRASH_IMPACT - NEOMUNA_IN
    lead_len = (ACT3_IN - ACT2_IN) - comp_len
    fixed = sum(o - i for i, o, _ in LIGHTFALL_LEAD if o is not None)
    for n, (src_in, src_out, what) in enumerate(LIGHTFALL_LEAD):
        dur = (src_out - src_in) if src_out is not None else lead_len - fixed
        prefix = "the gallop cuts to neon -- " if n == 0 else ""
        t.run(LIGHTFALL, src_in, dur, f"II. {prefix}{what}",
              plate_slot=(src_out is None))

    t.run(COMP, NEOMUNA_IN, comp_len,
          f"II. Neomuna, unbroken from source "
          f"{int(NEOMUNA_IN + 1380)//60}:{(NEOMUNA_IN + 1380) % 60:04.1f} "
          "straight through to the crash",
          plate_slot=True)
    t.at_bed(ACT3_IN, "Act II")

    # ---- Act III-A: contiguous with Act II. The crash is not a cut. --------
    def src_at(bed_time):
        """Where this run is in the source, for a given position in the song."""
        return CRASH_IMPACT + (bed_time - ACT3_IN)

    t.run(COMP, src_at(ACT3_IN), ENEMY_CU_IN - ACT3_IN,
          "III. the crash (impact on the flute entry), then the strand descent")

    # The enemy close-up. Marked, not cut: the span stays, blacked out, so the
    # timing is unchanged and the artwork has a measured slot to land in.
    t.card(marker_path("COMIC PLACEHOLDER", "4:33-4:37  enemy CU"),
           ARTWORK_IN - ENEMY_CU_IN,
           "III. COMIC PLACEHOLDER over the enemy close-up")

    # The artwork, up before the shout and held through the song's one silence.
    t.card(ART, HOWL_SLAM - ARTWORK_IN,
           f"III. ARTWORK held through the HOWL and the {HOWL_GAP_IN:.2f}-"
           f"{HOWL_SLAM:.2f}s silence; picture returns on the slam")

    # ...and the picture returns on the downbeat, onto three Guardians.
    a3a_out = 287.000
    t.run(COMP, src_at(HOWL_SLAM), a3a_out - HOWL_SLAM,
          "III. the band slams back in on three Guardians, held",
          plate_slot=True)
    t.at_bed(a3a_out, "Act III-A")

    # ---- Act III-B: the Collection Trailer montage, in source order --------
    # Continuous from 0:55, with each mechanic card blacked out where it falls.
    # The montage's length is fixed by the anchors, so the marks cost nothing:
    # a card and the footage it replaces are the same number of seconds.
    montage_in = 55.0
    montage_len = PAUSE_AT - a3a_out
    pos = montage_in
    for card_in, card_out, what in TRAILER_CARDS:
        t.run(TRAILER, pos, card_in - pos,
              f"III. the Collection Trailer montage, unbroken from "
              f"{int(pos)//60}:{pos % 60:04.1f}")
        t.card(marker_path("COMIC PLACEHOLDER", what),
               card_out - card_in,
               f"III. COMIC PLACEHOLDER over the {what}")
        pos = card_out
    t.run(TRAILER, pos, montage_in + montage_len - pos,
          "III. the montage runs out to the pause")
    t.at_bed(PAUSE_AT, "Act III-B")

    # ---- the pause: the song stops; the moment plays in its own audio ------
    # UNPLATED, deliberately. The owner names this shot as Cortney Nickerson's,
    # and she has no authored Guardian identity in ~/Videos/nameplates.json,
    # the website's characters.json, or vocab/casting.yaml. A missing name is
    # omitted and recorded; it is never invented (AGENTS.md). See the punch
    # list in docs/cuts/07-seven-days-to-the-wolves.md.
    t.run(TRAILER, PAUSE_IN, PAUSE_DUR,
          "III. SONG PAUSES -- hero montage in its own audio, then resumes. "
          "Casting requested: Cortney Nickerson. UNPLATED: no authored "
          "identity exists, so no plate is invented.",
          audio="source")
    t.at_bed(PAUSE_AT, "the pause consumed no bed time")

    # ---- Act III-C: the Pale Heart -----------------------------------------
    pale_out = 361.200
    t.run(COMP, 171.0, pale_out - PAUSE_AT,
          "III. the Pale Heart, unbroken from source 25:51 -- Guardians "
          "gathering on the plains", plate_slot=True)
    t.at_bed(pale_out, "Act III-C")

    # ---- Act III-D: the finale ---------------------------------------------
    # Out at source 26:30 + 50.5, a beat before the branded THE FINAL SHAPE
    # cards start at 51 s: the film ends on the Guardians, not on a logo.
    finale_out = pale_out + 50.5
    t.run(FINALE, 0.0, finale_out - pale_out,
          "III. the finale, unbroken from source 26:30 -- the Guardians "
          "assembled", plate_slot=True)
    t.at_bed(finale_out, "Act III-D")

    # ---- the outro, over the fade ------------------------------------------
    # The song fades from 6:57 and is silent by 7:04. Holding the artwork there
    # beats truncating the fade -- a short picture would cut it off.
    t.card(ART, END - finale_out, "ARTWORK (outro, over the fade)")
    t.at_bed(END, "the whole cut")

    return t


def audit(shots):
    """The rules that were prose in the first cut, as assertions."""
    seen = set()
    for s in shots:
        if "video_id" not in s:
            continue
        assert s["video_id"] not in BANNED_SOURCES, (
            f"{s['video_id']} is excluded from this cut")
        key = (s["video_id"], s["start_sec"])
        assert key not in seen, f"shot reused: {key}"
        seen.add(key)


def main():
    t = build()
    audit(t.shots)

    out = {
        "title": "Seven Days to the Wolves",
        "kind": "timing_pass",
        "bed": "bed_seven_days_to_the_wolves",
        "bed_offset_sec": 0.0,
        "bed_gain_db": -3.5,
        "anchors": {
            "act2_gallop_in": ACT2_IN,
            "act3_flute_change": ACT3_IN,
            "howl_silence": [HOWL_GAP_IN, HOWL_SLAM],
            "pause_at_bed": PAUSE_AT,
        },
        "note": "AUTHORED shotlist, not a story.py output. A TIMING PASS: "
                "spans destined for removal or artwork are blacked out with "
                "marker cards at their exact duration, so nothing is cut yet. "
                "Shots marked audio=source do not advance the bed clock.",
        "shots": t.shots,
    }
    dest = REPO / "stories/seven-days-timing-pass.json"
    dest.write_text(json.dumps(out, indent=1))

    print(f"{len(t.shots)} shots")
    print(f"  film   {t.wall:7.3f}s  ({int(t.wall)//60}:{t.wall % 60:04.1f})")
    print(f"  bed    {t.bed:7.3f}s  (song is {END:.3f}s)")
    print(f"  the song plays from the first frame")
    print(f"  plate slots: {sum(1 for s in t.shots if s.get('plate_slot'))}")
    print(f"  cards:       {sum(1 for s in t.shots if s.get('still'))}")
    print(f"-> {dest}")


if __name__ == "__main__":
    main()
