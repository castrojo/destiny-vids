#!/usr/bin/env bash
# Build join-2238 review excerpts: A (as shipped), B (picture dissolve), C (cut on shot change)
set -euo pipefail
FF=/home/linuxbrew/.linuxbrew/bin/ffmpeg
REPO=/var/home/jorge/src/destiny-vids
PROG="/var/home/jorge/Videos/Wolves/megacut/seven-days-to-the-wolves-v3.5.mp4"
ACT6="/var/home/jorge/Videos/Wolves/Prod/06-7daystothewolves.mp4"
P4="$REPO/renders/perfume-4.mp4"
OUT="$REPO/renders/review"
W="$REPO/work/seam-2238"

# --- intermediate: act VI tail 426.0 -> 432.0, visually lossless, pts normalized
"$FF" -hide_banner -loglevel error -y -ss 426.0 -i "$ACT6" -t 6.2 \
  -vf "setpts=PTS-STARTPTS" -af "asetpts=PTS-STARTPTS" \
  -c:v libx264 -crf 12 -preset fast -pix_fmt yuv420p -c:a pcm_s16le "$W/act6tail.mkv"
# tail t=0 ~= act-film 426.007 (first frame >= 426.0). Windows relative to tail:
#   B act6: 427.231-426.007=1.224 -> 431.231-426.007=5.224  (4.000 s)
#   C act6: 426.997-426.007=0.990 -> 430.997-426.007=4.990  (4.000 s)

# --- A: as shipped, from the delivered programme, seam at 4.000
"$FF" -hide_banner -loglevel error -y -ss 1353.105 -i "$PROG" -t 8.0 \
  -vf "fps=30,format=yuv420p" -c:v libx264 -crf 18 -preset medium \
  -c:a aac -b:a 192k -ar 48000 -ac 2 -movflags +faststart \
  "$OUT/join-2238-A-asshipped.mp4"

# --- B: 0.5 s picture-only dissolve ending at the cut; audio hard-cut at 4.000
"$FF" -hide_banner -loglevel error -y -i "$W/act6tail.mkv" -i "$P4" -filter_complex "
[0:v]trim=start=1.224:end=5.224,setpts=PTS-STARTPTS,fps=30,scale=1920:1080,setsar=1,format=yuv420p[v0];
[1:v]trim=start=0:end=4.5,setpts=PTS-STARTPTS,fps=30,scale=1920:1080,setsar=1,format=yuv420p[v1];
[v0][v1]xfade=transition=fade:duration=0.5:offset=3.5,format=yuv420p[vout];
[0:a]atrim=start=1.224:end=5.224,asetpts=PTS-STARTPTS,aresample=48000[a0];
[1:a]atrim=start=0:end=4.0,asetpts=PTS-STARTPTS,aresample=48000[a1];
[a0][a1]concat=n=2:v=0:a=1,volume=-1.7dB,aresample=48000[aout]" \
  -map "[vout]" -map "[aout]" -t 8.0 \
  -c:v libx264 -crf 18 -preset medium -c:a aac -b:a 192k -ar 48000 -movflags +faststart \
  "$OUT/join-2238-B-picturedissolve.mp4"

# --- C: act VI ends at the shot change (430.997 = frame 25834/59.94), hard cut both sides
"$FF" -hide_banner -loglevel error -y -i "$W/act6tail.mkv" -i "$P4" -filter_complex "
[0:v]trim=start=0.990:end=4.990,setpts=PTS-STARTPTS,fps=30,scale=1920:1080,setsar=1,format=yuv420p[v0];
[1:v]trim=start=0:end=4.0,setpts=PTS-STARTPTS,fps=30,scale=1920:1080,setsar=1,format=yuv420p[v1];
[v0][v1]concat=n=2:v=1:a=0,format=yuv420p[vout];
[0:a]atrim=start=0.990:end=4.990,asetpts=PTS-STARTPTS,aresample=48000[a0];
[1:a]atrim=start=0:end=4.0,asetpts=PTS-STARTPTS,aresample=48000[a1];
[a0][a1]concat=n=2:v=0:a=1,volume=-1.7dB,aresample=48000[aout]" \
  -map "[vout]" -map "[aout]" -t 8.0 \
  -c:v libx264 -crf 18 -preset medium -c:a aac -b:a 192k -ar 48000 -movflags +faststart \
  "$OUT/join-2238-C-shotchange.mp4"

echo BUILT
for f in "$OUT"/join-2238-*.mp4; do
  "$FF" -hide_banner -i "$f" 2>&1 | grep -E 'Duration|Stream' | sed "s|^|$(basename "$f"): |"
done
