---
name: farm
version: "1.0"
last_updated: "2026-08-13"
id: farm
one_line_purpose: Offload a long encode to the ghost k3s cluster and verify what comes back.
entry_point: docs/skills/farm.md
category: editing
mcp_compliance_level: partial
optimization_status: draft
status: active
dependencies: []
tags: [encode, farm, cluster, argo, ffmpeg, rendering]
description: >-
  Runs one encode on the ghost cluster instead of the laptop: frame-grid
  segments in parallel in one Argo pod, stream-copy join, ffprobe
  verification, local fallback when the cluster is unreachable.
metadata:
  type: procedure
---

# Encode farm

## When to Use

- A render or re-encode takes minutes on the laptop and starves the agent
  sessions running on the same machine
- Re-encoding a Prod act, a megacut segment, or any single long file

## When NOT to Use

- Cutting a story from the index → [`editing/SKILL.md`](editing/SKILL.md)
  (render.py; the farm re-encodes a file that already exists)
- A social copy under a byte cap → `tools/social.py` (two-pass arithmetic the
  farm does not do)
- Anything needing a working local ffmpeg → [`../rendering.md`](../rendering.md)

## Core Process

```bash
python3 tools/farm.py ~/Videos/Wolves/Prod/01-intro.mp4 \
    --out renders/01-intro.crf18.mp4
```

That is the whole interface for the default job: `libx264 crf 18 preset slow`
on the picture, `-c:a copy` on the sound (zero audio generations — the audio
tenet). Override the video recipe after `--` and the audio pass separately:

```bash
python3 tools/farm.py in.mp4 --out out.mp4 --audio-args "-c:a aac -b:a 192k" -- \
    -c:v libx264 -crf 20 -preset medium
```

Useful flags: `--segments N`, `--threads N` (default 6 — x264 flattens past
~8), `--reference FILE` (verify against a known-good encode, comparing codec
and geometry too), `--keep` (leave the Workflow + PVC for debugging),
`--local` (force the fallback), `--dry-run`.

## How it works (and why)

One input file → N **frame-grid segments** → N parallel ffmpeg processes in
one pod on `ghost` → `concat -c copy` join. Audio is *not* segmented: chunks
are video-only, one continuous audio pass runs beside them, and the join muxes
the two — per-chunk audio copies left AAC priming seams and non-monotonic DTS
warnings. This is the megacut's own join trick applied to a single file; the
module docstring in `tools/farm.py` records the full reasoning.

Data moves with `kubectl cp` around a `local-path` PVC (the cluster has no
artifact repository and no shared filesystem — by design, per the lab ADRs).
Progress streams from the pod's logs; the run ends with an ffprobe
verification against the source or `--reference`, because an ffmpeg exit code
of 0 is not evidence (issue #88).

## Red flags

- **The image is `docker.io/linuxserver/ffmpeg:8.1.2-cli-ls76`, not
  `ghcr.io/jrottenberg/ffmpeg`.** The jrottenberg image cannot be pulled on
  this cluster: the zot mirror syncs on *tag* references only (lab ADR 0007,
  so a digest pin 404s), ghcr's jrottenberg repo has no tags past 6.0, and
  `jrottenberg/*` is not in the sync allowlist. Widening the allowlist is a
  `lab/` change, which the farm must not make.
- **CPU-only.** No VAAPI for delivery encodes; AMD H.264 VAAPI quality is not
  delivery grade.
- **Requests fit the allocatable remainder, not the node.** ghost has ~15 of
  31.7 CPU already requested by lab workloads, so the pod requests 12 and
  bursts to `--limit-cpu` 24 when the cluster is idle. A request near the
  node's size would never schedule; `pod_blocker` fails fast with the
  scheduler's message if that changes.
- **Namespace `argo`, service account `argo`, node `ghost`, plain `Workflow`
  objects.** Never a WorkflowTemplate (those are GitOps'd from `lab/` and
  ArgoCD reverts manual edits), never SSH to a node.
- **Cleanup is automatic** (Workflow + PVC deleted); `--keep` opts out. A
  one-hour TTL after success is the backstop if the tool dies mid-run.
- If the cluster is unreachable the tool says so once and runs the same
  segmented plan locally — degrade, never block. A *wrong* output is the one
  unforgivable failure: verification failures exit 1 with the diff printed.

## Verification

`python3 -m pytest -q tests/test_farm.py` is offline. The live round trip is
gated: `DESTINY_FARM_E2E=1 python3 -m pytest -q tests/test_farm.py::test_cluster_roundtrip`.
