# Final review fix report

## 2026-08-26 final fix wave

- RAFI_02 now decode-gates timed cards in memory on every CLI run. It writes
  their PNGs only with `--cards-dir`, emits `track-cards.json` with exact
  record-backed intervals and filenames, and reports the gated and written
  outputs truthfully.
- Added public CLI regression tests for omitted-card-directory gating, a failed
  decode gate, and the exact frame-addressable sidecar.
- Rewrote Lakshmi's record explanation as current placement state and reason.
- Assigned Lakshmi receiver port 8880 in the Hero farm-plumbing reference.
- Added the Hero-only authorized-audio Argo recipe and cross-references that
  override generic local-audio examples. The recipe makes no authorization
  claim and keeps all media commands in Argo.
- Regenerated the skill catalog after updating the affected skill metadata.

## Validation

- TDD red: the new RAFI_02 CLI tests failed against the old misleading output.
- `python3 -m pytest --basetemp=.pytest-tmp -q tests/test_rafi_hero_overlay.py`
  — 27 passed (three existing Pillow deprecation warnings).
- Parsed the documented authorized-audio YAML and confirmed its `main` DAG runs
  fetch, audio, and upload in order.
- `pre-commit run --all-files` — passed.
- A policy-constrained full offline run (with local media integrations
  deselected) reached 3,533 passed and 8 skipped. Nine unrelated delivery and
  read-time tests require pytest's temporary directory to be outside the
  repository; the required project-local temporary directory changes their
  intended worktree/path classification. No local media command was run.
