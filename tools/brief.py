#!/usr/bin/env python3
"""A GitHub issue that asks for a video -> a validated, executable brief.

The owner files ideas the way people actually file ideas: a YouTube link, a
couple of timecodes, a song, and a sentence about who should be named on
screen. That is the right way to file, and nothing here tries to change it.
But prose is not executable, and "an agent reads the issue and works out what
was meant" is exactly the failure this repo bans everywhere else -- it is the
same move as inventing on-screen copy, one step earlier.

So an issue carries two things. The prose stays the prose. Beside it lives a
fenced ``brief`` block: the same request in YAML, matching
``schema/brief.schema.json``. Tools read the block; humans read the issue.

    ```brief
    title: Paris / Jeefy
    sources:
      - url: https://www.youtube.com/watch?v=9Yh23FKEGt4
        note: cinematics only, no space shots
    characters: [saladin]
    plates:
      - at: "0:14"
        copy:
          label: TRUSTEE // GUARDIAN
          name: Paris Pittman
          class: Harbringer Titan
          title: Kolossus of Kubernetes
    automatable: partly
    blocked_on: Paris is not cast in vocab/casting.yaml yet.
    ```

The block is not the owner's job to write. ``normalize`` reads an issue's prose
and PROPOSES one, printing it for a one-word confirmation; only then does it go
in the issue. That keeps filing frictionless and still ends with something a
tool can execute -- and it puts the owner, not the agent, at the point where a
guess would otherwise be made.

Three rules this module exists to enforce:

* **An unknown character is an error, never a normalization.** ``characters``
  and ``plates[].character`` are the same vocabulary the index uses, so they
  are checked against ``vocab/casting.yaml``. A name that is not a lead key or
  one of its ``aka`` spellings stops the parse and lists what is valid. Casting
  a real person is an owner decision (docs/skills/casting.md); an agent that
  quietly maps "Paris" onto the nearest key has made that decision for them.

* **A derived field in a brief is an error.** ``clean``, ``footage_tier``,
  ``traversal_hero`` and ``casting`` are computed by ``tools/derive.py`` at
  assembly. Accepting one here would let an issue smuggle in the value that the
  index computes -- and ``clean`` in particular is the gate the whole repo
  rests on. The schema forbids them structurally; ``_reject_derived`` says so
  in the error message a person will actually read.

* **"Not automatable" is a result.** ``automatable`` is required. A visual
  judgement about a frame, a claim about a real person, and a licensing
  decision cannot be automated in this repo, and an agent that names one and
  stops has finished its job correctly.

Commands::

    python3 tools/brief.py parse 3                  # issue -> validated brief JSON
    python3 tools/brief.py parse --file brief.yaml  # or straight from a file
    python3 tools/brief.py normalize 1              # prose -> proposed block
    python3 tools/brief.py check                    # every open issue's block

``gh`` is only needed by the commands that read GitHub. Parsing and validation
are pure functions over text, which is what the tests exercise.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.derive import lead_alias_index, load_leads, snake_case  # noqa: E402

BRIEF_SCHEMA_PATH = REPO_ROOT / "schema" / "brief.schema.json"

# The fenced block, by its info string. ```brief is preferred; ```yaml brief is
# accepted because GitHub highlights the former as plain text, and somebody
# will reasonably reach for the latter to get colour.
BRIEF_BLOCK_RE = re.compile(
    r"^[ \t]*```[ \t]*(?:yaml[ \t]+)?brief[ \t]*\r?\n(.*?)^[ \t]*```",
    re.DOTALL | re.MULTILINE | re.IGNORECASE,
)

# Computed by tools/derive.py at assembly time. Named here so that a brief that
# carries one gets an error explaining WHY rather than a schema path.
DERIVED_FIELDS = ("clean", "footage_tier", "traversal_hero", "casting")

TIMECODE_RE = re.compile(r"\b(\d{1,2}:\d{2}(?::\d{2})?)\b")
YOUTUBE_URL_RE = re.compile(r"https?://(?:www\.|music\.)?youtu(?:be\.com|\.be)/\S+")


class BriefError(Exception):
    """A brief that cannot be executed as written."""


# --------------------------------------------------------------------------
# extraction
# --------------------------------------------------------------------------

def extract_block(body):
    """The raw YAML text of the ``brief`` block in an issue body, or None.

    Returns None when the issue has no block at all -- an ordinary state, not
    an error: it means nobody has normalized this issue yet.
    """
    if not body:
        return None
    match = BRIEF_BLOCK_RE.search(body)
    return match.group(1) if match else None


def has_block(body):
    """Whether this issue body carries a brief block."""
    return extract_block(body) is not None


def _coerce_automatable(data):
    """Put back the ``yes``/``no`` that YAML 1.1 turned into booleans.

    ``automatable: no`` is the natural way to write this field and the way the
    issue form suggests it, but YAML 1.1 reads bare yes/no/on/off as booleans,
    so the value arrives as ``False``. Rejecting it would mean telling an owner
    their correct answer is invalid, and quoting is not something anyone should
    have to remember. The enum stays strings, and the boolean is translated
    back here -- at the edge, once.
    """
    value = data.get("automatable")
    if isinstance(value, bool):
        data["automatable"] = "yes" if value else "no"


def _automatable_spelling_is_yes_or_no(text):
    """Whether the raw text really spelled `automatable` as yes/no.

    YAML 1.1 also reads `on`/`off`/`true`/`false` as booleans, and translating
    those into "yes"/"no" would silently accept a spelling the enum does not
    have. Only the two words the schema documents are forgiven their type.
    """
    match = re.search(r"^[ \t]*automatable[ \t]*:[ \t]*(\S+)", text, re.MULTILINE)
    return bool(match) and match.group(1).strip("\"'").lower() in ("yes", "no")


def _reject_derived(data):
    """Refuse a brief that sets a field the index computes.

    The schema already rejects these as unknown properties. This exists so the
    message names the rule instead of the JSON pointer, because the mistake is
    conceptual: the value would be recomputed and silently overwritten, and for
    `clean` a false positive puts a HUD in a finished cut.
    """
    present = [f for f in DERIVED_FIELDS if f in data]
    if present:
        raise BriefError(
            "brief sets derived field(s): " + ", ".join(present) + ". "
            "clean, footage_tier, traversal_hero and casting are computed by "
            "tools/derive.py at assembly time -- a brief that sets one is "
            "overwritten, so state the tags that produce it instead."
        )


def _validate_schema(data):
    """Validate against schema/brief.schema.json, if jsonschema is installed."""
    try:
        from jsonschema import Draft202012Validator
    except ImportError:  # pragma: no cover - validation is optional, as in ingest.py
        return
    with BRIEF_SCHEMA_PATH.open(encoding="utf-8") as fh:
        schema = json.load(fh)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path)
    )
    if errors:
        lines = [
            f"  {'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}"
            for e in errors
        ]
        raise BriefError("brief does not match schema/brief.schema.json:\n"
                         + "\n".join(lines))


def _resolve_character(name, alias_index, leads):
    """A brief's character name -> its canonical vocab/casting.yaml key.

    Raises rather than guessing. An unrecognized name is far more often a
    person the project has not cast yet than a typo, and inventing the binding
    is the one thing casting must never do.
    """
    key = alias_index.get(snake_case(name))
    if key is None:
        known = ", ".join(sorted(leads))
        raise BriefError(
            f"unknown character {name!r}. `characters` uses the lead keys in "
            f"vocab/casting.yaml, which are the same ids the segment index "
            f"tags. Add the binding there first (an owner decision -- see "
            f"docs/skills/casting.md), or use one of: {known}"
        )
    return key


def parse_brief(text, casting_path=None):
    """Parse and validate brief YAML text into a normalized dict.

    Character names are resolved to canonical keys, so everything downstream
    compares ids rather than spellings. Everything else is returned as written:
    a brief is the owner speaking, and this function's job is to refuse what it
    cannot execute, not to improve it.
    """
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise BriefError(f"brief block is not valid YAML: {exc}") from exc
    if data is None:
        raise BriefError("brief block is empty")
    if not isinstance(data, dict):
        raise BriefError(f"brief block must be a mapping, got {type(data).__name__}")

    if _automatable_spelling_is_yes_or_no(text):
        _coerce_automatable(data)
    _reject_derived(data)
    _validate_schema(data)

    leads = load_leads(casting_path)
    alias_index = lead_alias_index(leads)

    if "characters" in data:
        data["characters"] = [
            _resolve_character(name, alias_index, leads) for name in data["characters"]
        ]
    for plate in data.get("plates") or []:
        if plate.get("character"):
            plate["character"] = _resolve_character(
                plate["character"], alias_index, leads
            )

    if data["automatable"] in ("no", "partly") and not data.get("blocked_on"):
        raise BriefError(
            f"automatable is {data['automatable']!r} but blocked_on is missing. "
            "Stopping is a valid outcome here; stopping without naming what "
            "would unblock it makes the next agent rediscover the blocker."
        )
    return data


def parse_issue_body(body, casting_path=None):
    """The validated brief in an issue body. Raises if there is no block."""
    text = extract_block(body)
    if text is None:
        raise BriefError(
            "issue has no ```brief block. Run "
            "`python3 tools/brief.py normalize <issue>` to propose one from the "
            "prose, then add it after the owner confirms."
        )
    return parse_brief(text, casting_path=casting_path)


# --------------------------------------------------------------------------
# normalization: prose -> a PROPOSED block
# --------------------------------------------------------------------------

def _person_index(leads):
    """``{spelling: character_id}`` for the real people already cast.

    The owner writes "Starring Kat", not "starring saint_14" -- they refer to
    the person, and the binding to the character is the thing vocab/casting.yaml
    already records.
    """
    index = {}
    for character_id, entry in leads.items():
        for spelling in (entry.get("person"), entry.get("display_name")):
            if spelling:
                index.setdefault(snake_case(spelling), character_id)
    return index


# A real person's name in an issue does not mean they are in the video. "Thanks
# to Kat for the idea" is not casting; neither is "ask Lenka about the music".
# A proposal that read those as credits would put a colleague in a cut they are
# not in, and the owner's one-word confirmation would ratify it. So a person is
# only read as cast when the sentence says so.
CASTING_CUES = (
    "starring", "stars", "star", "featuring", "features", "cast", "casting",
    "plays", "playing", "as ", "nameplate", "plate", "credit", "credits",
    "hero shot", "with ",
)


def _looks_like_casting(line):
    lowered = line.lower()
    return any(cue in lowered for cue in CASTING_CUES)


def _find_characters(body, leads):
    """Character ids named in prose, read conservatively.

    A DESTINY character's name is read anywhere: naming Osiris is naming a
    role, and a role is what the index tags. A REAL PERSON's name is only read
    on a line that is talking about casting, because their name appears in
    issues for every other reason too.

    Either way this proposes; it never decides. An id that is not already in
    vocab/casting.yaml is never invented, so the worst case is a name the owner
    deletes, not a binding an agent created.
    """
    found = []
    alias_index = lead_alias_index(leads)
    lowered = body.lower()
    for spelling, key in alias_index.items():
        words = spelling.replace("_", " ")
        if len(words) < 4 or key in found:
            continue
        if re.search(rf"\b{re.escape(words)}\b", lowered):
            found.append(key)

    person_index = _person_index(leads)
    for line in body.splitlines():
        if not _looks_like_casting(line):
            continue
        line_lowered = line.lower()
        for spelling, key in person_index.items():
            words = spelling.replace("_", " ")
            if len(words) < 3 or key in found:
                continue
            if re.search(rf"\b{re.escape(words)}\b", line_lowered):
                found.append(key)
    return found


def _split_media_urls(body):
    """(source urls, music url or None), reading the owner's own labelling.

    A music.youtube.com link is unambiguous. A plain YouTube link on a line
    that says "music" is the other way the owner writes it (issue #4), and
    guessing wrong there would score the cut with its own source audio.
    """
    music = None
    sources = []
    for line in body.splitlines():
        urls = [u.rstrip(").,") for u in YOUTUBE_URL_RE.findall(line)]
        if not urls:
            continue
        labelled_music = re.search(r"\bmusic\b|\bsong\b|\btrack\b", line, re.I)
        for url in urls:
            if music is None and ("music.youtube" in url or labelled_music):
                music = url
            else:
                sources.append(url)
    return sources, music


def propose_brief(title, body, casting_path=None):
    """Read an issue's prose and propose a brief, conservatively.

    Only facts that are unambiguously in the text become fields: URLs, the
    timecodes attached to them, and character names that already exist in
    vocab/casting.yaml. Everything else -- the sentences that carry the actual
    direction -- is preserved verbatim in `notes`, because paraphrasing intent
    loses the part an editor needs.

    The result is deliberately `automatable: no`: a proposal is a guess about
    what the owner meant, and it is not executable until the owner has looked
    at it. Confirming the block is what makes it a brief.
    """
    body = body or ""
    proposal = {}
    if title:
        proposal["title"] = title

    urls, music_url = _split_media_urls(body)
    if urls:
        proposal["sources"] = [{"url": u} for u in urls]
    if music_url:
        proposal["music"] = {"url": music_url}

    found = _find_characters(body, load_leads(casting_path))
    if found:
        proposal["characters"] = found

    beats = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = TIMECODE_RE.search(stripped)
        if match and not stripped.startswith("http"):
            beats.append({"at": match.group(1), "note": stripped})
    if beats:
        proposal["beats"] = beats

    proposal["notes"] = body.strip()
    proposal["automatable"] = "no"
    proposal["blocked_on"] = (
        "Owner has not confirmed this brief. It was proposed from the issue "
        "prose; nothing here is an owner statement until they say so."
    )
    return proposal


def render_block(brief):
    """A brief dict as the fenced block to paste into an issue."""
    body = yaml.safe_dump(brief, sort_keys=False, allow_unicode=True,
                          default_flow_style=False, width=78)
    return "```brief\n" + body + "```"


# --------------------------------------------------------------------------
# GitHub
# --------------------------------------------------------------------------

def _gh_json(args):
    """Run a `gh` command that emits JSON, with a legible failure."""
    try:
        out = subprocess.run(["gh", *args], capture_output=True, text=True, check=True)
    except FileNotFoundError as exc:
        raise BriefError("`gh` is not installed; this command needs it") from exc
    except subprocess.CalledProcessError as exc:
        raise BriefError(f"gh {' '.join(args)} failed: {exc.stderr.strip()}") from exc
    return json.loads(out.stdout or "null")


def fetch_issue(number):
    """One issue as ``{"number", "title", "body"}``."""
    return _gh_json(["issue", "view", str(number), "--json", "number,title,body"])


def fetch_open_issues():
    """Every open issue, newest first."""
    return _gh_json(
        ["issue", "list", "--state", "open", "--limit", "200",
         "--json", "number,title,body"]
    )


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _cmd_parse(args):
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
        brief = (parse_brief(text) if not has_block(text)
                 else parse_issue_body(text))
    else:
        issue = fetch_issue(args.issue)
        brief = parse_issue_body(issue.get("body"))
    print(json.dumps(brief, indent=2))
    return 0


def _cmd_normalize(args):
    issue = fetch_issue(args.issue)
    proposal = propose_brief(issue.get("title"), issue.get("body"))
    print(f"# proposed brief for #{issue['number']}: {issue.get('title')}")
    print("# Nothing below is an owner statement yet. Post it as a comment,")
    print("# get a one-word confirmation, then edit it into the issue body.")
    print(render_block(proposal))
    return 0


def _cmd_check(args):
    issues = ([fetch_issue(n) for n in args.issue] if args.issue
              else fetch_open_issues())
    problems = 0
    for issue in issues:
        number, title = issue["number"], issue.get("title", "")
        if not has_block(issue.get("body")):
            print(f"#{number} {title}: no brief block (run `normalize {number}`)")
            continue
        try:
            brief = parse_issue_body(issue.get("body"))
        except BriefError as exc:
            problems += 1
            print(f"#{number} {title}: INVALID\n  " + str(exc).replace("\n", "\n  "))
            continue
        note = f"automatable={brief['automatable']}"
        if brief.get("blocked_on"):
            note += f", blocked on: {brief['blocked_on']}"
        print(f"#{number} {title}: ok ({note})")
    return 1 if problems else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("parse", help="issue or file -> validated brief JSON")
    p.add_argument("issue", nargs="?", type=int, help="issue number")
    p.add_argument("--file", help="read brief YAML (or an issue body) from a file")
    p.set_defaults(func=_cmd_parse)

    n = sub.add_parser("normalize", help="propose a brief block from issue prose")
    n.add_argument("issue", type=int)
    n.set_defaults(func=_cmd_normalize)

    c = sub.add_parser("check", help="validate open issues' brief blocks")
    c.add_argument("issue", nargs="*", type=int, help="specific issues (default: all open)")
    c.set_defaults(func=_cmd_check)

    args = parser.parse_args(argv)
    if args.command == "parse" and not args.file and args.issue is None:
        parser.error("parse needs an issue number or --file")
    try:
        return args.func(args)
    except BriefError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
