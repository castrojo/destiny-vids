#!/usr/bin/env python3
"""Per-chapter conversations, authored in one Markdown file per act.

    python3 tools/chapter_md.py show II     # the schedule the file resolves to

THE PROBLEM THIS EXISTS FOR
---------------------------
Dropping a conversation into an act used to mean computing a film timecode
for every single line, and a character with three things to say became one
huge pill or nothing. Now the owner edits ``chapters/<act>.md``:

    ## 6:45
    Karena: Hit 'em with your lessons learned
    Rochaporto: One reference architecture coming up!
    jrsapi: Shit are you taking notes?

One ``## <time>`` heading drops the WHOLE conversation at that programme
time; the per-line timing is derived from how long each line takes to read.
Pinning one line re-seats it exactly and the rest of the conversation
adjusts around it:

    ## 6:45
    Karena: Hit 'em with your lessons learned
    jrsapi @ 6:52: Shit are you taking notes?

A pinned line lands exactly where it is pinned; the lines after it cascade
from there, and any slack between the previous line's read time and the pin
is silence -- a pill is down, the story breathes. A pin earlier than the
previous line's read time is still honoured, and the overlap is recorded in
``unresolved``.

READABILITY IS THE CLOCK
------------------------
A pill's hold is ``len(text) / CPS`` clamped to [MIN_HOLD, MAX_HOLD] -- the
characters-per-second metric pysrt exposes as ``characters_per_second``,
set conservative for a theatre screen (nobody reads 40 ft away at home-page
speed), with GAP of silence between pills so a change of speaker registers.
(source: /byroot/pysrt, SubRipItem.characters_per_second)

THE CLOCK IS THE PROGRAMME'S
----------------------------
Every timecode in a chapter file is on the WHOLE SHOW's clock, because that
is the clock the owner watches and marks against ("HIS CLOCK IS THE
MEGACUT'S" -- scripts/build_efmb_plates.py). The conversion to act-film
time subtracts the act's start in the programme, a committed constant whose
derivation is stated where it lives. An act with no entry there is an act
this tool does not time yet.

SEATS FOLLOW THE SPEECH ON SCREEN
---------------------------------
When a line's words match the act's recovered dialogue -- the shots where
the characters on screen are visibly saying them -- the line is seated
THERE, not where the cascade would have put it (owner, 2026-08-20: "if the
words in the conversation match the video and the characters look like they
are talking, heavily bias placement towards that"). An explicit ``@`` pin
still wins; the evidence-backed seat is reported either way, because the
second half of the ruling is "always inform the operator of improvements" --
every sync seat and every overridden one is printed by ``show``, recorded in
the manifest's ``unresolved``, and printed to stderr at build time.

DEGRADE, NEVER BLOCK
--------------------
A line with no words becomes a placeholder pill credited to nobody (the
repo's rule); a speaker that resolves to nothing in vocab/casting.yaml is
printed verbatim -- the owner typed it, which makes it owner-supplied copy
-- and a lowecase login-shaped speaker also earns its GitHub avatar, the
same shape act II's late pass uses. Anything the scheduler cannot honour
exactly is printed to stderr and recorded in ``unresolved``; the build
proceeds.
"""
from __future__ import annotations

import argparse
import difflib
import importlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import placeholder  # noqa: E402

CPS = 15.0       # chars/sec reading speed; conservative for a theatre screen
MIN_HOLD = 2.2   # the house rule: below this a plate cannot be read
MAX_HOLD = 7.0   # past this a static pill reads as stuck, not as dialogue
GAP = 0.25       # the beat between pills; PLATE_GAP in the act builds

CHAPTERS_DIR = REPO_ROOT / "chapters"

# The source video each act's picture is cut from -- where its recovered
# dialogue lives (dialogue/<video_id>/dialogue.json). That record is the
# evidence for "the characters on screen are saying these words". Empty
# today: act II's source plays under an instrumental, so nothing was ever
# recovered from it -- the one-line record that stood here was the owner's
# own Cayde line, retired with the card on 2026-08-20. Re-add an entry when
# an act's source has genuine recovered dialogue to seat against.
ACT_SOURCES = {}

# How close a line must read to a recovered cue to inherit its seat. Kept
# deliberately loose -- the owner paraphrases -- because a false seat is
# reported and overruled by any pin, while a missed one is never seen.
SYNC_MATCH = 0.65

TIME = r"[0-9]+(?::[0-9]+(?:\.[0-9]+)?){0,2}"
HEADING = re.compile(rf"^##\s+(?P<at>{TIME})\s*(?P<label>.*)$")
# An UNTIMED chapter's heading, for a run of cards that has no clock at all.
# Act VIII's credits are the case: its cards carry relative WEIGHTS that get
# scaled into whatever window the cover's own runtime leaves, so there is no
# second to pin them to and inventing one would be a lie about the picture.
UNTIMED_HEADING = re.compile(r"^##\s+(?P<label>.+)$")
# `Speaker: line`, with three optional prefixes/suffixes that exist so a
# migrated pill reproduces exactly: `[an_id]` binds the line to the plate
# that id already names, `@ <time>` pins it, and `+<seconds>` states the
# hold instead of deriving it from read speed.
LINE = re.compile(
    rf"^(?:\[(?P<id>[A-Za-z0-9_.-]+)\]\s*)?"
    rf"(?P<speaker>[^:@\s][^:@]*?)"
    rf"(?:\s*@\s*(?P<at>{TIME}))?"
    rf"(?:\s*\+\s*(?P<dur>[0-9]+(?:\.[0-9]+)?))?"
    rf"\s*:\s*(?P<text>.*)$")
# The red splash -- the boss bar. `! NAME` for the bar alone,
# `! NAME | a second row` to author its title, `! NAME |` to keep a title
# SLOT (rendered as lorem credited to nobody until the words exist), and
# `! [the_id] NAME` to keep an existing card's id when the Markdown takes
# over a seat the build script used to hold.
BOSS = re.compile(
    rf"^!\s+(?:\[(?P<id>[A-Za-z0-9_.-]+)\]\s*)?(?P<name>[^@|+]+?)"
    rf"(?:\s*@\s*(?P<at>{TIME}))?"
    rf"(?:\s*\+\s*(?P<dur>[0-9]+(?:\.[0-9]+)?))?"
    rf"\s*(?:\|\s*(?P<title>.*?))?\s*$")
# Every other card on screen -- a title, a context slab, a choice menu, a
# status readout. It has no speaker and no one line of dialogue, so its copy
# is the `- field: value` rows underneath it rather than the row itself.
#
#     * [opening_black_head] title @ 4:43.80 +10.65
#       - title: Eons later
#       - body: Maintainer-Guardians hold the line for humanity
CARD = re.compile(
    rf"^\*\s+(?:\[(?P<id>[A-Za-z0-9_.-]+)\]\s*)?(?P<kind>[a-z][a-z0-9_]*|-)"
    rf"(?:\s*@\s*(?P<at>{TIME}))?"
    rf"(?:\s*\+\s*(?P<dur>[0-9]+(?:\.[0-9]+)?))?\s*$")
# A NOTE TO THE AGENT, never to the audience: `>> re-time this once the bed
# lands <<`. It exists because the owner writes instructions in the same
# breath as dialogue, and before this marker they were indistinguishable from
# it -- "Add youtube click link thing to this video" was a pill on screen,
# speaker blank, because it happened to end in a colon. A note may span
# lines; everything from `>>` to `<<` is invisible to every rule below.
NOTE_OPEN = re.compile(r"^\s*>>")
NOTE_CLOSE = re.compile(r"<<\s*$")
# `[speaker] the words`, the shorthand the owner actually writes when a new
# voice cuts in. It is NOT the `[an_id]` prefix: an id is always followed by
# a speaker, so a bracket followed by the words themselves -- or straight by
# `@` or `+` or `:` -- is naming who is talking.
#
#     [amber] Which one of you is Kyleford?
#     [https://github.com/wrkode] Oh dibs on this one
#
# A GitHub URL in the brackets resolves to the login and its portrait. The
# URL itself never reaches the screen: it is a way of pointing at a person,
# not a thing to render.
SPEAKER_TAG = re.compile(r"^\[(?P<who>[^\]]+)\]\s*(?P<rest>.*)$")
GITHUB_URL = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/"
    r"(?P<login>[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)/?$")
