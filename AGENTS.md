# destiny-vids — Agent Operating Contract

`destiny-vids` is a shot-level index of Bungie's official Destiny 2 footage,
plus the tools that turn a plain-language outline into a rendered, credited cut.
The repo stores **metadata and timestamps, never footage**.

What it is building is *Seven Days to the Wolves*: **eight acts behind a
prologue**, released as one whole unit.
[`docs/running-order.md`](docs/running-order.md) is the source of truth for what
they are and what order they play in.

## Read order

1. This file — repo rules, commands, and boundaries.
2. [`docs/running-order.md`](docs/running-order.md) — what the show is.
3. [`docs/SKILL.md`](docs/SKILL.md) — find the skill for your task and load it.
4. The design docs that skill links to (`docs/taxonomy.md`,
   `docs/pipeline.md`, `docs/agent-retrieval.md`, `docs/rendering.md`).

## Build, test, and lint

```bash
python3 -m pytest -q                              # the whole suite (fast, offline)
python3 scripts/generate_skill_index.py --check   # skill catalog
python3 tools/corpus.py --check                   # per-character corpora
python3 tools/rederive.py --check                 # no hand-edited derived field
python3 scripts/generate_schema_enums.py --check  # schema enums match vocab/
```

Run all five before every commit. The suite is offline: no model, no network,
no footage. Optional extras matter only for frame-touching stages —
`scenedetect` + `opencv-python-headless` (shot detection), `Pillow`
(nameplates), `imageio-ffmpeg` (fallback ffmpeg).

If one of the last four fails, **regenerate — never hand-resolve**:
`generate_skill_index.py --write`, `corpus.py --write`,
`generate_schema_enums.py --write`. A conflict in `docs/skills/index.json`,
`docs/skills/index.md`, `corpus/*.json` or a schema's `enum` list is always
settled by re-running the tool, because those are outputs.

## "A video now" means a video now

**This is rule zero. It outranks everything below it, including quality.**

When the owner asks for a video, the next artifact you produce is a video file
they can open. Not a plan for one, not a refactor that will make the next one
better, not an issue explaining why it is hard. **Render something, put it
where they can watch it, tell them the path — then do the other work.**

The failure this exists to stop has happened repeatedly here: an agent is asked
for a quick cut, notices something structurally wrong on the way there, fixes it
properly, and surfaces hours later with excellent engineering and **no video**.

This is an ordering rule, not a licence to ship slop: the render happens
*first*, the improvement *after*. If a fix genuinely must precede the render,
say so in one line and give an ETA.

| Signal | What it means |
|---|---|
| "I want a video" / "ship it" / "publish" | Stop. Render. Deliver a path. Then continue. |
| "quick" / "for iteration" | A rough cut beats a correct cut that does not exist. |
| An owner asking twice | You already got this wrong once. Deliver before your next tool call. |

**Answer the question that was asked, and never bury the deliverable.** "When
can I have my video" is answered with a **time** and whether you are still
working, in the first line. Say the path and the runtime first; findings and
caveats go after, and go short.

**A found problem is an issue, not a detour.** Rule 3 below still binds — never
publish a wrong credit — but "this cut could be better" is never a reason to
withhold it.

## The three rules that outrank convenience

1. **`clean` is the primary gate, and it must be positively established.** An
   untagged `overlays` derives `clean = false`. A tagger that skips `overlays`
   does not leave a small gap — it marks its whole output uncuttable. Never
   "fix" this by defaulting `clean` to true.
2. **The fiction bends to the footage.** Rewrite the outline beat to fit the
   shots that exist; never invent a shot, and never widen the pool to unclean
   footage to make a beat land. Unmatched beats are reported, never dropped.
3. **Casting names real people.** A wrong `character` tag credits a real person
   for a shot they are not in. Tag a character only when they are visibly in
   frame; omit rather than guess.

## Degrade, never block

**A missing string is not a failure. It is a punch-list item.** Nothing here
may halt because a word has not been written yet. A nameplate whose subclass
nobody has authored renders without the subclass row. A brief naming somebody
not in `vocab/casting.yaml` runs on the names that do resolve and records the
rest in `unresolved`. A beat with no matching shot is reported and the cut is
still made. **Ship the degraded output and record what is missing.**

