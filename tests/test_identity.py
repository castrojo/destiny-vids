"""GitHub-login identity model invariants."""
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from tools.identity import (
    UnknownPerson,
    canonical_login,
    chat_identity,
    login_for_cast_key,
    load_people,
    person_for_character,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CASTING_PATH = REPO_ROOT / "vocab" / "casting.yaml"


def casting():
    return yaml.safe_load(CASTING_PATH.read_text(encoding="utf-8"))


def test_character_resolves_to_its_assigned_github_person():
    assert person_for_character("mara_sov").login == "angellk"
    assert person_for_character("the_speaker").login == "jbryce"


def test_login_spelling_is_canonical_but_display_names_are_not_aliases():
    assert canonical_login("hikariknight") == "HikariKnight"
    with pytest.raises(UnknownPerson):
        canonical_login("Hikari")


def test_chat_identity_uses_the_stable_github_account_id():
    assert chat_identity("akgraner")["avatar_url"].endswith("/6200805?v=4")


def test_legacy_cast_key_migrates_without_copying_a_second_plate():
    assert login_for_cast_key("joseph_sandoval") == "jrsapi"
    assert login_for_cast_key("shuah_khan") == "shuahkh"
    assert "legacy_titles" not in casting()["ensemble"]


def test_identity_parsing_and_casefold_index_are_cached(monkeypatch):
    import tools.identity as identity

    identity._casting.cache_clear()
    identity._people.cache_clear()
    identity._folded_logins.cache_clear()
    calls = 0
    original = identity.yaml.safe_load

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(identity.yaml, "safe_load", counted)
    load_people()
    canonical_login("hikariknight")
    chat_identity("akgraner")
    assert calls == 1


def test_every_bound_lead_references_one_person_record():
    people = load_people()
    leads = casting()["leads"]["values"]
    assert all(entry["person"] in people for entry in leads.values()
               if entry.get("person") is not None)


def test_leads_do_not_duplicate_person_identity_fields():
    for character, entry in casting()["leads"]["values"].items():
        assert "github" not in entry, character
        assert "dialogue_label" not in entry, character
        assert "plate" not in entry, character


def test_numeric_github_ids_and_authored_plates_live_only_in_people():
    doc = casting()
    people = doc["people"]
    ids = [person["github_id"] for person in people.values()]
    assert len(ids) == len(set(ids))
    for entry in doc["leads"]["values"].values():
        assert not {"github_id", "plate"} & set(entry)


def test_ensemble_titles_are_the_people_records_not_a_second_map():
    assert not {"titles", "legacy_titles"} & set(casting()["ensemble"])
    assert all(person.plate is not None
               for person in load_people().values()
               if person.login in {"rochaporto", "akgraner", "KyleGospo"})


def test_casting_vocabulary_matches_its_schema():
    schema = __import__("json").loads(
        (REPO_ROOT / "schema" / "casting.schema.json").read_text())
    errors = list(Draft202012Validator(schema).iter_errors(casting()))
    assert not errors, "\n".join(error.message for error in errors)
