"""tools/deliver.py — the delivery graph: master -> Prod/ -> megacut/ -> 10mb/.

Offline: fixtures are tiny text "videos" under tmp_path; nothing encodes, and
the ffprobe duration check skips itself on a file that is not a real video.
"""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools import deliver  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


# --- the committed inputs ---------------------------------------------------


def test_the_act_list_comes_from_the_real_running_order():
    """The tool must never carry its own act list: it parses the source of
    truth. If the table stops parsing, that is the failure to fix, not the
    parser."""
    acts = deliver.parse_running_order(REPO_ROOT / "docs" / "running-order.md")
    assert [a.numeral for a in acts] == ["0", "I", "II", "III", "IV", "V", "VI",
                                         "VII", "VIII"]
    # The PROLOGUE is "0" on purpose. It is a cold open in front of act I and it
    # takes no numeral, because the eight act numerals are load-bearing: giving
    # it "I" and shifting everything behind it would move every chapter marker,
    # every Prod/NN-*.mp4 name and every key in delivery.json.
    assert acts[0].numeral == "0"
    assert acts[0].prod_file == "00-prologue.mp4"
    assert acts[6].prod_file == "06-7daystothewolves.mp4"
    # Act VIII has no film (issue #51); its numeral is load-bearing.
    assert acts[-1].numeral == "VIII"
    # Act VIII HAS a film now (#51). It had none for most of the project's
    # life, which is why this used to assert the opposite.
    assert acts[-1].prod_file == "08-credits.mp4"


def test_the_delivery_map_covers_every_filmed_act_and_no_phantom_acts():
    """delivery.json is intent, not a second act list: it may not invent acts
    the running order does not have, and every act WITH a film must declare
    its master -- otherwise publish has nothing to link and the graph has a
    silent hole."""
    acts = deliver.parse_running_order(REPO_ROOT / "docs" / "running-order.md")
    masters, social = deliver.load_delivery(
        REPO_ROOT / "stories" / "megacut" / "delivery.json")
    numerals = {a.numeral for a in acts}
    assert set(masters) <= numerals, "the map names an act the order does not"
    assert set(social.get("absent", {})) <= numerals
    for act in acts:
        if act.prod_file:
            assert act.numeral in masters, f"act {act.numeral} has a film " \
                                           f"but no declared master"


# --- fixture ----------------------------------------------------------------

RUNNING_ORDER = """# The running order

| Act | Chapter | The film | State |
|---|---|---|---|
| **I** | Intro | `Prod/01-intro.mp4` — the opener | delivered |
| **II** | Song | `Prod/02-song.mp4` — the song | delivered |
| **III** | Credits | — | **not designed** — #51 |
"""

README = """# Prod

Hand-written prose the tool must preserve.

{table}

Trailing prose.
"""


@pytest.fixture
def ws(tmp_path):
    """A minimal but complete workspace: two filmed acts with linked masters,
    checksums, a megacut, one social copy, and a no-film act."""
    root = tmp_path
    masters = root / "masters"
    masters.mkdir()
    wolves = root / "wolves"
    (wolves / "Prod").mkdir(parents=True)
    (wolves / "10mb").mkdir()
    (wolves / "megacut").mkdir()

    (root / "running-order.md").write_text(RUNNING_ORDER)
    (root / "delivery.json").write_text(json.dumps({
        "masters": {
            "I": {"path": str(masters / "intro-master.mp4"), "note": ""},
            "II": {"path": str(masters / "song-master.mp4"), "note": "v2"},
        },
        "social": {"audio_bitrate": 256,
                   "absent": {"II": "too long for the cap"}},
    }))
    (root / "plan.json").write_text(json.dumps({
        "items": [{"kind": "card", "image": "x.png", "dur": 5.0}],
        "output": str(wolves / "megacut" / "show-v1.mp4"),
    }))

    (masters / "intro-master.mp4").write_bytes(b"intro-content")
    (masters / "song-master.mp4").write_bytes(b"song-content")
    os.link(masters / "intro-master.mp4", wolves / "Prod" / "01-intro.mp4")
    os.link(masters / "song-master.mp4", wolves / "Prod" / "02-song.mp4")
    (wolves / "10mb" / "01-intro.mp4").write_bytes(b"social-copy")
    (wolves / "megacut" / "show-v1.mp4").write_bytes(b"megacut")
    future = 2_000_000_000  # mtimes lie under Syncthing; fixtures pin them
    os.utime(wolves / "10mb" / "01-intro.mp4", (future, future))
    os.utime(wolves / "megacut" / "show-v1.mp4", (future, future))
    acts = deliver.parse_running_order(root / "running-order.md")
    masters, _social = deliver.load_delivery(root / "delivery.json")
    table = deliver.expected_table(acts, masters)
    (wolves / "Prod" / "README.md").write_text(README.format(table=table))
    sums = "\n".join(f"{deliver.md5(f)}  {f.name}"
                     for f in sorted((wolves / "Prod").glob("*.mp4")))
    (wolves / "Prod" / deliver.CHECKSUMS).write_text(sums + "\n")
    return root


