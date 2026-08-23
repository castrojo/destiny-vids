"""The intermission slide deck that concludes the mrbobbytables section.

The whole point of this deck is WHERE ITS WORDS LIVE. Owner, 2026-08-23:
*"Have it be the concluding text of his scene so I can edit it in one
place."* So the tests that matter here are not about pixels: they are about
the manifest never becoming a second place the copy can be edited, and about
the deck's unwritten words staying visible to the punch list.
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import build_intermission  # noqa: E402

from tools import chapter_md, placeholder  # noqa: E402

MANIFEST = REPO_ROOT / "stories" / "03-intermission-plates.json"


def committed():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_the_committed_manifest_is_what_the_generator_produces(tmp_path):
    """A slide added here by hand is reverted by the next build. The copy
    goes in chapters/III-mrbobbytables.md; this file is an output."""
    assert MANIFEST.read_text(encoding="utf-8") == build_intermission.write_manifest(
        path=tmp_path / "regenerated.json")


def test_the_manifest_says_which_file_to_edit_instead():
    doc = committed()
    assert doc["source"] == "chapters/III-mrbobbytables.md"
    assert "chapters/III-mrbobbytables.md" in doc["_what"]


def test_every_slide_comes_from_the_chapter_file():
    deck, _ = chapter_md.deck_entries("III")
    assert committed()["plates"] == deck


def test_the_deck_is_all_placeholder_and_credits_nobody():
    """Lorem under a real name is putting words in a colleague's mouth. The
    deck names nobody at all, so there is nobody to misquote."""
    plates = committed()["plates"]
    assert plates
    for spec in plates:
        assert placeholder.is_placeholder(spec), spec["id"]
        assert not spec.get("speaker")
        assert not spec.get("avatar") and not spec.get("avatar_url")


def test_the_unwritten_copy_reaches_the_punch_list():
    """`placeholder.py` reads committed JSON, so a deck that lived only as
    Markdown would report zero unwritten words -- the one direction that
    tool must never be wrong in."""
    found = {row["id"] for row in placeholder.scan()}
    assert {p["id"] for p in committed()["plates"]} <= found


def test_the_missing_bed_is_recorded_rather_than_borrowed():
    """Owner: 'I want to put a different song here eventually.' No bed is
    cleared, so the deck is silent and says so."""
    notes = " ".join(committed()["unresolved"]).lower()
    assert "bed" in notes and "silent" in notes


def test_the_deck_runs_out_on_black_rather_than_on_a_word():
    doc = committed()
    last = max(p["at"] + p["dur"] for p in doc["plates"])
    assert doc["film_sec"] == pytest.approx(last + build_intermission.TAIL)


def test_the_command_seats_each_slide_where_the_chapter_file_says(tmp_path):
    """`renders/` is gitignored, so the cards are staged here rather than
    assumed: a test that needs a previous render is a test CI cannot run."""
    plates = committed()["plates"]
    cards = tmp_path
    for spec in plates:
        (cards / f"plate_{spec['id']}.png").write_bytes(b"")
    argv = build_intermission.command(
        plates, doc_total := committed()["film_sec"], cards,
        REPO_ROOT / "renders" / "intermission" / "out.mp4",
        ffmpeg=["ffmpeg"])
    graph = argv[argv.index("-filter_complex") + 1]
    for spec in plates:
        assert f"+{spec['at']:.3f}/TB" in graph
    # the LAST -t is the output length; the earlier ones hold a still
    assert argv[len(argv) - argv[::-1].index("-t")] == str(doc_total)
    assert "-an" in argv


def test_a_slide_with_no_rendered_card_is_named_not_guessed():
    with pytest.raises(FileNotFoundError):
        build_intermission.command(
            committed()["plates"], 27.0, REPO_ROOT / "no" / "such" / "dir",
            REPO_ROOT / "renders" / "intermission" / "out.mp4",
            ffmpeg=["ffmpeg"])
