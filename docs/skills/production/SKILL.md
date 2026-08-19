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
| [`delivery.md`](references/delivery.md) | The `~/Videos/Wolves/` workspace, the delivery graph (`tools/deliver.py` status/publish/build), the per-project contract, hardlinks and checksums, **putting the film on the owner's television with `catt`**, **why freshness cannot be eyeballed**, publishing via the playlist, the audio rules that bite at delivery, and the Syncthing hazard. |
| [`parallel-and-tagging.md`](references/parallel-and-tagging.md) | Stale tags and `verify_tags_match_detection`, running several videos at once, batch tagging from generated worksheets, and what to work on first. |
| [`social-copies.md`](references/social-copies.md) | Byte-capped social encodes with `tools/social.py`: encode from `Prod/`, re-encode but never process. |
| [`avatars.md`](references/avatars.md) | The credits' avatar cache (`tools/avatars.py`): conditional requests, negative caching, backoff, and the Actions job that fetches on the built-in runner token instead of your laptop. |

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
python3 tools/deliver.py publish --act VII    # name what you rebuilt
```

**Never build a media path by hand.** `media/<id>.mp4` is how act II broke:
the master was replaced as `.mkv` and the builder could no longer find it,
while `status` still said `ok`. Ask `tools/footage.py` for the path.

**Long encodes run on the cluster.** `exo-0` has 32 cores and the
`linuxserver/ffmpeg` image already cached; the workstation does not need to
carry an hour of x264. Stage inputs into `/var/mnt/exo0-stage/dv`, run a pod
pinned to that node with `imagePullPolicy: IfNotPresent`, and copy the result
back. The recipe, and the two traps that make a naive attempt fail (the
registry mirror times out, and the image's entrypoint is already `ffmpeg`), are
in [`docs/rendering.md`](../../rendering.md).

## A refresh is every rung, or it is not a refresh
"Refresh the video" always means the **whole** chain, and it always includes
the last two:

```
cards / plates  ->  act master  ->  Prod/  ->  megacut/  ->  10mb/
```

`10mb/` social snippets and `Prod/` are **not optional trailing chores** —
they are what the owner actually opens. A megacut rebuilt over a stale `Prod/`
link, or shipped without regenerating the social copies, is a partial refresh
that reads as a finished one. `deliver.py publish` handles `Prod/`;
`deliver.py build` handles the megacut and the `10mb/` copies.

**Existence is not freshness.** This is the rung that had no guard, and it is
where a main title shipped 17 hours out of date with every other gate green:

```python
if args.cards or not (PLATES_DIR / "plate_maintitle-b.png").exists():   # WRONG
    render_cards()
```

The template moved at 16:56; the PNGs were from 23:24 the night before; the
file *existed*, so the "rebuild" ran on yesterday's cards, produced a new
master, and published a digest saying it was current. The act really had been
rebuilt — it had just been rebuilt **from yesterday**.

Ask the only question that matters about a derived file — is it older than
what derives it — with [`tools/freshness.py`](../../../tools/freshness.py):

```python
if args.cards or freshness.needs_render([MANIFEST, CARD_HTML], CARD_PNGS):
    render_cards()
