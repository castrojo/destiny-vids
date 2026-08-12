# Epic H — Tempo: make the cut land on the music

**Parent:** #9 · **Depends on:** A · **Blocks:** I · **Blocked by:** J3 (for H1)
**Design:** [`docs/plans/wolves/design.md` §7](../design.md)

Shots on the beat, sections on the bar, chatter on the downbeat. All of it is
`60 / bpm` and integer division — the math is small on purpose, and small math is
what makes a highlight reel feel deliberate instead of assembled.

**Done looks like:** a cut list whose every shot duration is a whole number of
beats, whose sections end exactly where the song's sections end, and whose report
names every shot that could not be put on the grid.

**Invariants for every sub-issue here**

- Quantization only ever **trims**, and only from the tail. The in-point is what
  the index spent a detector pass to find.
- BPM is authored. Detection is an authoring aid that never runs at render time.
- A shot that will not fit the grid is reported, never stretched and never
  dropped.

---

## H1 — Track records

**Labels:** `enhancement` · **Blocked by:** J3

`tracks/<track_id>.json` plus `schema/track.schema.json`, modeled directly on
`videos/` and `schema/video.schema.json`: `track_id`, `title`, `artist`,
`source_url`, `usage_class`, `source_rights_note`, `bpm`, `beat_offset_sec`,
`meter`, and `sections[] = {name, start_sec, bars, register, energy}`.

Audio is footage's twin: it lives in gitignored `media/`, and the repo carries
metadata and timecodes only.

**Acceptance**

- [ ] `*.mp3`, `*.m4a`, `*.wav`, `*.flac`, `*.opus` are gitignored beside
      `*.mp4`, and a test asserts no audio file is tracked.
- [ ] `usage_class` and `source_rights_note` are **required** — a track with no
      stated licence cannot enter the index, the same rule videos already live
      under.
- [ ] `register` on a section uses `vocab/register.yaml`'s −2..+2, not a new
      scale.
- [ ] One real, license-clear track record is committed as the worked example.

---

## H2 — `tools/tempo.py`: the grid and the quantizer

**Labels:** `enhancement` · **Depends on:** H1

```python
beat_grid(bpm, offset, duration) -> list[float]
quantize(duration, bpm, minimum_beats=1) -> tuple[float, bool]   # (duration, on_grid)
```

Round a shot's duration **down** to a whole number of beats. A shot shorter than
one beat keeps its source length and returns `on_grid=False`.

**Acceptance**

- [ ] Quantized duration never exceeds the source duration — the property test
      that matters, because exceeding it means freezing a frame.
- [ ] A shot of exactly N beats is unchanged.
- [ ] `--quantize beat|bar|off` on the render path, defaulting to `beat`; `off`
      reproduces today's output exactly, so this can land without changing any
      existing render.
- [ ] Off-grid shots are counted in the report and named.

---

## H3 — Sections fit the song

**Labels:** `enhancement` · **Depends on:** H2, A3

A `## Section` maps to one song section and its shots fill exactly that section's
bars. Fill greedily in beat-quantized shots; trim the last shot so the section
ends on the bar line.

**Acceptance**

- [ ] Section boundaries land on bar lines, exactly, with no accumulated drift
      across a long cut (do the arithmetic in beats, convert to seconds once).
- [ ] Beats run out before bars → report the shortfall and hold the last shot.
- [ ] Bars run out before beats → report the unplaced beats. The fiction bends to
      the footage, and to the song.
- [ ] A cut with no track record still renders, unquantized, with a `warn`.

---

## H4 — `detect`, the authoring aid

**Labels:** `enhancement`, `help wanted` · **Depends on:** H1

`python3 tools/tempo.py detect --audio media/<track>.mp3` prints a proposed BPM
and offset for a human to paste into the track record. Optional dependency,
exactly like `scenedetect`: absent, the subcommand explains what to install and
exits cleanly.

**Acceptance**

- [ ] The suite passes with the dependency absent — no test imports it.
- [ ] Nothing in the render path ever calls `detect`.
- [ ] The output is copy-pasteable into a track record, and says plainly that a
      human has to confirm it.
- [ ] The install note records the real state of the world: librosa pulls in
      numba, which still gates it on newer Pythons, and `aubio`'s official wheels
      stopped at 0.4.9 in 2019.

**Do not** wire beat detection into the render. A render that re-analyzes audio
is a render that produces a different cut on a different machine.
