# destiny-vids — Agent Operating Contract

`destiny-vids` is a shot-level index of Bungie's official Destiny 2 footage,
plus the tools that turn a plain-language outline into a rendered, credited cut.
The repo stores **metadata and timestamps, never footage**.

## Read order

1. This file — repo rules, commands, and boundaries.
2. [`docs/SKILL.md`](docs/SKILL.md) — find the skill for your task and load it.
3. The design docs the skill points at (`docs/taxonomy.md`, `docs/pipeline.md`,
   `docs/agent-retrieval.md`, `docs/rendering.md`).

## Where the work lives

**GitHub issues are the backlog.** There is no TODO file, no notes doc, and no
planning markdown in the repo — those go stale and mislead the next agent.
Session state stays in the agent's session folder.

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
