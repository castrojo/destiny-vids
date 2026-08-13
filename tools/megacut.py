#!/usr/bin/env python3
"""Ordered cuts and chapter cards -> one continuous programme.

This is the assembly stage: it takes finished deliverables that already exist
and joins them into one file, with the reference deck's title cards between
them. It edits nothing. Every segment it is handed is either a rendered cut
from this repo or an owner-approved deliverable from ``~/Videos``, and the
cards are PNGs rendered by ``tools/plate.py render``.

    python3 tools/megacut.py renders/megacut.json --out renders/megacut.mp4

Segment, then concatenate -- and still one generation
-----------------------------------------------------
This used to be **one** ``filter_complex`` over every input at once, on the
reasoning that normalising each segment to a temporary file and concatenating
the temporaries would re-encode every frame twice.

That reasoning was right about quality and wrong about whether it runs. On the
real programme -- fourteen inputs, half an hour of 1080p -- ffmpeg buffers the
inputs ``concat`` is not consuming yet, climbs to ~2 GB resident, and then
**deadlocks**: every thread in ``futex_do_wait``, 0% CPU, no output growth.
Measured twice, at two presets, stalling at the same point on the timeline. A
fourteen-input graph over *short* inputs completes fine, so the shape is not
the problem; the duration behind it is.

So each item is normalised to its own segment first, and the segments are then
joined with the **concat demuxer**. The generation count is unchanged, which is
the part worth protecting:

* **Video is encoded once.** Segments are encoded at the plan's own ``crf`` and
  ``preset``, and the join then uses ``-c:v copy``. Nothing is re-encoded, so
  this costs no quality against the single-pass form -- it only costs disk,
  briefly, in a temporary directory.
* **Audio is encoded once.** Segments carry **FLAC**, which is lossless, so the
  single AAC encode happens at the join, across the whole programme rather than
  per segment. Encoding AAC per segment and copying would have been the real
  quality regression: every join would carry its own encoder delay and padding,
  which is audible as a tick.

What "normalise" means here, and why each choice
------------------------------------------------
The segments genuinely disagree, so a re-encode is unavoidable:

* **Frame rate.** Sources run at 30/1, 60/1 and 60000/1001. ``concat`` requires
  one rate, and picking 60000/1001 keeps the 59.94 material untouched while the
  integer-rate material resamples predictably. Choosing 30 would throw away the
  60fps Guardian intros; choosing 60/1 would make the 59.94 cut drift against
  its own audio.
* **Audio.** Everything is 48 kHz 5.1, and it is passed through **unprocessed**
  -- no normaliser, no limiter, no EQ (the audio tenet). Silent segments get
  generated 5.1 silence of exactly matching length rather than being left with
  no stream, because ``concat`` needs every segment to carry both.
* **Colour.** BT.709 SDR is tagged explicitly. Untagged 1080p is *assumed* to be
  BT.709 by most players, but "most" is not a guarantee, and a mis-tagged master
  is invisible until someone grades against it.

Audio is re-encoded once to AAC. That is one generation of lossy-to-lossy loss
on segments whose deliverables are already AAC; it is recorded rather than
hidden, and the lossless-master path (see ``docs/skills/references/audio-standard.md``) is the upgrade
if a delivered master is ever wanted.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# 59.94, as a rational so ffmpeg never rounds it to 60.
DEFAULT_FPS = "60000/1001"
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080
DEFAULT_SAMPLE_RATE = 48000
DEFAULT_LAYOUT = "5.1"

# Named so a test can point them somewhere that does not exist. The system
# ffmpeg on an atomic Fedora/Bluefin host is `ffmpeg-free`, which has no H.264
# decoder, so these are preferred over PATH.
LINUXBREW_FFMPEG = "/home/linuxbrew/.linuxbrew/bin/ffmpeg"
SHIM_FFMPEG = str(Path.home() / ".local/bin/ffmpeg")


def ffmpeg_bin():
    """The ffmpeg that can actually decode H.264.

    On an atomic Fedora/Bluefin host the ``ffmpeg`` on PATH is ``ffmpeg-free``,
    which has no H.264 decoder and fails only once decoding starts -- which
    reads like a corrupt input file. Prefer the linuxbrew build, then the local
    container shim, and fall back to PATH.

    This never raises when no ffmpeg exists: *building* a command is pure
    string work, and the offline test suite has to be able to do it on a
    machine with no ffmpeg at all. A missing binary surfaces when the command
    is actually run, which is the only place it matters.
    """
    for candidate in (LINUXBREW_FFMPEG, SHIM_FFMPEG):
        if Path(candidate).exists():
            return candidate
    return shutil.which("ffmpeg") or "ffmpeg"


def ffprobe_bin():
    """The ffprobe beside the chosen ffmpeg."""
    ffmpeg = ffmpeg_bin()
    head, sep, tail = ffmpeg.rpartition("ffmpeg")
    return f"{head}ffprobe{tail}" if sep else "ffprobe"


def load_plan(path, require_sources=True):
    """Validate a plan. ``require_sources`` off reads a plan whose files are
    not built yet -- which is what ``--chapters`` needs, since the running order
    is a decision and the footage is not a precondition for recording it. Every
    other check still runs, and an item with no file must then carry its own
    ``dur`` or the arithmetic has nothing to work from.
    """
    plan = json.loads(Path(path).read_text())
    items = plan.get("items")
    if not items:
        raise ValueError("plan has no items")
    for i, item in enumerate(items):
        kind = item.get("kind")
        if kind not in ("card", "clip"):
            raise ValueError(f"item {i}: kind must be 'card' or 'clip', got {kind!r}")
        src = item.get("image") if kind == "card" else item.get("path")
        if not src:
            raise ValueError(f"item {i}: missing {'image' if kind == 'card' else 'path'}")
        if not resolve(src):
            if require_sources:
                raise ValueError(f"item {i}: source does not exist: {src}")
            if kind == "clip" and item.get("dur") is None:
                raise ValueError(
                    f"item {i}: {src} does not exist and the item has no `dur`, "
                    f"so its length is unknowable"
                )
        if kind == "card" and float(item.get("dur", 0)) <= 0:
            raise ValueError(f"item {i}: card needs a positive dur")
        if kind == "clip" and item.get("audio") not in ("source", "silent"):
            raise ValueError(
                f"item {i}: clip audio must be 'source' or 'silent' -- state it "
                f"explicitly, so a segment is never silently dropped to silence"
            )
        if kind == "clip" and "dur" in item and float(item["dur"]) <= 0:
            raise ValueError(f"item {i}: clip dur, when given, must be positive")
    return plan


def resolve(src, required=True):
    """The one path resolver: absolute wins, then repo-root, then cwd.

    Validation and encoding MUST agree on this. When the two disagreed, a
    relative path could be validated against the repo copy and then encoded
    from a different file of the same name in the working directory -- the file
    that was checked would not be the file that shipped.
    """
    p = Path(src)
    if p.is_absolute():
        return str(p) if not required or p.exists() else ""
    for candidate in (REPO_ROOT / src, Path.cwd() / src):
        if candidate.exists():
            return str(candidate)
    return "" if required else str(REPO_ROOT / src)


def build_inputs(plan, items=None):
    """ffmpeg input arguments, in item order."""
    args = []
    fps = plan.get("fps", DEFAULT_FPS)
    for item in (plan["items"] if items is None else items):
        if item["kind"] == "card":
            args += ["-loop", "1", "-framerate", fps,
                     "-t", str(item["dur"]), "-i", resolve(item["image"])]
        else:
            args += ["-i", resolve(item["path"])]
    return args


def build_filtergraph(plan, items=None):
    """A filter_complex that normalises one item into ``[vout]``/``[aout]``.

    ``items`` is a one-item list; the parameter is a list so the chains stay
    indexed exactly as they were when this built the whole programme at once.

    **There is no ``concat`` filter here, and that is load-bearing.** A segment
    holds one item, so ``concat=n=1`` looked like a harmless no-op that kept a
    single code path. It is not harmless: on one of the acts it re-timed the
    output, squeezing 307.967 s of frames into 299.48 s of timestamps, and the
    encoder then dropped the ~506 frames whose timestamps collided. The frame
    count going in and coming out matched, so nothing errored -- the programme
    was simply 8.5 s short, and every act after it started early.

    Measured on that file: the same chains WITHOUT concat give 307.99 s, with
    concat give 299.48 s. Other acts pass through concat unharmed, so this is a
    property of one source rather than of the filter in general -- which is
    exactly why the fix is to not ask for a concatenation of one thing.
    """
    fps = plan.get("fps", DEFAULT_FPS)
    w = int(plan.get("width", DEFAULT_WIDTH))
    h = int(plan.get("height", DEFAULT_HEIGHT))
    rate = int(plan.get("sample_rate", DEFAULT_SAMPLE_RATE))
    layout = plan.get("layout", DEFAULT_LAYOUT)

    items = plan["items"] if items is None else items
    chains, labels = [], []
    for i, item in enumerate(items):
        v, a = f"v{i}", f"a{i}"
        if item["kind"] == "card":
            dur = float(item["dur"])
            # The card is a transparent PNG in the deck's own geometry. Flatten
            # it onto real black rather than relying on yuv420p to drop alpha:
            # the colour under a fully transparent pixel is undefined, so
            # dropping alpha alone can reveal white fringing.
            chains.append(
                f"color=c=black:s={w}x{h}:r={fps}:d={dur}[bg{i}]"
            )
            chains.append(
                f"[{i}:v]scale={w}:{h}:flags=lanczos,format=rgba[fg{i}]"
            )
            chains.append(
                f"[bg{i}][fg{i}]overlay=0:0:shortest=1,"
                f"fps={fps},format=yuv420p,setsar=1,setpts=PTS-STARTPTS[{v}]"
            )
            chains.append(
                f"anullsrc=channel_layout={layout}:sample_rate={rate}:d={dur},"
                f"asetpts=PTS-STARTPTS[{a}]"
            )
        else:
            if item["audio"] == "silent":
                # Both legs are pinned to ONE duration so they are equal by
                # construction. Previously the silence was set to a probed or
                # authored scalar while the video leg ran its own natural
                # length: if the two disagreed, `concat` advanced each stream's
                # timeline independently and every segment after this one
                # drifted out of sync. Trimming the video to its own probed
                # duration is a no-op; trimming it to an authored `dur` is the
                # author's stated intent. Either way they cannot diverge.
                dur = item.get("dur")
                if dur is None:
                    dur = probe_duration(resolve(item["path"]), stream="v:0")
                chains.append(
                    f"[{i}:v]scale={w}:{h}:flags=lanczos,setsar=1,"
                    f"fps={fps},format=yuv420p,trim=duration={dur},"
                    f"setpts=PTS-STARTPTS[{v}]"
                )
                chains.append(
                    f"anullsrc=channel_layout={layout}:sample_rate={rate}:d={dur},"
                    f"asetpts=PTS-STARTPTS[{a}]"
                )
            else:
                chains.append(
                    f"[{i}:v]scale={w}:{h}:flags=lanczos,setsar=1,"
                    f"fps={fps},format=yuv420p,setpts=PTS-STARTPTS[{v}]"
                )
                # aresample only where the rate differs; aformat pins the layout
                # so concat sees one shape. No gain is applied anywhere.
                chains.append(
                    f"[{i}:a]aresample={rate},"
                    f"aformat=sample_fmts=fltp:channel_layouts={layout},"
                    f"asetpts=PTS-STARTPTS[{a}]"
                )
        labels += [f"[{v}][{a}]"]

    if len(items) != 1:
        raise ValueError(
            "build_filtergraph normalises exactly one item; the programme is "
            "joined by the concat DEMUXER, in build_concat_command")
    # `null`/`anull` rename the labels and do nothing else. Naming the outputs
    # keeps build_segment_command's -map arguments independent of the chain.
    chains.append(f"[v0]null[vout]")
    chains.append(f"[a0]anull[aout]")
    return ";".join(chains)


def probe_duration(path, stream=None):
    """Duration in seconds.

    ``stream="v:0"`` asks the video stream rather than the container. The two
    can disagree -- a container's ``format=duration`` covers its longest
    stream, so on a file whose audio outruns its picture it is the wrong number
    to cut silence against. Falls back to the container when a stream reports
    no duration of its own, which some muxers do.
    """
    probe = ffprobe_bin()
    if stream:
        out = subprocess.run(
            [probe, "-v", "error", "-select_streams", stream,
             "-show_entries", "stream=duration", "-of", "csv=p=0", path],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        if out and out.upper() != "N/A":
            return float(out)
    out = subprocess.run(
        [probe, "-v", "error",
         "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def segment_video_chain(plan, item):
    """The normalising video chain for a clip, as a plain -vf string."""
    fps = plan.get("fps", DEFAULT_FPS)
    w = int(plan.get("width", DEFAULT_WIDTH))
    h = int(plan.get("height", DEFAULT_HEIGHT))
    chain = (f"scale={w}:{h}:flags=lanczos,setsar=1,"
             f"fps={fps},format=yuv420p")
    if item["audio"] == "silent":
        # Both legs pinned to ONE duration so they are equal by construction.
        dur = item.get("dur")
        if dur is None:
            dur = probe_duration(resolve(item["path"]), stream="v:0")
        chain += f",trim=duration={dur}"
    return chain + ",setpts=PTS-STARTPTS"


def build_segment_command(plan, index, seg_path):
    """Encode one item to its own normalised segment.

    This is where the picture is encoded, at the plan's own quality, so the
    join can copy it. Audio is **24-bit PCM**: lossless, so carrying it here
    costs nothing but disk, and it keeps the single AAC encode at the join,
    where it spans the whole programme instead of restarting at every cut.

    PCM rather than FLAC, and that is not a preference. FLAC carries its
    STREAMINFO in the stream's extradata; the concat demuxer binds the first
    file's extradata to the joined stream, so every later segment decodes as
    "Invalid data found when processing input". Measured, not guessed. PCM has
    no extradata to mismatch.

    **A clip is filtered with -vf/-af, not -filter_complex, and that is
    load-bearing.** On one act -- 30 fps, timescale 1/15360 -- the identical
    chain run through ``-filter_complex`` came out 299.48 s instead of
    307.967 s, with ``drop=505`` frames: the filtered timestamps were rescaled
    and the colliding frames were discarded. The same chain as ``-vf`` gives
    307.99 s. The programme was 8.5 s short and every act after that one
    started early, while ffmpeg exited 0 and reported the full frame count
    going in. Cards keep the graph form because they need lavfi sources, and
    they are stills whose durations are authored rather than carried.

    Matroska, not MP4, because a segment is a temporary the concat demuxer
    reads back -- it never needs a faststart-able moov.
    """
    crf = str(plan.get("crf", 16))
    preset = plan.get("preset", "slow")
    rate = str(plan.get("sample_rate", DEFAULT_SAMPLE_RATE))
    layout = plan.get("layout", DEFAULT_LAYOUT)
    item = plan["items"][index]

    common = [
        "-c:v", "libx264", "-preset", preset, "-crf", crf,
        "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        # The three -color_* flags above describe the *frames*, and x264 only
        # copies the matrix from them -- primaries and transfer come out
        # `unknown`, which is a silent mismatch against every other deliverable
        # in ~/Videos/Wolves/Prod. Writing the VUI directly is the only way all
        # three actually land in the bitstream. It has to be written HERE, on
        # the segment: the join copies the bitstream, so whatever the VUI says
        # at this point is what ships. Verified by ffprobe, not assumed.
        "-x264-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709",
        "-c:a", "pcm_s24le", "-ar", rate,
        str(seg_path), "-y",
    ]

    if item["kind"] == "card":
        return [
            ffmpeg_bin(), "-nostdin", "-hide_banner",
            *build_inputs(plan, [item]),
            "-filter_complex", build_filtergraph(plan, [item]),
            "-map", "[vout]", "-map", "[aout]",
            *common,
        ]

    args = [ffmpeg_bin(), "-nostdin", "-hide_banner", "-i", resolve(item["path"])]
    if item["audio"] == "silent":
        dur = item.get("dur")
        if dur is None:
            dur = probe_duration(resolve(item["path"]), stream="v:0")
        args += ["-f", "lavfi", "-i",
                 f"anullsrc=channel_layout={layout}:sample_rate={rate}:d={dur}"]
        maps = ["-map", "0:v:0", "-map", "1:a:0", "-t", str(dur)]
        af = []
    else:
        maps = ["-map", "0:v:0", "-map", "0:a:0"]
        # aresample only where the rate differs; aformat pins the layout so the
        # join sees one shape. No gain is applied anywhere.
        af = ["-af", f"aresample={rate},"
                     f"aformat=sample_fmts=fltp:channel_layouts={layout}"]
    return [*args, "-vf", segment_video_chain(plan, item), *af, *maps, *common]


def build_concat_command(plan, list_path, out_path):
    """Join the segments: copy the picture, encode the sound once.

    ``-safe 0`` because the list holds absolute paths. The video is copied, so
    every segment must share codec parameters -- they do, by construction:
    ``build_segment_command`` encodes them all from the same plan.
    """
    abitrate = plan.get("audio_bitrate", "640k")
    return [
        ffmpeg_bin(), "-nostdin", "-hide_banner",
        "-f", "concat", "-safe", "0", "-i", str(list_path),
        "-map", "0:v:0", "-map", "0:a:0",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", abitrate,
        "-ar", str(plan.get("sample_rate", DEFAULT_SAMPLE_RATE)),
        "-movflags", "+faststart",
        str(out_path), "-y",
    ]


def assemble(plan, out_path, workdir=None, log=None):
    """Build every segment, then join them. Returns the output path.

    The segments land in a temporary directory that is removed afterwards --
    they are pure intermediates, and keeping them would invite somebody to
    hand-edit one, which is the failure this repo's regenerated-artifact rule
    exists to prevent.
    """
    log = log or (lambda msg: print(msg, file=sys.stderr))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ctx = (tempfile.TemporaryDirectory(prefix="megacut-", dir=workdir)
           if workdir is None else None)
    tmp = Path(ctx.name) if ctx else Path(workdir)
    try:
        segments = []
        for i, item in enumerate(plan["items"]):
            seg = tmp / f"seg{i:03d}.mkv"
            log(f"  segment {i + 1}/{len(plan['items'])}: {item.get('label', item['kind'])}")
            subprocess.run(build_segment_command(plan, i, seg), check=True)
            segments.append(seg)
        list_path = tmp / "segments.txt"
        list_path.write_text(
            "".join(f"file '{s}'\n" for s in segments), encoding="utf-8")
        log(f"  joining {len(segments)} segments")
        subprocess.run(build_concat_command(plan, list_path, out_path), check=True)
    finally:
        if ctx:
            ctx.cleanup()
    return out_path


def expected_duration(plan):
    total = 0.0
    for item in plan["items"]:
        if item["kind"] == "card":
            total += float(item["dur"])
        else:
            # `is None`, not `or`: a 0 would fall through to a probe and report
            # a length the graph does not build. build_filtergraph tests the
            # same way, and the two must not disagree about what "no dur" is.
            dur = item.get("dur")
            if dur is None:
                dur = probe_duration(resolve(item["path"]), stream="v:0")
            total += float(dur)
    return total


def chapters(plan):
    """The programme's chapter markers, derived from the plan's own clock.

    A chapter starts where its ACT SLIDE starts, not where the film behind it
    does: the slide is how the audience is told which act this is, so a marker
    landing after it would drop them into a card they have already read. The
    The title is the card's `chapter` -- an authored audience-facing string,
    NOT the item's `label`, which is a build note ("held long, by owner
    request"). It lives on the item so the running order and its markers cannot
    disagree; a card without one falls back to `label` and reads oddly, which is
    the visible failure that gets it filled in.

    Yielded as (seconds, title), so a caller can format them for YouTube, an
    ffmpeg metadata file, or a review note without this knowing about any of
    them.
    """
    out, t = [], 0.0
    for item in plan["items"]:
        if item["kind"] == "card":
            out.append((t, item.get("chapter") or item.get("label") or "Chapter"))
            t += float(item["dur"])
            continue
        dur = item.get("dur")
        if dur is None:
            dur = probe_duration(resolve(item["path"]), stream="v:0")
        t += float(dur)
    return out


def format_chapters(marks):
    """YouTube's chapter format: `H:MM:SS Title`, one per line.

    The first marker must be at zero or YouTube ignores the whole list, which
    holds here by construction -- the programme opens on act I's slide.
    """
    lines = []
    for seconds, title in marks:
        h, rem = divmod(int(seconds), 3600)
        m, s = divmod(rem, 60)
        stamp = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
        lines.append(f"{stamp} {title}")
    return "\n".join(lines)


def parse_stamp(text):
    """Read a review note's timecode: `12:43`, `1:02:11`, `763`, `12:43.5`."""
    parts = str(text).strip().split(":")
    if len(parts) > 3 or not all(parts):
        raise ValueError(f"not a timecode: {text!r}")
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + float(part)
    return seconds


