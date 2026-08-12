# Epic F — Nameplate v2: the face is the interface

**Parent:** #9 · **Depends on:** B, C, D, E · **Blocks:** G
**Design:** [`docs/plans/wolves/design.md` §6](../design.md)

The plate's field set is closed on purpose, and `docs/skills/plates.md` says the
only legal way to say something new is to **add the field to the data model
deliberately**. This epic is that deliberate addition, done once: an avatar, an
org band, a generated title, and a ribbon rack — then the vocabulary closes
again, with a test pinning the new set.

**Done looks like:** a contributor's plate carries a face you can recognize from
a couch, their affiliation's mark, "Shipwright of Kubernetes", and their ribbons —
and `tests/test_plate.py`'s closed-vocabulary test passes against the new set.

**Invariants for every sub-issue here**

- Every new field is authored or resolved. Nothing is improvised at render time.
- The avatar is the biggest thing on the plate. Chrome shrinks to make room.
- The existing plate keeps working: a lead with no avatar renders exactly as it
  does today.

---

## F1 — Extend the closed field set, once

**Labels:** `enhancement` · **Depends on:** —

Add exactly four fields to the plate spec: `avatar` (a path in `avatars/`),
`affiliation` (an org id), `ribbons` (the rack data), and keep `title` as it is.
Update `docs/skills/plates.md`'s field table, and update the
`test_no_plate_field_is_invented_beyond_the_reference_deck` allow-list in the
same commit.

**Acceptance**

- [ ] The allow-list grows by exactly these fields and no others.
- [ ] `docs/skills/plates.md` documents each new field with an example, and says
      where its value comes from (never from a manifest by hand).
- [ ] The rationale is recorded: this is the deliberate extension the skill
      allows for, not a drift.
- [ ] A plate spec with an unknown field is rejected, not ignored.

**Do not** add a role line, a pronoun row, an "AS <CHARACTER>" line, or a commit
count. The plate names a person; it does not describe them.

---

## F2 — Big PFP, small chrome

**Labels:** `enhancement` · **Depends on:** F1, B3

Draw the avatar at 220 px (20% of frame height at 1080p), floor 160 px, never
upscaled past the 460 px GitHub serves, masked to the plate's hex-crest language
with a thin ring in the person's own chrome. Shrink the box around it: the plate
sizes to its content and the scrim is only as wide as the text.

**Acceptance**

- [ ] Avatar ≥ 160 px and larger than every other element; a test measures it.
- [ ] Chrome (box fill, rules, crest, scrim) ≤ 35% of the plate's area — the
      "if it blocks the shot, let it be the face" rule, as arithmetic.
- [ ] A missing or withheld avatar renders initials in the same footprint, so
      layout never depends on a network fetch having worked.
- [ ] Determinism holds: same spec in, same bytes out (the existing test).

---

## F3 — 10-foot type and title-safe placement

**Labels:** `enhancement` · **Depends on:** F2

Today's plate has a 28.8 px eyebrow and sits at the 5% action-safe margin. That
is a monitor design. Android TV's canvas is 960×540 dp (1 dp = 2 px at 1080p),
putting its 34 sp body minimum at **68 px**; EBU R 095 puts *text* inside the 10%
title-safe box (1536×864 px). Raise the ramp's floor and move the row in.

**Acceptance**

- [ ] No text on any plate below 34 px at 1080p; the name is ≥ 48 px.
- [ ] The plate row sits inside the 10% title-safe box, and a test asserts the
      rendered bounding box does.
- [ ] Existing plate tests are updated in the same commit, with the margin
      constants named after the standard they come from — the file already names
      the CSS rule each constant came from, so keep that habit.
- [ ] A plate at the new ramp still fits the frame with the longest real name and
      title in `vocab/casting.yaml`.

---

## F4 — Fonts that exist off Fedora

**Labels:** `bug` · **Depends on:** —

`plate.py`'s `FONT_CANDIDATES` lists only Fedora paths
(`/usr/share/fonts/dejavu/DejaVuSansMono.ttf`), so every plate test fails with
`RuntimeError: no regular monospace font found` on Debian/Ubuntu — including a
plain CI container, where the same font lives at
`/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf`. The chatter renderer (G)
will share this resolution path, so fix it before it is duplicated.

**Acceptance**

- [ ] Debian/Ubuntu paths added; `tests/test_plate.py` passes on a bare CI image.
- [ ] Resolution stays ordered and explicit — first existing candidate wins, and
      the error still lists everything it tried.
- [ ] One font resolver, used by both the plate and the chatter renderer.
