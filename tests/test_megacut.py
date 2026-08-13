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
    """Every segment must carry both streams; a missing leg is the classic way
    an assembly desynchronises partway through. The join reads the segments in
    order, so a segment with no audio would silently shift everything after
    it."""
    _, plan = _plan(tmp_path, [
        {"kind": "card", "image": "c.png", "dur": 5.0},
        {"kind": "clip", "path": "a.mp4", "audio": "silent", "dur": 10.0},
        {"kind": "clip", "path": "b.mp4", "audio": "source", "dur": 3.0},
    ])
    for item in plan["items"]:
        graph = megacut.build_filtergraph(plan, [item])
        assert "[v0]null[vout]" in graph
        assert "[a0]anull[aout]" in graph


def test_a_segment_is_never_a_concatenation_of_one(tmp_path):
    """`concat=n=1` reads as a harmless no-op and is not one: on one act it
    re-timed 307.967s of frames into 299.48s of timestamps, the encoder dropped
    the frames that collided, and the programme came out 8.5s short with every
    later act starting early. The join is the concat DEMUXER, not a filter."""
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 3.0},
    ])
    assert "concat" not in megacut.build_filtergraph(plan, plan["items"])

    _, two = _plan(tmp_path, [
        {"kind": "card", "image": "c.png", "dur": 5.0},
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 3.0},
    ])
    with pytest.raises(ValueError):
        megacut.build_filtergraph(two)


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
    graph = "".join(megacut.build_filtergraph(plan, [i]) for i in plan["items"])
    assert graph.count("fps=60000/1001") == 2


def test_colour_is_written_into_the_x264_vui(tmp_path):
    """-color_primaries describes the frames; x264 copies only the matrix from
    them and leaves primaries/transfer `unknown`. Both must be set.

    On the SEGMENT, which is the stage that encodes: the join copies the
    bitstream, so a VUI written any later would never reach it."""
    path, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 3.0},
    ])
    cmd = megacut.build_segment_command(plan, 0, "seg000.mkv")
    assert "-color_primaries" in cmd
    assert "colorprim=bt709:transfer=bt709:colormatrix=bt709" in cmd
    assert "copy" not in cmd, "the segment encodes; only the join copies"


def test_the_join_copies_the_picture_and_encodes_the_sound_once(tmp_path):
    """The reason segmenting costs no quality. Video is encoded at the segment
    and copied here, so there is one video generation. Audio rides the segments
    as lossless 24-bit PCM and is encoded to AAC once, ACROSS the joins --
    encoding AAC per segment would give every cut its own encoder delay and
    padding. PCM rather than FLAC because the concat demuxer binds the first
    file's extradata to the whole stream, and FLAC keeps its STREAMINFO
    there."""
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 3.0},
    ])
    seg = megacut.build_segment_command(plan, 0, "seg000.mkv")
    assert seg[seg.index("-c:a") + 1] == "pcm_s24le"

    join = megacut.build_concat_command(plan, "segments.txt", "out.mp4")
    assert join[join.index("-c:v") + 1] == "copy"
    assert join[join.index("-c:a") + 1] == "aac"
    assert "-safe" in join and join[join.index("-safe") + 1] == "0"


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
    assert megacut.build_segment_command(plan, 0, "seg000.mkv")[0] == "ffmpeg"
    assert megacut.build_concat_command(plan, "l.txt", "out.mp4")[0] == "ffmpeg"


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


# --- sub-chapters: an act's own internal marks (issue #92) ------------------
#
# TWO CLOCKS, and naming them is the whole point (issue #109 burned two
# sessions on exactly this):
#   * the act manifest's `at` is ACT FILM time -- where the mark lands inside
#     that act's own delivered file;
#   * chapters() counts in PROGRAMME time -- the running total of item
#     durations.
# A sub-chapter therefore lands at clip_start_programme + at_film. The
# manifest's `src` is SOURCE time -- the anchor back into the original
# footage -- and assembly never reads it.


def _sub_chapter_plan(tmp_path, marks):
    """A programme plan plus the ACT'S OWN manifest holding its marks. The
    plan carries only a pointer, so the act keeps its own timecodes."""
    manifest = tmp_path / "act2.json"
    manifest.write_text(json.dumps({"chapters": marks}))
    plan = {"items": [
        {"kind": "card", "image": "a.png", "dur": 5.0, "chapter": "I. One"},
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 100.0},
        {"kind": "card", "image": "b.png", "dur": 5.0, "chapter": "II. Two"},
        {"kind": "clip", "path": "b.mp4", "audio": "source", "dur": 200.0,
         "sub_chapters": str(manifest)},
    ]}
    return plan


