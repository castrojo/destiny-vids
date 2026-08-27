#!/usr/bin/env python3
"""Build the clean, non-act Excision connective segment."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import farm, peaks, redact, render  # noqa: E402

MEDIA_DIR = REPO_ROOT / "media"
DEFAULT_OUT = REPO_ROOT / "renders" / "excision" / "excision-clean.mp4"

BEATS = [
    {
        "segment_id": "excision-rally",
        "video_id": "yt_excision_chezvii_4k",
        "start_sec": 40.0,
        "end_sec": 92.5,
        "start_tc": "0:40.000",
        "end_tc": "1:32.500",
        "beat": "The defenders of Sol rally for the last battle",
        "redactions": True,
    },
    {
        "segment_id": "excision-ward-of-dawn",
        "video_id": "yt_excision_nohud_hoople",
        "start_sec": 476.0,
        "end_sec": 496.0,
        "start_tc": "7:56.000",
        "end_tc": "8:16.000",
        "beat": "Saint-14's Ward of Dawn holds the line",
    },
    {
        "segment_id": "excision-unmake-the-witness",
        "video_id": "yt_excision_nohud_hoople",
        "start_sec": 938.0,
        "end_sec": 1018.0,
        "start_tc": "15:38.000",
        "end_tc": "16:58.000",
        "beat": "The fireteam channels the Traveler and unmakes the Witness",
    },
]


def film_duration():
    return sum(beat["end_sec"] - beat["start_sec"] for beat in BEATS)


def clip_command(ffmpeg, beat, source, out):
    duration = beat["end_sec"] - beat["start_sec"]
    command = render._cut_argv(
        ffmpeg, source, beat["start_sec"], duration, out, keep_audio=True
    )
    if beat.get("redactions"):
        filters = redact.drawbox_filters(
            redact.load_redactions(beat["video_id"])["redactions"]
        )
        vf_index = command.index("-vf") + 1
        command[vf_index] = ",".join([command[vf_index], *filters])
    return command


def concat_command(ffmpeg, list_path, out, audio_gain=None):
    command = render._concat_argv(
        ffmpeg, list_path, out, audio_gain=audio_gain
    )
    command[-1:-1] = ["-r", "60000/1001", "-fps_mode", "cfr"]
    return command


def _index_segment_id(beat):
    return (
        f"seg_{beat['video_id']}_"
        f"{int(beat['start_sec']):04d}-{int(beat['end_sec']):04d}"
    )


def validate_clean_gate():
    results = []
    for beat in BEATS:
        segment_id = _index_segment_id(beat)
        path = REPO_ROOT / "segments" / f"{segment_id}.json"
        segment = json.loads(path.read_text(encoding="utf-8"))
        if segment.get("clean"):
            results.append(f"{segment_id}: clean")
            continue
        if beat.get("redactions"):
            acknowledgements = {
                acknowledged
                for item in redact.load_redactions(beat["video_id"])["redactions"]
                for acknowledged in item.get("acknowledges", [])
            }
            if segment_id in acknowledgements:
                results.append(f"{segment_id}: redacted")
                continue
        raise ValueError(
            f"{segment_id} is not clean and has no acknowledged redaction"
        )
    return results


def _sources():
    resolved = {}
    for beat in BEATS:
        video_id = beat["video_id"]
        if video_id in resolved:
            continue
        source = render.resolve_media(video_id, MEDIA_DIR)
        if source is None:
            raise FileNotFoundError(f"missing media for {video_id} in {MEDIA_DIR}")
        resolved[video_id] = source.resolve()
    return resolved


def _chain(ffmpeg, tmp, out, sources, audio_gain=None):
    clips = []
    commands = []
    for index, beat in enumerate(BEATS, 1):
        clip = tmp / f"clip_{index:03d}{render.INTERMEDIATE_SUFFIX}"
        clips.append(clip)
        commands.append(
            clip_command(ffmpeg, beat, sources[beat["video_id"]], clip)
        )

    list_path = tmp / "concat_list.txt"
    commands.append(concat_command(ffmpeg, list_path, out, audio_gain))
    list_content = "".join(f"file '{clip}'\n" for clip in clips)
    return commands, list_path, list_content


def build(out=DEFAULT_OUT, local=False, target_dbtp=peaks.DEFAULT_TARGET_DBTP):
    out = Path(out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    validate_clean_gate()
    sources = _sources()
    if local:
        use_farm, why = False, "--local given"
    else:
        use_farm, why = farm.cluster_available()
    if use_farm:
        print("excision: cluster reachable; encoding on the farm")
    else:
        print(f"excision: encoding on THIS host -- {why}")

    ffmpeg = render.find_ffmpeg()
    with tempfile.TemporaryDirectory(
        dir=out.parent, prefix=".build-excision-"
    ) as tmp_name:
        tmp = Path(tmp_name)

        def run(audio_gain=None):
            launcher = ["ffmpeg"] if use_farm else ffmpeg
            commands, list_path, list_content = _chain(
                launcher, tmp, out, sources, audio_gain
            )
            if use_farm:
                farm.run_ffmpeg_chain_on_cluster(
                    commands,
                    inputs=list(sources.values()),
                    out=out,
                    tmp_prefix=tmp,
                    text_files={list_path: list_content},
                    expected_duration=film_duration(),
                    label="Excision clean cut",
                )
                return

            list_path.write_text(list_content, encoding="utf-8")
            for command in commands:
                farm.run_capped_local(
                    command,
                    reason="the Excision farm is unavailable",
                    check=True,
                )

        run()
        if target_dbtp is not None:
            peaks.correct_delivered_peak(
                out,
                1.0,
                target_dbtp,
                run,
                ffmpeg=ffmpeg,
                attempts=5,
                margin_db=peaks.DELIVERED_BAND_MARGIN_DB,
            )
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--local", action="store_true")
    args = parser.parse_args(argv)
    out = build(args.out, local=args.local)
    print(f"OK: {film_duration():.1f}s -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
