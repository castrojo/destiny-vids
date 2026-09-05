#!/usr/bin/env python3
"""Season of the Blueberries: the Expansion Pack authoring pass, parsed.

The owner-authored copy lives in one Markdown file per episode under
``stories/standalone/authoring/season-of-the-blueberries/`` (added by commit
32bd741), named ``NN-<slug>.md`` after the manifest chapter it authors. The
grammar, exactly as the files carry it:

    ## 02:32.00 — `cortney-losing-money`

    - Placement: `chat-cortney`
    - Copy: Why do we keep losing SO much money
    - Next line: My face hurts
    - Direction: Owner-authored two-line Cortney cue. ...

One ``##`` heading per cue: an absolute source timecode (``MM:SS.ss`` in the
season's one source), an em-dash, and the cue's backticked slug. The four
bullets are the whole field vocabulary; ``Next line`` and ``Direction`` are
optional. Everything else in the file -- the title, the preamble, owner
comments -- is prose and never becomes a card.

THE COPY IS SACROSANCT. ``Copy`` and ``Next line`` values are preserved
VERBATIM: spelling, punctuation, capitalization, backticks and ``_emphasis_``
markers all survive untouched (only the line's trailing whitespace is
dropped). Nothing here is invented, paraphrased, or normalised. A heading
that LOOKS like a cue (it opens with a timecode) but does not follow the
grammar -- or a cue missing its ``Placement`` or ``Copy`` -- raises
``AuthoringError`` naming the file and line: a malformed recognized entry is
a loud failure, never a silently skipped card.

WHICH CUES RENDER. Only the placements the delivery pipeline can seat
faithfully:

* ``chat-cortney`` -- the recurring player: speaker ``Cortney`` (the
  GitHub-profile name the season manifest records for CortNick), avatar from
  the credits cache for CortNick. ``Copy`` and ``Next line`` become two
  separate, ordered chat pills.
* ``chat-<speaker>`` -- any other owner-supplied speaker token renders as a
  chat pill carrying the token VERBATIM as its speaker. An avatar is
  attached only when the season's own identity data proves the login (the
  fixed cast or the contributor-ledger snapshots); otherwise the pill draws
  plate.py's standard no-photo crest -- an avatar is never invented. A
  ``chat-owner-speaker`` cue whose Direction declares ``speaker label is
  exactly `X```` uses exactly ``X`` and stays avatarless, as directed.
* ``top-third`` / ``bottom-right`` -- the project-lore lanes hive_series
  already renders; ``Copy`` plus an optional ``Next line`` become the card's
  verbatim lines.

Everything else -- gold/hero/nameplate variants, boss overlays, reveal
titles, protected gaps, episode-start trims, role-portrait bonds
(``chat-left-<login>-as-<character>``), hybrid lanes
(``top-third-as-cortney-chat``), and the ``chat-sequence-start`` template
marker -- is recorded in ``unresolved`` with the cue's id and the precise
reason, and is NEVER rendered with an invented treatment. The season
contract seats a post-picture multi-message conversation as a full-screen
transmission, but the authoring docs do not say which sequences play after
the picture, so no cue is given that treatment by a guess; the ambiguity is
recorded instead.

HOW CHAT WINDOWS ARE SEATED (the schedule). Authored absolute source
anchors never move. Cues are taken in source-time order; within one anchor
the owner's own Direction markers decide the sequence -- a
speaker-qualified "Name ... line N" orders that speaker's lines, a bare
"sequence line N"/"line N" pins the line to that absolute slot at the
anchor, "Final ... line" pins the last slot, and "follows the X cue" /
"sequence after X" places a line after speaker X's lines. A cue with no
marker keeps its document position (and a ``Next line`` rides immediately
after its ``Copy``). Nothing is reordered by slug or by guess. The first
pill at an anchor seats AT the anchor. A pill whose anchor is still
occupied by the previous pill seats at ``previous end + TAIL_OUT``
(plate.py's tail gap) -- that is the sequencing the owner asks for with
"sequence the lines without overlap", not a retimed cue. Every pill holds
``readtime.required_hold(text)`` -- plate.py's MIN_HOLD floor, lengthened at
the project's 17 CPS reading rate when the words need it. A pill fits only
when its hold AND tail gap clear the next anchor THAT ITSELF RENDERS AS
CHAT (an unsupported cue is a phantom boundary and constrains nothing), or
when its hold clears the chapter end for the last cue (the cut itself is
the clearing, no tail owed). A pill that cannot fit is recorded in
``unresolved`` -- never overlapped, never silently retimed, never silently
dropped.

PROTECTED GAPS. A `protected-gap` cue is never drawn AND is a scheduling
barrier -- the owner's "leave the picture alone": its protected window runs
from its anchor to the NEXT authored cue at a later anchor (the beat the
clean lead-in protects), or to the chapter end when nothing follows. No
chat pill's window (including its tail gap) may cover any part of a
protected window, and no lore card's window may intersect one -- a card
that would is recorded in ``unresolved``, never drawn over a protected
beat. Note the asymmetry that keeps this honest: a merely UNSUPPORTED cue
(unrenderable, unprotective) forms no boundary at all, while a
protected-gap is unrenderable but binding.

Stdlib only; this module never touches media, the network, or ffmpeg.
"""

