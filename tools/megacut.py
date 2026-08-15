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
* **Audio is encoded once.** Segments carry **24-bit PCM**, which is lossless,
  so the single AAC encode happens at the join, across the whole programme
  rather than per segment. Encoding AAC per segment and copying would have
  been the real quality regression: every join would carry its own encoder
  delay and padding, which is audible as a tick. PCM rather than FLAC because
  FLAC's STREAMINFO lives in the stream's extradata and the concat demuxer
  binds the first file's extradata to the whole joined stream -- every later
  segment then fails to decode.

What "normalise" means here, and why each choice
------------------------------------------------
The segments genuinely disagree, so a re-encode is unavoidable:

* **Frame rate.** Sources run at 30/1, 60/1 and 60000/1001. ``concat`` requires
  one rate, and picking 60000/1001 keeps the 59.94 material untouched while the
  integer-rate material resamples predictably. Choosing 30 would throw away the
  60fps Guardian intros; choosing 60/1 would make the 59.94 cut drift against
  its own audio.
* **Audio.** Everything is 48 kHz **stereo**, and it is passed through
  **unprocessed**
  -- no normaliser, no limiter, no EQ (the audio tenet). The one exception is
  an **explicit fade**: a clip may carry ``fade_in``/``fade_out`` (seconds, on
  the ACT FILM clock -- the clip's own timeline, so a fade never moves when
  the running order does), which the segment encode applies with ``afade``.
  That is the act-join treatment from issue #105: an act enters dry out of the
  slide's digital silence unless its head is faded, and several acts end hot
  unless their tail is. A fade is a stated, reproducible shape in the plan --
  not a limiter, not a normaliser. How loud one act is against another is a
  mix decision and belongs to the owner; when the owner takes it, the plan
  records it as an explicit per-clip ``gain_db`` (a plain static gain, applied
  before the fades -- the first was act I, 9.1 LU under the show, #164), and
  no gain is ever applied that the plan does not state. ``crescendo_out`` plus
  ``crescendo_db`` may return an attenuated clip to unity over its final
  seconds; validation refuses a pair that would boost above the source level.
  Silent segments
  get generated silence, in the plan's own layout and of exactly matching
  length, rather than being left
  with no stream, because ``concat`` needs every segment to carry both.
* **Colour.** BT.709 SDR is tagged explicitly. Untagged 1080p is *assumed* to be
  BT.709 by most players, but "most" is not a guarantee, and a mis-tagged master
  is invisible until someone grades against it.

Audio is re-encoded once to AAC. That is one generation of lossy-to-lossy loss
on segments whose deliverables are already AAC; it is recorded rather than
hidden, and the lossless-master path (see ``docs/skills/references/audio-standard.md``) is the upgrade
if a delivered master is ever wanted.

The stream-copy path, and what it costs to earn it
--------------------------------------------------
The normalising re-encode exists because delivered acts disagree (30/1, 60/1
and 60000/1001 in one programme). But once an act HAS been normalised,
re-normalising it on every assembly is pure waste: measured here, the full
programme costs ~24 minutes of sequential x264 for ~20 minutes of picture.
So the encode moved out of the loop:

* ``tools/conform.py`` owns the delivery spec (60000/1001, 1080p, yuv420p,
  BT.709 VUI, H.264 High@4.2, closed GOP) and a cache keyed by
  (source content hash + spec version). ``assemble()`` ensures every clip's
  source is conformant BEFORE building segments; an unchanged act is a cache
  hit and costs a stat.
* A clip whose source conforms builds its segment with **``-c:v copy``** --
  the picture is remuxed, never re-encoded -- while the audio is decoded,
  filtered (``aresample``/``aformat``/the plan's explicit ``afade``) and
  written as PCM s24le exactly as before. The lossless-audio chain is
  unchanged: FLAC never goes in a segment (the extradata trap above), and no
  gain ever touches the sound.
* Cards still encode -- they are generated from PNGs -- but they encode to
  the same spec, so their bitstream joins the copied ones. A card on other
  settings would force the whole programme back onto the slow path.
* ``--jobs N`` builds segments (and first-run conforms) in parallel with a
  ProcessPoolExecutor. x264 scales sublinearly past ~8 threads, so several
  workers at fewer threads each beat one worker at all of them; the default
  is ``min(cpu_count() // 6, items)``. The concat list is written from the
  plan's index order, never from completion order -- order is the programme.

A plan that does not target the delivery spec (another fps or frame size)
takes the original per-segment encode path unchanged. ``verify_segment`` and
``verify_programme`` run on BOTH paths -- the copy path is exactly where a
silent re-time would hide, so that is where the checks must not come off.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import conform  # noqa: E402  (the delivery spec + conform cache)

# 59.94, as a rational so ffmpeg never rounds it to 60.
DEFAULT_FPS = "60000/1001"
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080
DEFAULT_SAMPLE_RATE = 48000
# STEREO, because every file in the chain is (issue #146). The default said
# "5.1" for months while all seven acts, every Prod/ master and every delivered
# megacut were two-channel -- so `aformat` matched a stereo source against a
# 5.1 layout, `anullsrc` spliced 5.1 silence between stereo segments, and the
# bitrate default below was a 5.1 number. Owner confirmed 2026-08-14: the show
# is delivered stereo. A stereo->5.1 upmix here would be assembly inventing a
# soundfield, which the audio tenet forbids; if 5.1 is ever wanted it belongs
# in the per-cut scripts that already know what is in the mix.
DEFAULT_LAYOUT = "stereo"
# The AAC request for the distribution copy. It reads like a 5.1 number and it
# is not one any more: ffmpeg's native AAC encoder clamps stereo to its own
# ceiling, so asking for 640k asks for THE CEILING -- measured at ~439 kb/s on
# every delivered megacut. Asking for a "correct-looking" stereo number like
# 320k would ship a WORSE file, which is the trap issue #146 nearly set. The
# real fix for the join is a LOSSLESS programme master (issue #145), not a
# different lossy number.
DEFAULT_AUDIO_BITRATE = "640k"

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
        if "trim_to" in item:
            if kind != "clip":
                raise ValueError(
                    f"item {i}: trim_to belongs on a CLIP -- a card's length "
                    f"is its authored `dur`, not a cut into a film")
            try:
                trim_to = float(item["trim_to"])
            except (TypeError, ValueError):
                raise ValueError(
                    f"item {i}: trim_to must be seconds of ACT FILM time, "
                    f"got {item['trim_to']!r}")
            if trim_to <= 0:
                raise ValueError(f"item {i}: trim_to must be positive")
            if "dur" in item and abs(float(item["dur"]) - trim_to) > 1e-6:
                raise ValueError(
                    f"item {i}: dur ({item['dur']}s) and trim_to ({trim_to}s) "
                    f"disagree about how long this clip plays. trim_to is the "
                    f"one that cuts, so a differing dur is a stale number the "
                    f"programme's arithmetic would believe -- state one")
        if "trim_from" in item:
            if kind != "clip":
                raise ValueError(
                    f"item {i}: trim_from belongs on a CLIP -- a card has no "
                    f"film to start late into")
            try:
                trim_from = float(item["trim_from"])
            except (TypeError, ValueError):
                raise ValueError(
                    f"item {i}: trim_from must be seconds of ACT FILM time, "
                    f"got {item['trim_from']!r}")
            if trim_from <= 0:
                raise ValueError(
                    f"item {i}: trim_from must be positive -- a clip with no "
                    f"head to skip states nothing")
            if "dur" in item:
                raise ValueError(
                    f"item {i}: dur and trim_from cannot both be stated -- "
                    f"`dur` would be read as the played length while "
                    f"trim_from cuts the head, and the plan's arithmetic "
                    f"would believe the wrong one. State trim_to instead")
            if "trim_to" in item and float(item["trim_to"]) <= trim_from:
                raise ValueError(
                    f"item {i}: trim_from ({trim_from}s) is at or past "
                    f"trim_to ({item['trim_to']}s) -- the window is empty")
        for fade in ("fade_in", "fade_out"):
            if fade not in item:
                continue
            if kind != "clip":
                raise ValueError(
                    f"item {i}: {fade} belongs on a CLIP -- a card is "
                    f"generated silence and there is nothing to fade")
            try:
                value = float(item[fade])
            except (TypeError, ValueError):
                raise ValueError(
                    f"item {i}: {fade} must be seconds, got {item[fade]!r}")
            if value < 0:
                raise ValueError(f"item {i}: {fade} must be >= 0 seconds")
            if item.get("audio") == "silent" and value:
                raise ValueError(
                    f"item {i}: {fade} on a silent clip fades generated "
                    f"silence -- a no-op that reads as a treatment. Drop it; "
                    f"if the slide should carry sound, that is a licensing "
                    f"decision for the owner, not a fade")
        crescendo_keys = ("crescendo_out", "crescendo_db")
        if any(key in item for key in crescendo_keys):
            if not all(key in item for key in crescendo_keys):
                raise ValueError(
                    f"item {i}: crescendo_out and crescendo_db must be stated "
                    "together")
            if kind != "clip" or item.get("audio") != "source":
                raise ValueError(
                    f"item {i}: a crescendo belongs on a source-audio CLIP")
            try:
                crescendo_out = float(item["crescendo_out"])
                crescendo_db = float(item["crescendo_db"])
            except (TypeError, ValueError):
                raise ValueError(
                    f"item {i}: crescendo_out and crescendo_db must be numbers")
            if crescendo_out <= 0 or crescendo_db <= 0:
                raise ValueError(
                    f"item {i}: crescendo_out and crescendo_db must be positive")
            if float(item.get("gain_db", 0)) + crescendo_db > 1e-9:
                raise ValueError(
                    f"item {i}: gain_db + crescendo_db would boost above the "
                    "source level")
        if kind == "clip" and ("dur" in item or "trim_to" in item):
            total = float(item.get("fade_in", 0)) + float(item.get("fade_out", 0))
            length = float(item.get("trim_to", item.get("dur", 0)))
            length -= float(item.get("trim_from", 0))
            if total >= length:
                raise ValueError(
                    f"item {i}: fade_in + fade_out ({total}s) meets or exceeds "
                    f"the clip's own duration ({length}s) -- the fades "
                    f"would overlap on the ACT FILM clock")
            if float(item.get("crescendo_out", 0)) >= length:
                raise ValueError(
                    f"item {i}: crescendo_out must be shorter than the clip")
        if kind == "card" and "sub_chapters" in item:
            raise ValueError(
                f"item {i}: sub_chapters belong on the act's CLIP -- a card is "
                f"the slide, and the marks index the film behind it")
        if kind == "clip" and "sub_chapters" in item and not isinstance(
                item["sub_chapters"], str):
            raise ValueError(
                f"item {i}: sub_chapters is a pointer at the act's own manifest "
                f"(a path string), not the marks themselves -- the marks live "
                f"with the act so two people's edits never collide in the plan")
    return plan


def resolve(src):
    """The one path resolver: absolute wins, then repo-root, then cwd.

    Validation and encoding MUST agree on this. When the two disagreed, a
    relative path could be validated against the repo copy and then encoded
    from a different file of the same name in the working directory -- the file
    that was checked would not be the file that shipped.

    A path that resolves nowhere comes back empty, which is what makes
    `if not resolve(src)` the missing-source check.
    """
    p = Path(src)
    if p.is_absolute():
        return str(p) if p.exists() else ""
    for candidate in (REPO_ROOT / src, Path.cwd() / src):
        if candidate.exists():
            return str(candidate)
    return ""


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
    chains = []
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


def probe_video_extent(path):
    """The video stream's own timeline length: last frame's pts + duration.

    A container's ``format=duration`` covers the LONGEST stream, and Matroska
    carries no per-stream duration header at all -- so neither number sees
    what #88 actually did. There the segment's audio leg stayed whole while
    its picture was re-timed 8.5 s short, and only a video-only measurement
    catches that. Packets are read, not decoded (about a second for a
    five-minute segment), and the max is taken because B-frame reordering
    means the last packet in mux order is not necessarily the last in
    presentation order.
    """
    out = subprocess.run(
        [ffprobe_bin(), "-v", "error", "-select_streams", "v:0",
         "-show_entries", "packet=pts_time,duration_time", "-of", "csv=p=0",
         str(path)],
        capture_output=True, text=True, check=True,
    )
    extent = 0.0
    for line in out.stdout.splitlines():
        parts = line.strip().split(",")
        if len(parts) < 2:
            continue
        try:
            pts, dur = float(parts[0]), float(parts[1])
        except ValueError:
            continue
        extent = max(extent, pts + dur)
    if extent <= 0.0:
        raise RuntimeError(f"no video packets read from {path}")
    return extent


# How far a built segment may drift from its source before it is a re-time,
# not rounding. The fps conversion lands within a frame or two of the source
# length (~0.03 s at 59.94); #88's failure was 8.487 s. 0.25 s sits ~8x above
# the noise and ~34x below the failure.
SEGMENT_DURATION_TOLERANCE_SEC = 0.25

# The join adds its own small rounding per segment (measured: +0.112 s over a
# 14-item programme). The base absorbs the one-off muxing/encoder delay; the
# per-item term keeps a long programme from false-positiving on accumulated
# rounding while still failing any real re-time (#88 was -8.487 s on one act).
PROGRAMME_DURATION_TOLERANCE_BASE_SEC = 0.5
PROGRAMME_DURATION_TOLERANCE_PER_ITEM_SEC = 0.1


def verify_segment(plan, index, seg_path):
    """Fail the build if one segment's PICTURE is not its source's length.

    This is the check issue #88 proved necessary: the filtergraph re-timed one
    act's video 8.5 s short, ffmpeg exited 0, the frame count going IN was
    right, and the programme only read as wrong when its act slides stopped
    landing on their marks. Comparing each segment's video extent against the
    item's own length turns that silent re-time into a loud stop that names
    the act.

    The expectation is on the item's own clock -- for a clip, its film time
    (the delivered file's video stream); for a card, the authored slide
    duration. The segment is that same clock re-encoded, so the two must agree
    within rounding.
    """
    item = plan["items"][index]
    expected_sec = item_duration(item)
    built_sec = probe_video_extent(seg_path)
    if abs(built_sec - expected_sec) > SEGMENT_DURATION_TOLERANCE_SEC:
        label = item.get("label", item.get("path") or item.get("image"))
        raise RuntimeError(
            f"segment {index} ({label}) is {built_sec:.3f}s of picture but "
            f"its source is {expected_sec:.3f}s -- {built_sec - expected_sec:+.3f}s "
            f"is a re-time, not rounding (#88). The programme is NOT written; "
            f"fix the segment's chain rather than shipping the shortfall.")
    return built_sec


def verify_programme(plan, out_path):
    """Fail the build if the joined programme is not the sum of its parts.

    The per-segment check catches a re-timed item; this one catches everything
    the join itself can lose -- a segment whose legs disagreed, a concat-time
    timestamp jump. Measured on a healthy build: +0.112 s over 14 items, and
    the point of the tolerance is that per-segment rounding does not
    accumulate into a false stop.

    Both numbers are on the PROGRAMME clock: the expected side is the plan's
    own arithmetic, the built side is the delivered file's container duration.
    """
    expected_sec = expected_duration(plan)
    built_sec = probe_duration(out_path)
    tolerance = (PROGRAMME_DURATION_TOLERANCE_BASE_SEC
                 + PROGRAMME_DURATION_TOLERANCE_PER_ITEM_SEC * len(plan["items"]))
    if abs(built_sec - expected_sec) > tolerance:
        raise RuntimeError(
            f"programme is {built_sec:.3f}s but the plan sums to "
            f"{expected_sec:.3f}s -- {built_sec - expected_sec:+.3f}s exceeds "
            f"the {tolerance:.3f}s join tolerance (#88). Do not ship it.")
    return built_sec


def clip_window(item):
    """A clip's authored in/out points on the ACT FILM clock: (start, end).

    ``trim_from`` is the in-point and ``trim_to`` the out-point, both stated in
    the delivered act's own seconds. Either may be absent -- ``start`` is 0.0
    and ``end`` is ``None`` (play to the file's end). Together they are the one
    sanctioned way a programme shortens a delivered act **without re-rendering
    it**: the act's own file is untouched, so what it ships standalone is
    unchanged, and only the programme skips the head or ends early.

    That distinction is load-bearing for act VI, whose 10 s head plate carries
    a rights condition: the standalone act still plays it.
    """
    start = float(item.get("trim_from", 0) or 0)
    end = item.get("trim_to")
    return start, (None if end is None else float(end))


def segment_video_chain(plan, item):
    """The normalising video chain for a clip, as a plain -vf string."""
    fps = plan.get("fps", DEFAULT_FPS)
    w = int(plan.get("width", DEFAULT_WIDTH))
    h = int(plan.get("height", DEFAULT_HEIGHT))
    chain = (f"scale={w}:{h}:flags=lanczos,setsar=1,"
             f"fps={fps},format=yuv420p")
    start, end = clip_window(item)
    if start or end is not None:
        # An authored window inside a delivered act: the act's own file is
        # never re-rendered, so the programme starts it late and/or ends it
        # early instead. Both numbers are on the ACT FILM clock, like every
        # other number the plan states. The trim is placed AFTER the fps
        # conversion so the window is cut on the delivery timeline rather than
        # on the source's -- and `setpts=PTS-STARTPTS` below rebases it to 0.
        parts = []
        if start:
            parts.append(f"start={start}")
        if end is not None:
            parts.append(f"end={end}")
        chain += ",trim=" + ":".join(parts)
    elif item["audio"] == "silent":
        # Both legs pinned to ONE duration so they are equal by construction.
        dur = item.get("dur")
        if dur is None:
            dur = probe_duration(resolve(item["path"]), stream="v:0")
        chain += f",trim=duration={dur}"
    return chain + ",setpts=PTS-STARTPTS"


def fade_chain(item, dur):
    """The explicit gain/fade filters a clip asks for, or "" -- ACT FILM clock.

    ``fade_in`` starts at 0 of the clip's own timeline; ``fade_out`` ENDS at
    the clip's end, so its start is ``dur - fade_out``. Both are seconds from
    the plan, stated explicitly and reproducibly -- the act-join treatment of
    issue #105. ``gain_db`` is a static per-act gain, applied BEFORE the
    fades. An act's level against the others is a mix decision that belongs
    to the owner -- so ``gain_db`` exists only as the place the OWNER'S OWN
    decision is recorded in the plan (the first was act I, 9.1 LU under the
    show and approved for correction, #164); a tool or agent never picks the
    number, and it is a plain gain, never a limiter or normaliser. ``dur`` is
    the clip's length on its own clock (authored, or probed by the caller);
    ``crescendo_out`` and ``crescendo_db`` add a linear-in-dB rise over the
    clip's final seconds. They are paired with an initial negative ``gain_db``;
    plan validation refuses any combination whose final gain exceeds unity.
    With nothing declared the chain is empty and the audio path is byte-identical
    to before.
    """
    gain_db = float(item.get("gain_db", 0))
    fade_in = float(item.get("fade_in", 0))
    fade_out = float(item.get("fade_out", 0))
    crescendo_out = float(item.get("crescendo_out", 0))
    crescendo_db = float(item.get("crescendo_db", 0))
    filters = []
    if gain_db:
        filters.append(f"volume={gain_db:+.1f}dB")
    if fade_in:
        filters.append(f"afade=t=in:st=0:d={fade_in:.3f}")
    if fade_out:
        filters.append(f"afade=t=out:st={dur - fade_out:.3f}:d={fade_out:.3f}")
    if crescendo_out:
        start = dur - crescendo_out
        filters.append(
            "volume='if(lt(t,"
            f"{start:.3f}),1,pow(10,({crescendo_db:.3f}*"
            f"(t-{start:.3f})/{crescendo_out:.3f})/20))':eval=frame")
    return "," + ",".join(filters) if filters else ""


def clip_audio_chain(item, rate, layout, dur):
    """The audio filter string for a source-audio clip: cut the authored
    window, resample if needed, pin the layout for the join, then the plan's
    explicit gain and fades. No gain unless the plan's owner-authored
    ``gain_db`` declares one. Shared by the encode and the stream-copy segment
    commands so the two paths treat a clip's sound identically -- ``dur`` is
    the clip's PLAYED length on the ACT FILM clock (authored, else probed by
    the caller), which is the window's length when one is stated.

    The window is cut on both streams by the same numbers, so sound cannot
    outlive picture, and ``asetpts`` rebases it to zero -- which is what makes
    a ``fade_in`` land on the first frame the programme actually plays rather
    than on a head the programme skipped.
    """
    start, end = clip_window(item)
    window = ""
    if start or end is not None:
        parts = []
        if start:
            parts.append(f"start={start}")
        if end is not None:
            parts.append(f"end={end}")
        window = "atrim=" + ":".join(parts) + ",asetpts=PTS-STARTPTS,"
    return (f"{window}aresample={rate},"
            f"aformat=sample_fmts=fltp:channel_layouts={layout}"
            f"{fade_chain(item, float(dur) if dur is not None else 0.0)}")


def build_segment_command(plan, index, seg_path, threads=None):
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
        *conform.video_encode_args(crf=crf, preset=preset, threads=threads),
        # The colour note that used to live here: the three -color_* flags
        # describe the *frames*, and x264 only copies the matrix from them --
        # primaries and transfer come out `unknown`, which is a silent
        # mismatch against every other deliverable in ~/Videos/Wolves/Prod.
        # Writing the VUI directly (inside video_encode_args) is the only way
        # all three actually land in the bitstream. It has to be written
        # HERE, on the segment: the join copies the bitstream, so whatever
        # the VUI says at this point is what ships. Verified by ffprobe.
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
        # The PLAYED length: the authored window if there is one, else the
        # authored duration, else probed from the video stream -- the container
        # can report a longer audio stream, and a fade placed against that
        # starts early. Only a fade needs the number, so only a fade pays the probe.
        start, end = clip_window(item)
        if start or end is not None:
            dur = (end if end is not None
                   else probe_duration(resolve(item["path"]), stream="v:0")) - start
            # A windowed clip is cut on BOTH streams by the same numbers, so
            # the sound cannot outlive the picture -- and a fade_out lands
            # against the authored end rather than against the file's.
            maps += ["-t", str(float(dur))]
        else:
            dur = item.get("dur")
            if dur is None and (
                    float(item.get("fade_out", 0))
                    or float(item.get("crescendo_out", 0))):
                dur = probe_duration(resolve(item["path"]), stream="v:0")
        # aresample only where the rate differs; aformat pins the layout so the
        # join sees one shape. No gain is applied anywhere; the only treatment
        # is an explicit fade the plan asked for (issue #105).
        af = ["-af", clip_audio_chain(item, rate, layout, dur)]
    return [*args, "-vf", segment_video_chain(plan, item), *af, *maps, *common]


def build_segment_copy_command(plan, index, seg_path, src_path):
    """Remux a CONFORMANT clip into its segment: copy the picture, decode the
    sound to PCM. There is no ``-vf`` anywhere -- ``src_path`` already matches
    the delivery spec (that is what ``tools/conform.py``'s cache guarantees),
    so filtering it would only spend a video generation.

    The audio leg is identical to the encode path's: decoded, resampled only
    where the rate differs, layout pinned, the plan's explicit fades applied,
    written as PCM s24le. Still never FLAC in a segment -- the concat demuxer
    binds the first file's extradata to the whole joined stream, and FLAC's
    STREAMINFO lives there. The picture copy changes none of that.

    ``src_path`` is the conformed file, and it is what gets probed too: the
    conform is timeline-preserving, so its lengths are the source's, and
    probing the file actually being remuxed keeps the check honest.
    """
    rate = str(plan.get("sample_rate", DEFAULT_SAMPLE_RATE))
    layout = plan.get("layout", DEFAULT_LAYOUT)
    item = plan["items"][index]

    args = [ffmpeg_bin(), "-nostdin", "-hide_banner", "-i", str(src_path)]
    if item["audio"] == "silent":
        dur = item.get("dur")
        if dur is None:
            dur = probe_duration(str(src_path), stream="v:0")
        args += ["-f", "lavfi", "-i",
                 f"anullsrc=channel_layout={layout}:sample_rate={rate}:d={dur}"]
        maps = ["-map", "0:v:0", "-map", "1:a:0", "-t", str(dur)]
        af = []
    else:
        maps = ["-map", "0:v:0", "-map", "0:a:0"]
        dur = item.get("dur")
        if dur is None and (
                float(item.get("fade_out", 0))
                or float(item.get("crescendo_out", 0))):
            dur = probe_duration(str(src_path), stream="v:0")
        af = ["-af", clip_audio_chain(item, rate, layout, dur)]
    return [*args, *af, *maps,
            "-c:v", "copy", "-c:a", "pcm_s24le", "-ar", rate,
            str(seg_path), "-y"]


def build_concat_command(plan, list_path, out_path):
    """Join the segments: copy the picture, encode the sound once.

    ``-safe 0`` because the list holds absolute paths. The video is copied, so
    every segment must share codec parameters -- they do, by construction:
    ``build_segment_command`` encodes them all from the same plan.

    TWO GAINS, and keeping them apart is the point. ``master_gain_db`` is the
    programme's mix, and the lossless master carries it too. ``distribution
    _gain_db`` is EXTRA headroom this leg needs and the master does not,
    because a lossy encoder reconstructs inter-sample peaks above the samples
    it was given -- measured here at ~2.1 dB across the whole programme, with
    the FLAC master reading -1.1 dBTP off the very same PCM that gave AAC
    +1.0. Both are plain static gains: never a limiter, never a normaliser,
    never EQ. Neither is guessed -- each is derived from a measurement of the
    file it applies to, which is the audio standard's own rule (issue #82:
    check the file you are actually shipping).
    """
    abitrate = plan.get("audio_bitrate", DEFAULT_AUDIO_BITRATE)
    gain = (float(plan.get("master_gain_db", 0))
            + float(plan.get("distribution_gain_db", 0)))
    audio_filter = ["-af", f"volume={gain:+.1f}dB"] if gain else []
    return [
        ffmpeg_bin(), "-nostdin", "-hide_banner",
        "-f", "concat", "-safe", "0", "-i", str(list_path),
        "-map", "0:v:0", "-map", "0:a:0",
        "-c:v", "copy",
        *audio_filter,
        "-c:a", "aac", "-b:a", abitrate,
        "-ar", str(plan.get("sample_rate", DEFAULT_SAMPLE_RATE)),
        "-movflags", "+faststart",
        str(out_path), "-y",
    ]


def build_master_command(plan, list_path, out_path):
    """Join the segments into a LOSSLESS programme master: copy the picture,
    encode the sound to FLAC.

    Issue #145. Seven of the nine acts carry FLAC masters at ~1.6-1.8 Mb/s and
    the programme squashed all of them into one ~439 kb/s AAC at the join --
    so the only artifact in the whole chain with no lossless option was the
    final movie, which is the file the show is actually watched and judged by.

    It costs one FLAC encode and nothing else: the picture is ``-c:v copy``
    here exactly as it is for the distribution copy, off the same PCM segments
    that already exist, so the two files carry the SAME bitstream and differ
    only in how the sound is stored.

    **Matroska, not MP4.** FLAC in MP4 is a late addition that many players
    still refuse; Matroska has carried FLAC since forever and is what the
    segments already are.

    The master carries ``master_gain_db`` and NOT ``distribution_gain_db``.
    That split is the whole reason both keys exist: the mix is one thing, and
    the extra headroom a lossy encoder's inter-sample overshoot demands is
    another. Measured on this programme, the same PCM gave a FLAC master at
    -1.1 dBTP and an AAC copy at +1.0 -- so making them carry one gain would
    either clip the copy or needlessly duck the master. Each leg is measured
    and corrected against the file that actually ships (issue #82).
    """
    master_gain = float(plan.get("master_gain_db", 0))
    audio_filter = ["-af", f"volume={master_gain:+.1f}dB"] if master_gain else []
    return [
        ffmpeg_bin(), "-nostdin", "-hide_banner",
        "-f", "concat", "-safe", "0", "-i", str(list_path),
        "-map", "0:v:0", "-map", "0:a:0",
        "-c:v", "copy",
        *audio_filter,
        "-c:a", "flac",
        "-ar", str(plan.get("sample_rate", DEFAULT_SAMPLE_RATE)),
        str(out_path), "-y",
    ]


def master_output_path(plan, out_path):
    """Where the lossless master goes: the plan's `master_output`, else the
    distribution copy's name with a `.mkv` extension. ``None`` disables it --
    an explicit ``"master_output": null`` is how a plan says it does not want
    one, rather than the key simply being forgotten."""
    if "master_output" in plan:
        stated = plan["master_output"]
        return None if stated is None else str(stated)
    return str(Path(out_path).with_suffix(".mkv"))


def default_jobs(n_items):
    """How many segments to build at once. x264's own threading saturates
    early (~8 threads), so workers at a few threads each beat one worker at
    every core: 4 x 6 finishes before 1 x 32."""
    return max(1, min((os.cpu_count() or 1) // 6, n_items))


def _copy_path_ok(plan, allow_copy=True):
    """Only a plan targeting the delivery spec can stream-copy: its segments
    must BE spec files, or the conform cache would hand back 59.94/1080p
    sources to a plan building something else. A plan at another rate or
    frame size still works -- it encodes, as it always has."""
    if not allow_copy:
        return False
    return (str(plan.get("fps", DEFAULT_FPS)) == conform.DELIVERY.fps
            and int(plan.get("width", DEFAULT_WIDTH)) == conform.DELIVERY.width
            and int(plan.get("height", DEFAULT_HEIGHT)) == conform.DELIVERY.height)


def _conform_one(job):
    """Picklable worker: conform one clip source, report what it cost."""
    index, src, cache_dir, ffmpeg, threads = job
    path, status = conform.ensure(src, out_dir=cache_dir, ffmpeg=ffmpeg,
                                  threads=threads, log=lambda _m: None)
    return index, str(path), status


def _segment_worker(job):
    """Picklable worker: build one segment, then verify it against its item.

    The verify rides inside the worker so a parallel build still fails the
    moment a segment re-times (#88), not after the other workers finish.
    """
    argv, plan, index, seg = job
    subprocess.run(argv, check=True)
    verify_segment(plan, index, seg)
    return index


def assemble(plan, out_path, log=None, jobs=None,
             conform_cache=None, allow_copy=True):
    """Build every segment, then join them. Returns the output path.

    Every segment is verified against its source's length as it is built, and
    the joined programme against the plan's sum, so a silent re-time stops the
    build instead of shipping (#88: one act came out of the filtergraph 8.5 s
    short, ffmpeg exited 0, and the file played fine). This holds on the
    stream-copy path too -- a remux that re-times is exactly the failure
    those checks exist for, so they do not come off when the encode does.

    The segments land in a temporary directory that is removed afterwards --
    they are pure intermediates, and keeping them would invite somebody to
    hand-edit one, which is the failure this repo's regenerated-artifact rule
    exists to prevent.

    Order is the programme: the concat list is written from a list indexed by
    plan position, filled in as workers finish -- never in completion order.
    """
    log = log or (lambda msg: print(msg, file=sys.stderr))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n_items = len(plan["items"])
    jobs = max(1, min(jobs, n_items)) if jobs else default_jobs(n_items)
    threads = max(1, (os.cpu_count() or 1) // jobs) if jobs > 1 else None
    copy_ok = _copy_path_ok(plan, allow_copy)
    ctx = tempfile.TemporaryDirectory(prefix="megacut-")
    tmp = Path(ctx.name)
    try:
        # Phase 1: every clip's source made conformant, cached, so its
        # segment can copy the picture. Unchanged sources are cache hits;
        # only a newly delivered act pays the encode, and only once.
        sources = {}
        if copy_ok:
            clip_jobs = [(i, resolve(item["path"]))
                         for i, item in enumerate(plan["items"])
                         if item["kind"] == "clip"]
            if clip_jobs:
                work = [(i, src, conform_cache, [ffmpeg_bin()], threads)
                        for i, src in clip_jobs]
                if jobs > 1 and len(work) > 1:
                    with ProcessPoolExecutor(max_workers=jobs) as pool:
                        results = list(pool.map(_conform_one, work))
                else:
                    results = [_conform_one(w) for w in work]
                for i, path, status in results:
                    if status != "conforms":
                        log(f"  conform [{status}]: "
                            f"{plan['items'][i].get('label', path)}")
                    sources[i] = path

        # Phase 2: the segments. Cards always encode (they are generated);
        # clips copy their picture when the plan targets the delivery spec.
        segments = [None] * n_items
        work = []
        for i, item in enumerate(plan["items"]):
            seg = tmp / f"seg{i:03d}.mkv"
            segments[i] = seg
            if item["kind"] == "clip" and copy_ok and clip_window(item) == (0.0, None):
                argv = build_segment_copy_command(plan, i, seg, sources[i])
                mode = "copy"
            else:
                argv = build_segment_command(plan, i, seg, threads=threads)
                mode = "encode"
            log(f"  segment {i + 1}/{n_items} [{mode}]: "
                f"{item.get('label', item['kind'])}")
            work.append((argv, plan, i, seg))
        if jobs > 1 and len(work) > 1:
            with ProcessPoolExecutor(max_workers=jobs) as pool:
                list(pool.map(_segment_worker, work))
        else:
            for w in work:
                _segment_worker(w)

        list_path = tmp / "segments.txt"
        list_path.write_text(
            "".join(f"file '{s}'\n" for s in segments), encoding="utf-8")
        log(f"  joining {len(segments)} segments")
        subprocess.run(build_concat_command(plan, list_path, out_path), check=True)
        verify_programme(plan, out_path)
        master_path = master_output_path(plan, out_path)
        if master_path:
            # Issue #145. Same segments, same picture bitstream, sound kept
            # lossless. Built AFTER the distribution copy is verified, so a
            # programme that failed its own duration check never leaves a
            # master behind implying it passed.
            log(f"  lossless master -> {master_path}")
            subprocess.run(
                build_master_command(plan, list_path, master_path), check=True)
            verify_programme(plan, master_path)
    finally:
        ctx.cleanup()
    return out_path


def expected_duration(plan):
    """The programme's length: every item on the programme clock, summed."""
    return sum(item_duration(item) for item in plan["items"])


def item_duration(item):
    """One item's length on the PROGRAMME (megacut) clock.

    `is None`, not `or`: a 0 would fall through to a probe and report a length
    the graph does not build. expected_duration and build_filtergraph test the
    same way, and the three must not disagree about what "no dur" is.

    ``trim_to``/``trim_from`` OUTRANK both -- they are the authored window
    (see ``clip_window``), and a clip that declares one IS its window long,
    everywhere. `dur` never cut anything, and that was the trap: an authored
    `dur` shorter than the file changed the plan's arithmetic while the segment
    still played to its own end, so the programme's clock and its picture
    disagreed and only `verify_segment` caught it.
    """
    start, end = clip_window(item)
    if end is not None:
        return end - start
    if start:
        return probe_duration(resolve(item["path"]), stream="v:0") - start
    dur = item.get("dur")
    if dur is None:
        dur = probe_duration(resolve(item["path"]), stream="v:0")
    return float(dur)


def load_sub_chapters(pointer):
    """An act's own sub-chapter marks, read from ITS manifest, not the plan.

    Two clocks live here, and mixing them is the recorded failure (issue
    #109):

    * ``at``  -- ACT FILM time: where the mark lands inside that act's own
      delivered file. This is the clock ``chapters()`` counts in per item, so
      a mark's programme time is ``clip_start_programme + at``.
    * ``src`` -- SOURCE time: the timecode in the act's original footage the
      mark is anchored to, so the mark and the credit it belongs to cannot
      drift apart when the act is re-cut. Assembly never reads it; it exists
      so the mark can be re-derived, not placed.

    The pointer keeps the marks in the act's own file (their source of truth)
    and out of the programme plan: an act writing its timecodes into
    ``megacut.json`` is how two people's edits collide (issue #92).
    """
    path = Path(pointer)
    if not path.is_absolute():
        path = REPO_ROOT / path
    manifest = json.loads(path.read_text())
    marks = []
    for i, mark in enumerate(manifest.get("chapters", [])):
        at = mark.get("at")
        if at is None:
            raise ValueError(
                f"{pointer}: chapter {i} has no `at` (act film time)")
        marks.append((float(at), mark.get("title") or "Chapter"))
    return marks


def chapters(plan, include_sub_chapters=False):
    """The programme's chapter markers, derived from the plan's own clock.

    A chapter starts where its ACT SLIDE starts, not where the film behind it
    does: the slide is how the audience is told which act this is, so a marker
    landing after it would drop them into a card they have already read. Where
    a slide has been RETIRED -- the owner cut the four Roman-numeral cards on
    2026-08-14 -- the same `chapter` string sits on the act's own CLIP instead,
    and the marker starts where the act starts, which is the only place left
    that means anything. Removing a card must not silently remove a marker.

    The title is the item's `chapter` -- an authored audience-facing string,
    NOT the item's `label`, which is a build note ("held long, by owner
    request"). It lives on the item so the running order and its markers cannot
    disagree; a card without one falls back to `label` and reads oddly, which is
    the visible failure that gets it filled in. A CLIP without one is simply not
    a chapter: most clips (the Perfume movements, the interstitials) are not.

    ``interstitial: true`` opts a CARD out entirely. The label fallback above
    exists so a missing `chapter` reads oddly and gets filled in -- but the
    scream card is a gag whose whole design is that no scrub bar announces it,
    and the fallback was quietly publishing its build label as a marker. A card
    that says it is an interstitial is not a chapter, and stating it beats
    relying on a card having no label.

    ``include_sub_chapters`` is OFF by default, so the published one-entry-per-
    act list is unchanged unless it is asked for. When on, a clip item may
    carry ``sub_chapters`` -- a pointer at the ACT'S OWN manifest -- and each
    of its marks is emitted at ``clip_start_programme + at``, where ``at`` is
    ACT FILM time (the same clock this function counts per item). TODO(owner):
    whether these belong in the YouTube chapter list at all, or only in an
    ffmpeg metadata track -- eight acts plus internal marks may be more
    granular than a scrub bar wants. Issue #92.

    Yielded as (seconds, title), so a caller can format them for YouTube, an
    ffmpeg metadata file, or a review note without this knowing about any of
    them.
    """
    out, t_programme = [], 0.0
    for item in plan["items"]:
        if item["kind"] == "card":
            if not item.get("interstitial"):
                out.append(
                    (t_programme,
                     item.get("chapter") or item.get("label") or "Chapter"))
            t_programme += float(item["dur"])
            continue
        if item.get("chapter"):
            out.append((t_programme, item["chapter"]))
        if include_sub_chapters and item.get("sub_chapters"):
            for at_film, title in load_sub_chapters(item["sub_chapters"]):
                out.append((t_programme + at_film, title))
        t_programme += item_duration(item)
    return out


def format_chapters(marks):
    """YouTube's chapter format: `H:MM:SS Title`, one per line.

    YouTube ignores a list whose first marker is not 0:00. That used to hold
    here by construction, because the programme opened on act I's slide -- it
    stopped holding when the prologue was placed in front of it (2026-08-14),
    and the first marker is now act I's at 1:39. The prologue carries no
    chapter by design (docs/running-order.md), so closing the gap means
    authoring a title for it, which is the owner's call, not the tool's. This
    function reports what the plan says and does not invent a zero marker.
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

    The offset is on the ACT'S OWN FILM clock, which is not the same as the
    offset into the played item once a clip carries a window: an act the
    programme starts 10.5 s late has every note 10.5 s further into its own
    file than into the programme's copy of it. ``trim_from`` is added back for
    exactly that reason -- the number this prints is the one to scrub to in the
    act's own project.

    The title is the act's, not the item's: a clip carries a `label` that is a
    build note ("held long, by owner request"), so an act's film is reported
    under the chapter it is announced by -- its own slide where one exists, and
    its own `chapter` string where the slide has been retired. That is what the
    audience -- and therefore the note -- calls it.
    """
    t = 0.0
    act = None
    for item in plan["items"]:
        dur = item_duration(item)
        if item.get("chapter"):
            act = item["chapter"]
        elif item["kind"] == "card":
            act = item.get("label")
        if seconds < t + dur or item is plan["items"][-1]:
            title = act or item.get("label") or item.get("path") or "?"
            start, _ = clip_window(item)
            return title, round(seconds - t + start, 3), item.get("path")
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
    ap.add_argument("--sub-chapters", action="store_true",
                    help="with --chapters: also emit each act's own internal "
                         "marks (opt-in; default keeps one marker per act). "
                         "TODO(owner): whether these belong in the YouTube "
                         "chapter list or only in ffmpeg metadata -- issue #92")
    ap.add_argument("--locate", metavar="TC", nargs="+",
                    help="turn review-note timecodes on the PROGRAMME clock "
                         "(12:43, 1:02:11, 763) into the act that is playing "
                         "and the offset inside its own file; encodes nothing")
    ap.add_argument("--jobs", type=int, default=None,
                    help="build this many segments in parallel "
                         "(default min(cpu//6, items)); x264 saturates early, "
                         "so workers x few threads beats one worker x all cores")
    ap.add_argument("--conform-cache",
                    help="where conformed clip sources are cached "
                         "(default: $DESTINY_CONFORM_CACHE or "
                         "~/.cache/destiny-vids/conform)")
    ap.add_argument("--no-copy", action="store_true",
                    help="encode every segment even when sources conform to "
                         "the delivery spec (debugging; the slow path)")
    args = ap.parse_args(argv)

    plan = load_plan(args.plan, require_sources=not (args.chapters or args.locate))
    if args.chapters:
        print(format_chapters(chapters(plan, include_sub_chapters=args.sub_chapters)))
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
        copy_ok = _copy_path_ok(plan, allow_copy=not args.no_copy)
        for i, item in enumerate(plan["items"]):
            if item["kind"] == "clip" and copy_ok and clip_window(item) == (0.0, None):
                print(f"# [{i}] COPY (via conform cache): "
                      f"{item.get('label', item['path'])}")
                print(" ".join(build_segment_copy_command(
                    plan, i, f"seg{i:03d}.mkv", resolve(item["path"]))))
            else:
                print(f"# [{i}] ENCODE: {item.get('label', item['kind'])}")
                print(" ".join(build_segment_command(plan, i, f"seg{i:03d}.mkv")))
        print(" ".join(build_concat_command(plan, "segments.txt", out_path)))
        master_path = master_output_path(plan, out_path)
        if master_path:
            print("# lossless programme master (issue #145)")
            print(" ".join(build_master_command(
                plan, "segments.txt", master_path)))
        print(f"# expected duration: {expected_duration(plan):.3f}s "
              f"across {len(plan['items'])} items")
        return 0

    print(f"assembling {len(plan['items'])} items -> {out_path}", file=sys.stderr)
    assemble(plan, out_path, jobs=args.jobs,
             conform_cache=args.conform_cache, allow_copy=not args.no_copy)
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
