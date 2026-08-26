"""The session-end worktree safety audit from issue #295."""

import subprocess

from tools import worktrees


HEAD = "a" * 40
OTHER_HEAD = "b" * 40
REPO = "/var/home/jorge/src/example"


def clean_git(cwd, *args):
    if args == ("worktree", "list", "--porcelain"):
        return (
            f"worktree {REPO}\n"
            f"HEAD {HEAD}\n"
            "branch refs/heads/main\n"
            "\n"
        )
    if args == ("status", "--porcelain", "--untracked-files=all"):
        return ""
    if args == ("branch", "-r", "--contains", HEAD, "--format=%(refname:short)"):
        return "origin/main\n"
    raise AssertionError((cwd, args))


def test_a_clean_named_remote_worktree_passes_strict_mode(capsys):
    assert worktrees.main(["--repo", REPO, "--check"], run_git=clean_git) == 0
    out = capsys.readouterr().out
    assert "main" in out
    assert "origin/main" in out
    assert "all 1 registered worktree(s) are safe" in out


def test_porcelain_parsing_preserves_spaces_detached_and_prunable_state():
    records = worktrees.parse_worktrees(
        "worktree /var/home/jorge/src/a repo\n"
        f"HEAD {HEAD}\n"
        "detached\n"
        "prunable gitdir file points to non-existent location\n"
        "\n"
    )

    assert len(records) == 1
    assert str(records[0].path) == "/var/home/jorge/src/a repo"
    assert records[0].branch is None
    assert records[0].detached is True
    assert records[0].prunable == "gitdir file points to non-existent location"


def test_a_bare_repository_record_is_parsed_without_inventing_a_head():
    records = worktrees.parse_worktrees(
        "worktree /var/home/jorge/src/example.git\n"
        "bare\n"
        "\n"
    )

    assert len(records) == 1
    assert records[0].bare is True
    assert records[0].head is None


def detached_git(cwd, *args):
    if args == ("worktree", "list", "--porcelain"):
        return f"worktree {REPO}\nHEAD {HEAD}\ndetached\n\n"
    if args == ("status", "--porcelain", "--untracked-files=all"):
        return ""
    if args == ("branch", "-r", "--contains", HEAD, "--format=%(refname:short)"):
        return "origin/main\n"
    raise AssertionError((cwd, args))


def test_detached_head_is_reported_and_only_strict_mode_fails(capsys):
    assert worktrees.main(["--repo", REPO], run_git=detached_git) == 0
    assert "detached-head" in capsys.readouterr().out

    assert worktrees.main(["--repo", REPO, "--check"], run_git=detached_git) == 1


def temporary_git(cwd, *args):
    if args == ("worktree", "list", "--porcelain"):
        return f"worktree /var/tmp/agent-work\nHEAD {HEAD}\nbranch refs/heads/feat/x\n\n"
    if args == ("status", "--porcelain", "--untracked-files=all"):
        return ""
    if args == ("branch", "-r", "--contains", HEAD, "--format=%(refname:short)"):
        return "origin/feat/x\n"
    raise AssertionError((cwd, args))


def test_a_worktree_under_a_temporary_root_is_unsafe(capsys):
    assert worktrees.main(["--repo", REPO, "--check"], run_git=temporary_git) == 1
    assert "temporary-path" in capsys.readouterr().out


def prunable_git(cwd, *args):
    if args == ("worktree", "list", "--porcelain"):
        return (
            f"worktree /var/home/jorge/src/missing\n"
            f"HEAD {HEAD}\n"
            "branch refs/heads/old\n"
            "prunable gitdir file points to non-existent location\n"
            "\n"
        )
    if args == ("branch", "-r", "--contains", HEAD, "--format=%(refname:short)"):
        return "origin/old\n"
    raise AssertionError((cwd, args))


def test_a_prunable_registration_is_reported_without_inspecting_the_missing_path(
    capsys,
):
    assert worktrees.main(["--repo", REPO, "--check"], run_git=prunable_git) == 1
    out = capsys.readouterr().out
    assert "prunable-registration" in out
    assert "gitdir file points to non-existent location" in out


