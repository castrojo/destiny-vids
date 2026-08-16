#!/usr/bin/env python3
"""The delivery graph: inputs -> master -> Prod/ -> megacut/ -> 10mb/.

`~/Videos/Wolves/` is the owner's delivery workspace, and for a long time its
freshness was maintained by hand: `Prod/README.md` prescribed a manual
`ln -f` and a manual `md5sum *.mp4 > CHECKSUMS.md5`, and nothing noticed when
either was skipped. What actually happened, measured 2026-08-13: act VI was
re-linked to a new master at 15:26 and `CHECKSUMS.md5` (13:22) went stale
under it; the delivered megacut (v0.8, 13:43) did not contain the new act VI;
the README named a master (v2) the link no longer pointed at (v3); and act
II's only twin lived in a worktree whose merge would delete it. The hardlinks
were all intact -- the drift was everything DOWNSTREAM of `Prod/`, and the
README's "no possible drift" claim was falsified. This tool is the graph that
notices:

    python3 tools/deliver.py status            # what is stale and why
    python3 tools/deliver.py status --check    # the same, as a gate (exit 1)
    python3 tools/deliver.py status --sources-only --check   # the CI gate
    python3 tools/deliver.py publish           # re-link Prod/, checksums, README
    python3 tools/deliver.py build --dry-run   # what a rebuild would run
    python3 tools/deliver.py build             # megacut + social copies, stale only
    python3 tools/deliver.py build --watch 60  # keep it fresh, forever

The rung before the master
--------------------------
The graph used to start at a **rendered file**, which cannot see the thing
that goes stale first: somebody edits a shotlist, a dialogue record, a plate
manifest or `vocab/casting.yaml`, and the delivered act silently predates its
own inputs. Acts IV and V sat behind a dictated dialogue round for days that
way (#118) and nothing noticed, because nothing was looking.

So each act declares its committed `sources` in the delivery map, hashed into
a `source_digest` that `publish` stamps. An edit to any of them reports the
act as **stale** and names the inputs. Two honest non-answers exist and are
distinguished on purpose: `sources: []` means the act has **no committed
inputs at all** (cut outside the repo -- a finding, and it must carry a note
saying so), while a missing `sources` key is **undeclared** and reported
rather than assumed fresh.

This rung reads only committed files, so `--sources-only` needs no footage and
no `~/Videos` and runs on CI, where every other check here has to degrade to a
report.

The footage rung, and why it is separate
----------------------------------------
`sources` covers what git tracks. It cannot cover `media/`, which is
gitignored, so an act cut from picture that has since been replaced still
reported `ok`: the Final Shape gameplay trailer and the live-action trailer
compilation were both swapped on 2026-08-15 and nothing said a word (#229).
Worse, the swap moved both from `.mp4` to `.mkv`, and `scripts/build_efmb.py`
built its path as `media/{id}.mp4` -- so act II could not be rebuilt at all.

So each act also declares `footage`: **video_ids, never paths**, resolved
through `tools/footage.py` and hashed by content with a `(path, size,
mtime_ns)` cache. It is a separate rung because it needs the footage on disk,
which CI does not have -- `--sources-only` stays footage-free on purpose.

What it trusts
--------------
The **act list and order come from `docs/running-order.md`**, the source of
truth -- parsed from its act table, never duplicated into a second
hand-maintained list here. Act VIII has no film (issue #51); its absence is
reported as by-design, never an error. The **declared masters** live in
`stories/megacut/delivery.json`, keyed by act numeral; that file is intent,
and `publish` is the only thing that makes `Prod/` match it.

Staleness is **content-based where it can be**. `~/Videos` is a Syncthing
folder and mtimes lie, so:

* `Prod/` links are checked by **inode identity** against the declared master
  (a hardlink that no longer resolves to its master's inode is stale by
  definition -- `tools/peaks.py trim` detaches on purpose via `os.replace`,
  and this tool is the re-link step its docstring defers to), and by
  **content hash** when the inodes disagree, so a re-link never downgrades
  what Prod carries. **Location** is checked too: a master or twin whose
  only resolution lives inside a git worktree is `ephemeral` -- one
  `git worktree remove` from gone -- regardless of which mtime is newer,
  because the hazard is where the file lives, not when it was written.
* `CHECKSUMS.md5` is verified by recomputing every line.
* The `Prod/README.md` master table is **generated** (between
  `<!-- deliver:table -->` markers) from the running order plus the delivery
  map, so a hand-edit that disagrees with reality is detected as drift.
* The megacut and the social copies are re-encodes, so content comparison is
  impossible; there mtime against `Prod/` is the signal, and the megacut also
  gets a **duration check** against the plan's own expected length when
  ffprobe is available -- a build still being written reports as incomplete
  rather than passing.

Degrade, never block: a missing master, a conflicted link, an absent
workspace -- all reported, none fatal. `status` without `--check` always
exits 0 once it has printed its report, so the test suite can run it against
the real workspace as a report without failing over the owner's mid-edit
state, and on a CI runner with no `~/Videos` at all.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import footage as footage_mod  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_WOLVES = Path.home() / "Videos" / "Wolves"
DEFAULT_RUNNING_ORDER = REPO_ROOT / "docs" / "running-order.md"
DEFAULT_DELIVERY = REPO_ROOT / "stories" / "megacut" / "delivery.json"
DEFAULT_PLAN = REPO_ROOT / "stories" / "megacut" / "megacut.json"

CHECKSUMS = "CHECKSUMS.md5"
TABLE_BEGIN = "<!-- deliver:table:start -->"
TABLE_END = "<!-- deliver:table:end -->"

# Where a hardlink's twin is looked for when Prod's inode does not match the
# declared master. Masters live in per-project dirs under ~/Videos, in the
# main checkout's renders/, and -- the recorded hazard, act II on 2026-08-13
# -- in worktrees under ~/src/dv-wt. Stat-only walk; missing roots are skipped.
TWIN_ROOTS = (
    Path.home() / "Videos",
    Path.home() / "src" / "destiny-vids" / "renders",
    Path.home() / "src" / "dv-wt",
)

# The megacut build lands within ~0.11 s of the plan's arithmetic (mux offset,
# measured on every build since v0.5); anything wider is a real disagreement.
DURATION_TOLERANCE_S = 2.0

# SOCIAL_CAP is tools/social.py's default target: a copy over it is rejected
# by the platform, so it is reported rather than trusted.
SOCIAL_CAP_BYTES = 10 * 1024 * 1024

# States. ABSENT_BY_DESIGN and NO_FILM are recorded decisions, not failures;
# everything in FAILING fails --check. EPHEMERAL is distinct from CONFLICT on
# purpose: conflict means "decide which content wins", ephemeral means "this
# content's only home is a git worktree that `git worktree remove` deletes --
# promote the master to a durable path".
OK = "ok"
NO_FILM = "no-film"
ABSENT_BY_DESIGN = "absent-by-design"
STALE = "stale"
MISSING = "missing"
CONFLICT = "conflict"
EPHEMERAL = "ephemeral"
UNDECLARED = "undeclared"

FAILING = {STALE, MISSING, CONFLICT, EPHEMERAL}

# One act row in docs/running-order.md's table:
#   | **I** | Project Bluefin | `Prod/01-intro.mp4` — ... | delivered |
# Act VIII's film cell is a dash -- it has no film and keeps its numeral.
# `0` is the PROLOGUE, which deliberately has no numeral: the eight act
# numerals are load-bearing (AGENTS.md), so a cold open in front of act I is
# numbered outside them rather than by renumbering everything behind it.
ACT_ROW = re.compile(r"^\|\s*\*\*(0|[IVXL]+)\*\*\s*\|([^|]*)\|([^|]*)\|")
PROD_FILE = re.compile(r"`Prod/([0-9]{2}-[^`]+\.mp4)`")


@dataclass
class Act:
    numeral: str           # "VI"
    title: str             # "7 Days to the Wolves"
    prod_file: str | None  # "06-7daystothewolves.mp4", None for act VIII


@dataclass
class Finding:
    node: str    # "master", "link", "checksum", "social", ...
    state: str   # OK / STALE / MISSING / CONFLICT / ...
    detail: str


@dataclass
class ActReport:
    act: Act
    findings: list = field(default_factory=list)

    def add(self, node, state, detail):
        self.findings.append(Finding(node, state, detail))
        return self.findings[-1]


def parse_running_order(path):
    """The act list and order, parsed from the running-order table.

    The table is the source of truth; this refuses to guess when it cannot
    read it, because a silently wrong order renumbers the show.
    """
    acts = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = ACT_ROW.match(line)
        if not m:
            continue
        numeral, title, film = m.group(1), m.group(2), m.group(3)
        f = PROD_FILE.search(film)
        acts.append(Act(numeral=numeral, title=title.strip().strip("*_ "),
                        prod_file=f.group(1) if f else None))
    if not acts:
        raise SystemExit(f"no acts parsed from {path} -- the running-order "
                         f"table is the source of truth and it must parse")
    return acts


def load_delivery(path):
    """The declared masters and social exemptions. Missing keys degrade:
    an act with no declared master is a punch-list item, not an error."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data.get("masters", {}), data.get("social", {})


