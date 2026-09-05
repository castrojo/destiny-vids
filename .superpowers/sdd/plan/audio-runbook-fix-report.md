# Audio runbook fix report

## 2026-08-26

- Split the Hero authorized-audio recipe into a source-only bed workflow and a
  picture-plus-verified-bed mux/validation workflow.
- Added explicit 48 kHz, high-frequency-ratio, decoded true-peak, source-hash,
  picture-hash, and original-bed-only gates.
- Made failure evidence durable through `onExit` uploads that skip absent
  artifacts while returning workflow status and hashes for existing artifacts.
- Routed Hero Core Process steps 1 and 4 to their respective workflow stages,
  and aligned the audio and farm Hero-exception notes.

## Validation

- Both embedded YAML manifests parse as `argoproj.io/v1alpha1` `Workflow`
  objects and `argo lint` reports no errors for either.
- `python3 scripts/check-doc-links.py` — 45 Markdown files checked; no broken
  links.
- `python3 -m pytest -q tests/test_skill_contract.py tests/test_skill_catalog.py
  tests/test_farm_policy.py` — 37 passed.
- `pre-commit run --all-files` — passed all hooks.
- No media command was run.
