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

## Auditioning a change without a rebuild

A music note — "try the vocal version", "start the bed at 7:45" — does not
need the act's builder, which can cost minutes to hours. Remux the
**delivered** act: picture stream-copied, only the audio decoded and re-laid:

```bash
ffmpeg -y -i ~/Videos/Wolves/Prod/<act>.mp4 \
  -ss <start> -t <dur> -i "song-source.webm" \
  -map 0:v -c:v copy -map 1:a -c:a flac \
  -movflags +faststart ~/Videos/Wolves/preview/<name>.mp4
```

FLAC at the native 48 kHz keeps the audition on the same lossless footing as
Prod itself; verify duration and streams with ffprobe before showing it. The
sidecar lands in `preview/` — never overwrite Prod for an audition, because
Prod's entries are hardlinks to declared masters.

If the audition is approved, promotion is: overwrite the act's declared master
in place (`cp` preserves the inode, so the Prod hardlink sees the new content
immediately), then `python3 tools/deliver.py publish --act <N>` to regenerate
CHECKSUMS.md5 and the README table, then rebuild the social copy with
`tools/social.py` (it rewrites the copy's `.source.md5` itself). **The record
amendment is part of the same change, not a follow-up to skip**: until the
act's committed record describes the new audio, the builder still produces the
old mix and a rebuild silently reverts the promotion. Record that gap in the
record's `unresolved` the moment the promotion ships.

Casting the audition to the owner's screen is `catt -d "<device>" cast <file>`.
An `UnsupportedNamespace: ... com.google.cast.media is not supported by
current app` error means a stuck receiver app, not a bad file:
`catt -d "<device>" stop`, then re-cast with `--force-default`.

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
- Treating a meter as a content detector: on a dense metal mix the 300–3400 Hz
  band ratio, 2.5–7 Hz envelope modulation (a ~161 bpm track's drums sit
  inside that band) and autocorrelation pitch salience all read instrumental
  and sung passages alike. "Where are the vocals" is answered by an ear —
  render a probe clip and ask.
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
`ffmpeg-free`: no H.264 decoder, and it fails only once decoding starts, which
reads like a corrupt input file.

Claims about yt-dlp's format selection were verified against current upstream
documentation, not recalled.
