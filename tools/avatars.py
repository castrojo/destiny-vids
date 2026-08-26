#!/usr/bin/env python3
"""The credits' avatar cache: fetching it politely, and getting it from CI.

Act VIII names about five hundred people and puts a face beside every one of
them. The renderer never touches the network -- ``tools.credits.avatar`` reads
``renders/avatars/<login>.png`` and degrades to a ring -- so the whole question
is how that directory gets filled without hammering github.com.

## What this fixes

The first version asked for every login on every run, one request each, with no
record of what it had already learned. Five hundred serial requests, repeated in
full whenever anything about the manifest changed, and a deleted account was
re-requested forever.

Three things make a re-run nearly free, and all three depend on ``index.json``:

* **Conditional requests.** A cached face is revalidated with
  ``If-None-Match``. A ``304`` is a header exchange -- no image, no decode, and
  the file on disk is already right.
* **Negative caching.** A ``404`` is an answer: that login has no avatar, or no
  account. It is recorded and not asked again for ``GONE_TTL``.
* **Backoff that reads the response.** On ``403``/``429`` the server says when
  to come back -- ``Retry-After``, else ``x-ratelimit-reset``. That is obeyed,
  with a cap, and after ``MAX_SLEEP_TOTAL`` of waiting the run STOPS and reports
  what is still missing. It does not block the build: a face nobody fetched is
  a ring, which is what the renderer already draws.

## Where it should actually run

Not here. ``.github/workflows/avatars.yml`` does this on a runner with
``${{ github.token }}`` -- the built-in token, never a PAT -- warms an
``actions/cache`` entry keyed on the login set, and uploads the directory as the
``avatars`` artifact. ``pull_from_actions()`` brings that back with
``gh run download``, so a workstation build spends one request instead of five
hundred. Every step of that degrades: no ``gh``, no network, no artifact, and
the direct fetch below still works.

    python3 -m tools.avatars --from-actions   # pull CI's cache (one request)
    python3 -m tools.avatars                  # fetch what is missing, politely
    python3 -m tools.avatars --revalidate     # re-check every cached face
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import credits as C  # noqa: E402

# The cache location has ONE owner -- ``tools.credits`` -- and is read through
# these two, never captured at import. A test that redirects the cache does it
# by moving ``C.AVATAR_DIR``, and both the renderer and the fetcher follow.
def avatar_dir():
    return C.AVATAR_DIR


def index_path():
    return avatar_dir() / "index.json"

# github.com/<login>.png is the avatar redirector, not the REST API: it needs no
# token and counts against no documented API budget. It is still rate limited in
# practice, which is what everything below is for.
AVATAR_URL = "https://github.com/{login}.png?size=256"
USER_AGENT = "destiny-vids credits (act VIII avatar cache)"

# A face on disk under this many bytes is a truncated download, not an avatar.
MIN_BYTES = 512

# How long a 404 is believed. Accounts do come back, and a deleted one is not
# worth a request per build until it does.
GONE_TTL = 30 * 24 * 3600
# How long a cached face goes before it is revalidated at all. A 304 is cheap
# but it is not free, and a PFP is not urgent.
FRESH_FOR = 14 * 24 * 3600

# Politeness, and the ceiling on it.
SPACING = 0.12          # seconds between requests, minimum
MAX_ATTEMPTS = 4        # per login, across throttles
MAX_SLEEP = 60.0        # one wait
MAX_SLEEP_TOTAL = 240.0 # all waits in a run, before it gives up and reports

# The workflow, and the artifact it publishes. Defined ONCE: the downloader and
# the upload step must not drift apart, and a test asserts they have not.
WORKFLOW = "avatars.yml"
ARTIFACT = "avatars"


def _manifest_entries(manifest):
    if isinstance(manifest, dict):
        return list(manifest.get("plates", manifest.get("cards", [])))
    return list(manifest or [])


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def required_avatar_logins(manifest):
    """Canonical logins whose portrait is required by a manifest."""
    from tools import identity

    logins = []
    for entry in _manifest_entries(manifest):
        if not entry.get("avatar_required"):
            continue
        avatar = entry.get("avatar")
        if not avatar:
            continue
        login = identity.canonical_login(Path(avatar).stem)
        logins.append(login)
    return list(dict.fromkeys(logins))


def required_avatar_logins_for_dialogue(video_id):
    """Canonical logins resolved by the live dialogue record for ``video_id``."""
    from tools import dialogue, identity

    logins = []
    for cue in dialogue.load_dialogue(video_id).get("cues", []):
        person = identity.person_for_character(cue.get("character", ""))
        if person and person.github_id:
            logins.append(person.login)
    return list(dict.fromkeys(logins))


def prepare_manifest_avatars(manifest, strict=False):
    """Drop plates whose required portrait is missing and record why."""
    prepared = copy.deepcopy(manifest)
    findings = []
    entries = _manifest_entries(prepared)
    kept = []
    for entry in entries:
        avatar = entry.get("avatar")
        if entry.get("avatar_required") and avatar and not have(Path(avatar).stem):
            findings.append({
                "plate_id": entry["id"],
                "speaker": entry.get("speaker") or entry.get("name"),
                "avatar": avatar,
                "status": "omitted_missing_required_avatar",
            })
            continue
        kept.append(entry)
    if findings and strict:
        raise FileNotFoundError(
            ", ".join(f"{item['plate_id']} ({item['avatar']})" for item in findings)
        )
    if isinstance(prepared, dict):
        if "plates" in prepared:
            prepared["plates"] = kept
        elif "cards" in prepared:
            prepared["cards"] = kept
        prepared.setdefault("unresolved", []).extend(findings)
    else:
        prepared = kept
    return prepared, findings


def requested_logins(manifest=None, dialogue_video_ids=None, credits_manifest=None):
    """Union the required logins across the selected inputs."""
    logins = []
    if manifest is not None:
        logins.extend(required_avatar_logins(manifest))
    for video_id in dialogue_video_ids or []:
        logins.extend(required_avatar_logins_for_dialogue(video_id))
    if credits_manifest is not None:
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import build_credits as B

        logins.extend(B.avatar_logins(credits_manifest))
    return list(dict.fromkeys(logins))


def load_index():
    """What is known about each login: etag, outcome, when it was checked."""
    try:
        data = json.loads(index_path().read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_index(index):
    avatar_dir().mkdir(parents=True, exist_ok=True)
    index_path().write_text(json.dumps(index, indent=1, sort_keys=True) + "\n")


def have(login):
    """Is there a usable image on disk for ``login``?"""
    path = avatar_dir() / f"{login}.png"
    return path.exists() and path.stat().st_size >= MIN_BYTES


def due(login, index, now=None, revalidate=False):
    """Should this login be asked about at all?

    The three answers this can give are the whole point of the index: skip a
    face that is fresh, skip a login that is known gone, ask about the rest.
    """
    now = time.time() if now is None else now
    row = index.get(login) or {}
    if row.get("status") == "gone" and now - row.get("checked", 0) < GONE_TTL:
        return False
    if not have(login):
        return True
    if revalidate:
        return True
    return now - row.get("checked", 0) >= FRESH_FOR


def _retry_after(headers, now):
    """How long the server asked us to wait, in seconds, or ``None``.

    ``Retry-After`` first because it is the direct instruction; the rate-limit
    reset is a timestamp and only means anything if it is in the future.
    """
    value = headers.get("Retry-After")
    if value:
        try:
            return max(0.0, float(value))
        except ValueError:
            pass
    reset = headers.get("x-ratelimit-reset")
    if reset:
        try:
            return max(0.0, float(reset) - now)
        except ValueError:
            pass
    return None


class Budget:
    """The run's patience, in seconds. Exhausting it ends the run, not the build."""

    def __init__(self, total=MAX_SLEEP_TOTAL, sleep=time.sleep, clock=time.time):
        self.left = total
        self._sleep = sleep
        self._clock = clock

    def wait(self, seconds):
        """Sleep for ``seconds``, capped. False when there is no patience left."""
        seconds = min(max(0.0, seconds), MAX_SLEEP)
        if seconds > self.left:
            return False
        self.left -= seconds
        self._sleep(seconds)
        return True

    def now(self):
        return self._clock()


