# Halo campaign — design

How [#11](https://github.com/castrojo/destiny-vids/issues/11) gets built on the
machinery in this repo. Companion docs: [`research.md`](research.md) for the
external facts, [`README.md`](README.md) for the issue map.

## 1. What the brief asks for

- A **multi-episode** campaign covering the arc of Halo: Combat Evolved, not one
  clip.
- Each episode alternates **dialogue-only beats** (radio chatter, callouts, no
  music) with **long combat movements**, each scored by **one continuous track**
  from the Wolves catalogue, switching back and forth several times.
- A **Halo CE / Halo 2-era HUD** over the footage throughout, with a callout
  snapping in as each trooper is introduced, and a closing Bazzite
  download/install call-to-action in the final beat.
- The same **template re-run** for other videos with a different cast of GitHub
  users, sourced from the contributor base of the relevant orgs.
- The **logo intro slides replaced** with org logos (nobara, bazzite, …).

## 2. What carries over, and what is Destiny-shaped

The *mechanisms* here are franchise-neutral; several of them are wired to Destiny
strings. Keep the two apart — the first column needs no work, the second is the
re-skin surface and is the reason [H-05](issues/05-universe-packs.md) is bigger
than "add a vocab folder".

| Mechanism (transfers as-is) | Why it transfers |
|---|---|
| Shot detection (`tools/annotate.py`) | Frame-difference boundaries know nothing about the fiction. |
| The clean gate (`vocab/cleanliness.yaml`, `derive.DISQUALIFYING_OVERLAYS`) | "Is something burned into this frame" is universal. |
| Cinematography, identity, register, action axes | Editorial vocabulary, not lore. |
| Story assembly (`tools/story.py`) | Beat → best distinct clean shot, no reuse, misses reported. |
| Render (`tools/render.py`) | Cut, normalize, concat. |
| Deterministic ensemble assignment (`tools/ensemble.py`) | Seeded round-robin over a contributor pool. |
| Plate *scheduling* (`plate.load_manifest_entries`) | Anchor a card, hold it long enough to read, never two at once. |

| Destiny-coupled (must be generalized or universe-scoped) | Where |
|---|---|
| Domain enums: era, activity, destination, class, element, faction, subclass | `vocab/domain.yaml`, `schema/segment.schema.json` |
| Lead cast map, and the single global path it loads from | `vocab/casting.yaml`, `derive.DEFAULT_CASTING_PATH` (`tools/derive.py:25`) |
| Search lexicon | `tools/search.py:40–164` |
| Rights note + era/destination heuristics | `tools/ingest.py:31–58` |
| `guardian_hero` as a salience *value* and as the ensemble trigger | `vocab/salience.yaml`, `derive.ENSEMBLE_SALIENCE` (`tools/derive.py:37`) |
| Hardcoded plate copy: `"CONTRIBUTOR // GUARDIAN"`, `"Project Bluefin, {month}"` | `tools/plate.py:441–445`, `:470–472` |
| `usage_class` documented as *Bungie-owned* footage | `vocab/provenance.yaml:27–32` |
| `faction` is a **hostile-only** axis ("Enemy faction(s) visible in the shot") | `schema/segment.schema.json` |

That last row is a trap worth naming now: `unsc` is not a `faction` value in this
schema's sense, because the axis means *enemy*. Halo's hostiles (`covenant`,
`flood`, …) belong there; the UNSC is the hero side and is carried by salience +
casting, exactly as Guardians are. See [H-05](issues/05-universe-packs.md).

## 3. The one decision that changes everything: where the footage comes from

#11 says "live-action" and writes its subject/setting/audio block in the shape of
a **generative video prompt**. This repo is an index of **footage that already
exists**. Those are different projects, and the difference is not cosmetic:

| | Index reading | Generation reading |
|---|---|---|
| Corpus | Official Halo footage, indexed by timecode | Clips produced from the prompt |
| `usage_class` | `third_party_copyrighted` (Microsoft) | Not third-party; the schema's `const` no longer fits |
| `clean` | Tagged from the frame, as today | Still tagged from the frame — a generated HUD is as disqualifying as a shipped one |
| Rights | Microsoft's Game Content Usage Rules | Whatever the generator's terms say, plus likeness questions |
| Repo work | H-05, H-07 | H-05, plus a new provenance class |

Everything downstream — the campaign format, the score, the HUD, the casting —
is **provenance-agnostic**. That is why the fork is isolated in H-00/H-07 and
does not thread through the rest of the plan. Nothing else is blocked on it
except the corpus.

## 4. Universe packs

### The coupling today

`vocab/domain.yaml` holds `class`, `element`, `faction`, `destination`, `era`,
`activity`, `subclass_version` — every value Destiny. `schema/segment.schema.json`
and `schema/video.schema.json` restate those enums.

AGENTS.md says "tests assert the two agree". **They do not, in general.** The
only agreement tests that exist are narrow:
`tests/test_ingest.py::test_ingested_real_records_present_and_valid` checks each
record's `era` against `vocab/domain.yaml`, and
`tests/test_search.py::test_preferred_salience_matches_the_vocab` checks one
ranking constant. The gap is already load-bearing: `vocab/domain.yaml` lists 13
`subclass_version` values (`arc_1`, `arc_2`, `solar_1`, …) and the schema's
`$defs.subclass_version` enum lists 7. A second universe multiplies that drift,
so the bidirectional test is a prerequisite of the split, not a nicety.

### The proposal

- Add `universe` (enum: `destiny`, `halo`) to the video record, **required**, and
  inherit it into segments the way `era`/`activity` already inherit
  (`annotate.INHERITABLE_FIELDS`). Make it **required on segments too**: a
  segment with no universe cannot be checked against any pack. The seven
  existing `videos/*.json` records get `universe: destiny`.
- Split the vocab: franchise-neutral axes stay at `vocab/`; the domain enums and
  the lead map move under `vocab/universes/<universe>/`.
- Keep **one union enum per field** in the schema — JSON Schema conditionals per
  universe would be unreadable and would drift from `vocab/` — and enforce
  isolation where the corpus is actually written: in
  `annotate.validate_segment()`, reject any value not in the record's own pack.
  A corpus test alone only catches what is already committed; the validator
  stops `faction: cabal` on a Halo segment at ingest time. Back it with the
  two-halved test (every pack value appears in the schema union; no record
  carries another universe's value).
- A field a universe does not use is simply **absent** — the schema only requires
  `segment_id`, `video_id`, `start_sec`, `end_sec`, `subject_salience` (plus
  `universe` once this lands).
- Generalize the Destiny strings listed in §2: a neutral salience value with
  `guardian_hero` as the Destiny pack's alias, `ENSEMBLE_SALIENCE` and
  `DEFAULT_CASTING_PATH` resolved per universe, plate copy sourced from the
  campaign's cast file rather than hardcoded, and the `usage_class` description
  reworded to name the rights-holder per record rather than Bungie globally.

### What the Halo pack fills in

| Field | Halo | Note |
|---|---|---|
| `faction` | `covenant`, `flood`, `forerunner_sentinel`, `unknown` | The axis means **enemy** faction ("Enemy faction(s) visible in the shot"). The UNSC is the hero side: it is carried by salience and casting, not by `faction`. Adding `unsc` here would quietly invert the meaning of every `faction` query. |
| `destination` | The CE mission locations — `pillar_of_autumn`, `alpha_halo_surface`, `truth_and_reconciliation`, `silent_cartographer`, `control_room`, `the_library`, `the_maw`, `orbit_space`, `unknown` | Names taken from the mission list in [`research.md`](research.md#4-halo-combat-evolved-campaign-arc), not invented. |
| `era` | `halo_ce`, `halo_ce_anniversary`, `halo_2`, `halo_2_anniversary`, `unknown` | Which release the footage is *from*, which is also the HUD-era tell. |
| `activity` | `campaign_mission`, `cinematic`, `unknown` | |
| `subject_salience` | `guardian_hero` → a neutral `hero_figure` with per-pack display copy | The value name is the one place the "Destiny-neutral" axes are not neutral. |
| `class`, `element`, `subclass_version` | **not used** | Halo has no player classes, damage elements, or subclass versions. Do not map them onto armour colours or weapon types; an empty field is honest and a wrong one is not. |

## 5. Casting

Three named roles, and a squad.

| Role | Handle | Binding shape |
|---|---|---|
| John 17 | `KyleGospo` | No blanket `require_helmet`: #11 opens with the helmet **under his arm** and has him pull it on. Constrain per beat, not per binding — see below. |
| Sgt. Johnson | `bketelsen` | Unconstrained. |
| The second veteran on the heavy weapon | `GloriousEggroll` | #11 gives no canon name. Key the binding on the description — `iron_lord_red_haired` is the precedent for a character the project casts before it can name. |
| The squad | contributors of the named orgs | Ensemble slots, filled by `tools/ensemble.py`, never tagged by hand. |

Three things that are not details:

- **A helmet constraint on the binding would exclude the brief's own opening
  shot.** The `saladin` precedent constrains a character who is *never* helmeted;
  John 17 is helmeted for most of the campaign but demonstrably not at the start.
  Model it as two beat-level filters (`helmet_simplicity`/`identity_visibility`
  in the outline) over one binding, so "helmet off, breathing hard" and "visor
  down, advancing" can both cast.
- **Rule 3 applies harder here than in Destiny.** A helmeted trooper is
  `character_identifiability: implied_by_costume` by default. Tag `character`
  only for the three leads, and only where they are visibly in frame. Everyone
  else is an ensemble slot, which is the honest answer.
- **Handles are not display copy.** #11 writes `kylegospo`; GitHub's canonical
  login is `KyleGospo`, and neither is necessarily how the person wants to be
  named on screen. On-screen copy is a closed set authored by the owner
  (`docs/skills/plates.md`), so the callout deck gets its strings from the cast
  file, not from a handle string manipulated at render time. Same for "John 17",
  which is the brief's spelling and is carried verbatim rather than corrected.

### Where a cast lives, and why that is not the pack

A universe pack and a cast are different lifetimes, and #11 needs them separated
to be re-runnable at all. The pack is stable (Halo has one Sgt. Johnson); the
cast changes every run (a different org's contributors).

- The **pack** defines *roles*: character ids, aliases, per-role constraints.
- The **cast file** (`casts/<name>.yaml`, [H-12](issues/12-reusable-campaign-template.md))
  binds a role to a person and to that run's authored on-screen copy.

The wrinkle to design around: `casting.person` today is *derived and stored on
every segment* by `tools/derive.py`, and search and plates read the stored value.
Swapping a cast file therefore does not recast an already-assembled corpus.
Either re-run derive per campaign (it is the only writer, so this stays legal
under "never hand-edit derived fields") or resolve casting at assembly time from
the run's cast file and stop storing the person on the segment. Pick one in
[H-12](issues/12-reusable-campaign-template.md); do not ship both.

## 6. The campaign format

A campaign is a list of episodes; an episode is a list of **movements**; a
movement is either `dialogue` or `combat`.

```jsonc
{
  "campaign_id": "halo-ce-ogc",
  "universe": "halo",
  "cast": "casts/open-gaming-collective.yaml",
  "episodes": [
    {
      "episode": 1,
      "title": "The Pillar of Autumn",
      "movements": [
        {"kind": "dialogue", "audio": "source", "beats": ["..."]},
        {"kind": "combat", "track": "wolves:<track_id>", "beats": ["..."]},
        {"kind": "dialogue", "audio": "source", "beats": ["..."]},
        {"kind": "combat", "track": "wolves:<track_id>", "beats": ["..."]}
      ]
    }
  ]
}
```

Rules the format enforces, each because of something that would otherwise go
wrong:

- **One track per combat movement.** "Scored by its own song" is the brief. A
  movement that needs two tracks is two movements.
- **Strict alternation, and at least two switches per episode.** The brief asks
  for "switching back and forth multiple times". Validate *adjacency* — no two
  consecutive movements of the same kind — not just a count, or four dialogue
  movements followed by two combat movements passes while reading nothing like
  the brief.
- **Shot uniqueness spans the campaign, not the episode.** `story.py` already
  refuses to reuse a shot within one cut; across six episodes the same rule has
  to hold, or episode 5 replays episode 1 and the whole thing reads as stock.
  This is not free: `build_story()` owns a fresh local `used` set
  (`tools/story.py:100–136`), so campaign-wide uniqueness needs the matcher to
  accept shared state — see §7 and [H-09](issues/09-campaign-episode-format.md).
- **Unmatched beats are reported per movement and never dropped** — the existing
  behaviour, carried up a level.
- **Tracks are referenced, never stored.** Music gets the same posture as
  footage: `media/` and the catalogue live outside the repo, and the campaign
  file holds an id and a duration.

## 7. Scored assembly and the audio plan

Three gaps between what `render.py` does and what the brief needs.

**Gap 1 — one bed, whole file.** `render.py --audio` maps a single external
track over the concatenated video with `-shortest` (`tools/render.py:158–181`),
and source audio is dropped entirely when a bed is given. The campaign needs
source audio *on the dialogue movements* and a track *on the combat movements*.

Recommended shape: render each movement through the existing path (it already
produces a normalized intermediate), attach that movement's bed there, then
concat the movements. The filter graph stays small and debuggable, and one
movement can be re-rendered without redoing the episode.

Two constraints that shape must respect, both from how the concat demuxer works:

- **Every movement must come out with identical stream parameters.** `cut_clip`
  normalizes audio to AAC 48 kHz stereo *only when `keep_audio` is true* and
  emits `-an` otherwise (`tools/render.py:150–154`), and `concat()` re-encodes an
  external bed without forcing its rate or channel count. A muted dialogue clip
  or a 44.1 kHz mono track therefore produces movements the demuxer cannot join.
  Force AAC 48 kHz stereo on every movement, and insert `anullsrc` silence where
  a source clip has no audio at all.
- **The concat demuxer cannot crossfade.** `acrossfade` at movement boundaries
  needs a filter-graph pass over the joined audio (or a final `filter_complex`).
  Hard cuts at boundaries are a legitimate simpler answer; pick one in
  [H-10](issues/10-scored-assembly-and-audio-plan.md) rather than assuming the
  existing concat path gives crossfades for free.

**Gap 2 — one shot per beat.** `story.py` casts each beat to exactly one shot,
so an episode's length is whatever the shots happen to add up to. A combat
movement has to fill *the track's* duration. Add a fill mode: keep casting from
the movement's beat pattern until the target duration is met, honouring
no-reuse, and **report the shortfall** when the clean pool runs out rather than
looping footage. A movement that cannot be filled is a beat to rewrite (rule 2),
not a gate to widen. Note that `build_story()` is duration-blind today (it takes
the beat's duration or the whole source span) and caps nothing, so the fill loop
has to budget the *capped* duration of each pick and trim only the last one.
Twelve full-track movements is a large ask of the pool: do a capacity check
against the corpus before committing to campaign-wide uniqueness.

**Gap 3 — "dialogue, no music" is a property of the source, not of the render.**
Keeping source audio does not guarantee radio chatter without score: published
footage frequently has music baked in, and the tagger works from keyframes
(`tools/annotate.py:165–181`), so nothing in the index currently knows whether a
shot's audio is speech, score, or both. Either tag an audio axis (speech present
/ music present) during annotation, or take owner-supplied dialogue stems. Decide
in [H-10](issues/10-scored-assembly-and-audio-plan.md); a dialogue movement built
from music-bearing clips is the failure mode this catches.

**Footage tier is an editorial choice, not a fallback.** `story.py` treats
`clean` as THE gate and gameplay as opt-in coverage (`--allow-gameplay`). Clean
gameplay is valid coverage under the repo contract; a Halo campaign may well
*want* it. Decide it upfront in the campaign template and record it there —
reaching for it mid-render because a movement came up short is the thing to
avoid, not the flag itself.

## 8. The HUD layer

### What it is

`tools/hud.py`, with `plan | render | burn` mirroring `tools/plate.py`, because
the plate tool already solved the hard parts: transparent PNGs at frame size,
one ffmpeg pass with an `overlay` chain (`plate.burn`, `tools/plate.py:527–569`),
`enable='between(t,…)'` windows, and a refusal to let two cards share the screen
(`plate.load_manifest_entries`, `tools/plate.py:492–513`).

Two differences from plates:

- **The chrome is continuous.** The visor frame, motion tracker, shield/ammo
  block and corner readout ride the whole episode: composite them with
  `overlay=0:0` and *no* `enable` guard, from a PNG sequence for the animated
  parts (tracker sweep, ticking readout) and a still for the static frame.
- **The treatment is a filter, not an image.** Scan-line flicker and chromatic
  fringing are ffmpeg filters applied once at burn time, not baked into the PNGs.

### What it must look like

CE-era, per [`research.md`](research.md#3-halo-ce--halo-2-era-hud-design-language):
motion tracker **lower left**, shield **upper centre**, ammo and grenades
**upper right**, centre reticle, waypoint markers at the screen edge. Dropping
the health bar and keeping only shields reads as Halo 2; keeping both reads as
CE. Rounded chrome and Forerunner gold read as Halo 4 and are wrong for this.

Two conflicts to settle before rendering, both in H-11:

- #11 asks for **military green**; the CE/2 HUD is **translucent blue-cyan**.
  The brief and the canon disagree, and "keep it canon" is also in the brief.
- The era's typeface is **Handel Gothic**, which is a commercial font. Nothing
  proprietary gets bundled; the tool picks from installed candidates and fails
  loudly when none is present, which is what `plate.py`'s `FONT_CANDIDATES`
  already does.

### What it must not do

- **It never makes unclean footage usable.** `overlays: hud` on a *source*
  segment still derives `clean = false`. Our HUD is composited at render time
  over shots that passed the gate; a shipped HUD in the source is a different
  thing that no edit removes.
- **A rendered episode is not re-ingestable.** Once the HUD is burned, the file
  is unclean by this index's own definition. Keep the pre-HUD render if anything
  downstream wants to re-cut.
- **It never invents copy.** Callout fields are a closed set in the universe
  pack, exactly like the nameplate deck, and the closing Bazzite CTA is authored
  text — including the URL — not a string an agent composes at render time.
- **It never puts two names on screen at once.** The chrome is continuous, so it
  *does* share the screen with plates — a card over the visor frame is the
  intended look. What must be mutually exclusive is the name-bearing layer: a
  trooper callout, the CTA, and a plate are three ways of captioning the same
  frame. `plate.load_manifest_entries` refuses overlapping plate windows today
  and knows nothing about HUD manifests, so one scheduler has to own the
  name-bearing timeline across both tools.

## 9. The intro slides

#11's last line: *"Replace the logo intro slides with logos from nobara, bazzite,
etc."* This is plate work, not HUD work — a title card deck at the head of each
episode — but it is the one requirement in the brief that needs assets the repo
has never handled.

- **A logo is a trademark, and trademarks are not covered by anything above.**
  Bungie's fan-content policy and Microsoft's GCUR are about *game* content. An
  org's logo is that project's mark, used with its permission and to its brand
  guidelines. Every logo needs a named source and a permission basis recorded
  next to it, the same way footage carries `source_rights_note`.
- **Which orgs?** The same corrected list as the cast
  ([H-04](issues/04-cast-and-org-list-corrections.md)) — and the correction
  matters more here, because a slide is a claim about who made this.
- **Where do the files live?** Logos are binary assets. `media/` is gitignored,
  and vendoring third-party marks into the repo is a rights decision, not a
  convenience one. Default to referencing them like footage: a manifest with a
  URL, a checksum and a permission note, fetched at render time.
- **What it must not do.** No recolouring a mark into HUD green, no compositing
  it into the visor frame, no invented tagline under it. Marks are used as
  given, and the on-screen copy stays a closed authored set.

Scoped in [H-14](issues/14-org-logo-intro-slides.md).

## 10. Re-running the template with a different cast


The brief wants the same structure re-run for other videos with different
people. Split what varies from what does not:

| Varies | Fixed |
|---|---|
| `casts/<name>.yaml` — the lead bindings and the org list | The campaign template: episodes, movement kinds, beat patterns |
| The corpus (`--dir segments`, filtered by `universe`) | The HUD deck and its copy fields |
| The catalogue's track assignment | The rules: alternation, one track per combat movement, no reuse |

`tools/campaign.py --template … --cast …` is then the whole re-run interface, and
the determinism requirement from `ensemble.py` extends to it: the same
(template, cast, roster month, corpus) must produce byte-identical cut lists and
manifests, or a re-render silently re-credits people.

## 11. Rights posture

Destiny footage sits under Bungie's fan-content policy; Halo footage sits under
**Microsoft's Game Content Usage Rules**, which are a different document with
different terms — including a required attribution string and a licence grant
back to Microsoft. See [`research.md`](research.md#1-rights).

Repo consequences, all in H-03:

- `tools/ingest.py:31` hardcodes the Bungie note into every record. It becomes
  per-universe.
- `schema/video.schema.json` describes `source_rights_note` as a Bungie
  statement; the description generalizes. `usage_class: third_party_copyrighted`
  still fits Halo footage under the index reading.
- `AGENTS.md`'s Rights section names Bungie only, and needs the second clause.

**Music is the sharp edge.** The GCUR covers game footage; it does not grant
rights to use soundtrack recordings as standalone audio. Scoring these episodes
with the Halo OST is therefore *not* something this repo's own rights posture
supports, while scoring them from the owner-supplied Wolves catalogue is exactly
what the body of #11 describes. That is the recommendation H-02 asks the owner to
confirm — the brief contains both instructions and only one of them survives
contact with the policy.

## 12. Proposed episode map (draft)

Six episodes over the ten CE missions. This is a **draft that the footage gets to
veto**: it is written before the corpus exists, so every beat in it is a
hypothesis, and rule 2 says the outline changes when the shots disagree.

| Ep | Missions | Shape |
|---|---|---|
| 1 | The Pillar of Autumn | dialogue (wake-up, orders) → combat → dialogue (evacuate) → combat (escape pods) |
| 2 | Halo; Truth and Reconciliation | dialogue (regroup on the ring) → combat (surface) → dialogue (night raid brief) → combat (boarding) |
| 3 | The Silent Cartographer | dialogue (beach landing) → combat (island) → dialogue (map room) → combat (extraction) |
| 4 | Assault on the Control Room | dialogue (approach) → combat (canyon) → dialogue → combat (interior push) |
| 5 | 343 Guilty Spark; The Library | dialogue (swamp, distress signal) → combat (first Flood contact) → dialogue (the Monitor) → combat (the stacks) |
| 6 | Two Betrayals; Keyes; The Maw | dialogue (the betrayal) → combat → dialogue (Keyes) → combat (the reactor run) → **CTA beat** |

That is twelve combat movements, so the catalogue has to supply twelve tracks
before assembly can start (H-02). Every episode alternates strictly, which is the
rule §6 validates rather than a coincidence of this draft. Each one opens with the
org logo deck (H-14); the closing CTA is the final beat of episode 6, where the
HUD resolves into the Bazzite download callout. Assembling all of it is
[H-15](issues/15-deliver-the-campaign.md) — the plan's only deliverable that is a
movie rather than a capability.

## 13. Deliberately not planned here

- Shipping footage or music. `media/`, `renders/` and `*.mp4` stay gitignored;
  the catalogue is referenced by id.
- Monetization, uploading, or disputing Content ID claims.
- Generating the footage, if H-00 lands on the generation reading — that is a
  different tool with a different provenance model, and this plan's campaign,
  score, HUD and casting layers sit on top of it either way.
- Any universe beyond `destiny` and `halo`. The pack mechanism is general; the
  plan does not speculate about a third.
