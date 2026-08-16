#!/usr/bin/env python3
"""Build act II of the musical -- *Endless Forms Most Beautiful*.

This is NOT ``tools/story.py``. There is no matcher and no index lookup: the
owner gave the cut as timecodes on one source, and every span below was then
snapped to a **measured** shot boundary rather than to the round number.

THE SHAPE OF THIS ACT
---------------------
One source, six unbroken runs in source order, plus one deliberate interruption.
The Endless Forms bed pauses at the interruption, Local Forecast carries
Cortney's plate and the reaction, and the hero clip plays its own source mix.
Source timing remains the authority; only final wall time moves.

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
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
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
    (362.200, 376.186, "DESTINY / DESTINY 2 logo slates, Bungie/Activision copyright, 'AVAILABLE ON PC OCTOBER 24'"),
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
#    269.700 -- an exact downbeat on the bed's own grid (beat index 692,
#    downbeat_phase 0, bar 1.578957 s; the record carried the argmax-wrong
#    phase 3 until #89 corrected it). On screen at that moment is a Sentinel
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


# --- the mapping between source, bed, and wall time -------------------------
# Every mark the owner ever gave for this act was given in FILM time, and the
# film has moved under all of them: the head lead went 8.564 -> 10.650, run 1's
# out point moved 6.467 -> 4.017, and the mech and the end cards are gone. A
# film timecode from an earlier pass therefore points at the wrong frame, and
# quietly so.
#
# SOURCE TIME IS THE INVARIANT. It is a position in a file that has not
# changed, so a mark recorded against it survives every re-cut that does not
# remove the frame itself. ``bed_for_source`` maps it to the original music
# clock. ``film_for_source`` maps it to final wall time and therefore adds the
# interruption's inserted wall duration after the Act-II resume point.

class NotInPicture(ValueError):
    """A source moment that no kept run plays, or a film moment in head/tail."""


def picture_offset_for_source(src_sec, runs=None):
    """Where ``src_sec`` sits in the picture, counting only KEPT time."""
    elapsed = 0.0
    for a, b, _ in (RUNS if runs is None else runs):
        if a <= src_sec < b:
            return elapsed + (src_sec - a)
        elapsed += b - a
    raise NotInPicture(
        f"source {src_sec:.3f}s is not inside any kept run -- it was cut. "
        "Nothing may be bound to a frame that does not play.")


def bed_for_source(src_sec, lead=None, runs=None):
    """Source seconds -> the unpaused Endless Forms bed clock."""
    if lead is None:
        lead = derive_lead(runs)
    return lead + picture_offset_for_source(src_sec, runs)


def source_for_bed(bed_sec, lead=None, runs=None):
    """The unpaused Endless Forms bed clock -> source seconds."""
    if lead is None:
        lead = derive_lead(runs)
    offset = bed_sec - lead
    if offset < 0:
        raise NotInPicture(
            f"bed {bed_sec:.3f}s is in the {lead:.3f}s head -- black, no picture")
    elapsed = 0.0
    for a, b, _ in (RUNS if runs is None else runs):
        span = b - a
        if offset < elapsed + span:
            return a + (offset - elapsed)
        elapsed += span
    raise NotInPicture(
        f"bed {bed_sec:.3f}s is past the last frame of picture "
        f"({lead + elapsed:.3f}s) -- it is in the tail")


def derive_lead(runs=None):
    """The head lead-in, derived from the sync anchor. Never typed."""
    return SYNC_ANCHOR_FILM - picture_offset_for_source(SYNC_ANCHOR_SRC, runs)


# --- the Cortney interruption -----------------------------------------------
# The owner gave these in the programme's OLD wall clock. They are source
# pointers, not placement offsets: deriving them through the pre-insertion bed
# clock is what keeps 6:17/6:19/6:27 attached to their original frames after
# the interruption grows final wall time.
MEGACUT_OFFSET = 121.567
ORIGINAL_MEGACUT_POINTERS = {
    "interrupt_in": 6 * 60 + 17,
    "resume": 6 * 60 + 19,
    "kolunmi": 6 * 60 + 27,
}


def source_from_original_megacut(mark):
    """Turn an owner programme mark into its stable Act-II source pointer."""
    return source_for_bed(float(mark) - MEGACUT_OFFSET)


def interruption_sources():
    """The source anchors derived from the owner's original programme marks."""
    return {
        name: round(source_from_original_megacut(mark), 3)
        for name, mark in ORIGINAL_MEGACUT_POINTERS.items()
    }


