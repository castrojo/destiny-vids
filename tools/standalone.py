"""Build standalone videos from one committed batch manifest.

A manifest in stories/standalone/<batch>.json records, per video: the pinned
yt-dlp source formats, authored excisions in source time, overlays, an
optional full-frame CTA takeover, a thumbnail pick, and audio probes. This
module owns the contract (schema/standalone-batch.schema.json), the
source-time -> output-time mapping every later stage relies on, and the
three commands that turn a record into a delivered file:

    python3 tools/standalone.py fetch  <manifest> <slug>
    python3 tools/standalone.py build  <manifest> <slug> [--local]
    python3 tools/standalone.py verify <manifest> <slug>

Nothing here is specific to any one video: the takeover is a generic
full-frame picture, the overlays are existing plate kinds, and every string
on screen comes from the manifest. The encode is farm-first
(``tools/farm.py``), one picture generation and one AAC generation, with the
delivered peak corrected by re-running from the SOURCE at a lower static
gain -- never by re-encoding the file it just wrote.
"""

from __future__ import annotations

import argparse
import array
import json
import math
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import conform, farm, peaks, plate, render, thumbnail  # noqa: E402

SCHEMA = REPO_ROOT / "schema" / "standalone-batch.schema.json"
SOURCE_DIR = REPO_ROOT / "media" / "standalone"
WORK_DIR = REPO_ROOT / "renders" / "standalone"
REVIEW_DIR = WORK_DIR / "review"

# yt-dlp's client for the pinned progressive-free format list. Measured
# against yt-dlp 2026.08.19 on all four batch sources: `android_vr` now warns
# that "https formats require a GVS PO Token which was not provided. They will
# be skipped" and answers with ONE muxed 360p/44.1 kHz AAC rung -- so a
# manifest pinning 137+251 would fail to fetch, and a "best" selector would
# silently deliver the resampled, band-limited sound the audio tenet forbids.
# `visionos` -- the client yt-dlp's own default order resolves to here --
# lists the full AVC video-only and non-DRC 48 kHz Opus ladder with no token.
# Quality does not rest on the client either way: both format ids come from
# the manifest, and the schema and loader both refuse a `-drc` id.
PLAYER_CLIENT = "visionos"

# The delivered container may differ from the sum of its parts by a frame or
# two of container rounding; more than this is a real edit drift.
DURATION_TOLERANCE_S = 0.08
# Below this, the delivered audio is not the source audio at that mark.
AUDIO_CORRELATION_FLOOR = 0.97
# How far the delivered window may be shifted against the source one before
# the comparison gives up. A codec and a container both add small, real
# delays -- an AAC encoder primes, an Opus stream pre-skips -- and a measured
# -1.0 ms offset is enough to invert the correlation of a tone. The search
# below finds that offset; it cannot manufacture a match, because a window
# from somewhere else in the film correlates with nothing at any lag.
ALIGNMENT_PAD_S = 0.05
# Mean absolute per-channel error between the delivered takeover frame and
# the approved CTA picture, 0-255.
CTA_FRAME_TOLERANCE = 3.0
PROBE_RATE = 8000
# Splice continuity, from the Saint-14 audio splice review: the step across
# a cut join as a ratio of the p99 sample-to-sample slew near it. At or
# below the target the join moves less than 99% of the signal's own moves,
# so it cannot click; past the blocker the join is an audible defect.
SPLICE_STEP_TARGET = 1.0
SPLICE_STEP_BLOCKER = 1.8


def load_manifest(path):
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    for video in data.get("videos", []):
        source = video.get("source") or {}
        audio_id = source.get("audio_format_id", "")
        if audio_id.endswith("-drc"):
            raise ValueError(f"{video['slug']}: DRC audio format is forbidden")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(data),
        key=lambda error: list(error.path),
    )
    if errors:
        raise ValueError("\n".join(
            f"{'/'.join(map(str, error.path))}: {error.message}"
            for error in errors
        ))
    return data


def entry_by_slug(manifest, slug):
    matches = [video for video in manifest["videos"] if video["slug"] == slug]
    if len(matches) != 1:
        raise KeyError(f"expected one video named {slug!r}, found {len(matches)}")
    return matches[0]


