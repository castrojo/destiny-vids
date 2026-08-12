---
name: editing
version: "1.1"
last_updated: "2026-08-12"
id: editing
one_line_purpose: Turn a plain-language outline into a rendered cut.
entry_point: docs/skills/editing.md
category: editing
mcp_compliance_level: partial
optimization_status: draft
status: active
dependencies: [indexing]
tags: [story, cut-list, render, ffmpeg, outline]
description: >-
  Covers outline authoring, shot matching, hold caps, and rendering a cut list
  to video. Use when writing a story outline, debugging a beat that matched the
  wrong shot, or rendering a cut.
metadata:
  type: procedure
---

# Editing a cut

## When to Use

- Writing an outline in `stories/`
- A beat matched a shot you did not intend
- Rendering a cut list to a video file

## When NOT to Use

- Getting a working ffmpeg → `docs/rendering.md`
- Putting names on screen → [`plates.md`](plates.md)

## Core Process

```bash
python3 tools/story.py stories/<name>.txt --dir segments            # inspect
python3 tools/story.py stories/<name>.txt --dir segments \
    --format json --out cut.json
python3 tools/render.py cut.json --media media --out renders/<name>.mp4 \
    --max-shot-sec 9
```

`story.py` walks the beats in order, casts each to the best **distinct clean**
shot, and prints its reasoning. It never reuses a shot, and unmatched beats are
reported rather than silently dropped.

**The fiction bends to the footage.** When a beat finds nothing, rewrite the
beat — do not widen the pool to unclean footage, and do not invent a shot.

### Writing an outline that lands

The matcher scores caption overlap plus editorial signals, and assigns greedily
in outline order. Two consequences to write around:

- **A mismatch cascades.** If beat 3 takes the shot beat 9 wanted, beat 9 gets
  something worse. Fix the earlier beat first, then re-run.
- **Domain words are parsed as filters, not prose.** Writing "vex" in a beat
  adds a `faction: vex` filter, which silently excludes shots that are *about*
  Guardians and were tagged with no faction. If a beat refuses to match the shot
  whose caption it nearly quotes, strip the enum-like words and describe the
  picture instead.

Phrasing a beat close to the target caption is legitimate: captions are the
index's search surface, and the outline is written against what exists.

### One cinematic, skipped forward

A cut that lives inside a single source cinematic gets two flags instead of an
edit timeline:

```bash
python3 tools/story.py stories/01-dance.txt --dir segments \
    --from-video yt_destiny_2_the_final_shape_launch_trailer --forward-only
```

- `--from-video` restricts the pool to one source, so nothing drifts in from
  another cinematic.
- `--forward-only` holds a playhead on the source timeline: each beat may only
  take a shot at or after the previous shot's out-point. The jump is reported
  per shot as `skip_sec` (`[skip +Xs]` in text output). It requires
  `--from-video` — a playhead is seconds on ONE cinematic's timeline, and the
  tool refuses the flag alone rather than compare seconds across unrelated
  sources.

The beat order *is* the timeline; the skips are the gaps between chosen shots.
This is deliberately not a sequencer — there is no cut-graph, no editing DSL,
and no layer that lets cut order disagree with source order. Write the beats in
source-time order and reorder by moving lines. Worked example:
[`docs/cuts/01-dance.md`](../cuts/01-dance.md).

Under `--forward-only` a mismatch cascades harder than usual: a wrong early
pick can strand every later beat behind the playhead. Fix the earliest wrong
beat, not the stranded one.

### Holds

`--max-shot-sec` trims any shot held longer than the cap, **from its tail**. The
in-point is what the detector pass and the index worked to find, so a trim never
moves the start. A detector-derived beat can be a fine *beat* and a terrible
*cut*: the Curse of Osiris cinematic ends on a 25-second static gateway shot.

Pass the same value to `tools/plate.py plan`, or every plate after the first
trimmed shot lands late.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "No clean shot matches, so I'll allow unclean footage." | The gate exists to keep a HUD out of the finished cut. Rewrite the beat instead. |
| "I'll hand-edit the timings in `cut.json`." | It is a derived artifact and the next run discards your edit. Change the outline or the cap. |
| "The beat matched something close enough." | A mismatch cascades into every later beat that wanted that shot. Fix it at the source. |
| "Stream copy is faster and looks the same." | It snaps the in-point to a keyframe, discarding the boundary the detector pass exists to find. |
| "I'll build a timeline layer so I can order shots freely." | One cinematic plus `--forward-only` is the shape. A sequencer buys freedom to hide continuity errors. |

## Red Flags

- Reaching for `--allow-gameplay` or `--include-unclean` to make a beat land.
  Coverage widening is a deliberate editorial choice, not a matcher fix.
- Hand-editing `cut.json` to change timings. Change the outline, the tags, or
  the cap — the cut list is a derived artifact.
- Adding a second cinematic, a track model, or a cut-graph to make a beat fit.
  Back out and simplify: beat order is the timeline.
- Stream-copying clips "to make the render faster". A stream copy snaps the
  in-point to the nearest keyframe and throws away the boundary the whole
  detector pass exists to find.
- A shot silently missing from the output. `render.py` reports missing sources;
  read its stderr rather than trusting the duration.

## Verification

```bash
python3 -m pytest -q tests/test_story.py tests/test_render.py

# the rendered cut is what the cut list said it would be
ffprobe -v error -show_entries format=duration -of csv=p=0 renders/<name>.mp4
```

## Delivery

A cut ships to two places from **one** cut list: the website player (source
audio) and a YouTube upload (a music bed, `render.py --audio`). They differ by
audio and filename, never by a second edit.

Upload order lives in a numeric filename prefix — `stories/01-dance.txt` →
`renders/01-dance-web.mp4`, `renders/01-dance-youtube.mp4`. Sorting the
directory sorts the playlist; there is no ordering manifest to keep in sync.

Each shipped cut gets a doc in `docs/cuts/` recording its source cinematic, its
skip points, its unresolved beats, and anything a human still has to decide.

Ranking weights and query mapping: `docs/agent-retrieval.md`. Encoder choices,
seeking, and the ffmpeg resolution order: `docs/rendering.md`. What a character
does and does not have on film: [`corpus.md`](corpus.md).
