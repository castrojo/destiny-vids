---
name: scoring
version: "1.0"
last_updated: "2026-08-11"
id: scoring
one_line_purpose: Measure a music bed, cut sections out of it, and cut to its bars.
entry_point: docs/skills/scoring.md
category: editing
mcp_compliance_level: partial
optimization_status: draft
status: active
dependencies: [editing]
tags: [music, bed, tempo, downbeat, excision, anchor, ffmpeg]
description: >-
  Covers bed records, bar-snapped excisions, the cached beat grid, and mapping a
  timecode between the source and edited timelines. Use when scoring a cut to a
  chosen track, removing a section from a bed, or landing a shot on a musical
  moment.
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

## When NOT to Use

- Sourcing the best copy of a track, or any mixing/mastering question →
  the `audio-quality-tenet` and `scoring-cuts-with-replacement-music` skills
- Assembling the picture → [`editing.md`](editing.md)

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

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "The tempo detector said 161, so it's 161." | It locked onto double time. Check `--beat-multiple 2` before anything is cut to it. |
| "I'll just cut the 13 seconds the owner asked for." | Mid-bar, that stumbles *and* re-phases the grid. Snap to bars; 12.098s is what four bars actually measure. |
| "I'll re-run the analysis at render time, it's the same audio." | Beat tracking is a heuristic. A different answer silently moves every cut. |
| "3:48 is 3:48." | Not once a section is gone. Edited 3:48 is source 4:00.098 here. |

## Red Flags

- A tempo exactly double the one you can tap
- An excision whose `removed_bars` is not a whole number
- A rendered bed whose bit depth or sample rate differs from the source
- Anchoring to a literal timecode on a bar-aligned cut
- Re-analysing a bed that already has a cached grid

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
