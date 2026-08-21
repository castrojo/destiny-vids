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

# WHERE EACH ACT STARTS IN THE PROGRAMME, in seconds. Committed constants
# with the derivation stated, the MEGACUT_OFFSET pattern from
# scripts/build_efmb_plates.py: recompute when the running order's timings
# change and state the new derivation.
#
#   II: prologue 101.200 (megacut.json item 0 `dur`) + act I 116.200
#       (trim 2.000 -> 118.200) + Perfume movement 2, 66.400
#       (source 93.000 -> 159.400) = 283.800 -- verified against the
#       seven-days-to-the-wolves-v4.2 dry run on 2026-08-20.
ACT_PROGRAMME_START = {"II": 283.800}

# Each act's film length, for the "runs off the picture" note. II: the
# committed manifest's _film_sec.
ACT_FILM_SEC = {"II": 355.468}

CHAPTER_FILES = {"II": "chapters/II-endless-forms.md"}

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
LINE = re.compile(
    rf"^(?P<speaker>[^:@\s][^:@]*?)"
    rf"(?:\s*@\s*(?P<at>{TIME}))?\s*:\s*(?P<text>.*)$")
# The red splash -- the boss bar. `! NAME` for the bar alone,
# `! NAME | a second row` to author its title, `! NAME |` to keep a title
# SLOT (rendered as lorem credited to nobody until the words exist), and
# `! [the_id] NAME` to keep an existing card's id when the Markdown takes
# over a seat the build script used to hold.
BOSS = re.compile(
    rf"^!\s+(?:\[(?P<id>[a-z0-9_]+)\]\s*)?(?P<name>[^@|]+?)"
    rf"(?:\s*@\s*(?P<at>{TIME}))?\s*(?:\|\s*(?P<title>.*?))?\s*$")
LOGIN_SHAPE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


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
    rel = CHAPTER_FILES.get(act)
    if rel is None:
        raise KeyError(
            f"no chapter file is wired for act {act!r}; wired: "
            + ", ".join(sorted(CHAPTER_FILES)))
    return REPO_ROOT / rel


def parse(text):
    """Chapter Markdown -> blocks of ``{anchor, label, lines}``.

    A block is one ``## <time>`` heading and the ``Speaker: text`` lines
    under it. Everything else -- instructions, commentary, examples indented
    into code blocks -- is ignored, so the file reads as a document first.
    """
    blocks, current = [], None
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
            continue
        if raw.startswith("##"):
            raise ValueError(
                f"line {lineno}: a block heading is `## <time>` -- "
                f"could not read a time in {raw!r}")
        if current is None:
            continue
        boss = BOSS.match(raw)
        if boss:
            title = boss["title"]
            current["lines"].append({
                "kind": "boss",
                "id": boss["id"],
                "name": boss["name"].strip(),
                "pin": (parse_tc(boss["at"]) if boss["at"] else None),
                # None: no second row. "": a placeholder slot. Text: authored.
                "title": None if title is None else title.strip(),
                "lineno": lineno,
            })
            continue
        line = LINE.match(raw)
        if line and line["speaker"].strip():
            current["lines"].append({
                "kind": "chat",
                "speaker": line["speaker"].strip(),
                "pin": (parse_tc(line["at"]) if line["at"] else None),
                "text": line["text"].strip(),
                "lineno": lineno,
            })
    return blocks


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
    words = [line["text"] if line["kind"] == "chat" else line["name"]
             for line in lines]
    holds = [hold_for(word) for word in words]
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
        path = chapter_path(act)
    except KeyError:
        return [], []
    if not path.exists():
        return [], []
    offset = ACT_PROGRAMME_START[act]
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
            if line["kind"] == "boss":
                entry = {
                    "id": line["id"] or f"ch_{act.lower()}_{b}_{n}_boss",
                    "kind": "miniboss",
                    "position": "boss",
                    "at": start,
                    "dur": hold,
                    "copy_source": "owner_supplied",
                    "name": line["name"],
                    "text_source": "owner_supplied",
                }
                if line["title"]:
                    entry["title"] = line["title"]
                elif line["title"] == "":
                    # The slot exists before its words do: lorem, credited
                    # to nobody, seeded exactly as the build script seeded
                    # it so the takeover changes no pixel.
                    entry["title"] = placeholder.lorem(28, seed=entry["id"])
                    entry["title_source"] = "placeholder"
                out.append(entry)
                continue
            slug = re.sub(r"[^a-z0-9]+", "_", line["speaker"].lower())
            entry = {
                "id": f"ch_{act.lower()}_{b}_{n}_{slug.strip('_')}",
                "kind": "chat",
                "position": "left",
                "at": start,
                "dur": hold,
                "copy_source": "owner_supplied",
                "speaker": line["speaker"],
                "text": line["text"],
                "text_source": ("owner_supplied" if line["text"]
                                else "placeholder"),
            }
            if LOGIN_SHAPE.match(line["speaker"]):
                entry["avatar"] = f"renders/avatars/{line['speaker']}.png"
                entry["avatar_url"] = (
                    f"https://github.com/{line['speaker']}.png?size=256")
            out.append(entry)
        end = at[-1] + holds[-1] + offset
        film_sec = ACT_FILM_SEC.get(act)
        if film_sec is not None and (at[0] < 0 or end - offset > film_sec):
            unresolved.append(
                f"the {block['label'] or format_tc(block['anchor'])} block "
                f"runs off the act's picture ({format_tc(at[0])} -> "
                f"{format_tc(at[-1] + holds[-1])} film); it is scheduled "
                "anyway so the conversation is reviewable")
    return out, unresolved


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    s = sub.add_parser("show", help="print the schedule a chapter resolves to")
    s.add_argument("act")
    args = ap.parse_args(argv)

    if args.command == "show":
        path = chapter_path(args.act)
        offset = ACT_PROGRAMME_START[args.act]
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
                    print(f"  {format_tc(start + offset)} programme / "
                          f"{format_tc(start)} film, up {hold:.2f}s{pin}  "
                          f"! {line['name']}")
                    continue
                print(f"  {format_tc(start + offset)} programme / "
                      f"{format_tc(start)} film, up {hold:.2f}s{pin}  "
                      f"{line['speaker']}: {line['text']}")
            for note in notes:
                print(f"  NOTE: {note}")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