# Existing, owner-approved material moved from Act VI. The Hero source clock is
# the official Final Shape Gameplay Trailer; the source span ends on the
# measured cut after the portrait.
HERO_SOURCE_ID = "yt_destiny_2_the_final_shape_gameplay_trailer"
HERO_IN = 43.000
HERO_OUT = 53.470
CORTNEY_PLATE_SEC = 4.000
OWNER_TEXT_SEC = 2.200
REACTION_HOLD_SEC = 2.200
REACTION_GAP_SEC = 0.250
REACTION_COUNT = 3
POST_HERO_BLACK_SEC = (
    OWNER_TEXT_SEC + REACTION_COUNT * REACTION_HOLD_SEC
    + REACTION_COUNT * REACTION_GAP_SEC
)
ELEVATOR_MUSIC_ID = "bed_local_forecast_slower"
ELEVATOR_MUSIC_IN = 6.500
AUDIO_FADE_SEC = 1.000


def interruption_duration():
    """Wall seconds inserted where the two Act-II source seconds were removed."""
    return CORTNEY_PLATE_SEC + (HERO_OUT - HERO_IN) + POST_HERO_BLACK_SEC


def interruption_wall_in(lead=None):
    """The final wall instant at which Act-II yields to the interruption."""
    return bed_for_source(interruption_sources()["interrupt_in"], lead)


def interruption_wall_out(lead=None):
    """The final wall instant at which Act-II source resumes."""
    return interruption_wall_in(lead) + interruption_duration()


def _wall_shift_for_source(src_sec):
    """The inserted wall time less the replaced source span, after resume."""
    pointers = interruption_sources()
    if pointers["interrupt_in"] <= src_sec < pointers["resume"]:
        raise NotInPicture(
            f"source {src_sec:.3f}s is replaced by the Cortney interruption")
    if src_sec >= pointers["resume"]:
        return interruption_duration() - (pointers["resume"]
                                           - pointers["interrupt_in"])
    return 0.0


def film_for_source(src_sec, lead=None, runs=None):
    """Source seconds -> final Act-II wall time. Raises if the frame was cut."""
    return bed_for_source(src_sec, lead, runs) + _wall_shift_for_source(src_sec)


def source_for_film(film_sec, lead=None, runs=None):
    """Final Act-II wall time -> source seconds, excluding interruption beats."""
    start = interruption_wall_in(lead)
    end = interruption_wall_out(lead)
    if start <= film_sec < end:
        raise NotInPicture(
            f"film {film_sec:.3f}s is inside the Cortney interruption")
    shift = 0.0
    if film_sec >= end:
        pointers = interruption_sources()
        shift = interruption_duration() - (
            pointers["resume"] - pointers["interrupt_in"])
    return source_for_bed(film_sec - shift, lead, runs)


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


# --- rendering -------------------------------------------------------------
# Until now this file described a cut nobody could rebuild. The delivered
# master was assembled by hand, which is why it went stale the moment the cut
# changed and why issue #88 had no upstream to fix. The recipe lives here now.

TARGET_W, TARGET_H, TARGET_FPS = 1920, 1080, 30

# THE BED'S SOURCE DECODES ABOVE FULL SCALE. Its fetched intermediate applies
# a -1.6 dB static gain before integer PCM encoding, so those peaks are retained
# rather than clipped. The mux therefore applies no second gain.
MUX_GAIN_DB = 0.0

# ISSUE #88, AND WHY EVERY CHAIN BELOW IS `-vf`.
#
# The identical normalising chain gives two different answers depending on how
# it is spelled. As `-vf` the act runs 307.99 s; wrapped in `-filter_complex`
# the same frames come out 299.48 s, about 2.8% fast, and ffmpeg discards 505
# frames whose rescaled timestamps collide -- exiting 0 while doing it. So:
# `-vf` only here, black is a real encoded clip joined by the concat DEMUXER
# rather than a filtergraph, and nothing in this path builds a filter_complex.
NORMALISE_VF = (
    f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease:"
    "flags=lanczos,"
    f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2,"
    f"fps={TARGET_FPS},format=yuv420p"
)
X264 = ["-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p"]