def run(root, *argv):
    return deliver.main([
        *argv,
        "--wolves-root", str(root / "wolves"),
        "--running-order", str(root / "running-order.md"),
        "--delivery", str(root / "delivery.json"),
        "--plan", str(root / "plan.json"),
    ])


def gather(root, twin_roots=[]):
    """Hermetic gather: twin search defaults OFF ([]), so a test never walks
    the real ~/Videos. Tests about twins pass the fixture root explicitly."""
    acts = deliver.parse_running_order(root / "running-order.md")
    masters, social = deliver.load_delivery(root / "delivery.json")
    return deliver.gather(acts, masters, social, root / "wolves",
                          root / "plan.json", twin_roots=twin_roots)


def findings(reports, numeral):
    return {f.node: f for r in reports if r.act.numeral == numeral
            for f in r.findings}


# --- the chain, healthy and broken ------------------------------------------


def test_an_up_to_date_chain_passes_check(ws):
    assert run(ws, "status", "--check") == 0
    reports = gather(ws)
    assert findings(reports, "I")["link"].state == deliver.OK
    assert findings(reports, "III")["film"].state == deliver.NO_FILM
    # A recorded absence is reported but never fails the gate.
    assert findings(reports, "II")["social"].state == deliver.ABSENT_BY_DESIGN


def test_a_master_rewritten_as_a_new_inode_detaches_the_link(ws):
    """The peaks.py trim flow: the master is os.replace'd by a corrected file,
    so Prod keeps the old inode. publish is the re-link step peaks defers to.
    """
    master = ws / "masters" / "intro-master.mp4"
    (ws / "masters" / "intro-new.mp4").write_bytes(b"intro-corrected")
    os.replace(ws / "masters" / "intro-new.mp4", master)
    assert run(ws, "status", "--check") == 1
    assert findings(gather(ws), "I")["link"].state == deliver.STALE
    assert run(ws, "publish") == 0
    assert deliver.same_file(ws / "wolves" / "Prod" / "01-intro.mp4", master)
    assert run(ws, "status", "--check") == 0


def test_an_older_master_never_reverts_newer_prod_content(ws):
    """Act II on 2026-08-13: the build lived in a worktree, the declared
    master was a revision behind. Re-linking would silently revert the show.
    """
    master = ws / "masters" / "song-master.mp4"
    prod = ws / "wolves" / "Prod" / "02-song.mp4"
    (ws / "masters" / "song-old.mp4").write_bytes(b"song-older-revision")
    os.replace(ws / "masters" / "song-old.mp4", master)
    past = 1_000_000_000
    os.utime(master, (past, past))
    os.utime(prod, (past + 1, past + 1))
    f = findings(gather(ws), "II")["link"]
    assert f.state == deliver.CONFLICT
    assert "revert" in f.detail
    assert run(ws, "publish") == 0
    assert prod.read_bytes() == b"song-content", "publish must not downgrade"


