# Keeping plates on the picture, and styling provenance

Reference for [`../SKILL.md`](../SKILL.md). Split out of it to keep the
skill inside its size budget. Letterbox-safe placement, and where the
treatment is ported from.

## Keep plates on the picture

Bungie's cinematics are 2.39:1 delivered in a 16:9 file, so roughly 140px at
the top and bottom of every frame is baked-in black. The row margins are
percentages, so measuring them against the *frame* drops a plate onto that bar
— it reads as a mistake, not a style, and it is the easiest defect to miss on a
still.

`render` and `burn` detect the real picture area with ffmpeg's `cropdetect` and
position against it:

```bash
python3 tools/plate.py render --manifest plates.json --fit-video media/<id>.mp4
python3 tools/plate.py burn --video base.mp4 --manifest plates.json \
    --fit-picture --out out.mp4
```

Detection falls back to the full frame when there is no letterbox, so passing
it is always safe.

## Styling provenance

The plate treatment is ported from the website's `WolvesIntroOverlay.vue`, and
where the site and the baked video reveals disagree, **the videos win**. The
constant-by-constant record — the four known divergences, the font trap
(`fc-match monospace`), and the gradient, shadow and chamfer details — lives in
[`references/plate-styling.md`](plate-styling.md).

The port covers the *deck's* shapes only. The two **full-frame** cards — the act
slide and the intro's comic title card — are still live on the site, so they are
rendered from its own CSS by `cards/render-cards.mjs` rather than ported;
`tools/plate.py` refuses one and names the driver. See
[`references/full-frame-cards.md`](full-frame-cards.md).

