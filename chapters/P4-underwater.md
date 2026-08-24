---
act: P4
manifest: stories/00-perfume-4-plates.json
# WHERE THIS INTERLUDE STARTS IN THE PROGRAMME, in seconds. Measured from a
# `tools/megacut.py stories/megacut/megacut.json --dry-run` on 2026-08-21:
# every segment up to Perfume movement 4a, summed -- prologue 101.200 +
# act I 116.200 + Perfume 2 66.400 + act II 364.068 + act III 160.200 +
# Perfume 3 114.848 + act IV 34.000 + act V 25.259 + interstitial 5.000 +
# act VI 401.527 = 1388.702. Movements 4a and 4b are two trims of ONE
# render, so the plate clock below is that render's own and starts here.
programme_start: 1388.702
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

## 24:02.653

[chat_loose_end] Jill Castro @ 24:02.653 +1.7: One more loose end

[chat_escape] Valerie @ 24:04.534 +1.7: You can't escape yourself
  - avatar: renders/avatars/valerie-tar-gz.png

[chat_promised] Rafael @ 24:06.414 +1.7: You promised

[chat_fine] castrojo @ 24:08.295 +1.7: Fine
  - avatar: renders/avatars/castrojo.png

[chat_minds] LH @ 24:12.057 +1.7: Show them the minds

[chat_wolves] Valerie @ 24:13.938 +3.0: Of the wolves
  - avatar: renders/avatars/valerie-tar-gz.png

[chat_wolf] Rafael @ 23:25.865 +3.0: What's a wolf?
