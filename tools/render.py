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
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

MEDIA_EXTS = (".mp4", ".mkv", ".webm", ".mov")

# Common intermediate format. Every clip is normalized to this so the concat
# demuxer can join them without re-muxing mismatched streams.
TARGET_W, TARGET_H, TARGET_FPS = 1920, 1080, 30

# Bluefin runs a long-lived ffmpeg container with $HOME bind-mounted at the same
# path, so host paths resolve unchanged inside it (see docs/rendering.md).
DEFAULT_CONTAINER = "bluefin-thumbnailer"
DEFAULT_IMAGE = "ghcr.io/jrottenberg/ffmpeg"


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


def load_shots(path):
    with Path(path).open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data["shots"] if isinstance(data, dict) else data


def cut_clip(ffmpeg, src, start_sec, duration, out_path, keep_audio=True):
    """Cut one clip and normalize it to the common intermediate format.

    ``-ss`` goes *after* ``-i`` (output seeking): ffmpeg decodes from the start
    and discards, so the in-point is exact on the source timeline.

    Input-side ``-ss`` is ~2.6x faster and is also accurate in modern ffmpeg
    (it seeks to the closest point before the target, then decodes and discards
    — it does not simply snap to a keyframe). It is still wrong *here*, for a
    subtler reason: it rebases output timestamps to zero, which shifts the phase
    of the 29.97 -> 30 fps conversion below and changes which source frames are
    duplicated. Measured on the same in-point, the two produce different frames.

    Normalizing every clip to one size/rate/pixel format is what lets the concat
    demuxer join them: it requires identical stream properties across inputs.
    """
    vf = (
        f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
        f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2,"
        f"fps={TARGET_FPS},format=yuv420p"
    )
    cmd = list(ffmpeg) + [
        "-v", "error", "-y",
        "-i", str(src),
        "-ss", f"{start_sec:.3f}", "-t", f"{duration:.3f}",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p",
    ]
    if keep_audio:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
    else:
        cmd += ["-an"]
    cmd.append(str(out_path))
    subprocess.run(cmd, check=True)


def concat(ffmpeg, clip_paths, out_path, audio_bed=None, workdir=None):
    """Join normalized clips with the concat demuxer.

    The list file is written into ``workdir`` rather than /tmp: a containerized
    ffmpeg only sees the bind-mounted home, so a /tmp path would resolve inside
    the container namespace and the join would fail on a missing file.
    """
    workdir = Path(workdir or Path(out_path).parent)
    list_path = workdir / "concat_list.txt"
    list_path.write_text(
        "".join(f"file '{Path(c).resolve()}'\n" for c in clip_paths), encoding="utf-8"
    )
    try:
        cmd = list(ffmpeg) + ["-v", "error", "-y", "-f", "concat", "-safe", "0",
                              "-i", str(list_path)]
        if audio_bed:
            cmd += ["-i", str(audio_bed), "-map", "0:v:0", "-map", "1:a:0", "-shortest",
                    "-c:a", "aac", "-b:a", "192k"]
        cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]
        cmd.append(str(out_path))
        subprocess.run(cmd, check=True)
    finally:
        list_path.unlink(missing_ok=True)


def render(shots, media_dir, out_path, keep_audio=True, audio_bed=None, verbose=True,
           ffmpeg=None):
    ffmpeg = ffmpeg or find_ffmpeg()
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    audio_bed = Path(audio_bed).resolve() if audio_bed else None
    rendered, missing = [], []
    # Intermediates live beside the output, not in /tmp, so a containerized
    # ffmpeg can see them through the same bind mount as the source media.
    with tempfile.TemporaryDirectory(dir=out_path.parent, prefix=".render-") as tmp:
        for n, shot in enumerate(shots, 1):
            src = resolve_media(shot["video_id"], media_dir)
            if src is None:
                missing.append(shot)
                continue
            duration = shot.get("duration") or (shot["end_sec"] - shot["start_sec"])
            clip = Path(tmp) / f"clip_{n:03d}.mp4"
            if verbose:
                print(f"  [{n:>2}] {shot['start_tc']}–{shot['end_tc']} "
                      f"({duration:.2f}s)  {shot.get('beat', shot['segment_id'])}")
            cut_clip(ffmpeg, src, shot["start_sec"], duration, clip, keep_audio)
            rendered.append(clip)
        if not rendered:
            raise RuntimeError("nothing to render: no shot resolved to a source file")
        concat(ffmpeg, rendered, out_path, audio_bed, workdir=tmp)
    return rendered, missing


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render a story.py shot list to a video file.")
    ap.add_argument("shotlist", help="JSON shot list from tools/story.py --format json")
    ap.add_argument("--media", default=str(REPO_ROOT / "media"),
                    help="directory of source video files named <video_id>.mp4")
    ap.add_argument("--out", default=str(REPO_ROOT / "renders" / "cut.mp4"))
    ap.add_argument("--mute", action="store_true", help="drop source audio")
    ap.add_argument("--audio", help="lay this audio file over the finished cut")
    ap.add_argument("--no-container", action="store_true",
                    help="skip the ffmpeg container and use a local binary")
    args = ap.parse_args(argv)

    ffmpeg = find_ffmpeg(prefer_container=not args.no_container)
    shots = load_shots(args.shotlist)
    print(f"ffmpeg: {' '.join(ffmpeg)}")
    print(f"rendering {len(shots)} shot(s) -> {args.out}")
    rendered, missing = render(shots, args.media, args.out,
                               keep_audio=not args.mute and not args.audio,
                               audio_bed=args.audio, ffmpeg=ffmpeg)
    total = sum(s.get("duration") or (s["end_sec"] - s["start_sec"]) for s in shots)
    print(f"OK: {len(rendered)} clip(s), ~{total:.1f}s -> {args.out}")
    for shot in missing:
        print(f"  MISSING SOURCE: {shot['video_id']} (shot {shot['segment_id']} skipped)",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
