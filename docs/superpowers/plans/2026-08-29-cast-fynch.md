# Fynch Casting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record Fynch as Ihor Dvoretskyi, verified through GitHub login `idvoretskyi`.

**Architecture:** `vocab/casting.yaml` remains the single casting authority. Add the verified person record and one lead binding, then update the README cast table and regenerate derived records/schema enums through existing tools.

**Tech Stack:** YAML, Python repository generators, pytest.

## Global Constraints

- GitHub account ID `118459`, login `idvoretskyi`, public name `Ihor Dvoretskyi`.
- Add no plate copy: none was authored.
- Do not hand-edit generated schema enums or derived segment fields.

---

### Task 1: Record the Fynch binding

**Files:**
- Modify: `vocab/casting.yaml`
- Modify: `README.md`
- Modify generated outputs only through repository commands.
- Test: `tests/test_derive.py`
- Test: `tests/test_search.py`

**Interfaces:**
- Consumes: `tools.derive.load_leads()`.
- Produces: canonical `fynch` lead binding to `idvoretskyi`.

- [ ] Add `idvoretskyi` under `people` with `github_id: 118459`.
- [ ] Add `fynch` under `leads.values` with `person: idvoretskyi` and no plate.
- [ ] Add Fynch to the README cast table.
- [ ] Run `python3 tools/rederive.py` and `python3 scripts/generate_schema_enums.py --write`.
- [ ] Run `python3 -m pytest -q tests/test_derive.py tests/test_search.py tests/test_index_integrity.py`.
- [ ] Commit and push the binding.