from __future__ import annotations

import re
from pathlib import Path

from tools import readtime
from tools.plate import MIN_HOLD, TAIL_OUT

# --- the grammar --------------------------------------------------------------

# `## 02:32.00 — `cortney-losing-money``: mm, then ss(.ff), em-dash, slug.
_ENTRY_HEADING = re.compile(
    r"^##\s+(\d{1,3}):(\d{2}(?:\.\d+)?)\s+—\s+`([^`]+)`\s*$")
# A `##` line that opens with a timecode but missed the full grammar is a
# RECOGNIZED entry gone malformed -- a loud failure, not prose.
_TIMECODEISH_HEADING = re.compile(r"^##\s*\d+:\d+")
_FIELD = re.compile(r"^-\s+(Placement|Copy|Next line|Direction):\s*(.*?)\s*$")

# The one Direction directive this parser acts on: an explicit speaker label,
# e.g. "Owner-authored speaker label is exactly `CVS Health`; do not infer a
# GitHub identity." Anything else in Direction is guidance, not data.
_SPEAKER_LABEL = re.compile(r"speaker label is exactly `([^`]+)`")

# Floating-point schedule comparisons get the same tolerance plate.py's
# overlap check uses.
_EPS = 1e-6

# The chat pill's seat: plate.py's `letterbox` lane, BELOW the picture on a
# letterboxed frame, so the pills never stack onto the fixed cast's
# lower-left Guardian plates or the bottom-right lore lane. On a full-frame
# probe it degrades to just inside the bottom edge, centred -- plate.py's
# own rule, unchanged.
CHAT_POSITION = "letterbox"

# Where the authoring files live; a module constant so callers (and tests)
# can redirect the pass.
AUTHORING_DIR = (Path(__file__).resolve().parents[1] / "stories"
                 / "standalone" / "authoring" / "season-of-the-blueberries")


class AuthoringError(ValueError):
    """A recognized authoring entry is malformed. Carries file and line."""


def _unquote(value):
    """One pair of wrapping backticks removed (the Placement convention);
    anything else -- including backticks inside Copy -- is left alone."""
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        return value[1:-1]
    return value


