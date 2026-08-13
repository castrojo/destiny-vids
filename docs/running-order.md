# The running order

**This file is the source of truth for what the show is and what order it plays
in.** Everything else executes it: `stories/megacut/megacut.json` assembles it,
`stories/megacut/megacut-cards.json` announces it, and
`docs/cuts/08-directors-cut-megacut.md` records how the current build was made.
If one of those disagrees with this file, this file is right and the other is a
bug.

## Seven Days to the Wolves, in eight acts

Settled by the owner on 2026-08-12 and **canonical**:

> intro → endlessformsmostbeautiful → mrbobbytables → kat → nat →
> 7daystothewolves → europa → credits

| Act | Chapter | The film | State |
|---|---|---|---|
| **I** | Project Bluefin | `Prod/01-intro.mp4` — Into the Light, six Guardians plated, the comic card | delivered |
| **II** | *Endless Forms Most Beautiful* | `Prod/02-endlessformsmostbeautiful.mp4` — the live-action trailers, and *The Long Walk* inside them | delivered and **credited**, in the programme |
| **III** | Bob Killen | `Prod/03-mrbobbytables.mp4` — August 2026 contributors | delivered, **partially complete** |
| **IV** | Bias for Action | `Prod/04-kat.mp4` — Kat Cosgrove | delivered, with the owner's dialogue change; **shares act V's slide** |
| **V** | Wrong Place, Wrong Time, Right Attitude | `Prod/05-nat.mp4` — Natali Vlatko | delivered; **shares act IV's slide** |
| **VI** | 7 Days to the Wolves | `Prod/06-7daystothewolves.mp4` — the musical | **editorial pass**, provenance open — #55; its tail now plates the Cayde-6 reveal and three gold credits |
| **VII** | Europa | `Prod/07-europa.mp4` — the director's cut | delivered; plays the pre-terse-pass film — #102; its master clips — #82 |
| **VIII** | Credits | — | **not designed** — #51 |

**The numbering is fixed.** Act VIII has no film, so it gets no slide and no
chapter marker — a card announcing an act that does not play, or a marker that
jumps to the next act's footage, is a lie about what the audience is watching.
It keeps its numeral so nothing renumbers around it: III is `mrbobbytables`
permanently, whatever gets built later.

**Act II has a film** ([`docs/cuts/02-endless-forms-most-beautiful.md`](cuts/02-endless-forms-most-beautiful.md)),
delivered to `Prod/` and **in the programme**: it has a slide, a chapter marker,
and its own place on the clock. Seven of the eight acts now play, which is what
**v0.5** was; the current build is **v0.6**. It is also the first feature act to carry **nameplates** — thirteen
of them, generated rather than placed by hand — now fifteen, plus a chapter
card, twelve dialogue pills, a patch-queue HUD and a villain's bar, all of it
still generated.

**Act I carries the GUARDIAN BOND companion cards**, ported from the live
overlay: Karl beside Kat, Alamo beside Natali, Katerina beside Kaslin, and Bob
Killen's unnamed Torosaurus beside Cortney, which she inherits by the owner's
explicit decision rather than by the recast.

**Act II emits two sub-chapters that nothing consumes yet.** `TOC` at 0:54.234
and `The Long Walk` at 2:27.801, in the act's own film time
(`python3 scripts/build_efmb_plates.py --chapters`). `chapters()` below derives
markers from act **slides** only, so an act's internal marks have nowhere to go
— [#92](https://github.com/castrojo/destiny-vids/issues/92). They are anchored
to source timecodes, so they cannot drift from the credits they belong to.

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
18:26 VII. Europa
```

**20:21.9**, six markers for seven acts. Every stamp after act I moved when act
II was wired in, and everything after act III moved again when acts IV and V
were given one slide — which is exactly why they are derived and never typed.

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
- **Act VII's master clips** at +0.3 dBTP — issue #82. The AAC deliverable of
  the same cut measured −1.0 and passed for weeks; nothing had ever measured the
  FLAC master. It needs a re-render of Europa's own build, not a fix here.
- **Act VIII does not exist.** Issue #51. The programme therefore ends on
  Europa with **no credit roll**, which is the single biggest reason v0.6 is not
  the feature. The only names in the show are act VI's tail — the Cayde-6
  reveal (Jorge Castro) and three gold credits behind it — and a reveal inside
  an act is not a credits sequence.
- **Act II's picture is a fan compilation**, not an official Bungie upload —
  the same provenance question act VI carries (#55). See its cut doc.

Delivered on 2026-08-12, so the two encode gaps this file used to list are
closed:

- **Act I** is rendered and delivered as `Prod/01-intro.mp4` — the frame-verified
  2.0 → 113.55 trim of `BKm0TPqeOjY`, six Guardian plates and the comic title
  card burned, Bungie's own score decoded from the **plain 251 Opus rung** to
  FLAC. Not `251-drc`: that rung is dynamic-range compressed, and taking it
  would have been the pipeline applying processing it forbids.
- **Act IV carries the owner's dialogue change** — the Kat/Ian split and
  "Remember kids, cardio!" are rendered and on screen, verified frame by frame.
  Rebuilt in `~/Videos/wolves-kat/` with `node render/render-plates.mjs`, then
  `./render/run-kat.sh` and the `SURROUND=0 ACODEC=flac OUT=…-hq.mp4` variant.
  The `Prod` hardlink survived the rebuild, because the script writes its master
  in place rather than replacing the file.
