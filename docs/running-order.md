# The running order

**This file is the source of truth for what the show is and what order it plays
in.** Everything else executes it: `stories/megacut/megacut.json` assembles it,
`stories/megacut/megacut-cards.json` announces it, and
`docs/cuts/08-directors-cut-megacut.md` records how the current build was made.
If one of those disagrees with this file, this file is right and the other is a
bug.

## Seven Days to the Wolves, in eight acts — behind a prologue

Settled by the owner on 2026-08-12 and **canonical**:

> intro → endlessformsmostbeautiful → mrbobbytables → kat → nat →
> 7daystothewolves → europa → credits

On 2026-08-14 the owner added a **prologue in front of it**. That order is
untouched: the prologue takes **no numeral** and nothing is renumbered.

| Act | Chapter | The film | State |
|---|---|---|---|
| **0** | *(no chapter — it is the main title)* | `Prod/00-prologue.mp4` — Nightwish's *Perfume Of The Timeless*, the main title at 0:11, then the March day→night bridge | delivered, **prototype**; shipping form is an embed |
| **I** | Project Bluefin | `Prod/01-intro.mp4` — Into the Light, six Guardians plated, the title cover | delivered |
| **II** | *Endless Forms Most Beautiful* | `Prod/02-endlessformsmostbeautiful.mp4` — the live-action trailers, and *The Long Walk* inside them | delivered and **credited**, in the programme |
| **III** | Bob Killen | `Prod/03-mrbobbytables.mp4` — August 2026 contributors | delivered, **partially complete** |
| **IV** | Bias for Action | `Prod/04-kat.mp4` — Kat Cosgrove | delivered, with the owner's dialogue change; **shares act V's slide** |
| **V** | Wrong Place, Wrong Time, Right Attitude | `Prod/05-nat.mp4` — Natali Vlatko | delivered; **shares act IV's slide** |
| **VI** | 7 Days to the Wolves | `Prod/06-7daystothewolves.mp4` — the musical | **editorial pass**, provenance open — #55; the **#104 interruption build** (v2, 443.5 s), its tail plating the Cayde-6 reveal and three gold credits; **the programme plays 431.267 of it** (v2.1) — the comic and the fade cut off the end, the file untouched |
| **VII** | Europa | `Prod/07-europa.mp4` — the director's cut | delivered; **no slide, no chapter marker** (v2.1) — a quick cut off movement 4; **1:37.266**, the comic cover cut so act VIII owns the reveal — #178; plays the pre-terse-pass film — #102; master corrected to −1.1 dBTP — #82 |
| **VIII** | Credits | `Prod/08-credits.mp4` — the cast, 619 contributors across **six** projects, the comic-cover reveal and the wordmark | delivered, **in the programme**; **no slide, no chapter marker** — it is meant to surprise — #51 |

## The prologue, and why it has no numeral

Added 2026-08-14 on the owner's instruction: *"Make this video the intro in
front of endless forms"*, pointing at Nightwish's official music video for
**"Perfume Of The Timeless"** (`oHCaZmIzr0o`). Asked where it should sit, the
owner placed it as a **new cold open in front of act I** — *Into the Light*
stays exactly where it was.

**It takes no numeral, and that is the whole design.** The eight numerals are
load-bearing: `AGENTS.md` says III is `mrbobbytables` permanently, and
renumbering to make room for a ninth act at the front would move every chapter
marker, every `Prod/NN-*.mp4` filename and every key in
`stories/megacut/delivery.json`. So it delivers as `00-prologue` and the
canonical eight-act order above is unchanged.

**It carries no slide and no chapter marker**, for the same reason act VIII
carries none: `chapters()` derives markers from slides, and a card announcing
the main title sequence would step on the main title sequence.

| | |
|---|---|
| Runtime | **1:39.200** — 91.200 of picture, then an 8.000 bridge |
| Title at | 11.000, staged: the lockup, then the credit pair at 15.400 |
| Out point | **91.200**, the source's own luma minimum (the owner said 1:31) |
| Master | `renders/00-prologue.mp4`, built by `scripts/build_prologue.py` |
| Copy | `stories/00-prologue-plates.json`, reproduced from the website's own cue |
| Rights | `music/bed_perfume_of_the_timeless.json` |

The build, the three measured numbers and the dramatic reasoning are in
[`docs/cuts/00-prologue.md`](cuts/00-prologue.md).

