"""Burned-pixel regression for the Act II LFX choice cursor.

Runs against the real ffmpeg resolved by ``tools.render.find_ffmpeg`` with
container preference disabled. Skipped when that ffmpeg cannot encode and
decode H.264.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from PIL import Image, ImageChops

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_efmb_plates  # noqa: E402
from tools import plate, render  # noqa: E402


RATE = "60000/1001"
FRAME_W, FRAME_H = 1920, 1080


def _require_h264_ffmpeg():
    """Resolve a local ffmpeg and prove it can encode and decode H.264."""
    try:
        ffmpeg = render.find_ffmpeg(prefer_container=False)
    except RuntimeError as exc:
        pytest.skip(f"no ffmpeg available: {exc}")
    argv = list(ffmpeg)

    # Exercise encoder and decoder with a tiny H.264 round-trip.
    tmp = Path(tempfile.mkdtemp(dir="/tmp", prefix="choice_probe_"))
    try:
        probe = tmp / "probe.mp4"
        enc = subprocess.run(
            argv + ["-v", "error", "-y",
                    "-f", "lavfi", "-i", "color=black:s=32x32:d=0.1",
                    "-c:v", "libx264", str(probe)],
            capture_output=True,
        )
        if enc.returncode != 0:
            pytest.skip("resolved ffmpeg cannot encode H.264")
        dec = subprocess.run(
            argv + ["-nostdin", "-v", "error", "-y", "-i", str(probe),
                    "-f", "null", "-"],
            capture_output=True,
        )
        if dec.returncode != 0:
            pytest.skip("resolved ffmpeg cannot decode H.264")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return ffmpeg


def _decode_all_frames(ffmpeg, video, out_dir, prefix="frame"):
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        list(ffmpeg)
        + ["-nostdin", "-y", "-i", str(video),
           "-start_number", "0",
           str(out_dir / f"{prefix}_%03d.png")],
        check=True, capture_output=True,
    )
    return sorted(out_dir.glob(f"{prefix}_*.png"))


def _allowed_cursor_bbox():
    """Bounding rectangle covering the start and end cursor footprints."""
    spec = {"label": "Your choices are:",
            "options": build_efmb_plates.CHOICE_OPTIONS}
    layout = plate._choice_layout(spec)
    start = plate._choice_cursor_position({**spec, "pointer": 0.0}, layout)
    end = plate._choice_cursor_position(
        {**spec, "pointer": plate.CHOICE_POINTER_CUT}, layout)
    cursor = plate._cursor()
    left = min(start[0], end[0])
    top = min(start[1], end[1])
    right = max(start[0] + cursor.width, end[0] + cursor.width)
    bottom = max(start[1] + cursor.height, end[1] + cursor.height)
    return (max(0, left), max(0, top),
            min(FRAME_W, right), min(FRAME_H, bottom))


def test_choice_base_stays_put_while_cursor_moves():
    ffmpeg = _require_h264_ffmpeg()

    # The resolved ffmpeg may be containerized and unable to see the default
    # pytest temp tree, so run the burn under /tmp.
    work_dir = Path(tempfile.mkdtemp(dir="/tmp", prefix="choice_burn_"))
    try:
        src = work_dir / "black.mp4"
        subprocess.run(
            list(ffmpeg) + ["-v", "error", "-y",
                            "-f", "lavfi",
                            "-i", f"color=black:s={FRAME_W}x{FRAME_H}:r={RATE}",
                            "-t", "1", "-c:v", "libx264rgb", "-crf", "0",
                            str(src)],
            check=True, capture_output=True,
        )

        options = build_efmb_plates.CHOICE_OPTIONS
        hold = 1.0
        fps = 16
        frames = max(2, int(round(hold * fps)))
        step = round(hold / frames, 4)
        label = "Your choices are:"

        entries = [
            {
                "id": "choice_lfx_base",
                "kind": "choice",
                "at": 0.0,
                "dur": hold,
                "position": "full",
                "label": label,
                "options": options,
            },
        ]
        for n in range(frames):
            entries.append({
                "id": f"choice_lfx_cursor_{n:02d}",
                "kind": "choice_cursor",
                "at": round(n * step, 3),
                "dur": step,
                "position": "full",
                "group": "choice_lfx_cursor",
                "order": n,
                "animation": True,
                "label": label,
                "options": options,
                "pointer": round((n / (frames - 1)) * plate.CHOICE_POINTER_CUT, 4),
            })

        # The cursor layer must agree with the static base on every row
        # centre; omitting the label throws the pointer ~17 px too high.
# Layout parity is computed independently below.
        for cursor_entry in entries[1:]:
            assert (plate._choice_cursor_position(cursor_entry) ==
                    plate._choice_cursor_position(
                        {**entries[0], "pointer": cursor_entry["pointer"]}))

        plates_dir = work_dir / "plates"
        plates_dir.mkdir()
        for e in entries:
            plate.render_plate(e).save(plates_dir / f"plate_{e['id']}.png")

        out = work_dir / "choice_burn.mp4"
        plate.burn(src, entries, plates_dir, out, ffmpeg=ffmpeg,
                   encode_args=("-c:v", "libx264rgb", "-crf", "0"))

        window_paths = _decode_all_frames(ffmpeg, out, work_dir / "frames")
        # 1 s at exactly 60000/1001 must yield ~60 frames, never 29-31.
        assert len(window_paths) in (59, 60, 61)

        loaded = [Image.open(p).convert("RGB") for p in window_paths]
        for image in loaded:
            assert image.getpixel((960, 540)) != (0, 0, 0)

        bbox = _allowed_cursor_bbox()
        left, top, right, bottom = bbox
        total = Image.new("RGB", loaded[0].size, (0, 0, 0))
        saw_change = False
        for before, after in zip(loaded, loaded[1:]):
            diff = ImageChops.difference(before, after)
            if diff.getbbox() is None:
                continue
            saw_change = True
            total = ImageChops.lighter(total, diff)
            # Every changed pixel must lie inside the cursor sweep.
            assert diff.crop((0, 0, left, FRAME_H)).getbbox() is None
            assert diff.crop((right, 0, FRAME_W, FRAME_H)).getbbox() is None
            assert diff.crop((left, 0, right, top)).getbbox() is None
            assert diff.crop((left, bottom, right, FRAME_H)).getbbox() is None

        assert saw_change, "cursor layer produced no visible motion"
        assert total.getbbox() is not None
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