def test_a_stale_checksum_is_detected_and_regenerated(ws):
    prod = ws / "wolves" / "Prod" / "01-intro.mp4"
    prod.unlink()
    (ws / "wolves" / "Prod" / "01-intro.mp4").write_bytes(b"intro-new")
    os.link(ws / "masters" / "intro-master.mp4", ws / "x")
    os.remove(ws / "x")
    # Prod content changed under a checksum file written before the change.
    f = findings(gather(ws), "I")["checksum"]
    assert f.state == deliver.STALE
    assert run(ws, "status", "--check") == 1
    run(ws, "publish")
    assert findings(gather(ws), "I")["checksum"].state == deliver.OK


def test_a_missing_social_copy_is_built_but_an_exempt_one_never_is(ws, capsys):
    (ws / "wolves" / "10mb" / "01-intro.mp4").unlink()
    # Give act II a copy requirement by removing its exemption, then missing.
    delivery = json.loads((ws / "delivery.json").read_text())
    del delivery["social"]["absent"]["II"]
    (ws / "delivery.json").write_text(json.dumps(delivery))
    assert findings(gather(ws), "I")["social"].state == deliver.MISSING
    assert findings(gather(ws), "II")["social"].state == deliver.MISSING
    capsys.readouterr()
    assert run(ws, "build", "--dry-run") == 0
    out = capsys.readouterr().out
    assert "social.py" in out and "01-intro.mp4" in out and "02-song.mp4" in out
    # Nothing was actually built.
    assert not (ws / "wolves" / "10mb" / "01-intro.mp4").exists()


def test_a_missing_megacut_is_a_build_action(ws, capsys):
    (ws / "wolves" / "megacut" / "show-v1.mp4").unlink()
    assert findings(gather(ws), "")["megacut"].state == deliver.MISSING
    capsys.readouterr()
    assert run(ws, "build", "--dry-run") == 0
    assert "megacut.py" in capsys.readouterr().out


def test_the_megacut_is_refused_while_a_link_conflicts(ws, capsys):
    """Baking a reverted act into a fresh megacut is the failure the whole
    graph exists to prevent; the megacut waits for the link to resolve."""
    (ws / "wolves" / "megacut" / "show-v1.mp4").unlink()
    master = ws / "masters" / "song-master.mp4"
    (ws / "masters" / "song-old.mp4").write_bytes(b"song-older-revision")
    os.replace(ws / "masters" / "song-old.mp4", master)
    past = 1_000_000_000
    os.utime(master, (past, past))
    os.utime(ws / "wolves" / "Prod" / "02-song.mp4", (past + 1, past + 1))
    capsys.readouterr()
    assert run(ws, "build", "--dry-run") == 0
    out = capsys.readouterr().out
    assert "REFUSED" in out and "megacut.py" not in out


def test_the_readme_table_is_regenerated_and_the_prose_survives(ws):
    # Drift the table by hand -- the historical failure, act VI naming v2
    # while the link pointed at v3.
    readme = ws / "wolves" / "Prod" / "README.md"
    text = readme.read_text()
    readme.write_text(text.replace("song-master.mp4` — v2",
                                   "a-hand-maintained-lie.mp4`"))
    assert findings(gather(ws), "")["readme"].state == deliver.STALE
    run(ws, "publish")
    text = (ws / "wolves" / "Prod" / "README.md").read_text()
    assert "Hand-written prose the tool must preserve." in text
    assert "Trailing prose." in text
    assert "a hand-maintained lie" not in text
    assert "song-master.mp4` — v2" in text
    assert "Act III has no film" in text
    assert findings(gather(ws), "")["readme"].state == deliver.OK


def test_a_checksum_line_for_a_file_that_is_not_an_act_is_stale(ws):
    with (ws / "wolves" / "Prod" / deliver.CHECKSUMS).open("a") as fh:
        fh.write(f"{'0' * 32}  09-phantom.mp4\n")
    assert findings(gather(ws), "")["checksum"].state == deliver.STALE


# --- the worktree hazard (#150): location, not mtime -------------------------


def make_worktree(ws, name="wt-feature"):
    """A directory that IS a linked git worktree: `.git` as a FILE, which is
    how git marks every checkout `git worktree add` makes (and `git worktree
    remove` deletes)."""
    wt = ws / "dv-wt" / name
    (wt / "renders").mkdir(parents=True)
    (wt / ".git").write_text(f"gitdir: {ws}/main/.git/worktrees/{name}\n")
    return wt