def cta_asset_path(video, manifest):
    """The takeover picture for one video: the video's own committed asset
    when its takeover names one (owner-approved per-video copy), otherwise
    the batch-wide ``cta_asset`` shared by every other takeover."""
    takeover = video.get("takeover") or {}
    return REPO_ROOT / (takeover.get("asset") or manifest["cta_asset"])


def _sorted_cuts(cuts):
    ordered = sorted(cuts or [], key=lambda cut: cut["start_sec"])
    previous_end = 0.0
    for cut in ordered:
        start, end = cut["start_sec"], cut["end_sec"]
        if start < previous_end or end <= start:
            raise ValueError(f"invalid or overlapping cut {start}-{end}")
        previous_end = end
    return ordered


def source_to_output(source_sec, cuts):
    removed = 0.0
    for cut in _sorted_cuts(cuts):
        start, end = cut["start_sec"], cut["end_sec"]
        if start <= source_sec < end:
            raise ValueError(
                f"{source_sec:.3f} is inside removed source range {start}-{end}"
            )
        if end <= source_sec:
            removed += end - start
    return source_sec - removed


def kept_ranges(duration_sec, cuts):
    cursor = 0.0
    kept = []
    for cut in _sorted_cuts(cuts):
        if cursor < cut["start_sec"]:
            kept.append((cursor, cut["start_sec"]))
        cursor = cut["end_sec"]
    if cursor < duration_sec:
        kept.append((cursor, duration_sec))
    return kept


def expected_duration(video, source_duration):
    """Output seconds: the source, less every authored excision."""
    return float(source_duration) - sum(
        cut["end_sec"] - cut["start_sec"] for cut in _sorted_cuts(video.get("cuts"))
    )


# --------------------------------------------------------------------------
# Fetching the source


def fetch_command(video, out):
    """The yt-dlp argv for one video's PINNED formats.

    Nothing here is "best": both format ids come from the manifest, so a
    rebuild months from now takes the same bitstreams. The audio format is
    never a ``-drc`` variant -- the loader and the schema both refuse one --
    so the sound arrives at its native rate with its dynamics intact.
    """
    source = video["source"]
    return [
        "yt-dlp",
        "--extractor-args", f"youtube:player_client={PLAYER_CLIENT}",
        "--no-playlist",
        "--no-part",
        "-f", f"{source['video_format_id']}+{source['audio_format_id']}",
        "--merge-output-format", "mkv",
        "-o", str(Path(out).resolve()),
        source["url"],
    ]


def _source_path(slug):
    return SOURCE_DIR / f"{slug}.mkv"


def _ensure_source(video, out=None):
    """The downloaded source for ``video``, fetched once and kept.

    The only step in this module that reaches the network. A non-empty file
    already on disk is the evidence it ran, so it is never re-fetched.
    """
    out = Path(out) if out is not None else _source_path(video["slug"])
    if out.exists() and out.stat().st_size > 0:
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(fetch_command(video, out), check=True)
    return out


# --------------------------------------------------------------------------
# Overlay seats


def _unresolved_path(slug):
    return WORK_DIR / f"{slug}-unresolved.json"


def read_unresolved(slug):
    """What the last build of ``slug`` could not place, as recorded."""
    path = _unresolved_path(slug)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("unresolved") or []


