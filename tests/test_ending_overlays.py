"""The underwater coda: the seven closing lines burned into a movement-5
DERIVATIVE, never into the clean movement.

The clean movement 5 (renders/perfume-5.mp4) stays clean for the dinosaur
pass. The derivative (renders/perfume-5-ending.mp4) is rebuilt directly from
the SAME original source window -- source 389.800 for 117.221 s -- so the
megacut does not stack a second x264 generation on the clean render, and the
decoded PCM of the two files is bit-identical.
"""

import json
from pathlib import Path

import pytest

from scripts import build_ending_overlays

REPO = Path(__file__).resolve().parents[1]
THREAD = REPO / "stories" / "00-perfume-thread.json"
MANIFEST = REPO / "stories" / "megacut" / "ending-cards.json"


def ending():
    return json.loads(MANIFEST.read_text())


def thread():
    return json.loads(THREAD.read_text())


def movement_five(doc):
    return next(m for m in doc["movements"] if m["id"] == "perfume-5")


def underwater(doc):
    by_id = {card["id"]: card for card in doc["plates"]}
    return [by_id[id_] for id_ in doc["underwater"]["plate_ids"]]


def build_command(tmp_path):
    return build_ending_overlays.command(
        ending(),
        str(THREAD),
        tmp_path / "cards",
        tmp_path / "perfume-5-ending.mp4",
        ffmpeg=["ffmpeg"],
    )


def test_overlay_command_reads_the_original_source_and_keeps_audio_untreated(
        tmp_path):
    cmd = build_command(tmp_path)
    joined = " ".join(cmd)
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "media/yt_nightwish_perfume_of_the_timeless.mkv" in joined
    assert "-c:a flac" in joined
    assert "afade" not in graph
    assert "volume=" not in graph
    assert "overlay=" in graph


def test_each_line_replaces_the_previous_line():
    cards = underwater(ending())
    for previous, current in zip(cards, cards[1:]):
        assert previous["at"] + previous["dur"] < current["at"]


def test_the_command_renders_the_full_movement_from_its_measured_in_point(
        tmp_path):
    """Source 389.800 for exactly 117.221 s -- the clean movement's window."""
    cmd = build_command(tmp_path)
    assert cmd[cmd.index("-ss") + 1] == "389.800"
    # The last -t is the global output duration; earlier ones bound the
    # looped plate inputs.
    out_t = [cmd[i + 1] for i, a in enumerate(cmd[:-1]) if a == "-t"][-1]
    assert out_t == "117.221"
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "pad=1920:1080:0:138" in graph
    assert "aresample=48000" in graph


def test_enable_windows_are_half_open(tmp_path):
    """gte/lt, never between(): between() includes its upper bound, so the
    next line's first frame would carry the ghost of the previous one."""
    graph = build_command(tmp_path)[
        build_command(tmp_path).index("-filter_complex") + 1]
    assert "between(" not in graph
    assert "enable='gte(t,6.920)*lt(t,10.320)'" in graph
    # Seven Days: 33.000 + 4.200, half-open.
    assert "enable='gte(t,33.000)*lt(t,37.200)'" in graph
    # For Nóva, the last card, holds to the passage's own out point.
    assert "enable='gte(t,106.000)*lt(t,109.500)'" in graph


def test_alpha_fades_stay_inside_their_windows(tmp_path):
    graph = build_command(tmp_path)[
        build_command(tmp_path).index("-filter_complex") + 1]
    for card in underwater(ending()):
        at = float(card["at"])
        end = at + float(card["dur"])
        assert f"fade=t=in:st={at:.3f}:d={float(card['fade_in']):.3f}:alpha=1" \
            in graph, card["id"]
        fade_out_at = end - float(card["fade_out"])
        assert f"fade=t=out:st={fade_out_at:.3f}:" \
            f"d={float(card['fade_out']):.3f}:alpha=1" in graph, card["id"]


def test_overlays_apply_in_manifest_order(tmp_path):
    graph = build_command(tmp_path)[
        build_command(tmp_path).index("-filter_complex") + 1]
    chain = [m.start() for m in
             __import__("re").finditer(r"overlay=0:0", graph)]
    assert len(chain) == len(underwater(ending()))
    assert chain == sorted(chain)


def test_every_underwater_plate_png_is_required(tmp_path):
    """A missing plate is a failed render, not a silently skipped line."""
    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()
    missing = build_ending_overlays.missing_cards(ending(), cards_dir)
    assert len(missing) == len(underwater(ending()))
    for path in missing:
        path.touch()
    assert build_ending_overlays.missing_cards(ending(), cards_dir) == []


def test_the_clean_movement_declares_the_derivative_separately():
    """The canonical movement stays clean; the derivative is a pointer out."""
    move = movement_five(thread())
    assert move["out_file"] == "renders/perfume-5.mp4"
    burned = {"fade_in", "fade_out", "fade", "plates", "overlay", "cards"}
    assert not burned & set(move)
    derivative = move["ending_derivative"]
    assert derivative["out_file"] == "renders/perfume-5-ending.mp4"
    assert derivative["overlay_manifest"] == "stories/megacut/ending-cards.json"
    assert derivative["overlay_section"] == "underwater"


def test_the_derivative_window_matches_the_clean_movement():
    move = movement_five(thread())
    assert float(move["in"]) == pytest.approx(389.800)
    assert float(move["duration"]) == pytest.approx(117.221)
