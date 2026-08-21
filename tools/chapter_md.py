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
# `Speaker: line`, with three optional prefixes/suffixes that exist so a
# migrated pill reproduces exactly: `[an_id]` binds the line to the plate
# that id already names, `@ <time>` pins it, and `+<seconds>` states the
# hold instead of deriving it from read speed.
LINE = re.compile(
    rf"^(?:\[(?P<id>[A-Za-z0-9_.-]+)\]\s*)?"
    rf"(?P<speaker>[^:@\[\s][^:@]*?)"
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
    rf"^\*\s+(?:\[(?P<id>[A-Za-z0-9_.-]+)\]\s*)?(?P<kind>[a-z][a-z0-9_]*)"
    rf"(?:\s*@\s*(?P<at>{TIME}))?"
    rf"(?:\s*\+\s*(?P<dur>[0-9]+(?:\.[0-9]+)?))?\s*$")
# A field of the entry above it. Repeating a key builds a list, which is how
# a card's `body` rows keep their order without any punctuation to count.
ATTR = re.compile(r"^\s*-\s+(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*:\s?(?P<value>.*)$")
LOGIN_SHAPE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")

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
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    for end, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            break
    else:
        raise ValueError("front matter opens with `---` and never closes")
    fields, section = {}, None
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[:1] in " \t" and section is not None:
            key, _, value = raw.strip().partition(":")
            fields[section][key.strip()] = scalar(value.strip())
            continue
        key, _, value = raw.partition(":")
        key, value = key.strip(), value.strip()
        if not value:
            section = key
            fields[key] = {}
            continue
        section = None
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
        memory.
        """
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
    blocks, current, entry = [], None, None
    for lineno, raw in enumerate(text.splitlines(), 1):
        heading = HEADING.match(raw)
        if heading:
            current = {
                "anchor": parse_tc(heading["at"]),
                "label": heading["label"].strip(),
                "lineno": lineno,
                "lines": [],
            }
            blocks.append(current)
            entry = None
            continue
        if raw.startswith("##"):
            raise ValueError(
                f"line {lineno}: a block heading is `## <time>` -- "
                f"could not read a time in {raw!r}")
        if current is None:
            continue
        attr = ATTR.match(raw)
        if attr and entry is not None:
            add_attr(entry["attrs"], attr["key"], attr["value"])
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
        if raw.strip():
            entry = None
    return blocks


def add_attr(attrs, key, raw):
    """One ``- key: value`` row into an entry's fields.

    Repeating a key builds a list, which is how a card's ``body`` rows keep
    their order, and how a pill carries more than one censor rule.
    """
    value = scalar(raw)
    if key == "censor":
        match = CENSOR.match(raw.strip())
        value = ({"find": match["find"], "replace": match["replace"]}
                 if match else raw.strip())
    if key in attrs:
        if not isinstance(attrs[key], list):
            attrs[key] = [attrs[key]]
        attrs[key].append(value)
    elif key in LIST_KEYS:
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


def entries(act):
    """The act's chapter file -> (plate-manifest chat entries, unresolved).

    Entries carry the same shape scripts/build_efmb_plates.py emits for its
    own chat cards, so the manifest cannot tell which file a line came from.
    A missing chapter file is not an error: it is an act with no authored
    conversation this way yet.
    """
    try:
        chap = chapter(act)
    except KeyError:
        return [], []
    path = chap.path
    if not path.exists():
        return [], []
    offset = chap.programme_start
    film_sec = chap.film_sec
    defaults = chap.defaults
    order = chap.fields.get("field_order")
    order = ([k.strip() for k in order.split(",")] if isinstance(order, str)
             else None)
    blocks = parse(path.read_text(encoding="utf-8"))
    out, unresolved = [], []
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
        for n, (line, start, hold) in enumerate(zip(block["lines"],
                                                    at, holds), 1):
            out.append(build_entry(act, b, n, line, start, hold,
                                   defaults, order))
        end = at[-1] + holds[-1] + offset
        if film_sec is not None and (at[0] < 0 or end - offset > film_sec):
            unresolved.append(
                f"the {block['label'] or format_tc(block['anchor'])} block "
                f"runs off the act's picture ({format_tc(at[0])} -> "
                f"{format_tc(at[-1] + holds[-1])} film); it is scheduled "
                "anyway so the conversation is reviewable")
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

    entry = {"id": line["id"] or _generated_id(act, b, n, line),
             "at": start, "dur": hold}

    if line["kind"] == "chat":
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

    entry.update(line["attrs"])

    if entry.get("fade_out_at") == "derived":
        entry["fade_out_at"] = round(
            entry["at"] + entry["dur"] - entry.get("fade_out", 0), 3)
    return _ordered(entry, order)


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
    speaker = line.get("speaker") or ""
    if not LOGIN_SHAPE.match(speaker):
        return None
    if key == "avatar":
        return f"renders/avatars/{speaker}.png"
    if key == "avatar_url":
        return f"https://github.com/{speaker}.png?size=256"
    return None


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
    plates = manifest_plates(act)
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
    for key, value in plate.items():
        if key in STRUCTURAL or predicted.get(key) == value:
            continue
        rows.extend(f"  - {key}: {item}" for item in _attr_rows(key, value))
    for key in predicted:
        if key not in plate and key not in STRUCTURAL:
            rows.append(f"  - {key}: null")
    return rows


def _attr_rows(key, value):
    """A plate field -> the ``- key: value`` rows that restore it."""
    if key == "censor" and isinstance(value, list):
        return [f"{item['find']} -> {item['replace']}" for item in value]
    if isinstance(value, list):
        return [_scalar_out(item) for item in value]
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
    """A number as short as it can be written without changing it."""
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return repr(round(float(value), 6)).rstrip("0").rstrip(".")


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
    doc[chap.plates_key] = plates
    text = json.dumps(doc, indent=_json_indent(raw), ensure_ascii=False) + "\n"
    if write and text != raw:
        path.write_text(text, encoding="utf-8")
    return text, unresolved


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
    resolved, _ = entries(act)
    if not resolved:
        return []
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
        if plate["id"] not in authored:
            notes.append(f"{plate['id']} is in the manifest and not in the "
                         "chapter file -- it is still built elsewhere")
    return notes


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
        for block in blocks:
            at, holds, notes = schedule_block(
                block, offset, seats=seat_lines(args.act, block["lines"]))
            label = f"  # {block['label']}" if block["label"] else ""
            print(f"## {format_tc(block['anchor'])}{label}")
            for line, start, hold in zip(block["lines"], at, holds):
                pin = " (pinned)" if line["pin"] is not None else ""
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
