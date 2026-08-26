# Rendering: getting a working ffmpeg

`tools/render.py` is the only stage that touches actual pixels, and it is the
stage most likely to fail on a Bluefin/Fedora atomic host — for a reason that is
easy to misdiagnose. This documents which ffmpeg to use and why.

## Production video encoding runs on Kubernetes

The local ffmpeg resolution below is for probes, still extraction, and
lightweight assets. It is **not** the production renderer. Video-producing
ffmpeg commands go to the ghost Kubernetes cluster in
`lscr.io/linuxserver/ffmpeg:8.1.2-cli-ls76`, with
`imagePullPolicy: IfNotPresent`; Kubernetes chooses between the two
scheduler-eligible roughly 32-core nodes. Never hostname-pin a build.

This is not a flag you pass — it is the DEFAULT everywhere, and since the
owner's ruling of 2026-08-25 it is the ONLY executor. Every video-encode
entry point (megacut, the builders, `tools/plate.py burn`, `tools/redact.py`,
`tools/conform.py`, `tools/render.py`) farms when the cluster answers, and
stops with a `FarmError` naming the reason when it does not. Local ffmpeg
execution is prohibited outright (`farm.run_capped_local` raises): a bare
local x264 run OOM-killed this workstation at 03:08Z on 2026-08-24, and the
memory-capped fallback that answered it is revoked. `--local` is rejected by
every tool that still accepts the flag. `tests/test_farm_policy.py`
statically pins the posture.

For the programme, use:

```bash
python3 tools/megacut.py stories/megacut/megacut.json
```

That farms both encode phases — the conform-cache misses and the ENCODE
segments — and keeps the COPY segments and the final concat local, because a
remux is not an encode. `--no-copy` survives as a debugging switch that
forces every segment down the encode path; the cold-cache local-x264 trap it
used to guard against is closed. The local final concat is allowed because it
stream-copies picture and only muxes/encodes audio.

## The delivery spec: render output is born conformant

Everything `render.py` emits now conforms to the one delivery spec defined in
`tools/conform.py` (`DELIVERY`): **60000/1001** (59.94 — the owner-approved
delivery rate), 1920×1080, yuv420p, BT.709 primaries/transfer/matrix written
into the x264 VUI, H.264 High@4.2, closed GOP. The flags come from
`conform.video_encode_args()` — one place, so the render stage, the conform
stage and the megacut's cards can never drift apart.

Why it matters: a conformant act needs **no normalising at assembly time**.
`tools/megacut.py` probes each clip's source, conforms it once through a
content-hash cache, and then builds the segment with `-c:v copy` — the
per-assembly re-encode of the whole programme (~17¾ minutes, measured) drops
to seconds when the acts are unchanged. The full story, including why cards
must encode to the same spec, is in
[`skills/megacut/references/assembly-graph.md`](skills/megacut/references/assembly-graph.md).

### The plate burn is the exception, and it is opt-in

