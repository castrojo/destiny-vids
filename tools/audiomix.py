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


def plan_regions(shots, bed_offset=0.0):
    """Walk a cut list and return its alternating source/bed regions.

    ``bed_offset`` is the wall time at which the song is first heard; the
    shots before it must be marked ``audio: "source"`` and are what plays
    instead. Regions are merged, so a run of twenty bed shots is one region.
    """
    regions = []
    wall = 0.0
    bed = 0.0
    for shot in shots:
        dur = float(shot["duration"])
        kind = "source" if shot.get("audio") == "source" else "bed"
        if regions and regions[-1]["kind"] == kind:
            regions[-1]["wall_end"] += dur
            if kind == "bed":
                regions[-1]["bed_end"] += dur
        else:
            r = {"kind": kind, "wall_start": wall, "wall_end": wall + dur}
            if kind == "bed":
                r["bed_start"] = bed
                r["bed_end"] = bed + dur
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


def build_filter(regions, bed_gain_db=0.0, source_gain_db=0.0):
    """The filtergraph: bed pieces delayed into place, source muted under them.

    Input 0 is the rendered picture (carrying its own source audio); input 1 is
    the bed.

    ``source_gain_db`` is the mirror of ``bed_gain_db`` and exists for the same
    reason. A diegetic insert brings its OWN peaks, and they are nobody's
    mastering decision -- so a cut whose bed is comfortably under the headroom
    gate can still be pushed over it by one loud explosion. Attenuating the
    source region is a static gain applied once, exactly like the bed's: it
    changes no dynamics, and it is preferable to a limiter, to `loudnorm`, or
    to pulling the whole film down and quietly re-levelling the music.
    """
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

    mute = "+".join(
        f"between(t,{r['wall_start']:.6f},{r['wall_end']:.6f})"
        for r in regions if r["kind"] == "bed")
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
        source_gain_db=0.0):
    """Mux the composed audio onto ``video``, stream-copying the picture."""
    if ffmpeg is None:
        from tools.render import find_ffmpeg

        ffmpeg = find_ffmpeg()
    cmd = list(ffmpeg) + [
        "-v", "error", "-y", "-i", str(video), "-i", str(bed),
        "-filter_complex", build_filter(regions, bed_gain_db, source_gain_db),
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
        source_gain_db=args.source_gain_db)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(REPO_ROOT))
    raise SystemExit(main())
