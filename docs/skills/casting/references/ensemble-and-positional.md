# The ensemble, positional casting, and authored identities

Part of the [casting skill](../SKILL.md).

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
invented title. [`plates.md`](../../plates/SKILL.md) covers how the two are scheduled.

### Authored identities are reproduced, not written

Ten people have a Guardian identity somebody actually authored, in files this
repo does not own — `~/Videos/nameplates.json` and, for seven of them,
`~/src/website public/wolves/characters/characters.json`. The roster and the
precedence between those sources are in
[`copy-authoring.md`](../../plates/references/copy-authoring.md#where-plate-copy-is-authored). Two consequences here:

- **Copying an authored identity onto an existing binding is reproduction**, and
  is allowed without asking — verbatim, with the source cited in a comment, as
  `elsie_bray` (Laura Santamaria) and `saint_14` (Kat Cosgrove) do.
- **Binding a new person is still a casting decision**, and stays the owner's.
  An authored plate says who somebody *is*; it does not say which Destiny
  character they play. Kaslin Fields, Christoph Blecker and Natali Vlatko have
  authored identities and no binding here, and that is a question for an
  issue, not an edit.

An authored identity also does not travel between tiers on its own: a person
cast as a **lead** is excluded from the ensemble pool entirely, so their copy
belongs on the lead binding and nowhere else.
