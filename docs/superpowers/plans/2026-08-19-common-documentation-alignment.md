# Common Documentation Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `destiny-vids` structurally compatible with `projectbluefin/common`'s agent-contract and skill-catalog model while preserving all local editorial, delivery, and GitHub workflow authority.

**Architecture:** `AGENTS.md` remains the local authority, `docs/SKILL.md` remains the curated task router, and machine-readable metadata is generated from YAML front matter on each canonical skill. Small validation tools enforce front matter, router coverage, links, size budgets, and catalog freshness; pre-commit and the existing CI job run those tools without creating a separate process-only workflow.

**Tech Stack:** Markdown, YAML front matter, Python 3.13, PyYAML, jsonschema Draft 2020-12, pytest, Bash, pre-commit.

## Global Constraints

- `destiny-vids` remains authoritative for editorial policy, casting, rights, rendering, delivery, issues, protected `main`, and its merge queue.
- `projectbluefin/common` is a compatible shared sidecar and never overrides local rules.
- Do not import Hive assignment, factory labels, OCI promotion, testing branches, or common's doc-only direct-push exception.
- Do not create `.github/agents/`, `CLAUDE.md`, `GEMINI.md`, or a second Copilot instruction contract.
- Preserve existing domain procedures and authored-copy rules; this migration changes structure and discoverability, not film policy.
- Canonical skills have a 200-line soft limit and 500-line hard limit.
- Skill categories are exactly `editorial`, `media-production`, `metadata`, `operations`, and `meta`.
- Generated `docs/skills/index.json` and `docs/skills/index.md` are tool-owned and never hand edited.
- An issue reference is historical evidence until git history and current authoritative records establish that it still applies.
- Do not stage or commit the pre-existing trailer and delivery changes in the working tree.
- Every implementation commit includes `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>`.

---

## File Structure

### New catalog and validation files

- `docs/skills/index.schema.json` — local JSON Schema for the generated catalog.
- `docs/skills/index.json` — generated machine-readable catalog.
- `docs/skills/index.md` — generated human-readable catalog mirror.
- `scripts/generate_skill_index.py` — parse skill front matter, validate it, and generate both catalog outputs.
- `scripts/check-skill-frontmatter.sh` — enforce required metadata, descriptions, and line budgets.
- `scripts/check-skill-index.sh` — prove every canonical skill appears in the curated router.
- `scripts/check-doc-links.sh` — CLI wrapper for the same relative-link scope as `tests/test_doc_links.py`.
- `.pre-commit-config.yaml` — aggregate local process and derived-artifact checks.
- `tests/test_skill_catalog.py` — unit tests for catalog parsing, validation, stable generation dates, and Markdown rendering.
- `tests/test_skill_contract.py` — repository-level checks for front matter, router coverage, agent authority, and prohibited duplicate contracts.

### Existing contract and router files

- `AGENTS.md` — local/common authority, two-output rule, every-loop repair, and issue-applicability rule.
- `docs/SKILL.md` — curated router plus link to generated catalog and skill-authoring rules.
- `.github/workflows/ci.yml` — install `pre-commit` and run the aggregate local hooks inside the existing test job.

### Canonical skills receiving front matter

- `docs/skills/corpus.md`
- `docs/skills/farm.md`
- `docs/skills/indexing.md`
- `docs/skills/intake.md`
- `docs/skills/review.md`
- `docs/skills/audio/SKILL.md`
- `docs/skills/casting/SKILL.md`
- `docs/skills/editing/SKILL.md`
- `docs/skills/issues/SKILL.md`
- `docs/skills/megacut/SKILL.md`
- `docs/skills/plates/SKILL.md`
- `docs/skills/production/SKILL.md`
- `docs/skills/scoring/SKILL.md`

### New progressive-disclosure references

- `docs/skills/audio/references/source-quality.md`
- `docs/skills/audio/references/delivery-gates.md`
- `docs/skills/megacut/references/delivery.md`
- `docs/skills/megacut/references/verification.md`
- `docs/skills/plates/references/binding-conflicts.md`
- `docs/skills/production/references/freshness.md`

