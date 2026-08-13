#!/usr/bin/env bash
# Rebuild the Wolves feature end to end, from the shotlist to a watchable file.
#
# ONE COMMAND PER ROUND OF NOTES. This exists because the loop is
# notes -> edit scripts/build_wolves.py -> watch it -> more notes, and every
# manual step in between is a step that gets skipped or mistyped at 1am.
#
#   ./scripts/rebuild-wolves.sh
#
# It also refuses to hand you a file with the two faults that have actually
# shipped here: a silent pause, and a true peak over the headroom gate. Both
# are invisible to "did it render" and both cost a re-render to find late.
set -euo pipefail
cd "$(dirname "$0")/.."

# The system ffmpeg on this atomic host is ffmpeg-free: no H.264 decoder, and
# it fails only once decoding starts, which reads like a corrupt input file.
FF=${DESTINY_FFMPEG:-/home/linuxbrew/.linuxbrew/bin/ffmpeg}
PY=${PYTHON:-.venv/bin/python3}
[ -x "$PY" ] || PY=python3

SHOTLIST=stories/seven-days-timing-pass.json
PICTURE=renders/07-wolves-picture.mp4
OUT=renders/07-wolves-timing-pass.mp4
REVIEW=${REVIEW_DIR:-$HOME/Videos/destiny-cuts-review}/07-seven-days-to-the-wolves-review.mp4

BED_GAIN=${BED_GAIN:--3.5}
SOURCE_GAIN=${SOURCE_GAIN:--1.5}   # the insert brings its own peaks; see AUDIO

echo "==> shotlist"
"$PY" scripts/build_wolves.py

echo "==> summit plates"
"$PY" scripts/build_summit_plates.py --fetch

echo "==> interruption cards"
"$PY" scripts/build_interruption_cards.py

echo "==> picture"
DESTINY_FFMPEG="$FF" "$PY" tools/render.py "$SHOTLIST" \
    --media media --out "$PICTURE" | tail -2

echo "==> audio"
DESTINY_FFMPEG="$FF" "$PY" tools/audiomix.py "$SHOTLIST" \
    --video "$PICTURE" --bed media/bed_seven_days_to_the_wolves.wav \
    --bed-gain-db "$BED_GAIN" --source-gain-db "$SOURCE_GAIN" \
    --media media \
    --out "$OUT" | tail -2

echo "==> checks"
"$PY" - "$SHOTLIST" "$OUT" <<'PY'
import json, subprocess, sys, math, array, os

shotlist, out = sys.argv[1], sys.argv[2]
FF = os.environ.get("DESTINY_FFMPEG", "/home/linuxbrew/.linuxbrew/bin/ffmpeg")
shots = json.load(open(shotlist))["shots"]

# Where does the film play its own audio? That region is the one place a
# missing audio track is INAUDIBLE as a bug: the bed is muted there by design,
# so a silent insert sounds exactly like a working pause.
#
# The interruption (#104) adds the inverse fault: a `silent` beat -- or the
# `hold` slot while no track is cleared -- that is AUDIBLE is the bed leaking
# into the pause. Both directions are measured here, from the shotlist's own
# wall clock.
wall, inserts, silences = 0.0, [], []
for s in shots:
    audio = s.get("audio", "bed")
    if audio == "source":
        inserts.append((wall, s["duration"]))
    elif audio in ("silent", "hold") and not s.get("audio_from"):
        silences.append((wall, s["duration"], audio))
    wall += s["duration"]


def measure(start, dur):
    raw = subprocess.run(
        [FF, "-v", "error", "-ss", str(start), "-i", out, "-t", str(dur),
         "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
        capture_output=True).stdout
    a = array.array("h", raw[: len(raw) // 2 * 2])
    rms = math.sqrt(sum(float(x) * x for x in a) / max(len(a), 1))
    return 20 * math.log10(rms / 32768 + 1e-12)


fail = []
for start, dur in inserts:
    db = measure(start, dur)
    print(f"    insert  @{start:7.2f}s  {dur:5.2f}s  rms {db:6.1f} dB")
    if db < -60:
        fail.append(f"the insert at {start:.2f}s is SILENT ({db:.1f} dB). "
                    "yt-dlp DASH formats are video-only -- fetch audio too.")

for start, dur, audio in silences:
    db = measure(start, dur)
    print(f"    {audio:6s} @{start:7.2f}s  {dur:5.2f}s  rms {db:6.1f} dB")
    if db >= -60:
        fail.append(f"the {audio} beat at {start:.2f}s is AUDIBLE "
                    f"({db:.1f} dB) -- the bed is leaking into the pause.")

peak = None
for line in subprocess.run(
        [FF, "-hide_banner", "-i", out, "-af", "loudnorm=print_format=summary",
         "-f", "null", "-"], capture_output=True, text=True).stderr.splitlines():
    if "Input True Peak" in line:
        peak = float(line.split(":")[1].strip().split()[0])
print(f"    true peak {peak} dBTP")
if peak is not None and peak > -1.0:
    fail.append(f"true peak {peak} dBTP is over the -1.0 gate. "
                "Lower SOURCE_GAIN (the insert usually brings the peaks).")

if fail:
    print("\nFAILED:")
    for f in fail:
        print("  " + f)
    raise SystemExit(1)
print("    OK")
PY

mkdir -p "$(dirname "$REVIEW")"
cp -f "$OUT" "$REVIEW"
# `bc` is not installed on this host; awk always is.
/home/linuxbrew/.linuxbrew/bin/ffprobe -v error -show_entries format=duration \
    -of csv=p=0 "$OUT" |
    awk -v f="$OUT" '{printf "\n%s  (%dm%05.2fs)\n", f, $1/60, $1%60}'
echo "watch: $REVIEW"
