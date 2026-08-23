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
    assert "anullsrc=channel_layout=stereo:sample_rate=48000:d=111.5" in graph


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


def test_final_mux_applies_only_an_explicit_static_master_gain(tmp_path):
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 3.0},
    ])
    plan["master_gain_db"] = -1.7
    cmd = megacut.build_concat_command(plan, "segments.txt", "out.mp4")
    assert cmd[cmd.index("-af") + 1] == "volume=-1.7dB"
    assert "loudnorm" not in cmd and "alimiter" not in cmd


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
    assert "anullsrc=channel_layout=stereo:sample_rate=48000:d=111.5" in graph


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
                      "aformat=sample_fmts=fltp:channel_layouts=stereo")
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


# --- gain_db: the owner's mix decision, recorded in the plan (#164) --------
#
# A static per-act gain is a mix decision that belongs to the owner; gain_db
# is the place their decision lands. It is applied BEFORE the fades so a fade
# shapes the corrected level, and an item without one keeps a byte-identical
# audio chain.


def test_fade_chain_applies_owner_gain_before_fades():
    chain = megacut.fade_chain({"gain_db": 3.5, "fade_in": 2.0}, 100.0)
    assert chain == ",volume=+3.5dB,afade=t=in:st=0:d=2.000"


def test_fade_chain_zero_gain_is_absent():
    assert megacut.fade_chain({"gain_db": 0}, 10.0) == ""


def test_crescendo_returns_attenuated_clip_to_unity():
    item = {"gain_db": -4.0, "crescendo_out": 4.0, "crescendo_db": 4.0}
    chain = megacut.fade_chain(item, 66.4)
    assert chain == (
        ",volume=-4.0dB,"
        "volume='if(lt(t,62.400),1,pow(10,(4.000*"
        "(t-62.400)/4.000)/20))':eval=frame")


def test_crescendo_without_authored_dur_probes_video(tmp_path, monkeypatch):
    probed = {}

    def fake_probe(path, stream=None):
        probed["stream"] = stream
        return 42.5

    monkeypatch.setattr(megacut, "probe_duration", fake_probe)
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source",
         "gain_db": -4.0, "crescendo_out": 4.0, "crescendo_db": 4.0},
    ])
    af = megacut.build_segment_command(plan, 0, "seg000.mkv")
    assert probed["stream"] == "v:0"
    assert "if(lt(t,38.500)" in af[af.index("-af") + 1]


def test_crescendo_may_not_boost_above_source(tmp_path):
    path, _ = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 10.0,
         "gain_db": -2.0, "crescendo_out": 4.0, "crescendo_db": 4.0},
    ])
    with pytest.raises(ValueError, match="boost above the source"):
        megacut.load_plan(path)


def test_crescendo_fields_are_a_pair(tmp_path):
    path, _ = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 10.0,
         "crescendo_out": 4.0},
    ])
    with pytest.raises(ValueError, match="must be stated together"):
        megacut.load_plan(path)

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
        # A PROBE writes nothing. Touching cmd[-2] blindly created a file
        # called `csv=p=0` in the working directory the moment anything
        # probed through this fake -- harmless to the assertions, litter in
        # the repo.
        if any("ffprobe" in str(part) for part in cmd):
            return subprocess.CompletedProcess(cmd, 0, stdout="")
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
        # The lossless master (issue #145) is the same programme, so it
        # probes the same: both joined files are checked, not just the copy.
        joined = {out_path, out_path.with_suffix(".mkv")}
        return 5.0 + 307.967 + 10.0 + 0.112 if Path(path) in joined else 307.967
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
    assert "anullsrc=channel_layout=stereo:sample_rate=48000:d=10.0" in cmd
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
                        18.1 if str(path).endswith(("out.mp4", "out.mkv"))
                        else 3.0)
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
                        12.1 if str(path).endswith(("out.mp4", "out.mkv"))
                        else 3.0)
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


# --- the farm path: ENCODE segments on the cluster, COPY segments local -----
#
# Owner's ruling, 2026-08-16: "always prefer remote encoding when available".
# The windowed acts are still long x264 runs even with the conform cache, so
# they ride tools/farm.py; a remux is not an encode, so the copy path never
# leaves this host. All of it offline: the cluster call and the probes are
# faked, and the assertions are about WHO is asked to build what.

