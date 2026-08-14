# Audio standard for the Wolves cuts

Reference for [`docs/skills/production.md`](../production/SKILL.md). **This is the
standard every delivered file in this project is held to** — the thresholds, the
sourcing rule, and the two failures that have actually shipped from here.

It lived in `~/Videos/AUDIO.md` until 2026-08-12 and moved here when this repo
became the source of truth for the project's policy. `~/Videos` delivers files;
it does not decide standards. The **tools** it describes are still in that
workspace, because they are tools rather than policy:

**One line:** *impeccable audio, as the artist intended* — source the best
version that exists, keep the chain lossless, ship it unaltered.

The authority for *why* is the `audio-quality-tenet` skill. This file is the
part that is specific to this project: which rungs, which thresholds, what
has actually gone wrong here, and the two tools that enforce it.

```bash
cd ~/Videos
./audio-check.sh --all                  # standing report over Wolves/Prod/
./audio-check.sh --bed path/to/bed.wav  # is this the best source we could have?
./audio-source.sh --list <URL_OR_ID>    # show the ladder, fetch nothing
./audio-source.sh <URL_OR_ID> out.wav   # fetch the best rung + provenance
```

## The state of the show

Listed in the canonical act order — [`docs/running-order.md`](../../running-order.md)
owns it. Europa is act VII because the running order says so; it was previously
pinned last by a `zz-` filename prefix in the retired `~/Videos/UPLOAD/`, and
that convention is gone.

