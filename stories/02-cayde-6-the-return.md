# 02 — Cayde-6: The Return

Production notes for [`02-cayde-6-the-return.txt`](02-cayde-6-the-return.txt),
the cut requested in [castrojo/destiny-vids#8](https://github.com/castrojo/destiny-vids/issues/8).

- **Outline:** [`stories/02-cayde-6-the-return.txt`](02-cayde-6-the-return.txt)
- **Corpus:** [`corpus/cayde_6.json`](../corpus/cayde_6.json)
- **Source:** `yt_destiny_2_the_final_shape_launch_trailer`, one cinematic
- **Length:** 24 shots, ~52.9s, 0 unmatched beats, all clean

```bash
# the cut list
python3 tools/story.py stories/02-cayde-6-the-return.txt --dir segments \
    --forward-only --from-video yt_destiny_2_the_final_shape_launch_trailer
```

## One cinematic, played forward

The cut is a single source video, walked from front to back. Every beat matches
a shot that starts at or after the previous beat's out point; the passages in
between are skipped. That is the whole mechanic — `--from-video` pins the pool
to one cinematic, `--forward-only` keeps the playhead monotonic, and `story.py`
reports the jump each beat made as `skip_sec`:

```
  1. two distant lights burning through heavy red fog
     yt_destiny_2_the_final_shape_launch_trailer  0:14–0:15  (1.16783s, cinematic, —)  [skip +14.248s]
  3. a commander kneeling on a windswept ridge, shield on his back
     yt_destiny_2_the_final_shape_launch_trailer  0:33–0:34  (1.23457s, cinematic, zavala)  [skip +9.943s]
  ...
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
  0:23–0:33". Each skip is computed from the beats that matched, which means
  reordering a beat re-derives the skips for free. An authored timeline would
  have to be kept in sync by hand — exactly the hand-edited-derived-field
  failure the pipeline refuses everywhere else.

The rule to keep: **if you find yourself adding a system to manage multiple
cinematics, back out.** Pin a different `--from-video` and write a second
outline.

### Where the skip points live

Nowhere, deliberately. Each one is the distance between a matched shot's
in-point and the playhead, reported per shot as `skip_sec` (`[skip +Xs]` in the
text output, `skip_sec` in `--format json`). **To move a skip, move a beat.**

## Working on this cut

### Reorder or add a beat

Edit the outline and re-run. Two forward-only-specific consequences:

- Beats must stay in **source order**. A beat that describes footage earlier
  than the previous beat's out point cannot be reached; it is reported as a miss
  rather than doubling back.
- `--forward-only` requires `--from-video`: the playhead is seconds on ONE
  cinematic's timeline, and the tool refuses the flag alone rather than compare
  seconds across unrelated sources.

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
   `plate:` block is reported under `unresolved` (`no_plate_copy`) rather than
   dropped.

To feature a different hero, find their shots (`python3 tools/corpus.py
<character>`), write beats for the ones in this trailer in source order, and
give the binding plate copy. Nothing else changes.

## The corpus

`tools/corpus.py` pivots the index (organised by video) into a per-subject
catalog (organised by who is in it), one file per subject in `corpus/`:

```bash
python3 tools/corpus.py cayde_6 --out corpus/cayde_6.json   # the catalog
python3 tools/corpus.py --check                             # committed corpora are fresh
```

The corpus is **derived, never hand-edited**: every field is copied or counted
from `segments/`, and `--check` rebuilds every committed file and fails on
drift. Unclean shots stay in the catalog labelled `blocked_by`, because knowing
the footage exists and why it cannot be cut is what stops the next person
re-finding it. The `gaps` list is derived the same way — the vocabulary values
this subject has no *clean* coverage of — so it can never shrink to flatter the
cut or grow to invent footage.

What a corpus deliberately does NOT hold is the editorial punch-list — the
requests no footage can carry and the calls only a human can make. Those are
authored, and they live in the next section of this document, where a rebuild
cannot overwrite them.

## What the issue asked for, and what the footage could carry

Every request in #8 lands in one of three places: on screen in this cut, in
`vocab/casting.yaml` as authored copy, or here as a recorded gap. A gap is
**recorded, never guessed**: each one says whether it is `automatable` and, if
not, what it is `blocked_on`. None of these block the cut — they are the
punch-list the next session works from.

| Request | Outcome |
|---|---|
| Cayde-6 as Jorge Castro, plate on the reveal | Plate copy on the `cayde_6` binding, reproduced **verbatim from the reference deck** (`np_jorge`: `TRUSTEE // GUARDIAN` / Harbinger Titan / Jorge Castro / Upender of Antipatterns \| The First Disciple, `trustee: true` — the burnished-silver chrome). **Not on screen yet** — his only indexed shot is 1.201s, under `plate.py`'s 1.5s `MIN_ANCHOR`, so `plan` reports him in `unresolved` (`no_window`). Do not lower `MIN_ANCHOR` to force it; the plate lands by itself once a longer Cayde shot is indexed. |
| Kelsey Hightower, `ARCHITECT // GUARDIAN` | Plate copy authored in #8, on the `zavala` binding. **On screen at 17.68s** (+5.0s) in this cut. |
| Petra Venj → Lori Lorusso, `HERALD // GUARDIAN`, "rusted out" | Recast in `vocab/casting.yaml`; `variant: rust` added to `tools/plate.py` (oxidised iron chrome, same geometry, same closed field set). She has no shot in this trailer, so the plate lands when a cut uses her footage. |
| Cut 0:44 / resume 0:54 / plates at 1:07, 1:08 / cut at 1:34 / intro 1:52 | **Unresolved.** Those timecodes address three sources the index does not have (`youtu.be/ZJLAJVmggt0`, `youtu.be/0MDrj33Aqqw`, `youtu.be/rQ4i0AT8c-M`), so none of the per-timecode instructions can be resolved against `segments/` today. `automatable: no` — `blocked_on: footage`: shot detection and tagging need the video files, which this repo never stores. Ingest and tag them, then rerun `tools/corpus.py cayde_6 --out corpus/cayde_6.json`. |
| Cayde's coverage | **Unresolved.** The whole index holds a single Cayde-6 shot (1.201s, this trailer at 1:07–1:08). The cut casts him as the reveal and gives the surrounding beats to the footage that exists, rather than inventing Cayde coverage. `blocked_on: footage` — no other indexed source contains him. |
| Katherine Druckman, `CONDUIT // GUARDIAN` | **Unresolved.** The copy names no Destiny character, so there is nothing to bind in `vocab/casting.yaml`, and the issue points at a shot in an unindexed video ("1:52 intro ... do the character on the left"). `blocked_on: human` — identifying who is on screen is a visual judgement about a real person's credit. |
| Kyle Gospodnetich, `MAINTAINER // TRAINEE` | **Unresolved.** Likewise names no character, and the issue asks to "check the bazzite.gg spelling" of the name. `blocked_on: human` — naming a real person on screen, and confirming how he spells his name. |
| "How's your sister" → "It's not too late Kyle" | **Unresolved.** Rewrites spoken/on-screen copy in an unindexed video; the original line can only be recovered from the footage, and the pipeline cuts picture — it does not author dialogue. `blocked_on: footage`. |
| Discussion placards | **Unresolved.** "Put plaques up for the conversation" supplies no copy, and nameplate fields are a closed set (`docs/skills/plates.md`). Nothing is invented to fill them. `blocked_on: input` — the placard copy has to be written by a human. |
| Two titans in the crowd as Bluefin maintainers | **Unresolved.** The machinery exists (group shots derive `casting.slots`; `tools/ensemble.py` + `plate.py plan --roster` credit them), but the shots live in an unindexed video and no maintainer list was supplied. `blocked_on: input` — a roster, plus the footage above. |
| **Lenka, displaced by the Petra recast** | **Unresolved.** The recast in #8 moves Petra Venj to Lori Lorusso and does not say where Lenka goes; she is no longer credited anywhere. `automatable: no` — `blocked_on: human`: a casting decision about a real person. Recorded here and beside the `petra_venj` binding; an agent does not resolve it. |

The `class` line on Lori's plate reads **"Harbringer Hunter"** because that is
what the issue wrote. On-screen copy is quoted, never corrected; the open
question is recorded as a `TODO(owner)` beside the binding. (Jorge's plate is a
different case: his identity is authored in the reference deck, so the deck
wins — `Harbinger Titan` — and the issue's "(change my class)" is satisfied by
it. An authored identity reproduced verbatim is the rule; the generic fallback
would be as wrong as an invented one.)

## Output targets

One master render serves both destinations. There is no second encoding path,
because a second path is a second thing to keep in sync.

```bash
python3 tools/story.py stories/02-cayde-6-the-return.txt --dir segments \
    --forward-only --from-video yt_destiny_2_the_final_shape_launch_trailer \
    --format json --out renders/02-cayde-6-the-return.cut.json

python3 tools/render.py renders/02-cayde-6-the-return.cut.json \
    --media media --out renders/02-cayde-6-the-return.raw.mp4 --max-shot-sec 9

python3 tools/plate.py plan renders/02-cayde-6-the-return.cut.json \
    --max-shot-sec 9 --out renders/02-cayde-6-the-return.plates.json
python3 tools/plate.py render --manifest renders/02-cayde-6-the-return.plates.json \
    --out-dir renders/plates
python3 tools/plate.py burn --video renders/02-cayde-6-the-return.raw.mp4 \
    --manifest renders/02-cayde-6-the-return.plates.json \
    --plates-dir renders/plates --out renders/02-cayde-6-the-return.mp4
```

`--max-shot-sec 9` is passed to **both** `render.py` and `plate.py plan`, or
every plate after the first trimmed shot lands late.

- **Website render** — `renders/02-cayde-6-the-return.mp4`, played by the site's
  existing player. The plates are burned in, so the site needs no overlay layer.
- **YouTube export** — the same file, uploaded as-is.

**Sequence order lives in the filename.** The `02-` prefix on the outline and on
every render artifact is the upload position; the previous cut in the sequence
is `01-dance`. Sorting `stories/` or `renders/` by name gives the running
order, which is why the number is a prefix and not a suffix or a side-car
field.

`renders/`, `media/`, `keyframes/` and `*.mp4` are gitignored: this repo ships
the recipe, never the footage. Rendering needs the source video in `media/` and
a working H.264 encoder — see [`docs/rendering.md`](../docs/rendering.md), and
note the `ffmpeg-free` trap on atomic Fedora hosts.

## Rights

Bungie footage, used under Bungie's fan-content policy: non-commercial fan work
only. The index stores metadata and timecodes; `usage_class` and
`source_rights_note` travel with the video record.
