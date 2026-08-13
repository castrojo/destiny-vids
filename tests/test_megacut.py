"""tools/megacut.py — the assembly stage.

These tests pin the two things that have actually gone wrong when joining
finished cuts: a segment silently losing its audio, and the filtergraph
re-encoding or mis-tagging something. They run offline and touch no footage.
"""

import json
import subprocess
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


# --- fades: the act-join treatment (issue #105) ------------------------------
# Measured on v0.6: every act enters dry out of the slide's digital silence,
# and several acts end hot against it. The treatment is an explicit fade the
# plan states, applied at the segment encode -- never a gain, never a
# normaliser. All fade times are ACT FILM time: they belong to the act, so
# they cannot drift when the running order moves the act.

def test_no_fade_declared_means_the_audio_chain_is_byte_identical(tmp_path):
    """The untreated path must not change by one character: the tenet's
    'passed through unprocessed' test pins it, and a plan with no fades is
    every plan that existed before #105."""
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 3.0},
    ])
    af = megacut.build_segment_command(plan, 0, "seg000.mkv")
    af_str = af[af.index("-af") + 1]
    assert af_str == ("aresample=48000,"
                      "aformat=sample_fmts=fltp:channel_layouts=5.1")
    assert "afade" not in af_str


def test_fade_in_is_applied_from_the_clips_own_start(tmp_path):
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source",
         "dur": 100.0, "fade_in": 2.0},
    ])
    af = megacut.build_segment_command(plan, 0, "seg000.mkv")
    af_str = af[af.index("-af") + 1]
    assert "afade=t=in:st=0:d=2.000" in af_str
    # the fade rides after the rate/layout normalisation, on the same stream
    assert af_str.index("aformat") < af_str.index("afade")


def test_fade_out_is_placed_against_the_clips_end(tmp_path):
    """st is dur - fade_out on the ACT FILM clock: a fade that was authored
    against the programme clock would move every time the running order did."""
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source",
         "dur": 100.0, "fade_out": 2.5},
    ])
    af = megacut.build_segment_command(plan, 0, "seg000.mkv")
    assert "afade=t=out:st=97.500:d=2.500" in af[af.index("-af") + 1]


def test_fade_out_without_an_authored_dur_probes_the_video_stream(tmp_path, monkeypatch):
    """The fade ends where the picture ends. The container's format duration
    can be the audio stream outrunning the picture, which would start the
    fade early -- so the probe asks the video stream, like the silent path."""
    probed = {}
    def fake_probe(path, stream=None):
        probed["stream"] = stream
        return 42.5
    monkeypatch.setattr(megacut, "probe_duration", fake_probe)
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "fade_out": 2.0},
    ])
    af = megacut.build_segment_command(plan, 0, "seg000.mkv")
    assert probed["stream"] == "v:0"
    assert "afade=t=out:st=40.500:d=2.000" in af[af.index("-af") + 1]


def test_no_fade_out_means_no_probe(tmp_path, monkeypatch):
    """A clip that declares nothing must not suddenly require footage to
    build a command -- --dry-run and the offline suite depend on that."""
    monkeypatch.setattr(megacut, "probe_duration",
                        lambda *a, **k: pytest.fail("probed without a fade"))
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source"},
    ])
    megacut.build_segment_command(plan, 0, "seg000.mkv")


def test_a_fade_is_seconds_and_not_negative(tmp_path):
    for bad in (-1.0, "soon"):
        path, _ = _plan(tmp_path, [
            {"kind": "clip", "path": "a.mp4", "audio": "source",
             "dur": 10.0, "fade_in": bad},
        ])
        with pytest.raises(ValueError, match="fade_in"):
            megacut.load_plan(path)


def test_a_card_cannot_carry_a_fade(tmp_path):
    """A card is generated silence; fading silence is a no-op that reads as a
    treatment. If a slide should carry sound, that is a licensing decision."""
    path, _ = _plan(tmp_path, [
        {"kind": "card", "image": "c.png", "dur": 5.0, "fade_in": 1.0},
    ])
    with pytest.raises(ValueError, match="belongs on a CLIP"):
        megacut.load_plan(path)


def test_a_silent_clip_cannot_carry_a_fade(tmp_path):
    path, _ = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "silent",
         "dur": 10.0, "fade_out": 1.0},
    ])
    with pytest.raises(ValueError, match="silent"):
        megacut.load_plan(path)


