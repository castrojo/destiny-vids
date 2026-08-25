---
name: megacut
version: "1.0"
last_updated: "2026-08-19"
id: megacut
one_line_purpose: Assemble finished acts into the canonical programme without re-editing them.
entry_point: docs/skills/megacut/SKILL.md
category: media-production
status: active
dependencies: []
tags:
  - programme
  - assembly
  - cards
  - joins
  - delivery
description: >-
  Assemble finished acts into the canonical programme without re-editing them.
  Use when joining delivered cuts into one continuous video and verifying the
  joins.
metadata:
  type: procedure
---

# Assembling a programme

## When to Use

- Several finished cuts must play as one continuous video
- A compilation needs chapter cards between its parts
- Reproducing a running order that is authored somewhere else (the website's
  intro sequence, a playlist) — though **this show's order is authored here**,
  in [`../../running-order.md`](../../running-order.md)

## When NOT to Use

- Building a cut from indexed shots → [`editing`](../editing/SKILL.md)
- Putting names on people → [`plates`](../plates/SKILL.md)
- Delivering a finished file → [`production`](../production/SKILL.md)

## Assembly is not editing

This stage **joins finished things**. It never re-cuts, re-times or re-grades
one. Every item it is handed is either a rendered cut from this repo or an
owner-approved deliverable, and if one of them is wrong the fix belongs
upstream, in the thing that made it — not here.

That boundary is what makes the tool safe to re-run: the programme is a
**regenerated artifact**, so it is rebuilt rather than patched, exactly like
every other render in this repo.

**One sanctioned exception, and it proves the rule:** `trim_to` lets the
programme end a delivered act early. It is not editing, because the act's own
file is never touched — the cut lives in the plan, where it is read, tested
and reverted like any other number. Anything more than "stop here" still
belongs upstream.

## It joins finished things — and checks they are still finished

"Finished" was taken on trust: the tool resolved a path, found a file, and
encoded it. Nothing asked whether that file was still the act its records
describe, so an edited record with no rebuild shipped silently in the next
programme — and the assembly stage is the one place where that reaches an
audience.

So it checks, and reports. Before encoding, every seated clip is matched to its
act (by **inode**, since `Prod/` entries are hardlinks to the declared masters)
and checked against `stories/megacut/delivery.json`. An act whose master
predates its own committed inputs is **named on stderr and seated anyway** —
assembly reports stale acts; it never refuses one (`AGENTS.md`, *Nothing blocks
a release*).

```bash
python3 tools/deliver.py status --sources-only   # what moved, per act
python3 tools/deliver.py build                   # rebuild exactly what is stale
python3 tools/megacut.py <plan>                  # always assembles; stale acts
                                                 # are named on stderr, never refused
```

This is not editing policy leaking downstream: the fix still belongs upstream,
in the act. The report keeps assembly from *silently pretending* the upstream
fix happened; it never withholds the programme over one.

## Core Process

```bash
# 1a. Chapter cards, deck format (title / subtitle / body): a Python plate
python3 tools/plate.py render --manifest stories/<name>/<name>-cards.json \
    --out-dir renders/plates-<name>-cards

# 1b. Full-frame cards (`kind: act`, `kind: comic`): the site's own CSS in a
#     real browser. Do not port one into Pillow.
ln -sfn ~/src/website/node_modules node_modules
node cards/render-cards.mjs --manifest stories/<name>/<name>-cards.json \
    --out-dir renders/plates-<name>-cards

# 2. Check the graph before paying for the encode
python3 tools/megacut.py stories/<name>/<name>.json --dry-run

# 3. Assemble (the encodes run on the farm by default; --local forces this
#    host, memory-capped)
python3 tools/megacut.py stories/<name>/<name>.json

# 4. Measure the joins on the built file
python3 tools/transitions.py stories/<name>/<name>.json --measure <built>.mp4
```

Both renderers write `plate_<id>.png` into the same directory and each skips
what the other owns, so a manifest may mix them and `burn` still reads one
plates-dir without caring which tool drew which file.

## Where the detail lives

This skill is the contract. The procedure lives in `references/`:

| Reference | What is in it |
|---|---|
| [`cards.md`](references/cards.md) | Full-frame cards from the site's CSS, the plan's two item kinds, and why `audio` has no default. |
| [`assembly-graph.md`](references/assembly-graph.md) | Segments-then-join, the `filter_complex` deadlock it replaced, the `-vf` vs `-filter_complex` trap, and conform rules. |
| [`joins.md`](references/joins.md) | Where two finished things touch: silent joins, `trim_to`, holds, and measuring the premise rather than the number. |
| [`delivery.md`](references/delivery.md) | Delivering the finished programme into `~/Videos/Wolves/Prod/` and the owner decision about duplicate publication. |
| [`verification.md`](references/verification.md) | The manual probes: slide placement, duration proofs, silent-stretch checks, and frame-by-frame join inspection. |

## Red Flags

- **An item that plays before act I does not get act I's numeral.** The
  prologue is `0`; do not renumber the show to make room at the front.
- **A silent segment's two legs must be equal by construction.** Probe the
  video stream, not the container, and pin both legs to one number.
- **Validation and encoding must resolve a path the same way.** The file that
  was validated must be the file that ships.
- **`-color_primaries` alone does not tag the file.** Use
  `tools/conform.py:video_encode_args` and verify the output with `ffprobe`.
- **Don't re-encode an act that already conforms.** `tools/conform.py` owns the
  delivery spec and the conform cache.
- **A card is a transparent PNG.** Flatten it onto real black with `overlay`;
  do not rely on pixel format conversion to drop alpha safely.
- **"Drop the audio" is not the same as "mute it".** A dialogue-free music
  choice is a different source or a different edit, never silence.
- **When a segment's audio is a fraction short of its picture, pad it** with
  `apad` and let the picture decide the length. Cutting to the shorter stream
  drops a frame and, in a concat, drifts everything after it.
- **Never assume an anchor measured on a different upload.** Two uploads of the
  same cinematic can differ by seconds.
- **Never hand-edit the assembled file.** Fix the plan or the upstream cut and
  re-run.
- **Chapter card copy is reproduced, never authored.** A card whose words
  nobody wrote is omitted and recorded, not invented.
- **A card that exists on the site is not re-implemented.** Render it from the
  site's CSS with `cards/render-cards.mjs`.
- **A fade is for a join into or out of silence.** Where music meets music, a
  `fade_out` meeting a `fade_in` makes the hole you were trying to hide.
- **Assembly may shorten an act only with `trim_to`, never with `dur`.**
- **A reported lost card is recovered from records, not guessed.** Search every
  worktree, restore the whole authored object, then rebuild.

## Verification

Logs that say `wrote …` prove nothing. At minimum:

```bash
python3 tools/transitions.py stories/<name>/<name>.json --measure <built>.mp4
ffmpeg -v error -xerror -i <built>.mp4 -f null -
```

Checklist:

- [ ] programme duration equals the plan's arithmetic
- [ ] every act slide lands where the plan says
- [ ] extract frames either side of every join and look at them
- [ ] per-segment peaks and silent stretches were checked where the brief cares

Use [`references/verification.md`](references/verification.md) for the detailed
slide-matching, `volumedetect`, and silence-floor probes.
