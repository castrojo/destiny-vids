---
act: IV
manifest: stories/04-kat-plates.json
# Programme start measured from `python3 tools/megacut.py stories/megacut/megacut.json --dry-run` on 2026-08-25. The programme item-duration rule is authoritative.
programme_start: 1005.709
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
---

# Act IV — Bias for Action: Kat Cosgrove's conversation

This file is where you write and rewrite this chapter's dialogue. The build
(`python3 scripts/build_kat.py`) reads it and writes
[`stories/04-kat-plates.json`](../stories/04-kat-plates.json), which is
generated — never hand-edit it.

The pre-reveal exchange stays pinned to its measured seats. The conversation
under the 16:56.809 heading flows from that anchor, so an approved readable
hold carries each later pill forward without overlap.

- `[an-id]` keeps the pill's existing id, which is what the delivered master
  and every note about this act refer to.
- `@ 16:45.709`, where present, is programme time — 16 minutes 45.709 seconds
  into the whole show, the clock you scrub. This act starts at 16:45.709.
- `+2.4` is how long the pill holds. Delete it and the hold is derived from
  read speed instead (15 characters a second, floor 2.2 s, ceiling 7 s).
- A real-person speaker is their canonical GitHub login; its avatar derives
  from `vocab/casting.yaml`.
- A line with no words renders as a placeholder credited to nobody.

Check what it resolves to, and that it still matches the manifest:

```bash
python3 tools/chapter_md.py show IV
python3 tools/chapter_md.py check IV
```

## 16:46.309

[p1-kat-shooting] katcosgrove @ 16:46.309 +2.4: Hey why are they shooting at me!

[p2-bobby] mrbobbytables @ 16:49.009 +2.4118: The gamers don't know you're here to help

## 16:56.809

[p2c-kat-nice] katcosgrove +2.2: Nice to meet you too!
  - fade_in: 0.2

[p3-kat-linux1] katcosgrove +2.8824: I miss ONE email now I gotta use a Linux desktop?

[p3b-kat-soundbet] katcosgrove +3.2353: How much you want to bet their sound just doesn't work?

[p3c-hey] TBD +2.4118: HEY! We know when you're not upstreaming!

[p3d-kat-bettershit] katcosgrove +2.2: I have better sh*t to do!

[p4-kat-linux2] katcosgrove +2.2: I miss ingress-nginx sometimes

[p5-kat-linux3] katcosgrove +2.2: Fine I'll fix your sh*t too

[p6-kat-cardio] katcosgrove +2.4: Remember kids, cardio!
