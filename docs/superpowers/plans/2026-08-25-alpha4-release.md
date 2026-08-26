# Alpha4 Release and Full Megacut Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve all authored work, rebuild the canonical 18-item *Seven Days to the Wolves* programme as `alpha4` on the remote farm, verify it, push the release branch, and stage it for the home-theater premiere.

**Architecture:** A named `release/alpha4` branch is created from the current clean act-II-updated checkout. Worktree changes are inspected and preserved on named remote branches before any cleanup; the release manifest is then bumped, all act and interlude builders are run, delivery is published, and `tools/megacut.py` assembles the programme. The final premiere uses `~/Videos/premiere.sh`, which stages the best available audio and opens VLC paused; Discord Go Live setup and disconnect remain manual because the repository explicitly forbids account automation.

**Tech Stack:** Git worktrees and branches, Python 3 tooling, Bash builders, Kubernetes/Argo farm via `tools/farm.py`, ffmpeg/ffprobe, pytest, pre-commit, VLC, Discord Go Live.

## Global Constraints

- The release identifier is `alpha4`; the canonical running order, item count, trim points, authored copy, and delivery layout remain unchanged.
- FFmpeg must never run locally; use the Kubernetes farm for every ffmpeg encode, and report a cluster outage as an explicit failure.
- Do not invent missing copy or cast a person without evidence.
- Do not move an authored beat to satisfy a layout or gate constraint.
- Do not hand-edit derived fields, generated outputs, delivery digests, or files in `~/Videos/Wolves`.
- Do not delete dirty worktree files or remove a worktree until its branch is safely present on a remote.
- A reported gap, stale record, or blocked plate is recorded and degraded according to repository policy; it does not withhold the video. A failed artifact verification must be corrected before that artifact is published.

---

### Task 1: Preserving dirty worktrees

**Files:**
- Inspect: `/var/home/jorge/src/destiny-vids/.superpowers/worktrees/common-doc-alignment`
- Inspect: `/var/home/jorge/src/dv-hero-videos`
- Modify: Git history and remote branches only; do not delete source files

**Interfaces:**
- Consumes: Existing worktree diffs and branches `feat/common-doc-alignment` and `feat/hero-videos`.
- Produces: Each coherent change committed on a named branch and present on `origin` or a named rescue branch.

- [ ] **Step 1: Capture each worktree's status and diff**

```bash
git worktree list --porcelain
git -C /var/home/jorge/src/destiny-vids/.superpowers/worktrees/common-doc-alignment status --short --branch
git -C /var/home/jorge/src/destiny-vids/.superpowers/worktrees/common-doc-alignment diff -- . ':!*.mp4'
git -C /var/home/jorge/src/dv-hero-videos status --short --branch
git -C /var/home/jorge/src/dv-hero-videos diff -- . ':!*.mp4'
find /var/home/jorge/src/dv-hero-videos/docs/skills/hero-videos \
  /var/home/jorge/src/dv-hero-videos/scripts/build_rafi_hero_overlay.py \
  /var/home/jorge/src/dv-hero-videos/scripts/qrcard.py \
  /var/home/jorge/src/dv-hero-videos/stories/rafi-hero-qr.json \
  /var/home/jorge/src/dv-hero-videos/tests/test_rafi_hero_overlay.py -type f -print
```

- [ ] **Step 2: Commit the coherent common-doc change**

```bash
git -C /var/home/jorge/src/destiny-vids/.superpowers/worktrees/common-doc-alignment \
  add -u .superpowers/sdd/2026-08-19-common-documentation-alignment/task-1-report.md
git -C /var/home/jorge/src/destiny-vids/.superpowers/worktrees/common-doc-alignment \
  commit -m "chore(docs): preserve common alignment cleanup" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
git -C /var/home/jorge/src/destiny-vids/.superpowers/worktrees/common-doc-alignment \
  push -u origin HEAD:rescue/common-doc-alignment
```

- [ ] **Step 3: Validate and commit the hero-videos change**

