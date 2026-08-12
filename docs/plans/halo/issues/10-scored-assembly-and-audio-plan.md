# H-10 — Scored assembly: fill a combat movement to one track, and lay per-movement audio

**What:** two gaps between what the render path does and what a scored episode
needs.

**Gap 1 — one audio bed for the whole file.** `render.py --audio` maps a single
external track over the concatenated video with `-shortest`
(`tools/render.py:158–181`), and source audio is dropped entirely when a bed is
given (`keep_audio=not args.mute and not args.audio`, line 253). The brief needs
source audio on the dialogue movements — that *is* the radio chatter — and a
track on the combat movements.

**Gap 2 — one shot per beat.** `story.py` casts each beat to exactly one shot, so
an episode runs however long its shots add up to. A combat movement has to fill
its track.

**Gap 3 — "dialogue, no music" is a property of the source.** Keeping source
audio does not guarantee chatter without score. Published footage often has music
baked in, and the tagger sees keyframes, not audio (`tools/annotate.py:165–181`),
so nothing in the index knows whether a shot's audio is speech, score or both.

**Scope:**
- Per-movement audio. Recommended: render each movement through the existing
  path with its own bed, then concat the movements — the filter graph stays
  small and a single movement can be re-rendered without redoing the episode. A
  single `filter_complex` across an episode is the alternative and is much
  harder to debug when it goes wrong.
- Make the movements joinable, which the current path does not do for free:
  - `cut_clip` normalizes audio to AAC 48 kHz stereo only when `keep_audio` is
    true and emits `-an` otherwise (`tools/render.py:150–154`); `concat()`
    re-encodes an external bed without forcing its rate or channels. Force AAC
    48 kHz stereo on **every** movement output.
  - Insert `anullsrc` silence where a source clip has no audio stream, so a muted
    dialogue clip does not produce a movement with no audio track at all.
  - The concat demuxer cannot crossfade. Either accept hard cuts at movement
    boundaries or add a filter-graph pass over the joined audio for
    `acrossfade` — decide and write it down; do not assume the existing path
    gives crossfades.
- Dialogue movements keep source audio; combat movements take the track. If the
  owner wants source audio under the music, that is ducking and it is a separate,
  explicit choice — not a default.
- Establish that a dialogue movement's source *is* dialogue: either add an audio
  axis at annotation time (speech present / music present) or take owner-supplied
  dialogue stems. Without one of the two, "dialogue-only, no music" is unverified
  and the first music-bearing clip breaks the alternation the brief is built on.
- Fill-to-duration for combat movements: keep casting from the movement's beat
  pattern until the track's duration is met, honouring no-reuse across the
  campaign, and **report the shortfall** when the clean pool runs dry. A movement
  that cannot be filled is a beat to rewrite; it is not a reason to reach for
  `--include-unclean`. Two mechanics this needs that `build_story()` lacks: it is
  duration-blind (it takes the beat's duration or the entire source span, and
  caps nothing), so the fill loop must budget the *capped* duration of each pick
  and trim only the final one.
- Do a corpus capacity check before committing: twelve full-track combat
  movements under campaign-wide uniqueness is a large ask of a clean pool, and
  the honest failure is "the corpus is too small", found early.
- Footage tier is an upfront editorial choice. Clean gameplay is valid coverage
  under the repo contract (`story.build_story(allow_gameplay=…)`); if the
  campaign wants it, the template says so from the start. What is forbidden is
  flipping it mid-render because a movement came up short.
- Keep re-encoding every clip. `docs/rendering.md` measured this: input seeking
  rebases output timestamps to zero, which shifts the phase of the 29.97 → 30
  fps conversion and changes which source frames get duplicated — the
  keyframe-snapping justification is the stale claim `AGENTS.md` calls out.
  Re-encoding is also what normalizes every clip to identical stream
  parameters, which the movement-concat above depends on.

**Acceptance:**
- [ ] An episode renders with source audio on dialogue movements and one
      continuous track on each combat movement.
- [ ] Every movement output has identical video and audio stream parameters, and
      concatenating them produces no audio dropout at a boundary.
- [ ] A combat movement's video duration matches its track within a stated
      tolerance, or the shortfall is reported.
- [ ] No shot repeats to pad a movement.
- [ ] `tests/test_render.py`-style tests cover the audio plan without invoking
      ffmpeg.

**Depends on:** H-02 (tracks and durations), H-09 (movements exist)

**Automatable:** yes.
