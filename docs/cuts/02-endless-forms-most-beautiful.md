# 02 — *Endless Forms Most Beautiful* (act II)

**Status:** **credited and delivered** as **act II** of the running order —
`~/Videos/Wolves/Prod/02-endlessformsmostbeautiful.mp4`, and **in the
programme** as of the megacut's v0.5. Delivered is not published. Provenance on
the source is **weak and recorded** (below).
**Runtime:** 307.998 s (5:07.998) for a 307.998 s song — the film *is* the song.
**Master:** `renders/efmb-plated.mp4` — 1920x1080 H.264, 30 fps, FLAC 48 kHz
stereo, **−1.0 dBTP, −11.3 LUFS integrated, LRA 5.9**, measured on the
**delivered** file. `renders/efmb-hq.mp4` is the same cut before the plates.

Origin: [issue #74](https://github.com/castrojo/destiny-vids/issues/74) — act II
had a slot in the canonical order and no film. This is the film.

## What this act is

The one act built entirely from Bungie's **live-action** trailers, scored to an
instrumental so the picture carries it alone. Five unbroken runs in source
order, one song end to end, no excision and no pause.

It is a **feature act, not a hero video** ([`docs/catalog.md`](../catalog.md)) —
but it is no longer uncredited. Thirteen plates name the people the show is
about; see [The cast](#the-cast) below. Its other on-screen copy is the act
slide, which belongs to the megacut.

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

## The cast

Thirteen plates, generated by `scripts/build_efmb_plates.py` into
[`stories/02-endless-forms-plates.json`](../../stories/02-endless-forms-plates.json).
The manifest is an **output**: a conflict in it is settled by re-running the
tool, never by hand.

| Film | Who | Where, and why that shot |
|---|---|---|
| 0:54.634 | **Joseph Sandoval · Ricardo Rocha · Karena Angell** | The trio out of the fog, **left to right as the owner gave them** |
| 1:13.401 | Giklab | The hooded Hunter and his Ghost, close |
| 2:10.267 | Dylan Taylor *(placeholder)* | The Titan walking out of the dark |
| 2:41.767 | **William Rizzo** | The lone Hunter on the Dreadnaught |
| 2:51.801 | HuntedRaven7 | Two Guardians climbing the stair into the light |
| 3:30.034 | hanthor | The Guardian reaching out over the neon city |
| 3:37.701 | Ahmed Adan *(placeholder)* | Three Guardians, supers lit, before the throne |
| 4:29.700 | **Kyle Gospodnetich** | The Sentinel raising the Void shield — **on the downbeat** |
| 4:34.333 | **`[ p5 ]`** | The hooded Hunter, blade raised, magenta arc blooming |
| 4:43.666 | **`[ EyeCantCU ]`** | The Warlock, arms spread, going off in solar fire |
| 4:47.933 | **`[ REDACTED ]`** | Cayde's sign-off, as a chat card |

Every window is authored against a **source** timecode and converted to film
time by `build_efmb.film_for_source`. Nothing here types a film timecode,
because every mark the owner ever gave has moved: the head lead went
8.564 → 10.650 and run 1's out point 6.467 → 4.017, so his `0:55` now points
0.364 s away from what he meant and his `4:50` by 2.131. A binding whose frame
gets cut **raises** rather than sliding onto whatever now occupies that second.

Copy is **reproduced, never composed** — every word comes from
`vocab/casting.yaml`, and a missing key raises instead of falling back to the
generic blueberry plate, which would quietly overwrite an identity the owner
authored. `[ p5 ]` and `[ EyeCantCU ]` are authored copy and a test pins them.
The two placeholders are people the owner **named** with no plate written yet
(#87): they get their name and the neutral eyebrow, and no invented rows.

### Kyle's name arrives on the slam

His plate's `at` is derived from the **same sync anchor as the cut**, so the
card, the Sentinel's shield and the drum land together at 269.700 — and stay
together if a run ever moves.

### Cayde is redacted here, and only here

The `cayde_6` binding names **Jorge Castro**, and that is correct everywhere
else in the programme: he is revealed later, so acts I and III–VII are
untouched. Here the joke depends on the audience not being told yet, so the
pill reads `[ REDACTED ] | I'm so proud of you kids!`. The bracketed form is
the owner's own treatment — the same one he authored for `[ p5 ]` — and it is a
**redaction of a name this repo already knows**, recorded beside it, never an
invented one. The line is his: it stays `owner_supplied` and must never read as
recovered Bungie dialogue.

The shot is 2.30 s against a 2.2 s minimum hold. It fits by a tenth of a
second. **Do not shorten it.**

### Two burned-in titles the plates keep clear of

The act removes every title card in the source, but two are **welded to picture
it keeps** and cannot be cut without losing the shot:

| Source | What |
|---|---|
| 172.500 → 174.433 | `BECOME LEGEND`, fading in over the cave at the end of run 2 |
| 356.500 → 358.200 | `NEW LEGENDS WILL RISE`, across the end fight |

The first is a **different instance** from the one the removal list already
names at 244.833. Both are recorded as no-plate zones: a plate that would run
into one is shortened, and a plate that would *start* inside one raises, since
laying our credit over the publisher's is the one thing that would make it look
deliberate. Ahmed Adan's badge was on the first of them until the **burned film
was looked at** — the manifest could never have shown it.

## Sub-chapters

```console
$ python3 scripts/build_efmb_plates.py --chapters
0:54.234  TOC
2:41.367  Rizzo
```

Anchored to the same source timecodes as the credits, so a chapter and the
credit it belongs to cannot drift apart. A chapter starts where the **shot**
starts, not where the plate does — the plate is 0.4 s late on purpose.

Nothing consumes them yet: `tools/megacut.py` derives the programme's chapters
from act **slides** only. That is [#92](https://github.com/castrojo/destiny-vids/issues/92).

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

- **Provenance.** The picture is fan-compiled. Inherits #55. The owner has since
  set a standing rule — *"bias towards official bungie"* — which this act's own
  source does not meet; upgrading it to Bungie's uploads of the four trailers is
  available and not done.
- **The source was fetched at the 1080p rung** when 2160p exists for the same
  upload — [#86](https://github.com/castrojo/destiny-vids/issues/86). Re-fetching
  would mean re-verifying every boundary here, since they are measured against
  the current file.
- **The tail is 16.065 s of black** under the outro. The owner's decision, so
  the act keeps room for more content later: *"keep it black for future
  flexibility to add more content"*. A fill was sourced and verified shot by
  shot from official Bungie uploads — nine shots, ~16.1 s, none of them used
  elsewhere in the show — and is **recorded rather than cut in**. Adding it
  means reworking `TAIL_POLICY` and the `head + picture + tail == song`
  assertion, and the sync anchor must survive it.
- **Recorded plate gaps** — [#87](https://github.com/castrojo/destiny-vids/issues/87):
  Karena has no avatar because no GitHub login for her is on record anywhere in
  this repo, so her wreath rings the drawn crest; Ricardo's subclass is
  unauthored, so his class row reads bare `Hunter`; Joseph and Dylan have no
  logins. Every one of them is a word only the owner can write.
- **The bed's `downbeat_phase` is one beat off** —
  [#89](https://github.com/castrojo/destiny-vids/issues/89). It does not affect
  this act: the anchor at 269.700 was measured from the audio by ear, not read
  from the stored phase.
- **Sub-chapters are emitted and unconsumed** —
  [#92](https://github.com/castrojo/destiny-vids/issues/92).
- **No lossless provenance.** As with every bed in this show, the source is a
  YouTube Opus rung; the FLAC master is lossless *relative to that*.

## Reproducing it

```bash
python3 scripts/build_efmb.py                     # print the cut and the arithmetic
python3 scripts/build_efmb.py --json plan.json    # the same, machine-readable
python3 scripts/build_efmb.py --render            # cut, black, and score it

python3 scripts/build_efmb_plates.py              # print the credits
python3 scripts/build_efmb_plates.py --write      # regenerate the manifest
python3 scripts/build_efmb_plates.py --check      # CI: committed == generated
python3 scripts/build_efmb_plates.py --fetch-avatars

python3 tools/plate.py render --manifest stories/02-endless-forms-plates.json \
    --out-dir renders/plates-efmb --fit-video renders/efmb-hq.mp4
python3 tools/plate.py burn --video renders/efmb-hq.mp4 \
    --manifest stories/02-endless-forms-plates.json \
    --plates-dir renders/plates-efmb --out renders/efmb-plated.mp4 --fit-picture
```

The media is fetched, never committed: the compilation as H.264 into
`media/yt_destiny_all_live_action_trailers.mp4`, and the bed as Opus 251
decoded to `media/bed_endless_forms_most_beautiful.wav`.

### Two ffmpeg spellings this act has been lost to

Both exited 0 and wrote a plausible file. Both are now pinned by tests that
inspect the **argv**, not the video.

1. **`-filter_complex` re-times the act** ([#88](https://github.com/castrojo/destiny-vids/issues/88)).
   The identical normalising chain as `-vf` runs 307.99 s; wrapped in a
   filtergraph the same frames come out 299.48 s — 2.8% fast, 505 frames
   discarded where the rescaled timestamps collide. So `--render` uses `-vf`
   only, and black is a real encoded clip joined by the concat **demuxer**.
2. **A one-frame PNG does not survive five minutes of timeline.** Fed to
   `overlay` as-is it EOFs at once, and `eof_action=repeat` does not hold it:
   a plate gated to t=5 draws and the identical plate gated to t=269 does not.
   Act II burned "successfully" with **no credits on it at all**, twice, before
   anyone looked at a frame instead of the manifest. Each plate input is now
   `-loop 1 -framerate 1 -t <duration>`, and the output carries its own `-t`
   because with every input the same length there is no unambiguous shortest
   stream — that one cost 318.767 s against a 307.998 s cut.
