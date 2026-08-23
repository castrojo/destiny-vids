"""The chapter files reproduce the manifests they took over.

This is the whole safety argument for moving an act's copy out of its plate
manifest and into ``chapters/<act>.md``. The migration claims to change WHERE
the words live and nothing else -- not a timecode, not a fade, not a field
order. A claim like that is worth exactly as much as the test that proves it,
so this asserts the strongest form: every plate the chapter file resolves to
is the plate the committed manifest already held, key order included.

If one of these fails after a copyedit, the copyedit is not wrong -- it just
means the manifest is stale and wants
``python3 tools/chapter_md.py sync <act> --write``. The failure is doing its
job either way: it is impossible for the words on screen to disagree with the
words in the chapter file without something going red.
"""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import chapter_md  # noqa: E402

# Every act whose chapter file authors the plates in its manifest. Act II is
# deliberately absent: its builder contributes most of its plates, so its
# chapter file is a partial author and `sync` skips it by design.
OWNED = sorted(act for act, chap in chapter_md.discover().items()
               if chap.fields.get("owns_plates"))


def committed(act):
    """The plates in the manifest that the chapter file is answerable for.

    A `casting` or `brief` nameplate resolves from the roster, not from the
    Markdown, so an act like VI holds both kinds in one array. The chapter
    file is asked to reproduce its own, and to leave the others alone --
    which `test_the_manifest_is_current_with_its_chapter_file` checks, since
    a dropped nameplate changes the manifest text.
    """
    chap = chapter_md.chapter(act)
    with chap.manifest_path().open(encoding="utf-8") as fh:
        plates = json.load(fh)[chap.plates_key]
    return [p for p in plates
            if p.get("copy_source") not in chapter_md.DERIVED_COPY]


@pytest.mark.parametrize("act", OWNED)
def test_the_chapter_file_resolves_to_the_committed_plates(act):
    resolved, _ = chapter_md.entries(act)
    assert resolved == committed(act)


@pytest.mark.parametrize("act", OWNED)
def test_the_plates_keep_the_field_order_the_manifest_reads_in(act):
    """A manifest is read by people too, so its columns do not shuffle."""
    resolved, _ = chapter_md.entries(act)
    assert [list(p) for p in resolved] == [list(p) for p in committed(act)]


@pytest.mark.parametrize("act", OWNED)
def test_the_manifest_is_current_with_its_chapter_file(act):
    """The manifest is an output. Committed, but an output."""
    text, _ = chapter_md.sync(act)
    assert text == chapter_md.chapter(act).manifest_path().read_text(
        encoding="utf-8")


@pytest.mark.parametrize("act", OWNED)
def test_check_reports_no_drift_for_a_migrated_act(act):
    assert chapter_md.check(act) == []


def test_at_least_one_act_is_migrated():
    """A guard against this file quietly testing nothing.

    Parametrising over a discovered list means an empty list is a green run,
    which is the failure mode where a whole migration disappears and no test
    goes red.
    """
    assert OWNED, "no act declares owns_plates -- the migration has vanished"


@pytest.mark.parametrize("act", OWNED)
def test_every_plate_keeps_the_id_the_delivered_master_refers_to(act):
    """Ids are how a note, an issue and a rendered PNG name the same pill.

    A run with no ids at all is addressed by its order instead -- act VIII's
    credit cards never had one, and minting some here would write a new field
    into a delivered record. What is checked there is that they still have
    none, so nobody starts half-identifying them.
    """
    resolved, _ = chapter_md.entries(act)
    want = committed(act)
    if any("id" not in plate for plate in want):
        assert all("id" not in plate for plate in resolved)
        assert len(resolved) == len(want)
        return
    ids = [plate["id"] for plate in resolved]
    assert ids == [plate["id"] for plate in want]
    assert len(set(ids)) == len(ids)


# ---------------------------------------------------------------------------
# Act II, the last act to migrate and the only partial author.
# ---------------------------------------------------------------------------
# It cannot join OWNED: `scripts/build_efmb_plates.py` still places its
# titles, banners, Guardian reveals and the 67-frame choice screen, and it is
# the manifest's generator. What DID move is every word anybody speaks. So
# the claim this act can make is narrower than the others' and is checked in
# its own shape: the chapter file is the sole author of act II's dialogue.

def _act_two_chats():
    chap = chapter_md.chapter("II")
    with chap.manifest_path().open(encoding="utf-8") as fh:
        plates = json.load(fh)[chap.plates_key]
    return [p for p in plates if p.get("kind") == "chat"]


def test_every_word_spoken_in_act_two_is_authored_in_its_chapter_file():
    """The guard against a pill drifting back into Python.

    Act II's dialogue lived in about ten constant tables in its generator,
    and the cost was that a copyedit meant reading code. Adding a pill back
    to one of those tables would work, and nobody would notice until the next
    person went looking for the words in the obvious place. This notices.
    """
    authored = {e["id"] for e in chapter_md.entries("II")[0]
                if e.get("kind") == "chat"}
    rendered = {p["id"] for p in _act_two_chats()}
    assert rendered - authored == set(), \
        "act II renders chat pills its chapter file does not author"
    assert authored - rendered == set(), \
        "the chapter file authors pills act II does not render"
    assert len(rendered) > 50, "act II's conversations have gone missing"


def test_act_two_pills_reproduce_the_manifest_exactly():
    """Same identity claim as the migrated acts, over the dialogue only."""
    by_id = {p["id"]: p for p in _act_two_chats()}
    for entry in chapter_md.entries("II")[0]:
        if entry.get("kind") != "chat":
            continue
        assert entry == by_id[entry["id"]]
        assert list(entry) == list(by_id[entry["id"]])
