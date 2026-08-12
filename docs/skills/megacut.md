---
name: megacut
version: "1.2"
last_updated: "2026-08-12"
id: megacut
one_line_purpose: Join finished cuts into one programme with deck-format chapter cards.
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
  intro sequence, a playlist, `UPLOAD/README.md`)

## When NOT to Use

- Building a cut from indexed shots → [`editing.md`](editing.md)
- Putting names on people → [`plates.md`](plates.md)
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
# 1. Chapter cards: the deck's title card, one PNG each
python3 tools/plate.py render --manifest renders/<name>-cards.json \
    --out-dir renders/plates-<name>-cards

# 2. Check the graph before paying for the encode
python3 tools/megacut.py renders/<name>.json --dry-run

# 3. Assemble
python3 tools/megacut.py renders/<name>.json
```

The plan is an ordered list of two kinds of item:

```json
{
  "output": "renders/<name>.mp4",
  "items": [
    {"kind": "card", "image": "renders/plates-x/plate_card0.png", "dur": 5.0},
    {"kind": "clip", "path": "renders/segment.mp4", "audio": "silent"},
    {"kind": "clip", "path": "/abs/path/deliverable.mp4", "audio": "source"}
  ]
}
```

`audio` has no default **on purpose**. A clip that silently defaulted to
silence would ship a mute segment that looks fine in every log, so the tool
refuses a clip that does not say which it is.

## One pass, not two

The obvious implementation normalises each segment to a temp file, then
concatenates the temps. That encodes every frame **twice**. `tools/megacut.py`
builds a single `filter_complex` instead: decoded once, encoded once.

## What has to be normalised, and why

Segments genuinely disagree, so *some* re-encode is unavoidable:

| Property | Rule | Why |
|---|---|---|
| Frame rate | **60000/1001** | Real sources here run 30/1, 60/1 and 60000/1001. 30 would throw away the 60fps material; 60/1 makes 59.94 material drift against its own audio. |
| Audio | 48 kHz 5.1, **unprocessed** | The audio tenet: no normaliser, no limiter, no EQ. |
| Silence | **Generated**, length probed | `concat` needs every segment to carry both streams. A silence source one frame short desynchronises everything after it. |
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
- **Chapter card copy is reproduced, never authored.** Cards use the deck's
  closed `title` / `subtitle` / `body` shape. A card whose words nobody has
  written is omitted and recorded — see [`plates.md`](plates.md).
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

- Duration equals the sum of the parts.
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
cp <master> ~/Videos/UPLOAD/<NN>-<name>.mp4
cd ~/Videos/UPLOAD
ffmpeg -v error -xerror -i <NN>-<name>.mp4 -f null -   # verify the STAGED copy
md5sum <NN>-<name>.mp4 >> CHECKSUMS.md5 && md5sum -c CHECKSUMS.md5
```

Then update `UPLOAD/README.md`: the table, the true-peak list, and the master
that regenerates it. A staged file with no row is a file nobody can trace.

**Ask what the programme duplicates.** Its segments are usually already staged
as standalone cuts, and `UPLOAD/` sorts lexically into playlist order — so
shipping both shows the same footage twice. That is an ordering decision and it
belongs to the owner, so **stage the file but leave it out of `yt-refresh.py`'s
`VIDEOS` list** until they choose. Staging publishes nothing; the `VIDEOS` list
does.