def test_fades_may_not_overlap_the_whole_clip(tmp_path):
    path, _ = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source",
         "dur": 3.0, "fade_in": 2.0, "fade_out": 2.0},
    ])
    with pytest.raises(ValueError, match="meets or exceeds"):
        megacut.load_plan(path)


def test_fade_chain_is_empty_without_declared_fades():
    assert megacut.fade_chain({"audio": "source"}, 10.0) == ""


def test_fade_chain_formats_both_ends():
    chain = megacut.fade_chain({"fade_in": 1.5, "fade_out": 2.0}, 100.0)
    assert chain == ",afade=t=in:st=0:d=1.500,afade=t=out:st=98.000:d=2.000"

# --- the #88 guard: a silent re-time must stop the build -------------------
#
# Issue #88: one act's segment came out of the filtergraph with 307.967 s of
# frames re-timed into 299.48 s of timestamps, the encoder dropped the 505
# frames that collided, ffmpeg exited 0, and the programme shipped 8.5 s short
# with every later act starting early. Nothing in any log said so. These tests
# fake the ffmpeg layer and pin the two checks that turn that failure loud.


def _run_fake_ffmpeg(monkeypatch):
    """Pretend every ffmpeg command succeeds and writes its output file."""
    def fake_run(cmd, **kw):
        Path(cmd[-2]).touch()  # the output path sits just before "-y"
        return subprocess.CompletedProcess(cmd, 0)
    monkeypatch.setattr(megacut.subprocess, "run", fake_run)
    # The conform phase is tools/conform.py's own tested concern; here every
    # clip source counts as already conformant so assemble() can be driven
    # end to end with no ffmpeg at all.
    monkeypatch.setattr(megacut.conform, "ensure",
                        lambda src, **kw: (Path(src), "conforms"))


def test_a_retimed_segment_fails_the_build(tmp_path, monkeypatch):
    """The #88 regression test: a segment whose picture is 8.5 s short of its
    source is a re-time, not rounding, and the build must STOP and say so --
    the v0.5 programme shipped exactly this because nothing checked."""
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "act2.mp4", "audio": "source"},
    ])
    _run_fake_ffmpeg(monkeypatch)
    # The source probes at its true length; the segment's video comes out at
    # the re-timed length the issue measured.
    monkeypatch.setattr(megacut, "probe_duration",
                        lambda path, stream=None: 307.967)
    monkeypatch.setattr(megacut, "probe_video_extent", lambda path: 299.48)
    with pytest.raises(RuntimeError, match=r"re-time.*#88"):
        megacut.assemble(plan, tmp_path / "out.mp4")


def test_a_healthy_build_passes_verification(tmp_path, monkeypatch):
    """The same checks pass a healthy build: segment lengths track their
    sources and the programme is the sum of its parts, within rounding."""
    _, plan = _plan(tmp_path, [
        {"kind": "card", "image": "c.png", "dur": 5.0},
        {"kind": "clip", "path": "a.mp4", "audio": "source"},
        {"kind": "clip", "path": "b.mp4", "audio": "silent", "dur": 10.0},
    ])
    _run_fake_ffmpeg(monkeypatch)
    out_path = tmp_path / "out.mp4"

    def fake_probe(path, stream=None):
        # The joined programme is the sum of its parts plus the measured
        # +0.112 s of non-accumulating join rounding; every source is 307.967.
        return 5.0 + 307.967 + 10.0 + 0.112 if Path(path) == out_path else 307.967
    monkeypatch.setattr(megacut, "probe_duration", fake_probe)
    # Healthy extents: within a frame or two of each source.
    monkeypatch.setattr(megacut, "probe_video_extent",
                        lambda path: 307.94 if "seg001" in str(path)
                        else (10.0 if "seg002" in str(path) else 5.0))
    out = megacut.assemble(plan, out_path)
    assert Path(out).exists()


def test_a_programme_that_comes_out_short_fails(tmp_path, monkeypatch):
    """The per-segment check passes and the JOIN still loses time -- the
    final check is the backstop for join-level drift, and it must fail the
    build rather than ship a short programme."""
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 100.0},
        {"kind": "clip", "path": "b.mp4", "audio": "source", "dur": 100.0},
    ])
    _run_fake_ffmpeg(monkeypatch)
    monkeypatch.setattr(megacut, "probe_video_extent", lambda path: 100.0)
    monkeypatch.setattr(megacut, "probe_duration",
                        lambda path, stream=None: 191.4)  # the join lost 8.6 s
    with pytest.raises(RuntimeError, match=r"plan sums to"):
        megacut.assemble(plan, tmp_path / "out.mp4")


