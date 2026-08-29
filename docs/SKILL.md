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
| Take an issue all the way to a rendered cut, or make videos in volume | [`production`](skills/production/SKILL.md) |
| Cast a character, add a lead binding, or credit the monthly ensemble | [`casting`](skills/casting/SKILL.md) |
| Write an outline, assemble a cut list, mark material for removal, or render it | [`editing`](skills/editing/SKILL.md) |
| Meet the audio standard every delivered file is held to | [`audio`](skills/audio/SKILL.md) |
| Put a name on screen — Guardian nameplates and title cards | [`plates`](skills/plates/SKILL.md) |
| Add or re-time an act's chat dialogue in one Markdown file per chapter | [`chapters`](skills/chapters.md) |
| Join the finished acts into one programme | [`megacut`](skills/megacut/SKILL.md) |
| Run a long encode on the ghost cluster instead of the laptop | [`farm`](skills/farm.md) |
| Replace the rest of a video with the reusable LF training CTA | [`training-cta`](skills/training-cta/SKILL.md) |
| Build a Hive episode or the full Season of the Blueberries cut | [`hive`](skills/hive.md) |
| Work out why CI is red when the suite is green here, or add a check | [`testing`](skills/testing.md) |

This table is the curated task router. The complete generated catalog lives in
[`skills/index.json`](skills/index.json), with a human-readable mirror in
[`skills/index.md`](skills/index.md). Both are generated from skill front
matter by `scripts/generate_skill_index.py`; never hand-edit them.

## Design docs (reference, not skills)

These explain *why* the model is shaped this way. A skill links to them rather
than restating them:

| Doc | What it covers |
|---|---|
| [`rendering.md`](rendering.md) | Which ffmpeg, why, and the seeking/AV1 traps. |
| [`../schema/brief.schema.json`](../schema/brief.schema.json) | Every field of an issue's `brief` block. |

## Writing a skill here

Follow the local [skill metadata rules](../AGENTS.md#documentation) for every
canonical skill. [`projectbluefin/common`'s `write-a-skill.md`](https://github.com/projectbluefin/common/blob/main/docs/skills/write-a-skill.md)
is the compatible cross-repository reference.

**Write the current state, not the history that produced it.** No
version-by-version narration, and no prose copy of a fact that has a machine
record — link the record instead. See "Documentation" in
[`AGENTS.md`](../AGENTS.md).

Keep a skill to one file until it is genuinely unreadable; only then split it
into `skills/<name>/SKILL.md` plus `skills/<name>/references/*.md`. A split
costs an agent an extra read, so it needs to buy more than tidiness.

`tests/test_doc_links.py` proves every relative link in the docs tree resolves.
`scripts/check-skill-frontmatter.sh` and
`scripts/generate_skill_index.py --check` validate the skill metadata and
generated catalog.
