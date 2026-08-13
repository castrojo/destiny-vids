# Holds, extracted windows, and artwork cards

Reference for [`../SKILL.md`](../SKILL.md). Split out of it to keep the
skill inside its size budget. How long a shot may stay on screen, how to cut
from a long source, and the still that behaves like a shot.

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

