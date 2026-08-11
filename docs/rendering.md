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
service:

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

### Why the paths just work

The container is started with the user's home bind-mounted **at the same path**:

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
