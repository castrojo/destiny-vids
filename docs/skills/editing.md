---
name: editing
version: "1.4"
last_updated: "2026-08-12"
id: editing
one_line_purpose: Turn a plain-language outline into a rendered cut.
entry_point: docs/skills/editing.md
category: editing
mcp_compliance_level: partial
optimization_status: draft
status: active
dependencies: [indexing]
tags: [story, cut-list, render, ffmpeg, outline, still, artwork-card, window-extract, timing-pass, marker-card, two-clocks, bed-pause]
description: >-
  Covers outlines, shot matching, artwork cards, timing passes with marker cards, and a bed that pauses.
  Use when writing an outline, marking material for removal before editing, or scoring a cut whose song does not run end to end.
metadata:
  type: procedure
  context7-sources:
    - /websites/ffmpeg_documentation
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

**Beat order is also credit placement.** A contributor can only be plated
where an ensemble shot plays, so where the credits land is decided by the
outline, not by the scheduler. Every ensemble anchor in a Destiny cinematic
sits in its opening firefight, so an outline that runs its Guardian beats off
at the top credits the whole month in the first twelve seconds and then goes
silent. Move the beat and the credit moves with it: `stories/osiris-sagira.txt`
deals its Guardian beats out across the story, and on the same roster that
reorder alone turned three contributors crammed into the first 1.2 seconds
(three more with no window at all) into all seven credited across a minute.
Spreading is measured, not guessed: `tools/plate.py plan` prints every plate
it placed, in order, so check the credit times before rendering.

### Two cut shapes, and spanning is the default

**A cut spans every source unless you tell it not to.** That is the shape of a
**hero video** — one person, one video, every clean shot of that bound character
in the whole index. Karena's Mara Sov video is her Season of the Lost shots
*and* her Final Shape shots, summed. Hero videos are promotional material for
the feature, *Seven Days to the Wolves*; the two kinds and their rules are
[`docs/catalog.md`](../catalog.md).

```bash
# hero video: the whole index is the pool. No flags. This is the default.
python3 tools/story.py stories/mara-sov.txt --dir segments
```

Start from the corpus, which already spans sources — `python3 tools/corpus.py
mara_sov --dir segments` reports `6/6 clean shot(s), 11.304s across 2 video(s)`.
That list *is* the hero video's shot list. Full walkthrough:
[`docs/cuts/hero-montage.md`](../cuts/hero-montage.md).

