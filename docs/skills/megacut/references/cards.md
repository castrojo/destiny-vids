# Cards are reproduced, not designed

Part of the [megacut skill](../SKILL.md).

## Cards are reproduced, not designed

A card that exists on the website is **rendered from the website's own rules**.
`cards/act.html` and `cards/comic.html` copy the CSS out of
`CinematicTransition.vue` and `WolvesIntroOverlay.vue`, and
`cards/render-cards.mjs` screenshots them with playwright — the same pattern
`~/Videos/wolves-{kat,natali}/render/plate.html` and
`nimbatus-review/render/endcard.html` have always used.

Re-implementing one in Pillow gets you a second, drifting version of chrome
that already exists; `tools/plate.py` refuses a card kind outright and names
the driver instead. The Python renderer is for the *deck's* shapes — the
Guardian plate, the small title card, the chat pill, the status HUD.

Two rules survive the move to a browser:

- **Copy still arrives in the manifest.** A row nobody authored is left out of
  the URL and does not render. The card templates default nothing.
- **A CSS comment containing `*/` truncates the stylesheet**, and the card then
  renders as unstyled black text on white — which is exactly what a path like
  `wolves-*/render/reveal.html` does inside a comment. A test pins it.

The plan is an ordered list of two kinds of item:

```json
{
  "output": "renders/<name>.mp4",
  "items": [
    {"kind": "card", "image": "renders/plates-x/plate_act1.png", "dur": 5.0},
    {"kind": "clip", "path": "renders/segment.mp4", "audio": "silent"},
    {"kind": "clip", "path": "/abs/path/deliverable.mp4", "audio": "source"}
  ]
}
```

`audio` has no default **on purpose**. A clip that silently defaulted to
silence would ship a mute segment that looks fine in every log, so the tool
refuses a clip that does not say which it is.

