---
name: scoring
version: "1.3"
last_updated: "2026-08-12"
id: scoring
one_line_purpose: Measure a music bed, cut sections out of it, and cut to its bars.
entry_point: docs/skills/scoring.md
category: editing
mcp_compliance_level: partial
optimization_status: draft
status: active
dependencies: [editing]
tags: [music, bed, tempo, downbeat, excision, anchor, ffmpeg, true-peak, section-detection, two-clocks, bed-pause, diegetic-insert, insert-headroom, source-gain]
description: >-
  Covers bed records, bar-snapped excisions, the cached grid, named anchors, a bed that pauses mid-cut, and a master over 0 dBTP.
  Use when scoring a cut, pausing the song for a moment of source audio, or supporting a second recording.
metadata:
  type: procedure
  context7-sources:
    - /librosa/librosa
    - /websites/ffmpeg_documentation
---

# Scoring a cut to a bed

## When to Use

- Replacing a cut's audio with a chosen track
- Cutting a section out of that track
- Landing a specific shot at a specific moment in the music
- Finding where a section (a gallop, a solo, a break) actually starts
- Supporting more than one recording of the same song
- A delivered file whose true peak is above 0 dBTP
- The song must pause, duck, or start late over picture already running

## When NOT to Use

- Sourcing the best copy of a track, or any mixing/mastering question →
  the `audio-quality-tenet` and `scoring-cuts-with-replacement-music` skills
- Assembling the picture, marking material for removal → [`editing.md`](editing.md)

## Core Process

1. **Measure** the bed. Never take a duration from a search result.
2. **Check the metrical level** before trusting the tempo (see below).
3. **Excise** any unwanted section — it snaps to bar lines.
4. **Map** the anchor timecode between the source and edited timelines.
5. **Render** the edited bed, lossless.

```bash
python3 tools/bed.py measure media/<bed>.wav --id <bed_id> \
    --beat-multiple 2 --source-url <url> --title <t> --artist <a>
python3 tools/bed.py excise music/<bed_id>.json --from 2:59 --to 3:12
python3 tools/bed.py render music/<bed_id>.json --out renders/bed-edited.wav
python3 tools/bed.py map music/<bed_id>.json --at 3:48 --edited
```

## The bed record

A bed gets a record in `music/<bed_id>.json`, which is to a track what
`videos/<video_id>.json` is to a source video: provenance plus measurements,
**never the media**. Same rights posture — `usage_class` and
`source_rights_note` on every record.

## The grid is cached on purpose

`measure` writes the tempo, the beats and the downbeat phase into the record,
and everything afterwards reads *that* rather than re-analysing.

This is a **correctness requirement, not an optimisation**. Beat tracking is a
heuristic; a library upgrade can shift the downbeat phase by a beat, and every
cut in a finished piece would move with it. Committing the grid makes a
re-render reproducible, and keeps the suite offline — `librosa` is needed only
to *create* a record, exactly as `scenedetect` is needed only to index a video.

### Check the metrical level before trusting the tempo

Beat trackers routinely lock onto double time. This bed reports **161.5 bpm**
for a song that is felt at **80.75**, and snapping to the fast grid snaps to
half-bars — a weaker boundary that reads as choppy.

`--beat-multiple 2` keeps every other beat and picks the stronger phase. It is
a deliberate operator choice because getting it wrong is not subtle, and no
heuristic beats listening once. Both the raw detection and the chosen level stay
in the record:

```json
"detected_tempo_bpm": 161.499,
"beat_multiple": 2,
"tempo_bpm": 80.75,
"bar_sec": 2.9722
```

A tempo outside roughly 60–160 bpm, or one exactly double what you tapped, is
the tell.

### `beat_track` returns tempo as an array, and the official example is stale

librosa's own tutorial still prints the tempo like a scalar:

```python
tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
print('Estimated tempo: {:.2f} beats per minute'.format(tempo))   # raises
beat_times = librosa.frames_to_time(beat_frames, sr=sr)
```

`source: /librosa/librosa` (tutorial quickstart)

On **librosa 0.11.0** that `format` call raises
`TypeError: unsupported format string passed to numpy.ndarray.__format__`,
because `tempo` is now `ndarray` of shape `(1,)`. Verified on this host, not
inferred. Take it as `float(np.atleast_1d(tempo)[0])`.

The wider lesson is why the tempo is *not* trusted for the bar length here:
`bar_sec` is derived from the median tracked beat interval instead, so the
reported tempo and the grid can never disagree.

