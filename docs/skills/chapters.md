---
name: chapters
version: "1.1"
last_updated: "2026-09-04"
id: chapters
one_line_purpose: Author a chapter's on-screen copy in one Markdown file per chapter.
entry_point: docs/skills/chapters.md
category: editorial
status: active
dependencies: []
tags:
  - dialogue
  - chat
  - chapters
  - markdown
description: >-
  Edit any word the audience reads without computing timecodes: one Markdown
  file per chapter, with per-line timing derived from readability. Use when
  writing or rewriting chat pills, red splashes, or title, status and credit
  cards.
metadata:
  type: procedure
---

# Chapter conversations

## When to Use

- Rewriting **any** word the audience reads, in any act
- Adding or rewriting chat dialogue without computing timecodes
- Giving one character several lines in a row — each its own pill
- Seating or rewording a red splash (the boss bar) — `! NAME` lines
- Editing a title, status, bookline or credit card
- Reading the whole show through in one page — `chapters/full-script.md`

## When NOT to Use

- Recovered footage dialogue for a source video → `dialogue/<video_id>/`
  and `tools/dialogue_md.py`
- A nameplate's name, or a roster credit wall — those resolve from
  `vocab/casting.yaml` and `stories/roster-*.json`, which is the one place
  those names live. A chapter file leaves them alone.
- Plate geometry, fade curves, letterbox rects and encode parameters →
  [`plates`](plates/SKILL.md). Those live beside the plate in the manifest;
  nobody opens that file to change a word.

## Where each act's copy lives

Read this table before touching any on-screen copy. Two systems with similar
names are easy to confuse:

- `chapters/<act>.md` — **what the owner writes.** One file per chapter,
  carrying that chapter's dialogue and cards. The build reads it and the
  plates land in the generated manifest.
- `dialogue/<video_id>/` — **recovered-footage provenance.** What people in a
  *source video* visibly say, with timecodes and evidence. Chapter seating
  uses it as evidence; it is not where act copy is edited.

| Chapter | Copy lives in | Owns its manifest? |
|---|---|---|
| 0 — prologue titles | `chapters/0-prologue.md` | yes |
| I — intro | — (no authored copy) | — |
| II — endlessforms | `chapters/II-endless-forms.md` — every pill and both red splashes; the act's titles, banners, Guardian reveals and choice screen are still placed by `scripts/build_efmb_plates.py` | no, partial |
| III — mrbobbytables | `chapters/III-mrbobbytables.md` (the two fixed pills); the act's conversation is recovered speech in `dialogue/yt_curse_of_osiris_opening_cinematic/` | yes |
| IV — kat | `chapters/IV-kat.md` | yes |
| V — nat | `chapters/V-nat.md` | yes |
| VI — 7daystothewolves | `chapters/VI-wolves.md` | yes, its own plates only |
| P4 — underwater interlude | `chapters/P4-underwater.md` | yes |
| VII — europa | `chapters/VII-europa.md` | yes |
| VIII — the cries | `chapters/VIII-cta.md` | yes, `cta_cards` |
| VIII — fixed credits | `chapters/VIII-fixed.md` | yes, `fixed_cards` |

Standalone series whose builder does not yet consume chapter Markdown stage
owner-authored passes under `stories/standalone/authoring/<series>/`, one file
per episode. That directory is the durable copy record, not a render manifest:
it preserves exact source marks, wording, order, and production directions
until the series builder gains a chapter adapter. Do not leave a pass in
session notes, and do not paste it into the generated season manifest.

**Act II is a partial author, and that is the whole difference.** Every word
anybody *speaks* in it — all 53 pills and both red splashes — is authored in
its chapter file, exactly like the other ten. What it does not own is its
**manifest**: `scripts/build_efmb_plates.py` still places the act's titles,
banners, Guardian reveals and the 67-frame choice screen, and it is the file
that writes `stories/02-endless-forms-plates.json`. So act II is absent from
`owns_plates` and `sync` skips it, while
`tests/test_chapter_identity.py` still holds the same identity claim over its
dialogue: every chat plate the manifest renders is one the chapter file
authored, key order included.

