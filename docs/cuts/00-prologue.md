# 00 — Prologue

**The feature's main title sequence.** It has **no numeral**: it is a cold open
in front of act I, and the eight act numerals are load-bearing. See
[`docs/running-order.md`](../running-order.md), which is the source of truth
for where it sits and why.

| Piece | Where |
|---|---|
| Copy | [`stories/00-prologue-plates.json`](../../stories/00-prologue-plates.json) |
| Card | [`cards/maintitle.html`](../../cards/maintitle.html) |
| Builder | [`scripts/build_prologue.py`](../../scripts/build_prologue.py) |
| Rights | [`music/bed_perfume_of_the_timeless.json`](../../music/bed_perfume_of_the_timeless.json) |
| Master | `renders/00-prologue.mp4` → `~/Videos/Wolves/Prod/00-prologue.mp4` |

Origin: the owner, 2026-08-14 — *"Make this video the intro in front of endless
forms"*, pointing at Nightwish's official music video for **"Perfume Of The
Timeless"** (`oHCaZmIzr0o`, 8:27), with the main title at 0:11, the credit pair
*Music by Nightwish* / *Action by Bungie*, an out point at 1:31, and *"make it
nice and clean and crisp … this is our first impression"*.

```bash
python3 scripts/build_prologue.py --print-command   # the ffmpeg call, no render
python3 scripts/build_prologue.py --cards           # re-render the title PNGs
DESTINY_FFMPEG=$(which ffmpeg) python3 scripts/build_prologue.py
```

## What plays

| From | To | |
|---|---|---|
| 0.000 | 11.000 | The void. Pale filaments on near-black; no faces, no cuts. |
| 11.000 | 12.400 | The lockup fades up over 1.4 s. |
| 12.280 | — | **The source cuts.** The void gives way to a white starburst, then to the living world. The reveal happens *through* the title. |
| 15.400 | | Hard swap: the credit pair appears, nothing else moves. |
| 21.200 | 22.600 | The title fades out, clear of the 24.880 cut. |
| 91.200 | 99.200 | **The bridge.** March's Bluefin wallpaper, day turning to night. |

Total **99.200 s**. The song runs under all of it and fades from 93.000.

## Three numbers, all measured

None of these were taken on trust from the request. The commands are here so
the next person can disagree with the reading rather than with the number.

### The out point is 91.200, not 91.000

The owner said *"stop at 1:31"*. The picture's mean luma there:

```bash
ffmpeg -v error -ss 87 -i media/yt_nightwish_perfume_of_the_timeless.mkv -t 10 \
  -vf "signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-" -an -f null -
```

`YAVG` holds ~46 through 88.8, falls to **30.0 at 91.200**, and is climbing
again by 91.400. So 1:31 is one frame off the bottom of a natural fade the
source performs by itself. The out point moves the six frames to the actual
minimum, and the cut lands on black the film was already going to give us.

### The title is cued at 11.000 because of where the shots are

```bash
ffmpeg -v error -i media/yt_nightwish_perfume_of_the_timeless.mkv -t 95 \
  -vf "select='gt(scene,0.25)',metadata=print:file=-" -an -f null -
```

Boundaries at **12.28–12.56**, 24.88, 36.32, 40.72, 44.36, 49.64, 75.64. The
owner's 0:11 is 1.3 s ahead of the first one, which is the interesting part: the
title is fully present on the empty dark *before* the world arrives, so the
biggest visual event in the section happens behind a title that is already
settled. Cueing later would have put the title up during the event and made
them compete. It then holds through the bloom and clears well before 24.88.

### The bridge is 8.000, and 2.6 of it is the turn

The owner: *"put up a 03-bluefin-day.jxl and fade to the dark version so that
that replaces the black part, make it seem like one movie/video."*

March's pair is the same drawing at two times of day — pink sunset with a white
sun, then blue night with a crescent moon and fireflies — and **in both of them
the pack is closing on the herd**. Crossfading one into the other, immediately
before a film called *Seven Days to the Wolves*, is a sun going down over a
hunt. That is why it gets 2.600 s: it should read as a *turn*, not a dissolve.

| | |
|---|---|
| 0.0 → 1.4 | up from black to **day** |
| 1.4 → 2.6 | hold |
| 2.6 → 5.2 | **the turn** |
| 5.2 → 6.8 | hold night |
| 6.8 → 8.0 | down to black, so act I's slide rises out of the same darkness |