# A field of the entry above it. Repeating a key builds a list, which is how
# a card's `body` rows keep their order without any punctuation to count.
ATTR = re.compile(r"^\s*-\s+(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*:\s?(?P<value>.*)$")
_LEGACY_LOGIN_SHAPE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")

# WHERE A PORTRAIT COMES FROM, AND WHY IT IS NOT TYPED HERE.
#
# A pill's picture is a claim about a real person, and this repo keeps those
# in exactly one place. So a chapter file names the PERSON and the resolution
# happens here:
#
#   - cast: joseph_sandoval     the portrait vocab/casting.yaml records
#   - avatar_login: KyleGospo   this GitHub account's picture
#
# Both are AUTHORING keys: they are consumed here and never reach the
# manifest, which carries the resolved cache path and the URL beside it as
# provenance. Pasting the URL into the chapter file instead would make a
# second copy of a casting fact, and the second copy is always the one that
# goes wrong.
#
# They are two keys because they answer two different questions. `cast` is
# "whatever the casting record says", which is right for somebody whose
# portrait is not a GitHub picture at all; `avatar_login` is "this account's
# picture", which is what act II's owner-seated pills were built from even
# for people whose casting record names a different image. Collapsing them
# would silently swap portraits on eight delivered pills.
PORTRAIT_KEYS = ("cast", "avatar_login")

# Keys whose value is a list even when it appears once: writing one `- body:`
# row must not produce a bare string where the renderer wants rows.
LIST_KEYS = {"body", "options", "rows", "lines", "censor", "plate_ids"}
# `- censor: Goddamn -> G{k8s}ddamn`
CENSOR = re.compile(r"^(?P<find>.*?)\s*->\s*(?P<replace>.*)$")


def parse_tc(text):
    """``M:SS(.ss)``, ``H:MM:SS`` or bare seconds -> float seconds."""
    parts = text.strip().split(":")
    if len(parts) == 1:
        return float(parts[0])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def format_tc(seconds):
    """Seconds -> ``M:SS.ss`` for the schedule ``show`` prints."""
    return f"{int(seconds // 60)}:{seconds % 60:05.2f}"


def format_tc_ms(seconds):
    """Seconds -> ``M:SS.sss``, the precision a pin has to round-trip at.

    ``format_tc`` rounds to hundredths because it prints for a person. A pin
    written back by ``extract`` is read again by ``parse_tc`` and has to land
    on the frame it came from, so it keeps the third decimal a plate's ``at``
    is stored with.
    """
    return f"{int(seconds // 60)}:{seconds % 60:06.3f}"


# ---------------------------------------------------------------------------
# THE REGISTRY IS THE CHAPTER FILES THEMSELVES.
#
# An act's programme offset, its film length and where its plates are written
# used to be three dicts in this module, which meant adding a chapter was an
# edit here AND a file there, and the two drifted -- act II's film length sat
# 4.5 s short of the manifest it describes for exactly as long as nobody
# looked. Now each `chapters/<act>.md` carries its own front matter and this
# module discovers it, so the file an owner edits is the file that declares
# what it is.
# ---------------------------------------------------------------------------

def parse_front_matter(text):
    """Leading ``---`` block -> (fields, body).

    Deliberately not YAML: the fields are strings, numbers and one nested
    ``defaults:`` mapping, and a chapter file must stay readable to somebody
    who has never heard of a YAML parser. Anything unrecognised is left
    alone rather than guessed at.

    A scalar field can run long enough that one line reads badly (Act II's
    `field_order` is seventeen names) -- an indented continuation line with
    no `defaults:` section open is folded onto the top-level scalar it
    follows, joined with a space, rather than parsed as a bogus key of its
    own (task-2-rereview-1.md: the un-joined tail silently dropped every
    name after the first line's trailing comma).
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    for end, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            break
    else:
        raise ValueError("front matter opens with `---` and never closes")
    fields, section, last_key = {}, None, None
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[:1] in " \t":
            if section is not None:
                key, _, value = raw.strip().partition(":")
                fields[section][key.strip()] = scalar(value.strip())
                continue
            if last_key is not None:
                fields[last_key] = scalar(
                    f"{fields[last_key]} {raw.strip()}")
                continue
        key, _, value = raw.partition(":")
        key, value = key.strip(), value.strip()
        if not value:
            section, last_key = key, None
            fields[key] = {}
            continue
        section, last_key = None, key
        fields[key] = scalar(value)
    return fields, "\n".join(lines[end + 1:])


def scalar(text):
    """A front-matter or attribute value -> str, float, int, bool or None.

    A quoted value stays a string, which is the whole reason quoting is
    supported: a card whose subtitle is the year 2026 must not come back as
    an integer and re-render as something subtly different.
    """
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    if text in ("true", "false"):
        return text == "true"
    if text in ("null", "~", ""):
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


class Chapter:
    """One act's chapter file, and everything it declares about itself."""

    def __init__(self, path, fields, body):
        self.path = Path(path)
        self.fields = fields
        self.body = body
        self.act = str(fields["act"])
        self.manifest = fields.get("manifest")
        self.defaults = fields.get("defaults") or {}
        self.plates_key = fields.get("plates_key", "plates")

    @property
    def programme_start(self):
        """Where this act starts in the whole show, in seconds.

        Authored in the file with its derivation beside it, because it is a
        measurement of a running order and not something to recompute from
        memory. An untimed chapter has none, and needs none: nothing in it
        is pinned to a second.
        """
        if self.fields.get("timed") is False:
            # An untimed chapter pins nothing, so this is not a clock -- it
            # is only where the chapter falls in the running order, for
            # anything that reads the show end to end.
            return float(self.fields.get("programme_start", 0.0))
        return float(self.fields["programme_start"])

    @property
    def film_sec(self):
        """The act's own length, read from its manifest, never restated.

        A chapter file that names a manifest gets this for free; one that
        does not may state ``film_sec`` itself. Absent both, the "runs off
        the picture" note is simply not available, which is a missing
        warning and not an error.
        """
        if "film_sec" in self.fields:
            return float(self.fields["film_sec"])
        doc = self.manifest_doc()
        if doc is None:
            return None
        for key in ("film_sec", "_film_sec"):
            if key in doc:
                return float(doc[key])
        return None

    def manifest_path(self):
        return None if self.manifest is None else REPO_ROOT / self.manifest

    def manifest_doc(self):
        path = self.manifest_path()
        if path is None or not path.exists():
            return None
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)


def discover(directory=None):
    """Every chapter file that declares an act -> ``{act: Chapter}``.

    A Markdown file in ``chapters/`` with no front matter is documentation,
    not a chapter, and is skipped in silence.
    """
    found = {}
    base = Path(directory) if directory else CHAPTERS_DIR
    if not base.exists():
        return found
    for path in sorted(base.glob("*.md")):
        fields, body = parse_front_matter(path.read_text(encoding="utf-8"))
        if "act" not in fields:
            continue
        chapter = Chapter(path, fields, body)
        found[chapter.act] = chapter
    return found


def chapter(act):
    """The act's ``Chapter``, or ``KeyError`` naming what is wired."""
    found = discover()
    if act not in found:
        raise KeyError(
            f"no chapter file is wired for act {act!r}; wired: "
            + (", ".join(sorted(found)) or "(none)"))
    return found[act]


def _act_map(attr):
    out = {}
    for act, chap in discover().items():
        try:
            value = getattr(chap, attr)
        except KeyError:
            continue
        if value is not None:
            out[act] = value
    return out


