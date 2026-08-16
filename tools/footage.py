#!/usr/bin/env python3
"""Where a master lives, and whether it is still the same file.

``media/`` is gitignored, so nothing in git can prove which picture an act was
cut from. Two things go wrong because of that, and both have happened here:

* **A master is replaced in place.** ``deliver.py`` hashes only committed
  inputs, so an act cut from footage that no longer exists still reports ``ok``.
* **A master changes container.** ``yt_destiny_all_live_action_trailers`` went
  ``.mp4`` -> ``.mkv`` and ``scripts/build_efmb.py``, which built its path as
  ``media/{id}.mp4``, stopped being able to find it at all.

So callers ask for a **video_id**, never a filename::

    python3 tools/footage.py path yt_destiny_all_live_action_trailers
    python3 tools/footage.py digest yt_destiny_all_live_action_trailers

Hashing hundreds of MB on every ``deliver.py status`` is too slow, so the
content digest is cached by ``(path, size, mtime_ns)`` -- the same posture
``tools/conform.py`` takes, for the same reason. A file whose stat has not
moved cannot have changed content without somebody working to defeat the
cache, and the cache is disposable: delete it and the next call rebuilds it.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MEDIA = REPO_ROOT / "media"

# Preference order when a master exists in more than one container: the first
# one found wins, so the answer cannot depend on directory iteration order.
EXTENSIONS = (".mkv", ".mp4", ".webm", ".mov", ".m4v")


def cache_path():
    """Disposable, and outside the repo: a cache is never an input."""
    override = os.environ.get("DESTINY_FOOTAGE_CACHE")
    if override:
        return Path(override)
    root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return root / "destiny-vids" / "footage-digests.json"


def resolve(video_id, media_dir=None):
    """The file for a video_id, whatever container it landed in.

    Returns None when nothing matches -- an absent master is drift to report,
    not an exception to raise, which is the same call `source_digest` makes.
    """
    media = Path(media_dir) if media_dir else MEDIA
    for ext in EXTENSIONS:
        candidate = media / f"{video_id}{ext}"
        if candidate.exists():
            return candidate
    return None


def file_digest(path):
    """SHA-256 of a file's bytes, cached by (path, size, mtime_ns).

    ponytail: whole-file hash, chunked. A head+tail sample would be quicker on
    a 500 MB master, but it cannot see a re-encode that preserves the ends, and
    the cache already makes the second call free.
    """
    path = Path(path)
    st = path.stat()
    key = str(path.resolve())
    stamp = [st.st_size, st.st_mtime_ns]

    cache = {}
    cp = cache_path()
    if cp.exists():
        try:
            cache = json.loads(cp.read_text())
        except (json.JSONDecodeError, OSError):
            cache = {}  # a corrupt cache is rebuilt, never fatal
    hit = cache.get(key)
    if hit and hit.get("stamp") == stamp:
        return hit["digest"]

    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(4 << 20), b""):
            h.update(chunk)
    digest = h.hexdigest()

    cache[key] = {"stamp": stamp, "digest": digest}
    try:
        cp.parent.mkdir(parents=True, exist_ok=True)
        cp.write_text(json.dumps(cache, indent=1, sort_keys=True) + "\n")
    except OSError:
        pass  # an unwritable cache costs speed, never correctness
    return digest


def footage_digest(video_ids, media_dir=None):
    """One digest over an act's footage inputs, in declared order.

    A missing master hashes as absent rather than raising, so a replaced or
    renamed file reports as drift instead of crashing the report -- the same
    contract as `deliver.source_digest`.
    """
    h = hashlib.sha256()
    for video_id in video_ids:
        h.update(video_id.encode())
        path = resolve(video_id, media_dir)
        h.update(file_digest(path).encode() if path else b"\0absent")
    return h.hexdigest()


def missing(video_ids, media_dir=None):
    """The declared ids with no file in media/, in declared order."""
    return [v for v in video_ids if resolve(v, media_dir) is None]


def newer_than(video_ids, path, media_dir=None):
    """The declared masters modified AFTER `path` was written.

    A delivered act that is older than its own footage was cut from a file
    that has since been replaced. mtime is only a hint -- the content digest
    is the authority -- but it is the hint that works before anything has been
    recorded, which is exactly when this goes unnoticed.
    """
    path = Path(path)
    if not path.exists():
        return []
    cutoff = path.stat().st_mtime
    out = []
    for video_id in video_ids:
        found = resolve(video_id, media_dir)
        if found and found.stat().st_mtime > cutoff:
            out.append(video_id)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("command", choices=("path", "digest"))
    ap.add_argument("video_id", nargs="+")
    args = ap.parse_args(argv)

    if args.command == "path":
        rc = 0
        for video_id in args.video_id:
            path = resolve(video_id)
            if path is None:
                print(f"error: no file in media/ for {video_id} "
                      f"(tried {', '.join(EXTENSIONS)})", file=sys.stderr)
                rc = 1
            else:
                # Repo-relative when it is under the repo: callers are shell
                # scripts that run from the root and print this path to the
                # user, and an absolute path there is just noise.
                try:
                    print(path.relative_to(REPO_ROOT))
                except ValueError:
                    print(path)
        return rc

    print(footage_digest(args.video_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
