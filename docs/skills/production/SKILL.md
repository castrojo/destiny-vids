---
name: production
version: "1.3"
last_updated: "2026-08-27"
id: production
one_line_purpose: Take approved video work from issue brief to delivered artifact.
entry_point: docs/skills/production/SKILL.md
category: operations
status: active
dependencies: []
tags:
  - production
  - delivery
  - issues
  - workflow
  - video
description: >-
  Take approved video work from issue brief to delivered artifact. Use when an
  issue needs to run from brief, through indexing or rendering, to a file in
  the delivery workspace.
metadata:
  type: procedure
  context7-sources:
    - /addyosmani/agent-skills
---

# Making videos in volume

## When to Use

- Taking an issue all the way to a rendered file
- Working several videos at once, or alongside other agents
- Deciding what to do first when the index is thin

## When NOT to Use

- Debugging one stage — go to that stage's skill
  ([`editing`](../editing/SKILL.md),
  [`plates`](../plates/SKILL.md))

## Rule zero: deliver first, improve second

**When the owner asks for a video, the next thing you produce is a video
file.** See `AGENTS.md`, "A video now means a video now" — it is rule zero and
it outranks everything in this skill.

The loop below is a *production* loop, and its most common failure is not a bad
render. It is **no render**: an agent asked for a quick cut finds a real
structural problem on the way, fixes it properly, and surfaces hours later with
good engineering and nothing to watch. Deliver the cut, file the problem, then
fix it.

```bash
# Deliver something watchable in one command, even mid-round:
./scripts/rebuild-wolves.sh
python3 tools/megacut.py stories/megacut/megacut.json
```

An encode's ETA is measurable, so measure it rather than guessing — two `stat`
calls a few seconds apart on the growing output give the rate. **A question
about timing gets a time.**

## Core Process

```bash
python3 tools/gaps.py
scripts/make_video.sh 3
scripts/make_video.sh --video-id yt_foo
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
  to an outline. It draws **only** from the clean pool.
- **Uncut** — the whole video, credited end to end. Right for a cinematic that
  already tells its story. `tools/uncut.py` does not filter on `clean`, by
  design, which is why stage 7 checks before it builds.

`make_video.sh` picks up `stories/<video_id>.txt` automatically if it exists.
Writing the outline is editorial work; the script does not invent one.

Standalone sequel titles keep the series construction and add a Roman numeral:
`Bluefin and the Hive II`, not `Bluefin in the Hive II`. The episode number
changes; the established title wording does not.

### Rebuilt non-act segments

Perfume movements and other `renders/` items have no act numeral, so their
input provenance is not stamped by `publish --act`. After their owning
renderer succeeds, record the digest through the delivery interface rather
than typing one:

```bash
python3 tools/deliver.py publish --segment renders/perfume-4-overlays.mp4
```

The command requires the output to exist and derives its digest from the
declared sources.

## The gate at stage 7

`build_uncut_credited.sh` renders the **whole** video and credits it. That is
right for a cinematic; it is exactly wrong for a trailer whose unclean beats
are scattered HUD and title cards, because rendering the whole thing puts every
one of them on screen.

So `make_video.sh` checks before it builds, and **fails closed**:

- An unclean beat that survives redaction **whole** → refuse, and point at the
  cut path.
- An unclean beat a redaction boundary **cuts through** → refuse *unless* that
  redaction record names the segment in `acknowledges`.

A video that refuses here does not need the gate relaxed. It needs cutting.

## Human stop points

**Stage 5 stops and asks a person to look at frames.** That is not a missing
feature. `clean` is the gate the whole repo rests on, it must be positively
established, and "nobody has looked at this frame" is not evidence the frame is
clean.

**A brief with `automatable: no` stops at stage 1**, prints what it is waiting
on, and exits 0 — stopping is the correct result, not a failure. A brief with
`automatable: partly` runs the mechanical half and stops before the credited
build: indexing is mechanical, putting names on screen is not.

`--video-id` skips the brief entirely. That is a debugging path for a video you
already understand, not the way to run an issue — it bypasses `automatable`
with it.

Both stops print the exact next command. Neither is a state to route around.

## Tail CTAs bias long

A final call to action is not a transition to hurry through. Hold it long
enough that the audience can read the whole card without racing; when review
says it is short, increase the tail before shrinking copy or type. A requested
multiplier changes only the CTA hold and extends the runtime after the card
begins. It never pulls an earlier beat forward or re-times authored content.

## Where the detail lives

This skill is the contract. The procedure lives in `references/`:

| Reference | What is in it |
|---|---|
| [`delivery.md`](references/delivery.md) | The `~/Videos/Wolves/` workspace, the delivery graph, hardlinks, checksums, playlists, and the Syncthing hazard. |
| [`social-copies.md`](references/social-copies.md) | Byte-capped social encodes from `Prod/`. |
| [`key-art.md`](references/key-art.md) | Stills cut from the key art: YouTube thumbnails and the website's social preview card. |
| [`avatars.md`](references/avatars.md) | The credits avatar cache and the Actions job that fetches it. |
| [`freshness.md`](references/freshness.md) | Keeping delivery current across `cards / plates -> master -> Prod -> megacut -> 10mb/`. |
| [`standalone-batch.md`](references/standalone-batch.md) | The "Bluefin and the X" cuts: one closed manifest, source-time seats, the CTA takeover, and splicing an intro film in front with a hard cut. |

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I should fix the pipeline before rendering." | Deliver the watchable cut first; improvements come after the owner has a file. |
| "The CTA already contains all the words, so five seconds is enough." | A CTA succeeds only when it can be read. Extend a final tail before shrinking its copy. |
| "I can move the previous beat earlier to buy CTA time." | A tail extension changes only the CTA hold; authored beats before it keep their clocks. |
| "The local encode is quicker to start." | The farm is the default whenever reachable; local is a stated, capped fallback. |

## Red Flags

- A new act's master that never went through `tools/peaks.py`.
- Starting a render while the previous one may still be writing the same path.
- Rendering a guessed recovery over a master instead of recovering authored
  copy from every worktree first.
- Exactly 1 beat for a cut-heavy video — the source is AV1, not H.264.
- A video whose segments are 0 clean — `overlays` was skipped wholesale.
- Two agents on one `video_id`.
- Anything under `media/`, `keyframes/` or `renders/` appearing in `git status`.
- A file hand-edited in `~/Videos/Wolves/Prod/`, or a `cp` over one of its
  entries instead of `ln -f`.
- Shipping a master and walking away before `deliver.py publish` and the
  downstream rebuilds.
- Any write to `~/src/website`.
- Trusting a bed's measured true peak as the *delivered* peak.
- Renumbering an act, or "closing the gap" in `Prod/` numbering.
- A music bed at 44.1 kHz, one with nothing above 16 kHz, or a format id
  ending in `-drc`.

## Verification

```bash
python3 -m pytest -q                  # includes committed-index integrity
python3 tools/deliver.py status       # the delivery chain, as a report (never a gate here)
python3 tools/readtime.py             # plates held too briefly to read (reports, never gates)
~/Videos/audio-check.sh --all         # gates every act in Wolves/Prod

# before any encode: report authored work that is not yet durable
python3 tools/worktrees.py
```

`tests/test_index_integrity.py` validates every committed segment, video and
tag file against its schema. The delivery chain is a report here, never a gate;
the freshness procedures live in [`references/freshness.md`](references/freshness.md).
Resolve findings in the worktree you own before rendering. Never alter another
agent's checkout, and never withhold an already-requested film for its finding.