```

A flag may force **extra** work. A flag may never be the only thing standing
between you and a current card. `tests/test_freshness.py` fails any builder
that gates a card render on a bare `.exists()`.

**`publish` after every act rebuild — and name the act.** It re-links `Prod/`,
regenerates the checksums and README table, *and* stamps the act's input
digest, which is what makes the next edit show up as drift.

**`--act` is repeatable, and it is the whole guarantee.** `publish --act VII`
makes a claim about act VII and about nothing else. A blanket `publish`
certifies **every** act at once, so a rebuild of one act declares the other
seven freshly built too — that is how one render laundered a whole programme
and stale acts kept shipping.

It also stamps **only acts whose master is newer than the inputs it names**,
and only counts inputs git reports as edited. A committed file's mtime says
when the repo was checked out, not when anybody changed it, so trusting it
blocks every act after a rebase — a wall, not a gate. The content digest is
the authority; this is just the cheap proof that a render happened after the
edit.

**Assembly reports stale acts; it never refuses them.** `tools/megacut.py`
names every seated act whose master predates its own committed inputs, on
stderr, and assembles anyway -- AGENTS.md, *Nothing blocks a release*. The
digest hashes whole files, so it answers "did an input move", not "did the
picture change": act III once held the entire programme over a comment about a
different act's casting, with every frame of it correct. Go and look at the
frame before calling an act stale.

**A builder's default output is not automatically its master.** Acts VI and
VIII both write somewhere else by default, so a `rebuild` command is declared
only once `--print-command` has been checked to name the declared master.
Guessing one re-burns nameplates about real people.

Transcoding is cheap and the megacut is what gets reviewed, so it should never
be more than one edit behind. `--watch` polls rather than using inotify on
purpose: an edit can arrive from a rebase, another agent's worktree, or another
machine, and none of those raise a local file event.

**An act with `sources: []` is not configured — it is a finding.** It means the
act is cut outside the repo, so there is nothing to edit here and nothing to
watch. No act is in that state: every act in
[`stories/megacut/delivery.json`](../../../stories/megacut/delivery.json) names
its committed sources, and acts IV, V and VII are repo-driven — their builders
are the `rebuild` commands declared in that map. An act that reads `[]` again
is a finding to report, not a list to fill in with guesses.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll fix the underlying problem first, then the render will be right." | The owner asked for a video. Render, deliver the path, *then* fix. The ordering is the rule; the fix is still welcome after. |
| "It's not worth shipping until X is done." | A cut that exists can be watched, judged and corrected. A cut that does not exist teaches nobody anything. |
| "I found something important on the way, so the detour was justified." | File it as an issue in one minute. A found problem is never a licence to spend the owner's afternoon. |
| "I'll explain what I learned, then give them the file." | Path and runtime first. Explanation after, and short. |
| "I rebuilt the act, the delivery is fine." | Not until `deliver.py publish`. Until then `Prod/` may still link the old master and the megacut still contains it. |
| "`publish` made the gate green, so the delivery is fresh." | `publish` records; it never rebuilds. A green gate you got without a render was the bug, not the proof. |
| "The act rebuilt fine, so the video is current." | Only if its cards did too. A rebuild that consumes stale PNGs produces a new file full of old pictures, and every gate goes green. |
| "The PNG is already there, no need to re-render." | Existence is not freshness. The question is whether it predates its template. |
| "I'll regenerate the social copies next time." | `10mb/` is what the owner opens. A refresh that stops at the megacut is a partial refresh reported as a finished one. |
| "I rebuilt one act, so I'll just run `publish`." | Name it: `publish --act <numeral>`. A blanket publish certifies every act, including the seven you did not touch. |
| "`--print-command` needs a working encoder." | No. Printing is for reading and pasting; resolving ffmpeg is a precondition of *running*. Requiring one takes the offline suite offline. |
| "The assembly stage just joins finished things, so staleness is somebody else's rung." | Assembly is the stage where a stale act reaches an audience. It checks and reports — it never refuses. |
| "The megacut is only one act behind, I'll roll it in next time." | Transcoding is cheap. `deliver.py build` rebuilds only what is stale; there is no next time to save for. |
| "I'll tag the obvious ones and leave the rest." | An untagged beat derives `clean = false`. Half a tag file marks half the video uncuttable. |
| "The delivered file needs one small fix, I'll edit it in place." | It is regenerated from checked-in data. A hand-edit is lost on the next month's render and nobody can tell it happened. |
| "I'll upload it and share the video link." | YouTube cannot replace a file. Share the playlist; `yt-refresh.py` swaps the contents. |
| "I cast it and the command returned, so it's playing." | `catt` **is** the HTTP server. If its process ended, so did the film. `catt status` a minute later, or you have not cast anything. |
| "I'll wrap the cast in `timeout` so it can't hang." | `timeout` caps the *film*, not the command. It is how a 38-minute programme stops after 90 seconds. |
| "`catt: command not found` — I'll install it." | It is installed. `~/.local/bin` is not on every agent shell's `PATH`. Export it before installing anything. |
| "A new build is ready, I'll cast it." | Not from zero. Read the position out of `status` and hand it back with `-t`, or you restart the owner's screening. |
| "I'll drop the cast log in `work/`." | `work/` is tracked. Session scratch goes in the session folder or `/tmp`. |
| "This build's duration matches the plan, so it's the current one." | The plan's arithmetic describes the graph, not the acts seated in it. Ask `deliver.py status`, then look at the frame. |
| "The newest file in `megacut/` is the one to ship." | `~/Videos` is a Syncthing folder and mtimes arrive from other machines. Cast the plan's declared `output`. |
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
  act number from [`docs/running-order.md`](../../running-order.md), and every
  numeral is load-bearing, so nothing renumbers. III is `mrbobbytables`
  permanently.
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
