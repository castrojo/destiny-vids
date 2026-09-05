---
act: VII
manifest: stories/07-europa-plates.json
# WHERE THIS ACT STARTS IN THE PROGRAMME, in seconds. Measured, not guessed:
# `tools/megacut.py --dry-run` puts Excision at 1450.294, Perfume movement 4
# at 1602.796, and Europa at 1718.362. The insertion shifts the programme
# clock only; each plate's act-local seat is unchanged.
# Restate the derivation when the running order moves.
programme_start: 1718.362
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
- `@ 26:27.060` is programme time — the clock you scrub in the whole
  show. This act starts at 26:27.060.
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

>> Every `@` pin in this act is owner placement from the delivered master and
never moves, and those pins sit 0.4 s apart -- no unpinned line fits between
them, and the renderer refuses two pills on screen at once. The unpinned
lines therefore cascade through the open water AFTER each pinned run, in the
owner's written order: alolita's report and tophee's confirmations follow the
deployment exchange, and the sacrifice line with the Lone Wolf Protocol trio
follow the creed, rolling into nimbatus' "Wilco". <<

## 28:38.926

[d01] krook @ 28:38.926 +1.6: Deploy CNCF Projects Team
  - avatar: ~/Videos/wolves-directors-cut/nimbatus-review/render/krook.png
  - fade_out_at: 1.864

[d02] preethit @ 28:40.926 +1.6: Stand down, I'm sending my wolf
  - fade_out_at: 3.864

[d03] alolita @ 28:42.926 +2.6: Are you sure the Kube is on Europa?
  - avatar: renders/avatars/alolita.png
  - fade_out_at: 6.864

[d04] preethit @ 28:45.926 +2.0: I hope she can handle the Kube
  - fade_out_at: 9.264

[d04b] preethit @ 28:48.326 +2.2: I must not fail

alolita: We have failed, Guardians are down

tophee: I've confirmed it myself, we have no choice

tophee: She's the only way to stop the Toilmaster

## 29:02.926

[d05] castrojo @ 29:02.926 +2.6: They must never know what you did for them
  - avatar: renders/avatars/castrojo.png
  - fade_out_at: 26.864

[d06] mrbobbytables @ 29:05.926 +2.0: When all hope is lost
  - avatar: renders/avatars/mrbobbytables.png
  - fade_out_at: 29.264

[d07] jeefy @ 29:08.326 +2.2: Standing by for Extraction
  - avatar: renders/avatars/jeefy.png
  - fade_out_at: 31.864

[d08] ihor @ 29:10.926 +2.2: G{k8s}dspeed
  - avatar: renders/avatars/idvoretskyi.png
  - fade_out_at: 34.464

[d11] preethit @ 29:13.526 +2.2: Our clan
preethit: Is the Iron
preethit: That forges Wolves

mrbobbytables: Wolves gladly sacrifice for their own

[krook] Initiate Lone Wolf Protocol
[iancoldwater] Local Security systems trivially pwned
[tabbysable] Europan Security systems trivially pwned (again)

## 29:39.926

[d09] nimbatus @ 29:39.926 +1.8: Wilco
  - avatar: ~/src/website/public/wolves/characters/nimbatus.webp
  - fade_out_at: 63.064

[d10] nimbatus @ 29:42.126 +2.0: {k8s}ut
  - avatar: ~/src/website/public/wolves/characters/nimbatus.webp
  - fade_out_at: 65.464

preethit @ 29:49.095: Hummingbird will find the girl
  - avatar: renders/avatars/preethit.png
