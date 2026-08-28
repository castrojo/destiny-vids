# Source quality and provenance

Reference for [`../SKILL.md`](../SKILL.md). This is the sourcing half of the
audio standard: **which rung to fetch, what "lossless" means here, and what
must be checked before a bed is trusted**.

## Verify the upload before measuring it

A plausible YouTube ID can resolve to a different Nightwish video. Read the
provenance file the fetch writes and confirm its `title`, `video id`, and URL
match the chosen recording; format 251 at 48 kHz proves source quality, not
source identity. If it is wrong, remove that exact fetched artifact and
re-fetch before creating a bed record.

## The honest caveat: "lossless" here is relative

**Every** bed in this show originates from a YouTube Opus rung. None comes from
a CD, a purchase, or a lossless distribution. A FLAC master is therefore
lossless *relative to that Opus source* — it guarantees no **further**
generation loss. It is not lossless provenance, and nothing here should be
described as if it were.

That still matters: it means a fold-down for streaming, a container change, or
a re-encode starts from the bed rather than from a lossy deliverable.

## Rule 1 — source by codec, never by bitrate

`yt-dlp` selecting on raw bitrate picks **format 140 (AAC, 130 k, 44.1 kHz,
brickwalled at ~15 kHz)** over **format 251 (Opus, 118 k, 48 kHz, full band)**,
purely because 130 > 118. The AAC rung is audibly worse and forces a needless
44.1→48 kHz resample at render.

That mistake has shipped from here, and been independently rediscovered once —
which is why the rule now lives in `audio-source.sh` rather than in memory:

```bash
-f ba -S "acodec:opus,asr,abr"     # codec, then sample rate, then bitrate
--extractor-args "youtube:player_client=visionos"
```

Reproduced on the exact track that got it wrong:

| Sort | Selected |
|---|---|
| `-S abr` (bitrate first) | 140 · mp4a · **44100 Hz** |
| `-S acodec:opus,asr,abr` | 251 · opus · **48000 Hz** |

**Current yt-dlp picks 251 by default too, and it is worth knowing why.** Its
default sort ranks **`acodec` ahead of `br`**, and within `acodec` the order
is `flac > wav > opus > vorbis > aac > mp4a > mp3` — Opus outranks AAC. The
bitrate-first behaviour is the *legacy* `ytdl_default` ordering, which puts
`tbr` near the front, ahead of any codec field. So the danger is a
youtube-dl-compatible sort, or an explicit `-S abr`, not a current default.
The explicit sort is pinned anyway: a default that shifts under you is exactly
how the first failure happened.

The extractor arg is load-bearing, and **which** client is load-bearing has
moved twice: the older documented `player_client=android` returns only a 360p
muxed format, and `android_vr` now warns that its "https formats require a GVS
PO Token which was not provided. They will be skipped" — leaving the same
single muxed 360p/44.1 kHz AAC rung, which is exactly the sourcing failure
rule 1 exists to prevent. Measured on yt-dlp 2026.08.19, `player_client=visionos`
still lists the full video-only AVC and non-DRC 48 kHz Opus ladder with no
token, and is what yt-dlp's own default order resolves to here:

```bash
--extractor-args "youtube:player_client=visionos"
```

Check the ladder with `-F` before trusting any client: a client that has been
degraded does not error, it just stops listing the good rungs.

## Rule 2 — decode at native rate, never resample

`audio-source.sh` decodes to 24-bit WAV at the source's own sample rate. A bed
that arrives at 48 kHz stays 48 kHz. A bed that arrives at 44.1 kHz is a
**sourcing** problem to fix at the source, not a resampling problem to paper
over.
