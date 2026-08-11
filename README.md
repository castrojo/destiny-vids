# destiny-vids — shot-level index for Destiny 2 footage

A taxonomy and data model for indexing Bungie's official Destiny 2 YouTube content
at the **shot/beat level**, so you can write a story in plain language and get back
an ordered, ready-to-cut sequence of **clean** shots.

Bungie explicitly permits and encourages fan-made music videos built from this
footage. This repo is the **categorization schema plus the assembly tools** —
ingestion at scale, storage, and search infra live elsewhere.

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
| Elsie Bray | Laura Santamaria | |
| Anna Bray | Joanna Lee | |
| Zavala | Kelsey Hightower | |
| Cayde-6 | castrojo | |
| Osiris | mrbobbytables | |
| Saint-14 | Kat | remains the bubble in the original Wolves |
| Mara Sov | Karena Angel | |
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
| `examples/` | Fully-annotated example records that validate against the schemas. |
| `tools/story.py` | **Outline → ordered cut list.** Text/JSON/EDL/CSV. |
| `tools/render.py` | **Cut list → rendered video.** ffmpeg cut + concat against local source media. |
| `tools/ensemble.py` | Monthly Bluefin contributor roster → Guardian credit tiles. |
| `tools/search.py` | NL query → enum filters + caption match + editorial ranking. |
| `tools/ingest.py` | Video-level ingestion: Bungie YouTube title (oEmbed, no API key) → inherited defaults → `video.schema.json` record. |
| `tools/annotate.py` | Annotator pipeline: shot detection → keyframes → pluggable tagger → schema-valid records. |
| `tools/derive.py` | Pure derivation of `clean`, `footage_tier`, `traversal_hero` and `casting`. |
| `stories/` | Worked outlines. |
| `videos/` | Ingested video-level records (5 real Bungie trailers, metadata-only). |
| `tags/` | Tagger output per video, keyed by beat index — replayed by `annotate.JsonTagger`. |
| `segments/` | Assembled, schema-valid segment records for real footage (69 real shots from the TFS launch trailer). |
| `tests/` | `pytest` suite across search, derivation, story assembly, ensemble casting, ingestion, the stub pipeline, and ffmpeg resolution. |
| `docs/` | `taxonomy.md` (axis reference), `pipeline.md` (segmentation + cost tiers), `agent-retrieval.md` (query mapping), `rendering.md` (which ffmpeg, and why). |

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
detection worked to find. A shot whose source file is absent is **reported and
skipped**, never silently dropped.

**Which ffmpeg?** On Bluefin, the already-running `bluefin-thumbnailer`
container — the host's `ffmpeg-free` has no H.264 decoder and fails only once
decoding starts. `render.py` resolves the container first and prints what it
chose; `--no-container` forces a local binary. Full rationale, resolution order,
and the AV1 shot-detection trap: `docs/rendering.md`.

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

`videos/` already holds 5 real ingested Bungie trailers. Segment-level tagging
still needs the frame pass (`tools/annotate.py`), where `overlays` is a
**required** tagger field — a tagger that skips it silently marks its whole output
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
change would re-credit a real person.