def _assemble_with_fakes(tmp_path, monkeypatch, items, **assemble_kw):
    """Drive assemble() with no ffmpeg, no cluster, no probes. Returns the
    (farmed, verified) call records."""
    _, plan = _plan(tmp_path, items)
    _run_fake_ffmpeg(monkeypatch)
    farmed = []
    verified = []

    def fake_farm(argv, *, inputs, out, expected_duration=None, **kw):
        farmed.append({"argv": argv, "inputs": inputs, "out": Path(out),
                       "expected_duration": expected_duration})
        Path(out).touch()

    monkeypatch.setattr(megacut.farm, "run_ffmpeg_on_cluster", fake_farm)
    monkeypatch.setattr(megacut, "verify_segment",
                        lambda plan_, i, seg: verified.append(i) or 1.0)
    total = sum(megacut.item_duration(it) for it in plan["items"])
    monkeypatch.setattr(megacut, "probe_duration",
                        lambda path, stream=None: total)
    megacut.assemble(plan, tmp_path / "out.mp4", jobs=1, **assemble_kw)
    return plan, farmed, verified


def test_farm_mode_sends_encode_segments_to_the_cluster_only(tmp_path, monkeypatch):
    """A card (always an encode) and a WINDOWED clip ride the farm; the
    conformable unwindowed clip stays on the local copy path -- shipping a
    stream copy to a cluster to memcpy it would be slower than doing it here.
    Every segment is verified wherever it was built."""
    plan, farmed, verified = _assemble_with_fakes(tmp_path, monkeypatch, [
        {"kind": "card", "image": "c.png", "dur": 5.0},
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 3.0},
        {"kind": "clip", "path": "b.mp4", "audio": "source", "trim_to": 7.0},
    ], use_farm=True, farm_jobs=2, farm_threads=8)
    # farmed is filled from worker threads: compare as a set keyed by segment.
    by_seg = {f["out"].name: f for f in farmed}
    assert sorted(by_seg) == ["seg000.mkv", "seg002.mkv"]
    for f in farmed:
        assert "libx264" in f["argv"], "a farmed segment is a real encode"
        assert "copy" != f["argv"][f["argv"].index("-c:v") + 1]
    assert by_seg["seg000.mkv"]["inputs"][0].endswith("c.png")
    assert by_seg["seg002.mkv"]["inputs"][0].endswith("b.mp4")
    # The farm-side check gets the item's own clock, not the file's.
    assert by_seg["seg000.mkv"]["expected_duration"] == 5.0
    assert by_seg["seg002.mkv"]["expected_duration"] == 7.0
    assert sorted(verified) == [0, 1, 2], "copy AND farm segments verify"


def test_no_farm_means_everything_stays_local(tmp_path, monkeypatch):
    _, farmed, _ = _assemble_with_fakes(tmp_path, monkeypatch, [
        {"kind": "card", "image": "c.png", "dur": 5.0},
        {"kind": "clip", "path": "b.mp4", "audio": "source", "trim_to": 7.0},
    ])
    assert farmed == []


def test_a_farm_failure_fails_the_build_before_the_join(tmp_path, monkeypatch):
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "b.mp4", "audio": "source", "trim_to": 7.0},
    ])
    _run_fake_ffmpeg(monkeypatch)

    def boom(argv, **kw):
        raise megacut.farm.FarmError("pod cannot run: unschedulable")
    monkeypatch.setattr(megacut.farm, "run_ffmpeg_on_cluster", boom)
    with pytest.raises(megacut.farm.FarmError, match="unschedulable"):
        megacut.assemble(plan, tmp_path / "out.mp4", jobs=1, use_farm=True)
    assert not (tmp_path / "out.mp4").exists()


def _main_with_fake_cluster(tmp_path, monkeypatch, capsys, extra_args,
                            available):
    """Run main() with the cluster probe and the build itself faked; returns
    the kwargs assemble() saw."""
    plan_path, _ = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 3.0},
    ])
    monkeypatch.setattr(megacut.farm, "cluster_available",
                        lambda *a, **k: available)
    monkeypatch.setattr(megacut, "stale_seated_acts", lambda plan: [])
    seen = {}
    monkeypatch.setattr(megacut, "assemble",
                        lambda plan, out_path, **kw: seen.update(kw))
    megacut.main([str(plan_path), *extra_args])
    return seen, capsys.readouterr().err