---

### Task 1: Build the Skill Catalog Core

**Files:**
- Create: `docs/skills/index.schema.json`
- Create: `scripts/generate_skill_index.py`
- Create: `tests/test_skill_catalog.py`

**Interfaces:**
- Produces: `find_skill_files(skills_dir: Path) -> list[Path]`
- Produces: `parse_front_matter(path: Path) -> dict[str, object]`
- Produces: `build_skill_entry(path: Path, repo_root: Path) -> dict[str, object]`
- Produces: `build_catalog(repo_root: Path, generated_at: date | None = None) -> dict[str, object]`
- Produces: `pin_unchanged_generated_at(catalog: dict, existing: dict | None) -> None`
- Produces: `validate_catalog(catalog: dict, schema_path: Path) -> None`
- Produces: `render_markdown(catalog: dict) -> str`
- Consumes later: all canonical skill front matter and `docs/skills/index.schema.json`.

- [ ] **Step 1: Write fixture-based parser and schema tests**

Add tests that do not depend on the still-unmigrated real skills:

```python
from datetime import date
from pathlib import Path

import pytest

from scripts import generate_skill_index as catalog


MINIMAL = """\
---
name: demo-skill
version: "1.0"
last_updated: "2026-08-19"
id: demo-skill
one_line_purpose: Demonstrate catalog generation.
entry_point: docs/skills/demo-skill.md
category: meta
status: active
dependencies: []
tags: [demo]
description: >-
  Demonstrates catalog generation. Use when testing skill metadata.
metadata:
  type: procedure
---

# Demo
"""


def test_build_skill_entry_reads_required_metadata(tmp_path: Path):
    path = tmp_path / "docs/skills/demo-skill.md"
    path.parent.mkdir(parents=True)
    path.write_text(MINIMAL)

    entry = catalog.build_skill_entry(path, tmp_path)

    assert entry["id"] == "demo-skill"
    assert entry["category"] == "meta"
    assert entry["entry_point"] == "docs/skills/demo-skill.md"
    assert entry["doc_type"] == "procedure"


def test_entry_point_must_match_actual_path(tmp_path: Path):
    path = tmp_path / "docs/skills/demo-skill.md"
    path.parent.mkdir(parents=True)
    path.write_text(MINIMAL.replace(
        "docs/skills/demo-skill.md", "docs/skills/wrong.md"))

    with pytest.raises(ValueError, match="does not match actual path"):
        catalog.build_skill_entry(path, tmp_path)


def test_unchanged_catalog_keeps_previous_generated_date():
    current = {
        "generated_at": "2026-08-19",
        "schema_version": "1.0",
        "skills": [{"id": "demo"}],
    }
    rebuilt = {
        "generated_at": "2026-08-20",
        "schema_version": "1.0",
        "skills": [{"id": "demo"}],
    }

    catalog.pin_unchanged_generated_at(rebuilt, current)

    assert rebuilt["generated_at"] == "2026-08-19"


def test_markdown_catalog_links_to_entry_point():
    rendered = catalog.render_markdown({
        "generated_at": "2026-08-19",
        "schema_version": "1.0",
        "skills": [{
            "id": "demo-skill",
            "entry_point": "docs/skills/demo-skill.md",
            "category": "meta",
            "status": "active",
            "one_line_purpose": "Demonstrate catalog generation.",
        }],
    })

    assert "[demo-skill](demo-skill.md)" in rendered
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```bash
python3 -m pytest -q tests/test_skill_catalog.py
```

Expected: collection fails because `scripts.generate_skill_index` does not
exist.

- [ ] **Step 3: Add the local catalog schema**

Port common's `docs/skills/index.schema.json`, changing:

```json
{
  "$id": "https://github.com/castrojo/destiny-vids/docs/skills/index.schema.json",
  "title": "destiny-vids skill catalog"
}
```

Set `category.enum` exactly to:

```json
["editorial", "media-production", "metadata", "operations", "meta"]
```

Keep the common fields and limits: kebab-case `id`, 120-character
`one_line_purpose`, 256-character `description`, active/deprecated/reserved
status, and date-shaped `last_updated`.

- [ ] **Step 4: Implement the catalog generator**

Port common's generator but parameterize the repository root for unit tests:

```python
def find_skill_files(skills_dir: Path) -> list[Path]:
    files = sorted(p for p in skills_dir.glob("*.md")
                   if p.name not in {"index.md"})
    files += sorted(skills_dir.glob("*/SKILL.md"))
    return files


