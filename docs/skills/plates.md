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
| `class` | `Voidwalker Warlock` |
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

The deck's `gp_*` entries add three **placement** fields, which are deck data,
not new copy: `position: "group"` with an absolute `x` (measured against the
picture, never the raw frame), a `scale` factor that shrinks the card, and a
`group` key marking which row a card belongs to.

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

## Plates from a brief

The exception to "copy lives in `vocab/casting.yaml`" is the owner writing a
plate into an issue's `brief` block (`plates[]` in
[`schema/brief.schema.json`](../../schema/brief.schema.json)) — issue #1 plates
Paris Pittman, who has no binding. That is legitimate: the owner is the one
source that may introduce a *new* claim about a real person, and the brief is
where they speak. `plan` reads it:

```bash
python3 tools/plate.py plan cut.json --brief 1 --out plates.json   # or a YAML file
```

Brief plates are planned **first**, as fixed credits, and everything derived
routes around them. They live inside `plan` — not in a post-hoc `merge` — for
two reasons: a brief's `at` is in *source* time ("drop her nameplate right
after she removes her helmet, 0:14") and only the shot list can map that onto
the cut's clock, and a brief plate naming a `character` **is** that
character's one plate — planned anywhere else it would double-plate the
reveal or die on `merge`'s overlap check.

Three rules keep the exception narrow:

- **The field set is still closed.** A `copy` key the deck has no field for is
  refused, from a brief same as anywhere else.
- **The vocab wins a conflict.** If the character's binding already has a
  `plate:` block, that copy is used and the brief's is reported as deferred.
  The vocab is the durable record, changed by reviewed PR; a brief is one
  video's request in an editable issue body. Letting a brief override it would
  let two videos disagree about a real person's credit — the drift the vocab
  exists to prevent. A brief that disagrees is a signal the record needs an
  edit, so the conflict is logged, never adjudicated silently. (The owner's
  *timing* is still honoured — timing is a per-video decision; copy is a
  durable claim.)
- **The owner's `at` is honoured, not re-derived.** The moment is mapped from
  source time onto the cut, exactly — no `LEAD_IN`, because the owner pointed
  at a moment inside the footage, not a shot head. A moment that is not in the
  cut is **reported, not moved**; a plate that names a `character` falls back
  to the derived reveal rather than vanishing, and one that carries only copy
  is reported and skipped. Without an `at`, a plate goes through the normal
  reveal scheduling (hero move and all) with the brief's copy.

Every planned entry carries `copy_source` — `"brief"` or `"casting"` — so a
reader of the manifest can tell an owner-authored plate from a vocab-derived
one without knowing the convention. Brief plates are lead-tier: with
`--only ensemble` they arrive via `--around`, the same way dialogue does.

Scheduling rules, all of which exist because a plate is a claim about a person:

- Each lead is plated **once**, on the first shot long enough to read.
- A reveal **waits for the character's hero move**. `traversal_hero` is already
  derived — wide, stable, in motion — so the index says which shot that is, and
  the reveal prefers it over the static insert the character happens to appear
  in first. Osiris is named as he climbs the stairwell, not while the camera
  sits on his mask. Bounded by `MAX_REVEAL_DEFERRAL`: a lead the audience has
  watched unnamed for that long is not being revealed any more, just belatedly
  captioned, so past it the reveal drops back to the first appearance.
- Never on a shot with `usable = false`: that shot is already excluded from the
  character's retrieval, so it is not a reveal.
- A plate is **anchored** to a shot but not confined to it — a lower third rides
  across a cut, and Destiny cinematics are full of two-second shots that could
  otherwise never carry a reveal. The anchor must still be long enough to
  register (`MIN_ANCHOR`).
- **Two plates are never visible at once — unless they share a row.** `plan`
  and `burn` both refuse an overlapping manifest, with one narrow exception:
  members of the same group row carry a shared `group` key and are one row by
  construction. A group member overlapping anything outside its row is still
  an error.
