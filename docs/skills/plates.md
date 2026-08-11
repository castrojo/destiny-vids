---
name: plates
version: "1.0"
last_updated: "2026-08-11"
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

The deck's other shapes are the title card (`title`, `subtitle`, `body[]`) and
the **chat card** (`speaker`, `text`) — see "Showing a conversation" below.

That is the whole vocabulary, taken from the reference deck
(`~/Videos/nameplates.json`). **Do not add a line the deck has no field for.**
An invented row — an `AS <CHARACTER>` casting line, a role, a pronoun — puts
unauthored text on a card whose entire purpose is naming real people, and a
test pins the vocabulary so it cannot drift by accident. If a plate genuinely
needs to say something new, add the field to the data model deliberately.

Local additions to the deck's shape are limited to chrome flags: `kind: ghost`
(drops the class line, because a Ghost has no subclass) and `variant` (for the
`leader` gold treatment — the wolves trailer reserves it for Christoph Blecker,
and it **takes precedence over `trustee`**, mirroring the CSS selector
`.wolves-guardian-plate-trustee:not(.wolves-guardian-plate-leader)`, so a
binding may carry both flags and plate gold. The leader block deliberately does
not restyle the class row, which stays the default blue).

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

`burn` composites every plate in one ffmpeg pass — an `overlay` chain gated by
`enable='between(t,in,out)'` — and stream-copies audio, so titling never costs
the soundtrack a second generation. `enable` is FFmpeg's timeline-editing
option: the expression is evaluated per frame, and the filter passes the frame
through untouched when it is false.

```text
smartblur = enable='between(t,10,3*60)'
```

`source: /websites/ffmpeg_documentation` (timeline editing)

## Showing a conversation

The chat card (`kind: chat`) puts a line of dialogue on screen under the name
of the person cast in that role. It exists because the alternative — typing the
conversation into a manifest — is exactly the invented copy the rest of this
skill forbids. Both of its fields are recovered, never authored here:

- `speaker` comes from `vocab/casting.yaml`, preferring the character's `plate:`
  name, so a line and that character's reveal credit the person identically.
- `text` comes from `dialogue/<video_id>/dialogue.json`, which carries the
  source timecodes, the recovery method, and per-line `evidence` for who is
  speaking. Fix a wrong line **there**, not in a render.

Each video's conversation lives in its own folder, beside the Markdown the
owner actually edits:

```text
dialogue/<video_id>/DIALOGUE.md    the conversation, as prose
dialogue/<video_id>/dialogue.json  the provenance record the pipeline reads
```

`tools/dialogue_md.py` keeps the two in step, and is the only supported way to
rewrite a line:

```bash
python3 tools/dialogue_md.py export <video_id>            # record -> DIALOGUE.md
python3 tools/dialogue_md.py apply  <video_id> --dry-run  # preview the edits
python3 tools/dialogue_md.py apply  <video_id>            # DIALOGUE.md -> record
```

Editing the Markdown never loses provenance. Timecodes and evidence ride in the
heading and are restored verbatim; a line the owner rewrites is marked
`text_source: owner_supplied` and keeps the recovered wording in
`recovered_text`; a deleted section moves to `dropped` with a reason. The
owner supplying copy is allowed — an *agent* inventing it is not, and keeping
both versions is what tells the two apart. A test asserts the checked-in
`DIALOGUE.md` still matches the record, so the pair cannot drift.

It deliberately carries no `class` row and no character line: who plays whom is
established once by the Guardian reveal.

```bash
# 1. reveals first -- naming the cast right is the job the index exists for
python3 tools/plate.py plan cut.json --only leads --hold 4 --out leads.json
# 2. dialogue fits around them (anchored: each line where its footage landed)
python3 tools/dialogue.py cut.json --video-id <id> --around leads.json \
    --out chat.json
# 3. the ensemble takes what is left, then merge and burn
python3 tools/plate.py plan cut.json --roster roster.json --only ensemble \
    --around fixed.json --out ens.json
python3 tools/plate.py merge leads.json chat.json ens.json --out plates.json
```

`--mode script` is the alternative: it replays the exchange in spoken order
instead of anchoring each line to its own footage. Anchored is right for an
uncut source, where the picture and the conversation share a clock. Script mode
is for a **re-ordered cut**, where anchoring scatters the lines out of sequence
and the exchange stops reading as a conversation.

Dropped lines are always reported with a reason — a line whose footage is not
in the cut, or that a reveal already covers, is never lost silently.

## Keep plates on the picture

Bungie's cinematics are 2.39:1 delivered in a 16:9 file, so roughly 140px at
the top and bottom of every frame is baked-in black. The row margins are
percentages, so measuring them against the *frame* drops a plate onto that bar
— it reads as a mistake, not a style, and it is the easiest defect to miss on a
still.

`render` and `burn` detect the real picture area with ffmpeg's `cropdetect` and
position against it:

```bash
python3 tools/plate.py render --manifest plates.json --fit-video media/<id>.mp4
python3 tools/plate.py burn --video base.mp4 --manifest plates.json \
    --fit-picture --out out.mp4
```

Detection falls back to the full frame when there is no letterbox, so passing
it is always safe.

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

## Red Flags

- Inventing a plate line, a role, or a pronoun row.
- Hardcoding copy in the manifest instead of `vocab/casting.yaml`.
- Planning with a different `--max-shot-sec` than the render used — every plate
  after the first trimmed shot lands late.
- A subclass line on a Ghost.
- A plate positioned against the frame on a letterboxed source, so it sits on
  the black bar instead of the picture.

## Verification

```bash
python3 -m pytest -q tests/test_plate.py     # includes the closed-vocabulary test

# eyeball a plate inside its window
ffmpeg -ss <at+1> -i renders/cut-plated.mp4 -frames:v 1 /tmp/plate.jpg
```
