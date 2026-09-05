#!/usr/bin/env python3
"""Report whether registered Git worktrees hold unpublished authored work.

The report is read-only: it never pushes, commits, moves, prunes, or removes a
worktree. The default exit is zero so production can report another worktree's
hazard without withholding a film. ``--check`` exits non-zero only when the
selected checkout is unsafe; findings in other agents' worktrees remain visible
without making their state somebody else's gate.

Usage:
    python3 tools/worktrees.py
    python3 tools/worktrees.py --check
    python3 tools/worktrees.py --repo /path/to/checkout
"""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPORARY_ROOTS = (Path("/tmp"), Path("/var/tmp"))


@dataclass(frozen=True)
class Worktree:
    path: Path
    head: str | None
    branch: str | None = None
    detached: bool = False
    prunable: str | None = None
    bare: bool = False


def run_git(cwd: Path | str, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def parse_worktrees(raw: str) -> list[Worktree]:
    worktrees = []
    fields: dict[str, str] = {}
    for line in [*raw.splitlines(), ""]:
        if line:
            key, _, value = line.partition(" ")
            fields[key] = value
            continue
        if fields:
            branch = fields.get("branch")
            worktrees.append(
                Worktree(
                    path=Path(fields["worktree"]),
                    head=fields.get("HEAD"),
                    branch=branch.removeprefix("refs/heads/") if branch else None,
                    detached="detached" in fields,
                    prunable=fields.get("prunable"),
                    bare="bare" in fields,
                )
            )
            fields = {}
    return worktrees


def is_temporary_path(path: Path) -> bool:
    resolved = path.resolve(strict=False)
    return any(resolved == root or resolved.is_relative_to(root)
               for root in TEMPORARY_ROOTS)


def describe_git_error(exc: BaseException) -> str:
    detail = getattr(exc, "stderr", None) or str(exc)
    return " ".join(str(detail).strip().split())


def selected_worktree(repo: Path, worktrees: list[Worktree]) -> Worktree | None:
    requested = repo.resolve(strict=False)
    candidates = []
    for worktree in worktrees:
        if worktree.bare:
            continue
        root = worktree.path.resolve(strict=False)
        if requested == root or requested.is_relative_to(root):
            candidates.append((len(root.parts), worktree))
    return max(candidates, default=(0, None), key=lambda item: item[0])[1]


def main(argv=None, run_git=run_git):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        default=str(REPO_ROOT),
        help="any checkout in the repository (default: this checkout)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero when the selected checkout is unsafe",
    )
    args = parser.parse_args(argv)

    try:
        worktrees = parse_worktrees(
            run_git(Path(args.repo), "worktree", "list", "--porcelain")
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"{args.repo}  inspection-error ({describe_git_error(exc)})")
        return 1 if args.check else 0
    if not worktrees:
        print(f"{args.repo}  inspection-error (no registered worktrees)")
        return 1 if args.check else 0

    unsafe = 0
    checkout_count = 0
    findings_by_path = {}
    for worktree in worktrees:
        if worktree.bare:
            print(f"{worktree.path}  (bare)  (none)  bare-repository")
            continue
        checkout_count += 1
        dirty = False
        errors = []
        if not worktree.prunable:
            try:
                dirty = bool(run_git(
                    worktree.path,
                    "status",
                    "--porcelain",
                    "--untracked-files=all",
                ).strip())
            except (OSError, subprocess.SubprocessError) as exc:
                errors.append(describe_git_error(exc))
        if worktree.head:
            try:
                remote_output = run_git(
                    Path(args.repo),
                    "branch",
                    "-r",
                    "--contains",
                    worktree.head,
                    "--format=%(refname:short)",
                )
            except (OSError, subprocess.SubprocessError) as exc:
                errors.append(describe_git_error(exc))
                remote_output = ""
        else:
            errors.append("worktree record has no HEAD")
            remote_output = ""
        remotes = [line.strip() for line in remote_output.splitlines()
                   if line.strip()]
        hazards = []
        hazards.extend(f"inspection-error ({error})" for error in errors)
        if worktree.prunable:
            hazards.append(f"prunable-registration ({worktree.prunable})")
        if is_temporary_path(worktree.path):
            hazards.append("temporary-path")
        if worktree.detached or worktree.branch is None:
            hazards.append("detached-head")
        if dirty:
            hazards.append("dirty")
        if not remotes:
            hazards.append("unpublished-head")
        unsafe += bool(hazards)
        findings_by_path[worktree.path.resolve(strict=False)] = hazards
        branch = worktree.branch or "(detached)"
        remote = ", ".join(remotes) if remotes else "(none)"
        verdict = ", ".join(hazards) if hazards else "safe"
        print(f"{worktree.path}  {branch}  {remote}  {verdict}")

    if unsafe:
        print(f"{unsafe} of {checkout_count} registered worktree(s) are unsafe")
    else:
        print(f"all {checkout_count} registered worktree(s) are safe")

    if not args.check:
        return 0

    selected = selected_worktree(Path(args.repo), worktrees)
    if selected is None:
        print(f"{args.repo}  inspection-error (no checkout worktree selected)")
        return 1
    selected_findings = findings_by_path[selected.path.resolve(strict=False)]
    if selected_findings:
        print(f"selected worktree is unsafe: {selected.path}")
        return 1
    other_findings = unsafe
    if other_findings:
        print(
            f"selected worktree is safe; {other_findings} other worktree "
            f"finding(s) reported"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
