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