def dirty_unpublished_git(cwd, *args):
    if args == ("worktree", "list", "--porcelain"):
        return f"worktree {REPO}\nHEAD {HEAD}\nbranch refs/heads/feat/draft\n\n"
    if args == ("status", "--porcelain", "--untracked-files=all"):
        return "?? chapters/draft.md\n"
    if args == ("branch", "-r", "--contains", HEAD, "--format=%(refname:short)"):
        return ""
    raise AssertionError((cwd, args))


def test_dirty_and_unpublished_work_are_reported_together(capsys):
    assert (
        worktrees.main(["--repo", REPO, "--check"], run_git=dirty_unpublished_git)
        == 1
    )
    out = capsys.readouterr().out
    assert "dirty" in out
    assert "unpublished-head" in out


def rescued_git(cwd, *args):
    if args == ("worktree", "list", "--porcelain"):
        return f"worktree {REPO}\nHEAD {HEAD}\nbranch refs/heads/local-name\n\n"
    if args == ("status", "--porcelain", "--untracked-files=all"):
        return ""
    if args == ("branch", "-r", "--contains", HEAD, "--format=%(refname:short)"):
        return "origin/rescue/archived-name\n"
    raise AssertionError((cwd, args))


def test_remote_reachability_not_branch_name_is_the_durability_proof():
    assert worktrees.main(["--repo", REPO, "--check"], run_git=rescued_git) == 0


def failing_status_git(cwd, *args):
    if args == ("worktree", "list", "--porcelain"):
        return f"worktree {REPO}\nHEAD {HEAD}\nbranch refs/heads/main\n\n"
    if args == ("status", "--porcelain", "--untracked-files=all"):
        raise subprocess.CalledProcessError(
            128, ["git", "status"], stderr="fatal: cannot inspect worktree"
        )
    if args == ("branch", "-r", "--contains", HEAD, "--format=%(refname:short)"):
        return "origin/main\n"
    raise AssertionError((cwd, args))


def test_an_inspection_failure_is_visible_and_never_counts_as_clean(capsys):
    assert worktrees.main(["--repo", REPO, "--check"], run_git=failing_status_git) == 1
    out = capsys.readouterr().out
    assert "inspection-error" in out
    assert "cannot inspect worktree" in out


def empty_git(cwd, *args):
    if args == ("worktree", "list", "--porcelain"):
        return ""
    raise AssertionError((cwd, args))


def test_an_empty_worktree_listing_is_not_an_all_clear(capsys):
    assert worktrees.main(["--repo", REPO, "--check"], run_git=empty_git) == 1
    out = capsys.readouterr().out
    assert "inspection-error" in out
    assert "no registered worktrees" in out


def shared_git(cwd, *args):
    if args == ("worktree", "list", "--porcelain"):
        return (
            f"worktree {REPO}\n"
            f"HEAD {HEAD}\n"
            "branch refs/heads/main\n"
            "\n"
            "worktree /var/home/jorge/src/someone-elses-work\n"
            f"HEAD {OTHER_HEAD}\n"
            "branch refs/heads/feat/other\n"
            "\n"
        )
    if args == ("status", "--porcelain", "--untracked-files=all"):
        if str(cwd) == REPO:
            return ""
        return " M chapters/other.md\n"
    if args == ("branch", "-r", "--contains", HEAD, "--format=%(refname:short)"):
        return "origin/main\n"
    if args == (
        "branch",
        "-r",
        "--contains",
        OTHER_HEAD,
        "--format=%(refname:short)",
    ):
        return "origin/feat/other\n"
    raise AssertionError((cwd, args))


def test_strict_mode_checks_this_checkout_but_still_reports_other_findings(capsys):
    assert worktrees.main(["--repo", REPO, "--check"], run_git=shared_git) == 0
    out = capsys.readouterr().out
    assert "someone-elses-work" in out
    assert "dirty" in out
    assert "selected worktree is safe" in out