The pills used to be generated from megacut-relative constants across about
ten code paths, which meant a copyedit was a code edit. They were lifted with
`chapter_md.extract`, every one pinned with an explicit hold so no seat could
re-time, and the result was proven byte-identical against the delivered
manifest before the constants were deleted. Where a card the builder still
places has to give way to a line, the builder reads the line's clear time off
the chapter entries (`chapter_floor`) rather than off a table of its own —
so lengthening a line still moves the card after it.

**Never edit a manifest to change a word.** Once a chapter owns its plates,
the manifest is an *output*: `tools/plate.py` re-syncs it from the chapter
file before every burn, so a hand-edit is reverted at the moment it would
otherwise reach a frame.

**A heading label lets a held frame derive its own duration.** Writing
`## <heading> <label>` (for example `## 9:52.203 paused`) tags every entry
under that heading until the next one, and `chapter_md.block_end(act, label)`
returns the film position where the labelled block ends — so a builder that
holds a frame for "as long as this conversation takes" derives that hold from
the conversation's own authored length instead of a hand-typed duration that
goes stale the next time a line is added or cut. `entries(act,
include_block_labels=True)` returns each entry's label under the private
`_chapter_label` key, for a builder (or a test) that needs to know which
block an entry belongs to; it is never written into the manifest.

**`source_anchor` seats a pill on a source frame instead of its natural
schedule.** A pill that must play back exactly when it was actually said —
because the owner locked it to a specific moment in the source footage,
independent of how long anything authored before it runs — carries
`source_anchor: <source seconds>` instead of `@ <heading time>` or
`seen_at_src`. Act II's builder (`scripts/build_efmb_plates.py`) pops the key,
sets `at` from that source frame, and publishes `seen_at_src` in its place;
the key never reaches the manifest. Its seat stays tied to the current source
frame rather than to a programme-clock pin that may move with an edit.

**An inserted clip inside a held source frame needs three labelled blocks.**
Label the pre-insert hold, the inserted action, and the post-insert hold; the
picture builder derives all three half-open intervals from those records. Its
inverse clock must return the held source frame during the post-insert interval
and raise only inside the external clip.

**An identifier is not visual evidence.** A constant or plate ID can preserve
an earlier interpretation of a frame; extract and inspect the target frame
before using it as a `source_anchor`. Name a real person or label a group only
from what is visible in that frame.

**`show` and `check` print the seat the BUILD emits, not the file's raw
schedule.** An act whose builder moves a line between the chapter file and
the manifest — act II does both of the things above — declares the mapping in
its front matter:

```
reseat: scripts/build_efmb_plates.py:reseat_chapter_entries
```

`chapter_md.emitted_entries(act)` imports that function lazily (only for the
act that declares one, so the general chapter tool never depends on one act's
renderer) and hands it the resolved entries; `show` marks anything it moves
`(reseated by the build)` and `check` compares the moved seats. Without it,
`show` quotes a programme time the delivered master does not carry — an
editor asked to nudge a line scrubs to it and is looking at the wrong
picture — and `check` reports the accepted mapping as permanent drift, which
hides the real thing. A hook that cannot be imported degrades to the file's
own schedule with a note, and never raises. **The mapping lives in the
builder that performs it**; restating it in `chapter_md` (or in a test) is a
second copy, and the copy nobody rebuilds from is the one that goes stale.

**The orphan trap, retired:** `dialogue/yt_destiny_all_live_action_trailers/`
used to carry exactly one line — Cayde's "I'm so proud of you kids!"
sign-off, an owner-supplied line recorded in #93 that stopped playing when
the v3.9 converge removed `cayde_signoff` from act II's manifest. The owner
retired it outright on 2026-08-20 ("I don't want it in the movie"): record,
builder emission code, and `ACT_SOURCES` entry all deleted, and
`tests/test_efmb_act.py` pins the retirement. The lesson that stays: a
one-line DIALOGUE.md whose line no act renders is a stub, not a
conversation — re-wire the line or retire the record, never wordsmith it.

