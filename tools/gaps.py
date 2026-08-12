#!/usr/bin/env python3
"""What in the index is unfinished, and which of it is worth an issue.

The index does not fail loudly when it is incomplete. A video with no segments
is simply absent from every search; a beat with no ``overlays`` derives
``clean = false`` and quietly leaves every cut. Both are the gates working as
designed -- "nobody has looked at this frame" really is not evidence that the
frame is clean -- but the cost is that the repo's unfinished work is invisible
unless somebody goes looking for it.

This is the going-looking. It reports four gaps:

* **unindexed** -- a record in ``videos/`` with no segments at all. Ingested,
  never indexed; contributes nothing to any cut.
* **unreviewed** -- segments that derive ``clean = false`` because ``overlays``
  was never tagged, as distinct from segments correctly rejected for carrying a
  HUD or burned-in text. The distinction matters: the first is work remaining,
  the second is the gate doing its job, and reporting them together would
  invite somebody to "fix" the second.
* **uncast** -- a lead in ``vocab/casting.yaml`` written into the story with
  ``person: null``. Retrieval works; the tile just has nobody's name on it.
* **untagged-character** -- an indexed video where no segment names any
  character. Usually a tagging pass that skipped the axis, which makes the
  whole video invisible to casting.

``--file`` turns each gap into a GitHub issue. Every filed issue carries a
FINGERPRINT line -- a stable id for the gap, not for its current numbers -- so
a rerun edits the issue it already opened rather than filing a second one.
Numbers move as work lands; the gap is the same gap. An issue whose gap has
closed is left open with a comment rather than closed automatically: a robot
that opens issues and a robot that closes them are very different amounts of
trust, and only the first one is being asked for here.

Gaps already tracked by a human-written issue are skipped. That is not a nicety
-- issues #5, #6 and #7 exist and are owned by somebody, and re-filing their
contents under a robot's fingerprint would bury the human's version.

    python3 tools/gaps.py                  # report
    python3 tools/gaps.py --json
    python3 tools/gaps.py --file           # open/update issues
    python3 tools/gaps.py --file --dry-run # show what --file would do
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.derive import DISQUALIFYING_OVERLAYS, load_leads  # noqa: E402
from tools.search import load_segments  # noqa: E402

FINGERPRINT_PREFIX = "gap-fingerprint:"
BOT_LABEL = "triage"


def load_videos(directory):
    """Every video-level record in ``directory``, keyed by video_id."""
    videos = {}
    for path in sorted(glob.glob(os.path.join(directory, "*.json"))):
        with open(path, encoding="utf-8") as fh:
            record = json.load(fh)
        if "video_id" in record and "segment_id" not in record:
            videos[record["video_id"]] = record
    return videos


PLACEHOLDER_URL_MARKERS = ("youtu.be/unknown", "example.com")


def _is_fetchable(record):
    """Whether this record names footage that could actually be indexed.

    ``tools/ingest.py --id ... --title ...`` builds a record offline, without a
    URL, so the README's own example leaves behind a record whose
    ``youtube_url`` is ``https://youtu.be/unknown``. It is a documentation
    artifact, not unfinished work: there is no video to fetch, so reporting it
    as an unindexed gap would file an issue nobody can ever close.
    """
    url = record.get("youtube_url") or ""
    return bool(url) and not any(m in url for m in PLACEHOLDER_URL_MARKERS)


def _segments_by_video(segments):
    by_video = {}
    for segment in segments:
        by_video.setdefault(segment.get("video_id"), []).append(segment)
    return by_video


def _is_unreviewed(segment):
    """A beat that is unclean only because nobody tagged its overlays.

    A segment that carries ``hud`` or ``burned_text`` is a correct rejection
    and is not a gap. A segment with no ``overlays`` key at all has never been
    looked at, which is.
    """
    overlays = segment.get("overlays")
    if overlays is None:
        return True
    return not (set(overlays) & DISQUALIFYING_OVERLAYS) and not segment.get("clean", False)


def find_gaps(videos_dir=None, segments_dir=None, casting_path=None):
    """Every gap in the index, as a list of dicts with stable fingerprints."""
    videos = load_videos(str(videos_dir or (REPO_ROOT / "videos")))
    segments = load_segments(str(segments_dir or (REPO_ROOT / "segments")))
    by_video = _segments_by_video(segments)
    gaps = []

    for video_id, record in sorted(videos.items()):
        shots = by_video.get(video_id) or []
        if not shots:
            if not _is_fetchable(record):
                continue
            gaps.append({
                "kind": "unindexed",
                "fingerprint": f"unindexed:{video_id}",
                "video_id": video_id,
                "title": f"{video_id} is ingested but not indexed",
                "detail": (
                    f"`videos/{video_id}.json` exists ({record.get('title', '')!r}) "
                    "but no segments reference it, so the video contributes "
                    "nothing to any search or cut."
                ),
                "counts": {"segments": 0},
                "automatable": "partly",
            })
            continue

        unreviewed = [s for s in shots if _is_unreviewed(s)]
        if unreviewed:
            gaps.append({
                "kind": "unreviewed",
                "fingerprint": f"unreviewed:{video_id}",
                "video_id": video_id,
                "title": (
                    f"{video_id}: {len(unreviewed)} of {len(shots)} beats "
                    "still unreviewed"
                ),
                "detail": (
                    f"{len(unreviewed)} of {len(shots)} segments carry no "
                    "`overlays` and therefore derive `clean = false`, keeping "
                    "them out of every cut. That is the gate working rather "
                    "than a defect, but the footage is unusable until somebody "
                    "reviews the keyframes."
                ),
                "counts": {"segments": len(shots), "unreviewed": len(unreviewed)},
                "automatable": "partly",
            })

        if not any(s.get("character") for s in shots):
            gaps.append({
                "kind": "untagged-character",
                "fingerprint": f"untagged-character:{video_id}",
                "video_id": video_id,
                "title": f"{video_id}: no segment names a character",
                "detail": (
                    f"All {len(shots)} segments are indexed, but none carries a "
                    "`character`, so the video is invisible to casting and no "
                    "lead can be cut from it."
                ),
                "counts": {"segments": len(shots)},
                "automatable": "no",
            })

    leads = load_leads(casting_path)
    uncast = sorted(k for k, v in leads.items() if not v.get("person"))
    if uncast:
        gaps.append({
            "kind": "uncast",
            "fingerprint": "uncast:leads",
            "video_id": None,
            "title": f"{len(uncast)} written leads are still uncast",
            "detail": (
                "These characters are written into the story in "
                "`vocab/casting.yaml` but have `person: null`, so retrieval "
                "identifies them and their tile has no name on it: "
                + ", ".join(f"`{k}`" for k in uncast)
                + "."
            ),
            "counts": {"uncast": len(uncast)},
            "automatable": "no",
        })
    return gaps


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------

def format_report(gaps):
    """The gaps as text, grouped by kind."""
    if not gaps:
        return "no gaps: every ingested video is indexed, reviewed and cast."
    lines = []
    for kind in ("unindexed", "unreviewed", "untagged-character", "uncast"):
        of_kind = [g for g in gaps if g["kind"] == kind]
        if not of_kind:
            continue
        lines.append(f"{kind} ({len(of_kind)})")
        for gap in of_kind:
            lines.append(f"  {gap['title']}")
    return "\n".join(lines)


def issue_body(gap):
    """The body of the issue this gap files, fingerprint included."""
    automatable = gap["automatable"]
    blocked = {
        "no": "Needs human judgement; an agent should not attempt it unattended.",
        "partly": "The mechanical half is scripted; the visual judgement is not.",
        "yes": "",
    }[automatable]
    return "\n".join([
        f"**What:** {gap['detail']}",
        "",
        "**Reproduction:**",
        "```bash",
        "python3 tools/gaps.py",
        "```",
        "",
        f"**Automatable:** {automatable}. {blocked}".rstrip(),
        "",
        "---",
        f"<!-- {FINGERPRINT_PREFIX} {gap['fingerprint']} -->",
        "_Filed by `tools/gaps.py`. Reruns edit this issue rather than filing "
        "another; the numbers above move as work lands._",
    ])


def fingerprint_of(body):
    """The gap fingerprint recorded in an issue body, or None."""
    match = re.search(rf"{re.escape(FINGERPRINT_PREFIX)}\s*(\S+)", body or "")
    return match.group(1) if match else None


def covered_by_human_issue(gap, issues):
    """Whether a person already filed this gap under their own words.

    Matching is on the video id as a whole token in an issue that has no
    fingerprint of its own -- i.e. one a human wrote. Issue #7 is the worked
    example: it describes exactly the `unreviewed` gap for one video, and
    filing a robot copy beside it would bury the version somebody is working
    from.

    Token matching rather than a substring, because video ids nest:
    ``yt_destiny_2_beyond_light_reveal_trailer`` contains
    ``yt_destiny_2_beyond_light``, and a plain ``in`` would let an issue about
    one video silence the gaps of another.
    """
    video_id = gap.get("video_id")
    if not video_id:
        return False
    pattern = re.compile(rf"(?<![\w-]){re.escape(video_id)}(?![\w-])")
    for issue in issues:
        if fingerprint_of(issue.get("body")):
            continue
        haystack = f"{issue.get('title', '')}\n{issue.get('body', '')}"
        if pattern.search(haystack):
            return True
    return False


# --------------------------------------------------------------------------
# GitHub
# --------------------------------------------------------------------------

def _gh(args, check=True):
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=check)


def fetch_open_issues():
    out = _gh(["issue", "list", "--state", "open", "--limit", "200",
               "--json", "number,title,body"])
    return json.loads(out.stdout or "[]")


def file_gaps(gaps, issues, dry_run=False):
    """Open or update one issue per gap. Returns a list of action strings."""
    existing = {}
    for issue in issues:
        fingerprint = fingerprint_of(issue.get("body"))
        if fingerprint:
            existing[fingerprint] = issue
    actions = []
    for gap in gaps:
        if covered_by_human_issue(gap, issues):
            actions.append(f"skip (a human already filed it): {gap['title']}")
            continue
        body = issue_body(gap)
        issue = existing.get(gap["fingerprint"])
        if issue:
            actions.append(f"update #{issue['number']}: {gap['title']}")
            if not dry_run:
                _gh(["issue", "edit", str(issue["number"]),
                     "--title", gap["title"], "--body", body])
        else:
            actions.append(f"open: {gap['title']}")
            if not dry_run:
                _gh(["issue", "create", "--title", gap["title"],
                     "--body", body, "--label", BOT_LABEL])
    return actions


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="machine-readable gaps")
    parser.add_argument("--file", action="store_true",
                        help="open or update a GitHub issue per gap")
    parser.add_argument("--dry-run", action="store_true",
                        help="with --file, print what would happen and stop")
    parser.add_argument("--videos-dir", default=None)
    parser.add_argument("--segments-dir", default=None)
    args = parser.parse_args(argv)

    gaps = find_gaps(args.videos_dir, args.segments_dir)

    if args.file:
        try:
            issues = fetch_open_issues()
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            print(f"cannot reach GitHub, so nothing was filed: {exc}", file=sys.stderr)
            return 2
        for action in file_gaps(gaps, issues, dry_run=args.dry_run):
            print(action)
        return 0

    print(json.dumps(gaps, indent=2) if args.json else format_report(gaps))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