def test_remote_is_the_default_when_the_cluster_is_reachable(tmp_path, monkeypatch, capsys):
    seen, err = _main_with_fake_cluster(tmp_path, monkeypatch, capsys, [],
                                        (True, ""))
    assert seen["use_farm"] is True
    assert "--local" in err, "the escape hatch is advertised in the output"


def test_an_unreachable_cluster_falls_back_with_a_stated_reason(tmp_path, monkeypatch, capsys):
    """The bug the owner caught was a SILENT local default: the fallback must
    say why, in the output, every time."""
    seen, err = _main_with_fake_cluster(tmp_path, monkeypatch, capsys, [],
                                        (False, "kubectl not on PATH"))
    assert seen["use_farm"] is False
    assert "UNREACHABLE" in err and "kubectl not on PATH" in err


def test_local_forces_local_even_with_a_healthy_cluster(tmp_path, monkeypatch, capsys):
    calls = []

    def recording_available(*a, **k):
        calls.append(1)
        return (True, "")
    monkeypatch.setattr(megacut.farm, "cluster_available", recording_available)
    monkeypatch.setattr(megacut, "stale_seated_acts", lambda plan: [])
    seen = {}
    monkeypatch.setattr(megacut, "assemble",
                        lambda plan, out_path, **kw: seen.update(kw))
    plan_path, _ = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 3.0},
    ])
    megacut.main([str(plan_path), "--local"])
    assert seen["use_farm"] is False
    assert calls == [], "--local never even asks the cluster"
    assert "--local given" in capsys.readouterr().err


def test_farm_flag_on_an_unreachable_cluster_still_ships_locally(tmp_path, monkeypatch, capsys):
    """Degrade, never block: --farm pins the posture, it does not turn a
    down cluster into no video."""
    seen, err = _main_with_fake_cluster(tmp_path, monkeypatch, capsys,
                                        ["--farm"], (False, "no route to host"))
    assert seen["use_farm"] is False
    assert "no route to host" in err


def test_farm_and_local_are_mutually_exclusive(tmp_path):
    plan_path, _ = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 3.0},
    ])
    with pytest.raises(SystemExit, match="mutually exclusive"):
        megacut.main([str(plan_path), "--farm", "--local"])


# --- trim_from: skipping an act's authored head, in the programme only ------
#
# Issue #206. Two acts opened static behind their slide: act II with a 10.5 s
# black head and act VI with its own 10 s title plate. Neither was fixable
# plan-side, because `trim_to` only ever cut tails. `trim_from` is its mirror,
# and the point of doing it in the PLAN rather than in the act is that the act
# ships unchanged -- which is what keeps act VI's head plate, a rights
# condition, playing wherever the act plays standalone.

def test_a_window_is_the_two_trims_together():
    assert megacut.clip_window({}) == (0.0, None)
    assert megacut.clip_window({"trim_to": 431.267}) == (0.0, 431.267)
    assert megacut.clip_window({"trim_from": 10.5}) == (10.5, None)
    assert megacut.clip_window(
        {"trim_from": 10.0, "trim_to": 431.267}) == (10.0, 431.267)


def test_trim_from_shortens_the_programme_clock():
    """The played length is the window's, everywhere -- expected_duration,
    verify_segment and the chapter arithmetic all read it from here."""
    assert megacut.item_duration({"trim_from": 10.0, "trim_to": 431.267}) \
        == pytest.approx(421.267)
    assert megacut.item_duration({"trim_to": 431.267}) == pytest.approx(431.267)


