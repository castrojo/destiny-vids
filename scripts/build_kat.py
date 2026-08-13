#!/usr/bin/env python3
"""Build act IV (Kat Cosgrove) from its committed record.

Act IV had **no committed inputs at all** (#152). It was cut entirely in
``~/Videos/wolves-kat`` by an ad-hoc ``render/run-kat.sh``, so the words on
screen lived outside this repo, nothing here could edit them, and no check
could tell whether a revision took. That is exactly why the dictated Kat
dialogue round (#118) never landed: *the words had no home*.

This script is that home's other half. ``stories/04-kat-plates.json`` holds the
copy, the windows and the measured build parameters; this reads them and
produces the film:

    python3 scripts/build_kat.py --print-command     # the ffmpeg call, no render
    python3 scripts/build_kat.py --plates-only       # just re-render the pills
    python3 scripts/build_kat.py                     # the delivered master
    python3 scripts/build_kat.py --variant variant_51

**The default builds what is actually delivered**, which is not what the
original script's defaults built. ``~/Videos/Wolves/Prod/04-kat.mp4`` hardlinks
``wolves-kat-reveal-hq.mp4``: FLAC, stereo. ``run-kat.sh``'s defaults produce
the *other* file, the AAC 5.1 sibling. Defaulting to the delivered variant is
the whole point of a committed builder -- a rebuild that silently swapped the
two would replace a lossless master with a lossy one and nothing would say so.

FOOTAGE IS NEVER COMMITTED, so this reads the source, the music bed and the
avatars from the project folder (``--project``, default ``~/Videos/wolves-kat``)
and reports what is missing rather than substituting anything.

THE PLATES ARE RENDERED BY ``tools/plate.py``, this repo's own port of the
``plate.html`` pill the delivered master was screenshotted from. The port lands
on the delivered geometry: with the act's measured letterbox rect the two agree
to **1px of width and 2px of height, and the top-left corner is exact**. It is
a re-render, not the same bytes, so a rebuild is compared before it is
delivered rather than assumed identical.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.render import find_ffmpeg  # noqa: E402

MANIFEST = REPO_ROOT / "stories" / "04-kat-plates.json"
DEFAULT_PROJECT = Path("~/Videos/wolves-kat")
PLATES_DIR = REPO_ROOT / "renders" / "plates-04-kat"


def load_manifest(path=MANIFEST):
    with Path(path).open(encoding="utf-8") as fh:
        return json.load(fh)


def picture_rect(doc):
    """The act's MEASURED letterbox, as ``plate.py --picture`` wants it.

    Measured, not probed: ``detect_picture`` needs the footage present and its
    probe lands at 40 s, past the end of this 34 s act, so it returns nothing
    and the plates would seat against the raw frame.
    """
    lb = doc["letterbox"]
    return 0, lb["active_y"], 1920, lb["active_height"]


def render_plates(doc, project, out_dir=PLATES_DIR):
    """Render the dialogue pills from the manifest, into ``out_dir``."""
    x, y, w, h = picture_rect(doc)
    manifest = _project_manifest(doc, project)
    cmd = [sys.executable, str(REPO_ROOT / "tools" / "plate.py"), "render",
           "--manifest", str(manifest),
           "--out-dir", str(out_dir),
           "--picture", f"{x},{y},{w},{h}"]
    subprocess.run(cmd, check=True)
    return out_dir


def _project_manifest(doc, project):
    """The manifest with its avatar paths pointed at ``project``.

    The committed manifest names avatars by FILE NAME, not by path: they are
    people's photographs and this repo commits none of them. Resolving them
    against the project folder here keeps the record portable and keeps the
    missing-file case a punch-list item -- ``plate.py`` falls back to the drawn
    crest and says which one it could not read.
    """
    out = dict(doc)
    out["plates"] = [
        {**p, "avatar": str(Path(project).expanduser() / "render" / p["avatar"])}
        if p.get("avatar") else dict(p)
        for p in doc["plates"]
    ]
    scratch = REPO_ROOT / "renders" / ".04-kat-plates.resolved.json"
    scratch.parent.mkdir(parents=True, exist_ok=True)
    scratch.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return scratch


def overlay_chain(doc):
    """The ``filter_complex`` for the picture: base, five pills, the nameplate.

    Every overlay is one ``scale`` + a fade pair on the alpha channel, then an
    ``overlay`` gated by ``enable='between(...)'`` -- the shape ``run-kat.sh``
    used, generated from the record instead of written out by hand, so moving a
    window means editing the manifest and nothing else.
    """
    trim = doc["trim"]
    parts = [f"[0:v]trim={trim['in']:g}:{trim['out']:g},"
             f"setpts=PTS-STARTPTS,setsar=1[base]"]
    prev = "base"
    for i, cue in enumerate(_cues(doc), start=1):
        at, dur = float(cue["at"]), float(cue["dur"])
        out = at + dur
        parts.append(
            f"[{i}:v]scale=1920:1080,"
            f"fade=t=in:st={at:g}:d={cue['fade_in']:g}:alpha=1,"
            f"fade=t=out:st={cue['fade_out_at']:g}:d={cue['fade_out']:g}:alpha=1"
            f"[o{i}]")
        label = "vout" if i == len(_cues(doc)) else f"t{i}"
        parts.append(f"[{prev}][o{i}]overlay=0:0:"
                     f"enable='between(t,{at:g},{out:g})'[{label}]")
        prev = label
    return parts


def _cues(doc):
    """Every timed overlay in input order: the pills, then the nameplate.

    The reveal goes LAST so it composites on top -- it never shares the screen
    with a pill (nothing precedes it, and the first pill starts 1.2 s after the
    card is gone), so the order is about input numbering, not contention.
    """
    return [*doc["plates"], doc["reveal"]]


def audio_chain(doc, variant):
    """The audio graph. Stereo passes through; 5.1 adds an LFE and nothing else.

    The delivered master is the stereo branch: ``anull``, i.e. the bed reaches
    the encoder untouched. The 5.1 branch carries the artist's stereo mix
    bit-exact as FL/FR and derives an LFE additively -- FC/BL/BR are digital
    silence. No upmix, no EQ, no loudness processing, and deliberately NOT
    ffmpeg's ``surround`` filter, which resynthesises the soundfield and adds
    ~43 ms of latency that would desync audio from picture.
    """
    trim = doc["trim"]
    pre = (f"[{len(_cues(doc)) + 1}:a]atrim={trim['in']:g}:{trim['out']:g},"
           f"asetpts=PTS-STARTPTS[apre]")
    if not variant.get("surround"):
        return [pre, "[apre]anull[aout]"]
    gain, low = variant["lfe_gain"], variant["lfe_low"]
    return [pre,
            "[apre]asplit=2[m51s][lfes]",
            "[m51s]pan=5.1|FL=c0|FR=c1[m51]",
            f"[lfes]pan=mono|c0=0.5*c0+0.5*c1,"
            f"lowpass=f={low}:poles=2,lowpass=f={low}:poles=2,"
            f"volume={gain},pan=5.1|LFE=c0[l51]",
            "[m51][l51]amix=inputs=2:normalize=0[aout]"]


def build_command(doc, project, variant_key="delivered", plates_dir=PLATES_DIR,
                  ffmpeg=None, out=None):
    """The whole ffmpeg call, assembled from the record."""
    project = Path(project).expanduser()
    variant = doc["encode"][variant_key]
    enc = doc["encode"]
    trim = doc["trim"]
    src = project / "sources" / f"{doc['source_id']}.mkv"
    bed = project / "render" / doc["bed"]["file"]
    target = Path(out).expanduser() if out else project / variant["out"]

    cmd = [*(ffmpeg or find_ffmpeg()), "-y",
           "-ss", f"{trim['in']:g}", "-t", f"{trim['out']:g}", "-i", str(src)]
    for cue in _cues(doc):
        # A cue with `file` is supplied by the project, not rendered from this
        # record -- the reveal nameplate is the one such cue, and why is in its
        # `_not_repo_rendered` note.
        img = (project / cue["file"]) if cue.get("file") else (
            Path(plates_dir) / f"plate_{cue['id']}.png")
        cmd += ["-itsoffset", f"{float(cue['at']):g}",
                "-loop", "1", "-framerate", str(enc["fps"]),
                "-t", f"{float(cue['dur']):g}",
                "-i", str(img)]
    cmd += ["-i", str(bed)]

    graph = ";".join([*overlay_chain(doc), *audio_chain(doc, variant)])
    cmd += ["-filter_complex", graph, "-map", "[vout]", "-map", "[aout]",
            "-c:v", enc["vcodec"], "-preset", enc["preset"],
            "-crf", str(enc["crf"]), "-pix_fmt", enc["pix_fmt"],
            "-colorspace", enc["colorspace"],
            "-color_primaries", enc["colorspace"],
            "-color_trc", enc["colorspace"],
            "-c:a", variant["acodec"]]
    # A bitrate is meaningless for a lossless codec, so it is omitted rather
    # than passed a -b:a the encoder would ignore.
    if variant.get("audio_bitrate"):
        cmd += ["-b:a", variant["audio_bitrate"]]
    cmd += ["-movflags", "+faststart", "-t", f"{trim['out']:g}", str(target)]
    return cmd, target


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", default=str(DEFAULT_PROJECT),
                    help="where the footage, bed and avatars live "
                         "(never committed)")
    ap.add_argument("--variant", default="delivered",
                    choices=("delivered", "variant_51"),
                    help="`delivered` is FLAC stereo, what Prod/04 hardlinks")
    ap.add_argument("--out", default=None, help="override the output path")
    ap.add_argument("--plates-dir", default=str(PLATES_DIR))
    ap.add_argument("--print-command", action="store_true",
                    help="print the ffmpeg call and stop")
    ap.add_argument("--plates-only", action="store_true",
                    help="re-render the dialogue pills and stop")
    ap.add_argument("--skip-plates", action="store_true",
                    help="reuse the rendered pills already in --plates-dir")
    args = ap.parse_args(argv)

    doc = load_manifest()
    project = Path(args.project).expanduser()

    if args.plates_only:
        render_plates(doc, project, Path(args.plates_dir))
        return 0

    if args.print_command:
        cmd, target = build_command(doc, project, args.variant,
                                    Path(args.plates_dir), ffmpeg=["ffmpeg"],
                                    out=args.out)
        print(" ".join(cmd))
        print(f"\n-> {target}", file=sys.stderr)
        return 0

    missing = [p for p in (project / "sources" / f"{doc['source_id']}.mkv",
                           project / "render" / doc["bed"]["file"])
               if not p.exists()]
    if missing:
        for p in missing:
            print(f"build_kat: missing input {p}", file=sys.stderr)
        print("build_kat: footage is never committed -- stage the project "
              "folder or pass --project", file=sys.stderr)
        return 2

    if not args.skip_plates:
        render_plates(doc, project, Path(args.plates_dir))
    cmd, target = build_command(doc, project, args.variant,
                                Path(args.plates_dir), out=args.out)
    print(f"build_kat: -> {target}")
    subprocess.run(cmd, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
