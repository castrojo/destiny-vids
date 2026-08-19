# Taxonomy reference

Axis-by-axis reference for the Destiny 2 shot index. Enum values are canonical in
`vocab/*.yaml`; this document explains **intent, edge cases, and how each field is
meant to be filled and queried**. Assumes familiarity with Destiny and editing.

Every tagged field carries provenance: `{source: inherited|observed,
label_source: manual|heuristic|model, confidence: 0..1}`. "Inherited" means copied
from the parent video's defaults; "observed" means read from this segment's own
frames/audio.

---

## Axis A — Cleanliness (`vocab/cleanliness.yaml`)

The project's **primary gate**, ahead of every other axis in this document. The
operative question for any shot is *"is this frame clean enough to cut into a
sequence at all?"* — not *"can our performer stand in for this Guardian?"*
(identity/substitutability, Axis D). The fiction bends to the footage: the
story gets written to fit the best available shots, not the other way round, so
a shot's editorial merit is moot if it physically cannot be cut in.

- **`overlays`** (multi, observed): `hud, nameplates, burned_text, talking_head,
  letterbox, none`. Overlays burned into the frame — nothing an edit can remove.
  Tag `[]` or `["none"]` for a frame with nothing burned in.
- **`disqualifying_overlays`**: `{hud, nameplates, burned_text, talking_head}`.
  `letterbox` is **deliberately excluded** — pillarbox/letterbox bars can be
  cropped in the edit, so it's a warning, not a veto.
- **`clean`** (derived boolean) = `overlays` contains none of the disqualifying
  four. **The critical subtlety:** an absent/untagged `overlays` derives
  `clean = false`, **not** true. Cleanliness must be *positively established* —
  guessing clean on an untagged shot is how a HUD ends up in the finished cut.
  An explicitly empty list, or `["none"]`, is clean.
- **`footage_tier`** (derived enum) — `content_type` in `{cinematic, cutscene}` →
  `cinematic`; `content_type == gameplay` → `gameplay`; anything else (`trailer`,
  `UNKNOWN`, absent) → `mixed`. Gameplay is **kept**, not dropped: it's ranked
  beneath cinematics as B-roll/coverage, so a cut defaults to the cinematic look
  and falls back to gameplay for coverage.

**`clean` and `footage_tier` are independent axes — don't conflate them.** Clean
gameplay (HUD off, e.g. a photo-mode-style capture) is perfectly usable. Going
the other way, a pre-rendered *cinematic* with a burned-in title/date card is
**not** clean and is excluded regardless of how good the shot is —
`examples/lightfall-title-card-unclean.json` is exactly this case: gorgeous
Neomuna skyline, `footage_tier: cinematic`, `clean: false` because of the
`burned_text` overlay. `examples/hunter-arc-pvp.json` is the mirror case: a
`gameplay`-tier shot with `overlays: [hud, nameplates]`, unclean for an
unrelated reason (the HUD, not the tier).

`clean` is the dominant term in the retrieval ranking — bigger than every other
signal combined (see `docs/agent-retrieval.md`) — and it is a hard prerequisite
for `tools/story.py`, which never puts an unclean shot in a cut. `tools/search.py`
excludes unclean shots from its result pool by default; pass `--include-unclean`
to surface them anyway, heavily penalized, for triage.

---

## Axis B — Domain semantics (`vocab/domain.yaml`)

The **observed vs inherited split** is the important design move.

| Field | Observed / Inherited | Notes |
|---|---|---|
| `class` | observed | `{titan, hunter, warlock, unknown}`. Gameplay frequently hides class — honor `unknown`, don't guess. |
| `element` | observed | `{arc, solar, void, stasis, strand, prismatic, unknown}`. The **visual** signal (Arc = blue lightning) and era-independent. |
| `faction` | observed, multi | Enemies **present** in frame. Presence ≠ subject — see salience. |
| `destination` | observed | Where the shot is. Orthogonal to `era` (same place recurs across expansions). |
| `character` | observed, entity list | Free-text `{name, kind}`, **not** an enum — too open-ended (Zavala, Cayde-6, Savathûn…). |
| `era` | inherited | Expansion/era from the video's release/playlist. |
| `activity` | inherited | `{cinematic, patrol, strike, raid, crucible_pvp, gambit, dungeon, story_mission, unknown}`. Usually derivable from playlist/title. |
| `subclass_version` | inherited | Arc 2.0 vs 3.0 etc. **Never frame-visible** — a lore-timeline fact derived from `era`. |

**Why the split matters.** A flash model can see "blue Arc VFX" but cannot know if
it's Arc 2.0 or Arc 3.0 — that's a function of *when the video shipped*. Tagging the
observable (`element`) from pixels and the timeline-dependent (`subclass_version`)
from `era` dissolves the "subclass reworks across eras" problem, and keeping
`destination` and `era` orthogonal dissolves the "same location, different
expansion" problem.

