# The status nameplate

Reference for [`docs/skills/plates.md`](../plates.md). Split out of it to keep
the skill inside its size budget; this is the detail needed when changing the
HUD card's chrome, not when planning a cut.

The site's **top-of-frame HUD** is not the reveal plate. It is persistent
chrome that the intro overlay re-labels per cue, ported from
`projectbluefin/website` `src/components/wolves/cinematic/Nameplate.vue` on the
tokens in `src/style/wolves-cinematic.scss`.

## The field set

Exactly two authored lines, plus one chrome flag:

| Field | Example |
|---|---|
| `detail` | `Legends Sought` — the small eyebrow |
| `label` | `Follow the path, we've got your back` |
| `glitch` | `true` — the `#nova4ever` interference burst |

Both lines are uppercased on render (`text-transform: uppercase`).

## Where its copy is authored

Two read-only places, and it is **reproduced from them, never written**:

- **Per-cue overrides** — `src/data/wolves-intro-sequence.ts`, as
  `nameplateDetail` / `nameplateTitle` on a cue carrying `statusOnly`.
- **The segment default** — `INTRO_DISPLAY` in `src/WolvesApp.vue`. This is
  easy to miss: the HUD is *persistent*, so a segment that only reproduces the
  per-cue overrides renders a card that pops in and out, when on the site it is
  on screen continuously with the default showing between cues.

## Constants

| Constant | CSS |
|---|---|
| `STATUS_PANEL` | `--wc-panel: rgb(14 16 20 / 88%)` |
| `STATUS_LINE` | `--wc-line: rgb(96 165 250 / 28%)` |
| `STATUS_ACCENT` | `--wc-gold: #60a5fa` |
| `STATUS_WHITE` | `--wc-white: #e9e9e5` |
| `FS_STATUS_DETAIL` / `LS_STATUS_DETAIL` | `.wc-label`: 1.1rem, `0.32em` |
| `FS_STATUS_LABEL` / `LS_STATUS_LABEL` | `.wc-nameplate-label`: 2.2rem, `0.06em`, weight 700 |
| `STATUS_PAD_*` | `padding: 1.2rem 2.4rem 1.2rem 1.6rem` |
| `STATUS_RULE` | `border-left: 2px solid var(--wc-gold)` |
| `STATUS_CHAMFER` | `.wc-plate` clip-path, `0.9rem` |
| `STATUS_INSET` | `.wc-intro-nameplate { top: 3rem; left: 3rem }` |

> **`--wc-gold` is the token's NAME, not its value.** It resolves to `#60a5fa`,
> a blue. Reproducing the name instead of the value renders this card gold and
> wrong — the same class of mistake as reading a variable and believing its
> label over its contents.

## The glitch

`@keyframes wc-nameplate-glitch`, reproduced at its 0% keyframe:

```css
text-shadow: 2px 0 0 rgb(255 0 64 / 75%), -2px 0 0 rgb(0 220 255 / 75%);
clip-path: polygon(0 0, 100% 0, 100% 42%, 0 42%, 0 58%, 100% 58%, 100% 100%, 0 100%);
```

- The split is a **text**-shadow, so it is applied to the type layer and not to
  the panel. Splitting the finished card fringes the plate's edges instead and
  leaves the words looking untouched.
- The clip-path **tear** cuts the 42%–58% band out of the whole card.
- The animation's `transform: skewX()` is **not** reproduced. A burned-in plate
  is one still per cue; at 0.45s the burst reads as interference either way,
  and a still cannot honestly represent a mid-animation frame it was never
  sampled at.

## Two behaviours worth knowing

- **It is a different row from the lower third.** The one-plate-at-a-time check
  exempts a status card against a Guardian plate — on the site they are *meant*
  to be on screen together, the HUD above and the reveal below. Two status
  cards at once are still an error.
- **The rotating dinosaur avatar badge is deliberately not drawn.** It is
  animated brand artwork rather than copy, cycling on a 20-second timer
  (`AVATAR_ROTATE_MS`) that no still can represent honestly. A frozen stand-in
  would put a picture on the card that nobody authored, so it is omitted and
  recorded rather than approximated.