def parse_authoring(text, source_name="<authoring>"):
    """The authoring cues in ``text``, in document order.

    Returns a list of dicts: ``slug``, ``source_at`` (absolute source
    seconds), ``placement``, ``copy``, ``next_line`` (or None),
    ``direction`` (or None), and ``line`` (the heading's line number, for
    error messages). Prose -- titles, preambles, owner comments, bullets
    outside the four known fields -- never becomes a cue.

    Raises AuthoringError on a malformed RECOGNIZED entry: a timecode-led
    heading that does not match the grammar, a bad timecode, a duplicated
    field, or an entry missing its Placement or Copy.
    """
    entries = []
    current = None

    def close():
        nonlocal current
        if current is None:
            return
        entry, current = current, None
        slug = entry["slug"]
        if not entry.get("placement"):
            raise AuthoringError(
                f"{source_name}:{entry['line']}: entry `{slug}` has no "
                "`- Placement:` field")
        if not entry.get("copy"):
            raise AuthoringError(
                f"{source_name}:{entry['line']}: entry `{slug}` has no "
                "`- Copy:` field")
        entries.append(entry)

    for lineno, line in enumerate(text.splitlines(), start=1):
        heading = _ENTRY_HEADING.match(line)
        if heading:
            close()
            minutes, seconds, slug = heading.groups()
            if float(seconds) >= 60:
                raise AuthoringError(
                    f"{source_name}:{lineno}: entry `{slug}` has an invalid "
                    f"timecode {minutes}:{seconds}")
            current = {
                "slug": slug,
                "source_at": int(minutes) * 60 + float(seconds),
                "placement": None,
                "copy": None,
                "next_line": None,
                "direction": None,
                "line": lineno,
            }
            continue
        if line.startswith("## ") or line.startswith("##\t"):
            if _TIMECODEISH_HEADING.match(line):
                raise AuthoringError(
                    f"{source_name}:{lineno}: a timecode-led heading that "
                    "does not match `## MM:SS.ss — `slug`': "
                    f"{line.strip()!r}")
            close()  # a prose section heading ends any open entry
            continue
        field = _FIELD.match(line)
        if field and current is not None:
            key, value = field.groups()
            slot = {"Placement": "placement", "Copy": "copy",
                    "Next line": "next_line", "Direction": "direction"}[key]
            if current[slot] is not None:
                raise AuthoringError(
                    f"{source_name}:{lineno}: entry `{current['slug']}` "
                    f"repeats `- {key}:`")
            current[slot] = _unquote(value) if slot == "placement" else value
        # Anything else is prose and is ignored.
    close()
    return entries


def load_chapter_authoring(authoring_dir, chapter):
    """The cues for one manifest chapter, or [] when the episode has no
    authoring file (episodes without an Expansion Pack pass ship as they
    are -- absence is not an error)."""
    path = (Path(authoring_dir)
            / f"{chapter['number']:02d}-{chapter['slug']}.md")
    if not path.exists():
        return []
    return parse_authoring(path.read_text(encoding="utf-8"), str(path))


# --- classification -----------------------------------------------------------


def _identity_records(manifest):
    """The identities the season's own records prove, as
    ``(fixed, ledger)``: lowercased login -> ``(canonical login, display
    name-or-None)`` for the fixed cast, and lowercased login -> canonical
    login for contributor-ledger candidates.

    A fixed-cast speaker carries the manifest's verified ``plate.name``
    (Cortney, Angie Jones, Shellea Williams) -- never the raw login. A
    ledger-proven speaker keeps the owner's supplied token as its label but
    earns the cached avatar. A handle neither record vouches for renders
    label-only, avatarless -- an avatar is never invented."""
    fixed = {}
    for member in manifest.get("fixed_cast") or []:
        login = member.get("github_login")
        if login:
            name = (member.get("plate") or {}).get("name") or None
            fixed[login.lower()] = (login, name)
    ledger = {}
    for snapshot in (manifest.get("contributor_ledger") or {}).get(
            "snapshots") or []:
        for candidate in snapshot.get("candidates") or []:
            login = candidate.get("login")
            if login:
                ledger.setdefault(login.lower(), login)
    return fixed, ledger


