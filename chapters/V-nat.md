---
act: V
manifest: stories/05-natali-plates.json
# Programme start measured from `python3 tools/megacut.py stories/megacut/megacut.json --dry-run` on 2026-08-25. The programme item-duration rule is authoritative.
programme_start: 1079.642
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

# Act V — Natali Vlatko's arrival

This file is where you write and rewrite this chapter's dialogue. The build
(`python3 scripts/build_natali.py`) reads it and writes
[`05-natali-plates.json`](../stories/05-natali-plates.json), which is generated —
never hand-edit it.

Every line below carries `@ <programme time>` and `+<seconds>`, because this
act was already delivered and its pills must come back exactly where they
were. **Change the words freely.** Only touch a `@` or a `+` when you mean to
move or re-time that pill, and expect to rebuild the act when you do.

- `[an-id]` keeps the pill's existing id, which is what the delivered master
  and every note about this act refer to.
- `@ 17:59.642` is programme time — the clock you scrub in the whole
  show. This act starts at 17:19.709.
- `+2.4` is how long the pill holds. Delete it and the hold is derived from
  read speed instead (15 characters a second, floor 2.2 s, ceiling 7 s).
- `- field: value` rows under a line carry its chrome — the avatar, the fade,
  the censor rule, the `_note` that records where the line came from.
- A line with no words renders as a placeholder credited to nobody.

Check what it resolves to, and that it still matches the manifest:

```bash
python3 tools/chapter_md.py show V
python3 tools/chapter_md.py check V
```

## 18:02.242

[p1-nat-mouthbreathers] Nat @ 18:02.242 +2.6: Hey these mouth breathers are shooting at me!
  - avatar: natali.jpg
  - _note: #118 Nat line 1, marked by the owner at 10:45 on the programme clock of the cut they watched. Seated on the cockpit close-up 2.269-6.073 -- her rule is 'dialogue only when her character is onscreen', and this is her in the ship under fire. Clears 0.87s before the 6.073 cut.

[p2-nat-ceasefire] Nat @ 18:07.442 +2.2: I am a Documentation Expert, cease fire!
  - avatar: natali.jpg
  - _note: #118 Nat line 2. Back in the cockpit after the 7.608 cut; she is onscreen through the boost. Clears at 10.0, before the landing burst.

[p3-nat-goddamn] Nat @ 18:09.942 +1.4: Goddamn it!
  - censor: Goddamn -> G{k8s}ddamn
  - avatar: natali.jpg
  - _note: #118's '[Stumble animation]' pair, first half. The landing burst -- the act's own shudder -- peaks ~10.4; the line rides it. She is onscreen from here to the end of the act.

[p4-nat-gitpush] Nat @ 18:11.542 +1.7: No time to `git push`!
  - avatar: natali.jpg
  - _note: #118 stumble pair, second half, as she picks herself up and walks. Backticks are the owner's own and are reproduced.

[p5-nat-stranded] Nat @ 18:13.442 +2.4: I'm stranded, they'll never find the docs in time!
  - avatar: natali.jpg
  - _note: #118, the setup for the docs gag, over the walk as her ship leaves.

[p6-nick-docs1] Nick @ 18:16.042 +1.2: docs.bazzite.gg
  - avatar: nick.jpg
  - _note: #118, radio answer 1 of 3. Nick has NO avatar in the project and no vocab binding -- plate.py will fall back to the drawn crest and name the missing file, which is the degrade-and-record path; drop render/nick.jpg in and rebuild to fill the slot.

[p7-kat-screams] Kat @ 18:17.442 +1.6: I can hear their screams!
  - avatar: kat.jpg
  - _note: #118, Kat on the radio; her avatar is the project's own kat.jpg.

[p8-nick-docs2] Nick @ 18:19.242 +1.2: docs.bazzite.gg
  - avatar: nick.jpg
  - _note: #118, radio answer 2 of 3.

[p9-nat-voices] Nat @ 18:20.642 +2.3: Like one hundred thousand voices cried out in terror
  - avatar: natali.jpg
  - _note: #118, over the walk; she is onscreen. Runs under her reveal card, which sits ABOVE the matte (reveal.html bottom:336px) while pills sit inside it -- two bands, no collision.

[p10-nick-docs3] Nick @ 18:23.142 +1.4: docs.bazzite.gg
  - avatar: nick.jpg
  - _note: #118, the button. Clears at 24.9, on the act's own picture fade (fade_out_at 24.95) -- the gag ends the act.