def test_probe_video_extent_reads_frames_not_the_container(tmp_path, monkeypatch):
    """The extent is the video stream's own last-frame end -- the one number
    that saw #88, since the segment's audio leg stayed whole while its picture
    was re-timed. B-frame reordering puts the largest pts before the last
    packet in mux order, so the max is taken, not the tail line."""
    packets = "307.891000,0.016683\n307.941000,0.016683\n307.908000,0.016683\n"
    monkeypatch.setattr(megacut.subprocess, "run", lambda *a, **kw:
                        subprocess.CompletedProcess(a[0], 0, stdout=packets))
    extent = megacut.probe_video_extent(tmp_path / "seg000.mkv")
    assert extent == pytest.approx(307.941 + 0.016683)


def test_probe_video_extent_refuses_an_empty_answer(tmp_path, monkeypatch):
    """A segment with no readable video packets is not 'zero seconds of
    picture', it is a broken probe -- refuse rather than pass."""
    monkeypatch.setattr(megacut.subprocess, "run", lambda *a, **kw:
                        subprocess.CompletedProcess(a[0], 0, stdout=""))
    with pytest.raises(RuntimeError, match="no video packets"):
        megacut.probe_video_extent(tmp_path / "seg000.mkv")


# --- the stream-copy path (the conform cache in the assembly loop) ----------
#
# When every clip in the plan already matches the delivery spec
# (tools/conform.py), a segment's picture is REMUXED, not re-encoded -- the
# ~24 minutes of x264 the whole programme used to cost. The checks that
# caught #88 stay on in both paths.

def test_a_conforming_clip_copies_its_picture(tmp_path):
    """The copy segment has NO -vf and no encoder: the source was already
    normalised to the delivery spec, so filtering would only spend a
    generation. Audio is still decoded to PCM s24le with the plan's fades --
    the lossless-segment rule (never FLAC in a concat segment) is unchanged."""
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 3.0,
         "fade_in": 2.0},
    ])
    cmd = megacut.build_segment_copy_command(plan, 0, "seg000.mkv",
                                             "/cache/conformed.mp4")
    assert cmd[cmd.index("-c:v") + 1] == "copy"
    assert cmd[cmd.index("-c:a") + 1] == "pcm_s24le"
    assert "-vf" not in cmd and "libx264" not in cmd
    assert "-filter_complex" not in cmd
    af = cmd[cmd.index("-af") + 1]
    assert af.startswith("aresample=48000,aformat=")
    assert "afade=t=in:st=0:d=2.000" in af
    for banned in ("volume=", "loudnorm", "dynaudnorm", "alimiter"):
        assert banned not in af


def test_a_conforming_silent_clip_copies_picture_and_generates_silence(tmp_path):
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "silent", "dur": 10.0},
    ])
    cmd = megacut.build_segment_copy_command(plan, 0, "seg000.mkv",
                                             "/cache/conformed.mp4")
    assert cmd[cmd.index("-c:v") + 1] == "copy"
    assert "anullsrc=channel_layout=5.1:sample_rate=48000:d=10.0" in cmd
    assert "-t" in cmd and cmd[cmd.index("-t") + 1] == "10.0"


def test_the_copy_path_is_chosen_only_when_the_plan_targets_the_spec(tmp_path):
    """A plan at another rate or frame size still encodes every segment: its
    segments must not be spec files, and a conform cache would hand back
    59.94/1080p sources to a plan building something else."""
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 3.0},
    ])
    assert megacut._copy_path_ok(plan)

    _, legacy = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 3.0},
    ], fps="30")
    assert not megacut._copy_path_ok(legacy)
    assert not megacut._copy_path_ok(plan, allow_copy=False)


def test_cards_still_encode_on_the_copy_path(tmp_path):
    """A card is generated from a PNG -- there is nothing to copy. It encodes
    to the SAME spec, or one card would force the whole programme back onto
    the slow path."""
    _, plan = _plan(tmp_path, [{"kind": "card", "image": "c.png", "dur": 5.0}])
    cmd = megacut.build_segment_command(plan, 0, "seg000.mkv")
    assert "libx264" in cmd
    assert cmd[cmd.index("-profile:v") + 1] == "high"
    assert cmd[cmd.index("-level:v") + 1] == "4.2"
    assert "+cgop" in cmd
    assert "colorprim=bt709:transfer=bt709:colormatrix=bt709" in cmd