def _unsupported_reason(placement):
    """The precise treatment family an unsupported placement names."""
    families = [
        ("gold-plate", "a gold plate variant is a hero treatment this "
                       "pipeline does not draw"),
        ("hero-nameplate", "a hero nameplate is a treatment this pipeline "
                           "does not draw"),
        ("character-nameplate", "a character nameplate without a "
                                "real-person identity is never guessed"),
        ("nameplate", "a nameplate variant is a treatment this pipeline "
                      "does not draw"),
        ("red-boss-overlay", "a boss overlay is a treatment this pipeline "
                             "does not draw"),
        ("boss", "a boss overlay is a treatment this pipeline does not "
                 "draw"),
        ("episode-start", "an episode-start trim moves the chapter "
                          "boundary; this pass never re-cuts the chapter"),
        ("protected-gap", "a protected gap asks the picture to be left "
                          "alone; no card is rendered, and the gap is "
                          "recorded so the omission is visible"),
        ("reveal-title", "a reveal title is a treatment this pipeline does "
                         "not draw"),
        ("warning-curse", "a curse-cast visual treatment is not a card "
                          "this pipeline draws"),
        ("featured-top-third", "an attributed top-third variant is not the "
                               "plain top-third lore lane"),
        ("top-third-as-", "a top-third card styled as a specific person's "
                          "chat is a hybrid treatment, never rendered by a "
                          "guess"),
        ("cncf-upper-third", "an upper-third variant is not the plain "
                             "top-third lore lane"),
        ("top-right", "top-right is not one of the project-lore lanes "
                      "(top-third, bottom-right)"),
    ]
    for prefix, detail in families:
        if placement.startswith(prefix):
            break
    else:
        detail = "no renderer knows this placement"
    return (f"placement {placement!r}: {detail}; the cue is recorded, "
            "never rendered with an invented treatment")


def _classify(entry, fixed, ledger):
    """One cue -> ("chat", speaker, avatar_or_none) | ("lore",) |
    ("unresolved", reason). Classification looks at the placement and the
    season's identity records only; copy is never inspected to decide what
    a cue IS."""
    placement = entry["placement"]
    if placement in ("top-third", "bottom-right"):
        return ("lore",)
    if placement == "chat-sequence-start":
        return ("unresolved",
                "placement 'chat-sequence-start' marks the start of the "
                "standard chat-card sequence: a template marker, not a chat "
                "line. The authoring docs do not say whether that sequence "
                "plays over the picture or after it -- a post-picture "
                "conversation is the full-screen transmission treatment, "
                "which this renderer does not build -- so the marker is "
                "recorded, not rendered by a guess")
    match = re.fullmatch(r"chat-(.+)", placement)
    if match:
        token = match.group(1)
        # `chat-cortney` names the recurring player: the season record binds
        # that name to the fixed-cast CortNick entry, whose plate.name is
        # the verified GitHub profile name.
        key = "cortnick" if token.lower() == "cortney" else token.lower()
        if key in fixed:
            canonical, name = fixed[key]
            return ("chat", name or token, f"renders/avatars/{canonical}.png")
        if token.startswith("left-") or "-as-" in token:
            return ("unresolved",
                    f"placement {placement!r} is a one-video role bond (a "
                    "real handle beside a lore-character portrait); "
                    "role-portrait treatments are not supported, so the "
                    "cue is recorded, never rendered with an invented "
                    "presentation")
        if token == "owner-speaker":
            label = _SPEAKER_LABEL.search(entry.get("direction") or "")
            if label:
                return ("chat", label.group(1), None)
            return ("unresolved",
                    f"placement {placement!r} carries no speaker and its "
                    "Direction declares no `speaker label is exactly` "
                    "label; a speaker is never invented")
        avatar = None
        canonical = ledger.get(token.lower())
        if canonical:
            avatar = f"renders/avatars/{canonical}.png"
        return ("chat", token, avatar)
    return ("unresolved", _unsupported_reason(placement))


# --- same-anchor sequencing ------------------------------------------------------
#
# A multi-line beat at one source anchor is ordered by the owner's own
# Direction markers, never by slug or by guess:
#
# * "Name ... line N" (speaker-qualified, e.g. "Cortney sequence line 1",
#   "Taylor sequence line 2") orders the line WITHIN that speaker's lines;
# * a bare "sequence line N" / "line N" pins the line to absolute slot N at
#   the anchor;
# * "Final ... line" pins the last slot;
# * "follows the X cue" / "sequence after X" places the line after speaker
#   X's lines at this anchor.
#
# A cue carrying no marker keeps its document position. The pass is a
# deterministic reorder of one anchor's chat lines; it never moves a line
# to a different anchor and never changes copy.

