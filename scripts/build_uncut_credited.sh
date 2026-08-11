#!/usr/bin/env bash
# Build a credited, scored, redacted cut of one indexed video, end to end.
#
# This is the whole pipeline as one command, because the interesting part of
# this repo is the generation, not the hand-assembly: every input is data that
# is already checked in (segments, vocab/casting.yaml, dialogue/, redactions/)
# and every intermediate is derived.
#
# Order matters and encodes the priority:
#   1. lead reveals   -- naming the cast correctly is the job the index exists for
#   2. dialogue       -- fitted around the reveals, anchored to its own footage
#   3. the ensemble   -- credited into whatever screen time is left
#
# Usage:
#   scripts/build_uncut_credited.sh <video_id> <roster.json> [music.mp3]
set -euo pipefail

VIDEO_ID="${1:?usage: $0 <video_id> <roster.json> [music.mp3]}"
ROSTER="${2:?usage: $0 <video_id> <roster.json> [music.mp3]}"
MUSIC="${3:-}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Intermediates live under the repo, not /tmp: the containerized ffmpeg on an
# atomic host only bind-mounts $HOME, so a /tmp path resolves inside the
# container and the input "does not exist".
mkdir -p renders

WORK="$(mktemp -d "$REPO_ROOT/renders/.build-XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

OUT_DIR="renders"
PLATES_DIR="$OUT_DIR/plates-$VIDEO_ID"
BASE="$WORK/base.mp4"
MANIFEST="$OUT_DIR/$VIDEO_ID-plates.json"
FINAL="$OUT_DIR/$VIDEO_ID-credited.mp4"

mkdir -p "$OUT_DIR"

echo "==> whole video as a cut list"
python3 tools/uncut.py "$VIDEO_ID" --out "$WORK/cut.json"

echo "==> 1/3 lead reveals"
python3 tools/plate.py plan "$WORK/cut.json" --only leads --hold 4 \
    --out "$WORK/leads.json"

echo "==> 2/3 dialogue, around the reveals"
python3 tools/dialogue.py "$WORK/cut.json" --video-id "$VIDEO_ID" \
    --around "$WORK/leads.json" --out "$WORK/chat.json"

echo "==> 3/3 the ensemble, around both"
python3 tools/plate.py merge "$WORK/leads.json" "$WORK/chat.json" \
    --out "$WORK/fixed.json"
python3 tools/plate.py plan "$WORK/cut.json" --roster "$ROSTER" \
    --only ensemble --hold 2.6 --around "$WORK/fixed.json" \
    --out "$WORK/ensemble.json"

python3 tools/plate.py merge "$WORK/leads.json" "$WORK/chat.json" \
    "$WORK/ensemble.json" --out "$MANIFEST"

echo "==> redact burned-in copy${MUSIC:+ and score}"
if [ -n "$MUSIC" ]; then
    python3 tools/redact.py --video "media/$VIDEO_ID.mp4" --video-id "$VIDEO_ID" \
        --audio "$MUSIC" --audio-gain 0.9 --out "$BASE"
else
    python3 tools/redact.py --video "media/$VIDEO_ID.mp4" --video-id "$VIDEO_ID" \
        --out "$BASE"
fi

echo "==> burn the deck"
python3 tools/plate.py render --manifest "$MANIFEST" --out-dir "$PLATES_DIR" >/dev/null
python3 tools/plate.py burn --video "$BASE" --manifest "$MANIFEST" \
    --plates-dir "$PLATES_DIR" --out "$FINAL"

echo "==> $FINAL"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$FINAL"
