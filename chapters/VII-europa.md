---
act: VII
manifest: stories/07-europa-plates.json
# WHERE THIS ACT STARTS IN THE PROGRAMME, in seconds. Measured, not guessed:
# the running order's segment durations summed on 2026-08-25, with each item
# taken the way tools/megacut.py's item_duration takes it (an authored
# `trim_from`/`trim_to`/`dur` outranks a probe, and the window is
# trim_to MINUS trim_from; otherwise the v:0 stream duration) -- prologue
# 101.200 + act I 116.200 + Perfume 2 66.400 + act II 411.267 + act III
# 168.600 + Perfume 3 114.848 + intermission 27.194 + act IV 34.000 +
# act V 25.259 + interstitial 5.000 + act VI 401.527 + Perfume 4a 13.120 +
# Perfume 4b 102.445 = 1587.060. Every `@` pin below was co-shifted by the
# same +47.267, so each plate's act-local seat is unchanged; the manifest
# regenerates byte-identical.
# Restate the derivation when the running order moves.
programme_start: 1587.060
# The order this act has always written its plates in, kept so the generated
# manifest reads the way the delivered one did.
# This act's whole plate list comes from this file, so the manifest is
# regenerated from it: `python3 tools/chapter_md.py sync <act> --write`.
owns_plates: true
field_order: id, kind, position, speaker, text, censor, avatar, avatar_url, at, dur, fade_in, fade_out_at, fade_out, _note
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
- `@ 26:27.060` is programme time — the clock you scrub in the whole
  show. This act starts at 26:27.060.
- `+2.4` is how long the pill holds. Delete it and the hold is derived from
  read speed instead (15 characters a second, floor 2.2 s, ceiling 7 s).
- A real-person speaker is their canonical GitHub login; its portrait derives
  from `vocab/casting.yaml`.
- A line with no words renders as a placeholder credited to nobody.

Check what it resolves to, and that it still matches the manifest:

```bash
python3 tools/chapter_md.py show VII
python3 tools/chapter_md.py check VII
```

>> The priority-now readability pass retains every word and written order.
The opening deployment run and the closing nimbinatus run use a 0.25 s clear
gap between pills; the unpinned lines continue to cascade after their pinned
runs, so no two pills occupy the letterbox together. <<

## 26:27.624

[d01] krook @ 26:27.624 +2.2: Deploy CNCF Projects Team

[d02] preethit @ 26:30.074 +2.2: Stand down, I'm sending my wolf

[d03] alolita @ 26:32.524 +2.6: Are you sure the Kube is on Europa?

[d04] preethit @ 26:35.374 +2.2: I hope she can handle the Kube

[d04b] preethit @ 26:37.824 +2.2: I must not fail

alolita: We have failed, Guardians are down

tophee: I've confirmed it myself, we have no choice

tophee: She's the only way to stop the Toilmaster

## 26:51.624

[d05] castrojo @ 26:51.624 +2.6: They must never know what you did for them

[d06] mrbobbytables @ 26:54.624 +2.2: When all hope is lost

[d07] jeefy @ 26:57.074 +2.2: Standing by for Extraction

[d08] idvoretskyi @ 26:59.624 +2.2: G{k8s}dspeed

[d11] preethit @ 27:02.224 +2.2: Our clan
preethit: Is the Iron
preethit: That forges Wolves

mrbobbytables: Wolves gladly sacrifice for their own

[krook] Initiate Lone Wolf Protocol
[IanColdwater] Local Security systems trivially pwned
[tabbysable] Europan Security systems trivially pwned (again)

## 27:28.624

[d09] nimbinatus @ 27:28.624 +2.2: Wilco

[d10] nimbinatus @ 27:31.074 +2.2: {k8s}ut

preethit @ 27:37.793: Hummingbird will find the girl
