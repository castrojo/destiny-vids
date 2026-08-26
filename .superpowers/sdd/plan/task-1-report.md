# Task 1 report — GitHub identity foundation

**Status:** DONE_WITH_CONCERNS

## Commits

- `330bdc6` — `feat(identity): establish GitHub login model`.

## Tests and results

- `python3 -m pytest -q tests/test_identity.py tests/test_derive.py tests/test_rederive.py tests/test_dialogue.py tests/test_dialogue_md.py tests/test_act2_casting.py tests/test_casting_pending.py tests/test_index_integrity.py tests/test_plate.py tests/test_credits.py tests/test_ensemble.py tests/test_search.py tests/test_brief.py tests/test_nimbatus_redaction.py` — **2015 passed, 4 skipped**.
- `python3 tools/corpus.py --check` — passed.
- `python3 tools/rederive.py --check` — **1321** segments current.
- `python3 scripts/generate_schema_enums.py --check` — **28** enums current.
- `python3 scripts/generate_skill_index.py --check` — **9** skills current.
- `pre-commit run --all-files` — passed.
- `python3 tools/identity.py` — reports remaining legacy speakers and exits 0; `python3 tools/identity.py --act II --check` exits 1 as designed because Act II's raw owner prompt remains unmigrated.

## Self-review

- Added a login-keyed `people` model with verified numeric GitHub IDs, a casting schema, identity API, and offline audit.
- Moved bound-character and ensemble plate resolution to shared people records; regenerated all affected derived segment metadata.
- Removed identity aliases from normal chapter and dialogue resolution while retaining literal release-train chapter behavior with explicit legacy findings.
- Kept `chapters/II-endless-forms.md` untouched.

## Concerns

- The intentionally preserved raw Act II prompt contains legacy speakers and portrait overrides, so its selected identity audit correctly fails until Task 2 normalizes it.
- The unrestricted suite still has pre-existing Act II manifest assertions that assume the raw prompt is already integrated; those assertions conflict with the required preservation of commit `dae60dd` and were not normalized in this task.
