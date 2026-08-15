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
| **3** | 159.400 → 274.240 | 114.840 | after act III | " |
| **4** | 274.240 → 389.800 | 115.560 | before act VII | " |
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

---

# The join pass (v2.1) — four notes from the owner, watching

v2.0 seated the thread. The owner then watched it and marked four timecodes.
Three of the four turned out to be the **same problem**: an audio fade-out
meeting an audio fade-in, putting a hole in the sound at the exact moment the
picture was doing something. The fourth was a tail nobody had re-examined since
the acts were cut separately.

Nothing was re-rendered. Act VI's file in `Prod/` is untouched; the cut lives in
the plan, which is what the new `trim_to` key is for.

## 23:55 — "when the song ends… cut out the comic and fade"

Both things the owner asked to remove start on **the same measured frame**.
`431.267` is act VI's last shot change:

- the comic cover — **SEVEN DAYS TO THE WOLVES / THE FIGHT FOR FREEDOM BEGINS!**
  — comes up on it and holds **12.2 s** to the end of the act;
- the song is at full level right up to it (−12.6 dB) and decaying immediately
  after: −13.9, −16.2, −26.3, −46.4, silence by 441.

So one cut removes the comic *and* the fade, and act VI now ends on its last
full bar and hands straight to Perfume. The owner said 23:55; the measured frame
is 23:59.5, and it is the frame their description names.

**Every credit survives.** Act VI's tail plates — the Cayde-6 reveal (Jorge
Castro), then Kelsey Hightower, Brian Ketelsen and Angie Jones, and since
2026-08-15 castrojo's six spoken lines — all end by act-film **429.980**,
1.25 s before the cut. That was checked against
`stories/06-wolves-cayde-plates.json` *before* cutting, and it is asserted in
`tests/test_interludes.py`, because a dropped credit is not recoverable by a
revert. The margin used to be 21.6 s; the pills were seated into exactly that
empty tail, so any further trim here is now a real risk rather than a rounding
question.

## 2026-08-15 — "the transition to the other song is also a hot mess"

The owner's note on the v2.7 join, and it was a **measurement** problem, not a
level one: `tools/transitions.py` had the two sides within 0.3 dB of each other
(−16.9 → −17.2 dB) and no silence at all. Spectral flux on the delivered files
found what was actually wrong, on both sides at once:

- act VI's cut at **431.267** fell **24 ms inside a drum hit** at 431.243 — the
  programme played a transient's attack and took the rest away, which is a
  click, not an ending;
- movement 4 opened with a **0.421 s stub** of the previous phrase before its
  own first hit, so the new song did not land for nearly half a second after the
  cut.

Fixed on both sides, and neither side loses any song:

| | before | after |
|---|---|---|
| act VI out (`megacut.json`) | 431.267 | **431.231** — the 59.94 fps frame ahead of the hit |
| movement 3/4 boundary | 273.840 | **274.240** — the 25 fps frame ahead of movement 4's first hit; movement 3 keeps the 0.400 s |

**Three joins were built and measured before choosing** —
`renders/review/join-A.mp4` (as shipped), `join-B.mp4` (act VI trimmed only)
and `join-C.mp4` (both sides). A and B both leave the new song's first hit
**0.48 s after** the seam; C lands it **on** the seam at full flux. C shipped.
The comic is still never seen: it comes up 36 ms after the cut.

**The cover now happens once.** It was already act VIII's reveal — #178 took it
off the end of act VII for exactly this reason.

## 25:13 — "don't fade this it's awesome, quick cut to europa, get rid of the title slide"

Movement 4 loses both fades and act VII's title slide is gone, so movement 4
hard-cuts into Europa.

**This costs act VII its chapter marker**, and that is a real consequence rather
than an oversight: `chapters()` derives markers from slides, so no slide means
no marker — exactly as for act VIII. The published list is **five** entries now.
The card's authored copy is **kept** in `megacut-cards.json` under `retired`
with its reason, so restoring the slide never means rewriting it.

## 27:03 — "needs a dramatic analysis, very close"

Measured what is actually there, rather than trusting the original brief:

| Act VII / movement 5 | What is on screen |
|---|---|
| VII tail | the Europa/Jupiter vista behind the **Coming to KubeCon NA** card, fading to black over its last half second |
| M5 **0.000** | a **dark Earth limb** (Y ≈ 24), held |
| M5 **3.504** | the **sun bursts** over the curve (Y jumps to 93) |
| M5 **4.505** | an ice plume |
| M5 **6.506** | **the owner's frame** (programme 27:02.3) — the body sinking through deep blue water |

**The original premise did not survive the measurement.** The brief asked to
"match the transition panning up from laura"; vertical displacement across both
sides is **0 px** by row-profile correlation. There is no pan. What the join
*is* — and what it is good at — is **dark to dark**: one world in space goes
out, another comes up, and the sun breaks over it 3.5 s later.

