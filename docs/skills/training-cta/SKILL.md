---
name: training-cta
version: "1.0"
last_updated: "2026-08-28"
id: training-cta
one_line_purpose: Replace picture with the approved LF training CTA while preserving audio.
entry_point: docs/skills/training-cta/SKILL.md
category: media-production
status: active
dependencies: []
tags:
  - cta
  - linux-foundation
  - training
  - video
description: >-
  Use when a Bluefin video should replace its remaining picture with the
  approved Linux Foundation training card while the source audio continues.
metadata:
  type: procedure
  context7-sources:
    - /websites/ffmpeg_documentation
---

# Linux Foundation training CTA

## When to Use

A Bluefin video should end its real picture at an authored mark
(`takeover.source_at`) and hold the approved Linux Foundation training card
full-frame through EOF, while the source audio keeps playing. The approved
asset is the committed `assets/cta/linux-foundation-training-forest.png`
(1920x1080, pinned by SHA-256 in `tests/test_standalone.py`).

## When NOT to Use

- A generic title card, ending card, or thumbnail — use `plates`.
- Anything off-screen: upload descriptions, captions, links.
- Changing the CTA copy or artwork. The asset is approved; a change is a new
  asset with a new digest, not an edit.

## Core Process

1. Use the committed asset, never a workspace copy. The regression test pins
   its bytes; if the hash disagrees, the file in the repo is the one that is
   wrong.
2. Convert the authored `takeover.source_at` to output time through the
   excisions (`tools/standalone.source_to_output`) before cutting anything. A
   mark inside a removed range is an error, not an approximation.
3. Overlay the still at `0:0` full-frame from the converted mark to EOF.
4. Preserve the source audio untouched — no re-encode, no ducking, no restart.
5. Bound the looped still (`-loop 1`) with `shortest=1` so the picture ends
   with the audio instead of hanging on a frozen card.

## Common Rationalizations

- "This video needs its own CTA copy" — no. One approved card for every
  video; per-video copy is a new approval, not a parameter.
- "A fade would look nicer" — not by default. The approved treatment is a
  straight cut to the card.
- "The audio under the CTA is boring, let's swap in music" — the audio is
  the source's; this skill touches picture only.

## Red Flags

- The asset on disk hashes differently than the pinned digest.
- Audio is muted, ducked, or restarts at the takeover mark.
- An unbounded still that outlasts the audio track.
- The takeover mark placed by output time without passing through the
  excision map.

## Verification

- `sha256sum assets/cta/linux-foundation-training-forest.png` matches the
  digest pinned in `tests/test_standalone.py`.
- Extract a frame after the takeover mark and confirm the card is on screen.
- Probe audio before and after the mark and confirm the waveform continues
  correlated — same track, no seam.
