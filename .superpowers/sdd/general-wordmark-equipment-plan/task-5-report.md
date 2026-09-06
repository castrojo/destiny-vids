# Task 5 report: stage-only wordmark and still-image quality gate

## Status

Complete. The ensemble workflow now composites the pinned Bluefin website
wordmark only while the stage is active. Clean and full-frame segments retain
their existing command path and do not receive a wordmark input or overlay
filter.

## Implementation

- `scripts/build_uta_ensemble.py`
  - Adds source-backed wordmark geometry helpers and the pure-Pillow
    `fit_wordmark`, `wordmark_box`, and `layout_review_frame` interfaces.
  - Stages `/work/bluefin-wordmark.png` only in `stage_segment()`, scales it
    with Lanczos to the record's `display_width` of 600px while preserving
    aspect ratio, and overlays it at the recorded `(980, 48)` before equipment
    cards.
  - Fetches the rendered asset in the Argo fetch task without changing the
    clean segment graph.
  - Adds local day/night Pillow previews and a catalog-ordered contact sheet.
    The contact sheet records all 26 item IDs, source character, authored or
    placeholder description marker, final hold, and extracted-art alpha bounds.
  - Makes card rendering testable with supplied still backgrounds and returns
    per-card measurements used by the contact sheet.
- `scripts/fetch_wordmark.py`
  - Verifies the raw pinned website SVG before transformation.
  - Handles the pinned file's black lettering in `style` attributes, reversing
    it to white while preserving the `#4285f4` fin. Legacy no-argument fetch
    behavior remains unchanged.
- `stories/uta-general-ensemble.json`
  - Corrects the recorded source digest to the raw pinned SVG digest
    `d336d743082bded58c561c2c53baf1896dae87d7346224d9d06512e6c247cf74`.
    The previously recorded `4ae1...` value was the digest after replacing
    black lettering with white and could not validate the fetched source.
- `tests/test_uta_ensemble.py` and `tests/test_fetch_wordmark.py`
  - Add failing-first geometry, stage/clean graph, Pillow compositor,
    contact-sheet, 26-card image-level, and raw website recoloring coverage.

## Generated artifacts and review

The pinned asset was fetched and rasterized to:

`/var/home/jorge/Videos/Wolves/Hero/.work-uta-general/assets/bluefin-wordmark.png`

The required still artifacts were generated at:

- `/var/home/jorge/Videos/Wolves/Hero/.work-uta-general/review/stage-day-wordmark.png`
- `/var/home/jorge/Videos/Wolves/Hero/.work-uta-general/review/stage-night-wordmark.png`
- `/var/home/jorge/Videos/Wolves/Hero/.work-uta-general/review/equipment-contact-sheet.png`

The fitted wordmark is 600x230, with visible box `(980, 48, 600, 230)`. It
does not overlap the band, any of the four kid stations, or the bottom
equipment bounds. The current generated schedule contains exactly 26 cards:
eight RAFI items and eighteen Leonardo items. All current cards are RGBA,
non-empty, and their solid-alpha bounds remain inside the bottom rail. The
still review covered the rotated tall spear and kopis, the smallest art,
longest authored descriptions, fourteen placeholder descriptions, the two
text-only degradations, and the contact-sheet metadata. No clipped copy,
display art, leader line, or opaque full-frame sheet was observed.

The local previews are a Pillow-only preflight for transparency, sizing,
wordmark placement, and rail fit. They do not validate the real band or
children; returned Argo frames remain the authoritative visual gate for the
actual composition. No local ffmpeg or ffprobe command was run, and no video
container was decoded.

## Validation

- `python3 -m pytest tests/test_fetch_wordmark.py tests/test_hero_equipment.py tests/test_uta_ensemble.py -q`
  - 75 passed.
- `python3 scripts/build_uta_ensemble.py --cards --contact-sheet --out-dir "$HOME/Videos/Wolves/Hero/.work-uta-general"`
  - completed; wrote 26 current cards, both stage previews, and the 26-item
    contact sheet.
- `python3 scripts/build_uta_ensemble.py --audit-assets --hero-root "$HOME/Videos/Wolves/Hero"`
  - completed for all 18 Leonardo assets.
- `python3 scripts/build_uta_ensemble.py --workflow --out-dir "$HOME/Videos/Wolves/Hero/.work-uta-general"`
  - completed; the generated workflow contains the stage-only wordmark input.
- Repository-required validation:
  - 4110 passed, 9 skipped.
  - corpus, rederived metadata, schema-enum, identity, and all pre-commit
    checks passed.

