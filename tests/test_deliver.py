"""tools/deliver.py — the delivery graph: master -> Prod/ -> megacut/ -> 10mb/.

Offline: fixtures are tiny text "videos" under tmp_path; nothing encodes, and
the ffprobe duration check skips itself on a file that is not a real video.
"""
import types
import json
import os
import re
import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools import deliver  # noqa: E402
from tools import footage  # noqa: E402

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
    assert social["absent"]["0"] == (
        "A standalone 10mb copy is permitted only for private draft-level "
        "review; it is not a publication deliverable.")
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
    social_stamp = wolves / "10mb" / "01-intro.mp4.source.md5"
    social_stamp.write_text(deliver.md5(masters / "intro-master.mp4") + "\n")
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
    (wolves / "megacut" / "show-v1.mp4.prod.md5").write_text(
        deliver.md5(wolves / "Prod" / deliver.CHECKSUMS) + "\n")
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
    assert findings(gather(ws), "I")["social"].state == deliver.STALE


def test_an_over_cap_social_copy_with_current_provenance_is_blocked_not_stale(ws):
    """Over the cap with a digest that matches its master is a RECIPE
    problem: re-encoding the same recipe yields the same bytes, so STALE
    there is an infinite re-encode loop under --watch. It is BLOCKED -- a
    recorded editorial decision (lower the audio rung or the height)."""
    copy = ws / "wolves" / "10mb" / "01-intro.mp4"
    copy.write_bytes(b"0" * (deliver.SOCIAL_CAP_BYTES + 1))
    f = findings(gather(ws), "I")["social"]
    assert f.state == deliver.BLOCKED
    assert f.state not in deliver.FAILING


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


def test_social_provenance_detects_a_replaced_prod_despite_newer_copy(ws):
    """Syncthing timestamps are not provenance; the source content is."""
    prod = ws / "wolves" / "Prod" / "01-intro.mp4"
    prod.write_bytes(b"intro-replacement")
    social = ws / "wolves" / "10mb" / "01-intro.mp4"
    future = 2_000_000_000
    os.utime(social, (future, future))

    finding = findings(gather(ws), "I")["social"]
    assert finding.state == deliver.STALE
    assert "source digest" in finding.detail


def test_rebuilding_an_act_schedules_every_downstream_delivery_rung(
        ws, capsys):
    """The status snapshot predates the rebuild, so descendants are explicit."""
    delivery = json.loads((ws / "delivery.json").read_text())
    source = ws / "stories.json"
    source.write_text('{"copy": "new"}')
    delivery["masters"]["I"].update({
        "sources": [str(source)],
        "source_digest": "outdated",
        "rebuild": ["echo", "rebuild-intro"],
    })
    (ws / "delivery.json").write_text(json.dumps(delivery))

    capsys.readouterr()
    assert run(ws, "build", "--dry-run") == 0
    output = capsys.readouterr().out
    for label in ("rebuild I", "link I", "megacut", "social I"):
        assert f"would {label}" in output


def test_a_missing_megacut_is_a_build_action(ws, capsys):
    (ws / "wolves" / "megacut" / "show-v1.mp4").unlink()
    assert findings(gather(ws), "")["megacut"].state == deliver.MISSING
    capsys.readouterr()
    assert run(ws, "build", "--dry-run") == 0
    assert "megacut.py" in capsys.readouterr().out


def test_missing_distribution_megacut_names_unpromoted_same_stem_master(ws):
    """A remote build can leave its archival MKV behind if MP4 promotion fails."""
    out = ws / "wolves" / "megacut" / "show-v1.mp4"
    out.unlink()
    out.with_suffix(".mkv").write_bytes(b"remote-master")

    finding = findings(gather(ws), "")["megacut"]
    assert finding.state == deliver.MISSING
    assert "show-v1.mkv" in finding.detail
    assert "unpromoted" in finding.detail


