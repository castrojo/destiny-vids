---
act: VIII-cta
manifest: stories/08-credits.json
plates_key: cta_cards
# NO CLOCK. These cards are not pinned to a second: `dur_sec` is a relative
# WEIGHT, scaled at build time into whatever window the comic reveal leaves.
# Changing one card's weight changes every other card's length, which is why
# removing a card here means moving its weight onto the cards that stay.
timed: false
# Nothing here is pinned to a second. This is where the chapter falls in the
# running order, so a read-through of the whole show puts it in the right
# place -- it is never used to seat a card. Act VIII starts at 1959.685,
# summed on 2026-08-27 the way tools/megacut.py's item_duration sums it
# (an authored trim window is trim_to MINUS trim_from): act VII's start
# 1718.362 (see chapters/VII-europa.md) + act VII 108.400 + the mission
# pause 23.423 + Perfume 5 3.760 + Perfume 5-ending 105.740.
programme_start: 1959.685
# No key in this run is a list: `body` here is one sentence under a name,
# not the several lines a book page carries.
list_keys:
owns_plates: true
field_order: _what, kind, text, eyebrow, name, body, scale, dur_sec
defaults:
  # Nothing here is a chat pill, so none of the pill chrome applies.
  kind: null
  position: null
  copy_source: null
  text_source: null
  avatar: null
  avatar_url: null
---

# Act VIII — the cries, before the cover drops

Three cards, in this order, between the credits and the comic reveal. The
words are **the owner's own**, quoted in each card's `_what`; reproduce them
exactly, including the casing, which is a treatment and not shouting.

Two cards that used to live here — MAKE YOUR OWN FATE and BECOME LEGEND —
were **removed** on the owner's instruction, and their combined weight was
folded into the first card below. Do not re-add them: the run was retuned
around their absence, and putting one back would silently shorten everything
after it.

## the cries

* cta
  - text: YOU ARE THE DREAM OF MANY ANCESTORS
  - scale: huge
  - dur_sec: 8.5
  - _what: The call to action, and now the ONLY cry before the birthday card and FIGHT. Owner, 2026-08-16: 'have the first slide in the credits be "you are the dream of many ancestors" and drop "make your own fate" and "become legend" and just have that one phrase, it's a much more powerful statement'. So two committed cards were REMOVED rather than demoted -- MAKE YOUR OWN FATE (large, 4.0) and BECOME LEGEND (huge, 4.5) -- and this line takes the weight of both, 8.5, so the birthday card and FIGHT keep the durations they were tuned to: cta dur_sec are RELATIVE weights scaled into the window the cover's own time leaves, so dropping a card without moving its weight would have silently lengthened every card that stayed. The wording is the owner's, set in the deck's uppercase like every other cry -- the same casing treatment 'seven days to the wolves' gets. ITS ONE BLUE LETTER IS THE F OF 'OF' -- checked on a rendered frame, not assumed: the first draft of this note claimed the line had no b and no f at all, and the render says otherwise. At `huge` it is above CTA_SEAR_FROM, so that F is seared like the cries it replaced.

* birthday
  - eyebrow: Happy Tenth Birthday
  - name: RAFAEL CASTRO
  - body: "We love you" - Mom and Dad
  - dur_sec: 5.0
  - _what: THE OWNER'S OWN WORDS, verbatim, replacing the 'Introducing' card: 'Change introducing Rafael to Happy Tenth Birthday / RAFAEL CASTRO / "We love you" - Mom and Dad'. The second, redacted name is GONE with the card that carried it and is recorded nowhere, which is what a redaction is for. This is the one card in the run set in the credit treatment rather than the seared one: it is a birthday card, not a battle cry.

* cta
  - text: FIGHT
  - scale: colossal
  - dur_sec: 9.5
  - _what: "Owner: 'FIGHT <--- I want this one up longer than the first 2 (do not touch the comic book reveal length.) HUGE BOLD FONT. BLUE F'. Its weight is longer than cards one and two put together, and it is the last thing on screen before the cover drops. Moved huge -> colossal on 2026-08-15 so that promoting the two cries above it did not quietly demote FIGHT to joint-largest: it is the biggest thing in the act and has to stay that way."
