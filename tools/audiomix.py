#!/usr/bin/env python3
"""Compose a cut's audio when the bed does not run end to end.

``tools/render.py --audio`` lays one file over a finished cut and calls it
done. That is the right answer whenever the song plays from first frame to
last. It cannot express the two things this project actually wants:

  * a **pre-roll** -- the film opens on its own source audio and the song
    enters later, over picture that is already running;
  * a **pause** -- the song stops, a moment plays in its own audio, and the
    song resumes *from where it stopped* rather than from where it would have
    been.

Both are the same mechanic: the cut has **two clocks**. ``wall`` is position in
the film; ``bed`` is position in the song. A shot marked ``audio: "source"``
advances wall and **not** bed. Everything else follows from that -- including
the fact that a musical with a pause in it is longer than its own song, which
is why every anchor in the builder is asserted against bed time.

Two more non-bed dispositions exist for the interruption (issue #104), and
they are different promises, not synonyms:

  * ``silent`` -- a deliberate silence, forever. The picture's own audio is
    muted and nothing replaces it (the held beat before the slide appears).
  * ``hold`` -- the hold-music slot. Silent TODAY, because no cleared track
    exists on this machine and music is a licensing decision, which is one of
    the two things that stop work here. When the owner picks one it is wired
    in with ``audio_from``, exactly like a source swap. The kind exists so
    that the slot is a recorded, greppable place rather than a silence
    nobody can tell apart from the deliberate one beside it.

A shot carrying any other ``audio`` value is an error, not a bed shot: a typo
must fail loudly, because the bed-clock arithmetic is load-bearing.

    plan = plan_regions(shots, bed_offset=20.166)
    mux(video, bed_wav, plan, out="cut.mp4", bed_gain_db=-3.5)

The bed is cut into as many pieces as there are gaps, each delayed to its wall
position, and the source audio is muted wherever the bed is playing. Nothing is
mixed on top of anything: at every instant exactly one of the two is audible,
which is what "pause the song" means and what ducking would not achieve.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Non-bed dispositions (see the module docstring). ``source`` may carry
#: ``audio_from``; ``hold`` is the slot that will, once a track is cleared;
#: ``silent`` never does.
NON_BED_KINDS = ("source", "silent", "hold")


def plan_regions(shots, bed_offset=0.0):
    """Walk a cut list and return its alternating source/bed regions.

    ``bed_offset`` is the wall time at which the song is first heard; the
    shots before it must be marked ``audio: "source"`` and are what plays
    instead. Regions are merged, so a run of twenty bed shots is one region.

    A non-bed shot may carry ``audio_from`` -- ``{"video_id", "start_sec"}``,
    the start in THAT source's own clock -- when what is heard is not the
    picture's own audio. That is how a cleared hold-music track will reach
    the ``hold`` regions (issue #104; the slot is silent until the owner
    picks one). Regions merge only when kind AND ``audio_from`` agree; a
    ``bed`` or ``silent`` shot carrying one is an error, because it would
    never be heard there.
    """
    regions = []
    wall = 0.0
    bed = 0.0
    for shot in shots:
        dur = float(shot["duration"])
        audio = shot.get("audio") or "bed"
        if audio == "bed":
            kind = "bed"
        elif audio in NON_BED_KINDS:
            kind = audio
        else:
            raise ValueError(
                f"{shot.get('beat', '?')!r}: unknown audio disposition "
                f"{audio!r} -- expected one of 'bed', {', '.join(NON_BED_KINDS)}. "
                "An unrecognised value must not silently become bed time: the "
                "bed clock is load-bearing.")
        audio_from = shot.get("audio_from")
        if audio_from is not None and kind not in ("source", "hold"):
            raise ValueError(
                f"{shot.get('beat', '?')!r}: audio_from on a {kind!r} shot "
                "would never be heard -- nothing plays there")
        if (regions and regions[-1]["kind"] == kind
                and regions[-1].get("audio_from") == audio_from):
            regions[-1]["wall_end"] += dur
            if kind == "bed":
                regions[-1]["bed_end"] += dur
        else:
            r = {"kind": kind, "wall_start": wall, "wall_end": wall + dur}
            if kind == "bed":
                r["bed_start"] = bed
                r["bed_end"] = bed + dur
            if audio_from is not None:
                r["audio_from"] = audio_from
            regions.append(r)
        wall += dur
        if kind == "bed":
            bed += dur

    if regions:
        first_bed = next((r for r in regions if r["kind"] == "bed"), None)
        if first_bed and abs(first_bed["wall_start"] - bed_offset) > 0.05:
            raise ValueError(
                f"the bed first plays at wall {first_bed['wall_start']:.3f}s but "
                f"bed_offset says {bed_offset:.3f}s -- the pre-roll shots and the "
                "declared offset disagree")
    return regions


def total_bed(regions):
    return sum(r["bed_end"] - r["bed_start"] for r in regions if r["kind"] == "bed")


def total_wall(regions):
    return regions[-1]["wall_end"] if regions else 0.0


def resolve_audio_inputs(regions, media_dir=None):
    """Map each ``audio_from`` video_id to its media file, as extra inputs.

    Returns ``{video_id: path}`` in first-use order; input 0 is the picture
    and input 1 the bed, so the filter numbers them from 2 in dict order.
    """
    from tools.render import resolve_media

    paths = {}
    for r in regions:
        af = r.get("audio_from")
        if not af:
            continue
        vid = af["video_id"]
        if vid in paths:
            continue
        path = resolve_media(vid, media_dir) if media_dir else None
        if path is None:
            raise ValueError(
                f"{vid!r}: audio_from names a source that is not in "
                f"{media_dir} -- fetch it first. NOTE: resolve_media knows "
                "only video containers; an audio-only hold-music track "
                "(issue #104) will need an extension added there too.")
        paths[vid] = path
    return paths


def build_filter(regions, bed_gain_db=0.0, source_gain_db=0.0,
                 audio_inputs=None):
    """The filtergraph: bed pieces delayed into place, source muted under them.

    Input 0 is the rendered picture (carrying its own source audio); input 1 is
    the bed; ``audio_inputs`` maps a video_id to its input number (2 and up)
    for source regions whose audio comes from a different file than the
    picture.

    ``source_gain_db`` is the mirror of ``bed_gain_db`` and exists for the same
    reason. A diegetic insert brings its OWN peaks, and they are nobody's
    mastering decision -- so a cut whose bed is comfortably under the headroom
    gate can still be pushed over it by one loud explosion. Attenuating the
    source region is a static gain applied once, exactly like the bed's: it
    changes no dynamics, and it is preferable to a limiter, to `loudnorm`, or
    to pulling the whole film down and quietly re-levelling the music.
    """
    audio_inputs = audio_inputs or {}
    parts = []
    labels = []
    for i, r in enumerate(x for x in regions if x["kind"] == "bed"):
        lab = f"b{i}"
        delay = int(round(r["wall_start"] * 1000))
        chain = (f"[1:a]atrim=start={r['bed_start']:.6f}:end={r['bed_end']:.6f},"
                 f"asetpts=PTS-STARTPTS")
        if bed_gain_db:
            # A static gain, applied once. Not loudnorm and not a limiter: the
            # record's dynamics are the artist's (see docs/skills/scoring.md).
            chain += f",volume={bed_gain_db}dB"
        chain += f",adelay={delay}|{delay}[{lab}]"
        parts.append(chain)
        labels.append(lab)

    # Non-bed regions whose audio is another file's: the picture is muted
    # there too, and the named source plays instead -- trimmed in ITS OWN
    # clock (audio_from.start_sec) and delayed to the region's wall position.
    # This is also how a cleared hold-music track will play under the
    # interruption's `hold` regions (issue #104).
    for j, r in enumerate(x for x in regions
                          if x["kind"] != "bed" and x.get("audio_from")):
        lab = f"s{j}"
        start = float(r["audio_from"]["start_sec"])
        dur = r["wall_end"] - r["wall_start"]
        idx = audio_inputs[r["audio_from"]["video_id"]]
        delay = int(round(r["wall_start"] * 1000))
        chain = (f"[{idx}:a]atrim=start={start:.6f}:end={start + dur:.6f},"
                 f"asetpts=PTS-STARTPTS")
        if source_gain_db:
            chain += f",volume={source_gain_db}dB"
        chain += f",adelay={delay}|{delay}[{lab}]"
        parts.append(chain)
        labels.append(lab)

    # The picture's own track is audible ONLY in a source region playing its
    # own audio. Bed regions mute it; silent and hold regions mute it too --
    # a deliberate silence is only silence if the picture is muted there, and
    # the hold slot is silent until it carries an audio_from of its own.
    muted = [r for r in regions
             if r["kind"] != "source" or r.get("audio_from")]
    mute = "+".join(
        f"between(t,{r['wall_start']:.6f},{r['wall_end']:.6f})" for r in muted)
    src = "[0:a]"
    if source_gain_db:
        src += f"volume={source_gain_db}dB,"
    src += "volume=0:enable='" + (mute or "0") + "'[src]"
    parts.append(src)

    inputs = "".join(f"[{l}]" for l in labels) + "[src]"
    parts.append(f"{inputs}amix=inputs={len(labels) + 1}:normalize=0:"
                 f"dropout_transition=0[aout]")
    return ";".join(parts)


def mux(video, bed, regions, out, bed_gain_db=0.0, ffmpeg=None, bitrate="320k",
        source_gain_db=0.0, media_dir=None):
    """Mux the composed audio onto ``video``, stream-copying the picture."""
    if ffmpeg is None:
        from tools.render import find_ffmpeg

        ffmpeg = find_ffmpeg()
    audio_paths = resolve_audio_inputs(regions, media_dir)
    # Input 0 is the picture, 1 the bed, then the audio_from files in
    # first-use order -- the same order build_filter numbers them.
    audio_inputs = {vid: i + 2 for i, vid in enumerate(audio_paths)}
    cmd = list(ffmpeg) + ["-v", "error", "-y", "-i", str(video), "-i", str(bed)]
    cmd += [arg for path in audio_paths.values() for arg in ("-i", str(path))]
    cmd += [
        "-filter_complex",
        build_filter(regions, bed_gain_db, source_gain_db, audio_inputs),
        "-map", "0:v:0", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", bitrate, "-ar", "48000",
        str(out),
    ]
    subprocess.run(cmd, check=True)
    return Path(out)


def main(argv=None):
    import argparse

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("shotlist")
    ap.add_argument("--video", required=True)
    ap.add_argument("--bed", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--bed-offset", type=float, default=0.0)
    ap.add_argument("--bed-gain-db", type=float, default=0.0)
    ap.add_argument("--source-gain-db", type=float, default=0.0,
                    help="static gain on the diegetic-insert regions, "
                         "so their own peaks cannot breach the headroom gate")
    ap.add_argument("--media", default=None,
                    help="media directory, needed when a source region "
                         "carries audio_from (its video_id resolves there)")
    args = ap.parse_args(argv)

    doc = json.loads(Path(args.shotlist).read_text())
    shots = doc["shots"] if isinstance(doc, dict) else doc
    regions = plan_regions(shots, args.bed_offset)
    for r in regions:
        span = f"{r['wall_start']:8.3f} -> {r['wall_end']:8.3f}"
        extra = (f"   bed {r['bed_start']:8.3f} -> {r['bed_end']:8.3f}"
                 if r["kind"] == "bed" else "")
        print(f"  {r['kind']:6s} wall {span}{extra}")
    print(f"  bed used {total_bed(regions):.3f}s over {total_wall(regions):.3f}s of film")
    mux(args.video, args.bed, regions, args.out, args.bed_gain_db,
        source_gain_db=args.source_gain_db, media_dir=args.media)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(REPO_ROOT))
    raise SystemExit(main())
