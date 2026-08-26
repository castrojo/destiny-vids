import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_prologue


def _load_manifest():
    return json.loads(build_prologue.MANIFEST.read_text())


def test_the_briefing_is_unseated_but_its_copy_is_not_lost():
    """Owner, 2026-08-23: "get rid of that thanks for volunteering slide",
    "I will put it somewhere else".

    Unseated is not cancelled. The card must be off the prologue's timeline AND
    off its picture -- but the words are authored, so re-seating it later has
    to be a move rather than a rewrite. The parked copy lives in the chapter
    file; this pins that it is still there, verbatim, and still findable.
    """
    doc = _load_manifest()
    by_id = {p["id"]: p for p in doc["plates"]}
    assert "mission-briefing" not in by_id, "the card is off the prologue"
    assert "plate_mission-briefing.png" not in build_prologue.filtergraph()

    parked = (build_prologue.REPO_ROOT / "chapters" / "0-prologue.md").read_text()
    for line in ("PROJECT BLUEFIN MISSION BRIEFING",
                 "Thanks for Volunteering",
                 "Tophee Protocol Quick Insertion // ACTIVATED",
                 "Agones Cluster // Cycling",
                 "Mechaphippy Deployment // UNAUTHORIZED"):
        assert line in parked, f"parked copy lost the line {line!r}"

    assert any("unseated from the prologue" in u.lower()
               for u in doc["unresolved"]), "the unseating is unrecorded"


def test_book_a_sits_on_the_book_not_the_terrarium():
    """book-a is the seat the owner authored before #321 displaced it.

    The briefing card pushed it to 34.0 to make room; once the briefing was
    unseated, 34.0 was no longer the Origin of Species page the box is written
    against but the library/terrarium shot that follows the ~33.5 dissolve.
    The owner called that a severe regression on 2026-08-23, so it is back at
    26.9 -- restored to its previous value rather than re-derived, and verified
    on frame. 26.9 + 6.74 = 33.64, inside the book shot that opens at the
    24.875 cut.
    """
    assert _load_plate("book-a")["at"] == 26.9


def _load_plate(id_):
    doc = _load_manifest()
    return {p["id"]: p for p in doc["plates"]}[id_]


def _input_paths(cmd):
    return [cmd[i + 1] for i, arg in enumerate(cmd) if arg == "-i"]


def test_filtergraph_reads_manifest_once_and_uses_changed_timing(tmp_path, monkeypatch):
    """A monkeypatched MANIFEST with a different book time drives the graph.

    This fails if filtergraph() ever falls back to the hard-coded production
    number (book 26.9-33.640) instead of reading the file.
    """
    modified_manifest = tmp_path / "modified-prologue-plates.json"
    doc = _load_manifest()
    plates_by_id = {p["id"]: p for p in doc["plates"]}
    plates_by_id["book-a"]["at"] = 50.25
    plates_by_id["book-a"]["dur"] = 4.5
    modified_manifest.write_text(json.dumps(doc))

    monkeypatch.setattr(build_prologue, "MANIFEST", modified_manifest)

    fg = build_prologue.filtergraph()
    assert "enable=between(t\\,50.250\\,54.750)" in fg, \
        "the book window must come from the monkeypatched manifest"
    assert "enable=between(t\\,34.000\\,40.740)" not in fg

    # The suite is offline: no ffmpeg is installed on the CI runner, and
    # command() prefixes the argv with find_ffmpeg(). Stub it so this test
    # stays about the manifest-derived timing, which is what it pins.
    monkeypatch.setattr(build_prologue, "find_ffmpeg", lambda: ["ffmpeg"])
    cmd = build_prologue.command(Path("day.png"), Path("night.png"))
    inputs = _input_paths(cmd)
    assert "plate_book-a.png" in str(inputs[3])
    assert not any("mission-briefing" in str(i) for i in inputs)