def resolve_master(path):
    """Masters are stored `~`-rooted or absolute, never worktree-relative."""
    return Path(path).expanduser()


def md5(path):
    with open(path, "rb") as fh:
        return hashlib.file_digest(fh, "md5").hexdigest()


def same_file(a, b):
    """Hardlink identity: same device and inode means the same file."""
    try:
        sa, sb = os.stat(a), os.stat(b)
    except OSError:
        return False
    return (sa.st_dev, sa.st_ino) == (sb.st_dev, sb.st_ino)


def is_worktree_path(path):
    """True when `path` lives inside a LINKED git worktree -- a checkout whose
    root holds a `.git` FILE (`gitdir: ...`) rather than the main checkout's
    `.git` DIRECTORY. `git worktree remove` deletes the whole tree, so a
    master or twin that resolves only there is one command away from gone,
    and no amount of freshness saves it.

    Not string-matching on `dv-wt/`: the convention is how OUR worktrees are
    named, but the hazard is being a worktree, wherever it sits.
    """
    p = Path(path).resolve()
    for ancestor in (p, *p.parents):
        git = ancestor / ".git"
        if git.is_file():
            return True
        if git.is_dir():
            return False
    return False


def find_twins(path, roots=TWIN_ROOTS):
    """Every *.mp4 under `roots` sharing `path`'s inode, except `path` itself.

    This is how a Prod entry whose declared master disagrees is still named:
    the inode does not lie about where its content lives, even when the twin
    is inside a worktree about to be deleted.
    """
    try:
        st = os.stat(path)
    except OSError:
        return []
    want = (st.st_dev, st.st_ino)
    found = []
    for root in roots:
        root = Path(root)
        if not root.exists():
            continue
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                if not name.endswith(".mp4"):
                    continue
                p = Path(dirpath) / name
                try:
                    s = p.stat()
                except OSError:
                    continue  # Syncthing can move a file mid-walk
                if (s.st_dev, s.st_ino) == want and p != Path(path):
                    found.append(p)
    return found


