# Plates from a brief

Reference for [`../SKILL.md`](../SKILL.md). Split out of it to keep the
skill inside its size budget. The end-to-end path from an issue's `brief`
block to a burned cut, including the ensemble roster and the ordering rules.


The exception to "copy lives in `vocab/casting.yaml`" is the owner writing a
plate into an issue's `brief` block (`plates[]` in
[`schema/brief.schema.json`](../../../../schema/brief.schema.json)) — which may name
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

- **The field set is still closed.** `plan` refuses a `copy` key the deck has
  no field for, from a brief same as anywhere else.
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
**A brief plate without `copy_source` is a hand-edit.**

When a committed plate manifest names a generated roster, commit that exact
roster beside the manifest. A path under `renders/` is ignored and a live
roster query changes as contributors land work; neither is reproducible
evidence for a real person's on-screen credit.

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
  that cannot hold a readable row at all falls back to the sequential
  right-hand plates. Either way contributors are never dropped over a layout:
  whoever the shot cannot hold still goes through the re-home pass and the
  tail roster card.
- The deck's `gp_*` entries carry placement data, not new copy:
  `position: "group"`; an absolute `x` measured against the **picture**, never
  the raw frame; a `scale` that shrinks the card; and a `group` key naming the
  row. The intro overlay also supplies `raised` (`top: 28%`, for a Guardian
  towering above the lower third) and `position: "status"`.
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
legitimate resting state — see [`casting.md`](../../casting/SKILL.md).
`unresolved` is the whole punch-list: an empty list means nobody was missed, so
an omission it does not report is a bug in `plan`, not a gap to work around.

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
an `enable=between(t,in,out)` expression, evaluated per frame — and
stream-copies audio, so titling never costs the soundtrack a second generation.
Two spellings of it have shipped a video with **no plates on it**, exiting 0 at
the right length — [`docs/rendering.md`](../../../rendering.md#burning-plates-onto-a-cut).
