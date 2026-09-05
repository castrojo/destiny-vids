#!/usr/bin/env python3
"""Build an act from its committed record.

Acts IV, V and VII had **no committed inputs at all** (#152). They were cut in
``~/Videos/wolves-*`` by ad-hoc ``run-*.sh`` scripts, so the words on screen
lived outside this repo, nothing here could edit them, and no check could tell
whether a revision took. That is precisely why the dictated Kat/Nat dialogue
round (#118) never landed: the words had no home.

This is the shared half of the fix. Each act commits a manifest -- the copy,
the windows, the measured letterbox and the encode parameters -- and a thin
front end (``scripts/build_kat.py``, ``scripts/build_natali.py``) points this
at it:

    python3 scripts/build_kat.py --print-command     # the ffmpeg call, no render
    python3 scripts/build_natali.py --plates-only    # just re-render the pills
    python3 scripts/build_kat.py                     # the delivered master
    python3 scripts/build_natali.py --variant variant_51

**The default builds what is actually delivered**, which is not what the
original scripts' defaults built. Both ``Prod/04`` and ``Prod/05`` hardlink a
FLAC stereo master, while ``run-kat.sh`` and ``run-natali.sh`` default to the
AAC 5.1 sibling. A committed builder that inherited those defaults would
quietly replace a lossless master with a lossy one and nothing would say so,
which is most of the reason to commit one.

FOOTAGE IS NEVER COMMITTED, so this reads the source, the bed and the avatars
from the project folder (``--project``) and reports what is missing rather
than substituting anything.

THE PLATES ARE RENDERED BY ``tools/plate.py``, this repo's own port of the
``plate.html`` pill the delivered masters were screenshotted from. On act IV
the port lands on the delivered geometry: with the act's measured letterbox
rect the two agree to 1px of width and 2px of height, and the top-left corner
is exact. It is a re-render, not the same bytes, so a rebuild is compared
before it is delivered rather than assumed identical.
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
from tools import chapter_md  # noqa: E402

# Each act's front end passes its own; nothing here is Kat-specific.
ACTS = {
    "IV": {"manifest": "stories/04-kat-plates.json",
           "project": "~/Videos/wolves-kat",
           "plates_dir": "renders/plates-04-kat"},
    "V": {"manifest": "stories/05-natali-plates.json",
          "project": "~/Videos/wolves-natali",
          "plates_dir": "renders/plates-05-natali"},
    "VII": {"manifest": "stories/07-europa-plates.json",
            "project": "~/Videos/wolves-directors-cut",
            "plates_dir": "renders/plates-07-europa"},
}


def act_paths(act):
    spec = ACTS[act]
    return (REPO_ROOT / spec["manifest"], Path(spec["project"]),
            REPO_ROOT / spec["plates_dir"])


def load_manifest(path):
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


def render_plates(doc, project, out_dir):
    """Render the dialogue pills from the manifest, into ``out_dir``."""
    x, y, w, h = picture_rect(doc)
    manifest = _project_manifest(doc, project)
    cmd = [sys.executable, str(REPO_ROOT / "tools" / "plate.py"), "render",
           "--manifest", str(manifest),
           "--out-dir", str(out_dir),
           "--picture", f"{x},{y},{w},{h}"]
    subprocess.run(cmd, check=True)
    return out_dir


def _resolve_avatar(project, value):
    """One manifest ``avatar`` -> the path the pill renderer should open.

    Canonical ``renders/avatars/<login>.png`` paths belong to this repository's
    shared avatar cache. Legacy bare filenames remain project-local, under
    ``<project>/render/``. Absolute and ``~``-rooted values pass through.
    """
    p = Path(value).expanduser()
    if p.is_absolute():
        return str(p)
    if len(p.parts) > 1:
        return str(REPO_ROOT / p)
    return str(Path(project).expanduser() / "render" / value)


def _project_manifest(doc, project):
    """The manifest with its avatar paths pointed at ``project``.

    Avatars are people's photographs and this repo commits none of them, so
    the record names where they live rather than carrying them. Resolving
    them here keeps the record portable and keeps the missing-file case a
    punch-list item -- ``plate.py`` falls back to the drawn crest and says
    which one it could not read.
    """
    out = dict(doc)
    out["plates"] = [
        {**p, "avatar": _resolve_avatar(project, p["avatar"])}
        if p.get("avatar") else dict(p)
        for p in doc["plates"]
    ]
    scratch = REPO_ROOT / "renders" / f".{Path(doc['_manifest_name']).stem}.resolved.json"
    scratch.parent.mkdir(parents=True, exist_ok=True)
    scratch.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return scratch


def overlay_chain(doc):
    """The ``filter_complex`` for the picture: base, the pills, the nameplate.

    Every overlay is one ``scale`` + a fade pair on the alpha channel, then an
    ``overlay`` gated by ``enable='between(...)'`` -- the shape the ad-hoc
    ``run-*.sh`` scripts used, generated from the record instead of written out
    by hand, so moving a window means editing the manifest and nothing else.

    An act whose picture fades to black at the end says so in ``trim`` and gets
    one final ``fade`` on the composited chain: act V's cinematic resolves into
    its own fade and the cut has to land with it, while act IV ends on a hard
    cut and carries none.
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
        last = i == len(_cues(doc))
        label = ("vout" if last and not trim.get("fade_out")
                 else f"t{i}")
        parts.append(f"[{prev}][o{i}]overlay=0:0:"
                     f"enable='between(t,{at:g},{out:g})'[{label}]")
        prev = label
    if trim.get("fade_out"):
        parts.append(f"[{prev}]fade=t=out:st={trim['fade_out_at']:g}:"
                     f"d={trim['fade_out']:g}[vout]")
    return parts


