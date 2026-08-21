---
act: IV
manifest: stories/04-kat-plates.json
# WHERE THIS ACT STARTS IN THE PROGRAMME, in seconds. Measured, not guessed:
# the running order's segment durations summed from a
# `tools/megacut.py stories/megacut/megacut.json --dry-run` on 2026-08-21 --
# prologue 101.200 (megacut.json item 0 `dur`) + act I 116.200 + Perfume
# movement 2 66.400 + act II 359.968 + act III 160.200 + Perfume movement 3
# 114.848 = 918.816. Restate the derivation when the running order moves.
programme_start: 918.816
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

# Act IV — Bias for Action: Kat Cosgrove's conversation

This file is where you write and rewrite this chapter's dialogue. The build
(`python3 scripts/build_kat.py`) reads it and writes
[`stories/04-kat-plates.json`](../stories/04-kat-plates.json), which is
generated — never hand-edit it.

Every line below carries `@ <programme time>` and `+<seconds>`, because this
act was already delivered and its pills must come back exactly where they
were. **Change the words freely.** Only touch a `@` or a `+` when you mean to
move or re-time that pill, and expect to rebuild the act when you do.

- `[an-id]` keeps the pill's existing id, which is what the delivered master
  and every note about this act refer to.
- `@ 15:18.816` is programme time — 15 minutes 18.816 seconds into the whole
  show, the clock you scrub. This act starts at 15:18.816.
- `+2.4` is how long the pill holds. Delete it and the hold is derived from
  read speed instead (15 characters a second, floor 2.2 s, ceiling 7 s).
- `- field: value` rows under a line carry its chrome — the avatar, the fade,
  the censor rule, the `_note` that records where the line came from.
- A line with no words renders as a placeholder credited to nobody.

Check what it resolves to, and that it still matches the manifest:

```bash
python3 tools/chapter_md.py show IV
python3 tools/chapter_md.py check IV
```

## 15:19.416

[p1-kat-shooting] kat @ 15:19.416 +2.4: Hey why are they shooting at me!
  - avatar: ~/Videos/wolves-kat/render/kat.jpg
  - _note: #118 line 1, the conversation's setup. Seated in the pre-reveal action (0-6.03 is the opening run; the first cut is 6.03), fully in by 1.2 after the ~0.1s black lead.

[p2-bobby] mrbobbytables @ 15:22.116 +2.4: The gamers don't know you're here to help
  - avatar: ~/Videos/wolves-kat/render/mrbobbytables.jpg
  - _note: #118 line 2, the answer. Clears at 5.7, 0.33s before the 6.03 cut, so the hero shot and the reveal at 7.0 arrive clean. mrbobbytables is bound in vocab/casting.yaml; avatar is the project's own mrbobbytables.jpg.

## 15:29.916

[p2c-kat-nice] kat @ 15:29.916 +1.3: Nice to meet you too!
  - avatar: ~/Videos/wolves-kat/render/kat.jpg
  - fade_in: 0.2
  - _note: Owner 2026-08-15, verbatim. Seated after Kat's combat roll, while she looks overhead and turns; it clears before the Linux desktop line.

[p3-kat-linux1] kat @ 15:31.466 +2.1: I miss ONE email now I gotta use a Linux desktop?
  - avatar: ~/Videos/wolves-kat/render/kat.jpg
  - _note: #118 line 3, after Kat's combat-roll reply. It clears 0.08s before the 14.833 cut.

[p3b-kat-soundbet] kat @ 15:33.766 +2.4: How much you want to bet their sound just doesn't work?
  - avatar: ~/Videos/wolves-kat/render/kat.jpg
  - _note: Owner 2026-08-14, verbatim: 'add a "How much you want to bet their sound just doesn't work?" after kat's linux desktop line.' No speaker was named; it continues Kat's own line and is seated as hers. The seat is the recorded exception the retired p1b-ian held: it arrives on the 14.833 shake cut, 0.35s after the Linux line clears, and clears at 17.35, 0.4s before the 17.75 cut.

[p3c-hey] TBD @ 15:36.516 +1.9: HEY! We know when you're not upstreaming!
  - _note: Owner 2026-08-14: 'add another sound line after the missing an email' -- this pair, verbatim. THE OWNER NAMED NO SPEAKER for this line, and it is not Kat's (it addresses her), so it carries the vocab's own uncast speaker TBD and the drawn crest, never a guessed name -- rule 3. One word from the owner recasts it. Spans the 17.75/18.65 cluster cuts (precedented) and clears at 19.6, a frame ahead of the 19.62 cut.

[p3d-kat-bettershit] kat @ 15:38.766 +1.7: I have better sh*t to do!
  - avatar: ~/Videos/wolves-kat/render/kat.jpg
  - _note: Kat's retort, owner verbatim including the sh*t asterisk (her 23.3 line spells it out -- both reproduced exactly as written). Enters after the 19.85 cut, clears at 21.65.

[p4-kat-linux2] kat @ 15:40.766 +2.2: I miss ingress-nginx sometimes
  - avatar: ~/Videos/wolves-kat/render/kat.jpg
  - _note: #118 line 4. Re-seated +1.75 to make room for the upstreaming exchange; now spans the 23.05 cut (precedented by the cluster pills) and clears at 24.15.

[p5-kat-linux3] kat @ 15:43.216 +1.9: Fine I'll fix your sh*t too
  - avatar: ~/Videos/wolves-kat/render/kat.jpg
  - _note: #118 line 5, order kept: after the ingress line, before cardio. Re-seated; clears at 26.3.

[p6-kat-cardio] kat @ 15:45.416 +2.4: Remember kids, cardio!
  - avatar: ~/Videos/wolves-kat/render/kat.jpg
  - _note: The note's 10:33 beat, nudged +0.6 by the upstreaming exchange; clears at 29.0, 0.17s before the 29.17 cut.
