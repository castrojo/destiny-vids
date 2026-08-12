#!/usr/bin/env python3
"""Sync the labels the issue pipeline runs on.

Work in this repo moves on GitHub issues, and an agent picking one up reads
its state from the label alone, so the set is deliberately tiny. Characters
are NOT labels and never will be: casting lives in the `brief` block in the
issue body, keyed by the leads in vocab/casting.yaml — a character/* label
would be a second, diverging source of truth about a real person.

Beyond the four state labels there are three triage axes, and each earns its
place by answering a question the state labels cannot:

  area/*      which stage of the pipeline the work lands in, so an agent can
              pick up the work it is equipped for. These mirror the skills in
              docs/skills/, not an invented taxonomy.
  size/*      the cost of the work, so a backlog can be read at a glance
              instead of re-estimated by every reader. Thresholds are in the
              descriptions and are agent-hours, not calendar time.
  priority/*  the running order. Ordering lives on the issue rather than in a
              planning file, for the same reason the backlog does: a file
              goes stale and misleads the next agent.

An area is a routing hint, never a claim about a person or a frame, so
mislabelling one costs a re-read and nothing worse. That is the test a new
axis has to pass before it is added here.

Three classes of work here are permanently not automatable (visual judgement
on a frame, a claim about a real person, a licensing decision), so
`automatable/no` is not a sad label: "not automatable, stopping" is a
first-class successful outcome.

--check compares the owned set against the live repo via `gh label list`.
If gh is missing, unauthenticated or the network is down, it prints a skip
notice and exits 0, so CI without a token does not fail spuriously. --write
creates or edits to match; there a broken gh is an error, since a write was
explicitly asked for.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# The whole owned set. Anything else on the repo (GitHub's defaults, etc.)
# is none of this script's business.
LABELS = [
    {
        "name": "triage",
        "color": "fbca04",
        "description": "Filed, nobody has looked at it yet.",
    },
    {
        "name": "agent-ready",
        "color": "0e8a16",
        "description": "Enough detail for an agent to start.",
    },
    {
        "name": "blocked",
        "color": "b60205",
        "description": "Waiting on an owner decision.",
    },
    {
        "name": "automatable/no",
        "color": "6b7280",
        "description": "Needs human judgement; will never be automated. "
                       "Stopping here is a first-class outcome.",
    },

    # --- area: which stage of the pipeline, mirroring docs/skills/ ---------
    {
        "name": "area/indexing",
        "color": "1d76db",
        "description": "Ingest, shot detection, keyframes, tagging.",
    },
    {
        "name": "area/cut",
        "color": "1d76db",
        "description": "Producing one video: outline, cut list, render.",
    },
    {
        "name": "area/casting",
        "color": "1d76db",
        "description": "Lead bindings and the ensemble in vocab/casting.yaml.",
    },
    {
        "name": "area/plates",
        "color": "1d76db",
        "description": "On-screen copy: nameplates, title cards, chat cards.",
    },
    {
        "name": "area/rights",
        "color": "1d76db",
        "description": "Licensing, attribution, and what may be published.",
    },
    {
        "name": "area/tooling",
        "color": "1d76db",
        "description": "The pipeline itself: tools, schema, vocab, docs.",
    },

    # --- size: agent-hours, so a backlog reads without re-estimating ------
    {
        "name": "size/S",
        "color": "c2e0c6",
        "description": "Under 2 agent-hours.",
    },
    {
        "name": "size/M",
        "color": "c2e0c6",
        "description": "2 to 8 agent-hours.",
    },
    {
        "name": "size/L",
        "color": "c2e0c6",
        "description": "8 to 24 agent-hours.",
    },
    {
        "name": "size/XL",
        "color": "c2e0c6",
        "description": "Over 24 agent-hours; split it before starting.",
    },

    # --- priority: the running order, kept on the issue not in a file -----
    {
        "name": "priority/now",
        "color": "d93f0b",
        "description": "Work the top of the queue. Start here.",
    },
    {
        "name": "priority/next",
        "color": "e99695",
        "description": "Queued behind the current work.",
    },
    {
        "name": "priority/later",
        "color": "f9d0c4",
        "description": "Real work, not yet scheduled.",
    },
]


class GhUnavailable(Exception):
    """gh is missing, unauthenticated, or the network is down."""


def _gh(args):
    """Run gh and return stdout, raising GhUnavailable on any failure."""
    if shutil.which("gh") is None:
        raise GhUnavailable("the gh CLI is not installed")
    try:
        result = subprocess.run(["gh", *args],
                                capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        detail = e.stderr.strip() or str(e)
        raise GhUnavailable(f"`gh {args[0]}` failed "
                            f"(unauthenticated or offline?): {detail}") from e
    return result.stdout


def repo_labels():
    """The labels the live repo carries, as gh reports them."""
    out = _gh(["label", "list", "--json", "name,color,description",
               "--limit", "200"])
    try:
        return json.loads(out)
    except json.JSONDecodeError as e:
        raise GhUnavailable(f"could not parse `gh label list` output: {e}") \
            from e


def drift(desired, actual):
    """Owned-label drift: labels that are missing, or whose color or
    description differs. Labels this script does not own are ignored — it
    manages its own set, not the whole namespace.

    gh reports colors without '#', and case varies between the API and this
    file, so colors compare case-insensitively.
    """
    actual_by_name = {label["name"]: label for label in actual}
    problems = []
    for label in desired:
        have = actual_by_name.get(label["name"])
        if have is None:
            problems.append({"name": label["name"], "kind": "missing"})
            continue
        diffs = {}
        if str(have.get("color", "")).lower() != label["color"].lower():
            diffs["color"] = (have.get("color"), label["color"])
        if have.get("description", "") != label["description"]:
            diffs["description"] = (have.get("description"),
                                    label["description"])
        if diffs:
            problems.append({"name": label["name"], "kind": "changed",
                             "diffs": diffs})
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Sync the repo's owned labels.")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true",
                       help="report drift against the live repo (exit 1 on "
                            "drift, 0 when in sync or when gh is unusable)")
    group.add_argument("--write", action="store_true",
                       help="create or update the owned labels via "
                            "gh label create/edit")
    args = ap.parse_args(argv)

    try:
        actual = repo_labels()
    except GhUnavailable as e:
        if args.check:
            print(f"SKIP: {e} — label drift unchecked, nothing written.")
            return 0
        print(f"error: {e}", file=sys.stderr)
        return 1

    problems = drift(LABELS, actual)

    if args.check:
        if not problems:
            print(f"labels in sync ({len(LABELS)} owned)")
            return 0
        for p in problems:
            if p["kind"] == "missing":
                print(f"MISSING: {p['name']}")
            else:
                for field, (have, want) in sorted(p["diffs"].items()):
                    print(f"CHANGED: {p['name']} {field}: {have!r} -> {want!r}")
        print("Run: python3 scripts/sync_labels.py --write",
              file=sys.stderr)
        return 1

    # --write
    if not problems:
        print(f"labels already in sync ({len(LABELS)} owned)")
        return 0
    wanted = {label["name"]: label for label in LABELS}
    for p in problems:
        label = wanted[p["name"]]
        verb = "create" if p["kind"] == "missing" else "edit"
        subprocess.run(["gh", "label", verb, label["name"],
                        "--color", label["color"],
                        "--description", label["description"]],
                       check=True)
        print(f"{verb}d {label['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