def test_megacut_provenance_detects_a_changed_prod_checksum_set(ws):
    checksums = ws / "wolves" / "Prod" / deliver.CHECKSUMS
    checksums.write_text("changed\n")

    finding = findings(gather(ws), "")["megacut"]
    assert finding.state == deliver.STALE
    assert "checksum set" in finding.detail


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
    deliver.check_sources(master, r)
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
    """Delivery freshness REPORTS. It does not gate.

    ``AGENTS.md``: "A gate may inform. It may never withhold the film... a
    tool that discovers a problem reports and proceeds." This check used to
    assert, and it was by a wide margin the most expensive thing in the repo:
    it went red on every unrelated branch, so a one-word docs change could not
    land until somebody re-rendered five acts. It ran on a machine holding no
    footage, where the question it asks -- does the owner's rendered master
    predate its inputs -- cannot be usefully answered.

    The detector is not deleted; it is kept where a person will see it.
    ``deliver.py status`` prints it per act, assembly prints ``NOTE: act ...
    is stale and seated``, and this reports through ``warnings`` so it reaches
    pytest's summary. A bare ``print`` would NOT: pytest captures stdout and
    stderr from a passing test and discards them, so moving the assertion to a
    print would have dropped the "may inform" half of the rule along with the
    gate.

    An act that DECLARES `stale_blocked_on` is exempt, and that is the whole
    point of the field: act III cannot be rebuilt by anybody until the owner
    names the roster it credits (#256), so failing here forever turned an
    honestly-recorded owner decision into a red X that blocked the merge
    queue -- 24 commits of authored work sat behind it. AGENTS.md: a gap that
    is recorded and degrades correctly is a punch-list item, not a failure.
    The act still announces itself in `status` and in megacut's
    stale-and-seated NOTE.

    A digest is a whole-file hash. It answers "did an input byte move", never
    "did the picture change", so this is a prompt to go and look at the frame
    -- never on its own a reason to re-render.
    """
    masters, _ = deliver.load_delivery(
        REPO_ROOT / "stories" / "megacut" / "delivery.json")
    stale = []
    for numeral, master in masters.items():
        sources = master.get("sources")
        if not sources or not master.get("source_digest"):
            continue
        if deliver.source_digest(sources) == master["source_digest"]:
            continue
        blocker = deliver.blocked_on(master)
        if not blocker:
            stale.append(numeral)
            continue
        assert re.match(r"^#\d+$", str(blocker)), (
            f"act {numeral}: `stale_blocked_on` must name the issue holding "
            f"the decision (e.g. '#256'), not {blocker!r} -- an unexplained "
            f"exemption is how a stale act ships quietly")
    if stale:
        warnings.warn(
            f"DELIVERY REPORT: act(s) {', '.join(stale)} have committed "
            f"inputs that no longer match the delivered master. This is a "
            f"punch-list item, not a failure: go and look at the frame, and "
            f"if the picture really moved, rebuild the act and run "
            f"`python3 tools/deliver.py publish`.",
            stacklevel=1)


def test_a_blocked_act_is_still_stale_everywhere_that_reaches_picture(tmp_path):
    """The exemption is scoped to the CI gate and nowhere else.

    `stale_blocked_on` says "nobody can fix this yet", never "pretend it is
    fresh". `stale_source_acts` is what `megacut.py` asks before it seats an
    act, so a blocked act must still be in that list -- otherwise the flag
    would quietly buy a stale act a seat in the programme, which is the exact
    failure `--allow-stale` exists to make loud.
    """
    source = tmp_path / "source.txt"
    source.write_text("current", encoding="utf-8")
    masters = {"III": {
        "sources": [str(source)],
        "source_digest": "stale0000",
        "stale_blocked_on": "#256",
    }}
    assert {"III"} <= {n for n, _ in deliver.stale_source_acts(masters)}

    report = deliver.ActReport(deliver.Act("III", "t", None))
    deliver.check_sources(masters["III"], report)
    state = {f.node: f.state for f in report.findings}["sources"]
    assert state == deliver.BLOCKED
    assert state not in deliver.FAILING


