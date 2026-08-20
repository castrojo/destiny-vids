---
name: audio
version: "1.0"
last_updated: "2026-08-19"
id: audio
one_line_purpose: Preserve source fidelity and enforce delivery audio headroom.
entry_point: docs/skills/audio/SKILL.md
category: media-production
status: active
dependencies: []
tags:
  - audio
  - delivery
  - source
  - headroom
  - ffmpeg
description: >-
  Preserve source fidelity and enforce delivery audio headroom. Use when
  sourcing a bed, measuring a deliverable, or deciding whether a file meets the
  repo's audio standard.
metadata:
  type: policy
  context7-sources:
    - /websites/ffmpeg_documentation
---

# Audio standard

**This is the standard every delivered file in this project is held to** — the
thresholds, the sourcing rule, and the gates that enforce them. Companion to
[`production`](../production/SKILL.md).

**One line:** *impeccable audio, as the artist intended* — source the best
version that exists, keep the chain lossless, ship it unaltered.

The authority for *why* is the `audio-quality-tenet` skill; this file is the
project-specific part.

## When to Use

- Choosing or fetching a music bed
- Checking whether a bed came from the right rung
- Measuring a delivered act or programme
- Deciding whether a master or AAC copy needs headroom correction

## When NOT to Use

- Delivering a finished file through the workspace graph →
  [`production`](../production/SKILL.md)
- Getting ffmpeg working on an atomic host → [`../../rendering.md`](../../rendering.md)

## The three rules

1. **Source by codec, never by bitrate.** Prefer the native-rate Opus rung over
   a numerically higher but worse AAC one; the full ladder, the exact `yt-dlp`
   sort, and the provenance caveat are in
   [`references/source-quality.md`](references/source-quality.md).
2. **Decode at native rate, never resample.** A 44.1 kHz fetch is a sourcing
   problem to fix at the source, not something to paper over downstream.
3. **Headroom is a derived static gain, never a normaliser.** No EQ,
   compression, limiting or `loudnorm`; only a measured static trim on the file
   that is actually shipping. The delivery loop lives in
   [`references/delivery-gates.md`](references/delivery-gates.md).

## Shortest command path

```bash
cd ~/Videos
./audio-source.sh --list <URL_OR_ID>    # inspect the ladder, fetch nothing
./audio-source.sh <URL_OR_ID> out.wav   # fetch the best rung + provenance
./audio-check.sh --bed out.wav          # gate the source
./audio-check.sh --all                  # gate Wolves/Prod
```

## Read current state from records, not prose

Live delivery state does not belong in this skill. Read the machine record:

```bash
python3 tools/deliver.py status
python3 tools/peaks.py measure <file>
```

Bed provenance and rights live in `music/bed_*.json`; declared masters and
their published paths live in `stories/megacut/delivery.json`; act order lives
in [`../../running-order.md`](../../running-order.md).

## Where the detail lives

This skill is the contract. The detail lives in `references/`:

| Reference | What is in it |
|---|---|
| [`source-quality.md`](references/source-quality.md) | Source-rung selection, native-rate decoding, provenance checks, and the "lossless relative to the source" caveat. |
| [`delivery-gates.md`](references/delivery-gates.md) | True-peak behaviour, AAC overshoot, `audio-check.sh`, peak trimming, and lossless-master builds. |

## Red Flags

- Sorting by bitrate (`-S abr`, legacy `ytdl_default`, or equivalent) and
  taking AAC 140 over Opus 251.
- Trusting a plausible YouTube ID because it fetched 48 kHz audio, without
  reading the provenance file it wrote.
- Resampling a 44.1 kHz bed to 48 kHz instead of re-sourcing it.
- Describing a FLAC master as provenance-lossless rather than **lossless
  relative to the fetched source**.
- Measuring only the bed or only the FLAC master; the delivered AAC is the
  file that overshoots.
- Shipping after `audio-check.sh --bed` while skipping
  `./audio-check.sh --all`.
- Using `loudnorm`, limiting, compression, EQ, or any non-static processing.
- A standalone builder that never calls
  `peaks.trim_master_peak(out_path.resolve())` after its final ffmpeg command.

## Verification

```bash
./audio-source.sh --list <URL_OR_ID>         # inspect the rung ladder first
./audio-check.sh --bed <bed.wav>             # source gate
./audio-check.sh --all                       # delivery gate over Wolves/Prod
python3 tools/peaks.py measure <file>        # delivered true peak
ffmpeg -i <master>.mp4 -map a:0 -f md5 -     # prove a master is bit-exact
```

Use `/home/linuxbrew/.linuxbrew/bin/ffmpeg`. The system `ffmpeg` is
`ffmpeg-free`: no H.264 decoder, and it fails only once decoding starts.
