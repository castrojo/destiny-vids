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
| **I** | Project Bluefin | Into the Light, six Guardians plated, the comic card | built in-repo, **not yet rendered** |
| **II** | *Endless Forms Most Beautiful* | — | **no film** — #74 |
| **III** | Bob Killen | `Prod/03-mrbobbytables.mp4` — August 2026 contributors | delivered, **partially complete** |
| **IV** | Bias for Action | `Prod/04-kat.mp4` — Kat Cosgrove | delivered; a dialogue change is staged, unrendered |
| **V** | Wrong Place, Wrong Time, Right Attitude | `Prod/05-nat.mp4` — Natali Vlatko | delivered |
| **VI** | 7 Days to the Wolves | `Prod/06-7daystothewolves.mp4` — the musical | **timing pass**, provenance open — #55 |
| **VII** | Europa | `Prod/07-europa.mp4` — the director's cut | delivered |
| **VIII** | Credits | — | **not designed** — #51 |

**The numbering is fixed.** Acts II and VIII have no film, so they get no slide
and no chapter marker — a card announcing an act that does not play, or a marker
that jumps to the next act's footage, is a lie about what the audience is
watching. They keep their numerals so nothing renumbers around them: III is
`mrbobbytables` permanently, whatever gets built later.

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

- **Act I** is not rendered. It is built here (`renders/megacut-01-hero.mkv`)
  and belongs in `Prod/01-intro.mp4` once it is.
- **Act VI has no lossless master** — the musical is AAC, so `Prod` holds the
  best that exists rather than the best possible. Issue #58.
- **Act IV's master predates the owner's dialogue change** (the Kat/Ian split
  and "Remember kids, cardio!"), which is staged in `~/Videos/wolves-kat/` and
  unrendered.
- **Acts II and VIII do not exist.**
