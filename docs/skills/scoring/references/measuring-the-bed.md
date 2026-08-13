# Measuring the bed

Part of the [scoring skill](../SKILL.md).

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

### The downbeat phase is evidence-backed, never an argmax

Onset strength answers *"what is loudest"*; the bar line is *"where the bar
begins"*, and in any backbeat-driven genre those are different questions: the
snare on 2 and 4 out-accents the kick, so a bare argmax parks the bar line on
the snare. That is exactly what shipped in the act II bed
(`downbeat_phase: 3`, strength `[3.13, 3.61, 3.25, 3.81]` — positions 2 and 4
out-accent 1 and 3), and it read the shipped sync anchor as 0.372 s off a beat
it was in fact exactly on ([#89](https://github.com/castrojo/destiny-vids/issues/89)).

`measure` now resolves the phase with `resolve_downbeat_phase`: the strength
vector's parity classes narrow the answer to a pair (the loud pair is the
snares, the bar line is in the quiet pair), and **measured events decide** —
the song's own re-entries, measured phase-free from the energy envelope (a
composer puts the band back in on beat 1), plus any `--anchor SEC` the
operator asserts by ear. The record keeps the audit trail:

```json
"downbeat_phase": 0,
"downbeat_phase_evidence": "5 measured re-entries/anchors land a mean 0.042s from phase-0 bar lines ...",
"measured_reentries": [{"measured_sec": 24.98, "onset_db": 9.1, ...}, ...]
```

When no event lands near any phase, or the strength signature is ambiguous,
the phase is recorded as `null` with the candidates and the reason — a missing
phase is a punch-list item, an invented one puts every bar-snapped cut a beat
off. `excise` and `map` refuse a `null` phase loudly; the fix is evidence, not
a guess: measure a re-entry, or get the owner to tap one bar line.

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

