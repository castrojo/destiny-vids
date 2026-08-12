---
name: corpus
version: "1.0"
last_updated: "2026-08-12"
id: corpus
one_line_purpose: Build and read the per-character corpus of indexed footage.
entry_point: docs/skills/corpus.md
category: indexing
mcp_compliance_level: partial
optimization_status: draft
status: active
dependencies: [casting, indexing]
tags: [corpus, coverage, gaps, characters, unresolved]
description: >-
  The generated per-character corpus: what footage exists for each cast member,
  how much of it is cuttable, and what is missing. Read it before writing an
  outline, when extending the index, or when a cast request cannot be settled
  from the footage.
metadata:
  type: procedure
---

# The character corpus

`segments/` answers *what is this shot?*. The corpus answers *what do we have of
this character, how much of it can I cut, and what is missing?* — the question
you actually ask before writing an outline.

## When to Use

- Writing a story around a character: check coverage before writing beats
- Extending the index to the next character or story
- Recording a cast request that cannot be settled from the footage

## When NOT to Use

- Retrieving shots for one beat → `tools/search.py`, see `docs/agent-retrieval.md`
- Deciding *who* plays a character → [`casting.md`](casting.md)
- Tagging new footage → [`indexing.md`](indexing.md)

## Core Process

```bash
python3 tools/corpus.py --character osiris   # coverage for one character
python3 tools/corpus.py --write              # rebuild after indexing or recasting
python3 tools/corpus.py --check              # what CI runs
```

`corpus/characters.json` and its mirror `corpus/README.md` are **generated**.
Hand-editing either is the same mistake as hand-editing `clean`: the next
`--write` discards it, and in between the corpus lies about the index.

The corpus is a view, not a second source of truth. It re-derives `clean` and
`footage_tier` through `tools/derive.py` instead of reading them off the record,
so a hand-set gate cannot be laundered into "coverage". `usable` is evaluated
per character rather than copied from the record's `casting`, which only ever
names the first character matched in a two-hander — otherwise Sagira would lose
every shot she shares with Osiris.

### Extending it to the next character

The amount of Destiny footage is fixed, so this is a long walk taken one story
at a time. The corpus is the ratchet:

1. Index a video ([`indexing.md`](indexing.md)). Beats carry `character` names.
2. Bind any new character in `vocab/casting.yaml` ([`casting.md`](casting.md)).
3. `python3 tools/corpus.py --write` and commit the corpus with the segments.

Nothing in the corpus is per-character code: a name tagged in a frame shows up
the moment the segments land, bound or not.

### Reading the gaps

`unresolved` is the useful half of the file — a gap is the next piece of work:

| kind | Means | Next step |
|---|---|---|
| `uncast_lead` | Footage exists, nobody is bound to the character | A casting decision (a human's) |
| `unindexed_lead` | Someone is cast, the index has zero shots of them | Index a video that features them |
| `unbound_character` | A name tagged in footage with no entry in `leads.values` | Decide whether it is a castable role |
| `pending_binding` | A person was requested, their character is unknown | See below |

Every gap carries `automatable`, and `blocked_on` when there is something to
wait for. `automatable: false` means the next step needs a human who has seen
the footage.

### A request you cannot settle

A cast request arrives as a person plus a description of a figure on screen —
"the woman", "the main character". Turning that into a Destiny character is a
visual judgment, and if the video is not indexed there is nothing to look at.
Record it in `vocab/casting.yaml` under `leads.pending`, quoting the requester's
own words in `described_as`, and let the corpus carry it:

```yaml
  pending:
    <github-handle>:
      github: <github-handle>
      display_name: null        # null until someone says how they are credited
      described_as: Woman       # the requester's words, never a character name
      requested_in: <issue url>
      source_video: <video url>
      automatable: no
      blocked_on: >
        The source video is not ingested, so no indexed shot shows this figure.
```

Derivation never reads `pending`. The entry casts nobody, plates nothing, and
needs no search phrase until it is promoted into `leads.values` — at which point
it is an ordinary binding and [`casting.md`](casting.md)'s checklist applies.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "It's obviously Ikora — who else would it be?" | You have not seen the video. A wrong binding credits a real person for a shot they are not in. Park it in `pending`. |
| "I'll hand-edit the corpus, it's just a table." | It is generated. Your edit disappears on the next `--write` and lies until then. |
| "The character has 22 shots, that's plenty of coverage." | Count `usable` and `clean`, not `shots`. A constrained binding's failed shots are not coverage. |
| "The request can live in the PR description." | A request nobody can query is a request that gets dropped. It goes in the vocab, and a test pins it. |

## Red Flags

- Promoting a `pending` entry to a binding without having watched the footage.
- Committing segments without re-running `--write`; the check fails, and a stale
  corpus points an outline at footage that is not there.
- Reading `clean` from a corpus row and assuming the record agreed — if they
  disagree, the record is wrong and `tests/test_derive.py` will say so.
- Treating an empty `unresolved` list as success. Nine of the leads have no
  footage indexed at all; that list is the roadmap.

## Verification

```bash
python3 -m pytest -q tests/test_corpus.py
python3 tools/corpus.py --check
```

The casting model itself is in `docs/taxonomy.md`; retrieval weights are in
`docs/agent-retrieval.md`.
