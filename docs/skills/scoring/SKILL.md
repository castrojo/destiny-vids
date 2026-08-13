---
name: scoring
version: "2.0"
last_updated: "2026-08-13"
id: scoring
one_line_purpose: Measure a music bed, cut sections out of it, and cut to its bars.
entry_point: docs/skills/scoring/SKILL.md
category: editing
mcp_compliance_level: partial
optimization_status: draft
status: active
dependencies: [editing]
tags: [music, bed, rights, attribution, insert-track, tempo, downbeat, excision, anchor, ffmpeg, true-peak, section-detection, two-clocks, bed-pause, diegetic-insert, insert-headroom, source-gain]
description: >-
  Covers bed records and their rights buckets, bar-snapped excisions, the cached grid, named anchors, a bed that pauses mid-cut, and a second track over that pause.
  Use when scoring a cut, pausing the song, or clearing and crediting a track.
metadata:
  type: procedure
  context7-sources:
    - /librosa/librosa
    - /websites/ffmpeg_documentation
---

# Scoring a cut to a bed

## When to Use

- Replacing a cut's audio with a chosen track
- Cutting a section out of that track
- Landing a specific shot at a specific moment in the music
- Finding where a section (a gallop, a solo, a break) actually starts
- Supporting more than one recording of the same song
- A delivered file whose true peak is above 0 dBTP
- The song must pause, duck, or start late over picture already running

## When NOT to Use

- Sourcing the best copy of a track, or any mixing/mastering question →
  the `audio-quality-tenet` and `scoring-cuts-with-replacement-music` skills
- Assembling the picture, marking material for removal → [`editing.md`](../editing/SKILL.md)

## Core Process

1. **Measure** the bed. Never take a duration from a search result.
2. **Check the metrical level** before trusting the tempo.
3. **Excise** any unwanted section — it snaps to bar lines.
4. **Map** the anchor timecode between the source and edited timelines.
5. **Render** the edited bed, lossless.

```bash
python3 tools/bed.py measure media/<bed>.wav --id <bed_id> \
    --beat-multiple 2 --source-url <url> --title <t> --artist <a>
python3 tools/bed.py excise music/<bed_id>.json --from 2:59 --to 3:12
python3 tools/bed.py render music/<bed_id>.json --out renders/bed-edited.wav
python3 tools/bed.py map music/<bed_id>.json --at 3:48 --edited
```

## The bed record

A bed gets a record in `music/<bed_id>.json`, which is to a track what
`videos/<video_id>.json` is to a source video: provenance plus measurements,
**never the media**. Same rights posture — `usage_class` and
`source_rights_note` on every record, validated against
[`schema/bed.schema.json`](../../../schema/bed.schema.json) and
`vocab/provenance.yaml`.

`usage_class` says which bucket the track is in, and **both buckets are
usable**:

| Value | What it means |
|---|---|
| `third_party_copyrighted` | Somebody else's recording, used as a non-commercial fan-work bed. |
| `cc_by_4_0` | **Cleared.** Commercial use, sync and redistribution permitted; attribution is the only condition, and `--attribution` is then required — the credit is reproduced verbatim in [`ATTRIBUTIONS.md`](../../../ATTRIBUTIONS.md), which the suite checks. |

```bash
python3 tools/bed.py measure media/<bed>.wav --id <bed_id> \
    --usage-class cc_by_4_0 --attribution "$(cat credit.txt)" ...
```

## A second track, while the song is paused

`audio: "insert"` plays a different track over a span — hold music under a
title card, say. It advances **wall and not bed**, exactly like `audio:
"source"`, so an interruption costs the song nothing and no anchor after it
moves. The shot names its own `insert_bed`, and optionally `insert_start` and
`insert_gain_db`. See `tools/audiomix.py` and act VI's Ambassadors beat in
`scripts/build_wolves.py`.

## Where the detail lives

This skill is the contract. The procedure lives in `references/`:

