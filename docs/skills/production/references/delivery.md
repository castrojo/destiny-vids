# Delivering a finished cut

Part of the [production skill](../SKILL.md).

## Delivering a finished cut

A render in `renders/` is not a deliverable. The delivery workspace is
**`~/Videos/Wolves/`** — the owner's, not this repo's, and output only: every
file in it is a regenerated artifact.

| Folder | What goes in it |
|---|---|
| `Prod/` | The show at the **highest quality that exists** — one file per act, `NN-<act>.mp4`, FLAC audio, picture never re-encoded |
| `10mb/` | Social copies under a byte cap (`tools/social.py`), built from `Prod/` |
| `megacut/` | The final movie, and nothing else (`tools/megacut.py`) |
| Watch | `catt` to the owner's TV — see [Putting it on the television](#putting-it-on-the-television) |
| Publish | `python3 ~/Videos/yt-refresh.py` — one unlisted playlist |

**The order is [`docs/running-order.md`](../../../running-order.md)'s, not the
filenames'.** `NN-` is the act number, which is fixed — every numeral is
load-bearing, and renumbering to close a gap renumbers the show.

**`Prod/` is hardlinks** to each project's master, so it costs no disk. The
link itself cannot drift — but everything downstream of it can and has:
checksums go stale under a re-link, the megacut keeps playing yesterday's
acts, social copies go missing, and the README keeps naming last week's
master. That is what `tools/deliver.py` is for.

**Refresh only your own line in `CHECKSUMS.md5`.** Rewriting the whole file
asserts that every act in it is correct, and you only built one. A failing line
for somebody else's act is a report, not a chore — act I's line was stale for
exactly this reason and was deliberately left alone. The exception is
`deliver.py publish`: it recomputes every line before it rewrites the file,
so the assertion it writes is the one it checked.

## Putting it on the television

**"Stream it" means the film is playing on the owner's TV before you do
anything else.** It is `AGENTS.md`'s rule zero at the last rung: a path in a
message is not something anybody is watching.

This section exists because it was rediscovered from scratch in at least six
sessions — each one re-running `which catt` and `catt scan`, each one falling
into the same two traps below, one of them reinstalling the tool. **Nothing
here is new; it is written down.**

