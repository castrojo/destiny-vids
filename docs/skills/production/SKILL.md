# Making videos in volume

## When to Use

- Taking an issue all the way to a rendered file
- Working several videos at once, or alongside other agents
- Deciding what to do first when the index is thin

## When NOT to Use

- Debugging one stage — go to that stage's skill
  ([`indexing.md`](../indexing.md), [`editing.md`](../editing/SKILL.md),
  [`plates.md`](../plates/SKILL.md))
- Filing or triaging the work itself → [`issues.md`](../issues/SKILL.md)

## The loop

```bash
python3 tools/gaps.py                        # what is unfinished
scripts/make_video.sh 3                       # issue -> as far as it can go
scripts/make_video.sh --video-id yt_foo       # or drive it by video
```

`make_video.sh` runs the stages in order and **skips any whose output already
exists**, so re-running it after a tagging pass resumes at assembly rather than
re-fetching 200 MB:

| # | Stage | Skipped when |
|---|---|---|
| 1 | read the issue's brief | — |
| 2 | ingest a video record | `videos/<id>.json` exists |
| 3 | fetch the media (H.264) | `media/<id>.mp4` exists |
| 4 | detect beats + keyframes | `keyframes/<id>/beats.json` exists |
| 5 | **tag** | `tags/<id>.json` exists *and* `worksheet.py check` passes |
| 6 | assemble segments | never — it is cheap and idempotent |
| 7 | finish: a **cut**, or the **uncut** credited build | nothing asked for |

## Two ways to finish

Which one applies is a property of the footage, not a preference:

```bash
scripts/make_video.sh 3 --outline stories/yt_foo.txt   # CUT
scripts/make_video.sh 3 renders/roster.json            # UNCUT, credited
```

- **Cut** — `tools/story.py` picks clean shots out of the index and orders them
  to an outline. It draws **only** from the clean pool, so a trailer full of
  HUD and title cards is fine: the unusable material is never chosen. This is
  the path for almost every trailer.
- **Uncut** — the whole video, credited end to end. Right for a cinematic that
  already tells its story. `tools/uncut.py` does not filter on `clean`, by
  design, which is why stage 7 checks before it builds.

`make_video.sh` picks up `stories/<video_id>.txt` automatically if it exists.
Writing the outline is editorial work; the script does not invent one.

## The gate at stage 7

`build_uncut_credited.sh` renders the **whole** video and credits it. That is
right for a cinematic — the source already tells the story, and
`redactions/<video_id>.json` trims publisher copy off the head and tail. It is
exactly wrong for a trailer whose unclean beats are scattered HUD and title
cards, because rendering the whole thing puts every one of them on screen.

So `make_video.sh` checks before it builds, and **fails closed**:

- An unclean beat that survives redaction **whole** → refuse, and point at the
  cut path.
- An unclean beat a redaction boundary **cuts through** → refuse *unless* that
  redaction record names the segment in `acknowledges`.

That second case is the one the index cannot resolve alone: tags are beat-level
and redaction is frame-level, so on Curse of Osiris the last beat is clean
footage that dissolves into a logo card, and the 163.6s cut removes exactly the
card. Trusting *every* straddle would be too generous — a head cut made for a
ratings card would silently grandfather an unrelated HUD beat that happens to
overlap it. `acknowledges` makes the trust explicit, per beat, in a file you
edit by hand.

A video that refuses here does not need the gate relaxed. It needs cutting.

## Where the detail lives

This skill is the contract. The procedure lives in `references/`:

| Reference | What is in it |
|---|---|
| [`delivery.md`](references/delivery.md) | The `~/Videos/Wolves/` workspace, the delivery graph (`tools/deliver.py` status/publish/build), the per-project contract, hardlinks and checksums, publishing via the playlist, the audio rules that bite at delivery, and the Syncthing hazard. |
| [`parallel-and-tagging.md`](references/parallel-and-tagging.md) | Stale tags and `verify_tags_match_detection`, running several videos at once, batch tagging from generated worksheets, and what to work on first. |
| [`social-copies.md`](references/social-copies.md) | Byte-capped social encodes with `tools/social.py`: encode from `Prod/`, re-encode but never process. |

## Where it stops, and why that is the design

**Stage 5 stops and asks a person to look at frames.** That is not a missing
feature. `clean` is the gate the whole repo rests on, it must be positively
established, and "nobody has looked at this frame" is not evidence the frame is
clean. A script that guessed here would eventually put a HUD in a finished cut.
What the stop hands over is a generated worksheet; what lets the script
continue is `tools/worksheet.py check` passing, not the file merely existing.

