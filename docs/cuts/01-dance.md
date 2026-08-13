# 01 — Dance

**Sequence position: 01.** The first cut in the ordered upload series, so it
ships as `01-dance` everywhere: outline, cut list, plate manifest, renders.

| Piece | Where |
|---|---|
| Outline | [`stories/01-dance.txt`](../../stories/01-dance.txt) |
| Source cinematic | `yt_destiny_2_the_final_shape_launch_trailer` ([`videos/`](../../videos)) |
| Footage corpus | [`corpus/ensemble.json`](../../corpus/ensemble.json) |
| Nameplates | placeholder blueberries, `vocab/casting.yaml` → `ensemble.placeholder_plate` |

Origin: [issue #4](https://github.com/castrojo/destiny-vids/issues/4) — a dance
video, a music bed, a sound-effect hit while the first Guardian is alone, and
placeholder blueberry nameplates.

## What this cut is, and what it is not

The brief asks for dancing. **The index has no dance footage.** `action: emote`
appears on exactly one shot in the entire index — an Eliksni busker at 0:04 of
the Final Shape launch trailer — and that shot is unclean (`burned_text`), so
the clean gate bars it. There is no clean shot of a Guardian dancing, and there
is no Tower or social-space footage at all.

So the fiction bent to the footage, per `AGENTS.md`. The cut is *staged* as a
dance without ever depicting one, in four movements:

| Movement | Resumes at | The beat |
|---|---|---|
| 1 — ALONE | 0:32 | One Guardian by themselves. The SFX hit lands here. |
| 2 — THEY GATHER | 0:39 | Others are already in the room; the floor fills. |
| 3 — THE FLOOR MOVES | 0:55 | Light goes up, the crowd moves as one. |
| 4 — THE DROP | 1:23 | Everything opens out: supers, embers, prismatic light. |

Nothing in the outline claims anyone is dancing. The music and the cut rhythm
carry that; the footage carries Guardians being Guardians. **No beat was widened
to unclean footage and no shot was invented** — the coverage that would have
been needed and does not exist is recorded as `unresolved` (below, and in the
corpus), not papered over.

It is a hero cut. The one antagonist shot (the Witness, 1:23–1:25) is a 2.3s
long shot held at distance with the face never given, per the standing
editorial direction: wide, brief, never close-up. There is no per-enemy camera
logic anywhere in this cut, by design.

## Architecture: one cinematic, skipped forward

The whole cut is **one cinematic advanced by skipping forward**. Two flags on
`tools/story.py` enforce it:

```bash
python3 tools/story.py stories/01-dance.txt --dir segments \
    --from-video yt_destiny_2_the_final_shape_launch_trailer --forward-only
```

- `--from-video` restricts the candidate pool to one source. Every shot in the
  finished cut comes from that cinematic; nothing can drift in from another.
- `--forward-only` keeps a playhead on the source timeline. Each beat may only
  take a shot starting at or after the previous shot's out-point, so the cut
  never runs its source backwards. The distance jumped is reported per shot as
  `skip_sec`, and printed as `[skip +Xs]`.

That is the entire mechanism. **The beat order *is* the timeline** and the skip
points are simply the gaps between chosen shots.

### Why not a virtual edit

The obvious alternative was a timeline/sequencer layer: several cinematics,
tracks, a cut-graph, an edit DSL. It was rejected deliberately.

| Virtual edit | One cinematic + skip forward |
|---|---|
| A new abstraction to learn, maintain, and test | Two flags on the tool that already exists |
| Cut order and source order can disagree — you can hide continuity errors | Cut order *is* source order, so continuity is checkable by reading timecodes |
| The cut list stops being a plain derived artifact | `cut.json` stays exactly what `story.py` already emitted |
| Reordering means editing a graph | Reordering means moving a line in a text file |

The constraint also does real editorial work: a monotonic playhead means the
cut inherits the trailer's own build, which is why the movements escalate
without anyone hand-timing them. If you find yourself adding a system to manage
multiple cinematics, back out and simplify.

The cost is honest and worth stating: a beat can only be served by footage that
lies *after* the previous beat's shot. A mismatch early cascades, and with
`--forward-only` it can strand every later beat. When that happens, fix the
earliest wrong beat first — never reach for `--include-unclean`.

### Where the skip-forward points live

In [`stories/01-dance.txt`](../../stories/01-dance.txt), nowhere else. Each
`# --- MOVEMENT n ---` header names the source timecode its movement resumes
at, and every blank-line gap between beats is a skip. To see the actual jumps
the assembler took, read the `[skip +Xs]` annotation in `story.py`'s text
output or the `skip_sec` field in the JSON cut list.

## Working on the cut

### Add or reorder a hero beat

1. Find the shot in the corpus first — `python3 tools/corpus.py ensemble --dir
   segments` — and read its timecode. If nothing covers the beat, the beat is
   the thing that changes.
2. Insert the beat line into `stories/01-dance.txt` **in source-time order**,
   under the movement it belongs to. Describe the picture; the matcher scores
   caption overlap.
3. Re-run the command above and read the report. Zero misses and 20 (or n)
   shots means it landed.
4. Avoid enum-like words unless you mean them as filters — `titan`, `arc`,
   `vex` and friends become hard filters, not prose. See
   [`docs/skills/editing/SKILL.md`](../skills/editing/SKILL.md).

Moving a beat *earlier* than the shot it wants is the one move that silently
fails: under `--forward-only` its shot is already behind the playhead, so it
matches something worse or nothing at all. Reorder in source-time order and the
problem does not arise.

### Change which heroes get featured

This cut is cast entirely to the **ensemble** — anonymous Guardians, i.e.
blueberries — because that is what the source cinematic has, and because the
brief asked for placeholder blueberry nameplates.

To feature a named lead instead, name them in the beat (`Osiris`, `Elsie
Bray`...): `tools/search.py` turns a character name into a casting filter, and
`tools/plate.py plan` will then plate them automatically from their `plate:`
copy in `vocab/casting.yaml`. That only works where the index actually casts a
lead into a shot — check with `python3 tools/corpus.py <lead> --dir segments`
before writing the beat. Casting names real people; if the corpus is empty, the
answer is that the footage does not exist, not that the beat should guess.

### Nameplates

The roster for this cut does not exist yet, so it uses placeholders:

```bash
python3 tools/story.py stories/01-dance.txt --dir segments \
    --from-video yt_destiny_2_the_final_shape_launch_trailer --forward-only \
    --format json --out cut.json
python3 tools/plate.py plan cut.json --placeholders 4 --max-shot-sec 9 \
    --out plates.json
```

`--placeholders N` plates the first N ensemble shots that can hold a plate with
the uncast copy in `vocab/casting.yaml` (`ensemble.placeholder_plate`) — blue
chrome, `CONTRIBUTOR // GUARDIAN`, name `TBD`. It names nobody on purpose. It
is mutually exclusive with `--roster`: once real contributors are known, they
are who the plate is for, and you swap the flag rather than editing copy.

Plates hold 5s by default, so a ~41s cut fits about four; `--hold` trims that if
you want more. Pass `plan` the same `--max-shot-sec` the render gets or every
plate after the first trimmed shot lands late.

## Output targets

Two deliveries, one cut list. They differ by audio and by filename — not by
pipeline, and **not** by a second edit.

```bash
# 1. cut list (shared by both)
python3 tools/story.py stories/01-dance.txt --dir segments \
    --from-video yt_destiny_2_the_final_shape_launch_trailer --forward-only \
    --format json --out cut.json

# 2. website render — source audio, embedded in the site's video player
python3 tools/render.py cut.json --media media --out renders/01-dance-web.mp4 \
    --max-shot-sec 9

# 3. YouTube export — music bed laid over the finished cut
python3 tools/render.py cut.json --media media --out renders/01-dance-youtube.mp4 \
    --max-shot-sec 9 --audio <music-bed>

# 4. nameplates, burned into whichever output needs them
python3 tools/plate.py burn --video renders/01-dance-youtube.mp4 \
    --manifest plates.json --out renders/01-dance-youtube-plated.mp4
```

**Sequence order lives in the filename prefix.** `01-` is the upload position;
`02-cayde-6-the-return` and `03-zavala` follow it, and the next cut is
`stories/04-<name>.txt` → `renders/04-<name>-*.mp4`. Sorting the
directory sorts the playlist. There is no manifest and no ordering table to keep
in sync — the prefix is the whole convention, and it survives files being
copied out of the repo, which a manifest would not. This story-prefix sequence
is the repo's own; it is separate from the **act numbering** of the show, which
`docs/running-order.md` owns and `~/Videos/Wolves/Prod/` is named for.

`renders/`, `media/` and `*.mp4` are gitignored. The index references footage by
`video_id` and timecode and ships none of it; both outputs are non-commercial
fan work under Bungie's fan-content policy, and every source video record
carries its `usage_class` and `source_rights_note`.

## The footage corpus

[`corpus/ensemble.json`](../../corpus/ensemble.json) is the catalog this outline
was written against: every indexed shot cast to the anonymous-Guardian subject,
with its tags, its `clean` status, and — the reason it exists — the coverage
that is **missing**. Built and rebuilt by `tools/corpus.py`; see
[`docs/skills/corpus.md`](../skills/corpus.md) for how to add the next subject.

It is derived and regenerable. Do not hand-edit it, for the same reason nobody
hand-edits `clean`.

### Unresolved for this cut

From the corpus (`gaps`), the ensemble subject has **no clean coverage** of:

| Gap | Consequence here |
|---|---|
| `action: emote` | The dance itself cannot be shown. No Guardian emote shot is indexed at all; the index's only `emote` shot is an Eliksni busker, and it is unclean. |
| `action: vehicle` | No sparrow/ship beat is writable. |
| `shot_scale: CU` / `ECU` / `INSERT` | No close-up on a blueberry — no hands, no faceplate detail, no cutaway inserts. This is why the cut reads wide throughout. |

These are recorded, not worked around. If someone later indexes a clean emote
shot of a Guardian, the corpus stops reporting the gap and this cut can finally
be rewritten toward the footage it always wanted.

### Not automatable

Marked `automatable: no` with the reason, per `AGENTS.md` — these are judgment
calls, not missing code:

| Item | `blocked_on` |
|---|---|
| The reference video's 6:23 start point | Requires watching third-party footage that is not indexed here. Nothing about it can be verified offline, so nothing about it was assumed. |
| Music track, and where "C+C Music Factory is Mastery / full of Jams" lands | Lyric transcription is on-screen/recorded copy: it must be recovered from the source, never written from memory. The `--audio` bed is left to whoever supplies the file. |
| Music licensing | A rights decision, not the agent's call. The cut stays non-commercial regardless. |
| The "tin" SFX frame in MOVEMENT 1 | The exact frame is a visual/audio judgment against a reference this repo does not hold. The movement is where it belongs; the frame is for a human. |
| Producing the actual `.mp4` | Source media is never committed (`media/`, `renders/`, `*.mp4` are gitignored), so no render can be produced from a clean checkout. The commands above are the reproduction. |
| Real names on the nameplates | Casting names real people. Placeholders ship until a roster exists. |