def _write_unresolved(slug, unresolved):
    """Record what could not be placed -- ALWAYS, empty list included.

    A sidecar that only appears when something broke is a sidecar nobody
    checks. Written beside the render so the punch list for a cut is one
    file away from the cut.
    """
    path = _unresolved_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"slug": slug, "unresolved": unresolved}, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def mapped_overlays(video, source_duration):
    """(accepted, unresolved) for one video's overlays.

    Every authored mark is SOURCE time, so it is mapped through the cuts
    before anything renders. A seat that cannot survive that mapping -- it
    sits inside a removed span, runs past the end of the source, collides
    with an accepted plate, or runs under the full-frame takeover that
    covers it -- is DROPPED and recorded. It is never slid to somewhere that
    fits: an authored placement is content, and moving it is the owner's
    call (AGENTS.md, "Degrade, never block").
    """
    cuts = video.get("cuts") or []
    takeover = video.get("takeover")
    covered_from = (source_to_output(takeover["source_at"], cuts)
                    if takeover else None)
    accepted, unresolved = [], []
    for overlay in video.get("overlays") or []:
        item = dict(overlay)
        source_at = item.pop("source_at")
        try:
            item["at"] = source_to_output(source_at, cuts)
            if source_at >= source_duration:
                raise ValueError(
                    f"source mark {source_at:.3f} exceeds {source_duration:.3f}"
                )
            # The takeover is an opaque full-frame picture composited last,
            # so a plate that runs into it is not on screen for the time the
            # record says. Accepting it would ship a seat nobody can see and
            # a review frame that shows the CTA instead of the plate.
            if covered_from is not None and \
                    item["at"] + float(item["dur"]) > covered_from + 1e-6:
                raise ValueError(
                    f"the seat ends at {item['at'] + float(item['dur']):.3f} "
                    f"which the full-frame takeover covers from "
                    f"{covered_from:.3f}")
            plate.load_manifest_entries([*accepted, item])
            # The standalone path never passes through `plan`, which is the
            # only other place "the vocab wins a conflict" is enforced --
            # which is how act VI shipped cards contradicting their bindings
            # (#111). Checked here, per overlay, so the batch's committed
            # seats are held to vocab/casting.yaml everywhere
            # mapped_overlays runs (build, verify, and the offline suite).
            # A contradiction is reported as unresolved -- dropped and
            # recorded, never shipped -- the same posture as every other
            # seat fault in this loop. Omitted copy fields are not
            # contradictions, so an intentional name-only card still passes.
            plate.check_copy_against_bindings([item])
        except ValueError as error:
            unresolved.append({"id": item["id"], "reason": str(error)})
            continue
        accepted.append(item)
    return accepted, unresolved


# --------------------------------------------------------------------------
# The one-pass filtergraph


def _t(value):
    """A filtergraph time: enough decimals to be exact, none to be noise."""
    text = f"{float(value):.3f}".rstrip("0")
    return f"{text}0" if text.endswith(".") else text


def video_out_label(video, overlays):
    """The label the picture leaves the graph on."""
    steps = len(overlays) + (1 if video.get("takeover") else 0)
    return "[outv]" if steps else "[basev]"


def filtergraph(video, duration_sec, overlays, gain=1.0):
    """One graph: the excisions, then every still, in one generation.

    The picture is decoded once, trimmed, normalised to the delivery raster
    and overlaid; the audio is trimmed on the same boundaries and never
    touched otherwise. ``gain`` is a static scale from the delivered-peak
    loop -- there is no loudnorm, compressor or limiter anywhere in here,
    because those rewrite dynamics a gain only scales.

    Input order is fixed by ``encode_video``: input 0 is the source, input 1
    is the CTA when the video has a takeover, and the rendered plates follow.
    Every still is a looped -- infinite -- input, so each overlay carries
    ``shortest=1`` and the finite source decides where the file ends.
    """
    cuts = video.get("cuts") or []
    chain = conform.video_filter_chain()
    volume = f",volume={gain:.6f}" if gain < 1.0 else ""
    parts = []

    if not cuts:
        parts.append(f"[0:v]{chain}[basev]")
        parts.append(f"[0:a]asetpts=PTS-STARTPTS{volume}[basea]")
    else:
        ranges = kept_ranges(duration_sec, cuts)
        if not ranges:
            raise ValueError("the cuts remove the whole source")
        single = len(ranges) == 1
        joins = []
        for index, (start, end) in enumerate(ranges):
            vlabel = "[basev]" if single else f"[v{index}]"
            alabel = "[basea]" if single else f"[a{index}]"
            parts.append(
                f"[0:v]trim=start={_t(start)}:end={_t(end)},{chain}{vlabel}")
            parts.append(
                f"[0:a]atrim=start={_t(start)}:end={_t(end)},"
                f"asetpts=PTS-STARTPTS{volume}{alabel}")
            joins += [vlabel, alabel]
        if not single:
            parts.append(f"{''.join(joins)}concat=n={len(ranges)}:v=1:a=1"
                         f"[basev][basea]")

    takeover = video.get("takeover")
    current = "[basev]"
    index = 1 + (1 if takeover else 0)
    for position, overlay in enumerate(overlays, start=1):
        start = float(overlay["at"])
        end = start + float(overlay["dur"])
        last = position == len(overlays) and not takeover
        label = "[outv]" if last else f"[ov{position}]"
        parts.append(
            f"{current}[{index}:v]overlay=0:0:"
            f"enable='between(t,{_t(start)},{_t(end)})':shortest=1{label}")
        current = label
        index += 1
    if takeover:
        at = source_to_output(takeover["source_at"], cuts)
        parts.append(f"{current}[1:v]overlay=0:0:"
                     f"enable='gte(t,{_t(at)})':shortest=1[outv]")
    return ";".join(parts)


