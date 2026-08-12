# destiny-vids — shot-level index for Destiny 2 footage

A taxonomy and data model for indexing Bungie's official Destiny 2 YouTube content
at the **shot/beat level**, so you can write a story in plain language and get back
an ordered, ready-to-cut sequence of **clean** shots.

Bungie explicitly permits and encourages fan-made music videos built from this
footage. This repo is the **categorization schema plus the assembly tools** —
ingestion at scale, storage, and search infra live elsewhere.

**Working on this repo as an agent?** Start with [`AGENTS.md`](AGENTS.md), then
[`docs/SKILL.md`](docs/SKILL.md) to load the one skill your task needs.

## The governing idea

**The fiction bends to the footage.** You do not hunt for shots that fit a
predetermined script; you write the script to fit the shots that already exist.
Bungie's cinematics already tell a good story — the work is naming the cast and
putting the beats in order.

Two consequences run through the whole schema:

1. **`clean` is the primary gate.** The only question that disqualifies a shot
   outright is whether something is burned into the frame that no edit can
   remove — HUD, nameplates, titles/date cards, a talking head. Everything else
   is a preference; this is a veto.
2. **Casting is inverted.** Named characters are bound 1:1 to real people
   (**leads**). Every anonymous Guardian is a **slot**, filled from a rotating
   monthly pool of Project Bluefin contributors. The nameless crowd in the
   cinematics *is* the project's cast, and it gets filled with real people.

## The cast

**Leads** — a named Destiny character bound to one person, fixed for the life of
the project. Most bindings are unconstrained: the project *names a role*, it does
not composite a face, so framing is irrelevant and a face-clear close-up is still
first-party footage.

