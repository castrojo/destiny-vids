---
name: farm
version: "1.2"
last_updated: "2026-08-24"
id: farm
one_line_purpose: Run frame-touching encodes on the remote Kubernetes farm.
entry_point: docs/skills/farm.md
category: operations
status: active
dependencies: []
tags:
  - ffmpeg
  - kubernetes
  - encode
  - remote
  - render
description: >-
  Run frame-touching encodes on the remote farm. Use when the cluster is
  reachable and you need a Prod encode, a megacut segment, or another long
  render.
metadata:
  type: runbook
---

# Encode farm

## Hero workspace exception

`~/Videos/Wolves/Hero` forbids local `ffmpeg` and `ffprobe` for **all** media
work, including audio-only probes, bed construction, and delivery measurement.
That stricter hero policy overrides the generic local examples and exemptions
in this runbook. For an authorized Hero source, follow the
[hero-scoped Argo audio recipe](hero-videos/references/authorized-audio-on-argo.md);
do not apply a local command from this file. The recipe does not assert that an
authorized song source exists.

## When to Use

**Whenever the cluster is reachable and something has to be encoded.** Owner,
2026-08-16: *"always prefer remote encoding when available."* There is no length
threshold to judge — `exo-0` has 32 cores to this workstation's 16 and is not
also running the agent sessions, so the remote path is both faster and the one
that does not starve the session that asked for it.

Every encode entry point in the repo takes this posture by itself now
(`tests/test_farm_policy.py` pins it): farm when the cluster answers, and when
it does not — or the operator passed `--local` — the same argv runs on this
host **memory-capped** (`farm.run_capped_local`, a systemd scope with
MemoryMax=12G / MemoryHigh=10G) with the reason printed. A bare uncapped local
x264 run is what OOM-killed the owner's workstation at 03:08Z on 2026-08-24.
Local is a stated, bounded fallback — never silent, never unbounded.

- Re-encoding a Prod act, a megacut segment, or any single long file
- Assembling the programme — `tools/megacut.py` farms its ENCODE segments and
  its conform-cache misses, and keeps video stream-copy joins here, because
  remuxing bytes is not encoding

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

### Megacut assembly is remote end to end

`tools/megacut.py` farms both encode phases when the cluster answers: the
conform cache (a miss used to mean a silent local x264 run even under
`--farm` — the trap this section used to warn about) and the ENCODE
segments. COPY segments, the final concat and the lossless master stay local;
they stream-copy picture, and remuxing bytes is not an encode. `--no-copy`
remains as the debugging switch that forces every segment down the encode
path. If a build prints a conform-cache encode under
`~/.cache/destiny-vids/conform/` running on THIS host without `--local` in
sight, the cluster is unreachable and the log will say why — that is the
fallback working, not a leak, but the reason is worth reading.

`tools/social.py` follows the same remote-first rule. Its two passes run
sequentially in one farm workspace, then the fetched output is verified and
the tool records the exact `Prod/` source digest beside the 10 MB file. A
missing or mismatched digest makes `deliver.py status` schedule a rebuild even
when Syncthing timestamps are misleading.

### Building a new encoder: the shared posture

A new build script never shells out to ffmpeg itself. It takes the posture
from `tools/farm.py`:

- `farm.run_encode(argv, inputs=[...], out=..., local=args.local)` — one
  encode; farms when the cluster answers, else `run_capped_local` with the
  reason printed, and a `FarmError` mid-encode falls back the same way.