def test_the_cluster_uploads_carry_every_card_the_filtergraph_overlays(monkeypatch):
    """A plate the argv reads but the farm never stages is a card the remote
    encode cannot find. `mission-briefing` was added to the filtergraph without
    being added to `inputs=`, and the cluster leg failed on it."""
    sent = {}
    monkeypatch.setattr(build_prologue.farm, "cluster_available",
                        lambda: (True, ""))
    monkeypatch.setattr(build_prologue.farm, "run_ffmpeg_on_cluster",
                        lambda argv, **kw: sent.update(kw))
    monkeypatch.setattr(build_prologue, "find_ffmpeg", lambda: ["ffmpeg"])

    argv = build_prologue.command(Path("day.png"), Path("night.png"))
    assert build_prologue.encode(argv, Path("day.png"), Path("night.png")) == "cluster"

    staged = {Path(p).name for p in sent["inputs"]}
    for tok, nxt in zip(argv, argv[1:]):
        if tok == "-i" and nxt.endswith(".png"):
            assert Path(nxt).name in staged, f"{nxt} is read but never staged"


def test_a_failed_cluster_encode_stops_with_the_reason_and_runs_nothing_locally(monkeypatch):
    """Owner ruling, 2026-08-25 (c975ceb): local ffmpeg execution is
    prohibited. A farm that fails mid-encode is NOT a fallback -- the build
    stops with the cluster's reason, and nothing runs on this host."""
    def boom(argv, **kw):
        raise build_prologue.farm.FarmError("workflow Failed")

    monkeypatch.setattr(build_prologue.farm, "cluster_available",
                        lambda: (True, ""))
    monkeypatch.setattr(build_prologue.farm, "run_ffmpeg_on_cluster", boom)
    monkeypatch.setattr(build_prologue.subprocess, "run",
                        lambda *a, **kw: pytest.fail("a local encode ran"))
    monkeypatch.setattr(build_prologue.farm, "run_capped_local",
                        lambda *a, **kw: pytest.fail("the local fallback ran"))

    with pytest.raises(build_prologue.farm.FarmError, match="workflow Failed"):
        build_prologue.encode(["ffmpeg", "-i", "x"], Path("d.png"), Path("n.png"))


def test_an_unreachable_cluster_stops_with_the_reason_too(monkeypatch):
    """The other outage shape: no cluster at all. Same contract -- FarmError
    naming why, and no local execution."""
    monkeypatch.setattr(build_prologue.farm, "cluster_available",
                        lambda: (False, "kubectl not on PATH"))
    monkeypatch.setattr(build_prologue.subprocess, "run",
                        lambda *a, **kw: pytest.fail("a local encode ran"))

    with pytest.raises(build_prologue.farm.FarmError,
                       match="kubectl not on PATH"):
        build_prologue.encode(["ffmpeg", "-i", "x"], Path("d.png"), Path("n.png"))


def test_every_stream_the_filtergraph_reads_has_an_input_behind_it(monkeypatch):
    """ffmpeg numbers inputs by position, so removing one silently re-points
    every later `[N:v]` at the wrong file -- or, as here, at no file at all.
    Dropping the briefing card left `day` and `night` reading [5] and [6] of a
    six-input command, and the encode died with exit 234 rather than saying so.
    """
    import re

    monkeypatch.setattr(build_prologue, "find_ffmpeg", lambda: ["ffmpeg"])
    cmd = build_prologue.command(Path("day.png"), Path("night.png"))
    n_inputs = len(_input_paths(cmd))

    read = {int(m) for m in re.findall(r"\[(\d+):[va]\]",
                                       build_prologue.filtergraph())}
    assert read, "the graph reads no inputs at all"
    assert max(read) < n_inputs, (
        f"the graph reads input [{max(read)}] but only {n_inputs} are passed")
    assert read >= set(range(n_inputs)), (
        f"inputs {sorted(set(range(n_inputs)) - read)} are passed but never read")
