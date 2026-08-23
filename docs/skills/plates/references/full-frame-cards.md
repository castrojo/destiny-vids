# Full-frame cards: the act slide and the comic title card

Reference for [`../SKILL.md`](../SKILL.md). Split out of it to keep
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
| `cards/maintitle.html` | `.wolves-intro-overlay-text-slim`, with the two lines' treatments swapped at the owner's request |
| `cards/bookline.html` | one owner line seated on moving picture — `maintitle.html`'s `.lockup` face and halo, nothing else |
| `cards/render-cards.mjs` | the driver — playwright, 1920x1080 at 1x, `omitBackground` |

```bash
ln -sfn ~/src/website/node_modules node_modules     # playwright is not vendored
node cards/render-cards.mjs --manifest <manifest> --out-dir <plates-dir>
node cards/render-cards.mjs --manifest <manifest> --out-dir <dir> --only id1,id2
```

## The seared divider

A ` | ` inside a `title` or a `body` line is **drawn**, not typed: `maintitle.html`
replaces the typeface's pipe glyph with a vertical rule carrying the film's blue
sear. The three colours are `tools/credits.py`'s own `SEAR_MID` / `SEAR_HALO` /
`SEAR_FLARE`, because act VIII already implements this treatment from the
owner's instruction — *"blue sear with heat for the big ones"*. **A sear here is
blue heat, not amber**; the obvious warm reading is a second, contradicting
definition of a treatment that already exists.

The string is untouched. Only the spaced form ` | ` matches, because a pipe
inside a word is not a divider and a card must not guess which one an author
meant.

## Query parameters that are not copy

`stage`, `variant`, `angle` and `size` travel the same query string as the
authored fields and change no string:

| Param | What it switches |
|---|---|
| `stage` | the main title's two beats — `title`, then `credits` |
| `variant` | the eyebrow's weight option, `b`..`e`, or `poster` for a CTA-first end card |
| `angle` | a `bookline`'s tilt in degrees, so it can sit on a tilted page |
| `size` | a `bookline`'s type size, for a beat that runs to two lines |
| `placement` | where a `daycard`'s line sits vertically over its wallpaper |
| `glyph` / `glyph_src` | a mark that stands in for one letter of the title |

**The house display face is Adwaita Sans.** Owner: *"inter should not be used
our font is adwaita"*. It ships the full ramp — Thin, ExtraLight, Light,
Regular, Medium, SemiBold, Bold, ExtraBold, Black — so every `font-weight`
between 100 and 900 is a real, distinct face.

That is a change from what these cards were authored against. The old stack was
the website's — `'Inter', 'Arial Narrow', sans-serif` — and neither of the first
two is installed here, so it fell through to DejaVu Sans: Book (400) and Bold
(700) and nothing between. CSS font matching snapped 500 down and 600 up, so a
"400/500/600/700" option set was two options wearing four names, and the
variants had to reach for weight, stroke width (`-webkit-text-stroke`, the only
continuous lever), contrast and size instead.

**The eyebrow variants have not been re-cut as a weight ramp**, even though they
now could be. They are the ones the owner picked by eye, rendered **over the
frame they ship on** rather than on a swatch, because half of "too thin" is
contrast against the picture underneath. Re-deriving them from a number would
discard that judgement.

**The Guardian nameplates are a separate decision and use DejaVu Sans Mono.**
`tools/plate.py` pins it explicitly and `test_the_font_stack_resolves_the_way_the_browser_did`
guards it: the reference plates were baked by a headless browser that fell
through to DejaVu Sans Mono, and preferring the desktop's Adwaita Mono rendered
them in a face that matched neither the stack nor any already-shipped video.
Do not "fix" that to Adwaita for consistency.

## A poster CTA over a wallpaper

`variant: "poster"` is still the title-card shape — `title`, `subtitle`, then
`body[]` — with the first body row treated as the CTA and later body rows as
the tag footer. It does **not** add a copy field.

When a poster has to enter in beats, use two cards with the same authored
fields:

