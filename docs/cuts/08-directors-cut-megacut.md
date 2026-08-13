# Seven Days to the Wolves — the programme, in acts

The whole show as **one continuous video**, assembled from the finished cuts and
announced by act slides in the Wolves cinematic's own chrome.

**Status: v0.7 is built** — `~/Videos/Wolves/megacut/seven-days-to-the-wolves-v0.7.mp4`,
**20:21.9** planned, seven of the eight acts on six slides — acts IV and V
share one. v0.7 is v0.6 with the **act-join treatment** of
[#105](https://github.com/castrojo/destiny-vids/issues/105): every act used to
enter dry out of the slides' digital silence (4–14 s of `-inf` per join, then
an entry as hot as −15 dB a second later), and acts I and III ended hot
against it. The plan now carries explicit `fade_in`/`fade_out` shapes per act
(act-film clock, `afade` at the segment encode, no gain anywhere); durations
are unchanged, so **no chapter moved**, and v0.6 is kept beside it. Earlier:
v0.6 added **act VI's tail plates** (the Cayde-6 reveal that finally names
Jorge Castro, and three gold credits behind it — see
[`07-seven-days-to-the-wolves.md`](07-seven-days-to-the-wolves.md), "The tail
plates"). The owner asked for "one
supercut with everything that we have", and .5 was their name for it.

It is **not the feature**. Act VIII, the credits, is not designed (#51), so the
programme ends on Europa — though it no longer credits *nobody*: act VI's tail
now names Jorge Castro, Kelsey Hightower, Brian Ketelsen and Angie Jones. Act
VI is an editorial pass whose
provenance is an open owner decision (#55); act II's picture comes from a fan
compilation carrying the same question; act III is partially complete by the
owner's own description; act VII's master clips at +0.3 dBTP (#82). None of that
is fixable by re-assembling — assembly joins finished things and never re-cuts
one.

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
| **VI** | 673.992 | 1106.692 | **Seven Days to the Wolves** — the musical (editorial pass) | `Prod/06-…` |
| — | 1106.692 | 1111.692 | Slide **VII** — `Europa` / *Director's Cut* | rendered |
| **VII** | 1111.692 | 1221.892 | **Europa Director's Cut** | `Prod/07-…` |
| **VIII** | — | — | Credits — **not designed** (#51) | — |

**1221.892s planned — 20:21.9**, output to
`~/Videos/Wolves/megacut/`. The 79 ms is act II's audio leg outrunning its
video leg by 31 ms plus per-segment rounding; it does not accumulate, and every
act slide lands within a second of its mark. Every act plays
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
  carries the old Foreman lines; its master also clips at +0.3 dBTP (#82).
  Rebuild it in `~/Videos/wolves-directors-cut/` and re-link.
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
  expected total; 1221.859s for v0.6 and v0.7 — fades do not move the clock) rather than trusting a number typed here.
- **Per segment**, the peak matches its source — a re-encode must not lift one.
- **Colour**: `bt709` primaries, transfer **and** matrix. `-color_primaries`
  describes the *frames*; x264 copies only the matrix from them, so the VUI is
  written with `-x264-params` and probed afterwards.
- Extract frames either side of every join, inside all six plate windows, and
  at the head and tail of the title cover — **and look at them**. On the
  cover, check that no caption box touches the ink: that is the whole point
  of the margins, and it is a visual judgement no assertion replaces.
