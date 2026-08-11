---
name: casting
version: "1.0"
last_updated: "2026-08-11"
id: casting
one_line_purpose: Bind a Destiny character to a person and credit the monthly ensemble.
entry_point: docs/skills/casting.md
category: indexing
mcp_compliance_level: partial
optimization_status: draft
status: active
dependencies: [indexing]
tags: [casting, vocab, ensemble, leads, contributors]
description: >-
  Covers lead bindings, ensemble slots, and how casting is derived rather than
  tagged. Use when adding or changing a cast member, crediting contributors, or
  debugging a casting role that did not derive.
metadata:
  type: reference
---

# Casting

Casting names **real people**. Every rule below exists because the cost of
getting it wrong is crediting someone for a shot they are not in.

## When to Use

- Adding, changing or removing a lead binding in `vocab/casting.yaml`
- Crediting a month's Project Bluefin contributors
- A shot shows a character but `casting.role` did not derive as `lead`

## When NOT to Use

- Rendering the credit on screen → [`plates.md`](plates.md)
- Tagging what is visible in a frame → [`indexing.md`](indexing.md)

## Core Process

Two tiers, and the difference between them is the whole model:

- **Lead** — a named Destiny character bound 1:1 to one person, fixed for the
  life of the project. Most bindings are unconstrained: naming a role does not
  require a lookalike.
- **Ensemble** — every anonymous Guardian is a *slot*, filled from a rotating
  monthly pool of contributors. `casting.person` is always `null` on an ensemble
  segment, because people are assigned per month and a re-roll must not
  invalidate a tagged segment.

### Adding a binding

Edit `vocab/casting.yaml` under `leads.values`, then make it queryable — a
binding nobody can search for is a binding that does not exist, and a test
enforces exactly that:

1. `vocab/casting.yaml`: `person`, `display_name`, `aka`, optional
   `constraints`, optional `plate` copy.
2. `tools/search.py` `PHRASES`: at least one phrase for the character and one
   for the person.
3. Docs: the cast table in `README.md` and the bindings table in
   `docs/taxonomy.md`.
4. `python3 tools/rederive.py` — the checked-in segments still carry the old
   casting until it is run. Renaming a person is five places, not four.

`constraints` (`require_helmet`, `require_far`) exist only where the project
wants the figure to read as the character rather than as the person — currently
one binding, `saladin` → `jeefy`. A violating shot derives `usable = false` with
the reasons in `constraints_failed` and is excluded from that character's
retrieval.

Not every binding is a Guardian: `sagira` is a Ghost, so framing and helmet
questions do not apply and her nameplate carries no subclass line.

### Re-casting the index after a vocab edit

`casting` is a pure function of the tagger's `character` list plus this vocab,
so a vocab edit re-casts the whole index **without re-tagging** — but the
checked-in segments still carry the old value until something recomputes them.
The only writer used to be `tools/annotate.py index`, which needs the source
video, and `media/` is gitignored. So a rename left every segment stale with no
runnable remedy.

`tools/rederive.py` is that remedy. It recomputes every derived field from the
fields the record already carries — no video, no keyframes, no model:

```bash
python3 tools/rederive.py --check    # report drift, change nothing, exit 1
python3 tools/rederive.py            # rewrite the drifted segments
```

It reports each change, so a vocab edit's blast radius is visible before it is
committed:

```text
seg_yt_..._0027-0029.json
    casting.person: 'karena_angel' -> 'karena_angell'
```

This is not a licence to edit a derived field by hand. It is the opposite: the
one supported way to make the files agree with the vocab again, which is why it
refuses to touch a tagger field and preserves each file's existing JSON layout
so the diff shows the change and nothing else.

### Ensemble

```bash
python3 tools/ensemble.py roster --month YYYY-MM --out roster.json
python3 tools/ensemble.py assign --roster roster.json --shotlist cut.json
```

Assignment is a round-robin over a **month-seeded rotation** of the sorted
roster, so the same (month, roster, shot list) always produces the same tiles.
"Random contributor" therefore means *rotated*, never *reshuffled per run* — a
re-render must not re-credit a different person.

Slots are a pure function of the tags, never hand-set: `crowd` → 6, `group` or
`crowd_group` salience → 3, otherwise 1.

On-screen credit copy lives beside the casting decision in `vocab/casting.yaml`:
the generic ensemble copy under `ensemble.plate`, and — under `ensemble.titles`,
keyed by GitHub login — the Guardian identity of any contributor whose plate is
genuinely authored in the reference deck (castrojo's is `np_jorge`). Most
contributors have no entry: an unknown seal is `Bluefin Blueberry`, never an
invented title. [`plates.md`](plates.md) covers how the two are scheduled.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "It's probably them — same armor, two shots earlier." | A wrong tag credits a real person for a shot they are not in. Omit rather than guess. |
| "I'll tag `casting` directly, it's faster." | It is derived. A hand-set value is overwritten and hides the vocab bug that made you reach for it. |
| "The search phrase can come later." | A binding nobody can query does not exist, and the suite fails on it. |
| "Re-rolling the roster is fine, it's only credits." | Assignment is deterministic on purpose: a re-render must not re-credit a different person. |

## Red Flags

- Setting `casting` in a tagger. It is derived by `tools/derive.py` from the
  `character` list plus `vocab/casting.yaml`, so a vocab edit re-casts the whole
  index with no re-tagging.
- Naming a character who is not clearly visible in the frame, or inferring one
  from the shots around it.
- Adding a binding without a search phrase (the suite fails), or leaving a
  phrase behind after removing one (the suite fails the other way too).
- Treating `substitutability` as a usability gate. It was demoted: it only
  tie-breaks between otherwise-equal ensemble shots.

## Verification

```bash
# every binding is queryable, both directions
python3 -m pytest -q tests/test_search.py tests/test_derive.py

# what derived for one video
python3 - <<'PY'
import json, glob
for p in sorted(glob.glob('segments/*<video_id>*.json')):
    s = json.load(open(p)); c = s.get('casting') or {}
    if c.get('role') == 'lead':
        print(s['start_tc'], c['character'], c['person'], 'usable=', c['usable'])
PY
```

The full casting model, including why it is inverted (the crowd is the cast), is
in `docs/taxonomy.md`.
