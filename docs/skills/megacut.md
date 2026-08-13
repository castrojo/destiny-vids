---
name: megacut
version: "1.2"
last_updated: "2026-08-12"
id: megacut
one_line_purpose: Join finished cuts into one programme, with act slides between them.
entry_point: docs/skills/megacut.md
category: editing
mcp_compliance_level: partial
optimization_status: draft
status: active
dependencies: [plates, editing]
tags: [assembly, concat, chapter-cards, ffmpeg, programme]
description: >-
  Assembles already-finished cuts and owner-approved deliverables into one
  continuous programme, separated by the reference deck's title cards, in a
  single ffmpeg pass. Use when several cuts must play as one video.
metadata:
  type: procedure
  context7-sources:
    - /websites/ffmpeg_documentation
---

# Assembling a programme

## When to Use

- Several finished cuts must play as one continuous video
- A compilation needs chapter cards between its parts
- Reproducing a running order that is authored somewhere else (the website's
  intro sequence, a playlist) — though **this show's order is authored here**,
  in [`docs/running-order.md`](../running-order.md)

## When NOT to Use

- Building a cut from indexed shots → [`editing.md`](editing/SKILL.md)
- Putting names on people → [`plates.md`](plates/SKILL.md)
- Fitting a cut to music → [`scoring.md`](scoring.md)
- Delivering a finished file → [`production.md`](production.md)

## Assembly is not editing

This stage **joins finished things**. It never re-cuts, re-times or re-grades
one. Every item it is handed is either a rendered cut from this repo or an
owner-approved deliverable, and if one of them is wrong the fix belongs
upstream, in the thing that made it — not here.

That boundary is what makes the tool safe to re-run: the programme is a
**regenerated artifact**, so it is rebuilt rather than patched, exactly like
every other render in this repo.

## Core Process

```bash
# 1a. Chapter cards, deck format (title / subtitle / body): a Python plate
python3 tools/plate.py render --manifest stories/<name>/<name>-cards.json \
    --out-dir renders/plates-<name>-cards

# 1b. Full-frame cards (`kind: act`, `kind: comic`): the SITE'S OWN CSS in a
#     real browser. Do not port one into Pillow -- see "Cards are reproduced".
ln -sfn ~/src/website/node_modules node_modules      # playwright is not vendored
node cards/render-cards.mjs --manifest stories/<name>/<name>-cards.json \
    --out-dir renders/plates-<name>-cards

# 2. Check the graph before paying for the encode
python3 tools/megacut.py stories/<name>/<name>.json --dry-run

# 3. Assemble
python3 tools/megacut.py stories/<name>/<name>.json
```

Both renderers write `plate_<id>.png` into the same directory and each skips
what the other owns, so a manifest may mix them — the Wolves hero segment
carries six Guardian plates *and* the comic title card, and `burn` reads one
plates-dir without caring which tool drew which file.

## Cards are reproduced, not designed

A card that exists on the website is **rendered from the website's own rules**.
`cards/act.html` and `cards/comic.html` copy the CSS out of
`CinematicTransition.vue` and `WolvesIntroOverlay.vue`, and
`cards/render-cards.mjs` screenshots them with playwright — the same pattern
`~/Videos/wolves-{kat,natali}/render/plate.html` and
`nimbatus-review/render/endcard.html` have always used.

Re-implementing one in Pillow gets you a second, drifting version of chrome
that already exists; `tools/plate.py` refuses a card kind outright and names
the driver instead. The Python renderer is for the *deck's* shapes — the
Guardian plate, the small title card, the chat pill, the status HUD.

Two rules survive the move to a browser:

- **Copy still arrives in the manifest.** A row nobody authored is left out of
  the URL and does not render. The card templates default nothing.
- **A CSS comment containing `*/` truncates the stylesheet**, and the card then
  renders as unstyled black text on white — which is exactly what a path like
  `wolves-*/render/reveal.html` does inside a comment. A test pins it.

The plan is an ordered list of two kinds of item:

```json
{
  "output": "renders/<name>.mp4",
  "items": [
    {"kind": "card", "image": "renders/plates-x/plate_act1.png", "dur": 5.0},
    {"kind": "clip", "path": "renders/segment.mp4", "audio": "silent"},
    {"kind": "clip", "path": "/abs/path/deliverable.mp4", "audio": "source"}
  ]
}
```

`audio` has no default **on purpose**. A clip that silently defaulted to
silence would ship a mute segment that looks fine in every log, so the tool
refuses a clip that does not say which it is.

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

## Red Flags

- **A silent segment's two legs must be equal by construction.** Generating
  silence from a probed or authored duration while the picture runs its own
  natural length is a latent desync: `concat` advances each stream's timeline
  per segment, so a mismatch drifts **every segment after it**. Pin both to one
  number. Probe the **video stream**, not the container — `format=duration`
  covers the longest stream, which is the wrong number on a file whose audio
  outruns its picture.
