# Assembling a programme

## When to Use

- Several finished cuts must play as one continuous video
- A compilation needs chapter cards between its parts
- Reproducing a running order that is authored somewhere else (the website's
  intro sequence, a playlist) — though **this show's order is authored here**,
  in [`docs/running-order.md`](../../running-order.md)

## When NOT to Use

- Building a cut from indexed shots → [`editing.md`](../editing/SKILL.md)
- Putting names on people → [`plates.md`](../plates/SKILL.md)
- Fitting a cut to music → [`scoring.md`](../scoring/SKILL.md)
- Delivering a finished file → [`production.md`](../production/SKILL.md)

## Assembly is not editingThis stage **joins finished things**. It never re-cuts, re-times or re-grades
one. Every item it is handed is either a rendered cut from this repo or an
owner-approved deliverable, and if one of them is wrong the fix belongs
upstream, in the thing that made it — not here.

That boundary is what makes the tool safe to re-run: the programme is a
**regenerated artifact**, so it is rebuilt rather than patched, exactly like
every other render in this repo.

**One sanctioned exception, and it proves the rule:** `trim_to` lets the
programme end a delivered act early. It is not editing, because the act's own
file is never touched — the cut lives in the plan, where it is read, tested
and reverted like any other number. Anything more than "stop here" still
belongs upstream.

## It joins finished things — and checks they are still finished

"Finished" was taken on trust: the tool resolved a path, found a file, and
encoded it. Nothing asked whether that file was still the act its records
describe, so an edited record with no rebuild shipped silently in the next
programme — and the assembly stage is the one place where that reaches an
audience.

It now refuses. Before encoding, every seated clip is matched to its act (by
**inode**, since `Prod/` entries are hardlinks to the declared masters) and
checked against `stories/megacut/delivery.json`. An act whose master predates
its own committed inputs is named, and the build exits non-zero.

```bash
python3 tools/deliver.py status --sources-only   # what moved, per act
python3 tools/deliver.py build                   # rebuild exactly what is stale
python3 tools/megacut.py <plan>                  # always assembles; stale acts
                                                 # are named on stderr, never refused
```

This is not editing policy leaking downstream: the fix still belongs upstream,
in the act. The gate only stops assembly from *pretending* the upstream fix
happened.

## Core Process

```bash
# 1a. Chapter cards, deck format (title / subtitle / body): a Python plate
python3 tools/plate.py render --manifest stories/<name>/<name>-cards.json \
    --out-dir renders/plates-<name>-cards

# 1b. Full-frame cards (`kind: act`, `kind: comic`): the SITE'S OWN CSS in a
#     real browser. Do not port one into Pillow -- see "Cards are reproduced".
ln -sfn ~/src/website/node_modules node_modules      # playwright is not vendored
node cards/render-cards.mjs --manifest stories/<name>/<name>-cards.json \
    --out-dir renders/plates-<name>-cards

# 2. Check the graph before paying for the encode
python3 tools/megacut.py stories/<name>/<name>.json --dry-run

# 3. Assemble. Clips whose sources match the delivery spec (tools/conform.py)
#    are stream-copied, not re-encoded; the first run conforms what is new and
#    caches it, so re-runs cost seconds. --jobs N parallelises what encodes.
python3 tools/megacut.py stories/<name>/<name>.json

# 4. Measure the joins on the BUILT file (issue #105)
python3 tools/transitions.py stories/<name>/<name>.json --measure <built>.mp4
```

Both renderers write `plate_<id>.png` into the same directory and each skips
what the other owns, so a manifest may mix them — the Wolves hero segment
carries six Guardian plates *and* the comic title card, and `burn` reads one
plates-dir without caring which tool drew which file.

## Where the detail lives

This skill is the contract. The procedure lives in `references/`:

| Reference | What is in it |
|---|---|
| [`cards.md`](references/cards.md) | Full-frame cards are rendered from the site's own CSS in a real browser, the plan's two item kinds, and why `audio` has no default. |
| [`assembly-graph.md`](references/assembly-graph.md) | Segments-then-join (and the `filter_complex` deadlock it replaced), the `-vf` vs `-filter_complex` re-timing trap, and what has to be normalised. |
| [`joins.md`](references/joins.md) | Where two finished things touch: the audio hole under a dramatic cut, `trim_to`, holds that go wrong without being edited, and measuring a brief's premise rather than its number. |