The wallpapers are cached by `scripts/fetch_wallpapers.py`, which grew a
`--variant day` for this: it had only ever cached the `-night` halves, because
act VIII is the only thing that had wanted them. JPEG XL still decodes through
GdkPixbuf — neither Pillow nor this host's ffmpeg can open it.

**The frame also opens up here.** The music video is 1920x804 scope and is
padded, not scaled, so the prologue plays in bars; the bridge is full-frame
16:9, and act I after it is too. Leaving somebody else's picture and entering
the film is visible in the shape of the frame.

## The sparks, and why the fix is level and not a limiter

The owner on the first cut:

> the sparks in the beginning of the video is jarring audio for the audience,
> tone them down the best you can

Two separate things were wrong.

### The master was above full scale

It measured **+0.4 dBTP**. Every other act in this show passes
`tools/peaks.py`, which lands a master in the **−0.9…−1.1 dBTP** band by static
gain; this build never ran it. That is the same systemic miss as issue #82 —
the deliverable gets checked and the master does not — and it is fixed by the
same tool. The master is **−1.1 dBTP** now.

### The sparks stood 13–18 dB above the bed

| | |
|---|---|
| Sustained level, first 13 s | −13 … −18 dB RMS |
| Spark transients | repeatedly **~0 dBFS** |
| Source master, decoded | peaks to **+1.9 dBFS** — already clipped |

The source is Nightwish's own loud master. Nothing here un-clips it.

**No compressor, no limiter, no normaliser.** The audio tenet forbids dynamics
processing on finished music, and it is the wrong tool anyway: squashing these
transients would dull the crackle into mush. The sanctioned lever is **level**.

So `scripts/build_prologue.py` rides the level across the opening, as an
evaluated `volume` expression — automation, not a filter that reshapes
dynamics:

```
gain(t) = −12 · (1 − (t/12.28)²)  dB,  and 0 dB from 12.28 onward
```

**The shape is the cut's.** The picture is a dark void until the 12.28 shot
change, so the ride reaches unity exactly there: the sparks are held down
precisely where they live, and full level arrives on the film's biggest visual
event instead of on a black screen. Nothing after 12.28 is touched.

Measured on the delivered file, against the same points before:

| Moment | Before | After | |
|---|---|---|---|
| 0.864 s | −0.08 dBFS | **−13.5** | 13.4 dB down |
| 9.504 s | −0.000001 dBFS | **−5.8** | 5.8 dB down |
| True peak | +0.4 dBTP | **−1.1 dBTP** | in band |

Every transient is still there. None of them arrives at full scale.

**Source quality, recorded rather than assumed** (the tenet's rule 2, missed
when the bed record was created): band energy above a swept 6-pole highpass
runs −55.4 dB at 14 kHz to −78.9 dB at 20.5 kHz — a **smooth roll-off with no
brickwall**, consistent with a healthy 48 kHz Opus rung. The numbers are in
`music/bed_perfume_of_the_timeless.json`.

### One process note worth keeping

The first attempt at the gate produced a master **250 frames short**, with FLAC
decode errors — because a render had been stopped and a second render started
against the same output path before the first one's ffmpeg had actually gone.
Two encoders on one file. The fix was to rebuild and **verify the master's
frame count and clean decode before trimming**, which is now the order things
are done in: build → verify → gate → verify → publish.

## The lockup: a blue B, and no box

Two owner corrections, both applied.

> don't forget the blue b … the words are fine just color in the b

The eyebrow stays as **type** — the real wordmark was the alternative and was
declined — and only the **B** of BLUEFIN is coloured. The value is not chosen:
`#4285f4` is the published fill of the fin ligature in Project Bluefin's own
mark (`scripts/fetch_wordmark.py` recolours that mark's black type for dark
backgrounds and leaves exactly this blue untouched), so the one coloured letter
carries the same value the one coloured element of the real mark does. The
manifest names the *word* (`accent: "BLUEFIN"`) rather than a character offset,
so editing the copy cannot silently move the colour onto a different letter.

> remove the black transclucent box around the words

Gone. The scrim below was the right diagnosis and the wrong object: a panel
behind titles over moving picture reads as a box, because it is one. The
legibility problem it solved is real, so it moved onto the **glyphs** — a tight
near-opaque core that gives each letterform its own edge, plus two wider soft
falloffs. Same protection, travelling with the letters, with no edge of its
own. Verified against the 12.28 starburst and the pale haze at 16 s, which are
the two frames that defeated the plain site shadow.

