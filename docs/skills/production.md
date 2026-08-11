---
name: production
version: "1.0"
last_updated: "2026-08-11"
id: production
one_line_purpose: Run the issue-to-render loop, repeatedly and in parallel.
entry_point: docs/skills/production.md
category: editing
mcp_compliance_level: partial
optimization_status: draft
status: active
dependencies: [issues, indexing, editing, casting, plates]
tags: [pipeline, batch, parallel, make-video, resume]
description: >-
  The whole loop from an issue to a rendered cut, what resumes, where it stops
  on purpose, and how several agents make videos at once without colliding.
  Use when producing videos in volume rather than debugging one stage.
metadata:
  type: procedure
---

# Making videos in volume

## When to Use

- Taking an issue all the way to a rendered file
- Working several videos at once, or alongside other agents
- Deciding what to do first when the index is thin

## When NOT to Use

- Debugging one stage — go to that stage's skill
  ([`indexing.md`](indexing.md), [`editing.md`](editing.md),
  [`plates.md`](plates.md))
- Filing or triaging the work itself → [`issues.md`](issues.md)

## The loop

```bash
python3 tools/gaps.py                        # what is unfinished
scripts/make_video.sh 3                       # issue -> as far as it can go
scripts/make_video.sh --video-id yt_foo       # or drive it by video
```

`make_video.sh` runs the stages in order and **skips any whose output already
exists**, so re-running it after a tagging pass resumes at assembly rather than
re-fetching 200 MB:

| # | Stage | Skipped when |
|---|---|---|
| 1 | read the issue's brief | — |
| 2 | ingest a video record | `videos/<id>.json` exists |
| 3 | fetch the media (H.264) | `media/<id>.mp4` exists |
| 4 | detect beats + keyframes | `keyframes/<id>/beats.json` exists |
| 5 | **tag** | `tags/<id>.json` exists |
| 6 | assemble segments | never — it is cheap and idempotent |
| 7 | plates, dialogue, ensemble, redact, render | no roster given, or `automatable: partly` |

## The gate at stage 7

`build_uncut_credited.sh` renders the **whole** video and credits it. That is
right for a cinematic — the source already tells the story, and
`redactions/<video_id>.json` trims publisher copy off the head and tail. It is
exactly wrong for a trailer whose unclean beats are scattered HUD and title
cards, because rendering the whole thing puts every one of them on screen.
`tools/uncut.py` does not filter on `clean`, by design.

So `make_video.sh` checks before it builds, and **fails closed**:

- An unclean beat that survives redaction **whole** → refuse, and point at
  `tools/story.py`, which draws only from the clean pool.
- An unclean beat the redaction range **cuts through** → note it and continue.
  Somebody drew that boundary by hand. Tags are beat-level and redaction is
  frame-level, so this is the case the index cannot resolve alone: on Curse of
  Osiris the last beat is clean footage that dissolves into a logo card, and
  the redaction ends at 163.6s precisely to clip it.

A video that refuses here does not need the gate relaxed. It needs cutting
instead of crediting end to end.

## Where it stops, and why that is the design

**Stage 5 stops and asks a person to look at frames.** That is not a missing
feature. `clean` is the gate the whole repo rests on, it must be positively
established, and "nobody has looked at this frame" is not evidence the frame is
clean. A script that guessed here would eventually put a HUD in a finished cut.

**A brief with `automatable: no` stops at stage 1**, prints what it is waiting
on, and exits 0 — stopping is the correct result, not a failure. A brief with
`automatable: partly` runs the mechanical half and stops before the credited
build: indexing is mechanical, putting names on screen is not.

`--video-id` skips the brief entirely. That is a debugging path for a video you
already understand, not the way to run an issue — it bypasses `automatable`
with it.

Both stops print the exact next command. Neither is a state to route around.

## Stale tags

Beat index is positional, so a tag file and a detection pass agree only if they
describe the same shots — and nothing in the data says so. Re-fetch a video at
a different resolution, or change `--min-shot-sec`, and every tag slides onto a
neighbouring shot. The result still validates, and now calls a HUD-bearing beat
clean while naming a real person in a shot they are not in.

`verify_tags_match_detection` runs before any tag is replayed: it compares the
beat count, and the actual boundaries against `keyframes/<video_id>/beats.json`
from pass 1. A same-count re-detection with different cuts is the dangerous
case, and the manifest is what catches it.

## Doing several at once

One issue, one branch, one video. The stages write to per-video paths
(`media/<id>.mp4`, `keyframes/<id>/`, `tags/<id>.json`,
`segments/seg_<id>_*.json`), so two agents on two videos do not touch the same
file.

Two things are shared, and both want their own small PR:

- **`vocab/casting.yaml`** — every video reads it, and it names real people.
  A casting change buried inside a cut is a merge conflict that mis-credits
  somebody.
- **`docs/skills/*`** — a learning belongs in the PR that produced it.

Keyframes go to `keyframes/<video_id>/`, chosen from the record rather than
from the command line. Passing `--keyframes-dir keyframes/` once put one
video's `000.jpg` at the root of the tree, where the next video's `000.jpg`
overwrote it — silently, because stills are gitignored and nothing downstream
reads a filename.

## Batch tagging

Tagging is the slow stage and the only one that needs eyes, so it is the one
worth parallelizing: hand each video to its own tagger with its own context.

- Give every tagger **the same enum list and the same reference tag file**, or
  their output is not comparable across videos.
- A tagger reads *its own* `keyframes/<video_id>/beats.json`. Beat index is
  positional, and a tag file is only valid against the detection pass that
  produced it.
- Expect rejects, and expect them to differ by source: a cinematic rejects a
  handful of title and rating cards (2/50 on Curse of Osiris, 9/69 on the
  Final Shape trailer), while a **gameplay** trailer legitimately rejects far
  more, because the HUD is in the footage. A low clean count on a gameplay
  trailer is the gate working. Do not soften `hud` to raise it.

## What to work on first

`tools/gaps.py` ranks itself: an **unindexed** video contributes nothing to any
cut, so indexing one adds more usable material than reviewing the tail of a
video that already works. **uncast** leads and **untagged-character** videos
are owner decisions and visual judgement respectively — file them, do not
grind them.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll tag the obvious ones and leave the rest." | An untagged beat derives `clean = false`. Half a tag file marks half the video uncuttable. |
| "The gameplay trailer has almost nothing clean, the tagging must be wrong." | Gameplay trailers have HUD in the footage. That is what the tier is for. |
| "I'll re-run detection, it's cheap." | Beat index is positional. New detection invalidates the tag file. |
| "I'll bump `vocab/casting.yaml` while I'm here." | It names real people and every video reads it. Its own PR. |
| "The render failed, I'll hand-fix the segment." | Derived fields are recomputed. Fix the tag or the vocab. |

## Red Flags

- Exactly 1 beat for a cut-heavy video → the source is AV1, not H.264
  (`docs/rendering.md`). `make_video.sh` warns on the codec before this bites.
- A video whose segments are 0 clean → `overlays` was skipped wholesale.
- Two agents on one `video_id`.
- Anything under `media/`, `keyframes/` or `renders/` appearing in `git status`.

## Verification

```bash
python3 tools/gaps.py
python3 -m pytest -q                  # includes committed-index integrity
python3 scripts/generate_skill_index.py --check
```

`tests/test_index_integrity.py` validates every committed segment, video and
tag file against its schema. It exists because a hand-corrected
`label_source: "human"` — one word, not in the enum — sat in the index until a
rebuild failed on it.
