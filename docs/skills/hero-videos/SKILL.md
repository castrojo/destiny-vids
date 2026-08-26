---
name: hero-videos
version: "1.1"
last_updated: "2026-08-25"
id: hero-videos
one_line_purpose: Build a hero character music video from a paper-background animation.
entry_point: docs/skills/hero-videos/SKILL.md
category: media-production
status: active
dependencies:
  - farm
  - audio
tags:
  - ffmpeg
  - floodfill
  - qr
  - overlay
  - hero
  - argo
description: >-
  Key a paper-background character animation to transparency, compose the
  frame, and render on the farm. Use when working in ~/Videos/Wolves/Hero,
  when a RAFI_* hero video needs a pass, or when adding a QR card or URL
  wordmark to a hero cut.
metadata:
  type: procedure
---

# Hero videos

## When to Use

- Any pass over `~/Videos/Wolves/Hero/RAFI_*` — a new video, a re-render, a
  composition change
- Adding, moving or restyling corner furniture (a QR card, a URL wordmark)
- Keying a paper-background animation to transparency

## When NOT to Use

- The encode mechanics themselves → [`farm.md`](../farm.md)
- Building or checking a music bed → [`audio/SKILL.md`](../audio/SKILL.md)
- Guardian nameplates and chat plates → [`plates/SKILL.md`](../plates/SKILL.md)

## Core Process

The record is `stories/rafi-hero-qr.json`. It carries the frame, the shared
`placement`, the `cards`, the `wordmark`, and a `videos` map holding each
video's own measured `character` block. **The builder reads it; nothing is
hand-placed.**

```bash
cd ~/src/dv-hero-videos
python3 scripts/build_rafi_hero_overlay.py --video rafi01 \
    --out renders/rafi01-overlay.png
python3 -m pytest tests/test_rafi_hero_overlay.py -q
cp renders/rafi01-overlay.png ~/Videos/Wolves/Hero/.work-rafi01/
kubectl create -f ~/Videos/Wolves/Hero/.work-rafi01/rafi01-encode-v4.yaml
```

Then mux the bed unchanged, and verify. Full detail — the filter graph, and the
per-video measurements you must take before writing one:
[references/keying-and-composition.md](references/keying-and-composition.md).

## Thumbnails

Build thumbnails from the supplied, finished `RAFI_0N.png` still—not an
extracted frame from the picture or delivery video. The two owner-supplied
fields map to the canonical Bluefin status plate: `detail` is
`APPRENTICE MAINTAINER`, `label` is `RAFAEL`. Reuse `tools/plate.py`'s
`_render_status`; its angular translucent panel, 2px blue rule, tracking, and
type ramp are the design system. Do not replace it with a generic title box.

Deliver a 1920x1080 JPEG below 2 MB and inspect it at 336x189.

## What you must not get wrong

- **Render on the farm.** `floodfill` is single-threaded; an uncapped local x264
  run OOM-killed the workstation on 2026-08-24.
- **`floodfill`'s `d0`/`d1`/`d2` are planar G,B,R.** `d0=0:d1=255:d2=0` renders
  BLUE — the key is `colorkey=0x0000FF`.
- **Fill before the tight crop**, and apply the matte to the **original** pixels.
  Both shortcuts fail silently: the first leaves the paper opaque, the second
  haloes the character blue.
- **Measure every number per video.** Crop boxes, title-plate masks, padding rows
  and frame counts belong to one source and never transfer.
- **Furniture goes in the corners**, never centred. Owner: *"why are you blocking
  art?"*
- **A QR is decoded off a rendered frame**, at both ends of the day/night
  crossfade. The source PNG proves nothing.
- **A thumbnail uses the finished still**, never a frame taken from the video.
- **Read the instruction literally.** "Add the URL bottom left" means *text*. It
  was built as a QR code twice before anyone re-read the sentence.

## Verification

```bash
ffmpeg -v error -i <deliverable> -f null -                 # clean decode
ffmpeg -i <deliverable> -af ebur128=peak=true -f null -    # dBTP + LUFS
```

Frame count and duration must match the bed within a frame. Then scan the QR off
a real frame — see the reference.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "It's a short clip, I'll just encode locally." | There is no length threshold. The workstation has been killed by this once. |
| "The crop from video 1 will be close enough." | It is measured from a different drawing. Re-derive it. |
| "The QR decodes in the mock, ship it." | The mock is not `yuv420p` at CRF 17 and 280px wide. |
| "The card doesn't touch him, so it's fine." | Competing with the art is the problem, not overlap. |
