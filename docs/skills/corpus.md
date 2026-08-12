---
name: corpus
version: "1.0"
last_updated: "2026-08-12"
id: corpus
one_line_purpose: Catalog every indexed shot of one character, and the coverage they lack.
entry_point: docs/skills/corpus.md
category: editing
mcp_compliance_level: partial
optimization_status: draft
status: active
dependencies: [casting, editing]
tags: [corpus, character, coverage, gaps, unresolved]
description: >-
  Builds a per-character catalog of indexed shots plus the vocabulary values
  that have no clean coverage. Use before writing an outline for a character,
  or when extending the index to the next character or story.
metadata:
  type: procedure
---

# Character corpus

## When to Use

- Before writing an outline: what has this character actually got?
- A beat will not match and you need to know whether the footage exists at all
- Extending coverage to the next character or story

## When NOT to Use

- Matching a specific beat to a shot → [`editing.md`](editing.md)
- Binding a character to a person → [`casting.md`](casting.md)
- Tagging new footage → [`indexing.md`](indexing.md)

## Core Process

```bash
python3 tools/corpus.py ensemble --dir segments              # read it
python3 tools/corpus.py osiris --dir segments --out corpus/osiris.json
python3 tools/corpus.py --write                              # rebuild all committed
python3 tools/corpus.py --check                              # ...and fail if stale
```

A **subject** is a casting subject, because casting is how this index says who
is in a shot: a lead key from `vocab/casting.yaml` (`osiris`, `zavala`, ...) or
`ensemble`, the anonymous Guardian — every blueberry in the crowd.

Each corpus holds the subject's shots (tags, timecodes, `clean`, `caption`),
coverage counts per axis, and `gaps`.

### A corpus spans every source, and that is the mission

**`corpus.py` pools a character across the whole index, not one cinematic**, and
the header says so explicitly:

```text
CORPUS: mara_sov
6/6 clean shot(s), 11.304s across 2 video(s)
```

That cross-source pool **is the shot list for that character's hero video** —
one person, one video, every instance of them in the collection
([`docs/cuts/hero-montage.md`](../cuts/hero-montage.md)). Read the corpus first
and the outline writes itself: one beat per shot, and `tools/story.py` with no
`--from-video` spans exactly the same pool.

So a corpus is also **the coverage ledger for a finished hero video**. Because a
montage is defined as "all of them", the corpus is what says whether the video
is complete as of the current index — and when a new cinematic is indexed, the
corpus grows and the hero video becomes re-cuttable. Hero videos are not final;
they are complete *as of an index*.

### Gaps are the point

A gap is a `vocab/` enum value the subject has **no clean coverage of**. That is
an editorial fact: it is exactly what makes a beat unwritable. Each gap carries
`status: unresolved` and, where relevant, the unclean shots that would have
covered it — so "there is no footage" and "the footage exists but the clean
gate bars it" stay distinguishable. They have different fixes: one needs new
indexing, the other needs a re-tag or nothing at all.

Unclean shots stay **in** the corpus, labelled with `blocked_by`. Knowing the
footage exists and why it cannot be cut is what stops the next person
re-finding it and re-arguing it.

### Adding the next character or story

1. Make sure the shots are cast: a lead needs its binding in
   `vocab/casting.yaml`, and `tools/derive.py` computes `casting` from there.
2. `python3 tools/corpus.py <subject> --dir segments --out corpus/<subject>.json`
3. Commit the file. `--write` / `--check` then keep it in sync for everyone,
   the same way `scripts/generate_skill_index.py` keeps the skill catalog fresh.

The amount of Destiny footage is finite, so the corpus directory is meant to
grow one subject at a time until it covers all of it. Nothing about it is
per-cut: a corpus outlives the video it was first built for.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll add the missing shot to the corpus so the beat lands." | The corpus is derived from `segments/`. Index the footage or rewrite the beat. |
| "The unclean shot covers it well enough." | Then the gap would not be reported. The clean gate is a gate, not a preference. |
| "I'll note the music cue in the corpus file." | Editorial unknowns belong in the cut's doc under `docs/cuts/`. The corpus only holds what is derivable from the index. |
| "`unknown` on an axis is a gap." | `unknown` means *not determinable*, not a shot someone could go get. It is excluded on purpose. |

## Red Flags

- Hand-editing a file in `corpus/`. It is derived; the next `--write` discards
  the edit. This is the same mistake as hand-editing `clean`.
- A gap quietly disappearing between commits without new footage being indexed.
- Writing a beat against a value listed in `gaps`. It cannot land, and forcing
  it means widening to unclean footage.

## Verification

```bash
python3 -m pytest -q tests/test_corpus.py
python3 tools/corpus.py --check
```

Worked example, including how one cut's unresolved beats were recorded rather
than guessed: [`docs/cuts/01-dance.md`](../cuts/01-dance.md). For a corpus
written *before* the outline, so the beats could be shaped around the gaps it
reported, see [`docs/cuts/03-zavala.md`](../cuts/03-zavala.md). The axes
themselves are documented in `docs/taxonomy.md`.
