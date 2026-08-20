---
name: plates
version: "1.0"
last_updated: "2026-08-19"
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
---

# Guardian nameplates

## When to Use

- Crediting a lead or the monthly ensemble on screen
- Changing plate copy, position, or timing
- Porting the Bluefin plate treatment somewhere new

## When NOT to Use

- Narration captions → the `authoring-video-closed-captions` skill
- Deciding *who* is cast → [`casting`](../casting/SKILL.md)

## The field set is closed

A Guardian nameplate carries **exactly**:

| Field | Example |
|---|---|
| `label` | `TRUSTEE // GUARDIAN` |
| `class` | `Voidwalker Warlock` |
| `name` | `Bob Killen` |
| `title` | `Reconciler of the Plane` |
| `trustee` | `true` — the burnished-silver chrome |

The deck's other authored shapes are the title card (`title`, `subtitle`,
`body[]`) and the **chat card** (`speaker`, `text`) —
[`references/conversation-cards.md`](references/conversation-cards.md).

Keep chat `text` verbatim. When an owner requests a swear censor, use the
Kubernetes helm only as an `o` replacement: add a `censor` entry whose `find`
value occurs exactly once and whose `replace` value uses `{k8s}`.
`tools/plate.py` replaces that token with the cached official white helm; it
does not alter the authored source string.

Cinematic text that shares the frame with identity plates uses its own kinds
(`caption`, `context`, `warning`) and `copy_source: owner_supplied`; these are
independent chrome rows, not extra nameplate fields. When one movement
derivative burns more than one authored block,
`ending_derivative.overlay_section` may be an ordered list, flattened in order
into one encode from the original source.

Local additions to the deck's shape are chrome and placement only:
`kind: ghost`, `variant`, `avatar`, `wreath`, group rows, and the `raised` /
`status` placements. Their rules live in
[`references/plate-chrome.md`](references/plate-chrome.md),
[`references/placement-and-styling.md`](references/placement-and-styling.md),
and [`references/full-frame-cards.md`](references/full-frame-cards.md). A brand
mark comes from the project's own site, never `/usr/share/pixmaps`.

**Do not add a line the deck has no field for.** An invented row — an
`AS <CHARACTER>` line, a role, a pronoun — puts unauthored text on a card whose
entire purpose is naming real people.

## Prose that is not written yet is lorem, never a gap

A chat pill with no `text` does **not** block and does not render empty:
`tools/placeholder.py` fills it with deterministic lorem ipsum, so timing,
seat and read length are reviewable while the copy is still being written.
`python3 tools/placeholder.py list` is the punch list.

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
across successive lossy burns.

`plan` reads copy from `vocab/casting.yaml`'s `plate:` block — the same file
that binds a character to a person — so recasting a role changes the on-screen
credit and nothing else.

## Where the detail lives

This skill is the contract. The procedure lives in `references/`:

| Reference | What is in it |
|---|---|
| [`copy-authoring.md`](references/copy-authoring.md) | **Read before writing copy.** The authored identities, their source files, and the known divergences. |
| [`from-a-brief.md`](references/from-a-brief.md) | Issue `brief` block → roster → planned manifest → burned cut, and the ordering rules. |
| [`conversation-cards.md`](references/conversation-cards.md) | `chat`, `status`, `miniboss`, `achievement`, and `companion` cards, plus placeholder behaviour. |
| [`placement-and-styling.md`](references/placement-and-styling.md) | Letterbox-safe placement and the treatment's provenance. |
| [`plate-chrome.md`](references/plate-chrome.md) | `avatar`, `wreath`, `variant`, Ghost handling, and brand-mark rules. |
| [`plate-styling.md`](references/plate-styling.md) | Constant-by-constant CSS provenance and the font trap. |
| [`status-nameplate.md`](references/status-nameplate.md) | The top-of-frame HUD card. |
| [`other-cards.md`](references/other-cards.md) | `miniboss`, `achievement`, and `companion` detail. |
| [`full-frame-cards.md`](references/full-frame-cards.md) | `act` and `comic` cards, rendered by the site's own CSS. |
| [`hero-credit.md`](references/hero-credit.md) | Act VIII's cast placard — a lower third that credits the person, not the character. |
| [`binding-conflicts.md`](references/binding-conflicts.md) | What to do when authored card copy must deliberately diverge from a committed binding. |

## Red Flags

- Inventing a plate line, a role, or a pronoun row.
- Hardcoding copy in the manifest instead of `vocab/casting.yaml`.
- A plate manifest that hides where its copy came from; every planned entry
  needs `copy_source`.
- Letting a brief override a binding's `plate:` block silently. The vocab wins;
  if the brief is right, fix the vocab.
- Calling a burn done because ffmpeg exited 0. Check a frame, not the manifest.
- Guessing a pill's seat when the manifest's clock is in doubt. Omission
  degrades; misplacement lies.
- A looped still overlaid on a finite picture without a bound. Trim the still
  to the picture's length and add `shortest=1`.
- Shipping a cut with a non-empty `unresolved` list without reading it.
- Planning with a different `--max-shot-sec` than the render used.
- A subclass line on a Ghost.
- A plate rendered in anything but DejaVu Sans Mono.
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