```bash
git -C /var/home/jorge/src/dv-hero-videos diff --check
(cd /var/home/jorge/src/dv-hero-videos && \
  python3 -m pytest -q tests/test_rafi_hero_overlay.py)
git -C /var/home/jorge/src/dv-hero-videos add \
  docs/SKILL.md docs/skills/index.json docs/skills/index.md \
  docs/skills/hero-videos scripts/build_rafi_hero_overlay.py \
  scripts/qrcard.py stories/rafi-hero-qr.json tests/test_rafi_hero_overlay.py
git -C /var/home/jorge/src/dv-hero-videos \
  commit -m "feat(heroes): preserve Rafi hero overlay work" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
git -C /var/home/jorge/src/dv-hero-videos push
```

- [ ] **Step 4: Prove both preserved branches are remotely reachable**

```bash
for w in \
  /var/home/jorge/src/destiny-vids/.superpowers/worktrees/common-doc-alignment \
  /var/home/jorge/src/dv-hero-videos
do
  h=$(git -C "$w" rev-parse HEAD)
  test "$(git -C "$w" branch -r --contains "$h" | wc -l)" -gt 0
done
```

Expected: both commands exit 0; no dirty file is discarded.

### Task 2: Creating the release branch and alpha4 manifest

**Files:**
- Create: Git branch `release/alpha4`
- Modify: `stories/megacut/megacut.json`
- Test: JSON parse and diff checks

**Interfaces:**
- Consumes: Clean `feat/act-two-vocal-bed` checkout at `0b69450`.
- Produces: Clean `release/alpha4` with `_version` beginning `alpha4`.

- [ ] **Step 1: Confirm the release source is clean**

```bash
git status --short
test -z "$(git status --short)"
git switch -c release/alpha4
git push -u origin release/alpha4
```

- [ ] **Step 2: Change only the megacut version record**

Edit the first line of `stories/megacut/megacut.json`'s `_version` value from
`alpha3` to:

```text
alpha4 -- full remote-first rebuild of the canonical 18-item programme from the current release branch; all stale act masters and dependent renders are rebuilt and republished before assembly.
```

Do not change `items`, trims, cards, or derived fields.

- [ ] **Step 3: Validate the manifest**

```bash
python3 -m json.tool stories/megacut/megacut.json >/dev/null
git diff --check
git diff -- stories/megacut/megacut.json
git add stories/megacut/megacut.json
git commit -m "chore(release): start alpha4 megacut" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
git push
```

Expected: the diff changes only `_version`, and the release branch is on
`origin` before any render starts.

### Task 3: Running the preflight bug sweep

**Files:**
- Read: `stories/megacut/delivery.json`, `stories/megacut/megacut.json`
- Test: delivery status, megacut dry-run, farm policy, targeted tests

**Interfaces:**
- Consumes: `release/alpha4` and current `~/Videos/Wolves` delivery state.
- Produces: A recorded preflight report identifying every stale, foreign, blocked, or unresolved item without changing authored records.

- [ ] **Step 1: Run the required freshness proof**

```bash
python3 tools/deliver.py status --check
python3 tools/megacut.py stories/megacut/megacut.json --dry-run
```

Expected before rebuilding: stale/foreign findings may be reported; no finding
is silently ignored and the dry-run still lists all 18 plan items.

- [ ] **Step 2: Verify the declared rebuild map and canonical scope**

```bash
python3 - <<'PY'
import json

delivery = json.load(open("stories/megacut/delivery.json", encoding="utf-8"))
plan = json.load(open("stories/megacut/megacut.json", encoding="utf-8"))
assert set(delivery["masters"]) == {"0", "I", "II", "III", "IV", "V", "VI", "VII", "VIII"}
assert len(plan["items"]) == 18
for numeral, master in delivery["masters"].items():
    assert master.get("rebuild"), numeral
print("nine act rebuild commands and 18 programme items confirmed")
PY
```

- [ ] **Step 3: Run targeted offline regression tests**

