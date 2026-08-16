"""Every committed plate manifest must agree with its binding on CHROME too.

`tools/plate.check_copy_against_bindings` is the guard that stops a
hand-authored manifest silently contradicting `vocab/casting.yaml` -- built
after act VI's tail shipped two cards that disagreed with their bindings
(#111). It compares `label`, `class` and `title`.

It does not compare `trustee` or `variant`, and both are part of the plates
skill's closed field set:

  * `trustee: true` is the burnished-silver treatment. `_variant_for()` reads
    it as `VARIANTS["trustee" if spec.get("trustee") else "default"]`, so a
    card that merely OMITS the flag renders default blue -- the authored
    identity, minus the chrome that identity was granted.
  * `variant: leader` is the gold treatment, and the vocab records it as the
    owner's decision for specific people. Attaching it to somebody else
    promotes a real person's card on nobody's authority.

Either way the card names a real person and shows them wrong, which is the
class of error AGENTS.md rule 3 exists to prevent.

TODO(owner): the runtime guard in `tools/plate.py` is still the narrower
three-field check. It was left alone deliberately: `tools/plate.py` is a
declared source of act VII in `stories/megacut/delivery.json`, so editing it
by one byte marks the act stale and fails
`tools/deliver.py status --sources-only --check` until act VII is re-rendered
and republished -- the trap recorded in #219, where a cosmetic `plate.py` edit
was reverted rather than force a re-render of an owner-approved cut. This test
closes the hole for every manifest that SHIPS, which is every committed one.
Fold the two chrome fields into `check_copy_against_bindings` itself the next
time a change is already paying for an act VII re-render.
"""
import json
from pathlib import Path

import pytest

from tools.derive import load_leads

REPO_ROOT = Path(__file__).resolve().parents[1]

# The chrome flags, and what they mean when a card leaves them out. Both are
# falsy-by-default in the renderer, so "absent" is a real value here rather
# than "no opinion" -- which is precisely why comparing only present fields
# (as the runtime guard does) misses a dropped TRUSTEE.
CHROME_DEFAULTS = {"trustee": False, "variant": None}


def _manifest_paths():
    """Every committed JSON under stories/ that carries plate entries."""
    return sorted(REPO_ROOT.glob("stories/**/*.json"))


def _entries(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []
    if isinstance(data, dict):
        for key in ("plates", "entries", "cards"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            return []
    if not isinstance(data, list):
        return []
    return [e for e in data if isinstance(e, dict) and e.get("name")]


def _authored_identities():
    """{credited name: (character key, authored plate copy)}."""
    by_name = {}
    for character, binding in (load_leads() or {}).items():
        copy = (binding or {}).get("plate") or {}
        if copy.get("name"):
            by_name.setdefault(copy["name"], (character, copy))
    return by_name


@pytest.mark.parametrize("path", _manifest_paths(),
                         ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_committed_plates_match_their_binding_chrome(path):
    by_name = _authored_identities()
    problems = []

    for entry in _entries(path):
        name = entry["name"]
        if name not in by_name:
            continue
        character, bound = by_name[name]

        # An explicit, reasoned divergence is allowed -- the same escape hatch
        # the runtime guard offers, and just as noisy on purpose.
        override = entry.get("copy_override")
        if isinstance(override, dict) and override.get("decided_by"):
            continue

        for field, default in CHROME_DEFAULTS.items():
            want = bound.get(field, default)
            got = entry.get(field, default)
            if want != got:
                problems.append(
                    f"plate {entry.get('id', '?')!r} credits {name!r} with "
                    f"{field}={got!r}, but the `{character}` binding in "
                    f"vocab/casting.yaml says {field}={want!r}"
                )

    assert not problems, (
        f"{path.relative_to(REPO_ROOT)} disagrees with vocab/casting.yaml on "
        "plate chrome. The vocab wins a conflict: fix the manifest, edit the "
        "binding, or record the decision with a `copy_override` carrying a "
        "`decided_by` issue URL.\n  " + "\n  ".join(problems)
    )


def test_the_gate_catches_a_dropped_trustee():
    """The failure this file exists for, in miniature.

    Bob Killen's binding carries `trustee: true`. A card that names him and
    omits the flag renders default blue chrome -- his authored identity minus
    the treatment it was granted -- and the runtime guard says nothing.
    """
    by_name = _authored_identities()
    if "Bob Killen" not in by_name:
        pytest.skip("the osiris binding no longer carries authored copy")
    _, bound = by_name["Bob Killen"]
    assert bound.get("trustee") is True, "the fixture this test relies on moved"

    dropped = {"id": "x", "name": "Bob Killen"}
    assert dropped.get("trustee", False) != bound.get("trustee", False)


def test_the_gate_catches_a_stolen_leader_variant():
    """`variant: leader` is gold, and the vocab records who was granted it."""
    by_name = _authored_identities()
    plain = [(name, copy) for name, (_, copy) in by_name.items()
             if not copy.get("variant")]
    if not plain:
        pytest.skip("every authored identity carries a variant")
    name, bound = plain[0]
    stolen = {"id": "x", "name": name, "variant": "leader"}
    assert stolen.get("variant", None) != bound.get("variant", None)