def build_skill_entry(path: Path, repo_root: Path) -> dict[str, object]:
    fm = parse_front_matter(path)
    rel = path.relative_to(repo_root).as_posix()
    required = (
        "id", "name", "one_line_purpose", "entry_point", "category",
        "status", "tags", "description", "version", "last_updated",
    )
    missing = [key for key in required if key not in fm]
    if missing:
        raise ValueError(f"{rel}: missing required front-matter key(s): {missing}")
    if fm["id"] != fm["name"]:
        raise ValueError(f"{rel}: id and name must match")
    if fm["entry_point"] != rel:
        raise ValueError(
            f"{rel}: entry_point front-matter value "
            f"({fm['entry_point']!r}) does not match actual path ({rel!r})")
    entry = {
        "id": fm["id"],
        "name": fm["name"],
        "one_line_purpose": fm["one_line_purpose"],
        "entry_point": fm["entry_point"],
        "category": fm["category"],
        "status": fm["status"],
        "tags": fm["tags"],
        "description": " ".join(str(fm["description"]).split()),
        "version": str(fm["version"]),
        "last_updated": str(fm["last_updated"]),
    }
    doc_type = (fm.get("metadata") or {}).get("type")
    if doc_type:
        entry["doc_type"] = doc_type
    return entry
```

The CLI supports only `--write` and `--check`; both validate against the local
schema. `--write` emits both generated files. `--check` prints the exact
regeneration command and exits 1 on drift.

- [ ] **Step 5: Run focused tests**

Run:

```bash
python3 -m pytest -q tests/test_skill_catalog.py
```

Expected: all catalog unit tests pass.

- [ ] **Step 6: Commit the catalog core**

```bash
git add docs/skills/index.schema.json scripts/generate_skill_index.py \
  tests/test_skill_catalog.py
git diff --cached --name-only
git commit -m "feat(docs): add skill catalog generator" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 2: Add Skill Contract Validators

**Files:**
- Create: `scripts/check-skill-frontmatter.sh`
- Create: `scripts/check-skill-index.sh`
- Create: `scripts/check-doc-links.sh`
- Create: `tests/test_skill_contract.py`

**Interfaces:**
- Consumes: canonical files returned by `find_skill_files`.
- Produces: shell commands that return 0 only when metadata, router coverage,
  links, and line budgets are valid.
- Produces: reusable test helpers `_canonical_skills() -> list[Path]` and
  `_front_matter(path: Path) -> dict[str, object]`.

- [ ] **Step 1: Write repository-contract tests**

Create tests that intentionally fail before the skill migration:

```python
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS = REPO_ROOT / "docs/skills"


def _canonical_skills():
    return (
        sorted(p for p in SKILLS.glob("*.md") if p.name != "index.md")
        + sorted(SKILLS.glob("*/SKILL.md"))
    )


def _front_matter(path):
    text = path.read_text()
    assert text.startswith("---\n"), f"{path} has no YAML front matter"
    raw = text.split("---\n", 2)[1]
    return yaml.safe_load(raw)


def test_every_skill_has_common_compatible_front_matter():
    required = {
        "name", "version", "last_updated", "id", "one_line_purpose",
        "entry_point", "category", "status", "dependencies", "tags",
        "description", "metadata",
    }
    for path in _canonical_skills():
        fm = _front_matter(path)
        assert required <= fm.keys(), f"{path}: {required - fm.keys()}"
        assert fm["metadata"]["type"] in {
            "procedure", "reference", "runbook", "policy"}


def test_no_canonical_skill_exceeds_hard_limit():
    oversized = {
        str(path.relative_to(REPO_ROOT)): len(path.read_text().splitlines())
        for path in _canonical_skills()
        if len(path.read_text().splitlines()) > 500
    }
    assert not oversized


def test_agent_contract_is_not_duplicated():
    forbidden = [
        REPO_ROOT / "CLAUDE.md",
        REPO_ROOT / "GEMINI.md",
        REPO_ROOT / ".github/copilot-instructions.md",
    ]
    assert not [str(path.relative_to(REPO_ROOT))
                for path in forbidden if path.exists()]
    assert not list((REPO_ROOT / ".github/agents").glob("**/*"))
```