## Red Flags

- **An item that plays before act I does not get act I's numeral.** The eight
  act numerals are load-bearing (`AGENTS.md`), so a cold open is numbered
  *outside* them — the prologue is `0`, and nothing behind it moved. Renumbering
  to make room at the front rewrites every chapter marker, every
  `Prod/NN-*.mp4` name and every key in `delivery.json`. `deliver.py`'s
  `ACT_ROW` accepts `0` for exactly this.
- **A silent segment's two legs must be equal by construction.** Generating
  silence from a probed or authored duration while the picture runs its own
  natural length is a latent desync: `concat` advances each stream's timeline
  per segment, so a mismatch drifts **every segment after it**. Pin both to one
  number. Probe the **video stream**, not the container — `format=duration`
  covers the longest stream, which is the wrong number on a file whose audio
  outruns its picture.
- **Validation and encoding must resolve a path the same way.** If the checker
  prefers the repo root and the encoder prefers the working directory, the file
  that was validated is not necessarily the file that ships.
- **`-color_primaries` alone does not tag the file.** Those flags describe the
  *frames*; x264 copies the matrix from them and leaves primaries and transfer
  `unknown`. The file then silently disagrees with every other deliverable.
  Pass `-x264-params colorprim=…:transfer=…:colormatrix=…` as well, and
  **verify with `ffprobe`** — this was caught only by probing the output against
  a known-good deliverable. The shared spelling lives in
  `tools/conform.py:video_encode_args`; use it rather than re-typing the flags.
- **Don't re-encode an act that already conforms.** `tools/conform.py` owns
  the delivery spec and a content-hash cache; `assemble()` conforms each clip
  source once and then stream-copies its picture. A new act built by
  `tools/render.py` is born conformant. `--check` a file before paying for an
  encode.
- **A card is a transparent PNG.** Flatten it onto real black with `overlay`;
  do not rely on `format=yuv420p` to drop the alpha, because the colour under a
  fully transparent pixel is undefined and can fringe.
- **"Drop the audio" is not the same as "mute it".** A source labelled *without
  dialogue* still carries the **score**; muting a segment to lose a voice-over
  throws the music away with it, and the result reads as a broken cut rather
  than an edit. If dialogue-free music is wanted, that is a different source or
  a different edit — never silence.
- **Source audio by rung, not by convenience.** Prefer the native-rate stream,
  and never take a `-drc` variant: it applies dynamic range compression, which
  the audio tenet forbids. Place stereo into 5.1 with `pan`, never `-ac`, which
  quietly rescales a finished mix.
- **When a segment's audio is a fraction short of its picture, pad it** with
  `apad` and let the picture decide the length. Cutting to the shorter stream
  drops a frame and, in a concat, drifts everything after it.
- **Never assume an anchor measured on a different upload.** In/out points are
  frame-verified per file. Two uploads of the "same" cinematic can differ by
  seconds — one here had a marketing end card the other did not.
- **Never hand-edit the assembled file.** Fix the plan or the upstream cut and
  re-run.
- **Chapter card copy is reproduced, never authored.** The deck's card is the
  closed `title` / `subtitle` / `body` shape; the act slide adds only the
  owner's `act` numeral and `chapters` list. A card whose words nobody has
  written is omitted and recorded — see [`plates.md`](../plates/SKILL.md).
- **A card that exists on the site is not re-implemented.** Render it from the
  site's CSS with `cards/render-cards.mjs`; a Pillow port of chrome that
  already ships is a second version to keep in step.
- **A music bed under a silent segment is a licensing decision.** Leave it
  silent and record it; never pick a track to fill the gap.