def test_assemble_copies_every_clip_when_all_sources_conform(tmp_path, monkeypatch):
    """End to end, with ffmpeg faked: conformable clips take the copy command,
    the card encodes, and the join is still the concat demuxer."""
    _, plan = _plan(tmp_path, [
        {"kind": "card", "image": "c.png", "dur": 5.0},
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 3.0},
        {"kind": "clip", "path": "b.mp4", "audio": "silent", "dur": 10.0},
    ])
    _run_fake_ffmpeg(monkeypatch)
    monkeypatch.setattr(megacut, "probe_duration",
                        lambda path, stream=None:
                        18.1 if str(path).endswith("out.mp4") else 3.0)
    monkeypatch.setattr(megacut, "probe_video_extent",
                        lambda path: 5.0 if "seg000" in str(path)
                        else (3.0 if "seg001" in str(path) else 10.0))
    commands = []

    def spy_worker(job):
        argv, _plan_, index, seg = job
        commands.append(argv)
        Path(seg).touch()
        return index
    monkeypatch.setattr(megacut, "_segment_worker", spy_worker)

    megacut.assemble(plan, tmp_path / "out.mp4", jobs=1)
    assert "libx264" in commands[0], "the card encodes"
    assert commands[1][commands[1].index("-c:v") + 1] == "copy"
    assert commands[2][commands[2].index("-c:v") + 1] == "copy"
    assert all("-vf" not in c for c in commands[1:])


def test_assemble_encodes_clips_when_the_plan_is_off_spec(tmp_path, monkeypatch):
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 3.0},
    ], fps="30")
    _run_fake_ffmpeg(monkeypatch)
    monkeypatch.setattr(megacut, "probe_duration", lambda path, stream=None: 3.0)
    monkeypatch.setattr(megacut, "probe_video_extent", lambda path: 3.0)
    conform_calls = []
    monkeypatch.setattr(megacut.conform, "ensure",
                        lambda *a, **kw: conform_calls.append(a) or (a[0], "x"))
    megacut.assemble(plan, tmp_path / "out.mp4", jobs=1)
    assert conform_calls == [], "an off-spec plan never touches the cache"


def _touch_segment_worker(job):
    """Module-level so ProcessPoolExecutor can pickle it: build nothing, just
    'write' the segment so the assemble flow completes."""
    _argv, _plan, _index, seg = job
    Path(seg).touch()
    return _index


def test_parallel_builds_cannot_reorder_the_programme(tmp_path, monkeypatch):
    """Order is the programme. The concat list is indexed by plan position
    and written after all workers finish, so completion order can never
    shuffle it."""
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": f"{c}.mp4", "audio": "source", "dur": 3.0}
        for c in "abcd"
    ])
    _run_fake_ffmpeg(monkeypatch)
    monkeypatch.setattr(megacut, "probe_duration",
                        lambda path, stream=None:
                        12.1 if str(path).endswith("out.mp4") else 3.0)
    monkeypatch.setattr(megacut, "probe_video_extent", lambda path: 3.0)
    monkeypatch.setattr(megacut, "_segment_worker", _touch_segment_worker)

    written = {}

    def fake_write(self, text, **kw):
        written[str(self)] = text
    monkeypatch.setattr(Path, "write_text", fake_write)

    megacut.assemble(plan, tmp_path / "out.mp4", jobs=4)
    list_text = next(v for k, v in written.items() if k.endswith("segments.txt"))
    lines = [l for l in list_text.splitlines() if l]
    assert [Path(l.split("'")[1]).name for l in lines] == \
        [f"seg{i:03d}.mkv" for i in range(4)]


def test_default_jobs_scales_with_cores_and_items(monkeypatch):
    monkeypatch.setattr(megacut.os, "cpu_count", lambda: 32)
    assert megacut.default_jobs(13) == 5
    assert megacut.default_jobs(2) == 2, "never more workers than items"
    monkeypatch.setattr(megacut.os, "cpu_count", lambda: 4)
    assert megacut.default_jobs(13) == 1, "a small machine stays serial"
