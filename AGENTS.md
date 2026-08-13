# destiny-vids — Agent Operating Contract

`destiny-vids` is a shot-level index of Bungie's official Destiny 2 footage,
plus the tools that turn a plain-language outline into a rendered, credited cut.
The repo stores **metadata and timestamps, never footage**.

## What this repo produces: features and hero videos

Two kinds of video, built by the same tools, governed by different rules. Most
of this repo's historical confusion is one being cut as if it were the other —
read [`docs/catalog.md`](docs/catalog.md) before building either.

**The feature** is the main story: **Seven Days to the Wolves**, released as
**one whole unit** at KubeCon NA. It is **eight acts**, and
[`docs/running-order.md`](docs/running-order.md) is the source of truth for what
they are and what order they play in — read it before building anything for the
feature. Act VI is the **musical**, one song end to end cut to Nightwish's
*7 Days to the Wolves*, and an editorial pass of it exists
([`docs/cuts/07-seven-days-to-the-wolves.md`](docs/cuts/07-seven-days-to-the-wolves.md)).
It is the longest act and the centre of the show; it is not the whole show.

It used to be four parts, then a single song, and the eight acts settled it: the
Europa director's cut is **act VII** and the Nati teaser is **act V**, so
neither is unplaced any more. Appearing in the feature never made an appearance
somebody's hero video, and it still does not — act IV is Kat's act *and* her
hero video is a separate, separately-released thing.