| Reference | What is in it |
|---|---|
| [`measuring-the-bed.md`](references/measuring-the-bed.md) | The cached grid, checking the metrical level, the librosa tempo-array gotcha, measuring section boundaries instead of trusting a tracklist, and recording what you measured about the source. |
| [`excisions-and-anchors.md`](references/excisions-and-anchors.md) | Named anchors over literal timecodes, bar-snapped excisions, mapping between the source and edited timelines, and keeping the chain lossless. |
| [`two-clocks-and-levels.md`](references/two-clocks-and-levels.md) | A bed that pauses or enters late (`tools/audiomix.py`), the diegetic insert's out-point, its peaks and audibility checks, and the static-gain fix for a master over 0 dBTP. |

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "The tempo detector said 161, so it's 161." | It locked onto double time. Check `--beat-multiple 2` before anything is cut to it. |
| "I'll just cut the 13 seconds the owner asked for." | Mid-bar, that stumbles *and* re-phases the grid. Snap to bars; 12.098s is what four bars actually measure. |
| "I'll re-run the analysis at render time, it's the same audio." | Beat tracking is a heuristic. A different answer silently moves every cut. |
| "3:48 is 3:48." | Not once a section is gone. Edited 3:48 is source 4:00.098 here. |
| "The tracklist says the bridge is at 4:20." | A tracklist is not a measurement. Read the centroid, the flatness and the percussive RMS, and confirm the boundary in two of them. |
| "The instrumental is the album take with the vocals muted." | It is a different arrangement with a different length. Anchor by name and map each recording separately. |
| "True peak is over, I'll run loudnorm." | That rewrites the artist's dynamics. A static gain at the mux fixes the peak and changes nothing else. |
| "I measured the peak on the bed, so the delivery is fine." | Measure the delivered file. The encode adds intersample peaks the WAV did not have. |
| "The track needs a licence decision, so the cut is blocked." | Only if it is **uncleared**. Choosing between tracks that are already CC BY is taste, not rights — pick one, record the obligation, ship. See `AGENTS.md`, "A rights *decision* blocks. A rights *choice* does not." |
| "It's CC BY and the credits act doesn't exist yet, so I can't use it." | Attribution has to land *somewhere*, not somewhere specific. `ATTRIBUTIONS.md` satisfies it today; the on-screen home is #51's job. |
| "CC licensed means I can use it freely." | Not CC0. The condition is the licence — a record claiming `cc_by_4_0` without its verbatim credit claims a permission it does not have, and the suite fails it. |

## Red Flags

- An anchor asserted against wall time in a cut whose bed pauses. Bed time is
  the only clock the music knows.
- A source-audio insert cut to a round number rather than to its own phrase.
- Ducking a dense master under dialogue or an action hit instead of pausing it.
- A tempo exactly double the one you can tap
- An excision whose `removed_bars` is not a whole number
- A rendered bed whose bit depth or sample rate differs from the source
- Anchoring to a literal timecode on a bar-aligned cut
- Re-analysing a bed that already has a cached grid
- A bed record with no measured spectral cutoff
- A section boundary taken from a tracklist rather than measured
- `loudnorm`, a compressor or a limiter anywhere near a finished master

## Verification

```bash
python3 -m pytest -q tests/test_bed.py

# duration is source minus every excision
ffprobe -v error -show_entries format=duration -of csv=p=0 renders/bed-edited.wav

# no truncation or corruption, and nothing clipped
ffmpeg -v error -xerror -i renders/bed-edited.wav -f null -
ffmpeg -hide_banner -nostats -i renders/bed-edited.wav -af volumedetect -f null - 2>&1 |
  grep max_volume
```

Proving a bed is genuinely instrumental — measure the vocals stem, never trust
the title — is `scoring-cuts-with-replacement-music`. This bed measures
−32.2 dBFS on the vocals stem with 80% of that energy in 500 Hz–2 kHz and only
10.6% above 4 kHz, which is melodic leakage rather than a voice; the outro
window measures −56.1 dBFS.
