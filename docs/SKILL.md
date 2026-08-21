# destiny-vids Skill Router

Agent entry point for `destiny-vids`. Find the skill that matches your task,
load **only** that skill, then act.

## Read order

1. [`AGENTS.md`](../AGENTS.md) — repo contract, commands, boundaries.
2. [`running-order.md`](running-order.md) — what the show is.
3. This file — task→skill mapping.
4. The skill named below, and the design docs it links to.

## Skill index

| I need to... | Load |
|---|---|
| Turn the owner's dictated Whisp notes into filed issues, or find out why a submitted request never landed | [`intake`](skills/intake.md) |
| File work, pick up an issue, or normalize a request into a brief | [`issues`](skills/issues/SKILL.md) |
| Take an issue all the way to a rendered cut, or make videos in volume | [`production`](skills/production/SKILL.md) |
| Index a new video: detect beats, extract keyframes, tag, assemble segments | [`indexing`](skills/indexing.md) |
| Cast a character, add a lead binding, or credit the monthly ensemble | [`casting`](skills/casting/SKILL.md) |
| Find out what footage a character actually has — and what they lack | [`corpus`](skills/corpus.md) |
| Write an outline, assemble a cut list, mark material for removal, or render it | [`editing`](skills/editing/SKILL.md) |
| Score a cut to a music bed, pause the song mid-cut, or land a shot on a beat | [`scoring`](skills/scoring/SKILL.md) |
| Meet the audio standard every delivered file is held to | [`audio`](skills/audio/SKILL.md) |
| Put a name on screen — Guardian nameplates and title cards | [`plates`](skills/plates/SKILL.md) |
| Add or re-time an act's chat dialogue in one Markdown file per chapter | [`chapters`](skills/chapters.md) |
| Join the finished acts into one programme | [`megacut`](skills/megacut/SKILL.md) |
| Apply a round of notes without rebuilding acts that were already right | [`review`](skills/review.md) |
| Run a long encode on the ghost cluster instead of the laptop | [`farm`](skills/farm.md) |

This table is the catalog. There is no generated index behind it — add a row
when you add a skill.

## Design docs (reference, not skills)

These explain *why* the model is shaped this way. A skill links to them rather
than restating them:

| Doc | What it covers |
|---|---|
| [`taxonomy.md`](taxonomy.md) | Every axis and field, and the casting model. |
| [`pipeline.md`](pipeline.md) | Segmentation, inheritance, review tiers, cost posture. |
| [`agent-retrieval.md`](agent-retrieval.md) | How a natural-language query maps to filters and ranking. |
| [`rendering.md`](rendering.md) | Which ffmpeg, why, and the seeking/AV1 traps. |
| [`../schema/brief.schema.json`](../schema/brief.schema.json) | Every field of an issue's `brief` block. |

## Writing a skill here

A skill is a plain Markdown file: an H1, when to use it, the workflow, the
traps. No front matter, no version field, no catalog entry — the router table
above is the only registration step.

**Write the current state, not the history that produced it.** No
version-by-version narration, and no prose copy of a fact that has a machine
record — link the record instead. See "Documentation" in
[`AGENTS.md`](../AGENTS.md).

Keep a skill to one file until it is genuinely unreadable; only then split it
into `skills/<name>/SKILL.md` plus `skills/<name>/references/*.md`. A split
costs an agent an extra read, so it needs to buy more than tidiness.

`tests/test_doc_links.py` proves every relative link in the docs tree
resolves. That is the only check on this tree, and it is enough.
