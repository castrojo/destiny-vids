#!/usr/bin/env bash
# One GitHub issue -> a rendered cut, resuming wherever the last run stopped.
#
# The stages already exist as separate tools, and each one is worth running
# alone while debugging. What did not exist was the path between them: an agent
# picking up an issue had to know that ingest comes before detection, that
# detection happens twice with tagging in between, and that tagging is the one
# stage a script cannot do for you. That knowledge lived in a skill doc, which
# meant every new video re-derived it.
#
# So this is the loop, in order, with the stop in the right place:
#
#   1. brief      -- read the issue's `brief` block (tools/brief.py)
#   2. ingest     -- a video record per source (tools/ingest.py)
#   3. fetch      -- the media itself, H.264 (yt-dlp)
#   4. detect     -- beats + one keyframe each (pass 1)
#   5. TAG        -- STOPS HERE. A person or a vision model looks at frames.
#   6. assemble   -- replay tags into segments (pass 2)
#   7. build      -- plates, dialogue, ensemble, redaction, render
#
# Every stage is skipped when its output already exists, so re-running after
# tagging picks up at 6 rather than re-fetching 200MB and re-detecting. That
# also makes the script safe to run repeatedly while a video is half-done,
# which is the normal state of a video.
#
# Stage 5 is not a missing feature. Cleanliness has to be positively
# established -- an untagged beat derives clean = false and leaves every cut --
# and "nobody has looked at this frame" is not evidence that the frame is
# clean. A script that guessed here would put a HUD in a finished cut. See
# docs/skills/indexing.md.
#
# Usage:
#   scripts/make_video.sh <issue-number> [roster.json]
#   scripts/make_video.sh --video-id <video_id> [roster.json]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

usage() {
    echo "usage: $0 <issue-number> [roster.json]" >&2
    echo "       $0 --video-id <video_id> [roster.json]" >&2
    exit 2
}