def test_publish_cannot_certify_an_act_whose_rebuild_is_blocked(tmp_path):
    """`publish --act III` must not stamp a digest for a render that did not
    happen. The mtime guard cannot catch it -- act III's inputs moved in a
    COMMIT, so they look untouched on disk -- and stamping would erase the
    only record saying the act is stale, turning its own gate green."""
    src = tmp_path / "master.mp4"
    src.write_bytes(b"x")
    inp = tmp_path / "in.txt"
    inp.write_text("moved")
    doc = {"masters": {"III": {
        "path": str(src), "sources": [str(inp)],
        "source_digest": "stale0000", "stale_blocked_on": "#256"}}}
    path = tmp_path / "delivery.json"
    path.write_text(json.dumps(doc), encoding="utf-8")

    lines = []
    deliver.record_source_digests(
        [deliver.Act("III", "t", None)],
        doc["masters"], path, log=lines.append, only=["III"])

    after = json.loads(path.read_text(encoding="utf-8"))
    assert after["masters"]["III"]["source_digest"] == "stale0000"
    assert any("blocked on #256" in ln for ln in lines), lines


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


# --- the footage rung (#229) ------------------------------------------------
#
# `sources` covers what git tracks. These cover what it cannot: media/ is
# gitignored, so an act cut from picture that was later replaced used to
# report `ok`.

def _footage_report(master, media, monkeypatch, tmp_path):
    monkeypatch.setattr(footage, "MEDIA", media)
    monkeypatch.setenv("DESTINY_FOOTAGE_CACHE", str(tmp_path / "cache.json"))
    act = deliver.Act("II", "Endless Forms", "02.mp4")
    r = deliver.ActReport(act)
    deliver.check_footage(master, r)
    return r.findings[0]


def test_footage_replaced_in_place_is_stale(tmp_path, monkeypatch):
    """The defect #229 records: the master is swapped, nothing says a word."""
    media = tmp_path / "media"
    media.mkdir()
    (media / "yt_trailers.mp4").write_bytes(b"the picture the act was cut from")
    monkeypatch.setattr(footage, "MEDIA", media)
    monkeypatch.setenv("DESTINY_FOOTAGE_CACHE", str(tmp_path / "cache.json"))
    master = {"path": "~/m.mp4", "footage": ["yt_trailers"],
              "footage_digest": footage.footage_digest(["yt_trailers"],
                                                       media_dir=media)}
    assert _footage_report(master, media, monkeypatch, tmp_path).state \
        == deliver.OK

    (media / "yt_trailers.mp4").write_bytes(b"a different upload entirely")
    f = _footage_report(master, media, monkeypatch, tmp_path)
    assert f.state == deliver.STALE
    assert "rebuild the act" in f.detail


def test_a_master_that_changed_container_still_resolves(tmp_path, monkeypatch):
    """.mp4 -> .mkv is what actually broke scripts/build_efmb.py."""
    media = tmp_path / "media"
    media.mkdir()
    (media / "yt_trailers.mkv").write_bytes(b"same bytes, new container")
    monkeypatch.setattr(footage, "MEDIA", media)
    assert footage.resolve("yt_trailers").name == "yt_trailers.mkv"
    assert footage.missing(["yt_trailers"]) == []


def test_a_similarly_named_file_is_not_the_master(tmp_path, monkeypatch):
    """`<id>.1080p-orig.mkv` sits beside the real master and is NOT it."""
    media = tmp_path / "media"
    media.mkdir()
    (media / "yt_perfume.1080p-orig.mkv").write_bytes(b"the superseded rung")
    monkeypatch.setattr(footage, "MEDIA", media)
    assert footage.resolve("yt_perfume") is None


def test_absent_footage_is_reported_not_hashed_as_present(tmp_path, monkeypatch):
    media = tmp_path / "media"
    media.mkdir()
    monkeypatch.setattr(footage, "MEDIA", media)
    monkeypatch.setenv("DESTINY_FOOTAGE_CACHE", str(tmp_path / "cache.json"))
    master = {"path": "~/m.mp4", "footage": ["yt_gone"], "footage_digest": "x"}
    f = _footage_report(master, media, monkeypatch, tmp_path)
    assert f.state == deliver.MISSING
    assert "yt_gone" in f.detail


def test_undeclared_footage_is_reported_never_assumed_fresh():
    act = deliver.Act("II", "Endless Forms", "02.mp4")
    r = deliver.ActReport(act)
    deliver.check_footage({"path": "~/m.mp4"}, r)
    assert r.findings[0].state == deliver.UNDECLARED


