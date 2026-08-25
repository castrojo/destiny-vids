"""Cut list -> rendered video.

The last mile: takes the JSON shot list ``tools/story.py --format json`` emits,
finds each shot's source file, cuts the exact in/out points with ffmpeg, and
concatenates them into one file.

    python3 tools/story.py stories/hero-cut.txt --dir segments --format json --out cut.json
    python3 tools/render.py cut.json --media media/ --out renders/hero-cut.mp4

Source media is resolved as ``<media_dir>/<video_id>.<ext>`` and is NEVER
committed: this repo indexes Bungie footage, it does not redistribute it. A shot
whose source file is missing is reported and skipped rather than silently
dropped, for the same reason story.py reports unmatched beats.

Every clip is re-encoded to a common format before concatenation. Stream-copying
would be faster but cuts would snap to the nearest keyframe, which moves the
in-point off the beat the index carefully identified.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import conform, peaks  # noqa: E402

MEDIA_EXTS = (".mp4", ".mkv", ".webm", ".mov", ".wav", ".flac", ".m4a")

# Common intermediate format. Every clip is normalized to this so the concat
# demuxer can join them without re-muxing mismatched streams. The frame rate
# is the delivery spec's (tools/conform.py): a cut rendered from now on comes
# out already conformant, so megacut's assembly can copy its picture instead
# of re-encoding it.
TARGET_W, TARGET_H = conform.DELIVERY.width, conform.DELIVERY.height
TARGET_FPS = conform.DELIVERY.fps

# Bluefin runs a long-lived ffmpeg container with $HOME bind-mounted at the same
# path, so host paths resolve unchanged inside it (see docs/rendering.md).
DEFAULT_CONTAINER = "bluefin-thumbnailer"

# Where and how long detect_picture reads the source. PROBE_AT is now only the
# fallback for a source whose duration cannot be read: issue #161's fix is to
# probe RELATIVE to the cut's own length, at several points, because a fixed
# 40 s offset reads nothing at all on anything shorter -- which was every act
# under 40 s and nearly every hero video.
PROBE_AT = 40.0
PROBE_LEN = 5.0
# Through the body of the cut, avoiding the head and the tail where fades and
# title cards live and would be read as a different matte.
PROBE_FRACTIONS = (0.25, 0.5, 0.75)

# The one intermediate shape. Every clip -- cut or still -- is normalised to it,
# because the concat demuxer joins only inputs whose stream properties match.
VIDEO_FILTER = (
    f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
    f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2,"
    f"fps={TARGET_FPS},format=yuv420p"
)

# Issue #144. `docs/skills/audio/SKILL.md` states the rule in one
# line -- "source the best version that exists, KEEP THE CHAIN LOSSLESS, ship it
# unaltered" -- and this module used to encode AAC 192k at three places inside
# that chain. The loss was invisible where it happened (the file plays fine) and
# permanent for everything built from the output; wrapping such a render in FLAC
# afterwards makes the CONTAINER lossless while the content has already been
# through a lossy generation.
#
# Intermediates carry PCM. Not FLAC, and that distinction is measured, not
# theoretical: FLAC's STREAMINFO lives in extradata and the concat demuxer binds
# the FIRST file's extradata to the whole joined stream, so every later segment
# fails to decode. PCM has no extradata to mismatch. Disk cost is real and
# temporary -- the same trade tools/megacut.py already makes. Matroska for the
# same reason megacut uses it: an intermediate is read back by the demuxer and
# never needs a faststart-able moov.
INTERMEDIATE_AUDIO_ARGS = ("-c:a", "pcm_s24le", "-ar", "48000", "-ac", "2")
INTERMEDIATE_SUFFIX = ".mkv"
# The one place a lossy encode may happen is DELIVERY, and here it does not
# happen at all: every act master in this project is FLAC, so a cut leaves this
# module lossless and any fold-down to a distribution codec starts from it.
DELIVERY_AUDIO_CODEC = "flac"


def _container_running(name):
    try:
        out = subprocess.run(
            ["podman", "ps", "--filter", f"name=^{name}$", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return name in out.stdout.split()


def find_ffmpeg(prefer_container=True):
    """Resolve ffmpeg to an argv *prefix*, not just a path.

    Returns a list so a containerized ffmpeg (``podman exec ... ffmpeg``) is
    interchangeable with a local binary at every call site.

    Order:
      1. ``DESTINY_FFMPEG`` — full command, shell-split (wins outright).
      2. The running ffmpeg container (``DESTINY_FFMPEG_CONTAINER``), which is
         the preferred path on Bluefin: a full non-free build with libx264 and
         libfdk_aac, and no host packages to install.
      3. ``imageio-ffmpeg``'s bundled static binary.
      4. ``ffmpeg`` on PATH — last, because the Fedora/Bluefin default is
         ``ffmpeg-free``, which lacks H.264 and fails only once decoding starts.
    """
    override = os.environ.get("DESTINY_FFMPEG")
    if override:
        return shlex.split(override)

    if prefer_container and shutil.which("podman"):
        name = os.environ.get("DESTINY_FFMPEG_CONTAINER", DEFAULT_CONTAINER)
        if _container_running(name):
            return ["podman", "exec", name, "ffmpeg"]
        image = os.environ.get("DESTINY_FFMPEG_IMAGE")
        if image:
            home = str(Path.home())
            return ["podman", "run", "--rm", "-v", f"{home}:{home}",
                    "-w", os.getcwd(), "--entrypoint", "ffmpeg", image]

    try:
        import imageio_ffmpeg

        return [imageio_ffmpeg.get_ffmpeg_exe()]
    except ImportError:
        pass

    found = shutil.which("ffmpeg")
    if not found:
        raise RuntimeError(
            "no ffmpeg found: start the ffmpeg container, "
            "pip install imageio-ffmpeg, or set DESTINY_FFMPEG"
        )
    return [found]


def ffmpeg_for_printing():
    """The ffmpeg to name when a caller is only PRINTING a command.

    ``--print-command`` exists to be read, diffed and pasted, so resolving a
    real encoder is a precondition of RUNNING the command, never of showing
    it. Falling back to the bare name keeps the offline suite offline instead
    of making a print depend on an H.264 build the runner does not have.
    """
    try:
        return find_ffmpeg()
    except Exception:
        return ["ffmpeg"]


def find_ffprobe(prefer_container=True):
    """``find_ffmpeg``'s sibling: same resolution order, for ffprobe.

    The one divergence is ``imageio-ffmpeg``: that wheel ships a bare ffmpeg
    with no ffprobe beside it, so it cannot satisfy this lookup and is
    skipped. ``DESTINY_FFPROBE`` wins outright when set.
    """
    override = os.environ.get("DESTINY_FFPROBE")
    if override:
        return shlex.split(override)

    if prefer_container and shutil.which("podman"):
        name = os.environ.get("DESTINY_FFMPEG_CONTAINER", DEFAULT_CONTAINER)
        if _container_running(name):
            return ["podman", "exec", name, "ffprobe"]
        image = os.environ.get("DESTINY_FFMPEG_IMAGE")
        if image:
            home = str(Path.home())
            return ["podman", "run", "--rm", "-v", f"{home}:{home}",
                    "-w", os.getcwd(), "--entrypoint", "ffprobe", image]

    found = shutil.which("ffprobe")
    if not found:
        raise RuntimeError(
            "no ffprobe found: start the ffmpeg container or set DESTINY_FFPROBE"
        )
    return [found]


def resolve_media(video_id, media_dir):
    """Find the source file for a video_id, as an absolute path.

    Absolute matters: a containerized ffmpeg does not share the caller's working
    directory, so a relative path would resolve against the container's cwd.
    """
    for ext in MEDIA_EXTS:
        path = (Path(media_dir) / f"{video_id}{ext}").resolve()
        if path.exists():
            return path
    return None


def probe_windows(duration, probe_len=None):
    """Where to read a source for its picture area, given how long it is.

    Issue #161: this used to be one fixed offset, ``PROBE_AT = 40.0``. Act IV
    is 34.0 s long, so the probe seeked past the end, decoded nothing,
    cropdetect reported nothing and ``detect_picture`` returned ``None`` --
    which is ALSO the legitimate answer for an un-letterboxed source, so the
    caller could not tell the two apart and placed plates against the raw
    frame. Measured on that act, the fallback put the pill 18 px onto the
    active picture; on a shorter cut it seats a nameplate on the matte, which
    is the exact failure this function exists to prevent. Every act under 40 s
    and nearly every hero video was affected.

    So the offsets are now RELATIVE to the source, and there is more than one
    of them: a single window can land on a fade, a title card or a shot that
    happens to be letterboxed differently, and three readings across the body
    of the cut outvote one. The head and the tail are avoided deliberately --
    that is where fades and cards live.

    ``duration`` of ``None`` (unprobeable) falls back to the old fixed offset,
    which is the best guess available and no worse than before.
    """
    probe_len = PROBE_LEN if probe_len is None else probe_len
    if not duration or duration <= 0:
        return [(PROBE_AT, probe_len)]
    windows = []
    for fraction in PROBE_FRACTIONS:
        length = min(probe_len, duration)
        start = max(0.0, min(duration * fraction, duration - length))
        window = (round(start, 3), round(length, 3))
        if window not in windows:
            windows.append(window)
    return windows


def probe_media_duration(video):
    """A source's length in seconds, or ``None`` if it cannot be read.

    ``None`` is a real answer, not an error: ``find_ffprobe`` raises when the
    only ffmpeg available is imageio's bundled binary, which ships with no
    ffprobe beside it. A caller that cannot measure the source falls back to
    the fixed probe offset, which is what it did before issue #161 anyway.
    """
    try:
        ffprobe = find_ffprobe()
    except Exception:
        return None
    cmd = [*ffprobe, "-v", "error",
           "-show_entries", "format=duration", "-of",
           "default=noprint_wrappers=1:nokey=1", str(Path(video).resolve())]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(proc.stdout.strip())
    except (subprocess.CalledProcessError, ValueError, OSError):
        return None


def detect_picture_status(video):
    """``(rect, status)`` -- the picture area, and how confidently it is known.

    ``status`` is one of:

    * ``"letterboxed"`` -- cropdetect agreed on a rect smaller than the frame;
    * ``"full-frame"``  -- it decoded and found no matte, so the frame IS the
      picture and placing against it is correct;
    * ``"undecodable"`` -- nothing decoded anywhere: no decoder, an unreadable
      file, or a source shorter than every probe window.

    The last two used to be the same ``None``, which is the whole of issue
    #161: a caller could not tell "there is no matte" from "I never looked",
    and one of those is safe to place against and the other is not.
    """
    ffmpeg = find_ffmpeg()
    src = str(Path(video).resolve())
    readings = []
    decoded = False
    for start, length in probe_windows(probe_media_duration(video)):
        cmd = [*ffmpeg, "-nostdin", "-hide_banner",
               "-ss", str(start), "-t", str(length), "-i", src,
               "-vf", "cropdetect=24:2:0", "-f", "null", "-"]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        found = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", proc.stderr)
        if found:
            decoded = True
            readings.extend(found)
    if not readings:
        return None, ("full-frame" if decoded else "undecodable")
    # The steadiest reading across every probe window, not the last one.
    best = Counter(readings).most_common(1)[0][0]
    w, h, x, y = (int(v) for v in best)
    return (x, y, w, h), "letterboxed"


def detect_picture(video):
    """Find the real picture area inside a letterboxed frame.

    Bungie's cinematics are 2.39:1 delivered in a 16:9 file, so ~140px of the
    top and bottom of every frame is baked-in black. Anything positioned
    against the *frame* -- a nameplate on a 10% bottom margin -- ends up
    hanging off the picture and onto the bar, which reads as a mistake.

    Returns ``(x, y, w, h)``, or ``None`` when there is no rect to give. Use
    ``detect_picture_status`` when the caller needs to know WHY there is none
    -- "no matte" and "never looked" are different answers (issue #161).
    """
    return detect_picture_status(video)[0]


def load_shots(path):
    with Path(path).open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data["shots"] if isinstance(data, dict) else data


def _still_argv(ffmpeg, image, duration, out_path, keep_audio):
    cmd = list(ffmpeg) + ["-v", "error", "-y", "-loop", "1", "-t", f"{duration:.3f}",
                          "-i", str(image)]
    if keep_audio:
        cmd += ["-f", "lavfi", "-t", f"{duration:.3f}",
                "-i", "anullsrc=r=48000:cl=stereo",
                # Explicit maps: with two inputs, implicit selection drops the
                # silent track and the still stops matching the cut clips.
                "-map", "0:v:0", "-map", "1:a:0",
                # PCM, not AAC: an intermediate is a link in the middle of a
                # chain the audio standard requires to be lossless (issue
                # #144), and PCM also has no extradata for the concat demuxer
                # to bind from the first segment -- the trap that rules FLAC
                # out here. It is silence, so this costs only disk.
                *INTERMEDIATE_AUDIO_ARGS]
    else:
        cmd += ["-map", "0:v:0", "-an"]
    cmd += ["-vf", VIDEO_FILTER,
            *conform.video_encode_args(crf=18, preset="medium"), str(out_path)]
    return cmd


def still_clip(ffmpeg, image, duration, out_path, keep_audio=True):
    """Render a still image as a clip in the common intermediate format.

    An artwork card takes the slot a dropped shot left behind, so it has to be
    indistinguishable from a cut clip to the concat demuxer: same size, rate and
    pixel format, and the *same* audio disposition. Giving a still a silent
    track when the other clips are video-only (which is what ``--audio`` does)
    would make it the only input with a stream the others lack, and the join
    fails.

    This is the LOCAL executor -- the encode runs memory-capped
    (``tools.farm.run_capped_local``), because every render.py entry point is
    farm-first and a local encode is a fallback with a stated reason, never
    a silent unbounded one. The farm path builds the same argv with
    ``_still_argv`` and runs it in the pod.
    """
    from tools import farm
    farm.run_capped_local(
        _still_argv(ffmpeg, image, duration, out_path, keep_audio),
        reason="render clip on this host", check=True)


def cut_clip(ffmpeg, src, start_sec, duration, out_path, keep_audio=True):
    """Cut one clip and normalize it to the common intermediate format.

    ``-ss`` goes *after* ``-i`` (output seeking): ffmpeg decodes from the start
    and discards, so the in-point is exact on the source timeline.

    Input-side ``-ss`` is ~2.6x faster and is also accurate in modern ffmpeg
    (it seeks to the closest point before the target, then decodes and discards
    — it does not simply snap to a keyframe). It is still wrong *here*, for a
    subtler reason: it rebases output timestamps to zero, which shifts the phase
    of the 29.97 -> 60000/1001 fps conversion below and changes which source
    frames are duplicated. Measured on the same in-point, the two produce
    different frames.

    Normalizing every clip to one size/rate/pixel format is what lets the concat
    demuxer join them: it requires identical stream properties across inputs.

    Like ``still_clip``, this is the LOCAL executor: memory-capped via
    ``tools.farm.run_capped_local``. The farm path builds the same argv with
    ``_cut_argv``.
    """
    from tools import farm
    farm.run_capped_local(
        _cut_argv(ffmpeg, src, start_sec, duration, out_path, keep_audio),
        reason="render clip on this host", check=True)


def _cut_argv(ffmpeg, src, start_sec, duration, out_path, keep_audio):
    cmd = list(ffmpeg) + [
        "-v", "error", "-y",
        "-i", str(src),
        "-ss", f"{start_sec:.3f}", "-t", f"{duration:.3f}",
        "-vf", VIDEO_FILTER,
        *conform.video_encode_args(crf=18, preset="medium"),
    ]
    if keep_audio:
        # PCM: no lossy generation mid-chain (issue #144), and no extradata for
        # the concat demuxer to mismatch.
        cmd += list(INTERMEDIATE_AUDIO_ARGS)
    else:
        cmd += ["-an"]
    cmd.append(str(out_path))
    return cmd


# A bed may run past the cut -- `-shortest` trims the tail, which is the whole
# point of it. It may not fall SHORT, because the same flag then trims the
# PICTURE. Rounding across a per-clip sum is real, so the comparison carries a
# frame or two of slack.
CONCAT_BED_TOLERANCE_SEC = 0.1


def _check_bed_covers_the_cut(clip_paths, audio_bed):
    """Refuse a bed shorter than the cut it is muxed against.

    ``concat`` passes ``-shortest``, which stops the OUTPUT at the shorter of
    the two mapped streams -- picture included. A bed longer than the cut is
    the intended use and is trimmed. A bed that is shorter silently truncates
    the film, exits 0, and says nothing: the render just ends early.

    That is a wrong result rather than a missing string, so it fails loudly
    instead of degrading -- AGENTS.md's degrade rule covers copy nobody has
    written yet, not footage silently dropped on the floor.

    Unmeasurable is not the same as wrong: ``probe_media_duration`` returns
    ``None`` when there is no ffprobe to be had (imageio's bundled ffmpeg
    ships without one), and a check that cannot run must not block a render
    that would otherwise be fine.
    """
    bed_sec = probe_media_duration(audio_bed)
    if bed_sec is None:
        return
    cut_sec = 0.0
    for clip in clip_paths:
        one = probe_media_duration(clip)
        if one is None:
            return
        cut_sec += one
    if bed_sec + CONCAT_BED_TOLERANCE_SEC < cut_sec:
        raise RuntimeError(
            f"the audio bed is {bed_sec:.3f}s but the cut is {cut_sec:.3f}s "
            f"({cut_sec - bed_sec:.3f}s short). `-shortest` would trim the "
            f"PICTURE to the bed and exit 0, shipping a film that ends early. "
            f"Lengthen the bed, or shorten the cut deliberately.")


def _concat_argv(ffmpeg, list_path, out_path, audio_bed=None, audio_gain=None):
    """The join's argv, from the list file's PATH (its content is the
    caller's -- the local path writes real entries beside the output, the
    farm path hands the pod a rewritten one; see render())."""
    cmd = list(ffmpeg) + ["-v", "error", "-y", "-f", "concat", "-safe", "0",
                          "-i", str(list_path)]
    if audio_bed:
        cmd += ["-i", str(audio_bed), "-map", "0:v:0", "-map", "1:a:0", "-shortest"]
        if audio_gain is not None:
            cmd += ["-af", f"volume={audio_gain}"]
        cmd += ["-c:a", DELIVERY_AUDIO_CODEC]
    else:
        if audio_gain is not None:
            # Source audio from the clips; implicit selection picks it up.
            cmd += ["-af", f"volume={audio_gain}"]
        # State the codec even with no bed: the clips now carry PCM, and
        # the container's default would put the lossy generation back.
        cmd += ["-c:a", DELIVERY_AUDIO_CODEC]
    cmd += conform.video_encode_args(crf=18, preset="medium")
    cmd.append(str(out_path))
    return cmd


def concat(ffmpeg, clip_paths, out_path, audio_bed=None, workdir=None,
           audio_gain=None):
    """Join normalized clips with the concat demuxer.

    The list file is written into ``workdir`` rather than /tmp: a containerized
    ffmpeg only sees the bind-mounted home, so a /tmp path would resolve inside
    the container namespace and the join would fail on a missing file.

    ``audio_gain`` is a STATIC volume scale applied at this final pass (never a
    limiter, never a normaliser): it exists so tools/peaks.py's delivered-peak
    correction can re-run just the concat instead of re-cutting every clip.
    None means no filter, so an uncorrected render is bit-identical to before.

    This is the LOCAL executor -- memory-capped via
    ``tools.farm.run_capped_local``. The farm path builds the same argv with
    ``_concat_argv`` and runs the whole chain in one pod.
    """
    from tools import farm
    workdir = Path(workdir or Path(out_path).parent)
    list_path = workdir / "concat_list.txt"
    list_path.write_text(
        "".join(f"file '{Path(c).resolve()}'\n" for c in clip_paths), encoding="utf-8"
    )
    try:
        if audio_bed:
            _check_bed_covers_the_cut(clip_paths, audio_bed)
        farm.run_capped_local(
            _concat_argv(ffmpeg, list_path, out_path, audio_bed=audio_bed,
                         audio_gain=audio_gain),
            reason="render join on this host", check=True)
    finally:
        list_path.unlink(missing_ok=True)


def resolve_duration(shot):
    """A shot's hold in seconds, clamped to the span that was vetted.

    story.py clamps a beat's hold at the cut; this is the same clamp at the
    render, for a shotlist build_story never produced — hand-edited, or from a
    future producer. A hold longer than ``end_sec - start_sec`` makes
    ``-ss start_sec -t duration`` decode past the out-point into footage no
    tagger vetted: the ``clean``-gate violation the story-side clamp exists to
    prevent. Clamp it here too, and warn naming the shot rather than silently
    truncating.

    A still has no out-point to overrun, so its authored duration stands.
    """
    if shot.get("still"):
        return float(shot.get("duration") or 2.0)
    duration = shot.get("duration") or (shot["end_sec"] - shot["start_sec"])
    vetted = shot["end_sec"] - shot["start_sec"]
    # Both endpoints are rounded to milliseconds when the shotlist is written,
    # so `end - start` reconstructs the duration with a few femtoseconds of
    # float error -- 85.996 - 72.94 is 13.055999999999997, not 13.056. Compared
    # exactly, that "overruns" and every single shot warns, which destroys the
    # signal: this message exists to name a REAL clean-gate violation, and one
    # that fires on all 33 shots is one nobody reads. A microsecond is far below
    # a frame at any frame rate, so anything inside it is noise, not an overrun.
    if duration > vetted + 1e-6:
        print(f"  CLAMPED: shot {shot['segment_id']} asked for {duration:g}s, "
              f"shot holds {vetted:g}s", file=sys.stderr)
        duration = vetted
    return duration


def cap_holds(shots, max_shot_sec, log=None):
    """Trim any shot held longer than ``max_shot_sec``, from its tail.

    A detector-derived beat can be far longer than an edit wants — this
    cinematic ends on a 25-second static gateway shot, which is a fine *beat*
    and a terrible final *cut*. The in-point is what the index worked to find,
    so the trim always comes off the end and never moves the start.

    The hold is first clamped to the shot's own vetted span (see
    ``resolve_duration``), and the clamp is written back so the render does
    not resolve — and warn about — the same overrun a second time.
    """
    if not max_shot_sec:
        return list(shots)
    out = []
    for shot in shots:
        duration = resolve_duration(shot)
        if shot.get("still"):
            out.append(shot)
            continue
        if duration > max_shot_sec:
            if log:
                log(f"  trimmed {shot['segment_id']} {duration:.1f}s -> {max_shot_sec:.1f}s")
            shot = dict(shot, duration=float(max_shot_sec),
                        end_sec=shot["start_sec"] + float(max_shot_sec))
        elif shot.get("duration") and shot["duration"] != duration:
            shot = dict(shot, duration=duration)
        out.append(shot)
    return out


def render(shots, media_dir, out_path, keep_audio=True, audio_bed=None, verbose=True,
           ffmpeg=None, target_dbtp=peaks.DEFAULT_TARGET_DBTP, local=False):
    """Cut the shot list and join it. REMOTE BY DEFAULT (AGENTS.md: "always
    prefer remote encoding when available"): when the cluster answers, the
    clips and the concat run as one chain in a single pod
    (``tools.farm.run_ffmpeg_chain_on_cluster``) and only the finished cut is
    fetched back. ``local=True`` -- or a cluster that does not answer -- runs
    the same argvs on this host, memory-capped, with the reason printed.
    """
    from tools import farm
    ffmpeg = ffmpeg or find_ffmpeg()
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    audio_bed = Path(audio_bed).resolve() if audio_bed else None
    if local:
        use_farm, farm_why = False, "--local given"
    else:
        use_farm, farm_why = farm.cluster_available()
    if use_farm:
        print("render: cluster reachable; the cut encodes on the farm "
              "(--local to force this host)", file=sys.stderr)
    else:
        print(f"render: encoding on THIS host -- {farm_why}", file=sys.stderr)

    rendered, missing = [], []
    # Intermediates live beside the output, not in /tmp, so a containerized
    # ffmpeg can see them through the same bind mount as the source media.
    # (On the farm path these paths name POD-side intermediates -- the helper
    # rewrites every token under this directory into the pod's chain dir.)
    with tempfile.TemporaryDirectory(dir=out_path.parent, prefix=".render-") as tmp:
        jobs = []  # (kind, source-or-image, shot, duration, clip)
        total = 0.0
        for n, shot in enumerate(shots, 1):
            duration = resolve_duration(shot)
            clip = Path(tmp) / f"clip_{n:03d}{INTERMEDIATE_SUFFIX}"
            if shot.get("still"):
                image = Path(shot["still"]).expanduser().resolve()
                if not image.exists():
                    missing.append(shot)
                    continue
                if verbose:
                    print(f"  [{n:>2}] STILL ({duration:.2f}s)  "
                          f"{shot.get('beat', image.name)}")
                jobs.append(("still", image, shot, duration, clip))
            else:
                src = resolve_media(shot["video_id"], media_dir)
                if src is None:
                    missing.append(shot)
                    continue
                if verbose:
                    print(f"  [{n:>2}] {shot['start_tc']}–{shot['end_tc']} "
                          f"({duration:.2f}s)  "
                          f"{shot.get('beat', shot['segment_id'])}")
                jobs.append(("cut", src, shot, duration, clip))
            rendered.append(clip)
            total += duration
        if not jobs:
            raise RuntimeError("nothing to render: no shot resolved to a source file")
        # Fail fast on a short bed BEFORE paying for any encode: on the local
        # path concat() re-checks against the real clip files; on the farm
        # path the clips only ever exist pod-side, so this planned-duration
        # check is the one that keeps a short bed from silently ending the
        # film early (the `-shortest` trap _check_bed_covers_the_cut names).
        if audio_bed:
            bed_sec = probe_media_duration(audio_bed)
            if bed_sec is not None and \
                    bed_sec + CONCAT_BED_TOLERANCE_SEC < total:
                raise RuntimeError(
                    f"the audio bed is {bed_sec:.3f}s but the cut is "
                    f"{total:.3f}s ({total - bed_sec:.3f}s short). "
                    "`-shortest` would trim the PICTURE to the bed and exit "
                    "0, shipping a film that ends early. Lengthen the bed, "
                    "or shorten the cut deliberately.")

        def run_chain(audio_gain=None):
            """The whole cut as one farm chain: every clip encode, then the
            concat, in one pod workspace; only the finished cut comes back."""
            argvs, inputs = [], []
            for kind, target, shot, duration, clip in jobs:
                if kind == "still":
                    argvs.append(_still_argv(["ffmpeg"], target, duration,
                                             clip, keep_audio))
                else:
                    argvs.append(_cut_argv(["ffmpeg"], target,
                                           shot["start_sec"], duration,
                                           clip, keep_audio))
                inputs.append(target)
            list_path = Path(tmp) / "concat_list.txt"
            argvs.append(_concat_argv(["ffmpeg"], list_path, out_path,
                                      audio_bed=audio_bed,
                                      audio_gain=audio_gain))
            if audio_bed:
                inputs.append(audio_bed)
            farm.run_ffmpeg_chain_on_cluster(
                argvs, inputs=inputs, out=out_path, tmp_prefix=tmp,
                # The list the LOCAL run would write; the helper rewrites
                # its contents to the pod's paths and places it there.
                text_files={list_path: "".join(f"file '{c}'\n"
                                               for c in rendered)},
                expected_duration=total)

        if use_farm:
            run_chain()
        else:
            for kind, target, shot, duration, clip in jobs:
                if kind == "still":
                    still_clip(ffmpeg, target, duration, clip, keep_audio)
                else:
                    cut_clip(ffmpeg, target, shot["start_sec"], duration,
                             clip, keep_audio)
            concat(ffmpeg, rendered, out_path, audio_bed, workdir=tmp)
        # A cut must not ship above the delivered-peak band either: measure the
        # FINISHED file and re-run the concat at a corrected static gain until
        # it has real headroom (tools/peaks.py -- never a limiter, never a
        # normaliser). Only the concat is re-run, not the clip cuts. A muted
        # render has no audio to measure.
        #
        # Farm path: the pod's intermediates are gone after the fetch, so a
        # correction re-runs the whole chain at the derived gain -- the
        # cluster absorbs the re-encode, which is what it is for.
        if target_dbtp is not None and (keep_audio or audio_bed):
            def rerun(new_gain):
                if use_farm:
                    run_chain(audio_gain=new_gain)
                else:
                    concat(ffmpeg, rendered, out_path, audio_bed, workdir=tmp,
                           audio_gain=new_gain)

            peaks.correct_delivered_peak(
                out_path, 1.0, target_dbtp, rerun, ffmpeg=ffmpeg,
                attempts=5,
                margin_db=peaks.DELIVERED_BAND_MARGIN_DB)
    return rendered, missing


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render a story.py shot list to a video file.")
    ap.add_argument("shotlist", help="JSON shot list from tools/story.py --format json")
    ap.add_argument("--media", default=str(REPO_ROOT / "media"),
                    help="directory of source video files named <video_id>.mp4")
    ap.add_argument("--out", default=str(REPO_ROOT / "renders" / "cut.mp4"))
    ap.add_argument("--audio", help="lay this audio file over the finished cut")
    ap.add_argument("--no-container", action="store_true",
                    help="skip the ffmpeg container and use a local binary")
    ap.add_argument("--max-shot-sec", type=float, default=None,
                    help="trim any shot held longer than this, from its tail")
    ap.add_argument("--target-dbtp", type=float, default=peaks.DEFAULT_TARGET_DBTP,
                    help="delivered true-peak target in dBTP; the finished file "
                         "is measured and re-run at a corrected static gain "
                         f"until it has headroom (default {peaks.DEFAULT_TARGET_DBTP})")
    ap.add_argument("--local", action="store_true",
                    help="cut and join on THIS host even when the farm cluster "
                         "is reachable (the escape hatch; the encodes run "
                         "under tools.farm.run_capped_local's memory cap)")
    args = ap.parse_args(argv)

    ffmpeg = find_ffmpeg(prefer_container=not args.no_container)
    shots = load_shots(args.shotlist)
    print(f"ffmpeg: {' '.join(ffmpeg)}")
    print(f"rendering {len(shots)} shot(s) -> {args.out}")
    shots = cap_holds(shots, args.max_shot_sec, log=print)
    rendered, missing = render(shots, args.media, args.out,
                               keep_audio=not args.audio,
                               audio_bed=args.audio, ffmpeg=ffmpeg,
                               target_dbtp=args.target_dbtp,
                               local=args.local)
    total = sum(resolve_duration(s) for s in shots)
    print(f"OK: {len(rendered)} clip(s), ~{total:.1f}s -> {args.out}")
    for shot in missing:
        src = shot.get("still") or shot.get("video_id")
        print(f"  MISSING SOURCE: {src} (shot {shot.get('segment_id','?')} skipped)",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
