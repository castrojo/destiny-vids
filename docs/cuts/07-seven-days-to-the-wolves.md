# Seven Days to the Wolves — the musical (timing pass)

**Status:** timing pass, for review. **Not delivered** — see Rights.
**Runtime:** 427.6 s (7:08) for a 424.0 s song. The 3.65 s difference is the pause.
**Rendered:** `renders/07-wolves-timing-pass.mp4` — 1920x1080 H.264, 30 fps,
AAC 48 kHz, −1.2 dBTP, −10.0 LUFS integrated.

The project's first musical: one song, three acts. This is the flagship the
hero videos and the teaser are marketing toward.

## What this pass is

The first cut was 289 shots in 424 s, 25 of them replayed, a third of Act I
from Curse of Osiris, and the middle reshuffled out of source order. It was a
good first cut and the wrong method. This one inverts it.

> **Mark, don't cut.** Anything destined for removal or replacement stays in
> the timeline at its exact duration, blacked out by a marker card saying what
> will happen there.

Because a card and the footage it replaces are the same number of seconds,
**timing is preserved by construction**. Every anchor lands where it will land
in the finished cut, so this can be played against the music and reviewed
before a frame is actually removed. The convention is written up in
[`docs/skills/editing.md`](../skills/editing.md).

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
| Artwork | `~/Pictures/Artwork/wolves.jpg` | The *Seven Days to the Wolves* poster |

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
| 2 | 0:10 – 0:47 | 10 – 47 | `act1` 0:21.2 – 0:58.2 | **Act I**, the intro capture |
| 2b | 0:47 – 3:02.8 | 47 – 182.8 | `act1` 1:07.2 – 3:23 | ...continuing past the excised sun |
| 3 | 3:02.8 – 3:20.6 | 182.8 – 200.6 | Lightfall trailer | **Act II** opens: the gallop cuts to neon |
| 4 | 3:20.6 – 4:19.4 | 200.6 – 259.4 | `act2` 0:47.1 – 1:45.9 | Neomuna, unbroken into the crash |
| 5 | 4:19.4 – 4:33.5 | 259.4 – 273.5 | `act2` 1:45.9 | **Act III**, the crash, the strand descent |
| 6 | 4:33.5 – 4:37.0 | 273.5 – 277.0 | card | `COMIC PLACEHOLDER` over the enemy CU |
| 7 | 4:37.0 – 4:39.7 | 277.0 – 279.7 | artwork | held through the HOWL and the silence |
| 8 | 4:39.7 – 4:47.0 | 279.7 – 287.0 | `act2` 2:06.2 | the band slams back in, on three Guardians |
| 9 | 4:47.0 – 5:22.2 | 287.0 – 322.2 | `act3` 0:55 – 1:30.2 | the Collection Trailer montage, three cards marked |
| 10 | 5:22.2 – 5:25.9 | *paused* | `act3` 0:29.4 – 0:33.0 | **the song stops**; hero montage in its own audio |
| 11 | 5:25.9 – 6:04.9 | 322.2 – 361.2 | `act2` 2:51 – 3:30 | the Pale Heart, Guardians gathering |
| 12 | 6:04.9 – 6:55.4 | 361.2 – 411.7 | `act4` 0:00 – 0:50.5 | the finale, the Guardians assembled |
| 13 | 6:55.4 – 7:07.6 | 411.7 – 424.0 | artwork | the outro, over the fade |

**The song plays from the first frame**, under the title card — the record's own
opening is quiet pickups, which is what a title card wants. The only source
audio in the film is the 3.65 s pause.

## Everything below is measured

### The two act hinges

Unchanged from the first cut, and still the only frame-accurate obligations:
the **gallop at 182.834 s** (the spectral centroid collapses to 768 Hz) and the
**flute entry at 259.390 s**, both snapped to the bar grid (76 bpm, bar 3.158 s).

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

The capture is source 0:10 → 3:23, which is **193 s**, and the intro has only
182.834 s to spend once the song plays from frame one.

One span is dropped from inside it — **source 0:58 → 1:07**, a static distant
sun followed by several seconds of black, which stops the intro dead. The rest
of the difference comes off the **head**, because the capture's ending (the ship
rising, the fade) is the payoff into Act II.

**The in-point is therefore derived, not written down:**

```python
CAPTURE_IN = CAPTURE_OUT - (ACT2_IN - TITLE_CARD_LEN) - sum(excisions)
```

Cut another span out of the intro and the capture simply starts earlier — the
gallop does not move, and no anchor after it does either. Buying the sun back
restored the Mars → Earth orrery approach at the head, which builds where the
sun sat still.

### Two clocks

