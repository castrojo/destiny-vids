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

## 2. What carries over unchanged

Most of this repo is not about Destiny at all. These stages are franchise-neutral
and need no work:

| Stage | Why it transfers |
|---|---|
| Shot detection (`tools/annotate.py`) | Frame-difference boundaries know nothing about the fiction. |
| The clean gate (`vocab/cleanliness.yaml`, `tools/derive.py`) | "Is something burned into this frame" is universal. |
| Cinematography, identity, salience, register, action axes | Editorial vocabulary, not lore. |
| Story assembly (`tools/story.py`) | Beat → best distinct clean shot, no reuse, misses reported. |
| Render (`tools/render.py`) | Cut, re-encode, concat. |
| Deterministic ensemble assignment (`tools/ensemble.py`) | Month-seeded round-robin over a contributor pool. |
| Plate scheduling (`tools/plate.py`) | Anchor a card to a shot, hold it long enough to read, never two at once. |

What is Destiny-shaped is narrow and enumerable: `vocab/domain.yaml`, the lead
map in `vocab/casting.yaml`, the hardcoded lexicon in `tools/search.py`
(`CLASS`/`ELEMENT`/`FACTION`/`DESTINATION`/`PHRASES`, lines 40–164), and
`tools/ingest.py`'s `RIGHTS_NOTE` + `ERA_RULES` (lines 31–58). That list is the
whole re-skin surface.

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
and `schema/video.schema.json` restate those enums, and the tests assert the two
agree (`tests/test_ingest.py::test_ingested_real_records_present_and_valid`
checks each record's `era` against `vocab/domain.yaml`).

### The proposal

- Add `universe` (enum: `destiny`, `halo`) to the video record, **required**, and
  inherit it into segments the way `era`/`activity` already inherit. The seven
  existing `videos/*.json` records get `universe: destiny`.
- Split the vocab: franchise-neutral axes stay at `vocab/`; the domain enums and
  the lead map move under `vocab/universes/<universe>/`.
- Keep **one union enum per field** in the schema, and add a test with two
  halves: every universe pack's values appear in the schema union, and no record
  carries a value from a universe other than its own. This keeps
  `vocab/` as the single source of truth without conditional schema branching,
  and keeps the existing "vocab and schema agree" contract intact.
- A field a universe does not use is simply **absent** — the schema only requires
  `segment_id`, `video_id`, `start_sec`, `end_sec`, `subject_salience`.

### What the Halo pack fills in

| Field | Halo | Note |
|---|---|---|
| `faction` | `unsc`, `covenant`, `flood`, `forerunner_sentinel`, `unknown` | The Destiny factions do not appear in Halo records, and vice versa. |
| `destination` | The CE mission locations — `pillar_of_autumn`, `alpha_halo_surface`, `truth_and_reconciliation`, `silent_cartographer`, `control_room`, `the_library`, `the_maw`, `orbit_space`, `unknown` | Names taken from the mission list in [`research.md`](research.md#4-halo-combat-evolved-campaign-arc), not invented. |
| `era` | `halo_ce`, `halo_ce_anniversary`, `halo_2`, `halo_2_anniversary`, `unknown` | Which release the footage is *from*, which is also the HUD-era tell. |
| `activity` | `campaign_mission`, `cinematic`, `unknown` | |
| `class`, `element`, `subclass_version` | **not used** | Halo has no player classes, damage elements, or subclass versions. Do not map them onto armour colours or weapon types; an empty field is honest and a wrong one is not. |

## 5. Casting

Three named roles, and a squad.

| Role | Handle | Binding shape |
|---|---|---|
| John 17 | `KyleGospo` | `constraints: {require_helmet: true}` — the character is defined by never taking the helmet off, so a face-clear shot is not him. Exactly the `saladin` precedent, for the opposite reason. |
| Sgt. Johnson | `bketelsen` | Unconstrained. |
| The second veteran on the heavy weapon | `GloriousEggroll` | #11 gives no canon name. Key the binding on the description — `iron_lord_red_haired` is the precedent for a character the project casts before it can name. |
| The squad | contributors of the named orgs | Ensemble slots, filled by `tools/ensemble.py`, never tagged by hand. |

Two things that are not details:

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
- **At least two switches per episode.** The brief asks for the alternation
  explicitly; a validator is cheaper than noticing in the render.
- **Shot uniqueness spans the campaign, not the episode.** `story.py` already
  refuses to reuse a shot within one cut; across six episodes the same rule has
  to hold, or episode 5 replays episode 1 and the whole thing reads as stock.
- **Unmatched beats are reported per movement and never dropped** — the existing
  behaviour, carried up a level.
- **Tracks are referenced, never stored.** Music gets the same posture as
  footage: `media/` and the catalogue live outside the repo, and the campaign
  file holds an id and a duration.

## 7. Scored assembly and the audio plan

Two gaps between what `render.py` does and what the brief needs.

**Gap 1 — one bed, whole file.** `render.py --audio` maps a single external
track over the concatenated video with `-shortest` (`tools/render.py:158–181`),
and source audio is dropped entirely when a bed is given. The campaign needs
source audio *on the dialogue movements* and a track *on the combat movements*.

Recommended shape: render each movement through the existing path (it already
produces a normalized intermediate), attach that movement's bed there, then
concat the movements. The filter graph stays small and debuggable, one movement
can be re-rendered without redoing the episode, and `acrossfade` at the movement
boundary is where the music is supposed to breathe anyway. A single
`filter_complex` spanning an episode is the alternative and is much harder to
read when it goes wrong.

**Gap 2 — one shot per beat.** `story.py` casts each beat to exactly one shot,
so an episode's length is whatever the shots happen to add up to. A combat
movement has to fill *the track's* duration. Add a fill mode: keep casting from
the movement's beat pattern until the target duration is met, honouring
no-reuse, and **report the shortfall** when the clean pool runs out rather than
looping footage or reaching for `--allow-gameplay`. A movement that cannot be
filled is a beat to rewrite (rule 2), not a gate to widen.

## 8. The HUD layer

### What it is

`tools/hud.py`, with `plan | render | burn` mirroring `tools/plate.py`, because
the plate tool already solved the hard parts: transparent PNGs at frame size,
one ffmpeg pass with an `overlay` chain, `enable='between(t,…)'` windows, and a
refusal to let two cards share the screen (`tools/plate.py:527–569`).

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
- **It never shares the screen with a plate.** `plate.py` refuses overlapping
  windows today; with two overlay tools, one scheduler owns the timeline or two
  names end up on screen at once.

## 9. Re-running the template with a different cast

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

## 10. Rights posture

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

## 11. Proposed episode map (draft)

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
before assembly can start (H-02). The closing CTA is the final beat of episode 6,
where the HUD resolves into the Bazzite download callout.

## 12. Deliberately not planned here

- Shipping footage or music. `media/`, `renders/` and `*.mp4` stay gitignored;
  the catalogue is referenced by id.
- Monetization, uploading, or disputing Content ID claims.
- Generating the footage, if H-00 lands on the generation reading — that is a
  different tool with a different provenance model, and this plan's campaign,
  score, HUD and casting layers sit on top of it either way.
- Any universe beyond `destiny` and `halo`. The pack mechanism is general; the
  plan does not speculate about a third.
