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

echo "==> burn plates onto the CLEAN picture (renders/efmb-plated.mp4)"
python3 tools/plate.py burn --video renders/efmb-hq.mp4 \
    --manifest stories/02-endless-forms-plates.json \
    --out renders/efmb-plated.mp4 --delivery-spec \
    "${LOCAL_OPT[@]+"${LOCAL_OPT[@]}"}"

echo "==> front section (title card -> perfume-2 -> Platform Wars -> Titanfall)"
# Owner, 2026-08-28: prepend, never rebase -- the existing film and every
# plate in it keep their seats; the front is a separate segment joined in
# front. 76.6 s = 4.0 black + 66.4 perfume-2 + 6.2 black.
python3 - "${LOCAL_OPT[@]+"${LOCAL_OPT[@]}"}" <<'PY'
import os, subprocess
from pathlib import Path
from tools import conform, farm

local = "--local" in __import__("sys").argv
ffmpeg = os.environ["DESTINY_FFMPEG"]
p2 = Path("renders/perfume-2.mp4")
front = Path("renders/efmb-front.mkv")

CLIP = 66.4   # perfume-2's own length
PRE, POST = 4.0, 6.2
vf = conform.video_filter_chain()
# The megacut plan's own treatment for movement 2, replayed inside the act:
# -4.0 dB under, 6.2 s fade-in, and the last 4.0 s rise linearly in dB back
# to unity (never above the source's peak).
cresc = ("volume='if(lt(t,{start:.3f}),1,pow(10,(4.0*(t-{start:.3f})/4.0)/20))'"
         ":eval=frame").format(start=CLIP - 4.0)
fc = (
    f"color=c=black:s=1920x1080:r=30:d={PRE},format=yuv420p[b0v];"
    f"anullsrc=r=48000:cl=stereo,atrim=duration={PRE},asetpts=PTS-STARTPTS[b0a];"
    f"[0:v]{vf}[v1];"
    f"[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
    f"volume=-4.0dB,afade=t=in:st=0:d=6.200,{cresc}[a1];"
    f"color=c=black:s=1920x1080:r=30:d={POST},format=yuv420p[b2v];"
    f"anullsrc=r=48000:cl=stereo,atrim=duration={POST},asetpts=PTS-STARTPTS[b2a];"
    f"[b0v][b0a][v1][a1][b2v][b2a]concat=n=3:v=1:a=1[outv][outa]"
)
argv = [ffmpeg, "-y", "-i", p2, "-filter_complex", fc,
        "-map", "[outv]", "-map", "[outa]",
        *conform.video_encode_args(),
        "-c:a", "pcm_s24le", front]
where = farm.run_encode(argv, inputs=[p2], out=front,
                        expected_duration=PRE + CLIP + POST, local=local,
                        label="farm[efmb-front]")
print(f"front segment built ({where})")
PY

echo "==> front cards (renders/plates-02-front)"
NODE_PATH="$HOME/src/website/node_modules" \
    node cards/render-cards.mjs \
    --manifest stories/02-front-plates.json \
    --out-dir renders/plates-02-front

echo "==> burn front cards"
python3 tools/plate.py burn --video renders/efmb-front.mkv \
    --manifest stories/02-front-plates.json \
    --plates-dir renders/plates-02-front \
    --out renders/efmb-front-carded.mkv --delivery-spec \
    "${LOCAL_OPT[@]+"${LOCAL_OPT[@]}"}"

echo "==> join front + plated film (concat demuxer: video copied, one FLAC encode)"
python3 - "${LOCAL_OPT[@]+"${LOCAL_OPT[@]}"}" <<'PY'
import os
from pathlib import Path
from tools import farm

local = "--local" in __import__("sys").argv
ffmpeg = os.environ["DESTINY_FFMPEG"]
front = Path("renders/efmb-front-carded.mkv").resolve()
plated = Path("renders/efmb-plated.mp4").resolve()
tmp = plated.with_name("efmb-plated-frontedtmp.mp4")
# The house pattern (tools/megacut.py): demuxer join, video copied, audio
# encoded ONCE here -- never per segment. The front carries 24-bit PCM for
# exactly this; FLAC's STREAMINFO would bind the first file's extradata to
# the whole joined stream and break every later decode.
lst = Path("renders/efmb-front-join.txt")
lst.write_text(f"file '{front}'\nfile '{plated}'\n")
argv = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", lst,
        "-c:v", "copy", "-c:a", "flac", tmp]
where = farm.run_encode(
    argv, inputs=[front, plated], out=tmp,
    text_files={lst: lst.read_text()},
    local=local, label="farm[efmb-front-join]")
os.replace(tmp, plated)
print(f"front joined ({where}); master replaced atomically")
PY

echo "==> LF training CTA over the black tail (approved card, audio untouched)"
# docs/skills/training-cta/SKILL.md: one approved card, straight cut, source
# audio untouched. The takeover mark is MEASURED (last black run's start),
# never hardcoded. The replace is atomic (ctatmp, then rename), matching the
# burn's idempotence note above.
python3 - "${LOCAL_OPT[@]+"${LOCAL_OPT[@]}"}" <<'PY'
import os, re, subprocess, sys
from pathlib import Path
from tools import conform, farm

local = "--local" in sys.argv
plated = Path("renders/efmb-plated.mp4")
asset = Path("assets/cta/linux-foundation-training-forest.png")
ffmpeg = os.environ["DESTINY_FFMPEG"]

proc = subprocess.run(
    [ffmpeg, "-hide_banner", "-i", str(plated),
     "-vf", "blackdetect=d=0.5:pix_th=0.10", "-an", "-f", "null", "-"],
    capture_output=True, text=True)
starts = [float(s) for s in re.findall(r"black_start:([\d.]+)", proc.stderr)]
ends = [float(s) for s in re.findall(r"black_end:([\d.]+)", proc.stderr)]
dur = float(subprocess.check_output(
    [farm.native_ffprobe(), "-v", "error", "-show_entries", "format=duration",
     "-of", "csv=p=0", plated]))
tail = [s for s, e in zip(starts, ends) if abs(e - dur) < 0.5]
assert tail, "no black tail in the plated master -- nothing to replace"
start = tail[-1]
print(f"CTA takeover at {start:.3f}s (black tail runs to EOF {dur:.3f}s)")

tmp = plated.with_name("efmb-plated-ctatmp.mp4")
argv = [ffmpeg, "-y", "-i", plated, "-loop", "1", "-i", asset,
        "-filter_complex",
        f"[0:v][1:v]overlay=0:0:enable='gte(t,{start:.3f})':shortest=1[v]",
        "-map", "[v]", "-map", "0:a?", "-c:a", "copy",
        *conform.video_encode_args(), tmp]
where = farm.run_encode(argv, inputs=[plated, asset], out=tmp,
                        expected_duration=dur, local=local,
                        label="farm[efmb-cta]")
os.replace(tmp, plated)
print(f"CTA burned ({where}); master replaced atomically")
PY

echo "==> done; deliver with: python3 tools/deliver.py publish --act II"
ffprobe -v error -show_entries format=duration -of csv=p=0 renders/efmb-plated.mp4
