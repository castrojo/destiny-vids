# Seven Days to the Wolves — the programme, in acts

The whole show as **one continuous video**, assembled from the finished cuts.
It **was** announced by act slides in the Wolves cinematic's own chrome; the
owner cut them on 2026-08-14, and the overlays that replace them are theirs to
design.

**Status: v2.6 is built and published** — two files, from one assembly:

| | |
|---|---|
| Distribution copy | `~/Videos/Wolves/megacut/seven-days-to-the-wolves-v2.6.mp4` — **35:27.3**, 1920×1080 59.94p, AAC stereo ~440 kb/s |
| **Lossless master** | `…-v2.6.mkv` — the same copied picture bitstream, FLAC stereo (issue #145) |

Measured on the delivered files, not asserted: the master reads **−1.1 dBTP /
−11.8 LUFS**, the distribution copy **−3.2 dBTP / −13.9 LUFS**, and
`tools/deliver.py status` reports **0 stale**.

## v2.9 — the 2026-08-15 review pass

Ten owner notes, every one of them fixed **in the act that owns it** rather
than in the assembly: *"make sure you're fixing the original video and do the
entire supercut when you're done"*.

| Note | Fixed in | What it was |
|---|---|---|
| the O in *Wolves* | `cards/maintitle.html` | CNCF's white Kubernetes helm, sized to the cap band |
| every b and f blue | `tools/blueletters.py` | one rule, one home; **not** chat bubbles, **not** nameplates |
| 1:32 fade, then black | `scripts/build_prologue.py` + the plan | a 1.2 s fade in front of **2.000 s of measured dead black** |
| 4:19 the woman | `scripts/build_interludes.py` | dusk day→night, and a 6-frame roar |
| 4:39 audio cut off | `megacut.json` | a crescendo peaking at −11.5 dB into an act entering at −21 |
| 4:40 the plaques | `scripts/build_efmb_plates.py` | three cards printing a **login** where a name belongs |
| 13:16 the band ghosts | `scripts/build_interludes.py` | three ghost shots, seven wallpapers |
| 14:11 | `megacut.json` | a 3.0 s dip where a jump cut belongs |
| the credits bed | `stories/08-credits.json` | the album pass restarted the song from its intro |
| MAKE YOUR OWN FATE | `tools/credits.py` | the fitter, not the sizes — see below |

**Three of these were measurement failures, not taste.** They are worth
recording because each looked like a styling question and was not:

- **1:32.** The bridge was doing what it was told. `signalstats` on the v2.8
  programme showed the frame pinned at **YAVG 16.00 from 99.35 to 101.02** —
  act I's own head, which holds flat black to 1.833 and starts climbing at
  2.000. The fade was hurried *and* two seconds of nothing followed it. Both
  ends were fixed: `BRIDGE_DOWN` 1.200 → 3.200, and act I's head skipped in the
  programme. **The programme's length is unchanged** — the bridge gains exactly
  what act I gives up.
- **The call to action.** The sizes were never the problem. `_cta_font` shrank
  a line until it fitted on **one row**, so an eighteen-character cry could
  never be big: it came out near the `medium` size whatever the card asked for,
  and FIGHT — five characters — was the only line that ever rendered at its
  stated size, which is why it was the only one nobody complained about. Lines
  **wrap** now and keep their size, balanced so a cry reads as a block rather
  than a list.
- **4:39.** Nothing was fading. Movement 2's crescendo returns Perfume to unity
  and it simply *stopped* at its loudest, a ten dB cliff into act II's first
  bar. The crescendo is the owner's own design and stays; what it was missing
  is its release.

**Artwork is high fidelity, and that was a correction.** The first interlude
pass cropped every wallpaper to 16:9 and downscaled it to 1920×1080 at fetch
time, then **stretched it to 1920×804** at render time to match the film's
scope window. The owner: *"YOU ARE FUCKING UP THE IMAGES"*, and *"why are you
using the 10xx versions use the high rez versions"*. Art is now cached at its
published resolution — up to **7680×4320**, vectors rasterised at a 3840 long
edge on their own aspect — and resampled **once**, fitted with
`force_original_aspect_ratio=decrease` and letterboxed. Never stretched, never
cropped.

**Every replacement is duration-locked** to the shot it covers, measured with
`select='gt(scene,…)'`, so no chapter marker downstream can move.

**v2.6 is the slide cut and the audio pass, in that order.**

The owner, 2026-08-14: *"we should remove the roman numeral chapter things —
I'll design overlays later, let's just cut them where appropriate. Like 16:43's
title makes no sense anymore, let's tighten this up."*

- **All four remaining Roman-numeral slides are retired** — I, III, the shared
  IV–V, and VI. The scream interstitial stays, being no numeral, and is now the
  *only* card the programme plays. Their authored copy is kept in
  `megacut-cards.json` against the overlays that will replace them.
- **No chapter marker was lost with them.** Each retired card's `chapter`
  string moved onto its act's own **clip**, and `chapters()` learned to read it
  there; the marker list is unchanged in content and starts where each act now
  starts. The scream card is marked `interstitial`, which opts it out — it had
  been quietly publishing its build label as a marker.
- **16:43 was not a card at all.** It was act VI's *own* 10.000 s head plate,
  playing straight after the act VI slide: 15.7 s in which nothing moved,
  announcing a main title the prologue had already delivered. Act II had the
  same shape with a 10.666667 s black head. Both are now skipped by the
  assembler's new `trim_from` — the mirror of `trim_to` — **in the programme
  only**. Neither act file is re-rendered, so act VI's plate, whose copy is a
  rights condition, still plays wherever the act plays standalone. Issue #206.
- **The joins were re-judged, not carried over.** Four of them lost the five
  seconds of digital silence their fades were shaped against; act I's
  `fade_in` went 2.0 → 0.0, because that fade was shaping the card and both the
  prologue's tail and act I's head already fade themselves. Details in the
  plan's `_transitions`.
- **40.667 s shorter** than v2.4: 4 × 5.0 s of card, plus 10.0 and 10.667 of
  head.

Then the audio, all of it measured on delivered files:

- **Two more clipping masters, found by sweeping the whole folder** rather than
  the one act that had failed before — the prologue at **+0.4 dBTP** and the
  credits at **+0.9**, both FLAC, both invisible for exactly the reason Europa
  was (#82). Corrected at source by `tools/peaks.py trim` (derived static gains
  0.841 and 0.794, picture stream copied untouched), each re-measured at
  **−1.1 dBTP**, and re-linked by `deliver.py publish`.
- **The programme has a lossless master for the first time** (#145). Until now
  the final movie — the file the show is actually watched and judged by — was
  the only artifact in the chain with no lossless option, squashing seven FLAC
  masters into one ~440 kb/s AAC at the join.
- **Two gains, kept apart.** Built from the *same* PCM with the *same* −1.7 dB
  mix gain, the master read −1.1 dBTP and the AAC copy **+1.0** — about 2.1 dB
  of inter-sample overshoot the encoder reconstructs above the samples it was
  given. So `master_gain_db` is the mix, carried by both, and
  `distribution_gain_db` is headroom only the lossy leg needs. The copy landed
  at −3.2 rather than −1.1, and that is **kept**: `peaks.py` records that the
  overshoot is not monotonic in the gain, the rule is to stop at the first safe
  result, and −13.9 LUFS is within a tenth of YouTube's own normalisation
  target.
- **The assembler stopped claiming 5.1** against nine stereo files (#146), and
  `tools/render.py` / `tools/audiomix.py` stopped baking lossy AAC generations
  into the middle of a chain the audio standard requires to be lossless (#144).

**It is not the feature yet.** Act VIII is delivered and in the programme, but
the credits sequence is still not designed (#51); act VI is an editorial pass
whose provenance is an open owner decision (#55); act II's picture comes from a
fan compilation carrying the same question; act III is partially complete by the
owner's own description. None of that is fixable by re-assembling — assembly
joins finished things and never re-cuts one.

*The sections below still describe earlier builds where they have not been
revised; the plan (`stories/megacut/megacut.json`) and
[`docs/running-order.md`](../running-order.md) are authoritative.*

## What the current build contains

**This is a build record, not the running order.**
[`docs/running-order.md`](../running-order.md) owns the order; the table below
is the *timeline of the assembly as it stands* — what is in it, where each item
lands on the clock, and what is missing. If the two disagree about the order,
the running order is right and this file is stale.

The timings are **derived, never typed**: re-run
`python3 tools/megacut.py stories/megacut/megacut.json --chapters` after every
assembly rather than editing this table. Wiring act II in moved every stamp
after act I by 312.967 s, which is the worked example of why.

| Act | From | To | What | Source |
|---|---|---|---|---|
| — | 0.000 | 5.000 | Slide **I** — `PROJECT BLUEFIN` / *seven days to the wolves* | rendered |
| **I** | 5.000 | 116.567 | **Into the Light** — six Guardians plated, the title cover, Bungie's score | `Prod/01-…` |
| — | 116.567 | 121.567 | Slide **II** — `ENDLESS FORMS MOST BEAUTIFUL` / *Nightwish* | rendered |
| **II** | 121.567 | 429.534 | **Endless Forms Most Beautiful** — the live-action trailers, one song end to end | `Prod/02-…` |
| — | 429.534 | 434.534 | Slide **III** — `Bob Killen` / *Voidwalker Warlock* | rendered |
| **III** | 434.534 | 594.734 | **mrbobbytables** — August 2026 contributors | `Prod/03-…` |
| — | 594.734 | 609.734 | Slide **IV–V** — `BIAS FOR ACTION` / *The Kat and the Nat*, held 15s | rendered |
| **IV** | 609.734 | 643.734 | **Kat Cosgrove** — Guardian intro | `Prod/04-…` |
| **V** | 643.734 | 668.992 | **Natali Vlatko** — Guardian arrival, straight off act IV | `Prod/05-…` |
| — | 668.992 | 673.992 | Slide **VI** — `7 Days to the Wolves` / *Nightwish* | rendered |
| **VI** | 673.992 | 1117.492 | **Seven Days to the Wolves** — the musical (editorial pass), #104 interruption build | `Prod/06-…` |
| — | 1117.492 | 1122.492 | Slide **VII** — `Europa` / *Director's Cut* | rendered |
| **VII** | 1122.492 | 1232.692 | **Europa Director's Cut** | `Prod/07-…` |
| **VIII** | — | — | Credits — **not designed** (#51) | — |

**1232.692s planned — 20:32.7**, output to
`~/Videos/Wolves/megacut/`. The 33 ms against the tool's sum (1232.659) is
act II's audio leg outrunning its video leg plus per-segment rounding; it does
not accumulate, and every act slide lands within a second of its mark. Every act plays
from `~/Videos/Wolves/Prod/`, which holds the **highest-quality master** of
each — FLAC audio, picture never re-encoded. Assembly re-encodes once and edits
nothing.

**The programme is stereo**, because every master is stereo FLAC. The older
retired `UPLOAD/` copies were AAC 5.1, but that 5.1 was the same two channels plus an
LFE derived by each cut's own script; upmixing here to recreate it would be
assembly inventing a soundfield, which the audio tenet forbids.

## The act slide is the cinematic's own card

Not a new design, and not a Pillow port: `cards/act.html` copies the rules of
`CinematicTransition.vue` and `wolves-cinematic.scss` — the slide the show
already plays between songs, the one that reads *"// Deploy CNCF Projects Team,
scramble all Guardians."* It is rendered by a real browser
(`cards/render-cards.mjs`), the same way `plate.html`, `reveal.html` and
`nimbatus-review/render/endcard.html` have always been rendered.

Two rows are additions, both the owner's: the **Roman numeral** ("Give them Huge
Roman numbers in the intro slides") and the **chapters** list ("each will have
chapters").

Act IV's slide is the exception in two ways, both requested: its copy is entirely
owner-authored —

```
The Knightly Order of Kubernetes sends a lone titan on a secret mission
Destination: Europa
TOC Authorization: [ DENIED ]
TAB Authorization: [ DENIED ]
CNCF Authorization: [ UNAUTHORIZED ]

BIAS FOR ACTION
```

— and it is **held 15 seconds**: "Hold that slide for a long time it's a
transition inbetween videos."

**Act V's own slide is superseded** — acts IV and V now share one slide (the
owner's call; see [`../running-order.md`](../running-order.md)), so the
paragraph below records the earlier separate-slide decision, kept because its
copy rules still hold. "Make the slide with the unauthorized
etc be the same for Natali and change the title to *Wrong Place, Wrong Time,
Right Attitude*." So the five authorisation lines are act IV's, copied
unchanged — *Destination: Europa* included: it is the same readout, and
rewriting a line of it per act would be authoring copy nobody wrote. Like act
IV it drops the eyebrow and the subtitle, because Natali's authored identity is
on her own reveal card inside the cut. Its 15s hold is the one thing here that
was **inferred** rather than said — identical copy, and five lines plus a
nine-word title do not read in five seconds — and it is recorded in the
manifest's `unresolved` so it can be cut back without archaeology.

## Act I: the hero segment

**Source: `BKm0TPqeOjY`, "Destiny 2: Into the Light Cinematic", official
"Destiny 2" channel.** Trimmed **2.0 → 113.55 = 111.567s**, both ends frame
verified against this file (Bungie's upload ends on a "Season of the Wish"
marketing card the fan copy does not have, so the website's 118.8 does not
transfer). Bungie's own score rides with it, from that upload's best audio rung.
`usage_class: third_party_copyrighted`, Bungie fan-content policy,
non-commercial, no footage committed.

### The GUARDIAN BOND companion cards

Owner instruction, this round: *"Intro missing dinosaur companions from port.
Alamo, karl, etc."* The live overlay renders a `GUARDIAN BOND` card beside a
Guardian's own lower third; `tools/plate.py` had no such card, so the burned
act I showed none. It has one now (`kind: "companion"`), ported from
`.wolves-companion-plate` and its CSS.

**All four documented bonds are here**, read from the site's own
`wolves-guardian-dinosaur-bonds.ts` and `wolves-dinosaur-species.ts` — nothing
was composed:

| Beside | Bond | Species |
|---|---|---|
| Cortney Nickerson | *(unnamed)* | *Torosaurus latus* |
| Kat Cosgrove | **Karl** | *Amargasaurus cazaui* |
| Kaslin Fields | **Katerina** | *Kentrosaurus aethiopicus* |
| Natali Vlatko | **Alamo** | *Alamosaurus sanjuanensis* |

Three things this needed a decision or a judgement for:

- **The Torosaurus is Bob Killen's bond**, and a bond does **not** follow a
  recast on its own. Cortney inherits it because the owner said so, explicitly,
  and that is recorded on the plate. Its card carries **no name row**, because
  no character sheet names that animal — the site's own `v-if` drops it too.
- **Alamo's artwork is capped at 200px**, and that is a frame judgement rather
  than a proportion: at full height it rose to y=379 and covered "Natali
  Vlatko" and "Shipwright of Kubernetes" on her raised plate. Found on the
  burned frame at t=90, which is the only place it could have been found. A
  test now pins the clearance.
- **`bond_of` is what lets the pair share the screen**, instead of a shared
  `group` string. The exemption is named on purpose: a group key could quietly
  cover somebody else's plate too.

Artwork is cached by `scripts/fetch_companion_art.py` into gitignored
`renders/`; the renderer never reaches outside the repo and never touches the
network, and a missing file degrades to the card alone.

**Orlin gets none.** The bond list keys on the Guardian's name, has no entry
for Orlin, and has none for Laura Santamaria either — so there is nothing to
inherit even if the owner wanted it.

### The title cover

Owner instruction, this round: *"replace the dino/QR sequence with wolves.jpg,
the same comic at the end of europa"* — and the owner's own name for it, *"call
this the title cover"*.

It takes the whole window the 23-shot comic/QR cycle held, and it is the same
asset the Europa director's cut ends on
(`~/Videos/wolves-directors-cut/STORYBOARD.md`, *Scene: Comic cover*).

**What the identities are, and why they are not plates.** The art is square
(9075×9075) and the frame is 16:9, so the cover fills the middle 1080px and
leaves **420px of margin** either side. A Guardian plate is **561px** wide
(`tools/plate.py`), so the owner's three authored cover identities could not be
plates without covering the ink — which the owner ruled out: *"can't have the
nameplates cover the art."* They are carried as **caption boxes on the card
itself**, in `captions[]`. Every authored string is reproduced verbatim; only
the chrome changed, to the box the owner picked: *"no tilt, use the same tech
outline on the box but keep them white."*

That chrome is the show's own, reproduced not designed — white stock, the 16px
top-left/bottom-right chamfer and the `#60a5fa` hairline `tools/plate.py`
draws, plus a left accent rule. The hairline is a nested panel, **not** a
`z-index: -1` pseudo-element: `clip-path` opens a stacking context, so that
layer paints *over* the white instead of behind it.

**The margins show a random Bluefin wallpaper**, by owner request (*"have it be
a random one every time"*). A roll nobody wrote down cannot be rebuilt, so
`cards/render-cards.mjs` records which file it picked in `wallpapers.json`
beside the PNG, and `--wallpaper-seed` replays it.

### What the title cover replaced

The site's full-screen comic title card is still reproduced by
`cards/comic.html`, which copies `.wolves-intro-overlay-title-card` and friends
out of `WolvesIntroOverlay.vue`. Two owner-authored pieces left with the cycle
and are **recorded, not re-authored** — the MakeMeAComic QR panel, and:

> "You don't need permission to contribute to your own destiny."
> — **Amber Graner**, Maintainer Guardian // The Iron Standard - Subclass [ REDACTED ]

Whether they return elsewhere is an owner decision, logged in the manifest's
`unresolved` and in issue #90.

The card **covers** the cinematic for its window, exactly as the site does. The
site cues it at source 24–38; here it runs **source 24.5 – 38 (segment 22.5 –
36.0)** so it cannot overlap Kat's plate, which the live overlay draws *on top*
of the card and `tools/plate.py` has no z-order for.

### The Guardian plates, and two recasts

| Act film | Verified on screen | Plate |
|---|---|---|
| 3.0 – 12.5 | purple void vortex | **Cortney Nickerson** (was Bob Killen) |
| 12.5 – 22.5 | Ward of Dawn bubble, Titan inside | Kat Cosgrove — Sentinel Titan |
| 38.0 – 46.0 | arc lightning duel | Kaslin Fields — Stormcaller Warlock |
| 68.5 – 75.0 | solar winged Guardian | **Orlin** (was Laura Santamaria) |
| 83.0 – 93.0 | green Strand tendrils | Christoph Blecker — Broodweaver Warlock (leader, gold) |
| 87.5 – 94.0 | icy-blue crystal Guardian, right of frame | Natali Vlatko — Behemoth Titan |

**The recasts changed who is credited, never which shot**, so the frame-verified
windows are untouched and nothing needs re-checking against the picture.

**Cortney's identity was authored** this round (issue #90) and is reproduced
verbatim, including the owner's spelling of *Weilder*. One row is still absent:
the owner wrote *"whatever the Void subclass is"*, and Void subclasses are
class-specific — Voidwalker (Warlock), Sentinel (Titan), Nightstalker (Hunter)
— so the subclass row needs her class before it can be written. It is omitted,
not guessed.

**Orlin is rendered as a name and nothing else.** No authored Guardian identity
exists in any of the places identities live (`~/Videos/nameplates.json`, the
website's `characters.json`, `vocab/casting.yaml`), and the previous occupant's
label, subclass and title are **hers** — inheriting them would put Laura
Santamaria's rows on Orlin's card. A missing row is omitted; it is never
guessed.

Two behaviours are carried over from the sequence file so nobody "fixes" them:

- **Kat's plate is deliberately cued ahead of the footage cut** (source 14.5,
  not the frame-accurate 17.5) by explicit owner request, with the first plate
  shortened to match.
- **Christoph and Natali share the shot** from ~89.5, which is why they carry
  opposite `position` values and a shared `group` key.

The site's top-of-frame HUD is deliberately **not** burned in — "just the name
plaquards" — which also drops the `#nova4ever` glitch bursts and the closing
*Legends Sought* card.

## Punch-list — owner decisions, not bugs

- **Cortney Nickerson's Void subclass** — issues #90 and #59. Her label, name
  and title are authored; the subclass row needs her class.
- **Four strings on the title cover** — issue #90: `speciesname`, which
  ANTIRRHOPUS is *proposed* for; whether Lakshmi's name goes on her own caption
  or stays only in the framing line; the *Weilder*/*Wielder* spellings, both
  reproduced as written; and whether the QR panel and the Amber Graner quote
  return elsewhere.
- **Who "Orlin" is.** The instruction was *"laura santamaria is orlin"*, given
  with intro notes, so it is applied to the intro plate **and nowhere else**;
  the Europa director's cut still credits Laura Santamaria. No surname, no
  authored identity. Both open.
- ~~**Act II has no film and no named track.**~~ **Settled.** "It's endless
  forms most beautiful, instrumental" named the *record*, not which
  instrumental; the track is now recorded as Nightwish's *Endless Forms Most
  Beautiful (Instrumental)*, [`6-9667CV1zQ`](https://www.youtube.com/watch?v=6-9667CV1zQ)
  from the official channel, and the act is delivered and credited (#74).
- **Act VIII (the credits) has no film** — #51 tracks the design; the owner's
  design brief is now in that issue's body.
- **Act III is partially complete, by the owner's own description**, and it is
  placed as-is: assembly joins finished things and never re-cuts one. Finishing
  it happens upstream, in the contributors project. Its slide carries Bob
  Killen's **authored** Guardian identity rather than an act title, because
  the film has none (#41) and one would have to be written. **This does not
  contradict the intro recast**: the owner replaced him on *one plate in act
  I*, and `vocab/casting.yaml` still binds Osiris to mrbobbytables with Bob's
  plate, which is what act III's film credits.
- **Act VI is an editorial pass, not an approved cut**, and its provenance is
  open (#55). Delivered is not published.
- **Act VII plays the pre-terse-pass film.** Its twelve terse-pass plates are
  rebuilt but its film is not (#102), so the Europa in this build still
  carries the old Foreman lines. Its master's +0.3 dBTP clip (#82) is **fixed**:
  re-rendered under the master gate on 2026-08-13, now −1.1 dBTP.
- ~~**Kat's cut is about to change under this plan.**~~ **Done 2026-08-12**:
  the dialogue split and "Remember kids, cardio!" are rendered into
  `Prod/04-kat.mp4` (rebuilt 16:52; the hardlink survived).
- **Chapters for every act.** Five acts carry a drafted list; none of it is
  the owner's copy yet (see [`../running-order.md`](../running-order.md)).
- **A music bed under the six slides.** They are silent; a bed is a licensing
  decision.
- **The QR is inverted** — light modules on near-black — because
  `filter: invert(1)` is what the site publishes. Reproduced, not corrected;
  worth an owner's eye on whether it scans from a screen.

## Reproducing

```bash
cd ~/src/destiny-vids

# playwright is not vendored; point node at a checkout that has it
ln -sfn ~/src/website/node_modules node_modules

yt-dlp --cookies-from-browser \
  firefox:~/.var/app/org.mozilla.firefox/config/mozilla/firefox/mha2aykb.default-release \
  -f "bv*[height=1080][vcodec^=av01]/bv*[height=1080][vcodec^=vp9]/bv*[height=1080]" \
  -o media/yt_into_the_light_cinematic.%\(ext\)s \
  https://www.youtube.com/watch?v=BKm0TPqeOjY

# act slides
node cards/render-cards.mjs --manifest stories/megacut/megacut-cards.json \
    --out-dir renders/plates-megacut-cards

# hero segment: Guardian plates (python) + comic cards (browser), one dir
python3 tools/plate.py render --manifest stories/megacut/megacut-hero-plates.json \
    --out-dir renders/plates-megacut-hero
node cards/render-cards.mjs --manifest stories/megacut/megacut-hero-plates.json \
    --out-dir renders/plates-megacut-hero
python3 tools/plate.py burn --video renders/megacut-01-hero-raw.mkv \
    --manifest stories/megacut/megacut-hero-plates.json \
    --plates-dir renders/plates-megacut-hero --out renders/megacut-01-hero.mkv

python3 tools/megacut.py stories/megacut/megacut.json --dry-run
python3 tools/megacut.py stories/megacut/megacut.json
```

Use `/home/linuxbrew/.linuxbrew/bin/ffmpeg` — the system `ffmpeg` is
`ffmpeg-free`, has no H.264 decoder, and fails only once decoding starts, which
reads like a corrupt input file.

## Verification, when it is rendered

Not asserted — measured. The previous assembly of this programme was verified
this way and every check caught something real:

```bash
ffmpeg -v error -xerror -i out.mp4 -f null -        # not truncated
ffprobe -select_streams v:0 -show_entries stream=color_primaries,color_transfer,color_space
ffmpeg -ss <seg> -t <len> -i out.mp4 -map a:0 -af volumedetect -f null /dev/null
```

- Duration equals the sum of the parts — derive it from the plan
  (`python3 tools/megacut.py stories/megacut/megacut.json --dry-run` prints the
  expected total; 1232.659s planned for v0.8 and v0.9, against 1232.765s
  measured on the delivered v0.9 — 1221.859s for v0.6 and v0.7, plus act VI
  v2's net +10.800s. v0.9 changed act VI's AUDIO only, so the plan total is
  unchanged) rather than trusting a number typed here.
- **Per segment**, the peak matches its source — a re-encode must not lift one.
- **Colour**: `bt709` primaries, transfer **and** matrix. `-color_primaries`
  describes the *frames*; x264 copies only the matrix from them, so the VUI is
  written with `-x264-params` and probed afterwards.
- Extract frames either side of every join, inside all six plate windows, and
  at the head and tail of the title cover — **and look at them**. On the
  cover, check that no caption box touches the ink: that is the whole point
  of the margins, and it is a visual judgement no assertion replaces.
