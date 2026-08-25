---
act: VIII-fixed
manifest: stories/08-credits.json
plates_key: fixed_cards
# NO CLOCK, and no ids: these cards are addressed by their ORDER, which the
# owner set deliberately. `dur_sec` is a real duration here, not a weight.
timed: false
# Nothing here is pinned to a second. This is where the chapter falls in the
# running order, so a read-through of the whole show puts it in the right
# place -- it is never used to seat a card. Act VIII starts at 1828.383,
# summed on 2026-08-25 the way tools/megacut.py's item_duration sums it
# (an authored trim window is trim_to MINUS trim_from): act VII's start
# 1587.060 (see chapters/VII-europa.md) + act VII 108.400 + the mission
# pause 23.423 + Perfume 5 3.760 + Perfume 5-ending 105.740.
programme_start: 1828.383
list_keys: names
owns_plates: true
# No `field_order`: these three cards do NOT agree on one. The first card
# reads role-first and the other two lead with their provenance note, which
# is how they are committed, so the rows below are the order.
defaults:
  kind: null
  position: null
  copy_source: null
  text_source: null
  avatar: null
  avatar_url: null
---

# Act VIII — the fixed credits

The three named cards that open the credits, after the comic reveal and
before "Contributions by YOU". **The order is the owner's and it is not the
obvious one** — the director gave up the opening slot so the people who
created Bluefin lead. Do not "fix" it back.

The roster walls that follow are **not here**: they are generated from
`stories/roster-*.json`, which is the one place those names live. A name
belongs in the roster, never typed in twice.

## the named cards

* -
  - role: Bluefin Created by
  - names: Jacob Schnurr
  - names: Andy Frazer
  - names: Marco Ceppi
  - names: Jorge O. Castro
  - dur_sec: 6.0
  - _what: "FIRST OF THE CREDITS, by the owner's revision on 2026-08-13: 'Put jorge castro before contributions by you so the bluefin creators get credit.' The credits open AFTER the comic reveal -- the owner moved them: 'Move the existing credits to after the comic reveal' -- so this is the first card the audience reads once the cover has landed. On 2026-08-23 he deleted the separate 'Directed by' card and put himself and Marco Ceppi on this one instead: the four names who created Bluefin, credited together, with no directing credit anywhere in the film. The deleted card is in git."

* -
  - _what: "Reproduced as the bed record spells it (music/bed_wish_i_had_an_angel.json, artist: Nightwish); the session note's 'Nightwise' is a typo, and a band's name is copy, not something to pass through unchecked."
  - role: Music by
  - names: Nightwish
  - dur_sec: 6.0
