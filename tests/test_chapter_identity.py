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

# Every act whose chapter file authors its manifest's whole plate list. Act
# II is deliberately absent: its builder contributes most of its plates, so
# its chapter file is a partial author and `sync` skips it by design.
OWNED = sorted(act for act, chap in chapter_md.discover().items()
               if chap.fields.get("owns_plates"))


def committed(act):
    chap = chapter_md.chapter(act)
    with chap.manifest_path().open(encoding="utf-8") as fh:
        return json.load(fh)[chap.plates_key]


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
    """Ids are how a note, an issue and a rendered PNG name the same pill."""
    resolved, _ = chapter_md.entries(act)
    ids = [plate["id"] for plate in resolved]
    assert ids == [plate["id"] for plate in committed(act)]
    assert len(set(ids)) == len(ids)
