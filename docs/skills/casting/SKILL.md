# Casting

Casting names **real people**. Every rule below exists because the cost of
getting it wrong is crediting someone for a shot they are not in.

## When to Use

- Adding, changing or removing a lead binding in `vocab/casting.yaml`
- Crediting a month's Project Bluefin contributors
- A shot shows a character but `casting.role` did not derive as `lead`

## When NOT to Use

- Rendering the credit on screen → [`plates.md`](../plates/SKILL.md)
- Tagging what is visible in a frame → [`indexing.md`](../indexing.md)

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

## Where the detail lives

This skill is the contract. The procedure lives in `references/`:

| Reference | What is in it |
|---|---|
| [`rederive-and-pending.md`](references/rederive-and-pending.md) | Re-casting the index after a vocab edit (`tools/rederive.py`), plate-only people, and the `leads.pending` queue for when the character is not known yet. |
| [`ensemble-and-positional.md`](references/ensemble-and-positional.md) | The month-seeded rotation, owner-authored positional casting in a per-cut builder, and reproducing authored Guardian identities. |
| [`depiction-rules.md`](references/depiction-rules.md) | How a binding carries a rule about how a character may be shown at all — the Witness's `eyes_or_smoke_only` is the standing example. |

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "It's probably them — same armor, two shots earlier." | A wrong tag credits a real person for a shot they are not in. Omit rather than guess. |
| "Their Guardian identity is authored, so they're basically cast." | Two different claims. Reproduce the identity; leave the binding to the owner. |
| "I'll tag `casting` directly, it's faster." | It is derived. A hand-set value is overwritten and hides the vocab bug that made you reach for it. |
| "The search phrase can come later." | A binding nobody can query does not exist, and the suite fails on it. |
| "Re-rolling the roster is fine, it's only credits." | Assignment is deterministic on purpose: a re-render must not re-credit a different person. |
| "They have plate copy, so bind them — it's only a credit." | A binding says they recur, for the life of the project. Whether it's that or a one-video credit is the owner's call; the punch-list asks. |
| "I can't see the video, but the description narrows it to one character." | Then park it in `leads.pending`. A binding is a claim about a real person; a queue entry is not. |
| "The owner only said it about this one video, so it's an outline note." | Ask which object it is about. "Cut her from this cut" is editorial; "never show its body" is a rule about the character and belongs on the binding. |
| "The allow-list is empty, so the rule isn't doing anything yet." | Empty means *exclude everything*, which is the rule at full strength. It is doing all of its work. |
| "A refresh flag only re-fetches, so it is safe to run." | Check what else it rewrites. A snapshot command that also re-derives the CAST throws the owner's curated names away silently — the derivation is not the credit. |
| "GitLab gives me a name and an email, so I have both." | Take the name. An email is somebody's contact detail, not copy, and a credit roll harvested into a committed manifest is the wrong place for hundreds of them. |
| "I'll bracket the handle like the others in that run." | `[ name ]` is the placeholder marker here. Somebody wearing brackets wears them because the owner chose it; a new credit gets the login plain. |

## Two ways a credit dies quietly

**Derivation overwriting authored copy.** A credit list is authored once and is
copy from then on: the owner decides how a real person is named. Any command
that can rewrite it needs its own flag, and the default must be to leave it
alone. Regenerating a cast because you asked for a *contributor* snapshot is
data loss with a clean exit code.

**Reaching for a name the platform did not verify.** A GitHub login resolves to
an account somebody controls; a GitLab commit-author name does not resolve to
anything, so it carries no face. Credit the name and let the portrait degrade
to the ring — never fetch `github.com/<that name>.png`, which returns whichever
stranger happens to hold the handle.

## Red Flags

- Setting `casting` in a tagger. It is derived by `tools/derive.py` from the
  `character` list plus `vocab/casting.yaml`, so a vocab edit re-casts the whole
  index with no re-tagging.
- Naming a character who is not clearly visible in the frame, or inferring one
  from the shots around it.
- Adding a binding without a search phrase (the suite fails), or leaving a
  phrase behind after removing one (the suite fails the other way too).
- Casting someone because they turned up in a brief with plate copy. Copy is a
  credit for one video; a binding is a claim that they recur.
- A snapshot or refresh command that rewrites authored credit copy as a side
  effect, rather than behind its own flag.
- A contributor's face fetched from a platform that never issued them a handle.
- Treating `substitutability` as a usability gate. It was demoted: it only
  tie-breaks between otherwise-equal ensemble shots.
- Widening a `depiction.rule` to a new value, or adding keys to the block, to
  let a shot through. The rule is the gate; the allow-list is the exception.
- Approving a Witness shot from a caption or a midpoint keyframe rather than
  looking at the frames.

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