def __getattr__(name):
    """``ACT_PROGRAMME_START`` and ``ACT_FILM_SEC``, derived not declared.

    Both used to be literals here. They are kept as module attributes
    because they read well at a call site and in a test, but they are now
    views over the chapter files, so there is nothing to keep in step.
    """
    if name == "ACT_PROGRAMME_START":
        return _act_map("programme_start")
    if name == "ACT_FILM_SEC":
        return _act_map("film_sec")
    if name == "CHAPTER_FILES":
        return {act: str(chap.path.relative_to(REPO_ROOT))
                for act, chap in discover().items()}
    raise AttributeError(name)


def _norm(text):
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", text.lower()).split())


def sync_seats(act):
    """Recovered dialogue for the act's source video: [(source_sec, text)]."""
    video_id = ACT_SOURCES.get(act)
    if not video_id:
        return []
    from tools.dialogue import load_dialogue
    try:
        data = load_dialogue(video_id)
    except (FileNotFoundError, KeyError):
        return []
    return [(cue["start_sec"], cue["text"])
            for cue in data.get("cues", []) if cue.get("text")]


def film_for_source(act, src_sec):
    """Source seconds -> the act's film clock, or None when cut/unwired."""
    if act == "II":
        scripts = str(REPO_ROOT / "scripts")
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        import build_efmb
        try:
            return round(build_efmb.film_for_source(src_sec), 3)
        except Exception:
            # The matched frame was cut from the film: there is no seat.
            return None
    return None


def seat_lines(act, lines):
    """Speech-evidence seats for a block's lines: one entry per line.

    Each entry is None, or ``{"film", "src", "matched"}`` -- the film time
    the line's words are actually spoken on screen, the source timecode that
    evidences it, and the recovered wording matched. Pinned lines get seats
    too: the pin still wins, but the operator is told what the evidence
    would have preferred.
    """
    recovered = sync_seats(act)
    seats = []
    for line in lines:
        seat = None
        if line["kind"] == "chat" and line["text"] and recovered:
            want = _norm(line["text"])
            best = max(( (difflib.SequenceMatcher(None, want, _norm(text)).ratio(), src, text)
                         for src, text in recovered ), default=None)
            if best and best[0] >= SYNC_MATCH:
                film = film_for_source(act, best[1])
                if film is not None:
                    seat = {"film": film, "src": best[1],
                            "matched": best[2]}
        seats.append(seat)
    return seats


def hold_for(text):
    """How long one line stays up: read speed, clamped to the readable band."""
    return round(min(MAX_HOLD, max(MIN_HOLD, len(text) / CPS)), 3)


def chapter_path(act):
    return chapter(act).path


def parse(text):
    """Chapter Markdown -> blocks of ``{anchor, label, lines}``.

    A block is one ``## <time>`` heading and the entries under it: a
    ``Speaker: text`` pill, a ``!`` red splash, or a ``*`` card whose copy is
    the ``- field: value`` rows beneath it. Everything else -- instructions,
    commentary, examples indented into code blocks -- is ignored, so the file
    reads as a document first.
    """
    fields, text = parse_front_matter(text)
    timed = fields.get("timed", True) is not False
    # WHICH KEYS ARE ALWAYS LISTS is a fact about an act, not about a word.
    # The prologue's `body` is the lines of a book page and stays a list even
    # when there is one of them; act VIII's `body` is a single sentence under
    # a name. Same key, different records, so the file says which it means.
    list_keys = fields.get("list_keys")
    if isinstance(list_keys, str):
        list_keys = {k.strip() for k in list_keys.split(",") if k.strip()}
    elif isinstance(list_keys, dict):
        # `list_keys:` with nothing after it -- an act that declares no list
        # keys at all, which is not the same as an act that never mentioned
        # them and takes the default set.
        list_keys = set()
    else:
        list_keys = None
    blocks, current, entry = [], None, None
    in_note = False
    previous_blank = True
    for lineno, raw in enumerate(text.splitlines(), 1):
        was_blank, previous_blank = previous_blank, not raw.strip()
        if in_note:
            # Inside `>> ... <<`. It says nothing to the parser, and -- like a
            # `#` comment -- it must not detach the rows below it.
            in_note = not NOTE_CLOSE.search(raw)
            continue
        if NOTE_OPEN.match(raw):
            in_note = not NOTE_CLOSE.search(raw)
            continue
        heading = HEADING.match(raw) if timed else UNTIMED_HEADING.match(raw)
        if heading:
            current = {
                "anchor": parse_tc(heading["at"]) if timed else None,
                "label": heading["label"].strip(),
                "lineno": lineno,
                "lines": [],
            }
            blocks.append(current)
            entry = None
            continue
        if timed and raw.startswith("##"):
            raise ValueError(
                f"line {lineno}: a block heading is `## <time>` -- "
                f"could not read a time in {raw!r}")
        if current is None:
            continue
        if raw.lstrip().startswith("#"):
            # A comment inside an entry's rows -- why this card holds for six
            # seconds, why that one carries no fade. It must not end the
            # entry: an owner annotating their own copy would silently
            # detach every row below the note.
            continue
        attr = ATTR.match(raw)
        if attr and entry is not None:
            add_attr(entry["attrs"], attr["key"], attr["value"], list_keys)
            continue
        card = CARD.match(raw)
        if card:
            entry = {
                "kind": "card",
                "card_kind": card["kind"],
                "id": card["id"],
                "pin": (parse_tc(card["at"]) if card["at"] else None),
                "hold": (float(card["dur"]) if card["dur"] else None),
                "text": "",
                "attrs": {},
                "lineno": lineno,
            }
            current["lines"].append(entry)
            continue
        boss = BOSS.match(raw)
        if boss:
            title = boss["title"]
            entry = {
                "kind": "boss",
                "id": boss["id"],
                "name": boss["name"].strip(),
                "pin": (parse_tc(boss["at"]) if boss["at"] else None),
                "hold": (float(boss["dur"]) if boss["dur"] else None),
                # None: no second row. "": a placeholder slot. Text: authored.
                "title": None if title is None else title.strip(),
                "attrs": {},
                "lineno": lineno,
            }
            current["lines"].append(entry)
            continue
        tagged = speaker_tag(raw)
        if tagged is not None:
            speaker, rest, attrs = tagged
            shape = LINE.match(f"{speaker}{rest}" if rest[:1] in "@+:"
                               else f"{speaker}: {rest}")
            entry = {
                "kind": "chat",
                "id": None,
                "speaker": speaker,
                "pin": (parse_tc(shape["at"]) if shape["at"] else None),
                "hold": (float(shape["dur"]) if shape["dur"] else None),
                "text": shape["text"].strip(),
                "attrs": dict(attrs),
                "lineno": lineno,
            }
            current["lines"].append(entry)
            continue
        line = LINE.match(raw)
        if line and line["speaker"].strip():
            entry = {
                "kind": "chat",
                "id": line["id"],
                "speaker": line["speaker"].strip(),
                "pin": (parse_tc(line["at"]) if line["at"] else None),
                "hold": (float(line["dur"]) if line["dur"] else None),
                "text": line["text"].strip(),
                "attrs": {},
                "lineno": lineno,
            }
            current["lines"].append(entry)
            continue
        if raw.strip() and not was_blank and entry is not None \
                and entry["kind"] == "chat":
            # THE NEXT LINE OF THE SAME CONVERSATION. Owner, 2026-08-23:
            # "if there is an indent under a pill make it a new line."
            # Before this, such a line was dropped in silence -- about twenty
            # authored lines existed only as text in a file.
            #
            # ADJACENCY is the whole guard, and it is enough. Every editorial
            # note in these files is separated from its pill by a blank line,
            # so notes are untouched (proven: all ten acts resolve
            # byte-identically). Indentation deliberately does NOT matter --
            # the owner writes a continuation both ways, and a rule that
            # depended on whether he happened to indent would silently drop
            # half of them, which is the exact failure this replaces.
            entry = {
                "kind": "chat",
                "id": None,
                "speaker": entry["speaker"],
                "pin": None,
                "hold": None,
                "text": raw.strip(),
                "attrs": {},
                "lineno": lineno,
            }
            current["lines"].append(entry)
            continue
        if raw.strip():
            entry = None
    return blocks


