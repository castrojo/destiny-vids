# Delivery gates and headroom

Reference for [`../SKILL.md`](../SKILL.md). This is the delivery half of the
audio standard: **what gets measured, which gate fails, and how the shipped
file is brought under control without changing the mix**.

Declared masters, published paths, and any missing lossless-master rungs are
machine-recorded in `stories/megacut/delivery.json` and
`python3 tools/deliver.py status`; do not paste live act state into docs.

## Measure the whole folder, not the file you last fixed

A clipping master is invisible until something measures *it* — #82 was never
one act's bug, and a sweep over *every* file in `Prod/` found two more FLAC
masters over full scale that had passed for weeks. The correction is
`tools/peaks.py trim` — a derived static gain on the audio, picture stream
**copied** untouched, re-measured against the band — then
`tools/deliver.py publish` to re-link.

## Measure after the final lossy encode — and measure the master separately

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

## The delivered peak is what counts, not the bed's

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

**The programme itself has a lossless master**: FLAC in Matroska off the same
PCM segments and the same copied picture bitstream as the distribution `.mp4`,
in `~/Videos/Wolves/megacut/`.

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

## Prepending silent picture without touching source audio

A silent title sequence followed by source Opus does not require an audio
encode. Trim the audio packets first, then delay that trimmed stream while
muxing:

```bash
ffmpeg -copyts -i source.webm -ss 73 -to 468 \
  -c:a copy -avoid_negative_ts disabled trimmed.mka

first=$(ffprobe -v error -select_streams a -show_packets \
  -read_intervals '%+#1' -show_entries packet=pts_time -of csv=p=0 \
  trimmed.mka | head -1 | cut -d, -f1)

# offset = intro duration - $first
ffmpeg -copyts -i picture.mp4 -itsoffset 64.486 -i trimmed.mka \
  -map 0:v -map 1:a -c:v copy -c:a copy \
  -avoid_negative_ts disabled out.mkv
```

Use output-side `-ss` for the packet trim. Applying `-itsoffset` directly to
the original input can still be normalised by the mux, and `-shortest` then
ends the film after the audio's undelayed duration — silently dropping the
whole intro. FFmpeg documents `-copyts` as preserving input timestamps,
`-itsoffset` as adding to an input's timestamps, and `avoid_negative_ts` as a
mux-level timestamp shift; source: `/websites/ffmpeg_documentation`.

Verify both facts rather than trusting the command:

```bash
ffprobe -v error -select_streams a -show_packets -read_intervals '%+#1' \
  -show_entries packet=pts_time -of csv=p=0 out.mkv
ffmpeg -i trimmed.mka -map a:0 -f md5 -
ffmpeg -i out.mkv     -map a:0 -f md5 -
```

The first packet must land at the intro duration, and the decoded MD5 values
must match.

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
