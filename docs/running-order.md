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
| **II** | *Endless Forms Most Beautiful* | `Prod/02-endlessformsmostbeautiful.mp4` — the live-action trailers | delivered, **not wired into the megacut** — #74 |
| **III** | Bob Killen | `Prod/03-mrbobbytables.mp4` — August 2026 contributors | delivered, **partially complete** |
| **IV** | Bias for Action | `Prod/04-kat.mp4` — Kat Cosgrove | delivered, with the owner's dialogue change |
| **V** | Wrong Place, Wrong Time, Right Attitude | `Prod/05-nat.mp4` — Natali Vlatko | delivered |
| **VI** | 7 Days to the Wolves | `Prod/06-7daystothewolves.mp4` — the musical | **timing pass**, provenance open — #55 |
| **VII** | Europa | `Prod/07-europa.mp4` — the director's cut | delivered; its master clips — #82 |
| **VIII** | Credits | — | **not designed** — #51 |

**The numbering is fixed.** Act VIII has no film, so it gets no slide and no
chapter marker — a card announcing an act that does not play, or a marker that
jumps to the next act's footage, is a lie about what the audience is watching.
It keeps its numeral so nothing renumbers around it: III is `mrbobbytables`
permanently, whatever gets built later.

**Act II now has a film** ([`docs/cuts/02-endless-forms-most-beautiful.md`](cuts/02-endless-forms-most-beautiful.md)),
delivered to `Prod/`. It is **not yet in the programme**: its slide and its clip
are a change to `stories/megacut/`, which was held open by another agent when
the act was built, so wiring it in is filed rather than done. Until that lands,
the assembled megacut still runs I, III, IV, V, VI, VII.

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
1:56  III. Bob Killen
4:41  IV. Bias for Action
5:30  V. Wrong Place, Wrong Time, Right Attitude
6:11  VI. 7 Days to the Wolves
13:28 VII. Europa
```

A chapter starts on its **act slide**, not on the film behind it: the slide is
how the audience is told which act this is. The list regenerates from the plan's
own clock, so it cannot drift when a cut's length changes — re-run it after
every assembly and paste the output into the upload description.

Each act may also carry **sub-chapters** (`chapters[]` on its slide, rendered
under the title). Nobody has written any, so every list is empty; the field is
there and the renderer draws it the moment somebody fills it in.

## Where the files live

`~/Videos/Wolves/` is the delivery workspace. Three folders, one job each:

| Folder | What goes in it |
|---|---|
| `Prod/` | **The show, at the highest quality that exists.** One file per act, named `NN-<act>.mp4`. FLAC audio, no re-encoded picture. Hardlinks to each project's own master, so Prod costs no disk and cannot drift from what built it. |
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
- **Act VIII does not exist.** Issue #51.
- **Act II exists but is not in the programme.** Issue #74. It is delivered to
  `Prod/`; its slide and clip are still to be added to `stories/megacut/`.

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
