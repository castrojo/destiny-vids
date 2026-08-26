"""`leads.pending` — a cast request that names a PERSON but no character.

Casting names real people, and a wrong credit is not recoverable by a revert.
A request like castrojo/destiny-vids#14 (GitHub logins, the requester's
words for the figures on screen, a video that is not ingested) is therefore
RECORDED, never guessed: parked under `leads.pending`, which derivation never
reads. These tests pin the queue so the gap cannot be silently dropped — and
pin that a pending entry casts nobody, plates nothing and retrieves nothing.

wrkode was part of the #14 queue until the owner authored his plate for
act II: he is promoted to the shared `people` records (pinned in
tests/test_act2_casting.py), which partially closes #14. abangser and
robertsirc remain here.
"""

import json
from pathlib import Path

import pytest
import yaml

from tools.derive import compute_casting, load_leads

REPO_ROOT = Path(__file__).resolve().parents[1]
CASTING = yaml.safe_load(
    (REPO_ROOT / "vocab" / "casting.yaml").read_text(encoding="utf-8"))

PENDING = (CASTING.get("leads") or {}).get("pending") or {}
LEADS = load_leads()

# The people castrojo/destiny-vids#14 asked for who are STILL waiting: wrkode
# left the queue when the owner authored his plate for act II (he is in
# the shared `people` records now), and these two remain. Pinned by login so the
# request cannot be dropped in a vocab edit without this file going red.
REQUESTED = ["abangser", "robertsirc"]

# Everybody in the queue, in file order. #14 is not the only source of pending
# cast any more: the editorial pass on Seven Days to the Wolves added `inffy`,
# whom the owner cast onto the Hunter run in the Final Shape Gameplay Trailer
# and for whom no Guardian identity is authored anywhere. Pinned separately
# from REQUESTED so the #14 assertions below stay about #14.
PENDING_LOGINS = ["inffy"] + REQUESTED

# The video the request is about. Ingesting it is a licensing decision about a
# possibly-non-Bungie source, which is the owner's call — so the index must
# NOT contain it until the owner says so.
REQUESTED_VIDEO = "dOdPT9fLKEA"

# On-screen copy is authored, never invented: a pending entry must not carry
# any field a plate could render.
PLATE_FIELDS = {"plate", "label", "class", "subclass", "title", "pronouns",
                "trustee", "kind", "variant"}


def _seg(**overrides):
    base = {
        "action": ["traversal"],
        "shot_scale": "LS",
        "camera_movement": ["track"],
        "substitutability": 5,
        "subject_salience": "guardian_hero",
        "composition": ["group"],
        "content_type": "cinematic",
        "overlays": [],
        "character": [],
    }
    base.update(overrides)
    return base


def test_requested_people_are_recorded():
    """A request that is not written down is a request that gets dropped."""
    assert list(PENDING) == PENDING_LOGINS


@pytest.mark.parametrize("person", PENDING_LOGINS)
def test_every_pending_entry_is_recorded_as_blocked(person):
    """Whatever put someone in the queue, the queue's shape is the same: the
    requester's own words, and a reason an agent may not settle it alone."""
    entry = PENDING[person]
    assert entry["github"] == person
    assert entry["automatable"] is False
    assert entry["blocked_on"].strip()
    assert entry["described_as"], "the requester's own words, never a character name"


@pytest.mark.parametrize("person", REQUESTED)
def test_requested_cast_is_recorded_as_blocked(person):
    """Recorded as BLOCKED, in the requester's own words — a binding written
    down instead would credit someone for a shot nobody has seen."""
    entry = PENDING[person]
    assert entry["requested_in"] == (
        "https://github.com/castrojo/destiny-vids/issues/14")


def test_inffy_is_pending_because_no_identity_is_authored():
    """The owner cast the Hunter run onto this account, OVERRIDING their own
    proxy filename, which said "Laura". Both halves matter: the override is
    recorded so nobody credits Laura Santamaria for a shot the owner moved off
    her, and the entry stays *pending* because no Guardian identity is authored
    for inffy in the reference deck or the website's characters.json — so no
    plate copy may be written here."""
    entry = PENDING["inffy"]
    assert entry["display_name"] is None, "nobody has authored one"
    assert not PLATE_FIELDS & set(entry)
    assert "UchfadQhX7w" in entry["source_video"]
    assert "inffy" not in LEADS


@pytest.mark.parametrize("person", PENDING_LOGINS)
def test_a_pending_entry_is_not_a_binding(person):
    """`leads.pending` is a queue. Until an entry is promoted into
    `leads.values` it must cast nobody: no character, no plate, no retrieval."""
    assert person not in LEADS
    entry = PENDING[person]
    assert "character" not in entry
    assert not PLATE_FIELDS & set(entry), "plate copy is authored, never invented"
    for name in (person, entry.get("display_name") or person):
        casting = compute_casting(
            _seg(character=[{"name": name, "kind": "other"}]), LEADS)
        assert casting["role"] != "lead"
        assert casting["person"] is None


@pytest.mark.parametrize("person", REQUESTED)
def test_display_name_is_never_invented(person):
    """`display_name` is null unless the request itself named the person. The
    #14 body names nobody (its title named William Rizzo, whose plate the
    owner has since authored — see the shared `people` records), so nothing is made up."""
    assert PENDING[person]["display_name"] is None


def test_load_leads_never_returns_a_pending_entry():
    """The exclusion is explicit, not accidental: `load_leads` reads only
    `leads.values`, so derivation, search and plating never see the queue."""
    assert not (set(PENDING) & set(LEADS))


def test_pending_entries_are_not_search_phrases():
    """A pending person needs no query phrase (the queue casts nobody), and
    must not acquire one: a phrase for an unbound person would retrieve
    nothing and read as if the casting were made."""
    from tools import search
    cast_facets = {"casting.person", "casting.character"}
    targeted = {v for phrase in search.PHRASES.values()
                for facet, values in phrase if facet in cast_facets
                for v in values}
    assert not (set(REQUESTED) & targeted)
    assert "inffy" not in targeted
    assert "william_rizzo" not in targeted


def test_the_requested_video_is_not_ingested():
    """Whether dOdPT9fLKEA may be indexed at all is a licensing decision about
    a possibly-non-Bungie source — the owner's call, recorded in #14. Until
    then no video record, segment or keyframe directory may reference it."""
    for path in (REPO_ROOT / "videos").glob("*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        assert REQUESTED_VIDEO not in (record.get("youtube_url") or ""), path
        assert REQUESTED_VIDEO not in (record.get("video_id") or ""), path
    for path in (REPO_ROOT / "segments").glob("*.json"):
        assert REQUESTED_VIDEO not in path.name, path
        record = json.loads(path.read_text(encoding="utf-8"))
        assert REQUESTED_VIDEO not in (record.get("video_id") or ""), path
