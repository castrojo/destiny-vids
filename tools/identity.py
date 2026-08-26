#!/usr/bin/env python3
"""The one GitHub-account identity model used by casting and chat."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import sys

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASTING_PATH = REPO_ROOT / "vocab" / "casting.yaml"
RESERVED_SPEAKERS = frozenset({"[redacted]", "TBD"})
LEGACY_OVERRIDE_KEYS = frozenset({"cast", "avatar_login"})
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class UnknownPerson(ValueError):
    """A value that is not a recorded GitHub login."""


@dataclass(frozen=True)
class Person:
    login: str
    github_id: int
    plate: dict | None


def _path_key(path=None):
    return str((Path(path) if path else DEFAULT_CASTING_PATH).resolve())


@lru_cache
def _casting(path_key):
    with Path(path_key).open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@lru_cache
def _people(path_key):
    return {
        login: Person(login, int(record["github_id"]),
                      dict(record["plate"]) if record.get("plate") else None)
        for login, record in (_casting(path_key).get("people") or {}).items()
    }


def load_people(path=None) -> dict[str, Person]:
    """Return people keyed by their stored, case-preserving GitHub login."""
    return _people(_path_key(path))


@lru_cache
def _folded_logins(path_key):
    return {login.casefold(): login for login in _people(path_key)}


def canonical_login(value: str, people=None) -> str:
    """Normalize only a known login; names and historical personas are invalid."""
    folded = (_folded_logins(_path_key()) if people is None
              else {login.casefold(): login for login in people})
    try:
        return folded[str(value).casefold()]
    except KeyError as exc:
        raise UnknownPerson(f"unknown GitHub login: {value!r}") from exc


def person_for_character(character: str, casting=None) -> Person | None:
    """Resolve a cast character through its GitHub-login person binding."""
    if casting is None:
        casting = _casting(_path_key())
    elif isinstance(casting, (str, Path)):
        casting = _casting(_path_key(casting))
    binding = ((casting.get("leads") or {}).get("values") or {}).get(character) or {}
    login = binding.get("person")
    if not login:
        return None
    people = {
        key: Person(key, int(record["github_id"]),
                    dict(record["plate"]) if record.get("plate") else None)
        for key, record in (casting.get("people") or {}).items()
    }
    return people.get(login)


def login_for_cast_key(value: str, casting=None) -> str:
    """Resolve a transitional ``cast:`` key to a canonical GitHub login.

    The mapping only bridges existing raw chapter authoring while it migrates;
    it carries no plate copy and never turns a display name into an identity.
    """
    if casting is None:
        casting = _casting(_path_key())
    elif isinstance(casting, (str, Path)):
        casting = _casting(_path_key(casting))
    people = {
        login: Person(login, int(record["github_id"]),
                      dict(record["plate"]) if record.get("plate") else None)
        for login, record in (casting.get("people") or {}).items()
    }
    try:
        return canonical_login(value, people)
    except UnknownPerson:
        person = person_for_character(value, casting)
        if person:
            return person.login
        migrated = (casting.get("legacy_cast_logins") or {}).get(value)
        if migrated:
            return canonical_login(migrated, people)
        raise


def chat_identity(login: str, people=None) -> dict:
    """Return the canonical speaker and portrait fields for a known account."""
    people = load_people() if people is None else people
    canonical = canonical_login(login, people)
    person = people[canonical]
    return {
        "speaker": canonical,
        "avatar": f"renders/avatars/{canonical}.png",
        "avatar_url": f"https://avatars.githubusercontent.com/u/{person.github_id}?v=4",
    }


def _chapters():
    from tools import chapter_md
    return chapter_md.discover(), chapter_md


def audit(act=None, path=None):
    """Return identity findings without withholding an incomplete release."""
    casting = _casting(_path_key(path))
    people = load_people(path)
    findings = []
    ids = {}
    for login, person in people.items():
        previous = ids.setdefault(person.github_id, login)
        if previous != login:
            findings.append(("duplicate-github-id", f"{previous}, {login}: {person.github_id}"))
    for character, binding in ((casting.get("leads") or {}).get("values") or {}).items():
        login = binding.get("person")
        if login and login not in people:
            findings.append(("unknown-character-person", f"{character}: {login}"))
    chapters, chapter_md = _chapters()
    selected = [act] if act else sorted(chapters)
    for name in selected:
        if name not in chapters:
            findings.append(("unknown-act", name))
            continue
        resolved, _ = chapter_md.entries(name)
        for entry in resolved:
            if entry.get("kind") != "chat":
                continue
            speaker = entry.get("speaker", "")
            if speaker in RESERVED_SPEAKERS:
                continue
            try:
                canonical_login(speaker, people)
            except UnknownPerson:
                findings.append(("legacy-speaker", f"{name}: {speaker}"))
        text = chapters[name].path.read_text(encoding="utf-8")
        for key in LEGACY_OVERRIDE_KEYS:
            if f"- {key}:" in text:
                findings.append(("legacy-identity-override", f"{name}: {key}"))
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--act", help="audit one chapter act")
    parser.add_argument("--check", action="store_true", help="fail if selected findings remain")
    args = parser.parse_args(argv)
    findings = audit(args.act)
    for kind, detail in findings:
        print(f"{kind}: {detail}")
    if not findings:
        print("identity: clean")
    return 1 if args.check and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
