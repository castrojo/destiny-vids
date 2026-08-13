# Seven Days to the Wolves — the musical (editorial pass)

**Status:** editorial pass, delivered for review as **act VI** of the running
order — `~/Videos/Wolves/Prod/06-7daystothewolves.mp4`, hardlinked from
`~/Videos/wolves-musical/`. Delivered is not published: it is deliberately not
in `yt-refresh.py`'s manifest, because that means choosing a title and a
description, which is the owner's call. It is also **the one act with no
lossless master** (#58).
**Runtime:** 443.5 s (7:23.5) for a 424.0 s song. The 19.47 s difference is the
interruption ([issue #104](https://github.com/castrojo/destiny-vids/issues/104)) —
the bed is paused across all of it, so it costs the song nothing.
**Rendered:** `renders/07-wolves-timing-pass.mp4` — 1920x1080 H.264, 30 fps,
AAC 48 kHz, −2.8 dBTP, −10.1 LUFS integrated (interruption build, 2026-08-13;
the previous delivered build measured −1.6 dBTP, −10.1 LUFS). Delivered
**alongside** v1 as `~/Videos/wolves-musical/wolves-7days-master-v2.mp4` and
`-plated-master-v2.mp4` — v1 and the `Prod/` link are untouched; promoting v2
and reassembling the programme (v0.8) is a deliberate follow-up, coordinated
with the act II rebuild.

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
| 16 | 5:22.2 – 5:41.7 | *paused* | cards + `gameplay` 0:43.0 – 0:53.5 | **the interruption** (#104): the song stops, the Ambassadors interrupt, the clip is presented |
| 17 | 5:41.7 – 5:57.7 | 322.2 – 338.2 | `act2` 2:51 – 3:07 | the Pale Heart, Guardians gathering |
| 18 | 5:57.7 – 6:11.6 | 338.2 – 352.1 | `gameplay` 1:17.6 – 1:35.2 | three action runs, where the Ghost sequence was |
| 19 | 6:11.6 – 6:20.7 | 352.1 – 361.2 | `act2` 3:21 – 3:30 | back on the plains |
| 20 | 6:20.7 – 7:11.2 | 361.2 – 411.7 | `act4` 0:00 – 0:50.5 | the finale, the Guardians assembled |
| 21 | 7:11.2 – 7:23.5 | 411.7 – 424.0 | artwork | the outro, over the fade |

**The song plays from the first frame**, under the title card — the record's own
opening is quiet pickups, which is what a title card wants. The only source
audio in the film is the interruption's 10.47 s clip, which plays its own
effects and score by design (#104).

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

### The interruption: the song is paused and the clip is *presented*

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

against a background of under 30.

**Then issue #104 reframed the whole beat.** #95 wanted the clip's audio
SFX-only, and that search closed as *blocked* (below). The owner's solution
dissolves the problem rather than solving it: **stop hiding that it is a clip
— frame it as a presentation.** The song is paused, the CNCF Ambassadors
interrupt the film, and the clip is *played to the audience* with its own
effects and score. The with-music mix stops being a defect and becomes the
point; the polite hold music is smashed out by the explosion, and that is the
joke.

> *"Since this is an interruption we have unlimited time."* True mechanically
> as well as dramatically: the bed does not advance across the pause
> (`t.at_bed(PAUSE_AT, ...)` in `scripts/build_wolves.py`), so every second of
> the sequence is free — it costs the song nothing.

The sequence, built from `stories/06-wolves-interruption-cards.json` and the
constants in `scripts/build_wolves.py` — **every timecode names its clock**:
`322.200` is BED time, the clip's in/out are SOURCE time, the durations are
ACT-FILM time:

| # | Dur (film) | What | Audio |
|---|---|---|---|
| A | 1.0 s | the song stops; a held beat of black before anything appears | `silent` |
| B | 4.0 s | *"The CNCF Ambassadors would like a moment."* (owner-authored, verbatim; **text only** — the CNCF mark is rights-blocked) | `hold` slot |
| C | 4.0 s | *"Introducing ..."* → **Cortney Nickerson's nameplate**, her authored act-I identity verbatim — `AMBASSADOR // GUARDIAN` / *Weilder of the Arcane*, class row omitted exactly as there (#90) | `hold` slot |
| D | 10.470 s | the clip: **source 43.000 → 53.470**, its own effects and score | `source` |
| E | — | unpause; the song resumes at bed 322.200 | the song |

19.47 s of screen time, all free. The **hold-music slot ships silent**: no
cleared elevator-music asset exists on this machine, and picking a track is a
licensing decision — one of the two things that genuinely stop work, because
it cannot be un-done after publishing. The slot is recorded in the shotlist's
`unresolved` with a `TODO(owner)`, and `tools/audiomix.py` already knows the
`hold` kind: when the owner clears a track, both shots get an `audio_from`
and nothing else changes. Silence in that slot is a punch-list item; an
unlicensed track is not recoverable by a revert.

The lengths are the issue's craft guidance, not measurement: an ordinary
pre-punchline beat is 0.5–1 s, hold music wants 3–4 s, and past 5–6 s a
static element with no new development is dead air — so no static element
holds past 4.0 s and each is a new development (mark → name → explosion).

**The in-point is the owner's own correction, verified on frames.** Issue #104
as written said 43.0 → 51.0, but the owner's follow-up comment on the issue
retracts it: 51.0 is mid-combat, 53.470 *is* the cut, and the literal range
would drop the transcendence portrait they had previously insisted on. The
comment names **43.000 → 53.470** as "very likely what was meant" (option B;
the as-shipped 44.811 → 53.470 is option A). Option B is what is built here,
after extracting frames across the window in this worktree
(`renders/verify-104/`): combat with supers from 43.0, the white bloom at
52.0, the portrait at 53.0, and the *next* shot — Guardians running — at 53.6.
If the owner prefers A, it is a one-line change (`CLIP_IN = 44.811`) and a
rebuild.

The clip is `audio: "source"`, so it **costs no bed time**, and neither do the
silent and hold beats — extending the pause from 8.659 s to 19.470 s only
makes the film longer; no anchor moved.

What follows is the history that closed #95, kept because the measurements
stand. On *"recreate it with the sfx pristine version you have, no music"* —
**the delivered insert never did that, and an earlier paragraph here claimed
it did.** That claim argued from a spectral-flatness measurement (0.45 run-up,
0.47 across the explosion) that the trailer's own audio was "broadband, not
tonal". It stays deleted: a flatness average across a loud explosion can mask a
bed, and a measurement is not a licence to ignore the source the owner handed
over. Measured properly ([issue
#95](https://github.com/castrojo/destiny-vids/issues/95)), the trailer's audio
on this span **is** the with-music mix — correlation **0.875** against the
owner's own *"here it is with music"* clip at matching loudness.

**The fix was a source, not a process** — nothing is separated, ducked or
enhanced; the audio tenet in
[`docs/skills/references/audio-standard.md`](../skills/references/audio-standard.md)
rules that out, so the SFX-only audio had to come from another upload of the
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
gameplay. That is what closed #95 as blocked (PR #132), and what #104 then
reframed: no SFX-only mix exists, so the clip stops apologising for its score
and is *presented* with it. The `audio_from` mechanism in
`tools/audiomix.py` survives — it is how the hold-music slot will play once
the owner clears a track.

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
play **under the bed**: the interruption's clip is the film's one section with
its own audio.

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
What is specific to this cut: the song plays from the first frame, and the
only shots that cost no bed time are the interruption's — the only
`audio: "source"` shot is the clip, and beats A–C are `silent` / `hold`. The
film is therefore **443.5 s for 424.0 s of music**. Every anchor in the
builder is asserted against bed time.

### The pause's length, measured

The rule — [a diegetic insert has to be allowed to
end](../skills/scoring/references/two-clocks-and-levels.md#a-diegetic-insert-has-to-be-allowed-to-end) — came out
of this cut. The pause was first taken at 1.8 s and the moment *started and did
not finish*; the timing pass took it to 3.65 s; the editorial pass took it to
the shot the owner actually meant, 8.659 s, with the out-point on a measured
cut rather than on an audio envelope. The interruption (#104) takes the beat
to 19.470 s of film: the same shot, now 43.000 → 53.470 on the source clock,
*plus* the three presentation beats in front of it — all of it free to the
bed.

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

**The clip needs the same treatment, for its own reason.** An insert is
somebody else's mix and it brings peaks nobody here planned for, over a region
far too short to move the film's integrated loudness. Measured (on the
8.659 s pause; the interruption's clip is the same material, 1.8 s longer):

| Region | True peak |
|---|---|
| whole file, before | **−0.4 dBTP** — over the −1.0 gate |
| a bed region | −3.2 dBTP — fine, and unchanged |
| the pause region | **−0.4 dBTP** — the culprit |

So the clip gets a static **−1.5 dB** of its own
(`tools/audiomix.py --source-gain-db`, added in this pass as the mirror of
`--bed-gain-db`). Pulling the whole film down would have worked too and is
worse: it would quietly re-level music whose gain was already decided and
documented above. The silent and hold beats carry no audio at all, so they
cannot peak.

Delivered (previous build): **−1.6 dBTP**, −10.1 LUFS integrated, LRA 4.0. The
interruption rebuild's own numbers are in the verification table below.

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

The interruption (#104) adds the **inverse** fault, and the gate covers it too
(`scripts/rebuild-wolves.sh` measures both directions from the shotlist's own
wall clock): a `silent` beat — or the `hold` slot while no track is cleared —
that is *audible* means the bed is leaking into the pause.

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

**Shifted +10.811 s for the interruption build (#104).** Every window is after
the pause, and the pause grew by exactly 10.811 s of film (bed untouched), so
the same frames now play at 393.511 / 397.111 / 401.819 / 405.819 / 407.819.
The manifest records the shift in `_shifted`; the marks and the verified
frames above are unchanged.

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
    --fit-video renders/07-wolves-timing-pass.mp4
python3 tools/plate.py burn --video renders/07-wolves-timing-pass.mp4 \
    --manifest stories/06-wolves-cayde-plates.json \
    --plates-dir renders/plates-act6 \
    --out renders/07-wolves-plated.mp4 --fit-picture
```

(the v1 burn fitted against `~/Videos/Wolves/Prod/06-7daystothewolves.mp4`;
the #104 build fits against the fresh render, and the result is *then*
delivered alongside — never burned over a delivered file in place.)

`Prod/` holds **one file per act**, hardlinked to its project master. The
interruption build (2026-08-13, #104) is delivered **alongside** the v1
masters as `~/Videos/wolves-musical/wolves-7days-master-v2.mp4` and
`wolves-7days-plated-master-v2.mp4`; `Prod/06` still links to v1. Promoting is
one deliberate step — `ln -f wolves-7days-plated-master-v2.mp4
~/Videos/Wolves/Prod/06-7daystothewolves.mp4` — and because the act is now
443.5 s, **the programme (v0.7) then needs reassembly**: every chapter after
act VI moves +10.811 s. That reassembly is *not* done in this change, so it
cannot race the act II rebuild happening in parallel; it is the recorded
follow-up. **The un-plated master is kept beside the plated one**, because
burning is not idempotent: a re-burn starts from the clean act and never
stacks a second card on the first. Audio is stream-copied at the burn, so the
burn itself moves nothing.

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

# 2b. the interruption slides (copy: stories/06-wolves-interruption-cards.json)
python3 scripts/build_interruption_cards.py

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

Measured on the **interruption build** (2026-08-13; film clock, 443.533 s
container):

| Claim | Evidence |
|---|---|
| Not truncated | full `-xerror` decode passes; 13 301 frames, 443.533 s |
| The song is where it should be | cross-correlation against the bed: lag **0.00 ms**, r = 0.9998–0.9999 at film 100/250/300 |
| The song resumes where it stopped | film 350/400/440 = bed 330.530/380.530/420.530 (film − 19.470): lag **0.00 ms**, r = 0.9998–0.9999 |
| The interruption is a genuine pause | correlation against the bed **−0.02** across the region |
| The clip is not silent | region RMS **−18.8 dB** (film 331.2–341.67) — the trailer's own audio, effects and score, **by design** ([#104](https://github.com/castrojo/destiny-vids/issues/104)) |
| The held beats ARE silent | beat A RMS **−89.3 dB**; beats B and C RMS **−240 dB** (digital silence) — the hold-music slot ships empty, recorded in `unresolved` |
| Headroom | **−2.8 dBTP**, −10.1 LUFS integrated |
| The frames are the design | extracted and eyeballed: 322.6 black; 325.2 the Ambassadors slide; 329.2 "Introducing ..." + Cortney's plate; 340.2 the white bloom; 341.2 the transcendence portrait; 342.5 the Pale Heart resumed |
| The reveal still lands | plates re-burned at +10.811 s; the Cayde frame at film 394.5 carries the reveal card |
| Anchors hold | every `at_bed()` assertion in the builder, plus `tests/test_wolves_timing_pass.py` |
| No slide, no placeholder | asserted on timecode and on beat text, not on the absence of a card |
| No two summit slots repeat | peak pairwise correlation **0.27**, limit 0.35 |
| Joins | a frame extracted at every new cut and inside every summit slot |

The previous build's measurements (432.733 s, 12 977 frames, resume lag
1.00 ms, pause RMS −18.5 dB, −1.6 dBTP) stood on the 8.659 s pause and are
superseded by the table above.

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
- [ ] **Owner: Cortney Nickerson's class** — [issue #59] / [#90]. She is
      **plated now**: interruption card C introduces her with the identity the
      owner authored for act I (#90), verbatim — `AMBASSADOR // GUARDIAN` /
      *Weilder of the Arcane*. The class row stays **omitted**, exactly as in
      act I: her class was never named and a hint is not an authorisation.
- [ ] **Owner: the hold music** — [#104]. Interruption beats B and C carry the
      `hold` audio slot, which ships **silent**: no cleared elevator-music
      asset exists on this machine and picking a track is a licensing
      decision. Recorded in the shotlist's `unresolved` with a `TODO(owner)`;
      when a track is cleared, both shots get an `audio_from` and the mix
      wiring already knows what to do with it.
- [ ] **Owner: the CNCF mark on the interruption slide** — [#104]. The slide
      is the owner-authored line as text only; using the logo is a rights
      decision, not made.
- [ ] **Owner: a wreath for the interruption plate?** — [#104]. Card C
      reproduces the act-I treatment exactly, which has none.
- [ ] **Owner: confirm the clip's in-point** — [#104]. Built as option B of
      the owner's own correction (source 43.000 → 53.470); the issue text's
      43.0 → 51.0 would drop the portrait. One-line revert to option A:
      `CLIP_IN = 44.811` in `scripts/build_wolves.py`.
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
