---
name: editing
version: "1.0"
last_updated: "2026-08-19"
id: editing
one_line_purpose: Build and revise cuts from indexed footage without inventing shots.
entry_point: docs/skills/editing/SKILL.md
category: editorial
status: active
dependencies: []
tags:
  - story
  - cuts
  - render
  - beats
  - segments
description: >-
  Build and revise cuts from indexed footage without inventing shots. Use when
  making story outlines or renders from indexed segments.
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
- Putting names on screen → [`plates.md`](../plates/SKILL.md)

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


## Where the detail lives

This skill is the contract. The procedure lives in `references/`:

| Reference | What is in it |
|---|---|
| [`outline-and-shape.md`](references/outline-and-shape.md) | Writing beats the matcher can serve, and **spanning vs pinning** — the decision that decides what the cut is about. |
| [`hero-video.md`](references/hero-video.md) | The **hero video** — one person, one video, every source — and when *not* to pin a cut to one cinematic. |
| [`holds-and-windows.md`](references/holds-and-windows.md) | How long a shot may hold, cutting from a long source, and artwork cards. |
| [`timing-pass.md`](references/timing-pass.md) | **Mark, don't cut.** The review convention, and how filling a span smuggles banned material in. |
| [`shotlists-and-excisions.md`](references/shotlists-and-excisions.md) | Deriving in-points, the authored-shotlist invariant, and picking shots by eye. |
| [`timing-pass-notes.md`](references/timing-pass-notes.md) | The worked act VI timing pass. |

## Not every piece is a cut
Sometimes the source already tells the story and the job is to credit the cast
and clean the frame, not to re-edit. `tools/uncut.py` emits a cut list that is
simply every segment of one video in source order, so all the planners run
unchanged — and because nothing is re-ordered or capped, the finished file and
the source share a clock.

```bash
python3 tools/uncut.py <video_id> --out cut.json
python3 tools/redact.py --video media/<video_id>.mp4 --video-id <video_id> \
    --audio media/<bed>.mp3 --audio-gain 0.9 --out base.mp4
```

`redact.py` paints out the burned-in publisher copy an upload carries — the
ratings card at the head, the logo lockup and legal line at the tail — from
boxes authored in `redactions/<video_id>.json` against source pixels. On a cut
those frames are simply `burned_text` and get dropped; uncut, there is nothing
to drop them *for*, so they are covered instead. A redaction only ever removes:
it never paints anything the frame did not already have to say.

Two things follow, and both bite:

- **The index must still be honest.** A shot that dissolves into the logo card
  is `burned_text` and therefore not `clean`, even though the first fifteen
  seconds of it are beautiful. Tag it, and let the redaction — not a fib in the
  index — be what makes it usable here.
- **A hand-cut act never went through the clean gate at all.** When runs are
  authored as timecodes on an unindexed source, no tagger ever set `overlays`
  on them: **scan the finished picture for burned-in titles yourself** before
  plating it. Act II kept two, one of them unrecorded, and a credit was placed
  squarely on it.