def locate(plan, seconds):
    """Which act is playing at `seconds`, and how far into it.

    The whole point of a review loop is that a note is taken against the
    PROGRAMME clock -- "12:43 looks wrong" -- while a fix is made against an
    ACT: its own project, its own file, its own timeline. Doing that arithmetic
    by hand, per note, off a chapter list is where a round of notes silently
    gets applied to the wrong act.

    Returns (title, offset_into_that_item, path_or_None). A card is an act
    slide, so a note landing on one is a note about the slide, not the film.

    The title is the act's, not the item's: a clip carries a `label` that is a
    build note ("held long, by owner request"), so an act's film is reported
    under the chapter its own SLIDE announced. That is what the audience --
    and therefore the note -- calls it.
    """
    t = 0.0
    act = None
    for item in plan["items"]:
        dur = item.get("dur")
        if dur is None:
            dur = probe_duration(resolve(item["path"]), stream="v:0")
        dur = float(dur)
        if item["kind"] == "card":
            act = item.get("chapter") or item.get("label")
        if seconds < t + dur or item is plan["items"][-1]:
            title = act or item.get("label") or item.get("path") or "?"
            return title, round(seconds - t, 3), item.get("path")
        t += dur
    raise ValueError("empty plan")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("plan", help="JSON assembly plan")
    ap.add_argument("--out", help="output file (overrides the plan's `output`)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the command and the expected duration, encode nothing")
    ap.add_argument("--chapters", action="store_true",
                    help="print the chapter markers and exit, encoding nothing")
    ap.add_argument("--locate", metavar="TC", nargs="+",
                    help="turn review-note timecodes on the PROGRAMME clock "
                         "(12:43, 1:02:11, 763) into the act that is playing "
                         "and the offset inside its own file; encodes nothing")
    ap.add_argument("--workdir",
                    help="keep the intermediate segments here instead of a "
                         "temporary directory (they are large; for debugging a join)")
    args = ap.parse_args(argv)

    plan = load_plan(args.plan, require_sources=not (args.chapters or args.locate))
    if args.chapters:
        print(format_chapters(chapters(plan)))
        return 0

    if args.locate:
        for stamp in args.locate:
            seconds = parse_stamp(stamp)
            title, offset, path = locate(plan, seconds)
            m, s = divmod(offset, 60)
            where = f"{int(m)}:{s:06.3f}"
            print(f"{stamp:>9}  ->  {title}  @ {where}"
                  + (f"  [{path}]" if path else "  [act slide]"))
        return 0

    out_path = args.out or plan.get("output")
    if not out_path:
        raise SystemExit("no output: pass --out or set `output` in the plan")

    if args.dry_run:
        for i, item in enumerate(plan["items"]):
            print(" ".join(build_segment_command(plan, i, f"seg{i:03d}.mkv")))
        print(" ".join(build_concat_command(plan, "segments.txt", out_path)))
        print(f"# expected duration: {expected_duration(plan):.3f}s "
              f"across {len(plan['items'])} items")
        return 0

    print(f"assembling {len(plan['items'])} items -> {out_path}", file=sys.stderr)
    assemble(plan, out_path, workdir=args.workdir)
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
