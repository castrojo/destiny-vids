---
act: VII
manifest: stories/07-europa-plates.json
# WHERE THIS ACT STARTS IN THE PROGRAMME, in seconds. Measured, not guessed:
# the running order's segment durations summed from a
# `tools/megacut.py stories/megacut/megacut.json --dry-run` on 2026-08-21 --
# every segment before it, summed: prologue 101.200 + act I 116.200 +
# Perfume 2 66.400 + act II 359.968 + act III 160.200 + Perfume 3 114.848 +
# act IV 34.000 + act V 25.259 + interstitial 5.000 + act VI 401.527 +
# Perfume 4a 13.120 + Perfume 4b 102.445 = 1500.167.
# Restate the derivation when the running order moves.
programme_start: 1500.167
# The order this act has always written its plates in, kept so the generated
# manifest reads the way the delivered one did.
# This act's whole plate list comes from this file, so the manifest is
# regenerated from it: `python3 tools/chapter_md.py sync <act> --write`.
owns_plates: true
field_order: id, kind, position, speaker, text, censor, avatar, at, dur, fade_in, fade_out_at, fade_out, _note
defaults:
  kind: chat
  position: letterbox
  fade_in: 0.6
  fade_out: 0.25
  # `derived` is at + dur - fade_out, which is how every pill in this act
  # was already timed.
  fade_out_at: derived
  # This act's delivered pills carry none of the chrome act II's do. A
  # default of `null` removes the field rather than inventing it.
  copy_source: null
  text_source: null
  avatar: null
  avatar_url: null
---

# Act VII — Europa, the director's cut

This file is where you write and rewrite this chapter's dialogue. The build
(`python3 scripts/build_europa.py`) reads it and writes
[`07-europa-plates.json`](../stories/07-europa-plates.json), which is generated —
never hand-edit it.

Every line below carries `@ <programme time>` and `+<seconds>`, because this
act was already delivered and its pills must come back exactly where they
were. **Change the words freely.** Only touch a `@` or a `+` when you mean to
move or re-time that pill, and expect to rebuild the act when you do.

- `[an-id]` keeps the pill's existing id, which is what the delivered master
  and every note about this act refer to.
- `@ 25:00.167` is programme time — the clock you scrub in the whole
  show. This act starts at 25:00.167.
- `+2.4` is how long the pill holds. Delete it and the hold is derived from
  read speed instead (15 characters a second, floor 2.2 s, ceiling 7 s).
- `- field: value` rows under a line carry its chrome — the avatar, the fade,
  the censor rule, the `_note` that records where the line came from.
- A line with no words renders as a placeholder credited to nobody.

Check what it resolves to, and that it still matches the manifest:

```bash
python3 tools/chapter_md.py show VII
python3 tools/chapter_md.py check VII
```

## 25:00.731

[d01] krook @ 25:00.731 +1.6: Deploy CNCF Projects Team
  - avatar: ~/Videos/wolves-directors-cut/nimbatus-review/render/krook.png
  - fade_out_at: 1.864

[d02] preethi @ 25:02.731 +1.6: Stand down
  - fade_out_at: 3.864

[d03] alolita @ 25:04.731 +2.6: It's all for naught we fail
  - avatar: renders/avatars/alolita.png
  - fade_out_at: 6.864

[d04] preethi @ 25:07.731 +2: I'm sending our best
  - fade_out_at: 9.264

## 25:24.731

[d05] castrojo @ 25:24.731 +2.6: They must never know who we are
  - avatar: renders/avatars/castrojo.png
  - fade_out_at: 26.864

[d06] castrojo @ 25:27.731 +2: Don't get caught
  - avatar: renders/avatars/castrojo.png
  - fade_out_at: 29.264

[d07] jeefy @ 25:30.131 +2.2: It's all in your hands
  - avatar: renders/avatars/jeefy.png
  - fade_out_at: 31.864

[d08] ihor @ 25:32.731 +2.2: G{k8s}dspeed
  - avatar: renders/avatars/idvoretskyi.png
  - fade_out_at: 34.464

## 26:01.731

[d09] nimbatus @ 26:01.731 +1.8: Wilco
  - avatar: ~/src/website/public/wolves/characters/nimbatus.webp
  - fade_out_at: 63.064

[d10] nimbatus @ 26:03.931 +2: {k8s}ut
  - avatar: ~/src/website/public/wolves/characters/nimbatus.webp
  - fade_out_at: 65.464
