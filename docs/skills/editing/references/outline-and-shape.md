# Writing an outline, and choosing the cut's shape

Reference for [`../SKILL.md`](../SKILL.md). Split out of it to keep the
skill inside its size budget. How to write beats the matcher can serve, and
the spanning-vs-pinned decision that decides what the cut is about.

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
the feature, *Seven Days to the Wolves*: the feature is one whole unit,
released as a single show; a hero video is one person across every source.

```bash
# hero video: the whole index is the pool. No flags. This is the default.
python3 tools/story.py stories/mara-sov.txt --dir segments
```

Start from the corpus, which already spans sources — `python3 tools/corpus.py
mara_sov --dir segments` reports `6/6 clean shot(s), 11.304s across 2 video(s)`.
That list *is* the hero video's shot list. Full walkthrough:
[`hero-video.md`](hero-video.md).

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
[`stories/01-dance.txt`](../../../../stories/01-dance.txt) (ensemble) and
[`stories/03-zavala.txt`](../../../../stories/03-zavala.txt) (a lead, where the
beats had to bend to eight clean shots).

Under `--forward-only` a mismatch cascades harder than usual: a wrong early
pick can strand every later beat behind the playhead. Fix the earliest wrong
beat, not the stranded one. (A hero video has no playhead, so nothing is ever
stranded there — only distinctness cascades.)

[issue #49]: https://github.com/castrojo/destiny-vids/issues/49
