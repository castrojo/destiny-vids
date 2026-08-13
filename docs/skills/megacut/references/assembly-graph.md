# The assembly graph: segments, the join, and normalisation

Part of the [megacut skill](../SKILL.md).

## Segments, then a join — and still one generation

`tools/megacut.py` normalises each item to its own temporary segment and joins
them with the **concat demuxer**. It used to build one `filter_complex` over
every input at once, to avoid encoding each frame twice.

**That does not run on a real programme.** Fourteen inputs and half an hour of
1080p: ffmpeg buffers the inputs `concat` is not consuming yet, climbs to ~2 GB
resident, then **deadlocks** — every thread in `futex_do_wait`, 0% CPU, no
output growth. Measured twice, at two presets, stalling at the same point.
A fourteen-input graph over *short* inputs completes fine, so it is the
duration behind the inputs, not the shape of the graph.

The generation count is unchanged, which is the part worth protecting:

- **Video is encoded once.** Segments carry the plan's own `crf`/`preset`; the
  join is `-c:v copy`. It costs disk, briefly, not quality.
- **Audio is encoded once.** Segments carry lossless **24-bit PCM**, so the one
  AAC encode happens at the join, across the whole programme. Encoding AAC per
  segment and copying would give every cut its own encoder delay and padding —
  a tick at every join.
- **PCM, not FLAC**, in the segments. FLAC keeps its STREAMINFO in the stream's
  extradata, and the concat demuxer binds the first file's extradata to the
  whole joined stream: every later segment then fails to decode with
  `Invalid data found when processing input`.

### A clip is filtered with `-vf`, never `-filter_complex`

This one cost a whole rebuild and is invisible in every log. On one act — 30
fps, container timescale 1/15360 — the *identical* chain gave:

| Form | Result |
|---|---|
| `-vf "scale…,fps…,setpts…"` | **307.99 s** ✅ |
| `-filter_complex "[0:v]scale…,fps…,setpts…[v]"` | **299.48 s**, `drop=505` ❌ |

The filtered timestamps were rescaled and the frames that collided were
discarded. ffmpeg exited **0** and reported the full frame count going *in*.
The programme came out 8.5 s short and **every act after that one started
early**, which is how it was caught: the act slides no longer landed where the
plan said. Cards keep the graph form, because they need `lavfi` sources and are
stills whose durations are authored rather than carried.

`concat=n=1` on a single-item segment is not a harmless no-op either — it
re-times the same file the same way. The join is a demuxer, not a filter.

## What has to be normalised, and why

Segments genuinely disagree, so *some* re-encode is unavoidable:

| Property | Rule | Why |
|---|---|---|
| Frame rate | **60000/1001** | Real sources here run 30/1, 60/1 and 60000/1001. 30 would throw away the 60fps material; 60/1 makes 59.94 material drift against its own audio. |
| Audio | 48 kHz 5.1, **unprocessed** | The audio tenet: no normaliser, no limiter, no EQ. |
| Silence | **Generated**, length probed | Every segment must carry both streams. A silence source one frame short desynchronises everything after it. |
| Colour | BT.709, written into the VUI | See the trap below. |