[ $# -ge 1 ] || usage

ISSUE=""
VIDEO_ID=""
if [ "$1" = "--video-id" ]; then
    [ $# -ge 2 ] || usage
    VIDEO_ID="$2"
    shift 2
else
    ISSUE="$1"
    shift
fi
ROSTER="${1:-}"

say() { printf '==> %s\n' "$*"; }
skip() { printf '    (have %s, skipping)\n' "$*"; }

# ---------------------------------------------------------------- 1. brief
if [ -n "$ISSUE" ]; then
    say "brief for issue #$ISSUE"
    BRIEF="$(python3 tools/brief.py parse "$ISSUE")" || {
        echo "No usable brief. Propose one and get it confirmed:" >&2
        echo "    python3 tools/brief.py normalize $ISSUE" >&2
        exit 1
    }

    AUTOMATABLE="$(printf '%s' "$BRIEF" | python3 -c 'import json,sys; print(json.load(sys.stdin)["automatable"])')"
    if [ "$AUTOMATABLE" = "no" ]; then
        printf '%s' "$BRIEF" | python3 -c '
import json, sys
brief = json.load(sys.stdin)
print("This issue is not automatable, so it stops here -- which is the")
print("correct outcome, not a failure. It is waiting on:")
print()
print("   ", brief.get("blocked_on", "(unstated -- ask the owner)"))
'
        exit 0
    fi

    # Separate reads rather than one `read` over two words: a brief whose first
    # source has a url but no video_id (the normal shape for a video nobody has
    # ingested yet) would otherwise have the URL shift into VIDEO_ID, since
    # `read` collapses the empty leading field.
    VIDEO_ID="$(printf '%s' "$BRIEF" | python3 -c '
import json, sys
sources = json.load(sys.stdin).get("sources") or []
print((sources[0] if sources else {}).get("video_id") or "")
')"
    SOURCE_URL="$(printf '%s' "$BRIEF" | python3 -c '
import json, sys
sources = json.load(sys.stdin).get("sources") or []
print((sources[0] if sources else {}).get("url") or "")
')"
    if [ -z "$VIDEO_ID" ] && [ -z "$SOURCE_URL" ]; then
        echo "brief names no source to build from" >&2
        exit 1
    fi
else
    SOURCE_URL=""
fi

# ---------------------------------------------------------------- 2. ingest
if [ -z "$VIDEO_ID" ]; then
    say "ingest $SOURCE_URL"
    python3 tools/ingest.py "$SOURCE_URL"
    VIDEO_ID="$(python3 - "$SOURCE_URL" <<'PY'
import json, pathlib, sys
from tools.ingest import parse_video_id
wanted = parse_video_id(sys.argv[1])
for path in sorted(pathlib.Path("videos").glob("*.json")):
    record = json.loads(path.read_text())
    if wanted in record.get("youtube_url", ""):
        print(record["video_id"])
        break
PY
)"
    [ -n "$VIDEO_ID" ] || { echo "ingest did not produce a video record" >&2; exit 1; }
fi

RECORD="videos/$VIDEO_ID.json"
[ -f "$RECORD" ] || { echo "no video record at $RECORD" >&2; exit 1; }
say "video_id $VIDEO_ID"

MEDIA="media/$VIDEO_ID.mp4"
KEYFRAMES="keyframes/$VIDEO_ID"
TAGS="tags/$VIDEO_ID.json"

# ---------------------------------------------------------------- 3. fetch
if [ -f "$MEDIA" ]; then
    skip "$MEDIA"
else
    URL="$(python3 -c "import json;print(json.load(open('$RECORD'))['youtube_url'])")"
    say "fetch $URL"
    # H.264 explicitly: OpenCV cannot decode AV1 and silently reports the whole
    # video as one scene, which looks like a detector bug (docs/rendering.md).
    yt-dlp -S "vcodec:h264,res:1080" --merge-output-format mp4 \
        -o "media/$VIDEO_ID.%(ext)s" "$URL"
fi

CODEC="$(ffprobe -v error -select_streams v -show_entries stream=codec_name \
    -of csv=p=0 "$MEDIA" 2>/dev/null || echo unknown)"
if [ "$CODEC" != "h264" ]; then
    echo "WARNING: $MEDIA is $CODEC, not h264. Detection may report one beat" >&2
    echo "         for the whole video. See docs/rendering.md." >&2
fi

# ---------------------------------------------------------------- 4. detect
if [ -f "$KEYFRAMES/beats.json" ]; then
    skip "$KEYFRAMES/beats.json"
else
    say "detect beats and keyframes"
    python3 tools/annotate.py index --video "$MEDIA" --video-record "$RECORD"
fi
BEATS="$(python3 -c "import json;print(len(json.load(open('$KEYFRAMES/beats.json'))))")"

# ---------------------------------------------------------------- 5. tag
if [ ! -f "$TAGS" ]; then
    cat >&2 <<EOF

Stopping at tagging, which is where a person looks at frames.

    $BEATS keyframes in $KEYFRAMES/
    write $TAGS, keyed by beat index as a string ("0" .. "$((BEATS - 1))")

Every beat needs \`overlays\`: it is the input to the \`clean\` gate, and an
untagged beat derives clean = false and leaves every cut. Use [] for a clean
frame. Name a character only where they are visibly in frame.

Format and rules: docs/skills/indexing.md
Then run this script again -- it resumes here.
EOF
    exit 3
fi

# ---------------------------------------------------------------- 6. assemble
say "assemble segments"
python3 tools/annotate.py index --video "$MEDIA" --video-record "$RECORD" --tags "$TAGS"

python3 - "$VIDEO_ID" <<'PY'
import glob, json, sys
video_id = sys.argv[1]
segments = [json.load(open(p)) for p in glob.glob("segments/*.json")]
mine = [s for s in segments if s.get("video_id") == video_id]
clean = sum(1 for s in mine if s.get("clean"))
print(f"    {len(mine)} segment(s), {clean} clean")
if mine and clean == 0:
    print("    WARNING: nothing is clean. `overlays` was probably skipped --")
    print("    see docs/skills/indexing.md before cutting anything.")
PY

# ---------------------------------------------------------------- 7. build
if [ -z "$ROSTER" ]; then
    say "indexed. No roster given, so stopping before the credited build."
    echo "    python3 tools/ensemble.py roster --out renders/roster.json"
    echo "    $0 ${ISSUE:---video-id $VIDEO_ID} renders/roster.json"
    exit 0
fi

# `partly` means the mechanical half can run and the rest cannot. Indexing is
# the mechanical half; putting names on screen and shipping a file is not.
if [ "${AUTOMATABLE:-}" = "partly" ]; then
    say "brief is automatable: partly, so it stops before the credited build."
    printf '    waiting on: %s\n' "$(printf '%s' "$BRIEF" | python3 -c \
        'import json,sys; print(json.load(sys.stdin).get("blocked_on",""))')"
    exit 0
fi

# THE GATE, at the last moment it can still be enforced.
#
# build_uncut_credited.sh renders the WHOLE video and credits it. That is right
# for a cinematic, where the source already tells the story and redactions trim
# publisher copy off the head and tail -- and it is exactly wrong for a trailer
# whose unclean beats are scattered HUD, title cards and burned-in legal text,
# because rendering the whole thing puts every one of them in the finished
# file. tools/uncut.py does not filter on `clean`, by design.
#
# So the gate is checked here rather than assumed: if a beat is unclean and is
# not removed by the redaction range, this refuses and points at the cutting
# path, which does filter. Failing closed is the only safe direction -- the
# failure mode is a HUD in something published under real people's names.
python3 - "$VIDEO_ID" <<'PY' || exit 1
import glob, json, sys

sys.path.insert(0, ".")
from tools.redact import REDACTIONS_DIR, kept_range, load_redactions

video_id = sys.argv[1]
segments = [json.load(open(p)) for p in glob.glob("segments/*.json")]
mine = [s for s in segments if s.get("video_id") == video_id]
if not mine:
    print(f"no segments for {video_id}", file=sys.stderr)
    raise SystemExit(1)

start, end = 0.0, max(float(s["end_sec"]) for s in mine)
try:
    data = load_redactions(video_id, root=REDACTIONS_DIR)
except FileNotFoundError:
    pass
else:
    start, end = kept_range(data["redactions"], end)

exposed, clipped = [], []
for s in mine:
    if s.get("clean"):
        continue
    s0, s1 = float(s["start_sec"]), float(s["end_sec"])
    if s1 <= start or s0 >= end:
        continue                      # redaction removes it entirely
    if s0 >= start and s1 <= end:
        exposed.append(s)             # survives whole, untouched
    else:
        clipped.append(s)             # the owner drew a boundary through it

for s in clipped:
    # A beat the redaction range cuts through is one somebody has looked at: the
    # boundary is in redactions/<video_id>.json because a human put it there.
    # Tags are beat-level and redaction is frame-level, so this is exactly the
    # case the index cannot resolve on its own -- e.g. a long clean shot that
    # dissolves into a logo card in its final seconds.
    print(f"    note: {s['start_tc']}-{s['end_tc']} is unclean "
          f"({s.get('overlays')}) but the redaction range cuts through it; "
          "trusting that boundary.")

if exposed:
    print()
    print(f"REFUSING to build: {len(exposed)} unclean beat(s) survive redaction")
    print("whole. The uncut build renders the entire video, so each of these")
    print("would be in the finished file -- HUD, nameplates or burned-in text,")
    print("under real people's names.")
    for s in exposed[:8]:
        print(f"    {s['start_tc']}-{s['end_tc']}  overlays={s.get('overlays')}")
    if len(exposed) > 8:
        print(f"    ... and {len(exposed) - 8} more")
    print()
    print("This video needs cutting, not crediting end to end:")
    print("    python3 tools/story.py <outline> --format json --out cut.json")
    print("    python3 tools/render.py cut.json --out renders/cut.mp4")
    print("(tools/story.py draws only from the clean pool.)")
    print("If the unclean material is head/tail publisher copy, redact it:")
    print(f"    redactions/{video_id}.json")
    raise SystemExit(1)
PY

MUSIC="$(python3 - "${ISSUE:-}" <<'PY'
import json, subprocess, sys
issue = sys.argv[1]
if not issue:
    raise SystemExit
result = subprocess.run([sys.executable, "tools/brief.py", "parse", issue],
                        capture_output=True, text=True)
if result.returncode != 0:
    # Distinguished from "no music requested": the brief parsed a moment ago,
    # so failing now is an environment problem, and silently rendering an
    # unscored cut would look like the owner's choice.
    print("re-reading the brief for its music failed:", result.stderr.strip(),
          file=sys.stderr)
    raise SystemExit(1)
print((json.loads(result.stdout).get("music") or {}).get("path") or "")
PY
)" || exit 1

say "build the credited cut"
scripts/build_uncut_credited.sh "$VIDEO_ID" "$ROSTER" ${MUSIC:+"$MUSIC"}