def test_trim_from_cuts_both_streams_by_the_same_numbers(tmp_path):
    """Picture and sound are cut by one window. If only the picture moved, the
    act's head music would play over the act after it."""
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source",
         "trim_from": 10.5, "trim_to": 300.0, "fade_in": 2.0},
    ], layout="stereo")
    argv = megacut.build_segment_command(plan, 0, tmp_path / "seg.mkv")
    vf = argv[argv.index("-vf") + 1]
    af = argv[argv.index("-af") + 1]
    assert "trim=start=10.5:end=300.0" in vf
    assert vf.endswith("setpts=PTS-STARTPTS")
    assert "atrim=start=10.5:end=300.0,asetpts=PTS-STARTPTS," in af
    # The fade lands on the first frame the programme plays, not on the head
    # it skipped, because asetpts rebased the window to zero.
    assert "afade=t=in:st=0:d=2.0" in af
    assert argv[argv.index("-t") + 1] == "289.5"


def test_trim_to_alone_still_reads_as_an_end(tmp_path):
    """The old `trim=duration=` spelling is gone; on a window with no start,
    `end=` is the same cut and the same length."""
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "trim_to": 60.0},
    ], layout="stereo")
    argv = megacut.build_segment_command(plan, 0, tmp_path / "seg.mkv")
    assert "trim=end=60.0" in argv[argv.index("-vf") + 1]
    assert argv[argv.index("-t") + 1] == "60.0"


def test_trim_from_belongs_on_a_clip(tmp_path):
    path, _ = _plan(tmp_path, [
        {"kind": "card", "image": "a.png", "dur": 5.0, "trim_from": 1.0},
    ])
    with pytest.raises(ValueError, match="trim_from belongs on a CLIP"):
        megacut.load_plan(path)


def test_trim_from_and_dur_cannot_both_be_stated(tmp_path):
    """`dur` would be read as the played length while trim_from cuts the head:
    the plan's arithmetic would believe whichever it looked at first."""
    path, _ = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source",
         "trim_from": 10.0, "dur": 100.0},
    ])
    with pytest.raises(ValueError, match="dur and trim_from cannot both"):
        megacut.load_plan(path)


def test_an_empty_window_is_an_error(tmp_path):
    path, _ = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source",
         "trim_from": 60.0, "trim_to": 60.0},
    ])
    with pytest.raises(ValueError, match="the window is empty"):
        megacut.load_plan(path)


def test_fades_are_checked_against_the_window_not_the_file(tmp_path):
    """A 5 s fade pair fits a 300 s act and does not fit the 4 s of it the
    programme actually plays."""
    path, _ = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source",
         "trim_from": 296.0, "trim_to": 300.0,
         "fade_in": 2.0, "fade_out": 2.0},
    ])
    with pytest.raises(ValueError, match="meets or exceeds"):
        megacut.load_plan(path)


def test_locate_reports_the_act_film_time_the_head_was_cut_from(tmp_path):
    """The offset is what to scrub to in the ACT'S OWN project, so an act the
    programme starts 10.5 s late has every note 10.5 s further into its file."""
    plan = {"items": [
        {"kind": "clip", "path": "one.mp4", "audio": "source", "dur": 100.0},
        {"kind": "clip", "path": "two.mp4", "audio": "source",
         "chapter": "II. Two", "trim_from": 10.5, "trim_to": 60.0},
    ]}
    assert megacut.locate(plan, 110.0) == ("II. Two", 20.5, "two.mp4")


# --- chapters survive the cards being cut (owner, 2026-08-14) ---------------

def test_a_clip_can_carry_the_chapter_its_retired_slide_used_to():
    """The four Roman-numeral slides were cut. Markers are derived from the
    plan, so removing a card must not silently remove a marker: the same
    authored string moves onto the act's own clip and the marker starts where
    the act does."""
    plan = {"items": [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 99.2},
        {"kind": "clip", "path": "b.mp4", "audio": "source", "dur": 100.0,
         "chapter": "I. Project Bluefin"},
        {"kind": "clip", "path": "c.mp4", "audio": "source", "dur": 30.0},
    ]}
    assert megacut.chapters(plan) == [(99.2, "I. Project Bluefin")]


def test_a_clip_without_a_chapter_is_not_one():
    """Most clips are not acts -- the Perfume movements and the interstitials
    are not chapters, and must not fall back to their build labels."""
    plan = {"items": [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 10.0,
         "label": "Perfume, movement 2 -- a build note"},
    ]}
    assert megacut.chapters(plan) == []


