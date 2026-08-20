#!/usr/bin/env python3
"""Black out burned-in publisher copy, and lay a music bed under an uncut video.

An uncut source is the honest way to show a cinematic, but Bungie's upload is
not only the cinematic: it opens on a ratings card and closes on a logo lockup
with legal copy. Those are the frames the cleanliness axis calls ``burned_text``
-- the difference is that here they are not a reason to drop the shot, because
nothing is being re-cut. They are painted out instead.

What this does NOT do is invent picture: a redaction only ever *removes*, and
the boxes are authored in ``redactions/<video_id>.json`` against source pixels
so they can be reviewed without running a render.

A record carries an ``action``: ``box`` (the default) paints its window out;
``cut`` removes the window from the video entirely. A redaction whose content
is the whole frame -- the ratings card at the head, the logo card at the tail
-- should be cut, not boxed: a full-frame black rectangle reads as a defect,
not a fade, where the video should simply start and end on picture. ``cut``
windows trim the encode to ``kept_range``, and tools/uncut.py clamps its cut
list to the same range, so the two never disagree about where the picture is.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# The headroom constants and the measure/correct machinery live in
# tools/peaks.py, shared with tools/render.py; they are re-exported here so
# long-standing references to redact.gain_for_headroom keep resolving.
from tools.peaks import (DEFAULT_TARGET_DBTP, PEAK_ACCEPT_MARGIN_DB,  # noqa: E402, F401
                         QUIET_WARN_DB, correct_delivered_peak,
                         gain_for_headroom, measure_true_peak)
from tools.search import load_segments  # noqa: E402

REDACTIONS_DIR = REPO_ROOT / "redactions"

FRAME_W, FRAME_H = 1920, 1080


def load_redactions(video_id, root=REDACTIONS_DIR):
    path = Path(root) / f"{video_id}.json"
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def action_of(item):
    """A record's fate: ``box`` paints the window out, ``cut`` removes it.

    Records that predate the field default to ``box``: a window whose content
    is less than the whole frame has nothing to cut *to*.
    """
    action = item.get("action", "box")
    if action not in ("box", "cut"):
        raise ValueError(
            f"redaction {item.get('id')!r} has unknown action {action!r}")
    return action


def _window(item):
    start, end = float(item["start_sec"]), float(item["end_sec"])
    if end <= start:
        raise ValueError(f"redaction {item['id']!r} ends before it starts")
    return start, end


#: Slop on "touches the head/tail", in seconds (~1.5 frames at 29.97): a cut
#: window authored a frame short of the end still reaches it. Anything more
#: and the window leaves a hole, which is an error, not a trim.
EDGE_SLOP = 0.05


def kept_range(redactions, video_end):
    """The [start, end) of picture surviving the ``cut`` windows, source seconds.

    ``video_end`` is the source's duration -- the index's last segment end for
    the video. It is required because without it a cut window near the tail
    cannot be told apart from one in the middle of the picture. With no cut
    windows the range is the whole video: ``(0.0, video_end)``.

    tools/uncut.py clamps its cut list to this range and the encode below is
    trimmed to it; both must agree exactly, or every plate timed against the
    cut list lands at the wrong moment on the redacted file.

    A cut window has to touch the head or the tail: removing the middle of an
    uncut video would split it in two, which one trimmed encode cannot express,
    so a middle window is rejected loudly rather than handled differently by
    the two consumers.
    """
    merged = []
    for start, end in sorted(_window(i) for i in redactions
                             if action_of(i) == "cut"):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    start, end = 0.0, float(video_end)
    if merged and merged[0][0] <= EDGE_SLOP:
        start = merged.pop(0)[1]
    if merged and merged[-1][1] >= end - EDGE_SLOP:
        end = merged.pop(-1)[0]
    if merged:
        raise ValueError(
            "a `cut` redaction must start at 0 or reach the end of the video "
            f"({float(video_end):.2f}s); window "
            f"{merged[0][0]:.2f}-{merged[0][1]:.2f}s would leave a hole that "
            "one trimmed encode cannot express")
    if end <= start:
        raise ValueError("the `cut` redactions cover the whole video")
    return start, end


def video_extent(video_id, segments_dir=None):
    """The indexed end of ``video_id`` in source seconds.

    The index covers its videos end to end (tools/uncut.py reports any gap),
    so the last segment's end IS the video's end.
    """
    segments_dir = str(segments_dir or (REPO_ROOT / "segments"))
    ends = [float(s["end_sec"]) for s in load_segments(segments_dir)
            if s.get("video_id") == video_id]
    if not ends:
        raise SystemExit(
            f"`cut` redactions need the indexed extent of {video_id!r}, "
            f"but no segments for it exist in {segments_dir}")
    return max(ends)


def drawbox_filters(redactions):
    """Redaction records -> ffmpeg ``drawbox`` filters, one per box.

    Only ``box`` records paint: a ``cut`` record's window is removed from the
    video by the trim, so drawing a box over it would paint frames that no
    longer exist.

    ``enable`` is FFmpeg's timeline-editing option: the expression is evaluated
    per frame and the filter passes the frame through untouched when it is
    false, so one pass covers every window.
    """
    filters = []
    for item in redactions:
        if action_of(item) != "box":
            continue
        start, end = _window(item)
        boxes = item["boxes"]
        if boxes == "full":
            boxes = [{"x": 0, "y": 0, "w": FRAME_W, "h": FRAME_H}]
        for box in boxes:
            filters.append(
                f"drawbox=x={box['x']}:y={box['y']}:w={box['w']}:h={box['h']}"
                f":color=black@1.0:t=fill"
                f":enable='between(t,{start:.3f},{end:.3f})'"
            )
    return filters


def audio_encode_opts(codec):
    """Encoder options for the deliverable's audio.

    ``flac`` builds a lossless master, so that a re-encode later (a fold-down
    for streaming, a different container) starts from the bed rather than from
    a lossy deliverable. A bitrate is meaningless for a lossless codec, so it
    is omitted rather than passed and ignored.
    """
    if codec == "aac":
        return ["-c:a", "aac", "-b:a", "192k"]
    return ["-c:a", codec]


def build_command(ffmpeg, video, filters, out_path, audio=None, audio_gain=None,
                  trim=None, audio_codec="aac", audio_at=None):
    """One pass: paint out the boxes, trim to the kept range, swap or keep audio.

    The music bed replaces the source audio rather than mixing with it, so a
    cut that is scored is scored on purpose. ``-shortest`` keeps a long track
    from extending the picture.

    ``trim`` is the kept ``(start, end)`` from ``kept_range``, applied as a
    filter at the END of the chain so the box windows keep their source-second
    meaning (a None end trims to the end of the source). A filter, not ``-ss`` on the
    input: input seeking would rebase only the video, and an output-side
    ``-ss`` would skip the music bed's head -- either way the bed no longer
    starts at the start of the trimmed picture. The bed itself is never
    trimmed: it plays from its own beginning and ``-shortest`` stops it where
    the trimmed picture ends. Without a bed, a trimmed source track can no
    longer be stream-copied, so it is ``atrim``med and re-encoded instead.
    """
    cmd = [*ffmpeg, "-nostdin", "-y", "-i", str(video)]
    if audio:
        cmd += ["-i", str(audio)]

    vfilters = list(filters)
    if trim:
        spec = f"trim=start={trim[0]:.3f}"
        if trim[1] is not None:
            spec += f":end={trim[1]:.3f}"
        vfilters += [spec, "setpts=PTS-STARTPTS"]
    cmd += ["-vf", ",".join(vfilters)] if vfilters else []
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p"]

    if audio and audio_at is not None:
        if audio_at < 0:
            raise ValueError("audio_at must be non-negative")
        source_start = trim[0] if trim else 0.0
        gain = f",volume={audio_gain}" if audio_gain is not None else ""
        graph = (
            f"[0:a]atrim=start={source_start:.3f}:duration={audio_at:.3f},"
            "asetpts=PTS-STARTPTS[pre];"
            f"[1:a]asetpts=PTS-STARTPTS{gain}[music];"
            "[pre][music]concat=n=2:v=0:a=1[aout]"
        )
        cmd += ["-filter_complex", graph, "-map", "0:v:0", "-map", "[aout]",
                "-shortest", *audio_encode_opts(audio_codec)]
    elif audio:
        if audio_gain is not None:
            cmd += ["-af", f"volume={audio_gain}"]
        cmd += ["-map", "0:v:0", "-map", "1:a:0", "-shortest",
                *audio_encode_opts(audio_codec)]
    elif trim:
        spec = f"atrim=start={trim[0]:.3f}"
        if trim[1] is not None:
            spec += f":end={trim[1]:.3f}"
        cmd += ["-af", spec + ",asetpts=PTS-STARTPTS",
                "-map", "0:v:0", "-map", "0:a?", *audio_encode_opts(audio_codec)]
    else:
        cmd += ["-map", "0:v:0", "-map", "0:a?", "-c:a", "copy"]
    cmd += [str(out_path)]
    return cmd


def apply(video, redactions, out_path, audio=None, audio_gain=None, ffmpeg=None,
          video_end=None, target_dbtp=None, audio_codec="aac",
          audio_at=None, _attempts_left=5):
    if ffmpeg is None:
        from tools.render import find_ffmpeg

        ffmpeg = find_ffmpeg()
    trim = None
    if any(action_of(i) == "cut" for i in redactions):
        if video_end is None:
            raise ValueError("`cut` redactions need video_end -- the source's "
                             "duration -- to tell a tail cut from a hole")
        start, end = kept_range(redactions, video_end)
        if start > 0 or end < float(video_end):
            trim = (start, end)
    cmd = build_command(ffmpeg, Path(video).resolve(), drawbox_filters(redactions),
                        Path(out_path).resolve(),
                        Path(audio).resolve() if audio else None, audio_gain,
                        trim=trim, audio_codec=audio_codec, audio_at=audio_at)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
        raise RuntimeError(f"redaction pass failed:\n{tail}")

    # Verify the DELIVERED peak, not just the bed's -- the measure-and-correct
    # loop is shared with render.py and lives in tools/peaks.py. A hand-set
    # --audio-gain opts out (main passes target_dbtp=None then).
    if audio and audio_gain and target_dbtp is not None:
        def rerun(new_gain):
            cmd = build_command(ffmpeg, Path(video).resolve(),
                                drawbox_filters(redactions),
                                Path(out_path).resolve(),
                                Path(audio).resolve(), new_gain, trim=trim,
                                audio_codec=audio_codec, audio_at=audio_at)
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
                raise RuntimeError(f"redaction pass failed:\n{tail}")

        correct_delivered_peak(out_path, audio_gain, target_dbtp, rerun,
                               ffmpeg=ffmpeg, attempts=_attempts_left)
    return out_path


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Black out burned-in copy and optionally score an uncut video.")
    ap.add_argument("--video", required=True)
    ap.add_argument("--video-id", required=True,
                    help="which redactions/<video_id>.json to apply")
    ap.add_argument("--audio", default=None,
                    help="replace the source audio with this music bed")
    ap.add_argument("--audio-gain", type=float, default=None,
                    help="linear gain on the music bed, e.g. 0.8. Omit to derive "
                         "it from the bed's measured true peak (--target-dbtp)")
    ap.add_argument("--target-dbtp", type=float, default=DEFAULT_TARGET_DBTP,
                    help="deliverable headroom in dBTP when --audio-gain is not "
                         f"given (default {DEFAULT_TARGET_DBTP})")
    ap.add_argument("--audio-codec", default="aac",
                    help="deliverable audio codec; 'flac' builds a lossless "
                         "master (default aac)")
    ap.add_argument("--audio-at", type=float, default=None,
                    help="keep source audio until this output second, then "
                         "start the replacement bed")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    data = load_redactions(args.video_id)
    for item in data["redactions"]:
        print(f"  {item['id']:<18} {item['start_sec']:7.2f}-{item['end_sec']:7.2f}s  "
              f"{action_of(item):<4}  {item['reason']}")
    video_end = None
    if any(action_of(i) == "cut" for i in data["redactions"]):
        video_end = video_extent(args.video_id)
        start, end = kept_range(data["redactions"], video_end)
        print(f"kept range: {start:.2f}s -> {end:.2f}s")
    gain = args.audio_gain
    if args.audio and gain is None:
        gain, peak = gain_for_headroom(args.audio, args.target_dbtp)
        print(f"music bed: true peak {peak:+.1f} dBTP -> gain {gain:.3f} "
              f"(target {args.target_dbtp:+.1f} dBTP)")
    apply(args.video, data["redactions"], args.out,
          audio=args.audio, audio_gain=gain, video_end=video_end,
          audio_codec=args.audio_codec,
          audio_at=args.audio_at,
          target_dbtp=args.target_dbtp if args.audio_gain is None else None)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
