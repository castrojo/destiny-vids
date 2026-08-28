---
name: plates
version: "1.3"
last_updated: "2026-08-27"
id: plates
one_line_purpose: Render authored identity and dialogue cards without inventing copy.
entry_point: docs/skills/plates/SKILL.md
category: media-production
status: active
dependencies: []
tags:
  - nameplates
  - copy
  - cards
  - credits
  - rendering
description: >-
  Render authored identity and dialogue cards without inventing copy. Use when
  burning Guardian nameplates, chat cards, or full-frame cards onto a video.
metadata:
  type: policy
  context7-sources:
    - /addyosmani/agent-skills
    - /websites/ffmpeg_documentation
---

# Guardian nameplates

## When to Use

- Crediting a lead or the monthly ensemble on screen
- Changing plate copy, position, or timing
- Porting the Bluefin plate treatment somewhere new

## When NOT to Use

- Narration captions → the `authoring-video-closed-captions` skill
- Deciding *who* is cast → [`casting`](../casting/SKILL.md)

## Before you edit a manifest: is it an output?

Three checks, in order, before changing any `stories/*.json`. Each one has
already caught a wrong edit.

**1. Is it generated?** `stories/02-endless-forms-plates.json` is built by
`scripts/build_efmb_plates.py`, and the suite asserts the committed file equals
what the generator produces. A card added by hand survives until the next
build and no longer. Put the copy in the generator and regenerate.

```bash
grep -rl "$(basename <manifest>)" scripts/    # a builder here means it is an output
```

**2. Is the count pinned?** `schema/ending-cards.schema.json` fixes the ending
at `minItems: 15, maxItems: 15`. Adding a card fails validation until the bound
moves in the same commit. That pairing is deliberate — the ending is a fixed
sequence, so growing it is a decision, not a side effect.

**3. Will the seat collide?** `tools/plate.py::load_manifest_entries` refuses
two plates visible at once. Run it before committing:

```bash
python3 -c "
import json,sys; sys.path.insert(0,'.')
from tools import plate
d=json.load(open('stories/<manifest>.json'))
e=[p for p in (d.get('plates') or d.get('cards') or [])
   if isinstance(p.get('at'),(int,float)) and isinstance(p.get('dur'),(int,float))]
plate.load_manifest_entries(e)"
```

**If it refuses, that is the end of the automated road.** Sliding a
neighbouring plate to make room re-times an authored beat, which is the fourth
thing an agent may never do. Report the collision and the options; do not
resolve it. See "Degrade, never block" in [`AGENTS.md`](../../../AGENTS.md).

## The field set is closed

A Guardian nameplate carries **exactly**:

| Field | Example |
|---|---|
| `label` | `TRUSTEE // GUARDIAN` |
| `class` | `Voidwalker Warlock` |
| `name` | `Bob Killen` |
| `title` | `Reconciler of the Plane` |
| `trustee` | `true` — the burnished-silver chrome |

The deck's other authored shapes are the title card (`title`, `subtitle`, `body[]`) and the **chat card** (`speaker`, `text`) — see [`references/conversation-cards.md`](references/conversation-cards.md).

Keep chat `text` verbatim. For owner-requested censors, use the Kubernetes helm only for an `o`, an asterisk for other letters, and no unrequested censorship; the complete data contract is in [`references/conversation-cards.md`](references/conversation-cards.md).

A title card may use `position: "top-right"` for a sign in the picture's
upper-right safe area. The renderer measures both margins against the detected
picture rectangle, so the card stays on the image when the source is
letterboxed.

An owner-retired authored card remains complete in the generator's `RETIRED`
record, including timing and identity fields, and is removed from active pass
data; never preserve a partial duplicate.

### Finished identities never degrade to placeholders

Once a person's Guardian identity is authored, finished work reproduces the
complete authored text rows and the owner's recorded chrome treatment — never a
placeholder plate, a generic fallback such as `Bluefin Blueberry`, or an
agent-made approximation of the authored rows to make a timing pass look
complete.

**Castrojo's Guardian plates are standard blue and carry his full authored
identity:** `TRUSTEE // GUARDIAN` / `Harbinger Titan` / `Jorge Castro` /
`Upender of Antipatterns | The First Disciple`. `TRUSTEE` in the label is copy,
not permission to set `trustee: true`; omit that chrome flag and any `variant`.

