"""tools/megacut.py — the assembly stage.

These tests pin the two things that have actually gone wrong when joining
finished cuts: a segment silently losing its audio, and the filtergraph
re-encoding or mis-tagging something. They run offline and touch no footage.
"""

import json
from pathlib import Path

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


def test_a_command_can_be_built_with_no_ffmpeg_installed(tmp_path, monkeypatch):
    """The suite is offline and must run on a machine with no ffmpeg at all.
    Building a command is pure string work, so binary resolution must never
    raise here -- a missing binary surfaces when the command is *run*."""
    monkeypatch.setattr(megacut.shutil, "which", lambda _: None)
    monkeypatch.setattr(megacut, "LINUXBREW_FFMPEG", "/nonexistent/ffmpeg")
    monkeypatch.setattr(megacut, "SHIM_FFMPEG", "/nonexistent/shim/ffmpeg")
    assert megacut.ffmpeg_bin() == "ffmpeg"

    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 3.0},
    ])
    assert megacut.build_command(plan, "out.mp4")[0] == "ffmpeg"


def test_ffprobe_is_resolved_beside_the_chosen_ffmpeg(monkeypatch):
    monkeypatch.setattr(megacut, "ffmpeg_bin", lambda: "/opt/ffmpeg/bin/ffmpeg")
    assert megacut.ffprobe_bin() == "/opt/ffmpeg/bin/ffprobe"


def test_ffprobe_survives_ffmpeg_in_a_parent_directory(monkeypatch):
    """rpartition, not str.replace: a path like /opt/ffmpeg/bin/ffmpeg has the
    word twice, and replacing both yields a binary that does not exist."""
    monkeypatch.setattr(megacut, "ffmpeg_bin", lambda: "/ffmpeg/build/ffmpeg")
    assert megacut.ffprobe_bin() == "/ffmpeg/build/ffprobe"


def test_silent_clip_pins_both_legs_to_one_duration(tmp_path):
    """The legs must be equal BY CONSTRUCTION. If the silence and the picture
    disagree, concat advances each stream independently and everything after
    this segment drifts out of sync."""
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "silent", "dur": 111.5},
    ])
    graph = megacut.build_filtergraph(plan)
    assert "trim=duration=111.5" in graph, "video leg is not pinned"
    assert "anullsrc=channel_layout=5.1:sample_rate=48000:d=111.5" in graph


def test_source_clip_video_is_not_trimmed(tmp_path):
    """Only silent clips are pinned; a clip with real audio keeps its own
    length, and trimming it would silently drop the tail."""
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 3.0},
    ])
    assert "trim=duration=" not in megacut.build_filtergraph(plan)


def test_clip_dur_must_be_positive_when_given(tmp_path):
    path, _ = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "silent", "dur": 0},
    ])
    with pytest.raises(ValueError, match="must be positive"):
        megacut.load_plan(path)


def test_validation_and_encoding_resolve_the_same_file(tmp_path, monkeypatch):
    """load_plan used to check repo-root first while resolve() preferred the
    cwd, so a relative path could be validated against one file and encoded
    from a different file of the same name."""
    monkeypatch.setattr(megacut, "REPO_ROOT", tmp_path / "repo")
    (tmp_path / "repo" / "renders").mkdir(parents=True)
    (tmp_path / "repo" / "renders" / "a.mp4").write_bytes(b"repo")
    cwd = tmp_path / "elsewhere" / "renders"
    cwd.mkdir(parents=True)
    (cwd / "a.mp4").write_bytes(b"cwd")
    monkeypatch.chdir(tmp_path / "elsewhere")

    resolved = megacut.resolve("renders/a.mp4")
    assert resolved == str(tmp_path / "repo" / "renders" / "a.mp4")
    assert Path(resolved).read_bytes() == b"repo"


def test_chapters_start_on_the_act_slide_and_the_first_is_zero():
    """A marker landing after the slide drops the viewer into a card they have
    already read; YouTube ignores a list whose first mark is not 0:00."""
    plan = {"items": [
        {"kind": "card", "image": "a.png", "dur": 5.0, "chapter": "I. One"},
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 100.0},
        {"kind": "card", "image": "b.png", "dur": 15.0, "chapter": "II. Two"},
        {"kind": "clip", "path": "b.mp4", "audio": "source", "dur": 30.0},
    ]}
    marks = megacut.chapters(plan)
    assert marks == [(0.0, "I. One"), (105.0, "II. Two")]
    assert megacut.format_chapters(marks) == "0:00 I. One\n1:45 II. Two"


def test_chapters_fall_back_to_the_label_visibly():
    plan = {"items": [{"kind": "card", "image": "a.png", "dur": 5.0,
                       "label": "I — a build note"}]}
    assert megacut.chapters(plan) == [(0.0, "I — a build note")]


def test_chapters_pass_the_hour_mark():
    plan = {"items": [
        {"kind": "card", "image": "a.png", "dur": 1.0, "chapter": "I"},
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 3700.0},
        {"kind": "card", "image": "b.png", "dur": 1.0, "chapter": "II"},
    ]}
    assert megacut.format_chapters(megacut.chapters(plan)) == "0:00 I\n1:01:41 II"


def test_a_plan_may_be_read_for_its_order_before_its_footage_exists(tmp_path):
    """The running order is a decision; footage is not a precondition for
    recording it. But an item with no file must carry its own `dur`."""
    plan = {"items": [
        {"kind": "card", "image": "nope.png", "dur": 5.0, "chapter": "I"},
        {"kind": "clip", "path": "nope.mp4", "audio": "source", "dur": 10.0},
    ]}
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    assert megacut.load_plan(path, require_sources=False)["items"]
    with pytest.raises(ValueError):
        megacut.load_plan(path)

    plan["items"][1].pop("dur")
    path.write_text(json.dumps(plan))
    with pytest.raises(ValueError, match="unknowable"):
        megacut.load_plan(path, require_sources=False)