# `Cortney finale line 2` / `Taylor sequence line 1`: a Capitalized token,
# optional sequence/finale filler, then `line N`.
_QUALIFIED_LINE = re.compile(
    r"([A-Z][\w-]*)\s+(?:(?:sequence|finale)\s+)*line\s+(\d+)")
_BARE_LINE = re.compile(r"(?:(?:sequence|finale)\s+)*line\s+(\d+)", re.I)
_FINAL_LINE = re.compile(r"\bfinal\b[^.]*\bline\b", re.I)
_FOLLOWS = re.compile(r"follows\s+the\s+([\w-]+)\s+cue", re.I)
_AFTER = re.compile(r"sequence\s+after\s+([\w-]+)", re.I)
# Words that look like a speaker in the qualified pattern but are grammar.
_NOT_A_SPEAKER = {"sequence", "finale", "line", "owner", "authored",
                  "owner-authored"}


def _same_speaker(token, speaker):
    """A Direction's name for a speaker vs the spec's resolved label:
    exact, or a prefix of it ('Angie' for 'Angie Jones', 'Taylor' for
    'taylorwaggoner')."""
    token, speaker = token.lower(), speaker.lower()
    return token == speaker or speaker.startswith(token)


def _sequence_markers(direction, speaker):
    """``(speaker_line_no, anchor_slot, follows_speaker)`` for one cue.

    The qualified form wins and binds only when its name IS this cue's
    speaker; otherwise the number is the anchor-wide slot. A bare number is
    always anchor-wide. ``Final`` without a number pins the last slot."""
    direction = direction or ""
    speaker_num = anchor_num = None
    for match in _QUALIFIED_LINE.finditer(direction):
        token = match.group(1)
        if token.lower() in _NOT_A_SPEAKER:
            continue
        number = int(match.group(2))
        if _same_speaker(token, speaker):
            speaker_num = number
        else:
            anchor_num = number
        break
    if speaker_num is None and anchor_num is None:
        bare = _BARE_LINE.search(direction)
        if bare:
            anchor_num = int(bare.group(1))
    if speaker_num is None and anchor_num is None \
            and _FINAL_LINE.search(direction):
        anchor_num = float("inf")
    dep = None
    followed = _FOLLOWS.search(direction) or _AFTER.search(direction)
    if followed:
        dep = followed.group(1)
    return speaker_num, anchor_num, dep