def _run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-12:])
        raise RuntimeError(f"ffmpeg failed:\n  {' '.join(map(str, cmd))}\n{tail}")


def _cut_run(ffmpeg, src, start, duration, out_path):
    """One kept run, normalised, silent.

    ``-ss`` goes AFTER ``-i``: ffmpeg decodes from zero and discards, so the
    in-point is exact on the source timeline. Input-side seeking rebases output
    timestamps to zero, which shifts the phase of the frame-rate conversion and
    changes which frames get duplicated -- measurably different picture from
    the same in-point, and this act is cut to a beat.
    """
    _run(list(ffmpeg) + [
        "-nostdin", "-v", "error", "-y", "-i", str(src),
        "-ss", f"{start:.3f}", "-t", f"{duration:.3f}",
        "-vf", NORMALISE_VF, *X264, "-an", str(out_path)])


def _black(ffmpeg, duration, out_path):
    """A real encoded black clip, so the concat demuxer can join it.

    The head and the tail are black under the song, and they are PICTURE: made
    here as clips rather than as a filtergraph pad, because a filtergraph is
    exactly what #88 says re-times this act.
    """
    _run(list(ffmpeg) + [
        "-nostdin", "-v", "error", "-y",
        "-f", "lavfi", "-i",
        f"color=c=black:s={TARGET_W}x{TARGET_H}:r={TARGET_FPS}:d={duration:.3f}",
        "-t", f"{duration:.3f}", *X264, "-an", str(out_path)])