def speaker_tag(raw):
    """``[who] the words`` -> ``(speaker, rest, attrs)``, or ``None``.

    Distinguishing this from the `[an_id]` prefix is the whole job. An id is
    always followed by a speaker and a colon, so a bracket is naming a
    SPEAKER when what follows it either starts the timing (`@`, `+`, `:`) or
    carries no colon at all -- there is no speaker left for the colon to
    belong to.
    """
    tag = SPEAKER_TAG.match(raw)
    if not tag:
        return None
    who, rest = tag["who"].strip(), tag["rest"].strip()
    if not rest:
        return None
    if rest[:1] not in "@+:" and ":" in rest:
        return None            # `[an_id] speaker: words` -- the id form
    attrs = {}
    url = GITHUB_URL.match(who)
    if url:
        # A URL points AT a person; it is not something to put on screen.
        who = url["login"]
        attrs["avatar_login"] = who
    if not who or who.startswith("!") or who.startswith("*"):
        return None
    return who, rest, attrs


def add_attr(attrs, key, raw, list_keys=None):
    """One ``- key: value`` row into an entry's fields.

    Repeating a key builds a list, which is how a card's ``body`` rows keep
    their order, and how a pill carries more than one censor rule. ``[]`` is
    the one piece of punctuation the format needs: a list with nothing in it
    cannot be written as a number of rows, because that number is zero.
    """
    value = scalar(raw)
    if value == "[]" and key not in attrs:
        attrs[key] = []
        return
    if key == "censor":
        match = CENSOR.match(raw.strip())
        value = ({"find": match["find"], "replace": match["replace"]}
                 if match else raw.strip())
    if key in attrs:
        if not isinstance(attrs[key], list):
            attrs[key] = [attrs[key]]
        attrs[key].append(value)
    elif key in (LIST_KEYS if list_keys is None else list_keys):
        attrs[key] = [value]
    else:
        attrs[key] = value


def schedule_block(block, offset, seats=None):
    """One block's lines -> (film_at, hold) each, plus notes.

    ``anchor`` and every pin arrive on the programme clock and leave on the
    act's film clock. The heading seats the first line; every later line
    cascades off its predecessor's read time. A pinned line lands exactly on
    its pin -- slack before it is silence, and a pin earlier than the
    previous line's read time is honoured with the overlap recorded: the
    owner's placement is content, the report says what it cost.

    ``seats`` (from ``seat_lines``) are speech evidence: a line whose words
    match what the characters on screen are saying is seated at that moment
    instead of its cascade position, unless a pin says otherwise. Every seat
    taken -- and every seat a pin overrode -- is reported: always inform the
    operator of improvements.
    """
    lines = block["lines"]
    seats = seats or [None] * len(lines)
    words = [line.get("text") or line.get("name") or "" for line in lines]
    # An explicit `+<seconds>` is the owner stating the hold. It bypasses the
    # readable band entirely, because a migrated pill has to come back at the
    # length it was delivered at -- clamping it would re-time a delivered act
    # under the guise of reading it back.
    holds = [line["hold"] if line.get("hold") is not None else hold_for(word)
             for line, word in zip(lines, words)]
    anchor = round(block["anchor"] - offset, 3)
    at, notes = [None] * len(lines), []
    label = block["label"] or format_tc(block["anchor"])

    def seat_note(i, verb):
        seat = seats[i]
        return (f"line {i + 1} of the {label} block {verb} the shot where "
                f"those words are spoken (source {format_tc(seat['src'])}, "
                f"recovered: {seat['matched']!r}; programme "
                f"{format_tc(seat['film'] + offset)})")

    for i, line in enumerate(lines):
        natural = (anchor if i == 0
                   else round(at[i - 1] + holds[i - 1] + GAP, 3))
        seat = seats[i]
        if line["pin"] is not None:
            at[i] = round(line["pin"] - offset, 3)
            if i == 0 and abs(at[0] - anchor) > 0.005:
                notes.append(
                    f"the {label} block's first line is pinned to "
                    f"{format_tc(line['pin'])} programme, not its ## "
                    f"heading's {format_tc(block['anchor'])}; the pin wins")
            if seat is not None and abs(seat["film"] - at[i]) > 0.5:
                notes.append(seat_note(i, "is pinned away from") +
                             " -- the pin stands")
            if i > 0 and at[i] < natural:
                notes.append(
                    f"line {i + 1} of the {label} block is pinned "
                    f"{round(natural - at[i], 3)}s before the previous line "
                    "clears; the pin is honoured and the two overlap on "
                    "screen")
        elif seat is not None:
            at[i] = seat["film"]
            notes.append(seat_note(i, "is seated on"))
            if i > 0 and at[i] < natural:
                notes.append(
                    f"line {i + 1} of the {label} block's speech-evidence "
                    f"seat is {round(natural - at[i], 3)}s before the "
                    "previous line clears; the evidence is honoured and the "
                    "two overlap on screen")
        else:
            at[i] = natural
    return at, holds, notes


def block_end(act, label):
    """The act-local time right after a labelled block's last pill clears.

    For a builder that must seat something *after* an aside authored in the
    chapter file -- act II's paused conversation, say -- without recomputing
    the block's own schedule of held reads and gaps itself. Raises
    ``KeyError`` when the act has no chapter block with that label, the same
    way ``chapter()`` names what is wired instead of failing silently.
    """
    chap = chapter(act)
    for block in parse(chap.path.read_text(encoding="utf-8")):
        if block["label"] != label:
            continue
        at, holds, _ = schedule_block(
            block, chap.programme_start,
            seats=seat_lines(act, block["lines"]))
        return round(at[-1] + holds[-1] + GAP, 3)
    raise KeyError(f"{act}: no chapter block labelled {label!r}")


def entries(act, *, include_block_labels=False):
    """The act's chapter file -> (plate-manifest chat entries, unresolved).

    Entries carry the same shape scripts/build_efmb_plates.py emits for its
    own chat cards, so the manifest cannot tell which file a line came from.
    A missing chapter file is not an error: it is an act with no authored
    conversation this way yet.

    Copy written PAST the end of the act's picture is not the act's -- it is
    the deck that plays after it, and `deck_entries` below is what reads it.

    ``include_block_labels`` is for an in-memory builder that needs to know
    which chapter block a plate came from -- it stamps a private
    ``_chapter_label`` onto each entry. The default manifest shape never
    carries it: a builder that wants the label must ask for it, and a
    committed manifest must never see a key nothing else writes.
    """
    act_entries, _, unresolved = _split_entries(
        act, include_block_labels=include_block_labels)
    return act_entries, unresolved


def emitted_entries(act):
    """(the plates the act's BUILD emits, unresolved).

    ``entries`` above is the chapter file's own reading of itself. An act
    whose builder MOVES a seat between the file and the manifest -- act II,
    whose `paused` block rebases the pins authored after it and whose
    ``source_anchor`` rows are seated on the frames they name -- resolves to
    something the delivered master does not carry, and every command an
    editor is pointed at (``show``, ``check``) has to describe the film that
    ships rather than the file's raw schedule.

    That mapping belongs to the builder that performs it, so the chapter
    file declares it (``reseat: <path>:<function>`` in the front matter) and
    it is imported lazily, only for the act that has one. Restating the
    builder's arithmetic here would be a second copy of it, and the copy
    nobody rebuilds from is the one that goes stale.

    An act with no hook resolves to exactly ``entries(act)``.
    """
    resolved, unresolved = entries(act, include_block_labels=True)
    reseat, note = _reseater(act)
    if note is not None:
        unresolved.append(note)
    if reseat is None:
        for entry in resolved:
            entry.pop("_chapter_label", None)
        return resolved, unresolved
    return list(reseat(resolved)), unresolved


