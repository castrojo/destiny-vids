# Two clocks, diegetic inserts, and levels

Part of the [scoring skill](../SKILL.md).

## A loud master can exceed 0 dBTP, and the fix is a static gain

Modern and loudness-war-era masters routinely decode above full scale. Measured
on a 2007 metal master: **+2.1 dBFS true peak, −6.8 LUFS integrated, LRA 3.3**.

The correction is a **static gain at the mux** — nothing else:

```bash
ffmpeg -i cut.mp4 -i bed.wav -map 0:v:0 -map 1:a:0 -c:v copy \
    -af "volume=-3.5dB" -c:a aac -b:a 320k -ar 48000 -shortest out.mp4
```

`-c:v copy` matters: the picture is not re-encoded, so the gain pass costs one
audio encode and no generation loss on video. A static gain scales every sample
identically, so the LRA and every dynamic relationship the artist chose are
untouched — which is exactly what `loudnorm`, a compressor or a limiter would
change. Re-measure the **delivered** file afterwards, not the intermediate.

## Two clocks: when the bed does not run end to end

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

Two more non-bed dispositions exist, added for act VI's interruption
([issue #104](https://github.com/castrojo/destiny-vids/issues/104)), and they
are different promises rather than synonyms: **`silent`** is a deliberate
silence, forever; **`hold`** is a music slot that is silent *today* and takes
an `audio_from` once the owner clears a track (a licensing decision — never
filled unilaterally). Any other `audio` value is an error, because a typo
quietly becoming bed time would slide every anchor.

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

## A diegetic insert has to be allowed to end

When the bed pauses for a moment of source audio, the out-point belongs to
**that moment's own phrase**, not to the shot or to a round number. Cut back to
the song while the insert is still in the air and it reads as a dropout rather
than a decision — the moment starts and does not finish.

Find the out-point by measuring the insert's envelope and taking its resolution
(its quietest point after the last swell), the same way the bed's own gaps are
found. A pause under ~3 s rarely reads as deliberate at all.

If a note says the moment is *in the right place* but wrong somehow, change the
**length**, not the position. Those are separate faults and the in-point is
usually the part that was already right.

### ...and it brings its own peaks

An insert is somebody else's mix. Its peaks are not yours to have planned for,
and they are measured on a region far too short to move the film's integrated
loudness — so a cut whose bed sits comfortably under the headroom gate can be
pushed over it by one explosion, and the *whole-file* number is the only place
you will see it.

Measured on an 8.7 s insert in a 432 s film:

```text
whole file          -1.6 -> -0.4 dBTP   over the -1.0 gate
  bed region        -3.2 dBTP           fine, and unchanged
  insert region     -0.4 dBTP           the culprit, 8.7s of 432
```

**Measure per region, not just per file.** The fix is the same static gain the
bed already gets, applied to the insert regions only — `tools/audiomix.py
--source-gain-db`, the mirror of `--bed-gain-db`. Pulling the *whole* film down
would work too and is worse: it quietly re-levels music whose gain was already
decided and documented.

Do not reach for a limiter here. The insert's dynamics are the reason it is in
the film.

### And check the insert is actually audible

A source-audio region is the one part of a cut where a silent input fails
**silently**: the bed is muted there by design, so a missing audio track sounds
exactly like a working pause until somebody plays it. It happened here —
`yt-dlp -f 401` is video-only, so the insert rendered as digital silence and
every anchor, duration and sync check still passed.

```python
# the pause must be LOUD, not just present
rms = 20*log10(rms(pcm(out, pause_in, pause_len)))   # -240 dB is the bug
```

Assert a floor on the region's RMS, and assert its correlation against the bed
is ~0. The first catches a silent insert; the second catches the bed leaking
into a region that was supposed to be a pause. Neither is implied by the other.
