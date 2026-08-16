# Working from issues

## When to Use

- Filing a video idea, or a defect in the index
- Picking up work as an agent, and deciding whether you may finish it
- Turning a prose request into something a tool can execute
- Finding out what in the index is unfinished

## When NOT to Use

- Indexing a video once you have the brief → [`indexing.md`](../indexing.md)
- Assembling and rendering the cut → [`production.md`](../production/SKILL.md)
- Deciding who a shot depicts → [`casting.md`](../casting/SKILL.md)

## The shape of the backlog

Issues are the only backlog. There is no TODO file, no notes doc, and no
planning markdown in the repo — those go stale and mislead the next agent.

An issue carries two things, and they have different jobs:

- **The prose** is how the owner thinks. It stays exactly as written.
- **The `brief` block** is the same request in YAML, matching
  [`schema/brief.schema.json`](../../../schema/brief.schema.json). Tools read it.

````markdown
```brief
title: Harbringer — All shall burn
sources:
  - url: https://www.youtube.com/watch?v=0B9v8VoZrMU
music:
  url: https://music.youtube.com/watch?v=oKXIo7EOgXY
  note: melancholy; make it all fit
characters: [saint_14]
automatable: partly
blocked_on: the source is not indexed yet
```
````

Writing the block is **not the owner's job**. An agent proposes it; the owner
confirms it. That division is the point: it puts a human at the exact moment
where a guess would otherwise be made.

A brief's `plates[]` deserve a special mention: copy there is the owner
speaking, and the **one** place a new claim about a real person may enter the
system — a brief can name somebody who has no binding in `vocab/casting.yaml`
yet. `tools/plate.py plan --brief` turns them into fixed, owner-timed credits;
the rules (closed field set, the vocab wins a conflict, provenance on every
plate) are in [`plates.md`](../plates/SKILL.md).

```bash
python3 tools/brief.py normalize 3   # prose -> a PROPOSED block, printed
python3 tools/brief.py parse 3       # a confirmed block -> validated JSON
python3 tools/brief.py check         # every open issue's block
```

A proposal always comes back `automatable: no`. It is a reading of what
somebody meant, and it is not executable until they say it is right.

## Picking up work

1. Read the issue, prose included. The prose carries intent the block cannot.
2. `python3 tools/brief.py parse <issue>`. No block yet? Normalize, post the
   proposal, and wait — do not start from your own reading of the prose.
3. Check `automatable`. `no` means stop now and say what you need.
4. Check the issue is `agent-ready` and unassigned, then assign yourself.
5. Work on a branch, one issue per branch. `vocab/casting.yaml` is the file
   every video touches, so a casting change belongs in its own small PR rather
   than buried in a cut.
6. Open a PR saying `Closes #NNN`.

## Where the detail lives

This skill is the contract. The rest lives in `references/`:

| Reference | What is in it |
|---|---|
| [`labels-and-gaps.md`](references/labels-and-gaps.md) | The four state labels and three reading axes, the two-agents-one-issue race, and `tools/gaps.py` for finding the unfinished. |

## What is not an agent's call

Two things genuinely stop work, because neither can be undone after publishing:
a **rights** decision, and a **`clean`** violation. Everything else degrades and
carries on — see "Degrade, never block" in [`AGENTS.md`](../../../AGENTS.md).

A missing string is never a reason to halt. A brief naming somebody uncast runs
on the names that resolve and records the rest in `unresolved`; a plate whose
subclass nobody authored renders without that row. Ship it, record the gap,
move on.

What stays forbidden is *inventing* the missing string. These look alike and
are opposites:

| | |
|---|---|
| **Missing** a word | Omit, ship, record. |
| **Inventing** a word | Never. It puts words on a real colleague. |

So: name a character only where they are visibly in frame, never write plate
copy nobody authored, and leave rights calls to the owner. Then keep going.

| Class | Why it is the owner's | Worked example |
|---|---|---|
| A visual judgement about a frame | "Nobody has looked at this" is not evidence the frame is clean. | unreviewed beats keeping a video out of every cut |
| A claim about a real person | Casting, plate copy, a subclass, a pronoun. | a subclass word nobody has authored |
| A licensing decision | Rights are the owner's to accept. | ND-licensed photographs blocking a treatment |

Use `automatable: no` for work that genuinely cannot proceed, put the exact
missing decision in `blocked_on`, and file it. Do not use it for a gap you
could have shipped around.

**Before you mark anything blocked, read the issue's own comments.** The most
common defect in this backlog is not a wrong decision, it is an issue sitting
`blocked` on a question the owner already answered in a comment months earlier
— #73 waited on "who is Orlin" while the answer, a GitHub profile and "only in
the intro", sat two comments up. An owner reply is an instruction to execute,
not a note to file. Re-asking a question that has been answered is the same
cost as inventing an answer: the work does not happen.

**Do not cite a tool, test, or file you have not opened.** #222 and #223 were
filed on the findings of `tools/quality.py`, recorded in `sources/unindexed.json`
and guarded by `tests/test_quality.py` — none of which have ever existed here.
Both issues had a real defect inside them, and both were unusable, because
nothing they pointed at could be read. Check with `git log --all -- <path>`
before you cite: a path with no history never existed, and one with history was
deleted and needs repointing at whatever holds the fact now.


## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "A word is missing, so I have to stop." | No. Omit the row, ship the cut, record the gap. Only rights and `clean` stop work. |
| "I'll fill in the missing subclass, it's obvious." | That is inventing, not iterating. It puts words on a real colleague. |
| "The prose is clear enough, I'll just start." | Two agents reading the same prose build two different cuts. Normalize, confirm, then work. |
| "I'll add a `character/paris` label." | Characters live in the brief, in the index's own vocabulary. A label set is a second vocabulary that drifts. |
| "The owner obviously means Paris is a Titan." | That is a claim about a real person. `automatable: no`. |
| "I'll mark it automatable so it isn't stuck." | Stopping is a result here. A wrong credit is not recoverable by a revert. |
| "This is blocked on an owner decision." | Read the comments first. He has usually already answered, and the issue is waiting on you, not on him. |
| "The audit tool reported…" | Open the tool. `git log --all -- <path>` it. Do not cite evidence you did not read. |
| "I'll note the remaining work in NOTES.md." | It goes in an issue. Files like that go stale and mislead the next agent. |

## Red Flags

- A brief that sets `clean`, `footage_tier`, `traversal_hero` or `casting`.
  Those are derived by `tools/derive.py`; a brief that carries one is
  overwritten. `tools/brief.py` refuses it.
- A character id that is not in `vocab/casting.yaml`. That is a casting
  decision wearing a typo's clothes.
- `automatable: no` with an empty `blocked_on` — the next agent has to
  rediscover the blocker.
- A planning or notes markdown file appearing in the repo.

## Verification

```bash
python3 tools/brief.py check
python3 tools/gaps.py
python3 -m pytest -q tests/test_brief.py tests/test_gaps.py
```

The field-by-field brief reference is
[`schema/brief.schema.json`](../../../schema/brief.schema.json); what happens once
a brief is executable is [`production.md`](../production/SKILL.md).
