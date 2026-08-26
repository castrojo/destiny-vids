---
name: hero-videos
version: "1.3"
last_updated: "2026-08-26"
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
  when a hero video needs a pass, or when adding a QR card or URL
  wordmark to a hero cut.
metadata:
  type: procedure
  context7-sources:
    - /websites/ffmpeg_documentation
---

# Hero videos

## When to Use

- Any pass over `~/Videos/Wolves/Hero/` character sources (including RAFI and
  Lakshmi) — a new video, a re-render, a composition change
- Adding, moving or restyling corner furniture (a QR card, a URL wordmark)
- Keying a paper-background animation to transparency

## When NOT to Use

- The encode mechanics themselves → [`farm.md`](../farm.md)
- Building or checking a music bed → [`audio/SKILL.md`](../audio/SKILL.md)
- Guardian nameplates and chat plates → [`plates/SKILL.md`](../plates/SKILL.md)

## Core Process

The record is `stories/rafi-hero-qr.json`. It carries the frame, shared
`placement`, global fallback `cards`, the `wordmark`, and a `videos` map holding
each video's own `character` block. A character's optional `x_offset` defaults
to zero; it changes foreground placement, not corner furniture. A video may
override the fallback with per-video static cards. Timed-card playlists retain
their exact frame intervals and do not add a persistent card beneath them.
**The builder reads the record; nothing is hand-placed.**

1. Measure the source, bed, title treatment, fill seeds, and character union in
   Argo; record every source-specific result in the matching `verify-notes.md`.
2. Build and test the full-frame overlay from the record.
3. In Argo, derive the alpha from a verified full-frame fill, preserve original
   colour pixels, apply any completed-art closing still alpha, then crop, scale,
   position, and uniformly retime the source.
4. Mux the measured bed once, then perform all decode, audio, metadata, and
   delivered-frame checks in Argo.

```bash
cd ~/src/dv-hero-videos
python3 scripts/build_rafi_hero_overlay.py --video rafi01 \
    --out renders/rafi01-overlay.png
python3 -m pytest tests/test_rafi_hero_overlay.py -q
cp renders/rafi01-overlay.png ~/Videos/Wolves/Hero/.work-rafi01/
kubectl create -f ~/Videos/Wolves/Hero/.work-rafi01/rafi01-encode-v4.yaml
```

Then mux the bed unchanged, and verify in Argo. The bed defines
`target_frames = round(T * 24)`; uniformly retime the complete source with
`setpts=(target_frames/source_frames)*PTS`, explicitly emit 24 fps, and do not
cut, loop, or hold the ending to fit. Full detail — the filter graph, and the
per-video measurements you must take before writing one:
[references/keying-and-composition.md](references/keying-and-composition.md).
FFmpeg documents `setpts` as modifying video PTS and `fps` as converting to the
specified constant frame rate by dropping or duplicating as needed
(source: `/websites/ffmpeg_documentation`).

## Thumbnails

Build thumbnails from the supplied, finished hero still—not an extracted frame
from the picture or delivery video. The owner-supplied `detail` and `label`
fields map to the canonical Bluefin status plate. Reuse
`tools/plate.py`'s `_render_status`; its angular translucent panel, 2px blue
rule, tracking, and type ramp are the design system. Do not replace it with a
generic title box.

Deliver a 1920x1080 JPEG below 2 MB and inspect it at 336x189.

## What you must not get wrong

- **All hero `ffmpeg` and `ffprobe` work runs in Argo, never locally.** That
  includes probes, audio measurement, extraction, decode checks, and final
  verification—not only production encodes. Local Pillow/OpenCV inspection of
  already-produced PNGs and ordinary Python metadata work are allowed.
- **Keep local measurement helpers process-free.** A helper may use
  Pillow/OpenCV to measure inputs or hash returned Argo artifacts, but it must
  not shell out to a media executable or regenerate local video-derived probes.
  Record the manifest, workflow ID, and returned-artifact hashes instead.
- **`floodfill`'s `d0`/`d1`/`d2` are planar G,B,R.** `d0=0:d1=255:d2=0` renders
  BLUE — the key is `colorkey=0x0000FF`.
- **Fill before the tight crop**, and apply the matte to the **original** pixels.
  Both shortcuts fail silently: the first leaves the paper opaque, the second
  haloes the character blue.
- **Measure every number per video.** Crop boxes, title-plate masks, padding rows
  and frame counts belong to one source and never transfer.
- **Test each proposed fill seed across the source timeline.** A corner that is
  paper in the opening can become art later.
- **Use final-still alpha only for a verified completed closing interval.** It
  restores intentional transparent finishing treatment; using it earlier
  injects future art into unfinished frames.
- **Furniture goes in the corners**, never centred. Owner: *"why are you blocking
  art?"*
- **A QR is decoded off a rendered frame**, at both ends of the day/night
  crossfade. The source PNG proves nothing.
- **A thumbnail uses the finished still**, never a frame taken from the video.
- **Read the instruction literally.** "Add the URL bottom left" means *text*. It
  was built as a QR code twice before anyone re-read the sentence.

## Verification

Run all source probing, audio measurement, clean decode, `ffprobe`, and
delivered-frame extraction in the Argo workflow. Record the results in the
per-video `verify-notes.md`. Frame count and duration must match the bed within
a frame; scan the QR from real Argo-produced day and night frames. Local
Pillow/OpenCV can inspect those returned PNGs, but local `ffmpeg` and `ffprobe`
are prohibited.

- [ ] Per-video measurements and source/asset provenance are in `verify-notes.md`.
- [ ] `target_frames`, uniform `setpts` factor, 24 fps output, and effective
  speed are recorded from the measured bed.
- [ ] Argo verified decode, geometry, frame count, duration, decoded audio, and
  day/night QR frames.
- [ ] The thumbnail uses the finished still, is 1920x1080 and under 2 MB, and
  was reviewed at 336x189.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "It's a short clip, I'll just encode locally." | There is no length threshold. The workstation has been killed by this once. |
| "The crop from video 1 will be close enough." | It is measured from a different drawing. Re-derive it. |
| "The QR decodes in the mock, ship it." | The mock is not `yuv420p` at CRF 17 and 280px wide. |
| "The card doesn't touch him, so it's fine." | Competing with the art is the problem, not overlap. |

## Red Flags

- A local `ffmpeg` or `ffprobe` invocation for any hero source, audio, preview,
  or delivery check.
- A Python measurement helper that hides a local media-tool invocation behind
  `subprocess`, or presents a historical local probe as current reproduction.
- A source timeline fitted with `tpad`, a tail trim, loop, or editorial hold
  instead of one bed-driven retime.
- A fill seed accepted from a single frame, or final-still alpha switched in
  before complete artwork.
- A per-video card, x offset, crop, or thumbnail measurement copied into a
  different hero's record.
- Calling a provisional visual preview a picture, mux, or final delivery.