| Character | Cast as | |
|---|---|---|
| Elsie Bray | Laura Santamaria | authored plate |
| Anna Bray | Joanna Lee | |
| Zavala | Kelsey Hightower | |
| Cayde-6 | castrojo | |
| Osiris | mrbobbytables | |
| Sagira | Lindsay Gendreau | Osiris's Ghost; cast on presence, no framing constraint |
| Saint-14 | Kat | remains the bubble in the original Wolves; authored plate |
| Mara Sov | Karena Angell | subclass unauthored (#5) |
| Petra Venj | Lenka | |
| Variks | Nate Waddington | |
| The Speaker | Jonathan Bryce | |
| Amanda Holliday | Ashley Willis | |
| the red-haired Iron Lord (Rise of Iron intro) | Paris Pittman | canonical name unconfirmed |
| **Lord Saladin** | **Jeefy** | **constrained: far + helmeted only** |

Saladin is the one **constrained** binding: Jeefy plays the Iron Lord but does not
resemble Saladin, so the framing has to do the work. Only wide, helmeted shots
derive `usable = true`; anything tighter or face-clear derives `usable = false`
with the reason in `constraints_failed`, gets no ranking boost, and is excluded
from Saladin retrieval entirely. There is enough far/helmeted footage for this to
be a real cast rather than a compromise.

Written but not yet cast (retrieval still identifies them; the tile just has no
name on it): Ikora Rey, the Drifter, Crow, Caiatl, Eris Morn, Shaxx, Ghost,
Savathûn, the Witness. Add or change a binding in `vocab/casting.yaml`.

**Ensemble** — anonymous Guardians. A shot exposes `slots` (6 for a crowd, 3 for a
group, else 1), and `tools/ensemble.py` fills them from a month's contributors.
`casting.person` is always `null` for ensemble in a segment record: people are
assigned per month, so a rotating pool never invalidates a tagged segment.

## Repository layout

| Path | What it is |
|---|---|
| `vocab/` | Controlled vocabularies (YAML) — the **single source of truth** for every enum. `cleanliness.yaml` (overlays → `clean`, `footage_tier`) and `casting.yaml` (the lead cast map + ensemble policy) carry the two decisions above. |
| `schema/segment.schema.json` | JSON Schema (Draft 2020-12) for one indexed segment/beat. |
| `schema/video.schema.json` | JSON Schema for a source-video record (video-scoped inherited defaults). |
| `schema/brief.schema.json` | JSON Schema for the `brief` block in a GitHub issue — the machine-readable half of a request for a video. |
| `examples/` | Fully-annotated example records that validate against the schemas. |
| `tools/story.py` | **Outline → ordered cut list.** Text/JSON/EDL/CSV. |
| `tools/render.py` | **Cut list → rendered video.** ffmpeg cut + concat against local source media. |
| `tools/ensemble.py` | Monthly Bluefin contributor roster → Guardian credit tiles. |
| `tools/search.py` | NL query → enum filters + caption match + editorial ranking. |
| `tools/ingest.py` | Video-level ingestion: Bungie YouTube title (oEmbed, no API key) → inherited defaults → `video.schema.json` record. |
| `tools/annotate.py` | Annotator pipeline: shot detection → keyframes → pluggable tagger → schema-valid records. |
| `tools/derive.py` | Pure derivation of `clean`, `footage_tier`, `traversal_hero` and `casting`. |
| `tools/brief.py` | **Issue → executable brief.** Parses the fenced `brief` block in an issue body, or proposes one from prose for the owner to confirm. |
| `tools/corpus.py` | **Casting subject → footage corpus.** Every indexed shot a character appears in, plus the vocabulary values they have no clean coverage of. |
| `tools/gaps.py` | What in the index is unfinished — unindexed videos, unreviewed beats, uncast leads — optionally filed as fingerprinted issues. |
| `tools/plate.py` | **Cut list → Guardian nameplates.** Plans timed plates from the casting vocab + contributor roster, renders them as transparent PNGs, and burns them into a cut. |
| `tools/ffmpeg-container-shim.sh` | Host setup, not a pipeline stage: installs a containerized `ffmpeg`/`ffprobe` on `PATH` so the whole machine has H.264. See `docs/rendering.md`. |
| `scripts/make_video.sh` | The whole loop, issue → rendered cut, resuming at whatever stage is unfinished and stopping at tagging. |
| `stories/` | Worked outlines. A numeric prefix (`01-dance.txt`) is the cut's position in the story sequence. |
| `corpus/` | Per-character footage corpora, generated by `tools/corpus.py` — derived, never hand-edited. |
| `videos/` | Ingested video-level records (6 real Bungie videos, metadata-only). |
| `tags/` | Tagger output per video, keyed by beat index — replayed by `annotate.JsonTagger`. |
| `segments/` | Assembled, schema-valid segment records for real footage — 69 shots from the TFS launch trailer and 50 from the Curse of Osiris opening cinematic. |
| `tests/` | `pytest` suite across search, derivation, story assembly, ensemble casting, ingestion, the stub pipeline, and ffmpeg resolution. |
| `docs/` | `SKILL.md` (agent skill router) and `skills/`, plus the design docs: `taxonomy.md` (axis reference), `pipeline.md` (segmentation + cost tiers), `agent-retrieval.md` (query mapping), `rendering.md` (which ffmpeg, and why). `cuts/` documents each shipped cut. |
| `AGENTS.md` | Agent operating contract: commands, boundaries, and the three rules that outrank convenience. |

## The unit: a "beat"

Segmentation uses **automated shot-boundary detection as the primitive**
(PySceneDetect content-detector, with TransNetV2 as a neural upgrade for
fades/dissolves). Cinematics are cut-heavy → one shot = one beat. Gameplay has
long/absent cuts → fixed-window sampling (~2–4s) coalesced into tag-stable runs.

Shot cuts are free, deterministic and reproducible, so a cheap flash-tier model
**never has to decide where a segment starts** — killing the biggest
ambiguity-and-cost sink. See `docs/pipeline.md`.

## The axes

| Axis | Fields (see `vocab/`) |
|---|---|
| **A. Cleanliness** | `overlays` → derived `clean`, `footage_tier` |
| **B. Domain semantics** | `class`, `element`, `faction`, `destination`, `character`, `era`, `activity`, `subclass_version` |
| **C. Cinematography** | `shot_scale`, `composition`, `camera_angle`, `camera_movement`, `pacing`, `content_type`, `lighting` |
| **D. Casting** | derived `casting` (`role`, `character`, `person`, `usable`, `constraints_failed`, `slots`) |
| **E. Identity** | `substitutability` (0–5), `identity_visibility`, `character_identifiability`, `helmet_simplicity`, `face_count`, `subject_facing_camera` |
| **F. Register / mood** | `register` (−2..+2), `mood` |
| **G. Salience** | `subject_salience` (required) |
| **H. Action** | `action` (incl. first-class `traversal`), derived `traversal_hero` |

Three structural decisions cut across every axis:

- **Cleanliness must be positively established.** An untagged `overlays` derives
  `clean = false`, not true. Guessing clean on an unexamined shot is how a HUD
  ends up in the finished cut.
- **Gameplay is kept, not dropped.** `footage_tier` separates `cinematic` from
  `gameplay`, so gameplay stays retrievable as coverage while cinematics cut
  first. Tier and cleanliness are independent: clean gameplay is usable, and a
  cinematic with a burned-in date card is not.
- **Observed vs inherited, with provenance on every field.** Domain fields split
  into what a frame can *show* (`element`) and what only the video's era can
  supply (`subclass_version`). Each tagged field has an entry in `provenance`:
  `{source: inherited|observed, label_source: manual|heuristic|model,
  confidence: 0..1}`, so retrieval can trust-tier on it.

`substitutability` survives but is **demoted**: it no longer gates usability, it
only tie-breaks between otherwise-equal ensemble shots — how comfortably a
contributor's name sits on that Guardian.

## Build a story

Write an outline: one beat per line, in order, in plain language.

```
wide establishing shot of the Traveler
a crowd of guardians gathered beneath it
close up on a lone titan helmet
Elsie Bray hero shot
Lord Saladin speaking by firelight
guardians parkouring across a bridge toward the light
```

```bash
python3 tools/story.py stories/example-outline.txt
python3 tools/story.py stories/example-outline.txt --format edl --out cut.edl
python3 tools/story.py stories/example-outline.txt --format csv
python3 tools/story.py stories/example-outline.txt --allow-gameplay   # widen to coverage
```

It walks the beats in order, casts each to the best **distinct clean** shot, and
prints the cut with its reasoning. It never reuses a shot (a story that cuts the
same shot twice reads as padding), and **unmatched beats are reported, never
silently dropped** — no clean coverage is a real answer, so rewrite the beat
rather than cutting a HUD into the sequence.

`--format edl` emits a CMX3600-style EDL with a contiguous record timeline;
`--format json` emits a shot list you can feed straight to `tools/ensemble.py`
or `tools/render.py`.

### One cinematic, skipped forward

A cut that lives inside a single source cinematic says so, and never runs that
cinematic backwards:

```bash
python3 tools/story.py stories/01-dance.txt --dir segments \
    --from-video yt_destiny_2_the_final_shape_launch_trailer --forward-only
```

`--from-video` restricts the pool to one source; `--forward-only` holds a
playhead so each beat may only take a shot at or after the previous shot's
out-point, reporting the jump as `[skip +Xs]`. The beat order *is* the
timeline — there is no sequencer, no cut-graph, and no way for cut order to
disagree with source order. Worked example, with the reasoning:
[`docs/cuts/01-dance.md`](docs/cuts/01-dance.md).

## Know what a character has on film

An outline is written against the footage that exists, so the first question is
always "what has this character actually got?".

```bash
python3 tools/corpus.py ensemble --dir segments      # the anonymous Guardians
python3 tools/corpus.py osiris --dir segments --out corpus/osiris.json
python3 tools/corpus.py --check                      # committed corpora are fresh
```

A corpus lists every indexed shot cast to one subject — a lead key from
`vocab/casting.yaml`, or `ensemble` — with its tags, timecodes and `clean`
status, and then the part that matters: `gaps`, the vocabulary values the
subject has **no clean coverage** of, each marked `unresolved`. A beat written
against a gap cannot land, so the gap is the answer, and the fiction bends.

Unclean shots stay in the corpus labelled with `blocked_by`, because knowing
the footage exists and why it cannot be cut is what stops the next person
re-finding it. The files under `corpus/` are derived — rebuild with
`tools/corpus.py --write`, never hand-edit.

## Render the cut

The index stores timestamps, not footage, so rendering needs the source video
present locally — `media/<video_id>.mp4`, gitignored and never redistributed.

```bash
yt-dlp -S "vcodec:h264" -o "media/yt_destiny_2_the_final_shape_launch_trailer.%(ext)s" <url>
python3 tools/story.py stories/hero-cut.txt --dir segments --format json --out cut.json
python3 tools/render.py cut.json --media media --out renders/hero-cut.mp4
python3 tools/render.py cut.json --audio track.mp3   # lay a music bed
```

Every clip is re-encoded rather than stream-copied: a stream copy snaps the
in-point to the nearest keyframe, which throws away the exact boundary shot
detection worked to find. Re-encoding to one common size/rate/pixel format is
also what lets the concat demuxer join the clips at all — it requires identical
stream properties across inputs. A shot whose source file is absent is
**reported and skipped**, never silently dropped.

`--max-shot-sec` caps how long any one shot is held, trimming from its tail — a
detector-derived beat can be a fine *beat* and a terrible *cut* (the Curse of
Osiris cinematic ends on a 25-second static gateway shot). The in-point is what
the index worked to find, so a trim never moves the start.

**Which ffmpeg?** On Bluefin, the already-running `bluefin-thumbnailer`
container — the host's `ffmpeg-free` has no H.264 decoder and fails only once
decoding starts. `render.py` resolves the container first and prints what it
chose; `--no-container` forces a local binary. Full rationale, resolution order,
and the AV1 shot-detection trap: `docs/rendering.md`.

To give the whole machine a working ffmpeg instead, install the shim:

```bash
install -Dm755 tools/ffmpeg-container-shim.sh ~/.local/bin/ffmpeg
ln -sf ffmpeg ~/.local/bin/ffprobe          # it dispatches on $0
ffmpeg -version                             # => 8.1 (container)
FFMPEG_NO_CONTAINER=1 ffmpeg -version       # => the host binary (escape hatch)
```

## Name the cast on screen

`tools/plate.py` puts the casting on the frame, in the Project Bluefin Guardian
nameplate treatment (ported from the website's Wolves intro overlay):

```bash
python3 tools/ensemble.py roster --month 2026-08 --out roster.json
python3 tools/plate.py plan cut.json --roster roster.json --max-shot-sec 9 --out plates.json
python3 tools/plate.py burn --video renders/cut.mp4 --manifest plates.json \
    --out renders/cut-plated.mp4
```

`plan` reads the plate copy from `vocab/casting.yaml` — the same file that binds
a character to a person — so a recast changes the plate with no other edits. The
copy is the reference deck's vocabulary and nothing more: `label`, `class`,
`name`, `title`, `trustee` (`~/Videos/nameplates.json`), plus a `kind: "title"`
card for the ensemble roster. Do not invent fields; a plate that says something
the deck has no slot for is a plate that says something nobody wrote.

Copy that somebody *has* authored is reproduced verbatim rather than written
here — ten people have a Guardian identity in the deck or in the website's
`public/wolves/characters/characters.json`, and the roster, the precedence
between those sources and the known divergences are in
[`docs/skills/plates.md`](docs/skills/plates.md#where-the-copy-is-authored).

Each lead is plated **once**, on the first appearance long enough to read, and
never on a shot that failed its binding's constraints (that shot is already
excluded from the character's retrieval, so it is not a reveal). Ensemble
contributors come from the deterministic assignment in `tools/ensemble.py`;
anyone whose shot is too short to hold a plate is credited together on a roster
title card over the tail, because dropping a month's contributors silently is
the one unacceptable outcome.

Plates are anchored to a shot but not confined to it — a lower third routinely
rides across a cut, and Destiny cinematics are full of two-second shots that
could otherwise never carry a reveal. Two plates are never visible at once;
`plan` and `burn` both refuse a manifest where the windows overlap.

Pass `plan` the **same** `--max-shot-sec` the render used, so plate timings land
on the finished file rather than on the source timeline.

Before a month's roster exists, `--placeholders N` plates that many ensemble
shots with the uncast copy in `vocab/casting.yaml`
(`ensemble.placeholder_plate`: `CONTRIBUTOR // GUARDIAN`, name `TBD`) so a cut
can be timed and reviewed without anyone's name on it. It is mutually exclusive
with `--roster` — once real contributors are known, they are who the plate is
for.

## Ship a cut

A finished cut goes to two places from **one** cut list: the website player
(source audio) and a YouTube upload (a music bed via `render.py --audio`). They
differ by audio and filename, never by a second edit.

Upload order is the numeric filename prefix: `stories/01-dance.txt` →
`renders/01-dance-web.mp4` and `renders/01-dance-youtube.mp4`. Sorting the
directory sorts the playlist, and there is no ordering manifest to fall out of
sync. Each shipped cut is documented in `docs/cuts/` — its source cinematic,
skip points, unresolved beats, and whatever a human still has to decide.

| Cut | Doc |
|---|---|
| 01 — Dance | [`docs/cuts/01-dance.md`](docs/cuts/01-dance.md) |

## Editorial direction

Cuts favor **heroes and action**. The Traveler is used sparingly, and
antagonists stay mysterious — held wide, brief, and never in close-up — so
`enemy_threat` shots are coverage, not centerpieces.

## Cast the ensemble

```bash
python3 tools/ensemble.py roster --month 2026-08 --out roster.json
python3 tools/ensemble.py assign --roster roster.json --shotlist shotlist.json
```

`roster` collects a calendar month's Project Bluefin contributors via `gh api`
(bots filtered; a repo that errors is skipped with a warning rather than failing
the month). `assign` fills every ensemble slot and emits one credit **tile** per
contributor.

Assignment is **deterministic** — a re-render must not reshuffle who played whom —
so it round-robins a month-seeded rotation of the roster, sorted by login (the
pool is a cast list, not a leaderboard). Everyone is placed once before anyone
repeats, and if there are more contributors than slots the shortfall is reported
in `uncredited` rather than silently swallowed.

## Search

```bash
python3 tools/search.py "guardians parkouring across a bridge"
python3 tools/search.py "crowd of guardians" --top 3
python3 tools/search.py "Elsie Bray hero shot"
python3 tools/search.py "show us Hunters with Arc" --include-unclean
```

Controlled-vocab enums answer the *hard* facets (`"Hunter" + "Arc"` → exact
filter); a free-text `caption` catches the long tail. Unclean shots are excluded
from the pool outright; `--include-unclean` keeps them (heavily penalized) for
triage. The `+0.40` lead boost applies **only when the query asked for a
character** — its purpose is "when you ask for Elsie, hand me Elsie's footage",
not to let a named lead muscle in on an unrelated query.

Full weights and query-mapping behavior are in `docs/agent-retrieval.md`. The
caption signal is a dependency-free token-overlap stand-in; swap `caption_sim()`
for embedding cosine similarity in production.

## Ingest real footage (metadata-first)

```bash
python3 tools/ingest.py https://www.youtube.com/watch?v=6Gm5mbwrqSA --playlist "Destiny 2 Trailers"
python3 tools/ingest.py --id yt_demo --title "Destiny 2: Lightfall | Neomuna Gameplay Trailer"  # offline
```

## Index a video end to end

Indexing runs in two passes, because tagging happens out-of-band. The first
detects beats and writes one keyframe per beat — the stills a vision model or a
human reads. The second replays the resulting tags into schema-valid segments:

```bash
yt-dlp -S "vcodec:h264,res:1080" -o "media/<video_id>.%(ext)s" <url>
python3 tools/ingest.py <url> --id <video_id>

# pass 1 — detect + keyframes (also writes keyframes/<video_id>/beats.json)
python3 tools/annotate.py index --video media/<video_id>.mp4 \
    --video-record videos/<video_id>.json

# ...tag every keyframe into tags/<video_id>.json...

# pass 2 — assemble
python3 tools/annotate.py index --video media/<video_id>.mp4 \
    --video-record videos/<video_id>.json --tags tags/<video_id>.json
```

Stills land in `keyframes/<video_id>/`, derived from the record rather than
chosen at the command line, so two videos cannot collide on the same `000.jpg`.

Or run the whole loop from the issue that asked for the video:

```bash
scripts/make_video.sh 3          # resumes at whatever stage is unfinished
```

It skips any stage whose output already exists and **stops at tagging**, which
is the stage that needs somebody to look at frames.

Both passes run the **same detector settings**, so beat indices line up; a tag
file is only ever valid against the shot list its own detection pass produced.
`--min-shot-sec` (default 0.5s) merges the sub-second "shots" Destiny's ability
flashes and explosions provoke out of a frame-difference detector.

`overlays` is a **required** tagger field — an untagged `overlays` derives
`clean = false`, so a tagger that skips it silently marks its whole output
unusable.

## Cost posture

The schema is designed to be populated by a **flash-tier model** at scale.
`docs/pipeline.md` buckets every field into Tier 0 (free/deterministic), Tier 1
(flash-tier / cheap heuristic), and Tier 2 (heavy model or human). All four
derived fields are Tier 0 pure functions. Notably, `helmet_simplicity` is **not**
reliably flash-affordable per frame — cheapest path is inferring it from armor-set
metadata or the video title, else it defaults to `unknown`.

## Prior art borrowed

IPTC Video Metadata Hub (keywords/entities/persons-shown), PBCore, EBUCore `Shot`,
MovieLabs OMC depiction/portrayal model (the real prior art for "one character,
many doubles"), PySceneDetect / TransNetV2 / AutoShot (shot detection),
stock-footage editorial/mood + model-release conventions, film stand-in /
photo-double terminology, and CMX3600 EDL for the cut list. There is **no
standards-body canonical** shot-scale or camera-movement enum, so we adopt the
common editorial abbreviations.

## Validate

```bash
pip install jsonschema pyyaml pytest
python3 -m pytest -q
```

Optional extras, only for the frame-touching stages: `scenedetect` and
`opencv-python-headless` (shot detection), `imageio-ffmpeg` (a fallback ffmpeg
when the container isn't available). The test suite passes without them.

The suite validates every example against the schema, re-derives every derived
field and asserts it matches what is stored, and pins the cast list — so a silent
change would re-credit a real person. It also validates every **committed**
segment, video and tag file (`tests/test_index_integrity.py`), because the index
is data and data drifts: a hand-corrected `label_source: "human"` — one word, not
in the enum — sat in the index until a rebuild died on it.

## Work is filed as issues

The backlog is GitHub issues. An issue carries the owner's prose *and* a fenced
`brief` block — the same request in YAML, matching `schema/brief.schema.json`,
using the same character ids as the index:

````markdown
```brief
sources:
  - url: https://www.youtube.com/watch?v=0B9v8VoZrMU
characters: [saint_14]
automatable: partly
blocked_on: the source is not indexed yet
```
````

Writing that block is not the owner's job — an agent proposes it and the owner
confirms it:

```bash
python3 tools/brief.py normalize 3   # prose -> a proposed block
python3 tools/brief.py check         # validate every open issue
python3 tools/gaps.py                # what in the index is unfinished
```

`automatable` is required, because three classes of work here can never be
automated: a visual judgement about a frame, a claim about a real person, and a
licensing decision. An agent that names one and stops has succeeded. See
`docs/skills/issues.md`.

## Where a finished cut goes

A file in `renders/` is not a deliverable. The owner's delivery workspace is
`~/Videos` (read its `README.md`): approved cuts are staged into
`~/Videos/UPLOAD/` in playlist order and published by `~/Videos/yt-refresh.py`
into **one unlisted playlist**, because YouTube cannot replace a video file — a
re-upload always gets a new ID, so only a playlist link is stable.

The credited contributors cut is **regenerated, never hand-edited**: a new month
is a new render from checked-in data (`scripts/build_uncut_credited.sh`), not a
new edit. Titles, descriptions and audio treatment for a delivered file follow
that workspace's rules, not this one's — see
[`docs/skills/production.md`](docs/skills/production.md#delivering-a-finished-cut).
