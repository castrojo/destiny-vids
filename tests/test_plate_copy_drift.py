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
            # A season manifest seats its plates on the fixed cast instead of
            # a top-level list. The plate copy is the same kind of record and
            # the guard must see it too.
            fixed = data.get("fixed_cast")
            if not isinstance(fixed, list):
                return []
            return [
                {**member["plate"], "id": f"fixed_cast:{member.get('id', '?')}"}
                for member in fixed
                if isinstance(member, dict)
                and isinstance(member.get("plate"), dict)
                and member["plate"].get("name")
            ]
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
    problems = _chrome_problems(_entries(path), _authored_identities())

    assert not problems, (
        f"{path.relative_to(REPO_ROOT)} disagrees with vocab/casting.yaml on "
        "plate chrome. The vocab wins a conflict: fix the manifest, edit the "
        "binding, or record the decision with a `copy_override` carrying a "
        "`decided_by` issue URL.\n  " + "\n  ".join(problems)
    )


def _chrome_problems(entries, by_name):
    """Every entry whose chrome disagrees with the binding it credits.

    THE comparison -- the parametrized sweep over the committed manifests and
    the two miniature regressions below all run this one function. They used
    to assert on dicts they had just built themselves (`False != True`), which
    is a tautology wearing a guard's name: it could not fail, so it could not
    notice the comparison it was named after regressing.
    """
    problems = []
    for entry in entries:
        name = entry["name"]
        if name not in by_name:
            continue
        character, bound = by_name[name]

        # An explicit, reasoned divergence is allowed -- the same escape hatch
        # the runtime guard offers, and just as noisy on purpose.
        override = entry.get("copy_override")
        if isinstance(override, dict) and override.get("decided_by"):
            continue

        # A season fixed-cast plate is a deliberate per-video owner override:
        # its explicit `provenance` (owner instruction + factual name source)
        # plays the copy_override role, so the guard recognizes the decision
        # instead of forcing an empty global binding into vocab/casting.yaml
        # for a name that belongs to one video. The hatch is scoped to the
        # season's own `fixed_cast:` ids -- a provenance block on any other
        # record is not an override.
        provenance = entry.get("provenance")
        if (
            str(entry.get("id", "")).startswith("fixed_cast:")
            and isinstance(provenance, dict)
            and provenance.get("copy_source") == "owner_authored"
            and provenance.get("decided_by")
        ):
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
    return problems


def test_the_gate_catches_a_dropped_trustee():
    """The failure this file exists for, in miniature.

    Bob Killen's binding carries `trustee: true`. A card that names him and
    omits the flag renders default blue chrome -- his authored identity minus
    the treatment it was granted -- and the runtime guard says nothing.
    """
    by_name = _authored_identities()
    assert "Bob Killen" in by_name, (
        "the osiris binding no longer carries authored copy -- this guard "
        "needs a new fixture rather than a skip, or it stops guarding")
    _, bound = by_name["Bob Killen"]
    assert bound.get("trustee") is True, "the fixture this test relies on moved"

    dropped = {"id": "x", "name": "Bob Killen"}
    problems = _chrome_problems([dropped], by_name)
    assert problems, "a card that drops Bob Killen's trustee flag went unseen"
    assert "trustee" in problems[0]

    # ...and a card carrying the binding's own chrome is clean, so the guard is
    # discriminating rather than merely noisy.
    kept = {"id": "x", "name": "Bob Killen"}
    kept.update({f: bound[f] for f in CHROME_DEFAULTS if f in bound})
    assert not _chrome_problems([kept], by_name)


def test_the_gate_catches_a_stolen_leader_variant():
    """`variant: leader` is gold, and the vocab records who was granted it."""
    by_name = _authored_identities()
    plain = [(name, copy) for name, (_, copy) in by_name.items()
             if not copy.get("variant")]
    assert plain, (
        "every authored identity carries a variant -- this guard needs a new "
        "fixture rather than a skip, or it stops guarding")
    name, _bound = plain[0]
    stolen = {"id": "x", "name": name, "variant": "leader"}
    problems = _chrome_problems([stolen], by_name)
    assert problems, f"a card stealing `leader` chrome for {name!r} went unseen"
    assert "variant" in problems[0]

    assert not _chrome_problems([{"id": "x", "name": name}], by_name)


