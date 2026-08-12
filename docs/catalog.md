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

It is a **musical**: one song end to end, in three acts, cut to Nightwish's
*7 Days to the Wolves*. The song is the structure — the acts hinge on measured
moments in the bed (the gallop, the flute entry), not on chapter boundaries.

A **timing pass** is rendered and staged for review:
[`cuts/07-seven-days-to-the-wolves.md`](cuts/07-seven-days-to-the-wolves.md).
It is deliberately not a finished cut — spans destined for removal or artwork
are blacked out with marker cards at their exact duration, so the timing can be
judged against the music before anything is actually removed.

### What this replaced, and what is now unplaced

The feature was previously specified as four parts in a running order — the
Wolves video, the Europa director's cut, credits, then the Nati teaser. The
musical supersedes that structure.

Two finished pieces are therefore **unplaced**, and where they go is an open
owner decision rather than a settled fact:

| Piece | Was | Now |
|---|---|---|
| `zz-wolves-europa-directors-cut` | feature part 2 | unplaced |
| `02-wolves-natali-vlatko-behemoth-titan` (the Nati teaser) | feature part 4 | unplaced |

Neither is discarded. Both are finished, owner-approved work; they simply no
longer have a slot inside the feature file. The likely answer is promotional
release alongside the hero videos, but that is a decision, not a default.

**The credits sequence is still undesigned** — [issue #51]. A musical still has
to credit its cast, and the timing pass carries no plates yet — though the
Guardians-together runs it is built around are flagged `plate_slot` for that
pass.

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

Staged in `~/Videos/UPLOAD/` today, classified under this taxonomy:

| File | Kind |
|---|---|
| `01-wolves-kat-cosgrove-sentinel-titan` | hero video (promo) |
| `02-wolves-natali-vlatko-behemoth-titan` | the Nati teaser — **unplaced** since the feature became a musical |
| `zz-wolves-europa-directors-cut` | **unplaced**, same reason |
| `04-bluefin-contributors-…-curse-of-osiris` | neither — a monthly contributors reel |
| `05-destiny-prologue-the-dance` | neither — single-cinematic story cut |
| `06-destiny-cayde-6-the-return` | **mis-shaped**: named for a person, cut from one trailer |
| `07-seven-days-to-the-wolves` | **the feature** — timing pass, not yet approved; delivery blocked on provenance ([issue #60]) |

`07-` is the feature and stands alone: it is one song end to end, so nothing is
assembled around it. The two unplaced files above are finished work waiting on a
decision, not inputs to it.

`06-` is the worked example of the error this doc exists to prevent. It carries
Cayde's name but is a single-cinematic cut, and the unstaged `03-zavala` built
from the same trailer duplicates 68% of it. **A Cayde/castrojo hero video is
every Cayde shot in the index**, which is a different video that has not been
made yet — and today the index holds 1.2 seconds of him.

The monthly contributors reel is a third thing — the whole Curse of Osiris
cinematic, uncut and re-credited each month. It is neither part of the feature
nor a hero video, and it is regenerated per roster rather than authored.

[issue #49]: https://github.com/castrojo/destiny-vids/issues/49
[issue #60]: https://github.com/castrojo/destiny-vids/issues/60
[issue #51]: https://github.com/castrojo/destiny-vids/issues/51