def _sequence_anchor_group(items):
    """One anchor's chat line-items, reordered as the owner sequenced them.

    ``items`` is ``[(doc_position, entry, spec)]`` in document order and the
    result is the same list reordered. Pins land on their absolute slots;
    everything unpinned fills the remaining slots in document order, with
    one speaker's lines internally ordered by their speaker-scoped numbers
    and "follows/after" lines moved behind the speaker they follow.
    """
    marks = [_sequence_markers(item[1].get("direction"), item[2]["speaker"])
             for item in items]
    order = list(range(len(items)))

    # Speaker-internal order: a speaker's lines sort by their qualified
    # numbers (unnumbered lines keep their document rank) while staying at
    # the document positions that speaker occupies.
    positions_by_speaker = {}
    for pos in order:
        positions_by_speaker.setdefault(items[pos][2]["speaker"], []) \
            .append(pos)
    for positions in positions_by_speaker.values():
        keyed = sorted(
            positions,
            key=lambda p: (marks[p][0]
                           if marks[p][0] is not None
                           else positions.index(p) + 1, p))
        for slot, pos in zip(positions, keyed):
            order[slot] = pos

    # Anchor pins take their absolute slots; the unpinned fill the rest in
    # (speaker-corrected) document order. A pin past the end, or a tie,
    # takes the next free slot -- deterministic, never an error.
    n = len(order)
    result = [None] * n
    pinned = sorted((p for p in order if marks[p][1] is not None),
                    key=lambda p: (marks[p][1], p))
    free = [slot for slot in range(n)]
    for pos in pinned:
        target = marks[pos][1]
        slot = n - 1 if target == float("inf") else min(int(target) - 1,
                                                        n - 1)
        while slot < n and result[slot] is not None:
            slot += 1
        if slot >= n:
            slot = free[-1]
        result[slot] = pos
        free.remove(slot)
    pool = [pos for pos in order if marks[pos][1] is None]
    for slot, pos in zip(free, pool):
        result[slot] = pos

    # "follows the X cue" / "sequence after X": if the line sits before the
    # last of speaker X's lines, move it right behind them.
    for pos in list(result):
        dep = marks[pos][2]
        if dep is None:
            continue
        targets = [q for q in result
                   if q != pos and _same_speaker(dep, items[q][2]["speaker"])]
        if not targets:
            continue  # no usable cue here: document order stands
        here, last = result.index(pos), max(result.index(q) for q in targets)
        if here < last:
            result.insert(last, result.pop(here))
    return [items[pos] for pos in result]


# --- the schedule ---------------------------------------------------------------