def _cues(doc):
    """Every timed overlay in input order: the pills, then the nameplate.

    The reveal goes LAST so it composites on top. It never shares the screen
    with a pill in either act -- act IV holds every line until after the card,
    and act V clears its last line 1.15 s before the card fades in -- so the
    order is about input numbering, not contention.
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
    bed_in = len(_cues(doc)) + 1
    if variant.get("sfx"):
        # The hybrid layer: gated source transients mixed UNDER the bed. Act V
        # rendered one and the owner rejected it by ear ("this one is
        # awesome" of the bed-only cut), so it is a variant and never a
        # default -- kept because a rejected experiment is provenance.
        pre = (f"[{bed_in}:a]atrim={trim['in']:g}:{trim['out']:g},"
               f"asetpts=PTS-STARTPTS[bed];"
               f"[{bed_in + 1}:a]atrim={trim['in']:g}:{trim['out']:g},"
               f"asetpts=PTS-STARTPTS[sfx];"
               f"[bed][sfx]amix=inputs=2:normalize=0[apre]")
    else:
        pre = (f"[{bed_in}:a]atrim={trim['in']:g}:{trim['out']:g},"
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


def build_command(doc, project, variant_key="delivered", plates_dir=None,
                  ffmpeg=None, out=None):
    """The whole ffmpeg call, assembled from the record."""
    project = Path(project).expanduser()
    variant = doc["encode"][variant_key]
    enc = doc["encode"]
    trim = doc["trim"]
    plates_dir = Path(plates_dir) if plates_dir else act_paths(doc["act"])[2]
    src = project / "sources" / doc["source_file"]
    bed = project / "render" / doc["bed"]["file"]
    target = Path(out).expanduser() if out else project / variant["out"]

    # `source_in` is where the act starts in the SOURCE; `in`/`out` are the
    # cut's own clock, which every window above is measured in. They differ
    # whenever an act is lifted out of the middle of a longer file (act V
    # starts at 357.45), and are the same when it starts at zero (act IV).
    cmd = [*(ffmpeg or find_ffmpeg()), "-y",
           "-ss", f"{trim.get('source_in', trim['in']):g}",
           "-t", f"{trim['out']:g}", "-i", str(src)]
    for cue in _cues(doc):
        # A cue with `file` is supplied by the project, not rendered from this
        # record -- the reveal nameplate is the one such cue, and why is in its
        # `_not_repo_rendered` note.
        img = (project / cue["file"]) if cue.get("file") else (
            Path(plates_dir) / f"plate_{cue['id']}.png")
        cmd += ["-itsoffset", f"{float(cue['at']):g}", "-loop", "1"]
        # A still's input framerate only matters where the original script set
        # one; act V left it at ffmpeg's default and its master was built that
        # way, so the record carries whether to pass it rather than this
        # deciding for both acts.
        if enc.get("loop_framerate"):
            cmd += ["-framerate", str(enc["loop_framerate"])]
        cmd += ["-t", f"{float(cue['dur']):g}", "-i", str(img)]
    cmd += ["-i", str(bed)]
    if variant.get("sfx"):
        cmd += ["-i", str(project / "render" / variant["sfx"])]

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


def load_act(act):
    """The act's manifest, tagged with the file it came from.

    THE COPY COMES FROM THE CHAPTER FILE, not from the manifest. An act with
    a ``chapters/<act>.md`` has its pills resolved from the Markdown the owner
    edits, and the manifest supplies only what the Markdown is not about --
    the trim, the measured letterbox, the encode parameters. That way a
    copyedit is one line in one readable file, and the manifest is an output.

    An act with no chapter file keeps its manifest's own plates, so this is
    additive: nothing has to be migrated for the build to work.
    """
    manifest, project, plates_dir = act_paths(act)
    doc = load_manifest(manifest)
    doc["_manifest_name"] = manifest.name
    plates, unresolved = chapter_md.entries(act)
    if plates:
        doc["plates"] = plates
        for note in unresolved:
            print(f"chapter: {note}", file=sys.stderr)
        doc["unresolved"] = [*doc.get("unresolved", []), *unresolved]
    return doc, project, plates_dir


def main(act, argv=None):
    """The shared CLI. ``scripts/build_kat.py`` and friends pass their numeral."""
    doc, default_project, default_plates = load_act(act)
    ap = argparse.ArgumentParser(
        description=f"Build act {act} ({doc['title']}) from its committed record.")
    ap.add_argument("--project", default=str(default_project),
                    help="where the footage, bed and avatars live "
                         "(never committed)")
    ap.add_argument("--variant", default="delivered",
                    choices=tuple(k for k, v in doc["encode"].items()
                                  if isinstance(v, dict)),
                    help="`delivered` is the FLAC stereo master this act's "
                         "Prod/ entry hardlinks")
    ap.add_argument("--out", default=None, help="override the output path")
    ap.add_argument("--plates-dir", default=str(default_plates))
    ap.add_argument("--print-command", action="store_true",
                    help="print the ffmpeg call and stop")
    ap.add_argument("--plates-only", action="store_true",
                    help="re-render the dialogue pills and stop")
    ap.add_argument("--skip-plates", action="store_true",
                    help="reuse the rendered pills already in --plates-dir")
    ap.add_argument("--local", action="store_true",
                    help="encode on THIS host even when the farm cluster is "
                         "reachable (the escape hatch; the encode runs under "
                         "tools.farm.run_capped_local's memory cap)")
    args = ap.parse_args(argv)

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

    missing = [p for p in (project / "sources" / doc["source_file"],
                           project / "render" / doc["bed"]["file"])
               if not p.exists()]
    if missing:
        for p in missing:
            print(f"actbuild: missing input {p}", file=sys.stderr)
        print("actbuild: footage is never committed -- stage the project "
              "folder or pass --project", file=sys.stderr)
        return 2

    if not args.skip_plates:
        render_plates(doc, project, Path(args.plates_dir))
    cmd, target = build_command(doc, project, args.variant,
                                Path(args.plates_dir), out=args.out)
    print(f"actbuild: act {act} -> {target}")
    # Remote by default (AGENTS.md): the act's one encode runs on the farm
    # whenever the cluster answers; a local run is the stated, memory-capped
    # fallback via tools.farm.run_capped_local.
    from tools import farm
    inputs = [Path(cmd[i + 1]) for i, tok in enumerate(cmd) if tok == "-i"]
    farm.run_encode(cmd, inputs=inputs, out=target, local=args.local,
                    expected_duration=float(doc["trim"]["out"]))
    return 0
