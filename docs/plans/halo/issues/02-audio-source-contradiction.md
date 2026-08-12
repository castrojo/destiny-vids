# H-02 — Score: the Wolves catalogue and "use the Halo music" are mutually exclusive

**What:** #11 contains both instructions. The body says "Music tracks will be
supplied separately — reference the Wolves catalogue as the audio source rather
than generating original score." The audio line says "Use the Halo music and keep
it canon." Only one of them survives contact with the rights posture.

**Why the Halo OST loses on the repo's own terms:** Microsoft's Game Content
Usage Rules cover game content in fan videos; they do not grant rights to
soundtrack recordings used as standalone audio, which is exactly what a score bed
is. Halo OST audio is also Content ID-claimed on YouTube — including by third
parties with no rights to it. Detail and citations:
[`../research.md`](../research.md#5-halo-canon-audio).

The Wolves catalogue has neither problem, and is what the body of the brief asks
for. **Recommendation: score from Wolves; let "keep it canon" govern the fiction
and the HUD, not the soundtrack.**

**Also missing:** the repo has no catalogue file. Scored assembly (H-10) needs
per-track duration to know how long a combat movement has to run, and the
proposed episode map needs **twelve** tracks — six episodes, two combat movements
each.

**Scope:**
- Owner confirms the recommendation, or overrides it knowing the above.
- Owner supplies the catalogue as **metadata only** — `track_id`, title, artist,
  duration, rights/licence note, and where the audio lives outside the repo.
  Audio files get the same posture as footage: referenced, never committed
  (`.gitignore` already excludes `media/`).
- Confirm there are at least twelve usable tracks, or the episode map shrinks.

**Acceptance:**
- [ ] The decision is recorded in `docs/plans/halo/design.md` §10.
- [ ] A catalogue file exists with one entry per track, durations included.
- [ ] No audio file is committed.

**Depends on:** —

**Automatable:** no — a rights decision plus owner-held data.
