# Seven Days to the Wolves — the programme, in acts

The whole show as **one continuous video**, assembled from the finished cuts and
announced by act slides in the Wolves cinematic's own chrome.

**Status: planned and staged, NOT rendered.** The act slides and the comic title
card are rendered and reviewable in `renders/`; the programme itself is not
built, by owner instruction ("fix it in the video don't render it"). Nothing
goes to `~/Videos/UPLOAD/` for the feature — provenance there is an unresolved
owner decision (#55) and this cut does not change it.

## The canonical order

Given by the owner, verbatim:

> intro -> endlessdaysmostbeautiful -> mrbobbytables -> kat -> nat ->
> 7daystothewolves -> europa -> end credits

then amended twice: *"add osiris before europa and after nat"*, and then

> there is no "osiris" movie anymore it's the mrbobbytables one in 04 in
> uploads and it's in slot VI

So **mrbobbytables plays once, as act VI**, between nat and the musical — the
correction was that he had been named twice, as an empty act III *and* as act
VI's film. The acts run **I–IX**, and each slide carries its numeral, huge. Every act is to carry **chapters**;
none have been authored yet, so every `chapters` list is empty and the field
renders nothing.

| Act | From | To | What | Source |
|---|---|---|---|---|
| — | 0.000 | 5.000 | Slide **I** — `PROJECT BLUEFIN` / *seven days to the wolves* | rendered |
| **I** | 5.000 | 116.567 | **Into the Light** — six Guardians plated, the comic card, Bungie's score | `BKm0TPqeOjY` |
| **II** | — | — | **Endless Forms Most Beautiful (instrumental)** — **NOT BUILT** (#74) | — |
| **III** | — | — | **unnamed** — an open slot, no subject and no film | — |
| — | 116.567 | 131.567 | Slide **IV** — `BIAS FOR ACTION`, held 15s | rendered |
| **IV** | 131.567 | 165.567 | **Kat Cosgrove** — Guardian intro | `UPLOAD/01-…` |
| — | 165.567 | 180.567 | Slide **V** — `WRONG PLACE, WRONG TIME, RIGHT ATTITUDE`, held 15s | rendered |
| **V** | 180.567 | 205.826 | **Natali Vlatko** — Guardian arrival | `UPLOAD/02-…` |
| — | 205.826 | 210.826 | Slide **VI** — `Bob Killen` / *Voidwalker Warlock* | rendered |
| **VI** | 210.826 | 371.026 | **mrbobbytables** — August 2026 contributors, Curse of Osiris | `UPLOAD/04-…` |
| — | 371.026 | 376.026 | Slide **VII** — `7 Days to the Wolves` / *Nightwish* | rendered |
| **VII** | 376.026 | 803.726 | **Seven Days to the Wolves** — the musical (timing pass) | `UPLOAD/07-…` |
| — | 803.726 | 808.726 | Slide **VIII** — `Europa` / *Director's Cut* | rendered |
| **VIII** | 808.726 | 918.926 | **Europa Director's Cut** | `UPLOAD/zz-…` |
| **IX** | — | — | **End credits** — **NOT DESIGNED** (#51) | — |

**918.926s — 15:19.** The five delivered cuts are reused **as-is**: four are
owner-approved, and act VI is the partially complete one. This repo cannot
rebuild any of them — they are `~/Videos` projects with their own
`render/run-*.sh`. Assembly re-encodes them once and edits nothing.

**Acts II, III and IX have no card.** A slide announcing an act that does not
play is worse than a recorded gap, so they keep their numerals in the manifest's
`unresolved` list and nothing else. The numbering does not close up over them.

**Act III is an open slot with no subject.** The owner's first running order
put `mrbobbytables` third; his film is act VI by explicit instruction, so
naming III after him as well would put one person in the programme twice —
which is exactly what he caught. III keeps its numeral and nothing else,
because **VI is pinned** and renumbering around III would move it.

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
  rendered, so `UPLOAD/01-…` is still the old dialogue. Rebuild it there
  before assembling, or the programme ships the superseded lines.
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