```bash
python3 -m pytest -q \
  tests/test_farm_policy.py \
  tests/test_deliver.py \
  tests/test_megacut.py \
  tests/test_conform.py \
  tests/test_transitions.py
```

Expected: all selected tests pass before frame-touching work begins.

### Task 4: Rebuilding every act and Perfume interlude remotely

**Files:**
- Execute declared builders from `stories/megacut/delivery.json`
- Execute: `scripts/build_interludes.py`
- Generate: masters under `renders/` and project delivery directories

**Interfaces:**
- Consumes: current records, footage, cards, music, and release branch.
- Produces: rebuilt masters for acts 0 through VIII and clean Perfume movements 2
  through 5, with remote farm selection for every frame-touching encode.

- [ ] **Step 1: Confirm the farm is reachable**

```bash
python3 - <<'PY'
from tools import farm
ok, reason = farm.cluster_available()
print(reason)
raise SystemExit(0 if ok else 1)
PY
```

Expected: exit 0. If it exits 1, run the same builders without an explicit
local override only if their capped fallback reports the unavailable-cluster
reason; never run a bare local ffmpeg command.

- [ ] **Step 2: Rebuild all nine declared act masters**

```bash
python3 scripts/build_prologue.py
python3 scripts/build_act1.py
bash scripts/rebuild_efmb.sh
env ACODEC=flac bash scripts/build_uncut_credited.sh \
  yt_curse_of_osiris_opening_cinematic stories/roster-2026-08.json
python3 scripts/build_kat.py
python3 scripts/build_natali.py
bash scripts/rebuild_wolves_plated.sh
python3 scripts/build_europa.py
python3 scripts/build_credits.py \
  --out ~/Videos/wolves-credits/08-credits-master.mp4
```

After each command, verify its declared output exists and has a newer mtime
than the command's start time. Do not use `--print-command` output as a
replacement for running the builder.

- [ ] **Step 3: Rebuild all four clean Perfume movements**

```bash
python3 scripts/build_interludes.py
```

Expected outputs: `renders/perfume-2.mp4`, `renders/perfume-3.mp4`,
`renders/perfume-4.mp4`, and `renders/perfume-5.mp4`. Existing overlay
derivatives are rebuilt by their owning act builders when their inputs require
them; they are never hand-copied over.

- [ ] **Step 4: Publish each rebuilt act through the delivery graph**

```bash
python3 tools/deliver.py publish \
  --act 0 --act I --act II --act III --act IV --act V --act VI --act VII --act VIII
python3 tools/deliver.py status
```

Expected: each act's declared master and `Prod/` hardlink match by inode,
checksums and generated tables are current, and any remaining `copy` notes are
reported as unresolved owner decisions rather than treated as build failures.

- [ ] **Step 5: Commit source/provenance records, never media**

```bash
git status --short
git diff --check
git add stories/megacut/delivery.json
git commit -m "chore(release): record alpha4 rebuilt masters" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
git push
```

Only committed metadata changes belong in this commit. `media/`, `keyframes/`,
`renders/`, and video files remain ignored or outside Git.

### Task 5: Assembling and verifying the alpha4 megacut

**Files:**
- Read: `stories/megacut/megacut.json`
- Generate: `/var/home/jorge/Videos/Wolves/megacut/seven-days-to-the-wolves-alpha4.mp4`
- Generate: matching lossless `.mkv` programme master

**Interfaces:**
- Consumes: published act hardlinks and rebuilt `renders/` interludes.
- Produces: the alpha4 programme and its recorded provenance.

- [ ] **Step 1: Re-run the positive freshness proof**

```bash
python3 tools/deliver.py status --check
python3 tools/megacut.py stories/megacut/megacut.json --dry-run
```

Expected: no stale or foreign master remains. Recorded unresolved copy notes
may remain; they do not block assembly.

- [ ] **Step 2: Assemble with the farm default**

```bash
python3 tools/megacut.py stories/megacut/megacut.json
```

Expected output basename: `seven-days-to-the-wolves-alpha4.mp4`; expected
programme duration from the plan: `2321.142` seconds within the tool's
documented tolerance. The command must show remote farm work for encode
segments when the cluster answers.