## Concerns

The still-image gate is intentionally not a substitute for a remote render:
the actual band, keyed children, frame timing, and returned-frame visual review
still require the Argo workflow in the next production pass.

## Fix round 1

**Status:** complete.

The ensemble record now pins the source URL, source SHA-256, explicit
`preserve_colors` policy, 1200px raster request, derived PNG dimensions, and
staged PNG SHA-256. The builder reads that contract, fetches the PNG through
`scripts/fetch_wordmark.py` only when absent, rejects an existing stale or
wrong raster, and emits the verified digest in the Argo fetch task. The fetch
task runs `sha256sum -c` after staging the PNG. Legacy no-argument fetch
defaults remain unchanged.

The schedule validator now rejects every pocket other than `bottom`, with a
mutation regression covering the failure. Image coverage asserts the exact
`x=980`, `y=48`, `display_width=600` contract, 26 current cards split into
eight RAFI and eighteen Leonardo items, transparent context crops, no
design-sheet display art, and no opaque full-frame card overlays. The local
preflight now writes individual day and night composites for every rendered
card over the actual Pillow stage faces and pinned wordmark, alongside the
base wordmark stills and equipment contact sheet. It performs no video
decode.

The verified staged wordmark is `1992x765` with SHA-256
`e8ad8bbf657fd486a933f0ea30004817ae59cffd21fd588925b7dd0be897d44e`.

### Validation

- Focused suite: `81 passed`.
- Real `--audit-assets`: all 18 Leonardo assets and the staged wordmark
  passed.
- Regeneration: 26 cards, the Argo workflow, two base wordmark stills, two
  per-card day/night preflight sheets, and the equipment contact sheet.
- Full offline suite: `4116 passed, 9 skipped`.
- Corpus, derived metadata, schema-enum, identity, and all pre-commit checks
  passed.

### Artifacts

- `$HOME/Videos/Wolves/Hero/.work-uta-general/assets/bluefin-wordmark.png`
- `$HOME/Videos/Wolves/Hero/.work-uta-general/review/stage-day-wordmark.png`
- `$HOME/Videos/Wolves/Hero/.work-uta-general/review/stage-night-wordmark.png`
- `$HOME/Videos/Wolves/Hero/.work-uta-general/review/stage-day-cards.png`
- `$HOME/Videos/Wolves/Hero/.work-uta-general/review/stage-night-cards.png`
- `$HOME/Videos/Wolves/Hero/.work-uta-general/review/equipment-contact-sheet.png`
- `$HOME/Videos/Wolves/Hero/.work-uta-general/uta-ensemble.yaml`

### Concerns

No video was rendered by request. The per-card Pillow sheets verify the actual
bottom rail against day/night stage faces and the pinned wordmark, but Argo
returned frames remain the authoritative visual gate for the live band and
keyed children.

## Fix round 2

**Status:** complete.

The synthetic 26-card fit test remains offline and unchanged. A separate
local-only regression now skips when `~/Videos/Wolves/Hero` is unavailable and,
when present, runs the merged 26-item catalog through `extract_equipment` and
`render_card` using the actual Hero PNG sources. It asserts that every card
fits the bottom rail, context crops retain transparent pixels, quarter-turn
rotations change the extracted orientation, text-only entries write no art,
and no design-sheet file is used. Extraction and card-render failures are not
swallowed, so any real catalog failure fails the test.

### Validation

- `python3 -m pytest -q tests/test_uta_ensemble.py::test_solid_card_alpha_stays_inside_bottom_bounds tests/test_uta_ensemble.py::test_real_hero_assets_render_every_merged_equipment_card` — 2 passed.
- `python3 -m pytest -q tests/test_uta_ensemble.py` — 54 passed.
- `python3 -m pytest -q tests/test_fetch_wordmark.py tests/test_hero_equipment.py tests/test_uta_ensemble.py` — 82 passed.
- `HOME=/tmp PYTHONPATH=/var/home/jorge/.local/lib/python3.13/site-packages python3 -m pytest -q tests/test_uta_ensemble.py::test_real_hero_assets_render_every_merged_equipment_card` — 1 skipped.
- `python3 scripts/build_uta_ensemble.py --audit-assets --hero-root "$HOME/Videos/Wolves/Hero"` — passed for the local asset audit.

### Concerns

The real-asset regression is intentionally skipped on CI hosts without the
owner's local Hero asset tree; the existing synthetic regression remains the
offline CI coverage.
