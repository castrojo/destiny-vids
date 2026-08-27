---
act: P4
manifest: stories/00-perfume-4-plates.json
# Programme start measured from `python3 tools/megacut.py stories/megacut/megacut.json --dry-run` on 2026-08-27: Excision starts at 1450.294 and movement 4 starts at 1602.796. The programme item-duration rule is authoritative.
programme_start: 1602.796
owns_plates: true
field_order: id, kind, position, speaker, avatar, text, copy_source, at, dur, fade_in, fade_out_at, fade_out
defaults:
  kind: chat
  position: letterbox
  copy_source: owner_supplied
  fade_in: 0.4
  fade_out: 0.25
  fade_out_at: derived
  text_source: null
  avatar: null
  avatar_url: null
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

## 27:36.747

[chat_loose_end] Jill Castro @ 27:36.747 +1.7: One more loose end

[chat_escape] Valerie @ 27:38.628 +1.7: You can't escape yourself
  - avatar: renders/avatars/valerie-tar-gz.png

[chat_promised] Rafael @ 27:40.508 +1.7: You promised

[chat_fine] castrojo @ 27:42.389 +1.7: Fine
  - avatar: renders/avatars/castrojo.png

[chat_minds] LH @ 27:46.151 +1.7: Show them the minds

[chat_wolves] Valerie @ 27:48.032 +3.0: Of the wolves
  - avatar: renders/avatars/valerie-tar-gz.png

[chat_wolf] Rafael @ 26:59.959 +3.0: What's a wolf?