The one permitted narrowing is **explicit and owner-authored**: the owner may
record a partial or name-only treatment in the manifest itself. Act II's
**named placeholder badge** (`placeholder_dylan_taylor`) is the pattern — a
real person, credited by name, with every unauthored row omitted; see
[`references/conversation-cards.md`](references/conversation-cards.md). Rows
the owner has not written are **omitted, never invented** — nothing fills
them, not lorem, not a plausible line, not a row borrowed from another
identity. What the owner has not yet decided is recorded in the manifest's
`unresolved` list and the `python3 tools/placeholder.py list` punch list, so
the gap is tracked rather than papered over.

Placeholder machinery otherwise remains for undecided ensemble casting and
unwritten prose; it is never a fallback for an established real identity. A
fixed-manifest regression test for a plate compares the complete literal
entry — timing, provenance, and chrome flags — so omitted or extra fields
cannot drift past the closed field set.

### The GitHub login is the identity, not the name

Owner, on finding the show inconsistent: *"all of the nameplates are
inconsistent all over the show, ensure that people have proper nameplates
(github is the source of truth) and assign proper metadata."*

A binding's `github:` is what a plate resolves a person by, because a login is
verifiable and a display name is not. `vocab/casting.yaml` carries the scar:
`github.com/nimbatus` is an unrelated empty account while Laura Santamaria is
`nimbinatus`, so binding her by the character string would have put a
stranger's face on her credit.

No login means the crest stands in and the gap is recorded — the correct
outcome, and where `preethi` and Karena sit today. `github: null` with *"not
an agent's to guess"* beside it is a decision already taken.

### Dialogue the owner re-sequenced

For owner-sequenced dialogue around a freeze, derive every window from the
picture builder's evidenced constants, keep each card at `MIN_HOLD`, and
regenerate the manifest; never hand-edit a generated plate clock. When review
splits a cue, pin each authored `(start_sec, end_sec, character)` tuple and its
hundredth-second adjacency in focused tests. If review notes use a programme
baseline, record the programme mark beside its baseline act film and source
anchors, then derive the post-insert film time from the timeline shift. A
source-attached cue must still resolve to the evidenced picture — including a
held frame — not merely retain a stale film number. An external insert and its
surrounding held frame are separate half-open intervals: raise inside the
insert, and resolve the hold to its exact `source_at`.

### Cinematic text that shares the frame with identity plates

Owner-authored narration uses `kind: caption` in the top-safe rail while
Guardian and companion cards keep the lower third. Scene-setting metadata uses
`kind: context` above that lane; a full-screen deployment beat uses
`kind: warning`. These are independent chrome rows, not extra nameplate fields,
and each carries `copy_source: owner_supplied`. A caption's `glyphs` record
replaces a mark without changing its authored `text`; the renderer reserves the
mark's real width before wrapping or centering, and a missing mark degrades to
the plain authored letter. See
[`references/conversation-cards.md`](references/conversation-cards.md).

When one movement derivative burns more than one authored block,
`ending_derivative.overlay_section` may be an ordered list, flattened in order
into one encode from the original source. Do not make one derivative per section
or re-encode the clean movement: FFmpeg documents a cascading complex overlay graph;
provenance: `/websites/ffmpeg_documentation`, “Cascading Multiple Overlays” (verified
through Context7).

Local additions to the deck's shape are chrome and placement only:
`kind: ghost`, `variant`, `avatar`, `wreath`, group rows, and the `raised` /
`status` placements. Their rules live in
[`references/plate-chrome.md`](references/plate-chrome.md),
[`references/placement-and-styling.md`](references/placement-and-styling.md),
and [`references/full-frame-cards.md`](references/full-frame-cards.md). A brand
mark comes from the project's own site, never `/usr/share/pixmaps`. If a plate
genuinely needs a new line, add the field to the data model deliberately.

**Do not add a line the deck has no field for.** An invented row — an
`AS <CHARACTER>` line, a role, a pronoun — puts unauthored text on a card whose
entire purpose is naming real people.

## Ending cards

The ending manifest's pause cards use the existing title-card renderer. A pause
card may carry an optional, non-empty `subtitle`; render it as a smaller line
below the title, not as a new generic card configuration. The renderer passes
the manifest card ID to `ending.html`, which uses `body[data-card-id="..."]` for
small, authored exceptions such as a larger mission title or an optical
translation around artwork. Keep those selectors ID-specific; do not add a
manifest-wide offset abstraction.