# --------------------------------------------------------------------------
# Probing


def _ffprobe(ffmpeg):
    return conform.ffprobe_for(ffmpeg or render.find_ffmpeg())


def _source_duration(path, ffmpeg=None):
    out = subprocess.run(
        [*_ffprobe(ffmpeg), "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(Path(path).resolve())],
        capture_output=True, text=True, check=True)
    text = out.stdout.strip()
    if not text:
        raise ValueError(f"ffprobe reported no duration for {path}")
    return float(text)


def _probe_streams(path, ffmpeg=None):
    out = subprocess.run(
        [*_ffprobe(ffmpeg), "-v", "error", "-show_entries",
         "stream=index,codec_type,codec_name,sample_rate", "-of", "json",
         str(Path(path).resolve())],
        capture_output=True, text=True, check=True)
    return json.loads(out.stdout).get("streams") or []


def _pcm(path, at, dur, ffmpeg=None):
    """Mono 8 kHz signed 16-bit samples from ``path`` at ``at`` seconds."""
    out = subprocess.run(
        [*(ffmpeg or render.find_ffmpeg()), "-v", "error",
         "-ss", f"{float(at):.3f}", "-t", f"{float(dur):.3f}",
         "-i", str(Path(path).resolve()), "-vn", "-ac", "1",
         "-ar", str(PROBE_RATE),
         "-f", "s16le", "-"],
        capture_output=True, check=True)
    samples = array.array("h")
    samples.frombytes(out.stdout[: len(out.stdout) // 2 * 2])
    return samples


def _write_frame(path, at, out, ffmpeg=None):
    """One PNG frame of ``path`` at ``at`` seconds -- no JPEG generation."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [*(ffmpeg or render.find_ffmpeg()), "-v", "error", "-y",
         "-ss", f"{float(at):.3f}", "-i", str(Path(path).resolve()),
         "-frames:v", "1", str(out.resolve())], check=True)
    return out


# --------------------------------------------------------------------------
# Encoding


def _plate_inputs(overlays, plates_dir):
    """(placed overlays, their PNGs, plates nobody drew).

    ``plate.render_all`` skips the full-frame card kinds, so a manifest that
    names one would otherwise leave the graph reading an input that was never
    staged -- and every later overlay reading the wrong one. An undrawn plate
    is dropped here instead, which keeps the remaining input indexes correct.
    """
    placed, paths, missing = [], [], []
    for overlay in overlays:
        png = Path(plates_dir).resolve() / f"plate_{overlay['id']}.png"
        if not png.exists():
            missing.append({"id": overlay["id"],
                            "reason": f"no plate was rendered at {png}"})
            continue
        placed.append(overlay)
        paths.append(png)
    return placed, paths, missing


def _encode_command(ffmpeg, source, stills, graph, out_label, out):
    argv = [*ffmpeg, "-v", "error", "-y", "-i", str(source)]
    for still in stills:
        argv += ["-loop", "1", "-framerate", conform.DELIVERY.fps,
                 "-i", str(still)]
    argv += [
        "-filter_complex", graph,
        "-map", out_label,
        "-map", "[basea]",
        *conform.video_encode_args(),
        "-c:a", "aac",
        "-b:a", "320k",
        "-movflags", "+faststart",
        str(out),
    ]
    return argv


def encode_video(video, source, cta_asset, work_dir, local=False,
                 ffmpeg=None, log=print):
    """One farm-first encode of one standalone video, from its source.

    The picture takes exactly one H.264 generation and the sound exactly one
    AAC generation, both in this single pass: the trims, the plates and the
    CTA takeover are all filters in the same graph. The encode goes through
    ``farm.run_encode``, so it runs on the cluster whenever the cluster
    answers and falls back to a memory-capped local run that says why.

    The delivered-peak loop re-runs THIS command at a lower static gain --
    from the source, never from the file it just wrote, which would be a
    second generation of both streams.
    """
    ffmpeg = ffmpeg or render.find_ffmpeg()
    # Absolute, always: a containerized ffmpeg and a farm pod both read these
    # paths from a different working directory than this process has.
    source = Path(source).resolve()
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    duration = _source_duration(source, ffmpeg)
    overlays, unresolved = mapped_overlays(video, duration)

    plates_dir = work_dir / f"{video['slug']}-plates"
    if overlays:
        # Measured against the PICTURE, never the raw frame. Bungie's
        # cinematics arrive 2.39:1 inside a 16:9 file -- this batch's Final
        # Trial source carries 140 px of baked-in matte top and bottom -- so
        # a HUD on a 3rem inset and a nameplate on a 10% bottom margin both
        # land on the black bar instead of on the image.
        #
        # The STATUS is read, not just the rect: "there is no matte" and "I
        # never looked" are different answers (issue #161) and only the first
        # is safe to place against. A full-frame source gives ``None``, which
        # ``plate.place`` already reads as "the frame is the picture". An
        # UNDECODABLE one -- the ffmpeg-free default this host warns about,
        # an unreadable file -- gives ``None`` too, and placing against it
        # silently re-seats every plate on the matte, which is the exact bug
        # this call fixes. So the seats are dropped and recorded instead, and
        # the unplated video still ships (AGENTS.md, "Degrade, never block").
        picture, picture_status = render.detect_picture_status(
            source, ffmpeg=ffmpeg)
        if picture_status == "undecodable":
            unresolved += [
                {"id": item["id"],
                 "reason": "the source picture area could not be decoded, so "
                           "the seat could not be measured against the "
                           "picture and was not placed"}
                for item in overlays
            ]
            overlays = []
        else:
            plate.render_all(overlays, plates_dir, picture=picture)
    overlays, plate_paths, missing = _plate_inputs(overlays, plates_dir)
    unresolved += missing
    _write_unresolved(video["slug"], unresolved)
    for item in unresolved:
        log(f"  unresolved overlay {item['id']}: {item['reason']}")

    stills = ([Path(cta_asset).resolve()] if video.get("takeover") else []) \
        + [path.resolve() for path in plate_paths]
    out = Path(video["output"]).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out = out.resolve()
    out_label = video_out_label(video, overlays)
    wanted = expected_duration(video, duration)

    def run(gain):
        argv = _encode_command(
            ffmpeg, source, stills,
            filtergraph(video, duration, overlays, gain=gain),
            out_label, out)
        return farm.run_encode(
            argv,
            inputs=[source, *stills],
            out=out,
            local=local,
            expected_duration=wanted,
            label=f"Standalone {video['slug']}",
        )

    where = run(1.0)
    log(f"  encoded on {where}: {out}")
    peaks.correct_delivered_peak(
        out, 1.0, peaks.DEFAULT_TARGET_DBTP, run, ffmpeg=ffmpeg, log=log,
        margin_db=peaks.DELIVERED_BAND_MARGIN_DB)
    return out


def build(manifest_path, slug, local=False, ffmpeg=None, log=print):
    """Fetch what is missing, encode the cut, deliver the thumbnail."""
    manifest = load_manifest(manifest_path)
    video = entry_by_slug(manifest, slug)
    ffmpeg = ffmpeg or render.find_ffmpeg()
    source = _ensure_source(video)
    cta_asset = cta_asset_path(video, manifest)
    work_dir = WORK_DIR / slug
    out = encode_video(video, source, cta_asset, work_dir, local=local,
                       ffmpeg=ffmpeg, log=log)

    source_thumb = work_dir / f"{slug}-source-thumbnail.png"
    thumbnail.extract_source_frame(
        ffmpeg, source, video["thumbnail"]["source_at"], source_thumb)
    card = thumbnail.save_jungle_thumbnail(
        source_thumb, video["title"],
        Path(video["thumbnail_output"]).expanduser())
    log(f"  thumbnail: {card}")
    return out


# --------------------------------------------------------------------------
# Verification


def _percentile(values, pct):
    ordered = sorted(float(v) for v in values)
    if not ordered:
        raise ValueError("an empty window has no slew to measure")
    rank = (len(ordered) - 1) * pct / 100.0
    low = int(math.floor(rank))
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def splice_step_ratio(before, after):
    """The boundary step at a PCM join, as a ratio of nearby natural slew.

    ``before`` and ``after`` are same-rate sample sequences ending and
    starting at the join, at least two samples each. The step is
    ``|after[0] - before[-1]|``; the reference is the p99 of
    sample-to-sample ``|delta|`` across both windows. Above
    ``SPLICE_STEP_TARGET`` the join jumps further than 99% of the signal's
    own moves -- the audible click the Saint-14 splice review measured at
    all six first-pass publisher-card excisions (ratios 2.4-8.4 against a
    1.8 blocker). The fix is boundary selection inside the same frame
    window, never a fade: this helper is how a boundary proves itself.
    """
    before, after = list(before), list(after)
    if len(before) < 2 or len(after) < 2:
        raise ValueError("a splice needs at least two samples on each side")
    step = abs(float(after[0]) - float(before[-1]))
    slew = [abs(float(b) - float(a)) for a, b in zip(before, before[1:])]
    slew += [abs(float(b) - float(a)) for a, b in zip(after, after[1:])]
    reference = _percentile(slew, 99)
    if reference <= 0:
        # Digital silence slews nowhere; only a silent join is clean there.
        return 0.0 if step == 0 else math.inf
    return step / reference


# The frame grid a cut boundary quantizes against: the 30000/1001 source
# raster (the delivery fps=60000/1001 doubling happens after the trims, so
# segment lengths quantize on the source grid).
FRAME_DURATION = 1001 / 30000


def silence_pad(start, prev_end, frame_duration=FRAME_DURATION):
    """Seconds of silence concat inserts at the join before a cut's start.

    Each kept segment's video runs a whole number of frames; its audio is
    sample-exact. When the video side is the longer of the two, the concat
    filter pads the audio tail with silence before the next segment, so the
    shipped join is content -> silence -> content and the authored sample
    pair never meets -- a click no boundary selection can prevent, measured
    on the first reseated Saint-14 render (pads of 0.4-5.9 ms at four of six
    joins, step/p99 slew up to 3.5 delivered). The pad is

        (first frame pts >= start) - start
            + (prev_end - first frame pts >= prev_end)

    where ``prev_end`` is the kept segment's own start (the previous cut's
    end, or 0.0 for the opening segment). At or below zero the audio covers
    the video and the authored pair ships sample-exact. The fix is still
    boundary selection: seat the cut so the pad is non-positive, or so both
    edges of the residual gap sit on quiet samples.
    """
    def first_frame_pts(t):
        return math.ceil(t / frame_duration - 1e-9) * frame_duration

    return (first_frame_pts(start) - start) + \
        (prev_end - first_frame_pts(prev_end))


def correlation(left, right):
    """Normalized cross-correlation of two same-rate probe windows."""
    count = min(len(left), len(right))
    if not count:
        raise ValueError("an empty probe window has no energy to compare")
    left, right = list(left[:count]), list(right[:count])
    lm = sum(left) / count
    rm = sum(right) / count
    numerator = sum((a - lm) * (b - rm) for a, b in zip(left, right))
    left_energy = sum((a - lm) ** 2 for a in left)
    right_energy = sum((b - rm) ** 2 for b in right)
    if left_energy <= 0 or right_energy <= 0:
        # Silence correlates with everything and nothing. A zero-energy
        # window must never read as a pass.
        raise ValueError("a probe window has no energy -- it is silent, so "
                         "no correlation can vouch for it")
    return numerator / math.sqrt(left_energy * right_energy)


def aligned_correlation(reference, window):
    """The best correlation of ``reference`` against any seat in ``window``.

    ``window`` is the delivered probe extracted with ``ALIGNMENT_PAD_S`` of
    padding on both sides, so the search recovers the codec/container delay
    instead of failing on it.

    Every lag is scored. The coarse-then-fine shortcut this replaced was NOT
    the same answer as the exhaustive scan: bright, periodic content puts a
    strong autocorrelation peak one signal period from the true seat, and
    the +/-7-sample fine scan could not walk back to a peak sitting further
    from the best coarse point -- the Saint-14 mix at source 113.0 measured
    0.72 at the wrong seat against 0.9999 at the right one, a false "below
    floor" finding on a correct file. The exhaustive scan is ~2 s of
    arithmetic per probe, cheap beside the ffmpeg calls around it.

    Returns ``(correlation, lag_seconds)``; the lag is signed, negative when
    the delivered audio arrives early.
    """
    reference = list(reference)
    window = list(window)
    span = len(window) - len(reference)
    if span < 0:
        raise ValueError("the delivered probe window is shorter than the "
                         "source window it is compared against")
    centre = span // 2

    def at(lag):
        return correlation(reference, window[lag:lag + len(reference)])

    best = max(range(span + 1), key=at)
    return at(best), (best - centre) / float(PROBE_RATE)


def frame_difference(frame_path, reference_path):
    """Mean absolute per-channel error, 0-255, between two pictures."""
    from PIL import Image

    frame = Image.open(frame_path).convert("RGB")
    reference = Image.open(reference_path).convert("RGB")
    if reference.size != frame.size:
        reference = reference.resize(frame.size, Image.Resampling.LANCZOS)
    total = 0
    for a, b in zip(frame.getdata(), reference.getdata()):
        total += abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])
    return total / (frame.size[0] * frame.size[1] * 3)


def verify(manifest_path, slug, ffmpeg=None, log=print):
    """Check a delivered standalone video against its record.

    A REPORT, never a gate: every finding is a string in the returned list
    and the checks that follow it still run, so one bad probe cannot hide the
    next one. Nothing here withholds a film.
    """
    manifest = load_manifest(manifest_path)
    video = entry_by_slug(manifest, slug)
    ffmpeg = ffmpeg or render.find_ffmpeg()
    cuts = video.get("cuts") or []
    out = Path(video["output"]).expanduser()
    problems = []
    if not out.exists():
        return [f"{out} does not exist -- nothing to verify"]
    source = _source_path(slug)

    # 1. Duration: the source less every authored excision.
    if source.exists():
        source_duration = _source_duration(source, ffmpeg)
        wanted = expected_duration(video, source_duration)
        actual = _source_duration(out, ffmpeg)
        if abs(actual - wanted) > DURATION_TOLERANCE_S:
            problems.append(
                f"duration {actual:.3f}s is not the expected {wanted:.3f}s "
                f"(tolerance {DURATION_TOLERANCE_S}s)")
    else:
        source_duration = None
        problems.append(f"source {source} is absent -- duration and audio "
                        f"correlation cannot be checked")

    # 2. Stream shape.
    streams = _probe_streams(out, ffmpeg)
    picture = [s for s in streams if s.get("codec_type") == "video"]
    sound = [s for s in streams if s.get("codec_type") == "audio"]
    if not picture or picture[0].get("codec_name") != "h264":
        problems.append(f"video stream is {picture and picture[0].get('codec_name')}, "
                        f"not h264")
    if not sound:
        problems.append("no audio stream in the delivered file")

    # 3. The delivered audio IS the source audio at every probe.
    if source_duration is not None:
        for probe in video["audio_probes"]:
            mark = probe["source_at"]
            try:
                at = source_to_output(mark, cuts)
            except ValueError as error:
                problems.append(f"audio probe {mark}: {error}")
                continue
            pad = min(ALIGNMENT_PAD_S, at)
            try:
                score, lag = aligned_correlation(
                    _pcm(source, mark, probe["duration"], ffmpeg),
                    _pcm(out, at - pad, probe["duration"] + pad
                         + ALIGNMENT_PAD_S, ffmpeg))
            except ValueError as error:
                problems.append(f"audio probe {mark}: {error}")
                continue
            if score < AUDIO_CORRELATION_FLOOR:
                problems.append(
                    f"audio probe {mark} correlation {score:.4f} is below "
                    f"{AUDIO_CORRELATION_FLOOR}")
            else:
                log(f"  audio probe {mark} -> {at:.3f}s correlates "
                    f"{score:.4f} at {lag * 1000:+.1f} ms")

    # 4/5. Review frames: every overlay midpoint, and the takeover.
    review = REVIEW_DIR / slug
    overlays, unresolved = mapped_overlays(
        video, source_duration if source_duration is not None else math.inf)
    # The build drops a plate nobody drew -- a full-frame card kind, or a
    # renderer that skipped it -- and only the sidecar knows. Re-deriving the
    # seats here would rediscover the mapping failures and MISS that class,
    # so the record is read rather than recomputed. A review frame is never
    # written for a dropped plate: a picture named for a plate that is not in
    # it is exactly the false claim these frames exist to catch.
    dropped = {item["id"]: item["reason"] for item in unresolved}
    for item in read_unresolved(slug):
        dropped.setdefault(item["id"], item["reason"])
    for overlay_id, reason in dropped.items():
        problems.append(f"overlay {overlay_id} is unplaced: {reason}")
    for overlay in overlays:
        if overlay["id"] in dropped:
            continue
        midpoint = float(overlay["at"]) + float(overlay["dur"]) / 2.0
        _write_frame(out, midpoint, review / f"{overlay['id']}.png", ffmpeg)
    takeover = video.get("takeover")
    if takeover:
        try:
            at = source_to_output(takeover["source_at"], cuts) + 0.5
        except ValueError as error:
            problems.append(f"takeover: {error}")
        else:
            frame = _write_frame(out, at, review / "takeover.png", ffmpeg)
            asset = cta_asset_path(video, manifest)
            difference = frame_difference(frame, asset)
            if difference > CTA_FRAME_TOLERANCE:
                problems.append(
                    f"the frame at {at:.3f}s differs from {asset.name} by "
                    f"{difference:.2f} (tolerance {CTA_FRAME_TOLERANCE})")

    # 6. The thumbnail.
    card = Path(video["thumbnail_output"]).expanduser()
    if not card.exists():
        problems.append(f"thumbnail {card} does not exist")
    else:
        from PIL import Image

        size = Image.open(card).size
        if size != thumbnail.SIZE:
            problems.append(f"thumbnail is {size[0]}x{size[1]}, not "
                            f"{thumbnail.SIZE[0]}x{thumbnail.SIZE[1]}")
        if card.stat().st_size > thumbnail.BYTE_CAP:
            problems.append(f"thumbnail is {card.stat().st_size} bytes, over "
                            f"the {thumbnail.BYTE_CAP}-byte cap")

    for problem in problems:
        log(f"  {problem}")
    return problems


# --------------------------------------------------------------------------
# CLI


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("fetch", "build", "verify"):
        one = sub.add_parser(name)
        one.add_argument("manifest")
        one.add_argument("slug")
        if name == "build":
            one.add_argument(
                "--local", action="store_true",
                help="encode on this workstation instead of the farm; the "
                     "run is memory-capped and states its reason")
    args = parser.parse_args(argv)

    if args.command == "fetch":
        manifest = load_manifest(args.manifest)
        print(_ensure_source(entry_by_slug(manifest, args.slug)))
        return 0
    if args.command == "build":
        print(build(args.manifest, args.slug, local=args.local))
        return 0
    problems = verify(args.manifest, args.slug)
    if problems:
        print(f"{len(problems)} finding(s) for {args.slug}", file=sys.stderr)
        return 1
    print(f"{args.slug} verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