**The rendered file is a prototype, and the distinction matters.** Asked about
rights, the owner's answer was *"it's an iframe using their video don't
download it"* — the shipping presentation **embeds** Nightwish's video rather
than re-hosting it, and the web version is deliberately deferred (*"we are
prototyping we'll do the web thing later"*). So `Prod/00-prologue.mp4` exists
to cut and watch against, and the prologue is recorded in
`stories/megacut/delivery.json` as having **no social copy by design** — a
standalone clip is precisely the redistribution the embed avoids.

**One thing the owner may still want moved.** The written request said *"stop
at 1:31 and then transition to endless forms"*, while the placement chosen puts
the prologue in front of act I — so it currently plays
`PROLOGUE → I → II`, not `PROLOGUE → II`. The prologue was built
self-contained, with the bridge as its own tail, so moving it is one reordered
item in `stories/megacut/megacut.json` and a row here — not a re-render.

## The Perfume thread — the prologue was the first movement of five

Added 2026-08-14, later the same night, on the owner's instruction: take the
**middle** of the same music video and seat it between the acts. So the
prologue is no longer a cold open that ends — it is **movement 1 of five**, and
"Perfume Of The Timeless" now plays from the first frame of the show to the
last frame before the credits, **in source order and without gaps**. The eight
acts live inside it.

| Movement | Source in → out | Runtime | Seat |
|---|---|---|---|
| **1** — the prologue | 0 → 91.200 (+8 s bridge) | 1:39.200 | in front of act I |
| **2** | 93.000 → 159.400 | 1:06.400 | after act I |
| **3** | 159.400 → 328.080 | 2:48.685 | after act III |
| **4** | 328.080 → 389.800 | 1:01.728 | after act VI, before Europa |
| **5** | 389.800 → 507.021 (EOF) | 1:57.200 | after Europa, into the credits |

Movements 2–5 add **6:54.0**. They take **no numerals, no slides and no chapter
markers** — the same reasoning that keeps the prologue outside the eight, and
the chapter list still has its eight entries, though **every timestamp after
act I moved**.

They deliver to **`renders/` only, not `Prod/`**, and are rendered **clean** —
no fades, no overlays. The owner: *"we will be editing them in the future with
dino artwork"*, and a dinosaur pass wants unfaded picture. `Prod/` keeps meaning
"a finished act"; join treatment lives in `megacut.json` in act-film time.

**Two joins are the owner's to approve.** Movement 5 opens on the measured cut
at 389.800 to catch Europa's hand-down off Elsie Bray, and where exactly the
two camera moves meet is a judgement about frames. It also **moves the act VIII
ambush**: the drum smash now lands off the end of a different song, on a held
shot rather than on black.

The measured cut points, the two-answer in point and the rest are in
[`docs/cuts/00-perfume-thread.md`](cuts/00-perfume-thread.md).

**Act VIII has a film and the programme plays it.** Built from
`stories/08-credits.json` by `scripts/build_credits.py`: four fixed cards,
**eight** cast placards, the comic-cover reveal at :22, **619** contributors
across **six** projects, and the real Project Bluefin wordmark.

**The 2026-08-14 pass rebuilt how act VIII looks and who it names.** It runs
**3:47.303** now, not 3:48.430:

- **It is set in Adwaita**, resolved in `tools/credits.py` alone. `plate.py`
  still resolves DejaVu, because that reproduces the browser that baked the
  reference plates and changing it would restyle acts I–VII.
- **The frame is the desktop.** Every card sits on one of Project Bluefin's
  monthly **dark-mode** wallpapers — the dinosaurs — advanced card by card in
  calendar order and wrapping, graded blue rather than neutral (*"more blue
  than gold"*). November has no night art installed on this host, so the cycle
  is eleven months and says so. Cached by `scripts/fetch_wallpapers.py`, which
  decodes JPEG XL through GdkPixbuf because neither Pillow nor this host's
  ffmpeg can.
- **Fedora CoreOS and bootc lead the walls**, on their own larger grid — six
  across by three down against nine by four — under an `UPSTREAM` eyebrow, and
  each of their walls holds longer than a Bluefin one. The order is enforced
  in `schedule()`, so reordering the manifest cannot demote them.
- **The cast is the README's table minus Cayde-6**, by owner instruction. The
  six the vocab binds but the README does not list keep their bindings; only
  act VIII's placards went. Karena is **"Angel"**, one L.
- **The bed loops properly.** Span A used to end at 240.780, which is 0.7 s
  *inside* the song's own fade-out — so the loop played an ending and then the
  drums. It ends at 239.653152 now, the nearest tracked beat to the owner's :46.
- **"an ublue project" is off the wordmark.**
- **The picture is padded to outlast the music.** The concat demuxer lands
  short of the durations it is handed — 4.347 s short over 38 cards — so act
  VIII muxed 227.303 s of audio over 222.956 s of picture and four and a half
  seconds of the wordmark were not there. `tpad` clones the last frame and
  `-t` cuts both streams on one frame. **The megacut's own join check is what
  caught it**, not anybody's eyes.

**Still open on act VIII:** the principals' summit portraits. The owner asked
for *"a good shot of them from the CNCF contributor summit flickr feed"*; the
feed is twelve frames of one **group** photograph, so every crop box has to be
drawn by somebody who can say which face is whose — a visual judgement AND a
claim about a real person. The mechanism is built
(`tools/credits.summit_portrait`), `cast_photos` is empty, and the placards
degrade to the verified avatar until the owner fills it in.

**It is the one act with no slide and no chapter marker**, by owner
instruction — *"no credits slide, go right to the metal … it should surprise
the viewer."* Europa fades to black on its own tail and the drum smash lands on
the next frame. The missing marker is deliberate too: `chapters()` derives them
from slides, so a *VIII. Credits* entry on the scrub bar would spoil the same
surprise the cut is built to land. Every other act is still announced.

**Act VII no longer ends on the comic cover.** The cover is act VIII's reveal
now, so Europa ends on the fade-to-black it already had, 12.934 s earlier
(#178). Every chapter mark after act VII moved by that amount.

**The numbering is fixed.** III is `mrbobbytables` permanently, whatever gets
built later.

**Act II has a film** ([`docs/cuts/02-endless-forms-most-beautiful.md`](cuts/02-endless-forms-most-beautiful.md)),
delivered to `Prod/` and **in the programme**: it has a slide, a chapter marker,
and its own place on the clock. Seven of the eight acts now play, which is what
**v0.5** was; the current build is **v1.0** — all eight acts, 24:07.1. Its last pass (2026-08-14) rebuilt act VIII's look and cast and gave act II the CNCF round: four OG Guardians in bronze, a re-staggered trio, a team badge, four new lines, a full-frame Destiny-style **choice screen** with a cursor that never lands, and AN4-CH3CK-12 removed. It is also the first feature act to carry **nameplates** — thirteen
of them, generated rather than placed by hand — now eighteen, plus a chapter
card, twenty-six dialogue pills, a patch-queue HUD, a villain's bar and the
letterbox callout, all of it still generated.

**Act I carries the GUARDIAN BOND companion cards**, ported from the live
overlay: Karl beside Kat, Alamo beside Natali, Katerina beside Kaslin, and Bob
Killen's unnamed Torosaurus beside Cortney, which she inherits by the owner's
explicit decision rather than by the recast.

**Act II emits two sub-chapters, consumed only on opt-in.** `TOC` at 0:54.234
and `The Long Walk` at 2:27.801, in the act's own film time
(`python3 scripts/build_efmb_plates.py --chapters`). `chapters()` below derives
markers from act **slides** only, so an act's internal marks stay out of the
published list unless asked for: the act's clip in the programme plan carries a
`sub_chapters` **pointer** at its own manifest (the source of the marks), and
`--sub-chapters` emits them at slide-relative programme time. The default
chapter list is unchanged —
[#92](https://github.com/castrojo/destiny-vids/issues/92). They are anchored
to source timecodes, so they cannot drift from the credits they belong to.
**TODO(owner):** whether sub-chapters belong in the YouTube chapter list at
all, or only in an ffmpeg metadata track.

**Acts IV and V share one slide.** The owner's call: their films run 34 s and
25 s, and two slides held 15 s each announced 59 s of picture. Both acts keep
their numerals and their films — it merges the announcement, not the acts — and
it is one chapter marker, because a chapter starts on its slide and there is now
one slide.

The slide's copy is **owner-authored**: *Bias for Action*, subtitled *The Kat
and the Nat*, over act IV's terminal block. Act V's own title, *Wrong Place,
Wrong Time, Right Attitude*, stays its name here but **no longer appears on
screen** — recorded in the manifest's `unresolved`, because losing a title
somebody wrote should be deliberate.

**One person, one act.** `mrbobbytables` appears once, at III. An earlier pass
had him twice — as an empty act and as another act's film under his character's
name — and that is the specific mistake this table exists to prevent.

## Chapters

The acts **are** the chapters. Their titles are authored on the act slides
(`chapter` in `stories/megacut/megacut-cards.json`'s companion plan), and the
timestamps are **derived, never typed**:

```bash
python3 tools/megacut.py stories/megacut/megacut.json --chapters
```

```text
0:00  I. Project Bluefin
1:56  II. Endless Forms Most Beautiful
7:09  III. Bob Killen
9:54  IV–V. Bias for Action
11:08 VI. 7 Days to the Wolves
18:37 VII. Europa
```

**20:32.7**, six markers for seven acts. Every stamp after act I moved when act
II was wired in, everything after act III moved again when acts IV and V were
given one slide, and slide VII moved +10.811 s when act VI became the #104
interruption build — which is exactly why they are derived and never typed.

A chapter starts on its **act slide**, not on the film behind it: the slide is
how the audience is told which act this is. The list regenerates from the plan's
own clock, so it cannot drift when a cut's length changes — re-run it after
every assembly and paste the output into the upload description.

Each act may also carry **sub-chapters** — a contents list rendered under the
title. **They all live in one place:** `chapters[]` on that act's entry in
[`stories/megacut/megacut-cards.json`](../stories/megacut/megacut-cards.json).
Edit the array, re-render the cards, rebuild. A line nobody authored is omitted
rather than defaulted, so deleting one removes it from the slide.

Five acts carry a **drafted** list (I, II, III, VI, VII). Every line is either
read off the built film or reproduced from that act's own cut record, and each
card's `note` cites which — **none of it is the owner's copy yet**. Acts IV and
V carry none on purpose: 34 s and 25 s, one continuous scene each, so a contents
list would be longer than the thing it indexes.

```bash
node cards/render-cards.mjs --manifest stories/megacut/megacut-cards.json \
    --out-dir renders/plates-megacut-cards
```

## Where the files live

`~/Videos/Wolves/` is the delivery workspace. Three folders, one job each:

| Folder | What goes in it |
|---|---|
| `Prod/` | **The show, at the highest quality that exists.** One file per act, named `NN-<act>.mp4`. FLAC audio where a lossless master exists (act VI is AAC pending #58), no re-encoded picture. Hardlinks to each project's own master, so Prod costs no disk and cannot drift from what built it. |
| `10mb/` | Social copies, capped by bytes. Built by `tools/social.py` from `Prod/`, **never** from another social copy. |
| `megacut/` | The final movie, and nothing else. Assembled by `tools/megacut.py`. |

Nothing is hand-edited in any of them; every file is a regenerated artifact of a
script in this repo or in its own `~/Videos/<project>/render/`.

```bash
# the final movie
python3 tools/megacut.py stories/megacut/megacut.json

# a social copy of one act
python3 tools/social.py ~/Videos/Wolves/Prod/05-nat.mp4 \
    --out ~/Videos/Wolves/10mb/05-nat.mp4 --audio-bitrate 256
```

## What Prod is still missing

Recorded, not hidden:

- **Act VI has no lossless master** — the musical is AAC, so `Prod` holds the
  best that exists rather than the best possible. Issue #58. Its master lives in
  `~/Videos/wolves-musical/`, re-homed out of the retired `UPLOAD/` staging
  folder (issue #81) by moving the inode, so the hardlink never broke.
- ~~**Act VII's master clips** at +0.3 dBTP — issue #82.~~ **Fixed 2026-08-13**:
  Europa's own build was re-rendered under the new master gate
  (`tools/peaks.py trim`, PR #130) and the delivered master now measures
  **−1.1 dBTP**, inside the −0.9…−1.1 band. The issue stays open for its owner
  to close.
- **Act VIII does not exist.** Issue #51. The programme therefore ends on
  Europa with **no credit roll**, which is the single biggest reason the
  current build is not the feature. The only names in the show are act VI's
  tail — the Cayde-6 reveal (Jorge Castro) and three gold credits behind it —
  and a reveal inside an act is not a credits sequence.
- **Act II's picture is a fan compilation**, not an official Bungie upload —
  the same provenance question act VI carries (#55). See its cut doc.

Delivered on 2026-08-12, so the two encode gaps this file used to list are
closed:

- **Act I** is rendered and delivered as `Prod/01-intro.mp4` — the frame-verified
  2.0 → 113.55 trim of `BKm0TPqeOjY`, six Guardian plates and the title cover
  burned, Bungie's own score decoded from the **plain 251 Opus rung** to
  FLAC. Not `251-drc`: that rung is dynamic-range compressed, and taking it
  would have been the pipeline applying processing it forbids.
- **Act IV carries the owner's dialogue change** — the Kat/Ian split and
  "Remember kids, cardio!" are rendered and on screen, verified frame by frame.
  Rebuilt in `~/Videos/wolves-kat/` with `node render/render-plates.mjs`, then
  `./render/run-kat.sh` and the `SURROUND=0 ACODEC=flac OUT=…-hq.mp4` variant.
  The `Prod` hardlink survived the rebuild, because the script writes its master
  in place rather than replacing the file.
