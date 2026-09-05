# Audio runbook mechanics report

## 2026-08-26

- Removed the explicit audio map from the stage-1 spectrum image command so
  image2 receives only the `showspectrumpic` video output.
- Added a stable stage-1 `record-prefix`; every returned bed artifact is PUT
  with that prefix. Stage 2 now fetches the prefixed bed and gate through the
  port-8877 source server under `.work-example-hero01/`.
- Added a unique stage-2 `candidate-id`. It prefixes the candidate delivery,
  input-gate copy, logs, gate, workflow status, and SHA-256 record, preserving
  failed and prior candidate evidence.
- Restored `fsGroup: 100` to each PVC-mounting template, including both
  `onExit` upload templates.

## Validation

- Parsed both embedded Workflow manifests, checked their shell snippets, and
  verified their `work` mounts, source URLs, and artifact identifiers.
- `argo lint --offline --no-color` passed for both extracted manifests.
- `python3 scripts/check-doc-links.py` — 45 Markdown files checked.
- `python3 -m pytest -q tests/test_skill_contract.py tests/test_skill_catalog.py
  tests/test_farm.py tests/test_farm_policy.py` — 67 passed.
- `pre-commit run --all-files` — passed all 14 hooks.
- No media command was run.