def _reseater(act):
    """The act builder's seat mapping -> ``(callable or None, note)``.

    Declared by the chapter file rather than wired here, and imported only
    when it is asked for: a general chapter tool must not depend on one
    act's renderer, and that renderer already imports THIS module. The hook
    keeps the dependency one-way.

    A hook that cannot be loaded degrades to no mapping and a recorded note.
    A preview one release out of date is worth more than a traceback in
    front of somebody who only wanted to read their own dialogue back.
    """
    try:
        chap = chapter(act)
    except KeyError:
        return None, None
    declared = chap.fields.get("reseat")
    if not isinstance(declared, str) or not declared.strip():
        return None, None
    target, _, func_name = declared.strip().rpartition(":")
    module_path = REPO_ROOT / target
    try:
        if str(module_path.parent) not in sys.path:
            sys.path.insert(0, str(module_path.parent))
        module = importlib.import_module(module_path.stem)
        return getattr(module, func_name), None
    except Exception as exc:  # noqa: BLE001 -- any import failure degrades
        return None, (f"the declared reseat hook {declared!r} could not be "
                      f"loaded ({exc.__class__.__name__}: {exc}); seats are "
                      "shown as this file schedules them, which is not "
                      "necessarily what the build emits")


def deck_entries(act):
    """The slides that play AFTER the act -> (entries, unresolved).

    An act whose front matter declares ``deck: <label>`` may keep that deck's
    copy at the end of its own chapter file, which is the whole point: the
    words that conclude a scene are edited in the same place as the scene.
    Any block whose heading carries that label is the deck rather than the
    act -- ``## 16:23.000 intermission`` -- so the boundary is written down
    where the copy is, instead of being inferred from a runtime.

    Their ``at`` comes back rebased to the deck's own clock, because a deck
    is rendered as its own film and starts at zero.
    """
    _, deck, unresolved = _split_entries(act)
    return deck, unresolved


def _split_entries(act, *, include_block_labels=False):
    """(the act's plates, the trailing deck's plates, unresolved)."""
    try:
        chap = chapter(act)
    except KeyError:
        return [], [], []
    path = chap.path
    if not path.exists():
        return [], [], []
    offset = chap.programme_start
    film_sec = chap.film_sec
    defaults = chap.defaults
    order = chap.fields.get("field_order")
    order = ([k.strip() for k in order.split(",")] if isinstance(order, str)
             else None)
    blocks = parse(path.read_text(encoding="utf-8"))
    if chap.fields.get("timed") is False:
        resolved, notes = untimed_entries(act, blocks, defaults, order)
        return resolved, [], notes
    # `deck: <label>` in the front matter, matched against a block heading's
    # own label. A deck plays after the act, so its plates are not the act's
    # and never reach the act's manifest.
    deck_label = chap.fields.get("deck")
    out, deck, unresolved = [], [], []
    for b, block in enumerate(blocks, 1):
        if not block["lines"]:
            unresolved.append(
                f"the {block['label'] or format_tc(block['anchor'])} block "
                "has a heading and no lines -- nothing is scheduled for it")
            continue
        at, holds, notes = schedule_block(block, offset,
                                          seats=seat_lines(act,
                                                           block["lines"]))
        unresolved.extend(notes)
        into = (deck if deck_label and block["label"] == deck_label else out)
        for n, (line, start, hold) in enumerate(zip(block["lines"],
                                                    at, holds), 1):
            if line["kind"] == "chat":
                from tools.identity import RESERVED_SPEAKERS, UnknownPerson, canonical_login
                if line["speaker"] not in RESERVED_SPEAKERS:
                    try:
                        canonical_login(line["speaker"])
                    except UnknownPerson:
                        unresolved.append(
                            f"legacy-speaker: {line['speaker']} (no GitHub login "
                            "is inferred)")
            entry = build_entry(act, b, n, line, start, hold,
                                defaults, order)
            if include_block_labels:
                # Private to an in-memory builder -- never part of the
                # manifest shape scripts/build_efmb_plates.py emits, so a
                # caller has to ask for it by name.
                entry["_chapter_label"] = (
                    block["label"] or format_tc(block["anchor"]))
            into.append(entry)
        if into is deck:
            # Running off the picture is what a slide DOES. The note below
            # would fire on every one of them and mean nothing.
            continue
        end = at[-1] + holds[-1] + offset
        if film_sec is not None and (at[0] < 0 or end - offset > film_sec):
            unresolved.append(
                f"the {block['label'] or format_tc(block['anchor'])} block "
                f"runs off the act's picture ({format_tc(at[0])} -> "
                f"{format_tc(at[-1] + holds[-1])} film); it is scheduled "
                "anyway so the conversation is reviewable")
    if deck:
        base = deck[0]["at"]
        for slide in deck:
            slide["at"] = round(slide["at"] - base, 3)
            if "fade_out_at" in slide:
                slide["fade_out_at"] = round(slide["fade_out_at"] - base, 3)
    return out, deck, unresolved


def untimed_entries(act, blocks, defaults, order):
    """Cards in a chapter that has no clock: order is the only timing there is.

    Nothing is scheduled and no ``at`` or ``dur`` is invented. A card here
    says how long it wants relative to its neighbours -- ``dur_sec`` on act
    VIII's credits is a WEIGHT, scaled at build time into the window the
    comic reveal leaves -- so a pin would be a number nobody could honour.
    """
    out, unresolved = [], []
    for b, block in enumerate(blocks, 1):
        if not block["lines"]:
            unresolved.append(f"the {block['label']} block has a heading and "
                              "no cards -- nothing is written for it")
            continue
        for n, line in enumerate(block["lines"], 1):
            out.append(build_entry(act, b, n, line, None, None,
                                   defaults, order))
    return out, unresolved


# What an entry is before the chapter file says anything. A front-matter
# `defaults:` section merges over these, and a `null` there REMOVES a field:
# an act whose delivered pills never carried `copy_source` has to come back
# without one, or the takeover is not the lossless thing it claims to be.
CHAT_BASE = {
    "kind": "chat", "position": "left", "copy_source": "owner_supplied",
    "text_source": "auto", "avatar": "auto", "avatar_url": "auto",
}
BOSS_BASE = {
    "kind": "miniboss", "position": "boss", "copy_source": "owner_supplied",
    "text_source": "owner_supplied",
}


def build_entry(act, b, n, line, start, hold, defaults, order=None):
    """One parsed row -> the plate the manifest carries for it."""
    base = dict(BOSS_BASE if line["kind"] == "boss" else CHAT_BASE)
    if line["kind"] == "card":
        base = {"kind": line["card_kind"]}
    base.update(defaults or {})
    if line["kind"] == "card":
        # A card names its own kind on its own row. The act default -- almost
        # always `chat`, because most rows in a chapter file are dialogue --
        # must never quietly turn a status card into a pill. A kind of `-` is
        # a card that carries NO kind field: act VIII's credits are told
        # apart by their role, and never had one.
        base["kind"] = line["card_kind"]
        if line["card_kind"] == "-":
            base.pop("kind")

    entry = {"id": line["id"] or _generated_id(act, b, n, line),
             "at": start, "dur": hold}
    if start is None:
        # An untimed chapter. The card has no clock of its own, so it gets no
        # `at`/`dur` fields at all rather than a pair of nulls that would
        # read as "nought seconds, held for nothing".
        del entry["at"], entry["dur"]
        if not line["id"]:
            # Nor an invented id. Act VIII's credit cards are addressed by
            # their order and nothing else; minting one here would write a
            # new field into a delivered record to no purpose.
            del entry["id"]

    if line["kind"] == "chat":
        # The release train still carries literal pre-migration speakers.
        # Keep their on-screen spelling until the owning act normalizes them.
        entry["speaker"] = line["speaker"]
        entry["text"] = line["text"]
    elif line["kind"] == "boss":
        entry["name"] = line["name"]
        if line["title"]:
            entry["title"] = line["title"]
        elif line["title"] == "":
            # The slot exists before its words do: lorem, credited to
            # nobody, seeded exactly as the build script seeded it so the
            # takeover changes no pixel.
            entry["title"] = placeholder.lorem(28, seed=entry["id"])
            entry["title_source"] = "placeholder"

    for key, value in base.items():
        if value is None or key in entry:
            continue
        resolved = _resolve_default(key, value, line, entry)
        if resolved is not None:
            entry[key] = resolved

    attrs = dict(line["attrs"])
    portrait = _portrait({key: attrs.pop(key) for key in PORTRAIT_KEYS
                          if key in attrs})
    for key, value in attrs.items():
        # An explicit `- key: null` DELETES a field the defaults supplied,
        # which is how one card opts out of the fades every pill around it
        # carries. Writing a real null into a manifest is never what is meant.
        if value is None:
            entry.pop(key, None)
        else:
            entry[key] = value
    if portrait is not None:
        # A named portrait overrules whatever the speaker's own login
        # derived, including deriving nothing: the row said who this is.
        entry.pop("avatar", None)
        entry.pop("avatar_url", None)
        entry.update(portrait)

    if "at" in entry:
        entry["fade_out_at"] = _derive_fade_out_at(
            entry.get("fade_out_at"), entry)
    if entry.get("fade_out_at") is None:
        entry.pop("fade_out_at", None)
    return _ordered(entry, order)


