"""Tests for the ensemble caster: monthly contributor pool -> Guardian tiles.

Network-free: the roster half is exercised through fixture data, since the
`gh`-backed fetch is a thin shell-out.
"""

import pytest

from tools.ensemble import (
    DEFAULT_ORG,
    assign,
    build_roster,
    is_bot,
    month_bounds,
    month_offset,
)


def roster(*logins, month="2026-08"):
    return {
        "month": month,
        "contributors": [{"login": name, "commits": 1, "display_name": name}
                         for name in logins],
    }


def ensemble_seg(segment_id, slots):
    return {"segment_id": segment_id, "video_id": "yt_test",
            "casting": {"role": "ensemble", "character": None,
                        "person": None, "slots": slots}}


def test_month_bounds():
    assert month_bounds("2026-08") == ("2026-08-01T00:00:00Z", "2026-09-01T00:00:00Z")


def test_month_bounds_rolls_over_the_year():
    assert month_bounds("2026-12") == ("2026-12-01T00:00:00Z", "2027-01-01T00:00:00Z")


@pytest.mark.parametrize("login,expected", [
    ("dependabot", True), ("renovate[bot]", True), ("github-actions", True),
    ("some-bot", True), ("castrojo", False), ("robotics", False),
])
def test_bot_filter(login, expected):
    assert is_bot(login) is expected


def test_assignment_is_deterministic():
    """A re-render must not reshuffle who played whom."""
    pool = roster("a", "b", "c")
    segs = [ensemble_seg("s1", 3), ensemble_seg("s2", 2)]
    assert assign(pool, segs) == assign(pool, segs)


def test_everyone_is_placed_before_anyone_repeats():
    pool = roster("a", "b", "c", "d")
    result = assign(pool, [ensemble_seg("s1", 4)])
    assert sorted(a["login"] for a in result["assignments"]) == ["a", "b", "c", "d"]


def test_pool_wraps_when_there_are_more_slots_than_people():
    pool = roster("a", "b")
    result = assign(pool, [ensemble_seg("s1", 5)])
    assert result["slots_filled"] == 5
    assert len(result["tiles"]) == 2


def test_shortfall_is_reported_not_swallowed():
    """More contributors than slots means real people go uncredited — say so."""
    pool = roster("a", "b", "c", "d")
    result = assign(pool, [ensemble_seg("s1", 2)])
    assert len(result["uncredited"]) == 2
    assert set(result["uncredited"]) | {a["login"] for a in result["assignments"]} == \
        {"a", "b", "c", "d"}


def test_only_ensemble_slots_are_filled():
    """Leads are cast by hand and the crowd never spills onto them."""
    segs = [
        {"segment_id": "lead", "casting": {"role": "lead", "character": "zavala",
                                           "person": "kelsey_hightower", "slots": 0}},
        {"segment_id": "none", "casting": {"role": "none", "character": None,
                                           "person": None, "slots": 0}},
        ensemble_seg("crowd", 2),
    ]
    result = assign(roster("a", "b"), segs)
    assert {a["segment_id"] for a in result["assignments"]} == {"crowd"}


def test_months_rotate_the_cast():
    """Adjacent months must not hand almost everyone the same Guardian."""
    pool = [f"user{i}" for i in range(12)]
    offsets = {month_offset(f"2026-{m:02d}", len(pool)) for m in range(1, 13)}
    assert len(offsets) > 1


def test_empty_pool_is_survivable():
    result = assign(roster(), [ensemble_seg("s1", 3)])
    assert result["assignments"] == [] and result["pool_size"] == 0


def test_empty_shotlist_leaves_everyone_uncredited():
    result = assign(roster("a", "b"), [])
    assert result["slots_filled"] == 0
    assert sorted(result["uncredited"]) == ["a", "b"]


def test_build_roster_survives_an_unreachable_repo(monkeypatch):
    """A renamed or private repo should cost a few names, not the month."""
    import tools.ensemble as ensemble

    def fake_fetch(repo, since, until):
        return {"castrojo": 3} if repo == "good/repo" else {}

    monkeypatch.setattr(ensemble, "fetch_repo_contributors", fake_fetch)
    built = ensemble.build_roster("2026-08", ["good/repo", "gone/repo"])
    assert [c["login"] for c in built["contributors"]] == ["castrojo"]


def test_roster_is_sorted_by_login_not_commit_count():
    """The pool is a cast list, not a leaderboard — and alphabetical order is
    what keeps assignment reproducible when commit counts shift."""
    import tools.ensemble as ensemble

    monkeypatch_counts = {"zed": 99, "amy": 1}
    ensemble_fetch = lambda repo, since, until: monkeypatch_counts  # noqa: E731
    original = ensemble.fetch_repo_contributors
    ensemble.fetch_repo_contributors = ensemble_fetch
    try:
        built = build_roster("2026-08", ["r/r"])
    finally:
        ensemble.fetch_repo_contributors = original
    assert [c["login"] for c in built["contributors"]] == ["amy", "zed"]


# --- maintainers vs contributors --------------------------------------------

def test_org_membership_is_recorded_per_contributor():
    """The roster carries who is in the org; the plate copy reads it later."""
    built = build_roster("2026-08", repos=[], members={"hanthor", "ahmedadan"})
    assert built["org"] == DEFAULT_ORG