`tools/plate.py burn` is the **last** picture generation before an act is
delivered, so its argv — not the builder's — decides what the standalone
master's bitstream says. It still defaults to a private `crf 18` / `preset
medium` / untagged argv, which is why acts II and VI shipped with
`color_space`, `color_transfer` and `color_primaries` all `unknown` while
every act whose final pass runs through `conform` carried BT.709. Untagged SDR
is only *assumed* 709 by a player; `tools/megacut.py` records why "most
players" is not a guarantee.

Pass `--delivery-spec` (CLI) or `encode_args=conform.video_encode_args()`
(API) to get the delivery rung and the VUI. It is opt-in per act rather than
the default because every act declaring `tools/plate.py` as a delivery source
goes stale the moment the default moves, and an act only stops being stale by
being re-rendered — so flipping it forces rebuilds of acts nobody asked for.
Act II opts in; the rest are converted as they are next rebuilt.

## The problem: `ffmpeg-free` has no H.264

Fedora, and therefore Bluefin, ships **`ffmpeg-free`**: a build with patent-
encumbered codecs stripped out. It has AV1 (`libdav1d`), VP9, VP8 — and **no
H.264 decoder and no AAC**.

The failure mode is nasty because it is not a startup error. `ffmpeg -version`
works. `ffmpeg -filters` works. The command only dies once it reaches the first
frame:

```
[vist#0:0/h264 @ ...] Decoding requested, but no decoder found for: h264
```

Since essentially every YouTube download worth indexing is H.264, this breaks
the whole render stage while looking like a bad input file.

## The answer: the ffmpeg container

Bluefin already runs a long-lived ffmpeg container for the GNOME thumbnailer
service, managed by the `bluefin-thumbnailer.service` quadlet:

```console
$ podman ps --format "{{.Names}} {{.Image}}"
bluefin-thumbnailer  ghcr.io/jrottenberg/ffmpeg
```

This is the preferred ffmpeg for this repo. It is a full **non-free** build —
`libx264`, `libx265`, `libfdk_aac`, `libvpx`, `libsvtav1`, plus `drawtext`
(fontconfig/freetype) and VAAPI:

```console
$ podman exec bluefin-thumbnailer ffmpeg -version | head -1
ffmpeg version 8.1
```

Using it costs nothing: no layered packages, no `rpm-ostree` mutation of the
base image, no Homebrew build. It is already running.

## Host setup: make the container *be* `ffmpeg`

Rather than teaching every tool to find a working ffmpeg, put one on `PATH`.
`tools/ffmpeg-container-shim.sh` is that shim: it runs the container image, and
installs as `~/.local/bin/ffmpeg` with `~/.local/bin/ffprobe` symlinked to it
(it dispatches on `$0`).

```bash
install -Dm755 tools/ffmpeg-container-shim.sh ~/.local/bin/ffmpeg
ln -sf ffmpeg ~/.local/bin/ffprobe

cat > ~/.config/ffmpeg-container.conf <<'EOF'
FFMPEG_CONTAINER_IMAGE="ghcr.io/jrottenberg/ffmpeg:latest"
FFMPEG_CONTAINER_NAME="bluefin-thumbnailer"
EOF
```

```bash
ffmpeg -version          # => ffmpeg version 8.1  (container)
FFMPEG_NO_CONTAINER=1 ffmpeg -version   # => the host binary (escape hatch)
```

Pin `FFMPEG_CONTAINER_IMAGE` to the digest the thumbnailer service already runs
and the shim never triggers a pull. If that image is gone (a prune, a tag move),
it falls back to whatever image the running container actually uses rather thanfailing.

The escape hatch does not assume a specific host ffmpeg: `FFMPEG_NO_CONTAINER=1`
tries `/usr/bin/<tool>` first and then `/home/linuxbrew/.linuxbrew/bin/<tool>`,
so it lands on the Fedora `ffmpeg-free` build if that is all there is, and on a
Homebrew build with H.264 when one is installed.

### Why an ephemeral `podman run`, not `podman exec`

The shim runs the *image* rather than `exec`ing into the running container:

1. **That container belongs to the thumbnailer service.** Borrowing it for long
   encodes contends with desktop thumbnailing.
2. **It only bind-mounts `$HOME`.** `/tmp` and anything else is invisible inside
   it. An ephemeral run controls its own mounts, so `/tmp` works.

Overhead is ~156ms vs ~79ms for `exec` — irrelevant next to an encode.

The shim mounts `$HOME` and `/tmp`, adds `$PWD` explicitly when it falls outside
both, sets `-w "$PWD"` so relative paths resolve, allocates a TTY **only** when
stdin and stdout are both terminals (a TTY corrupts binary data on a pipe),
passes `/dev/dri` through for VAAPI, and keeps networking enabled so
`ffmpeg -i https://…` still works.

Verified behavior: relative paths, `/tmp` paths, paths outside `$HOME`, H.264 +
AAC encode, output files owned by the user (not root), exit-code propagation,
binary pipe integrity, and network inputs.

## Why `render.py` still resolves ffmpeg itself

The shim fixes *this* host. `tools/render.py` keeps its own resolution order so
the repo works on machines without it — and because being explicit about which
ffmpeg ran is worth more than the indirection costs.

### Why the paths just work

The thumbnailer container is started with the user's home bind-mounted **at the
same path**:

```
/var/home/jorge -> /var/home/jorge
```

So a host path is a valid container path, unchanged. `render.py` needs no path
translation, and the source media it reads sits under that mount.

Two consequences the code has to respect, both of which are real bugs if
ignored:

1. **Every path must be absolute.** `podman exec` does not inherit the caller's
   working directory, so a relative `media/foo.mp4` resolves against the
   container's cwd and fails. `resolve_media()` returns `.resolve()`d paths and
   `render()` absolutizes the output and audio bed.
2. **Intermediates must not live in `/tmp`.** Only the home directory is
   mounted. Clip intermediates and the concat list file are written to a
   temporary directory created *beside the output file*, not in the system
   temp dir.

(The `~/.local/bin` shim avoids both by using `podman run -w "$PWD"` with its
own mounts. `render.py` uses `podman exec`, so it must handle them.)

### The container is shared

`bluefin-thumbnailer` belongs to the thumbnailer service. `render.py` only ever
`exec`s ffmpeg inside it — it never starts, stops, or reconfigures it. Treat it
as read-only infrastructure.

## Resolution order

`find_ffmpeg()` returns an argv **prefix** (a list), so a containerized ffmpeg
is interchangeable with a local binary at every call site:

| Order | Source | Selected when |
|---|---|---|
| 1 | `$DESTINY_FFMPEG` | set; shell-split, wins outright |
| 2 | `podman exec <container> ffmpeg` | `podman` present and the container is running |
| 3 | `podman run --rm -v $HOME:$HOME <image>` | `$DESTINY_FFMPEG_IMAGE` is set and no container is running |
| 4 | `imageio-ffmpeg`'s bundled static binary | the package is installed |
| 5 | `ffmpeg` on `PATH` | **last** — on Bluefin this is the broken `ffmpeg-free` |

`PATH` deliberately ranks last: it is the one most likely to be found and least
likely to work.

```bash
python3 tools/render.py cut.json --media media --out renders/hero-cut.mp4
python3 tools/render.py cut.json --no-container          # force a local binary
DESTINY_FFMPEG_CONTAINER=my-ffmpeg python3 tools/render.py cut.json
DESTINY_FFMPEG="podman exec other ffmpeg" python3 tools/render.py cut.json
```

`render.py` prints the resolved command before it starts, so which ffmpeg ran is
never a guess:

```
ffmpeg: podman exec bluefin-thumbnailer ffmpeg
```

## Encoding on the cluster: `tools/farm.py`

Long encodes belong on the cluster rather than the workstation, and the way
they get there is `tools/farm.py` — never SSH, never a hand-written pod. One
command is the whole loop:

```bash
python3 tools/farm.py in.mp4 --out out.mp4          # chunked, verified
```

and the library entry points (`run_ffmpeg_on_cluster`, `run_ffmpeg_chain_on_cluster`,
`run_encode`) are what every builder in this repo calls. The flow, all driven
by the tool: an Argo **Workflow** and a **PVC** per job in namespace `argo`,
inputs staged with `kubectl cp`, progress streamed from the pod log, the
output fetched back and **verified by ffprobe** against the source (an ffmpeg
exit 0 alone is not evidence — issue #88 shipped a file 8.5 s short). Both
nodes are the farm: nothing is pinned, and the scheduler spreads segment pods
across `exo-0` and `ghost` (32 allocatable cores each). `farm.py --node`
exists for the rare run that must land somewhere specific.

**Pin the tag and never pull.** The cluster resolves images through a registry
mirror on ghost (`192.168.1.102:30501`) which times out on plain pulls, and a
pod then sits in `ErrImagePull` with the image already on disk. Both
`lscr.io/linuxserver/ffmpeg:latest` and `:8.1.2-cli-ls76` are cached on both
nodes — the farm submits with `imagePullPolicy: IfNotPresent` for exactly this
reason.

Verified on that image: `libx264`, `aac`, `libfdk_aac`, `flac`, `libopus`. It
is a full build, so unlike `/usr/bin/ffmpeg` it will not die once decoding
starts. The full non-free build is also the *speed* choice: on 24 cores,
libx264 measured faster than h264_vaapi on identical input (15.7x vs 13.7x
realtime) at better quality, so the farm requests CPU only — never
`amd.com/gpu`.

**What it does not solve.** Storage is `local-path` (RWO) and the footage lives
on the workstation, so every input is a `kubectl cp` upload and every output a
download. That transfer is the real cost, which is why cards and probes stay
local while anything with an x264 recipe goes to the farm.

## Fallback: `imageio-ffmpeg`

Off Bluefin, or with no container running, `pip install imageio-ffmpeg` supplies
a full static ffmpeg (H.264 + AAC) with no system packages. It is what
`--no-container` selects here.

## The other answer on this host: Homebrew

`~/Videos/README.md` and `~/Videos/OVERLAYS.md` tell agents to use
`/home/linuxbrew/.linuxbrew/bin/ffmpeg`. That is not a contradiction and neither
document is stale — the two workspaces solved the same problem differently, and
the Homebrew build is what the cuts already shipped there were made with.

Measured on this host, all three at once:

| Binary | Version | H.264 | `drawtext` |
|---|---|---|---|
| `/usr/bin/ffmpeg` (`ffmpeg-free`) | 7.1.3 | **no** | — |
| `/home/linuxbrew/.linuxbrew/bin/ffmpeg` | 8.1.2 | yes | **no** |
| the container (and `~/.local/bin/ffmpeg`) | 8.1 | yes | yes |

So: either non-free build renders this repo's cuts, and the missing `drawtext`
is precisely why `~/Videos` renders its cards in PIL and a headless browser
rather than in a filter chain — which is also what `tools/plate.py` does. Use
whichever the workspace you are in documents; what must never happen is falling
through to `/usr/bin/ffmpeg`, which fails only once decoding starts.

## Related trap: OpenCV cannot decode AV1

Shot detection has the mirror-image problem. `yt-dlp` prefers AV1 from YouTube,
and PySceneDetect's OpenCV backend cannot decode it — but rather than erroring,
it returns **one beat for the entire video**, which silently looks like a
trailer with no cuts.

Always fetch H.264:

```bash
yt-dlp -S "vcodec:h264,res:1080" --merge-output-format mp4 \
  -o "media/<video_id>.%(ext)s" <url>
```

Sanity check: a two-minute Bungie trailer should detect on the order of ~70
shots. If it reports 1, the codec is wrong, not the detector.

## A delayed `fade=t=in` is a gate, not only a ramp

`fade=t=in:st=X:d=D` holds **every frame before `X` fully black**, then ramps
over `D`. It is easy to read the filter as "start ramping at X" and reach for a
`color=black` clip plus a `concat` or an `overlay` to hold the black — one
filter already does both.

That is what opens the prologue: the picture is gated off until the source's
own flare, and a two-frame `d` lets the burst bloom out of black rather than
pop in half-lit.

```console
$ ffmpeg -f lavfi -i testsrc=size=320x180:rate=25:duration=3 \
    -vf "fade=t=in:st=2:d=0.1" -y /tmp/fadetest.mp4
# mean luma: 0.0 at 0.5s, 0.0 at 1.5s, 83.8 at 2.05s, 125.8 at 2.5s
```

**Measure the moment you are gating to, rather than taking a shot boundary.**
Scene detection reports a cut once the frame is already *different*; a flare
that blooms is visibly under way by then. The prologue's void sits on a flat
plateau (45.9, 45.8, 46.0) and departs it at 54.3 — that departure is the
frame to cut on, and it is 80 ms ahead of what the detector called.

## Seeking: why `-ss` goes after `-i`

`render.py` uses **output seeking** (`-ss` after `-i`), which decodes from the
start of the file and discards. It is ~2.6x slower than input-side `-ss` on a
two-minute source.

The common justification for this — "input seeking snaps to a keyframe" — is
**stale**. Per the FFmpeg documentation, input seeking moves to the closest
point before the requested position and then *decodes and discards the
intervening segment to ensure accuracy*. Both are accurate.

The real reason is specific to this pipeline: input seeking **rebases output
timestamps to zero**, which shifts the phase of the fps conversion every clip
goes through (the delivery rate is 60000/1001), changing which source frames
get duplicated. Measured on the same in-point, the two methods produce
visibly different frames:

```console
$ ffmpeg -i src.mp4 -ss 69.336 -t 0.968 ...   # 2.486s, framemd5 b8507036...
$ ffmpeg -ss 69.336 -i src.mp4 -t 0.968 ...   # 0.964s, framemd5 2e7dbbdb...
```

Same frame count, different frames. Accuracy wins; the cut list's in-points are
the entire point of the index.

If a future change drops the fps normalization (e.g. all clips from one
source at native rate), input seeking becomes safe and is worth the 2.6x.

### The consequence: cut long sources through a window extract

Output seeking is cheap on a two-minute trailer and brutal on a long one,
because the cost scales with the **in-point**, not the clip length. Measured
here at roughly 35x realtime, a clip at 24:00 in a 30-minute compilation costs
about 40 seconds of decode before it writes a frame — for a one-second clip, and
again for every other clip in that act.

So extract the span you need to its own file first and cut from that. The
procedure and the timecode-rebasing it forces are in
[`skills/editing/SKILL.md`](skills/editing/SKILL.md).

## The delivered peak is trimmed, not assumed

A cut re-encodes audio with AAC at the concat pass, and a lossy encoder
reconstructs inter-sample peaks above the samples it was given — so the
finished file can sit above the delivery band even when nothing downstream
touched the level. `render.py` therefore measures the **delivered** file with
`tools/peaks.py` and re-runs the concat (only the concat, never the clip cuts)
at a corrected **static gain** until it lands at or below −0.9 dBTP, the top
of the band `~/Videos/audio-check.sh` enforces. Never a limiter, never a
normaliser. A file that is still hot after five passes ships with a WARNING
rather than failing — degrade, never block. `--target-dbtp` moves the target;
a muted render has no audio and skips the check.

A file that was built *outside* `render.py` gets the same gate afterwards:
`python3 tools/peaks.py trim <file>` measures the delivered file and re-muxes
it at a corrected static gain, video stream copied untouched. That is how a
lossless FLAC master is held to the same standard as the AAC deliverable —
the gap that let act VII ship at +0.3 dBTP (issue #82).

## A YouTube upload is 8-bit H.264 and AAC, never HEVC and never FLAC

A mastering codec and an **ingest** codec are different jobs. Our masters are
10-bit HEVC with a FLAC soundtrack because that is the right thing to archive.
Handing that same file to YouTube is what produces "it's broken in Firefox and
fine in Chrome".

YouTube does not serve the file you upload; it re-encodes it into a ladder and
the browser picks a rendition. **Firefox on Linux takes VP9, Chrome takes AV1.**
So a defect in one arm of that ladder is invisible to whoever tested in the
other browser.

Given a 10-bit HEVC upload, YouTube's **VP9** renditions have come back with
picture out of order — on trailer 1 the main title played, disappeared for three
seconds under footage from thirty seconds later, then played *again*, which
reads to a viewer as the film looping. The AV1 renditions of the same upload were
correct, as was the master. Reproduced independently in the 1080p60 and 720p60
VP9 renditions; verified by decoding each from frame zero and diffing per second
against the master, because `-ss` seeking on a DASH `webm` lands in the wrong
place and will manufacture a phantom version of this bug.

Deliver a separate upload master. It is a transcode of the finished file, not a
re-render, and it costs about two minutes on the cluster:

```
-c:v libx264 -profile:v high -pix_fmt yuv420p -preset fast -crf 16
-maxrate 100M -bufsize 200M
-x264-params keyint=120:min-keyint=120:scenecut=0:open-gop=0
-color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv
-af apad -shortest -c:a aac -b:a 384k -ar 48000 -ac 2
-movflags +faststart
```

`apad` with `-shortest` is not decoration. Our music ends before the picture
does, so the encoder stops writing audio at the last note and the delivered
track is **shorter than the video** — 112.30 s against 124.31 s on trailer 1.
Local players tolerate it; an ingest pipeline has to invent the difference.
Pad the silence yourself rather than leaving it to be guessed at.

Check the result rather than assuming it: the picture must diff to nothing
against the master, and the peak still has to pass
[the delivery band](#the-delivered-peak-is-trimmed-not-assumed) — transcoding
re-encodes the audio, so the measured peak is a **new** fact each time.

## Burning plates onto a cut

`tools/plate.py` is a separate stage from `render.py`, deliberately: cutting and
titling are different concerns, and keeping them apart means a re-title does not
re-cut. It composites every plate in **one** ffmpeg pass — an `overlay` chain
where each plate is gated by an `enable=between(t,in,out)` expression — and
stream-copies the audio, so titling never costs the soundtrack a second
generation.

Two consequences worth stating:

1. **Plate timings are on the *rendered* timeline**, not the source. `plate.py
   plan` therefore has to be given the same `--max-shot-sec` the render used, or
   every plate after the first trimmed shot lands late.
2. **The plates are rendered at 1920×1080**, the same size `render.py`
   normalizes every clip to, so the overlay needs no scaling and the chrome
   stays pixel-exact.

### Two ways this pass has silently produced an unplated video

Both exit 0 and write a file of the right length, and both are pinned by
tests that inspect the argv.

**Shell quotes in an argv list.** `enable='between(t,1,2)'` is the spelling the
ffmpeg docs use, and it is correct *on a command line*, where the shell strips
the quotes. `burn()` builds an argv list and never sees a shell, so ffmpeg got
the quote characters as part of the expression, failed to parse it, and
disabled every overlay. Unquoted, the commas must be escaped instead
(`between(t\,1\,2)`) or the filtergraph parser reads them as argument
separators.

**A one-frame PNG does not survive a long timeline.** Fed to `overlay` as-is a
still image reaches EOF immediately, and `eof_action=repeat` does not hold that
frame for five minutes: a plate gated to `t=5` draws and the identical plate
gated to `t=269` does not, same file, same graph. Each image input therefore
needs `-loop 1` — bounded with `-t`, because an unbounded loop is an infinite
input and the encode never terminates, and with `-framerate 1`, because the
looped stream is the same still frame at every timestamp and decoding it thirty
times a second only costs time. The **output** needs its own `-t` as well: with
every input the same length there is no unambiguous shortest stream, and the
burn runs long.

## The shim only sees `$HOME`

The shim bind-mounts the home directory, so **a path outside `$HOME` does not
exist as far as the container is concerned**, and the error says so in the most
misleading way available:

```console
$ ffprobe /var/tmp/x.mp4
/var/tmp/x.mp4: No such file or directory
```

The file is right there. Python's `Path.exists()` returns `True`. Only the
containerized process cannot see it.

This bites tests hardest, because **pytest's `tmp_path` lives under `/var/tmp`**.
A check that writes a clip to `tmp_path` and then probes it with `ffprobe` from
`PATH` fails with a missing-file error that has nothing to do with the code under
test. Two ways out, and the second is usually better:

- Keep the fixture under `$HOME`.
- Probe with the **same** command the code resolved, via `find_ffmpeg()`, rather
  than with bare `ffprobe`. `imageio-ffmpeg`'s bundled binary is a real local
  process and sees the whole filesystem. `ffmpeg -i <file>` and a regex over its
  stderr replaces `ffprobe -show_entries` for stream questions.

The same rule applies at render time, which is why `render.py` keeps its
intermediates beside the output rather than in `/tmp`.

## Tests that touch ffmpeg must skip without it

The suite is offline and must pass on a runner with **no ffmpeg at all** — CI
has none. So any check that encodes must skip, not fail:

```python
def _ffmpeg():
    try:
        ffmpeg = render.find_ffmpeg(prefer_container=False)
    except RuntimeError:
        pytest.skip("no ffmpeg available")
    # Resolving a command is not the same as being able to run it.
    try:
        subprocess.run(list(ffmpeg) + ["-version"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("ffmpeg is not runnable here")
    return ffmpeg
```

Both halves matter. `find_ffmpeg` raises only when it can find *nothing*; with
`DESTINY_FFMPEG` set to a path that does not exist it returns happily and the
failure surfaces later as a `FileNotFoundError` from `subprocess`.

And a check that never actually encodes should not resolve ffmpeg at all — pass
a stub command in. Resolution is the part that raises:

```python
render.render(shots, media, out, ffmpeg=["ffmpeg-not-invoked"])
```

Resolution is also what a *fake* has to cover. Faking the function that uses a
binary is not enough when something resolves the binary before calling it —
see [`testing`](skills/testing.md), which also carries the `PATH` sandbox that
reproduces the runner locally in fifty seconds.

## Sources

Technical claims about `-ss` semantics and the concat demuxer's
identical-stream-properties requirement were verified against current FFmpeg
documentation via Context7: `/websites/ffmpeg_documentation`.