## The scrim that used to be here

The first pass put the lockup over bare picture, reasoning that the frame at
0:11 is near-black. It is — for 1.3 seconds. After 12.28 the source goes to a
white starburst and then a pale haze, and in the built file the eyebrow and the
credit pair were **unreadable** across most of the title's own window. That is
why some protection is not optional; only its *form* changed, per the owner's
note above.


## The copy is reproduced, and one treatment is swapped

The two title lines are the string the website's own prologue already carries,
at `~/src/website/src/data/wolves-intro-sequence.ts` (the 78.5–94 cue):

```
'PROJECT BLUEFIN\nseven days to the wolves'
```

— the same pair `stories/megacut/megacut-cards.json` reproduces for act I's
slide. Nothing here was written.

The owner asked for *"Seven Days to the Wolves … featured, the project bluefin
… on top, subtle but present"*. The site gives line 1 the display size and
line 2 the small one, so `cards/maintitle.html` **swaps the two treatments
between the lines** and leaves the authored order alone: Bluefin still sits on
top, and takes the small rule instead of the display one. No value is invented;
both rules are the site's, applied to the other line. The lowercase of *"seven
days to the wolves"* is the authored casing, and the card uppercases it in CSS
exactly as the site's own line2 rule does.

One fitting change: the site's line1 clamp tops out at 5.6rem, chosen for the
15 characters of `PROJECT BLUEFIN`. The 24-character title on that rule ran to
88% of frame width, so the maximum is 4.9rem here. The **tracking is not
touched** — letting the size carry the fit keeps the letterform spacing the
design specifies.

## The trap this act fell into

The first build emitted 91.2 s of film followed by **8 s of frozen final
frame**. The bridge never played, and ffmpeg exited 0.

`loop=loop=-1` makes a still stream **infinite**, and `overlay`'s framesync
will happily keep producing output after the *main* input ends, repeating its
last frame for as long as the secondary still has one. The overlaid picture
therefore ran to the `-t`, and `concat` had nothing left to put after it. The
fix is to bound each still with `trim` to the picture's own length and to add
`shortest=1`; both are in `_still()` with the reasoning attached.

It is worth noting how this was caught: not by watching, but by pulling frames
at 93.5, 96.5 and 98.5 and noticing they were **identical**. A silent no-op
that exits 0 is the failure mode this repo keeps re-learning — see
`tools/plate.py` on the quoted `enable=` spelling, which fails the same way and
is why the escaped-comma form is used here.

## Rights

The picture is Nightwish's own music video, which makes this the one asset in
the show whose **picture** is somebody else's rather than only its music.

Asked, the owner answered *"it's an iframe using their video don't download
it"*: the shipping presentation **embeds** it. So the rendered master is
prototype output for cutting and review, and
`stories/megacut/delivery.json` records the prologue as having **no social
copy by design** — a standalone clip is exactly the redistribution the embed
avoids. The web version is deferred by the owner (*"we are prototyping we'll do
the web thing later"*).

The record is a **bed** record, not a video record: `videos/*.json` is the
Destiny footage index and its schema is Destiny-shaped (`era`, `activity`,
`destination`), so filing a Nightwish music video there would mean three
`unknown`s and would pollute the pool `corpus.py` and `story.py` read.
`music/bed_perfume_of_the_timeless.json` is the record type built for this
rights shape, and it carries a **real** measured grid — 129.199 bpm, 507.008 s
— rather than an invented one.

## Unresolved

- **Where it sits.** The request said *"transition to endless forms"*; the
  placement chosen was *in front of act I*. It plays `PROLOGUE → I → II` today.
  Moving it is one reordered item in `megacut.json`.
- ~~The wordmark.~~ **Settled**: the owner asked for the words to stay as type
  with only the B coloured. `scripts/fetch_wordmark.py` remains the route if it
  is ever revisited.
- **Michroma**, the site's display face for this overlay, is not installed on
  this host, so the card resolves the act slides' stack (`Inter`,
  `Arial Narrow` → DejaVu Sans) exactly as `cards/act.html` does. That keeps
  the main title in the same face as every act slide it introduces, which is
  arguably right, but it is a substitution and is recorded as one.
- **The interstitials.** The owner wants the rest of the video —
  1:31 → 8:27 — *"broken into chunks to play in between the songs"*. Not built
  here. The shot boundaries above are the start of that map.