def fetch_one(login, index, budget, opener=None):
    """Fetch or revalidate one avatar. Returns the outcome as a string.

    ``fetched``  -- new bytes on disk.
    ``fresh``    -- the server said 304; the file was already right.
    ``gone``     -- 404, recorded so it is not asked again for a month.
    ``throttled``-- the budget ran out; nothing was written.
    ``failed``   -- anything else, which is not fatal to anybody.
    """
    opener = opener or urllib.request.urlopen
    path = avatar_dir() / f"{login}.png"
    row = dict(index.get(login) or {})

    for _attempt in range(MAX_ATTEMPTS):
        headers = {"User-Agent": USER_AGENT}
        if row.get("etag") and have(login):
            headers["If-None-Match"] = row["etag"]
        req = urllib.request.Request(AVATAR_URL.format(login=login),
                                     headers=headers)
        try:
            with opener(req, timeout=20) as resp:
                payload = resp.read()
                etag = resp.headers.get("ETag")
            if len(payload) < MIN_BYTES:
                row.update(status="failed", checked=budget.now())
                index[login] = row
                return "failed"
            avatar_dir().mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            row.update(status="have", etag=etag, bytes=len(payload),
                       checked=budget.now())
            index[login] = row
            return "fetched"
        except urllib.error.HTTPError as exc:
            if exc.code == 304:
                row.update(status="have", checked=budget.now())
                index[login] = row
                return "fresh"
            if exc.code == 404:
                row.update(status="gone", checked=budget.now())
                index[login] = row
                return "gone"
            if exc.code in (403, 429):
                wait = _retry_after(exc.headers or {}, budget.now())
                # No instruction from the server is not permission to retry
                # immediately: back off anyway, and let the budget end the run.
                if not budget.wait(wait if wait is not None else 5.0):
                    return "throttled"
                continue
            row.update(status="failed", checked=budget.now())
            index[login] = row
            return "failed"
        except OSError:
            if not budget.wait(2.0):
                return "throttled"
    return "throttled"


