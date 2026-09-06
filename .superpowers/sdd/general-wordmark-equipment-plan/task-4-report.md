# Task 4 report: complete General equipment integration

## Result

Task 4 is implemented without compositing the wordmark. The ensemble now
builds one normalized catalog from the eight existing RAFI callouts and all
eighteen Leonardo catalog items, renders one card per unique item, and keeps
the existing stage segmentation, kid retimes, farm workflow, and single-pass
audio assembly unchanged.

## Catalog and renderer integration

- `load_equipment_catalog()` loads the Leonardo `items` object from its
  committed catalog.
- `equipment_catalog()` preserves the RAFI copy, evidence, art, and
  presentation values while adding the Leonardo records, rejecting duplicate
  IDs.
- `normalize_callout()` is the only path from either catalog into
  `render_callout()`. It preserves RAFI `*_render` copy and approved font
  values, fills only Leonardo placeholder descriptions through
  `tools.placeholder.fill_equipment_description()`, and supplies the existing
  renderer contract.
- `render_uta_callout.visible_character_count()` counts label, subtitle, and
  description rows for the schedule readability gate.
- Authored Leonardo descriptions remain byte-for-byte unchanged. Placeholder
  descriptions are generated at render time and are never written back to the
  catalog.

## Extraction and real-asset audit

`extract_equipment()` now supports all three catalog modes:

- `components`: the existing connected-alpha-component extraction, including
  transparent-seed and quarter-turn validation.
- `context_crop`: exact source crop, source-coordinate polygon transformation,
  polygon mask multiplied by source alpha, empty/all-edge rejection, alpha
  crop, and declared quarter-turn rotation.
- `text_only`: no display art is produced; the renderer receives a copy-only
  card.

`--audit-assets` reads only the supplied Hero PNG/JPEG assets through Pillow.
It checks source presence, RGBA mode, catalog dimensions, mode-specific
geometry, seed/mask validity, non-empty results, and recorded contextual or
degraded dispositions. The audit completed successfully for all eighteen
Leonardo items. The two truthful degraded dispositions remain copy-only:
`leonardo_magnetic_grenade` and `leonardo_ai_control_module`. The five
context-bound items retain their catalog notes. The supplied dimensions and
alpha sources agree with the catalog, so no catalog correction was required.
No design-sheet pixels are used as display art.

## Complete schedule

All 26 catalog IDs are scheduled exactly once, in the bottom rail:

| Start | Hold | Item |
|---:|---:|---|
| 18.0 | 10.0 | `leonardo_magical_hi_tech_spear` |
| 34.0 | 12.0 | `spear` |
| 48.0 | 10.0 | `leonardo_diy_crossbow` |
| 60.0 | 10.0 | `leonardo_automatic_folding_shield` |
| 76.0 | 9.0 | `composite_bow` |
| 87.0 | 10.0 | `leonardo_regular_hunting_arrow` |
| 99.0 | 10.0 | `leonardo_tungsten_throwing_axe` |
| 116.0 | 12.0 | `double_kopis` |
| 130.0 | 10.0 | `leonardo_plasma_arrow` |
| 142.0 | 10.0 | `leonardo_magnetic_grenade` |
| 154.0 | 9.0 | `bead_catcher` |
| 165.0 | 10.0 | `leonardo_explosion_arrow` |
| 177.0 | 10.0 | `leonardo_steel_knife` |
| 196.0 | 10.0 | `hippershell_exox` |
| 207.0 | 20.0 | `leonardo_chili_smoke_grenade` |
| 236.0 | 9.0 | `bomb_10mm` |
| 247.0 | 16.0 | `leonardo_electroshock_grenade` |
| 268.0 | 9.0 | `magazine_20` |
| 279.0 | 10.0 | `leonardo_ai_control_module` |
| 300.0 | 10.0 | `ai_control_module` |
| 311.0 | 8.0 | `leonardo_provision_bag` |
| 354.0 | 10.0 | `leonardo_camel_bag` |
| 366.0 | 10.0 | `leonardo_tungsten_armor` |
| 384.0 | 12.0 | `leonardo_hippershell_exo_x` |
| 402.0 | 14.0 | `leonardo_hi_tech_sword` |
| 418.0 | 10.0 | `leonardo_hard_leather_gauntlet` |

The builder rejects duplicate or unsupported IDs, stage-window violations,
protected-passage overlap, sub-one-second gaps, presentation minimum
violations, unreadable holds, empty placeholders, changed authored copy, and
invalid source geometry. Rendered cards are additionally measured with the
solid-alpha threshold and must remain within the bottom bounds.

## Validation

- Targeted regression suite: 88 passed.
- Full offline suite: 4101 passed, 9 skipped.
- Real-asset preflight: 18 Leonardo items reported, no failures.
- Card render smoke check: 26 cards rendered and passed bottom-rail fitting.
- Workflow generation: complete 26-card schedule emitted; source tiling
  remains 11427 frames plus the 132-frame intro.
- Corpus, derived-field, identity, schema-enum, and all pre-commit checks
  passed.

## Remaining scope

Task 5 still owns wordmark compositing. This change intentionally leaves the
top rail available and does not add the wordmark to the ensemble card or
workflow layers.