**Prose gets a placeholder, not a gap.** A dialogue line nobody has written
renders as **lorem ipsum** (`tools/placeholder.py`), so every slot exists early
enough to be watched — timing, letterbox seat, read length, the gaps between
plates. A slot that renders nothing is a slot nobody notices is missing.

| | |
|---|---|
| **Missing** a word | Fill it with a **placeholder**, ship, record it. Always. |
| **Inventing** a word | Forbidden. Always. |

A placeholder is the opposite of an invention: it is Latin, so nobody mistakes
it for approved English, and **it credits nobody**. Placeholder prose carries
the vocab's uncast speaker (`TBD`) and the drawn crest — never a real login,
never a real avatar. The person a line is destined for goes in
`speaker_pending`, recorded rather than rendered.

That rule is written in scar tissue: act IV's first pass put lorem ipsum on
three real logins, and all three lines were dropped once real copy arrived,
because those people had only ever "spoken" words nobody wrote. **Lorem under a
real name is still putting words in a colleague's mouth.**

Find what is still unwritten with `python3 tools/placeholder.py list`.
`--check` exits non-zero for anyone gating a *final* cut; CI does not run it,
because CI must stay green while copy is being written.

**Three classes of work here can never be automated:** a visual judgement about
a frame, a claim about a real person, and a licensing decision. An agent that
reaches one, records `automatable: no` with the missing decision in
`blocked_on`, and stops has **succeeded**.

### A rights *decision* blocks. A rights *choice* does not

"It involves a licence" is not the test. The test is whether anybody still has
to grant something.

| Situation | Blocked? |
|---|---|
| The asset is not cleared, and clearing it needs somebody's permission. | **Yes.** Stop, record `blocked_on`, file the issue. |
| Several assets are *already* cleared and one must be picked. | **No.** That is taste. Pick one, record the obligation, ship. |
| A cleared asset carries a condition — attribution, a disclaimer. | **No.** Satisfy the condition. |
| The condition has no home yet. | **No.** Attribution has to land *somewhere*, not somewhere specific. [`ATTRIBUTIONS.md`](ATTRIBUTIONS.md) is that somewhere. |

**Recording that something is cleared is as important as recording that it is
not.** A rights bucket with only one value is not a rights bucket — that is why
`usage_class` has `cc_by_4_0` beside the Bungie bucket.

Record every gap where the next person will trip over it: `unresolved` in a
parsed brief, a `TODO(owner)` beside the binding, and a GitHub issue when
somebody has to decide.

## Boundaries

- **Never commit footage.** `media/`, `keyframes/`, `renders/` and `*.mp4` are
  gitignored. The index references source video by `video_id` and timecode.
- **Never hand-edit derived fields.** `clean`, `footage_tier`, `traversal_hero`
  and `casting` are computed by `tools/derive.py` at assembly time. A tagger
  that returns one is an error, by design.
- **Never hand-edit a committed record.** A one-word correction to a tag or a
  segment fails months later, when a rebuild dies on a value the enum does not
  have. Fix the tag file and re-run assembly.
  `tests/test_index_integrity.py` validates every committed segment, video and
  tag file against its schema.
- **`vocab/` is the single source of truth for every enum.** Adding a value is
  **one** edit — the `vocab/*.yaml` file — then
  `python3 scripts/generate_schema_enums.py --write`, because the schemas' enum
  lists are **generated**. Never hand-edit an enum in a schema. Everything else
  in a schema is hand-authored; a record type with **no** schema is the same bug
  one step earlier.
- **Never invent on-screen copy.** Nameplate fields are a closed set —
  [`docs/skills/plates/SKILL.md`](docs/skills/plates/SKILL.md). An authored
  Guardian identity is reproduced verbatim; the generic fallback for an authored
  identity is as wrong as an invented one. Dialogue is *recovered*, not
  written: `dialogue/<video_id>/dialogue.json` with source timecodes and
  per-line evidence, beside the `DIALOGUE.md` the owner edits.
  `redactions/<video_id>.json` only ever *removes* burned-in publisher copy.
- **Never publish commercially.** Bungie footage is used under Bungie's
  fan-content policy, which permits non-commercial fan creations. Every video
  record carries `usage_class` and `source_rights_note`. An asset claiming
  `cc_by_4_0` carries its required credit verbatim in
  [`ATTRIBUTIONS.md`](ATTRIBUTIONS.md), and `tests/test_index_integrity.py`
  fails if a line goes missing.

