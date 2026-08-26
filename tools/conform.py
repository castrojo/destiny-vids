#!/usr/bin/env python3
"""One delivery conformance spec, and a cached conformer for delivered acts.

The show's acts are delivered from several projects at several frame rates
(30/1, 60/1, 60000/1001) and colour-tag states. ``tools/megacut.py`` can join
them only after normalising every one to a single bitstream shape -- which
used to mean re-encoding the whole programme on every assembly, ~24 minutes
of x264 for 20 minutes of picture, even when nothing had changed.

This module fixes that in two halves:

* **The spec** (``DELIVERY``) is the single definition of what a delivered
  file must look like so the concat demuxer can join it to any other
  conformant file with ``-c:v copy``: 60000/1001, 1920x1080, yuv420p, BT.709
  written into the VUI (the ``-color_*`` flags alone are not enough -- x264
  copies only the matrix from them, so primaries and transfer must be forced
  through ``-x264-params``; see megacut.py's recorded failure), H.264
  High@4.2, closed GOP. The owner approved 59.94 fps as the delivery rate.
  Level 4.2 is the floor that 1920x1080 at 59.94 fits (4.1 caps at ~30 fps
  for that frame size).

* **The cache.** ``ensure()`` conforms a delivered act and keeps the result
  keyed by (source content hash + spec version), so the SECOND and later
  megacuts against unchanged acts conform nothing -- the probe is an ffprobe
  stream read and the cache lookup is a stat.

Conforming is a PICTURE operation. Audio is carried through losslessly --
stream-copied, never re-encoded, and never passed near a normaliser, limiter,
EQ or gain (docs/skills/audio/SKILL.md).

    python3 tools/conform.py act.mp4 [--out DIR]   # conform (cached)
    python3 tools/conform.py act.mp4 --check       # report, do no work

What the probe cannot see: whether the stream's GOPs are closed. No cheap
bitstream read answers that, so closed GOP is guaranteed *by construction* --
every encoder in this repo that emits delivery footage (render.py,
conform.py, megacut.py's cards) sets ``-flags +cgop`` -- and the probe covers
the properties it CAN measure. A file hand-built outside those tools that
claims conformance gets caught at the join by ``verify_programme``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _find_ffmpeg():
    """The one ffmpeg resolver is render.find_ffmpeg (docs/rendering.md).

    Imported lazily: render.py imports THIS module for the delivery spec, so
    a top-level import would be a cycle.
    """
    from tools import render
    return render.find_ffmpeg()

# Bump when DELIVERY changes: it is part of the cache key, so an old spec's
# conformed files are simply orphaned rather than silently trusted.
SPEC_VERSION = "delivery-v1"


@dataclass(frozen=True)
class DeliverySpec:
    """What a delivered file must be for the concat demuxer to join it blind.

    ``crf``/``preset`` are NOT conformance fields -- nothing in a probe can
    read them back out -- they are the quality the conforming encode uses,
    and they match the megacut plan's own so a conformed act and a freshly
    encoded card land on the same x264 settings (the join copies bitstreams,
    so their SPS must agree; see megacut.py's build_concat_command).
    """

    fps: str = "60000/1001"          # 59.94, as a rational so nothing rounds it to 60
    width: int = 1920
    height: int = 1080
    pix_fmt: str = "yuv420p"
    color_primaries: str = "bt709"
    color_transfer: str = "bt709"
    colorspace: str = "bt709"
    profile: str = "high"
    level: str = "4.2"               # 1080p59.94 does not fit in 4.1's MB/s
    crf: str = "16"
    preset: str = "slow"


DELIVERY = DeliverySpec()

# ffprobe cannot agree with itself: the jrottenberg container build prints the
# numeric profile IDC (High == 100), the linuxbrew build prints the name.
_PROFILE_ALIASES = {"high": "high", "100": "high"}


def video_filter_chain():
    """The normalising -vf chain. Kept identical in shape to megacut's
    segment chain: scale, square pixels, rate, pixel format, zeroed PTS."""
    return (f"scale={DELIVERY.width}:{DELIVERY.height}:flags=lanczos,setsar=1,"
            f"fps={DELIVERY.fps},format={DELIVERY.pix_fmt},setpts=PTS-STARTPTS")


def video_encode_args(*, crf=None, preset=None, threads=None):
    """The x264 argv that produces a spec-conformant bitstream.

    Shared by conform.py, render.py and megacut.py's card segments so every
    delivery-bitstream encoder in the repo sets the same profile, level,
    closed GOP and VUI from one place. The ``-color_*`` flags describe the
    frames to filters; the ``-x264-params`` VUI write is what actually lands
    all three colour fields in the bitstream (verified by ffprobe, not
    assumed -- see megacut.py).
    """
    args = [
        "-c:v", "libx264",
        "-preset", str(preset or DELIVERY.preset),
        "-crf", str(crf or DELIVERY.crf),
        "-pix_fmt", DELIVERY.pix_fmt,
        "-profile:v", DELIVERY.profile,
        "-level:v", DELIVERY.level,
        # Closed GOP: a frame after a join must never reference one before
        # it. x264's default is already closed; state it so a config change
        # cannot silently open the joins.
        "-flags", "+cgop",
        "-color_primaries", DELIVERY.color_primaries,
        "-color_trc", DELIVERY.color_transfer,
        "-colorspace", DELIVERY.colorspace,
        "-x264-params", f"colorprim={DELIVERY.color_primaries}"
                        f":transfer={DELIVERY.color_transfer}"
                        f":colormatrix={DELIVERY.colorspace}",
    ]
    if threads:
        args += ["-threads", str(threads)]
    return args


def ffprobe_for(ffmpeg):
    """The ffprobe beside a resolved ffmpeg argv prefix.

    ``render.find_ffmpeg`` returns a *prefix* (``podman exec <c> ffmpeg`` or a
    plain path), so the probe is the same prefix with the trailing ``ffmpeg``
    swapped -- that resolves to the container's ffprobe or the sibling binary
    without a second resolution order to keep in step.
    """
    prefix = list(ffmpeg)
    head, sep, tail = prefix[-1].rpartition("ffmpeg")
    prefix[-1] = f"{head}ffprobe{tail}" if sep else "ffprobe"
    return prefix


def probe_video(path, ffprobe):
    """The video stream's delivery-relevant properties, as ffprobe reports."""
    out = subprocess.run(
        [*ffprobe, "-v", "error", "-select_streams", "v:0",
         "-show_entries",
         "stream=codec_name,width,height,avg_frame_rate,pix_fmt,"
         "color_primaries,color_transfer,color_space,profile,level",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    streams = json.loads(out.stdout).get("streams") or []
    if not streams:
        raise RuntimeError(f"no video stream in {path}")
    return streams[0]


class ScopeMismatch(RuntimeError):
    """A source whose shape is not the one an act was composed against."""


def scope_filter(path, scope_w, scope_h, *, ffmpeg=None, ffprobe=None,
                 label=None):
    """The filter that brings a source to an act's AUTHORED scope frame.

    A scope act is composed at ``scope_w x scope_h`` inside the delivery
    raster and seated there with black bars. That seat is authored geometry —
    title cards and plates are rendered against it — while the size the source
    file happens to arrive at is a property of the FILE, and files get
    replaced.

    Conflating the two is a real failure here. Both perfume builders hardcoded
    the seat as ``pad=1920:1080:0:138``, correct only while the source arrived
    at exactly 1920x804. When the 4K re-upload replaced it (3840x1608 — the
    same 2.388:1 scope at twice the linear size) ``pad`` failed outright:
    "Padded dimensions cannot be smaller than input dimensions". You cannot
    pad a frame down.

    So the resampling is resolved from the source and the seat is not:

    * already at the scope frame — no filter at all, because a no-op
      downscale is still a generation;
    * larger — one lanczos downscale, in the same pass as the grade and the
      encode. At a 1080p ``DELIVERY`` that is the entire benefit of a 4K
      source: one resampling generation from the original bit depth instead
      of somebody else's downscale plus an 8-bit re-encode. It does NOT make
      the delivered picture 4K;
    * smaller — still scaled, so the act builds, but reported: an upscale
      invents no detail and the operator should know a better source is
      wanted.

    Aspect is a gate, not a guess. Scaling a differently-shaped source onto
    this frame would stretch the picture, moving every frame nobody asked to
    move, so it raises ``ScopeMismatch`` instead.

    Returns ``(filter_prefix, note)``. The prefix is ``""`` or ends in a
    comma, so callers can splice it straight into a chain.

    ffmpeg is resolved HERE and only if a probe actually happens, so a caller
    does not have to find an encoder just to ask a question about a file. The
    offline suite has no ffmpeg at all, and a caller that resolved one eagerly
    made these paths untestable on CI.
    """
    who = label or Path(path).name
    if ffprobe is None:
        ffprobe = ffprobe_for(ffmpeg if ffmpeg is not None else _find_ffmpeg())
    stream = probe_video(path, ffprobe)
    w, h = int(stream["width"]), int(stream["height"])
    if (w, h) == (scope_w, scope_h):
        return "", f"{w}x{h} (authored scope, no resampling)"
    want, got = scope_w / scope_h, w / h
    if abs(want - got) > 0.005:
        raise ScopeMismatch(
            f"{who} is {w}x{h} ({got:.3f}:1), but this act is composed for "
            f"{scope_w}x{scope_h} ({want:.3f}:1). Scaling it would stretch "
            f"the picture and move a frame nobody asked to move. Re-conform "
            f"the source, or re-author the seat.")
    if w < scope_w:
        print(f"scope: {who} is {w}x{h}, SMALLER than the {scope_w}x{scope_h} "
              f"scope frame -- upscaling, which adds no detail. A better "
              f"source exists somewhere.", file=sys.stderr)
    return (f"scale={scope_w}:{scope_h}:flags=lanczos,",
            f"{w}x{h} -> {scope_w}x{scope_h} (one lanczos generation, "
            f"{stream.get('pix_fmt', '?')} source)")


def _fps_close(reported, wanted):
    """Rational comparison, with room for spelling: 60000/1001 and 2997/50
    are both 59.94 (they differ in the fifth decimal), while 60/1 and 30/1
    are unmistakably something else.

    ``ZeroDivisionError`` is caught beside the parse errors because ffprobe
    reports ``0/0`` for a stream whose average frame rate is indeterminate,
    and ``float(den or 1)`` does not save us there -- ``"0"`` is a truthy
    string, so the fallback never fires. An unreadable rate is "not the spec",
    which is a mismatch to report; raising instead took the whole assembly
    down with it, since ``assemble()`` conforms every clip.
    ``farm._is_vfr`` guards the same shape for the same reason.
    """
    try:
        num, _, den = str(reported).partition("/")
        value = float(num) / float(den or 1)
    except (TypeError, ValueError, ZeroDivisionError):
        return False
    wnum, _, wden = str(wanted).partition("/")
    return abs(value - float(wnum) / float(wden or 1)) < 1e-3


def mismatches(props):
    """The ways a probed stream disagrees with the spec, as strings.

    Pure: takes the probe dict, returns the punch list. Empty means the file
    is joinable as-is. This is the conformance probe; closed GOP is covered
    by construction (see the module docstring), not here.
    """
    bad = []
    if props.get("codec_name") != "h264":
        bad.append(f"codec is {props.get('codec_name')}, not h264")
    if int(props.get("width", 0)) != DELIVERY.width or \
            int(props.get("height", 0)) != DELIVERY.height:
        bad.append(f"size is {props.get('width')}x{props.get('height')}, "
                   f"not {DELIVERY.width}x{DELIVERY.height}")
    if not _fps_close(props.get("avg_frame_rate"), DELIVERY.fps):
        bad.append(f"frame rate is {props.get('avg_frame_rate')}, "
                   f"not {DELIVERY.fps}")
    if props.get("pix_fmt") != DELIVERY.pix_fmt:
        bad.append(f"pixel format is {props.get('pix_fmt')}, not {DELIVERY.pix_fmt}")
    for field, wanted in (("color_primaries", DELIVERY.color_primaries),
                          ("color_transfer", DELIVERY.color_transfer),
                          ("color_space", DELIVERY.colorspace)):
        if props.get(field) != wanted:
            bad.append(f"{field} is {props.get(field)}, not {wanted}")
    profile = _PROFILE_ALIASES.get(str(props.get("profile")).lower())
    if profile != DELIVERY.profile:
        bad.append(f"profile is {props.get('profile')}, not {DELIVERY.profile}")
    try:
        level = int(props.get("level", 0)) / 10
    except (TypeError, ValueError):
        level = 0.0
    if abs(level - float(DELIVERY.level)) > 1e-9:
        bad.append(f"level is {props.get('level')}, not {DELIVERY.level}")
    return bad


def conforms(path, ffprobe):
    """(True, []) when the file is joinable as-is, else (False, reasons)."""
    bad = mismatches(probe_video(path, ffprobe))
    return (not bad, bad)


def content_hash(path):
    """SHA-256 of the file's bytes. The cache key's other half -- a file that
    changed must not be served its predecessor's conform."""
    with Path(path).open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def cache_root():
    """Where conformed files live. Big, derived, and safe to delete: every
    entry can be rebuilt from its source, which is the definition of a cache.
    """
    from tools.footage import xdg_cache
    return xdg_cache("DESTINY_CONFORM_CACHE", "conform")


def build_encode_command(src, dst, ffmpeg=None, threads=None, *, crf=None,
                         preset=None):
    """Re-encode the picture to the spec; carry the audio untouched.

    ``-map 0:a?`` + ``-c:a copy``: every audio stream rides through
    bit-exact -- the six FLAC masters stay FLAC, act VI's AAC stays the same
    AAC generation. Conforming never touches the soundtrack (the audio
    tenet), so there is nothing to gain-correct afterwards either.
    """
    ffmpeg = ffmpeg or _find_ffmpeg()
    return [
        *ffmpeg, "-nostdin", "-hide_banner",
        "-i", str(src),
        "-map", "0:v:0", "-map", "0:a?",
        "-vf", video_filter_chain(),
        *video_encode_args(crf=crf, preset=preset, threads=threads),
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(dst), "-y",
    ]


def ensure(source, out_dir=None, ffmpeg=None, threads=None, *, crf=None,
           preset=None, log=None, _probe=None, use_farm=None):
    """A spec-conformant version of ``source``, doing as little as possible.

    Returns ``(path, status)`` with status one of:

    * ``"conforms"``   -- the source already matches the spec; returned as-is.
    * ``"cache-hit"``  -- conformed earlier (same content, same spec version).
    * ``"conformed"``  -- encoded now.

    The encode lands beside the cache entry under a scratch name and is
    renamed over it only on success, so an interrupted conform never leaves
    a half-written file for the next run to trust. ``_probe`` substitutes the
    ffprobe stream read in tests, so the cache logic is checkable offline.

    The encode itself is remote by default (AGENTS.md: "always prefer remote
    encoding when available") -- a cache MISS used to mean a silent local
    x264 run even when megacut had farmed everything else, which is how a
    "--farm" build still loaded the workstation. ``use_farm`` pins the
    posture from a caller that already probed (megacut); ``None`` probes
    here. Local ffmpeg execution is prohibited (owner ruling, 2026-08-25):
    a cache miss on an unreachable cluster stops with FarmError naming why.
    """
    log = log or (lambda msg: print(msg, file=sys.stderr))
    src = Path(source)
    if _probe is not None:
        bad = mismatches(_probe(src))
    else:
        _ok, bad = conforms(src, ffprobe_for(ffmpeg or _find_ffmpeg()))
    if not bad:
        return src, "conforms"
    log(f"  conform {src.name}: " + "; ".join(bad))
    root = Path(out_dir) if out_dir else cache_root()
    entry_dir = root / SPEC_VERSION
    entry_dir.mkdir(parents=True, exist_ok=True)
    digest = content_hash(src)
    crf = str(crf or DELIVERY.crf)
    preset = str(preset or DELIVERY.preset)
    key = hashlib.sha256(f"{digest}\0{crf}\0{preset}".encode()).hexdigest()
    entry = entry_dir / f"{key}.mp4"
    if entry.exists():
        return entry, "cache-hit"
    tmp = entry_dir / f".{key}.tmp-{os.getpid()}.mp4"
    tmp.unlink(missing_ok=True)
    argv = build_encode_command(src, tmp, ffmpeg or _find_ffmpeg(), threads,
                                crf=crf, preset=preset)
    try:
        _encode(argv, src=src, out=tmp, use_farm=use_farm)
        tmp.replace(entry)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    entry.with_suffix(".json").write_text(json.dumps({
        "source": str(src),
        "sha256": digest,
        "crf": crf,
        "preset": preset,
        "spec": asdict(DELIVERY),
        "spec_version": SPEC_VERSION,
    }, indent=1) + "\n", encoding="utf-8")
    return entry, "conformed"


def _encode(argv, *, src, out, use_farm):
    """The conform encode, on the farm whenever it answers.

    ``use_farm`` is a tri-state: True/False pin the posture from a caller
    that probed already; None probes here. Local ffmpeg execution is
    prohibited (owner ruling, 2026-08-25): a cluster that cannot take the
    encode -- unreachable, asked not to, or failed mid-encode -- stops the
    conform with FarmError naming why. There is no workstation fallback.
    """
    from tools import farm
    if use_farm is None:
        use_farm, why = farm.cluster_available()
        if not use_farm:
            raise farm.FarmError(f"the cluster is not reachable ({why})")
    elif not use_farm:
        raise farm.FarmError(
            "local ffmpeg execution is prohibited (--local given)")
    farm.run_ffmpeg_on_cluster(argv, inputs=[src], out=out)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("inputs", nargs="+", help="delivered acts to conform")
    ap.add_argument("--out", help="cache directory (default: "
                    "$DESTINY_CONFORM_CACHE or ~/.cache/destiny-vids/conform)")
    ap.add_argument("--check", action="store_true",
                    help="report whether each file already conforms; "
                         "encode nothing. Exit 1 if any file does not conform.")
    ap.add_argument("--local", action="store_true",
                    help="REJECTED: local ffmpeg execution is prohibited "
                         "(owner ruling, 2026-08-25); kept only so its use "
                         "fails with the reason instead of silently farming")
    args = ap.parse_args(argv)

    ffmpeg = _find_ffmpeg()
    ffprobe = ffprobe_for(ffmpeg)

    if args.check:
        worst = 0
        for src in args.inputs:
            ok, bad = conforms(src, ffprobe)
            if ok:
                print(f"CONFORMS    {src}")
            else:
                print(f"NONCONFORM  {src}")
                for reason in bad:
                    print(f"            - {reason}")
                worst = 1
        return worst

    # Sequential: megacut owns conform parallelism across segments; this CLI
    # exists for one-off conforms and --check.
    for src in args.inputs:
        path, status = ensure(src, out_dir=args.out, ffmpeg=ffmpeg,
                              log=lambda _m: None,
                              use_farm=False if args.local else None)
        print(f"{status:<10} {src} -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
