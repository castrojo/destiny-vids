#!/usr/bin/env python3
"""Audit delivered midpoint frames for expected prepared-manifest plates."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import identity  # noqa: E402
from tools.render import find_ffmpeg  # noqa: E402

REPORT_NAME = "frame-audit.json"
CONTACT_SHEET_NAME = "frame-audit-contact-sheet.png"
FRAME_PREFIX = "frame_"
PLATE_PREFIX = "plate_"
THUMB_SIZE = (320, 180)
CELL_WIDTH = 360
CELL_PADDING = 16
CONTACT_COLUMNS = 3
ROW_FIELDS = (
    "plate_id",
    "expected_index",
    "manifest_index",
    "at",
    "dur",
    "sample_at",
    "speaker",
    "text",
    "avatar",
    "avatar_filename",
    "avatar_sha256",
    "plate_png",
    "frame",
    "status",
    "findings",
)


def _path(value) -> Path:
    return Path(value).expanduser()


def _resolved(value) -> Path:
    path = _path(value)
    return path if path.is_absolute() else (REPO_ROOT / path)


def _load_jsonish(value):
    if isinstance(value, (str, Path)):
        with _path(value).open(encoding="utf-8") as fh:
            return json.load(fh)
    return value


def _manifest_entries(manifest):
    document = _load_jsonish(manifest)
    if isinstance(document, dict):
        return list(document.get("plates", document.get("cards", [])))
    return list(document or [])


def _expected_ids(ledger, act: str) -> list[str]:
    data = _load_jsonish(ledger)
    key = {
        "II": "act_ii",
        "2": "act_ii",
        "ACT_II": "act_ii",
        "III": "act_iii",
        "3": "act_iii",
        "ACT_III": "act_iii",
    }.get(str(act).strip().upper())
    if not key or key not in data:
        raise ValueError(f"unknown act {act!r}")
    active = data[key].get("active") or []
    ids = []
    for item in active:
        plate_id = item.get("id") or (item.get("object") or {}).get("id")
        if plate_id:
            ids.append(plate_id)
    return ids


def _canonical_speaker(entry: dict) -> str | None:
    speaker = entry.get("speaker")
    if speaker:
        try:
            return identity.canonical_login(speaker)
        except identity.UnknownPerson:
            return speaker
    return entry.get("speaker_pending") or entry.get("name")


def _exact_copy(entry: dict) -> str | None:
    for key in ("text", "message"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    parts = []
    for key in ("title", "subtitle", "label", "class", "name", "footer"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    body = entry.get("body")
    if isinstance(body, list):
        parts.extend(str(line).strip() for line in body if str(line).strip())
    return "\n".join(parts) or None


def _avatar_file(entry: dict) -> Path | None:
    avatar = entry.get("avatar")
    if not avatar:
        return None
    return _resolved(avatar)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ffmpeg_prefix(ffmpeg=None) -> list[str]:
    if ffmpeg is None:
        return list(find_ffmpeg())
    if isinstance(ffmpeg, (str, Path)):
        return [str(ffmpeg)]
    return [str(part) for part in ffmpeg]


def _extract_frame(delivered_video, sample_at: float, out_path: Path, ffmpeg=None):
    video_path = _resolved(delivered_video)
    if not video_path.is_file():
        return False, f"missing delivered video: {video_path}"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        *_ffmpeg_prefix(ffmpeg),
        "-nostdin",
        "-y",
        "-v",
        "error",
        "-ss",
        f"{sample_at:.3f}",
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        str(out_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout).strip()
    if not out_path.is_file() or out_path.stat().st_size <= 0:
        return False, "ffmpeg wrote no frame"
    return True, None


def _row(plate_id: str, expected_index: int) -> dict:
    row = dict.fromkeys(ROW_FIELDS)
    row.update({
        "plate_id": plate_id,
        "expected_index": expected_index,
        "status": "ok",
        "findings": [],
    })
    return row


def _missing(missing: list[dict], row: dict | None, plate_id: str, status: str, **extra):
    finding = {"plate_id": plate_id, "status": status}
    finding.update({key: value for key, value in extra.items() if value is not None})
    missing.append(finding)
    if row is not None:
        row["findings"].append(finding)
        if row["status"] == "ok":
            row["status"] = status


def _contact_lines(row: dict) -> list[str]:
    lines = [row["plate_id"]]
    for field in ("speaker", "text", "avatar_filename"):
        value = row.get(field)
        if not value:
            continue
        if field == "text":
            lines.extend(textwrap.wrap(str(value), width=40) or [""])
        else:
            lines.extend(textwrap.wrap(str(value), width=40) or [""])
    return lines


def _cell_height(row: dict, line_height: int) -> int:
    return (CELL_PADDING + THUMB_SIZE[1] + CELL_PADDING +
            len(_contact_lines(row)) * line_height + CELL_PADDING)


def _load_frame_image(path: str | None) -> Image.Image:
    if path:
        frame = Path(path)
        if frame.is_file():
            try:
                with Image.open(frame) as img:
                    return img.convert("RGB")
            except OSError:
                pass
    return Image.new("RGB", THUMB_SIZE, (18, 24, 38))


def _draw_contact_sheet(rows: list[dict], out_path: Path):
    font = ImageFont.load_default()
    line_height = font.getbbox("Ag")[3] + 4
    if not rows:
        sheet = Image.new("RGB", (CELL_WIDTH, THUMB_SIZE[1] + CELL_PADDING * 2), (8, 12, 20))
        sheet.save(out_path)
        return out_path

    columns = min(CONTACT_COLUMNS, max(1, len(rows)))
    row_heights = []
    for start in range(0, len(rows), columns):
        chunk = rows[start:start + columns]
        row_heights.append(max(_cell_height(row, line_height) for row in chunk))
    width = columns * CELL_WIDTH + (columns + 1) * CELL_PADDING
    height = sum(row_heights) + (len(row_heights) + 1) * CELL_PADDING
    sheet = Image.new("RGB", (width, height), (8, 12, 20))
    draw = ImageDraw.Draw(sheet)

    y = CELL_PADDING
    for row_height, start in zip(row_heights, range(0, len(rows), columns)):
        chunk = rows[start:start + columns]
        for column, row in enumerate(chunk):
            x = CELL_PADDING + column * (CELL_WIDTH + CELL_PADDING)
            frame = ImageOps.contain(_load_frame_image(row.get("frame")), THUMB_SIZE)
            thumb = Image.new("RGB", THUMB_SIZE, (18, 24, 38))
            thumb.paste(frame, ((THUMB_SIZE[0] - frame.width) // 2,
                                (THUMB_SIZE[1] - frame.height) // 2))
            sheet.paste(thumb, (x, y))
            text_y = y + THUMB_SIZE[1] + CELL_PADDING
            for line in _contact_lines(row):
                draw.text((x, text_y), line, fill=(245, 245, 245), font=font)
                text_y += line_height
        y += row_height + CELL_PADDING
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    return out_path


def audit_frames(delivered_video, manifest, plates_dir, expected_ids, out_dir, ffmpeg=None) -> dict:
    out_dir = _path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plates_root = _path(plates_dir)
    entries = _manifest_entries(manifest)
    by_id = {entry.get("id"): (index, entry) for index, entry in enumerate(entries)}
    expected_ids = list(expected_ids)
    frames = []
    missing = []

    for expected_index, plate_id in enumerate(expected_ids):
        row = _row(plate_id, expected_index)
        found = by_id.get(plate_id)
        if found is None:
            _missing(missing, row, plate_id, "missing_cue")
            frames.append(row)
            continue
        manifest_index, entry = found
        at = entry.get("at")
        dur = entry.get("dur")
        row.update({
            "manifest_index": manifest_index,
            "speaker": _canonical_speaker(entry),
            "text": _exact_copy(entry),
            "avatar": entry.get("avatar"),
            "avatar_filename": Path(entry["avatar"]).name if entry.get("avatar") else None,
        })
        if not isinstance(at, (int, float)) or not isinstance(dur, (int, float)):
            _missing(missing, row, plate_id, "missing_cue", reason="missing at/dur")
            frames.append(row)
            continue

        sample_at = round(float(at) + float(dur) / 2.0, 3)
        plate_png = plates_root / f"{PLATE_PREFIX}{plate_id}.png"
        avatar_path = _avatar_file(entry)
        frame_path = out_dir / f"{FRAME_PREFIX}{plate_id}.png"

        row.update({
            "at": float(at),
            "dur": float(dur),
            "sample_at": sample_at,
            "plate_png": str(plate_png) if plate_png.is_file() else None,
        })

        if row["plate_png"] is None:
            _missing(missing, row, plate_id, "missing_plate_png", path=str(plate_png))

        if avatar_path:
            if avatar_path.is_file():
                row["avatar_sha256"] = _sha256(avatar_path)
            else:
                _missing(missing, row, plate_id, "missing_avatar", path=str(avatar_path))
        elif entry.get("avatar_required"):
            _missing(missing, row, plate_id, "missing_required_avatar")

        ok, detail = _extract_frame(delivered_video, sample_at, frame_path, ffmpeg=ffmpeg)
        if ok:
            row["frame"] = str(frame_path)
        else:
            _missing(missing, row, plate_id, "missing_frame", path=str(frame_path), detail=detail)

        frames.append(row)

    contact_sheet_rows = sorted(
        (row for row in frames if row["frame"] and row["manifest_index"] is not None),
        key=lambda row: row["manifest_index"],
    )
    contact_sheet = _draw_contact_sheet(contact_sheet_rows, out_dir / CONTACT_SHEET_NAME)
    report = {
        "delivered_video": str(_path(delivered_video)),
        "manifest": str(_path(manifest)) if isinstance(manifest, (str, Path)) else None,
        "plates_dir": str(plates_root),
        "expected_ids": expected_ids,
        "frames": frames,
        "missing": missing,
        "contact_sheet_plate_ids": [row["plate_id"] for row in contact_sheet_rows],
        "contact_sheet": str(contact_sheet),
        "report": str(out_dir / REPORT_NAME),
    }
    (out_dir / REPORT_NAME).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--delivered", required=True, help="delivered candidate to sample")
    ap.add_argument("--manifest", required=True, help="prepared manifest (dict or list)")
    ap.add_argument("--plates-dir", required=True, help="rendered plate PNG directory")
    ap.add_argument("--expected", required=True, help="recovery ledger JSON")
    ap.add_argument("--act", required=True, help="which act to load from the recovery ledger")
    ap.add_argument("--out", required=True, help="output directory for frames and report")
    ap.add_argument("--ffmpeg", nargs="+", help="explicit ffmpeg command prefix")
    ap.add_argument("--check", action="store_true", help="exit non-zero when anything is missing")
    args = ap.parse_args(argv)

    expected_ids = _expected_ids(args.expected, args.act)
    report = audit_frames(
        args.delivered,
        args.manifest,
        args.plates_dir,
        expected_ids=expected_ids,
        out_dir=args.out,
        ffmpeg=args.ffmpeg,
    )
    report["act"] = str(args.act)
    Path(report["report"]).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(
        f"frame-audit {args.act}: {len(report['frames'])}/{len(expected_ids)} rows, "
        f"{len(report['missing'])} missing"
    )
    print(report["report"])
    print(report["contact_sheet"])
    return 1 if args.check and report["missing"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
