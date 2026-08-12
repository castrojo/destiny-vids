---
name: plates
version: "1.1"
last_updated: "2026-08-12"
id: plates
one_line_purpose: Put Guardian nameplates and title cards on a rendered cut.
entry_point: docs/skills/plates.md
category: editing
mcp_compliance_level: partial
optimization_status: draft
status: active
dependencies: [casting, editing]
tags: [nameplates, overlay, credits, bluefin, ffmpeg]
description: >-
  Plans, renders, and burns Project Bluefin Guardian nameplates onto a cut.
  Use when crediting cast or contributors on screen, or changing plate copy,
  timing, or chrome.
metadata:
  type: procedure
  context7-sources:
    - /websites/ffmpeg_documentation
---

# Guardian nameplates

## When to Use

- Crediting a lead or the monthly ensemble on screen
- Changing plate copy, position, or timing
- Porting the Bluefin plate treatment somewhere new

## When NOT to Use

- Narration captions → the `authoring-video-closed-captions` skill
- Deciding *who* is cast → [`casting.md`](casting.md)

## The field set is closed

A Guardian nameplate carries **exactly**:

| Field | Example |
|---|---|
| `label` | `TRUSTEE // GUARDIAN` |
| `class` | `Dawnblade Warlock` |
| `name` | `Bob Killen` |
| `title` | `Reconciler of the Plane` |
| `trustee` | `true` — the burnished-silver chrome |

The title card is the deck's only other shape: `title`, `subtitle`, `body[]`.

That is the whole vocabulary, taken from the reference deck
(`~/Videos/nameplates.json`). **Do not add a line the deck has no field for.**
An invented row — an `AS <CHARACTER>` casting line, a role, a pronoun — puts
unauthored text on a card whose entire purpose is naming real people, and a
test pins the vocabulary so it cannot drift by accident. If a plate genuinely
needs to say something new, add the field to the data model deliberately.

Local additions to the deck's shape are limited to chrome flags: `kind: ghost`
(drops the class line, because a Ghost has no subclass) and `variant` (for the
`leader` gold treatment).

## Core Process

```bash
python3 tools/ensemble.py roster --month YYYY-MM --out roster.json
python3 tools/plate.py plan cut.json --roster roster.json --max-shot-sec 9 \
    --out plates.json
python3 tools/plate.py burn --video renders/cut.mp4 --manifest plates.json \
    --out renders/cut-plated.mp4
```

`plan` reads copy from `vocab/casting.yaml`'s `plate:` block — the same file
that binds a character to a person — so recasting a role changes the on-screen
credit and nothing else.

Scheduling rules, all of which exist because a plate is a claim about a person:

- Each lead is plated **once**, on the first appearance long enough to read.
- Never on a shot with `usable = false`: that shot is already excluded from the
  character's retrieval, so it is not a reveal.
- A plate is **anchored** to a shot but not confined to it — a lower third rides
  across a cut, and Destiny cinematics are full of two-second shots that could
  otherwise never carry a reveal. The anchor must still be long enough to
  register (`MIN_ANCHOR`).
- **Two plates are never visible at once.** `plan` and `burn` both refuse an
  overlapping manifest.
- Contributors whose shot is too short are credited together on a roster title
  card over the tail. Dropping a month's contributors silently is the one
  unacceptable outcome.

### Before a roster exists

```bash
python3 tools/plate.py plan cut.json --placeholders 4 --max-shot-sec 9 \
    --out plates.json
```

`--placeholders N` plates the first N ensemble shots that can hold a plate with
`ensemble.placeholder_plate` from `vocab/casting.yaml` — `CONTRIBUTOR //
GUARDIAN`, name `TBD`, default blue chrome. It names nobody on purpose: a
placeholder is for timing and review of a cut whose cast is not decided.

It is mutually exclusive with `--roster` and raises if both are passed. Once
real contributors are known, they are who the plate is for — swap the flag, do
not edit the copy. If fewer than N fit, you get the ones that read; a plate
squeezed in where it cannot be finished is worse than one less plate.

`burn` composites every plate in one ffmpeg pass — an `overlay` chain gated by
`enable='between(t,in,out)'` — and stream-copies audio, so titling never costs
the soundtrack a second generation. `enable` is FFmpeg's timeline-editing
option: the expression is evaluated per frame, and the filter passes the frame
through untouched when it is false.

```text
smartblur = enable='between(t,10,3*60)'
```

`source: /websites/ffmpeg_documentation` (timeline editing)

## Styling provenance

Ported from `projectbluefin/website`
`src/components/wolves/WolvesIntroOverlay.vue` (`.wolves-guardian-plate` and
friends): near-black translucent fill, chamfered corners, thin blue-white rules,
hex crest with chevron, uppercase letter-spaced eyebrow. The CSS is the source
of truth; `tools/plate.py` names the rule each constant came from so the two can
be diffed by eye. The entrance animation is deliberately not reproduced — a
still plate keeps the burn one ffmpeg pass instead of an image sequence.

The `ov/*.py` renderer described in `~/Videos/OVERLAYS.md` **no longer exists**;
`tools/plate.py` is the live implementation.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "One extra line makes the plate clearer." | It makes the plate say something nobody wrote. The deck's fields are the contract. |
| "I'll hardcode the copy just for this render." | Then the credit and the casting drift apart the first time a role is recast. Copy lives in `vocab/casting.yaml`. |
| "The plate is short, it can share the screen." | Two plates at once is unreadable; both `plan` and `burn` refuse it. |
| "The shot is only two seconds, so nobody can be plated there." | The plate rides across the cut. Only the *anchor* must be long enough to register. |
| "I'll put a plausible name on the placeholder so it looks finished." | A plate names a real person. `TBD` is the honest answer until a roster exists. |

## Red Flags

- Inventing a plate line, a role, or a pronoun row.
- Hardcoding copy in the manifest instead of `vocab/casting.yaml`.
- Planning with a different `--max-shot-sec` than the render used — every plate
  after the first trimmed shot lands late.
- A subclass line on a Ghost.
- A placeholder plate carrying anything but the vocab's uncast copy, or shipping
  alongside a real roster.

## Verification

```bash
python3 -m pytest -q tests/test_plate.py     # includes the closed-vocabulary test

# eyeball a plate inside its window
ffmpeg -ss <at+1> -i renders/cut-plated.mp4 -frames:v 1 /tmp/plate.jpg
```
