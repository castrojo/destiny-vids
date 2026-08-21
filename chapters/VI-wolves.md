---
act: VI
manifest: stories/06-wolves-cayde-plates.json
# WHERE THIS ACT STARTS IN THE PROGRAMME, in seconds. Measured, not guessed:
# the running order's segment durations summed from a
# `tools/megacut.py stories/megacut/megacut.json --dry-run` on 2026-08-21 --
# prologue 101.200 (megacut.json item 0 `dur`) + act I 116.200 + Perfume
# movement 2 66.400 + act II 359.968 + act III 160.200 + Perfume movement 3
# 114.848 + act IV 34.000 + act V 25.259 + the interstitial 5.259 = 983.075.
# Restate the derivation when the running order moves.
programme_start: 983.075
# This act's manifest holds BOTH kinds of plate: the pills below, and four
# `copy_source: brief` nameplates that resolve from the roster. This file
# authors only its own -- `sync` carries the nameplates through in place.
owns_plates: true
field_order: id, kind, position, speaker, avatar, detail, label, text, copy_source, at, dur, fade_in, fade_out_at, fade_out, seen_at_film, _note
defaults:
  kind: chat
  position: letterbox
  copy_source: owner_supplied
  avatar: auto
  fade_in: 0.6
  fade_out: 0.25
  # This act's pills start fading 0.6 s before their window closes, not
  # 0.25 s: the fade is a fade-IN's length long on the way out. That is what
  # is on the delivered master, so it is stated rather than re-derived.
  fade_out_at: derived 0.6
  text_source: null
  avatar_url: null
---

# Act VI — the wolves, and what is asked of you

Jorge Castro's six lines over his own close-up, and the Ghost's welcome an
act earlier. Act II plates him as `[ REDACTED ]`; this act is the reveal, so
these are the first words on screen carrying his name.

Every line here is **owner-supplied verbatim**, including two the owner
corrected himself: "For fives years" → "For five years", and "Lead the way,
open source will follow" → "Lead the way, we will follow". Reproduce them as
written; never tidy them.

Four gold nameplates sit between the welcome and the pills — the Cayde-6
reveal and three credits. They are **not here on purpose**: they carry
`copy_source: brief` and resolve from the roster, which is the one place
those names live. Edit them there.

## 17:23.202

* [ghost_welcome] status @ 17:23.202 +6.0
  - position: status
  # The Ghost's welcome is a hard cut on and off; it carries none of the
  # pills' fades.
  - fade_in: null
  - fade_out: null
  - fade_out_at: null
  - detail: AN4-CH4K-12
  - label: Welcome to KubeCon + Cloud Native Con
  - seen_at_film: 60.127
  - _note: Programme 16:26 maps to Act VI 1:00.127 -- owner note 2026-08-16: "the 'Welcome to KubeCon' text line goes here". The owner asked for the Ghost to welcome the audience, so this uses the top-of-frame status treatment rather than a normal lower-third chat; the seat is the Ghost's own shot (the Ghost over the Moon), confirmed on an extracted frame. Moved from 36.127, the star-map HUD shot.

## 22:16.732

[castrojo_line_1] castrojo @ 22:16.732 +2.8: For five years you've trusted us

[castrojo_line_2] castrojo @ 22:19.890 +2.8: Mastered your tools

[castrojo_line_3] castrojo @ 22:23.048 +2.8: Honed your craft

[castrojo_line_4] castrojo @ 22:26.206 +2.8: Made Lifelong Friends

[castrojo_line_5] castrojo @ 22:29.364 +2.8: And now it's up to you, guardian

[castrojo_line_6] castrojo @ 22:32.522 +2.8: Lead the way, we will follow