def test_worktree_detection_reads_git_not_the_path_string(tmp_path):
    """`dv-wt/` is our naming convention; the hazard is being a worktree. A
    `.git` file marks one, a `.git` directory marks the main checkout, and
    neither means 'not a checkout at all' (~/Videos)."""
    wt = make_worktree(tmp_path)
    main = tmp_path / "main"
    (main / ".git").mkdir(parents=True)
    elsewhere = tmp_path / "Videos"
    elsewhere.mkdir()
    assert deliver.is_worktree_path(wt / "renders" / "x.mp4")
    assert not deliver.is_worktree_path(main / "renders" / "x.mp4")
    assert not deliver.is_worktree_path(elsewhere / "x.mp4")


def test_a_worktree_master_is_ephemeral_even_intact_and_newer(ws):
    """The case that slipped through before: the declared master LIVES in a
    worktree, the link is intact, the mtime is newer -- every signal said ok
    while `git worktree remove` stood ready to delete the master. Location is
    the hazard, so this is ephemeral, never ok."""
    wt = make_worktree(ws)
    master = wt / "renders" / "song-master.mp4"
    master.write_bytes(b"song-content")
    prod = ws / "wolves" / "Prod" / "02-song.mp4"
    prod.unlink()
    os.link(master, prod)
    future = 2_000_000_000
    os.utime(master, (future, future))  # newer than Prod: mtime says "fine"
    delivery = json.loads((ws / "delivery.json").read_text())
    delivery["masters"]["II"]["path"] = str(master)
    (ws / "delivery.json").write_text(json.dumps(delivery))
    report = findings(gather(ws), "II")
    assert report["master"].state == deliver.EPHEMERAL
    assert report["link"].state == deliver.EPHEMERAL
    assert run(ws, "status", "--check") == 1


def test_a_twin_that_lives_only_in_a_worktree_is_ephemeral_not_conflict(ws):
    """Act II on 2026-08-13: the durable master was a revision behind and the
    build's only twin sat in dv-wt/feat-98-act2-overlay. It was caught as a
    conflict only because the mtimes happened to point that way; the real
    condition is that the delivered content has no durable home."""
    wt = make_worktree(ws, name="feat-98-act2-overlay")
    prod = ws / "wolves" / "Prod" / "02-song.mp4"
    # The durable master becomes an OLDER, different file...
    master = ws / "masters" / "song-master.mp4"
    (ws / "masters" / "song-old.mp4").write_bytes(b"song-older-revision")
    os.replace(ws / "masters" / "song-old.mp4", master)
    past = 1_000_000_000
    os.utime(master, (past, past))
    os.utime(prod, (past + 1, past + 1))
    # ...and Prod's content resolves only inside the worktree.
    os.link(prod, wt / "renders" / "efmb-plated.mp4")
    f = findings(gather(ws, twin_roots=[ws]), "II")["link"]
    assert f.state == deliver.EPHEMERAL
    assert "durable" in f.detail and "worktree" in f.detail


def test_a_newer_durable_master_supersedes_a_worktree_twin(ws):
    """When the durable master is NEWER, re-linking resolves the hazard by
    superseding the worktree content -- that is the ordinary stale path, not
    ephemeral: nothing worth keeping evaporates with the worktree."""
    wt = make_worktree(ws)
    prod = ws / "wolves" / "Prod" / "02-song.mp4"
    master = ws / "masters" / "song-master.mp4"
    (ws / "masters" / "song-new.mp4").write_bytes(b"song-v2-from-the-project")
    os.replace(ws / "masters" / "song-new.mp4", master)
    os.link(prod, wt / "renders" / "song-twin.mp4")
    f = findings(gather(ws, twin_roots=[ws]), "II")["link"]
    assert f.state == deliver.STALE
    assert "BEHIND" in f.detail


