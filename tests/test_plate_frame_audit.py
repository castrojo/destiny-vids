"""Tests for auditing delivered midpoint frames against prepared manifests."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import plate_frame_audit as audit  # noqa: E402


def write_png(path: Path, color=(64, 96, 160, 255)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (96, 54), color).save(path)


def write_fake_ffmpeg(path: Path):
    path.write_text(
        """#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from PIL import Image

args = sys.argv[1:]
out = Path(args[-1])
ss = args[args.index("-ss") + 1]
log_path = os.environ.get("PLATE_FRAME_AUDIT_LOG")
fail_id = os.environ.get("PLATE_FRAME_AUDIT_FAIL_ID")
if log_path:
    with Path(log_path).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ss": ss, "out": out.name}) + "\\n")
if fail_id and fail_id in out.name:
    raise SystemExit(1)
out.parent.mkdir(parents=True, exist_ok=True)
Image.new("RGB", (320, 180), (12, 34, 56)).save(out)
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def test_audit_frames_reports_midpoints_hashes_and_written_artifacts(tmp_path, monkeypatch):
    fake_ffmpeg = tmp_path / "fake_ffmpeg.py"
    write_fake_ffmpeg(fake_ffmpeg)
    log_path = tmp_path / "ffmpeg-log.jsonl"
    monkeypatch.setenv("PLATE_FRAME_AUDIT_LOG", str(log_path))

    delivered = tmp_path / "delivered.mp4"
    delivered.write_bytes(b"video")
    plates_dir = tmp_path / "plates"
    out_dir = tmp_path / "audit"

    avatar1 = tmp_path / "avatars" / "mrbobbytables.png"
    avatar2 = tmp_path / "avatars" / "angellk.png"
    write_png(avatar1, (10, 20, 30, 255))
    write_png(avatar2, (30, 20, 10, 255))
    write_png(plates_dir / "plate_d01.png")
    write_png(plates_dir / "plate_d23a.png")

    manifest = {
        "plates": [
            {
                "id": "d01",
                "at": 10.0,
                "dur": 1.111,
                "kind": "chat",
                "speaker": "mrbobbytables",
                "text": "What a shitshow",
                "avatar": str(avatar1),
                "avatar_required": True,
            },
            {
                "id": "d23a",
                "at": 1.234,
                "dur": 2.0,
                "kind": "chat",
                "speaker": "angellk",
                "text": "Check your email smartass",
                "avatar": str(avatar2),
                "avatar_required": True,
            },
        ],
        "unresolved": [],
    }

    report = audit.audit_frames(
        delivered,
        manifest,
        plates_dir,
        expected_ids=["d23a", "d01"],
        out_dir=out_dir,
        ffmpeg=[sys.executable, str(fake_ffmpeg)],
    )

    assert report["expected_ids"] == ["d23a", "d01"]
    assert [row["plate_id"] for row in report["frames"]] == ["d23a", "d01"]
    assert [row["sample_at"] for row in report["frames"]] == [2.234, 10.556]
    assert [row["speaker"] for row in report["frames"]] == ["angellk", "mrbobbytables"]
    assert report["missing"] == []
    assert Path(report["report"]).exists()
    assert Path(report["contact_sheet"]).exists()
    assert all(Path(row["frame"]).exists() for row in report["frames"])
    assert report["frames"][0]["avatar_filename"] == "angellk.png"
    assert report["frames"][0]["avatar_sha256"] == hashlib.sha256(
        avatar2.read_bytes()).hexdigest()
    assert report["frames"][1]["avatar_sha256"] == hashlib.sha256(
        avatar1.read_bytes()).hexdigest()

    ffmpeg_calls = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert ffmpeg_calls == [
        {"ss": "2.234", "out": "frame_d23a.png"},
        {"ss": "10.556", "out": "frame_d01.png"},
    ]