def test_the_digest_cache_is_keyed_on_content_not_just_mtime(tmp_path, monkeypatch):
    """A rewrite that keeps the size must still change the digest, because
    mtime_ns moves with it. The cache may be fast; it may not be wrong."""
    media = tmp_path / "media"
    media.mkdir()
    monkeypatch.setattr(footage, "MEDIA", media)
    monkeypatch.setenv("DESTINY_FOOTAGE_CACHE", str(tmp_path / "cache.json"))
    f = media / "yt_x.mp4"
    f.write_bytes(b"aaaa")
    first = footage.file_digest(f)
    assert footage.file_digest(f) == first  # cache hit
    f.write_bytes(b"bbbb")                  # same size, new content
    assert footage.file_digest(f) != first


def test_sources_only_never_touches_footage(ws, capsys, monkeypatch):
    """CI has no media/. The offline gate must stay offline."""
    def explode(*a, **k):
        raise AssertionError("--sources-only read footage")
    monkeypatch.setattr(footage, "footage_digest", explode)
    monkeypatch.setattr(footage, "missing", explode)
    rc = deliver.main([
        "status", "--sources-only",
        "--running-order", str(ws / "running-order.md"),
        "--delivery", str(ws / "delivery.json"),
    ])
    assert rc == 0
    assert "footage" not in capsys.readouterr().out


def test_a_master_older_than_its_footage_is_stale_before_any_digest(
        tmp_path, monkeypatch):
    """The #229 defect, caught with nothing recorded yet.

    Act I is the real case: its master was built 08-13 and the Into the Light
    cinematic in media/ was replaced 08-15, so it was cut from a file that is
    no longer there -- and every rung reported `ok`.
    """
    media = tmp_path / "media"
    media.mkdir()
    master_file = tmp_path / "act.mp4"
    master_file.write_bytes(b"the delivered act")
    picture = media / "yt_trailers.mp4"
    picture.write_bytes(b"a replacement upload")
    os.utime(master_file, (1, 1))          # the act is old
    os.utime(picture, (1 << 30, 1 << 30))  # its footage is newer

    monkeypatch.setattr(footage, "MEDIA", media)
    monkeypatch.setenv("DESTINY_FOOTAGE_CACHE", str(tmp_path / "cache.json"))
    act = deliver.Act("I", "intro", "01.mp4")
    r = deliver.ActReport(act)
    deliver.check_footage({"path": str(master_file),
                                "footage": ["yt_trailers"]}, r)
    assert r.findings[0].state == deliver.STALE
    assert "PREDATES" in r.findings[0].detail


def test_publish_refuses_to_stamp_footage_it_knows_is_stale(
        tmp_path, monkeypatch):
    """Recording a digest over a master that predates its picture would make
    the drift disappear, which is worse than never having recorded it."""
    media = tmp_path / "media"
    media.mkdir()
    master_file = tmp_path / "act.mp4"
    master_file.write_bytes(b"the delivered act")
    (media / "yt_trailers.mp4").write_bytes(b"a replacement upload")
    os.utime(master_file, (1, 1))
    os.utime(media / "yt_trailers.mp4", (1 << 30, 1 << 30))
    monkeypatch.setattr(footage, "MEDIA", media)
    monkeypatch.setenv("DESTINY_FOOTAGE_CACHE", str(tmp_path / "cache.json"))

    delivery = tmp_path / "delivery.json"
    delivery.write_text(json.dumps({"masters": {"I": {
        "path": str(master_file), "footage": ["yt_trailers"]}}}))
    deliver.record_source_digests(
        [deliver.Act("I", "intro", "01.mp4")],
        {}, delivery, log=lambda *a: None)
    after = json.loads(delivery.read_text())["masters"]["I"]
    assert "footage_digest" not in after, "publish laundered a stale master"


