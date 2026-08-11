# H-07 — Ingest the Halo corpus: video records, rights notes, era/destination rules

**What:** build the Halo side of the index — video records, then the two-pass
detect/tag/assemble run that `docs/skills/indexing.md` already describes. The
pipeline needs no new plumbing: `tools/ingest.py` reads titles from YouTube's
oEmbed endpoint with no API key, and `tools/annotate.py` detects beats and
assembles schema-valid segments.

**What is Destiny-shaped and has to become per-universe:**
- `RIGHTS_NOTE` (`tools/ingest.py:31`) — see H-03.
- `ERA_RULES` and `DESTINATION_RULES` (`tools/ingest.py:39–58`) — keyword rules
  mapping a title to inherited defaults. Halo needs its own: mission names to
  `destination`, release names to `era`.

**Start by verifying the sources.** No video id is committed to in this plan:
candidate URLs could not be opened from the planning environment, and a video
record carries a canonical URL and a rights note. Confirm on the official HALO
channel by hand, and settle which release the footage is from — *Combat Evolved*,
the 2011 *Anniversary* remaster, or the "Halo: Campaign Evolved" project
referenced in [`../research.md`](../research.md#2-official-footage-sources). That
choice sets `era`, and `era` is the HUD-era tell (H-11).

**Scope:**
- Verify and record the source video ids (H-01 supplies the starting point).
- Per-universe inference rules and rights note.
- Two-pass index per video, tags reviewed against keyframes.
- `overlays` is tagged on **every** beat. An untagged `overlays` derives
  `clean = false`, so a partial tagging pass does not leave a small gap — it
  marks the whole video uncuttable. Halo footage is full of burned-in HUD, so
  expect a genuinely low clean yield and record it rather than working around it.

**Acceptance:**
- [ ] `videos/*.json` records exist and validate, carrying `universe: halo` and a
      Halo rights note.
- [ ] `segments/` holds beats for each ingested video, every one with `overlays`
      tagged.
- [ ] The clean-yield count per video is reported in the issue, so H-09's episode
      map can be judged against real coverage.
- [ ] No media file is committed.

**Depends on:** H-00, H-01, H-03, H-05

**Automatable:** partly — detection and assembly are scripted; the visual
judgement per keyframe is not, and neither is verifying an official upload.
