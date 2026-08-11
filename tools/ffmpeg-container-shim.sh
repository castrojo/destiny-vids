#!/usr/bin/env bash
# Containerized ffmpeg/ffprobe shim.
#
# Fedora/Bluefin ships `ffmpeg-free`, which has no H.264 or AAC and fails only
# once decoding starts -- so it looks like a corrupt input file rather than a
# missing codec. This shim puts a full non-free ffmpeg (libx264, libx265,
# libfdk_aac, libvpx, libsvtav1, drawtext, VAAPI) on PATH instead.
#
# Installed as ~/.local/bin/ffmpeg and ~/.local/bin/ffprobe; dispatches on $0.
#
# Runs the image ephemerally rather than `podman exec`-ing into the running
# bluefin-thumbnailer container, for two reasons:
#   1. That container is owned by the thumbnailer service. Borrowing it for
#      long encodes contends with desktop thumbnailing.
#   2. It only bind-mounts $HOME, so /tmp and other paths would be invisible.
#      An ephemeral run controls its own mounts.
#
# Escape hatch: FFMPEG_NO_CONTAINER=1 ffmpeg ...   -> host binary
# Config:       ~/.config/ffmpeg-container.conf
set -euo pipefail

TOOL="$(basename "$0")"

CONF="${XDG_CONFIG_HOME:-$HOME/.config}/ffmpeg-container.conf"
# shellcheck source=/dev/null
[ -r "$CONF" ] && . "$CONF"

IMAGE="${FFMPEG_CONTAINER_IMAGE:-ghcr.io/jrottenberg/ffmpeg:latest}"
CONTAINER="${FFMPEG_CONTAINER_NAME:-bluefin-thumbnailer}"

host_fallback() {
    for candidate in /usr/bin/"$TOOL" /home/linuxbrew/.linuxbrew/bin/"$TOOL"; do
        [ -x "$candidate" ] && exec "$candidate" "$@"
    done
    echo "$TOOL: no containerized or host $TOOL available" >&2
    exit 127
}

[ -n "${FFMPEG_NO_CONTAINER:-}" ] && host_fallback "$@"
command -v podman >/dev/null 2>&1 || host_fallback "$@"

# If the configured image is gone, fall back to the image the thumbnailer
# container is actually running, so a pruned tag doesn't break the shim.
if ! podman image exists "$IMAGE" 2>/dev/null; then
    resolved="$(podman inspect "$CONTAINER" --format '{{.ImageName}}' 2>/dev/null || true)"
    if [ -n "$resolved" ]; then
        IMAGE="$resolved"
    else
        echo "$TOOL: container image '$IMAGE' not found; using host $TOOL" >&2
        host_fallback "$@"
    fi
fi

args=(run --rm -i)

# Interactive only when both ends are a terminal: allocating a TTY otherwise
# corrupts binary data on a pipe (ffmpeg ... - | something).
[ -t 0 ] && [ -t 1 ] && args+=(-t)

# $HOME and /tmp cover essentially every real invocation. $PWD is mounted
# explicitly when it falls outside both, so `cd /mnt/foo && ffmpeg -i in.mp4`
# still works; podman exec could not do this at all.
args+=(-v "$HOME:$HOME")
[ -d /tmp ] && args+=(-v /tmp:/tmp)
case "$PWD" in
    "$HOME"/*|"$HOME"|/tmp/*|/tmp) ;;
    *) args+=(-v "$PWD:$PWD") ;;
esac
args+=(-w "$PWD")

# Hardware encode/decode when the host exposes a render node.
[ -d /dev/dri ] && args+=(--device /dev/dri)

args+=(--entrypoint "$TOOL" "$IMAGE")

exec podman "${args[@]}" "$@"
