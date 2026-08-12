# 01 — Cayde-6: The Return

Production notes for [`01-cayde-6-the-return.txt`](01-cayde-6-the-return.txt),
the cut requested in [castrojo/destiny-vids#8](https://github.com/castrojo/destiny-vids/issues/8).

- **Outline:** [`stories/01-cayde-6-the-return.txt`](01-cayde-6-the-return.txt)
- **Corpus:** [`corpus/cayde_6.json`](../corpus/cayde_6.json)
- **Source:** `yt_destiny_2_the_final_shape_launch_trailer`, one cinematic
- **Length:** 24 shots, ~52.9s, 0 unmatched beats, all clean

```bash
# the cut list
python3 tools/story.py stories/01-cayde-6-the-return.txt --dir segments \
    --forward-only --video yt_destiny_2_the_final_shape_launch_trailer
```

## One cinematic, played forward

The cut is a single source video, walked from front to back. Every beat matches
a shot that starts at or after the previous beat's out point; the passages in
between are skipped. That is the whole mechanic — `--video` pins the pool to one
cinematic, `--forward-only` keeps the playhead monotonic, and `story.py` reports
what it passed over:

```
SKIPPED FORWARD — stretches of the cinematic this cut passes over:
           head: 0:00–0:14 (14.248s, 7 segment(s))
   after shot 2: 0:23–0:33 (9.943s, 5 segment(s))
   ...
  after shot 24: 2:11–2:21 (9.977s, 2 segment(s))
```

### Why not a virtual edit

The obvious alternative was to compose several cinematics behind a timeline
object — a cut graph, a sequencer, an edit DSL. It was rejected, and the reason
is not taste:

- **There is nothing to sequence.** The whole index holds *one* Cayde-6 shot,
  in this trailer. A multi-source stitcher would be an abstraction with a single
  input.
- **The existing tools already are the edit.** `story.py` emits an ordered shot
  list and `render.py` concatenates it. A timeline layer would sit between two
  things that already fit, and would need its own serialisation, its own tests,
  and its own answer for the `clean` gate.
- **Skips are derived, so they cannot rot.** Nothing in the repo stores "skip
  0:23–0:33". The skips are computed from the beats that matched, which means
  reordering a beat re-derives the skips for free. An authored timeline would
  have to be kept in sync by hand — exactly the hand-edited-derived-field
  failure the pipeline refuses everywhere else.

The rule to keep: **if you find yourself adding a system to manage multiple
cinematics, back out.** Pin a different `--video` and write a second outline.

### Where the skip points live

Nowhere, deliberately. They are computed in `find_skips()` in `tools/story.py`
from the gaps between matched shots, and printed under `SKIPPED FORWARD`
(`--format json` carries them as `skips[]`). **To move a skip, move a beat.**

## Working on this cut

### Reorder or add a beat

Edit the outline and re-run. Two forward-only-specific consequences:

- Beats must stay in **source order**. A beat that describes footage earlier
  than the previous beat's out point cannot be reached; it is reported as a miss
  rather than doubling back.
- The **first matched beat locks the cinematic** when `--video` is omitted. With
  `--video` the pool is pinned up front, which is what this cut does.

Everything in [`docs/skills/editing.md`](../docs/skills/editing.md) still
applies — especially that domain words are parsed as *filters*. Beat 17 ("a
winged silhouette ... held at distance") is written the long way around for
exactly this reason: the word "witness" would have added a `faction` filter.

### Change which heroes are featured

Heroes are cast in two places, and neither of them is this file:

1. **The beat** picks the shot. Rewrite the beat to describe the shot the hero
   is in — beat 13 is Cayde's reveal, beats 3/8/16/18 are the commander.
2. **`vocab/casting.yaml`** decides whose name appears on it. `plate:` copy on a
   lead binding is what `tools/plate.py plan` puts on screen; a binding with no
   `plate:` block simply gets no plate.

To feature a different hero, find their shots (`python3 tools/corpus.py build
<character>`), write beats for the ones in this trailer in source order, and
give the binding plate copy. Nothing else changes.

## The corpus

`tools/corpus.py` pivots the index (organised by video) into a per-character
catalog (organised by who is in it), one file per character in `corpus/`:

```bash
python3 tools/corpus.py build cayde_6     # writes corpus/cayde_6.json
python3 tools/corpus.py check             # fails if any committed corpus is stale
```

Each file has two halves, and the split is the point:

| Half | Fields | Rule |
|---|---|---|
| **Derived** | `shots`, `coverage`, `cast` | A projection of the segment records. Regenerating overwrites it, so it can never drift from the index. |
| **Authored** | `unresolved` | The gaps. Read back off the existing file and preserved verbatim on every rebuild, because "we do not have this" is knowledge no re-scan can produce. |

A gap must say what is missing, its `status`, whether it is `automatable`, and —
if not — what it is `blocked_on`. `validate_gaps()` enforces that, so a gap can
never degrade into a shrug.

**Extending it.** The amount of Destiny footage is finite, so this accumulates
one character (or one video) at a time: `tools/corpus.py build <character>` for
any lead in `vocab/casting.yaml`, commit the file, and `check` keeps it honest
from then on. When new footage is indexed, rebuild — the derived half updates
and the recorded gaps come along, so a gap that has just been filled is visible
as a gap sitting next to footage that now exists.

## What the issue asked for, and what the footage could carry

`corpus/cayde_6.json` holds the full list under `unresolved`, with a
`blocked_on` on each. The short version:

| Request | Outcome |
|---|---|
| Cayde-6 as Jorge Castro, `MAINTAINER // GUARDIAN` | Plate copy authored in `vocab/casting.yaml`. **Not on screen yet** — his only indexed shot is 1.201s, under `plate.py`'s 1.5s `MIN_ANCHOR`, so `plan` reports `UNPLATED cayde_6`. |
| Kelsey Hightower, `ARCHITECT // GUARDIAN` | On screen at 17.68s. |
| Petra Venj → Lori Lorusso, `HERALD // GUARDIAN`, "rusted out" | Recast in `vocab/casting.yaml`; `variant: rust` added to `plate.py` (oxidised chrome, same geometry, closed field set). She has no shot in this trailer, so the plate lands when a cut uses her footage. |
| Cut 0:44 / resume 0:54 / plates at 1:07, 1:08 / cut at 1:34 / intro 1:52 | **Unresolved.** Those timecodes are in three videos that are not indexed. |
| Katherine Druckman, Kyle Gospodnetich | **Unresolved.** Neither names a Destiny character, so there is nothing to bind. Identifying who is on screen is a claim about a real person. |
| "How's your sister" → "It's not too late Kyle" | **Unresolved.** On-screen copy from unindexed footage; the pipeline cuts picture, it does not author dialogue. |
| Discussion placards | **Unresolved.** No copy supplied, and nameplate fields are a closed set. |
| Two titans in the crowd as Bluefin maintainers | **Unresolved.** The ensemble machinery exists (`tools/ensemble.py`, `plate.py plan --roster`), but the shots are in an unindexed video and no roster was given. |

The class line reads **"Harbringer Hunter"** on both plates because that is what
the issue wrote. On-screen copy is quoted, never corrected; the open question is
recorded as the `class_line_spelling` gap.

## Output targets

One master render serves both destinations. There is no second encoding path,
because a second path is a second thing to keep in sync.

```bash
python3 tools/story.py stories/01-cayde-6-the-return.txt --dir segments \
    --forward-only --video yt_destiny_2_the_final_shape_launch_trailer \
    --format json --out renders/01-cayde-6-the-return.cut.json

python3 tools/render.py renders/01-cayde-6-the-return.cut.json \
    --media media --out renders/01-cayde-6-the-return.raw.mp4 --max-shot-sec 9

python3 tools/plate.py plan renders/01-cayde-6-the-return.cut.json \
    --max-shot-sec 9 --out renders/01-cayde-6-the-return.plates.json
python3 tools/plate.py render --manifest renders/01-cayde-6-the-return.plates.json \
    --out-dir renders/plates
python3 tools/plate.py burn --video renders/01-cayde-6-the-return.raw.mp4 \
    --manifest renders/01-cayde-6-the-return.plates.json \
    --plates-dir renders/plates --out renders/01-cayde-6-the-return.mp4
```

`--max-shot-sec 9` is passed to **both** `render.py` and `plate.py plan`, or
every plate after the first trimmed shot lands late.

- **Website render** — `renders/01-cayde-6-the-return.mp4`, played by the site's
  existing player. The plates are burned in, so the site needs no overlay layer.
- **YouTube export** — the same file, uploaded as-is.

**Sequence order lives in the filename.** The `01-` prefix on the outline and on
every render artifact is the upload position; the next video in the sequence is
`02-…`. Sorting `stories/` or `renders/` by name gives the running order, which
is why the number is a prefix and not a suffix or a side-car field.

`renders/`, `media/`, `keyframes/` and `*.mp4` are gitignored: this repo ships
the recipe, never the footage. Rendering needs the source video in `media/` and
a working H.264 encoder — see [`docs/rendering.md`](../docs/rendering.md), and
note the `ffmpeg-free` trap on atomic Fedora hosts.

## Rights

Bungie footage, used under Bungie's fan-content policy: non-commercial fan work
only. The index stores metadata and timecodes; `usage_class` and
`source_rights_note` travel with the video record.