The mechanic and when to reach for it are in
[`docs/skills/scoring.md`](../skills/scoring.md#two-clocks-when-the-bed-does-not-run-end-to-end).
What is specific to this cut: the song plays from the first frame, the only
`audio: "source"` shot is the pause, and the film is therefore **427.6 s for
424.0 s of music**. Every anchor in the builder is asserted against bed time.

Verified by correlating the delivered audio against the bed:

| Film position | Bed position | Correlation | |
|---|---|---|---|
| 100 s | 100 s | **+1.000** | the song is exactly where it should be |
| 323 s | — | ~**0.000** | inside the pause, the song is genuinely absent |
| 350 s | 346.35 s | **+1.000** | it resumes from where it stopped |

### The pause's length, measured

The rule — [a diegetic insert has to be allowed to
end](../skills/scoring.md#a-diegetic-insert-has-to-be-allowed-to-end) — came out
of this cut. The pause was first taken at 1.8 s and the moment *started and did
not finish*. The in-point never moved; only the out-point was wrong. From the
trailer's envelope:

```
28.2  build begins        29.63  peak (-9.5 dB)
30.36 release             32.56  second swell
33.00 the phrase lands in its quietest point (-31.9 dB)   <- out
```

### Guardians together

The selection signal is **Guardians in frame together**, and four runs are
flagged `plate_slot` in the shotlist for the nameplate pass rather than being
re-found by eye later: Act II opens on three Guardians advancing abreast
(source 23:29), the slam after the silence lands on three running at camera,
the Pale Heart run has them gathering on the plains, and the finale is the
whole assembled crowd.

## Editorial rules, enforced in the builder

- **No Curse of Osiris**, anywhere — asserted.
- **No shot used twice** — asserted. The first cut replayed 25.
- **No Savathûn. The Witness: eyes or smoke, never its body.** Act II starts at
  the Neomuna boundary (source 23:47.1), after the Throne World and its branded
  cards; the Pale Heart run starts at source 25:51, after the pyramid and
  monolith material. Both are asserted, because both were breached by a run
  reaching backwards to fill time rather than by anyone choosing the footage.
- **A long enemy hold becomes a card, never a jump cut.**
- **Publisher mechanic cards become artwork slots.** Three fall inside the
  Collection Trailer montage — `7 RAIDS` (63.3–65.2), `ENDLESS BUILDCRAFTING`
  (71.0–73.0), `COUNTLESS LEGENDS` (87.4–89.4) — each blacked out at its exact
  duration. Recovered from frames in the first cut, not invented.
- **The film ends on the Guardians, not a logo.** The finale run stops at
  source 26:30 + 50.5, a beat before the branded `THE FINAL SHAPE` cards.

## Audio

The 2007 master is loud: −6.8 LUFS integrated, and decoded its true peak
measures +2.1 dBFS. The fix is a **static −3.5 dB gain** applied once, at the
final mux — not `loudnorm`, not a limiter: a static gain changes no dynamics at
all, and the LRA is the artist's, not ours.

Delivered: **−1.2 dBTP**, −10.0 LUFS integrated, LRA 4.1. The true peak is
tighter than the first cut's −2.7 dBTP because the source-audio regions bring
their own peaks; it is still under 0 dBTP, which is the gate.

## Rights

Bungie footage under Bungie's fan-content policy: non-commercial, metadata and
timecodes only, no footage committed. The bed is a Nuclear Blast recording used
as a non-commercial fan-work music bed.

**The compilation provenance question is now larger, not smaller.** Act I, Act
II and the finale all come from Antesion's re-upload. The fan-content policy
covers Bungie's footage; it does not make a third party's compilation ours to
use. A timing pass is an internal review artifact, so this pass proceeds —
**delivery does not**. Nothing here goes to `~/Videos/UPLOAD/` until that is
decided.

## Punch list

- [ ] **Owner: is the Antesion compilation acceptable provenance?** [issue #55].
      Blocking
      delivery. If not, Acts I and II and the finale need re-sourcing from
      official uploads. Escalated: three of five sections now depend on it.
- [ ] **Owner: Cortney Nickerson's Guardian identity** — [issue #59]. The hero shot at the
      pause (Collection Trailer 0:29.4) is cast to her by the owner, and she
      has no authored identity in `~/Videos/nameplates.json`, the website's
      `characters.json`, or `vocab/casting.yaml`. **The shot is rendered
      unplated**: a missing name is omitted and recorded, never invented
      (`AGENTS.md`). Author the identity where identities are authored and the
      plate follows.
- [ ] Nameplates are not burned yet. Four `plate_slot` runs are flagged in the
      shotlist for that pass; the credits sequence is still [issue #51].
- [ ] The four `COMIC PLACEHOLDER` slots need their artwork: one enemy CU
      (3.5 s) and three publisher cards (1.9–2.0 s each).
- [ ] The bed is an official YouTube upload — lossy, and not the highest-quality
      upstream version. The purchasable lossless *Dark Passion Play* master is.
      Swapping it will re-time the cut: codec rungs differ in leading padding
      (~36 ms measured previously here), so cross-correlate and prove lag 0.
- [ ] Instrumental (`SE_c6nqy-y0`) and orchestral toggles not built.
- [ ] **A burned-in ESRB `TEEN` badge** sits bottom-right over the first ~4.4 s
      of the Neomuna run (extract 47.1 – 51.5). It is publisher copy, so it is a
      `redactions/` job for the finished cut, not a re-cut.
- [ ] Neither compilation extract is in `segments/`. Tagging exists to feed
      `story.py`'s matcher and nothing here uses it — index them only if these
      sources are wanted in search.

[issue #51]: https://github.com/castrojo/destiny-vids/issues/51
[issue #59]: https://github.com/castrojo/destiny-vids/issues/59
[issue #55]: https://github.com/castrojo/destiny-vids/issues/55