def fetch(logins, verbose=True, revalidate=False, opener=None, budget=None,
          spacing=SPACING, sleep=time.sleep):
    """Fill the cache for ``logins``. Never raises, never blocks a build.

    Returns the tally: what was fetched, revalidated, skipped, and what is
    still missing when the run stops early.
    """
    index = load_index()
    budget = budget or Budget()
    tally = {"fetched": 0, "fresh": 0, "gone": 0, "skipped": 0,
             "failed": 0, "throttled": 0}
    pending = []

    for login in dict.fromkeys(logins):
        if not due(login, index, now=budget.now(), revalidate=revalidate):
            tally["skipped"] += 1
            continue
        if tally["throttled"]:
            # The budget is spent. Everything after this is reported, not
            # requested -- five hundred more 403s help nobody.
            pending.append(login)
            continue
        outcome = fetch_one(login, index, budget, opener=opener)
        tally[outcome] = tally.get(outcome, 0) + 1
        if outcome == "throttled":
            pending.append(login)
        elif spacing:
            sleep(spacing)

    save_index(index)
    missing = [n for n in dict.fromkeys(logins) if not have(n)]
    if verbose:
        print(f"avatars: {tally['fetched']} fetched, {tally['fresh']} revalidated, "
              f"{tally['skipped']} already current, {tally['gone']} with no "
              f"account, {tally['failed']} failed")
        if pending:
            print(f"note: rate limited with {len(pending)} still to check; "
                  f"run again later or let {WORKFLOW} do it. "
                  f"{len(missing)} face(s) render as a ring until then.",
                  file=sys.stderr)
    return tally, missing


# --- the CI cache ----------------------------------------------------------

def pull_from_actions(verbose=True, runner=subprocess.run):
    """Unpack CI's avatar artifact into the cache. One request, not five hundred.

    Degrades at every step -- no ``gh``, not logged in, no successful run yet,
    artifact expired -- because the direct fetch above still works and a credit
    roll must build with none of this.
    """
    avatar_dir().mkdir(parents=True, exist_ok=True)
    cmd = ["gh", "run", "download", "--repo", "castrojo/destiny-vids",
           "--name", ARTIFACT, "--dir", str(avatar_dir())]
    try:
        done = runner(cmd, capture_output=True, text=True)
    except (OSError, FileNotFoundError) as exc:
        if verbose:
            print(f"note: no gh ({exc}); fetching directly instead.",
                  file=sys.stderr)
        return False
    if done.returncode != 0:
        if verbose:
            print(f"note: no avatar artifact to download "
                  f"({(done.stderr or '').strip()}); fetching directly instead.",
                  file=sys.stderr)
        return False
    if verbose:
        print(f"avatars: unpacked CI's {ARTIFACT} artifact into {avatar_dir()}")
    return True


def main(argv=None):
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest",
                    help="fetch or prepare against this plate manifest")
    ap.add_argument("--dialogue", action="append", default=[],
                    help="include one dialogue/<video_id>/dialogue.json identity set")
    ap.add_argument("--credits-manifest",
                    help="include this credits manifest's contributor login set")
    ap.add_argument("--prepare",
                    help="write a persistent burn manifest with missing required portraits omitted")
    ap.add_argument("--from-actions", action="store_true",
                    help="download CI's cache first, then fill any gaps")
    ap.add_argument("--revalidate", action="store_true",
                    help="re-check every cached face, not just the stale ones")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    manifest = _load_json(args.manifest) if args.manifest else None
    credits_manifest = (
        _load_json(args.credits_manifest)
        if args.credits_manifest
        else None
    )
    logins = requested_logins(
        manifest=manifest,
        dialogue_video_ids=args.dialogue,
        credits_manifest=credits_manifest,
    )
    if not (args.manifest or args.dialogue or args.credits_manifest):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import build_credits as B

        credits_manifest = json.loads(B.MANIFEST.read_text())
        logins = requested_logins(credits_manifest=credits_manifest)

    if args.prepare:
        if manifest is None:
            raise SystemExit("--prepare requires --manifest")
        prepared, findings = prepare_manifest_avatars(manifest)
        Path(args.prepare).write_text(
            json.dumps(prepared, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        if not args.quiet:
            kept = len(_manifest_entries(prepared))
            print(f"avatars: wrote {args.prepare} ({kept} kept, {len(findings)} omitted)")
        return 0

    if logins:
        if args.from_actions:
            pull_from_actions(verbose=not args.quiet)
        _tally, missing = fetch(logins, verbose=not args.quiet,
                                revalidate=args.revalidate)
        if missing and not args.quiet:
            print(f"{len(missing)} of {len(logins)} logins have no cached face.")
    elif not args.quiet:
        print("avatars: no required logins")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
