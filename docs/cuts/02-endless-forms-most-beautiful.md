# 02 — *Endless Forms Most Beautiful* (act II)

**Status:** first pass, delivered as **act II** of the running order —
`~/Videos/Wolves/Prod/02-endlessformsmostbeautiful.mp4`. Delivered is not
published. Provenance on the source is **weak and recorded** (below).
**Runtime:** 307.998 s (5:07.998) for a 307.998 s song — the film *is* the song.
**Master:** `renders/efmb-hq.mp4` — 1920x1080 H.264, 30 fps, FLAC 48 kHz
stereo, −1.0 dBTP, −11.3 LUFS integrated.

Origin: [issue #74](https://github.com/castrojo/destiny-vids/issues/74) — act II
had a slot in the canonical order and no film. This is the film.

## What this act is

The one act built entirely from Bungie's **live-action** trailers, scored to an
instrumental so the picture carries it alone. Five unbroken runs in source
order, one song end to end, no excision and no pause.

It is a **feature act, not a hero video** ([`docs/catalog.md`](../catalog.md)):
no cast is bound to this footage, so it carries **no nameplates**. Its only
on-screen copy is the act slide, which belongs to the megacut.

## Sources

| Role | Source | Notes |
|---|---|---|
| Bed | Nightwish, *Endless Forms Most Beautiful (Instrumental)* — [`6-9667CV1zQ`](https://www.youtube.com/watch?v=6-9667CV1zQ) | Official Nightwish channel. 307.998 s. **Opus rung 251 @48 k**, the top rung the ladder offers |
| Picture | *Destiny – All Live Action Trailers* — [`lL9i6wqwFD8`](https://www.youtube.com/watch?v=lL9i6wqwFD8) | **A fan compilation by Brutal Draconis**, 376.1 s. Not an official Bungie upload — see Rights |

The bed is a **different track from act V's**. Act V (Natali) uses *Shudder
Before the Beautiful*, instrumental, from the same album; #74 flagged that
naming the record does not name a track, and putting the same music under two
consecutive acts is the failure it was guarding against.

## The cut

The owner gave this as timecodes; every one was then snapped to a **measured**
shot boundary — `ContentDetector(threshold=27)` across the whole source, and
`blackdetect` for the black. Frames were reviewed on a contact sheet before
anything was removed.

`scripts/build_efmb.py` holds the runs and asserts the arithmetic. Run it to
print the cut; it is the authority, and this table is its output.

| Kept | Duration | Why the boundary is there |
|---|---|---|
| 0:00.000 → 0:06.467 | 6.467 s | The moon cold open, out on the cut to the man reading |
| 0:22.033 → 0:52.233 | 30.200 s | The moon battle, unbroken, out on the cut back to the reading |
| 1:02.633 → 2:54.433 | 111.800 s | In off the Halo slate, out on the cut to the DESTINY card |
| 3:00.533 → 4:04.833 | 64.300 s | In off the black after the card, out before the end title |
| 4:49.467 → 6:16.134 | 86.667 s | The owner's 4:50, snapped back to the boundary, to the end |

| Removed | Duration | Why |
|---|---|---|
| 0:06.467 → 0:22.033 | 15.566 s | The man reading to his son, and the book |
| 0:52.233 → 0:54.267 | 2.034 s | The reading, reprised |
| 0:54.267 → 1:02.633 | 8.366 s | Title card: from the creators of Halo |
| 2:54.433 → 2:59.167 | 4.734 s | Title card: DESTINY |
| 2:59.167 → 3:00.533 | 1.366 s | Black, measured by `blackdetect` |
| 4:04.833 → 4:06.100 | 1.267 s | Burned-in end title: BECOME LEGEND |
| 4:06.100 → 4:49.467 | 43.367 s | The dance section — cut separately as its own video |

### Removing the framing narration is what makes the moon continuous

The opening trailer keeps cutting away from the Moon to a man reading to his
son. The owner asked for **in-universe shots**, so those cutaways and the two
title cards that bracket them come out, and what is left plays as one
continuous scene — which is the entire point of the act's opening.

**The visor close-ups are not the same thing and they stay.** An actor's eyes
seen through a Guardian's helmet is inside the fiction; a man in a living room
reading about it is outside. Both are live action, and only one of them is the
thing that was removed. Getting that distinction wrong would have gutted the
middle of the act, since *Become Legend* is built on those shots.

## The song is longer than the picture, and the song wins

Picture after removals is **299.434 s**. The song is **307.998 s**. The
difference is **8.564 s**, and it is real: every second that would have filled
it is either material the owner named for removal or inside the dance section
that this act skips entirely.

Four ways to close it were put to the owner, who was unavailable when the
numbers came in. The pass takes the **reversible** one:

> **`TAIL_POLICY = "music_first"` — the song starts first.** The picture joins a
> song already playing. Nothing is truncated, nothing is frozen, and no removed
> material is quietly restored.

The three alternatives each cost something that cannot be taken back cleanly:
fading the last 8.6 s truncates the master, holding a frame freezes the film,
and taking the time back off the dance section contradicts a direct
instruction. In the megacut the **act slide covers the lead-in**; played alone
the act opens on black with the music under it.

`BED_LEAD_SEC` is **derived from the gap**, never typed, and asserted — so if a
run boundary ever moves, the song stays whole automatically.

## Audio

Held to [`docs/skills/references/audio-standard.md`](../skills/references/audio-standard.md).

The bed decodes **above full scale**: the first mux measured **+0.2 dBFS true
peak**, the exact failure the standard names and the same one that shipped in
act VII (#82). The fix was the prescribed **static gain at the mux**,
`volume=-1.2dB`, with `-c:v copy` — one audio encode, no generation loss on
picture, and every dynamic relationship the artist chose left alone. A
limiter or `loudnorm` would have changed them.

Re-measured on the **delivered** file, not the intermediate: **−1.0 dBTP,
−11.3 LUFS, LRA 5.9** — the same true peak as acts IV and V.

## Rights

The picture source is a **fan compilation**, not a publisher upload. That is
recorded in `videos/yt_destiny_all_live_action_trailers.json`'s
`source_rights_note` rather than assumed away, and it is the same posture as
the Antesion compilation the musical rests on ([#55](https://github.com/castrojo/destiny-vids/issues/55)).

The four trailers it collects — *The Law of the Jungle*, *Become Legend*,
*Evil's Most Wanted*, *New Legends Will Rise* — were all published officially by
Bungie. **Upgrading to those sources is available and not yet done**, exactly as
the Final Shape *Gameplay* Trailer was upgraded for the musical. It does not
block building the act; it is a **publishing** decision, and it is the owner's.

The bed is a Nuclear Blast copyrighted recording, official Nightwish delivery,
used as a non-commercial fan-work music bed. This repo stores measurements and
timecodes; it ships no audio and no footage.

## Unresolved

- **Provenance.** The picture is fan-compiled. Inherits #55.
- **The tail policy** was chosen without the owner, deliberately and
  reversibly. Changing it changes no run — one constant in `build_efmb.py`.
- **Act II is not wired into the megacut yet.** Its slide and its clip belong
  in `stories/megacut/`, which another agent held open during this session.
  Filed separately so nothing is edited underneath them.
- **No lossless provenance.** As with every bed in this show, the source is a
  YouTube Opus rung; the FLAC master is lossless *relative to that*.

## Reproducing it

```bash
python3 scripts/build_efmb.py                     # print the cut and the arithmetic
python3 scripts/build_efmb.py --json plan.json    # the same, machine-readable
```

The media is fetched, never committed: the compilation as H.264 into
`media/yt_destiny_all_live_action_trailers.mp4`, and the bed as Opus 251
decoded to `media/bed_endless_forms_most_beautiful.wav`.
