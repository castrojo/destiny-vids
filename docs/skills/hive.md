---
name: hive
version: "1.0"
last_updated: "2026-08-29"
id: hive
one_line_purpose: Build the Season of the Blueberries episodes and the full-season cut.
entry_point: docs/skills/hive.md
category: media-production
status: active
dependencies: []
tags:
  - hive
  - season-of-the-blueberries
  - episodes
  - farm
  - delivery
description: >-
  Build one weekly Hive episode or the whole Season of the Blueberries from
  the committed season manifest: farm-first encodes, one source download, a
  stream-copy season cut.
metadata:
  type: procedure
---

# Season of the Blueberries builds

## When to Use

- Building or rebuilding a Hive episode (`s01eNN-*.mp4`)
- Building the full-season cut (`season-01-full.mp4`)
- Regenerating the committed cards after an owner copy change

The committed record is
[`stories/standalone/season-of-the-blueberries.json`](../../stories/standalone/season-of-the-blueberries.json);
[`tools/hive_series.py`](../../tools/hive_series.py) is the whole build. The
cards, seats, overlays and copy rules are the manifest's, not this file's —
this skill is only the operating procedure.

## The interface

```bash
just hive-episode 3     # build and verify one episode
just hive-cut           # build and verify all 12, then season-01-full.mp4
just hive-cards         # regenerate the committed CTA and title slides
```

The recipes are one line over the CLI; everything else is
`python3 tools/hive_series.py <check|cards|build|build-all|cut|verify>`.
Hive commands are remote-only: no `--local` escape hatch exists. The supplied
immutable source at `~/Videos/Hive/source-<youtube-id>.mp4` is required; if it
is absent, stage it through a remote job rather than downloading or muxing it
on the workstation.

## What a build does

1. Fetches the manifest-pinned source (formats 137+251) **once** into
   `media/hive/` and reuses it for every episode.
2. Renders what the episode needs: dossier cards for the chapter's
   contributor snapshots (0–3, full-frame, before the chapter), the fixed
   cast's plates through `tools/plate.py`, the project-lore overlays here.
3. Encodes ONE pass through `tools.farm.run_encode`: opening CTA (10s,
   silent), title slide (5s, silent), dossiers (4s each, silent), the
   chapter with its own audio, closing training CTA (10s, silent).
4. Writes the episode, its title-slide JPEG thumbnail, and the
   `renders/hive/*-unresolved.json` sidecar — the punch list, never a gate.

`build` and `build-all` write only `~/Videos/Hive/Season-of-the-Blueberries/rough/`;
`cut` joins those rough episodes into `season-01-full-rough.mp4`. An explicit
promotion step copies a locally approved rough and paired thumbnail to the
top-level release paths. Builds and joins verify their streams on the farm;
they never use local ffmpeg or ffprobe.

## Seats and times

Authored `source_at` marks never move. The build converts them to
chapter-relative content time and lets the front cards offset them through
the concat. An unsupported plate, an unknown overlay position, a missing
face, or a display name that cannot fit the dossier panel all degrade to
recorded omissions — the episode ships regardless.

## Weekly contributor recognition

Recognition is public GitHub commit activity across the configured
repositories (`contributor_ledger.repositories` in the season manifest),
counted per durable numeric account ID between the last snapshot's
`captured_at` and now — not Hive calendar metrics, and not calendar-week
precise. Bots, non-User accounts, the fixed cast, and every ID already in
the ledger are excluded; up to three are selected by commit count
descending, normalized login ascending, ID ascending.

```bash
python3 tools/hive_series.py contributors          # this window's evidence, read-only
python3 tools/hive_series.py select-next           # issue the next episode's dossiers
python3 tools/hive_series.py status                # issued/delivered per episode
```

`select-next` fills the next chapter that has no `dossiers` key (a filled
chapter is never rewritten), appends the full candidate-evidence snapshot,
and extends the ledger — validated first, written atomically, and abandoned
untouched if any configured repository cannot be read. A week with no
eligible contributor still issues the episode with an empty dossier list
and a `dossier_note`: the release never waits for a card.

`.github/workflows/hive-weekly.yml` runs the selector every Saturday at
17:23 UTC plus on dispatch, and opens a PR only when the record changed.
That PR is opened with GITHUB_TOKEN so it does not trigger CI; it requires
the normal human/merge-queue gate — merging it is the approval for putting
a real person on screen. Merging to main also refreshes the selected
contributors' GitHub PFPs through the existing `avatars.yml` cache (the
season manifest is on its path list; no PAT). The workflow never renders
footage.
