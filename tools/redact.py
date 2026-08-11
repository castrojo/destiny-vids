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
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

REDACTIONS_DIR = REPO_ROOT / "redactions"

FRAME_W, FRAME_H = 1920, 1080


def load_redactions(video_id, root=REDACTIONS_DIR):
    path = Path(root) / f"{video_id}.json"
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def drawbox_filters(redactions):
    """Redaction records -> ffmpeg ``drawbox`` filters, one per box.

    ``enable`` is FFmpeg's timeline-editing option: the expression is evaluated
    per frame and the filter passes the frame through untouched when it is
    false, so one pass covers every window.
    """
    filters = []
    for item in redactions:
        start, end = float(item["start_sec"]), float(item["end_sec"])
        if end <= start:
            raise ValueError(f"redaction {item['id']!r} ends before it starts")
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


def build_command(ffmpeg, video, filters, out_path, audio=None, audio_gain=None):
    """One pass: paint out the boxes, and swap or keep the audio.

    The music bed replaces the source audio rather than mixing with it, so a
    cut that is scored is scored on purpose. ``-shortest`` keeps a long track
    from extending the picture.
    """
    cmd = [*ffmpeg, "-nostdin", "-y", "-i", str(video)]
    if audio:
        cmd += ["-i", str(audio)]

    cmd += ["-vf", ",".join(filters)] if filters else []
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p"]

    if audio:
        if audio_gain is not None:
            cmd += ["-af", f"volume={audio_gain}"]
        cmd += ["-map", "0:v:0", "-map", "1:a:0", "-shortest",
                "-c:a", "aac", "-b:a", "192k"]
    else:
        cmd += ["-map", "0:v:0", "-map", "0:a?", "-c:a", "copy"]
    cmd += [str(out_path)]
    return cmd


def apply(video, redactions, out_path, audio=None, audio_gain=None, ffmpeg=None):
    if ffmpeg is None:
        from tools.render import find_ffmpeg

        ffmpeg = find_ffmpeg()
    cmd = build_command(ffmpeg, Path(video).resolve(), drawbox_filters(redactions),
                        Path(out_path).resolve(),
                        Path(audio).resolve() if audio else None, audio_gain)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
        raise RuntimeError(f"redaction pass failed:\n{tail}")
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
                    help="linear gain on the music bed, e.g. 0.8")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    data = load_redactions(args.video_id)
    for item in data["redactions"]:
        print(f"  {item['id']:<18} {item['start_sec']:7.2f}-{item['end_sec']:7.2f}s  "
              f"{item['reason']}")
    apply(args.video, data["redactions"], args.out,
          audio=args.audio, audio_gain=args.audio_gain)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