## Three workspaces, one of them writable

This repo is not self-contained: the words that go on screen and the files that
get published both live outside it.

| Path | What it is | Write? |
|---|---|---|
| `~/src/destiny-vids` | The index, the tools, **and the policy**. | **yes** |
| `~/Videos` | The owner's delivery workspace, including `Wolves/`, where the show is delivered. | only where this repo says so |
| `~/src/website` | Where the authored Guardian identities live and where the card CSS is ported from. | **never** — other agents run worktrees against it |

**This repo is the source of truth for the project** — what the show is, what
order it plays in, what the standards are, how anything is built. `~/Videos` is
where files are *delivered*, not where policy is decided.

Two narrow things outside this repo are authoritative over it, and both are
**copy, not policy**: the authored Guardian identities, which are reproduced
rather than written, and the reference deck's field set. A delivered file is
likewise regenerated, never hand-edited. `~/Videos` is a Syncthing folder, so a
directory can vanish mid-session; check `~/.local/share/Trash` before rebuilding
anything.

## Where the work lives

**GitHub issues are the backlog.** Session state stays in the agent's session
folder. An issue carries the owner's prose *and* a fenced `brief` block that
makes it executable — see
[`docs/skills/issues/SKILL.md`](docs/skills/issues/SKILL.md), with the field
reference in [`schema/brief.schema.json`](schema/brief.schema.json).

The one exception is `docs/plans/<name>/`: a planning tree may be committed when
a design is too large for one issue body. **A plan decides nothing** — it may
*identify* an owner-held decision, but only the filed issues are authority to
act. CI may assert that a plan is navigable *while it exists*, never that one
exists, so deleting a tree is always green. **Delete the tree in the same commit
that files its contents as issues.** A plan that survives its filing is the
stale planning doc this contract exists to prevent.

## Documentation

The docs tree is the `projectbluefin/common` layout: a contract (this file), a
router ([`docs/SKILL.md`](docs/SKILL.md)), skills under `docs/skills/`, and a
short shelf of design docs beside them.

**Docs describe the current state, never the sequence of states that produced
it.** Version-by-version narration is the failure mode this repo has already
had: nine per-act build logs, several of them contradicting the running order
they were supposed to explain. Build history belongs in git, in the issue that
asked for the change, and in `_version` on the manifest that changed. **If a
sentence would start "v2.6 made…", it does not belong in a doc.**

The same rule kills duplication: a fact with a machine record — a trim point, a
master path, a bed's rights bucket — is *linked*, not restated. The record is
the truth; a prose copy is a future contradiction.

When a session surfaces a durable pattern, update the matching skill in the same
change and regenerate the catalog. Skills are **200 lines soft / 500 hard** and
**migrate on sight**: one that outgrows a flat file becomes
`docs/skills/<name>/SKILL.md` + `references/`, in that same change. See
[`docs/SKILL.md`](docs/SKILL.md), "Writing a skill here".

## Agent fast path

- Read the source before asserting repo-internal facts (enum values, field
  names, resolution order). `vocab/`, `schema/` and the tool docstrings are
  authoritative; memory is not.
- Look up external tool behavior via Context7 before claiming it. One stale
  "everybody knows" claim about ffmpeg input seeking already had to be
  corrected in `docs/rendering.md`.
- On an atomic Fedora/Bluefin host the default `ffmpeg` is `ffmpeg-free`: no
  H.264, and it fails only once decoding starts. See `docs/rendering.md`.

## The merge queue

`main` is protected: nothing is pushed to it directly, every change lands
through a pull request, and a PR cannot merge until **`test` is green on the PR
rebased onto the current `main`**. That last clause is the queue — it serialises
landings, so two changes that pass separately but break together are caught
before they land. That is the normal failure mode here, with several agents
editing `tools/plate.py`, `vocab/casting.yaml` and the generated indexes at once.

Turn on **auto-merge** and walk away. `.github/workflows/ci.yml` is the gate: the
offline suite plus the four derived-artifact checks, and it runs on `merge_group`
too.

GitHub's *native* merge queue needs an organization-owned repository and this one
is personal; the API refuses the `merge_queue` rule on both REST and GraphQL. The
up-to-date branch requirement is the same guarantee at lower throughput —
[#35](https://github.com/castrojo/destiny-vids/issues/35).
