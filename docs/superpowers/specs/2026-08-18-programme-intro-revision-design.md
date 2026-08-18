# Programme intro revision design

## Goal

Apply the owner's programme-time review notes to the current *Seven Days to the Wolves* build. Rebuild each affected act from its authoritative source record, publish each changed act, then regenerate the programme and eligible social copies.

The review baseline is:

`~/Videos/Wolves/review/intro-notes-baseline.mp4`

All timestamps below use that programme clock. `tools/megacut.py --locate` translates them to the owning act and local clock before any source record changes.

## Boundaries

- Change upstream act records and builders. Do not patch `Prod/` files or the assembled programme.
- Preserve owner-supplied copy exactly. Split dialogue without rewriting words.
- Do not invent speakers, identities, title-card copy, footage, or art.
- Missing art degrades to polished text on black. Stale or falsely placed plates never ship.
- Preserve source audio and existing mix decisions. No normalization, EQ, compression, or unnecessary audio encode.
- Encode remotely when cluster is available.
- Remove Sarah Novotny and Brent Burns from Act II scheduling only. Keep their casting records.

## Approved sequence at 0:35

The current book slide near programme 0:35 moves later. Its existing authored object moves intact; its words and treatment do not change.

The vacated slot becomes this mission briefing, using existing Project Bluefin briefing chrome:

- Small blue eyebrow: `PROJECT BLUEFIN MISSION BRIEFING`
- Large white title: `Thanks for Volunteering`
- Status row: `Tophee Protocol Quick Insertion // ACTIVATED`
- Status row: `Agones Cluster // Cycling`
- Status row: `Mechaphippy Deployment // UNAUTHORIZED`

The moved book slide follows the new briefing, preserving its complete authored object. The existing TITANFALL warning follows the moved book slide. The next section carries a countdown at the bottom of the frame.

Countdown behavior:

- Whole-second display.
- Value derives from the remaining programme time; no hand-authored list of steps.
- `00:00` first appears exactly at programme 4:44 and persists through the transition.
- Start value derives from the final seated start frame after card timing is resolved.
- Frame calculations use the delivery rate, `60000/1001`.

## Programme-time revisions

### Prologue and Act I

- **0:35** — apply the approved briefing → moved book slide → TITANFALL → countdown sequence above.
- **3:27** — show `Your Potential is Off the Charts`.

### Act II — Endless Forms Most Beautiful

- Remove Sarah Novotny and Brent Burns from the opening schedule.
- **4:44** — preserve the existing card's authored copy, but make it a polished major title card matching the visual weight of the ending's `FIGHT FOR US` treatment. Keep black background until owner-supplied art exists.
- **5:31** — preserve this card's existing authored copy and apply the same major-title treatment and black-background degradation.
- Fix LFX choice screen so it never blinks.
- **6:28** — split the long sentence into two sequential chat messages. Preserve every word and use the sentence boundary from recovered copy.
- **6:46** — place `POOR TECHNICAL DECISIONS` above the monster in red, using kernel-regression boss treatment.
- **7:06** — move banner above content into top letterbox area.
- **7:50** — remove extra dollar line.
- **8:00**, **8:10**, **8:29** — split each into two chat messages at the capitalization boundary visible in authored copy. Preserve casing and words.
- **8:35** — restore main dialogue: `Empathy`, `tacos.` The recovered record determines speaker/text fields; no identity is inferred.
- **9:00** — start with HikariKnight, not akgraner. After current speakers finish, add:
  - `<akgraner> Sounds like you need some help`
  - `<akgraner> Let me take care of this for you`
  - play the evidenced action shot
  - pause again and return to the hallway paused scene
  - `<Owen> Slay out, Queen!`
  - `<akgraner> Which one of you is Kyle?`
  - continue existing akgraner dialogue unchanged
- **9:57** — show `HATERS` over the bad guy using the red boss treatment from the lion section.
- **9:59** — `<kylegospo> Sup`
- **10:10** — `<kolunmi> Disco!`
- **10:24** — `<redacted> Harbringer to the TOC`, then `<redacted> They're ready`
- **10:26** — `<akgraner> Disco!`