## Finding a section boundary: measure it, don't take it from a tracklist

"When the gallop starts" and "when the flute comes in" are directions, not
timecodes, and a tracklist will not give you them. Measure the bed's own
structure in short windows and read the shape:

```python
rms  = librosa.feature.rms(y=y, hop_length=512)[0]
cent = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=512)[0]
flat = librosa.feature.spectral_flatness(y=y, hop_length=512)[0]
H, P = librosa.effects.hpss(y)      # harmonic vs percussive
```

What each one tells you, with the readings that identified them on the Nightwish
bed:

| Signal | What it means |
|---|---|
| **Centroid collapses** (2500 Hz → **768 Hz**) with **flatness ~0.0005** | a palm-muted low riff and nothing else — a gallop |
| **Percussive RMS drops out** for a window, then everything re-enters | a break, and the strongest "the beat changes again" candidate |
| **Mid band (700–2500 Hz) takes over** from the low band | a melodic lead instrument — whistle, pipe, flute |
| RMS rises and stays up | a new section, but a weak boundary on its own |

Split harmonic from percussive before reading the bands, or a cymbal wash reads
as a flute. A boundary you cannot see in *two* of these is probably not one.

Then snap the answer to a downbeat — never anchor to the literal timecode.

## Named anchors beat literal timecodes

A cut scored to a bed should refer to **musical events by name**, not to seconds:

```json
"anchors": { "act2_gallop_in": 182.834, "act3_flute_change": 259.390 }
```

Two things get easier, and both are otherwise expensive:

- **A second recording of the same song is a different timeline.** An
  instrumental or orchestral version is not the album take with parts muted:
  the arrangement, the length and the position of every section differ. A cut
  anchored to `3:04` is correct on exactly one recording; a cut anchored to
  `act2_gallop_in` is correct on all of them, once each record maps the name.
- **Re-sourcing the bed becomes a re-anchor, not a re-cut.** Codec rungs decode
  with different leading padding, so a better source silently moves every
  literal timecode (see below).

Placing an anchor is a listening judgement. Snap it and record it; never let a
detector guess where the gallop starts.

## Record what you measured about the source

A bed record holds provenance and measurements, so the audio checks belong in it
rather than in someone's memory:

```json
"source_format": "opus 48kHz stereo (yt-dlp format 774), decoded once to pcm_s24le",
"spectral_cutoff_hz": 19000,
"spectral_note": "real content to ~19 kHz, Opus lowpass above 20.5 kHz; not a low-rate re-encode"
```

Measure the cutoff before cutting anything to the bed. A ruler-flat brickwall
well below ~20 kHz means the upload was made from a lossy file, and decoding it
to 24-bit does not undo that. Writing the number down is what stops the next
person re-measuring — or worse, not measuring.

**Say so when the source is not the best available.** An official artist upload
is still lossy and is not "the highest-quality upstream version". That is fine
for a prototype and must be recorded as a known gap, not quietly shipped.

## A loud master can exceed 0 dBTP, and the fix is a static gain

Modern and loudness-war-era masters routinely decode above full scale. Measured
on a 2007 metal master: **+2.1 dBFS true peak, −6.8 LUFS integrated, LRA 3.3**.

The correction is a **static gain at the mux** — nothing else:

```bash
ffmpeg -i cut.mp4 -i bed.wav -map 0:v:0 -map 1:a:0 -c:v copy \
    -af "volume=-3.5dB" -c:a aac -b:a 320k -ar 48000 -shortest out.mp4
```

`-c:v copy` matters: the picture is not re-encoded, so the gain pass costs one
audio encode and no generation loss on video. A static gain scales every sample
identically, so the LRA and every dynamic relationship the artist chose are
untouched — which is exactly what `loudnorm`, a compressor or a limiter would
change. Re-measure the **delivered** file afterwards, not the intermediate.

## Excisions are snapped to bar lines

`excise` moves both endpoints to the nearest downbeat before recording them:

```text
requested 2:59.000 -> 3:12.000
snapped   2:59.281 -> 3:11.379  (+0.281s / -0.621s)
removes   12.098s = 4 bars
```

**Cutting an arbitrary span lands mid-bar.** The music stumbles, and every
downbeat after the splice sits at a new phase, so a single (tempo, offset) pair
no longer describes the timeline — you would need two grids joined at a
discontinuity, and every consumer would need to know about it.

