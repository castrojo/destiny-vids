---
name: casting
version: "1.2"
last_updated: "2026-08-12"
id: casting
one_line_purpose: Bind a Destiny character to a person and credit the monthly ensemble.
entry_point: docs/skills/casting.md
category: indexing
mcp_compliance_level: partial
optimization_status: draft
status: active
dependencies: [indexing]
tags: [casting, vocab, ensemble, leads, contributors, depiction]
description: >-
  Covers lead bindings, ensemble slots, depiction rules, and derived casting.
  Use when adding a cast member, crediting contributors, recording a rule for how a character may be shown, or debugging a casting role.
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

### Plate-only people

A person can carry owner-written nameplate copy and still have no binding here,
and that is a **terminal state, not a gap**. A `leads` binding is for someone who
*recurs*: it fixes their credit across every cut for the life of the project. A
one-video credit belongs in the copy the owner wrote for that video, and adding a
binding for it would claim a permanence nobody asked for.

Nothing in this repo can tell the two apart, so nothing in this repo tries —
`automatable: no`, blocked on an owner decision. The open ones (see
castrojo/destiny-vids#1 for the copy itself; do not transcribe it, it has one
home):

| Person | State | Blocked on |
|---|---|---|
| Paris Pittman | Cast, as `iron_lord_red_haired` — but the binding has no `plate:`, and the copy the owner wrote is a Guardian plate for Paris, not copy for an Iron Lord. | Authoring plate copy for the character, or deciding she stays plate-only. |
| Jeffrey Sica | Not cast, not in the index. Plate-only. | Whether he is recurring cast (add a binding) or a one-video credit (nothing to do). |

Neither blocks anything. A cast-but-unplated lead like Paris still makes the cut:
`tools/plate.py plan` writes the manifest and lists her under `unresolved` with
the reason, so the credit is never dropped in silence — see
[`plates.md`](plates.md). Someone with no binding at all is not in the index's
casting, and the brief that carries their copy is their punch-list.

### When the character is not known yet

A request often arrives the other way round: here is a person, and here is a
figure on screen — "the woman", "the main character". Turning that into a
Destiny character is a **visual judgment** on the footage, and it is not
available at all when the source video is not indexed. Park it in
`leads.pending` rather than guessing:

```yaml
  pending:
    <github-handle>:
      github: <github-handle>
      described_as: Woman        # the requester's words, never a character name
      automatable: no
      blocked_on: >
        The source video is not ingested, so no indexed shot shows this figure.
```

Derivation never reads `pending` (`load_leads` reads only `leads.values`), so a
pending entry casts nobody, plates nothing and needs no search phrase — it is a
queue, not a binding. It surfaces in exactly two places, per the contract's
"record the gap where the next person will trip over it": the vocab file itself,
beside the bindings, and the requester's GitHub issue, which stays open as the
punch-list (the live example is castrojo/destiny-vids#14, three logins and an
un-ingested video). `tests/test_casting_pending.py` pins the queue so it cannot
be silently dropped. Promoting an entry is an ordinary binding: move it under
its character key in `values`, add the search phrases, and run the checklist
above.

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

### When the owner says who is where, round-robin cannot help

Rotation answers *"who fills the anonymous slots"*. It cannot answer **"which
body is this named person"** — and when the owner says so, that is the only
question that matters:

> "0:55 left to right, Joseph Sandoval, Ricardo from CERN, Karena Angel"

`vocab/casting.yaml` holds the **copy** and `tools/ensemble.py` holds the
**rotation**; neither holds a binding from a person to a shot. Do not make
rotation approximate one — it would put a real person's name on whichever body
the seed happened to land on, which is rule 3 broken by machinery rather than by
guessing.

**Positional casting is authored, once, in a per-cut builder** that emits a
plate manifest. `scripts/build_efmb_plates.py` is the worked example: the
person→shot bindings are the only hand-written thing in it, the copy is read
verbatim from this file, and every window is derived. Three rules it earns:

- **Bind to SOURCE timecodes, never film time.** Every mark an owner gives is a
  film timecode, and the film moves under it — act II's head lead went
  8.564 → 10.650 s, so every one of his marks shifted by 0.364 to 2.131 s.
  Source time is a position in a file that has not changed.
- **A missing copy key must raise**, never fall back to the generic blueberry
  plate: the fallback silently overwrites an identity the owner authored.
- **Never credit one person twice with two different faces.** Exclude leads
  (they are credited where their character is) *and* anyone already carrying a
  named placeholder badge, or the roster hands them a second, generic plate.

Anyone the owner **named** but wrote no plate for gets a **named placeholder**:
their name, the neutral eyebrow, and no invented rows. That is the "missing, so
omit and record" case, and it is the opposite of composing the words to fill it.

On-screen credit copy lives beside the casting decision in `vocab/casting.yaml`:
the generic ensemble copy under `ensemble.plate`, and — under `ensemble.titles`,
keyed by GitHub login — the Guardian identity of any contributor whose plate is
genuinely authored in the reference deck (castrojo's is `np_jorge`). Most
contributors have no entry: an unknown seal is `Bluefin Blueberry`, never an
invented title. [`plates.md`](plates.md) covers how the two are scheduled.

### Authored identities are reproduced, not written

Ten people have a Guardian identity somebody actually authored, in files this
repo does not own — `~/Videos/nameplates.json` and, for seven of them,
`~/src/website public/wolves/characters/characters.json`. The roster and the
precedence between those sources are in
[`plates.md`](plates.md#where-the-copy-is-authored). Two consequences here:

- **Copying an authored identity onto an existing binding is reproduction**, and
  is allowed without asking — verbatim, with the source cited in a comment, as
  `elsie_bray` (Laura Santamaria) and `saint_14` (Kat Cosgrove) do.
- **Binding a new person is still a casting decision**, and stays the owner's.
  An authored plate says who somebody *is*; it does not say which Destiny
  character they play. Kaslin Fields, Christoph Blecker, Natali Vlatko and
  Doctor Andy Anderson have authored identities and no binding here, and that
  is a question for an issue, not an edit.

An authored identity also does not travel between tiers on its own: a person
cast as a **lead** is excluded from the ensemble pool entirely, so their copy
belongs on the lead binding and nowhere else.

## A binding can carry a depiction rule

Casting says *who* a figure is. A **depiction rule** says how a character may be
shown at all, and it applies whether or not anybody is cast as them.

The Witness is the standing example:

```yaml
the_witness:
  person: null
  aka: [witness]
  depiction:
    rule: eyes_or_smoke_only
    approved: []
```

> Eyes or smoke, never the body.

Three properties make it work, and all three are deliberate:

- **The default is exclusion.** An empty `approved` means *no* shots of that
  character are usable, exactly like an untagged `overlays` deriving
  `clean = false`. Permission is positively established or it does not exist.
- **It is not derived.** `clean`, `footage_tier`, `traversal_hero` and `casting`
  are the four derived fields and this is not a fifth. "Is that a body or a
  wisp?" is a visual judgement about a frame, which
  [`AGENTS.md`](../../AGENTS.md) lists among the things that can never be
  automated. A human adds a `segment_id` to `approved` after looking at it.
- **A rule is not an editorial choice.** "Cut Savathûn from this video" belongs
  in the outline for that video. "The Witness is never shown bodily" belongs
  here, because it holds for every cut the project ever makes. Putting the
  first one here would quietly ban a character from the whole index; putting the
  second in an outline loses it the moment somebody writes a new one.

The mechanism is generic — any binding may carry `depiction` — while the rules
themselves are specific and few. Add one only when the owner states it as a rule
about the character, not as a note about one cut.

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
