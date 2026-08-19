#!/usr/bin/env python3
"""Build the movement-2 countdown derivative without changing its clean source.

The default encoder is the farm when it is reachable. If it is not, pass
``--local`` explicitly; ``--print-command`` exposes the complete local argv
without encoding.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from fractions import Fraction
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import conform, farm, megacut, plate, render  # noqa: E402

THREAD = REPO_ROOT / "stories" / "00-perfume-thread.json"
PLAN = REPO_ROOT / "stories" / "megacut" / "megacut.json"
MOVEMENT_ID = "perfume-2"
TARGET = 264.0
FPS = Fraction(60000, 1001)
PICTURE = (0, (conform.DELIVERY.height - 804) // 2,
           conform.DELIVERY.width, 804)



def _frame_number(seconds):
    """Convert a positive programme time to its nearest delivery frame."""
    value = Fraction(str(seconds)) * FPS
    return (value.numerator * 2 + value.denominator) // (2 * value.denominator)



def _ceil_fraction(value):
    return -(-value.numerator // value.denominator)



def _label(remaining_frames):
    if remaining_frames <= 0:
        return 0
    return _ceil_fraction(Fraction(remaining_frames, 1) / FPS)



def _clock_text(seconds):
    return f"{seconds // 60:02d}:{seconds % 60:02d}"



def countdown_entries(segment_programme_start, segment_duration, target=264.0):
    """Return whole-second countdown plates, derived from delivery frames."""
    start_frame = _frame_number(segment_programme_start)
    end_frame = _frame_number(Fraction(str(segment_programme_start))
                               + Fraction(str(segment_duration)))
    target_frame = _frame_number(target)
    if target_frame < start_frame or target_frame >= end_frame:
        raise ValueError("countdown target must fall inside the segment")

    entries = []
    current_label = None
    current_frame = start_frame
    for frame in range(start_frame, end_frame):
        value = _label(target_frame - frame)
        if value == current_label:
            continue
        if current_label is not None:
            entries[-1]["dur"] = float(Fraction(frame - current_frame, 1) / FPS)
        programme_at = (float(target) if frame == target_frame
                        else float(Fraction(frame, 1) / FPS))
        entries.append({
            "id": f"countdown-{len(entries):02d}",
            "kind": "countdown",
            "at": float(Fraction(frame - start_frame, 1) / FPS),
            "dur": 0.0,
            "position": "countdown-bottom",
            "text": _clock_text(value),
            "programme_at": programme_at,
            "programme_frame": frame,
        })
        current_label = value
        current_frame = frame
    entries[-1]["dur"] = float(Fraction(end_frame - current_frame, 1) / FPS)
    return entries



def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))



def _movement_start(plan, path):
    start = Fraction(0)
    for item in plan["items"]:
        if item.get("path") == path:
            return float(start)
        start += Fraction(str(megacut.item_duration(item)))
    raise ValueError(f"movement {path!r} is not seated in the programme")



def plan_countdown(target=TARGET):
    thread = _load(THREAD)
    programme = _load(PLAN)
    movement = next(m for m in thread["movements"] if m["id"] == MOVEMENT_ID)
    derivative = thread["_derivatives"]["perfume-2-countdown"]
    # The named derivative is the programme contract. Do not infer the seat by
    # scanning sources: another derivative may intentionally share this source.
    start = _movement_start(programme, derivative["out_file"])
    entries = countdown_entries(start, movement["duration"], target=target)
    return {
        "movement": MOVEMENT_ID,
        "source": derivative["source"],
        "out_file": derivative["out_file"],
        "programme_start": start,
        "programme_target": target,
        "segment_duration": movement["duration"],
        "entries": entries,
    }



def _remote_argv(argv, local_ffmpeg):
    """Replace a local resolver prefix with the farm's native executable."""
    if argv and argv[0] == "ffmpeg":
        return argv
    prefix = list(local_ffmpeg)
    if argv[:len(prefix)] != prefix:
        raise ValueError("burn argv does not start with its local ffmpeg resolver")
    return ["ffmpeg", *argv[len(prefix):]]


def _farm_runner(source, entries, plates_dir, out, expected_duration, local_ffmpeg):
    def run(argv):
        farm.run_ffmpeg_on_cluster(
            _remote_argv(argv, local_ffmpeg),
            inputs=[source] + [
                plates_dir / f"plate_{unit['id']}.png"
                for unit in plate._burn_units(entries)
                if not unit["animation"]
            ] + [
                plates_dir / unit["pattern"]
                for unit in plate._burn_units(entries)
                if unit["animation"]
            ],
            out=out,
            expected_duration=expected_duration,
        )

    return run


def _use_farm(local):
    if local:
        print("encoder: local (--local explicitly authorizes the workstation fallback)")
        return False
    available, reason = farm.cluster_available()
    if not available:
        raise SystemExit(
            f"farm unavailable: {reason}; rerun with --local to authorize "
            "local encoding")
    print("encoder: farm (cluster reachable)")
    return True


def build(local=False):
    spec = plan_countdown()
    source = REPO_ROOT / spec["source"]
    out = REPO_ROOT / spec["out_file"]
    if not source.exists():
        raise SystemExit(f"clean movement is missing: {source}")
    plates_dir = REPO_ROOT / "renders" / "perfume-2" / "countdown"
    plate.render_all(spec["entries"], plates_dir, picture=PICTURE)
    ffmpeg = render.find_ffmpeg()
    use_farm = _use_farm(local)
    runner = (_farm_runner(source, spec["entries"], plates_dir, out,
                           spec["segment_duration"], ffmpeg)
              if use_farm else None)
    plate.burn(source, spec["entries"], plates_dir, out, ffmpeg=ffmpeg,
               runner=runner, encode_args=conform.video_encode_args())
    return spec


def _print_ffmpeg():
    try:
        return render.find_ffmpeg(prefer_container=False)
    except RuntimeError:
        return ["ffmpeg"]


def print_command(spec):
    argv = plate.burn_command(
        REPO_ROOT / spec["source"], spec["entries"],
        REPO_ROOT / "renders" / "perfume-2" / "countdown",
        REPO_ROOT / spec["out_file"], spec["segment_duration"],
        ffmpeg=_print_ffmpeg(), encode_args=conform.video_encode_args())
    print(shlex.join(argv))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-plan", action="store_true")
    parser.add_argument("--print-command", action="store_true",
                        help="print the complete ffmpeg argv and exit")
    parser.add_argument("--local", action="store_true",
                        help="explicitly authorize workstation encoding")
    args = parser.parse_args(argv)
    spec = plan_countdown()
    if args.print_plan:
        print(json.dumps(spec, indent=2))
        return 0
    if args.print_command:
        print_command(spec)
        return 0
    build(local=args.local)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
