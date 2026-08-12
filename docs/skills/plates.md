---
name: plates
version: "1.7"
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
| `class` | `Voidwalker Warlock` |
| `name` | `Bob Killen` |
| `title` | `Reconciler of the Plane` |
| `trustee` | `true` — the burnished-silver chrome |

The deck's other shapes are the title card (`title`, `subtitle`, `body[]`) and
the **chat card** (`speaker`, `text`) — see "Showing a conversation" below.

That is the whole vocabulary, taken from the reference deck
(`~/Videos/nameplates.json` — see "Where the copy is authored" below).
**Do not add a line the deck has no field for.**
An invented row — an `AS <CHARACTER>` casting line, a role, a pronoun — puts
unauthored text on a card whose entire purpose is naming real people, and a
test pins the vocabulary so it cannot drift by accident. If a plate genuinely
needs to say something new, add the field to the data model deliberately.

Local additions to the deck's shape are limited to chrome flags: `kind: ghost`
(drops the class line, because a Ghost has no subclass) and `variant` (`leader`
gold — the wolves trailer reserves it for Christoph Blecker — and it **takes
precedence over `trustee`**, mirroring the CSS selector
`.wolves-guardian-plate-trustee:not(.wolves-guardian-plate-leader)`, so a
binding may carry both flags and plate gold; the leader block does not restyle
the class row, which stays the default blue — and `rust`, oxidised iron for the
Rust Foundation herald, per #8 — and `bazzite`, Bazzite purple for the end
fight). A variant is colour only. Owner-authored imagery chrome — `avatar`,
`wreath`, bracketed names like `[ REDACTED ]` — is likewise not copy:
[`references/plate-chrome.md`](references/plate-chrome.md).

The deck's `gp_*` entries add three **placement** fields, which are deck data,
not new copy: `position: "group"` with an absolute `x` (measured against the
picture, never the raw frame), a `scale` that shrinks the card, and a `group`
key marking which row a card belongs to. Two more come from the intro overlay:
`raised` (`top: 28%`, for a Guardian towering over the lower third) and
`position: "status"`.

## The status nameplate is a fourth card, added deliberately

The site's **top-of-frame HUD** (`Nameplate.vue`) is not the reveal plate: it is
persistent chrome the intro overlay re-labels per cue, carrying **exactly two**
authored lines — `detail` and `label` — plus one chrome flag, `glitch`. It is a
**different row** from the lower third, so the one-plate-at-a-time check exempts
it against a Guardian plate; two status cards at once are still an error. Its
copy comes from the per-cue overrides *and* the segment default, so reproducing
only the cues renders a card that flickers where the site holds one
continuously. See [`references/status-nameplate.md`](references/status-nameplate.md).

## Where the copy is authored

"The deck" is shorthand for **four** files outside this repo, and knowing which
one to read is the difference between reproducing a credit and inventing one.
None of them is editable from here — this repo *reproduces* them:

| Source | What it is authoritative for |
|---|---|
| `~/Videos/nameplates.json` | The **field set**, the chrome flags, and the KubeCon interview's own plate timings. The worked example of every shape. |
| `~/src/website/public/wolves/characters/characters.json` | The **authored Guardian identities** — `label`, `class`, `name`, `title` per person. The broadest roster: seven people. |
| `~/src/website` `src/data/wolves-intro-sequence.ts` | The same identities as they appear in the Wolves intro, and the second corroboration when one disagrees. |
| `~/Videos/wolves-{kat,natali}/render/reveal.html` | The **baked** treatment the finished cuts actually shipped. Where it disagrees with the live site CSS, it wins — see "Styling provenance". |

**Never touch `~/src/website`.** Several agents run worktrees against it; read
it, quote it, and cite the file you read.

The seven authored identities, verbatim:

| Person | Label | Class | Title |
|---|---|---|---|
| Bob Killen | `TRUSTEE // GUARDIAN` | Voidwalker Warlock | Reconciler of the Plane |
| Kat Cosgrove | `MAINTAINER // GUARDIAN` | Sentinel Titan | Defender Queen of the Lost |
| Kaslin Fields | `MAINTAINER // GUARDIAN` | Stormcaller Warlock | Rage of the Paradox |
| Laura Santamaria | `MAINTAINER // GUARDIAN` | Gunslinger Hunter | The Order of Seven |
| Christoph Blecker | `TRUSTEE // GUARDIAN` | Broodweaver Warlock | First Among Equals — The North Star |
| Natali Vlatko | `MAINTAINER // GUARDIAN` | Behemoth Titan | Shipwright of Kubernetes |
| Doctor Andy Anderson | `MAINTAINER // GUARDIAN` | Shadebinder Warlock | Foundry of the Forbidden |