| Act | Cut | Bed source | In `Prod/` | True peak | Lossless master |
|---|---|---|---|---|---|
| II | Endless Forms Most Beautiful | Nightwish *Endless Forms Most Beautiful (Instrumental)* `6-9667CV1zQ`, **Opus 251** @48 k, static −1.6 dB into 32-bit PCM | FLAC stereo | −1.0 dBTP / −11.7 LUFS | `destiny-vids/renders/efmb-plated.mp4` |
| III | Contributors | Rammstein *Deutschland (Instrumental)* `WqaiHivKlsE`, **Opus 251** @48 k | FLAC stereo | −1.2 dBTP | `destiny-vids/renders/…-credited-hq.mp4` |
| IV | Kat | dArtagnan *Holding out for a Hero* `egLoz_DPQ8E`, **Opus rung 251** @48 k | FLAC stereo | −0.9 dBTP | `wolves-kat/wolves-kat-reveal-hq.mp4` |
| V | Natali | Nightwish *Shudder Before the Beautiful* `oTTITV4H9fo`, **Opus 251** @48 k | FLAC stereo | −1.0 dBTP | `wolves-natali/wolves-natali-arrival-shudder-bed-hq.mp4` |
| VI | The musical | Nightwish *7 Days to the Wolves* | AAC stereo 323 k | −1.6 dBTP | **none — issue #58** |
| VII | Europa | *Beauty Of The Beast* `X3WrCzLIIvk`, **Opus** @48 k | FLAC stereo | −1.1 dBTP (was **+0.3 — clipping**, issue #82) | `wolves-directors-cut/…-beauty-of-the-beast-hq.mp4` |

**Measure after the final lossy encode.** v2.4's lossless programme segments
were safe, but the joined AAC measured **+0.7 dBTP**. The fix is one derived
static gain at the final mux, followed by another measurement of the decoded
deliverable — never `loudnorm`, limiting, or compression. FFmpeg's `volume`
filter accepts dB values, and `ebur128=peak=true` measures true peak.
Source: `/websites/ffmpeg_ffmpeg-all`.

Measured on the files in `Wolves/Prod/` on 2026-08-13, not recalled. Every cut
**except the musical** has a lossless master behind it; each master's audio is
**bit-exact with its source bed**, verified by comparing decoded stream MD5s
rather than asserted. Act VI is the exception and is recorded as one:
`Prod/06-7daystothewolves.mp4` holds the best copy that exists rather than the
best possible.

**Act VII's FLAC master clipped**, and that is worth reading twice: the *AAC
5.1 deliverable* of the same cut measured −1.0 dBTP and passed for weeks. The
gain correction described below was applied to the lossy deliverable and never
to the master, and nothing measured the master until `--all` was pointed at
`Prod/`. **Check the file you are actually shipping.** The fix (issue #82) was
a derived static gain of 0.851 applied to the master by its own build —
`run-final-hq.sh` now ends with `tools/peaks.py trim`, which measures the
master and re-muxes it at the corrected gain, video stream copied untouched.
LRA stayed 11.3 LU and integrated moved −8.3 → −9.7 LUFS: exactly −1.4 dB
everywhere, which is what a static gain looks like. The video stream MD5 is
unchanged.

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

That mistake shipped once here, in Kat's bed, and was caught only by
after-the-fact analysis. Natali's storyboard then independently rediscovered
the same rule. Two hand-written rediscoveries of one rule is why it now lives
in `audio-source.sh`:

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
default sort is

```
… quality, res, fps, hdr:12, vcodec, channels, acodec, size, br, asr, proto, …
```

so **`acodec` is ranked ahead of `br`**, and within `acodec` the order is
`flac > wav > opus > vorbis > aac > mp4a > mp3` — Opus outranks AAC. The
bitrate-first behaviour that caused the original failure is the *legacy*
`ytdl_default` ordering, which puts `tbr` near the front, ahead of any codec
field. So this is a youtube-dl-compatible sort, or an explicit `-S abr`, not a
current default.

The explicit sort is pinned anyway: it is one line, it makes the intent
readable, and a default that shifts under you is exactly how the first failure
happened. Stated plainly rather than claiming the script fixes a break that is
currently latent.

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
the trim from the bed's measured
true peak. Source masters routinely run into full scale — Rammstein's measures
**+0.7 dBTP**, and the old MP3 of it **+1.5** — so a bed that clips is normal
and not a defect. `audio-check.sh` warns on it rather than failing, because the
pipeline's answer is the trim.

### The delivered peak is what counts, not the bed's

This bit is subtle and cost a real regression during this work:

> A lossy encoder reconstructs inter-sample peaks **above** the samples it was
> given. A mix measuring −1.1 dBTP came back from AAC at **+0.3 dBTP** —
> clipping, from a chain that measured correct at every earlier step.

How much overshoot depends on the material: the old MP3-sourced bed overshot by
0.2 dB, the higher-bandwidth Opus-sourced bed by **1.5 dB**. Deriving the gain
from the source fixed the old hardcoded-gain bug; it did not cover this one.

`redact.py` now measures the **delivered** file and re-runs at a corrected
static gain until it has real headroom. Corrections only ever go *down*, and
stop at the first safe result, because the overshoot is **not monotonic** in
the gain — measured here, gain 0.658 delivered −2.5 dBTP while 0.675 delivered
−0.8. Chasing a narrow window on that curve oscillates and costs a full render
per attempt.

The FLAC master of the same cut lands on target in **one** pass, which is the
cleanest confirmation that the overshoot is the encoder and nothing else.

## What `audio-check.sh` enforces

Strictness is deliberately asymmetric: **warn on beds, fail on delivery.** A
questionable source may be the only one that exists. A bad deliverable is the
fault itself, and both faults below have actually shipped from this folder.

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
verified byte-for-byte by MD5 for Kat. That is the contract for every per-cut
render script in `~/Videos/<project>/render/`: a default run reproduces what
shipped, and quality is an override rather than a rewrite.

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

Every claim above was measured, and the commands are cheap:

```bash
ffmpeg -i in.mp4 -af ebur128=peak=true -f null -     # true peak, LRA, LUFS
ffmpeg -i master.mp4 -map a:0 -f md5 -               # prove a master is bit-exact
ffmpeg -v error -xerror -i out.mp4 -f null -         # prove it is not truncated
```

Use `/home/linuxbrew/.linuxbrew/bin/ffmpeg`. The system `ffmpeg` is
`ffmpeg-free`: no H.264 decoder, and it fails only once decoding starts, which
reads like a corrupt input file.

## Sources

Technical claims about format selection were verified against current upstream
documentation rather than recalled:

- `/yt-dlp/yt-dlp` — default `--format-sort` field order and the `acodec`
  preference list (`yt_dlp/utils/_utils.py`, README "Sorting Formats").

Everything about true peak, encoder overshoot and the fold-down was measured on
these files directly; the commands are above.
