# Trailer 1 URL Dot Sear Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the two Bluefin-blue dots in `wolves.projectbluefin.io` into compact blue sears without changing the URL’s white letters.

**Architecture:** `blueifyDomain()` already wraps each URL dot in `.accent`; add a poster-scoped `.poster-cta .accent` treatment that reuses the existing sear palette in a smaller text-shadow stack. The change remains CSS-only after the existing DOM construction, so no manifest, timing, or audio behavior changes.

**Tech Stack:** HTML, CSS, browser-rendered title cards, pytest.

## Global Constraints

- Only the two URL dots get a sear.
- The CTA’s `b` and `f` remain white.
- Reuse the existing flare, mid, and halo Bluefin palette.
- Keep the URL’s existing size, layout, cue timing, runtime, and audio unchanged.
- Do not create a broad flare or panel behind the CTA.

---

### Task 1: Add and pin the compact dot sear

**Files:**
- Modify: `cards/maintitle.html: poster CTA CSS`
- Modify: `tests/test_cards.py: poster variant template test`

**Interfaces:**
- Consumes: `.poster-cta .accent` spans emitted by `blueifyDomain()`.
- Produces: a 1 px near-white dot core with a compact Bluefin shadow stack.

- [ ] **Step 1: Write the failing template test**

  Extend `test_maintitle_has_a_poster_variant_for_the_existing_body_shape`:

  ```python
  assert 'body[data-variant="poster"] .poster-cta .accent' in template
  assert "0 0 2px 0 rgb(196 226 255 / 95%)" in template
  assert "0 0 7px 1px rgb(147 197 253 / 85%)" in template
  assert "0 0 16px 2px rgb(37 99 235 / 45%)" in template
  ```

- [ ] **Step 2: Run the focused test to verify it fails**

  Run:

  ```bash
  python3 -m pytest -q tests/test_cards.py -k poster_variant
  ```

  Expected: failure because the poster-dot selector does not exist.

- [ ] **Step 3: Add the poster-only sear**

  Add below `.poster-cta`:

  ```css
  body[data-variant="poster"] .poster-cta .accent {
    color: #4285f4;
    text-shadow:
      0 0 2px 0 rgb(196 226 255 / 95%),
      0 0 7px 1px rgb(147 197 253 / 85%),
      0 0 16px 2px rgb(37 99 235 / 45%);
  }
  ```

  Do not change `blueifyDomain()`: it already accents only `.` and thus
  preserves the CTA’s white `b` and `f`.

- [ ] **Step 4: Run the focused test to verify it passes**

  Run:

  ```bash
  python3 -m pytest -q tests/test_cards.py -k poster_variant
  ```

  Expected: PASS.

- [ ] **Step 5: Render and inspect**

  Run:

  ```bash
  python3 scripts/build_trailer1.py --cards
  podman exec bluefin-thumbnailer ffmpeg -hide_banner -loglevel error \
    -i ~/Videos/Wolves/trailer-1.mp4 \
    -vf "trim=start=106:end=106.1,setpts=PTS-STARTPTS" \
    -frames:v 1 -y /var/tmp/trailer-1-dot-sear.png
  ```

  Inspect the frame: both dots have a tight blue sear; `b` and `f` are white;
  neither dot blooms into a blob.

- [ ] **Step 6: Run mandatory gates and commit**

  Run:

  ```bash
  python3 -m pytest -q
  python3 tools/corpus.py --check
  python3 tools/rederive.py --check
  python3 scripts/generate_schema_enums.py --check
  ```

  Then commit:

  ```bash
  git add cards/maintitle.html tests/test_cards.py
  git commit -m "feat(cards): sear Trailer 1 URL dots"
  ```