def test_publish_never_links_from_a_worktree(ws, capsys):
    """The refusal that makes the state structural: publish cannot 'fix' a
    link by attaching Prod to a path that evaporates."""
    wt = make_worktree(ws)
    master = wt / "renders" / "song-master.mp4"
    master.write_bytes(b"song-content")
    delivery = json.loads((ws / "delivery.json").read_text())
    delivery["masters"]["II"]["path"] = str(master)
    (ws / "delivery.json").write_text(json.dumps(delivery))
    prod = ws / "wolves" / "Prod" / "02-song.mp4"
    prod.unlink()
    capsys.readouterr()
    assert run(ws, "publish") == 0
    assert not prod.exists(), "publish linked from a worktree"
    assert "EPHEMERAL" in capsys.readouterr().out


def test_the_megacut_is_refused_while_a_link_is_ephemeral(ws, capsys):
    (ws / "wolves" / "megacut" / "show-v1.mp4").unlink()
    wt = make_worktree(ws)
    master = wt / "renders" / "song-master.mp4"
    master.write_bytes(b"song-content")
    delivery = json.loads((ws / "delivery.json").read_text())
    delivery["masters"]["II"]["path"] = str(master)
    (ws / "delivery.json").write_text(json.dumps(delivery))
    capsys.readouterr()
    assert run(ws, "build", "--dry-run") == 0
    out = capsys.readouterr().out
    assert "REFUSED" in out and "megacut.py" not in out


def test_an_absent_workspace_is_a_report_not_a_crash(tmp_path, capsys):
    """CI runners have no ~/Videos; the suite must stay green there."""
    rc = deliver.main(["status", "--wolves-root", str(tmp_path / "nope")])
    assert rc == 0
    assert "absent" in capsys.readouterr().out
    # ...but a GATE fails closed: a check that cannot see its workspace
    # proves nothing.
    assert deliver.main(["status", "--check",
                         "--wolves-root", str(tmp_path / "nope")]) == 1


# --- the real workspace, as a report ----------------------------------------


@pytest.mark.skipif(not deliver.DEFAULT_WOLVES.exists(),
                    reason="no ~/Videos/Wolves on this machine")