- **Validation and encoding must resolve a path the same way.** If the checker
  prefers the repo root and the encoder prefers the working directory, the file
  that was validated is not necessarily the file that ships.
- **`-color_primaries` alone does not tag the file.** Those flags describe the
  *frames*; x264 copies the matrix from them and leaves primaries and transfer
  `unknown`. The file then silently disagrees with every other deliverable.
  Pass `-x264-params colorprim=…:transfer=…:colormatrix=…` as well, and
  **verify with `ffprobe`** — this was caught only by probing the output against
  a known-good deliverable.
- **A card is a transparent PNG.** Flatten it onto real black with `overlay`;
  do not rely on `format=yuv420p` to drop the alpha, because the colour under a
  fully transparent pixel is undefined and can fringe.
- **"Drop the audio" is not the same as "mute it".** A source labelled *without
  dialogue* still carries the **score**; muting a segment to lose a voice-over
  throws the music away with it, and the result reads as a broken cut rather
  than an edit. If dialogue-free music is wanted, that is a different source or
  a different edit — never silence.
- **Source audio by rung, not by convenience.** Prefer the native-rate stream,
  and never take a `-drc` variant: it applies dynamic range compression, which
  the audio tenet forbids. Place stereo into 5.1 with `pan`, never `-ac`, which
  quietly rescales a finished mix.
- **When a segment's audio is a fraction short of its picture, pad it** with
  `apad` and let the picture decide the length. Cutting to the shorter stream
  drops a frame and, in a concat, drifts everything after it.
- **Never assume an anchor measured on a different upload.** In/out points are
  frame-verified per file. Two uploads of the "same" cinematic can differ by
  seconds — one here had a marketing end card the other did not.
- **Never hand-edit the assembled file.** Fix the plan or the upstream cut and
  re-run.
- **Chapter card copy is reproduced, never authored.** The deck's card is the
  closed `title` / `subtitle` / `body` shape; the act slide adds only the
  owner's `act` numeral and `chapters` list. A card whose words nobody has
  written is omitted and recorded — see [`plates.md`](plates/SKILL.md).
- **A card that exists on the site is not re-implemented.** Render it from the
  site's CSS with `cards/render-cards.mjs`; a Pillow port of chrome that
  already ships is a second version to keep in step.
- **A music bed under a silent segment is a licensing decision.** Leave it
  silent and record it; never pick a track to fill the gap.

## Verify, don't assert

A log that says `wrote …` proves nothing. Every one of these has caught a real
defect:

```bash
ffmpeg -v error -xerror -i out.mp4 -f null -        # not truncated
ffprobe -select_streams v:0 -show_entries stream=color_primaries,color_transfer,color_space
ffmpeg -ss <seg> -t <len> -i out.mp4 -map a:0 -af volumedetect -f null /dev/null
```

- **Duration equals the sum of the parts.** Not approximately: an 8.5 s
  shortfall on a 20-minute programme is one act silently truncated, and the
  file plays fine.
- **Every act slide lands where the plan says.** Cheap and decisive: extract a
  frame per second (`-vf fps=1,scale=64:36`), compare each against the rendered
  `plate_act*.png`, and print where each slide actually starts. A slide that is
  early is the act before it having been truncated.
- **Per segment**, the peak matches its source — a re-encode must not lift one.
- **Silent stretches read at the noise floor** (about −91 dB for AAC digital
  silence), not merely "quiet".
- Extract frames either side of every join **and look at them**.

## Delivering a programme

A programme is delivered like any other cut — see
[`production.md`](production.md) — with one extra question that only
compilations raise.

```bash
cd ~/Videos && ./audio-check.sh <master>     # the workspace's own gate, first
ln -f <master> ~/Videos/Wolves/Prod/<NN>-<act>.mp4
cd ~/Videos/Wolves/Prod
ffmpeg -v error -xerror -i <NN>-<act>.mp4 -f null -   # verify the delivered file
md5sum *.mp4 > CHECKSUMS.md5 && md5sum -c CHECKSUMS.md5
```

`ln -f`, **never `cp`** — `Prod/` is hardlinks to each project's master, so it
costs no disk and cannot drift. A `cp` over an existing entry breaks the link
silently and leaves a copy that goes stale. `NN` is the **act number** from
[`docs/running-order.md`](../running-order.md), not a sort key.

Then update `Wolves/Prod/README.md`: the act, and the master it links to. A
delivered file with no row is a file nobody can trace.

**Ask what the programme duplicates.** Its segments are usually already
delivered as standalone acts, so publishing both shows the same footage twice.
That is an ordering decision and it belongs to the owner, so **deliver the file
but leave it out of `yt-refresh.py`'s `VIDEOS` list** until they choose.
Delivering publishes nothing; the `VIDEOS` list does.