- **Scoring replaces the audio.** `--audio` maps the bed instead of the source
  and passes `-shortest`, so the dialogue is gone. If the conversation still
  needs to be legible, show it: `tools/dialogue.py` (see
  [`plates.md`](../plates/SKILL.md)).

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "No clean shot matches, so I'll allow unclean footage." | The gate exists to keep a HUD out of the finished cut. Rewrite the beat instead. |
| "The credits pile up in the intro, so I'll add a scheduler gap between contributor plates." | Measured on the Osiris cut, a cadence gate *costs* credits — it suppresses the group rows and the re-home pass. All the ensemble shots sitting in the intro is an outline problem: move the Guardian beat, and the credit moves with it. |
| "I'll hand-edit the timings in `cut.json`." | It is a derived artifact and the next run discards your edit. Change the outline or the cap. |
| "The act came out a bit short, the render will pad it." | It will not. A cut is a concatenation with no absolute timeline, so a short act slides every later shot earlier and every musical anchor with it. |
| "I'll skip the window extract, it's just one flag." | Output seeking decodes from the file start. A clip at 24:00 in a 30-minute source costs ~40s of decode, every time. |
| "The act is short, I'll loop the pool / start the run earlier to fill it." | That is not filling, it is choosing footage blind. It is how 25 shots got replayed and how a Savathûn montage entered a no-Savathûn film. Name the extra source and assert the boundary. |
| "The pause is in the right place but feels wrong, so I'll move it." | Position and length are separate faults. Measure the insert's phrase and fix the out-point first. |
| "I'll just cut the bits we don't want, then judge the timing." | You have thrown away the thing you were going to judge. Black them out in place at their exact duration first — a timing pass keeps every later anchor where it will actually land. |
| "Duck the song under the action beat, it's simpler than pausing." | A −6.8 LUFS master has to drop ~18 dB to sit under anything, which is a stop with mud on top. Pause it, and put the seam in a gap the artist already left. |
| "The card is just black with text, I'll drop it." | Dropping it shortens the film and loses the rhythm the trailer had. Replace it with artwork; the slot is the point. |
| "I'll set a long `duration` on the beat to hold the shot." | A hold is clamped to the segment. Past its out-point you are cutting the *next* shot, which nothing vetted. |
| "The beat matched something close enough." | A mismatch cascades into every later beat that wanted that shot. Fix it at the source. |
| "Stream copy is faster and looks the same." | It snaps the in-point to a keyframe, discarding the boundary the detector pass exists to find. |
| "I'll build a timeline layer so I can order shots freely." | One cinematic plus `--forward-only` is the shape. A sequencer buys freedom to hide continuity errors. |
| "To hold black before the picture, I'll cut in a black clip and concat it." | A delayed `fade=t=in:st=X` already holds every earlier frame black. One filter, no seam, no second stream to keep in sync. |
| "The detector says the cut is at X, so the event starts at X." | It says the frame is already *different* by X. A flare that blooms is under way before that — measure the luma's departure from its plateau and cut on that frame, or the reveal pops in half-lit. |

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
- A black hold built as its own clip when a filter already holds it, or a
  reveal cut on a scene-detector boundary rather than on the frame the light
  actually starts moving.
- An act whose measured length does not match the span it was written for.
- Selecting a shot from its midpoint keyframe alone, without scrubbing its edges.
- A still whose audio disposition differs from the cut clips around it.
- An anchor asserted against wall time in a cut whose bed pauses. Bed time is
  the only clock the music knows.
- A marker card that has grown chrome, a name, or a role. It is a slate, not a
  plate.
- Cutting dozens of clips out of a long source without extracting the window.
- **Any code path that extends a run to make a span add up.** Ask what it picked
  up. This is the single failure that has breached the most editorial rules here.
- A hard-coded in-point in an act that has excisions. Derive it, or the next
  excision silently shortens the act.

## Verification

```bash
python3 -m pytest -q tests/test_story.py tests/test_render.py

# the rendered cut is what the cut list said it would be
ffprobe -v error -show_entries format=duration -of csv=p=0 renders/<name>.mp4
```

The render prints the **delivered true peak** of the finished file and re-runs
the concat at a corrected static gain if it is above −0.9 dBTP
(`tools/peaks.py`, issue #44). Read that line before shipping; a WARNING there
means the file is still hot after five corrections.

For a scored cut, prove the audio landed rather than trusting the filtergraph —
correlate the delivered file against the bed at a known offset:

- a bed region returns **+1.000**
- a paused region returns roughly **0.000**
- after a pause, the offset is `bed_offset + total paused so far`

Checklist before calling a cut done:

- [ ] every act's measured length equals the span it was written for
- [ ] no shot appears twice
- [ ] no run begins before a boundary an editorial rule depends on
- [ ] every marked span is exactly as long as the material it stands in for
- [ ] anchors asserted against bed time, not wall time

## Delivery

A cut ships to two places from **one** cut list: the website player (source
audio) and a YouTube upload (a music bed, `render.py --audio`). They differ by
audio and filename, never by a second edit.

Upload order lives in a numeric filename prefix — `stories/01-dance.txt` →
`renders/01-dance-web.mp4`, `renders/01-dance-youtube.mp4`. Sorting the
directory sorts the playlist; there is no ordering manifest to keep in sync.

A cut's unresolved beats and anything a human still has to decide are recorded
in its outline's own header (see `stories/01-dance.txt`) and filed as issues —
there is no per-cut doc tree.

Ranking weights and query mapping: `docs/agent-retrieval.md`. Encoder choices,
seeking, and the ffmpeg resolution order: `docs/rendering.md`. What a character
does and does not have on film: [`corpus.md`](../corpus.md).
