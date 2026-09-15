---
act: P4
manifest: stories/00-perfume-4-plates.json
# Final alpha5 programme origin for movement 4: 1398.162 seconds.
programme_start: 1398.162
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

# Perfume, movement 4 — visual replacements only

The prior dialogue exchange was removed at the owner's instruction because it
was hallucinated. This interlude now carries only the authored wallpaper and
picture replacements from [`00-perfume-thread.json`](../stories/00-perfume-thread.json).

The derivative remains `renders/perfume-4-overlays.mp4` so those visual
replacements survive; it burns no dialogue plates.
