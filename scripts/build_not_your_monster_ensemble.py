#!/usr/bin/env python3
"""Build the ENSEMBLE cut of Bluefin: Not Your Monster.

The band plays in a rounded window at the centre of a dynamic Bluefin stage
cycling through all 17 monthly and extra wallpapers; all four kids' drawing
animations run keyed and live around it; the website Bluefin wordmark sits
top-center; and the 26 equipment callouts appear in the bottom rail.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RECORD = REPO / "stories" / "not-your-monster-ensemble.json"
INTRO_RECORD = REPO / "stories" / "not-your-monster-intro-cards.json"
WORK = Path.home() / "Videos" / "Wolves" / "Hero" / ".work-not-your-monster"

FPS_NUM, FPS_DEN = 25, 1
CANVAS_W, CANVAS_H = 2560, 1440

FETCH_BASE = "http://192.168.1.227:8877"
RECEIVER = "http://192.168.1.227:8882"
PVC = "uta-ensemble-work-ghost"

TAIL_PAD = 75
APERTURE_MASK = "aperture-mask.png"
WORDMARK_ASSET_PATH = Path(".work-not-your-monster/assets/bluefin-wordmark.png")

WALLPAPERS = [
    "month-01.png", "month-02.png", "month-03.png", "month-04.png",
    "month-05.png", "month-06.png", "month-07.png", "month-08.png",
    "month-09.png", "month-10.png", "month-12.png", "extra-sunset.png",
    "extra-space-needle.png", "extra-clouds.png", "extra-red-tulip.png",
    "extra-foothills.png", "extra-chicken.png"
]

FILL = "s0=255:s1=255:s2=255:d0=0:d1=255:d2=0"
LEONARDO_NAME_MASK = (
    "drawbox=x=1020:y=0:w=1026:h=128:color=0x0000FF@1:t=fill"
)
LEONARDO_PAPER_POCKET = f"floodfill=x=640:y=870:{FILL}"

KEY_CHAINS = {
    "RAFI_01": (
        "crop=1986:2046:0:0,"
        "drawbox=x=980:y=0:w=1006:h=300:color=white@1:t=fill,"
        "format=rgba,split[c][m];"
        "[m]format=rgb24,"
        "lutrgb=r='if(gt(val,231),255,val)':g='if(gt(val,231),255,val)'"
        ":b='if(gt(val,231),255,val)',"
        f"floodfill=x=2:y=2:{FILL},"
        "format=rgba,colorkey=0x0000FF:0.01:0.0,alphaextract[al];"
        "[c][al]alphamerge,crop=1759:1862:71:145"
    ),
    "RAFI_02": (
        "crop=1754:2046:0:0,"
        "drawbox=x=860:y=0:w=894:h=231:color=white@1:t=fill,"
        "format=rgba,split[c][m];"
        "[m]format=rgb24,"
        "lutrgb=r='if(gt(val,247),255,val)':g='if(gt(val,247),255,val)'"
        ":b='if(gt(val,247),255,val)',"
        f"floodfill=x=2:y=2:{FILL},"
        f"floodfill=x=200:y=950:{FILL},"
        f"floodfill=x=580:y=1250:{FILL},"
        f"floodfill=x=400:y=1100:{FILL},"
        f"floodfill=x=1600:y=600:{FILL},"
        "floodfill=x=500:y=1850:s0=171:s1=171:s2=171:d0=0:d1=255:d2=0,"
        "geq="
        "r='if(between(Y,1696,1942)*between(r(X,Y),160,185)"
        "*between(g(X,Y),160,185)*between(b(X,Y),160,185),0,r(X,Y))':"
        "g='if(between(Y,1696,1942)*between(r(X,Y),160,185)"
        "*between(g(X,Y),160,185)*between(b(X,Y),160,185),0,g(X,Y))':"
        "b='if(between(Y,1696,1942)*between(r(X,Y),160,185)"
        "*between(g(X,Y),160,185)*between(b(X,Y),160,185),255,b(X,Y))',"
        "format=rgba,colorkey=0x0000FF:0.01:0.0,alphaextract[al];"
        "[c][al]alphamerge,crop=1714:1714:40:231"
    ),
    "LAKSHMI": (
        "crop=1626:2048:0:0,split=2[c][m];"
        "[c]format=rgba[orig];"
        "[m]format=gray,lut=c0='if(gt(val,247),255,val)',"
        "drawbox=x=744:y=0:w=857:h=144:color=white:t=fill,format=rgb24,"
        + ",".join(
            f"floodfill=x={x}:y={y}:{FILL}"
            for x, y in [
                (2, 0), (1623, 0), (2, 2047), (1623, 2047), (2, 2),
                (1623, 2), (2, 2045), (1623, 2045), (1172, 60),
            ]
        )
        + ",colorkey=0x0000FF:similarity=0.00001:blend=0,"
        "format=rgba,alphaextract[al];"
        "[orig][al]alphamerge,crop=1414:1861:212:106"
    ),
    "LEONARDO": (
        "crop=2046:1746:0:0,"
        "format=rgba,split[c][m];"
        f"[m]format=rgb24,{LEONARDO_NAME_MASK},"
        "lutrgb=r='if(gt(val,247),255,val)':g='if(gt(val,247),255,val)'"
        ":b='if(gt(val,247),255,val)',"
        f"floodfill=x=2:y=2:{FILL},"
        f"floodfill=x=2043:y=2:{FILL},"
        f"floodfill=x=2:y=1743:{FILL},"
        f"floodfill=x=2043:y=1743:{FILL},"
        f"{LEONARDO_PAPER_POCKET},"
        "format=rgba,colorkey=0x0000FF:0.01:0.0,alphaextract[al];"
        "[c][al]alphamerge,crop=1888:1676:41:21"
    ),
}

KEY_BBOX = {
    "RAFI_01": (1759, 1862),
    "RAFI_02": (1714, 1714),
    "LAKSHMI": (1414, 1861),
    "LEONARDO": (1888, 1676),
}


def load_record():
    return json.loads(RECORD.read_text(encoding="utf-8"))


def stations(record):
    out = []
    for k in record["kids"]:
        bw, bh = KEY_BBOX[k["id"]]
        w = k["width"]
        h = int(round(bh * w / bw))
        out.append({
            **k,
            "scaled_width": w,
            "scaled_height": h,
        })
    return out


def build_background_graph(wallpapers, total_duration, fade_duration=1.5):
    """Build xfade filtergraph chaining N wallpapers over total_duration."""
    n = len(wallpapers)
    # Total time = n * D - (n - 1) * F  =>  D = (total_duration + (n - 1) * F) / n
    clip_dur = (total_duration + (n - 1) * fade_duration) / n
    shift = clip_dur - fade_duration

    inputs = []
    for i, name in enumerate(wallpapers):
        inputs.append(f"-loop 1 -t {clip_dur:.3f} -framerate {FPS_NUM}/{FPS_DEN} -i /work/nym/wallpapers/{name}")

    chain = []
    prev = "[0:v]"
    for i in range(1, n):
        offset = i * shift
        next_in = f"[{i}:v]"
        out_lbl = f"[v{i}]" if i < n - 1 else "[bg_out]"
        chain.append(
            f"{prev}{next_in}xfade=transition=fade:duration={fade_duration:.2f}:offset={offset:.3f}{out_lbl}"
        )
        prev = out_lbl

    return " ".join(inputs), ";".join(chain)


def build_workflow_yaml(record, pvc=PVC):
    output = record["delivery"]["output"]
    src_frames = record["delivery"]["source_frames"]
    prog_frames = record["delivery"]["programme_frames"]
    slide_frames = record["delivery"]["slide_frames"]
    gain = record["delivery"]["audio_gain_db"]
    bitrate = record["delivery"]["audio_bitrate_kbps"]
    win = record["band_window"]
    wordmark = record["wordmark"]
    kids = stations(record)

    bg_inputs, bg_filter = build_background_graph(WALLPAPERS, src_frames / FPS_NUM)

    cards = record["callout_schedule"]
    card_names = [
        f"card{i:02d}-{c['item']}-{c['pocket']}.png" for i, c in enumerate(cards)
    ]

    # Review timestamps: day, solo, night, credits
    review_times = [25.0, 75.0, 140.0, 230.0, 300.0, 360.0]

    fetch_cmds = [
        "mkdir -p /work/nym/assets /work/nym/cards /work/nym/wallpapers",
        "cd /work/nym",
        f"[ -f source.webm ] || curl -fsSL -o source.webm {FETCH_BASE}/.work-not-your-monster/source.webm",
        f'echo "{record["source"]["sha256"]}  source.webm" | sha256sum -c -',
        f"curl -fsSL -o assets/INTRO_BLUEFIN.png {FETCH_BASE}/.work-not-your-monster/assets/INTRO_BLUEFIN.png",
        f"curl -fsSL -o assets/bluefin-wordmark.png {FETCH_BASE}/.work-not-your-monster/assets/bluefin-wordmark.png",
        f"curl -fsSL -o cards/{APERTURE_MASK} {FETCH_BASE}/.work-not-your-monster/cards/{APERTURE_MASK}",
    ]
    for w in WALLPAPERS:
        fetch_cmds.append(
            f"[ -f wallpapers/{w} ] || curl -fsSL -o wallpapers/{w} {FETCH_BASE}/.work-not-your-monster/assets/wallpapers/{w}"
        )
    for cname in card_names:
        fetch_cmds.append(
            f"[ -f cards/{cname} ] || curl -fsSL -o cards/{cname} {FETCH_BASE}/.work-not-your-monster/cards/{cname}"
        )
    for kid in kids:
        fetch_cmds.append(
            f"[ -f {kid['id']}-src.mp4 ] || curl -fsSL -o {kid['id']}-src.mp4 {FETCH_BASE}/{kid['source'].replace(' ', '%20')}"
        )

    # Keying commands
    key_cmds = []
    for kid in kids:
        use = kid["use_frames"]
        factor = src_frames / use
        chain = KEY_CHAINS[kid["id"]]
        head, _, tail = chain.partition(";")
        pre = f"trim=end_frame={use},setpts=PTS-STARTPTS,setpts={factor:.9f}*PTS,fps={FPS_NUM}/{FPS_DEN}"
        graph = f"[0:v]{pre},{head}"
        if tail:
            graph = f"{graph};{tail}"
        post = (
            f"tpad=stop_mode=clone:stop={TAIL_PAD},"
            f"scale={kid['scaled_width']}:{kid['scaled_height']}:flags=lanczos"
        )
        if kid["flip"]:
            post += ",hflip"
        graph += f",{post},setsar=1,format=yuva420p[k]"
        
        mov = f"/work/nym/{kid['id']}-keyed.mov"
        proof = f"/work/nym/{kid['id']}-proof.png"
        key_cmd = (
            f"if [ ! -f {mov} ]; then\n"
            f"  ffmpeg -hide_banner -v error -y -i /work/nym/{kid['id']}-src.mp4 "
            f'-filter_complex "{graph}" -map "[k]" -frames:v {src_frames} '
            f"-c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le -qscale:v 11 -vendor apl0 "
            f"{mov}\n"
            f"fi\n"
            f"[ -f {proof} ] || ffmpeg -hide_banner -v error -y -ss 60 -i {mov} -frames:v 1 -pix_fmt rgba {proof}"
        )
        key_cmds.append(f"# Key {kid['id']}\n{key_cmd}")

    # Stage composite
    # Inputs:
    # 0: bg-video.mp4
    # 1: source.webm (band)
    # 2: aperture-mask.png
    # 3: bluefin-wordmark.png
    # 4..7: kids (LAKSHMI, RAFI_01, LEONARDO, RAFI_02)
    # 8..33: 26 cards
    stage_inputs = [
        "-i /work/nym/bg-video.mp4",
        "-i /work/nym/source.webm",
        f"-loop 1 -framerate {FPS_NUM}/{FPS_DEN} -i /work/nym/cards/{APERTURE_MASK}",
        f"-loop 1 -framerate {FPS_NUM}/{FPS_DEN} -i /work/nym/assets/bluefin-wordmark.png",
    ]
    for kid in kids:
        stage_inputs.append(f"-i /work/nym/{kid['id']}-keyed.mov")
    for cname in card_names:
        stage_inputs.append(f"-loop 1 -framerate {FPS_NUM}/{FPS_DEN} -i /work/nym/cards/{cname}")

    stage_chain = [
        # Band window
        f"[1:v]{win['letterbox_crop']},scale={win['width']}:{win['height']}:flags=lanczos,setsar=1,format=rgba[bandpix]",
        "[2:v]format=gray[amask]",
        "[bandpix][amask]alphamerge[band]",
        f"[0:v][band]overlay=x={win['x']}:y={win['y']}[stage0]",
        # Wordmark
        f"[3:v]format=rgba,scale={wordmark['display_width']}:-2:flags=lanczos,setsar=1[mark]",
    ]

    prev = "stage0"
    for idx, kid in enumerate(kids):
        in_idx = 4 + idx
        lbl = f"k{idx}"
        stage_chain.append(
            f"[{in_idx}:v]format=rgba,setsar=1,"
            f"fade=t=in:st=0:d=0.5:alpha=1,"
            f"fade=t=out:st={src_frames/FPS_NUM - 0.5:.3f}:d=0.5:alpha=1[{lbl}]"
        )
        stage_chain.append(
            f"[{prev}][{lbl}]overlay=x={kid['x']}:y={kid['y']}:eof_action=repeat[s{idx}]"
        )
        prev = f"s{idx}"

    stage_chain.append(
        f"[{prev}][mark]overlay=x={wordmark['x']}:y={wordmark['y']}:eof_action=repeat[wordmarked]"
    )
    prev = "wordmarked"

    for idx, (cname, c) in enumerate(zip(card_names, cards)):
        in_idx = 8 + idx
        a = c["start_seconds"]
        b = a + c["hold_seconds"]
        lbl = f"c{idx}"
        stage_chain.append(
            f"[{in_idx}:v]format=rgba,setsar=1,"
            f"fade=t=in:st={a:.3f}:d=0.5:alpha=1,"
            f"fade=t=out:st={b - 0.5:.3f}:d=0.5:alpha=1[{lbl}]"
        )
        stage_chain.append(
            f"[{prev}][{lbl}]overlay=x=0:y=0:enable='between(t,{a:.3f},{b:.3f})'[sc{idx}]"
        )
        prev = f"sc{idx}"

    stage_chain.append(f"[{prev}]format=yuv420p[v]")

    stage_cmd = (
        f"ffmpeg -hide_banner -v error -y {' '.join(stage_inputs)} "
        f'-filter_complex "{";".join(stage_chain)}" -map "[v]" '
        f"-c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -r {FPS_NUM}/{FPS_DEN} "
        f"-frames:v {src_frames} /work/nym/stage.mp4"
    )

    slide_dur = slide_frames / FPS_NUM
    head_slide_cmd = (
        f"ffmpeg -hide_banner -v error -y -loop 1 -framerate {FPS_NUM}/{FPS_DEN} "
        f"-i /work/nym/assets/INTRO_BLUEFIN.png -t {slide_dur:.3f} "
        f"-vf \"scale={CANVAS_W}:{CANVAS_H}:flags=lanczos,setsar=1,"
        f"fade=t=in:st=0:d=0.5,fade=t=out:st={slide_dur-0.5:.3f}:d=0.5,format=yuv420p\" "
        f"-c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -r {FPS_NUM}/{FPS_DEN} "
        f"-frames:v {slide_frames} /work/nym/head-slide.mp4"
    )

    delay_ms = int(round(slide_dur * 1000))
    concat_and_mux_cmds = [
        "cat > /work/nym/concat.txt <<'EOF'",
        "file '/work/nym/head-slide.mp4'",
        "file '/work/nym/stage.mp4'",
        "EOF",
        f"ffmpeg -hide_banner -v error -y -f concat -safe 0 -i /work/nym/concat.txt -c copy /work/nym/picture.mp4",
        f"ffmpeg -hide_banner -v error -y -i /work/nym/source.webm "
        f'-af "adelay={delay_ms}|{delay_ms},volume={gain:g}dB" -c:a aac -b:a {bitrate}k -ar 48000 -ac 2 /work/nym/audio.m4a',
        f"ffmpeg -hide_banner -v error -y -i /work/nym/picture.mp4 -i /work/nym/audio.m4a -map 0:v -map 1:a -c copy -movflags +faststart /work/nym/{output}",
    ]

    verify_cmds = [
        f"out=/work/nym/{output}",
        'ffprobe -v error -count_frames -show_format -show_streams -of json "$out" > /work/nym/ens-probe.json',
        'ffmpeg -xerror -v error -i "$out" -f null - 2> /work/nym/ens-decode.txt',
        'ffmpeg -hide_banner -nostats -y -i "$out" -af ebur128=peak=true -f null - 2> /work/nym/ens-ebur128.txt',
        ': > /work/nym/ens-gates.txt',
        "true_peak=$(awk '/^ *True peak:/ { in_tp=1; next } in_tp && /^ *Peak:/ { print $2; exit }' /work/nym/ens-ebur128.txt)",
        "printf 'true_peak_dbtp=%s\\n' \"$true_peak\" >> /work/nym/ens-gates.txt",
        'awk -v p="$true_peak" \'BEGIN { if (p == "" || p >= 0) exit 1 }\'',
        "v_frames=$(ffprobe -v error -select_streams v:0 -count_frames -show_entries stream=nb_read_frames -of default=nw=1:nk=1 \"$out\")",
        "printf 'video_frames=%s\\n' \"$v_frames\" >> /work/nym/ens-gates.txt",
        f'[ "$v_frames" = "{prog_frames}" ]',
        "printf 'all_gates=PASS\\n' >> /work/nym/ens-gates.txt",
    ]

    # Stills extraction
    for t in review_times:
        pt = slide_dur + t
        verify_cmds.append(
            f'ffmpeg -hide_banner -v error -y -ss {pt:.3f} -i "$out" -frames:v 1 -q:v 2 "/work/nym/review-{int(t)}s.jpg"'
        )

    upload_paths = [
        f"/work/nym/{output}",
        "/work/nym/ens-gates.txt",
        "/work/nym/ens-probe.json",
        "/work/nym/ens-ebur128.txt",
        "/work/nym/ens-decode.txt",
    ] + [f"/work/nym/review-{int(t)}s.jpg" for t in review_times]

    upload_cmds = [f'curl -fsS -T "{p}" "{RECEIVER}/$(basename {p})"' for p in upload_paths]

    full_script = (
        "set -ex\n"
        + "\n".join(fetch_cmds) + "\n\n"
        + f"# Build dynamic wallpaper background\nif [ ! -f /work/nym/bg-video.mp4 ]; then\n  ffmpeg -hide_banner -v error -y {bg_inputs} -filter_complex \"{bg_filter}\" -map \"[bg_out]\" -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -r {FPS_NUM}/{FPS_DEN} -frames:v {src_frames} /work/nym/bg-video.mp4\nfi\n\n"
        + "\n\n".join(key_cmds) + "\n\n"
        + f"# Render head slide\n{head_slide_cmd}\n\n"
        + f"# Render stage\n{stage_cmd}\n\n"
        + f"# Concat & Mux\n" + "\n".join(concat_and_mux_cmds) + "\n\n"
        + f"# Verify & Gates\n" + "\n".join(verify_cmds) + "\n\n"
        + f"# Upload\n" + "\n".join(upload_cmds) + "\n"
    )

    wf = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Workflow",
        "metadata": {
            "generateName": "nym-render-",
            "namespace": "argo",
            "labels": {
                "hero-video": "not-your-monster",
                "run-type": "ensemble-render"
            }
        },
        "spec": {
            "entrypoint": "render",
            "nodeSelector": {"kubernetes.io/hostname": "ghost"},
            "serviceAccountName": "argo",
            "podGC": {"strategy": "OnWorkflowCompletion"},
            "ttlStrategy": {"secondsAfterSuccess": 3600, "secondsAfterFailure": 3600},
            "volumes": [{"name": "work", "persistentVolumeClaim": {"claimName": pvc}}],
            "templates": [
                {
                    "name": "render",
                    "securityContext": {"fsGroup": 100},
                    "container": {
                        "image": "lscr.io/linuxserver/ffmpeg:8.1.2-cli-ls76",
                        "imagePullPolicy": "IfNotPresent",
                        "resources": {
                            "requests": {"cpu": "4", "memory": "4Gi"},
                            "limits": {"cpu": "24", "memory": "24Gi"}
                        },
                        "command": ["sh", "-c"],
                        "args": [full_script],
                        "volumeMounts": [{"name": "work", "mountPath": "/work"}]
                    }
                }
            ]
        }
    }
    return wf


def main():
    record = load_record()
    wf = build_workflow_yaml(record)
    import yaml
    out_yaml = WORK / "not-your-monster-render.yaml"
    out_yaml.write_text(yaml.dump(wf, sort_keys=False), encoding="utf-8")
    print(f"Generated {out_yaml}")


if __name__ == "__main__":
    main()