### Act III — Bob Killen

Recover the existing authored dialogue source and complete rebuild command before editing. Do not hand-edit its delivered master.

- **11:14** — `What a shitshow`
- **11:16** — split into two chat messages without rewriting.
- **11:22** — use mrbobbytables gold nameplate.
- **12:36** — `Everyone forgot how to use KVM! We need to split up`
- **12:41** — `Everyone's making their own and it's all bad!`
- Continue with existing sandbox material.
- **12:56** — split into multiple readable chat messages without rewriting.
- **13:09** — move sign to top-right and set:
  - Heading: `Maintainers Reading Emails`
  - Subtitle: `And Other Preposterous Tales`
  - Date: `Summer 2027`

### Interstitial and Act VI

- **16:22** — remove old Project Bluefin slide bleed-through.
- **21:37** — remove the entire section now represented by the Amber segment. Make the removal in Act VI's upstream builder so the show continues naturally; do not trim it in programme assembly.

### Act VII and ending

- **26:36** — change `Fight for Us` to `"We support the Community"`, preserving quotation marks.
- **26:55** — change heading to `Our Mission`, increase font size, use an existing dark wallpaper.
- **27:02** — main title: `We are Bluefin`.
- **27:06** — keep size, move text right and down to clear the bird, change copy to `We are not nice.`
- **27:11** — `We do what must be done.` with smaller `(Wait for it)` underneath.
- **28:51** — show `Prove it.` using the same title family.

Act VII currently has a source-digest mismatch. Inspect current rendered frames and copy before rebuilding. Digest mismatch alone does not prove stale pixels. Any plate whose screen content is stale must be re-rendered or omitted.

## LFX no-blink design

Current choice animation uses many short full-frame plates at 16 fps over a 59.94 fps delivery. Manifest continuity tests cannot prove the burned video keeps the menu visible.

Use one persistent choice-menu layer for the full hold. Animate only the cursor above it. Reuse existing choice chrome and pointer path; do not add a second menu renderer or dependency.

Test first with a rendered integration test:

1. Create a short synthetic 59.94 fps source.
2. Burn the choice sequence through the real plate burn path.
3. Decode every frame in the choice window.
4. Assert the static menu mask is present on every frame.
5. Assert pixels outside the bounded cursor region remain unchanged.
6. Assert first and last countdown/menu frames land at intended delivery frames.

Keep lightweight manifest tests for timing and authored options, but treat the burned-pixel test as the flicker regression gate.

## Data flow

For each timestamp:

1. Translate programme time to current act/local time.
2. Recover the complete existing authored object when copy or dialogue was lost.
3. Add or change the builder-owned source record.
4. Write a failing test for requested behavior.
5. Make the smallest builder/renderer change that passes.
6. Regenerate derived manifests with their existing generator.
7. Render cards from current templates before rebuilding the act.
8. Rebuild only the affected act remotely.
9. Inspect changed windows, decode the master, run audio/peak gates, then `deliver.py publish --act <act>`.
10. Reassemble the programme and regenerate eligible social copies.

## Acceptance checks

- Every requested line appears exactly once in intended order.
- No removed Sarah Novotny or Brent Burns plate remains in Act II.
- Countdown's first `00:00` frame is programme 4:44 at `60000/1001`.
- LFX menu remains visible on every output frame; only cursor region changes.
- Split messages preserve original words and capitalization.
- Boss bars, banners, and signs occupy requested frame/letterbox positions.
- Act VI removal loses no unrelated dialogue, credit, or music continuity.
- Act VII carries no stale or unsupported plate.
- New title cards reuse existing treatments; no duplicate rendering system.
- `python3 -m pytest -q`
- `python3 tools/corpus.py --check`
- `python3 tools/rederive.py --check`
- `python3 scripts/generate_schema_enums.py --check`
- Relevant generated-manifest `--check` commands pass.
- `python3 tools/deliver.py status --check` reports no stale deliverable rung.
- `python3 tools/megacut.py stories/megacut/megacut.json --dry-run` succeeds before encoding.
- Final programme decodes cleanly, matches planned duration, passes true-peak checks, and has current provenance/social outputs.