| Stage | What is visible |
|---|---|
| `title` | event and venue; `body[]` stays invisible but keeps its layout seat |
| `cta` | first body row and tags; title, subtitle, and hairline are invisible but keep their layout seat |

That keeps the CTA from jumping when it arrives. A card that says it is
`stage: "cta"` but omits the event fields is structurally wrong: the empty
fields collapse the seat the CTA was timed against.

For a wallpaper that must start bright and become dark, split its ffmpeg input
before giving it to the bridge and both end-card legs:

```text
[5:v]split=3[bridge_day][poster_day][poster_dark];
[poster_day]...trim=0:<hold+fade>...[day];
[poster_dark]...trim=0:<total-hold>...,eq=brightness=-0.55[dark];
[day][dark]xfade=transition=fade:duration=<fade>:offset=<hold>[poster_bg]
```

Do **not** reference `[5:v]` independently in three filter branches. FFmpeg's
documented duplication primitive is `split`; explicit branches are the
contract, not incidental framesync behavior. `xfade` starts at its `offset`
relative to the first leg. Its output lasts `first + second - duration`, so
choose the two trim lengths such that the transition occupies the requested
window exactly. Source: FFmpeg documentation via Context7
`/websites/ffmpeg_documentation`, “Split input streams” and “xfade”.

## A panel that hides something leaves with the shot, not on its own clock

A box over picture is often there to **cover** what is underneath. The moment
it is, its exit stops being a styling choice: every frame where the box has
gone and the picture has not cut is a frame showing the thing the box was
hiding.

Two ways to get this wrong, and this repo shipped both in one afternoon:

| Attempt | What the audience saw |
|---|---|
| Fade the box out before the cut | The panel is semi-transparent for the whole ramp, so the picture underneath reads *through* it — and if that picture is printed words, two sets of words at once. |
| Cut the box out before the cut | Cleaner, and still wrong: the bare picture plays for the rest of the shot. Here the page went on printing, so a line the box existed to cover appeared in the clear. |

**The fix is structural, not a timing tweak.** Composite the card onto the
**shot's own leg** of the join, before the transition:

```text
[head][card]overlay=...:enable=between(t\,<in>\,<shot_end>)[headcard];
[headcard][tail]xfade=transition=fade:duration=<d>:offset=<shot_end - d>[film]
```

Now the card and the picture are one image by the time the transition runs, so
they leave together and there is no in-between frame to get wrong. It also
answers "do not cover the incoming shot" for free: the outgoing leg's weight
reaches zero at the same instant the incoming shot is clean.

Keep the per-plate `fade` option (`"fade": 0` to switch it off) for cards that
are only type — those genuinely want a ramp, because there is no panel to see
through.

Two supporting rules:

- **The panel itself is opaque.** A 90% fill still lets printed words underneath
  read at full card opacity, which is the same fault standing still.
- **Check what the picture does under the card for the whole window**, not at
  one frame. A shot that looks static can be printing type, drifting, or cutting
  to a close-up inside its own boundaries.

## Blue letters are opt-in, per card

The project's b/f rule — every `B` and `F` in the film's blue,
`tools/blueletters.py` — is asked for by `blue_letters=true`, never applied by
a template on its own. `cards/ending.html` and `cards/bookline.html` both gate
it that way.

A card is allowed not to ask. At display sizes over a printed page a recoloured
letter mid-word reads as a typo rather than as branding, and the owner has
switched it off for exactly that reason. Switching it off on one card is not a
change to the rule; a template that applies it unconditionally is, because then
no card can decline it.

## Sizing a card: render the candidates over the frame they ship on

The same weight rule applies to
type size and leading, and for the same reason: half of "too small" is the
picture behind the type, so a swatch cannot answer it.

Composite each candidate over a real frame pulled from the source at the beat's
own timecode, and give the owner the set:

```bash
ffmpeg -v error -y -ss <t> -i media/<video_id>.mkv -frames:v 1     -vf "pad=1920:1080:0:<pad_y>:color=black" /tmp/frame.png
node cards/render-cards.mjs --manifest <manifest> --out-dir /tmp/cards --only <id>
# then alpha-composite plate over frame with Pillow and report the box size
```