def plan_authoring(entries, manifest, chapter):
    """Classify and seat one chapter's authoring cues.

    Returns ``(chats, lore, unresolved, protected_gaps)``:

    * ``chats`` -- plate.py-ready ``kind: chat`` specs in scheduled order,
      with ``at``/``dur`` in chapter-relative seconds and the authored
      absolute anchor preserved untouched in ``source_at``;
    * ``lore`` -- verbatim project-lore overlays (``id``, ``lines``,
      ``position``, ``source_at``) for the supported lore lanes, left in
      source time for the caller's overlay clamp;
    * ``unresolved`` -- ``{"id", "reason"}`` for every cue that cannot be
      seated faithfully, in document order;
    * ``protected_gaps`` -- ``[(start, end)]`` CHAPTER-RELATIVE no-draw
      windows from `protected-gap` cues, so the caller keeps lore cards out
      of them too.

    The seating rules are the module's contract (see the docstring): pinned
    anchors exact, same-anchor cascades at MIN_HOLD/TAIL_OUT, a cue that
    cannot clear the next distinct owner anchor or the chapter end is
    recorded, never overlapped or retimed.
    """
    start, end = float(chapter["start"]), float(chapter["end"])
    fixed, ledger = _identity_records(manifest)
    chats_pending = []  # (source_at, doc position, entry, spec)
    lore = []
    unresolved = []

    # Protected gaps are no-draw scheduling barriers (see the module
    # docstring): the protected window runs from the gap's anchor to the
    # next authored cue after it -- the beat the clean lead-in protects --
    # or to the chapter end. They are computed from ALL entries before
    # classification, and they still land in `unresolved` below as no-draw
    # records via the normal placement rule.
    all_anchors = sorted({e["source_at"] for e in entries})
    protected = []
    for entry in entries:
        if entry["placement"] != "protected-gap":
            continue
        later = [a for a in all_anchors if a > entry["source_at"] + _EPS]
        protected.append((entry["source_at"], later[0] if later else end))

    for index, entry in enumerate(entries):
        slug = entry["slug"]
        if not (start <= entry["source_at"] <= end):
            unresolved.append({
                "id": slug,
                "reason": f"absolute source {entry['source_at']:g}s is "
                          f"outside chapter {chapter['number']} "
                          f"({start:g}-{end:g}s); the cue is recorded, "
                          "never seated by a guess",
            })
            continue
        verdict = _classify(entry, fixed, ledger)
        if verdict[0] == "unresolved":
            unresolved.append({"id": slug, "reason": verdict[1]})
            continue
        if verdict[0] == "lore":
            lines = [entry["copy"]]
            if entry.get("next_line"):
                lines.append(entry["next_line"])
            lore.append({"id": slug, "lines": lines,
                         "position": entry["placement"],
                         "source_at": entry["source_at"]})
            continue
        _kind, speaker, avatar = verdict
        for line_index, text in enumerate(
                [entry["copy"], entry.get("next_line")]):
            if not text:
                continue
            spec = {
                "id": slug if line_index == 0 else f"{slug}-next",
                "kind": "chat",
                "speaker": speaker,
                "text": text,
                "position": CHAT_POSITION,
                "source_at": entry["source_at"],
                "copy_source": "owner_authored",
                "why": f"Owner-authored Expansion Pack cue `{slug}` "
                       f"({entry['placement']}) at absolute source "
                       f"{entry['source_at']:g}s.",
            }
            if avatar:
                spec["avatar"] = avatar
            # A Next line rides immediately after its Copy: it shares the
            # entry's sequence position with a sub-index.
            chats_pending.append((entry["source_at"],
                                  index + line_index / 10.0, entry, spec))

    # Source order across anchors; within one anchor, the owner's explicit
    # sequence markers decide (document order when there are none).
    groups = {}
    for item in chats_pending:
        groups.setdefault(item[0], []).append(item)
    ordered = []
    for anchor in sorted(groups):
        group = [(pos, entry, spec) for _at, pos, entry, spec in
                 groups[anchor]]
        ordered.extend((anchor, entry, spec)
                       for _pos, entry, spec in _sequence_anchor_group(group))

    # Only anchors that themselves render as chat bound the packing: an
    # unsupported cue constrains nothing (it never draws), so it must not
    # drop valid chats as a phantom boundary.
    anchors = sorted(groups)
    chats = []
    cursor = None  # previous pill's end + TAIL_OUT, in source seconds
    for source_at, _entry, spec in ordered:
        hold = readtime.required_hold(spec["text"])
        seat = source_at if cursor is None else max(source_at, cursor)
        # A protected gap is a hard no-draw window: the pill must clear it
        # entirely (tail gap included) or start after it ends. A pill that
        # would cover any part of one is recorded -- never drawn over a
        # protected beat.
        covering = next(
            ((g0, g1) for g0, g1 in protected
             if not (seat + hold + TAIL_OUT <= g0 + _EPS
                     or seat >= g1 - _EPS)),
            None)
        if covering is not None:
            unresolved.append({
                "id": spec["id"],
                "reason": f"its window ({seat:g}s + {hold:.2f}s) would "
                          f"cover the protected gap {covering[0]:g}-"
                          f"{covering[1]:g}s (the owner leaves the picture "
                          "alone there); recorded, never drawn over a "
                          "protected beat",
            })
            continue
        later = [a for a in anchors if a > source_at + _EPS]
        if later:
            # The next pinned cue still lands exactly on its anchor: this
            # pill's hold AND the tail gap must clear it.
            boundary = later[0]
            fits = seat + hold + TAIL_OUT <= boundary + _EPS
            boundary_text = f"the next owner anchor at {boundary:g}s"
            need = seat + hold + TAIL_OUT
        else:
            # The last cue owes no tail: the cut to the next segment is the
            # clearing, so only the hold must fit the chapter window.
            boundary = end
            fits = seat + hold <= boundary + _EPS
            boundary_text = f"the chapter end at {end:g}s"
            need = seat + hold
        if not fits:
            unresolved.append({
                "id": spec["id"],
                "reason": f"needs {hold:.2f}s from {seat:g}s but does not "
                          f"fit before {boundary_text} ({need:.2f}s > "
                          f"{boundary:g}s); recorded rather than "
                          "overlapped or retimed",
            })
            continue
        spec["at"] = round(seat - start, 3)
        spec["dur"] = round(hold, 3)
        chats.append(spec)
        cursor = seat + hold + TAIL_OUT

    return (chats, lore, unresolved,
            [(round(g0 - start, 3), round(g1 - start, 3))
             for g0, g1 in protected])