The workstation casts to Google Cast devices with
[`catt`](https://github.com/skorokithakis/catt), installed as a `uv` tool:

```bash
uv tool install catt                         # only if it is genuinely absent
export PATH="$HOME/.local/bin:$PATH"         # agent shells do not always have it
catt scan                                    # devices on the network, with IPs
```

`catt` lives at `~/.local/bin/catt`, which is **not on every agent shell's
`PATH`** — export it, or call the absolute path. A bare `catt: command not
found` means the `PATH`, not a missing install; check before installing
anything.

### Casting the programme

```bash
cd ~/Videos/Wolves/megacut
setsid nohup catt -d "Home Theater" cast seven-days-to-the-wolves-v3.9.mp4 \
    < /dev/null > /tmp/catt-wolves.log 2>&1 & disown
sleep 30 && catt -d "Home Theater" status         # Title / Time / State: the proof
```

`Home Theater` is the NVIDIA SHIELD. A device is addressable by **name or IP**,
and the name is the stable handle — IPs are DHCP leases, so `catt scan` is the
authority and a hardcoded address is a future failure.

Transport control is a separate invocation against the same device, so a
running cast is adjusted without restarting it:

```bash
catt -d "Home Theater" seek 00:12:30      # also: ffwd, rewind, pause, play
catt -d "Home Theater" volume 60          # also: volumeup, volumedown, volumemute
catt -d "Home Theater" stop               # ends playback AND the server below
```

### `catt` is the server, so it has to outlive your shell

Casting a **local file** does not upload it. `catt` starts an HTTP server on
this workstation and hands the device a URL, which the device then pulls from
in byte ranges for the whole runtime. The consequences are the whole trap:

| | |
|---|---|
| The `catt` process **is** the video source | Kill it and playback stalls partway in, long after the command "succeeded" |
| A `timeout N` wrapper caps the **film**, not the command | `timeout 90 catt cast` ends a 38-minute film after 90 seconds |
| An agent shell exiting takes the server with it | `setsid nohup … < /dev/null & disown`. A plain `&`, and a backgrounded tool call, both die with the shell |
| The workstation must stay awake and on the network | Sleeping it is the same as stopping the cast |

`catt status` a minute *after* casting is the only claim worth making. A cast
that "started" proves the device accepted a URL; it does not prove anything is
still being served. `pgrep -a catt` is the other half — no process, no film.
The log shows the device's range requests (`GET /?loaded_from_catt … 206`),
which is the server-side proof.

**Cast logs are session scratch, not repo records.** Write them to the session
folder or `/tmp` — never `work/`, which is tracked. A 35 KB cast log and a
saved-position file were committed that way, and are removed with this change.

### Keeping a screening alive across a rebuild

The owner watches while work continues, so a new build has to reach the
television **without restarting the film from zero**. Read the position out of
`status`, then hand it back with `-t`:

```bash
POS=$(catt -d "Home Theater" status | awk '/^Time:/ {print $2}')   # 00:24:20
catt -d "Home Theater" stop
sleep 5                                                            # let the app tear down
cd ~/Videos/Wolves/megacut
setsid nohup catt -d "Home Theater" cast -t "$POS" <new-build>.mp4 \
    < /dev/null > /tmp/catt-wolves.log 2>&1 & disown
```

`stop` then `cast` — not `cast` over a live one, which is how a cast lands on
the default receiver and silently ignores the file. The `sleep` is not
superstition: the receiver needs a moment to release before it will accept a
new load.

### Cast the `.mp4`, never the `.mkv`

Every programme build writes both, and only one of them plays. The distribution
`.mp4` is H.264 High\@4.2 with **AAC**; the same-stem `.mkv` archival master is
**FLAC**, which Cast devices do not decode — it fails as audio-only silence or a
refused load, not as an error you can read. The rule the rest of this file
already states applies here too: the declared `output` in
[`stories/megacut/megacut.json`](../../../../stories/megacut/megacut.json) is
the distribution artifact, and the `.mkv` is never a substitute for it.

### Which file to cast, and how to be sure

Ask [`tools/deliver.py`](../../../../tools/deliver.py), and cast the plan's
declared `output`:

```bash
python3 -c "import json;print(json.load(open('stories/megacut/megacut.json'))['output'])"
python3 tools/deliver.py status            # what that file's freshness actually is
```

**Never pick a build by reading the directory.** `megacut/` accumulates
superseded builds, and a filename cannot say which one is current — see
*Freshness is not something you can eyeball* below. If the declared output is
stale, say so in one line and **cast it anyway**: `AGENTS.md`'s *Nothing blocks
a release* holds here, and a stale film the owner can watch beats a fresh one
they cannot.

## Freshness is not something you can eyeball

`Prod/` and `megacut/` are the two places where a wrong file is indistinguishable
from a right one at a glance. Each of these has been used as proof and none of
them is:

| Not proof | Why |
|---|---|
| **Duration** matching `megacut.py --dry-run`'s expected total | The plan's arithmetic describes the *graph*, not the acts seated in it. A build from yesterday's masters has today's runtime. |
| **mtime** — the newest build in the folder | `~/Videos` is a Syncthing folder, so mtimes arrive from other machines. A newer file may be an experiment; an older one may be the declared output. |
| **The filename** — `-fresh`, `-current`, `-degraded`, a version bump | A name is written once, by hand, and never updated when the thing it describes changes. |
| **The file existing** | The `AGENTS.md` rung: existence is not freshness. |
| **A `.prod.md5` existing beside the output** | It is keyed to the output *path*, and the declared output is a fixed versioned filename. A stamp left by an earlier build of that same version survives the next one. |

Only two things settle it: `deliver.py status`, which recomputes the digests,
and **looking at the frame**. `AGENTS.md` is explicit that a digest mismatch is
a prompt to go and look, never a verdict on its own — the hash covers whole
files, so it answers "did an input move", not "did the picture change".

**A provenance stamp older than the output it describes proves nothing.**
`status` compares the recorded digest against `Prod/CHECKSUMS.md5`; it does not
assert that the stamp postdates the build. The two failures look identical from
the outside and want opposite fixes:

| What you see | What it means |
|---|---|
| `.prod.md5` **older** than the `.mp4` beside it | The output was rebuilt by `tools/megacut.py` directly, which does not close the provenance rung. Verify the build, then record it — `deliver.record_megacut_provenance`, or rebuild through `deliver.py build`. |
| `.prod.md5` **newer**, digest still mismatched | `Prod/` genuinely moved after the build. The programme is a rebuild behind. |

## The delivery graph: `tools/deliver.py`


The chain is `master -> Prod/NN-act.mp4 -> megacut/<version>.mp4 ->
10mb/NN-act.mp4`, and drift anywhere along it is the owner's "my copies are
many revisions late" complaint. The graph is now a tool:

```bash
python3 tools/deliver.py status            # what is stale and why, in dependency order
python3 tools/deliver.py status --check    # the same, as a gate (exit 1 on any staleness)
python3 tools/deliver.py publish           # re-link Prod/, regen CHECKSUMS.md5 + the README table
python3 tools/deliver.py build --dry-run   # what a rebuild would run
python3 tools/deliver.py build             # rebuild the stale: megacut, then social copies
```

The **acts and their order come from `docs/running-order.md`**, parsed from
its table — deliver.py carries no act list of its own. The **declared masters**
(and the acts that deliberately have no social copy) live in
[`stories/megacut/delivery.json`](../../../../stories/megacut/delivery.json),
keyed by act numeral. That file is intent; `publish` is the only thing that
makes `Prod/` match it, and it never uses `cp`.

Staleness is content-based where it can be, because `~/Videos` is a Syncthing
folder and mtimes lie: the hardlink layer is checked by **inode identity**
against the declared master, `CHECKSUMS.md5` by recomputation, and the
README's master table is **generated** between `<!-- deliver:table -->`
markers so a hand-edit that disagrees with the map is detected as drift. The
megacut is a re-encode, so mtime against Prod is the signal there, plus a
duration check against the plan's own arithmetic when ffprobe is available —
which is also what catches a build still being written.

Two deliberate behaviours, both learned the hard way on 2026-08-13:

- **`publish` never downgrades.** When a Prod entry and its declared master
  disagree in content, only the newer side may win. A declared master that is
  *older* than what Prod carries is a conflict — reported, not re-linked —
  because re-linking it would silently revert the show. (Act II: the #98
  build's only twin lived in `dv-wt/feat-98-act2-overlay`, a worktree whose
  merge deletes it, while the main checkout's `renders/efmb-plated.mp4` was a
  revision behind. Repaired under #150 by promoting the worktree build onto
  the durable master; the tool then re-attached the link.)
- **Location is a hazard, not just freshness.** A master or twin whose only
  resolution lives inside a git worktree is reported **`ephemeral`** — a
  distinct state from `conflict`, because the remedy differs: conflict means
  "decide which content wins", ephemeral means "promote the master to a
  durable path" (the main checkout's `renders/`, or the act's `~/Videos`
  project). Detection reads git, not the path string: a `.git` *file* marks a
  linked worktree, a `.git` *directory* the main checkout. Mtime ordering is
  irrelevant — a worktree-resident master that is *newer* is still one
  `git worktree remove` from gone, and `publish` refuses to link from a
  worktree path at all.
