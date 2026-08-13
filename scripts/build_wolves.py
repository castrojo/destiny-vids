#!/usr/bin/env python3
"""Build the authored shotlist for *Seven Days to the Wolves* -- editorial pass.

This is NOT ``tools/story.py``. There is no matcher and no index lookup: the
shots are picked by eye from contact sheets, because tagging exists to feed the
matcher and nothing here uses it.

WHAT CHANGED IN THE EDITORIAL PASS
----------------------------------
The timing pass was reviewed and the owner gave notes at FILM timecodes. Every
note below was confirmed by extracting the frame it names, and every span was
then snapped to a measured shot boundary -- never to a round number.

The marker cards are gone. A timing pass blacks out what it is going to remove;
this pass actually removes it, and fills every slot with picture:

  * six Contributor Summit group photographs replace the four COMIC PLACEHOLDER
    cards and the three black spans inside Act I (``scripts/build_summit_plates.py``);
  * the COUNTLESS LEGENDS publisher slide is removed outright rather than marked;
  * three action runs from the official Final Shape *Gameplay* Trailer fill the
    hole left by excising the Pale Heart's long Ghost sequence;
  * the pause is recut from that same trailer, to the shot the owner named.

WHAT CHANGED FROM THE FIRST CUT, AND WHY
----------------------------------------
The first cut was 289 shots in 424 s, 25 of them replayed, a third of Act I
from Curse of Osiris, and the middle reshuffled out of source order. This one
inverts the method.

**Mark, don't cut -- until now.** The timing pass left every doomed span in the
timeline at its exact duration behind a marker card, so the cut could be judged
against the music before a frame was taken out. That job is done. What survives
from it is the arithmetic: a card and the footage it replaces are the same
number of seconds, so **replacing a black span with a photograph moves no
anchor at all**, and only the genuine removals shorten anything.

**Continuity over selection.** Every act is ONE unbroken source run, in source
order. Act II and Act III-A are literally contiguous -- the window crash is not
a cut at all, it simply happens, which is the strongest possible way to land it
on the flute entry.

**Two clocks.** ``wall`` is position in the film, ``bed`` is position in the
song. A shot marked ``audio: "source"`` advances wall and not bed, so the film
is longer than its own song. Every anchor is asserted against BED time; see
``tools/audiomix.py``.

THREE TIMING INVARIANTS, WHICH THE ASSERTIONS BELOW ENFORCE
-----------------------------------------------------------
1. Bed anchors never move -- the gallop, the flute entry, the HOWL, the pause.
2. Act I removals are bought back off the HEAD, automatically, by the derived
   ``CAPTURE_IN``. Cut more out of the intro and the capture simply starts
   earlier; the gallop does not move.
3. A removal inside Act III must be FILLED, because that act's length is pinned
   between two anchors and ``wolves_act2`` has no footage past 210.015 s.

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
* **Every Act I edit is a measured span**, from ``blackdetect`` for the black
  and from ``ContentDetector`` for the picture. See ``ACT1_EDITS``.
* **The pause is the shot the owner named.** Frame-differencing the trailer at
  1/30 s finds the explosion's cut at **51.835** (frame delta 170 against a
  background of <30) and the cut out of the transcendence portrait at
  **53.470** (delta 89). Nothing there was chosen by eye.

EDITORIAL RULES ENFORCED HERE RATHER THAN REMEMBERED
----------------------------------------------------
  * no Curse of Osiris anywhere -- this is the finale
  * no shot used twice, asserted
  * no Savathun; the Witness only as eyes or smoke, never its body
  * no publisher slide survives: each is removed, or replaced by picture
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
# The owner named this shot: "we want this explosion to be cortney's segment.
# Capture the length of the shot, including the portrait of her in
# transcendence glowing mode, hold the scene until the cut."
#
# It is NOT in the Collection Trailer, which is where the timing pass looked
# for it. The owner's reference clip (~/Videos/wolves-directors-cut/cortney.mp4,
# 9.009 s, 640x360, with music) frame-matches the official Final Shape GAMEPLAY
# trailer at 45.0 -> 54.009: mean abs pixel diff 3.2-4.1 at 160x90 against a
# runner-up of 22-33, i.e. exact, at four probes across the clip.
#
# In-point is the enclosing shot boundary at 44.811, so the moment builds
# rather than starting mid-air. Out-point is the measured cut after the
# transcendence portrait. The reference is 9.009 s and this is 8.659 s.
PAUSE_AT = 322.200         # a downbeat (FIRST_BEAT + 102 bars)
PAUSE_IN = 44.811          # Gameplay Trailer: the shot the run-up sits in
PAUSE_OUT = 53.470         # the cut out of the transcendence portrait
PAUSE_DUR = PAUSE_OUT - PAUSE_IN

# Publisher mechanic cards inside the Collection Trailer montage. Two are
# replaced by a Contributor Summit photograph at their exact duration, so the
# montage's timing is untouched. The third -- COUNTLESS LEGENDS, at 87.4 -- is
# REMOVED outright on the owner's note ("cut out the renegades slide"), which
# is why it is not in this list: the montage simply stops before it.
TRAILER_CARDS = [
    (63.267, 65.233, "7 RAIDS card", "raids"),
    (71.033, 73.000, "ENDLESS BUILDCRAFTING card", "buildcrafting"),
]
COUNTLESS_LEGENDS_IN = 87.400   # the montage must never reach this

ART = str(Path.home() / "Pictures/Artwork/wolves.jpg")

# Contributor Summit group photographs, built by scripts/build_summit_plates.py.
# CNCF, CC BY-NC-ND 4.0; cropped to 16:9 on the owner's explicit authority.
# See that script's header and docs/cuts/07-seven-days-to-the-wolves.md.
SUMMIT_DIR = REPO / "renders" / "summit-plates"


def summit(slot, fallback_text, fallback_sub):
    """A summit photograph, or the marker card it replaces if it is missing.

    Degrade, never block: an absent plate is reported by the plate builder and
    the cut still renders, with the slot's original marker in place.
    """
    plate = SUMMIT_DIR / f"{slot}.jpg"
    if plate.exists():
        return str(plate)
    print(f"  MISSING PLATE {slot}: falling back to the marker card",
          file=sys.stderr)
    return marker_path(fallback_text, fallback_sub)


# --- sources -----------------------------------------------------------------
# Window extracts, so every seek lands in a short file: render.py seeks with
# -ss AFTER -i for frame accuracy, which decodes from zero (docs/rendering.md).
ACT1 = "wolves_act1"       # compilation 0:00-3:30      -- the Destiny 1 opening
LIGHTFALL = "yt_destiny_2_lightfall_launch_trailer"   # OFFICIAL Bungie upload
COMP = "wolves_act2"       # compilation 23:00-26:30    -- Neomuna, the crash
TRAILER = "wolves_act3"    # Collection Trailer 0:00-1:32
FINALE = "wolves_act4"     # compilation 26:30-30:23    -- the Pale Heart finale
# UchfadQhX7w, "Destiny 2: The Final Shape | Gameplay Trailer", 123 s, uploaded
# 2024-04-09 by the official "Destiny 2" channel -- NOT the Launch Trailer
# (6Gm5mbwrqSA) already indexed here. Fetched as 4K AV1 (format 401) and scaled
# to 1080p. An official Bungie upload, so it is better provenance than the fan
# compilation the rest of the film rests on (issue #55).
GAMEPLAY = "yt_destiny_2_the_final_shape_gameplay_trailer"

TITLE_CARD_LEN = 10.000    # the card opens the film; the song plays under it
CAPTURE_OUT = 203.000      # the first cinematic ends here (verified by frame)

# Everything the owner asked for inside the intro, in source order on `act1`.
#   "cut"          the span is removed; its seconds are bought back off the head
#   "<slot>"       the span is replaced, at its exact duration, by that summit
#                  photograph -- so the timeline does not move at all
#
# The black spans are from `blackdetect` (d=0.3, pic_th=0.98); the picture
# boundaries are from `ContentDetector`. Film timecodes in the comments are the
# owner's own notes, mapped through the timing pass's shot list.
ACT1_EDITS = [
    (58.166, 67.435, "cut",
     "the static sun, and the black after it -- to 67.435, where the black "
     "actually ends; the old 67.166 leaked 0.27 s of it into the cut"),
    (100.114, 100.885, "cut",
     "film 1:20 -- the dark tail after the enemy, so the enemy is a flash"),
    (100.885, 103.901, "act1_black_1",
     "film 1:21 -- the black; the owner asked for it gone, and it becomes the "
     "summit instead"),
    (122.939, 124.179, "cut",
     "film 1:42 -- the Ghost by itself; cuts straight to the two together"),
    (135.407, 136.781, "act1_black_2", "film 1:55 -- black"),
    (159.975, 162.354, "cut", "film 2:20 -- the court scene"),
    (163.293, 169.728, "cut",
     "film 2:23 to 2:30 -- the whole sequence, out on the ship lifting off"),
    (185.078, 187.156, "act1_black_3", "film 2:45 -- black"),
]

# The song plays from the first frame, so the intro has exactly ACT2_IN seconds
# to spend and the capture is trimmed to fit: card + capture = the gallop.
# Whatever is CUT above is bought back off the HEAD, which is why the in-point
# is derived rather than written down: drop another span and the capture simply
# starts earlier, and the gallop does not move. A replaced span costs nothing,
# because the photograph is exactly as long as the black it stands in for.
CAPTURE_IN = (CAPTURE_OUT - (ACT2_IN - TITLE_CARD_LEN)
              - sum(o - i for i, o, kind, _ in ACT1_EDITS if kind == "cut"))

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

# --- Act III-C: the Pale Heart, with its Ghost sequence taken out ------------
# "cut 5:44 extended ghost sequence, cut this to 5:56 and keep the rest."
# Verified by frame: `wolves_act2` 187.022 -> 200.965 is the Ghost alone,
# flying through fog and machinery. The Guardians return on the plains at
# 200.965, which is a detected cut.
PALE_IN = 171.000
GHOST_IN = 187.022         # the Ghost sequence starts
GHOST_OUT = 200.965        # ...and the Guardians are back on the plains
PALE_OUT = 210.000         # `wolves_act2` is 210.015 s long: there is no more

# The 13.943 s the Ghost vacates cannot be borrowed from the source -- the
# extract simply ends -- so it is filled with the three action runs the owner
# supplied as 640x360 proxies, recut here from the 1080p master. The proxies'
# own trims (77-82, 83-87, 91-97) are the owner's, not shot edges, so each is
# snapped to a detected boundary. Only the last is trimmed, and only at its
# TAIL: an in-point is what the detector worked to find, so a trim never moves
# the start (docs/skills/editing/SKILL.md, "Holds").
#
# CASTING, on the owner's instruction, which OVERRODE their own filenames:
# the Titan is Kat Cosgrove, the Warlock is Kaslin Fields, and the Hunter --
# whose proxy was named "Laura" -- is github.com/inffy, NOT Laura Santamaria.
# None of the three is plated: they play under the bed as action, and credit
# belongs to the credits sequence (issue #51). inffy has no authored Guardian
# identity anywhere, so no plate copy is written for them; see the punch list.
GHOST_FILL = [
    (77.578, 82.516, "a Titan holds the line behind a Ward of Dawn",
     "kat_cosgrove"),
    (82.516, 87.087, "a Warlock through the Dread, weapons up", "kaslin_fields"),
    (90.791, 95.225, "a Hunter vaults into the light, and three walk in "
     "together", "inffy"),
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
    pos = CAPTURE_IN
    for cut_in, cut_out, kind, what in ACT1_EDITS:
        # A replaced span sits flush against a cut span at 100.885, so the run
        # between them is legitimately zero-length. Anything else is a bug.
        if cut_in - pos > 1e-9:
            t.run(ACT1, pos, cut_in - pos,
                  f"I. intro capture from source {tc(pos)}")
        elif cut_in - pos < -1e-9:
            raise AssertionError(f"ACT1_EDITS overlap at {cut_in}: {what}")
        if kind != "cut":
            t.card(summit(kind, "COMIC PLACEHOLDER", what),
                   cut_out - cut_in, f"I. SUMMIT -- {what}")
        pos = cut_out
    t.run(ACT1, pos, CAPTURE_OUT - pos,
          f"I. intro capture from source {tc(pos)} to {tc(CAPTURE_OUT)}")
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

    # The enemy close-up. The timing pass blacked it out; this pass puts the
    # people the film is about there instead.
    t.card(summit("enemy_cu", "COMIC PLACEHOLDER", "4:33-4:37  enemy CU"),
           ARTWORK_IN - ENEMY_CU_IN,
           "III. SUMMIT -- the whole Contributor Summit, over the enemy CU")

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
    # The montage's length is fixed by the anchors either side, so removing the
    # COUNTLESS LEGENDS slide cannot simply shorten it -- the pause would slide
    # off its downbeat. The run starts EARLIER instead, and stops before the
    # slide. Bed time is unchanged and the slide never appears.
    montage_in = 51.767            # a detected boundary, 3.3 s earlier than the
                                   # timing pass's 55.0
    montage_len = PAUSE_AT - a3a_out
    pos = montage_in
    for card_in, card_out, what, slot in TRAILER_CARDS:
        t.run(TRAILER, pos, card_in - pos,
              f"III. the Collection Trailer montage, unbroken from "
              f"{int(pos)//60}:{pos % 60:04.1f}")
        t.card(summit(slot, "COMIC PLACEHOLDER", what),
               card_out - card_in, f"III. SUMMIT -- over the {what}")
        pos = card_out
    montage_out = montage_in + montage_len
    t.run(TRAILER, pos, montage_out - pos,
          "III. the montage runs out to the pause, stopping before the "
          "COUNTLESS LEGENDS slide")
    assert montage_out <= COUNTLESS_LEGENDS_IN + 1e-9, (
        f"the montage reaches source {montage_out:.3f}s but the COUNTLESS "
        f"LEGENDS slide starts at {COUNTLESS_LEGENDS_IN:.3f}s -- the publisher "
        "slide the owner asked to cut would be back on screen.")
    t.at_bed(PAUSE_AT, "Act III-B")

    # ---- the pause: the song stops; the moment plays in its own audio ------
    # UNPLATED, deliberately. The owner names this shot as Cortney Nickerson's,
    # and she has no authored Guardian identity in ~/Videos/nameplates.json,
    # the website's characters.json, or vocab/casting.yaml. A missing name is
    # omitted and recorded; it is never invented (AGENTS.md). See the punch
    # list in docs/cuts/07-seven-days-to-the-wolves.md.
    #
    # The source audio here is the trailer's own, unaltered. Measured over this
    # span it is broadband, not tonal -- spectral flatness 0.45 in the run-up
    # and 0.47 across the explosion -- i.e. gunfire and detonation rather than a
    # melodic bed, which is what "the sfx pristine version, no music" asks for.
    # Nothing is separated or enhanced to make that true (docs/skills/references/audio-standard.md).
    t.run(GAMEPLAY, PAUSE_IN, PAUSE_DUR,
          "III. SONG PAUSES -- the explosion, then the transcendence portrait, "
          "held to the cut, in its own audio. Casting requested: Cortney "
          "Nickerson. UNPLATED: no authored identity exists, so none is invented.",
          audio="source")
    t.at_bed(PAUSE_AT, "the pause consumed no bed time")

    # ---- Act III-C: the Pale Heart, around the excised Ghost sequence ------
    pale_out = 361.200
    t.run(COMP, PALE_IN, GHOST_IN - PALE_IN,
          "III. the Pale Heart, unbroken from source 25:51 -- Guardians "
          "gathering on the plains", plate_slot=True)
    for src_in, src_out, what, person in GHOST_FILL:
        t.run(GAMEPLAY, src_in, src_out - src_in,
              f"III. {what} [{person}, uncredited here by design]")
    t.run(COMP, GHOST_OUT, PALE_OUT - GHOST_OUT,
          "III. back on the plains, where the Ghost sequence used to end",
          plate_slot=True)
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
