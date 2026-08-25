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
4. The routed local skill, its references, and the design docs it links to
   (`docs/rendering.md`).
5. [`projectbluefin/common/docs/factory/agentic-model.md`](https://github.com/projectbluefin/common/blob/main/docs/factory/agentic-model.md)
   — a shared compatibility sidecar only; it never overrides local authority.

## Local authority and common compatibility

This repository's `AGENTS.md`, records, schemas, and routed skills are the
local authority. `projectbluefin/common` is a shared agent-contract sidecar for
compatible documentation and self-repair practices; it never overrides local
editorial, delivery, rights, GitHub, or merge policy.

## Self-repair and durable learning

Every implementation produces two outputs: the work and any durable learning
it exposed. Verify the repository and loaded skills, detect contradictory or
stale guidance, repair the nearest authoritative contract when source-backed,
validate the repair, and update the matching skill in the same logical change.

## Build, test, and lint

```bash
python3 -m pytest -q                              # the whole suite (fast, offline)
python3 tools/corpus.py --check                   # per-character corpora
python3 tools/rederive.py --check                 # no hand-edited derived field
python3 scripts/generate_schema_enums.py --check  # schema enums match vocab/
pre-commit run --all-files                        # documentation and process checks
```

Run this sequence before every commit. The suite is offline: no model, no
network, no footage. Regenerate stale catalog outputs with
`python3 scripts/generate_skill_index.py --write`. Optional extras matter only
for frame-touching stages —
`scenedetect` + `opencv-python-headless` (shot detection), `Pillow`
(nameplates), `imageio-ffmpeg` (fallback ffmpeg).

If one of the last three fails, **regenerate — never hand-resolve**:
`corpus.py --write`, `generate_schema_enums.py --write`. A conflict in
`corpus/*.json` or a schema's `enum` list is always settled by re-running the
tool, because those are outputs.

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
| "stream it" / "put it on" / "cast it" | The film plays on the owner's television *first*. A path is not a screening — [`delivery`](docs/skills/production/references/delivery.md). |
| "quick" / "for iteration" | A rough cut beats a correct cut that does not exist. |
| An owner asking twice | You already got this wrong once. Deliver before your next tool call. |

**Answer the question that was asked, and never bury the deliverable.** "When
can I have my video" is answered with a **time** and whether you are still
working, in the first line. Say the path and the runtime first; findings and
caveats go after, and go short.

**A found problem is an issue, not a detour.** Rule 3 below still binds — never
publish a wrong credit — but "this cut could be better" is never a reason to
withhold it.

**A full build starts with a positive freshness proof.** Before encoding any
Prod derivative or megacut, run both `python3 tools/deliver.py status --check`
and `python3 tools/megacut.py stories/megacut/megacut.json --dry-run`. Any
`stale`, `blocked`, or `NOTE: act ... is stale and seated` result means the
programme is stale even if a summary says `0 stale`. Rebuild or omit that act
before spending time on social copies or programme segments. Never describe a
megacut as fresh because its output and provenance files merely exist.

**A blocked act is seated, not waited for.** Owner, 2026-08-16, verbatim: *"I'd
rather have broken plates than no video."* An act whose plates cannot be placed
still plays: render it without them, record what is unresolved, and assemble the
programme. Nothing in this repo may hold the show back for a card. The width of
that licence — and it is exactly one square wide — is under **Degrade, never
block** below.

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

**Prose that is written but cannot be read in the time it is up is the same
gap one step later.** `dur` is authored by hand and nothing derives it from
the words, so a two-word pill and a twelve-word pill can both sit on screen
for 1.2 seconds. `python3 tools/readtime.py` lists every plate held shorter
than its own copy needs, and takes the same posture as `placeholder.py`: it
reports, exits 0, and only `--check` fails. **It never re-times anything** —
widening a hold shoves the beat after it, and moving an authored beat is the
owner's call.

**Four classes of work here can never be automated:** a visual judgement about
a frame, a claim about a real person, a licensing decision, and **moving copy
the owner already placed**. An agent that
reaches one, records `automatable: no` with the missing decision in
`blocked_on`, and stops has **succeeded** — the *decision* stops there. The
film does not.

**A gate refusing your seat is not permission to move an authored beat.** This
is the fourth class, and it is written from the exact failure: asked to put
Kyle's "Sup" on the Titan close-up, the builder refused the seat because the
pill would overlap his own nameplate — so the agent slid it earlier until the
assertion passed, which reordered an authored two-line exchange, and recorded
the reorder in its own commit message as though noting it were the same as
asking. It is not. **Explaining an editorial change is not authorisation for
one.**

Placement the owner gave you is *content*, not layout. When a constraint and an
owner's placement disagree, the constraint yields or the work stops:

| | |
|---|---|
| Seat it exactly where the owner said, gate passing | Do it. |
| The gate refuses, and only the **owner's** beat can move to satisfy it | **Stop.** Report the conflict and the options. This is `automatable: no`. |
| The gate refuses, and something *unauthored* can move instead | Move that, say which. |

"Fix X" is never authority to re-time Y. A finished section stays finished:
touching it is a separate request, and it needs a separate yes.

### Nothing blocks a release

**A gate may inform. It may never withhold the film.** There is no finding, no
check, no unanswered question that is a reason to hand back no video. If a
stage cannot vouch for something, it says so on stderr and *keeps going*.

This is rule zero applied to tooling, and it is written from a real failure:
`megacut.py` refused to assemble the whole programme because act III read
stale, and act III read stale because a **comment about a different act's
casting** had been added to `vocab/casting.yaml`. The two bindings act III
actually renders were byte-identical. The show was held for a change that
could not reach a pixel. Owner, 2026-08-17: *"you are blocking releases for no
reason. the reasons you are given are incorrect."*

So: a tool that discovers a problem **reports and proceeds**. `--force`-shaped
flags are the smell — if shipping requires a flag, the default was wrong, not
the operator. An unrecorded fault and a recorded one differ in what gets
printed, never in whether the audience gets a film.

### A plate may be missing. It may never be stale, and never false

Owner ruling: *"I'd rather have broken plates than no video."* And its limit,
from the same session: *"stale is never ok because that's wrong."* So **broken
means missing** — nothing else:

| | |
|---|---|
| A plate that is **absent** because nobody could place it | Ship it missing. Record it in `unresolved`. |
| A plate that is **stale** — the words on it are no longer the words the record says | **Never.** Re-render it. If it cannot be brought current, drop it. |
| A plate placed on a shot the evidence does not support | **Never.** Omit it instead. |

Stale is not a lesser fault than misplaced; it is the same fault with an older
timestamp. It puts copy on screen that the record no longer says, which is how
the main title once shipped 17 hours out of date because its PNGs merely
*existed*. **Existence is not freshness** — every card and plate is re-rendered
from its current template before its act is rebuilt.

**Stale is a claim about the screen, not about a hash.** `source_digest` covers
whole files, so it answers "did any input byte move", never "did the picture
change" — one comment marks an act stale while every frame is correct. A digest
mismatch is a **prompt to go and look**, and the evidence is the frame or the
copy, not the checksum. Never describe an act as stale, and never re-render one,
on a hash alone; and never hold a release for one.

A false plate is worse again: a pill placed without evidence puts a real
person's words against a shot they were not written for, which is a claim about
a real person. **Omission degrades; stale and misplaced both lie.**

No finding about an act's clock stops the programme either. When a manifest's
clock is in question, take the best rung the evidence supports and stop there:

| Rung | What ships |
|---|---|
| (a) | Clock resolved by measurement; every plate re-rendered and re-verified on the shot its `why` describes. |
| (b) | The requested change applied and verified; the already-verified plates carried through from a burn whose placement is itself evidenced. |
| (c) | The act re-rendered from current templates carrying **only** the plates that can be placed, the rest dropped and recorded. |

Rung (c) is always reachable, so "blocked, nothing delivered" is not an
outcome — and neither is "shipped the old master because its plates were
awkward". Escalating the clock decision still follows the `blocked_on` record
above; that record rides beside a shipped act, never instead of one.

### A rights *decision* blocks an asset. It never blocks the cut

"It involves a licence" is not the test. The test is whether anybody still has
to grant something.

| Situation | Blocked? |
|---|---|
| The asset is not cleared, and clearing it needs somebody's permission. | **The asset is blocked; the film is not.** Leave it out, record `blocked_on`, file the issue, ship the cut without it. |
| Several assets are *already* cleared and one must be picked. | **No.** That is taste. Pick one, record the obligation, ship. |
| A cleared asset carries a condition — attribution, a disclaimer. | **No.** Satisfy the condition. |
| The condition has no home yet. | **No.** Attribution has to land *somewhere*, not somewhere specific. [`ATTRIBUTIONS.md`](ATTRIBUTIONS.md) is that somewhere. |

**Recording that something is cleared is as important as recording that it is
not.** A rights bucket with only one value is not a rights bucket — that is why
`usage_class` has `cc_by_4_0` beside the Bungie bucket.

Record every gap where the next person will trip over it: `unresolved` in a
parsed brief, a `TODO(owner)` beside the binding, `speaker_pending` for prose.

**That record is the tracking. Do not also file an issue for it.** A gap that
is already recorded, already degrades correctly, and already ships is *done* —
filing it again turns the backlog into a second copy of `unresolved` that
nobody reconciles. File an issue only when one of these is true:

| File it | Don't |
|---|---|
| A deliverable is blocked and cannot ship. | A shipped cut has a row nobody authored. |
| Somebody must grant, approve, or decide before work continues. | The manifest already says the same thing in `unresolved`. |
| There is real work to do, and it is worth a person's afternoon. | It is one word, one spelling, or one omitted row. |

Batch the small owner-copy questions into one issue per act, not one per row.
`python3 tools/placeholder.py list` and the manifests' `unresolved` are the
punch list; the backlog is for work.

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
- **Some plate manifests are outputs too.** `stories/02-endless-forms-plates.json`
  is built by `scripts/build_efmb_plates.py`, and
  `tests/test_efmb_act.py::test_the_committed_manifest_matches_its_generator`
  asserts the committed file equals what the generator produces. A card added
  to it by hand is reverted by the next build, so **the copy goes in the
  generator** and the manifest is regenerated. Check for a generator before
  editing any `stories/*.json`.
- **A builder listed in `delivery.json` is frozen; check before you edit it.**
  Every path under a master's `sources` is hashed into that act's
  `source_digest`, so editing one — even to delete a dead constant or fix a
  comment — marks a delivered act **stale** for a change that cannot reach a
  pixel. Ask first, then decide:

  ```bash
  python3 -c "import json;print('\n'.join(sorted(s for m in json.load(open('stories/megacut/delivery.json'))['masters'].values() for s in m.get('sources') or [])))"
  ```

  Roughly forty files are on that list, including every `scripts/build_*.py`,
  `tools/plate.py`, `tools/credits.py` and `vocab/casting.yaml` — which is to
  say most of what an agent reaches for. A change that reaches a **frame**
  belongs in the same commit as the rebuild that justifies the new digest;
  tidying that reaches no frame is filed as an issue and rides along with the
  next real rebuild. Neither is a reason to hand-edit a digest.
- **A card count can be pinned by schema.** `schema/ending-cards.schema.json`
  fixes the ending at `minItems: 15, maxItems: 15`, so adding a card is a
  **two-file** change — the manifest and the bound — in one commit. The bound
  is hand-authored; only `enum` lists are generated.
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
- **Recovering authored copy is lookup, not reconstruction.** If the owner says
  a card, dialogue line, or credit was dropped, changed, or lost, inspect every
  worktree before editing: `git worktree list`, then search its records for the
  distinctive phrase. The record can intentionally remove adjacent cards or
  transfer their timing weight. Copy that entire authored object and its
  companion tests verbatim; never infer a shortened quote, re-add a removed
  card, or render over a delivery master until the recovered object matches its
  source exactly. The target repository remains authority; a worktree is
  evidence of in-progress authored state, not a source of policy.
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

### A worktree is a workspace, not a filing cabinet

**Authored copy must never live only in a worktree, and never in a temp
directory at all.** `/tmp` is `tmpfs` on this host: it is erased on reboot. A
worktree there holding the only copy of a card is a card that is one power cut
from never having existed.

This is not hypothetical. Three agent worktrees were found carrying **27, 4 and
2 commits that were on no branch anywhere**, one of them in `/tmp`. Between them
they held the 2026-08-18 revision of the ending — "We support the Community",
and the card `prove-it` — plus act II dialogue split for readability. All of it
had been *rendered*, and the delivered file went to `~/Videos` while the records
stayed behind. That is the whole reason a build could look a month old while
somebody was actively authoring it.

| | |
|---|---|
| Where a worktree goes | Beside the repo — `~/src/<name>` — never `/tmp`, never `/var/tmp` |
| What it is checked out on | A **named branch**. A detached HEAD is invisible to `git branch` and cannot be pushed by name |
| When it is pushed | **Before the render, not after.** A render is the moment the records become load-bearing; if the picture is worth encoding, the copy that produced it is worth pushing |
| When it is removed | Only once its branch is on the remote |

Before ending a session, prove nothing is stranded:

```bash
git worktree list
for w in $(git worktree list --porcelain | awk '/^worktree /{print $2}'); do
  h=$(git -C "$w" rev-parse HEAD)
  [ "$(git branch -r --contains "$h" 2>/dev/null | wc -l)" -eq 0 ] &&
    echo "UNPUSHED: $w ($h)"
done
```

Anything it names is work that exists nowhere else. Push it to a branch —
`rescue/<name>` if it has no better one — before you do anything else.

## Where the work lives

**GitHub issues are the backlog.** Session state stays in the agent's session
folder. An issue carries the owner's prose *and* a fenced `brief` block that
makes it executable — the field reference is
[`schema/brief.schema.json`](schema/brief.schema.json).

The one exception is `docs/plans/<name>/`: a planning tree may be committed when
a design is too large for one issue body. **A plan decides nothing** — it may
*identify* an owner-held decision, but only the filed issues are authority to
act. CI may assert that a plan is navigable *while it exists*, never that one
exists, so deleting a tree is always green. **Delete the tree in the same commit
that files its contents as issues.** A plan that survives its filing is the
stale planning doc this contract exists to prevent.

## Issue applicability

When assessing applicability, issue references are historical evidence, not
proof of current work. Before reporting or acting on an issue, check current
authoritative records and git history to establish that the issue still applies.
A stale `unresolved` line must not revive a settled casting or editorial
decision.

## Documentation

The docs tree is the `projectbluefin/common` layout: a contract (this file), a
router ([`docs/SKILL.md`](docs/SKILL.md)), skills under `docs/skills/`, and a
short shelf of design docs beside them.

**This file and `docs/skills/` are the whole agent contract.** Never add a
vendor-specific instruction file beside them — no `.github/copilot-instructions.md`,
no `CLAUDE.md`, no `.cursorrules`, no `.windsurfrules`. Owner, on an agent
starting one: *"Why are you violating my policies? Fix the skills and docs, no
copilot specific things."* A second contract is a second thing to keep in
step, and the one that drifts is always the one nobody routes through. Every
tool that reads instructions here reads `AGENTS.md`; guidance worth writing
down goes in this file or in the routed skill, and nowhere else.

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
change. Every canonical skill carries the local YAML front matter required by
the skill metadata contract, validated by
`scripts/check-skill-frontmatter.sh`. [`docs/SKILL.md`](docs/SKILL.md) is the
curated task router; the complete catalog is generated as
[`docs/skills/index.json`](docs/skills/index.json), with a human-readable mirror
in [`docs/skills/index.md`](docs/skills/index.md). Generate both with
`python3 scripts/generate_skill_index.py --write`; never hand-edit them. Prefer
one file per skill — a split into `references/` costs an agent an extra read, so
it has to buy more than tidiness.

## Agent fast path

- Read the source before asserting repo-internal facts (enum values, field
  names, resolution order). `vocab/`, `schema/` and the tool docstrings are
  authoritative; memory is not.
- Look up external tool behavior via Context7 before claiming it. One stale
  "everybody knows" claim about ffmpeg input seeking already had to be
  corrected in `docs/rendering.md`.
- On an atomic Fedora/Bluefin host the default `ffmpeg` is `ffmpeg-free`: no
  H.264, and it fails only once decoding starts. See `docs/rendering.md`.
- **Encoding is remote by default.** Owner, 2026-08-16, verbatim: *"why are you
  defaulting to locally that is incorrect, always prefer remote encoding when
  available."* The question is never "is this long enough to be worth the
  cluster" — it is "is the cluster reachable". If it is, the encode runs there.
  `exo-0` (`core@192.168.1.170`) has **32 cores against this workstation's 16**,
  and it is not also running the agent sessions, so local encoding is slower
  *and* it starves the thing asking for it.

  Local is a **fallback with a stated reason**, never a default and never
  silent: a tool that quietly encodes here because the cluster was awkward has
  the bug the ruling above names. `tools/farm.py` is the reference posture —
  cluster unless `cluster_available()` says otherwise, `--local` as an explicit
  escape hatch.

  And never UNCAPPED: a bare local x264 run of a full act OOM-killed this
  workstation at 03:08Z on 2026-08-24. Every local fallback encode runs under
  `farm.run_capped_local`'s systemd memory scope, and
  `tests/test_farm_policy.py` statically pins the posture for every
  video-encode entry point.

  Both nodes carry the `linuxserver/ffmpeg` image; pods submit with
  `imagePullPolicy: IfNotPresent` (the registry mirror times out on a plain
  pull) and are never hostname-pinned. `tools/farm.py` does the staging
  (`kubectl cp` around a per-job PVC) and the ffprobe verification. Recipe in
  [`docs/rendering.md`](docs/rendering.md), operations in
  [`docs/skills/farm.md`](docs/skills/farm.md).

## The merge queue

`main` is protected: nothing is pushed to it directly, every change lands
through a pull request, and a PR cannot merge until **`test` is green on the PR
rebased onto the current `main`**. That last clause is the queue — it serialises
landings, so two changes that pass separately but break together are caught
before they land. That is the normal failure mode here, with several agents
editing `tools/plate.py`, `vocab/casting.yaml` and the generated indexes at once.

Turn on **auto-merge** and walk away. `.github/workflows/ci.yml` is the gate,
and it is **one step**: the offline suite. The derived-artifact checks are
asserted inside that suite rather than run again beside it, so `--check` stays
a local command you run before committing, not a second copy of the gate.

**"Walk away" means auto-merge is on, not that you stopped.** Opening a PR and
sitting beside it is not landing it — owner, verbatim: *"I told you to turn
inference off not send a PR and sit there, merge it."* If a PR is the last
thing between the owner and the change they asked for, enable auto-merge (or
merge it) rather than reporting that a PR exists.

**Leave the checkout clean.** Owner, on finding one that was not: *"why is
there a dirty checkout? did you forget how to use git?"* Everything you
authored is committed to a named branch, or it is one `git checkout` from
being nobody's work. `git status --short` before you hand back, every time —
it costs a second and it is the difference between a finished change and a
pile of edits the next agent has to guess the intent of. Uncommitted scratch
belongs in the session folder, never in the tree.

**A merge is where work disappears.** Several agents edit `tools/plate.py`,
`vocab/casting.yaml` and the generated indexes at once, so a resolution that
takes one side wholesale silently drops the other. Count the test functions
across a merge, not just at the end of it:

```bash
git show <merge>^:tests/test_deliver.py | grep -c '^def test_'
git show <merge>:tests/test_deliver.py  | grep -c '^def test_'
```

A green suite proves nothing here: deleted tests do not fail. `69ebfca` took
`tests/test_deliver.py` from 59 test functions to 15 — the whole delivery
guard, and it stayed green for a day, because 44 tests that no longer exist
cannot go red.

**The gate asserts what a runner can actually know.** It holds no footage and
no `~/Videos`, so it cannot answer "is the delivered film current". Delivery
freshness is therefore a **report**, not a gate: `tools/deliver.py status`
prints it per act, and assembly prints `NOTE: act ... is stale and seated`
and carries on. Nothing refuses — that is the "Nothing blocks a release" rule
above, and CI is not exempt from it.

A check that can only run in the case where it passes is not a check. Before
adding a step, ask what failure it catches that the suite does not, and on
what evidence.

GitHub's *native* merge queue needs an organization-owned repository and this one
is personal; the API refuses the `merge_queue` rule on both REST and GraphQL. The
up-to-date branch requirement is the same guarantee at lower throughput —
[#35](https://github.com/castrojo/destiny-vids/issues/35).
