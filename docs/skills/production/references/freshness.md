# Keeping the delivery fresh

Reference for [`../SKILL.md`](../SKILL.md). This is the freshness and delivery
graph contract for anything already built.

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

**Video encodes run on the ghost Kubernetes cluster.** Its two
scheduler-eligible nodes each provide about 32 cores. Submit unpinned
Workflows through `tools/farm.py` and let Kubernetes place them; never choose
`ghost` or `exo-0` by hostname. The pinned CPU image is
`lscr.io/linuxserver/ffmpeg:8.1.2-cli-ls76` with
`imagePullPolicy: IfNotPresent`. One pod uses one node, so submit independent
encode units as independent Workflows to use both nodes. PNG/card generation
may remain local; workstation video encoding requires the explicit local
escape hatch. See [`docs/skills/farm.md`](../../farm.md).

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

The declared megacut `output` is the distribution artifact. Its same-stem
`.mkv` is an archival master, never a substitute for a missing distribution
file. `deliver.py build` records the checked `Prod/` checksum set beside the
distribution output; status treats a missing or mismatched record as stale.
Running `tools/megacut.py` directly does not close that provenance rung: after
verifying a direct build, record the checksum set with
`deliver.record_megacut_provenance`, or prefer `deliver.py build`.

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
what derives it — with [`tools/freshness.py`](../../../../tools/freshness.py):

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

**Declare only inputs the builder actually consumes.** A broad shared file in
`sources` makes unrelated edits report the act stale. Before rebuilding on a
digest mismatch, trace whether the changed value can reach a rendered frame.
If the builder consumes a committed manifest that already freezes the copy,
declare that manifest rather than also declaring the vocab file from which it
was once authored.

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
watch. Acts IV, V and VII are in that state, which is exactly why the Kat/Nat
dialogue round ([#118]) had nowhere to land. Giving those acts a builder is the
fix, not adding a source list that lies.

[#118]: https://github.com/castrojo/destiny-vids/issues/118