def test_every_declared_youtube_master_has_a_provenance_record():
    """Defect 1 of #229: three masters were used by the film with no record
    in videos/, so the picture was unreproducible. Offline: reads only the
    delivery map and videos/, never media/."""
    masters, _ = deliver.load_delivery(
        REPO_ROOT / "stories" / "megacut" / "delivery.json")
    unrecorded = []
    for numeral, master in masters.items():
        for video_id in master.get("footage") or []:
            # `wolves_act*` are this project's own intermediate renders, not
            # uploads; only fetched sources need a provenance record.
            if not video_id.startswith("yt_"):
                continue
            record = REPO_ROOT / "videos" / f"{video_id}.json"
            if record.exists():
                continue
            # A master that is not Destiny footage (the Perfume music video)
            # is governed by a record outside videos/, named explicitly.
            elsewhere = (master.get("footage_rights") or {}).get(video_id)
            if elsewhere and (REPO_ROOT / elsewhere).exists():
                continue
            unrecorded.append(f"{numeral}:{video_id}")
    assert not unrecorded, (
        f"declared footage with no videos/<id>.json: {', '.join(unrecorded)}. "
        f"Every fetched master needs its source URL and rights recorded.")


# --- publish must not launder staleness (the "always ships stale" defect) ---

def _stamp_ws(tmp_path, monkeypatch):
    """One act, one committed input, one master file, and a delivery map."""
    monkeypatch.setattr(deliver, "REPO_ROOT", tmp_path)
    src = tmp_path / "shotlist.json"
    src.write_text("v1")
    master = tmp_path / "master.mp4"
    master.write_bytes(b"rendered")
    old, new = 1_000_000_000, 1_000_000_100
    os.utime(master, (old, old))
    os.utime(src, (old - 10, old - 10))
    delivery = tmp_path / "delivery.json"
    delivery.write_text(json.dumps({"masters": {"I": {
        "path": str(master), "sources": ["shotlist.json"],
        "source_digest": deliver.source_digest(["shotlist.json"])}}}))
    return src, master, delivery, new


def _publish_digests(delivery, acts=None, dirty=("shotlist.json",)):
    doc = json.loads(Path(delivery).read_text())
    masters = doc["masters"]
    acts = acts or [deliver.Act(numeral="I", title="I", prod_file="01.mp4")]
    real = deliver.dirty_paths
    deliver.dirty_paths = lambda: set(dirty)
    try:
        deliver.record_source_digests(acts, masters, delivery,
                                      log=lambda *a: None,
                                      only=[a.numeral for a in acts])
    finally:
        deliver.dirty_paths = real
    return json.loads(Path(delivery).read_text())["masters"]["I"]


def test_a_digest_refresh_without_a_rebuild_never_stamps_a_build_commit(
        tmp_path, monkeypatch):
    """THE 29bb646 DEFECT: re-publishing acts whose digests moved stamped
    `built_from_commit` with the publish-time HEAD for masters that commit
    never rendered -- and the FOREIGN gate then reads green on exactly the
    master it exists to name. Only a certified rebuild may write it."""
    src, master, delivery, new = _stamp_ws(tmp_path, monkeypatch)
    src.write_text("v2")
    os.utime(src, (new, new))
    master.write_bytes(b"re-rendered")
    os.utime(master, (new + 10, new + 10))
    monkeypatch.setattr(deliver, "git_head", lambda: "f" * 40)

    after = _publish_digests(delivery)

    assert after["source_digest"] == deliver.source_digest(["shotlist.json"])
    assert "built_from_commit" not in after


def test_a_certified_rebuild_stamps_the_build_commit(tmp_path, monkeypatch):
    src, master, delivery, new = _stamp_ws(tmp_path, monkeypatch)
    monkeypatch.setattr(deliver, "git_head", lambda: "f" * 40)
    doc = json.loads(Path(delivery).read_text())
    real = deliver.dirty_paths
    deliver.dirty_paths = lambda: set()
    try:
        deliver.record_source_digests(
            [deliver.Act(numeral="I", title="I", prod_file="01.mp4")],
            doc["masters"], delivery, log=lambda *a: None,
            only=["I"], rebuilt={"I"})
    finally:
        deliver.dirty_paths = real
    after = json.loads(Path(delivery).read_text())["masters"]["I"]
    assert after["built_from_commit"] == "f" * 40


