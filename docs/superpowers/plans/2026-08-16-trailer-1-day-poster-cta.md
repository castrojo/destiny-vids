# Trailer 1 Day-Poster CTA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `wolves.projectbluefin.io` the large central call to action on Trailer 1's KubeCon end card over the March Bluefin day-wolves wallpaper.

**Architecture:** Keep `stories/trailer-1-plates.json` within the existing title-card field shape: the event remains `title`, the venue remains `subtitle`, `body[0]` is the CTA, and the remaining body rows are hashtags. A `variant: "poster"` styling switch lets `cards/maintitle.html` render that established data with a poster hierarchy. `scripts/build_trailer1.py` uses the already-resolved March day wallpaper as the end-card background instead of creating a black colour source.

**Tech Stack:** JSON manifest records, HTML/CSS/JavaScript rendered through Playwright, Python 3 build script, ffmpeg in `bluefin-thumbnailer`, pytest.

## Global Constraints

- The selected background is the March Bluefin **day** wolves wallpaper, never the night wallpaper and never a random choice.
- Do not add a copy field: end-card copy stays `title`, `subtitle`, and `body[]`.
- Copy is exact: `wolves.projectbluefin.io`, then `#KubeCon`, `#CloudNativeCon`, `#7wolves`.
- Preserve `TOTAL == 110.020`, `ENDCARD == 7.820`, the end-card cue, bridge timing, and audio fade.
- The event title retains its blue seared `|`; do not blueify the Linux Foundation trademarks in that title.
- Never put a panel behind the type. Darken the whole wallpaper and use the established glyph halo.
- A missing day wallpaper exits explicitly; never silently substitute night or black.

---

### Task 1: Record and pin the poster data shape

**Files:**
- Modify: `stories/trailer-1-plates.json: endcard`
- Modify: `tests/test_trailer1.py: end-card tests`

**Interfaces:**
- Consumes: the existing `endcard` plate record and `plate(manifest, plate_id)`.
- Produces: an endcard record with `variant == "poster"` and `body == ["wolves.projectbluefin.io", "#KubeCon", "#CloudNativeCon", "#7wolves"]`.

- [ ] **Step 1: Write the failing record tests**

  Replace the current end-card body assertion with:

  ```python
  def test_the_end_card_is_the_owners_words_in_the_owners_order(manifest):
      card = plate(manifest, "endcard")
      assert card["variant"] == "poster"
      assert card["title"] == "KubeCon | CloudNativeCon North America"
      assert card["subtitle"] == "Salt Lake City, Utah"
      assert card["body"] == [
          "wolves.projectbluefin.io",
          "#KubeCon",
          "#CloudNativeCon",
          "#7wolves",
      ]
  ```

  Add:

  ```python
  def test_the_end_card_poster_uses_no_new_copy_field(manifest):
      card = plate(manifest, "endcard")
      copy_fields = {
          key for key in card
          if not key.startswith(("_", "note"))
          and key not in {
              "id", "kind", "at", "dur", "stage", "variant", "angle",
              "size", "anchor", "anchor_out", "walk",
          }
      }
      assert copy_fields == {"title", "subtitle", "body"}
  ```

- [ ] **Step 2: Run the focused test to verify it fails**

  Run:

  ```bash
  python3 -m pytest -q tests/test_trailer1.py -k end_card
  ```

  Expected: failure because the record has no `variant` and the CTA is absent.

- [ ] **Step 3: Update the manifest**

  In the `endcard` record, add:

  ```json
  "variant": "poster"
  ```

  Make the beginning of `body`:

  ```json
  "body": [
    "wolves.projectbluefin.io",
    "#KubeCon",
    "#CloudNativeCon",
    "#7wolves"
  ]
  ```

  Update the record prose to state that the first body entry is the owner CTA
  and the remaining entries preserve the authored hashtag order.

- [ ] **Step 4: Run the focused test to verify it passes**

  Run:

  ```bash
  python3 -m pytest -q tests/test_trailer1.py -k end_card
  ```

  Expected: PASS.

- [ ] **Step 5: Commit the record and its tests**

  ```bash
  git add stories/trailer-1-plates.json tests/test_trailer1.py
  git commit -m "feat(trailer): record the day-poster CTA"
  ```

