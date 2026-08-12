# 02 — *Endless Forms Most Beautiful* (act II)

**Status:** **editorial pass**, delivered as **act II** of the running order —
`~/Videos/Wolves/Prod/02-endlessformsmostbeautiful.mp4`, and **in the
programme** as of the megacut's v0.5. Delivered is not published. Provenance on
the source is **weak and recorded** (below).
**Runtime:** 307.998 s (5:07.998) for a 307.998 s song — the film *is* the song.
**Master:** `renders/efmb-hq.mp4` — 1920x1080 H.264, 30 fps, FLAC 48 kHz
stereo, −1.0 dBTP, −11.3 LUFS integrated. **The master predates this pass and
must be rebuilt** before the numbers below describe a file that exists.

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
| 0:00.000 → 0:04.017 | 4.017 s | The moon cold open, out on the **last frame before the dissolve** |
| 0:22.033 → 0:52.233 | 30.200 s | The moon battle, unbroken, out on the cut back to the reading |
| 1:02.633 → 2:54.433 | 111.800 s | In off the Halo slate, out on the cut to the DESTINY card |
| 3:00.533 → 4:04.833 | 64.300 s | In off the black after the card, out before the end title |
| 4:49.467 → 5:44.000 | 54.533 s | The owner's 4:50, snapped back to the boundary, out before the mech |
| 5:45.767 → 6:02.200 | 16.433 s | In off the mech, out on the cut to the DESTINY logo card |

| Removed | Duration | Why |
|---|---|---|
| 0:04.017 → 0:06.467 | 2.450 s | **The dissolve into the man reading** — the owner's ":12–:14 human pic" |
| 0:06.467 → 0:22.033 | 15.566 s | The man reading to his son, and the book |
| 0:52.233 → 0:54.267 | 2.034 s | The reading, reprised |
| 0:54.267 → 1:02.633 | 8.366 s | Title card: from the creators of Halo |
| 2:54.433 → 2:59.167 | 4.734 s | Title card: DESTINY |
| 2:59.167 → 3:00.533 | 1.366 s | Black, measured by `blackdetect` |
| 4:04.833 → 4:06.100 | 1.267 s | Burned-in end title: BECOME LEGEND |
| 4:06.100 → 4:49.467 | 43.367 s | The dance section — cut separately as its own video |
| 5:44.000 → 5:45.767 | 1.767 s | **The Cabal war machine and its flashing gun** — the heroes take the screen |
| 6:02.200 → 6:16.134 | 13.934 s | **The publisher end cards** — DESTINY / DESTINY 2 slates and the Activision copyright |

Runs and removals now tile the **entire source**, 0 → 376.134, and the script
asserts it. A frame that is neither kept nor named as removed is a frame nobody
decided about — and the end cards are exactly what that invariant was missing
before, since run 5 used to run to the end of the source and swallow them
unremarked.

### The `:12–:14` human survived because it arrives on a dissolve

The owner: *":12 - :14 human pic snuck in remove it"*. He was right, and the
reason it snuck in is worth recording, because it will happen again.

The moon does not **cut** to the man reading. It **dissolves** into him — the
Guardian's visor becomes his face — and a dissolve produces no frame-to-frame
delta large enough for `ContentDetector` to fire. So the pass that removed the
framing narration found the next *hard* cut, at 6.467, and kept 2.45 s of the
very material it was removing.

The boundary above was found by stepping frames at 1/30 s and **looking**: the
last clean helmet frame is **4.017**, and his face is bleeding through by 4.05.
Cutting at 6.467 keeps the dissolve; cutting inside it keeps a ghost of him.

The same trap caught a later pass on a different trailer, and the rule that
came out of both is now in this file's docstring: **when a boundary matters,
detection proposes and the eye disposes.**

### The mech comes out whole, not trimmed

The owner: *"we might want to cut the big enemy with the flashing gun in that
scene so we can highlight the heroes instead, do that this is a pivotal [beat]
… unless you think it's awesome already."*

It is 1.767 s between two hard cuts: it opens on the white blowout of the gun
charging and resolves to the machine posed at camera. The first instinct was to
trim it to the charge and cut away — but halving a 1.767 s shot makes it a
flash-frame, which is worse than either keeping or cutting it. Removed whole,
it needs no mid-shot trim and leaves no artifact.

**One line in `REMOVED` restores it.**

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

## The head is cut to the music now, not to taste

Picture after removals is **281.283 s** against a **307.998 s** song, so 26.715 s
of the film carries no picture. Where that time goes used to be a matter of
taste. It is not any more, and the reason is the climax.

### The climactic beat, and the shot that was late for it

The song **breaks down hard at 258.0 s** and stays down to 268.0 (−12 dBFS
falling to −20). It builds for two seconds, and the **full band re-enters at
269.700 s**.

269.700 is an exact **downbeat** on the bed's own grid — beat index 683,
`downbeat_phase 3`, bar 1.578957 s — read from
`music/bed_endless_forms_most_beautiful.json`, not estimated.

On screen at that moment: a **Sentinel Titan raising the Void shield**. In the
delivered film the shield reached full extension at roughly 270.06 — about a
third of a second **after** the biggest musical event in the act. Close enough
to feel almost right, which is the worst kind of wrong.

### So the lead-in is derived from the music

```python
SYNC_ANCHOR_SRC  = 338.200   # the shield at full extension, verified by eye
SYNC_ANCHOR_FILM = 269.700   # the downbeat the band re-enters on
```

`BED_LEAD_SEC` is now whatever value puts the first on the second, computed by
walking the kept runs and asserted. **Type a number there and the shield drifts
off the beat the next time a boundary moves.** The script refuses to build if
the anchor has been cut, rather than silently syncing to a frame that no longer
plays.

| | Seconds |
|---|---|
| Head — black under the song's opening | **10.650** |
| Picture | **281.283** |
| Tail — black under the outro | **16.065** |
| **Total** | **307.998** — the song, exactly |

`head + picture + tail == song` is asserted, with **both** head and tail derived
and neither typed.

### The act ends on the cathedral

Cutting 13.934 s of publisher end card freed time that could not go to the head,
because the head is now spoken for by the sync — lengthening it would slide
every frame against the song and drag the shield off the downbeat. So the freed
time goes to the **tail**. The owner: *"cut to black, end on the heroes"*.

The last picture is now **source 360.5 → 362.2**: three figures walking into a
cathedral through the window light. Before it, at source 358.2 → 360.5, the
Hunter's hero pose under the caged Traveler — the shot that carries Cayde's
chat card. That shot is **2.3 s** and the card's minimum hold is **2.2 s**, so
it fits by a tenth of a second. **Do not shorten it.**

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

- **The master is stale.** Every number in this file describes the cut as
  `scripts/build_efmb.py` now defines it. The delivered file still carries the
  old one — the human dissolve, the mech, and 13.9 s of Activision slate. It
  must be rebuilt and re-measured on the **delivered** file before this act is
  shown.
- **Provenance.** The picture is fan-compiled. Inherits #55. The owner has since
  set a standing rule — *"bias towards official bungie"* — which this act's own
  source does not meet; upgrading it to Bungie's uploads of the four trailers is
  available and not done.
- **The source was fetched at the 1080p rung** when 2160p exists for the same
  upload — [#86](https://github.com/castrojo/destiny-vids/issues/86). Re-fetching
  would mean re-verifying every boundary here, since they are measured against
  the current file.
- **The tail** is now 16.065 s of black under the outro. The owner wants action
  there rather than black; candidate wide-traversal shots are being sourced from
  official Bungie uploads only, and none is committed to this cut yet.
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
