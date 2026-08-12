# destiny-vids — Agent Operating Contract

`destiny-vids` is a shot-level index of Bungie's official Destiny 2 footage,
plus the tools that turn a plain-language outline into a rendered, credited cut.
The repo stores **metadata and timestamps, never footage**.

## What this repo produces: features and hero videos

Two kinds of video, built by the same tools, governed by different rules. Most
of this repo's historical confusion is one being cut as if it were the other —
read [`docs/catalog.md`](docs/catalog.md) before building either.

**The feature** is the main story: **Seven Days to the Wolves**, released as
**one whole unit** at KubeCon NA. It is a **musical** — one song end to end, in
three acts, cut to Nightwish's *7 Days to the Wolves*, with the acts hinged on
measured moments in the bed rather than on chapter boundaries. A prototype is
staged ([`docs/cuts/07-seven-days-to-the-wolves.md`](docs/cuts/07-seven-days-to-the-wolves.md));
what it still needs is a **credits sequence** and a **provenance decision**.

It used to be four parts in a running order, and it is not any more — so the
Europa director's cut and the Nati teaser are now **unplaced**, and where they
go is an open decision. Appearing in the feature never made an appearance
somebody's hero video, and it still does not.

**A hero video is one person, one video, every source** — every clean shot of a
bound character in the whole index, summed into one cut. Karena is Mara Sov, so
hers is *every* instance of Mara Sov in the indexed cinematics — Season of the
Lost and the Final Shape trailer today, plus whatever is indexed tomorrow. Kat,
mrbobbytables, Cayde/castrojo and the rest of the cast each get one, and they
are **promotional material for the feature**, released weekly in the run-up.

**The schedule is real and dated**: teaser at T−7 weeks (21 Sep 2026), six
weekly hero videos, feature at KubeCon NA (9 Nov 2026) —
[`docs/release.md`](docs/release.md). The binding constraint is **indexing, not
editing**: of the cast, only Osiris/mrbobbytables (82.1s) and Zavala/Kelsey
(19.0s) have enough footage today. Kat has **zero** indexed shots and
Cayde/castrojo has **1.2 seconds**.

This is why segments carry a `video_id` *and* a character binding: so retrieval
can gather that character from everywhere at once. Both tools already work this
way — `tools/corpus.py <character>` reports the cross-source pool (`across 2
video(s)`), and `tools/story.py` spans the whole index **by default**.