- [ ] **Step 2: Run the tests and verify the front-matter test fails**

Run:

```bash
python3 -m pytest -q tests/test_skill_contract.py
```

Expected: failure naming the first skill without YAML front matter.

- [ ] **Step 3: Port and adapt the front-matter validator**

Use common's required keys and limits. Add checks not present in common's shell
script:

```bash
for key in name version last_updated id one_line_purpose entry_point \
           category status dependencies tags description; do
    # print "error: $f missing required key '$key'" and set rc=1
done
```

Validate:

- `name` and `id` equal the file stem or parent directory;
- category is one of the five local values;
- `metadata.type` exists;
- description is at most 256 characters;
- one-line purpose is at most 120 characters;
- canonical files over 200 lines warn;
- canonical files over 500 lines fail.

- [ ] **Step 4: Port and adapt the router coverage validator**

Skip generated `index.md` and `index.json`. Require:

```bash
docs/skills/foo.md       -> ](skills/foo.md)
docs/skills/foo/SKILL.md -> ](skills/foo/SKILL.md)
```

Print every missing route and exit 1 if any skill is absent.

- [ ] **Step 5: Add the link-check CLI**

Reuse the scope already tested by `tests/test_doc_links.py`: `docs/**/*.md`,
`README.md`, and `AGENTS.md`. The script must:

```python
if target.startswith(("http://", "https://", "mailto:", "#")):
    continue
target = target.split("#", 1)[0]
if target and not (source.parent / target).resolve().exists():
    print(f"error: broken link in {source.relative_to(REPO_ROOT)} -> {target}")
```

Name the file `scripts/check-doc-links.sh` to match the approved spec, but use
a Python shebang because the existing link parser is Python.

- [ ] **Step 6: Run validator unit coverage**

Run:

```bash
python3 -m pytest -q tests/test_skill_catalog.py tests/test_skill_contract.py
```

Expected: only the real-repository front-matter test remains red; the validator
scripts themselves import/parse successfully.

- [ ] **Step 7: Commit validators**

```bash
git add scripts/check-skill-frontmatter.sh scripts/check-skill-index.sh \
  scripts/check-doc-links.sh tests/test_skill_contract.py
git diff --cached --name-only
git commit -m "test(docs): add skill contract validators" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 3: Migrate the Flat Skills

**Files:**
- Modify: `docs/skills/corpus.md`
- Modify: `docs/skills/farm.md`
- Modify: `docs/skills/indexing.md`
- Modify: `docs/skills/intake.md`
- Modify: `docs/skills/review.md`

**Interfaces:**
- Consumes: front-matter schema and validator from Tasks 1-2.
- Produces: five catalogable skill entries with complete trigger and
  verification sections.

- [ ] **Step 1: Add exact front matter to each flat skill**

Use this metadata matrix:

| file | id | category | type | one-line purpose |
|---|---|---|---|---|
| `corpus.md` | `corpus` | `metadata` | `procedure` | Inspect and regenerate per-character footage coverage. |
| `farm.md` | `farm` | `operations` | `runbook` | Run frame-touching encodes on the remote Kubernetes farm. |
| `indexing.md` | `indexing` | `metadata` | `procedure` | Turn source footage into validated shot-level records. |
| `intake.md` | `intake` | `editorial` | `procedure` | Convert owner dictation into durable executable issue briefs. |
| `review.md` | `review` | `editorial` | `procedure` | Map programme notes to the owning act and rebuild only that act. |

For every file use:

```yaml
version: "1.0"
last_updated: "2026-08-19"
status: active
dependencies: []
metadata:
  type: <matrix value>