---

## Axis C — Cinematography (`vocab/cinematography.yaml`)

Separate axes, never one overloaded `shot_type`.

- `shot_scale`: `ELS, LS, MLS, MS, MCU, CU, ECU, INSERT, UNKNOWN`.
- `composition` (multi): `establishing, single, two_shot, group, crowd, OTS, POV,
  cutaway`. `crowd` sits above `group` — a mass of subjects too many to count
  individually — and it's the largest ensemble slot in the casting model below
  (Axis D): a `crowd` shot seats up to 6 contributor tiles versus 3 for `group`.
- `camera_movement` (multi): `static, pan, tilt, push_in, pull_out, track,
  handheld_shaky, orbit, crane, UNKNOWN`. **Deliberately coarse** — dolly vs zoom vs
  track are not cheaply distinguishable, so they're collapsed. `handheld_shaky`
  doubles as the "too shaky for a hero shot" signal.
- `pacing`: `slow, medium, fast, UNKNOWN`.
- `content_type`: `cinematic, gameplay, cutscene, trailer, UNKNOWN`.
- `lighting`: `bright, dim, high_contrast, silhouette, UNKNOWN`.

Use `UNKNOWN`/`unknown` rather than forcing a bad label. There is no standards-body
canonical enum for scale or movement; these are the common editorial abbreviations.

---

## Axis D — Identity / substitutability (`vocab/identity.yaml`) — refinement

The anonymity axis, and a secondary one. The anonymous crowd is cast from a
rotating pool of contributors, so anonymity is not a scarce resource and
`substitutability` is not a retrieval filter. What it carries:

- **`substitutability`** — ordinal `0..5`. `0` = clear, identifiable face,
  named/recognizable character, not substitutable; `5` = fully anonymous
  (helmet on, face away/obscured, small in frame, or only armor/hands/weapon
  visible). **Now a tie-breaker only, not a general usability gate**: for
  *ensemble* shots it decides between two otherwise-equal clean candidates
  which one reads more comfortably as "could be anyone" — it does not decide
  whether an ensemble shot is usable. A face-clear **lead** shot is normally
  fully usable at `0` regardless of substitutability (see
  `examples/elsie-bray-hero.json`, `substitutability: 1`) — the one exception
  being a *constrained* lead binding, where usability is instead gated by
  `identity_visibility`/`shot_scale` against that binding's `constraints`, not
  by substitutability either (see the `casting` section below). It is also no
  longer part of the `traversal_hero` derivation (Axis G).
- `identity_visibility`: `face_clear, partial_face, face_obscured, back_only,
  silhouette, none`.
- `character_identifiability`: `explicit, inferred, implied_by_costume, unidentifiable`.
- `face_count` (int) and `subject_facing_camera` (bool|null) — evidence.

**Independent of shot scale.** A `CU` on a *face-obscured helmet* is
high-substitutability despite being tight (see `examples/titan-helmet-cu.json`,
`substitutability: 4`). Do not proxy this axis with "wide" — related, not identical.

### `casting` — lead / ensemble (`vocab/casting.yaml`)

Derived object. Anonymity is not scarce and a resemblance constraint is the
rare exception rather than the default: Bungie's cinematics already tell a good
story, so the project simply **assigns names to the cast that is on screen**.
Two tiers, and the difference between them is the whole model:

- **`lead`** — a named Destiny NPC bound **1:1** to one real person, fixed for
  the life of the project. Bindings are **usually unconstrained**: naming a
  role does not require a lookalike, so most leads are usable at **any** shot
  scale — the project names a role, it does not composite a face. **Exactly
  one binding is constrained: `saladin` → `jeefy`.** jeefy plays the Iron Lord
  but does not resemble Saladin, so the framing has to do the work instead: a
  `leads` entry may carry `constraints` (`require_helmet`, `require_far` — see
  below), and when the character is on screen but the shot violates them,
  `role` stays `lead` while `usable` derives `false` and `constraints_failed`
  lists the unmet keys. A tight, face-clear Saladin
  (`examples/saladin-blocked-cu.json`: `MCU`, `constraints_failed:
  [require_far]`) is therefore *excluded* from Saladin's retrieval entirely;
  the far, helmeted shot (`examples/saladin-wide.json`: `LS`, `usable: true`)
  is the one that actually stands in for him. There is enough far/helmeted
  footage for this to be a real cast rather than a compromise — constraints
  exist only where the project still wants the figure to read as the
  character rather than as the person, which is why this is the exception and
  not the rule.
