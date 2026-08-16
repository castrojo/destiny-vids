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
        "Than any of you will ever understand",
        "Seven Days and one chain of lives unending",
        "Last sighs on a deathbed",
        "Break the Chain",
    ]
    assert cards[3]["emphasis"] == [{"text": "ever", "style": "seared"}]


def test_underwater_windows_stay_inside_the_measured_sequence():
    cards = selected(ending(), "underwater")
    assert cards[0]["at"] >= 6.52
    assert cards[-1]["at"] + cards[-1]["dur"] <= 37.64
    for left, right in zip(cards, cards[1:]):
        assert left["at"] + left["dur"] < right["at"]


def test_renderer_can_enumerate_every_ending_card():
    doc = ending()
    ids = [card["id"] for card in doc["plates"]]
    assert len(ids) == 12
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
    assert build_ending_pause.frame_count(doc) == 1439
    assert build_ending_pause.duration(doc) == 24.007317


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
    assert cmd[cmd.index("-frames:v") + 1] == "1439"


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
    assert "-frames:v 1439" in proc.stdout
