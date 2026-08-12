"""Consistency check: tools/derive.py must re-derive EXACTLY the derived values
stored in every annotated example record (examples/*.json), plus targeted unit
tests for the rule boundaries."""

import json
from pathlib import Path

import pytest

from tools.derive import (
    compute_casting,
    compute_clean,
    compute_footage_tier,
    compute_slots,
    compute_traversal_hero,
    derive_all,
    load_leads,
    snake_case,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
LEADS = load_leads()

EXAMPLE_SEGMENTS = []
for _path in sorted((REPO_ROOT / "examples").glob("*.json")):
    _data = json.loads(_path.read_text(encoding="utf-8"))
    if "segment_id" in _data:
        EXAMPLE_SEGMENTS.append((_path.name, _data))

assert EXAMPLE_SEGMENTS, "no example segment records found"


@pytest.mark.parametrize("name,segment", EXAMPLE_SEGMENTS, ids=[n for n, _ in EXAMPLE_SEGMENTS])
def test_examples_round_trip(name, segment):
    """Every stored derived value matches a fresh derivation."""
    derived = derive_all(segment, LEADS)
    for field, value in derived.items():
        assert segment[field] == value, field


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


# --- clean: the primary gate ------------------------------------------------

@pytest.mark.parametrize("overlays,expected", [
    ([], True),
    (["none"], True),
    (["letterbox"], True),          # croppable, so only a warning
    (["hud"], False),
    (["nameplates"], False),
    (["burned_text"], False),
    (["talking_head"], False),
    (["letterbox", "hud"], False),
])
def test_clean_gate(overlays, expected):
    assert compute_clean(_seg(overlays=overlays)) is expected


def test_clean_requires_positive_evidence():
    """An UNTAGGED shot is not clean. Guessing clean is how a HUD reaches the cut."""
    seg = _seg()
    del seg["overlays"]
    assert compute_clean(seg) is False


# --- footage_tier: gameplay is kept, not dropped ----------------------------

@pytest.mark.parametrize("content_type,expected", [
    ("cinematic", "cinematic"),
    ("cutscene", "cinematic"),
    ("gameplay", "gameplay"),
    ("trailer", "mixed"),
    ("UNKNOWN", "mixed"),
    (None, "mixed"),
])
def test_footage_tier(content_type, expected):
    assert compute_footage_tier(_seg(content_type=content_type)) == expected


def test_gameplay_can_be_clean():
    """Tier and cleanliness are independent: HUD-free gameplay is usable."""
    seg = _seg(content_type="gameplay", overlays=[])
    assert compute_footage_tier(seg) == "gameplay"
    assert compute_clean(seg) is True


def test_cinematic_can_be_unclean():
    """...and a pre-rendered cinematic with a burned-in card is not."""
    seg = _seg(content_type="cinematic", overlays=["burned_text"])
    assert compute_footage_tier(seg) == "cinematic"
    assert compute_clean(seg) is False


# --- traversal_hero ---------------------------------------------------------

_TRAVERSAL_CASES = (
    [({}, True)]
    + [({"shot_scale": s}, True) for s in ("ELS", "MLS", "MS")]
    + [({"shot_scale": s}, False) for s in ("MCU", "CU", "ECU", "INSERT", "UNKNOWN")]
    + [
        ({"action": ["combat"]}, False),
        ({"action": []}, False),
        ({"camera_movement": ["handheld_shaky"]}, False),
        ({"camera_movement": ["track", "handheld_shaky"]}, False),
        ({"camera_movement": []}, True),
        # Anonymity no longer gates traversal: a recognizable Guardian sprinting
        # across a bridge is still a hero traversal.
        ({"substitutability": 0}, True),
    ]
)


@pytest.mark.parametrize("overrides,expected", _TRAVERSAL_CASES)
def test_traversal_hero_boundaries(overrides, expected):
    assert compute_traversal_hero(_seg(**overrides)) is expected


# --- casting: leads ---------------------------------------------------------

def test_lead_direct_match():
    seg = _seg(substitutability=1, character=[{"name": "Elsie Bray", "kind": "guardian_npc"}])
    assert compute_casting(seg, LEADS) == {
        "role": "lead", "character": "elsie_bray", "person": "laura_santamaria",
        "usable": True, "constraints_failed": [], "slots": 0,
    }


@pytest.mark.parametrize("alias,expected", [
    ("elsie_gray", "elsie_bray"),
    ("The Exo Stranger", "elsie_bray"),
    ("Commander Zavala", "zavala"),
    ("cayde", "cayde_6"),
    ("Lord Saladin", "saladin"),
    ("Ana Bray", "anna_bray"),
    ("Variks the Loyal", "variks"),
    ("saint", "saint_14"),
    ("Queen Mara Sov", "mara_sov"),
])
def test_lead_aka_normalizes(alias, expected):
    seg = _seg(character=[{"name": alias, "kind": "guardian_npc"}])
    assert compute_casting(seg, LEADS)["character"] == expected


@pytest.mark.parametrize("shot_scale,identity", [
    ("CU", "face_clear"), ("ECU", "face_clear"), ("LS", "face_obscured"),
])
def test_unconstrained_lead_is_usable_at_any_scale(shot_scale, identity):
    """Most bindings name a role rather than matching a lookalike, so framing is
    irrelevant — a face-clear Elsie close-up is still Elsie."""
    seg = _seg(character=[{"name": "Elsie Bray", "kind": "guardian_npc"}],
               shot_scale=shot_scale, identity_visibility=identity, substitutability=0)
    got = compute_casting(seg, LEADS)
    assert got["usable"] is True and got["constraints_failed"] == []


def test_constrained_lead_saladin_far_and_helmeted():
    """jeefy plays the Iron Lord but does not resemble Saladin, so the framing has
    to do the work: far + helmeted is usable, anything tighter or face-clear is
    not, and the reason is named rather than silently dropped."""
    far = _seg(character=[{"name": "Lord Saladin", "kind": "guardian_npc"}],
               shot_scale="LS", identity_visibility="face_obscured")
    got = compute_casting(far, LEADS)
    assert got["person"] == "jeefy"
    assert got["usable"] is True and got["constraints_failed"] == []

    tight = _seg(character=[{"name": "Lord Saladin", "kind": "guardian_npc"}],
                 shot_scale="MCU", identity_visibility="face_obscured")
    got = compute_casting(tight, LEADS)
    assert got["usable"] is False and got["constraints_failed"] == ["require_far"]

    face = _seg(character=[{"name": "Lord Saladin", "kind": "guardian_npc"}],
                shot_scale="LS", identity_visibility="face_clear")
    got = compute_casting(face, LEADS)
    assert got["usable"] is False and got["constraints_failed"] == ["require_helmet"]

    both = _seg(character=[{"name": "Lord Saladin", "kind": "guardian_npc"}],
                shot_scale="CU", identity_visibility="face_clear")
    got = compute_casting(both, LEADS)
    assert got["constraints_failed"] == ["require_far", "require_helmet"]


@pytest.mark.parametrize("scale", ["ELS", "LS", "MLS", "MS"])
def test_far_scales_satisfy_require_far(scale):
    seg = _seg(character=[{"name": "Lord Saladin", "kind": "guardian_npc"}],
               shot_scale=scale, identity_visibility="face_obscured")
    assert compute_casting(seg, LEADS)["usable"] is True


@pytest.mark.parametrize("visibility", ["face_obscured", "back_only", "silhouette", "none"])
def test_concealed_visibilities_satisfy_require_helmet(visibility):
    seg = _seg(character=[{"name": "Lord Saladin", "kind": "guardian_npc"}],
               shot_scale="LS", identity_visibility=visibility)
    assert compute_casting(seg, LEADS)["usable"] is True


@pytest.mark.parametrize("character,person", [
    ("Elsie Bray", "laura_santamaria"),
    ("Anna Bray", "joanna_lee"),
    ("Zavala", "kelsey_hightower"),
    ("Cayde-6", "castrojo"),
    ("Lord Saladin", "jeefy"),
    ("Osiris", "mrbobbytables"),
    ("Saint-14", "kat"),
    ("Mara Sov", "karena_angell"),
    ("Petra Venj", "lenka"),
    ("Variks", "nate_waddington"),
    ("The Speaker", "jonathan_bryce"),
    ("Amanda Holliday", "ashley_willis"),
    ("iron_lord_red_haired", "paris_pittman"),
])
def test_cast_bindings(character, person):
    """The cast list, pinned. These bindings are fixed for the life of the
    project, so a silent change here would re-credit a real person."""
    seg = _seg(character=[{"name": character, "kind": "guardian_npc"}])
    assert compute_casting(seg, LEADS)["person"] == person


def test_lead_written_but_uncast_has_null_person():
    """An uncast lead still identifies the character; the tile just has no name."""
    seg = _seg(character=[{"name": "Ikora Rey", "kind": "guardian_npc"}])
    got = compute_casting(seg, LEADS)
    assert got["role"] == "lead" and got["character"] == "ikora_rey"
    assert got["person"] is None


# --- casting: ensemble ------------------------------------------------------

def test_ensemble_regardless_of_anonymity():
    """Anonymity is no longer a gate — a low-substitutability Guardian is still
    an ensemble slot, because the pool is now many people, not one stand-in."""
    for sub in (0, 2, 3, 5):
        got = compute_casting(_seg(substitutability=sub), LEADS)
        assert got["role"] == "ensemble", sub


def test_ensemble_person_is_assigned_later():
    """Segment records never name an ensemble person: the pool rotates monthly,
    and a tagged segment must not go stale when it does."""
    assert compute_casting(_seg(), LEADS)["person"] is None


@pytest.mark.parametrize("overrides,expected", [
    ({"composition": ["crowd"]}, 6),
    ({"composition": ["crowd", "establishing"]}, 6),
    ({"composition": ["group"]}, 3),
    ({"composition": ["single"], "subject_salience": "crowd_group"}, 3),
    ({"composition": ["single"]}, 1),
    ({"composition": []}, 1),
])
def test_ensemble_slot_counts(overrides, expected):
    seg = _seg(**overrides)
    assert compute_slots(seg) == expected
    assert compute_casting(seg, LEADS)["slots"] == expected


def test_crowd_group_salience_is_ensemble():
    got = compute_casting(_seg(subject_salience="crowd_group"), LEADS)
    assert got["role"] == "ensemble"


# --- casting: none ----------------------------------------------------------

@pytest.mark.parametrize("salience", ["environment_establishing", "enemy_threat",
                                      "object_artifact"])
def test_casting_none(salience):
    assert compute_casting(_seg(subject_salience=salience), LEADS) == {
        "role": "none", "character": None, "person": None,
        "usable": False, "constraints_failed": [], "slots": 0,
    }


def test_unlisted_character_falls_through_to_ensemble():
    seg = _seg(character=[{"name": "Some Random Frame", "kind": "other"}])
    assert compute_casting(seg, LEADS)["role"] == "ensemble"


def test_unlisted_character_with_environment_salience_is_none():
    seg = _seg(subject_salience="environment_establishing",
               character=[{"name": "The Traveler", "kind": "other"}])
    assert compute_casting(seg, LEADS)["role"] == "none"


def test_lead_beats_ensemble():
    """A named lead in a guardian_hero shot casts as lead, not ensemble."""
    seg = _seg(subject_salience="guardian_hero",
               character=[{"name": "Zavala", "kind": "guardian_npc"}])
    assert compute_casting(seg, LEADS)["role"] == "lead"


@pytest.mark.parametrize("raw,expected", [
    ("Elsie Bray", "elsie_bray"),
    ("The Traveler", "the_traveler"),
    ("Saint-14", "saint_14"),
    ("Amanda Holliday", "amanda_holliday"),
    ("  Elsie   Bray ", "elsie_bray"),
])
def test_snake_case(raw, expected):
    assert snake_case(raw) == expected