**A brief with `automatable: no` stops at stage 1**, prints what it is waiting
on, and exits 0 — stopping is the correct result, not a failure. A brief with
`automatable: partly` runs the mechanical half and stops before the credited
build: indexing is mechanical, putting names on screen is not.

`--video-id` skips the brief entirely. That is a debugging path for a video you
already understand, not the way to run an issue — it bypasses `automatable`
with it.

Both stops print the exact next command. Neither is a state to route around.


## Deliver first, improve second

**When the owner asks for a video, the next thing you produce is a video
file.** See `AGENTS.md`, "A video now means a video now" — it is rule zero and
it outranks everything in this skill.

The loop below is a *production* loop, and its most common failure is not a bad
render. It is **no render**: an agent asked for a quick cut finds a real
structural problem on the way, fixes it properly, and surfaces hours later with
good engineering and nothing to watch. Deliver the cut, file the problem, then
fix it.

```bash
# Deliver something watchable in one command, even mid-round:
./scripts/rebuild-wolves.sh          # act VI, end to end, with its own gates
python3 tools/megacut.py stories/megacut/megacut.json   # the whole programme
```

An encode's ETA is measurable, so measure it rather than guessing — two `stat`
calls a few seconds apart on the growing output give the rate. **A question
about timing gets a time.**

## Keeping the delivery fresh

**A scene changing and the film not changing is the failure mode**, and it is
invisible: the file is still there, still plays, and is a round of notes
behind. `tools/deliver.py` is the graph that notices —
`inputs -> master -> Prod/ -> megacut/ -> 10mb/`.