def test_a_clip_chapter_starts_after_the_head_it_skips():
    """The marker is on the PROGRAMME clock, so a windowed act's marker moves
    with the window rather than with the act's own file."""
    plan = {"items": [
        {"kind": "clip", "path": "a.mp4", "audio": "source",
         "trim_from": 10.0, "trim_to": 110.0, "chapter": "VI. Wolves"},
        {"kind": "clip", "path": "b.mp4", "audio": "source", "dur": 5.0,
         "chapter": "VII. Europa"},
    ]}
    assert megacut.chapters(plan) == [(0.0, "VI. Wolves"), (100.0, "VII. Europa")]


def test_an_interstitial_card_is_never_a_chapter():
    """The scream card's own note says a scrub-bar entry would spoil the gag,
    and the label fallback was publishing its build label as a marker anyway.
    A card that declares itself an interstitial opts out."""
    plan = {"items": [
        {"kind": "card", "image": "a.png", "dur": 5.0, "chapter": "I. One"},
        {"kind": "card", "image": "b.png", "dur": 5.0, "interstitial": True,
         "label": "Interstitial — a build note"},
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 10.0,
         "chapter": "II. Two"},
    ]}
    assert megacut.chapters(plan) == [(0.0, "I. One"), (10.0, "II. Two")]


def test_the_default_layout_is_the_one_every_file_actually_has():
    """Issue #146: the default said 5.1 for months while all seven acts, every
    Prod/ master and every delivered megacut were two-channel -- so aformat
    matched stereo sources against a 5.1 layout and anullsrc spliced 5.1
    silence between stereo segments. An upmix here would be assembly inventing
    a soundfield, which the audio tenet forbids."""
    assert megacut.DEFAULT_LAYOUT == "stereo"


def test_a_plan_without_a_bitrate_asks_for_the_encoder_ceiling(tmp_path):
    """640k is not a 5.1 leftover: ffmpeg's native AAC encoder clamps stereo to
    its own ceiling (~439 kb/s measured on every delivered megacut), so this
    asks for the ceiling. A 'correct-looking' stereo number would ship a worse
    file. The real fix for the join is the lossless master, issue #145."""
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 10.0},
    ])
    cmd = megacut.build_concat_command(plan, "list.txt", "out.mp4")
    assert cmd[cmd.index("-b:a") + 1] == megacut.DEFAULT_AUDIO_BITRATE == "640k"


# --- the lossless programme master (issue #145) ------------------------------
#
# Seven acts carry FLAC masters at ~1.6-1.8 Mb/s and the programme squashed all
# of them into one ~439 kb/s AAC at the join -- so the only artifact in the
# chain with no lossless option was the final movie, which is the file the show
# is actually watched and judged by.

def test_the_master_defaults_beside_the_distribution_copy():
    assert megacut.master_output_path({}, "/x/wolves-v2.6.mp4") \
        == "/x/wolves-v2.6.mkv"
    assert megacut.master_output_path(
        {"master_output": "/y/m.mkv"}, "/x/o.mp4") == "/y/m.mkv"


def test_a_plan_can_say_it_wants_no_master():
    """An explicit null is how a plan declines one -- distinguishable from the
    key having been forgotten, which is what gets it a master."""
    assert megacut.master_output_path({"master_output": None}, "/x/o.mp4") is None


def test_the_master_keeps_the_picture_and_the_sound(tmp_path):
    """One FLAC encode and nothing else: the picture is copied off the same PCM
    segments, so the two files carry the SAME bitstream."""
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 10.0},
    ], master_gain_db=-1.7)
    cmd = megacut.build_master_command(plan, "list.txt", "out.mkv")
    assert cmd[cmd.index("-c:v") + 1] == "copy"
    assert cmd[cmd.index("-c:a") + 1] == "flac"
    assert "-b:a" not in cmd, "a lossless codec has no bitrate to state"
    # The MIX gain, and only that.
    assert cmd[cmd.index("-af") + 1] == "volume=-1.7dB"