def test_the_gate_sees_season_fixed_cast_plates():
    """The sweep walks season `fixed_cast[].plate` records too -- a plate
    record that hides in a nested season shape is not outside the guard."""
    path = REPO_ROOT / "stories" / "standalone" / "season-of-the-blueberries.json"
    entries = _entries(path)
    names = {e["name"] for e in entries}
    assert {"Angie Jones", "Shellea Williams", "Cortney"} <= names
    # ...and they all carry the explicit provenance the guard recognizes.
    by_name = _authored_identities()
    assert not _chrome_problems(entries, by_name)


def test_a_fixed_cast_plate_needs_provenance_to_diverge():
    """Season-shaped entries are held to the same standard: a fixed-cast
    plate that contradicts an authored identity is flagged UNLESS it records
    explicit owner provenance -- the per-video override the season contract
    requires instead of an empty global binding."""
    by_name = _authored_identities()
    assert "Bob Killen" in by_name, "the fixture this test relies on moved"

    bare = {"id": "fixed_cast:x", "name": "Bob Killen"}
    problems = _chrome_problems([bare], by_name)
    assert problems, "a season plate dropping trustee chrome went unseen"
    assert "trustee" in problems[0]

    provenanced = {
        **bare,
        "provenance": {
            "copy_source": "owner_authored",
            "decided_by": "Owner instruction, the 2026-08-29 season decision",
            "name_source": "GitHub REST GET /users/example",
        },
    }
    assert not _chrome_problems([provenanced], by_name), (
        "explicit owner provenance is the season plate's override record"
    )

    # A provenance block without the owner instruction is not an override.
    hollow = {**bare, "provenance": {"copy_source": "owner_authored"}}
    assert _chrome_problems([hollow], by_name)

    # The hatch is scoped to the season's fixed-cast records: the same
    # provenance block on any other plate id exempts nothing.
    stray = {**provenanced, "id": "standalone-card-1"}
    assert _chrome_problems([stray], by_name), (
        "the provenance override must not reach records outside fixed_cast:"
    )


def _jorge_guardian_plates():
    """Every committed Guardian/nameplate record crediting Jorge Castro.

    Chat pills are excluded: they carry `speaker`/`text`, and the blue pill
    colour there is a separate, already-settled concern -- this invariant is
    about Guardian nameplate chrome only. The sweep walks every committed
    record under stories/ rather than naming manifests, so a new standalone
    batch or act manifest is covered the moment it exists.
    """
    found = []
    for path in _manifest_paths():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        candidates = []
        if isinstance(data, list):
            candidates = data
        elif isinstance(data, dict):
            for key in ("plates", "entries", "cards"):
                if isinstance(data.get(key), list):
                    candidates.extend(data[key])
            for video in data.get("videos") or []:
                if isinstance(video, dict):
                    candidates.extend(video.get("overlays") or [])
            for member in data.get("fixed_cast") or []:
                if isinstance(member, dict) and isinstance(member.get("plate"), dict):
                    candidates.append(member["plate"])
        for entry in candidates:
            if not isinstance(entry, dict) or entry.get("name") != "Jorge Castro":
                continue
            if entry.get("kind") == "chat" or "text" in entry:
                continue
            found.append((path, entry))
    return found


def test_jorge_castros_guardian_plates_are_basic_blue_everywhere():
    """Cayde/Jorge/Castrojo is always basic blue: the identity is workmanlike
    joy, not glory, so no Guardian plate of his carries the burnished-silver
    `trustee` chrome or any `variant`. `TRUSTEE` in his label is copy, not
    rank chrome.

    The sweep must actually find him -- the Blueberries and Drink full plates,
    the Final Trial name-only card, and Act VI's reveal are all committed
    records, so an empty result means the sweep broke, not that the invariant
    holds.
    """
    found = _jorge_guardian_plates()
    assert len(found) >= 4, (
        "the sweep stopped finding Jorge Castro's committed Guardian plates "
        "-- fix the sweep, do not assume the chrome is right")
    problems = [
        f"{path.relative_to(REPO_ROOT)}:{entry.get('id', '?')}"
        for path, entry in found
        if entry.get("trustee") or entry.get("variant")
    ]
    assert not problems, (
        "Jorge Castro's Guardian plates are standard blue; these records carry "
        "trustee or variant chrome:\n  " + "\n  ".join(problems))