def test_publish_refuses_to_stamp_a_master_that_predates_its_inputs(
        tmp_path, monkeypatch):
    """THE DEFECT: `publish` used to stamp every act unconditionally.

    Editing an input and running `publish` without rebuilding recorded the new
    digest over an old master, so the gate went green and the next megacut
    seated a stale act. Whoever ran `publish` erased the only signal that the
    act needed re-rendering -- which is why stale programmes shipped.
    """
    src, master, delivery, new = _stamp_ws(tmp_path, monkeypatch)
    src.write_text("v2")                    # the input moves...
    os.utime(src, (new, new))               # ...after the master was written
    before = json.loads(delivery.read_text())["masters"]["I"]["source_digest"]

    after = _publish_digests(delivery)

    assert after["source_digest"] == before, (
        "publish stamped a digest over a master that was never rebuilt -- "
        "that is the staleness eraser")


def test_publish_stamps_once_the_act_is_actually_rebuilt(tmp_path, monkeypatch):
    """The guard must not become a wall: a real rebuild still records."""
    src, master, delivery, new = _stamp_ws(tmp_path, monkeypatch)
    src.write_text("v2")
    os.utime(src, (new, new))
    master.write_bytes(b"re-rendered")      # the rebuild...
    os.utime(master, (new + 10, new + 10))  # ...lands after the input

    after = _publish_digests(delivery)

    assert after["source_digest"] == deliver.source_digest(["shotlist.json"])


def test_a_master_that_predates_its_inputs_is_reported_not_silent(
        tmp_path, monkeypatch, capsys):
    src, master, delivery, new = _stamp_ws(tmp_path, monkeypatch)
    src.write_text("v2")
    os.utime(src, (new, new))
    lines = []
    doc = json.loads(delivery.read_text())
    monkeypatch.setattr(deliver, "dirty_paths", lambda: {"shotlist.json"})
    deliver.record_source_digests(
        [deliver.Act(numeral="I", title="I", prod_file="01.mp4")],
        doc["masters"], delivery, log=lines.append, only=["I"])
    assert any("rebuild the act" in ln for ln in lines), lines


def test_a_checkout_does_not_block_every_act(tmp_path, monkeypatch):
    """REGRESSION: a rebase rewrites every mtime at once.

    An mtime-only guard then reports every act as "master predates its
    inputs" and `publish` can never record again -- a wall, not a gate. Only
    files that actually differ from HEAD carry a trustworthy mtime.
    """
    src, master, delivery, new = _stamp_ws(tmp_path, monkeypatch)
    src.write_text("v2")
    os.utime(src, (new, new))          # every mtime moved, as a checkout does...
    monkeypatch.setattr(deliver, "dirty_paths", lambda: set())  # ...but nothing is edited

    assert deliver.sources_newer_than(["shotlist.json"], master) == []


def test_publish_records_only_the_acts_it_was_told_to(tmp_path, monkeypatch):
    """A rebuild of ONE act must never certify the others.

    This is the blunt guarantee behind the mtime heuristics: whatever the
    filesystem says, `publish --act VII` makes a claim about act VII and
    about nothing else.
    """
    src, master, delivery, new = _stamp_ws(tmp_path, monkeypatch)
    doc = json.loads(delivery.read_text())
    doc["masters"]["II"] = {"path": str(master), "sources": ["shotlist.json"],
                            "source_digest": "stale-on-purpose"}
    delivery.write_text(json.dumps(doc))
    src.write_text("v2")

    acts = [deliver.Act(numeral="I", title="I", prod_file="01.mp4"),
            deliver.Act(numeral="II", title="II", prod_file="02.mp4")]
    deliver.record_source_digests(acts, doc["masters"], delivery,
                                  log=lambda *a: None, only=["I"])

    after = json.loads(delivery.read_text())["masters"]
    assert after["I"]["source_digest"] == deliver.source_digest(["shotlist.json"])
    assert after["II"]["source_digest"] == "stale-on-purpose"


