"""The authored cards and timing for the feature's final pause and coda."""

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts import build_ending_pause

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "stories" / "megacut" / "ending-cards.json"
SCHEMA = REPO / "schema" / "ending-cards.schema.json"
RENDERER = REPO / "cards" / "render-cards.mjs"
TEMPLATE = REPO / "cards" / "ending.html"


def ending():
    return json.loads(MANIFEST.read_text())


def selected(doc, section):
    by_id = {card["id"]: card for card in doc["plates"]}
    return [by_id[id_] for id_ in doc[section]["plate_ids"]]


def test_ending_record_matches_its_schema():
    schema = json.loads(SCHEMA.read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(ending())


def test_pause_copy_is_owner_authored_and_ordered():
    cards = selected(ending(), "pause")
    assert [card["id"] for card in cards] == [
        "mission", "we-are", "purpose", "lesson", "left-to-teach"
    ]
    assert cards[0]["label"] == "Mission"
    assert cards[0]["title"] == "Bring new contributors to cloud native"
    assert [card.get("title") for card in cards[1:]] == [
        "We are Project Bluefin",
        "And we have one purpose",
        "One lesson",
        "Left to teach",
    ]


def test_underwater_copy_and_emphasis_are_exact():
    cards = selected(ending(), "underwater")
    assert [card["text"] for card in cards] == [
        "A million loves",
        "We are not immortal",
        "One loss hurts us more",
        "Than any of you",
        "Will EVER understand",
        "Last sighs on a deathbed",
        "Seven Days",
        "One Chain of Lives Unending",
        "Fight for Us",
        "For Nóva",
    ]
    assert cards[4]["emphasis"] == [{"text": "EVER", "style": "seared"}]


def test_the_four_closing_cards_are_centred():
    """The owner asked for the last four in one treatment -- 'same font/size as
    the other 2', 'same font/placement as the others'. Everything before them is
    a matte line under the picture."""
    cards = selected(ending(), "underwater")
    assert [card["placement"] for card in cards] == (
        ["bottom_matte"] * 6 + ["center"] * 4)


def test_underwater_windows_stay_inside_the_measured_sequence():
    doc = ending()
    cards = selected(doc, "underwater")
    movement_in = 389.8
    assert cards[0]["at"] >= doc["underwater"]["source_in"] - movement_in
    assert (cards[-1]["at"] + cards[-1]["dur"]
            <= doc["underwater"]["source_out"] - movement_in)
    for left, right in zip(cards, cards[1:]):
        assert left["at"] + left["dur"] < right["at"]


def test_retired_copy_is_kept_rather_than_deleted():
    """A retired string is authored copy too. Both halves of the sentence the
    owner split across two centre cards are still readable in the record."""
    by_id = {card["id"]: card for card in ending()["plates"]}
    assert "Break the Chain" in by_id["seven-days"]["_retired_copy"]
    assert ("Seven Days and one chain of lives unending"
            in by_id["chain-unending"]["_retired_copy"])


def test_renderer_can_enumerate_every_ending_card():
    doc = ending()
    ids = [card["id"] for card in doc["plates"]]
    assert len(ids) == 15
    assert len(set(ids)) == len(ids)
    assert all(card["kind"] == "ending" for card in doc["plates"])
    assert set(doc["pause"]["plate_ids"] + doc["underwater"]["plate_ids"]) == set(ids)

    source = RENDERER.read_text()
    assert "ending: 'ending.html'" in source
    assert "'mode'" in source
    assert "'placement'" in source
    assert "'emphasis'" in source
    assert "'wallpaper'" in source


def test_ending_template_has_safe_emphasis_and_placement_hooks():
    source = TEMPLATE.read_text()
    assert "innerHTML" not in source
    assert "seared" in source
    assert "bottom_matte" in source
    assert "window.__renderReady = true" in source


def test_pause_cards_match_act_slide_chrome_without_darkening_wallpapers():
    source = TEMPLATE.read_text()
    assert "body.pause::before" not in source
    assert "width: min(64rem, 90vw)" in source
    assert "font-family: var(--wc-font-display)" in source
    assert "font-size: clamp(2.8rem, 5vw, 4.6rem)" in source


def test_pause_duration_is_frame_exact():
    doc = ending()
    assert build_ending_pause.frame_count(doc) == 1380
    assert build_ending_pause.duration(doc) == 23.023


def test_pause_command_has_fades_black_gaps_and_no_audio(tmp_path):
    doc = ending()
    cards = tmp_path / "cards"
    cards.mkdir()
    for id_ in doc["pause"]["plate_ids"]:
        (cards / f"plate_{id_}.png").touch()

    cmd = build_ending_pause.command(
        doc, cards, tmp_path / "mission-pause.mp4", ffmpeg=["ffmpeg"]
    )
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert graph.count("fade=t=in") == 5
    assert graph.count("fade=t=out") == 5
    assert graph.count("color=c=black") == 5
    assert "concat=n=10:v=1:a=0" in graph
    assert "-an" in cmd
    assert "anullsrc" not in graph
    assert cmd[cmd.index("-frames:v") + 1] == "1380"


def test_pause_builder_runs_as_a_script(tmp_path):
    cards = tmp_path / "cards"
    cards.mkdir()
    for id_ in ending()["pause"]["plate_ids"]:
        (cards / f"plate_{id_}.png").touch()
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts" / "build_ending_pause.py"),
            "--manifest", str(MANIFEST),
            "--cards-dir", str(cards),
            "--out", str(tmp_path / "pause.mp4"),
            "--print-command",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "-frames:v 1380" in proc.stdout


def test_the_fight_card_lights_the_bluefin_letters():
    """Owner: "Blue F's". The letters are picked by the project's own rule --
    tools/blueletters.py lights B, b, F and f -- not by hand, and the colour
    is the credits' accent rather than a second blue invented for one card."""
    card = {plate["id"]: plate for plate in ending()["plates"]}["fight-for-us"]
    assert card["blue_letters"] is True
    assert "BbFf" in (REPO / "tools" / "blueletters.py").read_text()
    template = TEMPLATE.read_text()
    assert "'BbFf'.includes(char)" in template
    assert "#93c5fd" in template


def test_the_nova_card_sets_the_wheel_as_a_letter_and_sears_only_the_accent():
    """Owner: "make the o the k8s symbol and make the accent above the symbol
    SEAR". The mark is somebody else's trademark and is reproduced as drawn;
    what is seared is the acute, which is ours."""
    card = {plate["id"]: plate for plate in ending()["plates"]}["for-nova"]
    assert card["text"] == "For Nóva"
    assert card["glyph"] == {
        "token": "ó", "accent": "´", "accent_style": "seared"}
    assert card["glyph_src"] == "renders/marks/kubernetes.png"
    assert (REPO / card["glyph_src"]).exists()
    # The mark is credited where a CC BY asset has to be credited.
    assert "kubernetes" in (REPO / "ATTRIBUTIONS.md").read_text().lower()
    # The renderer resolves and existence-checks the mark like any other asset.
    source = RENDERER.read_text()
    assert "'glyph_src'" in source
    assert "'glyph'" in source


def test_a_card_that_cannot_fit_is_measured_rather_than_clipped():
    """The card is 1920px wide and hides overflow, so copy that does not fit
    vanishes silently. Owner: "measure this whole thing"."""
    template = TEMPLATE.read_text()
    assert "function fit(" in template
    assert "line.scrollWidth" in template
    assert "window.__fit" in template
    assert "__fit" in RENDERER.read_text()
