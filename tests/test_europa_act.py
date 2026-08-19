"""Act VII -- Europa: the solo-wide walk-up, the retired KubeCon card.

Offline and dependency-free, like the rest of the suite: no ffmpeg, no media,
no network. What is pinned here is the committed record's picture graph, its
frame-derived durations, and the cue list the builder turns into inputs and
overlays.
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "stories" / "07-europa-plates.json"

from scripts import build_europa  # noqa: E402


def load():
    return json.loads(MANIFEST.read_text())


def test_walk_up_keeps_only_the_solo_wide():
    doc = load()
    walk = next(s for s in doc["picture"]["segments"]
                if s["label"] == "walk-up")
    assert walk["frames"] == [3443, 3509]
    assert "fade_out" not in walk
    wrap = next(s for s in doc["picture"]["segments"]
                if s["label"] == "wrap")
    assert "fade_in" not in wrap


def test_kubecon_card_is_retired_but_its_copy_is_recoverable():
    doc = load()
    assert doc["endcard"]["retired"] is True
    assert "KubeCon" in doc["endcard"]["_note"]
    assert doc["endcard"]["retired_note"]
    assert doc["endcard"] not in build_europa._cues(doc)


def test_new_picture_lengths_are_frame_derived():
    doc = load()
    pic = doc["picture"]
    assert pic["content_sec"] == 95.333333
    assert pic["delivered_frames"] == 2862
    assert pic["delivered_sec"] == 95.4
    assert doc["film_sec"] == 95.4


def test_laura_reveal_clears_before_its_half_open_boundary():
    reveal = load()["reveal"]
    end = reveal["at"] + reveal["dur"]
    assert end == 88.0
    assert reveal["fade_out_at"] + reveal["fade_out"] < end


def test_alolita_uses_the_verified_repo_avatar():
    doc = load()
    alolita = next(p for p in doc["plates"] if p["id"] == "d03")
    assert alolita["speaker"] == "alolita"
    avatar = Path(alolita["avatar"])
    if not avatar.is_absolute():
        avatar = REPO / avatar
    assert avatar == REPO / "renders" / "avatars" / "alolita.png"


def test_build_command_has_no_endcard_input_or_overlay(tmp_path):
    doc = load()
    cmd, _ = build_europa.build_commands(
        doc, "/project", tmp_path / "plates",
        tmp_path / "master.mp4", tmp_path / "delivered.mp4",
        ffmpeg=["ffmpeg"],
    )
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "endcard.png" not in " ".join(cmd)
    assert len(build_europa._cues(doc)) == len(doc["plates"]) + 1
    assert "90.8" not in graph
