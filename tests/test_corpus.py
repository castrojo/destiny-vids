"""Tests for the per-character corpus (tools/corpus.py).

The corpus is half derived and half authored, and both halves have to hold: the
derived half must never disagree with the index, and the authored half must
never be quietly dropped by a rebuild.
"""

import json
from pathlib import Path

import pytest

from tools import corpus
from tools.search import load_segments

REPO_ROOT = Path(__file__).resolve().parents[1]
SEGMENTS = str(REPO_ROOT / "segments")
CORPUS_DIR = REPO_ROOT / "corpus"

GAP = {
    "id": "example_gap",
    "need": "a beat the footage cannot cover",
    "status": "unresolved",
    "automatable": False,
    "blocked_on": "footage: not indexed",
}


@pytest.fixture(scope="module")
def segments():
    return load_segments(SEGMENTS)


def committed():
    for path in sorted(CORPUS_DIR.glob("*.json")):
        with path.open(encoding="utf-8") as fh:
            yield path, json.load(fh)


def test_every_committed_corpus_is_current():
    """A stale corpus is worse than none: it lies about what footage exists."""
    assert corpus.main(["check", "--dir", SEGMENTS,
                        "--corpus-dir", str(CORPUS_DIR)]) == 0


def test_corpus_only_cites_segments_that_exist(segments):
    known = {seg["segment_id"] for seg in segments}
    for path, record in committed():
        for shot in record["shots"]:
            assert shot["segment_id"] in known, (path.name, shot["segment_id"])


def test_corpus_finds_every_shot_the_character_is_in(segments):
    """The corpus is a pivot of the index, not a subset somebody curated."""
    for path, record in committed():
        found = corpus.character_shots(record["character"], segments)
        assert {s["segment_id"] for s in record["shots"]} == \
            {s["segment_id"] for s in found}, path.name


def test_corpus_carries_the_clean_gate_with_the_shot(segments):
    """`clean` travels with the shot so a reader never has to assume it."""
    for path, record in committed():
        assert all("clean" in shot for shot in record["shots"])
        assert record["coverage"]["clean_shots"] == \
            sum(1 for shot in record["shots"] if shot["clean"])


def test_corpus_generalises_to_another_character(segments):
    """Nothing in the tool is specific to the character it was written for."""
    built = corpus.build("osiris", SEGMENTS)
    assert built["coverage"]["shots"] == len(built["shots"]) > 0
    assert built["cast"]["person"] == "mrbobbytables"
    assert all(shot["video_id"] for shot in built["shots"])


def test_unknown_character_is_rejected():
    with pytest.raises(KeyError):
        corpus.build("gary_from_accounting", SEGMENTS)


def test_authored_gaps_survive_a_rebuild(tmp_path):
    out = tmp_path / "cayde_6.json"
    corpus.write(corpus.build("cayde_6", SEGMENTS, unresolved=[GAP]), out)
    again = corpus.build("cayde_6", SEGMENTS, unresolved=corpus.read_gaps(out))
    assert again["unresolved"] == [GAP]


def test_a_gap_must_say_what_is_missing():
    with pytest.raises(ValueError):
        corpus.validate_gaps([{"id": "x", "status": "unresolved", "automatable": True}])


def test_a_gap_must_use_a_known_status():
    with pytest.raises(ValueError):
        corpus.validate_gaps([dict(GAP, status="probably_fine")])


def test_a_gap_nobody_can_automate_must_name_its_blocker():
    """`automatable: false` with no reason is a shrug, not a record."""
    with pytest.raises(ValueError):
        corpus.validate_gaps([{"id": "x", "need": "y", "status": "unresolved",
                               "automatable": False}])


def test_committed_gaps_are_all_well_formed():
    for path, record in committed():
        corpus.validate_gaps(record["unresolved"])


def test_the_hero_corpus_records_why_the_cut_is_short():
    """The one-shot problem and the unindexed sources are written down, not lost."""
    with (CORPUS_DIR / "cayde_6.json").open(encoding="utf-8") as fh:
        record = json.load(fh)
    ids = {gap["id"] for gap in record["unresolved"]}
    assert {"sources_unindexed", "cayde_has_one_shot", "cayde_plate_anchor"} <= ids