**Spanning is the default; pinning is the exception.** `--from-video` +
`--forward-only` builds a chronological cut inside one trailer, correct only
when the cut retells *that trailer's* story. Reaching for it out of habit is a
recorded failure: three consecutive Destiny chapters came out of the same 1:53
trailer while four fully-indexed trailers had no outline at all, and two of
those cuts shared 68% of their footage and plated the same person (issue #49).

**Before pinning a source, ask what the cut is about. If it is about a person,
do not pin** — see [`docs/cuts/hero-montage.md`](docs/cuts/hero-montage.md).

## Read order

1. This file — repo rules, commands, and boundaries.
2. [`docs/SKILL.md`](docs/SKILL.md) — find the skill for your task and load it.
3. [`docs/catalog.md`](docs/catalog.md) — which of the two video kinds you are
   building. Getting this wrong wastes the whole cut.
4. The design docs the skill points at (`docs/taxonomy.md`, `docs/pipeline.md`,
   `docs/agent-retrieval.md`, `docs/rendering.md`).

## Where the work lives

**GitHub issues are the backlog.** Session state stays in the agent's session
folder. The one exception is `docs/plans/<name>/`: a planning tree may be
committed when a design is too large for one issue body — a design, the
research it rests on, and one issue-ready file per unit of work. Its lifecycle:

- **Created** only against an open issue the owner asked for.
- **A plan decides nothing.** It may *identify* an owner-held decision —
  rights, casting, provenance — but no plan text is authority to act on one.
  The filed issues are.
- **CI may assert only that a plan is navigable while it exists** — links
  resolve, its map matches its files. CI must never require a plan to *exist*,
  so deleting a tree is always green.
- **Deleted** when its contents are filed as issues, which is the tree's own
  stated destination — tree, its test file, and its README row removed in one
  commit. A plan that survives its filing is the stale planning doc this
  contract exists to prevent.

An issue carries the owner's prose *and* a fenced `brief` block that makes it
executable. How to file work, pick it up, and normalize prose into a brief is
[`docs/skills/issues.md`](docs/skills/issues.md); the field reference is
[`schema/brief.schema.json`](schema/brief.schema.json).

## Three workspaces, one of them writable

This repo is not self-contained: the words that go on screen and the files that
get published both live outside it.

| Path | What it is | Write? |
|---|---|---|
| `~/src/destiny-vids` | The index and the tools. | **yes** |
| `~/Videos` | The owner's delivery workspace: the reference deck, the finished cuts, `UPLOAD/` and the publish script. Read its `README.md`. | only where its own docs say so |
| `~/src/website` | Where the authored Guardian identities live (`public/wolves/characters/characters.json`) and where the plate CSS is ported from. | **never** — several agents run worktrees against it |

Nothing in either of those is editable from here, and both are *authoritative*
over this repo where they overlap: plate copy is
[reproduced](docs/skills/plates.md#where-the-copy-is-authored), not authored,
and a delivered file is
[regenerated](docs/skills/production.md#delivering-a-finished-cut), not
hand-edited. `~/Videos` is a Syncthing folder, so a directory can vanish
mid-session; check `~/.local/share/Trash` before rebuilding anything.

**Three classes of work here can never be automated:** a visual judgement about
a frame, a claim about a real person, and a licensing decision. An agent that
reaches one, records `automatable: no` with the missing decision in
`blocked_on`, and stops has **succeeded**. Never guess past one to keep a queue
moving — a wrong credit is not recoverable by a revert.

## Build, test, and lint

```bash
python3 -m pytest -q                       # the whole suite (fast, offline)
python3 scripts/generate_skill_index.py --check   # skill catalog freshness
```

The suite is offline and needs no model, no network, and no footage. Optional
extras only matter for the frame-touching stages: `scenedetect` +
`opencv-python-headless` (shot detection), `Pillow` (nameplates),
`imageio-ffmpeg` (fallback ffmpeg).

Run both before every commit.

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

**A missing string is not a failure. It is a punch-list item.**

Nothing here may halt because a word has not been written yet. A nameplate
whose subclass nobody has authored renders without the subclass row. A brief
naming somebody not yet in `vocab/casting.yaml` runs on the names that do
resolve and records the rest in `unresolved`. A beat with no matching shot is
reported and the cut is still made. **Ship the degraded output and record what
is missing** — a video that exists can be fixed; a video blocked on one word
never gets made, and a pipeline that refuses contributions stops being used.

This does **not** loosen rule 3, and the distinction is the whole point:

| | |
|---|---|
| **Missing** a word | Omit it, ship, record it. Always. |
| **Inventing** a word | Forbidden. Always. |

Guessing which person the owner meant, or writing a subclass nobody authored,
is not iteration — it puts words on a real colleague under the owner's name,
and no amount of velocity justifies it. The two failure modes look similar and
are opposites: one leaves a gap, the other fills it with fiction.

The only things that genuinely stop work are a **rights** decision and a
**clean** violation — the two that cannot be undone after publishing.
Everything else degrades and carries on.

Record the gap where the next person will trip over it: `unresolved` in a
parsed brief, a `TODO(owner)` beside the binding, and a GitHub issue when it
needs somebody to decide.

## Boundaries

- **Never commit footage.** `media/`, `keyframes/`, `renders/` and `*.mp4` are
  gitignored. The index references source video by `video_id` and timecode.
- **Never hand-edit derived fields.** `clean`, `footage_tier`, `traversal_hero`
  and `casting` are computed by `tools/derive.py` at assembly time. A tagger
  that returns one is an error, by design.
- **`vocab/` is the single source of truth for every enum.** Adding a value
  means editing `vocab/*.yaml` *and* `schema/segment.schema.json`; tests assert
  the two agree, and that every cast binding is queryable.
- **Never invent on-screen copy.** Nameplate fields are a closed set — see
  [`docs/skills/plates.md`](docs/skills/plates.md). A Guardian identity somebody
  *has* authored (ten people, in `~/Videos/nameplates.json` and the website's
  `characters.json`) is reproduced verbatim; the generic fallback for an
  authored identity is as wrong as an invented one. Dialogue shown on screen is
  *recovered*, not written: it lives in `dialogue/<video_id>/dialogue.json` with
  its source timecodes and per-line evidence for who is speaking, beside the
  `DIALOGUE.md` the owner edits (`tools/dialogue_md.py` round-trips the two, and
  records an owner's rewrite as theirs rather than overwriting the recovery).
  Likewise `redactions/<video_id>.json` only ever *removes* burned-in publisher
  copy.
- **Never hand-edit a committed record.** A one-word correction to a tag or a
  segment does not fail loudly — it fails months later, when a rebuild dies on
  a value like `label_source: "human"` that is not in the enum. Fix the tag
  file and re-run assembly. `tests/test_index_integrity.py` now validates every
  committed segment, video and tag file against its schema.

## Rights

Bungie footage is third-party copyrighted and used under Bungie's fan-content
policy, which permits non-commercial fan creations. Every video record carries
`usage_class` and `source_rights_note`. Keep it that way: index metadata, ship
no footage, and keep output non-commercial.

## Agent fast path

- Read the source before asserting repo-internal facts (enum values, field
  names, resolution order). `vocab/`, `schema/` and the tool docstrings are
  authoritative; memory is not.
- Look up external tool behavior via Context7 before claiming it — the ffmpeg
  seeking notes in `docs/rendering.md` are the worked example, and one stale
  "everybody knows" claim (input seeking snaps to keyframes) already had to be
  corrected there.
- On an atomic Fedora/Bluefin host the default `ffmpeg` is `ffmpeg-free`: no
  H.264, and it fails only once decoding starts. See `docs/rendering.md`.
- When a session surfaces a durable pattern, update the matching
  `docs/skills/*.md` in the same change and regenerate the catalog.

## The merge queue

`main` is protected by a ruleset: nothing is pushed to it directly, every change
lands through a pull request, and a PR cannot merge until **`test` is green on
the PR rebased onto the current `main`** ("require branches to be up to date").
That last clause is the queue: it serialises landings, so two changes that pass
separately but break together are caught before they land rather than after.
It is the normal failure mode here — several agents edit `tools/plate.py`,
`vocab/casting.yaml` and the generated indexes at once.

Turn on **auto-merge** and walk away; the PR merges itself when the check is
green, and its branch is deleted.

`.github/workflows/ci.yml` is the gate. It is the offline suite plus the three
derived-artifact checks, and it runs on `merge_group` too, so nothing has to
change if this repo ever moves to an organization:

```bash
python3 -m pytest -q
python3 scripts/generate_skill_index.py --check   # skill catalog
python3 tools/corpus.py --check                   # per-character corpora
python3 tools/rederive.py --check                 # no hand-edited derived field
```

Run all four before pushing. If one of the last three fails, **regenerate —
never hand-resolve**: `generate_skill_index.py --write`, `corpus.py --write`. A
conflict in `docs/skills/index.json`, `docs/skills/index.md` or `corpus/*.json`
is always settled by re-running the tool, because those files are outputs.

**What is missing, so nobody re-derives it:** GitHub's *native* merge queue —
which batches several PRs into one speculative build instead of serialising
them one at a time — needs an organization-owned repository, and this one is
owned by a personal account. The API refuses the `merge_queue` rule with
`Invalid rules: 'Merge queue'`, on both REST and GraphQL. The up-to-date branch
requirement above is the same guarantee at lower throughput. See the tracking
issue #35.
