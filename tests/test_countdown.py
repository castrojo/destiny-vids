"""Frame-derived programme countdown tests."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageStat

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts import build_countdown  # noqa: E402
from tools import plate  # noqa: E402
from test_plate_choice_video import _require_h264_ffmpeg  # noqa: E402

FPS = Fraction(60000, 1001)
RATE = "60000/1001"



def test_countdown_first_zero_is_exactly_programme_444():
    entries = build_countdown.countdown_entries(217.6, 46.6, target=264.0)
    zero = next(e for e in entries if e["text"] == "00:00")
    assert zero["programme_at"] == pytest.approx(264.0, abs=1e-9)
    assert all(e["text"] != "00:00" for e in entries[:entries.index(zero)])



def test_countdown_values_are_derived_not_authored():
    entries = build_countdown.countdown_entries(260.2, 4.8, target=264.0)
    assert [e["text"] for e in entries] == ["00:04", "00:03", "00:02", "00:01", "00:00"]



def test_countdown_plate_uses_the_lower_matte_safe_area():
    spec = {"kind": "countdown", "text": "00:00"}
    card = plate.render_plate(spec)
    assert card.mode == "RGBA"
    assert card.getchannel("A").getbbox() == (0, 0, card.width, card.height)
    frame = plate.place(card, "countdown-bottom", (0, 138, 1920, 804))
    x0, y0, x1, y1 = frame.getchannel("A").getbbox()
    assert x0 + x1 == plate.FRAME_W - 1
    assert y0 > 942
    assert y1 <= plate.FRAME_H


def test_burn_boundary_keeps_the_exact_60000_over_1001_frame():
    # This is the reported programme-local boundary: millisecond formatting
    # turns 46.596550 into 46.597 and starts the overlay one frame late.
    assert plate._ceil_frame_index(46.59655) == 2793
    assert plate._frame_enable(46.59655, 0.1001).startswith(
        "gte(n\\,2793)*lt(n\\,")


def test_countdown_burn_changes_on_the_exact_target_frame():
    """The real 60000/1001 burn must show zero on its target frame, not one late."""
    ffmpeg = _require_h264_ffmpeg()
    work = Path(tempfile.mkdtemp(dir="/tmp", prefix="countdown_burn_"))
    try:
        source = work / "source.mp4"
        subprocess.run(
            list(ffmpeg) + ["-v", "error", "-y", "-f", "lavfi",
                            "-i", f"color=black:s=1920x1080:r={RATE}",
                            "-t", "0.8", "-c:v", "libx264rgb", "-crf", "0",
                            str(source)],
            check=True, capture_output=True,
        )
        target_frame = 30
        programme_frame = target_frame
        boundary = Fraction(target_frame, 1) / FPS
        entries = [
            {"id": "one", "kind": "countdown", "at": 0.0,
             "dur": float(boundary), "position": "countdown-bottom",
             "text": "00:01", "programme_frame": programme_frame - 1},
            {"id": "zero", "kind": "countdown", "at": float(boundary),
             "dur": 0.3, "position": "countdown-bottom", "text": "00:00",
             "programme_frame": programme_frame},
        ]
        assert entries[1]["programme_frame"] == target_frame
        plates_dir = work / "plates"
        plates_dir.mkdir()
        for entry in entries:
            card = plate.render_plate(entry)
            plate.place(card, entry["position"], build_countdown.PICTURE).save(
                plates_dir / f"plate_{entry['id']}.png")
        output = work / "burn.mp4"
        plate.burn(source, entries, plates_dir, output, ffmpeg=ffmpeg,
                   encode_args=("-c:v", "libx264rgb", "-crf", "0"))

        frames = work / "frames"
        frames.mkdir()
        subprocess.run(
            list(ffmpeg) + ["-v", "error", "-y", "-i", str(output),
                            "-vf", f"select='eq(n,{target_frame - 1})+eq(n,{target_frame})'",
                            "-vsync", "0", str(frames / "frame_%02d.png")],
            check=True, capture_output=True,
        )
        decoded = sorted(frames.glob("frame_*.png"))
        assert len(decoded) == 2

        def expected(entry):
            frame = Image.new("RGBA", (1920, 1080))
            frame.alpha_composite(plate.place(
                plate.render_plate(entry), entry["position"],
                build_countdown.PICTURE))
            return frame.convert("RGB")

        before, target = (Image.open(path).convert("RGB") for path in decoded)
        expected_one, expected_zero = expected(entries[0]), expected(entries[1])
        before_one = ImageChops.difference(before, expected_one)
        before_zero = ImageChops.difference(before, expected_zero)
        target_one = ImageChops.difference(target, expected_one)
        target_zero = ImageChops.difference(target, expected_zero)
        assert sum(ImageStat.Stat(before_one).sum) < sum(ImageStat.Stat(before_zero).sum)
        assert sum(ImageStat.Stat(target_zero).sum) < sum(ImageStat.Stat(target_one).sum)
        assert target_one.getbbox() is not None, "00:01 must be absent at target frame"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_plan_uses_the_named_derivative_not_a_source_scan(monkeypatch, tmp_path):
    thread = tmp_path / "thread.json"
    plan = tmp_path / "plan.json"
    thread.write_text(json.dumps({
        "movements": [{"id": "perfume-2", "out_file": "renders/perfume-2.mp4",
                        "duration": 2.0}],
        "_derivatives": {
            "decoy": {"source": "renders/perfume-2.mp4",
                      "out_file": "renders/wrong.mp4"},
            "perfume-2-countdown": {"source": "renders/perfume-2.mp4",
                                     "out_file": "renders/perfume-2-countdown.mp4"},
        },
    }))
    plan.write_text(json.dumps({"items": [
        {"path": "renders/perfume-2-countdown.mp4", "kind": "clip", "dur": 2.0}
    ]}))
    monkeypatch.setattr(build_countdown, "THREAD", thread)
    monkeypatch.setattr(build_countdown, "PLAN", plan)
    result = build_countdown.plan_countdown(target=1.0)
    assert result["out_file"] == "renders/perfume-2-countdown.mp4"


def test_builder_defaults_to_the_reachable_farm(monkeypatch, tmp_path):
    source = tmp_path / "source.mp4"
    source.touch()
    output = tmp_path / "out.mp4"
    spec = {
        "source": str(source), "out_file": str(output),
        "segment_duration": 2.0, "entries": [],
    }
    captured = {}
    monkeypatch.setattr(build_countdown, "plan_countdown", lambda: spec)
    monkeypatch.setattr(build_countdown.plate, "render_all", lambda *a, **k: [])
    monkeypatch.setattr(build_countdown.plate, "burn",
                        lambda *a, **k: captured.update(k))
    monkeypatch.setattr("tools.farm.cluster_available", lambda: (True, ""))
    farmed = []
    monkeypatch.setattr("tools.farm.run_ffmpeg_on_cluster",
                        lambda argv, **kwargs: farmed.append(kwargs))
    build_countdown.build()
    assert captured["runner"] is not None
    captured["runner"](["ffmpeg", "-y"])
    assert farmed


def test_print_command_exposes_the_complete_burn_argv(capsys, tmp_path):
    spec = {
        "source": "renders/perfume-2.mp4",
        "out_file": "renders/perfume-2-countdown.mp4",
        "segment_duration": 2.0,
        "entries": [{"id": "zero", "at": 0.0, "dur": 2.0,
                     "kind": "countdown", "text": "00:00"}],
    }
    build_countdown.print_command(spec)
    line = capsys.readouterr().out.strip()
    assert line.startswith("/"), line
    assert "-filter_complex" in line
    assert "renders/perfume-2-countdown.mp4" in line
    assert "-c:a copy" in line


def test_unreachable_farm_requires_explicit_local_fallback(monkeypatch, tmp_path):
    source = tmp_path / "source.mp4"
    source.touch()
    spec = {"source": str(source), "out_file": str(tmp_path / "out.mp4"),
            "segment_duration": 2.0, "entries": []}
    monkeypatch.setattr(build_countdown, "plan_countdown", lambda: spec)
    monkeypatch.setattr(build_countdown.plate, "render_all", lambda *a, **k: [])
    monkeypatch.setattr(build_countdown.render, "find_ffmpeg", lambda: ["ffmpeg"])
    monkeypatch.setattr(build_countdown.farm, "cluster_available",
                        lambda: (False, "kubectl not on PATH"))
    with pytest.raises(SystemExit, match=r"--local"):
        build_countdown.build()
