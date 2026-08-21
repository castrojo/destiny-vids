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
