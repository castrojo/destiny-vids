---
act: III
manifest: stories/yt_curse_of_osiris_opening_cinematic-fixed-plates.json
# WHERE THIS ACT STARTS IN THE PROGRAMME, in seconds. Measured, not guessed:
# the running order's segment durations summed from a
# `tools/megacut.py stories/megacut/megacut.json --dry-run` on 2026-08-21 --
# prologue 101.200 (megacut.json item 0 `dur`) + act I 116.200 + Perfume
# movement 2 66.400 + act II 364.068 = 647.868.
# (act II grew 4.100 on 2026-08-24, when its hallway pause was extended to
# carry the cortney exchange; 359.968 -> 364.068.)
# Restate the derivation when the running order moves.
programme_start: 647.868
# This act's fixed plates come from this file, so the manifest is regenerated
# from it: `python3 tools/chapter_md.py sync III --write`.
owns_plates: true
# THE INTERMISSION THAT PLAYS AFTER THIS SECTION IS AUTHORED AT THE BOTTOM OF
# THIS FILE. Any block whose heading carries this label is the deck, not the
# act: its slides never reach the act's manifest and are rendered as their
# own short film by `scripts/build_intermission.py`. The owner's reason for
# the arrangement is that the deck IS the concluding text of Bob's scene, so
# it is edited where the rest of his scene is edited.
deck: intermission
field_order: id, kind, at, dur, position, copy_source, speaker, text
defaults:
  kind: chat
  position: left
  copy_source: owner_supplied
  # These two pills carry no chrome at all -- no avatar, no fades. A default
  # of `null` removes the field rather than inventing it.
  text_source: null
  avatar: null
  avatar_url: null
---

# Act III — mrbobbytables, and the long walk

**Only the act's one fixed card is here.** The conversation that
carries the rest of act III is *recovered speech*, not authored copy: it lives
in `dialogue/<video_id>/` with source timecodes and per-line evidence, beside
the `DIALOGUE.md` the owner edits. That record is provenance. Editing it here
would be writing words into somebody's mouth, which is the one thing this
repository never does.

[redacted]'s retirement conversation opened this act until 2026-08-24, when
the owner moved it to act II verbatim — "10:24 is where redacted's
'retirement conversation' should go, not in the next chapter" — onto the
Cayde-6 shot that closes act II's picture. It lives in
`chapters/II-endless-forms.md` now; the speaker is still `[redacted]` on
purpose, revealed in act VI. (This file's title keeps "the long walk" as
authored; renaming it is the owner's call, flagged in the change that moved
the lines.)

## 13:18.828

* [maintainer-emails] title @ 13:18.828 +4.0
  - position: top-right
  - copy_source: owner_supplied
  - title: Maintainers Reading Emails
  - subtitle: And Other Preposterous Tales
  - body: Summer 2027

Bob's gold trustee plate is **not** authored here. Its `copy_source` is
`casting`, so every row on it resolves from his binding in
`vocab/casting.yaml`, and a chapter file cannot author derived copy. It lives
in the manifest and is carried through untouched, exactly as act VI's roster
nameplates are.

The sign over the maintainer-email beat sits in the picture's upper-right safe
area rather than the lower third, so it does not collide with the pills below.

**The intermission.** The deck below plays **after** this section — after act III and after
Perfume's third movement, in the slot before act IV. It is the concluding
text of Bob's scene, so it lives here rather than in a file of its own.

Two things about that seat are deliberate. The act III → movement 3 join is a
hard cut covered by the Vex gate blooming to white (`_hard_out` on that item
in [`megacut.json`](../stories/megacut/megacut.json)); putting slides inside
it would break the one frame doing the most work. And the intermission is
where a **different song** goes — the owner's, not Perfume's — which is why
it is its own segment with its own audio rather than an overlay on the
movement.

**Every word below is a placeholder.** Nobody has written this copy yet, so
each row carries lorem ipsum and a source marker reading `placeholder`, which
is how `python3 tools/placeholder.py list` finds it again. Replace the words
and flip that marker to `owner_supplied`. The timing, the pacing and the read
length are reviewable now, which is the whole point of shipping a slot with
Latin in it rather than shipping a gap.

```bash
python3 scripts/build_intermission.py --write     # regenerate the manifest
python3 scripts/build_intermission.py --render    # and the film
```

## 15:22.916 intermission

* [intermission-1] slide @ 15:22.916 +6.0
  - position: slide
  - copy_source: placeholder
  - label: Lorem ipsum
  - label_source: placeholder
  - title: Dolor sit amet consectetur adipiscing elit
  - title_source: placeholder

* [intermission-2] slide @ 15:29.716 +6.0
  - position: slide
  - copy_source: placeholder
  - label: Sed do eiusmod
  - label_source: placeholder
  - title: Tempor incididunt ut labore et dolore magna
  - title_source: placeholder

* [intermission-3] slide @ 15:36.516 +6.0
  - position: slide
  - copy_source: placeholder
  - label: Ut enim ad minim
  - label_source: placeholder
  - title: Veniam quis nostrud exercitation ullamco laboris
  - title_source: placeholder

* [intermission-4] slide @ 15:43.316 +6.0
  - position: slide
  - copy_source: placeholder
  - label: Duis aute irure
  - label_source: placeholder
  - title: In reprehenderit voluptate velit esse cillum
  - title_source: placeholder