Plus, from `nameplates.json` only: **Jorge Castro** (Harbinger Titan, *Upender
of Antipatterns | The First Disciple*), **Jeffrey Sica** (Stormbreaker Titan,
*Forgemaster of the Seven*) and **Amber Graner** (Striker Titan, *The Iron
Standard*).

Two things follow, and they are the reason this section exists:

- **An identity that is authored must be reproduced, never paraphrased and
  never replaced by the generic fallback.** A person with an entry above is not
  a Bluefin Blueberry, wherever their credit lands.
- **An identity that is not authored is not yours to write.** `np_amber`'s own
  note records the correct shape of that gap: the deck carried
  `Subclass [ REDACTED ]` until the *owner* supplied Amber's class. That is
  exactly the state issue #5 is in for Karena Angell's subclass — the row ships
  short until the owner has the word.

### Known divergences

Recorded, not resolved. Each one is somebody's call, not an agent's:

- **Jeffrey Sica's title.** The deck says *Forgemaster of the Seven*; issue #1's
  owner-authored brief copy says *Forgemaster of Kubernetes*. A brief is the
  owner speaking, so `plan` will use it — but the two records disagree and one
  of them wants editing. See #27 (and #17 for whether he is cast at all).
- **A portrait row.** `reveal.html`'s `pfp` is implemented as the `avatar`
  chrome flag — see [`references/plate-chrome.md`](references/plate-chrome.md).
- **Kelsey Hightower has no deck entry** — but his plate is authored anyway.
  The owner wrote all four rows (`ARCHITECT // GUARDIAN`, Dawnblade Warlock,
  Kelsey Hightower, *Evangelist of the Open Sky*) into issue #8, so the issue —
  not the deck — is the authorisation, and the rows are reproduced verbatim on
  Zavala's binding. #33 added gold chrome (`variant: leader`) **on top of** that
  copy, not instead of it. Anything beyond those four rows is still not ours to
  write: a lead's `class: titan` tags describe *Zavala*, and printing one on
  the card would make it a claim about Kelsey, which only the owner may make.
- **Four of the seven have no binding here** — Kaslin, Christoph, Natali and
  Andy (see #26); Bob, Laura and Kat are bound and their copy is reproduced
  above. Adding a binding is a casting decision ([`casting.md`](casting.md));
  copying authored copy onto an existing binding is reproduction and is allowed.

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
[`schema/brief.schema.json`](../../schema/brief.schema.json)) — which may name
somebody who has no binding at all. That is legitimate: the owner is the one
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
- **A floor on the reveal is the owner's to set, not the tool's to fake.**
  `--reveal-after MM:SS` holds every derived lead reveal until that point on the
  *finished cut's* clock ("don't name him until 1:50"), and suppresses the
  `MAX_REVEAL_DEFERRAL` bound while it applies — the deferral cap exists to stop
  the tool dawdling, not to overrule an explicit ask. It is distinct from a
  brief's `at`, which pins **one** credit to a moment in *source* time. The
  floor only ever moves a reveal onto a later shot the character is genuinely
  in; if no appearance lies at or after it, the reveal degrades to the
  character's **latest** appearance and the shortfall is reported as
  `reveal_floor_missed` (`automatable: false`). Missing a timing request is
  recoverable; naming a real person over a shot they are not in is not.
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
- **The owner can pin a slot to a moment.** A brief beat with `ensemble: true`
  and an `at` — issue #1's "4:03 put a bluefin maintainer in here" — is a
  *fixed point*: `plan` takes that window before the rotation runs, and the
  round-robin routes around it the way it routes around a lead reveal. It
  requests a **slot, never a person**: who fills it is still the month's
  rotation, and the note stays direction rather than becoming copy, because a
  note turned into copy would put the owner's words on whichever real
  contributor landed there. A moment outside the cut is reported, not moved.

`plan` writes `{"plates": [...], "unresolved": [...]}`. A lead who made the cut
but got no plate lands in `unresolved` rather than disappearing — and so does
an ensemble contributor even the tail roster card had no room for:

| `reason` | Means | `automatable` |
|---|---|---|
| `uncast` | `leads.<character>.person` is null — nobody to credit | `false` — an owner casting decision |
| `no_plate_copy` | The binding has no `plate:` block, and copy is never invented | `false` — owner-authored copy |
| `no_window` | No appearance was long enough, or free, to hold a plate | `true` — re-plan, or give them a longer anchor |