```

Use 3-6 specific tags and a description with two sentences: capability first,
then `Use when ...` triggers. Keep each description under 256 characters.

- [ ] **Step 2: Normalize missing body sections**

Make only structural edits:

- `intake.md`: rename `## Why this skill exists` to `## When to Use` and add a
  short `## When NOT to Use` that routes normal issue work to
  `issues/SKILL.md`.
- `review.md`: add `## When to Use`, `## When NOT to Use`, rename
  `## The three-second version` to `## Core Process`, add a concise
  `## Red Flags`, and rename the final measurement section to
  `## Verification`.
- Preserve every command, timing rule, and editorial boundary.

- [ ] **Step 3: Run focused structure and link checks**

Run:

```bash
bash scripts/check-skill-frontmatter.sh
python3 scripts/check-doc-links.sh
python3 -m pytest -q tests/test_doc_links.py tests/test_skill_contract.py
```

Expected: front-matter failures now name only the eight unmigrated directory
skills; all links pass.

- [ ] **Step 4: Commit the flat-skill migration**

```bash
git add docs/skills/corpus.md docs/skills/farm.md docs/skills/indexing.md \
  docs/skills/intake.md docs/skills/review.md
git diff --cached --name-only
git commit -m "docs(skills): catalog flat production skills" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 4: Migrate the Focused Directory Skills

**Files:**
- Modify: `docs/skills/casting/SKILL.md`
- Modify: `docs/skills/editing/SKILL.md`
- Modify: `docs/skills/issues/SKILL.md`
- Modify: `docs/skills/scoring/SKILL.md`

**Interfaces:**
- Consumes: catalog metadata contract.
- Produces: four catalogable focused skills that remain below 200 lines.

- [ ] **Step 1: Add exact metadata**

Use:

| path | id | category | type | one-line purpose |
|---|---|---|---|---|
| `casting/SKILL.md` | `casting` | `metadata` | `policy` | Bind visible Destiny characters to verified contributor identities. |
| `editing/SKILL.md` | `editing` | `editorial` | `procedure` | Build and revise cuts from indexed footage without inventing shots. |
| `issues/SKILL.md` | `issues` | `operations` | `procedure` | Turn approved work into executable briefs and repository issues. |
| `scoring/SKILL.md` | `scoring` | `media-production` | `procedure` | Fit picture to measured music structure without changing the mix. |

Set each `entry_point` to its exact `docs/skills/<name>/SKILL.md` path.

- [ ] **Step 2: Normalize headings without rewriting policy**

- `issues/SKILL.md`: rename `## The shape of the backlog` to
  `## Core Process`; keep the remaining procedure beneath it.
- Confirm all four have `When to Use`, `When NOT to Use`, `Red Flags`, and
  `Verification`.
- Add `Common Rationalizations` only where the file already contains those
  failure patterns; do not pad a skill with generic prose.

- [ ] **Step 3: Run focused validation**

```bash
bash scripts/check-skill-frontmatter.sh
python3 scripts/check-doc-links.sh
python3 -m pytest -q tests/test_doc_links.py tests/test_skill_contract.py
```

Expected: metadata failures now name only `audio`, `megacut`, `plates`, and
`production`.

- [ ] **Step 4: Commit**