def test_a_blanket_publish_certifies_nothing(tmp_path, monkeypatch):
    """`publish` WRITES the digest gate, so it cannot be the thing that
    decides an act is fresh. An input that moved in a commit looks untouched
    on disk, and the mtime guard only sees dirty files -- so a publish with no
    named acts once stamped a new digest over act III, whose rebuild is
    blocked on an input that does not exist (#256), and turned its own gate
    green. With no `only`, nothing is stamped."""
    src, master, delivery, new = _stamp_ws(tmp_path, monkeypatch)
    src.write_text("v2")
    before = json.loads(delivery.read_text())["masters"]["I"]["source_digest"]
    lines = []
    doc = json.loads(delivery.read_text())
    deliver.record_source_digests(
        [deliver.Act(numeral="I", title="I", prod_file="01.mp4")],
        doc["masters"], delivery, log=lines.append)
    after = json.loads(delivery.read_text())["masters"]["I"]["source_digest"]
    assert after == before
    assert any("name the acts you rebuilt" in ln for ln in lines), lines


def test_the_copy_rung_surfaces_what_an_act_says_is_still_wrong(tmp_path):
    """An act can be perfectly fresh against its FILES and still carry copy
    the repo already knows is wrong. Act VII's manifest has said "the reveal
    still credits Laura Santamaria: the Orlin recast (#73) stays open" all
    along, while `status` reported the act `ok` -- every other rung asks
    about files, none asked what the act says about itself."""
    (tmp_path / "stories").mkdir()
    manifest = tmp_path / "stories" / "act-plates.json"
    manifest.write_text(json.dumps({
        "unresolved": ["the reveal still credits somebody who was recast"]}),
        encoding="utf-8")
    report = deliver.ActReport(deliver.Act("VII", "t", "07.mp4"))
    deliver.check_copy({"sources": ["stories/act-plates.json"]},
                       report, root=tmp_path)
    finding = {f.node: f for f in report.findings}["copy"]
    assert finding.state == deliver.UNRESOLVED
    assert "recast" in finding.detail
    # A recorded gap is a punch-list item; it must never fail the gate.
    assert deliver.UNRESOLVED not in deliver.FAILING


def test_the_copy_rung_stays_quiet_when_nothing_is_recorded(tmp_path):
    """No note when there is nothing to say -- and a source that is missing,
    unreadable or not JSON must not crash a delivery report."""
    (tmp_path / "stories").mkdir()
    (tmp_path / "stories" / "clean.json").write_text("{}", encoding="utf-8")
    (tmp_path / "stories" / "junk.json").write_text("not json", encoding="utf-8")
    report = deliver.ActReport(deliver.Act("I", "t", "01.mp4"))
    deliver.check_copy({"sources": [
        "stories/clean.json", "stories/junk.json", "stories/gone.json",
        "scripts/build.sh"]}, report, root=tmp_path)
    assert not [f for f in report.findings if f.node == "copy"]


def test_act_seven_really_does_declare_the_gap_the_owner_spotted():
    """The committed record, not a fixture: act VII is the case this rung was
    written for, and it must keep reaching the report."""
    masters, _ = deliver.load_delivery(
        REPO_ROOT / "stories" / "megacut" / "delivery.json")
    report = deliver.ActReport(deliver.Act("VII", "t", "07-europa.mp4"))
    deliver.check_copy(masters["VII"], report)
    detail = {f.node: f.detail for f in report.findings}["copy"]
    assert "Laura Santamaria" in detail


def test_a_master_built_outside_this_history_is_named_foreign(monkeypatch):
    """Prod/ is shared mutable state, so 'not stale' never meant 'mine'.

    A prologue slide committed on another agent's branch shipped in the next
    programme because every gate only ever asked whether inputs had moved.
    This is the question nobody was asking.
    """
    from tools import deliver

    act = types.SimpleNamespace(numeral="0", prod_file="00-prologue.mp4")

    # a commit this checkout has never seen
    monkeypatch.setattr(deliver, "commit_in_history", lambda c, root=None: False)
    r = deliver.ActReport(act)
    deliver.check_provenance({"built_from_commit": "d" * 40}, r)
    assert [f.state for f in r.findings] == [deliver.FOREIGN]
    assert deliver.FOREIGN in deliver.FAILING      # --check must fail on it

    # a commit that IS in history is fine
    monkeypatch.setattr(deliver, "commit_in_history", lambda c, root=None: True)
    r = deliver.ActReport(act)
    deliver.check_provenance({"built_from_commit": "d" * 40}, r)
    assert [f.state for f in r.findings] == [deliver.OK]

    # and nothing recorded is UNKNOWN, not an accusation
    r = deliver.ActReport(act)
    deliver.check_provenance({}, r)
    assert [f.state for f in r.findings] == [deliver.UNDECLARED]