def test_audit_frames_collects_missing_cue_plate_avatar_and_frame(tmp_path, monkeypatch):
    fake_ffmpeg = tmp_path / "fake_ffmpeg.py"
    write_fake_ffmpeg(fake_ffmpeg)
    monkeypatch.setenv("PLATE_FRAME_AUDIT_FAIL_ID", "d01")

    delivered = tmp_path / "delivered.mp4"
    delivered.write_bytes(b"video")
    manifest = {
        "plates": [{
            "id": "d01",
            "at": 4.0,
            "dur": 2.0,
            "kind": "chat",
            "speaker": "angellk",
            "text": "Hello",
            "avatar": str(tmp_path / "avatars" / "angellk.png"),
            "avatar_required": True,
        }]
    }

    report = audit.audit_frames(
        delivered,
        manifest,
        tmp_path / "plates",
        expected_ids=["missing", "d01"],
        out_dir=tmp_path / "audit",
        ffmpeg=[sys.executable, str(fake_ffmpeg)],
    )

    assert [item["status"] for item in report["missing"]] == [
        "missing_cue",
        "missing_plate_png",
        "missing_required_avatar",
        "missing_frame",
    ]
    assert report["missing"][0]["plate_id"] == "missing"
    row = report["frames"][0]
    assert row["plate_id"] == "d01"
    assert row["plate_png"] is None
    assert row["avatar_sha256"] is None
    assert row["frame"] is None


def test_cli_loads_recovery_ids_in_ledger_order_and_check_fails_on_missing(tmp_path):
    fake_ffmpeg = tmp_path / "fake_ffmpeg.py"
    write_fake_ffmpeg(fake_ffmpeg)

    delivered = tmp_path / "delivered.mp4"
    delivered.write_bytes(b"video")
    plates_dir = tmp_path / "plates"
    write_png(plates_dir / "plate_d01.png")
    write_png(plates_dir / "plate_d23a.png")
    avatar1 = tmp_path / "avatars" / "mrbobbytables.png"
    avatar2 = tmp_path / "avatars" / "clubanderson.png"
    write_png(avatar1)
    write_png(avatar2)

    manifest_path = tmp_path / "prepared.json"
    manifest_path.write_text(json.dumps([
        {
            "id": "d01",
            "at": 1.0,
            "dur": 2.0,
            "kind": "chat",
            "speaker": "mrbobbytables",
            "text": "first",
            "avatar": str(avatar1),
            "avatar_required": True,
        },
        {
            "id": "d23a",
            "at": 4.0,
            "dur": 2.0,
            "kind": "chat",
            "speaker": "clubanderson",
            "text": "second",
            "avatar": str(avatar2),
            "avatar_required": True,
        },
    ]), encoding="utf-8")

    ledger_path = tmp_path / "recovery.json"
    ledger_path.write_text(json.dumps({
        "act_iii": {
            "active": [
                {"id": "d23a", "object": {}},
                {"id": "d01", "object": {}},
            ]
        },
        "act_ii": {
            "active": [
                {"id": "missing", "object": {}},
            ]
        },
    }), encoding="utf-8")

    out_dir = tmp_path / "act-iii"
    assert audit.main([
        "--delivered", str(delivered),
        "--manifest", str(manifest_path),
        "--plates-dir", str(plates_dir),
        "--expected", str(ledger_path),
        "--act", "III",
        "--out", str(out_dir),
        "--ffmpeg", sys.executable, str(fake_ffmpeg),
        "--check",
    ]) == 0
    report = json.loads((out_dir / "frame-audit.json").read_text(encoding="utf-8"))
    assert report["expected_ids"] == ["d23a", "d01"]
    assert [row["plate_id"] for row in report["frames"]] == ["d23a", "d01"]

    assert audit.main([
        "--delivered", str(delivered),
        "--manifest", str(manifest_path),
        "--plates-dir", str(plates_dir),
        "--expected", str(ledger_path),
        "--act", "II",
        "--out", str(tmp_path / "act-ii"),
        "--ffmpeg", sys.executable, str(fake_ffmpeg),
        "--check",
    ]) == 1