def _concat(ffmpeg, parts, out_path, workdir):
    """Join the normalised parts with the concat DEMUXER.

    The list file is written into ``workdir`` rather than /tmp: a containerized
    ffmpeg only sees the bind-mounted home, so a /tmp path would resolve inside
    the container's own namespace and the join would fail on a missing file.
    """
    list_path = Path(workdir) / "efmb_concat.txt"
    list_path.write_text(
        "".join(f"file '{Path(p).resolve()}'\n" for p in parts), encoding="utf-8")
    try:
        _run(list(ffmpeg) + [
            "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_path), "-c", "copy", str(out_path)])
    finally:
        list_path.unlink(missing_ok=True)


def render(out_path=None, work_dir=None, verbose=True):
    """Build the act and compose its source, bed, and cleared hold audio."""
    from tools.render import find_ffmpeg
    from tools import audiomix

    plan = build()
    ffmpeg = find_ffmpeg()
    source = REPO_ROOT / "media" / f"{SOURCE_ID}.mp4"
    bed = REPO_ROOT / "media" / f"{BED_ID}.wav"
    hero = REPO_ROOT / "media" / f"{HERO_SOURCE_ID}.mp4"
    elevator = REPO_ROOT / "media" / f"{ELEVATOR_MUSIC_ID}.wav"
    for path, what in ((source, "picture source"), (bed, "music bed"),
                       (hero, "Cortney hero clip"),
                       (elevator, "cleared elevator music")):
        if not path.exists():
            raise SystemExit(
                f"missing {what}: {path}\nMedia is fetched, never committed -- "
                "see docs/cuts/02-endless-forms-most-beautiful.md.")

    renders = REPO_ROOT / "renders"
    renders.mkdir(exist_ok=True)
    work = Path(work_dir or renders / "efmb-parts")
    work.mkdir(parents=True, exist_ok=True)
    out_path = Path(out_path or renders / "efmb-hq.mp4")

    parts = []
    for i, piece in enumerate(plan["timeline"]):
        part = work / f"part_{i:02d}.mp4"
        if piece["kind"] == "source":
            if verbose:
                print(f"  source {fmt(piece['source_in'])} -> "
                      f"{fmt(piece['source_in'] + piece['duration'])}")
            _cut_run(ffmpeg, source, piece["source_in"], piece["duration"], part)
        elif piece["kind"] == "hero":
            if verbose:
                print(f"  Cortney hero {fmt(piece['source_in'])} -> "
                      f"{fmt(piece['source_in'] + piece['duration'])}")
            _cut_run(ffmpeg, hero, piece["source_in"], piece["duration"], part)
        else:
            if verbose:
                print(f"  black {piece['duration']:.3f}s ({piece['beat']})")
            _black(ffmpeg, piece["duration"], part)
        parts.append(part)

    silent = renders / "efmb-film-silent.mp4"
    if verbose:
        print(f"  joining {len(parts)} parts -> {silent.name}")
    _concat(ffmpeg, parts, silent, work)

    # audiomix needs an input track to mute under the bed and external clips.
    # This silent shell is lossless; it is replaced entirely by the composed
    # audio at the next step, while the already-encoded picture is copied.
    picture = renders / "efmb-film-audio-shell.mkv"
    _run(list(ffmpeg) + [
        "-nostdin", "-v", "error", "-y", "-i", str(silent),
        "-f", "lavfi", "-i",
        f"anullsrc=channel_layout=stereo:sample_rate=48000:d={plan['film_sec']:.3f}",
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "pcm_s24le",
        "-t", f"{plan['film_sec']:.3f}", str(picture)])

    if verbose:
        print("  mux: paused bed, Local Forecast, hero source audio; FLAC")
    regions = audiomix.plan_regions(plan["timeline"], bed_offset=0.0)
    audiomix.mux(picture, bed, regions, out_path, MUX_GAIN_DB,
                 ffmpeg=ffmpeg, codec="flac", media_dir=REPO_ROOT / "media")

    got = probe_duration(out_path)
    want = plan["film_sec"]
    if abs(got - want) > 0.25:
        raise RuntimeError(
            f"{out_path.name} is {got:.3f}s but the plan says {want:.3f}s. "
            "If the gap is ~2.8% the chain grew a -filter_complex -- see #88.")
    if verbose:
        print(f"  {out_path}  {got:.3f}s (plan {want:.3f}s)")
    return out_path


def build():
    bed = load_json(REPO_ROOT / "music" / f"{BED_ID}.json")
    bed_sec = float(bed["duration_sec"])
    source = REPO_ROOT / "media" / f"{SOURCE_ID}.mp4"
    src_sec = probe_duration(source) if source.exists() else 376.186

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

    source_picture = sum(b - a for a, b, _ in RUNS)

    # --- the head, derived from the music --------------------------------
    # Where does SYNC_ANCHOR_SRC sit in the picture, measuring only kept time?
    # The lead-in IS whatever puts the anchor on the beat. Deriving it rather
    # than typing it is what keeps the shield on the downbeat if a run moves,
    # and picture_offset_for_source raises if the anchor has been cut rather
    # than silently syncing to a frame that no longer plays.
    anchor_picture_offset = picture_offset_for_source(SYNC_ANCHOR_SRC)
    lead = SYNC_ANCHOR_FILM - anchor_picture_offset
    assert lead >= 0, (
        f"the anchor needs a lead of {lead:.3f}s -- there is more picture "
        "before the beat than the song has room for")

    tail = bed_sec - lead - source_picture
    assert tail >= -0.001, (
        f"picture overruns the song by {-tail:.3f}s; something must be cut")
    assert abs((lead + source_picture + tail) - bed_sec) < 0.001

    pointers = interruption_sources()
    start, resume = pointers["interrupt_in"], pointers["resume"]
    assert picture_offset_for_source(start) < picture_offset_for_source(resume)
    replaced = resume - start
    inserted = interruption_duration()
    picture = source_picture - replaced + inserted
    wall_sec = lead + picture + tail

    # One physical-picture timeline, and one audio timeline. Bed pieces name
    # their source clock explicitly so the source two-second replacement is
    # skipped rather than replayed beneath a later frame.
    timeline = [{
        "kind": "black",
        "duration": round(lead, 3),
        "beat": "Act II head black",
        "audio": "bed",
        "bed_from": 0.0,
    }]
    for a, b, why in RUNS:
        if a <= start < b:
            timeline.extend([
                {
                    "kind": "source",
                    "source_in": a,
                    "duration": round(start - a, 3),
                    "beat": why,
                    "audio": "bed",
                    "bed_from": round(bed_for_source(a, lead), 3),
                    "fade_out": AUDIO_FADE_SEC,
                },
                {
                    "kind": "black",
                    "duration": CORTNEY_PLATE_SEC,
                    "beat": "Cortney's authored plate over cleared Local Forecast",
                    "audio": "hold",
                    "audio_from": {
                        "video_id": ELEVATOR_MUSIC_ID,
                        "start_sec": ELEVATOR_MUSIC_IN,
                    },
                    "fade_in": AUDIO_FADE_SEC,
                },
                {
                    "kind": "hero",
                    "source_in": HERO_IN,
                    "duration": round(HERO_OUT - HERO_IN, 3),
                    "beat": "Cortney's hero clip",
                    "audio": "source",
                    "audio_from": {
                        "video_id": HERO_SOURCE_ID,
                        "start_sec": HERO_IN,
                    },
                },
                {
                    "kind": "black",
                    "duration": round(POST_HERO_BLACK_SEC, 3),
                    "beat": "Owner text and leader reactions",
                    "audio": "hold",
                    "audio_from": {
                        "video_id": ELEVATOR_MUSIC_ID,
                        "start_sec": ELEVATOR_MUSIC_IN + CORTNEY_PLATE_SEC,
                    },
                    "fade_in": AUDIO_FADE_SEC,
                    "fade_out": AUDIO_FADE_SEC,
                },
                {
                    "kind": "source",
                    "source_in": resume,
                    "duration": round(b - resume, 3),
                    "beat": why,
                    "audio": "bed",
                    "bed_from": round(bed_for_source(resume, lead), 3),
                    "fade_in": AUDIO_FADE_SEC,
                },
            ])
        else:
            timeline.append({
                "kind": "source",
                "source_in": a,
                "duration": round(b - a, 3),
                "beat": why,
                "audio": "bed",
                "bed_from": round(bed_for_source(a, lead), 3),
            })
    timeline.append({
        "kind": "black",
        "duration": round(tail, 3),
        "beat": "Act II black outro",
        "audio": "bed",
        "bed_from": round(lead + source_picture, 3),
    })
    assert round(sum(p["duration"] for p in timeline), 3) == round(wall_sec, 3)
    audible_bed = sum(p["duration"] for p in timeline if p["audio"] == "bed")
    assert round(audible_bed, 3) == round(bed_sec - replaced, 3)

    return {
        "act": "II",
        "title": "Endless Forms Most Beautiful",
        "source_id": SOURCE_ID,
        "bed_id": BED_ID,
        "source_duration_sec": round(src_sec, 3),
        "bed_duration_sec": round(bed_sec, 3),
        "picture_sec": round(picture, 3),
        "source_picture_sec": round(source_picture, 3),
        "gap_sec": round(bed_sec - source_picture, 3),
        "tail_policy": TAIL_POLICY,
        "sync_anchor_src": SYNC_ANCHOR_SRC,
        "sync_anchor_bed": SYNC_ANCHOR_FILM,
        "sync_anchor_wall": round(film_for_source(SYNC_ANCHOR_SRC, lead), 3),
        "bed_lead_sec": round(lead, 3),
        "bed_tail_sec": round(tail, 3),
        "film_sec": round(wall_sec, 3),
        "audible_bed_sec": round(audible_bed, 3),
        "interruption": {
            "source_in": start,
            "source_resume": resume,
            "source_replaced_sec": round(replaced, 3),
            "wall_in": round(interruption_wall_in(lead), 3),
            "wall_out": round(interruption_wall_out(lead), 3),
            "inserted_wall_sec": round(inserted, 3),
            "hero_source_id": HERO_SOURCE_ID,
            "hero_source": [HERO_IN, HERO_OUT],
            "elevator_music_id": ELEVATOR_MUSIC_ID,
        },
        "timeline": timeline,
        "runs": [{"in": a, "out": b, "sec": round(b - a, 3), "why": w}
                 for a, b, w in RUNS],
        "removed": [{"in": a, "out": b, "sec": round(b - a, 3), "why": w}
                    for a, b, w in REMOVED],
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    plan = build()

    if "--render" in argv:
        i = argv.index("--render")
        out = argv[i + 1] if len(argv) > i + 1 and not argv[i + 1].startswith("-") else None
        render(out_path=out)
        return 0

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
              f"bed {fmt(plan['sync_anchor_bed'])}, wall "
              f"{fmt(plan['sync_anchor_wall'])} (the downbeat)")
        print(f"  bed leads the picture by {plan['bed_lead_sec']:.3f}s")
        print(f"  black tail under the outro  {plan['bed_tail_sec']:.3f}s")
        print(f"  film {plan['film_sec']}s ({fmt(plan['film_sec'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
