# Pipeline: Segmentation → Inference → Review

How Bungie's official Destiny 2 YouTube footage becomes a searchable, beat-level index — on a flash-tier inference budget. Companion doc: `vocab/` (field definitions and controlled vocabularies).

Design constraint: **one cheap text/vision flash model, no per-frame heavy vision pipeline.** Every architectural decision below exists to keep the model out of the two places it is expensive and unreliable: deciding *where* segments start/end, and deciding *fine-grained visual identity*.

---

## 1. Segmentation

**The indexed unit is the *beat*.** A beat is the thing an editor searches for ("helmeted Guardian crossing a bridge at golden hour") and the thing that lands on a timeline.

### Primitive: shot-boundary detection

Shot boundaries are computed **deterministically, before any model is invoked**. The model is never asked "where does this shot end?" — that question is the single biggest ambiguity and cost sink in video indexing. If the model decides boundaries, every segment is a judgment call: boundaries drift between runs, overlapping windows double-count content, and review effort is spent re-arguing segmentation instead of metadata. Fixing boundaries up front makes everything downstream **reproducible, diffable, and cacheable** — the model only ever *describes* pre-cut spans.

**Primary: [PySceneDetect](https://www.scenedetect.com/) content detector.** Frame-difference + HSV histogram thresholding; CPU-only, faster than realtime, free. This is the default pass for everything.

**Optional upgrade: [TransNetV2](https://github.com/soCzech/TransNetV2).** A small neural net purpose-built for shot boundaries that handles **fades, dissolves, and soft transitions** that histogram methods miss. Still cheap (it runs on subsampled frames, not full-res), but a model dependency — so it's the upgrade path for cinematics, not the default. Prior art: [AutoShot](https://github.com/flix/AutoShot) and friends validate that a dedicated SBD pass beats asking a general VLM to find cuts.

### Two content types, two strategies

| Content | Cut behavior | Strategy |
|---|---|---|
| **Cinematics** (story trailers, cutscenes) | Cut-heavy, sub-second to ~8s shots | **One shot = one beat.** The edit already did the segmentation work; respect it. |
| **Gameplay** (reveals, ViDocs, gameplay trailers) | Long takes, few or no cuts | **Fixed-window sampling**: extract a keyframe every ~2–4s, tag each keyframe, then **coalesce runs of consecutive keyframes with stable tags** into one beat. |

Coalescing rule: adjacent keyframes merge while their Tier-1 tags (location/activity/action family) agree; a tag change or a detected shot cut closes the beat. Beats get `start_tc`/`end_tc` from the coalesced span, or from the shot detector for cinematics.

**Tradeoff, stated plainly:** shot-boundary beats are editable gold — clean in/out points that already sit on the music — but a detector pass costs machine time per video. Fixed-window sampling is cruder (beats start/end mid-gesture) but bounded and trivially cheap. We pay the detector cost because Destiny cinematics are the highest-value hero footage and gameplay coalescing gives acceptable edit points anyway.

### Known hazard: Destiny false cuts

PySceneDetect's content detector fires on large abrupt frame deltas — and Destiny is full of them:

- **Ability flashes / super activations** (full-screen bloom and color floods)
- **Explosions, muzzle flash, teleporter/dive transitions**
- **UI/HUD transitions** (director wipes, menu fades, orbit screens)

Mitigations, in order of cheapness: raise the detection threshold above the default on gameplay sources; apply a **minimum shot length** (~0.5–1.0s) and merge sub-threshold "shots" back into their neighbors; treat a detected cut whose surrounding keyframes carry identical tags as a coalescing no-op. TransNetV2 is the better answer where false cuts matter (it's trained against exactly these), which is why it's the upgrade path for cinematics.

`tools/annotate.py index` applies the minimum-shot-length mitigation by default (`--min-shot-sec 0.5`).

### Running a real video through it

Indexing is **two passes over the same detection**, because tagging happens
out-of-band:

```bash
# pass 1: beats + one keyframe each (plus keyframes/<dir>/beats.json)
python3 tools/annotate.py index --video media/<id>.mp4 \
    --video-record videos/<id>.json --keyframes-dir keyframes/<dir>

# pass 2: replay the tags produced from those stills into segments/
python3 tools/annotate.py index --video media/<id>.mp4 \
    --video-record videos/<id>.json --tags tags/<id>.json
```

Beat index is positional, so a tag file is only valid against the shot list its
own detection pass produced — which is exactly why both passes run identical
detector settings and why the beat manifest travels with the stills. If pass 1
reports **1 beat** for a cut-heavy source, the codec is wrong, not the detector
(see the AV1 trap in `docs/rendering.md`).

---

## 2. Metadata inheritance (metadata-first, frames-second)

The cheapest pixels are the ones you never look at. Every YouTube video arrives with **title, description, tags, and playlist membership** — a text bundle that pins down most of the taxonomy before a single frame is decoded.

**Step 1 — one text-only LLM call per video** (not per beat): feed title + description + tags + playlist name to the flash model; get back **video-scoped defaults**: `era`/`expansion`, `activity_type`, `content_type` (cinematic vs gameplay), and frequently `destination`. Stamped on every beat in the video as:

```
source = inherited, confidence = <0–1>
```

**Step 2 — the frame pass fills only what needs pixels** (shot_scale, camera_movement, action, identity_visibility, …). Where a frame-derived field contradicts an inherited default with higher confidence, it **overrides** and is stamped:

```
source = observed
```

`source` + `confidence` on every field is what makes review cheap: reviewers filter to `inherited AND confidence < threshold` instead of re-checking everything.

### Worked example

Video: title `"Destiny 2: The Final Shape | Launch Trailer"`, playlist `"The Final Shape"`, tags `[destiny 2, the final shape, launch trailer, witness, traveler]`.

One text-only call derives, before touching frames:

| Field | Value | Source | Confidence |
|---|---|---|---|
| `era` | `lightfall_tfs` era / `the_final_shape` | inherited | 0.99 |
| `content_type` | `cinematic` | inherited | 0.95 ("trailer" + no HUD terms) |
| `activity_type` | `n/a_cinematic` | inherited | 0.9 |
| `destination` | `pale_heart` (TFS default) | inherited | 0.7 |

Every beat in the video inherits these. The frame pass then only spends tokens on pixels: `shot_scale`, `camera_movement`, `identity_visibility`, `substitutability`, `overlays`, plus confirming/denying `destination: pale_heart` (a Witness-pyramid interior shot would override to `observed`). A gameplay example — `"Destiny 2: Into the Light | Onslaught Gameplay"`, playlist `"Into the Light"` — yields `era: into_the_light`, `content_type: gameplay`, `activity_type: onslaught`, `destination: last_city` at comparable confidence, still zero frames read — though `content_type: gameplay` is itself a strong prior that `overlays` will include `hud` (see §3).

---

## 3. Review tiers

Not every field deserves the same spend. Buckets:

| Tier | Cost model | Fields |
|---|---|---|
| **Tier 0 — free / deterministic** | No model. OpenCV/OCR/audio libs. | Shot boundaries, timecodes, HUD/OCR text (kill feed, location banners), audio/music/silence markers, dominant color, brightness, `face_count` — plus four assembly-time derivations that run after tagging, on every segment, regardless of which tagger produced it: `clean`, `footage_tier`, `traversal_hero`, `casting` (see below) |
| **Tier 1 — flash-tier model + cheap heuristics** | One flash vision call per keyframe/beat; classical CV where it's good enough | `class`, `element`, `faction`, `shot_scale` (coarse), `camera_movement` (coarse — optical-flow heuristics separate static/pan/tilt/push/handheld before the model ever sees it), `pacing`, `salience`, `action`, `identity_visibility`, `substitutability`, `overlays` (cheap and highly automatable — see below), `caption`, `mood`, `register` |
| **Tier 2 — heavy model or human** | Expensive per-shot; spend only on queue-selected shots | `helmet_simplicity`, fine-grained character identity (which named NPC), dolly-vs-zoom disambiguation, `subclass_version` confirmation (e.g. pre- vs post-rework Solar visuals), final hero-shot sign-off |

### `overlays` is a required tagger field, not an optional one

`clean` derives `false` on an untagged shot (`docs/taxonomy.md`, Axis A), so a tagger that silently skips `overlays` doesn't leave a small gap — it marks its **entire output unusable**: every segment it touches fails the primary gate by default. Every `Tagger` implementation must set it, no exceptions.

The good news is it's cheap. HUD reticles, nameplates, kill feeds, and burned-in title/date cards are near-textbook OCR/template-matching problems — nothing like the fine-grained discrimination `helmet_simplicity` needs (below) — so `overlays` sits comfortably in Tier 1. For `content_type: gameplay` sources it's arguably **Tier 0**: the inherited `content_type` already all but implies a HUD is in frame, so the tagger is mostly confirming a strong prior rather than discovering something from scratch.

### The four Tier 0 derivations run after tagging, not instead of it

`clean`, `footage_tier`, `traversal_hero`, and `casting` are pure functions of fields a tagger already produced. `tools/derive.py` computes all four once, deterministically, at assembly time — no vision pass, no separate heuristic budget, just set arithmetic and a lookup against `vocab/casting.yaml`'s `leads` map. A `Tagger` implementation is never allowed to set them directly; the assembler computes them itself from whatever the tagger returned, so every derivation reruns correctly from the stored tags alone — including after a `vocab/casting.yaml` edit (a new lead binding, a newly-cast role) with no re-tagging of a single frame.

### Honest verdict on `helmet_simplicity`

**It is not reliably flash-affordable per frame.** Telling "plain smooth helmet" from "helmet with antlers/wires/glow" at gameplay-trailer resolution, at distance, in motion, is exactly the kind of fine-grained visual discrimination flash models flub — and it still matters for us (a simple-helmet Guardian reads as more comfortably substitutable; a distinctive one reads as more specific). Cheapest path in order:

1. **Infer from armor-set metadata / title+description** — armor-focused videos ("Armor Showcase", eververse/season-pass trailers) name the sets; that text resolves helmet_simplicity at video scope for free.
2. **Else a heavier visual pass** (Tier 2) on queue-selected shots only.
3. **Default: `unknown`.** Do not force this field into the flash budget; a confidently-wrong `simple` is worse than an honest `unknown` because it silently poisons the substitutability tie-break.

### Named-character identity is usually inherited, not seen

Fine-grained character identity sits in Tier 2 *as a per-frame vision problem* — but for named story characters it rarely needs to be solved that way. A character like Elsie Bray is normally pinned by the video's **title, description, and subtitles** long before frames matter ("Destiny 2: Beyond Light — The Exo Stranger"), so the `character` list is filled by the same cheap text pass that sets era/activity and stamped `source = inherited`. `casting` then derives a `lead` binding from that list at zero model cost. Reserve the heavy per-frame identity pass for shots where the text bundle is silent and the character claim actually hinges on pixels.

### Human review queue: spend manual effort only where it converts

Route a beat into the human queue **only if** it is high-value hero material:

```
clean = true
AND ((casting.role = lead AND casting.usable)
     OR traversal_hero
     OR (subject_salience in {guardian_hero, crowd_group} AND shot_scale in {ELS, LS}))
```

`clean` comes first and is non-negotiable — there is no point spending a human review pass on a shot that's already excluded from retrieval by an unremovable overlay. The lead clause additionally requires `casting.usable`: the one constrained binding (`saladin` → `jeefy`) can derive `role = lead` on a shot that still fails its constraints, and that shot is already structurally excluded from Saladin's retrieval (`docs/agent-retrieval.md`), so reviewing it as hero material would not convert into anything cuttable. Past this gate, the queue targets the footage that will actually anchor an FMV: usable named leads, traversal beats, and establishing-scale hero/ensemble shots. Everything else stands on Tier 0/1 tags. The queue is the whole "ensure proper review" story: humans sign off on the small subset of footage that matters, instead of sampling noise across thousands of beats.

---

## 4. Traversal as first-class

Traversal is **both** an `action` vocabulary value (running, jumping, sparrow, platforming, bridge-crossing…) **and** a derived boolean, because "Guardian moving through big space" is the single most reusable FMV beat and it falls *between* "action beat" and "establishing shot" if you only model one axis:

```
traversal_hero =
    action includes traversal
    AND shot_scale ∈ {ELS, LS, MLS, MS}
    AND camera_movement ∉ {handheld_shaky}
```

Wide enough to show the world, tight enough to read as *a Guardian*, stable enough to cut on. Substitutability plays no part here any more — a recognizable Guardian, or a named lead, sprinting across a bridge is still a traversal hero beat; anonymity was never the point, reusability was. The bridge-running beat that isn't combat and isn't a pure landscape gets its own retrievable slot — that slot is `traversal_hero`.

---

## 5. Rendering

Everything above produces an *index*. Turning a retrieved cut list back into
frames is the one stage that decodes video, and on an atomic Fedora/Bluefin host
it is also the stage most likely to fail: the default `ffmpeg-free` has no H.264
decoder and errors only once decoding starts, which reads like a corrupt input
rather than a missing codec.

`tools/render.py` resolves a working ffmpeg — preferring the ffmpeg container
already running on the host — cuts each shot at its exact in/out point, and
concatenates. Clips are re-encoded rather than stream-copied, because a stream
copy snaps the in-point to the nearest keyframe and discards the precise
boundary §1 spent a detector pass to find.

`tools/plate.py` then names the cast on screen. It is a separate stage from the
cut for the same reason segmentation is separate from tagging: a re-title should
not re-cut. Plate copy is read from `vocab/casting.yaml`, so the on-screen
credit and the casting binding cannot drift apart — recasting a character
changes the plate and nothing else. Ensemble credits come from the deterministic
monthly assignment in `tools/ensemble.py`, so a re-render never re-credits a
different person.

See `docs/rendering.md` for the resolution order, the container's same-path bind
mount, the plate burn, and the matching AV1 hazard in shot detection (OpenCV
cannot decode AV1 and silently reports the whole video as a single beat).

---

## 6. Prior art

- **Shot detection:** [PySceneDetect](https://www.scenedetect.com/) (content/HSV-threshold SBD), [TransNetV2](https://github.com/soCzech/TransNetV2) (neural SBD, strong on soft transitions), [AutoShot](https://github.com/flix/AutoShot) (SBD + shot-annotation pipeline precedent).
- **Metadata standards:** [IPTC Video Metadata Hub](https://iptc.org/standards/video-metadata-hub/), [PBCore](https://pbcore.org/), [EBUCore](https://tech.ebu.ch/MetadataEbuCore), [MovieLabs Ontology for Media Creation (OMC)](https://mc.movielabs.com/) — our `source`/`confidence` stamping and inheritance-over-observation pattern follows their asset/derivative metadata models.
- **Editorial tagging:** stock-footage practice (Getty/Pond5-style mood, concept, and shot-type keywording) is the model for `mood`, `salience`, and caption-first retrieval.
- **Stand-in conventions:** film stand-in / photo-double / body-double practice — the performer substitutes for the principal when face/identity is hidden — is why `identity_visibility` and `substitutability` exist as fields at all: in Destiny the helmet does the doubling. The project no longer leans on this convention as its primary casting mechanism — most lead bindings carry no resemblance constraint at all (see `docs/taxonomy.md`'s casting section) — but it survives as more than inert vocabulary: it is the literal mechanism behind the project's one constrained binding (`saladin` → `jeefy`), whose `require_helmet` constraint is evaluated directly against `identity_visibility`.
- **On vocabularies:** there is **no standards-body canonical enum for shot scale or camera movement**. We adopt the common editorial abbreviations (ELS/LS/MLS/MS/MCU/CU/ECU; static/pan/tilt/push/handheld…) rather than inventing new terms.