Removing a **whole number of bars** is exactly the condition under which the
grid continues in phase across the splice. One grid, no special case. The suite
asserts it on both a synthetic grid and the real record: bar gaps either side of
the splice match the median.

Bars are counted **by index**, not by dividing the span by the median bar.
Tracked downbeats jitter, so four real bars measure 4.07 median bars, and
reporting that would suggest a fractional excision where the cut is exactly four
bars of music.

An excision that **overlaps one already recorded is refused**, naming the
excision it collides with — including an exact re-run of the same `excise`. The
rendered bed would survive an overlap (the filter coalesces spans), but
`edited_duration` and the timeline mapping sum `removed_sec` blindly, so a
double-counted span desyncs every anchor from the audio with no error anywhere.
Two excisions that merely touch at a bar line share no audio and are fine.

## Mapping between the two timelines

Once a section is gone there are two clocks, and confusing them silently moves
the anchor:

```console
$ python3 tools/bed.py map music/<bed>.json --at 3:48 --edited
edited 3:48.000  ->  source 4:00.098
  nearest edited downbeat 3:47.556 (-0.444s)
  5.114s from the end
```

`--edited` reads the argument on the edited timeline; without it, on the source.
A source moment **inside** an excision maps to `None` and the command exits
non-zero — it has no edited position, and returning a neighbouring one would be
a lie an anchor could be built on.

Anchor to `nearest edited downbeat`, not to the literal timecode: "every
boundary is bar-aligned" and "this shot starts at exactly 228.000s" do not
compose, because 228.000 is on a bar line only by coincidence.

## Keep the chain lossless

`render` concatenates the surviving spans **at the source's own codec, sample
rate and bit depth** — a 24-bit source that comes back 16-bit has been quietly
mastered. No EQ, no normalisation, no resample: cutting a section out of a bed
is an edit, not a mastering pass.

Prefer a copy already in the project over a fresh download. The Nightwish bed
existed at 24-bit in `~/Videos/wolves-natali/sources/`; a re-fetch produced
16-bit for the same YouTube id.

## Two clocks: when the bed does not run end to end

`render.py --audio` lays one file over a finished cut, which is right whenever
the song plays from first frame to last. Two things it cannot express, and both
are the same mechanic:

- a **pre-roll** — the film opens on its own source audio and the song enters
  later, over picture that is already running;
- a **pause** — the song stops, a moment plays in its own audio, and the song
  resumes *from where it stopped*.

`tools/audiomix.py` handles both by giving the cut two clocks:

> **`wall` is position in the film; `bed` is position in the song. A shot
> marked `audio: "source"` advances wall and not bed.**

Everything follows from that — including the fact that a musical with a pause
in it is **longer than its own song**, which is why every anchor in an authored
builder must be asserted against *bed* time, never wall time.

```bash
python3 tools/audiomix.py stories/<name>.json --video renders/<name>-picture.mp4 \
    --bed media/<bed>.wav --bed-offset 20.166 --bed-gain-db -3.5 \
    --out renders/<name>.mp4
```

The bed is cut into as many pieces as there are gaps, each delayed to its wall
position, and the source audio is muted wherever the bed plays. **Nothing is
mixed on top of anything**: at every instant exactly one of the two is audible.
That is what "pause the song" means, and it is not what ducking would do — a
dense, heavily-limited master has to come down so far to sit under dialogue or
an action hit that it is a stop with mud on top.

**Choose the pause point by measuring the bed, not by taste.** Scan for
full-band drops and put the seam in one: *7 Days to the Wolves* has exactly one
interior silence in 424 s (278.64 → 279.64 s, ending 23 ms before a downbeat),
and a stop placed there costs the music nothing because the artist already
stopped. Where no natural gap exists, snap the seam to a downbeat so the resume
lands on a bar.

Verify it landed, rather than trusting the filtergraph: correlate the delivered
audio against the bed at a known offset. A bed region should return `+1.000`,
and a paused region should return roughly `0.000`.

## A diegetic insert has to be allowed to end

When the bed pauses for a moment of source audio, the out-point belongs to
**that moment's own phrase**, not to the shot or to a round number. Cut back to
the song while the insert is still in the air and it reads as a dropout rather
than a decision — the moment starts and does not finish.

Find the out-point by measuring the insert's envelope and taking its resolution
(its quietest point after the last swell), the same way the bed's own gaps are
found. A pause under ~3 s rarely reads as deliberate at all.

