from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS = REPO_ROOT / "docs" / "skills"
PRE_COMMIT_CONFIG = REPO_ROOT / ".pre-commit-config.yaml"


def _canonical_skills() -> list[Path]:
    return (
        sorted(p for p in SKILLS.glob("*.md") if p.name != "index.md")
        + sorted(SKILLS.glob("*/SKILL.md"))
    )


def _front_matter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} has no YAML front matter"
    raw = text.split("---\n", 2)[1]
    data = yaml.safe_load(raw)
    assert isinstance(data, dict), f"{path} front matter must parse to a mapping"
    return data


def test_every_skill_has_common_compatible_front_matter():
    required = {
        "name",
        "version",
        "last_updated",
        "id",
        "one_line_purpose",
        "entry_point",
        "category",
        "status",
        "dependencies",
        "tags",
        "description",
        "metadata",
    }
    for path in _canonical_skills():
        fm = _front_matter(path)
        assert required <= fm.keys(), f"{path}: {required - fm.keys()}"
        assert fm["metadata"]["type"] in {
            "procedure",
            "reference",
            "runbook",
            "policy",
        }


def test_no_canonical_skill_exceeds_hard_limit():
    oversized = {
        str(path.relative_to(REPO_ROOT)): len(path.read_text(encoding="utf-8").splitlines())
        for path in _canonical_skills()
        if len(path.read_text(encoding="utf-8").splitlines()) > 500
    }
    assert not oversized


def test_agent_contract_is_not_duplicated():
    forbidden = [
        REPO_ROOT / "CLAUDE.md",
        REPO_ROOT / "GEMINI.md",
        REPO_ROOT / ".github" / "copilot-instructions.md",
    ]
    assert not [str(path.relative_to(REPO_ROOT))
                for path in forbidden if path.exists()]
    assert not list((REPO_ROOT / ".github" / "agents").glob("**/*"))


def test_agents_contract_declares_local_authority_and_common_sidecar():
    text = (REPO_ROOT / "AGENTS.md").read_text()
    assert "local authority" in text
    assert "projectbluefin/common" in text
    assert "never overrides" in text


def test_agents_contract_requires_issue_applicability_check():
    text = (REPO_ROOT / "AGENTS.md").read_text()
    assert "issue references are historical evidence" in text
    assert "git history" in text
    assert "still applies" in text


def test_agents_read_order_links_the_common_agentic_model_as_a_sidecar():
    text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "5. [`projectbluefin/common/docs/factory/agentic-model.md`]" in text
    assert "github.com/projectbluefin/common/blob/main/docs/factory/agentic-model.md" in text
    assert "shared compatibility sidecar only; it never overrides local authority" in text


def test_router_links_generated_catalog():
    text = (REPO_ROOT / "docs/SKILL.md").read_text()
    assert "skills/index.json" in text
    assert "skills/index.md" in text


def test_plates_docs_keep_the_high_risk_contract_and_navigation():
    skill = SKILLS / "plates" / "SKILL.md"
    front_matter = _front_matter(skill)
    assert front_matter["metadata"]["context7-sources"] == [
        "/addyosmani/agent-skills",
        "/websites/ffmpeg_documentation"
    ]

    expected = {
        skill: (
            "## Common Rationalizations",
            '"One extra line makes the plate clearer."',
            '"I\'ll hardcode the copy just for this render."',
            '"The brief\'s copy contradicts the binding, but the owner wrote it today."',
            '"I\'ll hand-author the manifest, so `plan`\'s rules don\'t apply."',
            '"The plate is short, it can share the screen."',
            '"The shot is only two seconds, so nobody can be plated there."',
            '"I\'ll put a plausible name on the placeholder so it looks finished."',
            '"No copy for this lead? Write them something."',
            "brief plate without it is a hand-edit",
            "Never ship the old master instead",
            "Styling taken from the live site where the baked reveal disagrees",
            "Do not make one derivative per section",
            "Cascading Multiple Overlays",
            "`premultiplied`",
            "references/conversation-cards.md",
            "references/plate-chrome.md",
            "references/full-frame-cards.md",
        ),
        SKILLS / "plates" / "references" / "conversation-cards.md": (
            "Use an asterisk for other letters",
            "do not add censorship the owner did not request",
            "records the mark under `glyphs`",
            "real width before wrapping or centering",
            "plain authored letter",
        ),
        SKILLS / "plates" / "references" / "plate-chrome.md": (
            "takes precedence over `trustee`",
            "default blue `#cbd5f5`",
            "Rust Foundation herald",
            "Nobara Project indigo",
            "YouTube logo red `#FF0000`",
            "scripts/fetch_brand_marks.py",
            "renders/marks/",
            "/usr/share/pixmaps",
            "Fedora CoreOS",
        ),
        SKILLS / "plates" / "references" / "from-a-brief.md": (
            "`plan` refuses a `copy` key",
            "A brief plate without `copy_source` is a hand-edit",
            "measured against the **picture**, never the raw frame",
            "`top: 28%`",
            "bug in `plan`, not a gap to work around",
        ),
        SKILLS / "plates" / "references" / "full-frame-cards.md": (
            "`--wc-grey`",
            "`signalstats` → `YAVG`",
            "white starburst **1.3 seconds later**",
            "Protect the glyphs, never readability with a scrim panel",
            "add `shortest=1`",
        ),
    }
    for path, snippets in expected.items():
        text = path.read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        for snippet in snippets:
            assert " ".join(snippet.split()) in normalized, (
                f"{path.relative_to(REPO_ROOT)} lost {snippet!r}"
            )


