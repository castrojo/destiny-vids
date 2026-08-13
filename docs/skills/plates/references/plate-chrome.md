# Owner-authored plate chrome

The detail behind [`../plates.md`](../SKILL.md)'s "Owner-authored chrome"
section: four additions the owner briefed directly. All four are **chrome and
imagery, not copy** — none adds a row of text the reference deck has no field
for, so the closed field set is untouched. They ride in a manifest entry — or
on a binding's `plate:` block in `vocab/casting.yaml`, which the
closed-vocabulary test allows as chrome flags — but **not** in a brief's
`copy`, whose schema pins the text rows only. `variant: bazzite` is the
exception: `variant` was already in the brief's set, so a brief may ask for
the purple.

## `avatar` — a profile picture in the crest

The value is a *local image path*; GitHub avatars are the source
(`https://avatars.githubusercontent.com/u/<id>?v=4`, e.g. `/u/52753`), fetched
and cached ahead of time — **the renderer never touches the network**. A
relative path resolves against the repo root.

The photo is cover-fit (CSS `object-fit: cover`: scaled to fill,
centre-cropped) and masked to the crest's inner hex, with the hex rules kept
drawn over it, so the card's geometry is unchanged. This is the implemented
answer to `reveal.html`'s `pfp` (see "Known divergences" in the parent
skill): the baked reference hid the hex crest behind a rectangular photo;
here the crest keeps its shape and the photo takes its fill, which is what
"composited into the crest" means at this card's size.

The chat pill's badge slot takes `avatar` too, masked to the circle
`plate.html` bakes (`.avatar`/`.pfp`: an 84px circle at 2x). The slot was
always reserved in the layout, so the pill's size does not move.

A missing or unreadable file degrades to the drawn crest with a stderr note —
a punch-list item, never a crash (degrade, never block).

## `wreath: true` — the struck laurel

A laurel ring around the crest, in the plate's own accent metal: the ring a
game draws around a max-level portrait. The brief was **restraint** — one
metal, no glow bloom, no second light source, nothing fighting the type —
and **scarcity**: exactly two people in the whole show carry it, and the
renderer never adds one by itself. Who carries it is casting
(`vocab/casting.yaml`), never a per-render whim.

Construction (`_wreath` in `tools/plate.py`): two branches of seven leaves
rise from an open bottom (a 35° gap, where a laurel ties) and stop short of
the top; leaves grow toward the middle of the branch. The "struck" relief is
the *same* accent metal darkened for the midrib and stem — engraving, not a
light source. The header rules shorten around the laurel's canvas; the card's
box and every row of type stay exactly where they were, and a test pins both
the presence of the leaves and a coverage ceiling on the ring (a struck
laurel, not a solid ring).

## `variant: "bazzite"` — purple chrome

For the three end-fight plates: "have his namebadge glowing purple, he is
special but don't say why". Same geometry, same closed field set, only the
colour changes — a variant like `rust` and `leader`, not a second kind of
card. The plate says **nothing** about why they are special.

The purples are **verified** from the official logo (`ublue-os/bazzite`,
`repo_content/Bazzite.svg`):

| Value | Source |
|---|---|
| `#8A2BE2` (accent, border) | logomark gradient end stop (`paint0_linear`) |
| `#0047AB` (logomark gradient start) | logomark gradient start stop |
| `#5835ce` (`glow`) | the wordmark's fill |
| `#c4b5fd` / `#ddd6fe` / `#a78bfa` (label / class / title) | Tailwind violet-300/200/400 — the wordmark purple is too dark to set type in on the translucent plate, so the text rows take the same palette family's tints. The type stays legible: a hum, not a glow. |

The crest carries the Bazzite logomark — the gradient tile with its white
D-pad, button ticks, and "b" — traced from the same SVG's path geometry
(`_bazzite_tile`). With an `avatar` set, the photo masks to the tile's
silhouette and the glyph is not drawn over a face: the tile's shape is the
logo, and the brief was "use the bazzite logo and his PFP".

## `[ REDACTED ]` as a name

The literal string goes in `name`. It is *authored copy* — the deck itself
carried `Subclass [ REDACTED ]` until the owner supplied Amber's class — so
it is not a new field, just a wide one: the box grows to fit it and nothing
special happens at render time.

Three names render bracketed: `[ REDACTED ]`, `[ p5 ]`, and `[ EyeCantCU ]`.
The last two are **real people whose GitHub handles the owner deliberately
chose instead of their real names** — the bracketed handle IS the authored
copy, not a placeholder awaiting resolution. Never "helpfully" substitute a
real name for one; a name change is the owner's edit, in the vocab. (For
`[ REDACTED ]` too: where it stands in for a word the owner has not supplied
yet, the owner supplies the real word, in the vocab.)

## Red flags specific to this chrome

- Fetching an avatar at render time. The renderer is offline; cache the file
  first and point `avatar` at the local path.
- A bazzite plate that explains itself. The purple is the whole statement;
  adding a "why" row is invented copy on a real person's card.
- A wreath that glows, sparkles, or appears on a third person. Struck metal
  around exactly two people is the brief; gaudy is overdone.
- Treating `[ REDACTED ]` as a placeholder to "fix" (see above).
