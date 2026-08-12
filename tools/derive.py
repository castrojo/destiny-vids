"""Derived (Tier 0/1, no-model) segment fields for the destiny-vids index.

Every function here is a pure function of already-tagged fields, cheap enough to
run over the whole index on every change. ``label_source`` for all of them is
``heuristic``.

- ``clean``          — the primary gate: no disqualifying burned-in overlays.
- ``footage_tier``   — cinematic | gameplay | mixed; keeps gameplay, tiers it.
- ``traversal_hero`` — wide, stable "Guardian in motion" beats.
- ``casting``        — lead (named character -> fixed person) or ensemble
                       (anonymous Guardian slots for the month's contributors).

``substitutability`` and ``register`` are model/heuristic INPUTS and are
deliberately NOT recomputed here.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASTING_PATH = REPO_ROOT / "vocab" / "casting.yaml"

# Overlays that cannot be edited out and so bar a shot from the story.
# `letterbox` is deliberately absent: bars can be cropped.
DISQUALIFYING_OVERLAYS = frozenset({"hud", "nameplates", "burned_text", "talking_head"})

# content_type -> footage_tier. Anything unlisted (trailer, UNKNOWN, absent)
# falls through to 'mixed'.
TIER_BY_CONTENT_TYPE = {
    "cinematic": "cinematic",
    "cutscene": "cinematic",
    "gameplay": "gameplay",
}

# Shot scales wide enough to show the world but tight enough to read as a
# Guardian (docs/pipeline.md §4).
TRAVERSAL_HERO_SCALES = frozenset({"ELS", "LS", "MLS", "MS"})

# Constraint evaluation for a CONSTRAINED lead binding (jeefy -> Saladin), where
# the person does not resemble the character and the framing has to do the work.
# The face is "concealed" when not clearly or partly visible; the shot is "far"
# when wide enough not to reveal facial detail.
FACE_CONCEALED_VISIBILITY = frozenset({"face_obscured", "back_only", "silhouette", "none"})
FAR_SCALES = frozenset({"ELS", "LS", "MLS", "MS"})

# Saliences whose subject is an anonymous Guardian body, i.e. an ensemble slot.
ENSEMBLE_SALIENCE = frozenset({"guardian_hero", "crowd_group"})

# How many contributor tiles a shot can carry, by how crowded the frame is.
SLOTS_CROWD = 6
SLOTS_GROUP = 3
SLOTS_SOLO = 1


def snake_case(name):
    """Normalize a free-text character name to a snake_case id.

    "Elsie Bray" -> "elsie_bray", "The Traveler" -> "the_traveler".
    """
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", str(name).lower())).strip("_")


def load_leads(path=None):
    """Load the lead cast map from vocab/casting.yaml.

    Returns ``{character_id: {"person": str|None, "display_name": str|None,
    "aka": [...]}}``, preserving YAML order.
    """
    path = Path(path) if path else DEFAULT_CASTING_PATH
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    values = ((data or {}).get("leads") or {}).get("values") or {}
    return {
        character_id: {
            "person": entry.get("person"),
            "display_name": entry.get("display_name"),
            "aka": list(entry.get("aka") or []),
            "constraints": dict(entry.get("constraints") or {}),
            "plate": dict(entry.get("plate") or {}) or None,
        }
        for character_id, entry in values.items()
    }


def load_placeholder_plate(path=None):
    """Load the UNCAST-ensemble nameplate copy from vocab/casting.yaml.

    The blueberry plate: what an ensemble slot says on screen before a month's
    roster exists. It lives in the vocab for the same reason lead plate copy
    does — so nobody hardcodes on-screen text into a manifest — and it credits
    nobody, because an uncast slot has no person to credit yet.
    """
    path = Path(path) if path else DEFAULT_CASTING_PATH
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    copy = ((data or {}).get("ensemble") or {}).get("placeholder_plate") or {}
    return dict(copy)


def lead_alias_index(leads):
    """Flatten a lead map into ``{alias_or_canonical_id: canonical_id}``."""
    index = {}
    for character_id, entry in leads.items():
        index[character_id] = character_id
        for alias in entry.get("aka") or []:
            index.setdefault(snake_case(alias), character_id)
    return index


def evaluate_constraints(segment, constraints):
    """Return the sorted constraint keys this segment FAILS.

    Empty list => the shot satisfies the binding. Known constraints:
      require_helmet -> identity_visibility must read as face-concealed.
      require_far    -> shot_scale must be wide-ish, not a close-up/insert.
    """
    failed = []
    if constraints.get("require_helmet"):
        if segment.get("identity_visibility") not in FACE_CONCEALED_VISIBILITY:
            failed.append("require_helmet")
    if constraints.get("require_far"):
        if segment.get("shot_scale") not in FAR_SCALES:
            failed.append("require_far")
    return sorted(failed)


def compute_clean(segment):
    """DERIVED primary gate: is this frame free of un-removable overlays?

    True iff ``overlays`` is tagged and contains none of ``hud``, ``nameplates``,
    ``burned_text``, ``talking_head``.

    An ABSENT ``overlays`` key derives False, not True. Cleanliness must be
    positively established: guessing clean on an untagged shot is how a HUD ends
    up in the finished cut. An explicitly empty list, or ``["none"]``, is clean.
    """
    overlays = segment.get("overlays")
    if overlays is None:
        return False
    return not (DISQUALIFYING_OVERLAYS & set(overlays))


def compute_footage_tier(segment):
    """DERIVED cutting tier from ``content_type``.

    Gameplay stays in the index — it is just B-roll, ranked beneath cinematics —
    so a story defaults to the cinematic look and drops to gameplay for coverage.
    """
    return TIER_BY_CONTENT_TYPE.get(segment.get("content_type"), "mixed")


def compute_traversal_hero(segment):
    """DERIVED boolean, exactly as defined in schema/segment.schema.json.

    True iff 'traversal' in action, shot_scale in {ELS, LS, MLS, MS}, and
    camera_movement excludes 'handheld_shaky'.

    Note: this no longer requires substitutability >= 3. Anonymity stopped being
    a usability gate when the ensemble became a whole contributor pool, so a
    recognizable Guardian sprinting across a bridge is still a hero traversal.
    """
    action = segment.get("action") or []
    camera_movement = segment.get("camera_movement") or []
    return bool(
        "traversal" in action
        and segment.get("shot_scale") in TRAVERSAL_HERO_SCALES
        and "handheld_shaky" not in camera_movement
    )


def compute_slots(segment):
    """How many contributor credit tiles an ensemble shot can carry."""
    composition = segment.get("composition") or []
    if "crowd" in composition:
        return SLOTS_CROWD
    if "group" in composition or segment.get("subject_salience") == "crowd_group":
        return SLOTS_GROUP
    return SLOTS_SOLO


def compute_casting(segment, leads):
    """DERIVED casting object, exactly as defined in vocab/casting.yaml.

    Applied in order:
      1. Any segment character name (snake_cased) matching a lead's canonical id
         or an ``aka`` -> role 'lead', that canonical character, and the
         binding's ``person`` (None when the role is written but not yet cast).
         Most bindings are unconstrained and usable at any shot scale, since the
         project names roles rather than compositing faces. A CONSTRAINED binding
         (jeefy -> Saladin: far + helmeted) is evaluated here: ``usable`` is
         False and ``constraints_failed`` lists the unmet keys when the shot
         violates it.
      2. elif subject_salience is an anonymous-Guardian salience -> role
         'ensemble' with ``slots`` tiles to fill. ``person`` stays None here:
         ensemble casting is assigned per calendar month by tools/ensemble.py,
         so a rotating pool never invalidates a tagged segment.
      3. else -> role 'none'.
    """
    alias_index = lead_alias_index(leads)
    for entry in segment.get("character") or []:
        canonical = alias_index.get(snake_case(entry.get("name", "")))
        if canonical:
            failed = evaluate_constraints(segment, leads[canonical].get("constraints") or {})
            return {
                "role": "lead",
                "character": canonical,
                "person": leads[canonical].get("person"),
                "usable": not failed,
                "constraints_failed": failed,
                "slots": 0,
            }
    if segment.get("subject_salience") in ENSEMBLE_SALIENCE:
        return {
            "role": "ensemble",
            "character": None,
            "person": None,
            "usable": True,
            "constraints_failed": [],
            "slots": compute_slots(segment),
        }
    return {"role": "none", "character": None, "person": None,
            "usable": False, "constraints_failed": [], "slots": 0}


def derive_all(segment, leads=None):
    """Return a dict of every derived field for ``segment``.

    Callers merge this into the record; nothing is mutated in place.
    """
    leads = load_leads() if leads is None else leads
    return {
        "clean": compute_clean(segment),
        "footage_tier": compute_footage_tier(segment),
        "traversal_hero": compute_traversal_hero(segment),
        "casting": compute_casting(segment, leads),
    }