```bash
git add docs/skills/casting/SKILL.md docs/skills/editing/SKILL.md \
  docs/skills/issues/SKILL.md docs/skills/scoring/SKILL.md
git diff --cached --name-only
git commit -m "docs(skills): catalog editorial workflow skills" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 5: Split and Migrate the Oversized Skills

**Files:**
- Modify: `docs/skills/audio/SKILL.md`
- Create: `docs/skills/audio/references/source-quality.md`
- Create: `docs/skills/audio/references/delivery-gates.md`
- Modify: `docs/skills/megacut/SKILL.md`
- Create: `docs/skills/megacut/references/delivery.md`
- Create: `docs/skills/megacut/references/verification.md`
- Modify: `docs/skills/plates/SKILL.md`
- Create: `docs/skills/plates/references/binding-conflicts.md`
- Modify: `docs/skills/production/SKILL.md`
- Create: `docs/skills/production/references/freshness.md`
- Modify: inbound links found by `rg 'audio/SKILL|megacut/SKILL|plates/SKILL|production/SKILL'`

**Interfaces:**
- Consumes: common-compatible metadata and the 200-line soft limit.
- Produces: four concise canonical skills with detailed references and no lost
  commands or policy.

- [ ] **Step 1: Add metadata before moving content**

Use:

| id | category | type | one-line purpose |
|---|---|---|---|
| `audio` | `media-production` | `policy` | Preserve source fidelity and enforce delivery audio headroom. |
| `megacut` | `media-production` | `procedure` | Assemble finished acts into the canonical programme without re-editing them. |
| `plates` | `media-production` | `policy` | Render authored identity and dialogue cards without inventing copy. |
| `production` | `operations` | `procedure` | Take approved video work from issue brief to delivered artifact. |

For `audio`, record:

```yaml
metadata:
  type: policy
  context7-sources:
    - /websites/ffmpeg_documentation
```

Do not add Context7 IDs to the other skills unless their existing prose already
names a verified external source.

- [ ] **Step 2: Split `audio` by decision frequency**

Keep in `audio/SKILL.md`:

- purpose and authority;
- `When to Use` / `When NOT to Use`;
- the three non-negotiable rules;
- the shortest command path;
- red flags;
- a reference table;
- verification checklist.

Move source-rung selection, native-rate details, and relative-lossless caveat
to `references/source-quality.md`.

Move true-peak behavior, AAC overshoot, `audio-check.sh`, peak trimming, and
lossless-master build examples to `references/delivery-gates.md`.

Delete the per-act snapshot:

> The two acts with a known gap are act I ... and act VI ...

Replace it with machine-derived commands and links to `delivery.json`; live act
state does not belong in a skill.

- [ ] **Step 3: Split `megacut`**

Keep assembly boundaries, core process, reference table, concise red flags,
and verification checklist in `SKILL.md`.

Move `## Delivering a programme` verbatim to
`references/delivery.md`.

Move the detailed manual probes under `## Verify, don't assert` to
`references/verification.md`; retain a short checklist and link in `SKILL.md`.

Fix the malformed heading:

```markdown
## Assembly is not editing

This stage **joins finished things**.
```

- [ ] **Step 4: Split `plates`**

Move `## When a card must diverge from its binding` and its contract-violation
procedure to `references/binding-conflicts.md`.

Keep the closed field set, placeholder policy, core render process, red flags,
and verification in `SKILL.md`. Link existing reference files instead of
restating their details.

- [ ] **Step 5: Split `production`**

Move `## Keeping the delivery fresh` and
`## A refresh is every rung, or it is not a refresh` into
`references/freshness.md`.

Keep rule zero, issue-to-video loop, human stop points, compact reference
table, red flags, and verification in `SKILL.md`.

Do not weaken “a video now means a video now”; the split changes only where
detail is read.

- [ ] **Step 6: Run size and link validation**

```bash
bash scripts/check-skill-frontmatter.sh
python3 scripts/check-doc-links.sh
python3 -m pytest -q tests/test_doc_links.py tests/test_cited_paths.py \
  tests/test_skill_contract.py
```

Expected:

- no missing front matter;
- no canonical skill over 500 lines;
- each of the four canonical skills is at or near the 200-line soft target;
- every moved link resolves.

- [ ] **Step 7: Commit**

```bash
git add docs/skills/audio docs/skills/megacut docs/skills/plates \
  docs/skills/production
git diff --cached --name-only
git commit -m "docs(skills): split oversized production guides" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 6: Realign the Router and Agent Contract

**Files:**
- Modify: `docs/SKILL.md`
- Modify: `AGENTS.md`
- Modify: `tests/test_skill_contract.py`
- Create generated: `docs/skills/index.json`
- Create generated: `docs/skills/index.md`

**Interfaces:**
- Consumes: all 13 migrated skill metadata records.
- Produces: curated task routing, generated catalog, local/common authority
  rule, self-repair loop, and issue-applicability contract.

- [ ] **Step 1: Add failing authority tests**

Append:

```python
def test_agents_contract_declares_local_authority_and_common_sidecar():
    text = (REPO_ROOT / "AGENTS.md").read_text()
    assert "local authority" in text
    assert "projectbluefin/common" in text
    assert "never overrides" in text