- **A crowded shot's ensemble credits are a staggered row, not a queue.** A
  shot with several ensemble slots spreads its cards across the frame like the
  reference deck's roll call (`gp_*`): doubly staggered, with entrances
  cascading `GROUP_STAGGER` (0.4s) apart and every card ending together. `x`
  is an **even spread centred on the picture**, computed from the actual
  rendered card widths — deliberately *not* a pointer at a specific body,
  because the casting model says the anonymous crowd is fillable by anyone and
  a plate that singles out a Guardian overclaims it. The row renders at
  `GROUP_SCALE` (0.78, the deck's value) and shrinks until it fits the row
  margins; six cards still fit one row. Past `GROUP_MIN_SCALE` the type is too
  small to be a credit, so the slots split into the fewest balanced rows that
  each fit (an unusually wide mix goes 3+3 in separate windows), and a shot
  that cannot hold a readable row at all falls back to the old sequential
  right-hand plates. Either way contributors are never dropped over a layout:
  whoever the shot cannot hold still goes through the re-home pass and the
  tail roster card.
- Contributors whose shot is too short are credited together on a roster title
  card over the tail — the card's headline is the owner-supplied
  `roster_title` in `vocab/casting.yaml` ("Thanks for working on Bluefin!"),
  its `subtitle` carries the month context. Dropping a month's contributors
  silently is the one unacceptable outcome.
- **That card is the cut's last beat, not just an overflow list.** It plays
  whether or not anyone is left to credit; its `body` (the leftover names) may
  be absent. Gating it on leftovers meant that crediting everyone in the body
  silently deleted the ending.
- **A person cast as a lead is never an anonymous Guardian.** `tools/ensemble.py`
  excludes anyone bound to a lead character from the contributor pool and
  reports them as `cast_as_lead`. castrojo is Cayde-6, so he is not a blueberry
  in the crowd: his authored plate lives on the `cayde_6` binding, and he is
  credited in cuts where Cayde is actually on screen. Being a named character
  and a nameless Guardian at once is a contradiction, and it puts a real person
  in a video their character is not in.
- **A maintainer is not a passing contributor.** `tools/ensemble.py roster`
  records `org_member` per person from the GitHub org (`gh api
  orgs/<org>/members`, falling back to public members), and the eyebrow follows
  it: `MAINTAINER // GUARDIAN` for org members, `CONTRIBUTOR // GUARDIAN`
  otherwise. Both strings live in `vocab/casting.yaml`, never in the renderer.
  `org_member` is **tri-state** — `null` means the lookup failed, which is not
  the same as "not a member", so it takes a neutral `GUARDIAN` eyebrow rather
  than silently demoting everyone when a token expires.
- **An authored identity beats the generic copy.** `ensemble.titles` in
  `vocab/casting.yaml` maps a GitHub login to that person's Guardian plate
  exactly as authored in the reference deck (castrojo's is `np_jorge`). A
  contributor with an entry gets that plate verbatim wherever they land;
  everyone else falls back to `Bluefin Blueberry`, because an unknown seal is
  never a made-up one. A specially-titled contributor who would otherwise land
  on the roster card gets first claim on the tail window, so the card never
  flattens an authored identity into a name line while the cut has room for
  the real plate. Add a login only with copy that exists in the deck.

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

**Where the site and the videos disagree, the videos win.** The plates in the
other cuts were baked by a headless browser from
`~/Videos/wolves-{kat,natali}/render/reveal.html`, which is a deliberate literal
2× of `.wolves-guardian-plate` — and it diverges from the live site in ways that
are immediately visible side by side:

| | Site CSS | Baked reveal (**use this**) |
|---|---|---|
| Class row case | `text-transform: uppercase` | authored case — "Behemoth Titan" |
| Class colour | `#bfdbfe` | `#cbd5f5` |
| Title colour | `#94a3b8` slate | `#93c5fd` blue |
| Title tracking | none | `0.08em` |

The **font** is the one that reads as broken from across the room. The stack is
`ui-monospace, 'SFMono-Regular', 'Cascadia Mono', monospace`; neither Apple's
SF Mono nor Cascadia Mono ships on a Fedora atomic host, so the browser fell
through to the fontconfig generic — **DejaVu Sans Mono**. Adwaita Mono is the
desktop's monospace and *is* installed, so preferring it silently rendered every
plate in a typeface that appears in neither the stack nor any other video.
Check with `fc-match monospace` before assuming.

Also carried from the baked reveal: the name's gradient has a **middle stop**
(`#fff 0%, #e2e8f0 60%, #a0aec0 100%`), the type has a `text-shadow`
(`0 2px 10px rgb(0 0 0 / 80%)` — it matters, the plate is translucent and
footage moves behind it), and the box applies `border-radius` *and* a
`clip-path`, so two corners are chamfered and the other two are rounded.

The `ov/*.py` renderer described in `~/Videos/OVERLAYS.md` **no longer exists**;
`tools/plate.py` is the live implementation.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "One extra line makes the plate clearer." | It makes the plate say something nobody wrote. The deck's fields are the contract. |
| "I'll hardcode the copy just for this render." | Then the credit and the casting drift apart the first time a role is recast. Copy lives in `vocab/casting.yaml` — or, for someone the vocab does not bind yet, in the issue's brief, which `plan` marks `copy_source: brief`. |
| "The brief's copy contradicts the binding, but the owner wrote it today." | Recency is not authority: the vocab is the reviewed record, the issue body is editable. The vocab wins; edit it if the brief is right. |
| "The plate is short, it can share the screen." | Two plates at once is unreadable; both `plan` and `burn` refuse it. The only exception is a group row, whose members are built to be seen together. |
| "The shot is only two seconds, so nobody can be plated there." | The plate rides across the cut. Only the *anchor* must be long enough to register. |

## Red Flags

- Inventing a plate line, a role, or a pronoun row — from a brief same as
  anywhere else: `plan` refuses a `copy` field outside the deck's set.
- Hardcoding copy in the manifest instead of `vocab/casting.yaml`.
- A plate manifest that hides where its copy came from — every planned entry
  carries `copy_source`, and a brief plate without it is a hand-edit.
- Letting a brief override a binding's `plate:` block silently. The vocab
  wins; if the brief is right, the fix is a vocab edit, not a per-video
  override.
- Planning with a different `--max-shot-sec` than the render used — every plate
  after the first trimmed shot lands late.
- A subclass line on a Ghost.
- A plate rendered in Adwaita Mono (or anything but DejaVu Sans Mono) — it is
  not in the font stack and matches none of the other videos.
- Styling taken from the live site where the baked reveal disagrees.
- A plate positioned against the frame on a letterboxed source, so it sits on
  the black bar instead of the picture.

## Verification

```bash
python3 -m pytest -q tests/test_plate.py     # includes the closed-vocabulary test

# eyeball a plate inside its window
ffmpeg -ss <at+1> -i renders/cut-plated.mp4 -frames:v 1 /tmp/plate.jpg
```