- **`publish` is the re-link `tools/peaks.py trim` defers to.** `peaks.py`
  corrects a master by `os.replace`ing it with a new inode *on purpose*, so a
  corrected master never silently rewrites its twin — and every such
  correction leaves the Prod link detached until `deliver.py publish`
  re-attaches it. Master gate, then publish: that is the whole loop.

`status` without `--check` always exits 0 once it has printed: a stale
deliverable is a punch-list item, not a build failure, and the suite runs it
against the real workspace as a report (`tests/test_deliver.py`) that stays
green while the owner is mid-edit — and on machines with no `~/Videos` at
all.

**Verify a titled deliverable by looking at a frame.** A cut that gained
nameplates is not verified by its duration, its checksum or ffmpeg's exit code:
`tools/plate.py burn` has twice written a correct-length, correctly-measured
file with **no plates on it at all**
([`docs/rendering.md`](../../../rendering.md#burning-plates-onto-a-cut)). Pull frames
inside two or three plate windows and look before you deliver.

### The per-project contract

Each act is built by its own project directory under `~/Videos/<project>/`, and
`Prod/` hardlinks to what that project produced. Read these **before** touching
a cut — they exist so nobody re-derives the analysis:

1. `STORYBOARD.md` — the scene, the source and in/out points, every decision and
   why, and which file is the shipped deliverable.
2. `render/run-<name>.sh` — the build, and the primary technical record: overlay
   cue times, geometry, colour, audio treatment. **Its defaults always rebuild
   the shipped file.** If they don't, that is a bug, not a variant.
3. `render/` — plates, avatars, music beds, and the scripts that made them.
4. `sources/` — downloaded originals. Large; never re-download needlessly.

A variant is an **environment override**, never an edit:
`MUSIC=… SFX=… OUT=… ./render/run-natali.sh`. That is what keeps "the default
rebuilds what shipped" true, and it is how the `-hq` lossless masters are built
alongside the deliverables (`SURROUND=0 ACODEC=flac OUT=…`).

Three rules there that this repo has to respect:

- **A regenerated file is not hand-edited.** The delivery notes name
  `renders/<video_id>-credited.mp4` as the master for the contributors piece and
  says so explicitly: it is rebuilt from checked-in data by
  `scripts/build_uncut_credited.sh`, so **a new month is a new render, not a new
  edit**. Fix the tag, the vocab or the redaction and re-run.
- **Share the playlist, never a video URL.** YouTube cannot replace a video
  file — a re-upload always gets a new ID — so a playlist link is the only
  stable handle. `yt-refresh.py` hashes each file and uploads only what changed.
  It resolves each cut by its **act number** out of `Prod/`, so the order it
  publishes is the running order. An upload costs ~1600 of the default 10,000
  daily quota units (about six a day); `403 quotaExceeded` means wait for the
  midnight Pacific reset.
- **Titling is the owner's call.** The contributors piece is delivered but
  deliberately not in `yt-refresh.py`'s manifest, because adding it means
  choosing its title and description ([issue #41]). That is the same class of
  stop as a casting decision: deliver it, say so, stop.

[issue #41]: https://github.com/castrojo/destiny-vids/issues/41
[issue #82]: https://github.com/castrojo/destiny-vids/issues/82

Delivery is also where the audio rules bite, and they are not this repo's:
load **`audio-quality-tenet`** before touching a deliverable's audio. What has
already been learned the hard way and must not be re-learned:

- The bed's gain is **derived from its measured true peak**, never hardcoded and
  never normalised. `tools/redact.py`'s `gain_for_headroom` exists because a
  hardcoded `0.9` shipped a **+0.5 dBTP** clipping master.
- **That alone is not enough: check the DELIVERED peak, not the bed's.** A lossy
  encoder reconstructs inter-sample peaks above the samples it is given, so a
  mix measuring −1.1 dBTP came back from AAC at **+0.3 dBTP** — clipping, from a
  chain correct at every earlier step. How much it overshoots depends on the
  material (0.2 dB on one bed, 1.5 dB on another). `redact.py` now measures the
  output and re-runs at a corrected **static** gain until it has headroom;
  corrections only go down and stop at the first safe result, because the
  overshoot is not monotonic in the gain. A FLAC build of the same cut lands on
  target in one pass, which is how you know it is the encoder. That
  measure-and-correct loop is `tools/peaks.py`, shared with `tools/render.py`:
  every cut gets the same delivered-peak trim (issue #44), held to a ceiling of
  −0.9 dBTP — the top of the band the checker above enforces.
- The contributors piece is **stereo AAC on purpose**; the Guardian intros are
  5.1. Do not "fix" one into the other.
- **Source a bed by codec, not by bitrate.** Sorting candidate downloads on raw
  bitrate picks a 44.1 kHz AAC rung over a 48 kHz Opus one whenever the AAC
  number is bigger, and that rung is brickwalled around 15 kHz and forces a
  needless resample. Fetch with `~/Videos/audio-source.sh`, which pins
  `-S "acodec:opus,asr,abr"` and records provenance. A 44.1 kHz bed is the
  fingerprint of having got this wrong.
- **Never take a `-drc` rung.** YouTube offers `251-drc` beside `251`: same
  codec, same bitrate, **dynamic range compressed**. A bare `-f ba -S acodec:opus`
  can select it, and taking it means the pipeline shipped compression it
  forbids — the artist's dynamics lost before the first edit, invisibly, because
  every other check passes. Ask for the rung by number (`-f 251`) when the
  ladder offers both, and confirm what was chosen in yt-dlp's own output.
- **Gate the file you actually ship.** Act VII's lossy deliverable measured
  −1.0 dBTP and passed for weeks while its FLAC master clipped at **+0.3**
  ([issue #82]) — the gain correction had been applied to one and never the
  other, and nothing measured the master because the standing report scanned the
  wrong folder. A check that runs over yesterday's staging directory is not a
  gate. The master gate now exists: `python3 tools/peaks.py trim <master>`
  runs the same measured delivered-peak loop on a finished lossless file —
  one derived static gain on the audio, video stream copied untouched — and a
  master build should end with it. Note it detaches hardlinks by design (the
  corrected file is a new inode, never an in-place rewrite), so the master
  gate is always followed by `python3 tools/deliver.py publish` to re-link
  `Prod/` — that re-link is the step `peaks.py` deliberately does not do.
- `ACODEC=flac` builds a **lossless master** alongside the deliverable, so a
  later fold-down starts from the bed rather than from a lossy file. The
  default stays `aac`, and the defaults must keep rebuilding the shipped file.
  The standard is
  [`docs/skills/audio/SKILL.md`](../../audio/SKILL.md) — the thresholds,
  the delivery band, the sourcing rule, and the failures that have actually
  shipped. The checker that enforces it is `~/Videos/audio-check.sh`.
- Prove it, don't assert it: `framemd5` proves an audio change touched no
  frames, an audio-stream MD5 proves a picture change touched no audio,
  `-xerror` proves the file is not truncated, `volumedetect` proves it is not
  clipping.

**Hazard: `~/Videos` is a Syncthing folder.** A remote deletion can remove a
directory while you are working in it — it has already destroyed a live
`render/` mid-session. It is a move to Trash, so check
`~/.local/share/Trash/info` before rebuilding anything.