Nothing blocks: the manifest is written either way, and `render`/`burn` read the
`plates` list and ignore the punch-list. Someone being cast but plate-only is a
legitimate resting state — see [`casting.md`](casting.md).

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
through untouched when it is false (`source: /websites/ffmpeg_documentation`,
timeline editing).

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

A record can also hold a line **never recovered at all** (act II's owner-
written closer): the top-level methods and the cue's `text_source`/`evidence`
are `owner_supplied` with no `recovered_text`, and it still enters via `apply`.

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

The plate treatment is ported from the website's `WolvesIntroOverlay.vue`, and
where the site and the baked video reveals disagree, **the videos win**. The
constant-by-constant record — the four known divergences, the font trap
(`fc-match monospace`), and the gradient, shadow and chamfer details — lives in
[`references/plate-styling.md`](references/plate-styling.md).

The port covers the *deck's* shapes only. The two **full-frame** cards — the act
slide and the intro's comic title card — are still live on the site, so they are
rendered from its own CSS by `cards/render-cards.mjs` rather than ported;
`tools/plate.py` refuses one and names the driver. See
[`references/full-frame-cards.md`](references/full-frame-cards.md).

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "One extra line makes the plate clearer." | It makes the plate say something nobody wrote. The deck's fields are the contract. |
| "I'll hardcode the copy just for this render." | Then the credit and the casting drift apart the first time a role is recast. Copy lives in `vocab/casting.yaml` — or, for someone the vocab does not bind yet, in the issue's brief, which `plan` marks `copy_source: brief`. |
| "The brief's copy contradicts the binding, but the owner wrote it today." | Recency is not authority: the vocab is the reviewed record, the issue body is editable. The vocab wins; edit it if the brief is right. |
| "The plate is short, it can share the screen." | Two plates at once is unreadable; both `plan` and `burn` refuse it. The only exception is a group row, whose members are built to be seen together. |
| "The shot is only two seconds, so nobody can be plated there." | The plate rides across the cut. Only the *anchor* must be long enough to register. |
| "I'll put a plausible name on the placeholder so it looks finished." | A plate names a real person. `TBD` is the honest answer until a roster exists. |
| "No copy for this lead? Write them something." | Then the plate says what nobody wrote. Leave them in `unresolved` until the owner writes it. |

## Red Flags

- Inventing a plate line, a role, or a pronoun row — from a brief same as
  anywhere else: `plan` refuses a `copy` field outside the deck's set.
- Hardcoding copy in the manifest instead of `vocab/casting.yaml`.
- A plate manifest that hides where its copy came from — every planned entry
  carries `copy_source`, and a brief plate without it is a hand-edit.
- Letting a brief override a binding's `plate:` block silently. The vocab
  wins; if the brief is right, the fix is a vocab edit, not a per-video
  override.
- Shipping a cut with a non-empty `unresolved` list without reading it: someone
  who was on screen went uncredited. The list is the whole punch-list — an
  empty `unresolved` really does mean nobody was missed, so anything it does
  not report is a bug in `plan`, not a gap to work around.
- Planning with a different `--max-shot-sec` than the render used — every plate
  after the first trimmed shot lands late.
- A subclass line on a Ghost.
- A plate rendered in Adwaita Mono (or anything but DejaVu Sans Mono) — it is
  not in the font stack and matches none of the other videos.
- Styling taken from the live site where the baked reveal disagrees.
- A full-frame card re-implemented in Python instead of rendered from the
  site's CSS — that is a second copy of chrome that already exists, and the two
  drift the first time the site changes.
- Falling back to `Bluefin Blueberry` for one of the seven people whose
  Guardian identity **is** authored (see "Where the copy is authored"). An
  unknown seal is a blueberry; a known one is a paraphrase.
- A plate positioned against the frame on a letterboxed source, so it sits on
  the black bar instead of the picture.
- A placeholder plate carrying anything but the vocab's uncast copy, or shipping
  alongside a real roster.

## Verification

```bash
python3 -m pytest -q tests/test_plate.py     # includes the closed-vocabulary test
python3 -m pytest -q tests/test_derive.py    # pins every authored plate verbatim

# diff every binding against the file that authored it (read-only) --
# the snippet lives in references/plate-styling.md, "Checking a binding for drift"

# eyeball a plate inside its window
ffmpeg -ss <at+1> -i renders/cut-plated.mp4 -frames:v 1 /var/tmp/plate.jpg
```
