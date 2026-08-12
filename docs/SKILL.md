# destiny-vids Skill Router

Agent entry point for `destiny-vids`. Find the skill that matches your task,
load only that skill, then act.

## Read order

1. [`AGENTS.md`](../AGENTS.md) — repo contract, commands, boundaries.
2. This file — task→skill mapping.
3. The skill file named below, and the design doc it links to.

## Skill index

| I need to... | Load |
|---|---|
| File work, pick up an issue, or normalize a request into a brief | [`issues.md`](skills/issues.md) |
| Take an issue all the way to a rendered cut, or make videos in volume | [`production.md`](skills/production.md) |
| Index a new video: detect beats, extract keyframes, tag, assemble segments | [`indexing.md`](skills/indexing.md) |
| Cast a character, add a lead binding, or credit the monthly ensemble | [`casting.md`](skills/casting.md) |
| Find out what footage a character actually has — and what they lack | [`corpus.md`](skills/corpus.md) |
| Write an outline, assemble a cut list, mark material for removal, or render it | [`editing.md`](skills/editing.md) |
| Score a cut to a music bed, pause the song mid-cut, or land a shot on a beat | [`scoring.md`](skills/scoring.md) |
| Put a name on screen — Guardian nameplates and title cards | [`plates.md`](skills/plates.md) |
| Join several finished cuts into one programme with chapter cards | [`megacut.md`](skills/megacut.md) |
| Get a working ffmpeg on an atomic host | [`../docs/rendering.md`](rendering.md) |

The machine-readable catalog is [`skills/index.json`](skills/index.json), with a
human-readable mirror at [`skills/index.md`](skills/index.md). Both are generated
by `scripts/generate_skill_index.py` — do not hand-edit either.

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
| [`plans/wolves/design.md`](plans/wolves/design.md) | **Planned, not built.** The comm-line system: `WOLVES.md`, identity, affiliation, tempo. |

## Writing a skill here

Follow `projectbluefin/common`'s
[`docs/skills/write-a-skill.md`](https://github.com/projectbluefin/common/blob/main/docs/skills/write-a-skill.md):
same front matter, same 200-line soft budget, same "link to canonical sources
instead of duplicating them" rule. The one local difference is `category`, whose
enum here is `indexing | editing | meta` (see `skills/index.schema.json`) —
this repo builds videos, not container images.

After adding or editing a skill:

```bash
python3 scripts/generate_skill_index.py --write
python3 -m pytest -q tests/test_skill_catalog.py
```
