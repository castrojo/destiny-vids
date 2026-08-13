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
| Turn the owner's dictated Whisp notes into filed issues, or find out why a submitted request never landed | [`intake.md`](skills/intake.md) |
| File work, pick up an issue, or normalize a request into a brief | [`issues.md`](skills/issues/SKILL.md) |
| Take an issue all the way to a rendered cut, or make videos in volume | [`production.md`](skills/production/SKILL.md) |
| Index a new video: detect beats, extract keyframes, tag, assemble segments | [`indexing.md`](skills/indexing.md) |
| Cast a character, add a lead binding, or credit the monthly ensemble | [`casting.md`](skills/casting/SKILL.md) |
| Find out what footage a character actually has — and what they lack | [`corpus.md`](skills/corpus.md) |
| Write an outline, assemble a cut list, mark material for removal, or render it | [`editing.md`](skills/editing/SKILL.md) |
| Score a cut to a music bed, pause the song mid-cut, or land a shot on a beat | [`scoring.md`](skills/scoring/SKILL.md) |
| Put a name on screen — Guardian nameplates and title cards | [`plates.md`](skills/plates/SKILL.md) |
| Join several finished cuts into one programme with chapter cards | [`megacut.md`](skills/megacut/SKILL.md) |
| Run a long encode on the ghost cluster instead of the laptop | [`farm.md`](skills/farm.md) |
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
same front matter, same size budget, same "link to canonical sources
instead of duplicating them" rule. The one local difference is `category`, whose
enum here is `indexing | editing | meta` (see `skills/index.schema.json`) —
this repo builds videos, not container images.

**The size budget is 200 lines soft, 500 hard, and it is *migrate on sight*.**
A skill that outgrows one file becomes `skills/<name>/SKILL.md` plus
`skills/<name>/references/*.md` — **in the same change that touched it**, with
no exemptions and no deferral list. `SKILL.md` keeps the front matter, the
triggers, the core workflow, the red flags, and a table pointing at each
reference; the detail moves out. `plates` and `editing` are the worked
examples, both migrated from 500-line flat files on 2026-08-13.

Two tests hold the line: `test_skill_size_budget` measures every flat skill,
every `*/SKILL.md` **and** every reference file, and
`test_migrated_skill_points_at_its_references` fails a migrated skill that
orphans one of its own references. `tests/test_doc_links.py` proves every
relative link in the docs tree still resolves — the check that a split is an
improvement rather than a pile of dead ends.

After adding or editing a skill:

```bash
python3 scripts/generate_skill_index.py --write
python3 -m pytest -q tests/test_skill_catalog.py tests/test_doc_links.py
```