# --- the per-node checks, in dependency order -------------------------------


def source_digest(sources):
    """A content hash over an act's committed inputs, in declared order.

    Content, not mtime: these files come out of git, so on a fresh clone every
    mtime is checkout time and every act would look stale at once. The digest
    survives a clone, a rebase and a Syncthing round trip, and it is the same
    reasoning the Prod link already uses.

    A path that does not exist hashes as absent rather than raising -- a
    renamed input should report as drift, not crash the report.
    """
    h = hashlib.sha256()
    for rel in sources:
        path = REPO_ROOT / rel
        h.update(rel.encode())
        if path.is_dir():
            for child in sorted(p for p in path.rglob("*") if p.is_file()):
                h.update(str(child.relative_to(REPO_ROOT)).encode())
                h.update(child.read_bytes())
        elif path.exists():
            h.update(path.read_bytes())
        else:
            h.update(b"\0absent")
    return h.hexdigest()


def sources_newer_than(sources, path):
    """The declared inputs modified AFTER `path` was written.

    The mtime companion to `source_digest`. The digest answers "are these the
    inputs that were recorded?"; this answers "could this master possibly have
    been built from them?" -- and only the second one can catch a digest being
    stamped over an act nobody re-rendered.

    mtime is a hint, not authority (Syncthing and a fresh clone both move it),
    but it is the hint that exists BEFORE anything is recorded, and it only
    ever makes the tool refuse to record. Erring this way costs a needless
    rebuild; erring the other way ships a stale act, which is the defect this
    exists to stop.
    """
    path = Path(path)
    if not path.exists():
        return []
    cutoff = path.stat().st_mtime
    out = []
    for rel in sources:
        p = REPO_ROOT / rel
        if p.is_dir():
            newest = max((c.stat().st_mtime for c in p.rglob("*")
                          if c.is_file()), default=None)
            if newest is not None and newest > cutoff:
                out.append(rel)
        elif p.exists() and p.stat().st_mtime > cutoff:
            out.append(rel)
    return out


def stale_source_acts(masters):
    """Acts whose committed inputs have moved since their master was recorded.

    The same judgement `check_sources` reports, in the form a caller can act
    on. It needs no footage and no ~/Videos, so any stage can ask it -- which
    is the point: the ASSEMBLY stage is where a stale act actually reaches an
    audience, and it used to have no way to ask.
    """
    out = []
    for numeral, master in (masters or {}).items():
        sources = master.get("sources")
        if not sources:
            continue
        recorded = master.get("source_digest")
        if not recorded:
            continue
        if source_digest(sources) != recorded:
            out.append((numeral, master))
    return out


def check_sources(act, master, report):
    """The rung BEFORE the master: did an act's inputs change without a render?

    `master -> Prod/ -> megacut/ -> 10mb/` starts at a rendered file, so it
    cannot see the thing that actually goes stale first -- somebody edits a
    shotlist, a dialogue record or a plate manifest, and the delivered act
    silently predates its own inputs. That is not hypothetical: acts IV and V
    were delivered on 11-12 August and the Kat/Nat dialogue round dictated on
    the 13th (#118) never reached them, which nothing detected.

    Unlike every other check here, this one needs **no footage and no
    ~/Videos**, so it runs as a gate on CI.
    """
    if master is None:
        return
    sources = master.get("sources")
    if sources is None:
        report.add("sources", UNDECLARED,
                   "no inputs declared -- nothing can tell whether this act's "
                   "master is older than the records that produce it. Add "
                   "`sources` to stories/megacut/delivery.json")
        return
    if not sources:
        report.add("sources", ABSENT_BY_DESIGN,
                   master.get("sources_note")
                   or "no committed inputs: this act is not built from the "
                      "repo yet")
        return
    digest = source_digest(sources)
    recorded = master.get("source_digest")
    if not recorded:
        report.add("sources", UNDECLARED,
                   f"inputs declared but never recorded -- run `deliver.py "
                   f"publish` to record {digest[:12]}")
        return
    if digest != recorded:
        report.add("sources", STALE,
                   f"inputs changed since this master was recorded "
                   f"({recorded[:12]} -> {digest[:12]}); rebuild the act, then "
                   f"`publish`. Declared inputs: {', '.join(sources)}")
        return
    report.add("sources", OK, f"{len(sources)} input(s) match {digest[:12]}")


