# Audio standard

**This is the standard every delivered file in this project is held to** — the
thresholds, the sourcing rule, and the gates that enforce them. Companion to
[`production`](../production/SKILL.md) and [`scoring`](../scoring/SKILL.md).

**One line:** *impeccable audio, as the artist intended* — source the best
version that exists, keep the chain lossless, ship it unaltered.

The authority for *why* is the `audio-quality-tenet` skill; this file is the
project-specific part. The two tools that enforce it live in the delivery
workspace, because they are tools rather than policy:

```bash
cd ~/Videos
./audio-check.sh --all                  # standing report over Wolves/Prod/
./audio-check.sh --bed path/to/bed.wav  # is this the best source we could have?
./audio-source.sh --list <URL_OR_ID>    # show the ladder, fetch nothing
./audio-source.sh <URL_OR_ID> out.wav   # fetch the best rung + provenance
```

**Verify the upload before measuring it.** A plausible YouTube ID can resolve
to a different Nightwish video. Read the provenance file the fetch writes and
confirm its `title`, `video id`, and URL match the chosen recording; format 251
at 48 kHz proves source quality, not source identity. If it is wrong, remove
that exact fetched artifact and re-fetch before creating a bed record.

## The state of the show

Do not read it from a table here — every column has a machine record, and a
pasted copy is wrong the next time an act is rebuilt:

```bash
python3 tools/deliver.py status              # each act's declared master and its rungs
python3 tools/peaks.py measure <file>        # the delivered true peak
```