def test_default_chapter_list_is_byte_identical_without_opt_in(tmp_path):
    """The published one-entry-per-act list must not silently change
    granularity: sub-chapters are emitted only when explicitly asked for."""
    plan = _sub_chapter_plan(tmp_path, [
        {"at": 54.234, "title": "TOC", "src": 72.0},
        {"at": 147.801, "title": "The Long Walk", "src": 165.567},
    ])
    default = megacut.chapters(plan)
    assert default == [(0.0, "I. One"), (105.0, "II. Two")]
    # An explicit False is the same call, not a different default.
    assert megacut.chapters(plan, include_sub_chapters=False) == default
    assert megacut.format_chapters(default) == "0:00 I. One\n1:45 II. Two"


def test_opt_in_emits_sub_chapters_at_programme_time(tmp_path):
    """`at` is ACT FILM time; chapters() counts PROGRAMME time. Act II's clip
    starts at 105.0 (card) + 5.0 (slide) = 110.0 on the programme clock, so a
    mark at film 54.234 lands at programme 164.234."""
    plan = _sub_chapter_plan(tmp_path, [
        {"at": 54.234, "title": "TOC", "src": 72.0},
        {"at": 147.801, "title": "The Long Walk", "src": 165.567},
    ])
    marks = megacut.chapters(plan, include_sub_chapters=True)
    assert marks == [
        (0.0, "I. One"),
        (105.0, "II. Two"),
        (164.234, "TOC"),
        (257.801, "The Long Walk"),
    ]
    assert megacut.format_chapters(marks) == (
        "0:00 I. One\n1:45 II. Two\n2:44 TOC\n4:17 The Long Walk")


def test_an_act_with_no_sub_chapters_is_a_no_op(tmp_path):
    """An act that never emitted marks -- or whose pointer names a manifest
    with an empty `chapters` -- leaves the list exactly as it was."""
    plan = _sub_chapter_plan(tmp_path, [])
    assert megacut.chapters(plan, include_sub_chapters=True) == [
        (0.0, "I. One"), (105.0, "II. Two")]
    plan["items"][3].pop("sub_chapters")
    assert megacut.chapters(plan, include_sub_chapters=True) == [
        (0.0, "I. One"), (105.0, "II. Two")]


def test_a_sub_chapter_mark_without_a_film_time_is_an_error(tmp_path):
    """`at` is the whole value -- a mark that names only a source timecode
    would be placed on the wrong clock, silently."""
    plan = _sub_chapter_plan(tmp_path, [{"title": "TOC", "src": 72.0}])
    with pytest.raises(ValueError, match="act film time"):
        megacut.chapters(plan, include_sub_chapters=True)


def test_sub_chapters_belong_on_the_clip_not_the_card(tmp_path):
    path, _ = _plan(tmp_path, [
        {"kind": "card", "image": "c.png", "dur": 5.0,
         "sub_chapters": "stories/02-endless-forms-plates.json"},
    ])
    with pytest.raises(ValueError, match="CLIP"):
        megacut.load_plan(path)


def test_sub_chapters_is_a_pointer_not_the_marks(tmp_path):
    path, _ = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 3.0,
         "sub_chapters": [{"at": 1.0, "title": "TOC"}]},
    ])
    with pytest.raises(ValueError, match="pointer"):
        megacut.load_plan(path)


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


# --- --locate: a review note's timecode -> the act that has to change --------

def test_parse_stamp_reads_the_shapes_a_review_note_uses():
    assert megacut.parse_stamp("763") == 763.0
    assert megacut.parse_stamp("12:43") == 763.0
    assert megacut.parse_stamp("1:02:11") == 3731.0
    assert megacut.parse_stamp("12:43.5") == 763.5
    for bad in ("", "1:2:3:4", "12:", ":30"):
        with pytest.raises(ValueError):
            megacut.parse_stamp(bad)


def _locate_plan():
    return {"items": [
        {"kind": "card", "image": "a.png", "dur": 5.0, "chapter": "I. One"},
        {"kind": "clip", "path": "one.mp4", "audio": "source", "dur": 100.0},
        {"kind": "card", "image": "b.png", "dur": 15.0, "chapter": "II. Two"},
        {"kind": "clip", "path": "two.mp4", "audio": "source", "dur": 30.0},
    ]}


def test_locate_maps_a_programme_timecode_onto_the_act_and_its_own_clock():
    """The note is taken against the programme; the fix is made against one
    act's file. Doing that arithmetic by hand is how a round of notes gets
    applied to the wrong act."""
    plan = _locate_plan()
    assert megacut.locate(plan, 0.0) == ("I. One", 0.0, None)
    assert megacut.locate(plan, 30.0) == ("I. One", 25.0, "one.mp4")
    # 105.0 is the first frame of act II's slide, not the last of act I.
    assert megacut.locate(plan, 105.0) == ("II. Two", 0.0, None)
    assert megacut.locate(plan, 130.0) == ("II. Two", 10.0, "two.mp4")


def test_locate_lands_a_note_past_the_end_on_the_last_act():
    """A note taken off a scrub bar can sit a frame past the last item; it is
    still a note about the closing act, not an error to raise at the owner."""
    title, offset, path = megacut.locate(_locate_plan(), 10_000.0)
    assert (title, path) == ("II. Two", "two.mp4")
    assert offset > 30.0
