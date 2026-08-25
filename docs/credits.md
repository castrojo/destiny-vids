# Act VIII — the live-concert credits

Act VIII was a still-card slideshow over a two-pass Nightwish bed. Its second
pass is now a **performance**, and that performance is the picture: the film's
last four minutes play under a live Nightwish set instead of over a wallpaper.

Three owner instructions drive it, and nothing else moves:

1. The second pass — *Storytime* — is replaced by *Last Ride of the Day*, live
   at Masters of Rock.
2. That concert is the frame from the swap to the last shot of the film.
3. The credits are redesigned so the video is enclosed and the contributor
   sections get an area of their own.

Everything before the swap is untouched: the call to action, the birthday card,
the comic reveal, the cast placards and the first walls all play exactly as
they did. The act is built by [`scripts/build_credits.py`](../scripts/build_credits.py)
from [`stories/08-credits.json`](../stories/08-credits.json), which is where the
measurements below are recorded.

## The layout: a scope seat

The clip is 1920×794 — 2.42:1 — and the delivery frame is 1920×1080. It seats
at `(0, 0)` at **native resolution**, and the 286 px it does not use become the
contributor band. No scale filter appears anywhere in the graph, so the
performance is never resampled.

The band carries the same information the full-frame wall does — section name,
page number, the logins, the side copy — in three rows of seven, or five for
the upstream tier, whose type is larger. A hairline seam at y=794 joins the two
so the band reads as part of the frame rather than as a strip beneath it.

The band credits **logins only**. A face plus its name needs a 196 px row and
the band is 286 px tall, so the portraits stop at the swap and the names carry
the credit from there. Nobody is dropped; the pictures are.

The band card draws nothing above the seam, and that is asserted rather than
assumed: `render_name_band` clears those rows to transparent, so a name that
drifted above the seam fails a test instead of being silently painted over.

A side rail — a vertical column beside a pillarboxed performance — was the
fallback if the band could not be read. It was not needed.

## Fitting the roll to the performance

The concert from its in point runs 265.701 s where *Storytime* covered 305.5 s.
The owner's answer was to **shrink the credits**: the walls scale to the bed,
and the bed is never stretched to the walls. `schedule()` already sized wall
pages by relative weight, so this falls out of the existing arithmetic.

The scheduler splits the sections between the two windows at the point where
both sides read at the same speed. Names are counted at their **reading
weight**, not their raw count: an upstream name is worth 1.25 of a Bluefin one,
the same ratio its wall already held for. Counted raw, the seam landed exactly
on the tier boundary and each side then paced itself — which made the more
distinguished tier the faster one.

## The wordmark

The mark's hold was measured against *Storytime*'s double-bass climax, and that
climax left with *Storytime*. The instruction outlived its song, so the hold is
no longer authored: `wordmark.dur_sec` is `null`, and the schedule starts the
mark at the measured end of the music and runs it to the last frame. The
performance comes off at the same instant — the mark is the last thing in the
film and does not share the frame with a band still playing.

The instruction is satisfied; the **length** is a number nobody has approved,
and it is recorded in the manifest's `unresolved` for the owner.

## Measurements

Every number is measured, and its evidence is in
[`music/bed_last_ride_of_the_day_live.json`](../music/bed_last_ride_of_the_day_live.json)
and the manifest's `_what` fields. They are recorded there, not restated here.

The sentence the owner asked to keep whole is **spoken stage banter, not sung**.
That matters for the seat: the crowd floor in the 250–3500 Hz band is −25.6 dB
and the loudest syllable only reaches −20.7, so there is no transient to land
ahead of. The in point sits in a real dip — nearly 5 dB below the crowd itself —
and the crossfade finishes before the first speech energy.

## Loudness: measured, not corrected

The live recording is **5.1 LU quieter** than the instrumental it takes over
from, measured over the spans actually used.

Nothing is applied. It cannot be raised — it already peaks at 0.0 dBFS, so
closing the gap upwards means limiting, which the audio tenet forbids. Closing
it downwards means attenuating 3:48 of already-approved audio and pulling the
whole act further below the programme. Both are the owner's call, so the film
ships at the levels the two recordings actually have, with the measurement on
the record.

The gap also reads worse than it sounds: the instrumental is a loudness-war
album master and the live take is not, so most of the difference is compression
rather than level, and the seam itself lands on quiet stage banter either way.

## How it renders

One picture timeline, one encode. The performance is **composited over the
cards** rather than cut beside them, so the scheduler keeps deciding when every
screen changes and the untouched first half is never re-encoded.

Seating an overlay at 3:47 is the whole engineering problem, and two obvious
ways to do it fail:

| Approach | Result |
|---|---|
| `setpts` with an offset | overlay's framesync holds the main picture until the overlay stream produces its first frame — 3:47 of buffered cards, **OOM-killed at 12.9 GB**. |
| `tpad=start_duration` | worse: it pushes its 13,608 pad frames downstream in one burst. |
| **`color` + `concat` in front** | streams. `concat` pulls one frame at a time as overlay asks for it. |

Those generated frames are never seen — `enable` keeps the overlay off until the
swap — so their colour is arbitrary and their only job is to exist. `enable`
does the actual switching, on the card clock, so the seam is exact rather than
rounded to a pad length.

The trim stays on the **output** side. The source is a DASH `webm`, and `-ss` on
one lands in the wrong place ([`rendering.md`](rendering.md)); decoding from
zero is the price of knowing which frame we started on.

The clip is 25 fps and the delivery spec is 59.94, so it is conformed once, in
the act's own graph, rather than being discovered at assembly time.

## Rights

`vocab/provenance.yaml`'s `third_party_copyrighted` was described in Bungie
terms only. The description is widened — the class is the **rights position**,
not the rightsholder — so a copyrighted concert recording used as bed and
picture sits in it honestly. No new value; the enums are unchanged.

The programme remains non-commercial fan use, and this change does not alter
that limit.

## Deliberately not done

- **No beat-grid snapping.** The bed record's `downbeat_phase` is `null` and
  honestly recorded as unresolved, so page changes are not snapped to bars.
  Inventing a phase to snap to would be worse than not snapping.
- **No loudness correction.** See above.
- **The encode is remote by default, like every other builder.** The concat
  list carries absolute host paths to the rendered PNGs, which
  `farm.rewrite_argv_for_pod` alone cannot rewrite — so the builder farms
  through `farm.run_encode(..., text_files={concat: ...})`, which rewrites
  the list's payload paths to the pod's layout (see
  [`skills/farm.md`](skills/farm.md)). `--local` is the explicit escape hatch
  and runs memory-capped; the bare local run of this argv is what OOM-killed
  the workstation at 03:08Z on 2026-08-24.
