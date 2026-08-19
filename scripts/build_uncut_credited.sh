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
# Resolved by id, never built as "media/$VIDEO_ID.mp4": a master that moves
# container (.mp4 -> .mkv, #229) must still be found.
SOURCE_VIDEO="$(python3 tools/footage.py path "$VIDEO_ID")"
ROSTER="${2:?usage: $0 <video_id> <roster.json> [music.mp3]}"
MUSIC="${3:-}"
MUSIC_AT=""

# ACODEC=flac builds a LOSSLESS master alongside the normal deliverable, so a
# later re-encode (a stereo fold-down for streaming, a different container)
# starts from the bed rather than from a lossy file. Output is suffixed so it
# never overwrites the shipped render.
ACODEC="${ACODEC:-aac}"
SUFFIX=""
[ "$ACODEC" = "aac" ] || SUFFIX="-hq"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ -z "$MUSIC" ]; then
    mapfile -t SCORE < <(python3 - "$VIDEO_ID" <<'PY'
import json
import sys
from pathlib import Path

record = Path("dialogue") / sys.argv[1] / "dialogue.json"
if record.exists():
    score = json.loads(record.read_text(encoding="utf-8")).get("score") or {}
    if score.get("bed_id"):
        print(Path("media") / f"{score['bed_id']}.wav")
        print(score.get("start_sec", 0))
PY
)
    if [ "${#SCORE[@]}" -ge 2 ]; then
        MUSIC="${SCORE[0]}"
        MUSIC_AT="${SCORE[1]}"
    fi
fi

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
FIXED_MANIFEST="stories/$VIDEO_ID-fixed-plates.json"
FINAL="$OUT_DIR/$VIDEO_ID-credited${SUFFIX}.mp4"

mkdir -p "$OUT_DIR"

echo "==> whole video as a cut list"
python3 tools/uncut.py "$VIDEO_ID" --out "$WORK/cut.json"

echo "==> 1/3 lead reveals"
STANDALONE_LEADS="$(python3 - "$VIDEO_ID" <<'PY'
import json
import sys
from pathlib import Path

record = Path("dialogue") / sys.argv[1] / "dialogue.json"
if not record.exists():
    print("true")
else:
    display = json.loads(record.read_text(encoding="utf-8")).get("display") or {}
    print("true" if display.get("standalone_leads", True) else "false")
PY
)"
if [ "$STANDALONE_LEADS" = "true" ]; then
    python3 tools/plate.py plan "$WORK/cut.json" --only leads --hold 4 \
        --out "$WORK/leads.json"
else
    printf '[]\n' > "$WORK/leads.json"
    echo "    omitted: dialogue pills carry the owner-authored speaker identities"
fi

echo "==> fixed cards and lead reveals"
FIXED_INPUTS=("$WORK/leads.json")
if [ -f "$FIXED_MANIFEST" ]; then
    FIXED_INPUTS+=("$FIXED_MANIFEST")
fi
python3 tools/plate.py merge "${FIXED_INPUTS[@]}" --out "$WORK/fixed.json"

echo "==> 2/3 dialogue, around the fixed cards"
python3 tools/dialogue.py "$WORK/cut.json" --video-id "$VIDEO_ID" \
    --around "$WORK/fixed.json" --out "$WORK/chat.json"

echo "==> 3/3 the ensemble, around both"
python3 tools/plate.py merge "$WORK/fixed.json" "$WORK/chat.json" \
    --out "$WORK/fixed-with-chat.json"
python3 tools/plate.py plan "$WORK/cut.json" --roster "$ROSTER" \
    --only ensemble --hold 2.6 --around "$WORK/fixed-with-chat.json" \
    --out "$WORK/ensemble.json"

python3 tools/plate.py merge "$WORK/fixed-with-chat.json" "$WORK/ensemble.json" \
    --out "$MANIFEST"

echo "==> redact burned-in copy${MUSIC:+ and score}"
if [ -n "$MUSIC" ]; then
    SCORE_ARGS=()
    [ -z "$MUSIC_AT" ] || SCORE_ARGS+=(--audio-at "$MUSIC_AT")
    python3 tools/redact.py --video "$SOURCE_VIDEO" --video-id "$VIDEO_ID" \
        --audio "$MUSIC" "${SCORE_ARGS[@]}" \
        --audio-codec "$ACODEC" --out "$BASE"
else
    python3 tools/redact.py --video "$SOURCE_VIDEO" --video-id "$VIDEO_ID" \
        --audio-codec "$ACODEC" --out "$BASE"
fi

echo "==> burn the deck"
python3 tools/plate.py render --manifest "$MANIFEST" --out-dir "$PLATES_DIR" \
    --fit-video "$SOURCE_VIDEO" >/dev/null
python3 tools/plate.py burn --video "$BASE" --manifest "$MANIFEST" \
    --plates-dir "$PLATES_DIR" --out "$FINAL"

echo "==> $FINAL"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$FINAL"