- **`ensemble`** — every anonymous Guardian in frame is a **slot**, filled from
  a rotating monthly pool of Project Bluefin contributors. The nameless-Guardian
  crowd is the project's diverse cast, not a stand-in problem, and it gets
  filled with real people. Slots are **derived, not tagged** (see below), and
  `casting.person` is always `null` for ensemble at index time — people are
  assigned per calendar month by `tools/ensemble.py`, so a rotating pool never
  invalidates a tagged segment. Ensemble casting is always `usable: true`,
  `constraints_failed: []` — the constraint mechanism only exists for leads.
- **`none`** — nobody to cast: environment, enemy, or artifact shots. Always
  `usable: false`, `constraints_failed: []`.

**The lead bindings live in `vocab/casting.yaml`, under `leads`** — open and
extensible. They are deliberately **not** copied here: every row names a real
person, and a stale copy is a wrong credit waiting to be read by somebody who
trusted the doc over the vocab.

Notes on a few of the bindings: `anna_bray` is Elsie's sister — the Bray line is the
project's through-thread, so both sisters are cast. `saint_14` carries a
`note` field ("Kat from now on, but she remains the bubble in the original
Wolves") — that's a standing direction for the humans doing the edit, not a
derivation input; the field is free text and `compute_casting` never reads it.
`iron_lord_red_haired` is the red-haired Iron Lord who dies in the *Rise of
Iron* intro — her canonical Destiny name is unconfirmed, so the key is
descriptive on purpose and should be renamed (with the old id kept in `aka`)
once she's identified. `nimbatus` is the same *person* as `elsie_bray`
(Laura Santamaria) under a **redaction** (#103): the programme reveals her real
name on act VII's Guardian card, so every earlier act credits her as NIMBATUS.
The binding carries her verified login (`nimbinatus` — *not* the unrelated
`nimbatus` account) and deliberately **no `plate` block**: her authored identity
lives on `elsie_bray`, its name row is the redacted string itself, and no
Nimbatus plate copy has been authored — so a plate pass over a pre-reveal
appearance reports `no_plate_copy` instead of printing her real name. `sagira`
is the one binding that is **not a Guardian** —
she is Osiris's Ghost, so no framing or helmet question applies and she is cast
on presence in frame alone; her nameplate accordingly carries no subclass line.

A binding may also carry an optional `plate` block: the on-screen nameplate copy
in the same four-field form as the reference deck (`label`, `class`, `name`,
`title`, plus `trustee` for the silver chrome). Keeping it beside the
character→person binding is what stops the credit and the casting from drifting
apart — recast a role and the plate follows, with no other edit. Derivation
never reads it; `tools/plate.py` does.

Which bindings carry one is the vocab's own fact — count the `plate:` blocks in
`vocab/casting.yaml`, never a prose count here. Their copy is **reproduced
verbatim** from sources this repo does not own (`~/Videos/nameplates.json`, the
website's `public/wolves/characters/characters.json`, or the issue that authored
the identity); none of it is written here. `sagira` is the exception shape: the
documented unknown-seal fallback (`title: Bluefin Blueberry`), not an authored
identity. Which source wins, who else has an authored identity, and where two
sources disagree is [`docs/skills/plates/SKILL.md`](skills/plates/SKILL.md).

Querying either half of a binding retrieves the same footage — "Zavala" and
"Kelsey" are the same lead, so both resolve to it. Alongside these, `leads`
also carries a set of **written-but-not-yet-cast** roles with `person: null`:
`ikora_rey`, `the_drifter`, `crow`, `caiatl`, `eris_morn`, `shaxx`, `ghost`,
`savathun`, `the_witness`. Retrieval still identifies the character for these —
the credit tile just has no name on it yet.

**Ensemble slots** are a pure function of composition/salience, never hand-tagged:
`composition` contains `crowd` → `6`; `composition` contains `group`, or
`subject_salience == crowd_group` → `3`; otherwise → `1`. The pool itself is
built and assigned by `tools/ensemble.py`: `roster --month YYYY-MM` collects
that month's Project Bluefin contributors, and `assign` deterministically walks
a shot list in timeline order, round-robining the sorted roster into every
ensemble slot so a re-render never reshuffles who played whom.

**The derived `casting` object** is exactly (`schema/segment.schema.json`
`$defs/casting`): `{role: "lead"|"ensemble"|"none", character: string|null,
person: string|null, usable: boolean, constraints_failed: array of string,
slots: integer}`. `usable` and `constraints_failed` are how the one constrained
binding blocks a shot from that character's retrieval.

**Derivation** (deterministic, `label_source = heuristic`), applied in order:

1. Normalize each `character[].name` to snake_case; if any matches a `leads`
   key or its `aka` list → `role = lead`, `character` = the canonical key,
   `person` = that binding's person (may be `null` if uncast), `slots = 0`.
   If the binding carries `constraints`, evaluate them against the shot:
   `require_helmet` fails unless `identity_visibility` is one of
   `face_obscured, back_only, silhouette, none`; `require_far` fails unless
   `shot_scale` is in `{ELS, LS, MLS, MS}`. `usable` = nothing failed;
   `constraints_failed` = the sorted unmet keys. Unconstrained bindings are
   always `usable = true`, `constraints_failed = []`.
2. Else if `subject_salience` is `guardian_hero` or `crowd_group` →
   `role = ensemble`, `character = null`, `person = null`, `usable = true`,
   `constraints_failed = []`, `slots` per the crowd/group/solo formula above.
3. Else → `role = none`, `character = null`, `person = null`, `usable = false`,
   `constraints_failed = []`, `slots = 0`.

**Retrieval consequence of `usable = false`:** a query or story beat that names
a *blocked* character gets nothing from that shot at all — `tools/search.py`'s
`matches_filter` refuses to match a `casting.person`/`casting.character` facet
when `casting.usable` is `False`, so the shot never even enters that
character's candidate pool (relaxing other filters, e.g. `shot_scale`, cannot
rescue it — the exclusion happens on the casting facet itself, independent of
scale). `tools/story.py` goes one step further and refuses a `usable: false`
lead shot for *any* beat, not just ones that name the character, since a shot
that doesn't read as its own binding shouldn't read as anything else either.
See `docs/agent-retrieval.md` for the exact scoring/exclusion mechanics.

**casting ≠ substitutability.** Substitutability still measures how anonymous
the *image* is — a face-clear Elsie Bray CU honestly scores `1`. `casting`
answers a different question: *who can this shot be, and is this shot allowed
to be them?* By `role = lead` and `usable = true` that same CU is prime,
fully-usable Laura Santamaria material despite the low score. Substitutability
tie-breaks between ensemble shots; casting (plus, for the one constrained
lead, its `constraints`) is the load-bearing gate.

---

## Axis E — Register / mood (`vocab/register.yaml`)

- **`register`** — ordinal `−2..+2`, mythic (+2) ↔ tactical (−2). **Derived, not
  judged**: pushed mythic by concrete signals already tagged (salience =
  environment/artifact/hero, Traveler/Light/ritual iconography, slow pacing, low/no
  HUD, orchestral audio) and tactical by (HUD present, weapon fire, kill feed, fast
  cuts, enemy-death salience). Because it's a function of other fields, it costs
  ~nothing and isn't a subjective new pass — that's what makes it queryable rather
  than a vibe field.
- `mood` (multi): `reverent, triumphant, lonely, ominous, serene, tense` — for
  semantic match.

---

## Axis F — Salience (`vocab/salience.yaml`)

- **`subject_salience`** (single, required): `guardian_hero,
  environment_establishing, enemy_threat, object_artifact, crowd_group, ambient`.

This is where the Guardian-centric stance becomes **mechanical**. Enemies are wanted
as *threat/stakes* (`enemy_threat` in the background of a hero shot), not as subject.
The agent down-weights `enemy_threat` and `ambient`, and up-weights the rest:
`guardian_hero, environment_establishing, object_artifact` — and now
`crowd_group` joins them. The anonymous crowd is the project's ensemble cast
(Axis D), not background noise, so a crowd/group shot is exactly as
retrieval-worthy as a solo hero shot, not something to be down-weighted for
lacking one. Cleaner than overloading `mood`.

---

## Axis G — Action (`vocab/action.yaml`)

- `action` (multi): `idle, combat, ability_cast, traversal, emote, dialogue, ritual,
  vehicle, unknown`. **`traversal` is first-class.**
- **`traversal_hero`** (derived boolean) =
  `action includes 'traversal'` **AND** `shot_scale ∈ {ELS, LS, MLS, MS}` **AND**
  `camera_movement` excludes `handheld_shaky`.

This makes the bridge-running beat a retrievable category instead of something that
falls between "action" and "establishing shot" (see `examples/bridge-traversal.json`).
Note what's **not** in the formula any more: `substitutability`. Anonymity stopped
being a usability gate when the ensemble became a whole contributor pool (Axis D),
so a recognizable Guardian — or a named lead — sprinting across a bridge is still
a hero traversal beat, not disqualified for being identifiable.

---

## Minimum viable tag set

The example queries are answerable with: `overlays`, `clean`, `footage_tier`
(cleanliness — the load-bearing baseline, Axis A); `class`, `element`, `faction`,
`destination`, `activity` (domain); `shot_scale`, `composition`, `camera_movement`,
`content_type` (cinematography); `casting` (role/character/person — lead vs.
ensemble); `subject_salience`; `register`; `action` + `traversal_hero`; and the
free-text `caption`. `substitutability` is not part of the baseline set — it's a
refinement, useful only as an ensemble tie-break. Everything else is refinement
too — add fields only when a real query needs them.
