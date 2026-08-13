# vocab/ — Canonical Controlled Vocabularies

These YAML files are the **single source of truth** for every enum used in the
Destiny 2 footage index. Shot/segment schemas, labelers, and retrieval agents
must reference these values exactly — never invent variants or synonyms.

## Files

| File | Axis |
|---|---|
| `cleanliness.yaml` | Frame overlays and the derived `clean`/`footage_tier` gate — the project's primary filter |
| `domain.yaml` | Destiny domain: class, element, faction, destination, era, activity, subclass_version |
| `cinematography.yaml` | Shot craft: scale, composition (incl. `crowd`), angle, movement, pacing, content_type, lighting |
| `identity.yaml` | Substitutability: how anonymous/interchangeable the on-screen subject reads (now a tie-break, not a gate) |
| `casting.yaml` | Lead/ensemble casting: named 1:1 NPC bindings vs. the rotating monthly ensemble pool |
| `register.yaml` | Mythic ↔ tactical register and mood |
| `salience.yaml` | What the shot is about (Guardian-centric stance) |
| `action.yaml` | What the subject does, plus the derived `traversal_hero` boolean |
| `provenance.yaml` | Source, label_source, confidence, usage_class |

## Provenance rule

**Every field in the schema carries `source`, `label_source`, and `confidence`**
(see `provenance.yaml`). Values are either `inherited` from video-level metadata
(title/description/tags/playlist set video-scoped defaults) or `observed` at
shot level, and were produced `manual`ly, by a `heuristic`, or by a `model`.

## Key design decisions

- **`clean` is the first-class filter** (`cleanliness.yaml`): the fiction bends
  to the footage now, not the other way round, so a shot's usability is decided
  by whether its overlays (HUD, nameplates, burned-text, talking-head) can be
  cut around — not by how replaceable its subject is. An untagged `overlays`
  field derives `clean = false`, never `true`: cleanliness has to be positively
  established, because a false positive puts a HUD in the finished cut.
  `footage_tier` (cinematic/gameplay/mixed) is a separate, independent axis —
  gameplay is kept as ranked-down coverage, not excluded.
- **Casting is inverted into lead/ensemble tiers** (`casting.yaml`): a `lead` is
  a named NPC bound 1:1 to one real person for the life of the project,
  **usually** usable at any shot scale — no resemblance constraints, because
  the project names a role rather than compositing a face onto it. Exactly one
  binding is the exception (`saladin` → `jeefy`, who doesn't resemble the Iron
  Lord): it carries `constraints` (`require_helmet`, `require_far`), and a
  shot that violates them derives `casting.usable = false` with the unmet keys
  in `constraints_failed`, excluding it from Saladin's retrieval. Every
  anonymous Guardian is an `ensemble` slot instead, filled from a rotating
  monthly pool of Project Bluefin contributors; slot counts (`crowd`→6,
  `group`→3, otherwise 1) are derived from composition/salience, never
  hand-tagged, and `casting.person` is always `null` for ensemble at index time
  so a rotating cast never invalidates a tagged segment.
- **Substitutability is demoted to a tie-break** (`identity.yaml`): it used to
  be the primary retrieval filter, back when one performer had to stand in for
  every Guardian. Now it only decides between two otherwise-equal clean
  ensemble shots — a face-clear lead close-up is fully usable at
  substitutability `0`.
- **Traversal is a first-class action** (`action.yaml`); the derived
  `traversal_hero` boolean marks the reusable "Guardian moving through big
  space" beat. Substitutability plays no part in it any more — identifiable or
  not, a Guardian sprinting through open space is still a traversal hero shot.
- **Some axes are derived, never observed**: `subclass_version` comes from era,
  `register` comes from proxies (salience, iconography, HUD, pacing, audio),
  and `clean` / `footage_tier` / `traversal_hero` / `casting` are pure functions
  computed once at assembly time from already-tagged fields — never hand-tagged,
  never settable by a tagger.
- **Deliberately coarse where observation is unreliable**: camera movement
  collapses dolly/zoom/track.