def check_footage(act, master, report):
    """The other half of the inputs rung: the picture, which git cannot see.

    `media/` is gitignored, so `check_sources` is blind to it. An act whose
    master footage was replaced in place still reported `ok` -- #229. This
    rung declares footage by **video_id**, so a master that changes container
    (`.mp4` -> `.mkv`, which really happened) is still found.

    Needs the footage on disk, so it is skipped entirely by `--sources-only`
    and reports rather than raising when `media/` is not there at all.
    """
    if master is None:
        return
    ids = master.get("footage")
    if ids is None:
        report.add("footage", UNDECLARED,
                   "no footage declared -- nothing can tell whether this act "
                   "was cut from picture that has since been replaced. Add "
                   "`footage` to stories/megacut/delivery.json")
        return
    if not ids:
        report.add("footage", ABSENT_BY_DESIGN,
                   master.get("footage_note")
                   or "no footage inputs: this act is not cut from media/")
        return

    gone = footage_mod.missing(ids)
    if gone:
        report.add("footage", MISSING,
                   f"declared footage absent from media/: {', '.join(gone)}. "
                   f"The act cannot be rebuilt until it is fetched back")
        return

    # The digest is the authority, but it only exists once `publish` records
    # it. Until then mtime still catches the exact defect #229 describes: a
    # master that is OLDER than the footage it declares was cut from a file
    # that is no longer there. media/ is fetched locally and never cloned, so
    # its mtimes mean something -- unlike the committed inputs, which is why
    # `check_sources` hashes content instead.
    newer = footage_mod.newer_than(ids, resolve_master(master["path"]))
    digest = footage_mod.footage_digest(ids)
    recorded = master.get("footage_digest")
    if not recorded:
        if newer:
            report.add("footage", STALE,
                       f"this master PREDATES its own footage "
                       f"({', '.join(newer)} was replaced after the act was "
                       f"built), so it was cut from picture that is no longer "
                       f"there; rebuild the act, then `publish`")
            return
        report.add("footage", UNDECLARED,
                   f"footage declared but never recorded -- run `deliver.py "
                   f"publish` to record {digest[:12]}")
        return
    if digest != recorded:
        report.add("footage", STALE,
                   f"footage changed since this master was recorded "
                   f"({recorded[:12]} -> {digest[:12]}); rebuild the act, then "
                   f"`publish`. Declared footage: {', '.join(ids)}")
        return
    report.add("footage", OK, f"{len(ids)} master(s) match {digest[:12]}")


def check_master(act, master, report):
    if master is None:
        report.add("master", MISSING,
                   "no master declared in the delivery map")
        return None
    path = resolve_master(master["path"])
    if not path.exists():
        report.add("master", MISSING, f"declared master does not exist: {path}")
        return None
    if is_worktree_path(path):
        report.add("master", EPHEMERAL,
                   f"the declared master lives in a git worktree: {path} -- "
                   f"`git worktree remove` deletes it. Promote it to a "
                   f"durable path (the main checkout's renders/, or the "
                   f"act's ~/Videos project) and update delivery.json")
        return path
    report.add("master", OK, str(path))
    return path


def check_link(act, master_path, wolves, report, twin_roots=TWIN_ROOTS):
    """Inode first; content decides which side a mismatch must move; LOCATION
    decides whether the content survives a worktree cleanup at all."""
    prod = wolves / "Prod" / act.prod_file
    if not prod.exists():
        report.add("link", MISSING, f"{prod.name} is not in Prod/")
        return
    if master_path is None:
        report.add("link", OK, f"{prod.name} present; cannot verify it "
                               f"against a master (see the master line)")
        return
    if is_worktree_path(master_path):
        # Whatever the inodes say, linking Prod to a worktree is the hazard
        # itself: the link looks intact right up until `git worktree remove`.
        # (check_master has already named the path; this is the link's view.)
        report.add("link", EPHEMERAL,
                   "the declared master is a worktree checkout, so this link "
                   "is one `git worktree remove` from dangling. publish will "
                   "not link from a worktree -- promote the master to a "
                   "durable path first")
        return
    if same_file(prod, master_path):
        n = os.stat(prod).st_nlink
        report.add("link", OK,
                   f"hardlink intact ({n} link{'s' if n != 1 else ''})")
        return
    # Inodes disagree. Hash both: identical content means the link merely
    # detached (peaks.py's os.replace does this on purpose) and re-linking is
    # free. Different content means one side is a revision of the other, and
    # only the NEWER side may win -- re-linking an older master over a newer
    # Prod entry is how a finished overlay pass gets silently reverted.
    same_content = md5(prod) == md5(master_path)
    prod_mt, master_mt = prod.stat().st_mtime, master_path.stat().st_mtime
    if same_content:
        report.add("link", STALE,
                   "detached copy -- same content as the master, different "
                   "inode (a corrected master replaced its own file; "
                   "publish re-links it)")
        return
    twins = find_twins(prod, roots=twin_roots)
    if twins and all(is_worktree_path(t) for t in twins
                     ) and master_mt <= prod_mt:
        # Every non-Prod resolution of this inode is a worktree checkout, and
        # the durable master does not supersede the content. Mtime direction
        # is incidental here -- the hazard is LOCATION: when the branch is
        # finished, `git worktree remove` makes the delivered act
        # un-reproducible even though nothing about it looks stale today.
        report.add("link", EPHEMERAL,
                   f"Prod's content resolves only inside worktree "
                   f"checkout(s) ({twins[0]}); the durable master "
                   f"{master_path} does not carry it. Promote the build onto "
                   f"the master (or fix delivery.json), then publish -- "
                   f"before the worktree is removed")
        return
    where = (f"; Prod's content actually twins with {twins[0]}" if twins
             else "; no twin found -- Prod's content exists nowhere else")
    if master_mt > prod_mt:
        report.add("link", STALE,
                   "Prod is a revision BEHIND the declared master; publish "
                   f"re-links{where}")
    else:
        report.add("link", CONFLICT,
                   "the declared master is OLDER than what Prod carries -- "
                   f"re-linking would revert content{where}. Bring the "
                   f"master up to date (or fix delivery.json), then publish")


