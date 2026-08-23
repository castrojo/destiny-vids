#!/usr/bin/env python3
"""Build act VII (Europa, the director's cut) from its committed record.

Thin front end on ``scripts/actbuild.py`` the way ``build_kat.py`` is, but
act VII is the one act whose picture is not a single source: it is an eight-
segment concat (the intro split around a native Jupiter video, two films, an
outro sting and a comic-cover still) with its own audio join, and the
delivered master is derived from that concat by cutting the cover off. So this
script reuses actbuild's record loading, plate rendering and avatar resolution,
and adds the three things the shared builder has never needed:

* the concat picture graph, compiled from the record's ``picture`` block
  (an input feeding two segments is split, never opened twice);
* the audio join from the record's ``audio`` block -- one leg (the song
  alone, a full replacement, which is what ships) or two crossfaded, with
  both fades optional, because the shipped mix has none;
* the nocover derivation: peaks-gate the 108.333333 s master (#82), then cut
  the delivered 95.4 s film from it with the picture STREAM-COPIED -- never
  re-encoded -- and the audio trimmed to 95.333333 s, faded only if the
  record asks for a fade.

    python3 scripts/build_europa.py --print-command     # the ffmpeg calls
    python3 scripts/build_europa.py --plates-only       # just the pills
    python3 scripts/build_europa.py                     # the delivered master

The default builds what is actually delivered: the FLAC stereo nocover master
that ``Prod/07-europa.mp4`` hardlinks to. FOOTAGE IS NEVER COMMITTED -- the
record names where every input lives and this reports what is missing rather
than substituting anything. The Prod/ re-link and ``deliver.py publish`` are
the delivery session's job, deliberately NOT done here (run-final-hq.sh's
``ln -f`` into Prod/ is not inherited).
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import actbuild  # noqa: E402
from tools.render import find_ffmpeg  # noqa: E402

ACT = "VII"


def _cues(doc):
    """Every timed overlay in input order: the pills, then the live cards.

    The reveal and the endcard are project-supplied full-frame PNGs (both carry
    authored copy this record must never rewrite) and composite last, in that
    order, so the endcard can take over the frame the moment the reveal
    clears. They never share the screen with each other or with a pill.

    A cue marked ``retired`` (the KubeCon endcard, owner 2026-08-16) stays in
    the record -- copy is recoverable, never rewritten -- but is excluded
    here, so it creates no still input and no overlay filter.
    """
    cues = [*doc["plates"], doc["reveal"]]
    if doc.get("endcard") and not doc["endcard"].get("retired"):
        cues.append(doc["endcard"])
    return [cue for cue in cues if not cue.get("retired")]


def _segment_chain(seg, in_label, out_label):
    """One concat segment's filter chain, from the record's ``picture`` block.

    Field order matters for two segments and the record says so explicitly:
    the walk-up's ``fps_first`` conforms the 24 fps source BEFORE its frame
    trim (the frame numbers are counted on the 30 fps conversion), while the
    speeder's ``window`` is a time trim on the native stream conformed after.
    """
    chain = []
    if seg.get("fps_first"):
        chain.append(f"fps={seg['fps_first']:g}")
    if seg.get("frames"):
        chain.append(f"trim=start_frame={seg['frames'][0]}:"
                     f"end_frame={seg['frames'][1]}")
    elif seg.get("window"):
        chain.append(f"trim={seg['window'][0]}:{seg['window'][1]}")
    chain.append("setpts=PTS-STARTPTS")
    if seg.get("fps") and not seg.get("fps_first"):
        chain.append(f"fps={seg['fps']:g}")
    if seg.get("scale_pad"):
        sp = seg["scale_pad"]
        chain.append(f"scale={sp['side']}:{sp['side']}")
        chain.append(f"pad=1920:1080:{sp['x']}:0:black")
    elif seg.get("scale"):
        chain.append("scale=1920:1080")
    chain.append("setsar=1")
    if seg.get("still"):
        chain.append("format=yuv420p")
    if seg.get("fade_in"):
        f = seg["fade_in"]
        chain.append(f"fade=t=in:st={f['at']:g}:d={f['dur']:g}")
    if seg.get("fade_out"):
        f = seg["fade_out"]
        chain.append(f"fade=t=out:st={f['at']:g}:d={f['dur']:g}")
    return f"[{in_label}]{','.join(chain)}[{out_label}]"


def picture_graph(doc):
    """The concat half of the filter graph; returns (parts, base_label).

    Segments compile in RECORD order -- that order is the concat order. An
    input feeding two segments is split, never opened twice: frame-exact by
    construction, the way the shipped graph did it.
    """
    pic = doc["picture"]
    counts = {}
    for seg in pic["segments"]:
        counts[seg["from"]] = counts.get(seg["from"], 0) + 1
    parts = []
    for name, n in counts.items():
        if n > 1:
            idx = list(pic["inputs"]).index(name)
            parts.append(f"[{idx}:v]split={n}"
                         + "".join(f"[i{idx}x{k}]" for k in range(n)))
    used, concat_in = {}, []
    for n, seg in enumerate(pic["segments"]):
        idx = list(pic["inputs"]).index(seg["from"])
        if counts[seg["from"]] > 1:
            k = used.get(seg["from"], 0)
            used[seg["from"]] = k + 1
            in_label = f"i{idx}x{k}"
        else:
            in_label = f"{idx}:v"
        parts.append(_segment_chain(seg, in_label, f"s{n}"))
        concat_in.append(f"s{n}")
    parts.append("".join(f"[{c}]" for c in concat_in)
                 + f"concat=n={len(concat_in)}:v=1:a=0[base]")
    return parts, "base"


def overlay_graph(doc, base, first_input):
    """The pill/card overlays on top of the concat, from the record's cues.

    Same house shape actbuild generates for the single-source acts -- a fade
    pair on the alpha channel and a half-open ``gte*lt`` enable, so a plate's
    fade completes inside its window and it can never ghost into the next
    shot -- but keyed off this build's own input numbering.
    """
    parts = []
    prev = base
    cues = _cues(doc)
    for n, cue in enumerate(cues):
        i = first_input + n
        at, dur = float(cue["at"]), float(cue["dur"])
        out = at + dur
        parts.append(
            f"[{i}:v]scale=1920:1080,"
            f"fade=t=in:st={at:g}:d={cue['fade_in']:g}:alpha=1,"
            f"fade=t=out:st={cue['fade_out_at']:g}:d={cue['fade_out']:g}"
            f":alpha=1[o{i}]")
        label = "vout" if n == len(cues) - 1 else f"t{i}"
        parts.append(f"[{prev}][o{i}]overlay=0:0:"
                     f"enable='gte(t,{at:g})*lt(t,{out:g})'[{label}]")
        prev = label
    return parts


def audio_graph(doc):
    """The record's ``join``, however many legs it has.

    One leg is a FULL REPLACEMENT -- the song alone, no crossfade -- and is
    what the act currently ships. Two legs are crossfaded. The fades are
    optional in both cases, because the shipped mix has none, and a builder
    that hard-codes them cannot express the act it is supposed to build.
    """
    pic, aud = doc["picture"], doc["audio"]
    parts = []
    labels = []
    for leg in aud["join"]:
        idx = list(pic["inputs"]).index(leg["from"])
        w = leg["window"]
        label = f"a{len(labels)}"
        chain = f"[{idx}:a]atrim={w[0]}:{w[1]},asetpts=PTS-STARTPTS"
        if leg.get("format"):
            chain += (",aformat=sample_fmts=fltp:sample_rates=48000:"
                      "channel_layouts=stereo")
        chain += f"[{label}]"
        parts.append(chain)
        labels.append(label)

    if len(labels) == 1:
        tail = f"[{labels[0]}]"
    else:
        tail = (f"[{labels[0]}][{labels[1]}]"
                f"acrossfade=d={aud['crossfade']:g}:c1=tri:c2=tri,")
    fade = aud.get("master_fade_out")
    if fade:
        tail += f"afade=t=out:st={fade['at']:g}:d={fade['dur']:g},"
    elif len(labels) == 1:
        tail += "anull,"
    parts.append(f"{tail}atrim=0:{pic['master_sec']:g}[aout]")
    return parts


def build_commands(doc, project, plates_dir, master_out, delivered_out,
                   ffmpeg=None):
    """The three commands: master, peaks gate, nocover derivation."""
    project = Path(project).expanduser()
    pic, enc = doc["picture"], doc["encode"]
    ff = list(ffmpeg or find_ffmpeg())
    paths = {name: (Path(p).expanduser() if Path(p).expanduser().is_absolute()
                    else project / p)
             for name, p in pic["inputs"].items()}

    cmd = [*ff, "-y"]
    for name, path in paths.items():
        seg = next((s for s in pic["segments"]
                    if s["from"] == name and s.get("still")), None)
        if seg:
            cmd += ["-loop", "1", "-framerate", str(enc["loop_framerate"]),
                    "-t", f"{seg['dur']:g}"]
        cmd += ["-i", str(path)]
    first_cue = len(paths)
    plates_dir = Path(plates_dir)
    for cue in _cues(doc):
        img = (project / cue["file"]) if cue.get("file") else (
            plates_dir / f"plate_{cue['id']}.png")
        cmd += ["-itsoffset", f"{float(cue['at']):g}", "-loop", "1"]
        if enc.get("loop_framerate"):
            cmd += ["-framerate", str(enc["loop_framerate"])]
        cmd += ["-t", f"{float(cue['dur']):g}", "-i", str(img)]

    pic_parts, base = picture_graph(doc)
    graph = ";".join([*pic_parts,
                      *overlay_graph(doc, base, first_cue),
                      *audio_graph(doc)])
    cmd += ["-filter_complex", graph, "-map", "[vout]", "-map", "[aout]",
            "-c:v", enc["vcodec"], "-preset", enc["preset"],
            "-crf", str(enc["crf"]), "-pix_fmt", enc["pix_fmt"],
            "-colorspace", enc["colorspace"],
            "-color_primaries", enc["colorspace"],
            "-color_trc", enc["colorspace"],
            "-c:a", doc["encode"]["delivered"]["acodec"],
            "-movflags", "+faststart", str(master_out)]

    # The delivered film: the cover (95.333333-108.333333) is CUT, picture
    # stream-copied from the peaks-gated master so no generation is added,
    # audio faded and trimmed to land the outro with the picture. The video
    # cut is by FRAME COUNT: with -c:v copy, -t flushes the two reordered
    # B-frames past the boundary (2864 frames instead of 2862), so the record
    # carries the delivered frame count and the cut is -frames:v.
    audio = doc["audio"]
    fade = audio.get("delivered_fade_out")
    af = f"afade=t=out:st={fade['at']:g}:d={fade['dur']:g}," if fade else ""
    derive = [*ff, "-y", "-i", str(master_out),
              "-map", "0:v", "-c:v", "copy",
              "-frames:v", str(pic["delivered_frames"]),
              "-map", "0:a",
              "-af", f"{af}atrim=0:{pic['audio_sec']:g}",
              "-c:a", doc["encode"]["delivered"]["acodec"],
              "-movflags", "+faststart", str(delivered_out)]
    return cmd, derive


def main(argv=None):
    doc, default_project, default_plates = actbuild.load_act(ACT)
    ap = argparse.ArgumentParser(
        description=f"Build act {ACT} ({doc['title']}) from its committed "
                    "record.")
    ap.add_argument("--project", default=str(default_project),
                    help="where the footage, cards and avatars live "
                         "(never committed)")
    ap.add_argument("--out", default=None,
                    help="override the delivered (nocover) output path")
    ap.add_argument("--plates-dir", default=str(default_plates))
    ap.add_argument("--master-out", default=None,
                    help="where the 108.333333 s peaks-gated master "
                         "intermediate is written (default <project>/"
                         "nimbatus-review/render/repo-build/"
                         "wolves-master-hq.mp4)")
    ap.add_argument("--print-command", action="store_true",
                    help="print the ffmpeg calls and stop")
    ap.add_argument("--plates-only", action="store_true",
                    help="re-render the dialogue pills and stop")
    ap.add_argument("--skip-plates", action="store_true",
                    help="reuse the rendered pills already in --plates-dir")
    ap.add_argument("--farm", action="store_true",
                    help="run the master encode on the farm cluster "
                         "(tools.farm.run_ffmpeg_on_cluster); the peaks trim "
                         "and the nocover derive are stream-copies and stay "
                         "local")
    args = ap.parse_args(argv)

    project = Path(args.project).expanduser()
    delivered = (Path(args.out).expanduser() if args.out else
                 project / doc["encode"]["delivered"]["out"])
    master = (Path(args.master_out).expanduser() if args.master_out else
              project / "nimbatus-review" / "render" / "repo-build"
              / "wolves-master-hq.mp4")

    if args.plates_only:
        actbuild.render_plates(doc, project, Path(args.plates_dir))
        return 0

    cmd, derive = build_commands(doc, project, Path(args.plates_dir),
                                 master, delivered, ffmpeg=["ffmpeg"])
    if args.print_command:
        print(" ".join(cmd))
        print()
        print(" ".join(derive))
        print(f"\n-> {master} -> {delivered}", file=sys.stderr)
        return 0

    missing = []
    for name, p in doc["picture"]["inputs"].items():
        path = Path(p).expanduser()
        if not path.is_absolute():
            path = project / p
        if not path.exists():
            missing.append(path)
    for cue in _cues(doc):
        if cue.get("file") and not (project / cue["file"]).exists():
            missing.append(project / cue["file"])
    if missing:
        for p in missing:
            print(f"build_europa: missing input {p}", file=sys.stderr)
        print("build_europa: footage is never committed -- stage the project "
              "folder or pass --project", file=sys.stderr)
        return 2

    if not args.skip_plates:
        actbuild.render_plates(doc, project, Path(args.plates_dir))
    master.parent.mkdir(parents=True, exist_ok=True)
    ff = find_ffmpeg()
    cmd, derive = build_commands(doc, project, Path(args.plates_dir),
                                 master, delivered)
    print(f"build_europa: act {ACT} master -> {master}")
    if args.farm:
        from tools import farm
        inputs = [Path(cmd[i + 1]) for i, tok in enumerate(cmd)
                  if tok == "-i"]
        farm.run_ffmpeg_on_cluster(cmd, inputs=inputs, out=master,
                                   expected_duration=108.333333)
    else:
        subprocess.run(cmd, check=True)
    # The delivered-peak gate (#82): static trim into the -0.9..-1.1 dBTP
    # band, video stream-copied. Runs on the 110.2 s master BEFORE the cover
    # is cut, so the delivered film's picture is copied from the gated master.
    subprocess.run([sys.executable, str(REPO_ROOT / "tools" / "peaks.py"),
                    "trim", str(master), "--ffmpeg", shlex.join(ff)],
                   check=True)
    print(f"build_europa: nocover -> {delivered}")
    subprocess.run(derive, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