### Task 2: Render the poster hierarchy in the existing title-card template

**Files:**
- Modify: `cards/maintitle.html: poster CSS and body-row construction`
- Modify: `tests/test_cards.py: maintitle poster template coverage`

**Interfaces:**
- Consumes: query parameter `variant=poster`, `title`, `subtitle`, and repeated `body` values from `cards/render-cards.mjs`.
- Produces: a transparent 1920×1080 card where the first body row receives class `poster-cta` and later rows receive class `poster-tag`.

- [ ] **Step 1: Write the failing template test**

  Add a test that reads `cards/maintitle.html` and asserts the narrow
  contract, rather than a brittle pixel snapshot:

  ```python
  def test_maintitle_has_a_poster_variant_for_the_existing_body_shape():
      template = (REPO_ROOT / "cards" / "maintitle.html").read_text()
      assert 'body[data-variant="poster"] .credits' in template
      assert "poster-cta" in template
      assert "poster-tag" in template
      assert "host.classList.contains('poster')" in template
  ```

- [ ] **Step 2: Run the focused test to verify it fails**

  Run:

  ```bash
  python3 -m pytest -q tests/test_cards.py -k poster_variant
  ```

  Expected: failure because the poster classes and selector do not exist.

- [ ] **Step 3: Add only poster-scoped styling**

  Add CSS selectors scoped to `body[data-variant="poster"]`:

  ```css
  body[data-variant="poster"] .lockup { width: 92%; }
  body[data-variant="poster"] .title {
    font-size: clamp(1.7rem, 2.5vw, 2.45rem);
    letter-spacing: 0.07em;
  }
  body[data-variant="poster"] .subtitle {
    margin-top: 0.8rem;
    font-size: clamp(1.1rem, 1.7vw, 1.5rem);
  }
  body[data-variant="poster"] .credits {
    margin-top: 2.5rem;
    gap: 0;
    font-family: var(--wc-font-display);
    letter-spacing: 0;
  }
  body[data-variant="poster"] .poster-cta {
    display: block;
    color: #fff;
    font-size: clamp(2.8rem, 5vw, 5.2rem);
    font-weight: 900;
    letter-spacing: 0.045em;
    line-height: 1.05;
  }
  body[data-variant="poster"] .poster-tag {
    display: inline;
    color: #cbd5e1;
    font-family: var(--wc-font-mono);
    font-size: 1.1rem;
    letter-spacing: 0.12em;
  }
  ```

  Apply the existing `blueify` implementation to `poster-cta`, so the dots
  in the domain receive the established Bluefin treatment. Keep
  `sear(titleEl, { blue: false })` unchanged for the event title.

- [ ] **Step 4: Classify the body rows by index**

  Replace the unconditional:

  ```javascript
  row.className = 'credit-line'
  sear(row)
  ```

  with:

  ```javascript
  const poster = host.classList.contains('poster')
  row.className = poster
    ? (index === 0 ? 'poster-cta' : 'poster-tag')
    : 'credit-line'
  if (poster) {
    blueify(row)
  } else {
    sear(row)
  }
  ```

  Set `host.classList.add('poster')` when
  `document.body.dataset.variant === 'poster'`. Preserve the current behavior
  for every non-poster card.

- [ ] **Step 5: Run the focused test to verify it passes**

  Run:

  ```bash
  python3 -m pytest -q tests/test_cards.py -k poster_variant
  ```

  Expected: PASS.

- [ ] **Step 6: Commit the template and its test**

  ```bash
  git add cards/maintitle.html tests/test_cards.py
  git commit -m "feat(cards): render Trailer 1 as a poster CTA"
  ```

### Task 3: Put the poster over the selected day wallpaper

**Files:**
- Modify: `scripts/build_trailer1.py: end-card graph and wallpaper validation`
- Modify: `tests/test_trailer1.py: filtergraph tests`

**Interfaces:**
- Consumes: `day_png` already resolved by `wallpaper("day")`.
- Produces: a bounded day-wallpaper end-card background labelled `endbg`, darkened globally before the transparent `plate_endcard.png` overlays it.

