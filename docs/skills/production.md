---
name: production
version: "1.1"
last_updated: "2026-08-12"
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
| 5 | **tag** | `tags/<id>.json` exists *and* `worksheet.py check` passes |
| 6 | assemble segments | never — it is cheap and idempotent |
| 7 | finish: a **cut**, or the **uncut** credited build | nothing asked for |

## Two ways to finish

Which one applies is a property of the footage, not a preference:

```bash
scripts/make_video.sh 3 --outline stories/yt_foo.txt   # CUT
scripts/make_video.sh 3 renders/roster.json            # UNCUT, credited
```

- **Cut** — `tools/story.py` picks clean shots out of the index and orders them
  to an outline. It draws **only** from the clean pool, so a trailer full of
  HUD and title cards is fine: the unusable material is never chosen. This is
  the path for almost every trailer.
- **Uncut** — the whole video, credited end to end. Right for a cinematic that
  already tells its story. `tools/uncut.py` does not filter on `clean`, by
  design, which is why stage 7 checks before it builds.

`make_video.sh` picks up `stories/<video_id>.txt` automatically if it exists.
Writing the outline is editorial work; the script does not invent one.

## The gate at stage 7

`build_uncut_credited.sh` renders the **whole** video and credits it. That is
right for a cinematic — the source already tells the story, and
`redactions/<video_id>.json` trims publisher copy off the head and tail. It is
exactly wrong for a trailer whose unclean beats are scattered HUD and title
cards, because rendering the whole thing puts every one of them on screen.

So `make_video.sh` checks before it builds, and **fails closed**:

- An unclean beat that survives redaction **whole** → refuse, and point at the
  cut path.
- An unclean beat a redaction boundary **cuts through** → refuse *unless* that
  redaction record names the segment in `acknowledges`.

That second case is the one the index cannot resolve alone: tags are beat-level
and redaction is frame-level, so on Curse of Osiris the last beat is clean
footage that dissolves into a logo card, and the 163.6s cut removes exactly the
card. Trusting *every* straddle would be too generous — a head cut made for a
ratings card would silently grandfather an unrelated HUD beat that happens to
overlap it. `acknowledges` makes the trust explicit, per beat, in a file you
edit by hand.

A video that refuses here does not need the gate relaxed. It needs cutting.

## Delivering a finished cut

A render in `renders/` is not a deliverable. The delivery workspace is
**`~/Videos/Wolves/`** — the owner's, not this repo's, and output only: every
file in it is a regenerated artifact.

| Folder | What goes in it |
|---|---|
| `Prod/` | The show at the **highest quality that exists** — one file per act, `NN-<act>.mp4`, FLAC audio, picture never re-encoded |
| `10mb/` | Social copies under a byte cap (`tools/social.py`), built from `Prod/` |
| `megacut/` | The final movie, and nothing else (`tools/megacut.py`) |
| Publish | `python3 ~/Videos/yt-refresh.py` — one unlisted playlist |

**The order is [`docs/running-order.md`](../running-order.md)'s, not the
filenames'.** `NN-` is the act number, which is fixed: acts II and VIII have no
film, so the numbering has gaps and closing them would renumber the show.

**`Prod/` is hardlinks** to each project's master, so it costs no disk and
cannot drift from what built it. Re-link with `ln -f`; `cp` over an existing
entry breaks the link silently and leaves a copy that goes stale.