def test_production_skill_keeps_the_canonical_shape_and_cta_rule():
    skill = SKILLS / "production" / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    front_matter = _front_matter(skill)

    assert front_matter["metadata"]["context7-sources"] == [
        "/addyosmani/agent-skills"
    ]
    for heading in (
        "## When to Use",
        "## When NOT to Use",
        "## Core Process",
        "## Common Rationalizations",
        "## Red Flags",
        "## Verification",
    ):
        assert heading in text
    assert "Tail CTAs bias long" in text
    assert "changes only the CTA hold" in text


def test_hygiene_hooks_cover_the_complete_skill_contract_surface():
    config = yaml.safe_load(PRE_COMMIT_CONFIG.read_text(encoding="utf-8"))
    hooks = {
        hook["id"]: hook
        for repo in config["repos"]
        for hook in repo["hooks"]
    }
    skill_paths = [
        path.relative_to(REPO_ROOT).as_posix()
        for path in SKILLS.rglob("*")
        if path.is_file()
    ]

    for hook_id in ("end-of-file-fixer", "trailing-whitespace"):
        matcher = re.compile(hooks[hook_id]["files"]).search
        unmatched = [path for path in skill_paths if not matcher(path)]
        assert not unmatched, f"{hook_id} misses {unmatched}"
        assert not matcher("docs/running-order.md")
        assert not matcher("README.md")


def test_validator_scripts_parse_cleanly():
    subprocess.run(["bash", "-n", str(REPO_ROOT / "scripts" / "check-skill-frontmatter.sh")],
                   check=True)
    subprocess.run(["bash", "-n", str(REPO_ROOT / "scripts" / "check-skill-index.sh")],
                   check=True)
    subprocess.run([sys.executable, "-m", "py_compile",
                    str(REPO_ROOT / "scripts" / "check-doc-links.py")],
                   check=True)


def _write_fixture_skill(path: Path, *, doc_type: str = "procedure") -> None:
    repo_root = path.parents[2] if path.name != "SKILL.md" else path.parents[3]
    entry_point = path.relative_to(repo_root).as_posix()
    skill_name = path.stem if path.name != "SKILL.md" else path.parent.name
    path.write_text(
        f"""\
---
name: {skill_name}
version: "1.0"
last_updated: "2026-08-19"
id: {skill_name}
one_line_purpose: Demonstrate contract validation.
entry_point: {entry_point}
category: meta
status: active
dependencies: []
tags: [demo]
description: >-
  Demonstrates contract validation. Use when testing the skill contract.
metadata:
  type: {doc_type}
---

# Demo
""",
        encoding="utf-8",
    )


def test_validator_scripts_work_on_fixture_repo(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "docs" / "skills").mkdir(parents=True)

    flat = repo / "docs" / "skills" / "demo.md"
    _write_fixture_skill(flat)
    nested_dir = repo / "docs" / "skills" / "nested"
    nested_dir.mkdir()
    _write_fixture_skill(nested_dir / "SKILL.md", doc_type="runbook")

    (repo / "docs" / "SKILL.md").write_text(
        """\
# Skill router

- [`demo`](skills/demo.md)
- [`nested`](skills/nested/SKILL.md)
""",
        encoding="utf-8",
    )
    (repo / "docs" / "guide.md").write_text(
        """\
# Guide

See [README](../README.md).
""",
        encoding="utf-8",
    )
    (repo / "README.md").write_text("# Readme\n", encoding="utf-8")
    (repo / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")

    subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "check-skill-frontmatter.sh"),
         str(repo)],
        check=True,
    )
    subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "check-skill-index.sh"),
         str(repo)],
        check=True,
    )
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "check-doc-links.py"),
         str(repo)],
        check=True,
    )
