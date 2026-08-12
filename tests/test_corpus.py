"""The character corpus must be a faithful, regenerable view of the index.

Two failure modes are worth a test each: a corpus that drifts from `segments/`
sends an outline at footage that is not there, and a corpus that reports a
guessed binding credits a real person for a shot they are not in.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.corpus import build_corpus, build_unresolved, load_pending, load_segments
from tools.derive import compute_casting, load_leads

REPO_ROOT = Path(__file__).resolve().parents[1]
LEADS = load_leads()
PENDING = load_pending()
SEGMENTS = load_segments()
CORPUS = json.loads((REPO_ROOT / "corpus" / "characters.json").read_text(encoding="utf-8"))

# The request this corpus was first built to answer, pinned so it cannot be
# quietly dropped: three people named in an issue, none of them bound yet.
REQUESTED = ["wrkode", "abangser", "robertsirc"]


def _seg(**overrides):
    base = {
        "segment_id": "seg_test_0000-0001",
        "video_id": "yt_test",
        "start_sec": 0.0,
        "end_sec": 4.0,
        "start_tc": "0:00",
        "end_tc": "0:04",
        "shot_scale": "LS",
        "composition": ["single"],
        "camera_movement": ["static"],
        "subject_salience": "guardian_hero",
        "content_type": "cinematic",
        "action": ["idle"],
        "mood": [],
        "register": 0,
        "overlays": [],
        "character": [],
        "caption": "a test shot",
    }
    base.update(overrides)
    return base


def _build(segments):
    return build_corpus(segments, LEADS, PENDING)


# --- the committed corpus tracks the index ----------------------------------

def test_corpus_is_not_stale():
    result = subprocess.run(
        [sys.executable, "tools/corpus.py", "--check"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"{result.stdout}{result.stderr}\nRun: python3 tools/corpus.py --write"
    )


def test_every_indexed_character_appears_in_the_corpus():
    """A character the index knows about and the corpus does not is footage
    nobody will find."""
    indexed = {c["name"] for s in SEGMENTS for c in (s.get("character") or [])}
    covered = {n for entry in CORPUS["characters"] for n in entry["names_in_index"]}
    assert indexed == covered


@pytest.mark.parametrize("entry", CORPUS["characters"], ids=lambda e: e["character"])
def test_shot_counts_match_a_direct_scan(entry):
    names = set(entry["names_in_index"])
    expected = [s for s in SEGMENTS
                if names & {c["name"] for c in (s.get("character") or [])}]
    assert entry["totals"]["shots"] == len(expected)
    assert {r["segment_id"] for r in entry["shots"]} == {s["segment_id"] for s in expected}


def test_a_two_hander_is_filed_under_both_characters():
    """A record's stored `casting` names only the first character matched, so
    the corpus has to walk the whole `character` list or Sagira loses every
    shot she shares with Osiris."""
    both = _seg(character=[{"name": "Osiris", "kind": "guardian_npc"},
                           {"name": "Sagira", "kind": "other"}])
    corpus = _build([both])
    assert {e["character"] for e in corpus["characters"]} == {"osiris", "sagira"}


# --- clean is never inherited, only derived ---------------------------------

def test_a_lying_clean_field_does_not_survive_into_the_corpus():
    """`clean` is derived by tools/derive.py. A record that claims clean while
    carrying burned-in text is a bug, and the corpus must not launder it."""
    lie = _seg(overlays=["burned_text"], clean=True,
               character=[{"name": "Zavala", "kind": "vanguard"}])
    row = _build([lie])["characters"][0]["shots"][0]
    assert row["clean"] is False


def test_untagged_overlays_read_as_unclean():
    segment = _seg(character=[{"name": "Zavala", "kind": "vanguard"}])
    segment.pop("overlays")
    entry = _build([segment])["characters"][0]
    assert entry["shots"][0]["clean"] is False
    assert entry["totals"]["clean"] == 0
    assert entry["totals"]["clean_seconds"] == 0


def test_a_constrained_binding_reports_its_failed_shots():
    """Saladin's binding is far + helmeted only. A face-clear close-up of him is
    in the index but is not coverage, and the corpus has to say so."""
    tight = _seg(shot_scale="CU", identity_visibility="face_clear",
                 character=[{"name": "Lord Saladin", "kind": "guardian_npc"}])
    entry = _build([tight])["characters"][0]
    assert entry["shots"][0]["usable"] is False
    assert entry["shots"][0]["constraints_failed"] == ["require_far", "require_helmet"]
    assert entry["totals"]["usable"] == 0


# --- gaps -------------------------------------------------------------------

def test_uncast_and_unindexed_leads_are_reported_as_gaps():
    gaps = {(g["kind"], g["id"]) for g in CORPUS["unresolved"]}
    assert ("uncast_lead", "ikora_rey") in gaps, "a character with footage and no person"
    assert ("unindexed_lead", "saladin") in gaps, "a binding with no footage"
    assert ("unbound_character", "the_traveler") in gaps, "a name with no binding"


def test_no_character_is_both_covered_and_unindexed():
    covered = {e["character"] for e in CORPUS["characters"]}
    unindexed = {g["id"] for g in CORPUS["unresolved"] if g["kind"] == "unindexed_lead"}
    assert covered & unindexed == set()


# --- the pending queue casts nobody -----------------------------------------

@pytest.mark.parametrize("person", REQUESTED)
def test_requested_cast_is_recorded_as_blocked(person):
    """A request that is not written down is a request that gets dropped, and a
    request that is written down as a binding credits someone for a shot nobody
    has seen. It is recorded, and recorded as blocked."""
    entry = PENDING[person]
    assert entry["automatable"] is False
    assert entry["blocked_on"].strip()
    assert entry["described_as"], "the requester's own words, never a character name"
    gap = next(g for g in CORPUS["unresolved"]
               if g["kind"] == "pending_binding" and g["id"] == person)
    assert gap["automatable"] is False and gap["blocked_on"]


@pytest.mark.parametrize("person", REQUESTED)
def test_a_pending_entry_is_not_a_binding(person):
    """`leads.pending` is a queue. Until an entry is promoted into
    `leads.values` it must cast nobody: no character, no plate, no retrieval."""
    assert person not in LEADS
    entry = PENDING[person]
    assert "character" not in entry and "plate" not in entry
    for name in (person, entry.get("display_name") or person):
        casting = compute_casting(_seg(character=[{"name": name, "kind": "other"}]), LEADS)
        assert casting["role"] != "lead"
        assert casting["person"] is None


def test_pending_entries_survive_a_rebuild():
    """Whatever else changes, the queue is carried into the corpus verbatim."""
    gaps = build_unresolved([], LEADS, PENDING)
    pending = [g for g in gaps if g["kind"] == "pending_binding"]
    assert [g["id"] for g in pending] == list(PENDING)
