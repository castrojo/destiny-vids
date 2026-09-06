---
name: hero-videos
version: "1.8"
last_updated: "2026-09-06"
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
    - /websites/opencv_4_13_0
    - /argoproj/argo-workflows
    - /python-pillow/pillow
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

1. Measure the source, title treatment, fill seeds, and character union in
   Argo; record every source-specific result in the matching `verify-notes.md`.
   If an audio source is authorized, first submit the remote-only
   [bed workflow](references/authorized-audio-on-argo.md#stage-1--bed-workflow).
   It has no picture dependency and returns the gated, native-rate PCM bed and
   its record without using a local media command.
2. Build and test the full-frame overlay from the record.
3. In Argo, derive the alpha from a verified full-frame fill, preserve original
   colour pixels, apply any completed-art closing still alpha, then crop, scale,
   position, and uniformly retime the source.
4. Submit the separate
   [mux/validation workflow](references/authorized-audio-on-argo.md#stage-2--mux-and-validation-workflow).
   It hash-verifies the picture and original bed, applies one candidate static
   gain, makes one AAC encode, and performs all decode, audio, metadata, and
   delivered-frame checks in Argo. Re-submit from the original bed when a
   decoded candidate needs a different gain; never use a prior AAC candidate.

```bash
cd ~/src/dv-hero-videos
python3 scripts/build_rafi_hero_overlay.py --video rafi01 \
    --out renders/rafi01-overlay.png
python3 -m pytest tests/test_rafi_hero_overlay.py -q
cp renders/rafi01-overlay.png ~/Videos/Wolves/Hero/.work-rafi01/
kubectl create -f ~/Videos/Wolves/Hero/.work-rafi01/rafi01-encode-v4.yaml
```

Then use the separate mux/validation workflow against the verified bed and
picture, and verify in Argo. The bed defines
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

- **Report deliverables from the `Hero/` root.** A rough cut or final
  master the owner is meant to open is promoted (hardlink or copy) to
  `~/Videos/Wolves/Hero/` and that root path is what you report — never
  only a hidden `.work-*` path. Owner correction, 2026-09-05.
- **All hero `ffmpeg` and `ffprobe` work runs in Argo, never locally.** That
  includes probes, audio measurement, extraction, decode checks, and final
  verification—not only production encodes. Local Pillow/OpenCV inspection of
  already-produced PNGs and ordinary Python metadata work are allowed.
  **There is no local fallback** (owner, 2026-09-05): if Argo fails, report
  and retry remotely—never run the media step on the workstation, whose
  memory this rule exists to protect.
- **Keep local measurement helpers free of media-container decoders.** They may
  hash containers as opaque bytes and use Pillow/OpenCV only on supplied stills
  or Argo-returned PNGs. They must never open a video or audio container—not
  through a shell command, `cv2.VideoCapture`, imageio readers, PyAV, or any
  linked-library reader. Record measurements as recorded values plus the Argo
  manifest, workflow ID, and returned-artifact hashes instead.
- **`floodfill`'s `d0`/`d1`/`d2` are planar G,B,R.** `d0=0:d1=255:d2=0` renders
  BLUE — the key is `colorkey=0x0000FF`.
- **Fill before the tight crop**, and apply the matte to the **original** pixels.
  Both shortcuts fail silently: the first leaves the paper opaque, the second
  haloes the character blue.
- **Measure every number per video.** Crop boxes, title-plate masks, padding rows
  and frame counts belong to one source and never transfer.
- **Test each proposed fill seed across the source timeline.** A corner that is
  paper in the opening can become art later.
- **Outer paper and enclosed paper pockets are different masks.** Edge seeds
  deliberately preserve enclosed white. If a pocket between limbs or equipment
  is paper, add a measured per-video interior seed and re-check the whole
  timeline; never restore the global colorkey that erases white artwork too.
- **Use final-still alpha only for a verified completed closing interval.** It
  restores intentional transparent finishing treatment; using it earlier
  injects future art into unfinished frames.
- **A design-sheet crop is evidence, not display art.** Equipment shown on
  screen must be a reviewed transparent component extracted from a
  source-backed RGBA asset. Quarter-turn tall equipment only after extraction,
  then re-measure its fit.
- **Wordmark validation is source-specific.** A pinned website mark and the
  legacy no-argument fallback may have different geometry and color contracts;
  pass each source's invariants explicitly, preserve the fallback's URL/output/
  width behavior, and cover both paths with offline fixtures. Never commit a
  fetched website asset.
- **A staged wordmark is a content-addressed input.** The record must carry
  the pinned source URL and source digest, its preserve-colors policy and
  raster width, plus the derived PNG dimensions and digest. Fetch it through
  the shared wordmark helper only when absent; an existing PNG whose
  dimensions, alpha, lettering/fin colors, or digest do not match is stale and
  must fail the builder. The Argo fetch step repeats the digest check after
  staging rather than trusting the transport.
- **Pillow preflight is still-image review only.** Load actual day/night stage
  faces and RGBA cards, use `Image.alpha_composite` for one-card-at-a-time
  composites, and write two contact sheets so every card can be reviewed in
  the real bottom rail. These sheets catch alpha, clipping, and contrast
  regressions; they are not evidence for the live band or keyed children and
  must never decode a video locally.
- **Keep both synthetic and source-backed card coverage.** Offline CI should
  retain a small synthetic RGBA fit test. When `~/Videos/Wolves/Hero` exists,
  a separate local regression must run the complete merged catalog through
  extraction and card rendering, fail on any real-source error, verify
  context transparency and rotations, and prove text-only entries write no
  art. The local regression skips only when the Hero asset root is absent.
- **Equal boxes do not mean equal characters.** In an ensemble, measure each
  returned proof's visible alpha area, balance visual weight within the
  available stations, and measure again after every matte change.
- **A raster bbox cannot report clipped copy.** Calculate card extents before
  drawing, fail on overflow, and omit a side leader when long copy widens
  beneath horizontal art.
- **Retained PVCs retain scratch mistakes too.** Truncate generated concat
  lists and similar append-only files before rebuilding them.
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

When `podGC` removes successful pods, the workflow must upload a text
probe/decode record alongside its media and review PNGs. Inspect the encode log
in its first minute for graph failures, but do not rely on Argo logs remaining
available after success.

Make every expected output value a workflow parameter or a value derived from
`target_frames`: derive duration as `target_frames / 24`, derive review indices
in the workflow shell, and use the same values in both probes and extraction.
Decode with `ffmpeg -xerror -v error -i <output> -f null -`, capture stderr
into an uploaded record, and write a decode PASS only after its zero exit.
Probe all streams: include `format=nb_streams,duration`, require one stream,
and explicitly fail if any `codec_type=audio` appears in the recorded probe.

- [ ] Per-video measurements and source/asset provenance are in `verify-notes.md`.
- [ ] `target_frames`, uniform `setpts` factor, 24 fps output, and effective
  speed are recorded from the measured bed.
- [ ] Argo verified decode, geometry, frame count, duration, decoded audio, and
  day/night QR frames.
- [ ] Ensemble proofs were re-measured after the final matte and their visible
  alpha areas match the authored visual-weight target.
- [ ] Every rendered card contains all authored copy inside its layout bounds;
  no fit decision depends on pixels already clipped by the canvas.
- [ ] The thumbnail uses the finished still, is 1920x1080 and under 2 MB, and
  was reviewed at 336x189.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "It's a short clip, I'll just encode locally." | There is no length threshold. The workstation has been killed by this once. |
| "The crop from video 1 will be close enough." | It is measured from a different drawing. Re-derive it. |
| "The QR decodes in the mock, ship it." | The mock is not `yuv420p` at CRF 17 and 280px wide. |
| "The card doesn't touch him, so it's fine." | Competing with the art is the problem, not overlap. |
| "All four stations use the same width, so they are balanced." | Wide props and sparse line art change visual weight. Count visible alpha pixels. |
| "The output bbox fits, so no copy is clipped." | A canvas cannot report pixels that were never drawn. Validate the calculated layout first. |

## Red Flags

- A local `ffmpeg` or `ffprobe` invocation for any hero source, audio, preview,
  or delivery check.
- A Python measurement helper that opens a media container through
  `cv2.VideoCapture`, imageio, PyAV, another linked library, or a shell command;
  or that presents a historical local probe as current reproduction.
- A source timeline fitted with `tpad`, a tail trim, loop, or editorial hold
  instead of one bed-driven retime.
- A fill seed accepted from a single frame, or final-still alpha switched in
  before complete artwork.
- Equal-width ensemble characters accepted without measuring their returned
  alpha footprints after the final key.
- A generated concat list appended on a retained PVC without first being
  truncated.
- A card whose only fit check is the raster alpha bbox, especially when copy
  approaches a canvas edge.
- A per-video card, x offset, crop, or thumbnail measurement copied into a
  different hero's record.
- Calling a provisional visual preview a picture, mux, or final delivery.