- [ ] **Step 3: Measure joins and decode the assembled file**

```bash
python3 tools/transitions.py stories/megacut/megacut.json --measure \
  /var/home/jorge/Videos/Wolves/megacut/seven-days-to-the-wolves-alpha4.mp4
/home/linuxbrew/.linuxbrew/bin/ffmpeg -v error -xerror \
  -i /var/home/jorge/Videos/Wolves/megacut/seven-days-to-the-wolves-alpha4.mp4 \
  -f null -
```

Expected: duration and every measured join agree with the plan, and ffmpeg
decodes the complete programme without an error.

- [ ] **Step 4: Record programme provenance and commit metadata**

```bash
python3 tools/deliver.py publish \
  --act 0 --act I --act II --act III --act IV --act V --act VI --act VII --act VIII
git status --short
git add stories/megacut/megacut.json stories/megacut/delivery.json
git commit -m "chore(release): publish alpha4 megacut" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
git push
```

### Task 6: Running the complete validation suite

**Files:**
- Test: repository-wide checks
- Read: final delivery and worktree reports

**Interfaces:**
- Consumes: pushed `release/alpha4` and delivered files.
- Produces: verified release branch with no uncommitted release metadata.

- [ ] **Step 1: Run the required repository checks**

```bash
python3 -m pytest -q
python3 tools/corpus.py --check
python3 tools/rederive.py --check
python3 scripts/generate_schema_enums.py --check
python3 scripts/generate_skill_index.py --check
pre-commit run --all-files
```

Expected: every command exits 0. If a generated-output check fails, run its
documented `--write` generator, review the exact diff, commit the generated
output, and rerun the failed check; never hand-edit generated content.

- [ ] **Step 2: Run delivery and audio gates**

```bash
python3 tools/deliver.py status --check
python3 tools/readtime.py
~/Videos/audio-check.sh --all
```

Expected: no failing freshness/provenance/link/checksum finding, audio checks
pass for every delivered act, and read-time findings are reports only.

- [ ] **Step 3: Push and prove the release branch**

```bash
git status --short
test -z "$(git status --short)"
git push
git log -1 --oneline
```

### Task 7: Staging the home-theater premiere

**Files:**
- Read: `/var/home/jorge/Videos/PREMIERE.md`
- Execute: `/var/home/jorge/Videos/premiere.sh`

**Interfaces:**
- Consumes: `/var/home/jorge/Videos/Wolves/megacut/seven-days-to-the-wolves-alpha4.mp4`.
- Produces: a verified stereo playback stage and VLC opened fullscreen/paused.

- [ ] **Step 1: Validate the premiere target without playing it**

```bash
/var/home/jorge/Videos/premiere.sh \
  /var/home/jorge/Videos/Wolves/megacut/seven-days-to-the-wolves-alpha4.mp4 \
  --dry-run
```

Expected: the exact alpha4 path resolves and the script reports the selected
audio source without altering the programme.

- [ ] **Step 2: Stage and open the premiere player**

```bash
/var/home/jorge/Videos/premiere.sh \
  /var/home/jorge/Videos/Wolves/megacut/seven-days-to-the-wolves-alpha4.mp4
```

The script opens VLC fullscreen and paused after verifying the staged stereo
copy. It cannot legally automate Discord Go Live or disconnect on GNOME
Wayland; do not replace this with UI simulation or a user-token bot.

- [ ] **Step 3: Perform the final worktree audit**

```bash
git worktree list
for w in $(git worktree list --porcelain | awk '/^worktree /{print $2}'); do
  h=$(git -C "$w" rev-parse HEAD)
  [ "$(git -C "$w" branch -r --contains "$h" 2>/dev/null | wc -l)" -gt 0 ] ||
    printf 'UNPUSHED: %s (%s)\n' "$w" "$h"
  git -C "$w" status --short
done
```

Expected: no `UNPUSHED` line and no dirty status in any worktree. Do not remove
a worktree unless its branch is already present on a remote.
