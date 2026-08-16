#!/usr/bin/env python3
"""Cast the anonymous-Guardian ensemble from a month's Project Bluefin contributors.

The cinematics are full of nameless Guardians. That crowd is this project's
diverse cast, and it gets filled with real people: every ``casting.role ==
"ensemble"`` segment exposes N ``slots``, and this tool walks a shot list in
timeline order handing those slots to the contributors who shipped work that
month — producing one credit TILE per contributor.

Two halves, usable independently:

  roster  — who contributed in a calendar month (via ``gh api``, or offline
            from a JSON file so nothing here needs the network to be testable).
  assign  — deterministically place that roster into a shot list's ensemble
            slots and emit the tile manifest.

Determinism matters: a re-render must not reshuffle who played whom. The same
(month, roster, shot list) always produces the same tiles, because assignment is
a round-robin over a month-seeded rotation of the sorted roster.

Usage:
    python3 tools/ensemble.py roster --month 2026-08
    python3 tools/ensemble.py roster --month 2026-08 --out roster.json
    python3 tools/ensemble.py assign --roster roster.json --dir examples
    python3 tools/ensemble.py assign --roster roster.json --shotlist story.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# `assign` imports tools.derive lazily to read the lead bindings, and running
# this file as a SCRIPT ("python3 tools/ensemble.py assign ...", the form the
# casting skill documents) puts tools/ on sys.path rather than the repo root --
# so that import failed while the tests, which import the package, passed. Same
# guard the other CLI tools carry.
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Repositories whose contributors make up the pool. Override with --repo.
DEFAULT_REPOS = [
    "projectbluefin/bluefin",
    "projectbluefin/bluefin-lts",
    "projectbluefin/common",
    "projectbluefin/dakota",
    "projectbluefin/knuckle",
]

# Bot accounts never get a Guardian tile.
BOT_LOGINS = {"dependabot", "github-actions", "renovate", "mergeraptor", "copilot"}

# The GitHub org whose members are credited as maintainers rather than
# contributors. Derived from the repos above rather than hardcoded twice.
DEFAULT_ORG = DEFAULT_REPOS[0].split("/")[0]


def fetch_org_members(org):
    """Logins in ``org``, via ``gh``. Returns a set, empty if it cannot tell.

    Tries the full member list first and falls back to public members, since an
    unauthenticated or low-scope token can only see the latter. **Failure is
    not "everyone is a contributor"** -- it is "membership is unknown", and the
    caller records that, because silently demoting every maintainer would be an
    incorrect on-screen credit rather than a missing one.
    """
    for endpoint in (f"orgs/{org}/members", f"orgs/{org}/public_members"):
        cmd = ["gh", "api", "--paginate", f"{endpoint}?per_page=100",
               "--jq", ".[].login // empty"]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True,
                                 timeout=120, check=True)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                FileNotFoundError):
            continue
        members = {login for login in out.stdout.split() if login}
        if members:
            return members
    print(f"  ! could not read members of {org} — membership unknown",
          file=sys.stderr)
    return set()


def month_bounds(month):
    """Return ISO 8601 (since, until) timestamps bounding a ``YYYY-MM`` month."""
    year, mon = (int(p) for p in month.split("-"))
    start = dt.datetime(year, mon, 1, tzinfo=dt.timezone.utc)
    end = dt.datetime(year + (mon == 12), (mon % 12) + 1, 1, tzinfo=dt.timezone.utc)
    return start.strftime("%Y-%m-%dT%H:%M:%SZ"), end.strftime("%Y-%m-%dT%H:%M:%SZ")


def is_bot(login):
    low = login.lower()
    return low in BOT_LOGINS or low.endswith("[bot]") or low.endswith("-bot")


def fetch_repo_contributors(repo, since, until):
    """Logins with at least one commit in ``repo`` during the window, via ``gh``.

    Returns ``{login: commit_count}``. A repo that errors (renamed, private,
    no access) yields nothing rather than failing the whole roster — a missing
    repo should cost you a few names, not the month's credits.
    """
    cmd = [
        "gh", "api", "--paginate",
        f"repos/{repo}/commits?since={since}&until={until}&per_page=100",
        "--jq", ".[].author.login // empty",
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=True)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        print(f"  ! {repo}: {type(exc).__name__} — skipped", file=sys.stderr)
        return {}
    counts = {}
    for login in out.stdout.split():
        if not is_bot(login):
            counts[login] = counts.get(login, 0) + 1
    return counts


def build_roster(month, repos=None, org=None, members=None):
    """Collect the month's contributors across ``repos`` into a roster record.

    Each contributor is marked ``org_member``, which is what decides whether
    they are credited as a MAINTAINER or a CONTRIBUTOR Guardian. ``members`` may
    be passed in to keep this offline; otherwise it is fetched once.

    ``org_member`` is a tri-state on purpose: ``None`` means membership could
    not be read, which is not the same as "not a member". The label copy for
    each case lives in vocab/casting.yaml, not here.
    """
    repos = repos or DEFAULT_REPOS
    org = org or DEFAULT_ORG
    if members is None:
        members = fetch_org_members(org)
    known = members is not None and len(members) > 0
    since, until = month_bounds(month)
    totals = {}
    per_repo = {}
    for repo in repos:
        counts = fetch_repo_contributors(repo, since, until)
        per_repo[repo] = sorted(counts)
        for login, n in counts.items():
            totals[login] = totals.get(login, 0) + n
    return {
        "month": month,
        "since": since,
        "until": until,
        "org": org,
        "repos": repos,
        "contributors": [
            {"login": login, "commits": totals[login], "display_name": login,
             "org_member": (login in members) if known else None}
            # Sort by login, not by commit count: the pool is a cast list, not a
            # leaderboard, and a stable alphabetical order keeps assignment
            # reproducible when commit counts shift.
            for login in sorted(totals)
        ],
        "repos_contributors": per_repo,
    }


def month_offset(month, pool_size):
    """Stable per-month rotation offset, so the cast changes month to month.

    Hash-derived rather than sequential so two adjacent months do not merely
    shift by one and hand almost everyone the same Guardian again.
    """
    if pool_size <= 0:
        return 0
    digest = hashlib.sha256(month.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % pool_size


def load_shotlist(path=None, directory=None):
    """Load segments from a story shot list, or from a directory of records.

    A shot list (tools/story.py output) is already in timeline order; a raw
    directory is sorted by ``video_id`` then start time so assignment is stable.
    """
    if path:
        with open(path) as fh:
            data = json.load(fh)
        shots = data.get("shots", data) if isinstance(data, dict) else data
        return [s.get("segment", s) for s in shots]
    segs = []
    for file_path in sorted(glob.glob(os.path.join(directory, "*.json"))):
        with open(file_path) as fh:
            rec = json.load(fh)
        if "segment_id" in rec:
            segs.append(rec)
    segs.sort(key=lambda s: (s.get("video_id", ""), s.get("start_sec", 0)))
    return segs


def _resolve_leads(leads=None):
    """The lead cast map, loaded from vocab/casting.yaml unless supplied."""
    if leads is not None:
        return leads
    from tools.derive import load_leads

    return load_leads()


def lead_people(leads=None):
    """Logins of people cast as a named lead character.

    A person cannot be both a named character and a nameless Guardian in the
    same project: crediting castrojo as an anonymous "Bluefin Blueberry" while
    he is cast as Cayde-6 contradicts the casting, and puts a real person in a
    video their character is not in. Lead bindings therefore remove someone
    from the ensemble pool entirely; they are credited where their character
    actually appears, from the `plate:` block on their binding.

    The match is on the binding's ``github`` login, because a roster
    contributor is only ever identified by login and ``github`` is the field
    vocab/casting.yaml documents as the person's VERIFIED one. ``person`` is a
    normalized snake_case id ("Kelsey Hightower" -> ``kelsey_hightower``), so
    comparing it against a login excludes somebody only when the two happen to
    be spelled alike -- which is why this used to match every multi-word lead
    against nothing at all. It is kept as a SECONDARY match because for some
    bindings the two genuinely are the same string (``castrojo``), and because
    erring toward exclusion under-credits somebody rather than crediting one
    real person twice under two identities.

    A lead with no ``github`` login cannot be excluded by any login at all.
    That gap is not silently accepted: see ``leads_without_login``.
    """
    logins = set()
    for entry in _resolve_leads(leads).values():
        if not entry.get("person"):
            continue
        for candidate in (entry.get("github"), entry.get("person")):
            if candidate:
                logins.add(candidate)
    return logins


def leads_without_login(leads=None):
    """Cast leads carrying no ``github`` login, so no login can exclude them.

    These are the bindings for which ``lead_people`` is guessing: the only
    string it can match on is the snake_case ``person`` id, which is not a
    login. If such a person is in the month's roster under their real login,
    nothing here can tell, and they would be credited as an anonymous Guardian
    while also being cast as a named lead.

    Recording the login is a claim about a real person, so it is not this
    tool's to invent -- the gap is reported and stays visible instead.
    """
    return sorted(
        entry.get("display_name") or entry.get("person")
        for entry in _resolve_leads(leads).values()
        if entry.get("person") and not entry.get("github")
    )


def assign(roster, segments, leads=None):
    """Fill every ensemble slot in ``segments`` from ``roster``.

    Round-robins a month-seeded rotation of the pool, so each contributor is
    placed once before anyone is placed twice. Returns the tile manifest.

    People cast as leads are excluded from the pool -- see ``lead_people``.
    Leads that no login could have excluded are reported in
    ``leads_unverifiable`` rather than left to luck.
    """
    leads = _resolve_leads(leads)
    cast_as_lead = lead_people(leads)
    unverifiable = leads_without_login(leads)
    pool = [c["login"] for c in roster.get("contributors", [])
            if c["login"] not in cast_as_lead]
    excluded = [c["login"] for c in roster.get("contributors", [])
                if c["login"] in cast_as_lead]
    tiles = []
    assignments = []
    if not pool:
        return {"month": roster.get("month"), "pool_size": 0,
                "assignments": [], "tiles": [], "unfilled_slots": 0,
                "cast_as_lead": excluded,
                "leads_unverifiable": unverifiable}

    offset = month_offset(roster["month"], len(pool))
    rotated = pool[offset:] + pool[:offset]
    display = {c["login"]: c.get("display_name") or c["login"]
               for c in roster["contributors"]}
    member = {c["login"]: c.get("org_member") for c in roster["contributors"]}

    cursor = 0
    for seg in segments:
        casting = seg.get("casting") or {}
        if casting.get("role") != "ensemble":
            continue
        slots = int(casting.get("slots") or 0)
        for slot_index in range(slots):
            login = rotated[cursor % len(rotated)]
            cursor += 1
            assignments.append({
                "segment_id": seg.get("segment_id"),
                "video_id": seg.get("video_id"),
                "start_tc": seg.get("start_tc"),
                "end_tc": seg.get("end_tc"),
                "slot": slot_index,
                "login": login,
                "display_name": display[login],
                "org_member": member.get(login),
            })

    by_login = {}
    for item in assignments:
        by_login.setdefault(item["login"], []).append(item["segment_id"])
    tiles = [
        {"login": login, "display_name": display[login], "appearances": segs}
        for login, segs in sorted(by_login.items())
    ]
    # Everyone in the pool should get a tile; if the shot list has fewer slots
    # than contributors, the tail of the rotation goes uncredited and the
    # shortfall is reported rather than silently swallowed.
    uncredited = [login for login in pool if login not in by_login]
    return {
        "month": roster["month"],
        "pool_size": len(pool),
        "slots_filled": len(assignments),
        "assignments": assignments,
        "tiles": tiles,
        "uncredited": uncredited,
        # Reported, not silently omitted: someone missing from the credits
        # because they are cast as a lead should be visible in the output.
        "cast_as_lead": excluded,
        # Leads whose binding carries no `github` login, so no login could
        # have excluded them. A punch-list item, not a failure.
        "leads_unverifiable": unverifiable,
    }


def fmt_roster(roster):
    lines = [f"Ensemble pool for {roster['month']} "
             f"({roster['since'][:10]} .. {roster['until'][:10]})"]
    contributors = roster["contributors"]
    lines.append(f"{len(contributors)} contributor(s) across {len(roster['repos'])} repo(s)")
    for c in contributors:
        lines.append(f"  {c['login']:<24} {c['commits']} commit(s)")
    if not contributors:
        lines.append("  (nobody — check the month, the repo list, and `gh auth status`)")
    return "\n".join(lines)


def fmt_assignment(result):
    lines = [f"Ensemble casting for {result['month']}: "
             f"{result.get('slots_filled', 0)} slot(s) across "
             f"{len(result['tiles'])} contributor(s)"]
    for tile in result["tiles"]:
        lines.append(f"  {tile['display_name']:<24} {len(tile['appearances'])} appearance(s)")
        for seg_id in tile["appearances"]:
            lines.append(f"      {seg_id}")
    if result.get("uncredited"):
        lines.append(f"  UNCREDITED (not enough ensemble slots): "
                     f"{', '.join(result['uncredited'])}")
    if result.get("leads_unverifiable"):
        lines.append(f"  LEADS WITH NO github LOGIN (cannot be excluded by "
                     f"login): {', '.join(result['leads_unverifiable'])}")
    if not result["tiles"]:
        lines.append("  (no ensemble slots found — are segments derived? run tools/derive.py)")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)

    this_month = dt.date.today().strftime("%Y-%m")

    p_roster = sub.add_parser("roster", help="collect a month's contributors")
    p_roster.add_argument("--month", default=this_month, help="YYYY-MM (default: this month)")
    p_roster.add_argument("--repo", action="append", dest="repos",
                          help="repo to scan (repeatable; default: the Bluefin factory)")
    p_roster.add_argument("--out", help="write the roster JSON here")

    p_assign = sub.add_parser("assign", help="cast a roster into ensemble slots")
    p_assign.add_argument("--roster", required=True, help="roster JSON from `roster`")
    p_assign.add_argument("--dir", default=os.path.join(REPO_ROOT, "examples"),
                          help="directory of segment records (default: examples/)")
    p_assign.add_argument("--shotlist", help="story shot list JSON (overrides --dir)")
    p_assign.add_argument("--out", help="write the tile manifest JSON here")

    args = ap.parse_args(argv)

    if args.command == "roster":
        roster = build_roster(args.month, args.repos)
        if args.out:
            with open(args.out, "w") as fh:
                json.dump(roster, fh, indent=2)
            print(f"wrote {args.out}")
        print(fmt_roster(roster))
        return 0

    with open(args.roster) as fh:
        roster = json.load(fh)
    segments = load_shotlist(args.shotlist, args.dir)
    result = assign(roster, segments)
    if args.out:
        with open(args.out, "w") as fh:
            json.dump(result, fh, indent=2)
        print(f"wrote {args.out}")
    print(fmt_assignment(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
