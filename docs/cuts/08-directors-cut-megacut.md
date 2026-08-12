# Seven Days to the Wolves — the programme, in acts

The whole show as **one continuous video**, assembled from the finished cuts and
announced by act slides in the Wolves cinematic's own chrome.

**Status: v0.5 is built** — `~/Videos/Wolves/megacut/seven-days-to-the-wolves-v0.5.mp4`,
**20:21.9** planned, seven of the eight acts on six slides — acts IV and V
share one. The last *built* file is 20:37.0 and predates that merge. The owner asked for "one
supercut with everything that we have", and .5 is their name for it.

It is **not the feature**. Act VIII, the credits, is not designed (#51), so the
programme ends on Europa and credits nobody. Act VI is a timing pass whose
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
| **I** | 5.000 | 116.567 | **Into the Light** — six Guardians plated, the comic card, Bungie's score | `Prod/01-…` |
| — | 116.567 | 121.567 | Slide **II** — `ENDLESS FORMS MOST BEAUTIFUL` / *Nightwish* | rendered |
| **II** | 121.567 | 429.534 | **Endless Forms Most Beautiful** — the live-action trailers, one song end to end | `Prod/02-…` |
| — | 429.534 | 434.534 | Slide **III** — `Bob Killen` / *Voidwalker Warlock* | rendered |
| **III** | 434.534 | 594.734 | **mrbobbytables** — August 2026 contributors | `Prod/03-…` |
| — | 594.734 | 609.734 | Slide **IV–V** — the terminal block, both titles, held 15s | rendered |
| **IV** | 609.734 | 643.734 | **Kat Cosgrove** — Guardian intro | `Prod/04-…` |
| **V** | 643.734 | 668.992 | **Natali Vlatko** — Guardian arrival, straight off act IV | `Prod/05-…` |
| — | 668.992 | 673.992 | Slide **VI** — `7 Days to the Wolves` / *Nightwish* | rendered |
| **VI** | 673.992 | 1106.692 | **Seven Days to the Wolves** — the musical (timing pass) | `Prod/06-…` |
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

**Act V carries the same terminal block.** "Make the slide with the unauthorized
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

### The comic title card, and the Amber Graner quote

Owner instruction: *"we need the 'comic book' slide with amber graner's quote
covering the same area."*

The site's full-screen comic title card is reproduced by `cards/comic.html`,
which copies `.wolves-intro-overlay-title-card` and friends out of
`WolvesIntroOverlay.vue` — the opaque black card, the cycling comic hero shot,
the MakeMeAComic QR panel, and the quote:

> "You don't need permission to contribute to your own destiny."
> — **Amber Graner**, Maintainer Guardian // The Iron Standard - Subclass [ REDACTED ]

It **covers** the cinematic for its window, exactly as the site does. The site
cues it at source 24–38; here it runs **source 24.5 – 38 (segment 22.5 – 36.0)**
so it cannot overlap Kat's plate, which the live overlay draws *on top* of the
card and `tools/plate.py` has no z-order for. The 23 authored hero shots share
the window evenly — the same slot arithmetic `getComicHeroShotIndex()` uses —
burned as 23 back-to-back stills. The 0.35s cross-fade between them is the one
thing a still cannot carry, and it is recorded rather than faked.

### The Guardian plates, and two recasts

| Programme | Verified on screen | Plate |
|---|---|---|
| 3.0 – 12.5 | purple void vortex | **Cortney Nickerson** (was Bob Killen) |
| 12.5 – 22.5 | Ward of Dawn bubble, Titan inside | Kat Cosgrove — Sentinel Titan |
| 38.0 – 46.0 | arc lightning duel | Kaslin Fields — Stormcaller Warlock |
| 68.5 – 75.0 | solar winged Guardian | **Orlin** (was Laura Santamaria) |
| 83.0 – 93.0 | green Strand tendrils | Christoph Blecker — Broodweaver Warlock (leader, gold) |
| 87.5 – 94.0 | icy-blue crystal Guardian, right of frame | Natali Vlatko — Behemoth Titan |

**The recasts changed who is credited, never which shot**, so the frame-verified
windows are untouched and nothing needs re-checking against the picture.

Both new names are rendered as a **name and nothing else**. Neither has an
authored Guardian identity in any of the places identities live
(`~/Videos/nameplates.json`, the website's `characters.json`,
`vocab/casting.yaml`), and the previous occupant's label, subclass and title are
**his and hers** — inheriting them would put Bob Killen's *Reconciler of the
Plane* on Cortney's card. A missing row is omitted; it is never guessed.

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

- **Cortney Nickerson's Guardian identity** — issue #59. Until it is authored,
  her plate is a name.
- **Who "Orlin" is.** The instruction was *"laura santamaria is orlin"*, given
  with intro notes, so it is applied to the intro plate **and nowhere else**;
  the Europa director's cut still credits Laura Santamaria. No surname, no
  authored identity. Both open.
- **Act II has no film and no named track.** "It's endless forms most
  beautiful, instrumental" names the *record*, not which instrumental.
- **Act IX has no design** — #51.
- **Act III has no subject.** An open numbered slot, the owner's to fill.
- **Act VI is partially complete, by the owner's own description**, and it is
  placed as-is: assembly joins finished things and never re-cuts one. Finishing
  it happens upstream. Its slide carries Bob Killen's **authored** Guardian
  identity rather than an act title, because the film has none (#41) and one
  would have to be written. **This does not contradict the intro recast**: the
  owner replaced him on *one plate in act I*, and `vocab/casting.yaml` still
  binds Osiris to mrbobbytables with Bob's plate, which is what act VI's film
  credits.
- **Act VII is a timing pass, not an approved cut**, and its provenance is
  open (#55). Staging is not publishing; this programme stays in `renders/`.
- **Kat's cut is about to change under this plan.** The dialogue split and
  "Remember kids, cardio!" are staged in `~/Videos/wolves-kat/` and not
  rendered, so `Prod/04-kat.mp4` is still the old dialogue. Rebuild it there
  and re-link, or the programme ships the superseded lines.
- **Chapters for every act.** The renderer takes them; nobody has written them.
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

- Duration equals the sum of the parts (918.926s expected).
- **Per segment**, the peak matches its source — a re-encode must not lift one.
- **Colour**: `bt709` primaries, transfer **and** matrix. `-color_primaries`
  describes the *frames*; x264 copies only the matrix from them, so the VUI is
  written with `-x264-params` and probed afterwards.
- Extract frames either side of every join, inside all six plate windows, and
  at the head and tail of the comic card — **and look at them**.
