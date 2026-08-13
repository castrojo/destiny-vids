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
| Publish | `python3 ~/Videos/yt-refresh.py` — one unlisted playlist |

**The order is [`docs/running-order.md`](../../../running-order.md)'s, not the
filenames'.** `NN-` is the act number, which is fixed: act VIII has no film, so
the numbering has a gap and closing it would renumber the show.

**`Prod/` is hardlinks** to each project's master, so it costs no disk and
cannot drift from what built it. Re-link with `ln -f`; `cp` over an existing
entry breaks the link silently and leaves a copy that goes stale.

**Refresh only your own line in `CHECKSUMS.md5`.** Rewriting the whole file
asserts that every act in it is correct, and you only built one. A failing line
for somebody else's act is a report, not a chore — act I's line was stale for
exactly this reason and was deliberately left alone.

**Verify a titled deliverable by looking at a frame.** A cut that gained
nameplates is not verified by its duration, its checksum or ffmpeg's exit code:
`tools/plate.py burn` has twice written a correct-length, correctly-measured
file with **no plates on it at all**
([`docs/rendering.md`](../../../rendering.md#burning-plates-onto-a-cut)). Pull frames
inside two or three plate windows and look before you deliver.

`~/Videos/UPLOAD/` was the older staging folder — a different order, AAC copies.
It has been superseded and emptied of everything load-bearing; its removal is
[issue #81]. **Nothing is staged there any more.** If you find a doc or a script
that still writes to it, that doc or script is the bug.

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
[issue #81]: https://github.com/castrojo/destiny-vids/issues/81

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
  gate.
- `ACODEC=flac` builds a **lossless master** alongside the deliverable, so a
  later fold-down starts from the bed rather than from a lossy file. The
  default stays `aac`, and the defaults must keep rebuilding the shipped file.
  The standard is
  [`references/audio-standard.md`](../../references/audio-standard.md) — thresholds,
  the delivery band, the sourcing rule, and the two failures that have actually
  shipped. The checker that enforces it is `~/Videos/audio-check.sh`.
- Prove it, don't assert it: `framemd5` proves an audio change touched no
  frames, an audio-stream MD5 proves a picture change touched no audio,
  `-xerror` proves the file is not truncated, `volumedetect` proves it is not
  clipping.

**Hazard: `~/Videos` is a Syncthing folder.** A remote deletion can remove a
directory while you are working in it — it has already destroyed a live
`render/` mid-session. It is a move to Trash, so check
`~/.local/share/Trash/info` before rebuilding anything.