def check_checksums(wolves, reports, programme):
    """The whole file is re-verified, so publish may rewrite the whole file.

    The hand-rule in docs/skills/production/references/delivery.md -- refresh
    only your own line -- exists because a hand edit asserts every line while
    having built one. This tool recomputes every line, so the assertion it
    writes is the one it checked.
    """
    path = wolves / "Prod" / CHECKSUMS
    recorded = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            parts = line.split(None, 1)
            if len(parts) == 2:
                recorded[parts[1].strip()] = parts[0]
    known = set()
    for report in reports:
        name = report.act.prod_file
        if not name:
            continue
        known.add(name)
        prod = wolves / "Prod" / name
        if not prod.exists():
            continue  # the link check already reported the absence
        if name not in recorded:
            report.add("checksum", MISSING, f"no line in {CHECKSUMS}")
        elif recorded[name] != md5(prod):
            report.add("checksum", STALE,
                       f"{CHECKSUMS} predates the current content")
        else:
            report.add("checksum", OK, f"matches {CHECKSUMS}")
    for name in sorted(set(recorded) - known):
        programme.add("checksum", STALE,
                      f"{CHECKSUMS} carries {name}, which is not an act in "
                      f"the running order -- a leftover line asserts a file "
                      f"the graph does not track")


def expected_table(acts, masters):
    """The generated Prod/README.md master table, markers included."""
    lines = [TABLE_BEGIN,
             "| File | Act | Master it links to |",
             "|---|---|---|"]
    for act in acts:
        if act.prod_file is None:
            continue
        master = masters.get(act.numeral)
        cell = f"`{master['path']}`" if master else "*no master declared*"
        if master and master.get("note"):
            cell += f" — {master['note']}"
        lines.append(f"| `{act.prod_file}` | {act.numeral} | {cell} |")
    nofilm = [a.numeral for a in acts if a.prod_file is None]
    if len(nofilm) == 1:
        lines += ["", f"Act {nofilm[0]} has no film. Its numeral is held so "
                      f"nothing renumbers around it."]
    elif len(nofilm) > 1:
        lines += ["", f"Acts {', '.join(nofilm)} have no film. Their numerals "
                      f"are held so nothing renumbers around them."]
    lines.append(TABLE_END)
    return "\n".join(lines)


def check_readme(wolves, acts, masters, programme):
    readme = wolves / "Prod" / "README.md"
    if not readme.exists():
        programme.add("readme", MISSING, "Prod/README.md does not exist")
        return
    text = readme.read_text(encoding="utf-8")
    m = re.search(re.escape(TABLE_BEGIN) + r"(.*?)" + re.escape(TABLE_END),
                  text, re.DOTALL)
    if not m:
        programme.add("readme", MISSING,
                      f"no generated-table markers ({TABLE_BEGIN}) -- the "
                      f"master table is hand-maintained and can drift")
        return
    current = TABLE_BEGIN + m.group(1) + TABLE_END
    if current.strip() == expected_table(acts, masters).strip():
        programme.add("readme", OK, "master table matches the delivery map")
    else:
        programme.add("readme", STALE,
                      "master table disagrees with the delivery map "
                      "(publish regenerates it)")


def check_megacut(plan_path, wolves, reports, programme):
    """The plan's declared `output` is the current megacut; older builds are
    history, not currency. Two signals: mtime against the newest Prod entry,
    and -- with ffprobe -- the built duration against the plan's own
    arithmetic, which is what catches a file still being written."""
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    out = Path(plan.get("output", "")).expanduser()
    newest = None
    for r in reports:
        if not r.act.prod_file:
            continue
        p = wolves / "Prod" / r.act.prod_file
        if p.exists():
            t = p.stat().st_mtime
            newest = t if newest is None else max(newest, t)
    if not out.exists():
        megadir = wolves / "megacut"
        builds = sorted(megadir.glob("*.mp4")) if megadir.exists() else []
        detail = f"the plan's output {out.name} has not been built"
        if builds:
            detail += f"; newest present is {builds[-1].name}"
        programme.add("megacut", MISSING, detail)
        return
    if newest and out.stat().st_mtime < newest:
        programme.add("megacut", STALE,
                      f"{out.name} is older than Prod's newest act -- the "
                      f"show being watched does not contain the current acts")
        return
    try:
        from tools import megacut
        actual = float(megacut.probe_duration(str(out), stream="v:0"))
        planned = float(megacut.expected_duration(plan))
    except Exception:
        programme.add("megacut", OK,
                      f"{out.name} newer than every Prod act (duration check "
                      f"skipped: ffprobe unavailable or the file unreadable)")
        return
    if abs(actual - planned) > DURATION_TOLERANCE_S:
        programme.add("megacut", STALE,
                      f"{out.name} decodes as {actual:.1f}s against "
                      f"{planned:.1f}s planned -- incomplete (still being "
                      f"written?) or not this plan's build")
    else:
        programme.add("megacut", OK,
                      f"{out.name} matches the plan ({actual:.1f}s of "
                      f"{planned:.1f}s)")


def check_social(acts, social, wolves, reports):
    absent = social.get("absent", {})
    bitrate = social.get("audio_bitrate", 256)
    by_numeral = {r.act.numeral: r for r in reports if r.act.prod_file}
    for act in acts:
        if act.prod_file is None:
            continue
        report = by_numeral[act.numeral]
        prod = wolves / "Prod" / act.prod_file
        copy = wolves / "10mb" / act.prod_file
        if act.numeral in absent:
            report.add("social", ABSENT_BY_DESIGN, absent[act.numeral])
        elif not prod.exists():
            continue  # nothing to encode from; the link check reported it
        elif not copy.exists():
            report.add("social", MISSING,
                       f"no 10mb copy (build encodes one with tools/social.py "
                       f"at {bitrate}k audio)")
        elif copy.stat().st_mtime < prod.stat().st_mtime:
            report.add("social", STALE, "10mb copy is older than its Prod "
                                        "master")
        elif copy.stat().st_size > SOCIAL_CAP_BYTES:
            report.add("social", STALE,
                       f"10mb copy is over the 10 MiB cap "
                       f"({copy.stat().st_size / (1024 * 1024):.2f} MiB) -- "
                       f"the platform will reject it")
        else:
            report.add("social", OK, "10mb copy current")


