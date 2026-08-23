---
act: "0"
manifest: stories/00-prologue-plates.json
# The prologue opens the show, so its own clock IS the programme's.
programme_start: 0.0
owns_plates: true
# The union of the orders the two card kinds already wrote in: a maintitle
# has a `stage`, a bookline has a `variant`, and neither grows a key the
# other has.
field_order: id, kind, stage, variant, at, dur, angle, size, label, accent, title, body, fade, anchor, anchor_out, note
defaults:
---

# Prologue — the main title

This file is where you write and rewrite the cards the show opens on. The
build (`python3 scripts/build_prologue.py`) reads it and writes
[`00-prologue-plates.json`](../stories/00-prologue-plates.json), which is
generated — never hand-edit it.

These are cards, not dialogue, so each one is a `*` row and its copy is the
`- field: value` rows underneath. A `- body:` row repeated is the card's
lines, in order — that is how a bookline keeps its four lines without
counting punctuation.

**The main title is the most-seen frame in the show.** Every card here is
pinned and given an explicit hold, because this act is delivered; change the
words freely, and touch a `@` or a `+` only when you mean to move the card.

```bash
python3 tools/chapter_md.py show 0
python3 tools/chapter_md.py check 0
```

## 0:11.000

* [maintitle-a] maintitle @ 0:11.000 +4.4
  - stage: title
  - label: PROJECT BLUEFIN
  - accent: BLUEFIN
  - title: seven days to the wolves
  - body: Music by Nightwish | Action by Bungie
  - note: Beat one: the lockup alone. It carries `body` so the credit rows still occupy their space -- they are merely invisible -- which is what makes the swap to `maintitle-b` invisible above the hairline. Fades up over 1.4s from 11.0, on the void, and is fully present before the 12.28 shot change.

* [maintitle-b] maintitle @ 0:15.400 +7.2
  - stage: credits
  - label: PROJECT BLUEFIN
  - accent: BLUEFIN
  - title: seven days to the wolves
  - body: Music by Nightwish | Action by Bungie
  - note: Beat two: identical card with the credit pair made visible, hard-cut in at 15.4 so only the credits appear. Holds, then fades out over 1.4s ending at 22.6 -- clear of the 24.88 cut.

**The mission briefing card is parked, not deleted.** The owner pulled it out
of the prologue on 2026-08-23 — *"get rid of that thanks for volunteering
slide"*, *"I will put it somewhere else"* — so it is unseated here and waiting
for the seat they choose. Its copy is authored and is reproduced verbatim
below so that re-seating it is a move, never a rewrite. Nothing else moved with
it; `book-a` stays at 34.0s, which the owner re-confirmed on 2026-08-22.

    id     mission-briefing
    kind   act
    dur    6.74
    label  PROJECT BLUEFIN MISSION BRIEFING
    title  Thanks for Volunteering
    body   Tophee Protocol Quick Insertion // ACTIVATED
    body   Agones Cluster // Cycling
    body   Mechaphippy Deployment // UNAUTHORIZED
    copy   owner_supplied

**`book-b` was not moved with `book-a`, and does not need to be.** It opens at
31.0s and runs to 34.9s, so on paper it starts *before* the card it follows —
but it carries an empty `body` and `scripts/build_prologue.py` never overlays
it, so the collision reaches no pixel. Verified on the rendered master, not
reasoned about. See the manifest's `unresolved`.

## 0:34.000

* [book-a] bookline @ 0:34.000 +6.74
  - variant: box
  - angle: 4.0
  - body: Two Generations of Contributors
  - body: One at their beginning
  - body: One at their end
  - body: These are their Real Stories
  - fade: 0
  - anchor: 1030
  - anchor: 443
  - anchor_out: 1030
  - anchor_out: 443

* [book-b] bookline @ 0:31.000 +3.9
  - variant: box
  - angle: -14.0
  - size: 3.0rem
  - body: []
  - anchor: 1000
  - anchor: 470
  - anchor_out: 1000
  - anchor_out: 470
