# Full-frame cards: the act slide and the comic title card

Reference for [`docs/skills/plates.md`](../plates.md). Split out of it to keep
the skill inside its size budget; this is the detail needed when rendering or
changing a card that covers the whole frame, not when planning a cut.

Both cards belong to `projectbluefin/website`, and both are reproduced by
rendering **the site's own CSS in a real browser** — the pattern
`~/Videos/wolves-{kat,natali}/render/plate.html`, `reveal.html` and
`nimbatus-review/render/endcard.html` have always used.

| File | Copies |
|---|---|
| `cards/act.html` | `src/components/wolves/cinematic/CinematicTransition.vue` + `src/style/wolves-cinematic.scss` |
| `cards/comic.html` | `.wolves-intro-overlay-title-card` and friends, `src/components/wolves/WolvesIntroOverlay.vue` |
| `cards/render-cards.mjs` | the driver — playwright, 1920x1080 at 1x, `omitBackground` |

```bash
ln -sfn ~/src/website/node_modules node_modules     # playwright is not vendored
node cards/render-cards.mjs --manifest <manifest> --out-dir <plates-dir>
node cards/render-cards.mjs --manifest <manifest> --out-dir <dir> --only id1,id2
```

## Why not Pillow

`tools/plate.py` ports the *deck's* shapes — the Guardian plate, the small title
card, the chat pill, the status HUD — because those are baked into videos and
the port is the record of what shipped. A card that **exists on the site and is
still live** is different: porting it produces a second version of chrome that
drifts the first time the site changes, and the drift is invisible until
somebody compares two renders side by side.

So `render_plate` raises on `kind: act` and `kind: comic` and names this
driver, and `render_all` skips them. Both renderers write `plate_<id>.png` into
the same directory, so a manifest may mix them: the Wolves hero segment carries
six Guardian plates *and* 23 comic cards, and `burn` reads one plates-dir.

## Fields

Copy arrives in the manifest; a row nobody authored is left out of the URL and
does not render. The templates default nothing.

**`kind: "act"`** — the deck's `title` / `subtitle` / `body` plus exactly two
owner-requested rows:

| Field | What it draws |
|---|---|
| `act` | the Roman numeral, huge (`clamp(6rem, 12vw, 11rem)`) |
| `body[]` | the teal terminal block, one authored line per row |
| `label` | the `.wc-label` eyebrow |
| `title` | `.wc-transition-title`, uppercase |
| `subtitle` | `.wc-transition-artist` |
| `chapters[]` | the act's chapters, under the title |

**`kind: "comic"`** — the full-screen card, opaque black, which **covers** the
picture for its window exactly as the site does:

| Field | What it draws |
|---|---|
| `art` | one comic hero shot (`wolves-comic-hero-shots.ts`) |
| `qr` / `qr_dialogue` / `qr_domain` | the MakeMeAComic panel |
| `quote` / `quote_by` / `quote_note` | the pull quote and its attribution |
| `wallpaper` | an image behind the card, in place of its opaque black |
| `wallpaper_dir` / `wallpaper_match` | roll a random one per render, from a directory, optionally filtered by regex |
| `captions[]` | caption boxes in the frame's margins |

A card whose only content is `art` — no QR panel, no quote — is not a hero shot
beside a column: it **is** the frame, and takes the full height. Without that
it renders at about a third of frame.

### Caption boxes, and when a plate cannot be one

A Guardian plate is **561px** wide. Square art on a 16:9 frame leaves **420px**
of margin either side, so an identity beside a square cover cannot be a plate
without covering the art. `captions[]` carries the same authored strings in
chrome that fits:

```json
{"side": "left", "label": "BLUEBERRY // HUMAN",
 "lines": ["Rafael Castro", "Blueberry Hunter", "Happy 10th Birthday!"]}
```

`side` picks the margin, `label` draws the mono eyebrow, and `lines[]` draws
the rows — the first as the headline, the rest as supporting detail. Absent
keys draw nothing, as everywhere else. The chrome is the deck's own, reproduced
not designed: white stock, the 16px chamfer and the `#60a5fa` hairline
`tools/plate.py` draws, plus a left accent rule, and **no tilt**.

This is a chrome change, never a copy change. Moving an identity off a plate
and into a caption must carry every authored string across verbatim; a row that
does not fit is a row the owner has to shorten, not one the renderer drops.

### A random wallpaper is only usable if the roll is recorded

`wallpaper_dir` picks a file at random per render. A render nobody wrote down
cannot be rebuilt, so the driver records its choice in `wallpapers.json` beside
the PNG, and `--wallpaper-seed <seed>` replays it — the pick is hashed from
`seed:card_id`, so it does not depend on directory order.

## Traps, each of which has already bitten

- **A CSS comment containing `*/` truncates the stylesheet.** A path like
  `wolves-*/render/reveal.html` inside a comment renders the whole card as
  unstyled black text on white. A test pins the comment count.
- **Reading pixels back from a `file://` image taints the canvas.** The comic
  card measures each artwork's visible alpha bounds, the way
  `centerComicHeroShot()` does, so the browser is launched with
  `--allow-file-access-from-files`; without it the card silently falls back to
  a plain contain-fit.
- **The site's viewport-relative sizes overflow a 1080-tall frame.** The comic
  card's square art viewport is `min(58vw, 50vh, 52rem)` and its QR panel
  resolves taller than the band the card reserves, so a still lands the panel
  on the quote. `comic.html` caps both to the reserved band in a clearly marked
  override block; everything above it is the site's CSS, unchanged.
- **The QR reproduces as an inverted code** — light modules on near-black —
  because `filter: invert(1)` is what the site publishes. Copied, not
  corrected.
- **A still cannot cross-fade.** The site dissolves between hero shots over
  0.35s; the burn cuts between stills on the same slot arithmetic
  `getComicHeroShotIndex()` uses, and the difference is recorded rather than
  faked.
- **`clip-path` opens a stacking context**, so a hairline drawn as a
  `z-index: -1` pseudo-element paints *over* the element's own background
  instead of behind it — a white box renders solid blue. The caption boxes nest
  a white panel 2px inside a blue parent instead.
