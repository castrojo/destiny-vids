import json
import sys
from pathlib import Path

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


def test_book_a_keeps_the_seat_the_owner_confirmed():
    """Dropping the briefing frees 26.9 again, but book-a does not go back to
    it. The 34.0 seat is an authored beat the owner re-confirmed on 2026-08-22,
    and undoing one needs its own yes (AGENTS.md)."""
    assert _load_plate("book-a")["at"] == 34.0


def _load_plate(id_):
    doc = _load_manifest()
    return {p["id"]: p for p in doc["plates"]}[id_]


def _input_paths(cmd):
    return [cmd[i + 1] for i, arg in enumerate(cmd) if arg == "-i"]


def test_filtergraph_reads_manifest_once_and_uses_changed_timing(tmp_path, monkeypatch):
    """A monkeypatched MANIFEST with a different book time drives the graph.

    This fails if filtergraph() ever falls back to the hard-coded production
    number (book 34.0-40.740) instead of reading the file.
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


def test_a_failed_cluster_encode_falls_back_instead_of_blocking_the_release(monkeypatch):
    """AGENTS.md: nothing blocks a release. The farm going down is a reason to
    say so on stderr and encode here, never a reason to hand back no picture."""
    def boom(argv, **kw):
        raise build_prologue.farm.FarmError("workflow Failed")

    ran = []
    monkeypatch.setattr(build_prologue.farm, "cluster_available",
                        lambda: (True, ""))
    monkeypatch.setattr(build_prologue.farm, "run_ffmpeg_on_cluster", boom)
    monkeypatch.setattr(build_prologue.subprocess, "run",
                        lambda argv, **kw: ran.append(argv))

    where = build_prologue.encode(["ffmpeg", "-i", "x"], Path("d.png"), Path("n.png"))
    assert where == "local"
    assert ran == [["ffmpeg", "-i", "x"]], "the fallback runs the identical argv"


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
