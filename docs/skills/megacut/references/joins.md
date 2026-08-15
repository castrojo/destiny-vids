# Joins: where two finished things meet

Assembly never re-cuts a film, but it owns **every frame where two of them
touch**. That is a real editorial surface with its own failures, and this file
is what a session of owner notes taught about it.

## The dominant failure: an audio hole under a dramatic cut

Four owner notes on one build; **three were the same bug**. In each case the
picture was doing something strong and the sound was ducking underneath it:

| Join | Picture | Sound |
|---|---|---|
| act III → movement 3 | the Vex gate blooms to **white**, then a fall out of the sky | 2.0 s fade out into 2.0 s fade in |
| Europa → movement 5 | fade to black, then a dark Earth limb holding 3.5 s to a **sunrise** | 3.0 s fade out into 2.0 s fade in |
| act VI → movement 4 | a hard cut between two worlds | a fade under it |

The default treatment — `fade_in 2.0` on anything entering behind a slide,
`fade_out 2.0` on anything whose tail does not fade itself (issue #105) — is
correct for an act **entering out of a slide's digital silence**. It is wrong
wherever two pieces of music meet directly, because there the two fades add up
to a four-second hole exactly where the cut lands.

**The rule:** a fade is for a join *into or out of silence*. Where music meets
music, or where the picture is carrying the transition, the join is **hard**.

A white flash is the classic cover for a hard music edit — the picture blinds
you and the next song is simply there.

## Measure the premise, not just the number

A brief said to "match the transition panning up from" a character. Vertical
displacement was measured on both sides of the join, by row-mean profile
correlation, and came out **0 px**. There was no pan on either side. The join
was **dark-to-dark**, which is a different and perfectly good idea, and the
frame was never what was wrong with it.

Had the number been "improved" without checking what it referred to, the cut
would have been moved to chase a camera move that does not exist.

```bash
# Cheap vertical-motion probe: greyscale at low res, correlate row profiles.
ffmpeg -v error -ss <t> -i <file> -vf "scale=160:90,format=gray" \
    -f rawvideo -pix_fmt gray -y /tmp/a.raw
```

Pair it with **looking at the frames**. A contact sheet of a join takes one
`ffmpeg` call and answers questions no statistic will:

```bash
ffmpeg -v error -pattern_type glob -i "/tmp/f/*.png" \
    -filter_complex "tile=4x2:margin=6:padding=6:color=0x202020" -y sheet.png
```

## A hold is relative to what surrounds it

One act slide held 15 s where every other held 5. That was deliberate — it was
the single card announcing two acts. It became wrong without being edited,
because what sits *before* it changed: the preceding item started ending on a
slow static shot, so a frozen silent card ran straight on from a frozen
picture and the transition became twenty seconds of nothing moving.

**Re-check every hold after re-ordering the programme.** A duration is a
relationship, not a property. When one turns out wrong, prefer **retiring the
exception** over inventing a third number — and assert that the remaining
holds are *equal to each other* rather than equal to a constant, because the
house length is a choice but having two by accident is a bug.

## `trim_to`: ending a delivered act early without re-rendering it

The one sanctioned way for assembly to shorten a film. It is **not** editing:
the act's own file in `Prod/` is untouched, and the cut lives in the plan
where it can be read, tested and reverted.

```json
{ "kind": "clip", "path": "…/06-7daystothewolves.mp4",
  "audio": "source", "trim_to": 431.267 }
```

- Seconds on the **act film clock**, like every other number in the plan.
- Cuts **picture and sound with one number**, so they cannot diverge.
- `item_duration()` honours it everywhere, so the programme's arithmetic, the
  chapter marks and `verify_segment` all agree.
- A `fade_out` lands against the **authored** end, not the file's.
- A trimmed clip is **forced off the stream-copy path** — a copy cannot cut
  mid-GOP safely — so expect that one act to re-encode on every build.

**`dur` does not do this, and that was the trap.** An authored `dur` shorter
than the file changed the plan's arithmetic while the segment still played to
its own end; the clock and the picture disagreed and only `verify_segment`
caught it. State `trim_to`, or state nothing.

## `trim_from`: starting a delivered act late, for the same reasons

The mirror of `trim_to`, and everything above applies to it unchanged: act
film clock, both streams by one number, honoured by `item_duration()`, off
the stream-copy path. Together the two are the clip's **window**.

```json
{ "kind": "clip", "path": "…/06-7daystothewolves.mp4",
  "audio": "source", "trim_from": 10.0, "trim_to": 431.267 }
```

It exists because of issue #206 and the owner's *"16:43's title makes no sense
anymore, let's tighten this up."* Two acts opened **static behind their
slide** — the slide's 5 s, and then the act's own frozen head:

| Act | Its own head | Total static |
|---|---|---|
| II | 10.666667 s of black (`blackdetect` on the delivered act), music already playing under it | 15.7 s |
| VI | 10.000 s title plate (`scripts/build_wolves.py`, `TITLE_CARD_LEN`) | 15.7 s |

Neither was fixable act-side without cost. Act II's head is **derived** from
its music sync anchor (`HEAD + PICTURE + TAIL == SONG`), so shortening it
re-syncs the whole act. Act VI's plate carries a **rights condition**.

**Trimming in the programme is what makes both safe.** The act's file is not
re-rendered, so act VI's attribution still plays wherever act VI plays
standalone — the condition travels with the act rather than with the
programme. That is the difference between removing a plate and skipping it.

### Three things to check before trimming a head

1. **What the sound is doing there.** A black head is rarely silent. Act VI's
   song runs at −18.4 dB right up to 10 s and then builds to −12.3 by 14 s, so
   the trim buys a *build* rather than a hold. Measure it; do not assume the
   head is dead air.
2. **`fade_in` now lands on the new first frame**, because the window is
   rebased to zero. A fade authored against the old head is a different fade.
3. **What the copy on the skipped head was for.** If it is a credit or a
   licence condition, it must still play *somewhere* — and "the act's own
   file" is a legitimate somewhere, but say so in the item note.

### Before you trim, read what is in the tail

The cut that removed a comic cover also came within 21.6 s of the act's
**credit plates**. Those windows were checked against the act's own plate
manifest *before* cutting, and the check is now a test:

```python
last = max(p["at"] + p.get("dur", 0) for p in plates["plates"])
assert last < TRIM_POINT
```

A wrong credit is not recoverable by a revert, and neither is a missing one.
**Never trim an act tail without reading its plate manifest first.**

### Look for the frame that does two jobs

The best trim point is usually not a compromise. Here the comic cover came up
on the act's **last shot change** and the song's fade-out began on that same
frame — so one cut removed both things the owner had asked to remove, and the
act ended on its last full bar. Measure the shot grid *and* the audio envelope
before choosing:

```bash
ffmpeg -hide_banner -nostats -ss <t> -copyts -i <file> \
    -vf "select='gt(scene,0.20)',showinfo" -an -f null - 2>&1 | grep pts_time
ffmpeg -hide_banner -ss <t> -t 1 -i <file> -af volumedetect -f null - 2>&1 |
    grep mean_volume        # note: needs the default log level, not -v error
```

## Retiring a card without deleting its words

A slide dropped from the programme keeps its authored copy in the cards
manifest under `retired`, with a `retired_note` saying who asked and why.
Restoring the slide must never mean rewriting it.

The consequence has to be recorded too: `chapters()` derives markers from
**slides**, so removing one silently removes that act's chapter marker.
