"""tools/megacut.py — the assembly stage.

These tests pin the two things that have actually gone wrong when joining
finished cuts: a segment silently losing its audio, and the filtergraph
re-encoding or mis-tagging something. They run offline and touch no footage.
"""

import json

import pytest

from tools import megacut


def _plan(tmp_path, items, **kw):
    for item in items:
        src = item.get("image") or item.get("path")
        if src and not str(src).startswith("/nope"):
            p = tmp_path / src
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"x")
            item["image" if "image" in item else "path"] = str(p)
    plan = {"output": str(tmp_path / "out.mp4"), "items": items, **kw}
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    return path, plan


def test_clip_must_state_its_audio(tmp_path):
    """A clip that defaulted to silence would ship a mute segment that looks
    fine in every log, so the tool refuses to guess."""
    path, _ = _plan(tmp_path, [{"kind": "clip", "path": "a.mp4"}])
    with pytest.raises(ValueError, match="must be 'source' or 'silent'"):
        megacut.load_plan(path)


def test_rejects_unknown_kind(tmp_path):
    path, _ = _plan(tmp_path, [{"kind": "sting", "path": "a.mp4"}])
    with pytest.raises(ValueError, match="kind must be"):
        megacut.load_plan(path)


def test_rejects_missing_source(tmp_path):
    path, _ = _plan(tmp_path, [{"kind": "clip", "path": "/nope/a.mp4",
                                "audio": "source"}])
    with pytest.raises(ValueError, match="does not exist"):
        megacut.load_plan(path)


def test_card_needs_a_positive_duration(tmp_path):
    path, _ = _plan(tmp_path, [{"kind": "card", "image": "c.png", "dur": 0}])
    with pytest.raises(ValueError, match="positive dur"):
        megacut.load_plan(path)


def test_every_item_contributes_one_video_and_one_audio_leg(tmp_path):
    """concat needs both streams from every segment; a missing leg is the
    classic way an assembly desynchronises partway through."""
    _, plan = _plan(tmp_path, [
        {"kind": "card", "image": "c.png", "dur": 5.0},
        {"kind": "clip", "path": "a.mp4", "audio": "silent", "dur": 10.0},
        {"kind": "clip", "path": "b.mp4", "audio": "source", "dur": 3.0},
    ])
    graph = megacut.build_filtergraph(plan)
    assert "[v0][a0][v1][a1][v2][a2]concat=n=3:v=1:a=1[vout][aout]" in graph


def test_silent_clip_gets_generated_silence_of_matching_length(tmp_path):
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "silent", "dur": 111.5},
    ])
    graph = megacut.build_filtergraph(plan)
    assert "anullsrc=channel_layout=5.1:sample_rate=48000:d=111.5" in graph


def test_source_audio_is_never_gained(tmp_path):
    """The audio tenet: pass it through, do not process it."""
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 3.0},
    ])
    graph = megacut.build_filtergraph(plan)
    for banned in ("volume=", "loudnorm", "dynaudnorm", "acompressor",
                   "alimiter", "equalizer"):
        assert banned not in graph


def test_cards_are_flattened_onto_real_black(tmp_path):
    """Dropping alpha alone can fringe: the colour under a fully transparent
    pixel is undefined."""
    _, plan = _plan(tmp_path, [{"kind": "card", "image": "c.png", "dur": 5.0}])
    graph = megacut.build_filtergraph(plan)
    assert "color=c=black:s=1920x1080" in graph
    assert "overlay=0:0" in graph


def test_everything_lands_on_one_frame_rate(tmp_path):
    _, plan = _plan(tmp_path, [
        {"kind": "card", "image": "c.png", "dur": 5.0},
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 3.0},
    ])
    graph = megacut.build_filtergraph(plan)
    assert graph.count("fps=60000/1001") == 2


def test_colour_is_written_into_the_x264_vui(tmp_path):
    """-color_primaries describes the frames; x264 copies only the matrix from
    them and leaves primaries/transfer `unknown`. Both must be set."""
    path, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 3.0},
    ])
    cmd = megacut.build_command(plan, "out.mp4")
    assert "-color_primaries" in cmd
    assert "colorprim=bt709:transfer=bt709:colormatrix=bt709" in cmd


def test_expected_duration_sums_the_parts(tmp_path):
    _, plan = _plan(tmp_path, [
        {"kind": "card", "image": "c.png", "dur": 5.0},
        {"kind": "clip", "path": "a.mp4", "audio": "silent", "dur": 111.5},
        {"kind": "card", "image": "d.png", "dur": 5.0},
    ])
    assert megacut.expected_duration(plan) == pytest.approx(121.5)
