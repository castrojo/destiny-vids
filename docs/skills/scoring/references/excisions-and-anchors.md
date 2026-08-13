# Excisions, anchors, and the two timelines

Part of the [scoring skill](../SKILL.md).

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

