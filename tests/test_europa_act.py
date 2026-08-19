"""Act VII -- Europa: the solo-wide walk-up, the retired KubeCon card.

Offline and dependency-free, like the rest of the suite: no ffmpeg, no media,
no network. What is pinned here is the committed record's picture graph, its
frame-derived durations, and the cue list the builder turns into inputs and
overlays.
"""

import json
from pathlib import Path, PurePosixPath

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


def test_no_avatar_is_named_by_an_absolute_path():
    """An absolute path in a manifest resolves on exactly one machine.

    These read `/var/home/jorge/src/destiny-vids/renders/avatars/...`, so they
    were green on the owner's workstation and red in every other checkout --
    the worst shape a check can have, because the agent verifies, pushes, and
    gets a red it cannot reproduce.

    The invariant is the one `tools/plate.py::_load_avatar` already
    implements: a path is either RELATIVE, and resolves against the repo root,
    or `~`-rooted, and resolves against the home of whoever is running. Both
    travel. An absolute path travels nowhere, so neither kind is spelled that
    way -- including the `~/Videos` and `~/src/website` assets, which are
    outside the repo but no less machine-specific when written out in full.

    Anchoring on the *current* repo root instead would invert the test: a
    reverted `/var/home/jorge/...` string does not start with the runner's own
    checkout path, so it would pass in CI and fail only on the one machine
    where it happens to work.
    """
    doc = load()
    for plate in doc["plates"]:
        avatar = plate.get("avatar")
        if not avatar:
            continue
        assert not PurePosixPath(avatar).is_absolute(), (
            f"plate {plate.get('id')}: {avatar!r} is an absolute path -- use a "
            f"repo-relative path for a file in this repo, or a `~`-rooted one "
            f"for a file outside it")
