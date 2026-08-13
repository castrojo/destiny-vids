"""Tests for the Whisp inbox ledger.

A dictated note with no status is the failure the intake audit found: nobody
can tell a note nobody read from a note somebody filed. These pin the two
properties that make the ledger trustworthy: a note without a receipt always
surfaces (``--check`` fails), and the ledger never carries the owner's words.

The suite is offline and never touches the real Whisp directory -- every test
scans a tmp_path fixture instead.
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tools.inbox import (
    find_changed,
    find_unstatused,
    load_ledger,
    main,
    reconcile,
    resolve_note_id,
    scan_notes,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMITTED_LEDGER = REPO_ROOT / "inbox" / "ledger.json"


@pytest.fixture
def notes_dir(tmp_path):
    directory = tmp_path / "notes"
    directory.mkdir()
    return directory


@pytest.fixture
def ledger_path(tmp_path):
    return tmp_path / "inbox" / "ledger.json"


def _note(notes_dir, name, text):
    (notes_dir / f"{name}.md").write_text(text, encoding="utf-8")
    return name


def _set(notes_dir, ledger_path, prefix, status):
    assert main(["--set", prefix, status,
                 "--notes-dir", str(notes_dir),
                 "--ledger", str(ledger_path)]) == 0


def test_scan_reads_only_markdown_notes(notes_dir):
    _note(notes_dir, "abc123", "a work order")
    (notes_dir / "metadata.json").write_text("{}", encoding="utf-8")
    assert list(scan_notes(notes_dir)) == ["abc123"]


def test_a_missing_notes_dir_is_not_an_empty_one(tmp_path):
    # A machine without the flatpak must not read as "every note was deleted".
    assert scan_notes(tmp_path / "nowhere") is None


def test_a_missing_notes_dir_marks_nothing_absent(notes_dir, ledger_path, capsys):
    _note(notes_dir, "abc123", "a work order")
    _set(notes_dir, ledger_path, "abc123", "landed")
    capsys.readouterr()
    gone = notes_dir.parent / "nowhere"
    assert main(["--notes-dir", str(gone), "--ledger", str(ledger_path)]) == 0
    assert "absent" not in capsys.readouterr().out
    assert main(["--check", "--notes-dir", str(gone),
                 "--ledger", str(ledger_path)]) == 0


def test_a_new_note_is_unstatused_and_fails_check(notes_dir, ledger_path, capsys):
    _note(notes_dir, "abc123", "a work order")
    assert main(["--check", "--notes-dir", str(notes_dir),
                 "--ledger", str(ledger_path)]) == 1
    assert "abc123" in capsys.readouterr().out


def test_write_adds_new_notes_without_a_status(notes_dir, ledger_path):
    _note(notes_dir, "abc123", "a work order")
    assert main(["--write", "--notes-dir", str(notes_dir),
                 "--ledger", str(ledger_path)]) == 0
    entry = load_ledger(ledger_path)["notes"]["abc123"]
    assert entry["status"] is None
    assert entry["excerpt"] is None
    # --check still surfaces it: --write is intake, not acknowledgement.
    assert main(["--check", "--notes-dir", str(notes_dir),
                 "--ledger", str(ledger_path)]) == 1


def test_a_statused_note_passes_check(notes_dir, ledger_path):
    _note(notes_dir, "abc123", "a work order")
    main(["--write", "--notes-dir", str(notes_dir), "--ledger", str(ledger_path)])
    _set(notes_dir, ledger_path, "abc", "filed #118")
    assert main(["--check", "--notes-dir", str(notes_dir),
                 "--ledger", str(ledger_path)]) == 0
    assert load_ledger(ledger_path)["notes"]["abc123"]["status"] == "filed #118"


def test_write_never_overwrites_a_recorded_status(notes_dir, ledger_path):
    _note(notes_dir, "abc123", "a work order")
    _set(notes_dir, ledger_path, "abc123", "landed")
    main(["--write", "--notes-dir", str(notes_dir), "--ledger", str(ledger_path)])
    assert load_ledger(ledger_path)["notes"]["abc123"]["status"] == "landed"


def test_editing_a_statused_note_surfaces_it_again(notes_dir, ledger_path):
    # The receipt covers the content it was recorded against; an edit may
    # carry new orders, so a changed hash fails --check even with a status.
    path = notes_dir / "abc123.md"
    path.write_text("version one", encoding="utf-8")
    _set(notes_dir, ledger_path, "abc123", "filed #118")
    path.write_text("version one, and another thing", encoding="utf-8")

    notes = scan_notes(notes_dir)
    ledger = load_ledger(ledger_path)
    assert find_changed(notes, ledger) == ["abc123"]
    assert main(["--check", "--notes-dir", str(notes_dir),
                 "--ledger", str(ledger_path)]) == 1


@pytest.mark.parametrize("status", ["done", "filed", "filed 118", "FILED #1",
                                    "landed-ish", ""])
def test_a_status_outside_the_enum_is_refused(notes_dir, ledger_path, status, capsys):
    _note(notes_dir, "abc123", "a work order")
    assert main(["--set", "abc123", status,
                 "--notes-dir", str(notes_dir),
                 "--ledger", str(ledger_path)]) == 2
    assert "invalid status" in capsys.readouterr().err


@pytest.mark.parametrize("status", ["filed #1", "landed", "superseded",
                                    "ignored", "out-of-scope"])
def test_every_status_in_the_enum_is_accepted(notes_dir, ledger_path, status):
    _note(notes_dir, "abc123", "a work order")
    _set(notes_dir, ledger_path, "abc123", status)


def test_note_ids_resolve_by_unique_prefix(notes_dir):
    _note(notes_dir, "abc123", "one")
    _note(notes_dir, "abd999", "two")
    assert resolve_note_id("abc", scan_notes(notes_dir), {"notes": {}}) == "abc123"
    with pytest.raises(ValueError, match="ambiguous"):
        resolve_note_id("ab", scan_notes(notes_dir), {"notes": {}})
    with pytest.raises(ValueError, match="no note id matches"):
        resolve_note_id("zzz", scan_notes(notes_dir), {"notes": {}})


def test_an_absent_note_cannot_be_statused(notes_dir, ledger_path):
    # A status asserts something about content; content that is not there
    # cannot be hashed, so the receipt would be a guess.
    assert main(["--set", "ghost", "ignored",
                 "--notes-dir", str(notes_dir),
                 "--ledger", str(ledger_path)]) == 2


def test_a_ledgered_note_that_vanishes_is_reported_not_dropped(notes_dir, ledger_path,
                                                               capsys):
    path = notes_dir / "abc123.md"
    path.write_text("a work order", encoding="utf-8")
    _set(notes_dir, ledger_path, "abc123", "filed #118")
    path.unlink()
    ledger = load_ledger(ledger_path)
    assert "abc123" in ledger["notes"]
    assert main(["--check", "--notes-dir", str(notes_dir),
                 "--ledger", str(ledger_path)]) == 0  # it has a receipt
    assert main(["--notes-dir", str(notes_dir), "--ledger", str(ledger_path)]) == 0
    assert "absent" in capsys.readouterr().out


def test_the_ledger_never_carries_note_text(notes_dir, ledger_path):
    # The notes are the owner's. Until the owner signs off on excerpts
    # (#121 blocked_on), the only fields a note produces are hash, mtime,
    # status and a null excerpt -- however distinctive its content.
    distinctive = "the purple zeppelin of data-collection 0141"
    _note(notes_dir, "abc123", distinctive)
    _set(notes_dir, ledger_path, "abc123", "filed #118")
    raw = ledger_path.read_text(encoding="utf-8")
    assert distinctive not in raw
    entry = load_ledger(ledger_path)["notes"]["abc123"]
    assert set(entry) == {"sha256", "mtime", "status", "excerpt"}
    assert entry["excerpt"] is None


def test_reconcile_is_idempotent(notes_dir, ledger_path):
    _note(notes_dir, "abc123", "a work order")
    ledger = load_ledger(ledger_path)
    notes = scan_notes(notes_dir)
    assert reconcile(notes, ledger) == ["abc123"]
    assert reconcile(notes, ledger) == []


def test_unstatused_lists_only_notes_without_a_status(notes_dir, ledger_path):
    _note(notes_dir, "abc123", "one")
    _note(notes_dir, "def456", "two")
    _set(notes_dir, ledger_path, "abc123", "out-of-scope")
    notes = scan_notes(notes_dir)
    ledger = load_ledger(ledger_path)
    assert find_unstatused(notes, ledger) == ["def456"]


def test_the_committed_ledger_matches_its_schema():
    """The ledger is a committed record; the suite, not the next rebuild,
    is where a hand edit fails."""
    with (REPO_ROOT / "schema" / "inbox-ledger.schema.json").open(encoding="utf-8") as fh:
        validator = Draft202012Validator(json.load(fh))
    ledger = json.loads(COMMITTED_LEDGER.read_text(encoding="utf-8"))
    errors = sorted(validator.iter_errors(ledger), key=lambda e: list(e.path))
    assert not errors, "\n".join(
        f"{'/'.join(str(p) for p in e.path)}: {e.message}" for e in errors
    )


def test_the_committed_ledger_statuses_only_point_at_real_shapes():
    """Every entry carries the four fields and no excerpt, per #121."""
    ledger = json.loads(COMMITTED_LEDGER.read_text(encoding="utf-8"))
    assert ledger["notes"], "the seed ledger should not be empty"
    for nid, entry in ledger["notes"].items():
        assert set(entry) == {"sha256", "mtime", "status", "excerpt"}, nid
        assert entry["excerpt"] is None, nid
