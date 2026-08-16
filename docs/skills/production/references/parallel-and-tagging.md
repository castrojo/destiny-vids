# Parallel work and batch tagging

Part of the [production skill](../SKILL.md).

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

- Start each tagger from the **generated worksheet**, not an empty file:
  `tools/worksheet.py generate <video_id>` writes every beat with its keyframe
  path, its timecodes, and `null` for every value, so batch output is
  comparable by construction. `make_video.sh` stage 5 generates it when no tag
  file exists. `null` is never a default — `overlays` and `character` must be
  earned per frame (see [`indexing.md`](../../indexing.md)).
- `tools/worksheet.py check tags/<id>.json` reports which beats still need
  which fields, `overlays` first — progress, rather than a binary "no
  tags yet". Stage 5 stops on this check, so a half-filled file does not
  reach assembly to fail there.
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

