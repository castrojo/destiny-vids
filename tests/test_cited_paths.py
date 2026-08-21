"""A repo path named outside fenced Markdown examples must actually exist.

`tests/test_doc_links.py` checks relative *Markdown links*. It does not see a
path cited in prose -- inside a JSON `_note`, a module docstring, a comment --
and that is where this repo's provenance actually lives. Two records went
wrong exactly there:

  * `videos/yt_nightwish_perfume_of_the_timeless.json` is named as THE rights
    record for the Perfume thread by three files. It has never existed (#226).
  * `stories/megacut/scream-card.json` was named by `build_scream_card.py`'s
    docstring and by `megacut.json`'s `_what` as the source of the owner's
    verbatim copy. The builder actually reads `megacut-cards.json`.

A citation that cannot be opened is the shape of a fact nobody can check --
which matters most for exactly the claims this project is strictest about:
where a rights posture is recorded, and whose words a card is reproducing.

Only paths under a KNOWN top-level directory are checked, and only ones that
look like a file (they carry a suffix). That keeps the check to real citations
rather than every slash-shaped string in prose.
"""
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Committed trees worth citing. `renders/`, `media/` and `keyframes/` are
# deliberately absent: they are gitignored build outputs, so a reference to
# one is expected not to resolve in a fresh clone.
CITED_DIRS = (
    "cards", "corpus", "dialogue", "docs", "examples", "inbox", "music",
    "redactions", "schema", "scripts", "segments", "stories", "tags", "tests",
    "tools", "videos", "vocab",
)

# The top-level directory must sit at a real path boundary. Without the
# lookbehind, `renders/plates-megacut-cards/plate_scream.png` matches on its
# tail as `cards/plate_scream.png` -- a gitignored build output reported as a
# broken citation.
CITATION = re.compile(
    r"(?<![\w/.-])((?:" + "|".join(CITED_DIRS) + r")/[A-Za-z0-9_./-]+"
    r"\.(?:json|jsonl|py|yaml|yml|md|sh|mjs|js|html|css|png|webp|srt|vtt))\b"
)
FENCED_BLOCK = re.compile(r"^(```|~~~).*?^\1\s*$", re.MULTILINE | re.DOTALL)

# Trees that are searched for citations.
SEARCH_DIRS = ("docs", "scripts", "stories", "tools", "vocab", "videos",
               "music", "schema", "dialogue", "redactions", "corpus", "cards")
SEARCH_FILES = ("README.md", "AGENTS.md", "ATTRIBUTIONS.md")
SEARCH_SUFFIXES = {".json", ".py", ".md", ".yaml", ".yml", ".sh"}

# Paths that are named ON PURPOSE while not existing. Each entry says why,
# because adding one has to be a deliberate act rather than a way to silence
# the check.
ALLOWED_MISSING = {
    "tools/quality.py":
        "docs/skills/issues/SKILL.md cites it precisely to say it never "
        "existed here -- the sentence is about a fabricated citation",
    "tests/test_quality.py":
        "same sentence in docs/skills/issues/SKILL.md",
    "corpus/osiris.json":
        "a command EXAMPLE in README.md and docs/skills/corpus.md -- the "
        "path is the --out of a corpus run, an output rather than a record",
    "docs/foo.md":
        "a fixture path inside tests/test_doc_links.py's own assertions",
    "videos/yt_nightwish_perfume_of_the_timeless.json":
        "#226: cited by three files and has never existed. Writing it needs "
        "two owner rights calls (is a third-party re-upload an acceptable "
        "picture source, and how the accepted watermark is worded), so it "
        "is tracked as a blocked issue rather than fixed here. REMOVE THIS "
        "ENTRY when #226 lands.",
}

# The 2026-08-19 common-documentation-alignment plan and spec named these as
# worked examples; the docs that cite them mean "a file shaped like this",
# not a file that exists. The plan tree itself was pruned in #300 and the
# proposal's real files have all landed since.
_PLAN = ("a worked example in the common-layout skill docs -- the name is "
         "the illustration and the file does not exist")
ALLOWED_MISSING.update({
    "docs/skills/demo-skill.md": _PLAN + " (a worked example)",
    "docs/skills/foo.md": _PLAN + " (a worked example)",
    "docs/skills/foo/SKILL.md": _PLAN + " (a worked example)",
    "docs/skills/wrong.md": _PLAN + " (a worked counterexample)",
})


def _searched_files():
    seen = []
    for name in SEARCH_FILES:
        p = REPO_ROOT / name
        if p.is_file():
            seen.append(p)
    for d in SEARCH_DIRS:
        root = REPO_ROOT / d
        if not root.is_dir():
            continue
        for p in sorted(root.rglob("*")):
            if p.is_file() and p.suffix in SEARCH_SUFFIXES:
                if "__pycache__" in p.parts:
                    continue
                seen.append(p)
    return seen


def _cited_text(path: Path, text: str) -> str:
    return FENCED_BLOCK.sub("", text) if path.suffix == ".md" else text


@pytest.mark.parametrize("path", _searched_files(),
                         ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_every_cited_repo_path_resolves(path):
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        pytest.skip("not text")

    missing = sorted({
        cited for cited in CITATION.findall(_cited_text(path, text))
        if cited not in ALLOWED_MISSING and not (REPO_ROOT / cited).exists()
    })

    assert not missing, (
        f"{path.relative_to(REPO_ROOT)} cites {len(missing)} repo path(s) that "
        f"do not exist: {missing}. A citation that cannot be opened is a fact "
        f"nobody can check. Fix the citation, add the file, or -- if it is "
        f"deliberately named while absent -- record why in ALLOWED_MISSING."
    )


def test_the_allowlist_does_not_outlive_its_reason():
    """An allowlisted path that now EXISTS is a stale exemption.

    #226's entry in particular is meant to be deleted the day the record is
    written, and nothing else would notice.
    """
    resurrected = sorted(p for p in ALLOWED_MISSING if (REPO_ROOT / p).exists())
    assert not resurrected, (
        f"these paths are allowlisted as deliberately-missing but now exist: "
        f"{resurrected}. Drop them from ALLOWED_MISSING.")


def test_the_gate_would_have_caught_the_scream_card():
    """The regression this file was written for, stated directly."""
    text = ("Copy is the owner's, reproduced from "
            "stories/megacut/scream-card.json; the treatment is the Alien "
            "one-sheet homage the line invokes.")
    found = CITATION.findall(text)
    assert "stories/megacut/scream-card.json" in found
    assert not (REPO_ROOT / "stories/megacut/scream-card.json").exists()


def test_the_gate_ignores_gitignored_build_outputs():
    """`renders/` is a build output; citing one is not a broken citation."""
    text = "Output: renders/plates-megacut-cards/plate_scream.png -- a still."
    assert CITATION.findall(text) == []


def test_the_gate_ignores_fenced_markdown_examples():
    text = """\
The record lives elsewhere.

```python
record = "stories/megacut/example-only.json"
```
"""
    assert CITATION.findall(_cited_text(Path("guide.md"), text)) == []
