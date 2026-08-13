# Seven Days to the Wolves — the musical (editorial pass)

**Status:** editorial pass, delivered for review as **act VI** of the running
order — `~/Videos/Wolves/Prod/06-7daystothewolves.mp4`, hardlinked from
`~/Videos/wolves-musical/`. Delivered is not published: it is deliberately not
in `yt-refresh.py`'s manifest, because that means choosing a title and a
description, which is the owner's call. It is also **the one act with no
lossless master** (#58).
**Runtime:** 432.7 s (7:12.7) for a 424.0 s song. The 8.66 s difference is the pause.
**Rendered:** `renders/07-wolves-timing-pass.mp4` — 1920x1080 H.264, 30 fps,
AAC 48 kHz, −1.2 dBTP, −10.0 LUFS integrated.

The project's first musical: one song, three acts. This is the flagship the
hero videos and the teaser are marketing toward.

## What this pass is

The pass before this one was a **timing pass**: nothing was removed, and every
span destined for removal stayed in the timeline at its exact duration behind a
marker card, so the cut could be played against the music and judged before a
frame was actually taken out. That worked, the owner reviewed it, and this pass
carries out the notes.

> **Mark, don't cut — until the notes come back.** The convention is written up
> in [`docs/skills/editing/SKILL.md`](../skills/editing/SKILL.md).

What survives from the timing pass is its arithmetic, and it is the reason the
notes could be applied without re-timing anything: **a card and the footage it
replaces are the same number of seconds.** So replacing a black screen with a
photograph moves no anchor at all, and only the genuine removals cost anything.

Three timing invariants govern every edit, and all three are assertions in
`scripts/build_wolves.py` rather than prose here:

1. **Bed anchors never move** — the gallop, the flute entry, the HOWL, the pause.
2. **Act I removals are bought back off the head**, automatically, by the
   derived `CAPTURE_IN`. Cut more out of the intro and the capture starts
   earlier; the gallop does not move.
3. **A removal inside Act III must be filled.** That act's length is pinned
   between two anchors *and* `wolves_act2` ends at 210.015 s, so the Pale Heart
   run cannot grow a tail to cover a removal — the footage does not exist.

**13 source runs, not 289 shots.** Every act is one unbroken run in source
order. Act II and Act III-A are literally contiguous: the window crash is not a
cut at all — it simply happens, which is the strongest possible way to land it
on the flute entry.

## Sources

| Role | Source | Notes |
|---|---|---|
| Bed | Nightwish, *7 Days to the Wolves* — [`LASru9j0oIc`](https://www.youtube.com/watch?v=LASru9j0oIc) | Album version (*Dark Passion Play*), official Nightwish channel. 424.0 s |
| Acts I, II, III | *All Cinematic Trailers (Destiny)* — [`oRoHW97OZcs`](https://www.youtube.com/watch?v=oRoHW97OZcs) | **A fan compilation by Antesion**, 30:23. Not an official Bungie upload — see Rights |
| Act III | *Destiny 2: The Collection Trailer* — [`qI-fxJM8rSM`](https://www.youtube.com/watch?v=qI-fxJM8rSM) | Official Destiny 2 channel |
| Act III | *Destiny 2: The Final Shape \| **Gameplay** Trailer* — [`UchfadQhX7w`](https://www.youtube.com/watch?v=UchfadQhX7w) | **Official Destiny 2 channel.** 123 s, 2024-04-09. New in this pass |
| Stills | Contributor Summit group photographs | CNCF, CC BY-NC-ND 4.0 — see Rights |
| Artwork | `~/Pictures/Artwork/wolves.jpg` | The *Seven Days to the Wolves* poster |

### The Gameplay Trailer is not the Launch Trailer

This bit cost a wrong turn, so it is written down. The owner supplied three
640x360 proxy clips named `UchfadQhX7w_Kat_77-82`, `_Kaslin_83-87` and
`_Laura_91-97`, and this repo already indexes a file called
`yt_destiny_2_the_final_shape_launch_trailer`. They are **different videos**:

| Title | ID |
|---|---|
| Teaser Trailer | `gGa8K-yQr8k` |
| Reveal Trailer | `Ehl6aWUiA4Y` |
| **Gameplay Trailer** — the proxies' source | **`UchfadQhX7w`** |
| Launch Trailer — indexed here already | `6Gm5mbwrqSA` |

Frame-matching all three proxies against the indexed 1080p launch trailer found
**no match at any offset**: best mean-abs-pixel-difference 45.3 / 60.6 / 59.0 at
160x90, with runners-up within 0.5 of the best — noise, not a match. Fetched
fresh as **4K AV1 (format 401)** and scaled to 1080p; the proxies then match the
new master to the frame (diff 3.7 / 4.2 against runners-up above 20).

It is an **official Bungie upload**, so it is better provenance than the fan
compilation the rest of the film rests on.

Three window extracts keep every seek in a short file — `render.py` seeks after
`-i` for frame accuracy, which decodes from zero (`docs/rendering.md`):

| Extract | Compilation span | Carries |
|---|---|---|
| `wolves_act1` | 0:00 – 3:30 | the Destiny 1 opening cinematic |
| `wolves_act2` | 23:00 – 26:30 | Neomuna, the crash, the Pale Heart |
| `wolves_act4` | 26:30 – 30:23 | the finale, the Guardians assembled |

Act II's opening 17.8 s comes from `yt_destiny_2_lightfall_launch_trailer` — an
**official Bungie upload**, already indexed here. See "The gallop cuts to neon".

**Curse of Osiris is excluded from the whole feature.** It is a finale; the
builder asserts on it rather than trusting anyone to remember.

## Structure

| # | Film | Bed | Source | What |
|---|---|---|---|---|
| 1 | 0:00 – 0:10 | 0 – 10 | title card | Project Bluefin, over the song's quiet opening |
| 2 | 0:10 – 1:30.8 | 10 – 90.8 | `act1` 0:10.1 – 1:40.9 | **Act I**, the orrery approach and the capture |
| 3 | 1:30.8 – 1:33.8 | 90.8 – 93.8 | **summit** | over the black the owner asked to lose |
| 4 | 1:33.8 – 2:04.1 | 93.8 – 124.1 | `act1` 1:43.9 – 2:04.2 | ...continuing, the Ghost-alone shot gone |
| 5 | 2:04.1 – 2:05.4 | 124.1 – 125.4 | **summit** | over a second black |
| 6 | 2:05.4 – 2:44.9 | 125.4 – 164.9 | `act1` 2:16.8 – 2:49.7 | the court scene and the 2:24 sequence gone |
| 7 | 2:44.9 – 2:47.0 | 164.9 – 167.0 | **summit** | over a third black |
| 8 | 2:47.0 – 3:02.8 | 167.0 – 182.8 | `act1` 3:07.2 – 3:23 | the ship rising, into the gallop |
| 9 | 3:02.8 – 3:20.6 | 182.8 – 200.6 | Lightfall trailer | **Act II** opens: the gallop cuts to neon |
| 10 | 3:20.6 – 4:19.4 | 200.6 – 259.4 | `act2` 0:47.1 – 1:45.9 | Neomuna, unbroken into the crash |
| 11 | 4:19.4 – 4:33.5 | 259.4 – 273.5 | `act2` 1:45.9 | **Act III**, the crash, the strand descent |
| 12 | 4:33.5 – 4:37.0 | 273.5 – 277.0 | **summit** | the whole summit, over the enemy CU |
| 13 | 4:37.0 – 4:39.7 | 277.0 – 279.7 | artwork | held through the HOWL and the silence |
| 14 | 4:39.7 – 4:47.0 | 279.7 – 287.0 | `act2` 2:06.2 | the band slams back in, on three Guardians |
| 15 | 4:47.0 – 5:22.2 | 287.0 – 322.2 | `act3` 0:51.8 – 1:27.0 | the Collection Trailer montage, two slots filled |
| 16 | 5:22.2 – 5:30.9 | *paused* | `gameplay` 0:44.8 – 0:53.5 | **the song stops**; the explosion and the portrait |
| 17 | 5:30.9 – 5:46.9 | 322.2 – 338.2 | `act2` 2:51 – 3:07 | the Pale Heart, Guardians gathering |
| 18 | 5:46.9 – 6:00.8 | 338.2 – 352.1 | `gameplay` 1:17.6 – 1:35.2 | three action runs, where the Ghost sequence was |
| 19 | 6:00.8 – 6:09.9 | 352.1 – 361.2 | `act2` 3:21 – 3:30 | back on the plains |
| 20 | 6:09.9 – 7:00.4 | 361.2 – 411.7 | `act4` 0:00 – 0:50.5 | the finale, the Guardians assembled |
| 21 | 7:00.4 – 7:12.7 | 411.7 – 424.0 | artwork | the outro, over the fade |

**The song plays from the first frame**, under the title card — the record's own
opening is quiet pickups, which is what a title card wants. The only source
audio in the film is the 8.66 s pause.

## The owner's notes, and what each one measured

Every note is a *film* timecode. Each was confirmed by extracting the frame it
names, then snapped to a measured shot boundary — the black spans from
`blackdetect`, the picture from `ContentDetector`. Nothing below was rounded to
a convenient number.

| Note | What was on screen | What was done |
|---|---|---|
| "1:21 just flash the enemy and then move on and remove the black" | the enemy CU at `act1` 99.3–100.1, a dark tail, then 3.0 s of black | the CU is kept as the flash it already is; the dark tail (0.771 s) is **cut**; the black becomes a **summit photograph** |
| "1:41 skip the ghost by itself and cut to the shot of them together" | Ghost alone at 122.9–124.2, the two together from 124.2 | the Ghost-alone shot is **cut** (1.240 s) |
| "speeder bike scene is awesome" | — | untouched |
| "02:20 court scene skip" | the throne room, 160.0–162.4 | **cut** (2.379 s) |
| "02:24 skip this whole sequence until 2:30" | ships over canyon → caged Vex mind → Ghost over a map | **cut** 163.3–169.7 (6.435 s), out on the ship lifting off |
| "2:45" | 2.1 s of black | **summit photograph** |
| "cut out the renegades slide" | the `COUNTLESS LEGENDS` publisher slide | **removed outright** — see below |
| "we want this explosion to be cortney's segment" | the wrong shot entirely | recut from the Gameplay Trailer — see below |
| "5:26 … keep this in its entirety" | the three Guardians on the plains | untouched, and it now follows Cortney directly |
| "cut 5:44 extended ghost sequence … to 5:56" | the Ghost alone, 13.9 s of it | **cut**, and the hole filled — see below |
| "Replace all black screen/placeholders" | 4 marker cards, 3 black spans | six photographs, one slide removed |

One black span the owner did not name — `act1` 135.4–136.8, at film 1:55 — is
also replaced, because "replace **all** black screen" is the instruction. Two
much shorter blacks (0.37 s and 0.54 s) are **left alone**: they are transitions
inside the cinematic, and a third of a second of photograph is a subliminal
flash, not a picture. The threshold used is 1.0 s, and it is written down here
rather than left for somebody to rediscover.

The excisions total 20.094 s, so the capture now starts at `act1` **10.072**
instead of 21.166 — which is where the documented capture begins. The 11 s
bought back at the head is the **Mars → Earth orrery approach**, checked by
frame, and it builds where the old head started cold.

## Everything below is measured

### The renegades slide could not simply be deleted

The `COUNTLESS LEGENDS` slide sits at `act3` 87.4–89.4, immediately before the
pause. Deleting its 2.0 s would have pulled the pause 2.0 s earlier and **off
its downbeat** — the one anchor in this section.

So the montage **starts earlier instead**: in-point 55.0 → **51.767** (a detected
boundary), running to 86.967, which stops 0.433 s short of the slide. Bed time
is unchanged, every anchor holds, and the slide never appears. The final run's
tail is the only thing trimmed, which is the house rule — an in-point is what
the detector worked to find, so a trim never moves the start.

`test_the_publisher_slide_the_owner_cut_never_comes_back` asserts on the
*timecode*, not on the absence of a card, because "no card" would still pass if
a run grew into the slide.

### The pause: the explosion, the portrait, and the cut

The owner's note — *"we want this explosion to be cortney's segment. Capture the
length of the shot, including the portrait of her in transcendence glowing mode,
hold the scene until the cut"* — came with a reference clip,
`~/Videos/wolves-directors-cut/cortney.mp4` (9.009 s, 640x360, with music).

**The timing pass had the wrong footage.** It paused on the Collection Trailer
at 0:29.4. The reference clip frame-matches the **Gameplay Trailer** at
**45.0 – 54.009** — mean abs pixel difference 3.2–4.1 at 160x90 against
runners-up of 22–33, at four probes across the clip. It is not in the
Collection Trailer at all.

The shot's own boundaries were then measured by differencing consecutive frames
at 1/30 s:

```
51.835   frame delta 170.2   the explosion's white bloom begins
53.003   ...decaying into the transcendence portrait
53.470   frame delta  89.1   the cut out of the portrait
```

against a background of under 30. The pause runs **44.811 → 53.470** (8.659 s):
in-point at the enclosing shot boundary so the moment builds rather than
starting mid-air, out-point exactly on the measured cut. The reference is
9.009 s; this is 8.659 s.

It is `audio: "source"`, so it **costs no bed time** — extending it from 3.65 s
only makes the film longer, and no anchor moved.

On *"recreate it with the sfx pristine version you have, no music"* — **the
delivered insert does not do that, and an earlier paragraph here claimed it
did.** That claim argued from a spectral-flatness measurement (0.45 run-up,
0.47 across the explosion) that the trailer's own audio was "broadband, not
tonal". It is deleted: a flatness average across a loud explosion can mask a
bed, and a measurement is not a licence to ignore the source the owner handed
over. Measured properly ([issue
#95](https://github.com/castrojo/destiny-vids/issues/95)), the trailer's audio
on this span **is** the with-music mix — correlation **0.875** against the
owner's own *"here it is with music"* clip at matching loudness.

**The fix is a source, not a process** — nothing is separated, ducked or
enhanced; the audio tenet in
[`docs/skills/references/audio-standard.md`](../skills/references/audio-standard.md)
rules that out, so the SFX-only audio must come from another upload of the
same moment. The owner named *DESTINY 2: THE FINAL SHAPE All Cutscenes*
([`yNBMDXdp69g`](https://www.youtube.com/watch?v=yNBMDXdp69g), 2:18:00). It
was fetched (plain 251 Opus — never a `-drc` rung) and searched end to end:

| Method | Result |
|---|---|
| Whole-movie visual scan, mean abs pixel diff, 9-frame windows | best **59.5** — noise; the control finds the beat in the gameplay trailer at **4.8** |
| Whole-movie visual scan, normalised cross-correlation | best **0.30** — noise; the trailer control scores **0.998** |
| Audio cross-correlation of the insert against the movie | no peak above **0.12** anywhere |

**The moment is not in that video.** It is first-person *gameplay* — the
seventh-column super cast — and a cutscenes compilation does not carry
gameplay. So the insert still plays the trailer's (with-music) audio, and the
gap is recorded here and in `scripts/build_wolves.py` next to the shot rather
than worked around: **what is needed is a source that contains this gameplay
moment with an SFX-only mix** — the picture span is gameplay trailer
44.811 → 53.470 (gameplay-trailer clock), i.e. act film 5:22.2 – 5:30.9.
`tools/audiomix.py` already implements the swap (`audio_from` on the shot, the
span named in the *audio* source's clock); when the owner names a source that
contains the moment, the fix is one line in the builder and a rebuild.

### The Ghost sequence, and why its hole had to be filled

`wolves_act2` 187.022 → 200.965 is the Ghost alone, flying through fog and
machinery — 13.943 s, verified by frame at both ends, with the Guardians
returning to the plains on the cut at 200.965.

The Pale Heart run **cannot** simply grow a tail to cover the removal:
`wolves_act2` is 210.015 s long and the run already ends at 210.0. There is no
more footage. Act III-C's length is pinned between two bed anchors, so 13.943 s
of picture had to come from somewhere.

It comes from the three runs the owner supplied as proxies, recut from the
1080p master at detected boundaries:

| Source | Duration | What |
|---|---|---|
| `gameplay` 77.578 – 82.516 | 4.938 | a Titan holds the line behind a Ward of Dawn |
| `gameplay` 82.516 – 87.087 | 4.571 | a Warlock through the Dread, weapons up |
| `gameplay` 90.791 – 95.225 | 4.434 | a Hunter vaults into the light, and three walk in together |

= **13.943 s**, exactly. Only the last is trimmed, and only at its tail. They
play **under the bed**: the pause is the film's one section with its own audio.

### Casting on those three runs — and an override

The owner named the people, and **overrode their own filenames doing it**:

> "the warlock should be kaslin fields and the hunter was laura santamaria but
> make it github.com/inffy"

| Shot | Proxy filename said | Cast as | Identity |
|---|---|---|---|
| Titan | Kat | **Kat Cosgrove** | authored; already bound in `vocab/casting.yaml` |
| Warlock | Kaslin | **Kaslin Fields** | authored in the website's `characters.json` (slug `kaslin`) |
| Hunter | **Laura** | **`github.com/inffy`** | **none authored anywhere** |

The override is recorded because the proxy file
`UchfadQhX7w_Laura_91-97.mp4` still carries the old name, and **a wrong credit
is not recoverable by a revert**.

**None of the three is plated**, so none of this reaches the screen in this
pass: the runs play under the bed as action, and credit belongs to the credits
sequence ([issue #51]). `inffy` is recorded in `leads.pending` with
`automatable: no` — no Guardian identity is authored for that account in the
reference deck or the website's `characters.json`, and a missing name is
omitted and recorded, never invented.

Kaslin is deliberately **not** added to `vocab/casting.yaml`. Her identity is
authored, but `leads` is keyed by *Destiny character* and there is no Destiny
character here — she is a Warlock in gameplay footage. The right home is
`ensemble.titles`, which is keyed by **GitHub login**, and nobody has supplied
hers. Inventing either key would have been the fault this file exists to
prevent, so the casting is recorded in the shotlist and here instead.

### The summit photographs

Six Contributor Summit group photographs replace the four `COMIC PLACEHOLDER`
cards and the three Act I black spans, built by
[`scripts/build_summit_plates.py`](../../scripts/build_summit_plates.py).

They are **picture, not slates**, which is why that script sits beside
`tools/marker.py` rather than inside it: a marker must never be mistakable for
finished picture, and the reverse holds too.

The crop is **computed, not centred.** The website's own sequence file already
records the problem next to its `backgroundMotion: 'kenburns'` flag — these are
wide group shots with empty plant and floor padding, and a centred crop frames
the padding instead of the people. So the 16:9 window is chosen by measuring
local variance (faces, lanyards and badges are high-frequency; foliage, carpet
and ceiling are not) and keeping the densest band. All six then get one common
grade, so they read as a set rather than as six unrelated stills.

Selection favoured the most people in frame, per the owner: the three overhead
wides of the whole summit take the three longest slots. Owner-confirmed
rejections: `summit-11` (one person holding a shirt), `summit-03` (its
near-duplicate) and `summit-15` (a blurred audience).

### The two act hinges

Unchanged, and still the only frame-accurate obligations: the **gallop at
182.834 s** (the spectral centroid collapses to 768 Hz) and the **flute entry at
259.390 s**, both snapped to the bar grid (76 bpm, bar 3.158 s).

### The song's one silence — and where the artwork goes

Scanning the whole bed for full-band drops finds **exactly one interior gap**:

```
gap_start  gap_end   len   next_downbeat  offset
   278.64   279.64  1.00        279.661   +0.023
```

A full second of silence, ending 23 ms before a downbeat. That is the "HOWL",
and it is the only place in 424 seconds where the band stops. The artwork comes
up at 277.0 — over the enemy close-up, before the shout — holds through the
silence, and **the picture returns on the slam**, onto three Guardians running
at camera. Nothing about that beat was chosen by taste.

The scan's only other hits are the intro's quiet pickups (1.6–6.3 s) and the
outro fade (416.8 s → end), which is why the artwork closes the film there
rather than the picture being truncated.

### "4:19 needs to be backed up a tad", as a number

The crash *shot* starts at extract 105.4; its audio impact ramps from 105.05 and
**peaks at 105.9**. The first cut put the shot's first frame on the flute entry,
so the impact landed half a second late. The Act II run is now placed so
**extract 105.9 lands on 259.390** — the shot starts a beat early and the impact
lands on the beat change.

### The gallop cuts to neon, and Savathûn stays out

The compilation reaches Neomuna at extract **47.1** — verified by frame. Before
it lie Savathûn's Throne World and the `THE WITCH QUEEN` branded cards, which
the standing no-Savathûn rule keeps out of this film.

That leaves only **58.8 s** of Neomuna before the crash, against a 76.556 s
gallop-to-flute span. An earlier build closed that gap by starting the run 17.8 s
early — which is exactly how the Witch Queen montage got in: not by anyone
choosing it, but by needing to fill time. `test_act_two_never_reaches_back_into_savathuns_throne_world`
now makes that impossible.

The gap is filled from the front instead, by the **official Lightfall launch
trailer**: the neon skyline establishing (0:44.9), a Guardian in a rain-slick
alley (0:52.0), then the Strand sequence (1:12.9 →). So the gallop lands on a
picture change — a hard cut to neon — and hands over to the compilation exactly
at the Neomuna boundary. It is also better provenance for 17.8 s of the film.

### The intro trim, and why the in-point is derived

The capture is source 0:10 → 3:23, and the intro has only 182.834 s to spend
once the song plays from frame one. Everything the owner cut out of the middle
is bought back off the **head**, because the capture's ending (the ship rising,
the fade) is the payoff into Act II.

**The in-point is therefore derived, not written down:**

```python
CAPTURE_IN = CAPTURE_OUT - (ACT2_IN - TITLE_CARD_LEN) - sum(cuts)
```

Cut another span out of the intro and the capture simply starts earlier — the
gallop does not move, and no anchor after it does either.

`sum(cuts)` counts only the spans marked `"cut"`. A span **replaced** by a
photograph costs nothing, because the photograph is exactly as long as the black
it stands in for. That distinction is the whole reason the black spans could be
dealt with without re-timing Act I, and
`test_act_one_edits_are_bought_back_off_the_head` pins both halves of it.

One boundary moved for its own reason: the static-sun excision now ends at
**67.435** rather than 67.166, because that is where `blackdetect` says the
black actually ends. The old value leaked 0.27 s of black into the cut.

### Two clocks

The mechanic and when to reach for it are in
[`docs/skills/scoring.md`](../skills/scoring/references/two-clocks-and-levels.md).
What is specific to this cut: the song plays from the first frame, the only
`audio: "source"` shot is the pause, and the film is therefore **432.7 s for
424.0 s of music**. Every anchor in the builder is asserted against bed time.

### The pause's length, measured

The rule — [a diegetic insert has to be allowed to
end](../skills/scoring/references/two-clocks-and-levels.md#a-diegetic-insert-has-to-be-allowed-to-end) — came out
of this cut. The pause was first taken at 1.8 s and the moment *started and did
not finish*; the timing pass took it to 3.65 s. This pass takes it to the shot
the owner actually meant, 8.659 s, with the out-point on a measured cut rather
than on an audio envelope.

### Guardians together

The selection signal is **Guardians in frame together**, and the runs flagged
`plate_slot` in the shotlist are there for the nameplate pass rather than being
re-found by eye later: Act II opens on three Guardians advancing abreast
(source 23:29), the slam after the silence lands on three running at camera,
both halves of the Pale Heart run have them gathering on the plains, and the
finale is the whole assembled crowd.

## Editorial rules, enforced in the builder

- **No Curse of Osiris**, anywhere — asserted.
- **No shot used twice** — asserted. The first cut replayed 25.
- **No Savathûn. The Witness: eyes or smoke, never its body.** Act II starts at
  the Neomuna boundary (source 23:47.1), after the Throne World and its branded
  cards; the Pale Heart run starts at source 25:51, after the pyramid and
  monolith material. Both are asserted, because both were breached by a run
  reaching backwards to fill time rather than by anyone choosing the footage.
- **No publisher slide survives** — each is removed, or replaced by picture, and
  the montage is asserted never to reach the removed one's timecode.
- **The film ends on the Guardians, not a logo.** The finale run stops at
  source 26:30 + 50.5, a beat before the branded `THE FINAL SHAPE` cards.

## Audio

The 2007 master is loud: −6.8 LUFS integrated, and decoded its true peak
measures +2.1 dBFS. The fix is a **static −3.5 dB gain** applied once, at the
final mux — not `loudnorm`, not a limiter: a static gain changes no dynamics at
all, and the LRA is the artist's, not ours.

**The pause needed the same treatment, for its own reason.** An insert is
somebody else's mix and it brings peaks nobody here planned for, over a region
far too short to move the film's integrated loudness. Measured:

| Region | True peak |
|---|---|
| whole file, before | **−0.4 dBTP** — over the −1.0 gate |
| a bed region | −3.2 dBTP — fine, and unchanged |
| the 8.7 s pause | **−0.4 dBTP** — the culprit |

So the pause gets a static **−1.5 dB** of its own
(`tools/audiomix.py --source-gain-db`, added in this pass as the mirror of
`--bed-gain-db`). Pulling the whole film down would have worked too and is
worse: it would quietly re-level music whose gain was already decided and
documented above.

Delivered: **−1.6 dBTP**, −10.1 LUFS integrated, LRA 4.0.

### The pause was silent, and everything else still passed

Worth recording, because it nearly shipped. The Gameplay Trailer was fetched
with `yt-dlp -f 401`, which is **video-only**, so the one region of the film
that plays its own audio rendered as **digital silence** — and every duration,
every anchor and every bed-sync check passed anyway, because the bed is muted
there by design. A silent insert sounds exactly like a working pause until
somebody plays it.

The verification now asserts a floor on the region's RMS as well as its
correlation against the bed. The two catch opposite faults and neither implies
the other: the floor catches a silent insert, the correlation catches the bed
leaking into a region that was supposed to be a pause.

## The tail plates — the Cayde-6 reveal

**Added 2026-08-13**, from the owner's brief. Act II plates Jorge Castro as
`[ REDACTED ]` with the note *"act II only — he is revealed later in the
programme"*. **This is that reveal**, and it is why the programme withholds his
name for sixteen minutes: it pays off on Cayde-6 walking alone out of the fog
at the end of this act, and three gold credits follow him.

The manifest is [`stories/06-wolves-cayde-plates.json`](../../stories/06-wolves-cayde-plates.json).

### The clock, settled on a frame

The brief's marks were **megacut** time. Act VI film = megacut − 673.992, which
`tools/megacut.py --locate 17:37` confirms independently (`VI @ 6:23.041`).
Nothing here is a film timecode anybody typed, and **every window was then
looked at** before a name was attached to it — the rule that caught both real
defects of the previous session, neither of which was visible in a manifest.

| Owner mark | Film | What is actually on that frame | Card |
|---|---|---|---|
| 17:37 | 382.7 | Cayde-6 alone in the fog, then the hooded close-up | **Jorge Castro**, basic blue |
| 17:37 | 386.3 | the Guardians walking up between the fire pillars | the narration, as the deck's title card |
| 17:45 | 391.008 | the Guardians assembled around the fire | **Kelsey Hightower**, gold |
| 17:49 | 395.008 | the group standing, sunset behind | **Brian Ketelsen**, gold |
| 17:51 | 397.008 | the front rank walking into camera | **Angie Jones**, gold |

Gold is `variant: leader` — the wolves overlay's `.wolves-guardian-plate-leader`,
which recolours the label and the title and deliberately leaves the class row
blue. The reveal carries no variant at all, which is the owner's *"basic blue,
like the blueberries"*.

### Why the reveal comes before the narration

Both are lower-third cards, so they cannot share a window — the one-card-at-a-
time check is there precisely to stop two credits stacking. The brief gives
both at 17:37, so they are sequenced inside that beat, name first, because the
name is the payoff the act has been saving. Swapping them is one edit to `at`.

### What the owner still has to settle

Recorded in the manifest's `unresolved`, and none of it is an agent's call:

- **`Harbringer Hunter`** is reproduced from the brief verbatim. The reference
  deck spells the same word *Harbinger* on the same person. One character, on
  his own credit — so it ships as he wrote it rather than silently corrected.
- **Two cards knowingly break the vocab-wins rule**, and that is a violation,
  not a design. [`plates/SKILL.md`](../skills/plates/SKILL.md) lists *"the
  brief's copy contradicts the binding, but the owner wrote it today"* as a
  **rationalization**: the vocab is the reviewed record, an issue body is
  editable, so **the vocab wins** — and `tools/plate.py plan` enforces exactly
  that. This manifest was hand-authored, so it never passed through `plan`.
  The committed `cayde_6` plate is `TRUSTEE // GUARDIAN` / Harbinger Titan /
  *"Upender of Antipatterns | The First Disciple"* / silver; `zavala` is
  `ARCHITECT // GUARDIAN` / Dawnblade Warlock. Both cards now carry an explicit
  `copy_override` naming #111 as the decider, and `render`/`burn` refuse the
  manifest without one. Resolution is #111: edit the bindings, or re-burn the
  two cards from them.
- **Brian Ketelsen and Angie Jones are not in `casting.yaml` at all.** Their
  copy exists only in the brief. A binding needs a GitHub login, and a login is
  not something to guess about a real person.
- **Kelsey and Brian carry the same title**, *Evangelist of the Open Sky*,
  exactly as written. Reproduced, not de-duplicated.

### Burning it

```bash
python3 tools/plate.py render --manifest stories/06-wolves-cayde-plates.json \
    --out-dir renders/plates-act6 \
    --fit-video ~/Videos/Wolves/Prod/06-7daystothewolves.mp4
python3 tools/plate.py burn --video ~/Videos/Wolves/Prod/06-7daystothewolves.mp4 \
    --manifest stories/06-wolves-cayde-plates.json \
    --plates-dir renders/plates-act6 \
    --out ~/Videos/Wolves/Prod/06-7daystothewolves-plated.mp4 --fit-picture
```

`Prod/` holds **one file per act**, hardlinked to its project master, so the
plated act is `Prod/06-7daystothewolves.mp4` →
`~/Videos/wolves-musical/wolves-7days-plated-master.mp4`. **The un-plated
master is kept beside it** as `wolves-7days-master.mp4`, because burning is not
idempotent: a re-burn starts from the clean act and never stacks a second card
on the first. Audio is stream-copied, so the act's duration is unchanged
(432.7330) and **no chapter after it moves**.

## Reproducing

**One command, once the sources are in `media/`:**

```bash
./scripts/rebuild-wolves.sh
```

That is the loop — notes, edit `scripts/build_wolves.py`, rebuild, watch. It
rebuilds the shotlist, the summit plates, the picture and the audio, copies a
review file to `~/Videos/destiny-cuts-review/`, and **refuses to hand over a
file** with either of the two faults that have actually shipped here: a silent
insert, or a true peak over the −1.0 dBTP gate. Both are invisible to "did it
render".

The steps it runs, for when a source has to be fetched first:

```bash
cd ~/src/destiny-vids
FF=/home/linuxbrew/.linuxbrew/bin/ffmpeg   # the system ffmpeg has no H.264 decoder

# 1. the new source: official Bungie upload, 4K AV1, video AND audio
yt-dlp -f 401 -o media/_gp4k.%(ext)s https://www.youtube.com/watch?v=UchfadQhX7w
yt-dlp -f 251 -o media/_gpaudio.%(ext)s https://www.youtube.com/watch?v=UchfadQhX7w
$FF -i media/_gp4k.mp4 -i media/_gpaudio.webm -map 0:v:0 -map 1:a:0 \
    -vf "scale=1920:1080:flags=lanczos,setsar=1" \
    -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p -c:a aac -b:a 320k \
    media/yt_destiny_2_the_final_shape_gameplay_trailer.mp4
python3 tools/ingest.py https://www.youtube.com/watch?v=UchfadQhX7w
python3 tools/annotate.py index \
    --video media/yt_destiny_2_the_final_shape_gameplay_trailer.mp4 \
    --video-record videos/yt_destiny_2_the_final_shape_gameplay_trailer.json

# 2. the summit plates (URLs and licence: stories/summit-photos.json)
python3 scripts/build_summit_plates.py --fetch

# 3. the shotlist, the picture, the audio
python3 scripts/build_wolves.py
DESTINY_FFMPEG=$FF python3 tools/render.py stories/seven-days-timing-pass.json \
    --media media --out renders/07-wolves-picture.mp4
DESTINY_FFMPEG=$FF python3 tools/audiomix.py stories/seven-days-timing-pass.json \
    --video renders/07-wolves-picture.mp4 \
    --bed media/bed_seven_days_to_the_wolves.wav \
    --bed-gain-db -3.5 --source-gain-db -1.5 \
    --media media \
    --out renders/07-wolves-timing-pass.mp4
```

**Fetching the audio separately is not optional.** Format 401 is video-only,
and a silent insert is invisible to every other check — see Audio.

## Verification

Not asserted — measured, on the delivered file.

| Claim | Evidence |
|---|---|
| Not truncated | full `-xerror` decode passes; 12 977 frames, 432.733 s |
| The song is where it should be | cross-correlation against the bed: lag **0.00 ms**, r = 0.9998–0.9999 at film 100/250/300 |
| The song resumes where it stopped | lag **1.00 ms** (8 samples at 8 kHz), r = 0.9997–0.9999 at film 340/400 |
| The pause is a genuine pause | correlation against the bed **−0.10** across the region |
| The pause is not silent | region RMS **−18.5 dB**, peak −1.9 dB — the trailer's own audio, **which carries the score**: the SFX-only source the owner named does not contain the moment ([issue #95](https://github.com/castrojo/destiny-vids/issues/95)) |
| Headroom | **−1.6 dBTP**, −10.1 LUFS, LRA 4.0 |
| Anchors hold | every `at_bed()` assertion in the builder, plus `tests/test_wolves_timing_pass.py` (28 tests) |
| No slide, no placeholder | asserted on timecode and on beat text, not on the absence of a card |
| No two summit slots repeat | peak pairwise correlation **0.27**, limit 0.35 |
| Joins | a frame extracted at every new cut and inside every summit slot |

## Rights

Bungie footage under Bungie's fan-content policy: non-commercial, metadata and
timecodes only, no footage committed. The bed is a Nuclear Blast recording used
as a non-commercial fan-work music bed.

**The compilation provenance question is unchanged.** Act I, Act II and the
finale all come from Antesion's re-upload. The fan-content policy covers
Bungie's footage; it does not make a third party's compilation ours to use. The
Gameplay Trailer added in this pass moves 22.6 s of the film onto an official
Bungie upload, so the exposure is slightly smaller than it was.

**That question gates publishing, not delivery**, and the two are different
things here by design: `~/Videos/Wolves/Prod/` holds what the show is made of,
and nothing is published until a file is added to `yt-refresh.py`'s manifest —
which needs a title and a description, i.e. the owner. So the cut is delivered
for review at the owner's instruction, and [issue #55] stays open.

**The CNCF photographs are `CC BY-NC-ND 4.0`**, verified on the Flickr metadata
for the group photos (account `143247548@N03`, album *Maintainer Summit North
America 2025*). Non-commercial reuse is fine. **NoDerivatives forbids
distributing a crop**, and every plate here is a crop: the sources are 3:2 and
the film is 16:9.

> **Owner decision, recorded verbatim:** *"crop it I have authority I work for
> the cncf"*

That is the licensing decision `AGENTS.md` reserves for the owner, and it has
been made **by the owner**, not inferred by an agent. It is recorded here and in
the header of `scripts/build_summit_plates.py` so nobody re-litigates it and
nobody mistakes it for an agent's judgement.

Attribution is required by the licence and is **not** burned onto the slides —
it belongs to the credits sequence ([issue #51]), together with the cast
credits. Until that sequence exists, this is an outstanding obligation, and it
is on the punch list rather than assumed done. The photographs show identifiable
attendees, so publicity and privacy interests survive the licence independently
of it.

## Punch list

- [ ] **Owner: is the Antesion compilation acceptable provenance?** [issue #55].
      Gates **publishing**, not staging. If not, Acts I and II and the finale
      need re-sourcing from official uploads.
- [ ] **Credits sequence** — [issue #51]. Now carries two obligations, not one:
      the cast credits *and* the CNCF attribution the photo licence requires.
- [ ] **Owner: Cortney Nickerson's Guardian identity** — [issue #59]. The pause
      is cast to her by the owner and she has no authored identity in
      `~/Videos/nameplates.json`, the website's `characters.json`, or
      `vocab/casting.yaml`. **The shot is rendered unplated.**
- [ ] **Owner: `github.com/inffy`'s Guardian identity** — [issue #72]. Same
      shape as Cortney's, recorded in `leads.pending`. The run renders unplated.
- [ ] **Kaslin Fields' GitHub login** — [issue #72]. Her identity *is* authored;
      the gap is that `ensemble.titles` is keyed by login and nobody has
      supplied hers, so there is nowhere correct to record it.
- [x] Nameplates are burned on the **tail** — the Cayde-6 reveal and three gold
      credits, see "The tail plates" above. The `plate_slot` runs through the
      rest of the act are still unplated.
- [ ] The bed is an official YouTube upload — lossy, and not the highest-quality
      upstream version. The purchasable lossless *Dark Passion Play* master is.
      Swapping it will re-time the cut: codec rungs differ in leading padding
      (~36 ms measured previously here), so cross-correlate and prove lag 0.
- [ ] Instrumental (`SE_c6nqy-y0`) and orchestral toggles not built.
- [ ] **A burned-in ESRB `TEEN` badge** sits bottom-right over the first ~4.4 s
      of the Neomuna run (extract 47.1 – 51.5). It is publisher copy, so it is a
      `redactions/` job for the finished cut, not a re-cut.
- [ ] **The Gameplay Trailer's segments are not tagged.** Its video record and
      75 detected shot boundaries are in, so the source is ingested and
      reproducible, but no `tags/` file exists — and without one, `overlays` is
      untagged and every segment would derive `clean = false`. That is the
      correct default, not a bug: it keeps unvetted footage out of `story.py`'s
      pool until somebody has actually looked at each shot. The runs used in
      this cut were picked by eye and do not go through the matcher.
- [ ] Neither compilation extract is in `segments/`. Tagging exists to feed
      `story.py`'s matcher and nothing here uses it — index them only if these
      sources are wanted in search.

[issue #51]: https://github.com/castrojo/destiny-vids/issues/51
[issue #59]: https://github.com/castrojo/destiny-vids/issues/59
[issue #55]: https://github.com/castrojo/destiny-vids/issues/55
[issue #72]: https://github.com/castrojo/destiny-vids/issues/72
