# The Perfume thread — one song, eight acts inside it

**Status:** movements 2–5 delivered to `renders/`, in the programme, **not in
`Prod/`**. The Europa join and the credits join are for the owner to approve.

## What it is

Nightwish's **"Perfume Of The Timeless"** (`oHCaZmIzr0o`) plays from the first
frame of the show to the last frame before the credits, and the eight acts live
inside it. Five movements, in source order, with no gaps:

| Movement | Source in → out | Runtime | Seat | Built by |
|---|---|---|---|---|
| **1** — the prologue | 0 → 91.200 (+8 s bridge) | 99.200 | cold open, in front of act I | `scripts/build_prologue.py` |
| **2** | 93.000 → 159.400 | 66.400 | after act I | `scripts/build_interludes.py` |
| **3** | 159.400 → 328.080 | 168.680 | after act III | " |
| **4** | 328.080 → 389.800 | 61.720 | before act VII | " |
| **5** | 389.800 → 507.021 (EOF) | 117.221 | after act VII, into the credits | " |

Movements 2–5 add **414.021 s** (6:54.0). With the prologue the programme goes
from v1.0's 24:07.1 to roughly **32:40**.

It is not four interstitials. It is **one song the acts interrupt** — which is
also why the movements are contiguous to the frame: any gap in the source would
be a gap the audience hears as a mistake rather than as an edit.

## The owner's spans, and what was actually cut

> *"Start at ~1:31 or wherever the last cut left off from (check another agent
> doing parallel work) — save the clip and cut it at ~2.39, then insert that
> after the destiny intro. 2-39-5:29 is the the next segment, insert after
> mrbobby. 5:29- start there and record that to 6:30, then insert that before
> europa. 6:30 match the transition panning up from laura after europa, then
> hold until the end of this, then roll credits."*

Every cut point was measured off the file with `select='gt(scene,0.25)'`, not
taken on trust:

| Owner said | Measured cut used | Delta |
|---|---|---|
| ~1:31 / "where the last cut left off" | **93.000** — see below | +2.0 |
| ~2:39 | **159.400** | +0.40 |
| 5:29 | **328.080** | −0.92 (next boundary is 14 s later, so unambiguous) |
| 6:30 | **389.800** | −0.20 (five frames at 25 fps) |
| "the end of this" | **507.021** (EOF; last cut is 467.52, then one held shot) | — |

## The in point had two answers

"Wherever the last cut left off" is ambiguous, because the prologue leaves off
in two different places: its **picture** ends at 91.200, and its **song** ends
at 99.200 having faded from 93.000.

**93.000 was chosen.** It replays exactly the 6.2 s the prologue faded *down*,
under a 6.2 s fade *up* (declared in the programme plan, not burned in). The
song dips out across act I and swells back — one continuous performance with a
hole in it, rather than two plays of the same bar.

It costs nothing on the picture side either, and that is measured: **there is no
shot boundary between 91.200 and 108.960.** The prologue and movement 2 are the
same continuous shot, so the join is invisible by construction rather than by
treatment.

The alternative, 99.200, would have been gapless in the song but would have
skipped 8 s of picture without saying so.

## Why they are clean, and why they are not in `Prod/`

The renders carry **no fades, no overlays, no cards**. All join treatment lives
in `stories/megacut/megacut.json` in act-film time, which is this repo's
convention (`_transitions`, #105) and means a re-order never moves a fade.

They deliver to `renders/` only. The owner: *"also want the snippets in the
render folder we will be editing them in the future with dino artwork."* They
are work-in-progress elements with a pass still to come, so:

- no `delivery.json` key, no `Prod/` hardlink, no README row, no checksum;
- the programme plan points at `renders/perfume-N.mp4` directly;
- `Prod/` keeps meaning **"a finished act"**.

A dinosaur pass wants unfaded picture to work on. Promoting them to `Prod/` is a
later decision, and a deliberate one.

## The two joins that need eyes

**Europa → movement 5.** The owner asked to *"match the transition panning up
from laura after europa"*. Laura Santamaria is **Elsie Bray**, act VII copy
(`vocab/casting.yaml`, README:90). Act VII runs 97.266 s; its tail is flat at
YAVG ≈ 37 from 89 s and then falls hard over its last half second (96.8 → 97.27:
32.8 → 24.8 → 16.0). It fades down; it does not cut. Movement 5 opens on the
measured cut at 389.800 and its upward move continues that fall.

Where exactly the two moves meet is a **craft judgement about frames and is not
automatable**. This build joins at 389.800 and the frame is the owner's to
approve. Act VII's out point is settled (#178) and is never shortened to fit.

**Movement 5 → the credits.** This moves the act VIII ambush.
`docs/running-order.md` records that the credits carry no slide and no marker
because *"Europa fades to black on its own tail and the drum smash lands on the
next frame."* The smash now lands off the end of a **different song**, and the
source's last shot is **held** (luma ≈ 32), not black.

Movement 5 gets a 1.5 s audio `fade_out` so the song lands rather than being
chopped. The picture is left un-faded on purpose — burning a dip would have to
be un-baked for the dinosaur pass. **TODO(owner):** whether the two pieces of
music collide, and whether the ambush wants black in front of it after all.

## Rights

Third-party copyrighted: Nuclear Blast's recording, Nightwish's own official
music video. The rights records are `music/bed_perfume_of_the_timeless.json` and
`videos/yt_nightwish_perfume_of_the_timeless.json`, written for the prologue and
unchanged here.

Like the prologue, these are **prototype output**: the shipping presentation
embeds the video rather than re-hosting it (owner: *"it's an iframe using their
video don't download it"*), so these renders are for cutting and review. **No
social copy is ever cut from them** — a standalone clip is exactly the
redistribution that instruction rules out.

Going from 1:31 to 8:27 of one commercial music video is a materially larger
exposure than the prologue alone, and the owner should see that stated even
though nothing here needs a new grant.

## Chapter markers

Unchanged in count. `megacut.chapters()` derives markers from act **slides**,
and the movements have none, so the published list is still eight entries — but
**every timestamp after act I moves**, so the YouTube chapter list must be
regenerated:

```bash
python3 tools/megacut.py stories/megacut/megacut.json --chapters
```

## Rebuilding

```bash
python3 scripts/build_interludes.py --print-command   # the ffmpeg calls, no render
python3 scripts/build_interludes.py                   # all four
python3 scripts/build_interludes.py --only perfume-3  # one of them
```

Footage is never committed. The source is read from gitignored
`media/yt_nightwish_perfume_of_the_timeless.mkv` and the script reports it
missing rather than substituting anything.

## Open follow-ups

- **Consolidate the five movements** into one builder and one manifest; today
  the prologue duplicates the conform and padding logic.
- **Movement 3 is 2:48.7**, longer than acts IV, V and VII. Built as instructed;
  flagged because it is the one placement where an interlude outweighs the acts
  around it.
- **The act VIII entry** after this change (above).