Report each candidate's **box dimensions in pixels of the 1920x1080 frame**
alongside the CSS values. "3.8rem" means nothing to the person choosing;
"1168x514, the largest that still clears the letterbox bars and the page
gutter" is the decision they are actually making.

## Where a line sits is authored, and it is measured

A card over a wallpaper has one readability decision in it — which horizontal
band of that picture the type sits on — and the band that works is a property
of the *image*, not of the card. So the seat travels on the plate (`placement`)
and the template carries the named seats, rather than one hard-coded `top`.

**Measure it; do not nudge it.** Composite the rendered PNG's alpha bounding box
against the wallpaper and read the luminance under the glyphs:

```python
from PIL import Image
bg = Image.open("renders/wallpapers/03-day.png").convert("L").resize((1920, 1080))
x0, y0, x1, y1 = Image.open("renders/plates-x/plate_card.png").split()[3].getbbox()
px = bg.load()
vals = sorted(px[x, y] for y in range(y0, y1, 3) for x in range(x0, x1, 4))
print(sum(vals) / len(vals), vals[int(len(vals) * .95)])   # mean, p95
```

The **95th percentile matters more than the mean**: a dark band with a few
bright specular hits is what actually eats a glyph. Compare candidate seats
against each other and keep the numbers in the plate's note, because the next
person to move the line needs to know which seats were already rejected.

Luminance is not the only test. **The subject of the picture outranks it** — a
darker band that lands the line across the face or head of whatever the image is
of is the wrong band, and it is the correction an owner makes immediately.

## Moving-picture type is measured across its whole window

Deck greys belong on a slide's black, not automatically on footage. `--wc-grey`
(`#8b8f96`) and the secondary `#cbd5e1` can read over a dark cue and vanish
when the image changes. Measure the luma under the card's full window with
`signalstats` → `YAVG`, not only the frame where it was cued. FFmpeg documents
that `signalstats` records Y-plane average statistics; provenance:
`/websites/ffmpeg_documentation`, “signalstats” (verified through Context7).

This is incident-derived: the prologue's main title was cued over a near-black
void, then the source cut to a white starburst **1.3 seconds later**, inside the
same card. A still approval did not prove the window readable.

**Protect the glyphs, never readability with a scrim panel.** A scrim diagnoses
the contrast problem and creates the wrong object over moving picture: a visible
box the owner will call out. Give the letters a tight near-opaque core and wider
soft falloffs so the protection travels with the glyphs and has no edge. The
radial wash in `act.html` is for a slide, where nothing moves behind it. This
does not weaken the structural panel rule above: an opaque panel that hides
source content must leave with that shot; it is not a contrast treatment.

## A looped still needs a finite bound

`loop=loop=-1` is an **infinite** stream. Without a bound, `overlay` framesync
can keep producing output after the main input ends by repeating its final
frame. The prologue's first build emitted the film, then eight seconds of frozen
last frame; the material after it never played, and ffmpeg still exited 0.
Trim the still to the picture's length and add `shortest=1`. FFmpeg's documented
looping-overlay example uses `shortest=1` to synchronize output duration;
provenance: `/websites/ffmpeg_documentation`, “Overlay Looping GIF” (verified
through Context7). The incident was caught by pulling three identical frames,
not by watching a process exit successfully.

## An authored glyph standing in for a letter

A mark replacing one letter — the Kubernetes helm as an `o` — travels as the
`glyph` / `glyph_src` pair, which `cards/ending.html` defines and other
templates reuse:

```json
"glyph": { "token": "o", "word": "Extinction" },
"glyph_src": "renders/marks/kubernetes.svg"
```

`token` is the letter, and the optional `word` scopes the search so the mark
lands in the intended word rather than on the first matching letter in the line.
Every template that draws one falls back to the plain letter on `img.onerror`,
because `renders/` is not committed and a checkout without the mark must still
produce the word.

**The record places the mark, never the template.** A template that matches a
word — `title.toLowerCase().lastIndexOf('evolve')` — makes the mark vanish
silently the first time the copy is rewritten, which is a card quietly losing an
authored element with no error and no failing test.

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
