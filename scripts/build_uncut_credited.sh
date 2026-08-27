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
#   scripts/build_uncut_credited.sh [--local] <video_id> <roster.json> [music.mp3]
set -euo pipefail

# Encoding is remote by default (AGENTS.md): the cluster has twice this
# workstation's cores and is not also hosting the agent session, so a local
# encode is both slower and starves the thing that asked for it. Both encode
# stages below (redact, plate burn) probe the cluster themselves and fall
# back to a memory-capped local encode with the reason printed; `--local`
# here is the explicit escape hatch, passed through to both.
LOCAL_OPT=()
if [ "${1:-}" = "--local" ]; then
    LOCAL_OPT=(--local)
    shift
    echo "farm: encoding locally -- asked for with --local" >&2
fi

VIDEO_ID="${1:?usage: $0 [--local] <video_id> <roster.json> [music.mp3]}"
# Resolved by id, never built as "media/$VIDEO_ID.mp4": a master that moves
# container (.mp4 -> .mkv, #229) must still be found.
SOURCE_VIDEO="$(python3 tools/footage.py path "$VIDEO_ID")"
ROSTER="${2:?usage: $0 [--local] <video_id> <roster.json> [music.mp3]}"
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
    else
        # `mapfile < <(...)` is a process substitution, so `set -e` cannot see
        # the Python exit code: a broken record or a missing `score.bed_id`
        # leaves SCORE empty and the build encodes a SILENT film, cleanly, at
        # exit 0. Degrading to no score is allowed -- doing it without saying
        # so is not.
        echo "    NOTE: no score for $VIDEO_ID (no dialogue record, no" \
             "score.bed_id, or the lookup failed) -- encoding SILENT" >&2
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
PREPARED_MANIFEST="$OUT_DIR/$VIDEO_ID-burn-manifest.json"
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

record = Path("dialogue") / sys.argv[1] / "presentation.json"
if not record.exists():
    print("true")
else:
    presentation = json.loads(record.read_text(encoding="utf-8"))
    print("true" if presentation.get("standalone_leads", True) else "false")
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

echo "==> required portraits from Actions and a persistent burn manifest"
python3 -m tools.avatars --manifest "$MANIFEST" --from-actions
python3 -m tools.avatars --manifest "$MANIFEST" \
    --prepare "renders/$VIDEO_ID-burn-manifest.json"

echo "==> redact burned-in copy${MUSIC:+ and score}"
REDACT_OUTRO=()
OUTRO="stories/$VIDEO_ID-outro.json"
if [ -f "$OUTRO" ]; then
    # The outro record darkens the tail and holds the last clean frame under
    # the closing wall; the bed continues under it and fades with the picture.
    REDACT_OUTRO=(--outro "$OUTRO")
fi
if [ -n "$MUSIC" ]; then
    SCORE_ARGS=()
    [ -z "$MUSIC_AT" ] || SCORE_ARGS+=(--audio-at "$MUSIC_AT")
    python3 tools/redact.py --video "$SOURCE_VIDEO" --video-id "$VIDEO_ID" \
        --audio "$MUSIC" "${SCORE_ARGS[@]}" "${REDACT_OUTRO[@]}" \
        --audio-codec "$ACODEC" "${LOCAL_OPT[@]+"${LOCAL_OPT[@]}"}" \
        --out "$BASE"
else
    python3 tools/redact.py --video "$SOURCE_VIDEO" --video-id "$VIDEO_ID" \
        --audio-codec "$ACODEC" "${REDACT_OUTRO[@]}" \
        "${LOCAL_OPT[@]+"${LOCAL_OPT[@]}"}" --out "$BASE"
fi

echo "==> burn the deck"
# Not >/dev/null: this prints which full-frame cards it did NOT draw, and the
# loop below only knows how to draw `logowall`. Swallowing it means a new
# full-frame kind is skipped in silence and the burn either dies on a missing
# PNG or, worse, reuses a stale one from the last build.
python3 tools/plate.py render --manifest "$PREPARED_MANIFEST" --out-dir "$PLATES_DIR" \
    --fit-video "$SOURCE_VIDEO" | grep -v '^wrote ' || true
# Full-frame cards plate.py does not draw (the interstitial precedent): each
# logowall entry is rendered from the landscape record by its own builder,
# landing in the same plates dir under the same plate_<id>.png name.
mapfile -t WALLS < <(python3 - "$PREPARED_MANIFEST" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    doc = json.load(fh)
entries = doc["plates"] if isinstance(doc, dict) else doc
for e in entries:
    if e.get("kind") == "logowall":
        print(f"{e['id']}\t{e.get('title', '')}\t{e.get('footer', '')}")
PY
)
for wall in "${WALLS[@]}"; do
    [ -n "$wall" ] || continue
    IFS=$'\t' read -r WALL_ID WALL_TITLE WALL_FOOTER <<< "$wall"
    WALL_ARGS=(--title "$WALL_TITLE")
    [ -z "$WALL_FOOTER" ] || WALL_ARGS+=(--footer "$WALL_FOOTER")
    python3 scripts/build_cncf_wall.py "${WALL_ARGS[@]}" \
        --fit-video "$SOURCE_VIDEO" \
        --out "$PLATES_DIR/plate_$WALL_ID.png"
done
python3 tools/plate.py burn --video "$BASE" --manifest "$PREPARED_MANIFEST" \
    --plates-dir "$PLATES_DIR" "${LOCAL_OPT[@]+"${LOCAL_OPT[@]}"}" --out "$FINAL"

echo "==> $FINAL"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$FINAL"

if [ "$VIDEO_ID" = "yt_curse_of_osiris_opening_cinematic" ]; then
    echo "==> acceptance audit (not run automatically)"
    echo "python3 tools/plate_frame_audit.py --delivered $FINAL --manifest $PREPARED_MANIFEST --plates-dir $PLATES_DIR --expected tests/fixtures/acts_ii_iii_recovery.json --act III --out renders/recovery/act-III --check"
fi