# --- publish ----------------------------------------------------------------


def link_master(src, prod):
    """`ln -f` semantics: a NEW directory entry for the master's inode,
    atomically renamed over the old one. Never a copy -- a copy silently
    breaks the link and goes stale."""
    tmp = prod.with_name(prod.name + ".deliver-tmp")
    tmp.unlink(missing_ok=True)
    os.link(src, tmp)
    os.replace(tmp, prod)


def publish(acts, masters, wolves, delivery_path=None, log=print):
    """Make Prod/ match the delivery map, then regenerate what describes it.

    Only ever `ln -f` semantics -- never a copy. A conflicted act (declared
    master older than Prod's content) is SKIPPED and reported: the tool
    refuses to revert content to keep a queue moving.
    """
    prod_dir = wolves / "Prod"
    prod_dir.mkdir(parents=True, exist_ok=True)
    for act in acts:
        if act.prod_file is None:
            continue
        master = masters.get(act.numeral)
        prod = prod_dir / act.prod_file
        if master is None:
            log(f"  {act.prod_file}: no declared master; left as-is")
            continue
        src = resolve_master(master["path"])
        if not src.exists():
            log(f"  {act.prod_file}: master missing ({src}); left as-is")
            continue
        if is_worktree_path(src):
            # Attaching Prod to a worktree path is the hazard itself (#150):
            # the link reads as intact until `git worktree remove` runs.
            # The remedy is promotion to a durable path, never this link.
            log(f"  {act.prod_file}: EPHEMERAL -- declared master lives in a "
                f"git worktree ({src}); NOT linked. Promote it to a durable "
                f"path first")
            continue
        if prod.exists():
            if same_file(prod, src):
                continue  # already the master's inode
            same_content = md5(prod) == md5(src)
            if not same_content and src.stat().st_mtime < prod.stat().st_mtime:
                log(f"  {act.prod_file}: CONFLICT -- declared master is older "
                    f"than Prod's content; NOT re-linked (see status)")
                continue
            log(f"  {act.prod_file}: "
                + ("re-attaching detached link" if same_content else
                   f"re-linking to newer master {src.name}"))
        link_master(src, prod)
        if not same_file(prod, src):
            log(f"  {act.prod_file}: FAILED to link -> {src}")
            return 1
    sums = []
    for f in sorted(prod_dir.glob("*.mp4")):
        sums.append(f"{md5(f)}  {f.name}")
    (prod_dir / CHECKSUMS).write_text("\n".join(sums) + "\n", encoding="utf-8")
    log(f"  {CHECKSUMS}: regenerated for {len(sums)} acts (every line "
        f"recomputed, so rewriting the file asserts nothing unchecked)")

    readme = prod_dir / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        table = expected_table(acts, masters)
        new, n = re.subn(
            re.escape(TABLE_BEGIN) + r".*?" + re.escape(TABLE_END),
            lambda _m: table, text, flags=re.DOTALL)
        if n:
            readme.write_text(new, encoding="utf-8")
            log("  README.md: master table regenerated from the delivery map")
        else:
            log(f"  README.md: no {TABLE_BEGIN} markers -- table NOT "
                f"touched; add the markers around the table to hand it to "
                f"the tool")
    record_source_digests(acts, masters, delivery_path, log=log)
    return 0