def test_agents_contract_requires_issue_applicability_check():
    text = (REPO_ROOT / "AGENTS.md").read_text()
    assert "issue references are historical evidence" in text
    assert "git history" in text
    assert "still applies" in text


def test_router_links_generated_catalog():
    text = (REPO_ROOT / "docs/SKILL.md").read_text()
    assert "skills/index.json" in text
    assert "skills/index.md" in text
```

- [ ] **Step 2: Run tests and verify they fail**

```bash
python3 -m pytest -q tests/test_skill_contract.py
```

Expected: the three new assertions fail against the old contract/router.

- [ ] **Step 3: Update `docs/SKILL.md`**

Preserve the task router table. Replace:

> This table is the catalog. There is no generated index behind it.

with:

```markdown
This table is the curated task router. The complete generated catalog lives in
[`skills/index.json`](skills/index.json), with a human-readable mirror in
[`skills/index.md`](skills/index.md). Both are generated from skill front
matter by `scripts/generate_skill_index.py`; never hand-edit them.
```

Add a short “Writing skills” section linking to local skill metadata rules in
`AGENTS.md` and common's `write-a-skill.md` as the compatibility reference.

- [ ] **Step 4: Update `AGENTS.md`**

Make these exact policy points explicit:

```markdown
## Local authority and common compatibility

This repository's `AGENTS.md`, records, schemas, and routed skills are the
local authority. `projectbluefin/common` is a shared agent-contract sidecar for
compatible documentation and self-repair practices; it never overrides local
editorial, delivery, rights, GitHub, or merge policy.
```

Add:

```markdown
## Self-repair and durable learning

Every implementation produces two outputs: the work and any durable learning
it exposed. Verify the repository and loaded skills, detect contradictory or
stale guidance, repair the nearest authoritative contract when source-backed,
validate the repair, and update the matching skill in the same logical change.
```

Add:

```markdown
## Issue applicability

Issue references are historical evidence, not proof of current work. Before
reporting or acting on an issue, check current authoritative records and git
history to establish that the issue still applies. A stale `unresolved` line
must not revive a settled casting or editorial decision.
```

Replace the no-front-matter/no-catalog paragraph with the generated-catalog
model. Preserve all video, copy, rights, delivery, and merge rules byte-for-byte
outside the edited documentation sections.

- [ ] **Step 5: Generate the catalog**

```bash
python3 scripts/generate_skill_index.py --write
```

Expected:

```text
wrote docs/skills/index.json and index.md (13 skills)
```

- [ ] **Step 6: Run contract checks**

```bash
python3 scripts/generate_skill_index.py --check
bash scripts/check-skill-frontmatter.sh
bash scripts/check-skill-index.sh
python3 scripts/check-doc-links.sh
python3 -m pytest -q tests/test_skill_catalog.py tests/test_skill_contract.py \
  tests/test_doc_links.py tests/test_cited_paths.py
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add AGENTS.md docs/SKILL.md docs/skills/index.json docs/skills/index.md \
  tests/test_skill_contract.py
git diff --cached --name-only
git commit -m "docs: align agent contract with common" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 7: Wire Pre-commit and CI

**Files:**
- Create: `.pre-commit-config.yaml`
- Modify: `.github/workflows/ci.yml`
- Modify: `AGENTS.md`

**Interfaces:**
- Consumes: all validators and existing offline checks.
- Produces: one developer-time aggregate and one existing CI job covering the
  same documentation contract.

- [ ] **Step 1: Add local pre-commit hooks**