## The file is the tool

Each chapter file is self-describing: its **front matter** declares which
manifest it writes, where the chapter starts in the programme (with the
derivation stated), the field order the manifest reads in, and the defaults
its plates take. There is no registry to update — `chapter_md` discovers the
files, so adding a chapter is one new file and nothing else.

The grammar, in full:

```markdown
## 15:31.472                       a block: one heading, the lines under it
kat: I miss ONE email now          a pill, held by read speed
kat @ 15:33.770: How much you...   pinned to an exact programme moment
[p2c-kat-nice] kat +1.3: Fine      bound to an existing plate, held 1.3 s
! [id] BOSS NAME @ 6:52 | title    a red splash
* [id] status @ 17:23.202 +6.0     a card; its copy is the rows below
  - label: Welcome to KubeCon      a field of the card above
  - body: first line               repeat a key to build a list
  - body: second line
  - fade_in: null                  delete a field the defaults supplied
  - censor: Goddamn -> G{k8s}ddamn
```

**A pill names a GitHub login, never a URL.** A canonical login resolves through
`vocab/casting.yaml`'s `people` map, which owns its stable numeric GitHub ID and
portrait fields. Display names, character IDs, historical personas, `cast:`,
`avatar_login:`, and GitHub URLs are not chapter authoring. Existing release-
train rows using those forms remain literal legacy speakers and are reported by
`tools/identity.py`; they are not aliases. `- avatar: null` removes a portrait
that was derived but is not wanted.

**A one-video character bond keeps the real handle visible.** When the owner
explicitly says a real GitHub speaker is playing a lore character for one
scene, the pill still names the real login. A character portrait may replace
the GitHub PFP as presentation chrome only when that bond and the portrait's
source are recorded beside the cue. Never replace the handle with the
character name: the audience knows the person and needs the picture to teach
the temporary role.

When lifting an existing manifest, keep a local authored `avatar` path as a
local chapter field. Omit a GitHub-derived URL only when the rebuilt entry
deterministically re-derives that exact portrait through its login. A card or
legacy speaker whose literal URL cannot be re-derived keeps it, rather than
losing a portrait or gaining an inferred identity.

Front matter worth knowing: `owns_plates` (this file is answerable for its
plates, so the manifest is regenerated from it), `field_order`, `defaults`
(a `null` there **removes** a field), `fade_out_at: derived [N]`,
`list_keys` (which keys are always lists — a fact about the act, not the
key), and `timed: false` for a run of cards that has no clock, like act
VIII's weighted cries.

**`deck: <label>` routes a block out of the act.** A block whose heading
carries that label (`## 15:18.816 intermission`) leaves `entries()` and comes
back from `deck_entries()` instead, rebased so its first card starts at 0.
That is how act III's intermission is authored: the deck is the *conclusion*
of Bob's scene, so the owner edits it where the scene is, while it renders as
its own film after the act rather than burning over the act's picture. A deck
block is exempt from the "runs off the act's picture" note, because running
off the picture is exactly what it does.

**Prose is not as inert as it looks.** A sentence containing `word: text`
matches the pill grammar and becomes a pill nobody wrote. Keep colons out of
chapter-file prose — say "a source marker reading `placeholder`", not
"`*_source: placeholder`" — and let `python3 tools/chapter_md.py show <act>`
confirm the act resolves to only the lines you meant.

Timing is derived, never typed: an unpinned line holds for `len(text) / 15`
seconds clamped to [2.2, 7.0] — characters-per-second, set conservative for
a theatre screen — with a 0.25 s beat between pills. An explicit `+<dur>`
bypasses the clamp entirely, which is what makes a migrated act reproduce
exactly. A pinned line lands exactly; a pin that overruns its neighbour is
honoured with the overlap recorded in `unresolved`.

