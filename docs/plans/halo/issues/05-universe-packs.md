# H-05 — Universe packs: scope the Destiny-specific vocab so a second universe can exist

**What:** `vocab/domain.yaml` and the lead map in `vocab/casting.yaml` are
Destiny. The schemas restate those enums. A Halo record has nowhere to put
`covenant` or `alpha_halo_surface`, and adding them to the shared enums makes
`titan` and `cabal` legal values on a Halo shot.

Note that AGENTS.md's "tests assert the two agree" is aspirational: the only
checks that exist are `tests/test_ingest.py`'s per-record `era` check and
`tests/test_search.py`'s salience constant. The drift is already real —
`vocab/domain.yaml` lists 13 `subclass_version` values and the schema's
`$defs.subclass_version` lists 7. Two universes double the surface, so the
bidirectional test below is part of this issue, not a follow-up.

**Scope:**
- Add `universe` (enum `destiny`, `halo`) to `schema/video.schema.json`,
  **required**, inherited into segments the way `era` and `activity` already are:
  add it to `annotate.INHERITABLE_FIELDS` (`tools/annotate.py:57`) and to the
  `provenance` `propertyNames` enum in **both** schemas, or the provenance entry
  the assembler writes for it fails validation. Make it **required on segments
  too** — a segment with no universe cannot be checked against any pack. Backfill
  the seven existing `videos/*.json` records with `universe: destiny`.
- Move the franchise-specific vocab to `vocab/universes/<universe>/`:
  `domain.yaml` and the lead map. Franchise-neutral axes — cleanliness,
  cinematography, identity, register, action, provenance — stay at `vocab/` and
  are shared.
- Keep **one union enum per field** in the schema, and enforce isolation in
  `annotate.validate_segment()`: reject any value not in the record's own pack, at
  ingest time. A corpus test only catches what is already committed. Back it with
  a bidirectional test in two halves: every universe pack's value appears in the
  schema union *and* every schema enum value belongs to some pack, and no record
  carries a value belonging to another universe. This preserves "`vocab/` is the
  single source of truth" without conditional schema branching.
- Fill in the Halo pack (values sourced from the mission list in
  [`../research.md`](../research.md#4-halo-combat-evolved-campaign-arc), not
  invented): `faction` = `covenant | flood | forerunner_sentinel | unknown`;
  `destination` = the CE mission locations; `era` = `halo_ce |
  halo_ce_anniversary | halo_2 | halo_2_anniversary | unknown`; `activity` =
  `campaign_mission | cinematic | unknown`.
  **`unsc` is deliberately not a `faction` value.** The axis is defined as
  "Enemy faction(s) visible in the shot"; putting the hero side in it inverts the
  meaning of every existing `faction` query and of the `enemy_threat` salience
  that pairs with it. The UNSC is carried by salience and casting, as Guardians
  are.
- Untangle the Destiny strings that the neutral stages still carry, or the pack
  split is cosmetic:
  - `guardian_hero` is both a `subject_salience` value (`vocab/salience.yaml`)
    and the ensemble trigger (`derive.ENSEMBLE_SALIENCE`). Introduce a neutral
    value with per-pack display copy, and keep the Destiny alias readable.
  - `derive.DEFAULT_CASTING_PATH` (`tools/derive.py:25`) hardcodes one global
    casting file; it resolves per universe.
  - `tools/plate.py` hardcodes `"CONTRIBUTOR // GUARDIAN"` (`:441–445`) and
    `"Project Bluefin, {month}"` (`:470–472`) — both become authored copy from
    the run's cast file.
  - `vocab/provenance.yaml:27–32` documents `usage_class` as Bungie-owned
    footage; the wording generalizes (H-03 owns the rights note itself).
- `class`, `element` and `subclass_version` are **not used** by the Halo pack.
  Halo has no player classes, damage elements or subclass versions; a field a
  universe does not use is absent, and only `segment_id`, `video_id`,
  `start_sec`, `end_sec`, `subject_salience` (plus `universe`) are required. Do
  not map armour colour onto `class` to fill a column.

**Acceptance:**
- [ ] Every existing test passes unchanged; the Destiny records are byte-identical
      apart from the added `universe`.
- [ ] A Halo segment carrying `faction: covenant` validates; one carrying
      `faction: cabal` is rejected by `validate_segment()`, not merely by a
      corpus test.
- [ ] A segment with no `universe` fails validation.
- [ ] The bidirectional vocab↔schema test passes for both packs (which means the
      existing `subclass_version` drift is closed as part of this).
- [ ] `tests/test_ingest.py`'s era check reads the record's own universe pack.
- [ ] No franchise-specific string remains hardcoded in `derive.py` or
      `plate.py`.

**Depends on:** H-00

**Automatable:** yes.
