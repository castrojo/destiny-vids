import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_prologue


def _load_manifest():
    return json.loads(build_prologue.MANIFEST.read_text())


def test_volunteer_briefing_precedes_the_moved_book():
    doc = _load_manifest()
    by_id = {p["id"]: p for p in doc["plates"]}
    card = by_id["mission-briefing"]
    assert card == {
        "id": "mission-briefing", "kind": "act",
        "at": 26.9, "dur": 6.74,
        "label": "PROJECT BLUEFIN MISSION BRIEFING",
        "title": "Thanks for Volunteering",
        "body": [
            "Tophee Protocol Quick Insertion // ACTIVATED",
            "Agones Cluster // Cycling",
            "Mechaphippy Deployment // UNAUTHORIZED",
        ],
        "copy_source": "owner_supplied",
    }
    assert by_id["book-a"]["at"] == 34.0
    assert card["at"] + card["dur"] <= by_id["book-a"]["at"]


def _load_plate(id_):
    doc = _load_manifest()
    return {p["id"]: p for p in doc["plates"]}[id_]


def test_filtergraph_briefing_before_book():
    fg = build_prologue.filtergraph()
    briefing = _load_plate("mission-briefing")
    book = _load_plate("book-a")
    briefing_window = (
        f"enable=between(t\\,{briefing['at']:.3f}\\,"
        f"{briefing['at'] + briefing['dur']:.3f})"
    )
    book_window = (
        f"enable=between(t\\,{book['at']:.3f}\\,"
        f"{book['at'] + book['dur']:.3f})"
    )
    assert briefing_window in fg
    assert book_window in fg
    assert fg.index(briefing_window) < fg.index(book_window)


def _input_paths(cmd):
    return [cmd[i + 1] for i, arg in enumerate(cmd) if arg == "-i"]


def test_filtergraph_reads_manifest_once_and_uses_changed_timing(tmp_path, monkeypatch):
    """A monkeypatched MANIFEST with swapped/different timings drives the graph.

    This fails if filtergraph() ever falls back to hard-coded old numbers
    (briefing 26.9-33.640, book 34.0-40.740) instead of reading the file.
    """
    modified_manifest = tmp_path / "modified-prologue-plates.json"
    doc = _load_manifest()
    plates_by_id = {p["id"]: p for p in doc["plates"]}
    # Swap and shift timings so the order and values differ from production.
    plates_by_id["book-a"]["at"] = 50.25
    plates_by_id["book-a"]["dur"] = 4.5
    plates_by_id["mission-briefing"]["at"] = 40.125
    plates_by_id["mission-briefing"]["dur"] = 5.25
    modified_manifest.write_text(json.dumps(doc))

    monkeypatch.setattr(build_prologue, "MANIFEST", modified_manifest)

    fg = build_prologue.filtergraph()
    book_window = "enable=between(t\\,50.250\\,54.750)"
    briefing_window = "enable=between(t\\,40.125\\,45.375)"

    assert briefing_window in fg, "briefing window must come from the monkeypatched manifest"
    assert book_window in fg, "book window must come from the monkeypatched manifest"
    # Order now flips: book follows briefing in production, but here book is later
    # than briefing, so the literal string for briefing should appear before book
    # because briefing at 40.125 is laid down before book at 50.25.
    assert fg.index(briefing_window) < fg.index(book_window)

    cmd = build_prologue.command(Path("day.png"), Path("night.png"))
    inputs = _input_paths(cmd)
    assert len(inputs) >= 4
    assert "plate_mission-briefing.png" in str(inputs[3])