- `farm.run_ffmpeg_chain_on_cluster(argvs, inputs=..., out=..., tmp_prefix=...,
  text_files=...)` — ordered commands whose intermediates (render.py's clips,
  act II's parts, a concat list) live and die in one pod; only `out` comes
  back.
- `farm.run_capped_local(cmd, reason=...)` — the fallback primitive: prints
  the reason, runs the encode under the 12G scope, warns loudly and runs
  uncapped only when systemd-run itself is unavailable (degrade, never
  block).

Audio-only ffmpeg calls (video stream-copied or absent) are exempt from all
of this and stay local — **except in `~/Videos/Wolves/Hero`**, where the Hero
workspace exception above requires Argo for every media command.
`tests/test_farm_policy.py` holds the generic whitelist.

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
- **Resolve ffmpeg to a single binary before farming: `DESTINY_FFMPEG=/home/linuxbrew/.linuxbrew/bin/ffmpeg`.**
  The farm rewrites `argv[0]` only, so this host's default
  `podman exec bluefin-thumbnailer ffmpeg` leaks its middle tokens into the
  pod and the job dies on `Unable to choose an output format for 'exec'`.
- **A 4K file in `media/` is not automatically our upscale, and the watermark
  is how you tell.** Publisher re-uploads of the same title exist at 2160p and
  sort next to ours. Ours is the **`upscale-scratch` PVC**, `final/master.mov`
  (ProRes), and its provenance is legible in its own dimensions: 3840x1608 is
  exactly 2x the authored 1920x804 scope, so it was upscaled from the **clean
  1080p**, which is why it carries no burned-in publisher copy. A source whose
  size is not 2x an authored scope did not come from us. Crop the watermark
  region of a mid-film frame and look before spending an encode:
  `ffmpeg -ss <t> -i <src> -vf crop=<w>:<h>:<x>:<y> -frames:v 1 /tmp/wm.png`.
- **Take the ProRes, never the upscaler's `master.mov` audio.** The upscale
  pipeline resamples to AAC 44.1 kHz while every original source carries Opus
  48 kHz. Remux the ProRes video against the **original** audio to get a
  working source with no generation loss on either stream.
- **`--print-command` output is a plan, not a master, and running it clips.**
  A builder that corrects peaks does so in `main()`: it renders, measures the
  true peak, derives a static gain and renders *again*. Lifting the printed
  command and running it on the farm skips the second half, so the file
  lands wherever the mix happened to peak — twice this session that was
  **+0.20 dBTP against a -1.10 ceiling**, i.e. clipping, from a run that
  reported success. Either farm the builder itself, or re-measure and re-render
  at the derived gain and verify the result lands on the ceiling.
- **That printed command is also not shell-safe.** The filtergraph contains
  `(` and `)`, so space-joining it into a script is a syntax error. Build farm
  scripts with `shlex.quote()` over the argv list, and strip the
  `podman exec bluefin-thumbnailer` prefix (see the `DESTINY_FFMPEG` flag
  above).
  It has cost a full render round more than once.
- **A concat LIST of absolute host paths farms through the chain runner's
  `text_files`.** `rewrite_argv_for_pod` rewrites `argv[0]` and named
  `inputs`, never the paths inside a `-f concat -i list.txt` payload — and
  act VIII's credits encode carries its rendered PNG paths exactly that way
  (its bare local rebuild is what OOM'd the workstation on 2026-08-24).
  `run_ffmpeg_chain_on_cluster(..., text_files={list_path: content})` —
  or `run_encode(..., text_files=...)` — rewrites every staged input's path
  inside the list's content to the pod's layout and places the rewritten
  list in the pod; the local file itself is never uploaded. Do not hand such
  an argv to `run_ffmpeg_on_cluster`: the pod would read a list of host
  paths it cannot see.
- **A plate burn is farmable, and it must be farmed.** Its argv carries ~78
  PNG `-i` inputs plus any `%0Nd` image sequence, and all of them have to be
  named in `inputs` or the pod cannot open them. Sequences stage as their
  frames; the pattern is rewritten to the pod's staged directory.
- **Fetch the burn's temporary output, not the master path.** `tools/plate.py`
  writes `<master>.burntmp.mp4` and atomically replaces the master only after
  the farm fetch succeeds; the runner must pass the output path named by the
  argv to `run_ffmpeg_on_cluster`.
- **One 78-deep `overlay` chain does not finish.** It stalls locally at ~12
  threads with a zero-byte output, and kills the pod on the cluster. Burn in
  batches. Batching by PLATE COUNT is correct but SERIAL -- pass N+1 consumes
  pass N -- so it uses one pod and about 3 of the cluster's 64 cores, and
  takes ~25 minutes for act II. Batching by TIME is independent and runs
  every segment at once, ~4 minutes, but a `-c copy` cut snaps to keyframes,
  so the segments do not sum to the source: act II came back 0.5 s long with
  held frames at each join. Aligning the cuts to real keyframes shrinks the
  error without removing it. Until the boundaries are frame-exact, the serial
  batch is what ships.

- If the cluster is unreachable the encode still ships: capped, local, and
  saying why — degrade, never block. What must never happen is an UNCAPPED or
  SILENT local encode. `--local` forces the workstation when that is what the
  operator wants. A *wrong* output is the one unforgivable failure:
  verification failures exit 1 with the diff printed.

## Verification

`python3 -m pytest -q tests/test_farm.py` is offline. The live round trip is
gated: `DESTINY_FARM_E2E=1 python3 -m pytest -q tests/test_farm.py::test_cluster_roundtrip`.