Bed provenance and rights live in `music/bed_*.json`; the act order is
[`docs/running-order.md`](../../running-order.md). The two acts with a known
gap are act I (quiet, +3.5 dB in the plan — #164; no committed builder — #159)
and act VI (no lossless master — #58).

**Measure the whole folder, not the file you last fixed.** A clipping master
is invisible until something measures *it* — #82 was never one act's bug, and
a sweep over *every* file in `Prod/` found two more FLAC masters over full
scale that had passed for weeks. The correction is `tools/peaks.py trim` — a
derived static gain on the audio, picture stream **copied** untouched,
re-measured against the band — then `tools/deliver.py publish` to re-link.

**Measure after the final lossy encode — and measure the master separately.**
Built from the *same* PCM segments with the *same* mix gain, a FLAC master
read −1.1 dBTP while its AAC copy read **+1.0** — about **2.1 dB** of
inter-sample overshoot the encoder reconstructs above the samples it was
given. So the programme carries **two** static gains, and the split is
deliberate: `master_gain_db` is the mix and both files carry it;
`distribution_gain_db` is headroom only the lossy leg needs. One shared gain
would either clip the copy or duck the master for nothing. Never `loudnorm`,
limiting, or compression. FFmpeg's `volume` filter accepts dB values, and
`ebur128=peak=true` measures true peak. Source:
`/websites/ffmpeg_documentation`.

**The programme itself has a lossless master** (issue #145): FLAC in Matroska
off the same PCM segments and the same copied picture bitstream as the
distribution `.mp4`, in `~/Videos/Wolves/megacut/`.

Measured on the files in `Wolves/Prod/`, not recalled. Every cut **except the
musical** has a lossless master behind it, and each master's audio is
**bit-exact with its source bed** — verified by comparing decoded stream MD5s,
never asserted. Act VI is the exception and is recorded as one:
`Prod/06-7daystothewolves.mp4` holds the best copy that exists rather than the
best possible.

**Gate the file you are actually shipping.** Act VII's *AAC deliverable*
measured −1.0 dBTP and passed for weeks while its FLAC master clipped at
**+0.3**: the gain correction had been applied to the lossy deliverable and
never to the master (#82). The gate belongs at the end of every build, the way
`run-final-hq.sh` ends with `tools/peaks.py trim`; adding it to the `scripts/`
builders is its own change because they are frozen by the delivery digest
(#167). A static gain shows in the measurements as exactly itself — LRA
unchanged at 11.3 LU, integrated loudness down by exactly the gain — and the
video stream MD5 untouched.

**Standalone builders call `peaks.trim_master_peak(out_path.resolve())` after
their final ffmpeg command.** The absolute path is essential when
`find_ffmpeg()` resolves to the containerized encoder: a relative staged
`.pretrim` input is not addressable inside the container. The gate copies the
video stream and applies one measured static audio gain, so it runs after
rendering and before `deliver.py publish`.

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

```
-f ba -S "acodec:opus,asr,abr"     # codec, then sample rate, then bitrate
--extractor-args "youtube:player_client=android_vr"
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

The `android_vr` extractor arg is load-bearing: the older documented
`player_client=android` workaround now returns only a 360p muxed format here.

## Rule 2 — decode at native rate, never resample

`audio-source.sh` decodes to 24-bit WAV at the source's own sample rate. A bed
that arrives at 48 kHz stays 48 kHz. A bed that arrives at 44.1 kHz is a
**sourcing** problem to fix at the source, not a resampling problem to paper
over.

## Rule 3 — headroom is a derived static gain, never a normaliser

Nothing here compresses, limits, EQs or loudness-normalises. The artist's
dynamics are the artist's. The only permitted correction is a **static scale**.

`tools/peaks.py::gain_for_headroom` (re-exported by `tools/redact.py`) derives
the trim from the bed's measured true peak. Source masters routinely run into
full scale — Rammstein's measures **+0.7 dBTP**, and the old MP3 of it **+1.5**
— so a bed that clips is normal and not a defect. `audio-check.sh` warns on it
rather than failing, because the pipeline's answer is the trim.

### The delivered peak is what counts, not the bed's

> A lossy encoder reconstructs inter-sample peaks **above** the samples it was
> given. A mix measuring −1.1 dBTP came back from AAC at **+0.3 dBTP** —
> clipping, from a chain that measured correct at every earlier step.

How much overshoot depends on the material: measured 0.2 dB on an MP3-sourced
bed, **1.5 dB** on a higher-bandwidth Opus one.

`redact.py` therefore measures the **delivered** file and re-runs at a
corrected static gain until it has real headroom. Corrections only ever go
*down*, and stop at the first safe result, because the overshoot is **not
monotonic** in the gain — measured here, gain 0.658 delivered −2.5 dBTP while
0.675 delivered −0.8. Chasing a narrow window on that curve oscillates and
costs a full render per attempt.

The FLAC master of the same cut lands on target in **one** pass, which is the
cleanest confirmation that the overshoot is the encoder and nothing else.

## What `audio-check.sh` enforces

Strictness is deliberately asymmetric: **warn on beds, fail on delivery.** A
questionable source may be the only one that exists; a bad deliverable is the
fault itself.

| Check | Bed | Deliverable |
|---|---|---|
| Sample rate ≠ 48 kHz | warn | **fail** (wrong rung) |
| No content above 16 kHz | warn | **fail** (came off a lossy low rung) |
| True peak ≥ −0.1 dBTP (clipping) | warn | **fail** |
| True peak above the −0.9…−1.1 band | warn | warn |
| No lossless master behind it | — | warn |
| LRA / integrated loudness | reported, so "dynamics untouched" is provable |

The brickwall test measures the >16 kHz band against a reference at 8 kHz. It
is calibrated on this repo's own known-bad/known-good pair — the two Kat
fetches of the *same song*, differing only in the rung:

| File | Ratio |
|---|---|
| `song-egLoz_DPQ8E.wav` (AAC 140, 44.1 kHz) | **−58.6 dB** — brickwalled |
| `song-egLoz_DPQ8E-opus48.wav` (Opus 251, 48 kHz) | **−34.2 dB** — full band |

24 dB of separation, so the threshold at −46 dB sits comfortably between them.

## Building a lossless master

Both are env overrides, so the **defaults still rebuild the shipped file** —
verified byte-for-byte by MD5. That is the contract for every per-cut render
script in `~/Videos/<project>/render/`: a default run reproduces what shipped,
and quality is an override rather than a rewrite.

```bash
# Guardian intro cuts
SURROUND=0 ACODEC=flac OUT=wolves-kat-reveal-hq.mp4 ./render/run-kat.sh

# the credited uncut build
ACODEC=flac scripts/build_uncut_credited.sh <video_id> <roster.json> <bed.wav>
```

Masters are **stereo**, matching Europa's: the 5.1 deliverable is *derived*
from stereo (FL/FR carry the original bit-exact, LFE is a low-passed sum at
−10 dB, FC/BL/BR are digital silence), so stereo is the real master and 5.1 is
a rendering of it. It is also what a Discord premiere or any other fold-down
wants.

**This is why the assembled programme is stereo**, and it was a decision rather
than an oversight. Every act in `Wolves/Prod/` is a stereo master; upmixing at
assembly to recreate the old 5.1 would be the megacut **inventing a soundfield**
out of two channels, which this standard forbids. If 5.1 delivery is wanted it
belongs in the per-cut scripts that already derive it. Recorded in
`stories/megacut/megacut.json`'s `_audio`.

## Verify, don't assert

Every claim above was measured on these files directly, and the commands are
cheap:

```bash
ffmpeg -i in.mp4 -af ebur128=peak=true -f null -     # true peak, LRA, LUFS
ffmpeg -i master.mp4 -map a:0 -f md5 -               # prove a master is bit-exact
ffmpeg -v error -xerror -i out.mp4 -f null -         # prove it is not truncated
```

Use `/home/linuxbrew/.linuxbrew/bin/ffmpeg`. The system `ffmpeg` is
`ffmpeg-free`: no H.264 decoder, and it fails only once decoding starts, which
reads like a corrupt input file.

Claims about yt-dlp's format selection were verified against current upstream
documentation (see the front matter's `context7-sources`), not recalled.
