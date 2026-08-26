---
act: P4
manifest: stories/00-perfume-4-plates.json
# Programme start measured from `python3 tools/megacut.py stories/megacut/megacut.json --dry-run` on 2026-08-25. The programme item-duration rule is authoritative.
programme_start: 1471.494
owns_plates: true
field_order: id, kind, position, speaker, avatar, avatar_url, text, copy_source, at, dur, fade_in, fade_out_at, fade_out
defaults:
  kind: chat
  position: letterbox
  copy_source: owner_supplied
  fade_in: 0.4
  fade_out: 0.25
  fade_out_at: derived
  text_source: null
  avatar: auto
  avatar_url: auto
---

# Perfume, movement 4 — the underwater exchange

This file is where you write and rewrite the exchange that plays under the
last movement of *Perfume Of The Timeless*, between the wolves and Europa.
The build (`python3 scripts/build_ending_overlays.py`) reads it and writes
[`00-perfume-4-plates.json`](../stories/00-perfume-4-plates.json), which is
generated — never hand-edit it.

This is not an act and takes no numeral; it is an interlude that happens to
carry dialogue, which is exactly why its words belong in a chapter file like
everything else the audience reads.

The pills sit inside one measured shot — the divers approaching the whale
skeleton — and the manifest's `chat` block records that window. Moving a
pill outside it is a picture decision, not a copyedit.

```bash
python3 tools/chapter_md.py show P4
python3 tools/chapter_md.py check P4
```

## 25:25.445

[chat_loose_end] JillCastro @ 25:25.445 +2.2: One more loose end

[chat_escape] valerie-tar-gz @ 25:27.745 +2.2: You can't escape yourself

[chat_promised] rafaelcastro10 @ 25:30.045 +2.2: You promised

[chat_fine] castrojo @ 25:32.345 +2.2: Fine

[chat_minds] LionHeartP @ 25:34.645 +2.2: Show them the minds

[chat_wolves] valerie-tar-gz @ 25:36.945 +3.0: Of the wolves

[chat_wolf] rafaelcastro10 @ 24:48.657 +3.0: What's a wolf?
