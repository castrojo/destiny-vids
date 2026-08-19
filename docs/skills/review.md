# The review loop

**A round of notes should cost one act, not one show.** This file is how a
sentence typed while watching becomes a rebuilt file, and it exists because the
expensive part of a revision has never been the render — it is working out
*which act a note is about*, and then rebuilding six that were already right.

## The three-second version

```bash
# 1. what is playing at the timecode you wrote down?
python3 tools/megacut.py stories/megacut/megacut.json --locate 12:43 4:01 18:30

# 2. fix that act in the project that made it, then re-deliver it to Prod/
# 3. re-assemble; the other acts are copied, not re-encoded
python3 tools/megacut.py stories/megacut/megacut.json
```

## Why a note is cheap: assembly never re-cuts an act

`tools/megacut.py` normalises each item to a temporary segment and joins them
with the **concat demuxer**, and the join is `-c:v copy`
([`tools/megacut.py`](../../tools/megacut.py), `build_concat_command`). **The
picture is never re-encoded at assembly.** Only the act you changed is rebuilt
by the project that owns it; everything else is copied through.

That is also the rule that keeps the loop honest: *assembly joins finished
things and never re-cuts one.* If an act is wrong, it is wrong in the project
that made it. Never "fix" an act by touching the programme.

## Step 1 — turn a timecode into an act

You watch the programme. You write `12:43 nameplate too short`. The fix lives
in an act's own file, on that act's own clock — and doing that subtraction by
hand, per note, off a chapter list is exactly how a round of notes gets applied
to the wrong act.

```bash
python3 tools/megacut.py stories/megacut/megacut.json --locate 12:43 4:01 18:30
```

Each stamp comes back as the act that is playing plus the offset on that act's
own clock, and as `[act slide]` when the note landed on a card — a note about
the *announcement*, not the film behind it. It takes several stamps at once,
reads `12:43`, `1:02:11`, `763` and `12:43.5`, and needs **no footage** — it
runs off the plan's own clock, so it works before a build and on a machine with
no media. The act clock it answers from is the plan,
[`stories/megacut/megacut.json`](../../stories/megacut/megacut.json) — run the
command for the current mapping rather than trusting any table pasted into a
doc, this one included.