**Seats follow the speech on screen.** A line whose words match the act's
recovered dialogue — the shots where the characters visibly say them — is
seated at that moment, not where the cascade would put it (owner ruling,
2026-08-20). A pin still wins. Every seat taken or overridden is printed by
`show`, printed to stderr at build time, and recorded in the manifest:
always inform the operator of improvements, never apply them silently.

## Core Process

```bash
python3 tools/chapter_md.py list              # every chapter and what it owns
$EDITOR chapters/V-nat.md                     # the words
python3 tools/chapter_md.py show V            # the schedule it resolves to
python3 tools/chapter_md.py check             # drift against every manifest
python3 tools/chapter_md.py sync V --write    # put the words in the manifest
python3 scripts/generate_full_script.py --write   # refresh the read-through
```

`chapters/full-script.md` is the whole programme in one page, in the order
the audience hears it, and it is **generated** — every block says which file
its lines are edited in.

## Integrating an owner's prompt-style edit

The owner sometimes edits a chapter file the way they would talk to an
agent: instructions, angle-bracket notes, and production directions mixed
into the dialogue. The integration order matters:

1. **Snapshot the raw edit first.** Commit it verbatim on its own branch
   before changing a word — authored copy must never exist only in a
   working tree, and the raw text is the evidence of intent.
2. **Execute or preserve every instruction.** A direction that is not
   dialogue (a recast note, a "make it dramatic" tail block) is either done
   in the same change or preserved verbatim in the commit message for the
   workstream that owns it. It never stays in the chapter file, and it is
   never treated as a line to render.
3. **Re-seat only what may move.** `@` pins are owner placement and never
   move. When new lines overlap, adjust only unpinned cascade lines, keep
   the owner's written order, and record the seating rule in the file.
4. **Finish with `show` clean and `sync --write`** — no overlap NOTEs you
   did not deliberately accept, then regenerate the manifest.

## Red Flags

- **Editing a manifest to change a word.** It is an output. The next burn
  re-syncs it from the chapter file and your edit is gone.
- Adding a plate to `stories/02-endless-forms-plates.json` by hand. CI
  regenerates it from `scripts/build_efmb_plates.py`; the builder is the
  source for act II.
- Opening `dialogue/` folders looking for an act's chat to copyedit. Only
  act III's *recovered* conversation lives there, and it is provenance, not
  copy.
- Typing per-line timecodes for every row — that is what the heading and the
  read-speed timing replace; pin only the lines that must land exactly.
- A line left blank under a real name. Blank text renders as a placeholder
  credited to nobody — which is right for an unwritten slot and wrong as a
  way to silence a line. Delete the row to drop the line.
- Recomputing `programme_start` from memory. Each chapter file carries its
  derivation; restate it from a `tools/megacut.py --dry-run` when the
  running order moves.
- Widening a hold because `tools/readtime.py` says a line is short. Moving
  an authored beat is the owner's call, never a tool's.
- **A line with leading whitespace silently falls out of the schedule** —
  `show` will not list it and nothing errors. If a line the owner wrote is
  missing from `show`, check for a stray indent before assuming a drop.
- Seating two pills so they overlap. `tools/plate.py` hard-refuses two
  visible pills at once, so "accept the overlap" is not buildable; re-seat
  an unpinned line instead.
- Leaving a standalone episode pass in an agent database or transcript after
  the session. Export it to the series authoring directory before stopping.

## Verification

```bash
python3 -m pytest -q tests/test_chapter_md.py tests/test_chapter_identity.py
python3 -m pytest -q tests/test_full_script.py
python3 tools/chapter_md.py check
python3 tools/identity.py --act <migrated-act> --check
python3 scripts/generate_full_script.py --check
```