def test_the_lossy_leg_carries_its_own_headroom_and_the_master_does_not(tmp_path):
    """Measured on this programme: the same PCM gave a FLAC master at
    -1.1 dBTP and an AAC copy at +1.0, because a lossy encoder reconstructs
    inter-sample peaks above the samples it was given. One shared gain would
    either clip the copy or needlessly duck the master."""
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 10.0},
    ], master_gain_db=-1.7, distribution_gain_db=-2.1)
    dist = megacut.build_concat_command(plan, "list.txt", "out.mp4")
    master = megacut.build_master_command(plan, "list.txt", "out.mkv")
    assert dist[dist.index("-af") + 1] == "volume=-3.8dB"
    assert master[master.index("-af") + 1] == "volume=-1.7dB"


def test_a_plan_with_no_distribution_gain_is_unchanged(tmp_path):
    """The key is optional: a plan that never states it behaves exactly as it
    did before the split."""
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "source", "dur": 10.0},
    ], master_gain_db=-1.7)
    dist = megacut.build_concat_command(plan, "list.txt", "out.mp4")
    assert dist[dist.index("-af") + 1] == "volume=-1.7dB"


# --- a windowed silent clip: the #88 guard's blind spot ---------------------
#
# `audio: "silent"` sized its silence from the WHOLE source while the picture
# was windowed by clip_window, so the two legs disagreed. verify_segment
# measured only v:0, certified the segment as correct, and the concat demuxer
# carried the overhang into every segment after it. The unwindowed case had
# already been fixed once; the windowed one reopened it.


def test_silence_is_cut_to_the_window_not_the_whole_source(tmp_path, monkeypatch):
    """The silence must be the item's PLAYED length, as the picture is."""
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "silent", "trim_to": 5.0},
    ])
    monkeypatch.setattr(megacut, "probe_duration",
                        lambda path, stream=None: 42.0)  # the file is far longer
    argv = megacut.build_segment_command(plan, 0, tmp_path / "seg000.mkv")

    assert "anullsrc=channel_layout=stereo:sample_rate=48000:d=5.0" in " ".join(argv)
    assert argv[argv.index("-t") + 1] == "5.0"
    # The picture is windowed to the same number; the two legs must agree.
    assert "trim=end=5.0" in " ".join(argv)


def test_a_windowed_silent_clip_still_honours_trim_from(tmp_path, monkeypatch):
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "silent",
         "trim_from": 2.0, "trim_to": 9.0},
    ])
    monkeypatch.setattr(megacut, "probe_duration",
                        lambda path, stream=None: 42.0)
    argv = megacut.build_segment_command(plan, 0, tmp_path / "seg000.mkv")

    assert argv[argv.index("-t") + 1] == "7.0"
    assert "d=7.0" in " ".join(argv)


def test_an_unwindowed_silent_clip_is_unchanged(tmp_path, monkeypatch):
    """The fix must not move the case that was already correct."""
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "silent", "dur": 12.0},
    ])
    monkeypatch.setattr(megacut, "probe_duration",
                        lambda path, stream=None: 42.0)
    argv = megacut.build_segment_command(plan, 0, tmp_path / "seg000.mkv")

    assert argv[argv.index("-t") + 1] == "12.0"


def test_a_segment_whose_sound_outlives_its_picture_fails_the_build(
        tmp_path, monkeypatch):
    """The durable half: measuring only v:0 is what hid this.

    The picture is the right length, so the #88 check passes. The sound runs
    to the source's full length, which the concat demuxer would carry into
    every later segment as an offset.
    """
    _, plan = _plan(tmp_path, [
        {"kind": "clip", "path": "a.mp4", "audio": "silent", "trim_to": 5.0},
    ])
    _run_fake_ffmpeg(monkeypatch)
    monkeypatch.setattr(megacut, "probe_duration",
                        lambda path, stream=None: 42.0)
    monkeypatch.setattr(megacut, "probe_video_extent", lambda path: 5.0)
    monkeypatch.setattr(megacut, "probe_audio_extent", lambda path: 42.0)

    with pytest.raises(RuntimeError, match="desyncs every segment after it"):
        megacut.assemble(plan, tmp_path / "out.mp4")


