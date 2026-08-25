#!/usr/bin/env python3
"""Build the intermission slide deck that plays after the mrbobbytables act.

WHERE THE WORDS ARE. Not here. Every slide is authored at the bottom of
``chapters/III-mrbobbytables.md``, under the block whose heading carries the
label its front matter declares in ``deck:``. That is the owner's
arrangement and the reason this builder exists at all: the deck is the
concluding text of Bob's scene, so it is edited where the rest of his scene
is edited rather than in a manifest, a table of constants, or a file of its
own.

    python3 scripts/build_intermission.py --write     # the manifest
    python3 scripts/build_intermission.py --render    # the film

``stories/03-intermission-plates.json`` is an OUTPUT. It is committed so the
punch list can find the deck's unwritten copy -- ``tools/placeholder.py``
reads committed JSON, and a deck that existed only as Markdown would report
as zero unwritten words, which is the one direction that tool must never be
wrong in. Never hand-edit it; edit the chapter file and re-run ``--write``.

THE DECK IS SILENT, ON PURPOSE AND NOT FOREVER. Owner, 2026-08-23: *"I want
to put a different song here eventually for now I need the text
placeholder."* So the slot is real, the timing is reviewable, and the audio
is a hole somebody is going to fill rather than a decision this script made.
The bed goes on the megacut item, beside the picture, the same way every
other segment's audio does.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import chapter_md, conform
from tools import plate as plate_mod
from tools.render import find_ffmpeg

ACT = "III"
MANIFEST = REPO / "stories" / "03-intermission-plates.json"
CARDS = REPO / "renders" / "intermission" / "cards"
OUT = REPO / "renders" / "intermission" / "03-intermission.mp4"

FPS = "60000/1001"
FADE = 0.5
# Air after the last slide clears, so the deck ends on black rather than on a
# cut out of a word. Long enough to read as a beat, short enough that it is
# not mistaken for the film having stopped.
TAIL = 0.8


def slides():
    """The deck's plates, on their own clock, and anything unresolved."""
    return chapter_md.deck_entries(ACT)


def duration(plates):
    return round(max(p["at"] + p["dur"] for p in plates) + TAIL, 3)


def document(plates, unresolved):
    return {
        "_what": (
            "The intermission slide deck that plays after act III and "
            "Perfume's third movement. GENERATED from the deck block in "
            "chapters/III-mrbobbytables.md -- edit the chapter file, then "
            "run `python3 scripts/build_intermission.py --write`."),
        "act": ACT,
        "source": "chapters/III-mrbobbytables.md",
        "film_sec": duration(plates),
        "unresolved": list(unresolved) + [
            "no bed is cleared or chosen for the intermission yet. Owner, "
            "2026-08-23: 'I want to put a different song here eventually "
            "for now I need the text placeholder.' The deck renders silent "
            "and the megacut item carries no audio until one is picked.",
            "every word on these slides is lorem ipsum. `python3 "
            "tools/placeholder.py list` names them; replacing the copy is "
            "one edit to the chapter file and one `--write`.",
        ],
        "plates": plates,
    }


def write_manifest(path=MANIFEST):
    plates, unresolved = slides()
    text = json.dumps(document(plates, unresolved), indent=1) + "\n"
    Path(path).write_text(text, encoding="utf-8")
    return text