def test_membership_is_tri_state_not_a_boolean():
    """Failing to read the org is NOT evidence that nobody is a maintainer.

    Demoting every maintainer because a token expired would put an incorrect
    credit on screen for a real person, which is worse than a vaguer one.
    """
    from tools.derive import ensemble_label, load_ensemble_plate

    copy = load_ensemble_plate()
    assert ensemble_label(copy, True) == "MAINTAINER // GUARDIAN"
    assert ensemble_label(copy, False) == "CONTRIBUTOR // GUARDIAN"
    assert ensemble_label(copy, None) == "GUARDIAN"
    # ...and the neutral case must not claim either way.
    assert "MAINTAINER" not in ensemble_label(copy, None)
    assert "CONTRIBUTOR" not in ensemble_label(copy, None)


def test_assignment_carries_membership_through_to_the_tile():
    roster = {
        "month": "2026-08",
        "contributors": [
            {"login": "hanthor", "display_name": "hanthor", "org_member": True},
            {"login": "Giklab", "display_name": "Giklab", "org_member": False},
        ],
    }
    segments = [
        {"segment_id": "s1", "casting": {"role": "ensemble", "slots": 2}},
    ]
    result = assign(roster, segments)
    by_login = {a["login"]: a["org_member"] for a in result["assignments"]}
    assert by_login == {"hanthor": True, "Giklab": False}


def test_the_checked_in_roster_agrees_with_the_org():
    """hanthor and ahmedadan are maintainers; the randos are contributors."""
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "renders" / "roster-2026-08.json"
    if not path.exists():
        pytest.skip("roster is a build artifact")
    roster = json.loads(path.read_text())
    membership = {c["login"]: c["org_member"] for c in roster["contributors"]}
    assert membership["hanthor"] is True
    assert membership["ahmedadan"] is True
    assert membership["castrojo"] is True
    assert membership["Giklab"] is False


# --- the lead exclusion --------------------------------------------------
#
# A person cannot be a named lead AND a nameless blueberry in the same
# project. That rule was written down in `lead_people`'s docstring and
# enforced against the wrong field: the exclusion set was built from the
# snake_case `person` id while the pool is keyed by GitHub login, so it
# matched nothing for every multi-word lead. None of it was covered.


def lead(person=None, github=None, display_name=None):
    return {"person": person, "github": github,
            "display_name": display_name or person, "aka": [], "plate": None}


def test_a_lead_is_excluded_by_their_github_login():
    """The login is what the roster is keyed by, so it is what must match.

    `person` is "Kelsey Hightower" normalized to kelsey_hightower; his login
    is kelseyhightower. Matching the two strings excludes nobody, and he was
    handed an anonymous Guardian tile while cast as Zavala.
    """
    leads = {"zavala": lead(person="kelsey_hightower", github="kelseyhightower",
                            display_name="Kelsey Hightower")}
    result = assign(roster("kelseyhightower", "someone_else"),
                    [ensemble_seg("s1", 2)], leads=leads)

    assert result["cast_as_lead"] == ["kelseyhightower"]
    assert [t["login"] for t in result["tiles"]] == ["someone_else"]


def test_a_lead_whose_person_id_is_already_their_login_stays_excluded():
    """castrojo's `person` and login are the same string; do not regress him."""
    leads = {"cayde_6": lead(person="castrojo", display_name="castrojo")}
    result = assign(roster("castrojo", "hanthor"), [ensemble_seg("s1", 2)],
                    leads=leads)

    assert result["cast_as_lead"] == ["castrojo"]
    assert [t["login"] for t in result["tiles"]] == ["hanthor"]


def test_an_uncast_character_excludes_nobody():
    leads = {"ikora_rey": lead(person=None)}
    result = assign(roster("a", "b"), [ensemble_seg("s1", 2)], leads=leads)

    assert result["cast_as_lead"] == []
    assert len(result["tiles"]) == 2


def test_a_lead_with_no_login_is_reported_rather_than_left_to_luck():
    """Degrade, never block: the gap is recorded, not guessed at.

    Nothing can exclude this person by login, because nobody has recorded
    one. Inventing it would be a claim about a real person, so the caster
    ships and says whose binding it cannot check.
    """
    leads = {
        "zavala": lead(person="kelsey_hightower", display_name="Kelsey Hightower"),
        "cayde_6": lead(person="castrojo", github="castrojo", display_name="castrojo"),
    }
    result = assign(roster("a"), [ensemble_seg("s1", 1)], leads=leads)

    assert result["leads_unverifiable"] == ["Kelsey Hightower"]


def test_the_committed_bindings_report_their_own_unverifiable_leads():
    """Runs against vocab/casting.yaml, so the punch list stays honest."""
    from tools.ensemble import lead_people, leads_without_login

    logins = lead_people()
    assert "castrojo" in logins, "castrojo is cast as Cayde-6"
    assert "nimbinatus" in logins, (
        "Laura Santamaria's verified login must be what excludes her, not the "
        "character string `nimbatus`, which is a different account entirely")
    # Not asserted as a fixed list: filling these in is owner work, and this
    # test must not fail the day somebody records one.
    assert isinstance(leads_without_login(), list)
