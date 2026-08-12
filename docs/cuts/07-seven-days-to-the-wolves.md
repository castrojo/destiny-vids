# Seven Days to the Wolves — the musical (prototype)

**Status:** prototype. Built to be iterated on, not defended.
**Runtime:** 423.7 s (the song is 424.0 s).
**Delivered:** `~/Videos/UPLOAD/07-seven-days-to-the-wolves.mp4` — 297 MB,
1920x1080 H.264 High, yuv420p, 30 fps, AAC 48 kHz, −2.7 dBTP. Decodes clean
end to end.

The project's first musical: one song, three acts. This is the flagship the
hero videos and the teaser are marketing toward.

## Sources

| Role | Source | Notes |
|---|---|---|
| Bed | Nightwish, *7 Days to the Wolves* — [`LASru9j0oIc`](https://www.youtube.com/watch?v=LASru9j0oIc) | Album version (*Dark Passion Play*), official Nightwish channel. 424.0 s |
| Act II + III | *All Cinematic Trailers (Destiny)* — [`oRoHW97OZcs`](https://www.youtube.com/watch?v=oRoHW97OZcs) | **A fan compilation by Antesion**, 30:23. Not an official Bungie upload — see Rights |
| Act III | *Destiny 2: The Collection Trailer* — [`qI-fxJM8rSM`](https://www.youtube.com/watch?v=qI-fxJM8rSM) | Official Destiny 2 channel |
| Act I | The existing index | 351 clean segments across 7 indexed sources |
| Artwork | `~/Pictures/Artwork/wolves.jpg` | The *Seven Days to the Wolves* poster |

## The two anchors, measured not guessed

The bed's structure was measured rather than taken from a tracklist:

- **The gallop — 182.834 s.** The spectral centroid collapses from ~2500 Hz to
  **768 Hz** between 3:04 and 3:18, with spectral flatness at 0.0005: a
  palm-muted low riff and nothing else. Act II starts here.
- **The flute entry — 259.390 s.** The sharpest post-gallop break: percussion
  drops out at 4:18 and the 700–2500 Hz band takes the lead from 4:20 on.

Both snapped to the nearest downbeat of the cached grid (76 bpm, bar 3.158 s).

**The window crash lands on the flute entry.** Compilation source `24:45.4`
is shot 164 of the cut, at **259.385 s** — 5 ms from the anchor. It is the
first shot of Act III, so the beat change and the glass break together.

## Act structure

| Act | Span | Source | Feel |
|---|---|---|---|
| I | 0 → 182.8 s | the existing index | wide, quiet, building |
| II | 182.8 → 259.4 s | compilation from source 23:47 (Neomuna) | the gallop |
| III | 259.4 → 424.0 s | the crash, the strand descent, the Collection Trailer montage, the Pale Heart climax | frantic |

Each act fills its span **exactly**. The cut is a concatenation with no absolute
timeline, so an act that comes up short slides every later anchor — the builder
asserts on it rather than letting the crash drift off the beat.

## The mechanic cards

Every black card that explains a game mechanic is replaced by the artwork, in
every instance. Recovered from the frames, not invented:

| Card | Source span (trailer) |
|---|---|
| 5 EXPANSIONS | 18.1 – 19.9 s |
| 4 CONTENT PACKS | 37.6 – 39.6 s |
| 10 DUNGEONS | 53.1 – 55.0 s |
| 7 RAIDS | 63.3 – 65.2 s |
| ENDLESS BUILDCRAFTING | 71.0 – 73.0 s |
| COUNTLESS LEGENDS | 87.4 – 89.4 s |

A seventh artwork card closes the film over the song's fade to silence. The
bed fades from 6:48 and is effectively silent by 7:00; holding the poster there
beats truncating the fade, which is what a short picture would have done
(`concat` passes `-shortest`).

## Editorial rules, enforced in the builder

- **No Savathûn.** Filtered by caption and by character tag.
- **The Witness: eyes or smoke, never its body.** Now a standing rule in
  `vocab/casting.yaml` with an allow-list that defaults to empty, asserted by
  `tests/test_witness_depiction.py`. The trailer's Witness silhouette (shot 12)
  and the compilation's pyramid/body shots are out.
- **No major-enemy subjects.** A shot whose first clause names an Ogre,
  Minotaur, Tormentor, Calus, etc. is dropped — that is the "long drawn-out
  enemy shot" the direction cuts. Rejected by hand from the compilation:
  #24/#35 (Cabal, Tormentor), #48/#49 (Calus); from the trailer: #63/#64
  (boss ogres), #73/#82/#83 (enemy subjects).
- **Guardians outnumbered and looking amazing** is the selection signal: low
  camera angle (the vocab annotates it "heroic framing"), group/crowd
  composition, hero salience, and hostiles present in frame.
- Every cut lands on the beat grid. Act III holds are capped at 1.6 s.

## How it was built, and what was deliberately skipped

Neither new source is in `segments/`. **Tagging exists to feed `story.py`'s
matcher; these shots were picked by eye from contact sheets, so no tags were
needed.** Detection pass 1 alone gave 99 shots (compilation window) and 94
(trailer), each with a midpoint keyframe.

Four subsystems were considered and cut, each with an "add when":

| Skipped | Instead | Add when |
|---|---|---|
| `bed.py anchor` subcommand | two constants in the builder | a second bed variant ships |
| `cards/<video_id>.json` + schema | a six-row list in the builder | the card list outgrows one screen |
| `depiction` enforcement in `story.py`/`corpus.py` | the rule in vocab + a test; selection is by hand | a tool starts auto-selecting Witness shots |
| indexing either source into `segments/` | detection pass 1 only | these sources are wanted in search |

**The window extract is what made the render feasible.** `render.py` seeks with
`-ss` after `-i` for frame accuracy, so an Act II clip at source 24:00 would
decode 24 minutes first — ~40 s per clip at the ~35x realtime measured here,
times 83 compilation clips. Re-encoding the 23:00–26:30 window to its own file
first makes every seek land in a 3.5-minute file. Timecodes rebase by
**1380 s**; the builder records the source timecode in each shot's label.

## Audio

The 2007 master is loud: **−6.8 LUFS integrated, LRA 3.3**. Decoded, its true
peak measured **+2.1 dBFS** — intersample peaks above full scale.

The fix was a **static −3.5 dB gain**, applied once at the final mux. Not
`loudnorm`, not a limiter: a static gain is the one correction that changes no
dynamics at all, and the LRA is the artist's, not ours. Delivered true peak is
**−2.7 dBTP**, integrated −10.0 LUFS.

The audio is encoded exactly once, from the 24-bit WAV at the final mux
(AAC 320k, 48 kHz native — no resample). The gain pass stream-copies the video,
so the picture is encoded once too.

## Rights

Bungie footage under Bungie's fan-content policy: non-commercial, metadata and
timecodes only, no footage committed. The bed is a Nuclear Blast recording used
as a non-commercial fan-work music bed.

**The compilation is a third party's re-upload.** The fan-content policy covers
Bungie's footage; it does not make Antesion's compilation ours to use. That is
an owner decision, recorded here rather than assumed.

## Punch list

- [ ] **Owner: is the Antesion compilation acceptable provenance?** If not, Act
      II and the Pale Heart climax need re-sourcing from official uploads.
- [ ] The bed is an official YouTube upload — lossy, and **not** "the highest
      quality upstream version". The purchasable lossless *Dark Passion Play*
      master is the real answer. Swapping it will re-time the cut: codec rungs
      differ in leading padding (~36 ms measured previously in this project),
      so cross-correlate and prove lag 0 before shipping.
- [ ] Instrumental (`SE_c6nqy-y0`) and orchestral toggles not built.
- [ ] Act I is machine-ordered by a heroic score, not directed. It is the
      weakest act and the obvious first thing to re-cut by hand.
- [ ] No nameplates or credits; the credits sequence is still [issue #51].
- [ ] `docs/catalog.md` still describes the feature as four parts. If this cut
      replaces that structure, the Europa director's cut and the Nati teaser
      need somewhere to go.
