---
act: III
manifest: stories/yt_curse_of_osiris_opening_cinematic-fixed-plates.json
# WHERE THIS ACT STARTS IN THE PROGRAMME, in seconds. Measured, not guessed:
# the running order's segment durations summed from a
# `tools/megacut.py stories/megacut/megacut.json --dry-run` on 2026-08-21 --
# prologue 101.200 (megacut.json item 0 `dur`) + act I 116.200 + Perfume
# movement 2 66.400 + act II 359.968 = 643.768.
# Restate the derivation when the running order moves.
programme_start: 643.768
# This act's fixed plates come from this file, so the manifest is regenerated
# from it: `python3 tools/chapter_md.py sync III --write`.
owns_plates: true
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

**Only the act's two fixed opening pills are here.** The conversation that
carries the rest of act III is *recovered speech*, not authored copy: it lives
in `dialogue/<video_id>/` with source timecodes and per-line evidence, beside
the `DIALOGUE.md` the owner edits. That record is provenance. Editing it here
would be writing words into somebody's mouth, which is the one thing this
repository never does.

The speaker below is `[redacted]` on purpose — he is revealed later in the
programme, in act VI.

## 10:47.335

[retirement-1] [redacted] @ 10:47.335 +2.125: Finally, retirement

[retirement-2] [redacted] @ 10:49.710 +2.125: The long walk beckons

Bob's gold trustee plate is **not** authored here. Its `copy_source` is
`casting`, so every row on it resolves from his binding in
`vocab/casting.yaml`, and a chapter file cannot author derived copy. It lives
in the manifest and is carried through untouched, exactly as act VI's roster
nameplates are.

The sign over the maintainer-email beat sits in the picture's upper-right safe
area rather than the lower third, so it does not collide with the pills below.

## 13:14.728

* [maintainer-emails] title @ 13:14.728 +4.0
  - position: top-right
  - copy_source: owner_supplied
  - title: Maintainers Reading Emails
  - subtitle: And Other Preposterous Tales
  - body: Summer 2027
