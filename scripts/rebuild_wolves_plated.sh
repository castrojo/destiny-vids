#!/usr/bin/env bash
# Rebuild act VI (Seven Days to the Wolves, the musical) for delivery.
#
# The delivered master (~/Videos/wolves-musical/wolves-7days-plated-master-v9.mp4)
# is a PLATE BURN over the clean wolves-7days-master-v9.mp4 kept beside it,
# and burning is not idempotent, so the one-command route names the two steps
# explicitly -- a guessed `rebuild` pointing at the plated file would burn a
# second set of nameplates about real people on top of the first. The burn
# below always targets the FROZEN clean master, never the plated one, and the
# farm fetch is atomic (burntmp, then replace) -- the idempotence the old
# rebuild_note was waiting for, same shape as act II's scripts/rebuild_efmb.sh
# (#348).
#
#   ./scripts/rebuild_wolves_plated.sh [--local]
#
# Remote by default (AGENTS.md): rebuild-wolves.sh's picture encode and the
# burn both run on the farm cluster whenever it answers, and fall back to a
# memory-capped local encode with the reason printed. `--local` forces the
# workstation.
set -euo pipefail
cd "$(dirname "$0")/.."

LOCAL_OPT=()
if [ "${1:-}" = "--local" ]; then
    LOCAL_OPT=(--local)
    shift
    echo "rebuild-wolves-plated: encoding on THIS host (--local)" >&2
fi

# The farm rewrites argv[0] only, so resolve ffmpeg to a single binary first:
# the PATH shim's `podman exec` middle tokens would leak into the pod.
export DESTINY_FFMPEG="${DESTINY_FFMPEG:-/home/linuxbrew/.linuxbrew/bin/ffmpeg}"

echo "==> timing pass (shotlist, plates, cards, picture, audio, gates)"
./scripts/rebuild-wolves.sh "${LOCAL_OPT[@]+"${LOCAL_OPT[@]}"}"

echo "==> burn plates onto the CLEAN v9 master (never the plated one)"
python3 tools/plate.py burn \
    --video ~/Videos/wolves-musical/wolves-7days-master-v9.mp4 \
    --manifest stories/06-wolves-cayde-plates.json \
    --out ~/Videos/wolves-musical/wolves-7days-plated-master-v9.mp4 \
    --fit-picture "${LOCAL_OPT[@]+"${LOCAL_OPT[@]}"}"

echo "==> done; deliver with: python3 tools/deliver.py publish --act VI"
ffprobe -v error -show_entries format=duration -of csv=p=0 \
    ~/Videos/wolves-musical/wolves-7days-plated-master-v9.mp4
