"""The Witness is shown as eyes or smoke, never its body.

A standing rule for the character rather than one cut's editorial choice, so it
lives in the vocabulary and is asserted here. The default is exclusion — the
same posture as the `clean` gate — because the judgement "is this a body or a
wisp?" is a visual one about a frame, which cannot be automated. A shot earns
its way in only by a human adding it to `approved`.
"""
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CASTING = yaml.safe_load((REPO_ROOT / "vocab/casting.yaml").read_text())
WITNESS = CASTING["leads"]["values"]["the_witness"]


def test_the_witness_carries_a_depiction_rule():
    assert WITNESS["depiction"]["rule"] == "eyes_or_smoke_only"


def test_approved_defaults_to_exclusion():
    """An empty allow-list must mean 'no Witness shots', never 'all of them'."""
    approved = WITNESS["depiction"]["approved"]
    assert isinstance(approved, list)
    for segment_id in approved:
        assert isinstance(segment_id, str) and segment_id


def test_every_approved_shot_exists_and_is_actually_the_witness():
    """An allow-list entry that names nothing is a rule with a hole in it."""
    import glob
    import json

    approved = set(WITNESS["depiction"]["approved"])
    if not approved:
        return
    seen = {}
    for path in glob.glob(str(REPO_ROOT / "segments/*.json")):
        data = json.loads(Path(path).read_text())
        for seg in (data if isinstance(data, list) else [data]):
            seen[seg["segment_id"]] = seg
    for segment_id in approved:
        assert segment_id in seen, f"approved shot {segment_id} does not exist"
        names = " ".join(
            (c.get("name", "") if isinstance(c, dict) else str(c)).lower()
            for c in (seen[segment_id].get("character") or [])
        )
        assert "witness" in names, (
            f"{segment_id} is approved for the Witness but is not tagged as them")


def test_the_rule_is_not_quietly_widened():
    """Only this one value is meaningful; a new rule name would bypass the gate."""
    assert set(WITNESS["depiction"]) == {"rule", "note", "approved"}
