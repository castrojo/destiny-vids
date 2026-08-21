# Chapter conversations

## When to Use

- Adding or rewriting an act's chat dialogue without computing timecodes
- Giving one character several lines in a row — each its own pill
- Seating or rewording a red splash (the boss bar) — `! NAME` lines
- Dropping a whole conversation at one programme timestamp

## When NOT to Use

- Recovered footage dialogue for a source video → `dialogue/<video_id>/`
  and `tools/dialogue_md.py`
- Nameplates, title cards, and other chrome → [`plates`](plates/SKILL.md)

## Where each act's chat lives today

Read this table before touching any chat copy — the convention is only
partly rolled out, and the two systems with similar names are easy to
confuse:

- `chapters/<act>.md` — **what the owner writes.** One file per act with
  chapter dialogue; the build reads it and the pills land in the generated
  manifest. The owner's format spec (one `## <programme time>` heading per
  conversation, `Speaker: line` rows, `@ <time>` pins, `!` splashes) is in
  the file's own header.
- `dialogue/<video_id>/` — **recovered-footage provenance.** What the
  characters in a *source video* visibly say, with timecodes and evidence.
  Chapter seating uses it as evidence; it is not where act copy is edited.

| Act | Chat copy lives in |
|---|---|
| 0 — prologue | `stories/00-perfume-4-plates.json` (inline pills) |
| I — intro | — (no chat) |
| II — endlessforms | `chapters/II-endless-forms.md` — today it authors only the two red splashes; the conversation pills are still `NEW_CHATS` in `scripts/build_efmb_plates.py` |
| III — mrbobbytables | `dialogue/yt_curse_of_osiris_opening_cinematic/` — the whole Bob/Andy conversation, burned into the act master |
| IV — kat | `stories/04-kat-plates.json` (inline pills) |
| V — nat | `stories/05-natali-plates.json` (inline pills) |
| VI — 7daystothewolves | `stories/06-wolves-cayde-plates.json` (inline pills) |
| VII — europa | `stories/07-europa-plates.json` (inline pills) |
| VIII — credits | — (no chat) |

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

Each act with chapter dialogue has one Markdown file, `chapters/<act>.md`
(today: act II). The owner edits it; the act's build script reads it and the
pills land in the generated plate manifest. The file's own header is the
usage doc — one `## <programme time>` heading per conversation, `Speaker:
line` rows under it, `@ <time>` on a row to pin that line exactly.

Timing is derived, never typed: a line holds for `len(text) / 15` seconds
clamped to [2.2, 7.0] — characters-per-second, the metric pysrt exposes as
`characters_per_second`, set conservative for a theatre screen — with a
0.25 s beat between pills. A pinned line lands exactly; slack before it is
silence, and a pin that overruns its neighbour is honoured with the overlap
recorded in the manifest's `unresolved`. **The clock is the whole show's** —
the conversion constants live in `tools/chapter_md.py`
(`ACT_PROGRAMME_START`) with their derivations, and are the only thing to
revisit when the running order's timings change.

**Seats follow the speech on screen.** A line whose words match the act's
recovered dialogue — the shots where the characters visibly say them — is
seated at that moment, not where the cascade would put it (owner ruling,
2026-08-20). A pin still wins. Every seat taken or overridden is printed by
`show`, printed to stderr at build time, and recorded in the manifest:
always inform the operator of improvements, never apply them silently.

## Core Process

```bash
$EDITOR chapters/II-endless-forms.md
python3 tools/chapter_md.py show II          # the schedule it resolves to
python3 scripts/build_efmb_plates.py --write # regenerate, never hand-edit
```

## Red Flags

- Opening `dialogue/` folders looking for an act's chat to copyedit. Only
  act III's lives there; the trailers folder is the orphan stub in the table
  above. The other acts' copy is in their plate manifests (or, for act II,
  the builder's `NEW_CHATS`).
- Migrating one act and stopping. The convention is per-chapter; an act left
  inline in its manifest is a copyedit the owner has to do in JSON.
- Typing per-line timecodes for every row — that is what the heading and the
  read-speed timing replace; pin only the lines that must land exactly.
- Editing the generated `stories/02-endless-forms-plates.json` by hand.
  CI regenerates it; the Markdown is the source.
- A line left blank under a real name. Blank text renders as a placeholder
  credited to nobody — which is right for an unwritten slot and wrong as a
  way to silence a line. Delete the row to drop the line.
- Recomputing `ACT_PROGRAMME_START` from memory. The constant carries its
  derivation; restate it from `stories/megacut/megacut.json` when the
  programme's timings move.

## Verification

```bash
python3 -m pytest -q tests/test_chapter_md.py
python3 tools/chapter_md.py show II
```
