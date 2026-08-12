"""Tests for the character corpus builder: casting subject -> shots + gaps.

The corpus is what an outline is written against, so the two things it must
never do are invent coverage that isn't there and quietly swallow footage the
clean gate rejected.
"""

import json
from pathlib import Path

import pytest

from tools import corpus
from tools.search import load_segments

REPO_ROOT = Path(__file__).resolve().parents[1]


def seg(segment_id, role, character=None, clean=True, overlays=None, **fields):
    record = {
        "segment_id": segment_id, "video_id": "yt_test",
        "start_tc": "0:00", "end_tc": "0:04", "start_sec": 0.0, "end_sec": 4.0,
        "clean": clean, "footage_tier": "cinematic", "traversal_hero": False,
        "overlays": overlays or [], "caption": "a caption",
        "shot_scale": "MS", "action": ["walk"],
        "casting": {"role": role, "character": character, "person": None,
                    "usable": True, "slots": 0},
    }
    record.update(fields)
    return record


def test_a_lead_corpus_only_holds_that_lead():
    segments = [seg("s1", "lead", "osiris"), seg("s2", "lead", "zavala"),
                seg("s3", "ensemble")]
    record = corpus.build("osiris", segments)
    assert [s["segment_id"] for s in record["shots"]] == ["s1"]


def test_the_ensemble_corpus_is_the_anonymous_guardians():
    segments = [seg("s1", "lead", "osiris"), seg("s2", "ensemble"),
                seg("s3", "ensemble")]
    record = corpus.build("ensemble", segments)
    assert [s["segment_id"] for s in record["shots"]] == ["s2", "s3"]


def test_shots_are_ordered_along_their_source():
    segments = [seg("s2", "ensemble", start_sec=9.0, end_sec=12.0),
                seg("s1", "ensemble", start_sec=1.0, end_sec=4.0)]
    record = corpus.build("ensemble", segments)
    assert [s["segment_id"] for s in record["shots"]] == ["s1", "s2"]


def test_an_unclean_shot_is_kept_and_labelled_with_what_barred_it():
    """Knowing the footage exists and why it can't be cut is the whole point."""
    segments = [seg("s1", "ensemble", clean=False, overlays=["burned_text"])]
    shot = corpus.build("ensemble", segments)["shots"][0]
    assert shot["clean"] is False
    assert shot["blocked_by"] == ["burned_text"]


def test_coverage_counts_only_clean_shots():
    segments = [seg("s1", "ensemble", action=["walk"]),
                seg("s2", "ensemble", action=["walk"], clean=False,
                    overlays=["burned_text"])]
    assert corpus.build("ensemble", segments)["coverage"]["action"] == {"walk": 1}


def test_a_value_with_only_unclean_footage_is_still_a_gap():
    """The clean gate is a gate, not a preference — barred footage isn't cover."""
    segments = [seg("s1", "ensemble", action=["walk"]),
                seg("s2", "ensemble", action=["emote"], clean=False,
                    overlays=["burned_text"])]
    gap = next(g for g in corpus.build("ensemble", segments)["gaps"]
               if g["value"] == "emote")
    assert gap["status"] == "unresolved"
    assert gap["blocked_candidates"] == [{"segment_id": "s2",
                                          "blocked_by": ["burned_text"]}]


def test_a_covered_value_is_not_reported_as_a_gap():
    segments = [seg("s1", "ensemble", action=["walk"])]
    values = {g["value"] for g in corpus.build("ensemble", segments)["gaps"]}
    assert "walk" not in values


def test_gaps_come_from_the_vocab_not_from_the_footage():
    """A gap is 'the enum says this exists and we have none of it'."""
    segments = [seg("s1", "ensemble", action=["walk"])]
    record = corpus.build("ensemble", segments)
    for axis in corpus.GAP_AXES:
        filename, key = corpus.COVERAGE_AXES[axis]
        allowed = set(corpus.vocab_values(filename, key))
        for gap in record["gaps"]:
            if gap["axis"] == axis:
                assert gap["value"] in allowed


def test_unknown_is_not_reported_as_missing_coverage():
    """`unknown` means 'not determinable', not a shot anyone could go get."""
    segments = [seg("s1", "ensemble", action=["walk"])]
    record = corpus.build("ensemble", segments)
    assert not [g for g in record["gaps"] if g["value"] in corpus.NOT_COVERAGE]


def test_an_unknown_subject_yields_an_empty_corpus_not_an_error():
    assert corpus.build("nobody", [seg("s1", "ensemble")])["shots"] == []


# --- the committed corpus ---------------------------------------------------

@pytest.fixture(scope="module")
def indexed():
    return load_segments(str(REPO_ROOT / "segments"))


def test_committed_corpus_is_in_sync_with_the_index(indexed):
    """A corpus is derived; a stale one is a lie about what footage exists."""
    corpus_dir = REPO_ROOT / "corpus"
    subjects = corpus.committed_subjects(str(corpus_dir))
    assert subjects, "no corpus files committed"
    for subject in subjects:
        current = (corpus_dir / f"{subject}.json").read_text(encoding="utf-8")
        assert current == corpus.dumps(corpus.build(subject, indexed)), (
            f"{subject} is stale; run: python3 tools/corpus.py --write")


def test_the_ensemble_corpus_records_the_dance_gap():
    """The Dance cut's premise has no clean footage; that stays on the record.

    If someone indexes a clean emote shot of a Guardian later, this test fails
    and the cut can finally be rewritten toward it.
    """
    record = json.loads((REPO_ROOT / "corpus" / "ensemble.json").read_text())
    gap = next((g for g in record["gaps"]
                if g["axis"] == "action" and g["value"] == "emote"), None)
    assert gap is not None and gap["status"] == "unresolved"


def test_check_mode_passes_on_a_fresh_corpus(capsys):
    assert corpus.main(["--check"]) == 0


def test_check_mode_fails_on_a_stale_corpus(tmp_path, capsys):
    stale = tmp_path / "ensemble.json"
    stale.write_text('{"subject": "ensemble"}\n', encoding="utf-8")
    assert corpus.main(["--check", "--corpus-dir", str(tmp_path)]) == 1
