# Plate styling provenance

Reference for [`docs/skills/plates.md`](../plates.md). Split out of it to
keep the skill inside its size budget; this is the constant-by-constant
record of where the plate's look came from, needed when changing chrome or
porting the treatment, not when planning a cut.

Ported from `projectbluefin/website`
`src/components/wolves/WolvesIntroOverlay.vue` (`.wolves-guardian-plate` and
friends): near-black translucent fill, chamfered corners, thin blue-white rules,
hex crest with chevron, uppercase letter-spaced eyebrow. The CSS is the source
of truth; `tools/plate.py` names the rule each constant came from so the two can
be diffed by eye. The entrance animation is deliberately not reproduced — a
still plate keeps the burn one ffmpeg pass instead of an image sequence.

**Where the site and the videos disagree, the videos win.** The plates in the
other cuts were baked by a headless browser from
`~/Videos/wolves-{kat,natali}/render/reveal.html`, which is a deliberate literal
2× of `.wolves-guardian-plate` — and it diverges from the live site in ways that
are immediately visible side by side:

| | Site CSS | Baked reveal (**use this**) |
|---|---|---|
| Class row case | `text-transform: uppercase` | authored case — "Behemoth Titan" |
| Class colour | `#bfdbfe` | `#cbd5f5` |
| Title colour | `#94a3b8` slate | `#93c5fd` blue |
| Title tracking | none | `0.08em` |

The **font** is the one that reads as broken from across the room. The stack is
`ui-monospace, 'SFMono-Regular', 'Cascadia Mono', monospace`; neither Apple's
SF Mono nor Cascadia Mono ships on a Fedora atomic host, so the browser fell
through to the fontconfig generic — **DejaVu Sans Mono**. Adwaita Mono is the
desktop's monospace and *is* installed, so preferring it silently rendered every
plate in a typeface that appears in neither the stack nor any other video.
Check with `fc-match monospace` before assuming.

Also carried from the baked reveal: the name's gradient has a **middle stop**
(`#fff 0%, #e2e8f0 60%, #a0aec0 100%`), the type has a `text-shadow`
(`0 2px 10px rgb(0 0 0 / 80%)` — it matters, the plate is translucent and
footage moves behind it), and the box applies `border-radius` *and* a
`clip-path`, so two corners are chamfered and the other two are rounded.

The `ov/*.py` renderer described in `~/Videos/OVERLAYS.md` **no longer exists**;
`tools/plate.py` is the live implementation.