def test_a_segment_with_no_audio_stream_does_not_trip_the_check(
        tmp_path, monkeypatch):
    """0.0 means 'no audio packets', not 'zero seconds of sound'."""
    monkeypatch.setattr(megacut.subprocess, "run", lambda *a, **kw:
                        subprocess.CompletedProcess(a[0], 0, stdout=""))
    assert megacut.probe_audio_extent(tmp_path / "seg000.mkv") == 0.0


def test_probe_audio_extent_takes_the_max_not_the_last_packet(
        tmp_path, monkeypatch):
    packets = "10.000000,0.021333\n10.021333,0.021333\n9.500000,0.021333\n"
    monkeypatch.setattr(megacut.subprocess, "run", lambda *a, **kw:
                        subprocess.CompletedProcess(a[0], 0, stdout=packets))
    extent = megacut.probe_audio_extent(tmp_path / "seg000.mkv")
    assert extent == pytest.approx(10.021333 + 0.021333)


# --- assembly refuses stale acts (the "always ships stale" defect) ----------

def _stale_ws(tmp_path, fresh=False, blocked_on=None):
    """A one-act plan seating a master whose input moved after the render."""
    import os
    from tools import deliver

    src_rel = "shotlist.json"
    (tmp_path / src_rel).write_text("v1")
    master = tmp_path / "master.mp4"
    master.write_bytes(b"rendered")

    # Digest recorded against v1, then the input moves -> the act is stale.
    old_root = deliver.REPO_ROOT
    deliver.REPO_ROOT = tmp_path
    try:
        digest = deliver.source_digest([src_rel])
    finally:
        deliver.REPO_ROOT = old_root
    if not fresh:
        (tmp_path / src_rel).write_text("v2")

    delivery = tmp_path / "delivery.json"
    entry = {"path": str(master), "sources": [src_rel], "source_digest": digest}
    if blocked_on:
        entry["stale_blocked_on"] = blocked_on
    delivery.write_text(json.dumps({"masters": {"I": entry}}))

    prod = tmp_path / "01-intro.mp4"
    os.link(master, prod)          # Prod is a hardlink, exactly as publish makes it
    plan = {"output": str(tmp_path / "out.mp4"),
            "items": [{"kind": "clip", "path": str(prod), "audio": "source",
                       "label": "Act I"}]}
    return plan, delivery, tmp_path


def test_assembly_refuses_an_act_whose_master_predates_its_inputs(
        tmp_path, monkeypatch):
    """THE DEFECT: assembly seated whatever file it found.

    Nothing in the assembly stage asked whether a master was still the act its
    records describe, so an edited record with no rebuild shipped silently in
    the next programme.
    """
    from tools import deliver
    plan, delivery, root = _stale_ws(tmp_path)
    monkeypatch.setattr(deliver, "REPO_ROOT", root)

    stale = megacut.stale_seated_acts(plan, delivery_path=delivery)

    assert [n for n, _, _ in stale] == ["I"]


def test_assembly_does_not_cry_stale_over_a_rebuilt_act(tmp_path, monkeypatch):
    """The gate must not block a correct build, or it will be switched off."""
    from tools import deliver
    plan, delivery, root = _stale_ws(tmp_path, fresh=True)
    monkeypatch.setattr(deliver, "REPO_ROOT", root)

    assert megacut.stale_seated_acts(plan, delivery_path=delivery) == []


def test_a_stale_act_is_matched_through_its_prod_hardlink(tmp_path, monkeypatch):
    """Plans seat `Prod/<act>.mp4`; delivery.json names the master.

    They are the same inode and must resolve to the same act, or the gate
    would silently match nothing on the one layout the repo actually uses.
    """
    from tools import deliver
    plan, delivery, root = _stale_ws(tmp_path)
    monkeypatch.setattr(deliver, "REPO_ROOT", root)
    masters, _ = deliver.load_delivery(delivery)
    assert Path(plan["items"][0]["path"]).name != Path(masters["I"]["path"]).name
    assert megacut.stale_seated_acts(plan, delivery_path=delivery)


