# The running order

**This file is the source of truth for what the show is and what order it plays
in.** Everything else executes it. If another file disagrees with this one about
the *order*, this one is right and the other is a bug.

This file names the acts. It does not restate how they were built — that lives
in the machine records, which are the only copy:

| Question | Answer lives in |
|---|---|
| What plays, in what order, with what trims | [`stories/megacut/megacut.json`](../stories/megacut/megacut.json) — `items[]` |
| Why the current build looks the way it does | the same file's `_version` |
| Which master each act hardlinks, and why | [`stories/megacut/delivery.json`](../stories/megacut/delivery.json) — `masters` |
| The authored card copy, including retired cards | [`stories/megacut/megacut-cards.json`](../stories/megacut/megacut-cards.json) |
| Whether any of it is stale | `python3 tools/deliver.py status` |

## Seven Days to the Wolves — eight acts, behind a prologue

The canonical order, settled by the owner and **not open for reinterpretation**:

> prologue → intro → endlessformsmostbeautiful → mrbobbytables → kat → nat →
> 7daystothewolves → europa → credits

| Act | Chapter title | The film |
|---|---|---|
| **0** | *(none — it is the main title)* | `Prod/00-prologue.mp4` |
| **I** | Project Bluefin | `Prod/01-intro.mp4` — Into the Light, six Guardians plated |
| **II** | *Endless Forms Most Beautiful* | `Prod/02-endlessformsmostbeautiful.mp4` — the live-action trailers |
| **III** | Bob Killen | `Prod/03-mrbobbytables.mp4` — monthly contributors |
| **IV** | Bias for Action | `Prod/04-kat.mp4` — Kat Cosgrove |
| **V** | *(shares act IV's marker)* | `Prod/05-nat.mp4` — Natali Vlatko |
| **VI** | 7 Days to the Wolves | `Prod/06-7daystothewolves.mp4` — the musical |
| **VII** | *(no marker)* | `Prod/07-europa.mp4` — the director's cut |
| **VIII** | *(no marker — it is meant to surprise)* | `Prod/08-credits.mp4` — the call to action, the comic reveal, the credits |

**All nine films exist and all nine play.** The current programme is **v3.0**,
**35:16.8**, at `~/Videos/Wolves/megacut/`.

### Three things about this table that are load-bearing

**The numerals never move.** III is `mrbobbytables` permanently. Renumbering to
close a gap would move every chapter marker, every `Prod/NN-*.mp4` filename and
every key in `delivery.json`. The prologue therefore takes **no numeral** and
delivers as `00-prologue`.

**One person appears once.** `mrbobbytables` is act III and nowhere else. An
earlier pass had him twice — as an empty act, and as another act's film under
his character's name.

**Not every act is announced.** The Roman-numeral slides were retired on the
owner's instruction; the programme plays exactly one card, the scream
interstitial between acts V and VI — *ON THE LINUX DESKTOP /
No one can hear you scream* — which carries no numeral and no marker, because a
scrub-bar entry would spoil the gag. Acts VII and VIII carry no marker
deliberately either: act VIII's whole design is that it surprises the viewer.

## The Perfume thread

Nightwish's *Perfume Of The Timeless* plays from the first frame of the show to
the last frame before the credits, **in source order and without gaps**. The
prologue is movement 1; four more movements sit between the acts.

| Movement | Seat |
|---|---|
| **1** — the prologue | in front of act I |
| **2** | after act I |
| **3** | after act III |
| **4** | after act VI, before Europa |
| **5** | after Europa, into the credits |

They take **no numerals, no slides and no chapter markers**, and they deliver to
`renders/` rather than `Prod/`, rendered **clean** — no fades, no overlays,
because a dinosaur-artwork pass is planned and wants unfaded picture. `Prod/`
means "a finished act"; join treatment lives in `megacut.json`, in act-film
time.

The measured in and out points are in `megacut.json`. Do not copy them here.

## Chapters

The acts **are** the chapters. Their titles are authored copy; the timestamps
are **derived, never typed**, because every stamp moves whenever anything
before it does.

```bash
python3 tools/megacut.py stories/megacut/megacut.json --chapters
```

```text
1:41  I. Project Bluefin
9:34  III. Bob Killen
14:09 IV–V. Bias for Action
15:13 VI. 7 Days to the Wolves
```

Re-run it after every assembly and paste the output into the upload
description. Never hand-edit the list.

**One recorded defect: the first marker is not 0:00.** YouTube ignores a chapter
list that does not open at zero, and the prologue carries no chapter by design.
Closing the gap means authoring a title for the prologue — the owner's call, and
`format_chapters` deliberately does not invent one.
[#220](https://github.com/castrojo/destiny-vids/issues/220).

Acts may also carry **sub-chapters** — `chapters[]` on that act's entry in
`megacut-cards.json`. Nothing renders them today, and `--chapters` omits them
unless asked with `--sub-chapters`.

## Where the files go

`~/Videos/Wolves/` — three folders, one job each, every file a regenerated
artifact:

| Folder | What goes in it |
|---|---|
| `Prod/` | **The show at the highest quality that exists.** One file per act, `NN-<act>.mp4`, FLAC where a lossless master exists, picture never re-encoded. Hardlinks to each project's own master, so it costs no disk and cannot drift. |
| `10mb/` | Social copies under a byte cap (`tools/social.py`), built from `Prod/` and never from each other. |
| `megacut/` | The final movie, and nothing else. |

```bash
python3 tools/deliver.py status     # what is stale and why
python3 tools/deliver.py build      # rebuild exactly what is stale
python3 tools/deliver.py publish    # after ANY act rebuild
```

Applying a round of notes to the right act:
[`skills/review.md`](skills/review.md). The audio the delivered files are held
to: [`skills/audio/SKILL.md`](skills/audio/SKILL.md).

## What is still open

Tracked as issues, not as prose here, so this file cannot go stale behind them:
[the open backlog](https://github.com/castrojo/destiny-vids/issues). The ones
that block *the feature* rather than an act are the provenance question
([#55](https://github.com/castrojo/destiny-vids/issues/55)) and act VI's
lossless bed ([#58](https://github.com/castrojo/destiny-vids/issues/58)).
