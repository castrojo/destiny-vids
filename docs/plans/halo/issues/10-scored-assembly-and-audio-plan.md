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

**Scope:**
- Per-movement audio. Recommended: render each movement through the existing
  path with its own bed, then concat the movements — the filter graph stays
  small, a single movement can be re-rendered without redoing the episode, and
  `acrossfade` at the boundary is where the music is meant to breathe. A single
  `filter_complex` across an episode is the alternative and is much harder to
  debug when it goes wrong.
- Dialogue movements keep source audio; combat movements take the track. If the
  owner wants source audio under the music, that is ducking and it is a separate,
  explicit choice — not a default.
- Fill-to-duration for combat movements: keep casting from the movement's beat
  pattern until the track's duration is met, honouring no-reuse across the
  campaign, and **report the shortfall** when the clean pool runs dry. A movement
  that cannot be filled is a beat to rewrite; it is not a reason to reach for
  `--allow-gameplay` or `--include-unclean`.
- Keep re-encoding every clip. A stream copy snaps the in-point to the nearest
  keyframe and throws away the boundary the detector pass exists to find
  (`docs/rendering.md`).

**Acceptance:**
- [ ] An episode renders with source audio on dialogue movements and one
      continuous track on each combat movement.
- [ ] A combat movement's video duration matches its track within a stated
      tolerance, or the shortfall is reported.
- [ ] No shot repeats to pad a movement.
- [ ] `tests/test_render.py`-style tests cover the audio plan without invoking
      ffmpeg.

**Depends on:** H-02 (tracks and durations), H-09 (movements exist)

**Automatable:** yes.
