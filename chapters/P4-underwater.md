---
act: P4
manifest: stories/00-perfume-4-plates.json
# Programme start measured from `python3 tools/megacut.py stories/megacut/megacut.json --dry-run` on 2026-08-27 after seating the 152.507 s Excision segment. The programme item-duration rule is authoritative.
programme_start: 1624.001
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

## 27:57.952

[chat_loose_end] Jill Castro @ 27:57.952 +1.7: One more loose end

[chat_escape] Valerie @ 27:59.833 +1.7: You can't escape yourself
  - avatar: renders/avatars/valerie-tar-gz.png

[chat_promised] Rafael @ 28:01.713 +1.7: You promised

[chat_fine] castrojo @ 28:03.594 +1.7: Fine
  - avatar: renders/avatars/castrojo.png

[chat_minds] LH @ 28:07.356 +1.7: Show them the minds

[chat_wolves] Valerie @ 28:09.237 +3.0: Of the wolves
  - avatar: renders/avatars/valerie-tar-gz.png

[chat_wolf] Rafael @ 27:21.164 +3.0: What's a wolf?