**`inputs` is two rungs, because git only sees one of them.** `sources` are
committed files, hashed by content, and gate CI. `footage` is what is in
`media/`, which is gitignored — declared by **video_id, never by path**, so a
master that changes container still resolves, and hashed with a
`(path, size, mtime_ns)` cache. An act cut from picture that was later replaced
therefore reports stale rather than `ok` (#229).

```bash
python3 tools/deliver.py status              # what is stale and why
python3 tools/footage.py path <video_id>     # where that master actually is
python3 tools/deliver.py build               # rebuild exactly what is stale
python3 tools/deliver.py build --watch 60    # keep it fresh while you work
python3 tools/deliver.py publish             # after ANY act rebuild
```

**Never build a media path by hand.** `media/<id>.mp4` is how act II broke:
the master was replaced as `.mkv` and the builder could no longer find it,
while `status` still said `ok`. Ask `tools/footage.py` for the path.

**`publish` after every act rebuild — and only after one.** It re-links
`Prod/`, regenerates the checksums and README table, *and* stamps the act's
input digest, which is what makes the next edit show up as drift.

It stamps **only acts whose master is newer than the inputs it names.** An act
whose records moved without a rebuild is reported and left stale, because the
alternative is worse than a missing record: `publish` claims "what is in
`Prod/` now was built from these inputs", so stamping an act nobody re-rendered
records a claim that cannot be true, and the gate goes green with a stale
master behind it. That is how stale programmes shipped, repeatedly — the fix
for a stale act is a rebuild, and `publish` can no longer be mistaken for one.

**Assembly refuses stale acts.** `tools/megacut.py` will not seat an act whose
master predates its own committed inputs; it names them and exits non-zero.
`--allow-stale` ships the old masters anyway and says so on stderr, for a
deliberate rough cut.

Transcoding is cheap and the megacut is what gets reviewed, so it should never
be more than one edit behind. `--watch` polls rather than using inotify on
purpose: an edit can arrive from a rebase, another agent's worktree, or another
machine, and none of those raise a local file event.

**An act with `sources: []` is not configured — it is a finding.** It means the
act is cut outside the repo, so there is nothing to edit here and nothing to
watch. Acts IV, V and VII are in that state, which is exactly why the Kat/Nat
dialogue round ([#118]) had nowhere to land. Giving those acts a builder is the
fix, not adding a source list that lies.

[#118]: https://github.com/castrojo/destiny-vids/issues/118

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll fix the underlying problem first, then the render will be right." | The owner asked for a video. Render, deliver the path, *then* fix. The ordering is the rule; the fix is still welcome after. |
| "It's not worth shipping until X is done." | A cut that exists can be watched, judged and corrected. A cut that does not exist teaches nobody anything. |
| "I found something important on the way, so the detour was justified." | File it as an issue in one minute. A found problem is never a licence to spend the owner's afternoon. |
| "I'll explain what I learned, then give them the file." | Path and runtime first. Explanation after, and short. |
| "I rebuilt the act, the delivery is fine." | Not until `deliver.py publish`. Until then `Prod/` may still link the old master and the megacut still contains it. |
| "`publish` made the gate green, so the delivery is fresh." | `publish` records; it never rebuilds. It now refuses to stamp an act whose master predates its inputs — a green gate you got without a render was the bug, not the proof. |
| "The assembly stage just joins finished things, so staleness is somebody else's rung." | Assembly is the stage where a stale act reaches an audience. It checks, and refuses. |
| "The megacut is only one act behind, I'll roll it in next time." | Transcoding is cheap. `deliver.py build` rebuilds only what is stale; there is no next time to save for. |
| "I'll tag the obvious ones and leave the rest." | An untagged beat derives `clean = false`. Half a tag file marks half the video uncuttable. |
| "The delivered file needs one small fix, I'll edit it in place." | It is regenerated from checked-in data. A hand-edit is lost on the next month's render and nobody can tell it happened. |
| "I'll upload it and share the video link." | YouTube cannot replace a file. Share the playlist; `yt-refresh.py` swaps the contents. |
| "The gameplay trailer has almost nothing clean, the tagging must be wrong." | Gameplay trailers have HUD in the footage. That is what the tier is for. |
| "I'll re-run detection, it's cheap." | Beat index is positional. New detection invalidates the tag file. |
| "I'll bump `vocab/casting.yaml` while I'm here." | It names real people and every video reads it. Its own PR. |
| "The render failed, I'll hand-fix the segment." | Derived fields are recomputed. Fix the tag or the vocab. |


## Red Flags

- **A new act's master that never went through `tools/peaks.py`.** The
  deliverable gets the true-peak loop and the master historically did not —
  that is issue #82, and the prologue repeated it exactly: it shipped at
  **+0.4 dBTP**, above full scale, because a fresh builder simply never called
  the gate. Build → **verify** → `peaks.py trim` → **verify** → `publish`.
- **Starting a render while the previous one may still be writing the same
  path.** Stopping a shell does not guarantee its ffmpeg is gone; two encoders
  on one output produced a master 250 frames short with a corrupt FLAC stream,
  and nothing failed loudly. Check the frame count and a clean decode
  (`ffmpeg -v error -i out -f null -`) before trusting any master, and always
  before gating one.
- **Rendering a guessed recovery over a master.** When an owner reports lost
  authored copy, find it across `git worktree list` first and compare the
  complete restored manifest object to that source. Only then replace the
  master and run `deliver.py publish`; a clean encode cannot prove the words,
  removals, or timing are right.
- Exactly 1 beat for a cut-heavy video → the source is AV1, not H.264
  (`docs/rendering.md`). `make_video.sh` warns on the codec before this bites.
- A video whose segments are 0 clean → `overlays` was skipped wholesale.
- Two agents on one `video_id`.
- Anything under `media/`, `keyframes/` or `renders/` appearing in `git status`.
- A file hand-edited in `~/Videos/Wolves/Prod/`, or a `cp` over one of its
  entries. Every entry is a hardlink to a project's master; `cp` breaks the link
  silently and leaves a copy that goes stale. Re-link with `ln -f`.
- Shipping a master and walking away. The link is not the delivery: the
  checksums, the megacut, the social copies and the README all sit downstream
  of it. `python3 tools/deliver.py status` shows the whole chain; `publish`
  re-links and regenerates, `build` re-encodes what is stale.
- Any write to `~/src/website`. It is read-only from here — several agents run
  worktrees against it — and it is where the authored plate copy lives.
- Trusting a bed's measured true peak as the *delivered* peak. The encoder adds
  inter-sample overshoot; measure the output file.
- Renumbering an act, or "closing the gap" in `Prod/`'s numbering. `NN-` is the
  act number from [`docs/running-order.md`](../../running-order.md): act VIII has
  no film, and its numeral is load-bearing so nothing renumbers around it. III
  is `mrbobbytables` permanently.
- A music bed at 44.1 kHz, or one with nothing above 16 kHz. Both mean the
  fetch took the wrong rung. So does a format id ending in `-drc`.

## Verification

```bash
python3 tools/gaps.py
python3 -m pytest -q                  # includes committed-index integrity
python3 tools/deliver.py status       # the delivery chain, as a report (never a gate here)
~/Videos/audio-check.sh --all         # gates every act in Wolves/Prod
```

`tests/test_index_integrity.py` validates every committed segment, video and
tag file against its schema. It exists because a hand-corrected
`label_source: "human"` — one word, not in the enum — sat in the index until a
rebuild failed on it.