def _derive_fade_out_at(value, entry):
    """``derived`` -> the moment this plate starts fading, from its own clock.

    Bare ``derived`` is ``at + dur - fade_out``: the fade ENDS as the plate's
    window does. ``derived 0.6`` subtracts 0.6 instead, because some acts were
    timed to start the fade a fade-IN's length early and that is what is on
    screen. The number is stated in the act's front matter rather than derived
    from which field it happens to equal, since those two being the same
    length is a coincidence, not a rule.
    """
    if not isinstance(value, str) or not value.startswith("derived"):
        return value
    lead = value[len("derived"):].strip()
    back = float(lead) if lead else entry.get("fade_out", 0)
    return round(entry["at"] + entry["dur"] - back, 3)


def _generated_id(act, b, n, line):
    if line["kind"] == "boss":
        return f"ch_{act.lower()}_{b}_{n}_boss"
    if line["kind"] == "card":
        return f"ch_{act.lower()}_{b}_{n}_{line['card_kind']}"
    slug = re.sub(r"[^a-z0-9]+", "_", line["speaker"].lower()).strip("_")
    return f"ch_{act.lower()}_{b}_{n}_{slug}"


def _resolve_default(key, value, line, entry):
    """A default that says ``auto`` works the value out from the line."""
    if value != "auto":
        return value
    if key == "text_source":
        return "owner_supplied" if line.get("text") else "placeholder"
    from tools.identity import UnknownPerson, canonical_login
    try:
        canonical_login(line.get("speaker") or "")
    except UnknownPerson:
        # Existing chapters are literal pre-migration authoring. Keep a
        # previously-rendered lowercase portrait stable while audit reports the
        # speaker; newly normalized chapters resolve through People above.
        if not _LEGACY_LOGIN_SHAPE.match(line.get("speaker") or ""):
            return None
    if key == "avatar":
        return f"renders/avatars/{line['speaker']}.png"
    if key == "avatar_url":
        return f"https://github.com/{line['speaker']}.png?size=256"
    return None


def _portrait(named):
    """``{cast: key}`` or ``{avatar_login: login}`` -> the plate's picture.

    Returns ``None`` when the row named nobody, so the speaker's own login
    still derives what it always did. Returns an EMPTY dict when the row
    named somebody with no portrait on record -- that is an answer, and it
    is the answer that keeps a pill's drawn crest instead of inventing a URL
    for a person who has none.
    """
    if not named:
        return None
    from tools.identity import UnknownPerson, canonical_login, person_for_character
    try:
        login = named.get("avatar_login")
        if login:
            canonical_login(login)
            return {"avatar": f"renders/avatars/{login}.png",
                    "avatar_url": f"https://github.com/{login}.png?size=256"}
        key = named.get("cast", "")
        person = person_for_character(key)
    except UnknownPerson:
        return {}
    if person and (person.plate or {}).get("avatar"):
        return {"avatar": f"renders/avatars/{key}.png",
                "avatar_url": person.plate["avatar"]}
    # A raw pre-migration chapter can still carry a historical portrait key.
    # It is audited as a legacy override and does not identify the speaker.
    import yaml
    with (REPO_ROOT / "vocab" / "casting.yaml").open(encoding="utf-8") as fh:
        legacy = ((yaml.safe_load(fh) or {}).get("ensemble") or {}) \
            .get("legacy_titles", {}).get(key, {})
    if not legacy.get("avatar"):
        return {}
    return {"avatar": f"renders/avatars/{key}.png", "avatar_url": legacy["avatar"]}


def _ordered(entry, order):
    """The plate's keys in the act's declared order.

    A manifest is read by people as well as regenerated by machines, so an
    act that has always written ``id, kind, position, speaker, text`` keeps
    writing it that way. Keys the order does not name follow, in the order
    the file gave them.
    """
    if not order:
        return entry
    out = {key: entry[key] for key in order if key in entry}
    out.update({key: value for key, value in entry.items() if key not in out})
    return out


# ---------------------------------------------------------------------------
# EXTRACT: the one-shot lift, and CHECK: the report that keeps it honest.
#
# An act with 142 plates is not hand-transcribed into Markdown; it is lifted
# by a tool that writes every field it cannot derive, so the round trip comes
# back byte for byte. After that the Markdown is the source and the manifest
# is output -- `check` is what says so out loud when the two disagree.
# ---------------------------------------------------------------------------

# Written by the entry's own row rather than as a `- field:` underneath it.
STRUCTURAL = {"id", "at", "dur", "kind", "speaker", "text", "name"}


def manifest_plates(act):
    """The act's committed plates, in the order the manifest holds them."""
    chap = chapter(act)
    doc = chap.manifest_doc()
    if doc is None:
        return []
    return doc.get(chap.plates_key) or []


DERIVED_COPY = frozenset({"casting", "brief"})
"""Plates whose words are NOT the owner's to type here.

A ``casting`` or ``brief`` nameplate resolves from ``vocab/casting.yaml`` and
the act's brief, which are already the one place those names live. Copying
them into a chapter file would make a second one, and the second one is always
the one that goes wrong -- these are claims about real people. The chapter
file leaves them alone; ``sync`` carries them through untouched.
"""


