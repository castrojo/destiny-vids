# What this project produces: the feature and hero videos

Two kinds of video come out of this repo. They are built by the same tools and
they are **not** the same thing, and most of the confusion in this repo's
history is one being cut as if it were the other.

| | **The feature** | **Hero video** |
|---|---|---|
| What it is | *Seven Days to the Wolves* — one whole unit | one person, one video |
| Scope of footage | whatever the story needs | **every clean shot of that character in the index** |
| Sources | as many as the story needs | **all of them, always** |
| Ordering authority | the story | the outline, arranged to say who someone is |
| Purpose | the thing itself | **promotional material for the feature** |
| How many | one | one per cast member, eventually |
| Ships | at KubeCon NA | weekly, in the run-up |

Release schedule for both: [`docs/release.md`](release.md).

## The feature: *Seven Days to the Wolves*

**One video, one unit.** Not a series and not separately-published parts — it is
released as a single piece at KubeCon NA.

It is **eight acts**, and [`running-order.md`](running-order.md) is the source of
truth for what they are and what order they play in. Read it before building
anything for the feature; if this file and that one disagree, that one is right.

The acts are announced by slides carrying a huge Roman numeral, and act VI is
the **musical** — one song end to end, cut to Nightwish's *7 Days to the
Wolves*, with its internal structure hinged on measured moments in the bed (the
gallop, the flute entry) rather than on chapter boundaries. The musical is the
longest act and the centre of the show; it is not the whole show.

An **editorial pass** of act VI is rendered:
[`cuts/07-seven-days-to-the-wolves.md`](cuts/07-seven-days-to-the-wolves.md).
The timing pass before it blacked out every doomed span at its exact duration
so the timing could be judged against the music; the owner's notes on that pass
have now been carried out, and every marker card is filled with picture. It is
still not a finished cut — it carries no nameplates.

The programme itself is assembled by `tools/megacut.py` from
`~/Videos/Wolves/Prod/` and **v0.6 is rendered** —
`~/Videos/Wolves/megacut/seven-days-to-the-wolves-v0.6.mp4` — though it is
still not the feature. The build record is
[`cuts/08-directors-cut-megacut.md`](cuts/08-directors-cut-megacut.md).

### What this replaced, and what is now placed

The feature was previously specified as four parts in a running order — the
Wolves video, the Europa director's cut, credits, then the Nati teaser. Then it
was specified as a musical, which left two finished pieces with nowhere to go.

**The eight acts settled it.** Both are placed, and neither is a loose end any
more:

| Piece | Was | Now |
|---|---|---|
| The Europa director's cut | feature part 2, then unplaced | **act VII** |
| The Nati teaser | feature part 4, then unplaced | **act V** |

Appearing in the feature never made an appearance somebody's hero video, and it
still does not: act IV is Kat's act *and* Kat's hero video is a separate,
separately-released thing.

**One act has no film.** Act VIII, the credits sequence, is **not designed** —
[issue #51]. Act II was the other gap: its music decision ([issue #74]) is
settled and it is delivered and credited. The numerals are held so nothing
renumbers around act VIII.

## Hero videos: one person, one video, every source

A hero video is **every instance of a bound character across the whole
collection, summed into one cut**. Karena is Mara Sov, so hers is every Mara Sov
shot the index holds — Season of the Lost *and* the Final Shape trailer today,
plus whatever is indexed next.

These are **promotional material for the feature**, released weekly in the
run-up to KubeCon: Kat, mrbobbytables, Cayde/castrojo, and every other cast
member gets one.

**A hero video is never someone's bit of another video.** Appearing in the
feature — or in any other cut — does not make that appearance their hero video.
The same person can have both, and the two are cut by different rules.

Two rules follow directly, and both are load-bearing:

1. **Never pin a hero video to one cinematic.** No `--from-video`. A hero video
   pinned to one source is a trailer re-edit wearing a person's name — that is
   how two Destiny cuts ended up sharing 68% of their footage while four indexed
   trailers went unused ([issue #49]).
2. **The corpus is the shot list and the completeness ledger.**
   `tools/corpus.py <character>` already spans sources and prints `across N
   video(s)`. A hero video is complete *as of an index*, never final — index a
   new cinematic and it becomes re-cuttable.

Full procedure: [`docs/cuts/hero-montage.md`](cuts/hero-montage.md).

## The teaser

The Destiny section of the **original** Wolves video — the oldest one, with the
calls to action — ships first, seven weeks before KubeCon. It is neither a hero
video nor part of the feature file: it is existing material re-released as
promotion. See [`docs/release.md`](release.md).

## Which is which, for the cuts that already exist

Delivered in `~/Videos/Wolves/Prod/` today, classified under this taxonomy.
`NN` is the **act number** from [`running-order.md`](running-order.md):

| File | Kind |
|---|---|
| `03-mrbobbytables` | **act III** of the feature — a monthly contributors reel, partially complete |
| `04-kat` | **act IV** of the feature; Kat's hero video is a separate, separately-released promo |
| `05-nat` | **act V** of the feature — the Nati teaser, no longer unplaced |
| `06-7daystothewolves` | **act VI** — the musical. Editorial pass, not approved; publication blocked on provenance ([issue #55]) |
| `07-europa` | **act VII** — the Europa director's cut, no longer unplaced |

Not acts, and not in the feature — build outputs under `renders/`:

| File | Kind |
|---|---|
| `01-dance-plated` | neither — single-cinematic story cut |
| `02-cayde-6-the-return` | **mis-shaped**: named for a person, cut from one trailer ([issue #49]) |

Two things the older `~/Videos/UPLOAD/` staging folder made easy to get wrong,
and which the act numbering now prevents: a cut appearing twice under two
different numbers, and a lexical filename prefix being mistaken for an ordering
decision. That folder is retired ([issue #81]).

`02-cayde-6-the-return` is the worked example of the error this doc exists to
prevent. It carries Cayde's name but is a single-cinematic cut, and `03-zavala`
built from the same trailer duplicates 68% of it. **A Cayde/castrojo hero video is
every Cayde shot in the index**, which is a different video that has not been
made yet — and today the index holds 1.2 seconds of him.

The monthly contributors reel is a third thing — the whole Curse of Osiris
cinematic, uncut and re-credited each month. It is not a hero video, and it is
regenerated per roster rather than authored; its August 2026 edition is
currently placed as **act III** of the feature, by the owner.

[issue #49]: https://github.com/castrojo/destiny-vids/issues/49
[issue #51]: https://github.com/castrojo/destiny-vids/issues/51
[issue #55]: https://github.com/castrojo/destiny-vids/issues/55
[issue #74]: https://github.com/castrojo/destiny-vids/issues/74
[issue #81]: https://github.com/castrojo/destiny-vids/issues/81
