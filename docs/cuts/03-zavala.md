# 03 — Zavala

**Sequence position: 03.** The third cut in the ordered upload series — behind
`01-dance` and `02-cayde-6-the-return`, which merged first — so it ships as
`03-zavala` everywhere: outline, cut list, plate manifest, renders.

| Piece | Where |
|---|---|
| Outline | [`stories/03-zavala.txt`](../../stories/03-zavala.txt) |
| Source cinematic | `yt_destiny_2_the_final_shape_launch_trailer` ([`videos/`](../../videos)) |
| Footage corpus | [`corpus/zavala.json`](../../corpus/zavala.json) |
| Nameplate | gold, `vocab/casting.yaml` → `leads.values.zavala.plate` |

Origin: [issue #33](https://github.com/castrojo/destiny-vids/issues/33) — make
Zavala's nameplate golden, hold the reveal until 1:50, no music, "just
cleanup".

## What this cut is, and what it is not

Zavala is **19.02 seconds of footage in the entire index**: eight clean shots,
six of them in this cinematic and two in the Lightfall launch trailer. The
corpus says what kind of seconds they are — every one is `MCU`, `MS` or `CU`,
and every one is `idle` or `dialogue`. There is no shot of him fighting, using
an ability, traversing, or held wide. He is a face in a war, not a body in one.

So the cut is built the way the footage allows: **the anonymous Guardians carry
the action and Zavala carries the drama**, cutting between the two. That is the
hero framing the direction asks for, not a compromise around it — the man gives
the order, the line holds, and the camera comes back to him for what it cost.

| Movement | Resumes at | The beat |
|---|---|---|
| 1 — WHAT IT COSTS | 0:14 | The threat implied and never shown, then a dead Ghost's shell. |
| 2 — THE COMMANDER | 0:32 | Boots on rock, then Zavala kneeling on the ridge. |
| 3 — THE ROOM HE COMMANDS | 0:39 | The people the order is given to, then the cockpit push-in. |
| 4 — THE LINE HOLDS | 0:55 | The fighting, the field after it, and him at the horizon. |
| 5 — THE GHOST OF A SMILE | 1:14 | The funeral, the antagonist wide and brief, the payoff. |

It is a hero cut. The one antagonist shot (the Witness, 1:23–1:25) is a 2.3s
long shot held at distance with the face never given, per the standing
editorial direction: wide, brief, never close-up. There is no per-enemy camera
logic anywhere in this cut, by design.

**No beat was widened to unclean footage and no shot was invented.** 25 beats,
25 shots, zero misses; ~59s of picture. What could not be reached — including
the 1:50 reveal — is recorded below and in the corpus, not worked around.

**This cut and `02-cayde-6-the-return` are substantially the same footage.**
Both are one-cinematic skip-forward cuts of
`yt_destiny_2_the_final_shape_launch_trailer` with overlapping beats; this
cut's payoff shot (~1:25, the smile breaking through) is the Cayde cut's
closing shot, and the Cayde cut already plates Zavala-as-Kelsey at 17.68s. This
outline was written before `02-cayde-6-the-return` merged, which is why the
overlap is recorded here rather than designed around. Whether two consecutive
uploads cut from the same trailer is wanted is the owner's call, not this
doc's.

## Architecture: one cinematic, skipped forward

The whole cut is **one cinematic advanced by skipping forward**. Two flags on
`tools/story.py` enforce it:

```bash
python3 tools/story.py stories/03-zavala.txt --dir segments \
    --from-video yt_destiny_2_the_final_shape_launch_trailer --forward-only
```

- `--from-video` restricts the candidate pool to one source. Every shot in the
  finished cut comes from that cinematic; nothing can drift in from another.
- `--forward-only` keeps a playhead on the source timeline. Each beat may only
  take a shot starting at or after the previous shot's out-point, so the cut
  never runs its source backwards. The distance jumped is reported per shot as
  `skip_sec`, and printed as `[skip +Xs]`.

That is the entire mechanism. **The beat order *is* the timeline** and the skip
points are simply the gaps between chosen shots. It is the same shape as
[`01-dance`](01-dance.md) — see that doc's *Why not a virtual edit* table for
the alternative that was rejected and why. Nothing here needed a second
cinematic, a sequencer, or a cut-graph, and if a future beat seems to, the
answer is a different source cinematic and a different cut, not a timeline
layer.

The Lightfall launch trailer holds Zavala's other two clean shots. They are
**not** in this cut and must not be spliced in: one cinematic per cut is the
whole constraint, and mixing two sources in one skip-forward playhead is
exactly the virtual edit this repo refuses. If those two shots are wanted,
they are a cut of their own, cut from that source.

### Where the skip-forward points live

In [`stories/03-zavala.txt`](../../stories/03-zavala.txt), nowhere else. Each
`# --- MOVEMENT n ---` header names the source timecode its movement resumes
at, and every gap between beats is a skip. To see the jumps the assembler
actually took, read the `[skip +Xs]` annotation in `story.py`'s text output or
the `skip_sec` field in the JSON cut list.

## Working on the cut

### Add or reorder a hero beat

1. Find the shot in the corpus first — `python3 tools/corpus.py zavala --dir
   segments` — and read its timecode. If nothing covers the beat, the beat is
   the thing that changes.
2. Insert the beat line into `stories/03-zavala.txt` **in source-time order**,
   under the movement it belongs to. Describe the picture; the matcher scores
   caption overlap.
3. Re-run the command above. Zero misses and 25 (or n) shots means it landed.
4. Naming `zavala` in a beat is what pins it to his footage — `tools/search.py`
   turns the name into a hard filter on `casting.character` and adds the lead
   bonus, so his beats match his shots rather than shots that merely look like
   them.

**Enum-like words are filters, not prose** ([`editing.md`](../skills/editing/SKILL.md)),
and this outline paid for that lesson three times. `ghost` filters on
`casting.character`, `fighting` on `action: combat`, and `pale` on
`destination: the_pale_heart` — each one silently emptied the candidate pool
for a beat whose caption otherwise matched word for word. Under
`--forward-only` the damage does not stay local: the beat matches something
later and worse, the playhead jumps with it, and every beat after it starves.
When a beat that should be obvious misses, check its words for enums before
rewriting the picture.

### Change which heroes get featured

Zavala is the subject because the issue asks for him; the rest of the cut is
anonymous Guardians, who are the ensemble tier. To feature another lead, name
them in a beat and check the footage exists first:

```bash
python3 tools/corpus.py <lead> --dir segments
```

`tools/plate.py plan` then plates them automatically from their `plate:` copy
in `vocab/casting.yaml`. Casting names real people; if the corpus is empty, the
answer is that the footage does not exist, not that the beat should guess.

### Nameplates

Zavala's plate is **gold** — `variant: leader` on his binding in
`vocab/casting.yaml`, the same treatment Osiris and Mara Sov carry, and the
answer to the first half of the issue.

It carries the **full authored copy**: `label: ARCHITECT // GUARDIAN`,
`class: Dawnblade Warlock`, `name: Kelsey Hightower`, `title: Evangelist of the
Open Sky` — written by the owner in [issue #8](https://github.com/castrojo/destiny-vids/issues/8),
which *is* the authorisation. Kelsey has no entry in the reference deck
(`~/Videos/nameplates.json`), but the deck is not the only authority: the owner
authored this identity in the issue, so the four rows are reproduced verbatim
and the gold chrome goes **on top of** them, not instead of them. The subclass
line names the role the project casts — the same construction Osiris's binding
carries — it is not a lore claim read back off the Titan on screen.

```bash
python3 tools/story.py stories/03-zavala.txt --dir segments \
    --from-video yt_destiny_2_the_final_shape_launch_trailer --forward-only \
    --format json --out cut.json
python3 tools/plate.py plan cut.json --max-shot-sec 9 --reveal-after 1:50 \
    --out plates.json
```

Pass `plan` the same `--max-shot-sec` the render gets, or every plate after the
first trimmed shot lands late.

## The 1:50 reveal

`--reveal-after` is the second half of the issue, and it is new in this cut:
a floor on the **finished cut's** clock, below which no derived lead reveal may
land. It is deliberately not a brief's `plates[].at`, which pins one credit to
one moment in *source* time; this holds every derived reveal until a point on
the video the owner is actually watching.

The footage cannot reach 1:50, and the tool says so rather than pretending:

```text
zavala      48.35s +5.0s  Kelsey Hightower (latest appearance)
  REVEAL     zavala     the cut has no appearance at or after 110.00s; revealed
                        at 48.35s instead -- reported, not moved onto another shot
  UNPLATED   the_witness uncast: no person is bound to this character in vocab/casting.yaml
```

(The second line is the antagonist beat. Nobody is bound to `the_witness` in
`vocab/casting.yaml`, so the shot goes unplated and is reported — which is the
correct outcome for a hero cut, and the tool's, not a decision made here.)

The arithmetic, which is checkable from the index:

| | |
|---|---|
| Requested | 1:50 (110.0s) |
| Delivered | 0:48.35, on his last appearance — the smile, riding into the closing walk |
| Every clean shot in this cinematic, cut end to end | 1:53.8 |
| Zavala's last clean shot on that maximal cut | starts 1:07.8, so the latest anchor any cut from this source can offer is **1:08.2** |
| Same figure for the Lightfall launch trailer | maximal cut 1:33.5, his last shot at 0:17.9 |

So no cut this index can build puts Zavala on screen at 1:50. Holding the plate
to 110s anyway would mean laying his name — and Kelsey Hightower's — over a
shot he is not in, and a timing request does not outrank a false credit. The
reveal therefore degrades to the closest the footage comes to the moment asked
for (his *latest* appearance, not his first), and the shortfall is written into
the manifest's `unresolved` with `automatable: false`.

Three things would resolve it, all of them the owner's to choose: accept the
earlier reveal, index a longer source that keeps him on screen past 1:50, or
tell us that 1:50 was a timecode in the reference video rather than in ours.

## Output targets

Two deliveries, one cut list. They differ by filename — not by pipeline, and
**not** by a second edit.

```bash
# 1. cut list (shared by both)
python3 tools/story.py stories/03-zavala.txt --dir segments \
    --from-video yt_destiny_2_the_final_shape_launch_trailer --forward-only \
    --format json --out cut.json

# 2. website render — source audio, embedded in the site's video player
python3 tools/render.py cut.json --media media --out renders/03-zavala-web.mp4 \
    --max-shot-sec 9

# 3. YouTube export — the same picture and the same audio: the issue asks for
#    no music, so there is no --audio bed on this one
python3 tools/render.py cut.json --media media \
    --out renders/03-zavala-youtube.mp4 --max-shot-sec 9

# 4. the gold nameplate, burned into whichever output needs it
python3 tools/plate.py burn --video renders/03-zavala-youtube.mp4 \
    --manifest plates.json --out renders/03-zavala-youtube-plated.mp4
```

`01-dance` differs from its YouTube export by a music bed; this one does not,
because the issue says so. The two outputs still stay separate files: they are
different deliveries with different lifetimes, and collapsing them would mean
re-rendering the site's copy the first time a bed *is* wanted.

**Sequence order lives in the filename prefix.** `03-` is the upload position,
after `01-dance` and `02-cayde-6-the-return`; the next cut is
`stories/04-<name>.txt` → `renders/04-<name>-*.mp4`. Sorting the directory
sorts the playlist. There is
no manifest and no ordering table to keep in sync — the prefix is the whole
convention, and it survives files being copied out of the repo, which a
manifest would not.

`renders/`, `media/` and `*.mp4` are gitignored. The index references footage
by `video_id` and timecode and ships none of it; both outputs are
non-commercial fan work under Bungie's fan-content policy, and every source
video record carries its `usage_class` and `source_rights_note`.

## The footage corpus

[`corpus/zavala.json`](../../corpus/zavala.json) is the catalog this outline was
written against: every indexed shot cast to Zavala, with its tags, its `clean`
status, and — the reason it exists — the coverage that is **missing**. It is the
second subject corpus after `corpus/ensemble.json`, and the pattern is meant to
keep going, one character or story at a time, until the fixed amount of Destiny
footage this project cares about is indexed:

```bash
python3 tools/corpus.py <lead>  --dir segments --out corpus/<lead>.json
python3 tools/corpus.py --write   # rebuild every committed corpus
python3 tools/corpus.py --check   # CI gate: fail if any is stale
```

Adding the next character is that one command plus the file it writes; see
[`docs/skills/corpus.md`](../skills/corpus.md). A corpus is derived and
regenerable — do not hand-edit it, for the same reason nobody hand-edits
`clean`.

### Unresolved for this cut

From the corpus (`gaps`), Zavala has **no clean coverage** of:

| Gap | Consequence here |
|---|---|
| `action: combat`, `ability_cast`, `traversal`, `ritual`, `vehicle`, `emote` | No beat can show him fight, throw a Super, move, or take part in the funeral he is standing near. The action beats are all anonymous Guardians for this reason. |
| `shot_scale: ELS`, `LS`, `MLS` | No wide of him. He cannot be the small figure in a big frame, which is the shape most of this cinematic's awe shots take. |
| `shot_scale: ECU`, `INSERT` | No eyes-only close-up and no cutaway detail — no hands, no shield, no insert to cut to. |

These are recorded, not worked around. If someone later indexes a clean wide or
a combat shot of Zavala, the corpus stops reporting the gap and this cut can be
rewritten toward the footage it always wanted — including, if the shot lands
late enough in its source, toward the 1:50 reveal.

### Not automatable

Marked `automatable: no` with the reason, per `AGENTS.md` — these are judgment
calls, not missing code:

| Item | `blocked_on` |
|---|---|
| What `https://www.youtube.com/watch?v=xI5poBxV_-A` shows, and what its 1:50 is | Requires watching third-party footage that is not indexed here and is not reachable offline. Nothing about it was assumed. |
| The 1:50 reveal itself | No cut this index can build shows Zavala at 1:50 (arithmetic above). Accepting the earlier reveal, indexing more footage of him, or re-pointing the timecode are all owner decisions. |
| Producing the actual `.mp4` | Source media is never committed (`media/`, `renders/`, `*.mp4` are gitignored), so no render can be produced from a clean checkout. The commands above are the reproduction. |

### The `brief` block this cut was built from

Issue #33 is prose, and prose is not executable. This is the block
[`tools/brief.py`](../../tools/brief.py) would propose for it — **a proposal**,
not a confirmation: it goes in the issue only if the owner says it reads right,
which is the point of the division ([`issues.md`](../skills/issues.md)).

````markdown
```brief
title: Zavala / Kelsey Hightower
sources:
  - url: https://www.youtube.com/watch?v=xI5poBxV_-A
    note: the owner's reference cut; not in the index and not reachable offline
  - video_id: yt_destiny_2_the_final_shape_launch_trailer
    note: six of Zavala's eight clean shots in the whole index are here
characters: [zavala]
plates:
  - character: zavala
    note: golden nameplate; do not reveal until 1:50
music:
  note: none -- "no music, etc, just cleanup"
automatable: partly
blocked_on: >-
  which clock 1:50 is on. No shot of Zavala exists that late in any cut this
  index can build, and the reference video that would say what 1:50 shows is
  not indexed.
```
````