def command(plates, total, cards_dir, out, ffmpeg=None):
    """Slides over black, each fading in and out on its authored seat.

    Overlay rather than concat: the seats and holds are authored in the
    chapter file, so the graph places each card at the moment it says and
    the black between them is whatever is left. A concat would re-derive
    those gaps and could disagree with the words.
    """
    paths = [Path(cards_dir) / f"plate_{p['id']}.png" for p in plates]
    missing = [path for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing intermission slide: {missing[0]}")

    graph = [f"color=c=black:s=1920x1080:r={FPS}:d={total}[bg]"]
    last = "[bg]"
    for i, (spec, _) in enumerate(zip(plates, paths)):
        out_start = spec["dur"] - FADE
        graph.append(
            f"[{i}:v]format=rgba,fade=t=in:st=0:d={FADE}:alpha=1,"
            f"fade=t=out:st={out_start:.3f}:d={FADE}:alpha=1,"
            f"setpts=PTS-STARTPTS+{spec['at']:.3f}/TB[s{i}]")
        graph.append(
            f"{last}[s{i}]overlay=0:0:eof_action=pass:"
            f"enable='between(t,{spec['at']:.3f},"
            f"{spec['at'] + spec['dur']:.3f})'[o{i}]")
        last = f"[o{i}]"
    graph.append(f"{last}format=yuv420p[vout]")

    return [
        *(ffmpeg or find_ffmpeg()),
        "-hide_banner", "-y",
        *sum((["-loop", "1", "-framerate", FPS, "-t", str(spec["dur"]),
               "-i", str(path)]
              for spec, path in zip(plates, paths)), []),
        "-filter_complex", ";".join(graph),
        "-map", "[vout]",
        "-t", str(total),
        *conform.video_encode_args(),
        "-an", "-movflags", "+faststart", str(out),
    ]


def render(cards_dir=CARDS, out=OUT, local=False):
    plates, _ = slides()
    if not plates:
        raise SystemExit(
            f"act {ACT}'s chapter file declares a deck but authors no slides")
    Path(cards_dir).mkdir(parents=True, exist_ok=True)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    plate_mod.render_all(plates, cards_dir)

    total = duration(plates)
    argv = command(plates, total, cards_dir, out)
    paths = [Path(cards_dir) / f"plate_{p['id']}.png" for p in plates]

    # ENCODING IS REMOTE BY DEFAULT (AGENTS.md). Twenty-seven seconds of
    # stills is not why -- the rule is that the cluster runs the encode
    # whenever it is reachable, because this workstation is also running the
    # session that asked for the film. Local is a fallback with a reason,
    # never a silent default -- and never an unbounded one: it runs under
    # farm.run_capped_local's memory cap.
    from tools import farm
    why = "--local given"
    if not local:
        # cluster_available() returns (ok, why_not) -- and a bare tuple is
        # ALWAYS truthy, which is exactly how this check once "worked" while
        # never actually falling back. Unpack it.
        ok, probe_why = farm.cluster_available()
        if ok:
            farm.run_ffmpeg_on_cluster(argv, inputs=paths, out=Path(out),
                                       name="intermission")
            return out
        why = f"the cluster is not reachable ({probe_why})"
        print(f"build_intermission: {why}; encoding locally",
              file=sys.stderr)
    farm.run_capped_local(argv, reason=why, check=True)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true",
                    help="regenerate the committed manifest")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the manifest is not what the chapter "
                         "file produces")
    ap.add_argument("--render", action="store_true", help="draw and encode")
    ap.add_argument("--local", action="store_true",
                    help="encode here instead of on the cluster")
    ap.add_argument("--print-command", action="store_true")
    args = ap.parse_args(argv)

    plates, unresolved = slides()
    for note in unresolved:
        print(f"chapter: {note}", file=sys.stderr)

    if args.check:
        want = json.dumps(document(plates, unresolved), indent=1) + "\n"
        have = MANIFEST.read_text(encoding="utf-8") if MANIFEST.exists() else ""
        if want != have:
            print(f"{MANIFEST.relative_to(REPO)} is not what "
                  "chapters/III-mrbobbytables.md produces -- run "
                  "`python3 scripts/build_intermission.py --write`",
                  file=sys.stderr)
            return 1
        print(f"{len(plates)} intermission slide(s) agree with the chapter file")
        return 0

    if args.write:
        write_manifest()
        print(f"wrote {MANIFEST.relative_to(REPO)} "
              f"({len(plates)} slides, {duration(plates)}s)")

    if args.print_command:
        from tools.render import ffmpeg_for_printing
        print(" ".join(ffmpeg_for_printing(
            command(plates, duration(plates), CARDS, OUT))))

    if args.render:
        render(local=args.local)
        print(f"wrote {OUT.relative_to(REPO)} ({duration(plates)}s, silent)")

    if not (args.write or args.render or args.print_command):
        for spec in plates:
            print(f"  {spec['at']:>6.3f} +{spec['dur']:.1f}  {spec['id']:<18}"
                  f" {spec.get('title') or spec.get('label') or ''}")
        print(f"{len(plates)} slide(s), {duration(plates)}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