def test_the_real_workspace_reports_without_failing(capsys):
    """status is wired into the suite as a REPORT, never a gate: a stale
    deliverable is a punch-list item, and the owner's ~/Videos being mid-edit
    must not fail the tests. --check is the gate, and nothing here uses it.
    """
    rc = deliver.main(["status"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "delivery status" in out
    # The eight acts of the running order all appear, VIII included.
    for numeral in ("I", "II", "III", "IV", "V", "VI", "VII", "VIII"):
        assert f"\n{numeral:<4}" in out


# --- the rung before the master: inputs -> master ---------------------------


def test_a_digest_is_content_not_mtime(tmp_path, monkeypatch):
    """These inputs come out of git, where every mtime is checkout time.

    An mtime-based check calls every act stale on a fresh clone; a content
    hash survives a clone, a rebase and a Syncthing round trip.
    """
    monkeypatch.setattr(deliver, "REPO_ROOT", tmp_path)
    f = tmp_path / "a.json"
    f.write_text("one")
    first = deliver.source_digest(["a.json"])
    os.utime(f, (0, 0))
    assert deliver.source_digest(["a.json"]) == first, "mtime must not count"
    f.write_text("two")
    assert deliver.source_digest(["a.json"]) != first, "content must count"


def test_a_directory_input_hashes_every_file_under_it(tmp_path, monkeypatch):
    # A dialogue record is a directory; a new line in it must register.
    monkeypatch.setattr(deliver, "REPO_ROOT", tmp_path)
    d = tmp_path / "dialogue" / "vid"
    d.mkdir(parents=True)
    (d / "dialogue.json").write_text("{}")
    before = deliver.source_digest(["dialogue/vid"])
    (d / "DIALOGUE.md").write_text("[Kat] Fine I'll fix your shit too")
    assert deliver.source_digest(["dialogue/vid"]) != before


def test_a_renamed_input_is_drift_not_a_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(deliver, "REPO_ROOT", tmp_path)
    assert deliver.source_digest(["gone.json"])  # absent hashes, never raises


def _report(master):
    act = deliver.Act("VI", "7 Days to the Wolves", "06.mp4")
    r = deliver.ActReport(act)
    deliver.check_sources(act, master, r)
    return r.findings[0]


def test_inputs_that_moved_since_the_render_are_stale(tmp_path, monkeypatch):
    monkeypatch.setattr(deliver, "REPO_ROOT", tmp_path)
    (tmp_path / "shotlist.json").write_text("v1")
    master = {"path": "~/m.mp4", "sources": ["shotlist.json"],
              "source_digest": deliver.source_digest(["shotlist.json"])}
    assert _report(master).state == deliver.OK
    (tmp_path / "shotlist.json").write_text("v2")
    f = _report(master)
    assert f.state == deliver.STALE
    assert "rebuild the act" in f.detail


def test_an_act_with_no_committed_inputs_says_so(tmp_path, monkeypatch):
    """Acts IV and V are cut outside the repo, so there is nothing to watch.

    That is a finding, not a configuration: it is precisely why the Kat/Nat
    dialogue round (#118) had nowhere to land.
    """
    monkeypatch.setattr(deliver, "REPO_ROOT", tmp_path)
    f = _report({"path": "~/m.mp4", "sources": [], "sources_note": "NOT REPO-DRIVEN"})
    assert f.state == deliver.ABSENT_BY_DESIGN
    assert "NOT REPO-DRIVEN" in f.detail


def test_undeclared_inputs_are_never_mistaken_for_fresh(tmp_path, monkeypatch):
    monkeypatch.setattr(deliver, "REPO_ROOT", tmp_path)
    assert _report({"path": "~/m.mp4"}).state == deliver.UNDECLARED


def test_declared_but_unrecorded_is_undeclared_not_ok(tmp_path, monkeypatch):
    # A digest nobody stamped proves nothing; publish is what stamps it.
    monkeypatch.setattr(deliver, "REPO_ROOT", tmp_path)
    (tmp_path / "s.json").write_text("x")
    assert _report({"path": "~/m.mp4",
                    "sources": ["s.json"]}).state == deliver.UNDECLARED


def test_every_declared_source_actually_exists():
    """A path typo would silently hash as 'absent' and then look stable."""
    masters, _ = deliver.load_delivery(
        REPO_ROOT / "stories" / "megacut" / "delivery.json")
    for numeral, master in masters.items():
        for rel in master.get("sources") or []:
            assert (REPO_ROOT / rel).exists(), \
                f"act {numeral} declares a source that does not exist: {rel}"


def test_an_act_with_no_committed_inputs_carries_its_reason():
    masters, _ = deliver.load_delivery(
        REPO_ROOT / "stories" / "megacut" / "delivery.json")
    for numeral, master in masters.items():
        if master.get("sources") == []:
            assert master.get("sources_note"), \
                f"act {numeral} declares no inputs and does not say why"


def test_the_recorded_digest_matches_what_is_committed():
    """The gate CI runs. If this fails, an act's inputs moved and nobody
    re-rendered it -- rebuild the act and `deliver.py publish`."""
    masters, _ = deliver.load_delivery(
        REPO_ROOT / "stories" / "megacut" / "delivery.json")
    stale = []
    for numeral, master in masters.items():
        sources = master.get("sources")
        if not sources or not master.get("source_digest"):
            continue
        if deliver.source_digest(sources) != master["source_digest"]:
            stale.append(numeral)
    assert not stale, (
        f"act(s) {', '.join(stale)}: committed inputs no longer match the "
        f"delivered master. Rebuild, then `python3 tools/deliver.py publish`.")


def test_the_watcher_flushes_so_its_log_is_readable_while_it_runs(
        ws, monkeypatch, capsys):
    """A watcher is run with its output redirected. Python block-buffers there,
    so an unflushed loop reads as an empty log for hours and looks dead."""
    flushed = []
    monkeypatch.setattr(sys.stdout, "flush", lambda: flushed.append(1))
    acts = deliver.parse_running_order(ws / "running-order.md")
    masters, social = deliver.load_delivery(ws / "delivery.json")
    deliver.watch(acts, masters, social, ws / "wolves", ws / "plan.json",
                  interval=0.01, dry_run=True, once=True)
    assert flushed, "the watch loop never flushed stdout"
