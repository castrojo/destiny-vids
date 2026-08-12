# The hero video — one person, one video, every source

**This is one of the two things this project produces**
([`docs/catalog.md`](../catalog.md)): a **hero video** is promotional material
for the feature, *Seven Days to the Wolves*. A lead is bound to a real person,
and their hero video is **every clean shot of that character in the entire
index**, from every cinematic, cut into one piece. Karena's video is every
instance of Mara Sov across the Destiny cinematics — not the Mara Sov shots that
happen to sit in one trailer.

**A feature act is not a hero video.** The Natali cameo is a post-credits scene
belonging to the feature; being in the feature does not make that appearance
somebody's hero video. The same person can have both, and they are cut
differently.

Contrast the two *cut shapes*, and note which is the exception:

| | Hero video | Single-cinematic cut |
|---|---|---|
| Pool | **the whole index** | one `video_id` |
| Ordering authority | the outline | the source's own timeline |
| Flags | **none** | `--from-video` + `--forward-only` |
| Answers | "who is this person?" | "what happens in this trailer?" |
| Grows when… | any new cinematic is indexed | never — the source is fixed |
| Worked example | this doc | [`01-dance`](01-dance.md), [`03-zavala`](03-zavala.md) |

The hero video is the default and needs no flags. The single-cinematic cut is
right only when a cut is *retelling one trailer's own story*, and reaching for
it by habit is a known failure: three consecutive Destiny chapters were all cut
from `yt_destiny_2_the_final_shape_launch_trailer`, and two of them shared
**35.9 seconds — 68% of one cut's runtime** ([issue #49]). Four fully-indexed
trailers had no outline written against them at all.

## Build one

**Step 1 — read the corpus. It is the hero video's shot list.** `tools/corpus.py`
already spans every source; that is the whole point of it.

```bash
python3 tools/corpus.py mara_sov --dir segments
```

```text
CORPUS: mara_sov
6/6 clean shot(s), 11.304s across 2 video(s)

  0:03–0:05 (1.933s, MLS, idle)   seg_yt_d2_season_of_the_lost_cutscenes_0003-0005
  0:05–0:07 (1.567s, ECU, idle)   seg_yt_d2_season_of_the_lost_cutscenes_0005-0006
  0:07–0:08 (1.467s, MS, ritual)  seg_yt_d2_season_of_the_lost_cutscenes_0006-0008
  0:18–0:21 (3.067s, CU, idle)    seg_yt_d2_season_of_the_lost_cutscenes_0017-0020
  0:27–0:30 (2.636s, MCU, dialogue) seg_yt_destiny_2_the_final_shape_launch_trailer_0027-0029
  1:54–1:54 (0.634s, MS, combat)  seg_yt_destiny_2_the_final_shape_launch_trailer_0113-0114
```

**`across 2 video(s)` is the line that matters.** Two sources, and a
`--from-video` cut would have thrown away whichever one it did not pick — four
shots or two, either way most of her.

The corpus also prints what she has **no clean coverage of**
(`ability_cast`, `traversal`, `emote`, `vehicle`, `ELS`, `LS`, `INSERT` for Mara
Sov). Those are not beats to write around; they are beats that cannot exist.

**Step 2 — write the outline against the shots that exist**, one beat per shot,
describing the picture. `stories/<character>.txt`.

**Step 3 — assemble with no source flag.** This is the entire difference:

```bash
python3 tools/story.py stories/mara-sov.txt --dir segments \
    --format json --out renders/mara-sov-cut.json
```

The pool is every clean segment in the index. Shots from different cinematics
sit next to each other, and `story.py` reports the `video_id` per shot so the
cut list stays honest about where each frame came from.

**Step 4 — render and plate as usual** ([`editing.md`](../skills/editing.md),
[`plates.md`](../skills/plates.md)). Nothing downstream changes: `render.py`
already resolves each shot's own `video_id` against `media/`, so a cross-source
cut list needs no special handling.

## Why there is no playhead

`--forward-only` is **refused** without `--from-video`, and `story.py` raises
rather than guessing. A playhead is seconds on **one** cinematic's timeline;
compared across sources it would silently exclude shots and report skips
measured between unrelated clocks.

A hero video therefore has no source-time ordering at all — **the outline is the
only ordering authority**. That is a feature: a hero video is ordered by what it
says about the person (arrival, command, cost, payoff), not by which trailer
Bungie shipped first.

The consequence for authoring: under `--forward-only` a bad early pick strands
every later beat behind the playhead, and here it cannot. A mismatch still
cascades through *distinctness* — a shot taken by beat 3 is unavailable to beat
9 — but no beat is ever unreachable.

## What this does not change

- **`clean` is still the primary gate.** Spanning sources widens the pool; it
  never lowers the bar. A hero video may not reach for unclean footage to fill a
  beat, and rule 1 of `AGENTS.md` is untouched.
- **The fiction still bends to the footage.** More sources means more shots, not
  permission to invent one. Unmatched beats are still reported, never dropped.
- **Casting still names real people.** A character's pool is exactly the shots
  tagged with that `casting.character`. A wrong tag now propagates into a hero
  video *about that person*, so it matters more here, not less.
- **Rights are unchanged** — index metadata, ship no footage, non-commercial.

## The corpus is the coverage ledger

Because a hero video is defined as "all of them", **the corpus is how you know
whether the video is finished**. `corpus/<character>.json` is committed and
regenerated, never hand-edited:

```bash
python3 tools/corpus.py <character> --dir segments --out corpus/<character>.json
python3 tools/corpus.py --write    # rebuild every committed corpus
python3 tools/corpus.py --check    # CI gate: fail if any is stale
```

Index a new cinematic and a lead's corpus grows on its own — which means **hero
videos are re-cuttable, not final**. A hero video is complete as of the index it
was cut from, and the corpus is what says so.

[issue #49]: https://github.com/castrojo/destiny-vids/issues/49