def record_source_digests(acts, masters, delivery_path, log=print):
    """Stamp each act's current input digest into the delivery map.

    This is what closes the loop: `publish` is the step that says "what is in
    Prod NOW is built from these inputs", so a later edit to any of them shows
    up as drift instead of going unnoticed. Recording it anywhere else would
    let an act be declared fresh without anything being delivered.
    """
    if delivery_path is None:
        return
    doc = json.loads(Path(delivery_path).read_text(encoding="utf-8"))
    changed = []
    for act in acts:
        master = doc.get("masters", {}).get(act.numeral)
        if not master:
            continue
        if master.get("sources"):
            # The SAME guard the footage digest below has always had, and its
            # absence here is what let stale programmes ship: `publish` claims
            # "what is in Prod now is built from these inputs", so stamping a
            # master that is OLDER than those inputs records a claim nobody
            # can have made true. It went green, `check_sources` had nothing
            # left to catch, and the next megacut seated the stale act.
            src = resolve_master(master["path"])
            behind = sources_newer_than(master["sources"], src)
            if behind:
                log(f"  {act.numeral}: inputs NOT recorded -- the master "
                    f"predates {', '.join(behind)}; rebuild the act first")
                continue
            digest = source_digest(master["sources"])
            if master.get("source_digest") != digest:
                master["source_digest"] = digest
                changed.append(f"{act.numeral} -> {digest[:12]}")
        # Footage is stamped only when every declared master is present AND
        # the delivered act is not older than the footage it names. Stamping
        # either case would launder the drift this rung exists to catch: a
        # digest recorded over "absent", or over a master that predates its
        # own picture, goes green while being wrong.
        ids = master.get("footage")
        if ids and not footage_mod.missing(ids):
            src = resolve_master(master["path"])
            if footage_mod.newer_than(ids, src):
                log(f"  {act.numeral}: footage NOT recorded -- the master "
                    f"predates {', '.join(footage_mod.newer_than(ids, src))}; "
                    f"rebuild the act first")
            else:
                digest = footage_mod.footage_digest(ids)
                if master.get("footage_digest") != digest:
                    master["footage_digest"] = digest
                    changed.append(f"{act.numeral} footage -> {digest[:12]}")
    if changed:
        Path(delivery_path).write_text(
            json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
        log(f"  delivery.json: recorded input digests for {', '.join(changed)}")


# --- build ------------------------------------------------------------------


def build(acts, masters, social, wolves, plan_path, reports, programme,
          dry_run, log=print):
    """Rebuild what is stale, in dependency order: Prod links, then the
    megacut, then the social copies. The graph is master -> Prod -> megacut
    -> 10mb, so a conflicted upstream link refuses the megacut rather than
    baking old content into a new encode."""
    actions = []  # (order, label, argv or None for a re-link)
    conflicted = set()
    for r in reports:
        if not r.act.prod_file:
            continue
        src_f = next((f for f in r.findings if f.node == "sources"), None)
        if src_f and src_f.state == STALE:
            cmd = (masters.get(r.act.numeral) or {}).get("rebuild")
            if cmd:
                argv = shlex.split(cmd) if isinstance(cmd, str) else list(cmd)
                actions.append((-1, f"rebuild {r.act.numeral}", argv,
                                shlex.join(argv)))
            else:
                # Degrade, never block: an act whose inputs moved but which has
                # no one-command rebuild is REPORTED, not silently skipped and
                # not faked with a guessed command. A wrong rebuild here
                # re-burns nameplates about real people.
                log(f"act {r.act.numeral}: inputs changed but no `rebuild` "
                    f"command is declared in delivery.json -- rebuild it by "
                    f"hand, then `deliver.py publish`")
        link = next((f for f in r.findings if f.node == "link"), None)
        if link and link.state in FAILING:
            if link.state in (CONFLICT, EPHEMERAL):
                # Both block downstream the same way; the remedies differ
                # (decide the content vs promote the master to a durable
                # path), and status names which.
                conflicted.add(r.act.numeral)
            else:
                actions.append((0, f"link {r.act.numeral}", None,
                                f"re-link Prod/{r.act.prod_file} to its "
                                f"declared master"))
        soc = next((f for f in r.findings if f.node == "social"), None)
        if soc and soc.state in FAILING and r.act.numeral not in conflicted:
            src = wolves / "Prod" / r.act.prod_file
            out = wolves / "10mb" / r.act.prod_file
            argv = [sys.executable, str(REPO_ROOT / "tools" / "social.py"),
                    str(src), "--out", str(out), "--audio-bitrate",
                    str(social.get("audio_bitrate", 256))]
            actions.append((2, f"social {r.act.numeral}", argv,
                            shlex.join(argv)))
    mega = next((f for f in programme.findings if f.node == "megacut"), None)
    if mega and mega.state in FAILING:
        if conflicted:
            log(f"megacut: REFUSED -- act(s) {', '.join(sorted(conflicted))} "
                f"have unresolved links; rebuilding would bake in the wrong "
                f"content")
        else:
            argv = [sys.executable, str(REPO_ROOT / "tools" / "megacut.py"),
                    str(plan_path)]
            actions.append((1, "megacut", argv, shlex.join(argv)))
    actions.sort(key=lambda a: a[0])
    for _order, label, argv, description in actions:
        if dry_run:
            log(f"  would {label}: {description}")
            continue
        log(f"  {label}: {description}")
        if argv is None:
            numeral = label.split()[-1]
            act = next(a for a in acts if a.numeral == numeral)
            publish([act], masters, wolves, log=log)
        else:
            proc = subprocess.run(argv, capture_output=True, text=True)
            if proc.returncode != 0:
                tail = (proc.stderr.strip().splitlines() or
                        proc.stdout.strip().splitlines() or ["no output"])
                log(f"  FAILED: {tail[-1]}")
                return 1
    if not actions:
        log("  nothing stale")
    if conflicted:
        log(f"  unresolved link(s): act(s) {', '.join(sorted(conflicted))} "
            f"-- see status; no tool action exists until the conflict is "
            f"decided or the master is promoted to a durable path")
    return 0


# --- status -----------------------------------------------------------------


def gather(acts, masters, social, wolves, plan_path, twin_roots=TWIN_ROOTS):
    reports = [ActReport(act) for act in acts]
    for r in reports:
        if r.act.prod_file is None:
            r.add("film", NO_FILM,
                  "no film by design (issue #51); the numeral is held so "
                  "nothing renumbers around it")
            continue
        master_path = check_master(r.act, masters.get(r.act.numeral), r)
        check_sources(r.act, masters.get(r.act.numeral), r)
        check_footage(r.act, masters.get(r.act.numeral), r)
        check_link(r.act, master_path, wolves, r, twin_roots=twin_roots)
    programme = ActReport(Act("", "the programme", None))
    check_checksums(wolves, reports, programme)
    check_readme(wolves, acts, masters, programme)
    check_megacut(plan_path, wolves, reports, programme)
    check_social(acts, social, wolves, reports)
    reports.append(programme)
    return reports


def print_report(reports, wolves, log=print):
    log(f"delivery status -- {wolves}")
    log("graph: inputs -> master -> Prod/ -> megacut/ -> 10mb/  "
        "(acts and order: docs/running-order.md)")
    programme = reports[-1]
    for r in reports[:-1]:
        head = f"{r.act.numeral:<4} {r.act.prod_file or r.act.title}"
        log(f"\n{head}")
        for f in r.findings:
            log(f"  {f.node:<9} {f.state:<16} {f.detail}")
    if programme.findings:
        log("\nprogramme")
        for f in programme.findings:
            log(f"  {f.node:<9} {f.state:<16} {f.detail}")
    failing = [f for r in reports for f in r.findings if f.state in FAILING]
    noted = [f for r in reports for f in r.findings
             if f.state in (ABSENT_BY_DESIGN, NO_FILM)]
    log(f"\n{len(failing)} stale, {len(noted)} recorded absences "
        f"(punch-list, not failures)")
    return 1 if failing else 0


# --- entry ------------------------------------------------------------------


def watch(acts, masters, social, wolves, plan_path, interval, dry_run,
          log=print, once=False):
    """Keep the delivery fresh: re-gather, rebuild what is stale, repeat.

    The owner's standard is that the megacut is never more than one edit
    behind, because transcoding is cheap and a stale programme is what gets
    reviewed and mis-trusted. This is the loop that enforces it.

    It is deliberately a poll, not an inotify watch: the inputs live in git and
    the outputs live in a Syncthing folder, so an edit can arrive from a
    rebase, another agent's worktree, or another machine -- none of which
    generate a local file event. A poll notices all three for the cost of a
    few hashes.

    Ctrl-C is a clean exit, not a traceback: this is meant to be left running.

    Output is flushed every round. A watcher is normally run with its output
    redirected to a log, where Python's block buffering would otherwise hold
    several KB back -- so the log reads as empty for hours and the loop looks
    dead while it is working.
    """
    import time

    def emit(msg=""):
        log(msg)
        try:
            sys.stdout.flush()
        except (ValueError, OSError):
            pass

    emit(f"watching {wolves} every {interval:g}s -- Ctrl-C to stop")
    rounds = 0
    try:
        while True:
            rounds += 1
            reports = gather(acts, masters, social, wolves, plan_path)
            failing = sum(1 for r in reports for f in r.findings
                          if f.state in FAILING)
            if failing:
                emit(f"[{rounds}] {failing} stale finding(s); rebuilding")
                build(acts, masters, social, wolves, plan_path, reports,
                      reports[-1], dry_run, log=emit)
            else:
                emit(f"[{rounds}] fresh")
            if once:
                return 0
            time.sleep(interval)
    except KeyboardInterrupt:
        emit("\nstopped")
        return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=("status", "publish", "build"))
    ap.add_argument("--check", action="store_true",
                    help="status as a gate: exit 1 when anything is stale")
    ap.add_argument("--dry-run", action="store_true",
                    help="build: print the rebuild commands, run nothing")
    ap.add_argument("--wolves-root", type=Path, default=DEFAULT_WOLVES)
    ap.add_argument("--running-order", type=Path, default=DEFAULT_RUNNING_ORDER)
    ap.add_argument("--delivery", type=Path, default=DEFAULT_DELIVERY)
    ap.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    ap.add_argument("--sources-only", action="store_true",
                    help="status: check ONLY the inputs->master rung, which "
                         "needs no footage and no ~/Videos, so it runs on CI")
    ap.add_argument("--watch", type=float, metavar="SECONDS",
                    help="build: keep rebuilding whatever goes stale, every "
                         "SECONDS. Transcoding is cheap; a stale megacut is "
                         "not")
    args = ap.parse_args(argv)

    wolves = args.wolves_root
    acts = parse_running_order(args.running_order)
    masters, social = load_delivery(args.delivery)

    if args.sources_only:
        # The one check that works with no workspace at all: it reads only
        # committed files. This is the gate that would have caught acts IV/V
        # drifting away from a dialogue round nobody rendered (#118).
        stale = 0
        for act in acts:
            if act.prod_file is None:
                continue
            report = ActReport(act)
            check_sources(act, masters.get(act.numeral), report)
            for f in report.findings:
                print(f"{act.numeral:4s} {f.node:9s} {f.state:16s} {f.detail}")
                if f.state == STALE:
                    stale += 1
        print(f"\n{stale} act(s) whose inputs moved without a rebuild")
        # UNDECLARED is a warning, never a gate failure: an act nobody has
        # taught the tool about must not block every unrelated PR.
        return 1 if (stale and args.check) else 0

    if not wolves.exists():
        # A CI runner has no ~/Videos. The suite must stay green there, and
        # the report must say WHY it is empty rather than look like a pass.
        # --check fails closed: a gate that cannot see its workspace proves
        # nothing, and passing anyway would read as "everything delivered".
        print(f"delivery workspace absent: {wolves} -- nothing to report "
              f"(normal off the owner's machine)")
        return 1 if args.check else 0

    if args.command == "status":
        reports = gather(acts, masters, social, wolves, args.plan)
        rc = print_report(reports, wolves)
        return rc if args.check else 0
    if args.command == "publish":
        return publish(acts, masters, wolves, args.delivery)
    if args.watch:
        return watch(acts, masters, social, wolves, args.plan, args.watch,
                     args.dry_run)
    reports = gather(acts, masters, social, wolves, args.plan)
    return build(acts, masters, social, wolves, args.plan, reports,
                 reports[-1], args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