If a note says the moment is *in the right place* but wrong somehow, change the
**length**, not the position. Those are separate faults and the in-point is
usually the part that was already right.

### ...and it brings its own peaks

An insert is somebody else's mix. Its peaks are not yours to have planned for,
and they are measured on a region far too short to move the film's integrated
loudness — so a cut whose bed sits comfortably under the headroom gate can be
pushed over it by one explosion, and the *whole-file* number is the only place
you will see it.

Measured on an 8.7 s insert in a 432 s film:

```text
whole file          -1.6 -> -0.4 dBTP   over the -1.0 gate
  bed region        -3.2 dBTP           fine, and unchanged
  insert region     -0.4 dBTP           the culprit, 8.7s of 432
```

**Measure per region, not just per file.** The fix is the same static gain the
bed already gets, applied to the insert regions only — `tools/audiomix.py
--source-gain-db`, the mirror of `--bed-gain-db`. Pulling the *whole* film down
would work too and is worse: it quietly re-levels music whose gain was already
decided and documented.

Do not reach for a limiter here. The insert's dynamics are the reason it is in
the film.

### And check the insert is actually audible

A source-audio region is the one part of a cut where a silent input fails
**silently**: the bed is muted there by design, so a missing audio track sounds
exactly like a working pause until somebody plays it. It happened here —
`yt-dlp -f 401` is video-only, so the insert rendered as digital silence and
every anchor, duration and sync check still passed.

```python
# the pause must be LOUD, not just present
rms = 20*log10(rms(pcm(out, pause_in, pause_len)))   # -240 dB is the bug
```

Assert a floor on the region's RMS, and assert its correlation against the bed
is ~0. The first catches a silent insert; the second catches the bed leaking
into a region that was supposed to be a pause. Neither is implied by the other.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "The tempo detector said 161, so it's 161." | It locked onto double time. Check `--beat-multiple 2` before anything is cut to it. |
| "I'll just cut the 13 seconds the owner asked for." | Mid-bar, that stumbles *and* re-phases the grid. Snap to bars; 12.098s is what four bars actually measure. |
| "I'll re-run the analysis at render time, it's the same audio." | Beat tracking is a heuristic. A different answer silently moves every cut. |
| "3:48 is 3:48." | Not once a section is gone. Edited 3:48 is source 4:00.098 here. |
| "The tracklist says the bridge is at 4:20." | A tracklist is not a measurement. Read the centroid, the flatness and the percussive RMS, and confirm the boundary in two of them. |
| "The instrumental is the album take with the vocals muted." | It is a different arrangement with a different length. Anchor by name and map each recording separately. |
| "True peak is over, I'll run loudnorm." | That rewrites the artist's dynamics. A static gain at the mux fixes the peak and changes nothing else. |
| "I measured the peak on the bed, so the delivery is fine." | Measure the delivered file. The encode adds intersample peaks the WAV did not have. |

## Red Flags

- An anchor asserted against wall time in a cut whose bed pauses. Bed time is
  the only clock the music knows.
- A source-audio insert cut to a round number rather than to its own phrase.
- Ducking a dense master under dialogue or an action hit instead of pausing it.

- A tempo exactly double the one you can tap
- An excision whose `removed_bars` is not a whole number
- A rendered bed whose bit depth or sample rate differs from the source
- Anchoring to a literal timecode on a bar-aligned cut
- Re-analysing a bed that already has a cached grid
- A bed record with no measured spectral cutoff
- A section boundary taken from a tracklist rather than measured
- `loudnorm`, a compressor or a limiter anywhere near a finished master

## Verification

```bash
python3 -m pytest -q tests/test_bed.py

# duration is source minus every excision
ffprobe -v error -show_entries format=duration -of csv=p=0 renders/bed-edited.wav

# no truncation or corruption, and nothing clipped
ffmpeg -v error -xerror -i renders/bed-edited.wav -f null -
ffmpeg -hide_banner -nostats -i renders/bed-edited.wav -af volumedetect -f null - 2>&1 |
  grep max_volume
```

Proving a bed is genuinely instrumental — measure the vocals stem, never trust
the title — is `scoring-cuts-with-replacement-music`. This bed measures
−32.2 dBFS on the vocals stem with 80% of that energy in 500 Hz–2 kHz and only
10.6% above 4 kHz, which is melodic leakage rather than a voice; the outro
window measures −56.1 dBFS.