**It also tells you which clock a note was written on.** If a stamp resolves to
an act whose content does not match the note, the note was taken on the *act's*
clock rather than the programme's. That has already happened once, and read as
programme time the brief's cues would have landed minutes from their frames
([#98](https://github.com/castrojo/destiny-vids/issues/98)).

## Step 2 — the act clocks, so you can predict the answer

Derive them, every time — do not read them from a table in a doc:

```bash
python3 tools/megacut.py stories/megacut/megacut.json --chapters
```

Which act owns which file is [`../running-order.md`](../running-order.md); the
measured trims are in `stories/megacut/megacut.json`.

**Never paste a copy of a derived stamp into a doc**, here or anywhere else. A
pasted chapter table goes stale the moment a trim moves: one that opens act I
at `0:00` still reads that way once the prologue is placed in front of it,
which puts it 1:41 wrong and in disagreement with `running-order.md`.

## Step 2b — read the whole show without watching it

Watching the programme end to end costs half an hour, which makes "the card is
on the wrong shot" expensive to check and expensive to re-check. `tools/shots.py`
is the cheap version: one frame per detected shot, labelled with its timecode,
tiled into one image per act.

```bash
python3 tools/shots.py                    # every act in Prod/ -> ~/Videos/Wolves/shots/
python3 tools/shots.py --act II --act VI  # just these
python3 tools/shots.py --video renders/efmb-hq.mp4 --out /tmp/sheet
```

The label is the **act's own clock** — the same clock `stories/*-plates.json`
uses — so a plate's `at` can be read straight off the sheet. It is not the
programme clock; `tools/megacut.py --locate` converts a note taken against the
full movie back to the act that was playing.

Detection is `ContentDetector(threshold=27)`, the same detector and the same
threshold every measured boundary in this repo was found with, so a sheet and a
cut list describe the same shots. **A sheet reporting one shot for a whole act
is the AV1 trap, not a long take** — see [`../skills/indexing.md`](indexing.md).

## Step 3 — rebuild only what changed

| The note is about | Rebuild | Cost |
|---|---|---|
| a **nameplate**'s copy, timing or rank | that act's plate builder, then its act | one act |
| an act's **picture or edit** | that act's project, then re-deliver to `Prod/` | one act |
| an act **slide**'s copy | `stories/megacut/megacut-cards.json`, then assemble | assembly only |
| the **running order** | [`docs/running-order.md`](../running-order.md) first, always | assembly only |

Act II's plates, as the worked example:

```bash
python3 scripts/build_efmb_plates.py            # preview the schedule, write nothing
python3 scripts/build_efmb_plates.py --write    # commit the manifest
python3 scripts/build_efmb_plates.py --check    # CI's question: is it regenerated?
```

The preview prints every plate's in and out point, so a timing note can be
checked **before** anything renders. That is the cheapest verification in the
repo — use it before every act II build.

Act II's picture and burn, the full rebuild:

```bash
python3 scripts/build_efmb.py                   # the plan: kept runs, removals, gap
python3 scripts/build_efmb.py --render          # picture + bed -> renders/efmb-hq.mp4
python3 tools/plate.py burn --video renders/efmb-hq.mp4 \
    --manifest stories/02-endless-forms-plates.json \
    --plates-dir renders/plates-efmb --out renders/efmb-plated.mp4 \
    --fit-picture --delivery-spec
python3 tools/deliver.py publish --act II
```

`--delivery-spec` is not optional here: without it the burn emits act II's
master untagged and a rung below `DELIVERY` — see
[`rendering.md`](../rendering.md). Give `--render` an **absolute** path or none
at all; a relative one resolves inside the ffmpeg container.

Verify the result rather than trusting the exit code — the two faults this act
has actually shipped are both invisible to "did it render":

```bash
ffprobe -v error -select_streams v:0 \
    -show_entries stream=color_space,color_transfer,color_primaries \
    -show_entries format=duration -of default=noprint_wrappers=1 \
    renders/efmb-plated.mp4          # want bt709 x3, and 307.998
ffmpeg -v info -i renders/efmb-plated.mp4 \
    -vf "crop=1200:500:360:180,blackdetect=d=1.0:pic_th=0.98" -an -f null -
```

The act's only black is the **10.667 s head**, a **1.03 s** span at 115.167,
and the **~16 s tail** from 291.967. Any other black span means the picture
ran long and the plates are sitting on frames they were not timed for.
`blackdetect` logs at *info*, so `-v error` silently prints nothing and looks
like a pass; crop past the burned-in caption band or no frame is ever black.

## What the loop refuses to hand you

Two faults have actually shipped here and both are invisible to "did it
render": a **silent pause** and a **true peak over the headroom gate**.
`scripts/rebuild-wolves.sh` checks for both and fails rather than hand you the
file. Keep it that way — a fault you can only find by watching costs a whole
watch.

Known and tracked, so nobody re-measures them:

- The delivered band is −4.6…−0.9 dBTP and the gate that holds it is
  `tools/peaks.py trim` ([#82](https://github.com/castrojo/destiny-vids/issues/82)).
  Whether every act is inside it right now is a measurement, not a doc fact —
  ask `~/Videos/audio-check.sh --all`.
- The delivered-peak trim is enforced by `tools/redact.py`, `tools/render.py`
  and the master gate `tools/peaks.py trim`; `tools/social.py` still encodes
  audio blind and relies on its master's peak
  ([#44](https://github.com/castrojo/destiny-vids/issues/44)).

## Taking notes so they survive the watch

Write the **programme timecode** and what you saw. Nothing else is needed —
`--locate` supplies the act, and the act supplies the project.

```
12:43  nameplate too short
14:02  wrong person credited
18:30  slide sits too long
```

A note that names a *fix* rather than a *symptom* ("make it 4.5 s") loses the
reason, and the reason is what survives the next re-cut. Record what you saw;
the constant is an implementation detail.

**Three kinds of note can never be actioned by an agent alone**, and they are
worth marking as you write them: a visual judgement about a frame, a claim
about a real person, and a licensing decision. An agent that reaches one and
stops has done the right thing — see [`AGENTS.md`](../../AGENTS.md).
