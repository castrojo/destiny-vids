# Common Documentation Alignment

## Goal

Align `destiny-vids` with the documentation and skill-maintenance model in
`projectbluefin/common` without importing factory workflow policy that does not
belong in this repository.

The result keeps `destiny-vids` authoritative for editorial policy, casting,
delivery, GitHub issues, protected `main`, and its merge queue. Common supplies
the shared shape for agent contracts, skill metadata, generated catalogs,
validation, and self-repair.

## Authority and read order

`AGENTS.md` remains the first and strongest local contract. The read order is:

1. `AGENTS.md` for local policy, commands, paths, and boundaries.
2. `docs/running-order.md` for the authored programme order.
3. `docs/SKILL.md` for task routing.
4. The routed local skill and its references.
5. `projectbluefin/common/docs/factory/agentic-model.md` as a shared sidecar
   for compatible cross-repository agent practices.

Common never overrides local rules. Inapplicable factory policies are not
copied into this repository: Hive assignment, factory label lifecycle, OCI
promotion, testing branches, and common's doc-only direct-push exception stay
out.

## Agent contract changes

`AGENTS.md` will:

- replace the claim that skills have no front matter or generated catalog;
- add the two-output rule: each implementation produces the work and any
  durable learning it exposed;
- add the every-loop sequence: verify, detect drift, repair the nearest
  authoritative record, validate, and write back;
- require issue applicability checks before an issue is reported or acted on;
- state that issue references are historical evidence until current
  authoritative records and git history establish that they still apply;
- point to the local generated catalog and common's shared agentic model;
- retain every existing editorial, rights, rendering, delivery, and merge rule.

No additional agent instruction files will be created. The audit found no
`.github/agents/`, `CLAUDE.md`, `GEMINI.md`, or Copilot instruction file.
Creating parallel contracts would introduce drift rather than alignment.

## Skill format

Every canonical skill file under `docs/skills/` will receive YAML front matter
compatible with common's catalog fields:

- `name`, `id`, `version`, `last_updated`;
- `one_line_purpose`, `entry_point`, `category`;
- `status`, `dependencies`, `tags`, `description`;
- `metadata.type`;
- optional `metadata.context7-sources` when external behavior has been
  verified through Context7.

The local category enum will describe this repository rather than reuse
common's image-factory-only values. Initial categories are:

- `editorial`
- `media-production`
- `metadata`
- `operations`
- `meta`

Each skill must expose enough structure for an agent to decide when and how to
use it:

- `## When to Use`
- `## When NOT to Use` where exclusions matter
- `## Core Process` or an equivalent procedural section
- `## Common Rationalizations` where the domain has recurring unsafe shortcuts
- `## Red Flags`
- `## Verification`

Existing domain content is preserved. This migration changes discoverability
and maintenance structure, not editorial policy.

## Progressive disclosure and size

Common's 200-line soft limit and 500-line hard limit apply to canonical
`SKILL.md` files. Large procedures keep the decision path in `SKILL.md` and
move infrequently needed detail into `references/`.

The initial migration splits:

- `audio/SKILL.md`
- `megacut/SKILL.md`
- `plates/SKILL.md`
- `production/SKILL.md`

Other skills remain in place unless the audit shows a focused split improves
navigation. All inbound links are updated in the same change.

## Router and generated catalog

`docs/SKILL.md` remains a hand-curated task-to-skill router. It is optimized
for a human or agent asking, "What do I load for this task?"

A generated catalog is added beside it:

- `docs/skills/index.schema.json`
- `docs/skills/index.json`
- `docs/skills/index.md`

The generated catalog contains every skill's metadata and is never hand
edited. The router links to it but does not duplicate the whole catalog.

## Validation tooling

The repository gains local versions of common's documentation checks:

- `scripts/check-skill-frontmatter.sh`
- `scripts/check-skill-index.sh`
- `scripts/check-doc-links.sh`
- `scripts/generate_skill_index.py`

The scripts are adapted to destiny-vids paths and category values. They check:

- required and valid front matter;
- description and canonical-file size budgets;
- every skill is linked from `docs/SKILL.md`;
- all internal Markdown links resolve;
- generated catalog freshness and schema validity;
- `entry_point` matches the canonical file path.

A local `.pre-commit-config.yaml` runs these process checks and the existing
derived-artifact checks. CI runs the same documentation checks as part of the
existing aggregate test job; it does not add a separate workflow or a
skill-drift gate.

The documented pre-commit command is added to the commit checklist. Existing
offline build checks remain unchanged and continue to be required.

## Current-state corrections

The migration removes or corrects guidance that contradicts the new model:

- "plain Markdown with no front matter";
- "there is no generated index";
- any implication that a referenced open issue is automatically current work;
- missing trigger, red-flag, and verification sections found by the audit.

Live gaps remain in manifests or GitHub issues according to the existing
repository policy. Skills describe procedures, not current backlog state.

## Implementation sequence

1. Add catalog schema, generator, and validation scripts.
2. Add front matter and required structural sections to all skills.
3. Split oversized skills and repair inbound links.
4. Update `docs/SKILL.md` and generate both catalog outputs.
5. Update `AGENTS.md` with authority, self-repair, and issue-applicability
   rules.
6. Add pre-commit and CI integration.
7. Run the complete repository verification suite.

Each step is reviewable, but the migration lands as one logical change so the
contract, catalog, and validators cannot disagree in an intermediate commit.

## Verification

The completed implementation must pass:

```bash
python3 -m pytest -q
python3 tools/corpus.py --check
python3 tools/rederive.py --check
python3 scripts/generate_schema_enums.py --check
python3 scripts/generate_skill_index.py --check
bash scripts/check-skill-frontmatter.sh
bash scripts/check-skill-index.sh
bash scripts/check-doc-links.sh
pre-commit run --all-files
```

The audit also verifies:

- every `docs/skills/*.md` and `docs/skills/*/SKILL.md` is cataloged;
- no canonical skill exceeds 500 lines;
- no duplicate agent contract was introduced;
- local editorial and delivery rules remain unchanged;
- no unrelated dirty worktree changes are included in the commit.

## Success criteria

- A new agent can follow the local read order and load the correct skill
  without relying on prose search.
- Skill metadata is machine-readable and generated outputs cannot drift
  silently.
- Durable discoveries update the closest authoritative skill in the same
  logical change.
- Old issue references cannot revive settled casting or editorial decisions
  without a git-history and current-record applicability check.
- The repository is structurally compatible with common while remaining
  locally authoritative.
