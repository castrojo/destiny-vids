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
([`tools/megacut.py`](../tools/megacut.py), `build_concat_command`). **The
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

```console
$ python3 tools/megacut.py stories/megacut/megacut.json --locate 12:43 4:01 18:30
    12:43  ->  VI. 7 Days to the Wolves  @ 1:29.041  [.../Prod/06-7daystothewolves.mp4]
     4:01  ->  II. Endless Forms Most Beautiful  @ 1:59.433  [.../Prod/02-endlessformsmostbeautiful.mp4]
    18:30  ->  VII. Europa  @ 0:03.341  [act slide]
```

It takes several stamps at once, reads `12:43`, `1:02:11`, `763` and `12:43.5`,
and needs **no footage** — it runs off the plan's own clock, so it works before
a build and on a machine with no media. `[act slide]` means the note landed on
a card, so it is a note about the *announcement*, not the film behind it.

**It also tells you which clock a note was written on.** If a stamp resolves to
an act whose content does not match the note, the note was taken on the *act's*
clock rather than the programme's. That has already happened once: an owner
brief whose last cue read `5:07` was written against act II's film, which runs
`5:07.998` — a perfect fit, and a 2:45 error if it had been read as programme
time ([#98](https://github.com/castrojo/destiny-vids/issues/98)).

## Step 2 — the act clocks, so you can predict the answer

| Act | Starts | Its film |
|---|---|---|
| I. Project Bluefin | 0:00 | `Prod/01-intro.mp4` |
| II. Endless Forms Most Beautiful | 1:56 | `Prod/02-endlessformsmostbeautiful.mp4` |
| III. Bob Killen | 7:09 | `Prod/03-mrbobbytables.mp4` |
| IV–V. Bias for Action | 9:54 | `Prod/04-kat.mp4`, `Prod/05-nat.mp4` |
| VI. 7 Days to the Wolves | 11:08 | `Prod/06-7daystothewolves.mp4` |
| VII. Europa | 18:37 | `Prod/07-europa.mp4` |

Regenerate this with `--chapters`; never hand-edit it, and never trust a copy
of it that has been pasted somewhere else.

## Step 3 — rebuild only what changed

| The note is about | Rebuild | Cost |
|---|---|---|
| a **nameplate**'s copy, timing or rank | that act's plate builder, then its act | one act |
| an act's **picture or edit** | that act's project, then re-deliver to `Prod/` | one act |
| an act **slide**'s copy | `stories/megacut/megacut-cards.json`, then assemble | assembly only |
| the **running order** | [`docs/running-order.md`](running-order.md) first, always | assembly only |

Act II's plates, as the worked example:

```bash
python3 scripts/build_efmb_plates.py            # preview the schedule, write nothing
python3 scripts/build_efmb_plates.py --write    # commit the manifest
python3 scripts/build_efmb_plates.py --check    # CI's question: is it regenerated?
```

The preview prints every plate's in and out point, so a timing note can be
checked **before** anything renders. That is the cheapest verification in the
repo — use it before every act II build.

## What the loop refuses to hand you

Two faults have actually shipped here and both are invisible to "did it
render": a **silent pause** and a **true peak over the headroom gate**.
`scripts/rebuild-wolves.sh` checks for both and fails rather than hand you the
file. Keep it that way — a fault you can only find by watching costs a whole
watch.

Known and tracked, so nobody re-measures them:

- ~~The programme peaks at **+0.2 dBTP**, inherited from act VII's master.~~
  **Fixed 2026-08-13**: act VII's master was re-rendered under
  `tools/peaks.py trim` (PR #130) and measures **−1.1 dBTP**; every act is now
  in the −4.6…−0.9 band and v0.8's programme peak is −0.9
  ([#82](https://github.com/castrojo/destiny-vids/issues/82) stays open for its
  owner to close).
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
stops has done the right thing — see [`AGENTS.md`](../AGENTS.md).