The underwater coda remains one ordered overlay section. Add a new card to both
`underwater.plate_ids` and `plates`, keep its half-open window inside the
measured movement, and preserve the existing centered treatment when the copy
belongs with the centered closing cards. Both counts are pinned by
`schema/ending-cards.schema.json`, so a new card is a two-file change.

## Prose that is not written yet is lorem, never a gap

A chat pill with no `text` does **not** block and does not render empty:
`tools/placeholder.py` fills it with deterministic lorem ipsum, so timing,
seat and read length are reviewable while the copy is still being written.
`python3 tools/placeholder.py list` is the punch list.

**Copy that is written but cannot be read in the time it is up is the same gap
one step later.** `dur` is authored by hand and nothing derives it from the
words, so a four-character pill and a ninety-character one can both sit up for
1.2 seconds. `python3 tools/readtime.py` lists every plate held shorter than
its own copy needs, separating the ones under `plate.py`'s 2.2s floor from the
ones that clear the floor and are still too fast to read.

It **reports and never re-times**. Widening a hold shoves whatever is seated
after it, and moving an authored beat is the owner's call — so the default
exits 0, and `--check` is only for whoever is gating a final cut.

**The one short-hold exception is owner-pinned and measured.** A standalone
placement the owner pinned may carry a hold shorter than the standard floor
only when all three hold: no standard-length window exists near the requested
seat, the actual static-renderer interval (`source_at` through
`source_at + dur` — the standalone path has no lead-in/tail-out envelope) is
measured wholly inside supported picture, and a literal regression test pins
the exception. It does not generalize: normal film plates through `plan` keep
the standard floor.

**A placeholder credits nobody** — the vocab's uncast speaker (`TBD`) and the
drawn crest, never a real login or somebody's avatar; the intended speaker is
kept in `speaker_pending`. Lorem under a real name is still putting words in a
colleague's mouth, and act IV lost three people to exactly that. Details and
the named-badge distinction:
[`references/conversation-cards.md`](references/conversation-cards.md).

## Core Process

```bash
python3 tools/ensemble.py roster --month YYYY-MM --out roster.json
python3 tools/plate.py plan cut.json --roster roster.json --max-shot-sec 9 \
    --out plates.json
python3 tools/plate.py burn --video renders/cut.mp4 --manifest plates.json \
    --out renders/cut-plated.mp4
```

A dense schedule must still end in **one picture encode**. If the burn grows to
so many independent still inputs that FFmpeg spends its time building scaler
graphs instead of emitting frames, composite the already-rendered full-frame
RGBA plates at their manifest boundaries into one alpha-preserving overlay
stream, then overlay that stream onto the clean act once. Do not split the deck
across successive lossy burns. FFmpeg's `overlay` filter supports `straight`,
`premultiplied`, and `auto` alpha handling; provenance:
`/websites/ffmpeg_documentation`, “overlay” (verified through Context7).

`plan` reads copy from `vocab/casting.yaml`'s `plate:` block — the same file
that binds a character to a person — so recasting a role changes the on-screen
credit and nothing else.

## Where the detail lives

This skill is the contract. The procedure lives in `references/`:

| Reference | What is in it |
|---|---|
| [`copy-authoring.md`](references/copy-authoring.md) | **Read before writing copy.** The authored identities, their source files, and the known divergences. |
| [`from-a-brief.md`](references/from-a-brief.md) | Issue `brief` block → roster → planned manifest → burned cut, the ordering rules, and `gp_*` placement data. |
| [`conversation-cards.md`](references/conversation-cards.md) | `chat`, `status`, `miniboss`, `achievement`, and `companion` cards; censors, caption glyphs, and placeholders. |
| [`placement-and-styling.md`](references/placement-and-styling.md) | Letterbox-safe placement and the treatment's provenance. |
| [`plate-chrome.md`](references/plate-chrome.md) | `avatar`, `wreath`, variants, Ghost handling, and brand-mark rules. |
| [`plate-styling.md`](references/plate-styling.md) | Constant-by-constant CSS provenance and the font trap. |
| [`status-nameplate.md`](references/status-nameplate.md) | The top-of-frame HUD card. |
| [`other-cards.md`](references/other-cards.md) | `miniboss`, `achievement`, and `companion` detail. |
| [`full-frame-cards.md`](references/full-frame-cards.md) | `act` and `comic` cards, rendered by the site's own CSS; moving-picture contrast and finite overlays. |
| [`hero-credit.md`](references/hero-credit.md) | Act VIII's cast placard — a lower third that credits the person, not the character. |
| [`binding-conflicts.md`](references/binding-conflicts.md) | What to do when authored card copy must deliberately diverge from a committed binding. |

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "One extra line makes the plate clearer." | It makes the plate say something nobody wrote. The deck's fields are the contract. |
| "I'll hardcode the copy just for this render." | Then the credit and the casting drift apart the first time a role is recast. Copy lives in `vocab/casting.yaml` — or, for someone the vocab does not bind yet, in the issue's brief, which `plan` marks `copy_source: brief`. |
| "The brief's copy contradicts the binding, but the owner wrote it today." | Recency is not authority: the vocab is the reviewed record, the issue body is editable. The vocab wins; edit it if the brief is right. |
| "I'll hand-author the manifest, so `plan`'s rules don't apply." | They still apply — `plan` was just the only thing enforcing them. `render` and `burn` now run `check_copy_against_bindings`, and a card contradicting its binding is refused unless it carries a `copy_override` naming the deciding issue. |
| "The plate is short, it can share the screen." | Two plates at once is unreadable; both `plan` and `burn` refuse it. The only exception is a group row, whose members are built to be seen together. |
| "The shot is only two seconds, so nobody can be plated there." | The plate rides across the cut. Only the *anchor* must be long enough to register. |
| "I'll put a plausible name on the placeholder so it looks finished." | A plate names a real person. `TBD` is the honest answer until a roster exists. |
| "No copy for this lead? Write them something." | Then the plate says what nobody wrote. Leave them in `unresolved` until the owner writes it. |
| "Their GitHub handle is probably their name — I'll set `github:` to that." | A login is verifiable; a guess resolves to whoever holds the handle. `github.com/nimbatus` is a stranger's empty account, and Laura Santamaria is `nimbinatus`. Leave it null and let the crest stand in. |

## Red Flags

- Inventing a plate line, a role, or a pronoun row.
- Hardcoding copy in the manifest instead of `vocab/casting.yaml`.
- A plate manifest that hides where its copy came from; every planned entry
  needs `copy_source`, and a brief plate without it is a hand-edit.
- Letting a brief override a binding's `plate:` block silently. The vocab wins;
  if the brief is right, fix the vocab.
- Calling a burn done because ffmpeg exited 0. Check a frame, not the manifest.
- Guessing a pill's seat when the manifest's clock is in doubt. Omission
  degrades; misplacement lies. Never ship the old master instead: stale copy is
  the same fault with an older timestamp.
- Using a freeze-frame or looped source frame to make an old plate seat fit.
  Re-seat the plate on the evidenced source frame in its generator; leave the
  picture unchanged, and let a short shot carry the plate across its cut.
- A looped still overlaid on a finite picture without a bound. Trim the still
  to the picture's length and add `shortest=1`.
- Shipping a cut with a non-empty `unresolved` list without reading it. An empty
  list means nobody was missed; an omission it does not report is a `plan` bug,
  not a gap to work around.
- Deck-grey text over moving picture without measuring its full window with
  `signalstats` → `YAVG`, or readability protection that adds a scrim panel
  instead of protecting the glyphs. See
  [`references/full-frame-cards.md`](references/full-frame-cards.md).
- Planning with a different `--max-shot-sec` than the render used.
- A subclass line on a Ghost.
- A plate rendered in anything but DejaVu Sans Mono.
- Styling taken from the live site where the baked reveal disagrees.
- A full-frame card re-implemented in Python instead of rendered from the
  site's CSS.
- Falling back to `Bluefin Blueberry` for somebody whose Guardian identity is
  already authored.
- A plate positioned against the frame on a letterboxed source, so it lands on
  the black bar instead of the picture.
- A placeholder plate carrying anything but the vocab's uncast copy, or
  shipping alongside a real roster.

## Verification

```bash
python3 -m pytest -q tests/test_plate.py     # includes the closed-vocabulary test
python3 -m pytest -q tests/test_derive.py    # pins every authored plate verbatim

# diff every binding against the file that authored it (read-only) --
# the snippet lives in references/plate-styling.md, "Checking a binding for drift"

# eyeball a plate inside its window
ffmpeg -ss <at+1> -i renders/cut-plated.mp4 -frames:v 1 renders/verify-plate.jpg
```