`~/Videos/UPLOAD/` was the older staging folder — a different order, AAC copies.
It has been superseded and emptied of everything load-bearing; its removal is
[issue #81]. **Nothing is staged there any more.** If you find a doc or a script
that still writes to it, that doc or script is the bug.

### The per-project contract

Each act is built by its own project directory under `~/Videos/<project>/`, and
`Prod/` hardlinks to what that project produced. Read these **before** touching
a cut — they exist so nobody re-derives the analysis:

1. `STORYBOARD.md` — the scene, the source and in/out points, every decision and
   why, and which file is the shipped deliverable.
2. `render/run-<name>.sh` — the build, and the primary technical record: overlay
   cue times, geometry, colour, audio treatment. **Its defaults always rebuild
   the shipped file.** If they don't, that is a bug, not a variant.
3. `render/` — plates, avatars, music beds, and the scripts that made them.
4. `sources/` — downloaded originals. Large; never re-download needlessly.

A variant is an **environment override**, never an edit:
`MUSIC=… SFX=… OUT=… ./render/run-natali.sh`. That is what keeps "the default
rebuilds what shipped" true, and it is how the `-hq` lossless masters are built
alongside the deliverables (`SURROUND=0 ACODEC=flac OUT=…`).

Three rules there that this repo has to respect:

- **A regenerated file is not hand-edited.** The delivery notes name
  `renders/<video_id>-credited.mp4` as the master for the contributors piece and
  says so explicitly: it is rebuilt from checked-in data by
  `scripts/build_uncut_credited.sh`, so **a new month is a new render, not a new
  edit**. Fix the tag, the vocab or the redaction and re-run.
- **Share the playlist, never a video URL.** YouTube cannot replace a video
  file — a re-upload always gets a new ID — so a playlist link is the only
  stable handle. `yt-refresh.py` hashes each file and uploads only what changed.
  It resolves each cut by its **act number** out of `Prod/`, so the order it
  publishes is the running order. An upload costs ~1600 of the default 10,000
  daily quota units (about six a day); `403 quotaExceeded` means wait for the
  midnight Pacific reset.
- **Titling is the owner's call.** The contributors piece is delivered but
  deliberately not in `yt-refresh.py`'s manifest, because adding it means
  choosing its title and description ([issue #41]). That is the same class of
  stop as a casting decision: deliver it, say so, stop.

[issue #41]: https://github.com/castrojo/destiny-vids/issues/41
[issue #82]: https://github.com/castrojo/destiny-vids/issues/82
[issue #81]: https://github.com/castrojo/destiny-vids/issues/81

Delivery is also where the audio rules bite, and they are not this repo's:
load **`audio-quality-tenet`** before touching a deliverable's audio. What has
already been learned the hard way and must not be re-learned:

- The bed's gain is **derived from its measured true peak**, never hardcoded and
  never normalised. `tools/redact.py`'s `gain_for_headroom` exists because a
  hardcoded `0.9` shipped a **+0.5 dBTP** clipping master.
- **That alone is not enough: check the DELIVERED peak, not the bed's.** A lossy
  encoder reconstructs inter-sample peaks above the samples it is given, so a
  mix measuring −1.1 dBTP came back from AAC at **+0.3 dBTP** — clipping, from a
  chain correct at every earlier step. How much it overshoots depends on the
  material (0.2 dB on one bed, 1.5 dB on another). `redact.py` now measures the
  output and re-runs at a corrected **static** gain until it has headroom;
  corrections only go down and stop at the first safe result, because the
  overshoot is not monotonic in the gain. A FLAC build of the same cut lands on
  target in one pass, which is how you know it is the encoder.
- The contributors piece is **stereo AAC on purpose**; the Guardian intros are
  5.1. Do not "fix" one into the other.
- **Source a bed by codec, not by bitrate.** Sorting candidate downloads on raw
  bitrate picks a 44.1 kHz AAC rung over a 48 kHz Opus one whenever the AAC
  number is bigger, and that rung is brickwalled around 15 kHz and forces a
  needless resample. Fetch with `~/Videos/audio-source.sh`, which pins
  `-S "acodec:opus,asr,abr"` and records provenance. A 44.1 kHz bed is the
  fingerprint of having got this wrong.
- **Never take a `-drc` rung.** YouTube offers `251-drc` beside `251`: same
  codec, same bitrate, **dynamic range compressed**. A bare `-f ba -S acodec:opus`
  can select it, and taking it means the pipeline shipped compression it
  forbids — the artist's dynamics lost before the first edit, invisibly, because
  every other check passes. Ask for the rung by number (`-f 251`) when the
  ladder offers both, and confirm what was chosen in yt-dlp's own output.
- **Gate the file you actually ship.** Act VII's lossy deliverable measured
  −1.0 dBTP and passed for weeks while its FLAC master clipped at **+0.3**
  ([issue #82]) — the gain correction had been applied to one and never the
  other, and nothing measured the master because the standing report scanned the
  wrong folder. A check that runs over yesterday's staging directory is not a
  gate.
- `ACODEC=flac` builds a **lossless master** alongside the deliverable, so a
  later fold-down starts from the bed rather than from a lossy file. The
  default stays `aac`, and the defaults must keep rebuilding the shipped file.
  The standard is
  [`references/audio-standard.md`](references/audio-standard.md) — thresholds,
  the delivery band, the sourcing rule, and the two failures that have actually
  shipped. The checker that enforces it is `~/Videos/audio-check.sh`.
- Prove it, don't assert it: `framemd5` proves an audio change touched no
  frames, an audio-stream MD5 proves a picture change touched no audio,
  `-xerror` proves the file is not truncated, `volumedetect` proves it is not
  clipping.

**Hazard: `~/Videos` is a Syncthing folder.** A remote deletion can remove a
directory while you are working in it — it has already destroyed a live
`render/` mid-session. It is a move to Trash, so check
`~/.local/share/Trash/info` before rebuilding anything.

## Where it stops, and why that is the design

**Stage 5 stops and asks a person to look at frames.** That is not a missing
feature. `clean` is the gate the whole repo rests on, it must be positively
established, and "nobody has looked at this frame" is not evidence the frame is
clean. A script that guessed here would eventually put a HUD in a finished cut.
What the stop hands over is a generated worksheet; what lets the script
continue is `tools/worksheet.py check` passing, not the file merely existing.

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

- Start each tagger from the **generated worksheet**, not an empty file:
  `tools/worksheet.py generate <video_id>` writes every beat with its keyframe
  path, its timecodes, and `null` for every value, so batch output is
  comparable by construction. `make_video.sh` stage 5 generates it when no tag
  file exists. `null` is never a default — `overlays` and `character` must be
  earned per frame (see [`indexing.md`](indexing.md)).
- `tools/worksheet.py check tags/<id>.json` reports which beats still need
  which fields, `overlays` first — progress, instead of the old binary "no
  tags yet". Stage 5 stops on this check, so a half-filled file no longer
  reaches assembly to fail there.
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
| "The delivered file needs one small fix, I'll edit it in place." | It is regenerated from checked-in data. A hand-edit is lost on the next month's render and nobody can tell it happened. |
| "I'll upload it and share the video link." | YouTube cannot replace a file. Share the playlist; `yt-refresh.py` swaps the contents. |
| "The gameplay trailer has almost nothing clean, the tagging must be wrong." | Gameplay trailers have HUD in the footage. That is what the tier is for. |
| "I'll re-run detection, it's cheap." | Beat index is positional. New detection invalidates the tag file. |
| "I'll bump `vocab/casting.yaml` while I'm here." | It names real people and every video reads it. Its own PR. |
| "The render failed, I'll hand-fix the segment." | Derived fields are recomputed. Fix the tag or the vocab. |

## A social copy is a delivery stage

```bash
python3 tools/social.py ~/Videos/Wolves/Prod/<act>.mp4 \
    --out ~/Videos/Wolves/10mb/<act>.mp4 --audio-bitrate 256
```

Social platforms cap an upload by **bytes**, so `tools/social.py` solves for the
video bitrate from the duration and the audio budget and spends exactly that in
a two-pass encode — the file lands under the cap by arithmetic, not by re-rolling
a CRF until one happens to fit. `--dry-run` prints the budget first.

Two rules, and the second is the one that gets broken:

- **Encode from `Prod/`, never from another social copy.** A copy of a copy is
  two lossy generations for no reason.
- **Re-encoding is allowed; processing is not.** No normaliser, no limiter, no
  EQ — the peak of a social copy must match its master's, and a test asserts the
  tool contains no filter that would change it. A starved music bed is the
  artifact people actually hear on a phone, so spend bitrate on audio first.

## Red Flags

- Exactly 1 beat for a cut-heavy video → the source is AV1, not H.264
  (`docs/rendering.md`). `make_video.sh` warns on the codec before this bites.
- A video whose segments are 0 clean → `overlays` was skipped wholesale.
- Two agents on one `video_id`.
- Anything under `media/`, `keyframes/` or `renders/` appearing in `git status`.
- A file hand-edited in `~/Videos/Wolves/Prod/`, or a `cp` over one of its
  entries. Every entry is a hardlink to a project's master; `cp` breaks the link
  silently and leaves a copy that goes stale. Re-link with `ln -f`.
- Any write to `~/src/website`. It is read-only from here — several agents run
  worktrees against it — and it is where the authored plate copy lives.
- Trusting a bed's measured true peak as the *delivered* peak. The encoder adds
  inter-sample overshoot; measure the output file.
- Renumbering an act, or "closing the gap" in `Prod/`'s numbering. `NN-` is the
  act number from [`docs/running-order.md`](../running-order.md): acts II and
  VIII have no film, and their numerals are load-bearing so nothing renumbers
  around them. III is `mrbobbytables` permanently.
- A music bed at 44.1 kHz, or one with nothing above 16 kHz. Both mean the
  fetch took the wrong rung. So does a format id ending in `-drc`.

## Verification

```bash
python3 tools/gaps.py
python3 -m pytest -q                  # includes committed-index integrity
python3 scripts/generate_skill_index.py --check
~/Videos/audio-check.sh --all         # gates every act in Wolves/Prod
```

`tests/test_index_integrity.py` validates every committed segment, video and
tag file against its schema. It exists because a hand-corrected
`label_source: "human"` — one word, not in the enum — sat in the index until a
rebuild failed on it.
