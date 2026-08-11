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
    echo "usage: $0 <issue-number> [roster.json] [--outline FILE]" >&2
    echo "       $0 --video-id <video_id> [roster.json] [--outline FILE]" >&2
    exit 2
}

[ $# -ge 1 ] || usage

ISSUE=""
VIDEO_ID=""
OUTLINE=""
if [ "$1" = "--video-id" ]; then
    [ $# -ge 2 ] || usage
    VIDEO_ID="$2"
    shift 2
else
    ISSUE="$1"
    shift
fi
ROSTER=""
while [ $# -gt 0 ]; do
    case "$1" in
        --outline) OUTLINE="${2:?--outline needs a file}"; shift 2 ;;
        *)         ROSTER="$1"; shift ;;
    esac
done

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
# parse_video_id returns (canonical_watch_url, youtube_id) -- match on the
# canonical URL, the same spelling ingest writes into the record.
watch_url, _youtube_id = parse_video_id(sys.argv[1])
for path in sorted(pathlib.Path("videos").glob("*.json")):
    record = json.loads(path.read_text())
    if watch_url in record.get("youtube_url", ""):
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
#
# The tag file starts life as a generated worksheet: every beat index already
# present, paired with its keyframe and timecodes, and null for every value.
# The mechanical half (file shape) is generated so the expensive half (looking
# at frames) is all that is left. null is not a default -- overlays in
# particular must be positively established per frame, never inherited from a
# skeleton -- so the check below, not the file's existence, is what lets the
# script continue.
if [ ! -f "$TAGS" ]; then
    say "worksheet for $VIDEO_ID"
    python3 tools/worksheet.py generate "$VIDEO_ID" \
        --keyframes-dir "$KEYFRAMES" --out "$TAGS"
fi

if ! python3 tools/worksheet.py check "$TAGS" --keyframes-dir "$KEYFRAMES"; then
    cat >&2 <<EOF

Stopping at tagging, which is where a person looks at frames.

    $TAGS is waiting: $BEATS beats to fill, one keyframe each in $KEYFRAMES/

Every beat needs \`overlays\`: it is the input to the \`clean\` gate, and an
untagged beat derives clean = false and leaves every cut. Use [] for a clean
frame. Name a character only where they are visibly in frame.

Progress: python3 tools/worksheet.py check $TAGS
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
#
# Two ways to finish, and which one applies is a property of the footage.
#
#   CUT      -- an outline picks clean shots out of the index and orders them.
#               tools/story.py draws only from the clean pool, so a trailer
#               full of HUD and title cards is fine: the unusable material
#               simply never gets chosen.
#   UNCUT    -- the whole video, credited end to end. Right for a cinematic
#               that already tells its story; wrong for anything whose unclean
#               beats are scattered through the middle.
#
# An outline is editorial work and this script does not invent one. But once
# one exists, the path from it to a rendered file is mechanical, and leaving
# that out was what made a freshly indexed trailer unreachable.
if [ -z "$OUTLINE" ] && [ -f "stories/$VIDEO_ID.txt" ]; then
    OUTLINE="stories/$VIDEO_ID.txt"
fi

if [ -n "$OUTLINE" ]; then
    [ -f "$OUTLINE" ] || { echo "no outline at $OUTLINE" >&2; exit 1; }
    mkdir -p renders
    CUT="renders/$VIDEO_ID-cut.json"
    say "cut list from $OUTLINE"
    python3 tools/story.py "$OUTLINE" --dir segments --format json --out "$CUT"
    say "render"
    python3 tools/render.py "$CUT" --out "renders/$VIDEO_ID-cut.mp4"
    say "renders/$VIDEO_ID-cut.mp4"
    echo "    Plates next, once you are happy with the cut:"
    echo "    python3 tools/plate.py plan $CUT --only leads --out plates.json"
    echo "    (docs/skills/plates.md)"
    exit 0
fi

if [ -z "$ROSTER" ]; then
    say "indexed. Nothing further asked for."
    echo "    A cut:   $0 ${ISSUE:---video-id $VIDEO_ID} --outline stories/$VIDEO_ID.txt"
    echo "    Uncut:   python3 tools/ensemble.py roster --out renders/roster.json"
    echo "             $0 ${ISSUE:---video-id $VIDEO_ID} renders/roster.json"
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
redactions = []
try:
    data = load_redactions(video_id, root=REDACTIONS_DIR)
except FileNotFoundError:
    pass
else:
    redactions = data["redactions"]
    start, end = kept_range(redactions, end)

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
        clipped.append(s)             # a redaction boundary runs through it

# A beat the redaction range cuts through is the one case the index cannot
# resolve alone: tags are beat-level and redaction is frame-level, so a long
# clean shot that dissolves into a logo card in its final seconds is tagged
# unclean as a whole while only its tail is. Trusting every such straddle
# would be too generous -- a head cut made for a ratings card would silently
# grandfather an unrelated HUD beat that happens to overlap it. So the trust
# is explicit: the redaction record names the segments it accounts for, in a
# file the owner reviews (CODEOWNERS).
acknowledged = set()
for item in redactions:
    acknowledged.update(item.get("acknowledges") or [])

for s in clipped:
    if s["segment_id"] in acknowledged:
        print(f"    note: {s['start_tc']}-{s['end_tc']} is unclean "
              f"({s.get('overlays')}); the redaction acknowledges it.")
    else:
        exposed.append(s)

if exposed:
    exposed.sort(key=lambda s: float(s["start_sec"]))
    print()
    print(f"REFUSING to build: {len(exposed)} unclean beat(s) survive redaction.")
    print("The uncut build renders the entire video, so each of these would be")
    print("in the finished file -- HUD, nameplates or burned-in text, under")
    print("real people's names.")
    for s in exposed[:8]:
        print(f"    {s['start_tc']}-{s['end_tc']}  overlays={s.get('overlays')}"
              f"  {s['segment_id']}")
    if len(exposed) > 8:
        print(f"    ... and {len(exposed) - 8} more")
    print()
    print("This video needs cutting, not crediting end to end:")
    print("    python3 tools/story.py <outline> --format json --out cut.json")
    print("    python3 tools/render.py cut.json --out renders/cut.mp4")
    print("(tools/story.py draws only from the clean pool.)")
    print("If a redaction boundary already handles the unclean part of a beat,")
    print(f"say so in redactions/{video_id}.json:")
    print('    "acknowledges": ["<segment_id>"]')
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

music = json.loads(result.stdout).get("music") or {}
if not music:
    raise SystemExit                     # genuinely unscored, by request

path = music.get("path")
if not path:
    # The common shape is `music: {url: ...}`, and nothing here fetches audio.
    # Rendering anyway would hand back a silent cut for a brief that asked for
    # a score -- the failure looks like an editorial choice, so it has to be
    # loud. Music is referenced, never committed, like all media.
    print("the brief asks for music but gives no local path.", file=sys.stderr)
    if music.get("url"):
        print(f"    yt-dlp -x --audio-format mp3 -o 'media/%(title)s.%(ext)s' "
              f"{music['url']}", file=sys.stderr)
    print("    then add `path: media/<file>.mp3` to the brief's music block.",
          file=sys.stderr)
    raise SystemExit(1)
print(path)
PY
)" || exit 1

say "build the credited cut"
scripts/build_uncut_credited.sh "$VIDEO_ID" "$ROSTER" ${MUSIC:+"$MUSIC"}
