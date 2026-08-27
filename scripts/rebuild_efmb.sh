#!/usr/bin/env bash
# Rebuild act II (Endless Forms Most Beautiful) end to end (#348).
#
# The delivered master (renders/efmb-plated.mp4) is a PLATE BURN over the
# pre-plate picture (renders/efmb-hq.mp4), and burning is not idempotent, so
# the one-command route has to name the three steps explicitly -- a guessed
# `rebuild` pointing at the plated file would burn a second set of nameplates
# about real people on top of the first. The burn below always targets the
# CLEAN picture this script just rendered, never the plated one, and the
# farm fetch is atomic (burntmp, then replace), which is the idempotence the
# old rebuild_note was waiting for.
#
#   ./scripts/rebuild_efmb.sh [--local]
#
# Every encode is REMOTE BY DEFAULT (AGENTS.md): the picture chain and the
# burn run on the farm cluster whenever it answers, and fall back to a
# memory-capped local encode with the reason printed. `--local` forces the
# workstation.
set -euo pipefail
cd "$(dirname "$0")/.."

LOCAL_OPT=()
if [ "${1:-}" = "--local" ]; then
    LOCAL_OPT=(--local)
    shift
    echo "rebuild-efmb: encoding on THIS host (--local)" >&2
fi

# The farm rewrites argv[0] only, so resolve ffmpeg to a single binary first:
# the PATH shim's `podman exec` middle tokens would leak into the pod.
export DESTINY_FFMPEG="${DESTINY_FFMPEG:-/home/linuxbrew/.linuxbrew/bin/ffmpeg}"

echo "==> clean picture (renders/efmb-hq.mp4)"
python3 scripts/build_efmb.py --render "${LOCAL_OPT[@]+"${LOCAL_OPT[@]}"}"

echo "==> plate manifest (stories/02-endless-forms-plates.json -- an OUTPUT)"
python3 scripts/build_efmb_plates.py --write

echo "==> required portraits from Actions and a persistent burn manifest"
python3 -m tools.avatars \
    --manifest stories/02-endless-forms-plates.json --from-actions
python3 -m tools.avatars \
    --manifest stories/02-endless-forms-plates.json \
    --prepare renders/02-endless-forms-burn-manifest.json

echo "==> render the burn manifest for frame audit"
python3 tools/plate.py render \
    --manifest renders/02-endless-forms-burn-manifest.json \
    --out-dir renders/plates-efmb --fit-video renders/efmb-hq.mp4

echo "==> burn plates onto the CLEAN picture (renders/efmb-plated.mp4)"
python3 tools/plate.py burn --video renders/efmb-hq.mp4 \
    --manifest renders/02-endless-forms-burn-manifest.json \
    --plates-dir renders/plates-efmb \
    --out renders/efmb-plated.mp4 --delivery-spec \
    "${LOCAL_OPT[@]+"${LOCAL_OPT[@]}"}"

echo "==> done; deliver with: python3 tools/deliver.py publish --act II"
ffprobe -v error -show_entries format=duration -of csv=p=0 renders/efmb-plated.mp4

echo "==> acceptance audit (not run automatically)"
echo "python3 tools/plate_frame_audit.py --delivered renders/efmb-plated.mp4 --manifest renders/02-endless-forms-burn-manifest.json --plates-dir renders/plates-efmb --expected tests/fixtures/acts_ii_iii_recovery.json --act II --out renders/recovery/act-II --check"
