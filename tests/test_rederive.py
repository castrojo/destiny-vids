"""Tests for re-deriving the index after a vocab edit.

`vocab/casting.yaml` promises that a vocab edit re-casts the whole index with no
re-tagging. These pin the tool that makes that true, and the two properties that
make it safe to run: it never touches a tagger field, and it never reformats a
file it did not need to change.
"""

import json
import shutil
from pathlib import Path

import pytest

from tools.derive import load_leads
from tools.rederive import _detect_format, main, rederive_segment

REPO_ROOT = Path(__file__).resolve().parents[1]
SEGMENTS = REPO_ROOT / "segments"


@pytest.fixture
def segdir(tmp_path):
    """A throwaway copy of a few real segments."""
    dest = tmp_path / "segments"
    dest.mkdir()
    for path in sorted(SEGMENTS.glob("*.json"))[:5]:
        shutil.copy(path, dest / path.name)
    return dest


def test_the_checked_in_index_agrees_with_the_vocab():
    """The whole point: drift is a bug, so the committed state must be clean."""
    assert main(["--check", "--dir", str(SEGMENTS)]) == 0


def test_stale_casting_is_detected_and_reported(segdir):
    path = next(iter(segdir.glob("*.json")))
    record = json.loads(path.read_text(encoding="utf-8"))
    record["casting"] = dict(record.get("casting") or {}, person="someone_else")
    path.write_text(json.dumps(record, indent=1), encoding="utf-8")

    assert main(["--check", "--dir", str(segdir)]) == 1  # drift, wrote nothing
    assert json.loads(path.read_text(encoding="utf-8"))["casting"]["person"] == "someone_else"

    assert main(["--dir", str(segdir)]) == 0             # rewrote it
    assert json.loads(path.read_text(encoding="utf-8"))["casting"]["person"] != "someone_else"


def test_rederive_never_rewrites_a_tagger_field(segdir):
    """It recomputes derived fields; everything the tagger said is untouched."""
    path = next(iter(segdir.glob("*.json")))
    before = json.loads(path.read_text(encoding="utf-8"))
    record = dict(before)
    record["clean"] = not record["clean"]          # corrupt a derived field
    path.write_text(json.dumps(record, indent=1), encoding="utf-8")

    main(["--dir", str(segdir)])
    after = json.loads(path.read_text(encoding="utf-8"))
    for field in ("overlays", "character", "caption", "shot_scale", "start_sec"):
        if field in before:
            assert after[field] == before[field], field
    assert after["clean"] == before["clean"]       # and the derived one is restored


def test_a_clean_run_leaves_bytes_identical(segdir):
    """No drift must mean no diff -- not even a reformat."""
    raw = {p.name: p.read_bytes() for p in segdir.glob("*.json")}
    assert main(["--dir", str(segdir)]) == 0
    for path in segdir.glob("*.json"):
        assert path.read_bytes() == raw[path.name], path.name


def test_a_rewrite_preserves_the_file_s_own_layout(segdir):
    """A one-word change must be a one-line diff, not a 378-line reformat."""
    path = next(iter(segdir.glob("*.json")))
    record = json.loads(path.read_text(encoding="utf-8"))
    record["casting"] = dict(record.get("casting") or {}, person="someone_else")
    path.write_text(json.dumps(record, indent=1), encoding="utf-8")  # 1-space, no tail

    main(["--dir", str(segdir)])
    raw = path.read_text(encoding="utf-8")
    assert raw == json.dumps(json.loads(raw), indent=1)
    assert not raw.endswith("\n")


@pytest.mark.parametrize("indent,tail", [(1, ""), (2, "\n"), (4, "")])
def test_format_detection_round_trips(indent, tail):
    record = {"a": 1, "b": {"c": [1, 2]}}
    raw = json.dumps(record, indent=indent) + tail
    assert _detect_format(raw, record) == (indent, tail)


def test_rederive_segment_reports_nothing_when_nothing_moved():
    record = json.loads(next(iter(SEGMENTS.glob("*.json"))).read_text(encoding="utf-8"))
    _, changes = rederive_segment(record, load_leads())
    assert changes == {}