**Reaching for `--from-video` by habit is a known failure.** Three consecutive
Destiny chapters were all cut from `yt_destiny_2_the_final_shape_launch_trailer`
while four fully-indexed trailers had no outline written against them; two of
those cuts shared 35.9s — 68% of one's runtime — and plated the same person
([issue #49]). Before pinning a source, ask whether the cut is retelling *that
trailer's* story. If it is about a person, it is not.

### One cinematic, skipped forward (the special case)

A cut that deliberately lives inside a single source cinematic — because it is
retelling that cinematic's own story in its own order — gets two flags instead
of an edit timeline:

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
source-time order and reorder by moving lines. Worked examples:
[`docs/cuts/01-dance.md`](../cuts/01-dance.md) (ensemble) and
[`docs/cuts/03-zavala.md`](../cuts/03-zavala.md) (a lead, where the beats had to
bend to eight clean shots).

Under `--forward-only` a mismatch cascades harder than usual: a wrong early
pick can strand every later beat behind the playhead. Fix the earliest wrong
beat, not the stranded one. (A hero video has no playhead, so nothing is ever
stranded there — only distinctness cascades.)

[issue #49]: https://github.com/castrojo/destiny-vids/issues/49

### Holds

`--max-shot-sec` trims any shot held longer than the cap, **from its tail**. The
in-point is what the detector pass and the index worked to find, so a trim never
moves the start. A detector-derived beat can be a fine *beat* and a terrible
*cut*: the Curse of Osiris cinematic ends on a 25-second static gateway shot.

Pass the same value to `tools/plate.py plan`, or every plate after the first
trimmed shot lands late.

### A hold cannot exceed the shot it was vetted on

A beat may carry its own `duration` (in a JSON outline), which is a legitimate
way to author a hold. It is capped at the segment's own length, and the cap is
reported:

```text
CLAMPED HOLDS — the outline asked to hold past the shot's out-point:
   3. yt_demo_0007  600s -> 4.2s
```

The cap is not tidiness. `render.py` cuts `-ss start_sec -t duration`, so a hold
longer than the segment keeps decoding **into the next shot** — footage no beat
selected and no tagger ever vetted, which may carry a HUD or a burned-in title
and may not be `clean` at all. The emitted `end_sec` still reports the segment's
real out-point, so nothing downstream reveals the overrun. That is the `clean`
gate defeated by arithmetic rather than by a bad tag.

Want a longer hold? Use a longer shot. The gate is per-shot because cleanliness
was established per-shot.

`render.py` applies the same clamp to every shot it cuts, not only to shotlists
`story.py` built: a hand-edited `cut.json` can carry a `duration` past
`end_sec`, and that is the identical hole. The render warns the same way —
`CLAMPED: shot <segment_id> asked for Xs, shot holds Ys` on stderr — and cuts
only the vetted span.

### Cutting from a long source: extract the window first

`render.py` seeks with `-ss` **after** `-i` on purpose (see below), so every clip
decodes from the file's start and discards. On a 30-minute compilation a clip at
24:00 decodes twenty-four minutes before it writes a frame — measured at roughly
35x realtime here, so about 40 seconds per clip, times however many clips the act
needs.

**Re-encode the span you need to its own file first**, and cut from that:

```bash
ffmpeg -ss 1380 -i media/<long>.mp4 -t 210 -c:v libx264 -preset veryfast -crf 16 \
    -c:a aac -b:a 192k media/<window>.mp4
```

Every later seek then lands inside a short file. `annotate.py` has no window or
offset option either, so this is also what keeps detection cheap.

The cost is bookkeeping: **timecodes rebase by the extract's start**. Record the
offset next to the shot, so a source timecode the owner gave you ("the crash at
24:46") stays checkable against the extract's own clock.

### Artwork cards: a shot that is a still

A shot carrying `"still": "<path>"` instead of `"video_id"` renders the image for
its authored duration through the same normalization chain as a cut clip. It is
how a dropped card keeps its slot — a trailer's black "8 DUNGEONS" plate is
`burned_text` and therefore already excluded, and dropping it silently shortens
the film; replacing it with artwork keeps the rhythm the trailer had.

**A still must match the cut clips' audio disposition exactly.** With `--audio`,
`render.py` sets `keep_audio=False` and every clip is video-only; a still that
carried a silent track would then be the only input with a stream the others
lack. The concat demuxer requires that all inputs "share identical stream
properties such as codecs and time bases"
(`source: /websites/ffmpeg_documentation`), so the join simply fails.

A still has no out-point, so `resolve_duration` leaves its hold alone and
`--max-shot-sec` does not trim it: a card's length is a musical decision, not a
detector artifact.

**This does not weaken the `clean` gate.** The card record never cuts the
source's burned-in frames at all — it puts artwork in the hole they leave.

### Mark, don't cut: the timing pass

Before an edit is worth making, its timing has to be judged — and you cannot
judge timing against a cut that has already thrown the material away. A
**timing pass** is the intermediate render that answers this:

> Anything destined for removal or replacement **stays in the timeline at its
> exact duration**, blacked out by a marker card saying what will happen there.

Because a card and the footage it replaces are the same number of seconds,
**timing is preserved by construction**: every later anchor lands exactly where
it will land in the finished cut, so the pass can be played against the music
and reviewed before a frame is actually removed.

```bash
python3 tools/marker.py "COMIC PLACEHOLDER" --sub "4:33-4:37  enemy CU"
```

Two kinds, and the sub-line always says *which* material is standing behind the
card:

| Card | Means |
|---|---|
| `COMIC PLACEHOLDER` | **an artwork slot** — artwork will be dropped in here later |
| `REMOVE — <reason>` | this is coming out; it is here so the timing still reads |

`tools/marker.py` renders these deliberately plain — full-frame black, one
tracked line, no chrome. A marker must never be mistakable for a finished
nameplate. They are **production markers, not credits**: a marker carries no
claim about any person, so none of the nameplate vocabulary rules in
[`plates.md`](plates.md) apply to it, and none of its shapes are reused either.

This is what replaces jump-cutting around unwanted material. A long enemy
close-up, a publisher's mechanic card, a repeated shot: black it out in place
and keep going. The reviewer sees a continuous cut with its holes labelled,
which is a far better artifact than a shorter cut whose rhythm has silently
changed.

**Leaving artwork slots is the point, not a workaround.** The slots are where
the film's own artwork goes; marking them early is what lets the artwork be
made to a known duration instead of being squeezed in afterwards.

### Two clocks: when the bed does not run end to end

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

### An authored shotlist, and the invariant it must hold

A cut list that `story.py` produced is derived, and hand-editing it is a Red Flag
below. A shotlist **authored from the start** is a different object: no matcher
ran, so there is nothing to be out of date with. Name it so the two are never
confused (`stories/<name>-prototype.json`, not `cut.json`) and say so in the
file.

This is the legitimate path when shots are chosen by eye — see the next section.
It comes with one invariant that is easy to miss:

> **A cut is a concatenation. It has no absolute timeline.**

So an act that comes up short does not leave a gap; it slides every later shot
earlier, and any shot that was supposed to land on a musical moment lands
somewhere else. Assert that each act fills its span rather than discovering it in
the render:

```python
assert abs(act_end - ANCHOR) < 0.15, "a short act slides every later anchor"
```

The same arithmetic makes an *unresolvable* shot dangerous. `render.py` skips a
shot whose source is missing and reports it on stderr — but the film is then
shorter than the shotlist says. `media/` is gitignored and varies per host, so
**filter the pool to sources that actually exist** before building.

### Picking shots by eye, without tagging

Tagging exists to feed `story.py`'s matcher. **If a human picks the shots, no
tags are needed** — and for a new source that is the difference between a cut
today and a tagging pass first.

Detection pass 1 alone gives what eyeball selection needs:

```bash
python3 tools/annotate.py index --video media/<window>.mp4 \
    --video-record videos/<id>.json          # no --tags: boundaries + keyframes
```

Then contact-sheet the keyframes (5x4 grids, each tile labelled with the shot
index and its in/out) and read them. Two hundred shots fit on ten sheets.

Two rules make this honest rather than a shortcut around the gate:

- **A midpoint keyframe does not prove the interval is clean.** Keyframes come
  from the middle of a beat by design; a shot whose middle is clean can still
  open or close on a logo card or a HUD frame. Scrub the edges of anything you
  select.
- **It buys a cut, not an index.** Nothing lands in `segments/`, so the shots are
  not searchable and no later cut can find them. That is the trade; make it
  deliberately.

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
- **Scoring replaces the audio.** `--audio` maps the bed instead of the source
  and passes `-shortest`, so the dialogue is gone. If the conversation still
  needs to be legible, show it: `tools/dialogue.py` (see
  [`plates.md`](plates.md)).

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "No clean shot matches, so I'll allow unclean footage." | The gate exists to keep a HUD out of the finished cut. Rewrite the beat instead. |
| "The credits pile up in the intro, so I'll add a scheduler gap between contributor plates." | Measured on the Osiris cut, a cadence gate *costs* credits — it suppresses the group rows and the re-home pass. All the ensemble shots sitting in the intro is an outline problem: move the Guardian beat, and the credit moves with it. |
| "I'll hand-edit the timings in `cut.json`." | It is a derived artifact and the next run discards your edit. Change the outline or the cap. |
| "The act came out a bit short, the render will pad it." | It will not. A cut is a concatenation with no absolute timeline, so a short act slides every later shot earlier and every musical anchor with it. |
| "I'll skip the window extract, it's just one flag." | Output seeking decodes from the file start. A clip at 24:00 in a 30-minute source costs ~40s of decode, every time. |
| "I'll just cut the bits we don't want, then judge the timing." | You have thrown away the thing you were going to judge. Black them out in place at their exact duration first — a timing pass keeps every later anchor where it will actually land. |
| "Duck the song under the action beat, it's simpler than pausing." | A −6.8 LUFS master has to drop ~18 dB to sit under anything, which is a stop with mud on top. Pause it, and put the seam in a gap the artist already left. |
| "The card is just black with text, I'll drop it." | Dropping it shortens the film and loses the rhythm the trailer had. Replace it with artwork; the slot is the point. |
| "I'll set a long `duration` on the beat to hold the shot." | A hold is clamped to the segment. Past its out-point you are cutting the *next* shot, which nothing vetted. |
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
- An act whose measured length does not match the span it was written for.
- Selecting a shot from its midpoint keyframe alone, without scrubbing its edges.
- A still whose audio disposition differs from the cut clips around it.
- An anchor asserted against wall time in a cut whose bed pauses. Bed time is
  the only clock the music knows.
- A marker card that has grown chrome, a name, or a role. It is a slate, not a
  plate.
- Cutting dozens of clips out of a long source without extracting the window.

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
