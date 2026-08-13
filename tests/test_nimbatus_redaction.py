"""Nimbatus — the name-until-Europa redaction (issue #103).

Nimbatus IS Laura Santamaria (github.com/nimbinatus), and her real name is
act VII copy only: act VII's Guardian card (82.525-90.000) is the reveal, and
every earlier act in the programme calls her NIMBATUS. Before this binding
existed that was correct only by luck — no earlier act happened to credit her.

The enforcement is structural, the same shape `cayde_signoff` carries in
act II: the pre-reveal name resolves to a binding that carries NO `plate:`
block, so tools/plate.py has no real-name copy to print and reports her under
`unresolved` (no_plate_copy) instead — missing words are punch-list items,
invented ones are forbidden. These tests pin the binding so the redaction
cannot be silently dropped, and prove a plate pass over a nimbatus shot
cannot emit "Laura Santamaria".
"""
from pathlib import Path

import pytest
import yaml

from tools.derive import compute_casting, load_leads

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW = (REPO_ROOT / "vocab" / "casting.yaml").read_text(encoding="utf-8")
BINDING = yaml.safe_load(RAW)["leads"]["values"]["nimbatus"]
LEADS = load_leads()

REAL_NAME = "Laura Santamaria"


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


def _shot(seg, start, end, character):
    return {
        "segment_id": seg, "video_id": "yt_v", "start_sec": start,
        "end_sec": end, "duration": end - start,
        "start_tc": "0:00", "end_tc": "0:01",
        "casting": {"role": "lead", "character": character,
                    "person": BINDING["person"], "usable": True,
                    "constraints_failed": [], "slots": 0},
    }


def test_nimbatus_is_bound_to_laura_santamaria():
    """'They are the same person' (owner, first alpha watch). The derivation
    path agrees: a shot tagged Nimbatus casts laura_santamaria."""
    assert BINDING["person"] == "laura_santamaria"
    got = compute_casting(
        _seg(character=[{"name": "Nimbatus", "kind": "guardian_npc"}]), LEADS)
    assert got["role"] == "lead"
    assert got["character"] == "nimbatus"
    assert got["person"] == "laura_santamaria"


def test_the_login_is_nimbinatus_not_nimbatus():
    """Two different GitHub accounts, and the wrong one matches the character
    name: `nimbinatus` is Laura Santamaria (Red Hat, u/1538692); `nimbatus`
    is an unrelated empty account (u/20426015). Avatar tooling resolves from
    this login, so pinning it is the cheap fix for a stranger's face landing
    on her credit."""
    assert BINDING["github"] == "nimbinatus"


def test_the_redaction_scope_is_recorded():
    """Same fields as cayde_signoff's card: what is redacted, and for how long."""
    assert BINDING["redacts"] == REAL_NAME
    scope = BINDING["redaction_scope"]
    assert "before VII" in scope
    assert "82.525" in scope, "the scope names the reveal card's window"


def test_the_binding_carries_no_plate_copy():
    """NO `plate:` block is the enforcement. Her authored identity
    (characters.json slug `laura`) lives on the elsie_bray binding, and its
    name row IS the redacted string, so it cannot be reused here; a Nimbatus
    plate (label / class / title under that name) is authored by nobody —
    TODO(owner), tracked by #103."""
    assert "plate" not in BINDING, (
        "plate copy here would have to be invented — the one thing "
        "vocab/casting.yaml must never do")
    assert BINDING["display_name"] == "Nimbatus"
    assert BINDING["display_name"] != BINDING["redacts"]


def test_a_pre_reveal_cut_cannot_plate_her_real_name():
    """The binding nobody enforces was the bug. Planned against the REAL
    vocab, a cut whose only lead is nimbatus produces no plate carrying her
    real name — it produces no plate at all, and the punch-list entry says
    exactly who went unplated and why."""
    plate = pytest.importorskip("tools.plate")
    shots = [_shot("s1", 0, 8, "nimbatus")]
    unresolved = []
    entries = plate.plan(shots, LEADS, unresolved=unresolved)

    assert REAL_NAME not in str(entries), "the real name must not print"
    assert [e for e in entries if e.get("id") == "nimbatus"] == []
    by_id = {u["id"]: u for u in unresolved}
    assert by_id["nimbatus"]["reason"] == "no_plate_copy"
    assert by_id["nimbatus"]["person"] == "laura_santamaria"
    assert by_id["nimbatus"]["display_name"] == "Nimbatus"


def test_elsie_bray_and_nimbatus_are_the_same_person_but_not_the_same_credit():
    """Two bindings, one person — on purpose. `nimbatus` is NOT an aka on
    `elsie_bray`: folding them together would route a pre-act-VII cut to the
    plate that prints her real name."""
    elsie = LEADS["elsie_bray"]
    assert elsie["person"] == BINDING["person"] == "laura_santamaria"
    assert "nimbatus" not in elsie["aka"]
    # ...and the tagged name decides the credit: Elsie plates the authored
    # (post-reveal) identity, Nimbatus cannot plate at all.
    assert elsie["plate"]["name"] == REAL_NAME
    assert LEADS["nimbatus"]["plate"] is None


def test_nimbatus_is_queryable():
    """A binding nobody can search for is a binding that does not exist."""
    from tools import search
    contributions = search.PHRASES.get("nimbatus") or []
    assert ("casting.character", {"nimbatus"}) in contributions