def test_assembly_never_refuses_over_a_stale_act(tmp_path, monkeypatch, capsys):
    """A stale act is REPORTED and seated. It never withholds the programme.

    Owner, 2026-08-17, when act III stopped every build: "you are blocking
    releases for no reason. the reasons you are given are incorrect." He was
    right on the evidence -- act III's digest covers all of vocab/casting.yaml,
    so 503 lines about OTHER acts' people marked it stale while the only two
    bindings it renders, osiris and sagira, were byte-identical. The digest
    answers "did the inputs move", never "did the picture change", and a signal
    that coarse may inform a person but may not hold the film.
    """
    plan, delivery, root = _stale_ws(tmp_path)
    monkeypatch.setattr(megacut, "stale_seated_acts",
                        lambda _plan: [("III", "Act III", None),
                                       ("VI", "Act VI", "#58")])
    monkeypatch.setattr(megacut, "expected_duration", lambda _p: 1.0)

    rc = megacut.main([str(_plan_file(tmp_path, plan)), "--dry-run"])

    assert rc == 0, "a stale act must not stop the build"
    err = capsys.readouterr().err
    assert "act III is stale and seated, with NO recorded reason" in err
    assert "act VI is stale and seated, as recorded (#58)" in err


def _plan_file(tmp_path, plan):
    f = tmp_path / "plan.json"
    f.write_text(json.dumps(plan))
    return f


def _foreign_ws(tmp_path):
    """Two stamped acts, only ONE of which the plan seats.

    Both masters carry a `built_from_commit` that is not in this history, so
    the only thing separating them is whether the programme plays them.
    """
    import os

    mega = tmp_path / "stories" / "megacut"
    mega.mkdir(parents=True)

    seated_master = tmp_path / "seated.mp4"
    seated_master.write_bytes(b"seated")
    bench_master = tmp_path / "benched.mp4"
    bench_master.write_bytes(b"benched")

    (mega / "delivery.json").write_text(json.dumps({"masters": {
        "I": {"path": str(seated_master), "built_from_commit": "dead" * 10},
        "II": {"path": str(bench_master), "built_from_commit": "beef" * 10},
    }}))

    prod = tmp_path / "01-intro.mp4"
    os.link(seated_master, prod)   # Prod is a hardlink, exactly as publish makes it
    plan = {"output": str(tmp_path / "out.mp4"),
            "items": [{"kind": "clip", "path": str(prod), "audio": "source",
                       "label": "Act I"}]}
    return plan, tmp_path


def test_only_the_acts_the_plan_seats_are_announced_as_foreign(
        tmp_path, monkeypatch):
    """REGRESSION: the "seated" in the name was unproven.

    The filter read `master.get("prod_file")`, a key no master in
    stories/megacut/delivery.json carries, so it was always `""`, the guard
    never fired, and a benched act was announced as though the programme
    played it. Over-reporting never ships wrong picture, but it trains an
    operator to scroll past the notes that matter.
    """
    from tools import deliver
    plan, root = _foreign_ws(tmp_path)
    monkeypatch.setattr(deliver, "REPO_ROOT", root)
    monkeypatch.setattr(deliver, "commit_in_history", lambda _c: False)

    assert [n for n, _, _ in megacut.foreign_seated_acts(plan)] == ["I"]


def test_a_seated_act_built_in_this_history_is_not_foreign(
        tmp_path, monkeypatch):
    """The gate must stay quiet on a correct build, or it gets ignored."""
    from tools import deliver
    plan, root = _foreign_ws(tmp_path)
    monkeypatch.setattr(deliver, "REPO_ROOT", root)
    monkeypatch.setattr(deliver, "commit_in_history", lambda _c: True)

    assert list(megacut.foreign_seated_acts(plan)) == []


def test_an_unstamped_act_is_unknown_rather_than_foreign(
        tmp_path, monkeypatch):
    """No `built_from_commit` means nobody recorded one -- not that it is
    somebody else's. Guessing would cry wolf until `publish` had run once."""
    from tools import deliver
    plan, root = _foreign_ws(tmp_path)
    doc = json.loads((root / "stories" / "megacut" / "delivery.json").read_text())
    del doc["masters"]["I"]["built_from_commit"]
    (root / "stories" / "megacut" / "delivery.json").write_text(json.dumps(doc))
    monkeypatch.setattr(deliver, "REPO_ROOT", root)
    monkeypatch.setattr(deliver, "commit_in_history", lambda _c: False)

    assert list(megacut.foreign_seated_acts(plan)) == []
