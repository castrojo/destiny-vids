# Release plan — the road to KubeCon NA

**KubeCon + CloudNativeCon North America 2026: 9–12 November 2026, Salt Lake
City** (Salt Palace Convention Center). Everything below is anchored to the
Monday it opens.

| When | Date | What ships |
|---|---|---|
| **T−7 weeks** | **Mon 21 Sep 2026** | **The teaser** — the Destiny section of the *original* Wolves video, the oldest one, with the calls to action |
| T−6w | Mon 28 Sep 2026 | hero video |
| T−5w | Mon 5 Oct 2026 | hero video |
| T−4w | Mon 12 Oct 2026 | hero video |
| T−3w | Mon 19 Oct 2026 | hero video |
| T−2w | Mon 26 Oct 2026 | hero video |
| T−1w | Mon 2 Nov 2026 | hero video |
| **T−0** | **Mon 9 Nov 2026** | ***Seven Days to the Wolves*** — the feature, as one unit |

Six weekly hero-video slots between the teaser and the feature. That number is
the schedule's output, not a target: fewer cast members with footage means
fewer, longer gaps — never a thinner video.

## The three things being released

1. **The teaser** — existing material, re-released. The Destiny section of the
   original Wolves video with its calls to action. Not a hero video, not part of
   the feature file. **Which file this is has not been identified in this repo**;
   it lives in `~/Videos`, and picking the wrong "oldest one" is a mistake a
   rebuild cannot fix.
2. **The hero videos** — one person, one video, every source. Promotional
   material ([`catalog.md`](catalog.md), [`cuts/hero-montage.md`](cuts/hero-montage.md)).
3. **The feature** — *Seven Days to the Wolves*, one unit: Wolves → Europa →
   **credits** → Nati teaser.

## What blocks this, measured

### The credits sequence does not exist

It is part 3 of the feature, between the main story and the Nati teaser, and it
has **not been designed**. It is the only part of the feature with no artifact
behind it. This is design work, not a render setting, and it is on the critical
path to T−0. Tracked in [issue #51].

### Most of the cast has no footage to make a hero video from

Every lead in `vocab/casting.yaml`, counted across the whole index — clean shots
only, all sources pooled, which is exactly the hero-video pool:

| Character | Cast as | Clean shots | Runtime | Sources | Hero video? |
|---|---|---|---|---|---|
| Osiris | mrbobbytables | 24 | 82.1s | 2 | **yes** |
| Zavala | Kelsey Hightower | 8 | 19.0s | 2 | **yes** |
| The Witness | *uncast* | 3 | 15.5s | 2 | uncast |
| Mara Sov | Karena Angell | 6 | 11.3s | 2 | thin |
| Sagira | Lindsay Gendreau | 3 | 10.1s | 1 | thin |
| Elsie Bray | Laura Santamaria | 3 | 7.8s | 3 | thin |
| Savathûn | *uncast* | 4 | 4.1s | 1 | uncast |
| Ikora Rey | *uncast* | 1 | 2.3s | 1 | uncast |
| **Cayde-6** | **castrojo** | **1** | **1.2s** | 1 | **no** |
| **Saint-14** | **Kat** | **0** | **0.0s** | 0 | **no** |
| Petra Venj, Variks, Saladin, Anna Bray, The Speaker, Amanda Holliday, the red-haired Iron Lord, Crow, Caiatl, Eris Morn, Shaxx, Ghost, the Drifter | various / uncast | 0 | 0.0s | 0 | **no** |

**Two of the three hero videos named so far cannot be built.** Kat has **zero**
indexed shots as Saint-14, and Cayde/castrojo has **one shot, 1.2 seconds** —
too short to hold a readable nameplate, which is why `06-` reports him
`no_window`. Only mrbobbytables (Osiris) has comfortable coverage.

**So the critical path is indexing, not editing** ([issue #50]). Six weekly slots need six
subjects with enough footage; the index currently supports two. The tools are
not the constraint and neither is render time — 232 clean segments across four
fully-indexed trailers already have no outline written against them
([issue #49]), and the characters who need coverage are not in those trailers
either.

Concretely, to fill the slots:

- **Index more sources.** Saint-14 and Cayde-6 have substantial screen time in
  Destiny cinematics this repo has not ingested. That is `tools/ingest.py` +
  `tools/annotate.py`, and it is the highest-leverage work before September.
- **Finish what is half-indexed.** `yt_d2_season_of_the_lost_cutscenes` is 11
  clean of 73 segments — 61 beats unreviewed ([issue #7]). Mara Sov's coverage
  comes mostly from there, so finishing it directly thickens a thin hero video.
- **Re-check the ledger after each pass.** `python3 tools/corpus.py --write`
  regenerates every corpus; the table above is reproducible from it.

### Do not fill a slot by lowering the bar

A slot with no footage behind it is **skipped**, and the reason is recorded. The
alternatives are all worse and all forbidden:

- Widening to unclean footage breaks the primary gate (`AGENTS.md` rule 1).
- Pinning to one cinematic to pad a runtime produces the `06-`/`03-` duplication
  again — 68% shared footage between two cuts.
- Tagging a character into shots they are not visibly in credits a real person
  for a shot they are not in (`AGENTS.md` rule 3), and no schedule outranks
  that.

Ship six hero videos or ship two. **Never ship a thin one to hold a date.**

## Owner decisions this plan does not make

- **Which file is the teaser** — "the oldest one, with the calls to action" is
  unambiguous to the owner and not resolvable from this repo.
- **What the credits sequence is** — who is credited, in what order, over what.
- **Which cast members get the six slots**, and in what order.
- **Rights on any new music** for the credits or the teaser.

[issue #7]: https://github.com/castrojo/destiny-vids/issues/7
[issue #50]: https://github.com/castrojo/destiny-vids/issues/50
[issue #51]: https://github.com/castrojo/destiny-vids/issues/51
[issue #49]: https://github.com/castrojo/destiny-vids/issues/49
