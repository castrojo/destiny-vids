# H-05 — Universe packs: scope the Destiny-specific vocab so a second universe can exist

**What:** `vocab/domain.yaml` and the lead map in `vocab/casting.yaml` are
Destiny. The schemas restate those enums, and tests assert the two agree. A Halo
record has nowhere to put `covenant` or `alpha_halo_surface`, and adding them to
the shared enums makes `titan` and `cabal` legal values on a Halo shot.

**Scope:**
- Add `universe` (enum `destiny`, `halo`) to `schema/video.schema.json`,
  **required**, inherited into segments the way `era` and `activity` already are.
  Backfill the seven existing `videos/*.json` records with `universe: destiny`.
- Move the franchise-specific vocab to `vocab/universes/<universe>/`:
  `domain.yaml` and the lead map. Franchise-neutral axes — cleanliness,
  cinematography, identity, salience, register, action, provenance — stay at
  `vocab/` and are shared.
- Keep **one union enum per field** in the schema. Add a test with two halves:
  every universe pack's values appear in the schema union, and no record carries
  a value belonging to another universe. This preserves "`vocab/` is the single
  source of truth" without conditional schema branching.
- Fill in the Halo pack (values sourced from the mission list in
  [`../research.md`](../research.md#4-halo-combat-evolved-campaign-arc), not
  invented): `faction` = `unsc | covenant | flood | forerunner_sentinel |
  unknown`; `destination` = the CE mission locations; `era` = `halo_ce |
  halo_ce_anniversary | halo_2 | halo_2_anniversary | unknown`; `activity` =
  `campaign_mission | cinematic | unknown`.
- `class`, `element` and `subclass_version` are **not used** by the Halo pack.
  Halo has no player classes, damage elements or subclass versions; a field a
  universe does not use is absent, and only `segment_id`, `video_id`,
  `start_sec`, `end_sec`, `subject_salience` are required. Do not map armour
  colour onto `class` to fill a column.

**Acceptance:**
- [ ] Every existing test passes unchanged; the Destiny records are byte-identical
      apart from the added `universe`.
- [ ] A Halo segment carrying `faction: covenant` validates; one carrying
      `faction: cabal` fails the universe test.
- [ ] `tests/test_ingest.py`'s era check reads the record's own universe pack.

**Depends on:** H-00

**Automatable:** yes.