def extract(act, gap=3.0):
    """The act's committed manifest -> the chapter file that reproduces it.

    Every plate is pinned and given an explicit hold, so nothing re-times on
    the way through: this is a change of where the words live, not of when
    they are on screen. Plates more than ``gap`` seconds apart start a new
    ``##`` block, which is only about how the file reads.
    """
    chap = chapter(act)
    offset = chap.programme_start
    defaults = chap.defaults or {}
    plates = [p for p in manifest_plates(act)
              if p.get("copy_source") not in DERIVED_COPY]
    header, _ = _split_header(chap.path.read_text(encoding="utf-8"))
    out = [header.rstrip("\n"), ""]
    previous_end = None
    for plate in plates:
        at, dur = plate.get("at", 0.0), plate.get("dur", 0.0)
        if previous_end is None or at - previous_end > gap:
            out.append(f"## {format_tc_ms(at + offset)}")
            out.append("")
        previous_end = at + dur
        out.extend(_extract_entry(plate, offset, defaults))
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def _extract_entry(plate, offset, defaults):
    """One committed plate -> the rows in the chapter file that restore it.

    Written by prediction rather than by rule: build the entry the row alone
    would produce, then write a ``- field: value`` for every difference. That
    way extract cannot fall out of step with ``build_entry`` -- whatever the
    defaults already derive is silently absent, and whatever they do not is
    always present.
    """
    at, dur = plate.get("at", 0.0), plate.get("dur", 0.0)
    pin = f"@ {format_tc_ms(at + offset)}"
    hold = f"+{_num(dur)}"
    ident = f"[{plate['id']}] "
    kind = plate.get("kind")
    if kind == "miniboss":
        title = plate.get("title")
        row = f"! {ident}{plate.get('name', '')} {pin} {hold}"
        if title is not None:
            row += f" | {title}"
        line = {"kind": "boss", "id": plate["id"], "name": plate.get("name", ""),
                "title": title, "pin": at + offset, "hold": dur, "attrs": {}}
    elif "speaker" in plate or kind == "chat":
        row = (f"{ident}{plate.get('speaker', '')} {pin} {hold}: "
               f"{plate.get('text', '')}")
        line = {"kind": "chat", "id": plate["id"],
                "speaker": plate.get("speaker", ""),
                "text": plate.get("text", ""),
                "pin": at + offset, "hold": dur, "attrs": {}}
    else:
        row = f"* {ident}{kind or 'plate'} {pin} {hold}"
        line = {"kind": "card", "id": plate["id"], "card_kind": kind or "plate",
                "text": "", "pin": at + offset, "hold": dur, "attrs": {}}

    predicted = build_entry("x", 0, 0, line, at, dur, defaults)
    rows = [row]
    portrait = _portrait_row(plate, predicted)
    for key, value in plate.items():
        if key in STRUCTURAL or predicted.get(key) == value:
            continue
        if portrait and key in ("avatar", "avatar_url"):
            continue
        rows.extend(f"  - {key}: {item}" for item in _attr_rows(key, value))
    if portrait:
        rows.append(f"  - {portrait}")
    for key in predicted:
        if key not in plate and key not in STRUCTURAL:
            rows.append(f"  - {key}: null")
    return rows


def _portrait_row(plate, predicted):
    """The ``cast:``/``avatar_login:`` row that restores a plate's picture.

    A lift that wrote the URL out longhand would move a casting fact into a
    second file, so the picture is described by WHO it is of. ``None`` when
    the speaker's own login already derives it, or when no naming reproduces
    it -- in which case the plain field rows are still written and nothing
    is lost.
    """
    avatar, url = plate.get("avatar"), plate.get("avatar_url")
    if not avatar or not url:
        return None
    if predicted.get("avatar") == avatar and predicted.get("avatar_url") == url:
        return None
    key = str(avatar).rsplit("/", 1)[-1].removesuffix(".png")
    from tools.identity import UnknownPerson, canonical_login
    try:
        canonical = canonical_login(key)
    except UnknownPerson:
        return None
    if url == f"https://github.com/{key}.png?size=256":
        return f"avatar_login: {canonical}"
    return None


def _attr_rows(key, value):
    """A plate field -> the ``- key: value`` rows that restore it."""
    if key == "censor" and isinstance(value, list):
        return [f"{item['find']} -> {item['replace']}" for item in value]
    if isinstance(value, list):
        return [_scalar_out(item) for item in value] or ["[]"]
    return [_scalar_out(value)]


def _scalar_out(value):
    """A value written so ``scalar`` reads it back as the same thing."""
    if value is True or value is False:
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return _num(value)
    text = str(value)
    # A string that would come back as a number, a bool or nothing has to be
    # quoted, or a card whose subtitle is the year 2026 returns as an int.
    if text.strip() != text or scalar(text) != text:
        return f'"{text}"'
    return text


def _num(value):
    """A number written so it reads back as the same number AND the same type.

    ``4.0`` must not become ``4``: the manifest is regenerated from this, and
    an angle that was a float coming back as an int rewrites a line of a
    delivered record for no reason at all.
    """
    if isinstance(value, int):
        return str(value)
    return repr(round(float(value), 6))


def _split_header(text):
    """A chapter file -> (everything before the first block, the blocks)."""
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if HEADING.match(line.rstrip("\n")):
            return "".join(lines[:i]), "".join(lines[i:])
    return text, ""


def sync(act, write=False):
    """Write the act's chapter file back into its manifest.

    The manifest is an OUTPUT once an act's chapter file owns its plates: the
    words live in the Markdown, and this is what puts them where the build
    reads them. Everything else in the manifest -- the trim, the measured
    letterbox, the encode parameters -- is untouched, because none of it is
    copy.

    An act whose chapter file authors only PART of its plates (act II, whose
    builder generates the rest) declares no ``owns_plates`` and is skipped:
    overwriting there would delete every plate the builder contributes.
    """
    chap = chapter(act)
    path = chap.manifest_path()
    if path is None:
        raise KeyError(f"act {act} has no manifest to write to")
    raw = path.read_text(encoding="utf-8")
    if not chap.fields.get("owns_plates"):
        return raw, []
    doc = json.loads(raw)
    plates, unresolved = entries(act)
    if not plates:
        return raw, unresolved
    before = doc.get(chap.plates_key) or []
    merged, notes = _merge_plates(before, plates)
    unresolved.extend(notes)
    doc[chap.plates_key] = merged
    if merged == before:
        # The manifest already says exactly this. Leaving the file alone --
        # rather than round-tripping it through a serialiser -- keeps the
        # hand-formatting these records were written with, and keeps a
        # delivered act off the stale list for whitespace nobody can see.
        return raw, unresolved
    text = json.dumps(doc, indent=_json_indent(raw), ensure_ascii=False) + "\n"
    if write and text != raw:
        path.write_text(text, encoding="utf-8")
    return text, unresolved


def _check_in_order(resolved, committed):
    """Drift for a run of cards that has no ids -- position is the identity.

    Act VIII's credit cards are addressed by their order in the run and by
    nothing else, so "the third card changed" is the most that can honestly
    be said about them.
    """
    notes = []
    if len(resolved) != len(committed):
        notes.append(f"the chapter file has {len(resolved)} card(s) and the "
                     f"manifest has {len(committed)}")
    for n, (new, old) in enumerate(zip(resolved, committed), 1):
        for key in sorted(set(new) | set(old)):
            if new.get(key) != old.get(key):
                notes.append(f"card {n}.{key}: chapter file says "
                             f"{new.get(key)!r}, manifest says "
                             f"{old.get(key)!r}")
    return notes


def _merge_plates(before, authored):
    """The manifest's plates with the chapter file's words put back, by id.

    A chapter file owns the plates it authors, NOT the whole array: act VI's
    pills sit in the same list as four ``brief`` nameplates that resolve from
    the roster. Replacing the array would delete them, so every DERIVED plate
    the chapter file does not name is carried through in the position it
    already holds, and a newly written line lands beside the plate it follows
    in time.

    A NON-derived plate the chapter no longer authors is dropped, with a
    note: carrying it through made deletion inexpressible, which is how
    act III's retirement pair survived its move to act II (2026-08-24).
    Deleting is reported, never silent.
    """
    if any("id" not in plate for plate in authored):
        # A run with no ids is owned outright: there is nothing to merge
        # against, and its order IS its content.
        return authored, []
    by_id = {plate.get("id"): plate for plate in authored}
    merged, notes = [], []
    for plate in before:
        if plate.get("id") in by_id:
            merged.append(by_id.pop(plate.get("id")))
        elif plate.get("copy_source") in DERIVED_COPY:
            merged.append(plate)
        else:
            notes.append(f"{plate.get('id')}: dropped -- no longer authored "
                         "in the chapter file, and not derived copy")
    for plate in by_id.values():
        if plate.get("copy_source") in DERIVED_COPY:
            notes.append(f"{plate.get('id')}: a chapter file cannot author "
                         f"{plate['copy_source']} copy; it is derived")
            continue
        at = plate.get("at", 0.0)
        index = len(merged)
        for position, existing in enumerate(merged):
            if existing.get("at", 0.0) > at:
                index = position
                break
        merged.insert(index, plate)
    return merged, notes