**One act has no film, and the numerals are load-bearing.** Act VIII, the
credits, is **not designed** (#51); act II was the other gap and is now
delivered and credited. Do not renumber to close the gap: III is
`mrbobbytables` permanently. The programme also still needs a **provenance
decision** (#55).

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
2. [`docs/running-order.md`](docs/running-order.md) — **what the show is**: the
   canonical eight acts, their chapters, and where the files live. It outranks
   every other description of the order, in this repo or outside it.
3. [`docs/SKILL.md`](docs/SKILL.md) — find the skill for your task and load it.
4. [`docs/catalog.md`](docs/catalog.md) — which of the two video kinds you are
   building. Getting this wrong wastes the whole cut.
5. The design docs the skill points at (`docs/taxonomy.md`, `docs/pipeline.md`,
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
[`docs/skills/issues.md`](docs/skills/issues/SKILL.md); the field reference is
[`schema/brief.schema.json`](schema/brief.schema.json).

## Three workspaces, one of them writable

This repo is not self-contained: the words that go on screen and the files that
get published both live outside it.

| Path | What it is | Write? |
|---|---|---|
| `~/src/destiny-vids` | The index, the tools, **and the policy**. | **yes** |
| `~/Videos` | The owner's delivery workspace: the reference deck, the per-cut projects, and `Wolves/`, where the show is delivered. | only where this repo or its own docs say so |
| `~/src/website` | Where the authored Guardian identities live (`public/wolves/characters/characters.json`) and where the card CSS is ported from. | **never** — several agents run worktrees against it |

**This repo is the source of truth for the project**: what the show is, what
order it plays in, what the standards are, and how anything is built. Start at
[`docs/running-order.md`](docs/running-order.md). `~/Videos` is where files are
*delivered*, not where policy is decided — a rule that only exists in a note in
that folder is a rule this repo will contradict sooner or later.

Two narrow things outside this repo remain *authoritative over it*, and both are
**copy, not policy**: the authored Guardian identities, which are
[reproduced](docs/skills/plates/SKILL.md#where-the-copy-is-authored) rather than
written, and the reference deck's field set. A delivered file is likewise
[regenerated](docs/skills/production/references/delivery.md), never
hand-edited. `~/Videos` is a Syncthing folder, so a directory can vanish
mid-session; check `~/.local/share/Trash` before rebuilding anything.

### Where the show is delivered

`~/Videos/Wolves/` — three folders, one job each, all of them regenerated
artifacts:

| Folder | What goes in it |
|---|---|
| `Prod/` | The whole show at the **highest quality that exists** — one file per act, FLAC audio where a lossless master exists, picture never re-encoded. |
| `10mb/` | Social copies under a byte cap (`tools/social.py`), built from `Prod/` and never from each other. |
| `megacut/` | The final movie, and nothing else. |

`~/Videos/UPLOAD/` was the **older** staging folder (AAC copies, a different
running order). It is superseded, and nothing depends on it any more; its
removal is [issue #81](https://github.com/castrojo/destiny-vids/issues/81).
**Nothing is staged there.**

**Nothing here is maintained by hand.** `tools/deliver.py` owns the graph —
`inputs -> master -> Prod/ -> megacut/ -> 10mb/` — and every rung is checked
rather than trusted:

```bash
python3 tools/deliver.py status            # what is stale and why
python3 tools/deliver.py build             # rebuild exactly what is stale
python3 tools/deliver.py build --watch 60  # keep the megacut one edit behind, never more
python3 tools/deliver.py publish           # after ANY act rebuild
```

**Run `publish` after every act rebuild.** It re-links `Prod/`, regenerates the
checksums and the README table, and stamps the act's **input digest** — the
hash of the committed records that act is built from. That last part is what
turns "somebody edited a dialogue record and nobody re-rendered" into a
reported failure instead of a film that quietly plays a round of notes behind.
CI gates it with `status --sources-only --check`, which needs no footage.

An act whose delivery entry says `sources: []` has **no committed inputs at
all** — it is cut outside the repo, so there is nothing here to edit and
nothing to watch. That is a finding, not a setting.

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

## "A video now" means a video now

**This is rule zero. It outranks everything below it, including quality.**

When the owner asks for a video, the next artifact you produce is a video file
they can open. Not a plan for one, not a refactor that will make the next one
better, not an issue explaining why it is hard. **Render something, put it
where they can watch it, tell them the path — then do the other work.**

The failure this exists to stop is real and it has happened repeatedly here: an
agent is asked for a quick cut, notices something structurally wrong on the way
there, fixes the structural thing properly — schema, vocab, tests, docs — and
surfaces hours later with excellent engineering and **no video**. Every
individual step was defensible. The whole was a failure, because the owner
asked for one thing and did not get it.

**The ordering rule, not the doing rule.** Nothing here says ship slop. It says
the render happens *first* and the improvement happens *after*, in that order,
even when the improvement is what makes the render good. If the fix genuinely
must precede the render, say so in one line and give an ETA — do not silently
spend the afternoon on it.

| Signal | What it means |
|---|---|
| "I want a video" / "ship it" / "publish" | Stop. Render. Deliver a path. Then continue. |
| "quick" / "for iteration" | A rough cut beats a correct cut that does not exist. |
| An owner asking twice | You already got this wrong once. Deliver before your next tool call. |

**Answer the question that was asked.** "When can I have my video" is answered
with a **time**, and whether you are still working, in the first line. Not with
context, not with what you learned, not with an apology. If you do not know the
time, measure it — an encode's rate is one `stat` a few seconds apart — and
then answer.

**Never bury the deliverable.** Say the path and the runtime first. Findings,
corrections and caveats go after, and they go short. Four paragraphs of
reasoning in front of a file path reads as an excuse whether or not it is one.

**A found problem is an issue, not a detour.** Filing it takes a minute and
keeps the queue honest; fixing it mid-errand spends the owner's time on
something they did not ask for. Rule 3 below still binds — never publish a
wrong credit — but "this cut could be better" is never a reason to withhold it.

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

### A rights *decision* blocks. A rights *choice* does not.

The rule above has one reading that has already cost a day, so it is written
out here rather than left to judgement. **"It involves a licence" is not the
test.** The test is whether anybody still has to grant something.

| Situation | Blocked? |
|---|---|
| The asset is not cleared, and clearing it needs somebody's permission. | **Yes.** Stop, record `blocked_on`, file the issue. |
| Several assets are *already* cleared and one must be picked. | **No.** That is taste. Pick one, record the obligation, ship. |
| A cleared asset carries a condition — attribution, a disclaimer. | **No.** Satisfy the condition. |
| The condition has no home yet (no credits sequence, no description). | **No.** Attribution has to land *somewhere*, not somewhere specific. `ATTRIBUTIONS.md` is that somewhere, and a `TODO(owner)` records the rest. |

The worked example is act VI's hold music (#104). Four CC BY 4.0 tracks were
found, verified, and written up — commercial use, sync and redistribution all
permitted, attribution the only condition — and then the work stopped to ask
which one. Nothing was blocked: a seventeen-second gag waited a day on a
question of taste wearing a licence's clothes.

Two structural fixes came out of it, and they are the reason this is a rule
rather than a note. `usage_class` had exactly **one** value, so the index could
say an asset was *somebody else's* and had no way to say it was *cleared* — and
an agent with nowhere to record "cleared" records "blocked". Bed records had no
schema at all, so nothing ever checked. Both are fixed; if a third asset class
appears with the same shape, fix it the same way rather than working around it.

**Recording that something is cleared is as important as recording that it is
not.** A rights bucket that only has one value is not a rights bucket.

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
  means editing `vocab/*.yaml` *and* the schema that mirrors it
  (`schema/segment.schema.json`, `schema/video.schema.json`,
  `schema/bed.schema.json`); tests assert they agree, and that every cast
  binding is queryable. A record type with **no** schema is the same bug one
  step earlier — that is how a bed's `usage_class` stayed unchecked free text.
- **Never invent on-screen copy.** Nameplate fields are a closed set — see
  [`docs/skills/plates/SKILL.md`](docs/skills/plates/SKILL.md). A Guardian identity somebody
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

**Not everything here is somebody else's.** `usage_class` also has `cc_by_4_0`,
for an asset whose licence already permits this use — the act VI hold music is
the first. That bucket exists so the index can record that something is
**cleared**, which it previously could not say at all. Its condition is not
optional: a record claiming it carries its required credit verbatim in
[`ATTRIBUTIONS.md`](ATTRIBUTIONS.md), and `tests/test_index_integrity.py`
fails if a line goes missing. Adding a value means editing `vocab/`, the
schemas, *and* the credit file — never just one.

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
- When a session surfaces a durable pattern, update the matching skill in the
  same change and regenerate the catalog. Skills are 200 lines soft / 500 hard
  and **migrate on sight**: one that outgrows a flat file becomes
  `docs/skills/<name>/SKILL.md` + `references/`, in that same change. See
  [`docs/SKILL.md`](docs/SKILL.md), "Writing a skill here".

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
