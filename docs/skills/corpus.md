---
name: corpus
version: "1.0"
last_updated: "2026-08-12"
id: corpus
one_line_purpose: Catalog every indexed shot a character appears in, and record the gaps.
entry_point: docs/skills/corpus.md
category: indexing
mcp_compliance_level: partial
optimization_status: draft
status: active
dependencies: [indexing, casting]
tags: [corpus, character, coverage, gaps, unresolved]
description: >-
  Covers building a per-character shot catalog from the index and recording what
  the footage cannot cover. Use before writing a story about a character, or when
  answering "do we have footage of X?".
metadata:
  type: procedure
---

# Character corpus

The index is organised by video. A cut is organised by **who is in it**. The
corpus pivots one into the other and writes the answer down, so the next story
about the same character starts from a catalog instead of a re-read of every
segment file.

## When to Use

- Before writing an outline about a character — find out what exists first
- Answering "do we have clean footage of X?"
- Recording a beat the footage cannot cover, so it is not rediscovered later
- After indexing a new video, to refresh what it added

## When NOT to Use

- Matching beats to shots → [`editing.md`](editing.md)
- Adding or changing a lead binding → [`casting.md`](casting.md)
- One-off queries you will not need twice → `tools/search.py`

## Core Process

```bash
python3 tools/corpus.py build cayde_6     # writes corpus/cayde_6.json
python3 tools/corpus.py check             # fails if any committed corpus is stale
```

`build` takes any lead key from `vocab/casting.yaml`. It matches the derived
`casting.character` first — the authoritative answer — and falls back to
normalising raw `character[]` names through the same alias index derivation
uses, so a corpus can never disagree with a cut.

`check` rebuilds every committed corpus and fails if one has drifted, the same
contract `scripts/generate_skill_index.py --check` applies to this catalog. Run
it after indexing a video.

### Two halves, and the split is the point

| Half | Fields | Rule |
|---|---|---|
| **Derived** | `shots`, `coverage`, `cast` | A projection of the segment records, with no judgement of its own. Regenerating overwrites it. |
| **Authored** | `unresolved` | The gaps. Read back off the existing file and preserved verbatim on every rebuild. |

`clean`, `footage_tier` and `overlays` travel with every shot, because `clean`
is the gate an editor is about to make a decision against and `overlays` is why
it says what it says. `coverage` counts clean shots separately from total shots
for the same reason: 40 seconds of a character is not 40 seconds you can cut.

### Recording a gap

A gap is **recorded, never guessed**. Add it to `unresolved` by hand; the next
rebuild keeps it.

```json
{
  "id": "cayde_plate_anchor",
  "need": "His only indexed shot is 1.201s, under plate.py's 1.5s MIN_ANCHOR.",
  "status": "unresolved",
  "automatable": false,
  "blocked_on": "footage: needs a Cayde shot of at least 1.5s"
}
```

`id`, `need`, `status` (`unresolved` | `todo` | `blocked`) and `automatable` are
required. `automatable: false` must say what it is `blocked_on` —
`validate_gaps()` rejects the alternative, because a gap that does not name its
blocker is a shrug, not a record.

`automatable: false` is the honest answer for a visual judgement, a claim about
a real person, or a licensing decision. All three are somebody else's call.

### Extending the index

The amount of Destiny footage is finite, so this accumulates: one file per
character in `corpus/`, added a character or a video at a time. Build, commit,
and `check` keeps it honest from then on. When new footage lands, rebuild — the
derived half updates and the recorded gaps come with it, so a gap that has just
been filled shows up sitting next to footage that now exists.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll add the missing shot to the corpus and tag it later." | The corpus is a projection of the index. A shot that is not indexed does not exist; that is a gap, not an entry. |
| "The character is probably in that other trailer too." | Probably is not an index. Build the corpus for the video after it is tagged. |
| "I'll drop the gap, it's obvious." | It was not obvious to whoever hits it next. The whole authored half exists so "we do not have this" survives. |
| "I'll hand-edit `shots` to fix a caption." | Fix the segment record and rebuild; `check` will catch the drift anyway. |

## Red Flags

- A corpus with `unresolved: []` after a story hit a wall. The wall is the data.
- `automatable: false` with no `blocked_on` — the validator rejects it, and it
  is rejected because it is a non-answer.
- Editing `coverage` counts by hand instead of rebuilding.
- Treating `seconds` as usable footage. Check `clean_shots` and `clean`.

## Verification

```bash
python3 -m pytest -q tests/test_corpus.py
python3 tools/corpus.py check
```

The casting model behind `casting.character`: [`casting.md`](casting.md). Field
definitions: [`../taxonomy.md`](../taxonomy.md). A worked example of a corpus
driving a cut: [`../../stories/01-cayde-6-the-return.md`](../../stories/01-cayde-6-the-return.md).