Use only pinned upstream hooks and local system hooks. Include:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: 2c9f875913ee60ca25ce70243dc24d5b6415598c
    hooks:
      - id: check-json
      - id: check-yaml
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: check-merge-conflict
      - id: detect-private-key
      - id: check-added-large-files
  - repo: local
    hooks:
      - id: check-skill-frontmatter
        name: Validate skill front matter
        language: system
        entry: bash scripts/check-skill-frontmatter.sh
        pass_filenames: false
        always_run: true
      - id: check-skill-index
        name: Validate docs/SKILL.md coverage
        language: system
        entry: bash scripts/check-skill-index.sh
        pass_filenames: false
        always_run: true
      - id: check-doc-links
        name: Validate internal Markdown links
        language: system
        entry: python3 scripts/check-doc-links.sh
        pass_filenames: false
        always_run: true
      - id: check-skill-catalog
        name: Validate generated skill catalog
        language: system
        entry: python3 scripts/generate_skill_index.py --check
        pass_filenames: false
        always_run: true
      - id: check-corpus
        name: Validate generated character corpora
        language: system
        entry: python3 tools/corpus.py --check
        pass_filenames: false
        always_run: true
      - id: check-derived-fields
        name: Validate derived metadata
        language: system
        entry: python3 tools/rederive.py --check
        pass_filenames: false
        always_run: true
      - id: check-schema-enums
        name: Validate generated schema enums
        language: system
        entry: python3 scripts/generate_schema_enums.py --check
        pass_filenames: false
        always_run: true
```

- [ ] **Step 2: Update the documented commit gate**

In `AGENTS.md`, make the required pre-commit sequence:

```bash
python3 -m pytest -q
python3 tools/corpus.py --check
python3 tools/rederive.py --check
python3 scripts/generate_schema_enums.py --check
pre-commit run --all-files
```

State that catalog outputs are regenerated with:

```bash
python3 scripts/generate_skill_index.py --write
```

- [ ] **Step 3: Integrate into the existing CI job**

Change dependency installation to:

```yaml
run: pip install --quiet jsonschema pyyaml pytest pillow pre-commit
```

After the existing source-freshness gate, add one aggregate step:

```yaml
- name: Documentation and process checks
  run: pre-commit run --all-files
```

Do not create a new job or workflow. Do not remove the existing explicit test
and delivery checks; duplicated process checks are acceptable for the first
migration only if pre-commit output remains the aggregate compatibility gate.

- [ ] **Step 4: Run pre-commit and fix only alignment findings**

```bash
pre-commit run --all-files
```

Expected: all hooks pass. If whitespace/end-of-file hooks modify unrelated
pre-existing files, do not stage those files; narrow hook `files:` patterns so
the alignment change does not absorb unrelated worktree changes.

- [ ] **Step 5: Run the complete repository verification suite**

```bash
python3 -m pytest -q
python3 tools/corpus.py --check
python3 tools/rederive.py --check
python3 scripts/generate_schema_enums.py --check
python3 scripts/generate_skill_index.py --check
bash scripts/check-skill-frontmatter.sh
bash scripts/check-skill-index.sh
python3 scripts/check-doc-links.sh
pre-commit run --all-files
```

Expected: every command exits 0.

- [ ] **Step 6: Audit the final diff**

```bash
git status --short
git diff --name-only HEAD
git diff --check
```

Expected alignment paths:

```text
.github/workflows/ci.yml
.pre-commit-config.yaml
AGENTS.md
docs/SKILL.md
docs/skills/**
scripts/check-doc-links.sh
scripts/check-skill-frontmatter.sh
scripts/check-skill-index.sh
scripts/generate_skill_index.py
tests/test_skill_catalog.py
tests/test_skill_contract.py
```

The existing modified trailer files and `.cwd-restore` remain unstaged and
outside every alignment commit.

- [ ] **Step 7: Commit CI integration**

```bash
git add .github/workflows/ci.yml .pre-commit-config.yaml AGENTS.md
git diff --cached --name-only
git commit -m "ci: enforce common-compatible skill docs" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

- [ ] **Step 8: Final branch verification**

```bash
git log --oneline --decorate -8
git status --short
git diff origin/main...HEAD --stat
```

Confirm the alignment commits are reviewable in sequence and no unrelated
working-tree change was committed.