- [ ] **Step 1: Write the failing filtergraph tests**

  Add:

  ```python
  def test_the_end_card_uses_the_resolved_day_wallpaper(manifest):
      graph = T.filtergraph(manifest)
      assert "[endday]eq=brightness=-0.55[endbg]" in graph
      assert "color=c=black" not in graph

  def test_the_end_card_wallpaper_is_bounded_to_its_own_window(manifest):
      graph = T.filtergraph(manifest)
      expected = f"trim=0:{T.ENDCARD:.3f}"
      assert expected in graph
  ```

- [ ] **Step 2: Run the focused tests to verify they fail**

  Run:

  ```bash
  python3 -m pytest -q tests/test_trailer1.py -k end_card_wallpaper
  ```

  Expected: failure because the graph creates `color=c=black`.

- [ ] **Step 3: Replace the black source with the bounded day still**

  In `filtergraph()`, replace the `color=c=black` end-card source with:

  ```python
  parts.append(_still(5, "endday",
                      f",trim=0:{ENDCARD:.3f},setpts=PTS-STARTPTS,"
                      f"format=yuv420p"))
  parts.append("[endday]eq=brightness=-0.55[endbg]")
  ```

  Do **not** increment `inputs`: input 5 is already the day wallpaper used by
  the bridge, and ffmpeg permits the same input to feed both filter chains.
  The end-card PNG remains input 7. The `command()` input order remains
  source, four card PNGs, day wallpaper, night wallpaper, end-card PNG; do
  not add a second wallpaper input.

  Keep the card fade chain and the final:

  ```python
  [endbg][ec]overlay=0:0:shortest=1,format=yuv420p[endcard]
  ```

  unchanged. The global darkening is the only background treatment.

- [ ] **Step 4: Run the focused tests to verify they pass**

  Run:

  ```bash
  python3 -m pytest -q tests/test_trailer1.py -k end_card_wallpaper
  ```

  Expected: PASS.

- [ ] **Step 5: Commit the background graph and tests**

  ```bash
  git add scripts/build_trailer1.py tests/test_trailer1.py
  git commit -m "feat(trailer): back the CTA with Bluefin day art"
  ```

### Task 4: Render, inspect, and deliver

**Files:**
- Generated: `renders/plates-trailer-1/plate_endcard.png`
- Generated: `renders/trailer-1.mp4`
- Delivered: `~/Videos/Wolves/trailer-1.mp4`

**Interfaces:**
- Consumes: the committed manifest, template, and build graph.
- Produces: an H.264 + FLAC, 110.020-second Trailer 1 master at the delivery path.

- [ ] **Step 1: Render the card and complete trailer**

  Run:

  ```bash
  python3 scripts/build_trailer1.py --cards
  ```

  Expected: output reports `"duration": 110.02` and
  `"delivered": "/var/home/jorge/Videos/Wolves/trailer-1.mp4"`.

- [ ] **Step 2: Check the delivered duration and codecs**

  Run:

  ```bash
  podman exec bluefin-thumbnailer ffprobe -v error \
    -show_entries format=duration:stream=codec_name \
    -of csv=p=0 ~/Videos/Wolves/trailer-1.mp4
  ```

  Expected: `h264`, `flac`, and a duration near `110.020`.

- [ ] **Step 3: Extract an end-card frame**

  Run:

  ```bash
  podman exec bluefin-thumbnailer ffmpeg -hide_banner -loglevel error \
    -ss 106 -i ~/Videos/Wolves/trailer-1.mp4 -frames:v 1 \
    -vf scale=1280:-1 -y /var/tmp/trailer-1-day-poster.png
  ```

  Inspect the frame. It passes only if the day wolves artwork is visible,
  `wolves.projectbluefin.io` is the largest text, the event title remains
  readable and seared, and no opaque panel sits behind the type.

- [ ] **Step 4: Run the mandatory gates**

  Run:

  ```bash
  python3 -m pytest -q
  python3 tools/corpus.py --check
  python3 tools/rederive.py --check
  python3 scripts/generate_schema_enums.py --check
  ```

  Expected: all commands exit 0.

- [ ] **Step 5: Commit the verified delivery-facing changes**

  ```bash
  git add cards/maintitle.html scripts/build_trailer1.py \
    stories/trailer-1-plates.json tests/test_cards.py tests/test_trailer1.py
  git commit -m "feat(trailer): ship the day-poster CTA"
  ```