So the frame was never the problem. A 2.0 s fade **in**, under an already
near-black shot, coming off a 3.0 s fade **out**, made about four seconds of
nothing exactly where the film wants to hold its breath. Movement 5 now enters
at full level on the cut and act VII's fade-out is 1.5 s: the dark limb becomes
a held breath *with music under it*, and the sunrise is the payoff.

**Still open (#192).** If it plays slack, the one-number alternative is to start
movement 5 at the sunrise — `393.560` is a measured shot change — so Europa's
black cuts straight to the sun. Not taken here: it opens a **3.76 s hole in the
song**, and gaplessness is the whole idea. Closing that hole means extending
movement 4 to 393.560, which changes the 25:13 cut the owner has already called
awesome.

## 12:43 — "can be a perfect transition with the music"

Act III ends on the Vex gate **blooming to white**; movement 3 opens on a figure
standing on a dead branch above the clouds and **falls at 12:43**, photographs
scattering. The picture was already perfect and the sound was ducking under it —
2.0 s out into 2.0 s in.

Both fades are now zero. A white flash is the classic cover for a hard music
edit: the picture blinds you and the next song is simply there.

## What changed in the tooling

`trim_to` — a clip key on the **act-film clock** that ends a delivered act early
in the programme without re-rendering it. `dur` could not do this and that was
the trap: an authored `dur` shorter than the file changed the plan's arithmetic
while the segment still played to its own end. `trim_to` cuts picture and sound
with one number, `item_duration()` honours it everywhere, a fade lands against
the authored end, and a trimmed clip is **forced off the stream-copy path**
because a copy cannot cut mid-GOP safely.

**Programme: 32:40.249 → 32:23.016.**

---

# The fifth note (v2.2) — 15:31

> *"entire transition is too weird and long, make it all fit."*

What was there, in order: movement 3 ends on a **dark, static** shot of animal
skulls in a hall; the song fades out over 2.0 s; the IV–V card holds **15.0 s
in silence**; Kat's ships arrive. About **twenty seconds in which neither the
picture nor the sound moved.**

The 15 s was not an accident — it was deliberate pacing from when acts IV and V
had their two slides collapsed into one, and a single card announcing 59 s of
two acts was judged to deserve a longer hold.

**What changed underneath it is this thread.** The card no longer follows an act
that ends on movement; it follows a slow static shot, so the two stillnesses ran
together.

So the exception is retired rather than a new number invented: the slide holds
**5.0 s**, what every other slide in the programme holds, and movement 3's
`fade_out` goes 2.0 → 1.0 so the music carries closer to the card. The slide's
owner-authored copy is untouched — only the hold is.

The test asserts all act slides hold the **same** length rather than 5.0
specifically: the house length is a choice, but having two of them by accident
is the bug.

**32:23.016 → 32:13.016.**

---

# The alpha QA pass (v2.3) — the eclipse, and 28:20

Two owner notes, same review: *"the eclipse/planets shot at the end of europa -
that is janky it could be the best transition in the show if done right"* — in
some cases *"it might be more dramatic cut right into the next song"* — and
*"28:20 has extra fade out that can be cut, including the music video director
text, transition when the camera is in the ship make the song fade out but not
too much then punch them with the credits at the end."*

**The eclipse (Europa → movement 5).** Measured: act VII's tail holds flat at
mean luma 36–37 through 96.73, then its own baked fade falls to black over the
last half second; its score is already at −39 dB mean by then. The v2.2
treatment — a 1.5 s plan fade into that baked fade, then movement 5's dark
limb — was a fade into a fade into dark. v2.3 **trims act VII at 96.73** (the
last full-brightness eclipse frame region, the burned KubeCon card still
readable for ~5.7 s) with **no audio fade**: music meets music, the join is
hard. Two candidate frames were rendered for the owner —
`renders/review/europa-join-A-needledrop.mp4` (eclipse cuts, dark limb holds
its breath, the sun breaks 3.5 s later) and
`europa-join-B-matchcut.mp4` (movement 5 opens straight on the meteor strike
at source 393.560; taking it means extending movement 4 to keep the song
gapless, which nudges the 25:13 cut). The cut lands at 16.7 s in each. **A
ships as the default until the owner picks** (#192).

**28:20 (movement 5 → the credits).** 28:20 programme time is movement 5's own
tail: the in-ship shot dissolves out from ~film 109.5, the source's burned
credits (*"© A LOVELY BUNCH OF COCONUTS 2024 / DIRECTED BY VILLE LIPIÄINEN"*)
fade in from 111.0, then near-black, then a held interior to EOF — one long
dissolve with no shot boundary ≥0.15 after 100. v2.3 **trims movement 5 at
109.5**, while the camera still reads as inside the ship: the director text
and 7.7 s of fade-to-nothing are gone, the song fades **1.5 s** from a −20 dB
bed ("not too much"), and act VIII's drum smash punches the next frame with
`fade_in 0.0`. That **resolves #191**: the ambush lands off a live frame at
mid-energy, not a long decay.

Same pass: act I carries the plan's first owner-approved `gain_db` (+3.5 dB,
the most its −4.6 dBTP peak allows without a limiter — #164).

**36:16.2 → 36:07.9.**

---

# The 4K source swap (v3.0) — 2026-08-15

> *"I found 4k perfume of timeless much higher quality swap it out and rebuild
> everything."*

All five movements come out of **one** gitignored file,
`media/yt_nightwish_perfume_of_the_timeless.mkv`. That file was replaced, and
the thread rebuilt end to end. The old file is kept beside it as
`…perfume_of_the_timeless.1080p-orig.mkv`.

| | before | after |
|---|---|---|
| Upload | `oHCaZmIzr0o` — Nightwish's own channel | **`O0lyFqLr3Cc`** — *Tribute to Floor Edition 2.0*, Nightwish Arena |
| Rung | 1920×804 VP9 | **3840×1608 VP9, fmt 313** |
| Bitrate | 1 667 k total | **5 896 k video — 3.5×** |
| Runtime / fps | 507.021 s @ 25 | 507.04 s @ 25 |
| Colour | tv / bt709 | **identical** |

Nightwish's own upload **tops out at 1080p** — there is no official 4K rung, so
the better picture only exists on a re-upload. Nothing about the rights posture
moves: still `third_party_copyrighted`, still non-commercial, still no footage
committed and no social copy cut from the thread.

## It is conformed, not used raw

A re-upload is not frame-trustworthy, so nothing was assumed:

- **It runs one frame late.** Measured three ways and consistent: envelope
  correlation over three 60 s windows all peak at −1 frame (r = 0.93–1.03), and
  decoding both files from frame zero puts the first shot change at frame
  **307** against the old file's **306**.
- So the conform **drops frame 0**, lanczos-downscales 3840×1608 → the same
  **1920×804** the builders already pad, **clones one frame back at the tail**,
  and is pinned to `-frames:v 12675` — the old file's exact count.
- Re-measured after conform: **0 frames offset** at 100 s, 250 s and 380 s.

**So every measured timecode in `stories/00-perfume-thread.json` still holds**,
and no builder changed. The whole point of the conform is that this document's
tables — 93.000, 159.400, 274.240, 389.800, 507.021 — did not have to be
re-derived.

Downscaling rather than keeping 4K is where the quality actually lands:
`build_interludes.py` **pads, never scales**, and delivery is 1920×1080. Coming
off a 4K decode makes the 1080p a supersample instead of a re-encode.

## The audio was deliberately NOT taken

The upload is a **"No SFX"** edit. Same length, aligned to −0.10 s, but only
r = 0.89 against the delivered bed — a different mix.

`music/bed_perfume_of_the_timeless.json` carries a *measured* tempo grid
(129.199 BPM, 1055 beats, downbeat phase with its evidence) and a measured
spectral cutoff, and the prologue's clipping fix (+0.4 dBTP, 2026-08-14) was
derived from that mix. Taking the new audio would silently invalidate all of it
for no gain the standard recognises.

**Picture only.** The conform copies the original Opus stream through
bit-for-bit (`-c:a copy`), so the bed record is untouched and
`docs/skills/references/audio-standard.md` needs no edit.

## The watermark stays

The upload burns a corner mark — *"Nightwish. ://: Arena."*, roughly x 3370–3790,
y 60–120 in 4K coordinates. This is exactly what `redactions/` exists for, and
**no redaction was written**: owner, 2026-08-15, *"the watermark is fine"*.

The title's *"with lyrics"* is **soft CC**, not burned in — checked across
eighteen sampled timestamps. There is no lyric burn to remove.

## What it bought

The win is largest exactly where the thread is darkest, which is where the old
encode was worst. The **underwater shot** (source ≈ 396–400 s, movement 5) is
one slow blue gradient — the 1 667 k VP9 blocked and banded across the water;
the 4K holds it clean with the particulate and the bubble trail intact. An A/B
is at `~/Videos/perfume-4k-ab-underwater.mp4` (12 s, current over new).

## The decoy, so nobody re-finds it

A search for "Perfume of the Timeless 4K" surfaces **`Gmf4TiBc7HA`** first — a
genuine 3840×1920 60 fps rung that contains **no footage at all**: it is the
Yesterwynde album cover held static for the whole runtime (nine sampled
timestamps differ by < 0.8/255; two scene changes in 492 s). Its audio is the
**album** master, 492.1 s and offset **+12.75 s** from the music video, so it
cannot seat the prologue's opening either. Rejected on both counts.

---

# Where the thread stands

| | |
|---|---|
| Delivered | `~/Videos/Wolves/megacut/seven-days-to-the-wolves-v3.0.mp4`, **35:16.8** (FLAC master `.mkv` beside it) |
| Source | **4K** `O0lyFqLr3Cc`, conformed to the old timeline; picture only |
| Movements | 5, gapless in the source, `renders/perfume-2..5.mp4` + the prologue; the programme plays 109.5 of movement 5 (the 28:20 cut) |
| Chapter marks | **four** — acts II, VII and VIII have no slide, so no marker |
| Open for the owner | #190 (one builder), #192 (A or B off the excerpts in `renders/review/`, and movement 3's length) |