def test_every_act_declares_what_picture_it_was_cut_from():
    """REGRESSION: four of nine acts could not answer #229's question.

    `footage` is the only rung that can see `media/` and the project folders,
    because git cannot -- so an act with no `footage` has nothing that would
    notice its picture being replaced under it. Acts IV, V and VII were in
    that state not because nobody typed the key, but because
    `tools/footage.py` resolved ids under `media/` alone while their picture
    lives beside their own master. Act VIII declares `[]`: it is drawn, not
    filmed, and "no picture" is an answer where "undeclared" is not.
    """
    masters, _ = deliver.load_delivery(
        REPO_ROOT / "stories" / "megacut" / "delivery.json")
    undeclared = [n for n, m in masters.items() if m.get("footage") is None]
    assert not undeclared, (
        "these acts cannot tell whether they were cut from picture that has "
        f"since been replaced: {', '.join(sorted(undeclared))}. Declare "
        "`footage` (or `[]` with a `footage_note` when the act is drawn)")


def test_an_act_with_no_footage_says_so_out_loud():
    """`[]` is a claim and needs a reason; it must not be a shrug."""
    masters, _ = deliver.load_delivery(
        REPO_ROOT / "stories" / "megacut" / "delivery.json")
    for numeral, master in masters.items():
        if master.get("footage") == []:
            assert master.get("footage_note"), (
                f"act {numeral} declares no footage but records no reason")


def test_footage_resolves_a_source_staged_beside_its_master(tmp_path):
    """REGRESSION: half the show's picture is not in `media/` at all.

    Acts IV, V and VII cut from a project directory next to their own master
    (`<project>/sources/<file>`, and Europa's `nimbatus-review/...` legs), so
    while `resolve` looked only under `media/` those acts could not declare
    `footage` -- declaring it reported MISSING forever, which is why they were
    left undeclared and unprotected instead.
    """
    project = tmp_path / "wolves-kat"
    (project / "sources").mkdir(parents=True)
    src = project / "sources" / "det0BbS_9GU.mkv"
    src.write_bytes(b"picture")

    media = tmp_path / "media"
    media.mkdir()

    assert footage.resolve("sources/det0BbS_9GU.mkv", media_dir=media) is None
    assert footage.resolve("sources/det0BbS_9GU.mkv", media_dir=media,
                           roots=[project]) == src
    assert footage.missing(["sources/det0BbS_9GU.mkv"], media_dir=media,
                           roots=[project]) == []


def test_media_still_wins_and_a_bare_id_still_tries_every_container(tmp_path):
    """The extra roots are additive: `media/` keeps its meaning and order."""
    media = tmp_path / "media"
    media.mkdir()
    (media / "yt_trailers.mkv").write_bytes(b"in media")
    other = tmp_path / "project"
    other.mkdir()
    (other / "yt_trailers.mp4").write_bytes(b"beside the master")

    assert footage.resolve("yt_trailers", media_dir=media,
                           roots=[other]).name == "yt_trailers.mkv"


def test_a_replaced_project_source_moves_the_footage_digest(tmp_path):
    """The whole point: a remaster landing in a project folder is now visible."""
    project = tmp_path / "wolves-kat"
    (project / "sources").mkdir(parents=True)
    src = project / "sources" / "det0BbS_9GU.mkv"
    src.write_bytes(b"the 1080p rung")
    media = tmp_path / "media"
    media.mkdir()

    ids = ["sources/det0BbS_9GU.mkv"]
    before = footage.footage_digest(ids, media_dir=media, roots=[project])
    src.write_bytes(b"the 4K remaster")
    after = footage.footage_digest(ids, media_dir=media, roots=[project])

    assert before != after
