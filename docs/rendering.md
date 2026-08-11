# Rendering: getting a working ffmpeg

`tools/render.py` is the only stage that touches actual pixels, and it is the
stage most likely to fail on a Bluefin/Fedora atomic host — for a reason that is
easy to misdiagnose. This documents which ffmpeg to use and why.

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
it falls back to whatever image the running container actually uses rather than
failing.

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

## Fallback: `imageio-ffmpeg`

Off Bluefin, or with no container running, `pip install imageio-ffmpeg` supplies
a full static ffmpeg (H.264 + AAC) with no system packages. It is what
`--no-container` selects here.

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

## Seeking: why `-ss` goes after `-i`

`render.py` uses **output seeking** (`-ss` after `-i`), which decodes from the
start of the file and discards. It is ~2.6x slower than input-side `-ss` on a
two-minute source.

The common justification for this — "input seeking snaps to a keyframe" — is
**stale**. Per the FFmpeg documentation, input seeking moves to the closest
point before the requested position and then *decodes and discards the
intervening segment to ensure accuracy*. Both are accurate.

The real reason is specific to this pipeline: input seeking **rebases output
timestamps to zero**, which shifts the phase of the 29.97 → 30 fps conversion
every clip goes through, changing which source frames get duplicated. Measured
on the same in-point, the two methods produce visibly different frames:

```console
$ ffmpeg -i src.mp4 -ss 69.336 -t 0.968 ...   # 2.486s, framemd5 b8507036...
$ ffmpeg -ss 69.336 -i src.mp4 -t 0.968 ...   # 0.964s, framemd5 2e7dbbdb...
```

Same frame count, different frames. Accuracy wins; the cut list's in-points are
the entire point of the index.

If a future change drops the fps normalization (e.g. all clips from one
source at native rate), input seeking becomes safe and is worth the 2.6x.

## Burning plates onto a cut

`tools/plate.py` is a separate stage from `render.py`, deliberately: cutting and
titling are different concerns, and keeping them apart means a re-title does not
re-cut. It composites every plate in **one** ffmpeg pass — an `overlay` chain
where each plate is gated by `enable='between(t,in,out)'` — and stream-copies
the audio, so titling never costs the soundtrack a second generation.

Two consequences worth stating:

1. **Plate timings are on the *rendered* timeline**, not the source. `plate.py
   plan` therefore has to be given the same `--max-shot-sec` the render used, or
   every plate after the first trimmed shot lands late.
2. **The plates are rendered at 1920×1080**, the same size `render.py`
   normalizes every clip to, so the overlay needs no scaling and the chrome
   stays pixel-exact.

## Sources

Technical claims about `-ss` semantics and the concat demuxer's
identical-stream-properties requirement were verified against current FFmpeg
documentation via Context7: `/websites/ffmpeg_documentation`.
