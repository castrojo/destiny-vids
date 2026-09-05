# Season of the Blueberries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 12 weekly KubeStellar contributor episodes and one full-season cut from a single Witch Queen source.

**Architecture:** A committed season manifest holds chapter windows, title-slide copy, fixed cast seats, and the no-repeat contributor ledger. A small Hive-series tool reuses the existing avatar, farm, conform, and thumbnail modules while adding full-frame cards and shared-source chapter rendering. GitHub Actions proposes the next contributor snapshot in a pull request; rendering remains local/farm because CI has no footage.

**Tech Stack:** Python 3.13, Pillow, FFmpeg through `tools/farm.py`, GitHub REST through `gh`, JSON, GitHub Actions, `just`.

## Global Constraints

- Store metadata and timestamps, never footage or delivered video.
- Preserve source audio; add no music.
- Use GitHub numeric IDs for the no-repeat ledger.
- Use full uncropped GitHub profile images on dossier cards.
- Generate no person-facing copy; title-slide lore is the only generated prose.
- Ship missing dossiers or unsupported character plates as omissions.
- Use remote encoding when available and the capped local fallback otherwise.

---

### Task 1: Title-slide lore supplier

**Files:**
- Modify in `projectbluefin/hive-lore`: `AGENTS.md`
- Create in `projectbluefin/hive-lore`: `lore/witch-queen.md`
- Create in `projectbluefin/hive-lore`: `mapping/kubestellar-hive.md`
- Create in `projectbluefin/hive-lore`: `vocab/season-one.yaml`
- Create in `projectbluefin/hive-lore`: `tools/titles.py`
- Create in `projectbluefin/hive-lore`: `tests/test_titles.py`

**Interfaces:**
- Consumes: chapter number and publisher chapter title.
- Produces: three deterministic subtitle candidates with provenance.

- [ ] Replace the obsolete contributor-epithet contract with title-slide-only policy.
- [ ] Add cited Destiny and KubeStellar/Hive reference notes.
- [ ] Add three reviewed subtitle candidates for each of the 12 chapters.
- [ ] Add a deterministic CLI that prints one chapter's candidates as JSON.
- [ ] Add tests for determinism, complete chapter coverage, and banned person-facing claims.
- [ ] Run `python3 -m pytest -q` and commit.

### Task 2: Season records and generated cards

**Files:**
- Create: `stories/standalone/season-of-the-blueberries.json`
- Create: `schema/hive-season.schema.json`
- Create: `tools/hive_series.py`
- Create: `tests/test_hive_series.py`
- Create generated assets under: `assets/hive/`

**Interfaces:**
- Consumes: one source file, season manifest, local avatar cache.
- Produces: CTA panels, title slides, dossier cards, fixed-cast plates, and thumbnails.

- [ ] Write failing tests for chapter bounds, source reuse, no-repeat IDs, exact CTA copy, title coverage, and unsupported-seat omission.
- [ ] Implement manifest loading and schema validation.
- [ ] Implement Pillow renderers for the three-panel opening CTA, chapter title slide, and full-PFP Guardian dossier A.
- [ ] Reuse `tools.avatars` to fetch declared GitHub logins and render missing faces as explicit unresolved entries.
- [ ] Record all 12 chapter windows and source-evidenced Angie, Shellea, and CortNick seats.
- [ ] Generate committed shared cards and run the focused tests.
- [ ] Commit.

### Task 3: Fast episode and season builds

**Files:**
- Modify: `tools/hive_series.py`
- Create: `justfile`
- Modify: `.gitignore`
- Test: `tests/test_hive_series.py`

**Interfaces:**
- Consumes: `build_episode(manifest_path, episode_number, local=False)`.
- Produces: one episode, its thumbnail, and `build_cut()` for the full season.

- [ ] Write failing tests for FFmpeg graph structure, one source download, farm-first execution, and stable output paths.
- [ ] Implement one-pass episode encoding: opening CTA panels, title slide, dossier cards, chapter picture/audio, fixed plates, closing training CTA.
- [ ] Implement full-cut concatenation from built episodes without re-encoding matching streams.
- [ ] Add `just hive-episode number` and `just hive-cut`.
- [ ] Build and verify episode 1, then build all episodes and the full cut.
- [ ] Commit.

### Task 4: Weekly contributor proposal

**Files:**
- Create: `.github/workflows/hive-weekly.yml`
- Modify: `tools/hive_series.py`
- Modify: `stories/standalone/season-of-the-blueberries.json`
- Test: `tests/test_hive_series.py`

**Interfaces:**
- Consumes: prior committed snapshot and configured KubeStellar repositories.
- Produces: the next episode's GitHub profile snapshots and updated no-repeat ledger.

- [ ] Write failing offline tests for bot exclusion, stable sorting, renamed-account IDs, fixed-cast exclusion, and empty-week degradation.
- [ ] Implement `snapshot` and `select` commands using `gh api --paginate`.
- [ ] Add a Monday schedule at a non-zero minute plus manual dispatch.
- [ ] Make the workflow create a branch and pull request only when the next episode record changes.
- [ ] Run focused tests and the complete repository validation sequence.
- [ ] Commit, push, open a PR, and enable auto-merge.