def _json_indent(raw):
    """The indent the file already uses, so regenerating it moves no line.

    The manifests were written by different hands at different times and do
    not agree on one or two spaces. Reformatting them all to match would put
    a thousand-line diff in front of a one-word copyedit.
    """
    for line in raw.splitlines()[1:]:
        stripped = line.lstrip(" ")
        if stripped and stripped != "}":
            return len(line) - len(stripped)
    return 1


def check(act):
    """Where the chapter file and the committed manifest disagree.

    A report, not a gate: the caller decides whether a difference matters.
    ``main``'s ``--check`` is the only thing that turns one into an exit
    code, the same posture as ``tools/placeholder.py``.
    """
    chap = chapter(act)
    if chap.manifest_path() is None:
        return []
    committed = manifest_plates(act)
    # The seats the BUILD emits, not this file's raw schedule: an act that
    # reseats a line (act II) would otherwise report its own accepted
    # mapping as ten lines of permanent drift, and real drift would be
    # indistinguishable from it.
    resolved, _ = emitted_entries(act)
    if not resolved and any(p.get("copy_source") not in DERIVED_COPY
                            for p in committed):
        # A file that resolves to nothing used to report nothing, which is
        # how a chapter whose grammar had stopped matching its own lines
        # looked exactly like a chapter in perfect agreement.
        return [f"the chapter file resolves to no plates at all, and the "
                f"manifest holds {len(committed)} -- its lines are not "
                f"being read"]
    if any("id" not in plate for plate in committed):
        return _check_in_order(resolved, committed)
    by_id = {plate["id"]: plate for plate in committed}
    notes = []
    for plate in resolved:
        old = by_id.get(plate["id"])
        if old is None:
            notes.append(f"{plate['id']} is authored in the chapter file and "
                         "is not in the committed manifest")
            continue
        for key in sorted(set(plate) | set(old)):
            if plate.get(key) != old.get(key):
                notes.append(f"{plate['id']}.{key}: chapter file says "
                             f"{plate.get(key)!r}, manifest says "
                             f"{old.get(key)!r}")
    authored = {plate["id"] for plate in resolved}
    for plate in committed:
        if plate["id"] in authored:
            continue
        if not chap.fields.get("owns_plates"):
            # A chapter that declares itself a PARTIAL author -- act II, whose
            # builder still generates most of its plates -- is not drifting by
            # having plates it does not author. Listing all 130 of them would
            # bury the two lines that mean something.
            continue
        if plate.get("copy_source") in DERIVED_COPY:
            # A nameplate resolving from the roster is SUPPOSED to be absent
            # here. Reporting it would train the reader to ignore this list,
            # which is the only way this report stops working.
            continue
        notes.append(f"{plate['id']} is in the manifest and not in the "
                     "chapter file -- it is still built elsewhere")
    return notes


def sync_manifest(path, write=True):
    """Bring one plate manifest current with whichever chapter file owns it.

    Builders address manifests by path, not by act -- ``build_ending_overlays``
    renders whichever movement it is pointed at -- so this resolves the act
    backwards from the file. A manifest nobody has migrated is left alone and
    reports nothing: not every manifest has a chapter file yet, and that is a
    punch-list item, never a stop.
    """
    path = Path(path).resolve()
    for chap in discover().values():
        if chap.manifest_path() and chap.manifest_path().resolve() == path:
            return sync(chap.act, write=write)[1]
    return []


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    s = sub.add_parser("show", help="print the schedule a chapter resolves to")
    s.add_argument("act")
    e = sub.add_parser("extract",
                       help="write an act's chapter file from its manifest")
    e.add_argument("act")
    e.add_argument("--write", action="store_true",
                   help="write the file rather than printing it")
    c = sub.add_parser("check",
                       help="report drift between a chapter file and its "
                            "manifest")
    c.add_argument("act", nargs="?")
    c.add_argument("--check", action="store_true",
                   help="exit non-zero on drift, for gating a final cut")
    sub.add_parser("list", help="every act with a chapter file")
    y = sub.add_parser("sync",
                       help="write a chapter file back into its manifest")
    y.add_argument("act", nargs="?")
    y.add_argument("--write", action="store_true",
                   help="write the manifest rather than reporting drift")
    args = ap.parse_args(argv)

    if args.command == "sync":
        acts = [args.act] if args.act else sorted(discover())
        changed = 0
        for act in acts:
            chap = discover().get(act)
            if chap is None or chap.manifest_path() is None:
                continue
            text, unresolved = sync(act, write=args.write)
            for note in unresolved:
                print(f"{act}: {note}", file=sys.stderr)
            if text != chap.manifest_path().read_text(encoding="utf-8"):
                changed += 1
                print(f"{act}: {chap.manifest} is out of date with "
                      f"{chap.path.relative_to(REPO_ROOT)}")
            elif args.write:
                print(f"{act}: {chap.manifest} is current")
        return 1 if changed and not args.write else 0

    if args.command == "list":
        found = discover()
        if not found:
            print("no chapter files yet")
            return 0
        for act, chap in sorted(found.items()):
            film = chap.film_sec
            print(f"{act:>4}  {chap.path.relative_to(REPO_ROOT)}  "
                  f"starts {format_tc(chap.programme_start)} programme, "
                  f"film {format_tc(film) if film else '(unknown)'}  "
                  f"-> {chap.manifest or '(no manifest)'}")
        return 0

    if args.command == "extract":
        text = extract(args.act)
        if not args.write:
            print(text, end="")
            return 0
        path = chapter(args.act).path
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path.relative_to(REPO_ROOT)}")
        return 0

    if args.command == "check":
        acts = [args.act] if args.act else sorted(discover())
        drifted = 0
        for act in acts:
            notes = check(act)
            for note in notes:
                print(f"{act}: {note}")
            drifted += len(notes)
        if not drifted:
            print(f"{len(acts)} chapter file(s) resolve to their manifests")
        return 1 if (drifted and args.check) else 0

    if args.command == "show":
        chap = chapter(args.act)
        path, offset = chap.path, chap.programme_start
        blocks = parse(path.read_text(encoding="utf-8"))
        if not blocks:
            print(f"{path}: no conversation blocks yet -- "
                  "add one as `## <programme time>` followed by "
                  "`Speaker: line` rows")
            return 0
        # `@ <programme time>` is the clock the owner scrubs, so this has to
        # print the seat the BUILD emits. Act II moves two classes of line
        # between this file and its manifest; showing the raw schedule sent
        # an editor to a timecode 47 s from the picture they meant to nudge.
        emitted, notes = emitted_entries(args.act)
        for note in notes:
            print(f"  NOTE: {note}")
        seats = {e["id"]: e for e in emitted if "id" in e}
        for b, block in enumerate(blocks, 1):
            at, holds, notes = schedule_block(
                block, offset, seats=seat_lines(args.act, block["lines"]))
            label = f"  # {block['label']}" if block["label"] else ""
            print(f"## {format_tc(block['anchor'])}{label}")
            for n, (line, start, hold) in enumerate(
                    zip(block["lines"], at, holds), 1):
                pin = " (pinned)" if line["pin"] is not None else ""
                seat = seats.get(line["id"]
                                 or _generated_id(args.act, b, n, line))
                if seat is not None and seat.get("at") is not None:
                    if start is None or abs(seat["at"] - start) > 5e-4:
                        # The builder seated this somewhere else. Say so:
                        # an unexplained clock is how a preview stops being
                        # believed.
                        pin += " (reseated by the build)"
                    start, hold = seat["at"], seat.get("dur", hold)
                if line["kind"] == "boss":
                    what = f"! {line['name']}"
                elif line["kind"] == "card":
                    what = (f"* {line['card_kind']}: "
                            + " / ".join(str(v) for v in line["attrs"].values()
                                         if isinstance(v, str))[:60])
                else:
                    what = f"{line['speaker']}: {line['text']}"
                print(f"  {format_tc(start + offset)} programme / "
                      f"{format_tc(start)} film, up {hold:.2f}s{pin}  {what}")
            for note in notes:
                print(f"  NOTE: {note}")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
