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

**What the root-cause hunt established (#88).** The trigger died with the
hand-assembled master it was found on; the scripted rebuild
(`scripts/build_efmb.py`) does not reproduce it. Established by measurement,
not assumed:

- The rebuilt act passes the issue's exact spellings — `-vf`, `-filter_complex`,
  and `-filter_complex` + `-fps_mode cfr` — at full length on ffmpeg 8.1 and
  9.0.1, as does the act's own source compilation.
- The issue's "possibly relevant" timescale (`1/15360` with 512-tick frames)
  is **refuted**: the rebuilt file carries the same pairing and is healthy, and
  acts III and VII carry it too and never failed. It is just this host's normal
  MP4 video timescale at 30/60 fps.
- Sixteen synthetic pathologies a hand assembly could have left — stream-copy
  concats of input- and output-seeked cuts, a concat-filter build, timestamp
  jitter, duplicate-pts bursts, edit-list offsets, a forced 90000 timescale,
  negative CTS, mkv and mpegts round-trips, a 23.98-in-a-30-container mismatch —
  all produce **identical** durations under both spellings.
- ffmpeg 8.1 → 8.1.2 (the binary in use at the time) changed nothing in the
  timestamp path, and the 8.1 CLI source feeds identical frames to both graph
  forms for this chain shape.

So the rule stands as insurance, and the failure mode that actually burned the
programme — **silence** — is what the tool now removes: `assemble()` fails the
build if any segment's video extent disagrees with its source by more than
0.25 s, or if the joined programme disagrees with the plan's sum. The check
measures the **video stream's own** last-frame end, not the container
duration: the re-timed segment's audio leg stayed whole, so only a video-only
measurement saw the loss.

## What has to be normalised, and why

Segments genuinely disagree, so *some* re-encode is unavoidable:

| Property | Rule | Why |
|---|---|---|
| Frame rate | **60000/1001** | Real sources here run 30/1, 60/1 and 60000/1001. 30 would throw away the 60fps material; 60/1 makes 59.94 material drift against its own audio. |
| Audio | 48 kHz 5.1, **unprocessed** | The audio tenet: no normaliser, no limiter, no EQ. The one exception is an explicit fade the plan states (below). |
| Silence | **Generated**, length probed | Every segment must carry both streams. A silence source one frame short desynchronises everything after it. |
| Colour | BT.709, written into the VUI | See the trap below. |

## Fades at the joins (issue #105)

Measured on v0.6 with `tools/transitions.py`: every act join was the same
shape — the outgoing act faded (or cut) to digital silence, the slide held
4–14 s of absolute `-inf`, and the next act entered dry, up to −15 dB one
second after the slide. The fix lives in the plan, not in a hand-render:

- A clip item may carry `fade_in` / `fade_out` in **seconds on the ACT FILM
  clock** — `fade_in` starts at the clip's own 0, `fade_out` ends at the
  clip's own end, so a fade can never drift when the running order moves.
- The segment encode appends `afade` after `aresample`/`aformat`. With no
  fades declared the chain is byte-identical to before (a test pins this).
- A `fade_out` needs the clip's length, so it probes the **video** stream
  when no `dur` is authored — the container duration can be the audio stream
  outrunning the picture, and a fade placed against that starts early.
- Cards and silent clips cannot carry fades: fading generated silence is a
  no-op that reads as a treatment, so the plan validator refuses it. A slide
  that should carry sound is a licensing decision (a bed), not a fade.

`tools/transitions.py <plan> --measure <built.mp4>` is the before/after
check: per-second RMS around every join, the silence-run length, and each
act's exit and entry level — all on the **programme clock**, with the tool
saying so in its header.

