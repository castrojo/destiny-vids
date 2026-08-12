---
name: plates
version: "1.0"
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
  card over the tail; a tail too short even for that card lands every one of
  them in `unresolved` instead. Dropping a month's contributors silently is the
  one unacceptable outcome.

`plan` writes `{"plates": [...], "unresolved": [...]}`. A lead who made the cut
but got no plate lands in `unresolved` rather than disappearing, with the reason
and whether a tool can fix it — and so does an ensemble contributor whom even
the tail roster card had no room for:

| `reason` | Means | `automatable` |
|---|---|---|
| `uncast` | `leads.<character>.person` is null — nobody to credit | `false` — an owner casting decision |
| `no_plate_copy` | The binding has no `plate:` block, and copy is never invented | `false` — owner-authored copy |
| `no_window` | No appearance was long enough, or free, to hold a plate | `true` — re-plan, or give them a longer anchor |

Nothing blocks: the manifest is written either way, and `render`/`burn` read the
`plates` list and ignore the punch-list. Someone being cast but plate-only is a
legitimate resting state — see [`casting.md`](casting.md).

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
| "No copy for this lead? Write them something." | Then the plate says what nobody wrote. Leave them in `unresolved` until the owner writes it. |

## Red Flags

- Inventing a plate line, a role, or a pronoun row.
- Hardcoding copy in the manifest instead of `vocab/casting.yaml`.
- Shipping a cut with a non-empty `unresolved` list without reading it: someone
  who was on screen went uncredited. The list is the whole punch-list — an
  empty `unresolved` really does mean nobody was missed, so anything it does
  not report is a bug in `plan`, not a gap to work around.
- Planning with a different `--max-shot-sec` than the render used — every plate
  after the first trimmed shot lands late.
- A subclass line on a Ghost.

## Verification

```bash
python3 -m pytest -q tests/test_plate.py     # includes the closed-vocabulary test

# eyeball a plate inside its window
ffmpeg -ss <at+1> -i renders/cut-plated.mp4 -frames:v 1 /tmp/plate.jpg
```
