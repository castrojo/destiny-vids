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
released as a single piece at KubeCon NA, and it runs:

| Order | Part | Status |
|---|---|---|
| 1 | The Wolves video | exists |
| 2 | The Europa video | exists as the director's cut |
| 3 | **Credits** | **not designed yet — open work** |
| 4 | The Nati teaser | exists; plays after the credits |

**Treat all four as one unit from here on.** They are not four videos to be
ordered in a playlist; they are the running order *inside* one file. Anything
that reasons about them separately — a playlist position, a per-part checksum
row, a "which chapter goes first" decision — is reasoning about the wrong
object.

**The credits sequence is the one undesigned part**, and it sits between the
main story and the Nati teaser. It is a real design task, not a render setting —
[issue #51].

**The Nati teaser is not a hero video.** It is part of the feature, playing after
the credits. Appearing in the feature does not make a person's appearance their
hero video, and a hero video is never "their bit of the feature". The same
person can have both, and they are cut by different rules.

The comm-line design that assembles the feature from one authored file is
[`docs/plans/wolves/design.md`](plans/wolves/design.md) (issue #9).

## Hero videos: one person, one video, every source

A hero video is **every instance of a bound character across the whole
collection, summed into one cut**. Karena is Mara Sov, so hers is every Mara Sov
shot the index holds — Season of the Lost *and* the Final Shape trailer today,
plus whatever is indexed next.

These are **promotional material for the feature**, released weekly in the
run-up to KubeCon: Kat, mrbobbytables, Cayde/castrojo, and every other cast
member gets one.

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
| `02-wolves-natali-vlatko-behemoth-titan` | **feature part 4** — the Nati teaser |
| `zz-wolves-europa-directors-cut` | **feature part 2** |
| `04-bluefin-contributors-…-curse-of-osiris` | neither — a monthly contributors reel |
| `05-destiny-prologue-the-dance` | neither — single-cinematic story cut |
| `06-destiny-cayde-6-the-return` | **mis-shaped**: named for a person, cut from one trailer |

Because the feature is one unit, the parts that belong to it **stop being
independent uploads** once it is assembled. The staged files above are inputs to
that assembly, not the release.

`06-` is the worked example of the error this doc exists to prevent. It carries
Cayde's name but is a single-cinematic cut, and the unstaged `03-zavala` built
from the same trailer duplicates 68% of it. **A Cayde/castrojo hero video is
every Cayde shot in the index**, which is a different video that has not been
made yet — and today the index holds 1.2 seconds of him.

The monthly contributors reel is a third thing — the whole Curse of Osiris
cinematic, uncut and re-credited each month. It is neither part of the feature
nor a hero video, and it is regenerated per roster rather than authored.

[issue #49]: https://github.com/castrojo/destiny-vids/issues/49
[issue #51]: https://github.com/castrojo/destiny-vids/issues/51
