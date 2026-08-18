# Encode farm

## When to Use

**Whenever the cluster is reachable and something has to be encoded.** Owner,
2026-08-16: *"always prefer remote encoding when available."* There is no length
threshold to judge — `exo-0` has 32 cores to this workstation's 16 and is not
also running the agent sessions, so the remote path is both faster and the one
that does not starve the session that asked for it.

Local video encoding requires an explicit `--local`; cluster failure is not
permission to use the workstation.

- Re-encoding a Prod act, a megacut segment, or any single long file
- Assembling the programme — `tools/megacut.py` farms its ENCODE segments and
  keeps video stream-copy joins here, because remuxing bytes is not encoding

## When NOT to Use

- Cutting a story from the index → [`editing/SKILL.md`](editing/SKILL.md)
  (render.py; the farm re-encodes a file that already exists)
- A social copy under a byte cap → `tools/social.py`. It keeps ownership of
  the two-pass byte-budget arithmetic, then runs both passes in one farm pod
  when the cluster is reachable so x264's stats file survives between them.
- PNG/card/plate rendering and probes that do not encode video
- An operator explicitly supplied `--local` after accepting workstation load

## Core Process

```bash
python3 - <<'PY'
from tools import farm
ok, why = farm.cluster_available()
raise SystemExit(0 if ok else f"cluster unavailable: {why}")
PY

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
`--local` (explicit workstation permission), `--dry-run`. Never pass
`--node`; Kubernetes chooses between the scheduler-eligible nodes.

### Strictly remote megacut assembly

Until the conform-cache phase itself is routed through the farm, a cold cache
is a trap: `--farm` moves segment encodes to Kubernetes but
`tools/conform.ensure()` can still start local x264 before those segments.
For a guaranteed cluster-only build, bypass that cache and farm every picture
segment:

```bash
python3 tools/megacut.py stories/megacut/megacut.json \
    --farm --no-copy --farm-jobs 3
```

The final concat/remux and audio-only output mux may run locally; neither
encodes picture. If a plain `--farm` run prints a conform-cache output under
`~/.cache/destiny-vids/conform/`, stop it immediately.

`tools/social.py` follows the same remote-first rule. Its two passes run
sequentially in one farm workspace, then the fetched output is verified and
the tool records the exact `Prod/` source digest beside the 10 MB file. A
missing or mismatched digest makes `deliver.py status` schedule a rebuild even
when Syncthing timestamps are misleading.

## How it works (and why)

One input file → N **frame-grid segments** → N parallel ffmpeg processes in
one pod on whichever node Kubernetes selects → `concat -c copy` join. Audio is
*not* segmented: chunks
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

- **The image is `lscr.io/linuxserver/ffmpeg:8.1.2-cli-ls76`, not
  `ghcr.io/jrottenberg/ffmpeg`.** The jrottenberg image cannot be pulled on
  this cluster: the zot mirror syncs on *tag* references only (lab ADR 0007,
  so a digest pin 404s), ghcr's jrottenberg repo has no tags past 6.0, and
  `jrottenberg/*` is not in the sync allowlist. Widening the allowlist is a
  `lab/` change, which the farm must not make. `lscr.io` is allowlisted
  wholesale and the linuxserver build is the same full non-free build.
- **CPU-only, and not just for quality.** On 24 cores, libx264 slow beat
  h264_vaapi on identical input (15.7x vs 13.7x realtime) — and AMD VAAPI
  quality is not delivery grade anyway. Never request `amd.com/gpu`.
- **Request low, limit high — that is the house style.** The cluster runs at
  156–263% limit overcommit. Requesting 24 CPU gets you Pending; requesting 2
  with a limit of 24 can burst across idle capacity. Both `ghost` and `exo-0`
  provide roughly 32 cores; separate Workflows are how the scheduler can use
  both. One pod never spans two nodes.
- **Namespace `argo`, service account `argo`, no hostname selector, plain
  `Workflow` objects.** Never pass `--node`, never use a WorkflowTemplate
  (those are GitOps'd from `lab/` and ArgoCD reverts manual edits), never SSH
  to a node.
- **Cleanup is automatic** (Workflow + PVC deleted); `--keep` opts out. A
  one-hour TTL after success is the backstop if the tool dies mid-run.
- If the cluster is unreachable, stop. `--local` is the only authorization to
  encode video on the workstation. A *wrong* output is the one unforgivable
  failure: verification failures exit 1 with the diff printed.

## Verification

`python3 -m pytest -q tests/test_farm.py` is offline. The live round trip is
gated: `DESTINY_FARM_E2E=1 python3 -m pytest -q tests/test_farm.py::test_cluster_roundtrip`.
