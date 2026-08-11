---
name: editing
version: "1.0"
last_updated: "2026-08-11"
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

## Red Flags

- Reaching for `--allow-gameplay` or `--include-unclean` to make a beat land.
  Coverage widening is a deliberate editorial choice, not a matcher fix.
- Hand-editing `cut.json` to change timings. Change the outline, the tags, or
  the cap — the cut list is a derived artifact.
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

Ranking weights and query mapping: `docs/agent-retrieval.md`. Encoder choices,
seeking, and the ffmpeg resolution order: `docs/rendering.md`.
