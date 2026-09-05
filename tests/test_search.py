"""Tests for the search engine against the canonical queries.

Run: python3 -m pytest tests/test_search.py -q
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import search  # noqa: E402

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples")


def top_id(query, **kwargs):
    segs = search.load_segments(EXAMPLES)
    out = search.search(query, segs, **kwargs)
    assert out["results"], f"no results for {query!r}"
    return out["results"][0][1]["segment_id"], out


# (query, expected top segment_id). Note the Hunter/Arc query is NOT here: its
# only footage is HUD-laden gameplay, so the clean gate correctly returns
# nothing (see test_unclean_excluded_by_default).
CANONICAL = [
    ("wide establishing shot of the Traveler", "seg_traveler_establishing_0003-0011"),
    ("guardians parkouring across a bridge", "seg_tfs_launch_bridge_0047-0054"),
    ("close-up on a Titan's helmet", "seg_titan_helmet_cu_0112-0118"),
    ("Elsie Bray hero shot", "seg_bl_elsie_hero_0102-0108"),
]


def test_canonical_queries():
    for query, expected in CANONICAL:
        got, _ = top_id(query)
        assert got == expected, f"{query!r} -> {got}, expected {expected}"


# --- the clean gate ---------------------------------------------------------

def test_unclean_excluded_by_default():
    """The only Hunter+Arc footage is HUD/nameplate gameplay. Excluding it is the
    right answer: the query has no shot that could be cut into the story."""
    segs = search.load_segments(EXAMPLES)
    out = search.search("show us Hunters with Arc", segs)
    assert out["total"] == 0
    assert out["pool"] < out["index"]


def test_include_unclean_surfaces_it_penalized():
    got, out = top_id("show us Hunters with Arc", include_unclean=True)
    assert got == "seg_arc_hunter_crucible_0134-0220"
    assert out["pool"] == out["index"]
    reasons = " ".join(out["results"][0][2])
    assert "UNCLEAN" in reasons


def test_every_default_result_is_clean():
    segs = search.load_segments(EXAMPLES)
    for query in ("guardians", "a wide shot", "helmet"):
        out = search.search(query, segs)
        assert all(seg["clean"] for _, seg, _ in out["results"]), query


def test_burned_in_text_blocks_a_cinematic():
    """Cleanliness is independent of tier: a pre-rendered shot with a title card
    is excluded even though it is cinematic-tier."""
    segs = {s["segment_id"]: s for s in search.load_segments(EXAMPLES)}
    card = segs["seg_lightfall_titlecard_0206-0212"]
    assert card["footage_tier"] == "cinematic" and card["clean"] is False
    out = search.search("Neomuna skyline", search.load_segments(EXAMPLES))
    assert card["segment_id"] not in [s["segment_id"] for _, s, _ in out["results"]]


def test_gameplay_tier_is_ranked_below_cinematic():
    clean_gameplay = {"clean": True, "footage_tier": "gameplay", "subject_salience": "guardian_hero"}
    clean_cinematic = {"clean": True, "footage_tier": "cinematic", "subject_salience": "guardian_hero"}
    assert search.score_segment(clean_cinematic, [])[0] > search.score_segment(clean_gameplay, [])[0]


# --- casting ----------------------------------------------------------------

def test_hunter_arc_parses_element_filter():
    parsed = search.parse_query("show us Hunters with Arc")
    assert parsed["filters"].get("element") == {"arc"}
    assert parsed["filters"].get("class") == {"hunter"}  # plural handled


def test_lead_boost_applies_to_elsie():
    _, out = top_id("Elsie Bray hero shot")
    top = out["results"][0][1]
    assert top["casting"]["role"] == "lead"
    assert top["casting"]["person"] == "nimbinatus"
    assert "lead: elsie_bray" in " ".join(out["results"][0][2])


def test_constrained_cast_excludes_blocked_shots():
    """jeefy -> Saladin is far + helmeted only, so a Saladin query returns the
    wide shot and never the blocked close-up."""
    segs = search.load_segments(EXAMPLES)
    out = search.search("Lord Saladin", segs)
    ids = [seg["segment_id"] for _, seg, _ in out["results"]]
    assert "seg_roi_saladin_far_0032-0041" in ids
    assert "seg_roi_saladin_cu_0102-0107" not in ids


def test_blocked_lead_gets_no_boost():
    segs = {s["segment_id"]: s for s in search.load_segments(EXAMPLES)}
    blocked = segs["seg_roi_saladin_cu_0102-0107"]
    assert blocked["casting"]["usable"] is False
    assert blocked["casting"]["constraints_failed"] == ["require_far"]
    _, reasons = search.score_segment(blocked, [], weights={"lead": 1.0})
    assert any("blocked cast" in r for r in reasons)
    assert not any("+0.40 lead" in r for r in reasons)


def test_unconstrained_lead_close_up_still_retrievable():
    """Only constrained bindings care about framing: Elsie's identifiable CU is
    still first-party footage."""
    segs = search.load_segments(EXAMPLES)
    out = search.search("Elsie Bray", segs)
    assert "seg_bl_elsie_hero_0102-0108" in [s["segment_id"] for _, s, _ in out["results"]]


def test_cast_names_route_to_casting_filters():
    for query, facet, val in [
        ("shots of Zavala", "casting.character", "zavala"),
        ("Kelsey Hightower footage", "casting.person", "kelseyhightower"),
        ("Cayde-6 talking", "casting.character", "cayde_6"),
        ("castrojo", "casting.person", "castrojo"),
        ("jeefy", "casting.person", "jeefy"),
        ("Mara Sov", "casting.character", "mara_sov"),
        ("Variks", "casting.character", "variks"),
        ("nate-double-u", "casting.person", "nate-double-u"),
        ("Saint-14", "casting.character", "saint_14"),
        ("The Speaker", "casting.character", "the_speaker"),
    ]:
        parsed = search.parse_query(query)
        assert val in parsed["filters"].get(facet, set()), (query, parsed["filters"])


def test_bound_login_routes_to_the_canonical_person():
    parsed = search.parse_query("kdruckman footage")
    assert parsed["filters"]["casting.person"] == {"kdruckman"}


def test_missing_plate_names_do_not_become_the_bogus_none_phrase():
    parsed = search.parse_query("none of the crowd")
    assert "casting.person" not in parsed["filters"]


def test_ensemble_role_is_queryable():
    segs = search.load_segments(EXAMPLES)
    out = search.search("anonymous guardians", segs)
    assert out["total"] > 0
    assert all(seg["casting"]["role"] == "ensemble" for _, seg, _ in out["results"])


def test_crowd_shot_offers_the_most_slots():
    segs = {s["segment_id"]: s for s in search.load_segments(EXAMPLES)}
    crowd = segs["seg_tfs_launch_tower_crowd_0112-0118"]
    assert crowd["casting"]["slots"] == 6


# --- relaxation -------------------------------------------------------------

def test_overspecified_relaxes_and_discloses():
    _, out = top_id("slow-motion supers in a raid")
    assert out["dropped"], "expected relaxation disclosure"
    dropped_facets = {f for f, _ in out["dropped"]}
    assert dropped_facets & {"activity", "pacing"}


def test_never_relax_hard_facets():
    segs = search.load_segments(EXAMPLES)
    out = search.search("Vex on Neomuna", segs)
    assert out["total"] == 0
    assert "faction" in out["active_filters"]


def test_plural_caption_terms_match_singular_captions():
    """'guardians' must match a caption that says 'Guardian'."""
    seg = {"caption": "a lone Guardian on a bridge", "character": [], "mood": []}
    assert search.caption_sim(seg, ["guardians"]) == 1.0


def test_preferred_salience_matches_the_vocab():
    """vocab/ is the single source of truth for every enum, so the ranking's
    preferred set must not drift from what salience.yaml declares."""
    import yaml
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "vocab" / "salience.yaml"
    declared = yaml.safe_load(path.read_text())["subject_salience"]["preferred_for_retrieval"]
    assert set(declared) == search.PREFERRED_SALIENCE


def test_every_cast_person_and_character_is_queryable():
    """A binding nobody can search for is a binding that does not exist."""
    from tools.derive import load_leads
    leads = load_leads()
    people = {f for facet in ("casting.person",) for phrase in search.PHRASES.values()
              for f_, vals in phrase if f_ == facet for f in vals}
    characters = {f for phrase in search.PHRASES.values()
                  for f_, vals in phrase if f_ == "casting.character" for f in vals}
    for character, entry in leads.items():
        assert character in characters, f"no query phrase for character {character}"
        if entry["person"]:
            assert entry["person"] in people, f"no query phrase for person {entry['person']}"


def test_no_orphaned_cast_phrases():
    """The reverse of the above: a query phrase pointing at a character or person
    that no longer exists in vocab/casting.yaml is dead weight, and silently
    stops matching when a role is recast."""
    from tools.derive import load_leads
    leads = load_leads()
    known_characters = set(leads)
    known_people = {e["person"] for e in leads.values() if e["person"]}
    for phrase, contributions in search.PHRASES.items():
        for facet, values in contributions:
            if facet == "casting.character":
                assert values <= known_characters, (phrase, values - known_characters)
            elif facet == "casting.person":
                assert values <= known_people, (phrase, values - known_people)