- **An act enters dry out of a slide's silence unless its head is faded.**
  The join applies no gain and no fade by itself; the treatment is
  `fade_in`/`fade_out` (seconds, ACT FILM clock) on the plan's clip items,
  applied by `afade` at the segment encode. Fades only — levelling one act
  against another is a mix decision for the owner. Measure first and after
  with `tools/transitions.py --measure` (issue #105).
- **A fade is for a join into or out of SILENCE.** Where music meets music, or
  where the picture is carrying the transition, a `fade_out` meeting a
  `fade_in` is a four-second hole in the sound exactly where the cut lands.
  Three of four owner notes on one build were this one bug. See
  [`joins.md`](references/joins.md).
- **Assembly may shorten an act only with `trim_to`, never with `dur`.** It
  cuts picture and sound on one number of the act film clock and leaves the
  act's own file untouched. A short `dur` changes the plan's arithmetic while
  the segment still plays to its own end — the clock and the picture then
  disagree. **Read the act's plate manifest before trimming its tail**: a
  credit cut out is not recoverable by a revert.
- **A hold is a relationship, not a property.** Re-ordering the programme can
  make a slide's duration wrong without anybody editing it — a long card after
  an act that now ends on a static shot is two stillnesses in a row. Prefer
  retiring the exception to inventing a third number, and assert that holds
  are equal to *each other*.
- **Measure a brief's premise, not just its number.** "Match the pan" was
  followed by a measurement showing 0 px of vertical motion on both sides.
  Chasing the number would have moved a good cut to match a camera move that
  does not exist.
- **Removing a slide removes that act's chapter marker.** `chapters()` derives
  markers from slides. If a card is dropped, keep its authored copy in the
  deck under `retired` with a note, and record the lost marker as a decision.
- **A reported lost card is recovered from records, not guessed.** Before
  touching it, run `git worktree list` and search each worktree's card or act
  manifest for a distinctive phrase. Restore the entire card object, including
  its text, scale, duration, and any adjacent removals or timing weights, then
  compare the restored object with that source before rebuilding. A worktree
  supplies authored state only; this repository's contract remains the policy.

## Verify, don't assert

A log that says `wrote …` proves nothing. Every one of these has caught a real
defect:

```bash
ffmpeg -v error -xerror -i out.mp4 -f null -        # not truncated
ffprobe -select_streams v:0 -show_entries stream=color_primaries,color_transfer,color_space
ffmpeg -ss <seg> -t <len> -i out.mp4 -map a:0 -af volumedetect -f null /dev/null
```

- **Duration equals the sum of the parts.** Not approximately: an 8.5 s
  shortfall on a 20-minute programme is one act silently truncated, and the
  file plays fine. **`assemble()` enforces this itself** — each segment's
  video extent against its source, and the programme against the plan's sum —
  so a re-time fails the build instead of shipping (#88). The manual checks
  below are for what a duration cannot see.
- **Every act slide lands where the plan says.** Cheap and decisive: extract a
  frame per second (`-vf fps=1,scale=64:36`), compare each against the rendered
  `plate_act*.png`, and print where each slide actually starts. A slide that is
  early is the act before it having been truncated.
- **Per segment**, the peak matches its source — a re-encode must not lift one.
- **Silent stretches read at the noise floor** (about −91 dB for AAC digital
  silence), not merely "quiet".
- Extract frames either side of every join **and look at them**.

## Delivering a programme

A programme is delivered like any other cut — see
[`production.md`](../production/SKILL.md) — with one extra question that only
compilations raise.

```bash
cd ~/Videos && ./audio-check.sh <master>     # the workspace's own gate, first
ln -f <master> ~/Videos/Wolves/Prod/<NN>-<act>.mp4
cd ~/Videos/Wolves/Prod
ffmpeg -v error -xerror -i <NN>-<act>.mp4 -f null -   # verify the delivered file
md5sum *.mp4 > CHECKSUMS.md5 && md5sum -c CHECKSUMS.md5
```

`ln -f`, **never `cp`** — `Prod/` is hardlinks to each project's master, so it
costs no disk and cannot drift. A `cp` over an existing entry breaks the link
silently and leaves a copy that goes stale. `NN` is the **act number** from
[`docs/running-order.md`](../../running-order.md), not a sort key.

Then update `Wolves/Prod/README.md`: the act, and the master it links to. A
delivered file with no row is a file nobody can trace.

**Ask what the programme duplicates.** Its segments are usually already
delivered as standalone acts, so publishing both shows the same footage twice.
That is an ordering decision and it belongs to the owner, so **deliver the file
but leave it out of `yt-refresh.py`'s `VIDEOS` list** until they choose.
Delivering publishes nothing; the `VIDEOS` list does.
