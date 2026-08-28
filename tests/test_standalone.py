import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tools import standalone


def _drc_manifest():
    return {
        "version": 1,
        "cta_asset": "assets/cta/linux-foundation-training-forest.png",
        "videos": [{
            "slug": "bad",
            "source": {
                "url": "https://www.youtube.com/watch?v=example",
                "youtube_id": "example",
                "video_format_id": "137",
                "audio_format_id": "251-drc",
                "usage_class": "third_party_copyrighted",
                "source_rights_note": "Non-commercial fan creation.",
            },
            "title": "Bad",
            "output": "~/Videos/Bad.mp4",
            "thumbnail_output": "~/Videos/Bad-thumbnail.jpg",
            "thumbnail": {"source_at": 1.0},
            "audio_probes": [{"source_at": 2.0, "duration": 1.0}],
            "overlays": [],
        }],
    }


def test_source_time_maps_through_the_blueberries_excision():
    cuts = [{"start_sec": 46.0, "end_sec": 54.0}]
    assert standalone.source_to_output(45.0, cuts) == 45.0
    assert standalone.source_to_output(97.0, cuts) == 89.0
    with pytest.raises(ValueError, match="inside removed source range"):
        standalone.source_to_output(50.0, cuts)


def test_kept_ranges_remove_exactly_the_authored_span():
    assert standalone.kept_ranges(
        120.0, [{"start_sec": 46.0, "end_sec": 54.0}]
    ) == [(0.0, 46.0), (54.0, 120.0)]


def test_manifest_rejects_drc_audio_format(tmp_path):
    path = tmp_path / "batch.json"
    path.write_text(json.dumps(_drc_manifest()))
    with pytest.raises(ValueError, match="DRC"):
        standalone.load_manifest(path)


def test_the_schema_itself_rejects_drc_audio_format():
    """The committed-record gate validates against the raw schema, not the
    loader, so a `-drc` audio format must fail schema validation on its own."""
    schema = json.loads(standalone.SCHEMA.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(_drc_manifest()))
    assert errors, "schema accepted audio_format_id '251-drc'"
    assert any(
        list(error.path)[:3] == ["videos", 0, "source"] for error in errors
    )

    clean = _drc_manifest()
    clean["videos"][0]["source"]["audio_format_id"] = "251"
    assert not list(Draft202012Validator(schema).iter_errors(clean))


def test_training_cta_is_the_approved_1080p_asset():
    import hashlib
    from PIL import Image

    path = standalone.REPO_ROOT / "assets/cta/linux-foundation-training-forest.png"
    assert Image.open(path).size == (1920, 1080)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        "46d05d65973f64c4811a02f64673db547cb2d403c58caa9fdbddc7b0da5883c5"
    )


# --------------------------------------------------------------------------
# Fetching: explicit, pinned, non-DRC formats


def test_fetch_uses_explicit_non_drc_format_ids(tmp_path):
    video = {
        "slug": "trial",
        "source": {
            "url": "https://www.youtube.com/watch?v=_OvgGtnN_Ts",
            "video_format_id": "137",
            "audio_format_id": "251",
        },
    }
    command = standalone.fetch_command(video, tmp_path / "trial.mkv")
    assert command[command.index("-f") + 1] == "137+251"
    assert command[command.index("--merge-output-format") + 1] == "mkv"
    # yt-dlp takes the extractor argument as ONE token, so the pinned player
    # client is asserted inside it rather than as a bare word. It is the
    # client that still lists the pinned video-only + non-DRC Opus rungs
    # without a PO token; `android_vr` degrades to one muxed 360p format.
    assert command[command.index("--extractor-args") + 1] == \
        "youtube:player_client=visionos"


def test_fetch_keeps_an_existing_non_empty_source(tmp_path, monkeypatch):
    """A source already on disk is never re-fetched: the download is the one
    step that reaches the network, and the file is the evidence it ran."""
    calls = []
    monkeypatch.setattr(standalone.subprocess, "run",
                        lambda *a, **k: calls.append(a))
    existing = tmp_path / "trial.mkv"
    existing.write_bytes(b"not empty")
    video = {
        "slug": "trial",
        "source": {
            "url": "https://example.invalid/x",
            "video_format_id": "137",
            "audio_format_id": "251",
        },
    }
    assert standalone._ensure_source(video, existing) == existing
    assert calls == []


def test_fetch_runs_yt_dlp_when_the_source_is_missing(tmp_path, monkeypatch):
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return None

    monkeypatch.setattr(standalone.subprocess, "run", fake_run)
    out = tmp_path / "trial.mkv"
    video = {
        "slug": "trial",
        "source": {
            "url": "https://example.invalid/x",
            "video_format_id": "137",
            "audio_format_id": "251",
        },
    }
    standalone._ensure_source(video, out)
    assert calls[0][0][0] == "yt-dlp"
    assert calls[0][1]["check"] is True


# --------------------------------------------------------------------------
# The one-pass filtergraph


def test_blueberries_filtergraph_cuts_video_and_audio_before_takeover():
    video = {
        "cuts": [{"start_sec": 46.0, "end_sec": 54.0}],
        "takeover": {"source_at": 97.0},
        "overlays": [],
    }
    graph = standalone.filtergraph(video, duration_sec=120.0, overlays=[])
    assert "trim=start=0.0:end=46.0" in graph
    assert "atrim=start=54.0:end=120.0" in graph
    assert "concat=n=2:v=1:a=1" in graph
    assert "gte(t,89.0)" in graph


def test_a_video_without_a_takeover_uses_input_one_for_its_first_plate():
    video = {"cuts": [], "overlays": []}
    graph = standalone.filtergraph(
        video,
        duration_sec=120.0,
        overlays=[{"id": "player", "at": 4.0, "dur": 30.0}],
    )
    assert "[basev][1:v]overlay=0:0" in graph


def test_a_takeover_reserves_input_one_and_plates_start_at_two():
    video = {"cuts": [], "overlays": [], "takeover": {"source_at": 100.0}}
    graph = standalone.filtergraph(
        video,
        duration_sec=120.0,
        overlays=[
            {"id": "first", "at": 4.0, "dur": 4.0},
            {"id": "second", "at": 20.0, "dur": 2.0},
        ],
    )
    assert "[basev][2:v]overlay=0:0:enable='between(t,4.0,8.0)':shortest=1" \
        in graph
    assert "[3:v]overlay=0:0:enable='between(t,20.0,22.0)':shortest=1" in graph
    # The CTA is overlaid LAST, from the input it reserved.
    assert graph.split(";")[-1].endswith(
        "[1:v]overlay=0:0:enable='gte(t,100.0)':shortest=1[outv]")


def test_every_still_overlay_is_bounded_by_the_source():
    """A looped still is an infinite input; without shortest=1 the encode
    never ends. Every overlay carries it, not just the takeover."""
    graph = standalone.filtergraph(
        {"cuts": [], "overlays": []},
        duration_sec=10.0,
        overlays=[{"id": "one", "at": 1.0, "dur": 2.0}],
    )
    assert graph.count("shortest=1") == 1
    assert graph.endswith("[outv]")


def test_an_uncut_video_with_nothing_over_it_maps_the_base_picture():
    graph = standalone.filtergraph(
        {"cuts": [], "overlays": []}, duration_sec=10.0, overlays=[])
    assert "[0:v]" in graph and "[basev]" in graph
    assert "overlay" not in graph
    assert standalone.video_out_label({"overlays": []}, []) == "[basev]"


def test_a_static_gain_below_one_scales_only_the_audio_leg():
    """Headroom is a static gain, never a limiter, and never on the picture."""
    graph = standalone.filtergraph(
        {"cuts": [], "overlays": []}, duration_sec=10.0, overlays=[],
        gain=0.75)
    assert "volume=0.750000" in graph
    assert graph.index("volume=") > graph.index("[0:a]")
    assert "loudnorm" not in graph and "acompressor" not in graph
    assert "alimiter" not in graph and "equalizer" not in graph


# --------------------------------------------------------------------------
# Overlay seats: mapped through the excisions, degraded when they cannot be


def test_overlay_source_marks_are_mapped_before_render():
    video = {
        "cuts": [{"start_sec": 46.0, "end_sec": 54.0}],
        "overlays": [{
            "id": "jorge",
            "source_at": 60.0,
            "dur": 4.0,
            "position": "left",
            "name": "Jorge Castro",
        }],
    }
    overlays, unresolved = standalone.mapped_overlays(video, 120.0)
    assert overlays[0]["at"] == 52.0
    assert unresolved == []


def test_overlay_inside_a_removed_span_degrades_to_unresolved():
    video = {
        "cuts": [{"start_sec": 46.0, "end_sec": 54.0}],
        "overlays": [{
            "id": "bad-seat",
            "source_at": 50.0,
            "dur": 4.0,
            "position": "left",
            "name": "Jorge Castro",
        }],
    }
    overlays, unresolved = standalone.mapped_overlays(video, 120.0)
    assert overlays == []
    assert unresolved[0]["id"] == "bad-seat"


def test_an_overlay_past_the_end_of_the_source_degrades_to_unresolved():
    video = {"cuts": [], "overlays": [
        {"id": "late", "source_at": 130.0, "dur": 2.0},
    ]}
    overlays, unresolved = standalone.mapped_overlays(video, 120.0)
    assert overlays == []
    assert "exceeds" in unresolved[0]["reason"]


def test_a_colliding_overlay_degrades_instead_of_being_retimed():
    """The seat the owner authored is content. A collision drops the later
    plate and records it; nothing is silently slid to make it fit."""
    video = {"cuts": [], "overlays": [
        {"id": "first", "kind": "caption", "source_at": 10.0, "dur": 4.0},
        {"id": "second", "kind": "caption", "source_at": 12.0, "dur": 4.0},
    ]}
    overlays, unresolved = standalone.mapped_overlays(video, 120.0)
    assert [o["id"] for o in overlays] == ["first"]
    assert overlays[0]["at"] == 10.0
    assert unresolved[0]["id"] == "second"
    assert "same time" in unresolved[0]["reason"]


def test_a_mapped_overlay_no_longer_carries_its_source_mark():
    video = {"cuts": [], "overlays": [
        {"id": "one", "source_at": 10.0, "dur": 4.0},
    ]}
    overlays, _ = standalone.mapped_overlays(video, 120.0)
    assert "source_at" not in overlays[0]
    assert video["overlays"][0]["source_at"] == 10.0


# --------------------------------------------------------------------------
# The encode: farm-first, one picture generation, one AAC generation


def _encode_fixture(tmp_path, monkeypatch, calls, video=None):
    monkeypatch.setattr(
        standalone.farm,
        "run_encode",
        lambda argv, **kwargs: calls.append((argv, kwargs)) or "cluster",
    )
    monkeypatch.setattr(standalone.render, "find_ffmpeg", lambda *a, **k: ["ffmpeg"])
    monkeypatch.setattr(standalone, "_source_duration", lambda *args: 120.0)
    monkeypatch.setattr(standalone, "_ensure_source", lambda *args: tmp_path / "src.mkv")
    monkeypatch.setattr(standalone.plate, "render_all", lambda *args, **kwargs: [])
    # Probing the picture reads the source with ffmpeg. These fixtures have no
    # source on disk, so the default answer is the safe one: it decoded and
    # found no matte, which `plate.place` reads as "the frame is the picture".
    monkeypatch.setattr(standalone.render, "detect_picture_status",
                        lambda *a, **k: (None, "full-frame"))
    monkeypatch.setattr(standalone.thumbnail, "extract_source_frame",
                        lambda *args, **kwargs: tmp_path / "src.png")
    monkeypatch.setattr(standalone.thumbnail, "save_jungle_thumbnail",
                        lambda *args: tmp_path / "thumb.jpg")
    monkeypatch.setattr(standalone.peaks, "correct_delivered_peak",
                        lambda *args, **kwargs: 1.0)
    monkeypatch.setattr(standalone, "_unresolved_path",
                        lambda slug: tmp_path / f"{slug}-unresolved.json")
    return video or {
        "slug": "x",
        "cuts": [],
        "overlays": [],
        "output": str(tmp_path / "x.mp4"),
    }


def test_build_routes_the_encode_through_run_encode(monkeypatch, tmp_path):
    calls = []
    video = _encode_fixture(tmp_path, monkeypatch, calls)
    monkeypatch.setattr(Path, "exists", lambda self: True)

    standalone.encode_video(
        video,
        tmp_path / "src.mkv",
        tmp_path / "cta.png",
        tmp_path,
        local=False,
    )
    assert len(calls) == 1
    assert calls[0][1]["local"] is False


def test_the_encode_takes_one_picture_and_one_aac_generation(monkeypatch,
                                                             tmp_path):
    calls = []
    video = _encode_fixture(tmp_path, monkeypatch, calls)
    standalone.encode_video(video, tmp_path / "src.mkv", tmp_path / "cta.png",
                            tmp_path, local=False)
    argv = calls[0][0]
    assert argv.count("libx264") == 1
    assert argv.count("aac") == 1
    assert "-ar" not in argv, "the source sample rate is never resampled"
    assert argv[argv.index("-b:a") + 1] == "320k"
    assert argv[-1] == str(tmp_path / "x.mp4")


def test_a_video_without_a_takeover_stages_no_cta_input(monkeypatch, tmp_path):
    """farm.rewrite_argv_for_pod rejects an input the argv never reads, so a
    CTA-less video must not list the CTA among its staged inputs."""
    calls = []
    video = _encode_fixture(tmp_path, monkeypatch, calls)
    standalone.encode_video(video, tmp_path / "src.mkv", tmp_path / "cta.png",
                            tmp_path, local=False)
    argv, kwargs = calls[0]
    assert kwargs["inputs"] == [tmp_path / "src.mkv"]
    assert str(tmp_path / "cta.png") not in argv


def test_every_staged_input_appears_verbatim_in_the_argv(monkeypatch,
                                                         tmp_path):
    calls = []
    video = _encode_fixture(tmp_path, monkeypatch, calls, video={
        "slug": "x",
        "cuts": [],
        "takeover": {"source_at": 100.0},
        "overlays": [],
        "output": str(tmp_path / "x.mp4"),
    })
    standalone.encode_video(video, tmp_path / "src.mkv", tmp_path / "cta.png",
                            tmp_path, local=False)
    argv, kwargs = calls[0]
    assert kwargs["inputs"] == [tmp_path / "src.mkv", tmp_path / "cta.png"]
    for path in kwargs["inputs"]:
        assert str(path) in argv
    assert kwargs["expected_duration"] == 120.0
    assert argv[argv.index(str(tmp_path / "cta.png")) - 1] == "-i"
    assert argv[argv.index(str(tmp_path / "cta.png")) - 2] == "60000/1001"
    assert argv[argv.index(str(tmp_path / "cta.png")) - 5] == "-loop"


def test_the_peak_rerun_rebuilds_from_the_source_not_the_output(monkeypatch,
                                                                tmp_path):
    """A correction re-encodes from the ORIGINAL source at a lower static
    gain; re-encoding the delivered file would add a second generation."""
    calls = []
    video = _encode_fixture(tmp_path, monkeypatch, calls)
    seen = {}

    def fake_correct(out_path, gain, target, rerun, **kwargs):
        seen["margin"] = kwargs.get("margin_db")
        rerun(0.5)
        return 0.5

    monkeypatch.setattr(standalone.peaks, "correct_delivered_peak",
                        fake_correct)
    standalone.encode_video(video, tmp_path / "src.mkv", tmp_path / "cta.png",
                            tmp_path, local=False)
    assert seen["margin"] == standalone.peaks.DELIVERED_BAND_MARGIN_DB
    assert len(calls) == 2
    rerun_argv = calls[1][0]
    assert str(tmp_path / "src.mkv") in rerun_argv
    assert "volume=0.500000" in " ".join(rerun_argv)
    assert rerun_argv.count(str(tmp_path / "x.mp4")) == 1


def test_the_unresolved_sidecar_is_written_even_when_it_is_empty(monkeypatch,
                                                                 tmp_path):
    calls = []
    video = _encode_fixture(tmp_path, monkeypatch, calls)
    standalone.encode_video(video, tmp_path / "src.mkv", tmp_path / "cta.png",
                            tmp_path, local=False)
    sidecar = json.loads((tmp_path / "x-unresolved.json").read_text())
    assert sidecar == {"slug": "x", "unresolved": []}


def test_an_undrawn_plate_degrades_instead_of_shifting_the_inputs(monkeypatch,
                                                                  tmp_path):
    """render_all skips full-frame cards. A skipped plate must leave the
    remaining overlay input indexes correct, not slide them by one."""
    calls = []
    video = _encode_fixture(tmp_path, monkeypatch, calls, video={
        "slug": "x",
        "cuts": [],
        "overlays": [
            {"id": "missing", "kind": "caption", "source_at": 5.0, "dur": 2.0},
            {"id": "drawn", "kind": "caption", "source_at": 20.0, "dur": 2.0},
        ],
        "output": str(tmp_path / "x.mp4"),
    })
    plates = tmp_path / "x-plates"

    def fake_render_all(entries, out_dir, picture=None):
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        drawn = Path(out_dir) / "plate_drawn.png"
        drawn.write_bytes(b"png")
        return [drawn]

    monkeypatch.setattr(standalone.plate, "render_all", fake_render_all)
    standalone.encode_video(video, tmp_path / "src.mkv", tmp_path / "cta.png",
                            tmp_path, local=False)
    argv, kwargs = calls[0]
    assert kwargs["inputs"] == [tmp_path / "src.mkv", plates / "plate_drawn.png"]
    graph = argv[argv.index("-filter_complex") + 1]
    assert "[basev][1:v]overlay=0:0:enable='between(t,20.0,22.0)'" in graph
    sidecar = json.loads((tmp_path / "x-unresolved.json").read_text())
    assert sidecar["unresolved"][0]["id"] == "missing"


def test_plates_are_measured_against_the_picture_not_the_matte(monkeypatch,
                                                               tmp_path):
    """A letterboxed source's plates are placed against its PICTURE rect.

    Bungie's cinematics are 2.39:1 inside a 16:9 file. Placing a 3rem status
    HUD or a 10%-margin nameplate against the raw frame seats it on the black
    bar -- measured at 140 px on this batch's Final Trial source, which is
    most of the HUD card. ``tools/render.detect_picture_status`` exists for
    exactly this, and gives ``None`` with ``"full-frame"`` for an unmatted
    source, which ``plate.place`` already reads as "the frame is the picture".
    """
    calls = []
    video = _encode_fixture(tmp_path, monkeypatch, calls, video={
        "slug": "x",
        "cuts": [],
        "overlays": [
            {"id": "hud", "kind": "status", "source_at": 5.0, "dur": 2.0},
        ],
        "output": str(tmp_path / "x.mp4"),
    })
    seen = {}

    def fake_render_all(entries, out_dir, picture=None):
        seen["picture"] = picture
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        drawn = Path(out_dir) / "plate_hud.png"
        drawn.write_bytes(b"png")
        return [drawn]

    monkeypatch.setattr(standalone.plate, "render_all", fake_render_all)
    monkeypatch.setattr(standalone.render, "detect_picture_status",
                        lambda *a, **k: ((0, 140, 1920, 800), "letterboxed"))
    standalone.encode_video(video, tmp_path / "src.mkv", tmp_path / "cta.png",
                            tmp_path, local=False)
    assert seen["picture"] == (0, 140, 1920, 800)


def test_the_picture_probe_reads_the_already_resolved_ffmpeg(monkeypatch,
                                                             tmp_path):
    """One encode resolves ffmpeg once; the probe must use THAT binary.

    ``encode_video`` threads its resolved prefix through the duration probe,
    the PCM reads and the encode. If the picture probe re-resolves internally,
    an explicit ``ffmpeg=`` override -- or a ``DESTINY_FFMPEG`` change --
    is honoured for the encode and not for the placement, and on this host the
    two can differ by whether H.264 decodes at all.
    """
    calls = []
    video = _encode_fixture(tmp_path, monkeypatch, calls, video={
        "slug": "x",
        "cuts": [],
        "overlays": [
            {"id": "hud", "kind": "status", "source_at": 5.0, "dur": 2.0},
        ],
        "output": str(tmp_path / "x.mp4"),
    })
    seen = {}

    def fake_status(source, ffmpeg=None):
        seen["ffmpeg"] = ffmpeg
        return (0, 140, 1920, 800), "letterboxed"

    monkeypatch.setattr(standalone.render, "detect_picture_status", fake_status)
    monkeypatch.setattr(standalone.plate, "render_all",
                        lambda *a, **k: [])
    standalone.encode_video(video, tmp_path / "src.mkv", tmp_path / "cta.png",
                            tmp_path, local=False, ffmpeg=["myffmpeg"])
    assert seen["ffmpeg"] == ["myffmpeg"]


def test_an_undecodable_picture_drops_the_seats_and_records_them(monkeypatch,
                                                                 tmp_path):
    """"No matte" and "I never looked" are different answers (issue #161).

    A source whose picture geometry cannot be decoded -- the ``ffmpeg-free``
    default this host warns about, an unreadable file -- returns the same
    ``None`` rect as a full-frame one. Placing against it silently re-seats
    every plate on the matte, which is the bug the picture probe exists to
    fix. So the affected seats are DROPPED and recorded, and the unplated
    video still ships: degrade, never block, but record.
    """
    calls = []
    video = _encode_fixture(tmp_path, monkeypatch, calls, video={
        "slug": "x",
        "cuts": [],
        "overlays": [
            {"id": "hud", "kind": "status", "source_at": 5.0, "dur": 2.0},
            {"id": "pill", "kind": "chat", "source_at": 20.0, "dur": 2.0},
        ],
        "output": str(tmp_path / "x.mp4"),
    })
    drawn = []
    monkeypatch.setattr(standalone.plate, "render_all",
                        lambda *a, **k: drawn.append(a) or [])
    monkeypatch.setattr(standalone.render, "detect_picture_status",
                        lambda *a, **k: (None, "undecodable"))
    standalone.encode_video(video, tmp_path / "src.mkv", tmp_path / "cta.png",
                            tmp_path, local=False)

    assert not drawn, "nothing may be seated against a picture nobody read"
    sidecar = json.loads((tmp_path / "x-unresolved.json").read_text())
    assert [item["id"] for item in sidecar["unresolved"]] == ["hud", "pill"]
    assert all("could not be decoded" in item["reason"]
               for item in sidecar["unresolved"])
    # The video still ships, unplated.
    assert len(calls) == 1
    graph = calls[0][0][calls[0][0].index("-filter_complex") + 1]
    assert "overlay=" not in graph


# --------------------------------------------------------------------------
# Verification arithmetic


def test_correlation_of_a_signal_with_itself_is_one():
    left = [0, 1000, -2000, 500, -100, 3000]
    assert standalone.correlation(left, list(left)) == pytest.approx(1.0)


def test_correlation_rejects_a_silent_probe_window():
    """Silence correlates with nothing; a zero-energy window must raise
    rather than divide by zero or read as a pass."""
    with pytest.raises(ValueError, match="no energy"):
        standalone.correlation([0, 0, 0, 0], [1, 2, 3, 4])


def test_a_shifted_delivered_window_still_correlates():
    """A codec primes and a container delays; a measured -1.0 ms offset is
    enough to invert a tone's correlation. The search recovers the seat."""
    reference = [0, 1000, -2000, 500, -100, 3000, -900, 400]
    window = [7, -3] + reference + [11, 5]
    score, lag = standalone.aligned_correlation(reference, window)
    assert score == pytest.approx(1.0)
    assert lag == pytest.approx(0.0, abs=1.0 / standalone.PROBE_RATE)


def test_alignment_cannot_manufacture_a_match_from_the_wrong_audio():
    """The lag search forgives delay, never content: a window from somewhere
    else correlates with nothing at any seat."""
    reference = [0, 1000, -2000, 500, -100, 3000, -900, 400]
    window = [50, -75, 25, -30, 60, -20, 15, -45, 70, -10, 33, -66]
    score, _ = standalone.aligned_correlation(reference, window)
    assert score < standalone.AUDIO_CORRELATION_FLOOR


def test_alignment_refuses_a_window_that_is_too_short_to_search():
    with pytest.raises(ValueError, match="shorter"):
        standalone.aligned_correlation([1, 2, 3, 4], [1, 2, 3])


def test_expected_output_duration_removes_every_cut():
    assert standalone.expected_duration(
        {"cuts": [{"start_sec": 46.0, "end_sec": 54.0}]}, 120.0
    ) == pytest.approx(112.0)


def test_verify_reports_a_drifted_duration_and_a_decorrelated_probe(
        monkeypatch, tmp_path):
    manifest_path = tmp_path / "batch.json"
    data = _drc_manifest()
    entry = data["videos"][0]
    entry["source"]["audio_format_id"] = "251"
    entry["slug"] = "vid"
    entry["output"] = str(tmp_path / "vid.mp4")
    entry["thumbnail_output"] = str(tmp_path / "vid.jpg")
    entry["cuts"] = [{"start_sec": 10.0, "end_sec": 20.0}]
    entry["audio_probes"] = [{"source_at": 30.0, "duration": 1.0}]
    manifest_path.write_text(json.dumps(data))
    Path(entry["output"]).write_bytes(b"mp4")

    from PIL import Image
    Image.new("RGB", (1920, 1080), (0, 0, 0)).save(entry["thumbnail_output"])

    monkeypatch.setattr(standalone.render, "find_ffmpeg", lambda *a, **k: ["ffmpeg"])
    monkeypatch.setattr(standalone, "_source_path",
                        lambda slug: tmp_path / "src.mkv")
    (tmp_path / "src.mkv").write_bytes(b"mkv")
    durations = {str(tmp_path / "src.mkv"): 120.0,
                 entry["output"]: 105.0}
    monkeypatch.setattr(standalone, "_source_duration",
                        lambda path, ffmpeg=None: durations[str(path)])
    monkeypatch.setattr(standalone, "_probe_streams", lambda *a, **k: [
        {"codec_type": "video", "codec_name": "h264"},
        {"codec_type": "audio", "codec_name": "aac"},
    ])
    monkeypatch.setattr(
        standalone, "_pcm",
        lambda path, at, dur, ffmpeg=None:
        [1, 2, 3, 4] if "src" in str(path) else [4, 3, 2, 1, 4, 3])
    monkeypatch.setattr(standalone, "_write_frame",
                        lambda *a, **k: tmp_path / "frame.png")

    problems = standalone.verify(manifest_path, "vid")
    assert any("duration" in p for p in problems)
    assert any("correlation" in p for p in problems)


def test_verify_is_quiet_when_everything_lines_up(monkeypatch, tmp_path):
    manifest_path = tmp_path / "batch.json"
    data = _drc_manifest()
    entry = data["videos"][0]
    entry["source"]["audio_format_id"] = "251"
    entry["slug"] = "vid"
    entry["output"] = str(tmp_path / "vid.mp4")
    entry["thumbnail_output"] = str(tmp_path / "vid.jpg")
    entry["cuts"] = [{"start_sec": 10.0, "end_sec": 20.0}]
    entry["audio_probes"] = [{"source_at": 30.0, "duration": 1.0}]
    manifest_path.write_text(json.dumps(data))
    Path(entry["output"]).write_bytes(b"mp4")

    from PIL import Image
    Image.new("RGB", (1920, 1080), (0, 0, 0)).save(entry["thumbnail_output"])

    monkeypatch.setattr(standalone.render, "find_ffmpeg", lambda *a, **k: ["ffmpeg"])
    monkeypatch.setattr(standalone, "_source_path",
                        lambda slug: tmp_path / "src.mkv")
    (tmp_path / "src.mkv").write_bytes(b"mkv")
    durations = {str(tmp_path / "src.mkv"): 120.0,
                 entry["output"]: 110.0}
    monkeypatch.setattr(standalone, "_source_duration",
                        lambda path, ffmpeg=None: durations[str(path)])
    monkeypatch.setattr(standalone, "_probe_streams", lambda *a, **k: [
        {"codec_type": "video", "codec_name": "h264"},
        {"codec_type": "audio", "codec_name": "aac"},
    ])
    monkeypatch.setattr(
        standalone, "_pcm",
        lambda path, at, dur, ffmpeg=None:
        [1, 2, 3, 4] if "src" in str(path) else [0, 1, 2, 3, 4, 0])
    monkeypatch.setattr(standalone, "_write_frame",
                        lambda *a, **k: tmp_path / "frame.png")
    assert standalone.verify(manifest_path, "vid") == []


def test_verify_compares_the_takeover_frame_with_the_cta_asset(monkeypatch,
                                                              tmp_path):
    """A takeover that is not the approved picture is a wrong claim on
    screen, so the delivered frame is compared to the asset itself."""
    from PIL import Image
    cta = tmp_path / "cta.png"
    Image.new("RGB", (1920, 1080), (30, 60, 90)).save(cta)
    same = tmp_path / "same.png"
    Image.new("RGB", (1920, 1080), (30, 60, 90)).save(same)
    other = tmp_path / "other.png"
    Image.new("RGB", (1920, 1080), (200, 60, 90)).save(other)

    assert standalone.frame_difference(same, cta) == pytest.approx(0.0)
    assert standalone.frame_difference(other, cta) > standalone.CTA_FRAME_TOLERANCE


def test_a_plate_the_takeover_would_cover_degrades_to_unresolved():
    """The CTA is an opaque full-frame picture composited last. A plate that
    runs into it is not on screen for the time the record says, so it is
    dropped and recorded rather than shipped invisible."""
    video = {
        "cuts": [{"start_sec": 46.0, "end_sec": 54.0}],
        "takeover": {"source_at": 97.0},
        "overlays": [
            {"id": "before", "source_at": 80.0, "dur": 4.0},
            {"id": "under", "source_at": 96.0, "dur": 4.0},
        ],
    }
    overlays, unresolved = standalone.mapped_overlays(video, 120.0)
    assert [o["id"] for o in overlays] == ["before"]
    assert unresolved[0]["id"] == "under"
    assert "takeover covers" in unresolved[0]["reason"]


def _verify_fixture(tmp_path, monkeypatch, entry_extra):
    manifest_path = tmp_path / "batch.json"
    data = _drc_manifest()
    entry = data["videos"][0]
    entry["source"]["audio_format_id"] = "251"
    entry["slug"] = "vid"
    entry["output"] = str(tmp_path / "vid.mp4")
    entry["thumbnail_output"] = str(tmp_path / "vid.jpg")
    entry["audio_probes"] = [{"source_at": 30.0, "duration": 1.0}]
    entry.update(entry_extra)
    manifest_path.write_text(json.dumps(data))
    Path(entry["output"]).write_bytes(b"mp4")

    from PIL import Image
    Image.new("RGB", (1920, 1080), (0, 0, 0)).save(entry["thumbnail_output"])

    monkeypatch.setattr(standalone.render, "find_ffmpeg", lambda *a, **k: ["ffmpeg"])
    monkeypatch.setattr(standalone, "_source_path", lambda slug: tmp_path / "src.mkv")
    (tmp_path / "src.mkv").write_bytes(b"mkv")
    durations = {str(tmp_path / "src.mkv"): 120.0, entry["output"]: 120.0}
    monkeypatch.setattr(standalone, "_source_duration",
                        lambda path, ffmpeg=None: durations[str(path)])
    monkeypatch.setattr(standalone, "_probe_streams", lambda *a, **k: [
        {"codec_type": "video", "codec_name": "h264"},
        {"codec_type": "audio", "codec_name": "aac"},
    ])
    monkeypatch.setattr(
        standalone, "_pcm",
        lambda path, at, dur, ffmpeg=None:
        [1, 2, 3, 4] if "src" in str(path) else [0, 1, 2, 3, 4, 0])
    frames = []
    monkeypatch.setattr(standalone, "_write_frame",
                        lambda path, at, out, ffmpeg=None:
                        frames.append(Path(out)) or Path(out))
    monkeypatch.setattr(standalone, "_unresolved_path",
                        lambda slug: tmp_path / f"{slug}-unresolved.json")
    return manifest_path, frames


def test_verify_reports_a_plate_the_build_could_not_draw(monkeypatch, tmp_path):
    """Only the sidecar knows an undrawn plate was dropped -- re-deriving the
    seats here would rediscover the mapping failures and miss that one."""
    manifest_path, frames = _verify_fixture(tmp_path, monkeypatch, {
        "overlays": [{"id": "undrawn", "kind": "caption",
                      "source_at": 10.0, "dur": 2.0}],
    })
    (tmp_path / "vid-unresolved.json").write_text(json.dumps({
        "slug": "vid",
        "unresolved": [{"id": "undrawn", "reason": "no plate was rendered"}],
    }))
    problems = standalone.verify(manifest_path, "vid")
    assert any("undrawn" in p and "unplaced" in p for p in problems)
    assert not [f for f in frames if f.name == "undrawn.png"], \
        "a review frame named for a plate that is not in the picture"


def test_verify_writes_a_review_frame_for_every_placed_plate(monkeypatch,
                                                             tmp_path):
    manifest_path, frames = _verify_fixture(tmp_path, monkeypatch, {
        "overlays": [{"id": "drawn", "kind": "caption",
                      "source_at": 10.0, "dur": 2.0}],
    })
    assert standalone.verify(manifest_path, "vid") == []
    assert [f.name for f in frames] == ["drawn.png"]


# --------------------------------------------------------------------------
# The committed batch manifest


BATCH = Path(__file__).resolve().parents[1] / \
    "stories" / "standalone" / "bluefin-video-batch.json"


def _batch_video(slug):
    manifest = json.loads(BATCH.read_text(encoding="utf-8"))
    return next(v for v in manifest["videos"] if v["slug"] == slug)


def _batch_overlay(slug, overlay_id):
    return next(o for o in _batch_video(slug)["overlays"]
                if o["id"] == overlay_id)


def test_final_trial_uses_one_normal_bazzite_plate_on_the_landing():
    video = _batch_video("bluefin-your-final-trial")
    john = _batch_overlay("bluefin-your-final-trial", "john-bazzite-landing")

    assert john == {
        "id": "john-bazzite-landing",
        "kind": "guardian",
        "source_at": 16.2,
        "dur": 2.2,
        "position": "left",
        "name": "John Bazzite",
        "variant": "bazzite",
        "copy_source": "owner_supplied",
        "why": (
            "The player lands at source 15.9-16.0, settles into the crouch "
            "at 16.2, rises through 16.4 and stands by 17.0. The wide "
            "plateau shot holds until the hard cut at 21.3, so the complete "
            "2.2s lower-third stays on the landed player."
        ),
    }
    assert not any(overlay["kind"] == "status"
                   for overlay in video["overlays"])


def test_the_top_right_hud_stays_inside_the_letterboxed_picture():
    """`plate.place` geometry only. The batch carries one real top-right
    seat -- the Saint-14 video's owner-authored "Activating CNCF Community"
    title card -- and the batch's letterboxed sources are 2.39:1 inside a
    16:9 file (measured picture rows 140-939 on the Final Trial source), so
    a card placed against the FRAME lands on the matte, which is the failure
    the picture probe exists to prevent. Pin the arithmetic: a top-right
    seat must stay inside the rect that source actually measures."""
    from PIL import Image

    from tools import plate

    picture = (0, 140, 1920, 800)          # measured on the Final Trial source
    card = Image.new("RGBA", (520, 190), (255, 0, 0, 255))
    frame = plate.place(card, position="top-right", picture=picture)
    box = frame.getbbox()
    px, py, pw, ph = picture
    assert box is not None
    assert box[0] >= px and box[1] >= py
    assert box[2] <= px + pw and box[3] <= py + ph


def test_every_committed_batch_seat_maps_and_collides_with_nothing():
    """No footage needed: the collision and takeover rules are arithmetic on
    the authored marks. A source long enough for every mark stands in for the
    real one, so this stays offline while still proving the seats coexist."""
    manifest = json.loads(BATCH.read_text(encoding="utf-8"))
    for video in manifest["videos"]:
        overlays = video["overlays"]
        duration = max(
            [o["source_at"] + o["dur"] for o in overlays]
            + [(video.get("takeover") or {}).get("source_at", 0.0)]
            + [0.0]
        ) + 1.0
        accepted, unresolved = standalone.mapped_overlays(video, duration)
        assert unresolved == [], f"{video['slug']}: {unresolved}"
        assert len(accepted) == len(overlays)


# The Blueberries Cayde-6 seat, per visual frame review (the segment records
# are coarser than the picture): Cayde is cleanly visible from source 33.533
# through 35.533, and the dissolve to the destruction wide begins at 35.567.
# BLUEBERRIES_CAYDE_VISIBLE is measured from delivered/source frame
# inspection at 59.94fps because the committed segment is coarser; a future
# tag correction to those segments must update this pin.
# The standalone renderer hard-overlays the static plate only from source_at
# through source_at+dur -- plate.py's lead-in/tail-out envelope does not apply
# here -- so the overlay interval itself must sit inside those bounds. Seated
# at 33.55 for 1.95s, 33.55-35.50 fits; this is an explicit short-hold
# exception because no 2.2s continuous Cayde shot exists near the owner's
# requested ~30s placement.
BLUEBERRIES_CAYDE_VISIBLE = (33.533, 35.533)
CASTROJO_PLATE = {
    "id": "jorge-cayde",
    "kind": "guardian",
    "source_at": 33.55,
    "dur": 1.95,
    "position": "left",
    "copy_source": "casting",
    "why": (
        "Visual frame review establishes Cayde-6 cleanly visible from "
        "source 33.533 through 35.533, with the dissolve to the destruction "
        "wide beginning at 35.567; the standalone renderer hard-overlays "
        "the static plate only from source_at through source_at+dur, with "
        "no lead-in/tail-out envelope. The segment records "
        "(seg_..._0033-0037, 'Cayde-6 reaches toward a red figure', "
        "casting person castrojo) span 33.300-37.767 but are coarser than "
        "the picture. Seated at 33.55 for 1.95s, the whole overlay "
        "interval 33.55-35.50 stays inside the measured visible bounds, "
        "honoring the owner's 'around the first ~30 seconds' placement "
        "without crediting Jorge over the destruction wide. This is an "
        "explicit short-hold exception to the 2.2s minimum because no "
        "2.2s continuous Cayde shot exists near 30s; the complete "
        "established four-row identity is kept."
    ),
    "label": "TRUSTEE // GUARDIAN",
    "class": "Harbinger Titan",
    "name": "Jorge Castro",
    "title": "Upender of Antipatterns | The First Disciple",
    "trustee": True,
}


def test_the_blueberries_jorge_plate_is_the_established_identity():
    """The full plate reproduces the `castrojo` binding in vocab/casting.yaml
    verbatim, so its copy_source is `casting` -- the words come from the
    reviewed durable record, not from this manifest. Compare the complete
    literal entry so extra as well as missing fields fail the pin."""
    plate = _batch_overlay("bluefin-and-the-blueberries", "jorge-cayde")
    assert plate == CASTROJO_PLATE
    assert _batch_video("bluefin-and-the-blueberries")["takeover"] == {
        "source_at": 91.7,
    }


def test_the_blueberries_overlay_interval_stays_on_visible_cayde():
    """The standalone renderer overlays the static plate from source_at
    through source_at+dur and nothing else -- there is no lead-in/tail-out
    envelope on this path -- so that interval itself must sit inside the
    measured visual bounds: Cayde cleanly visible 33.533-35.533, dissolve
    beginning 35.567. 33.55 through 35.50 fits with margin on both ends.
    """
    seat = _batch_overlay("bluefin-and-the-blueberries", "jorge-cayde")
    visible_from = seat["source_at"]
    visible_to = seat["source_at"] + seat["dur"]

    assert visible_from >= BLUEBERRIES_CAYDE_VISIBLE[0] - 1e-6
    assert visible_to <= BLUEBERRIES_CAYDE_VISIBLE[1] + 1e-6


def test_the_takeover_starts_before_the_new_legends_title():
    """The source's `NEW LEGENDS WILL RISE` title begins at source 91.767
    (seg_..._0091-0096, "'NEW LEGENDS WILL RISE' text over a crowd
    silhouette"). The takeover at 91.7 -- output 83.7 after the 8s excision --
    starts the approved CTA before that publisher title, its legal-card
    flash, and the hard transition."""
    video = _batch_video("bluefin-and-the-blueberries")
    assert video["takeover"]["source_at"] < 91.767
    assert video["cuts"][0]["end_sec"] - video["cuts"][0]["start_sec"] == 8.0
    assert standalone.source_to_output(
        video["takeover"]["source_at"], video["cuts"]) == pytest.approx(83.7)


def test_a_batch_plate_contradicting_a_binding_is_reported_not_shipped():
    """The standalone path never passes through `plan`, so mapped_overlays
    holds hand-authored copy to vocab/casting.yaml (#111's rule: the vocab
    wins). A contradiction is degraded to `unresolved` -- recorded, never
    shipped -- like any other seat fault."""
    video = {"cuts": [], "overlays": [{
        "id": "wrong-copy",
        "source_at": 10.0,
        "dur": 2.2,
        "position": "left",
        "name": "Jorge Castro",
        "label": "MAINTAINER // GUARDIAN",
        "class": "Harbringer Hunter",
    }]}
    accepted, unresolved = standalone.mapped_overlays(video, 120.0)
    assert accepted == []
    assert unresolved[0]["id"] == "wrong-copy"
    assert "vocab wins" in unresolved[0]["reason"]


def test_a_name_only_jorge_overlay_does_not_contradict_the_binding():
    """Omitted fields are not contradictions: the intentional name-only
    Jorge overlays (Care for a Drink, Final Trial) credit nobody with copy
    the binding does not say, so they pass the check."""
    video = {"cuts": [], "overlays": [{
        "id": "name-only",
        "source_at": 10.0,
        "dur": 2.2,
        "position": "left",
        "name": "Jorge Castro",
    }]}
    accepted, unresolved = standalone.mapped_overlays(video, 120.0)
    assert unresolved == []
    assert [o["id"] for o in accepted] == ["name-only"]


def test_the_reseated_thumbnail_marks_keep_the_title_off_the_subject():
    """Both marks were reseated after review found the title lockup crossing
    the subject's head: Final Trial's 68.9 ran the title over Cayde, and Saint
    14's 70.5 ran it over the Helm of Saint-14.

    The replacements were picked by composing the real card and checking the
    measured ink band against the picture, so pin them -- a silent revert puts
    type back across a face, and record the evidence beside the number.
    """
    marks = {
        "bluefin-your-final-trial": 87.6,
        "bluefin-and-saint-14": 71.95,
    }
    for slug, expected in marks.items():
        thumbnail = _batch_video(slug)["thumbnail"]
        assert thumbnail["source_at"] == expected, slug
        assert thumbnail.get("why"), f"{slug}: the reseat lost its evidence"


def test_the_saint_14_thumbnail_mark_stays_off_the_burned_in_publisher_card():
    """The Saint-14 source cuts from the Perfect Paradox shot to a burned-in
    `FIGHT THROUGH TIME` title: 72.000 is still the shot, 72.250 is already
    the card. A mark at or past the cut would put Bungie's own copy under the
    Bluefin lockup."""
    assert _batch_video("bluefin-and-saint-14")["thumbnail"]["source_at"] < 72.1


def test_no_committed_batch_overlay_is_unresolved():
    """Rule 2 reports unmatched seats rather than dropping them silently, so
    an empty `unresolved` is the shipping condition for this batch."""
    manifest = json.loads(BATCH.read_text(encoding="utf-8"))
    for video in manifest["videos"]:
        duration = max(
            [o["source_at"] + o["dur"] for o in video["overlays"]]
            + [(video.get("takeover") or {}).get("source_at", 0.0)]
        ) + 1.0
        _, unresolved = standalone.mapped_overlays(video, duration)
        assert unresolved == [], f"{video['slug']}: {unresolved}"


# --------------------------------------------------------------------------
# The Saint-14 quality pass
#
# Reviewed owner decisions, applied verbatim: three real Bluefin contributor
# plates from the deterministic GitHub-derived 2026-08 rotation (cast leads
# excluded), source-time excisions for the six burned-in Destiny publisher
# cards, the CTA takeover moved ahead of the final Destiny/Season of Dawn
# dissolve, and the audio probe moved out of the cut it fell inside. The
# opening ESRB head card and the Bungie logo are explicitly KEPT.

SAINT_SLUG = "bluefin-and-saint-14"

# Burned-in publisher copy excised from the source, in source time. The
# Bungie logo (6.039-8.275) and the ESRB head card (0.000-2.002) are not in
# this list on purpose: the owner wants them kept.
SAINT_CARD_CUTS = [
    (72.201, 74.364),    # FIGHT THROUGH TIME
    (77.405, 78.572),    # SAVE A LEGEND
    (80.468, 82.707),    # MASTER / THE SUNDIAL / NEW 6 PLAYER ACTIVITY
    (92.351, 93.925),    # NEW / EXOTIC QUESTS
    (97.963, 99.617),    # PvP ELIMINATION MODE / RUSTED LANDS RETURNS
    (114.604, 116.749),  # TIME TO CONQUER THE / SEASON OF DAWN
]
SAINT_CUT_TOTAL = sum(end - start for start, end in SAINT_CARD_CUTS)

SAINT_ESRB_HEAD = (0.000, 2.002)
SAINT_BUNGIE_LOGO = (6.039, 8.275)

SAINT_CONTRIBUTOR_PLATES = [
    {
        "id": "ensemble_hanthor",
        "kind": "guardian",
        "source_at": 35.150,
        "dur": 2.000,
        "position": "left",
        "copy_source": "casting",
        "why": (
            "Saint Transition Reviewer frame evidence: the hold opens on "
            "the fireteam trio walking and ends inside the gold Titan "
            "close-up, every body in frame an anonymous ensemble Guardian. "
            "No 2.2s continuous window exists anywhere in the 35-42s "
            "montage, so 2.000s is a narrow standalone short-hold "
            "exception, the same class as the Blueberries Cayde seat. "
            "hanthor is the first name in the deterministic GitHub-derived "
            "2026-08 rotation with the cast leads excluded, and a "
            "projectbluefin org member, so the eyebrow reads MAINTAINER // "
            "GUARDIAN; name and title reproduce the ensemble copy block in "
            "vocab/casting.yaml."
        ),
        "label": "MAINTAINER // GUARDIAN",
        "name": "hanthor",
        "title": "Bluefin Blueberry",
    },
    {
        "id": "ensemble_joshyorko",
        "kind": "guardian",
        "source_at": 37.250,
        "dur": 1.900,
        "position": "left",
        "copy_source": "casting",
        "why": (
            "Saint Transition Reviewer frame evidence: the whole hold "
            "stays inside the sword-Hunter close-up, an anonymous ensemble "
            "body. No 2.2s continuous window exists anywhere in the 35-42s "
            "montage, so 1.900s is a narrow standalone short-hold "
            "exception, the same class as the Blueberries Cayde seat. "
            "joshyorko is the second name in the deterministic "
            "GitHub-derived 2026-08 rotation with the cast leads excluded; "
            "label, name and title reproduce the ensemble copy block in "
            "vocab/casting.yaml."
        ),
        "label": "CONTRIBUTOR // GUARDIAN",
        "name": "joshyorko",
        "title": "Bluefin Blueberry",
    },
    {
        "id": "ensemble_rapenne-s",
        "kind": "guardian",
        "source_at": 39.260,
        "dur": 2.000,
        "position": "left",
        "copy_source": "casting",
        "why": (
            "Saint Transition Reviewer frame evidence: the whole hold "
            "stays inside the continuous walking-Titan world-morph, an "
            "anonymous ensemble body. No 2.2s continuous window exists "
            "anywhere in the 35-42s montage, so 2.000s is a narrow "
            "standalone short-hold exception, the same class as the "
            "Blueberries Cayde seat. rapenne-s is the third name in the "
            "deterministic GitHub-derived 2026-08 rotation with the cast "
            "leads excluded; label, name and title reproduce the ensemble "
            "copy block in vocab/casting.yaml."
        ),
        "label": "CONTRIBUTOR // GUARDIAN",
        "name": "rapenne-s",
        "title": "Bluefin Blueberry",
    },
]


def test_the_saint_14_contributor_plates_are_the_reviewed_rotation_records():
    """Three real Bluefin contributors at ~0:35, from the deterministic
    GitHub-derived 2026-08 rotation with the cast leads excluded. Each pin
    is the COMPLETE literal record, so an extra identity row (a class, an
    avatar, a trustee flag nobody authored) fails the same way a missing
    one does."""
    for expected in SAINT_CONTRIBUTOR_PLATES:
        assert _batch_overlay(SAINT_SLUG, expected["id"]) == expected


def test_the_saint_14_cuts_remove_exactly_the_six_publisher_cards():
    """The six source-time excisions, pinned to the millisecond: each one
    spans a burned-in Destiny publisher card and nothing else, with the
    boundary reseated inside the same 29.97fps frame window so the PCM
    join is click-safe (the splice review measured ratios 2.4-8.4 against
    the 1.8 blocker on the first-pass boundaries)."""
    cuts = _batch_video(SAINT_SLUG)["cuts"]
    assert [(c["start_sec"], c["end_sec"]) for c in cuts] == SAINT_CARD_CUTS
    assert all(cut.get("note") for cut in cuts)


def test_the_saint_14_cuts_keep_the_esrb_head_and_the_bungie_logo():
    """The owner explicitly kept the opening ESRB head card (0.000-2.002)
    and the Bungie logo (6.039-8.275). No authored cut may intersect either
    span."""
    cuts = _batch_video(SAINT_SLUG)["cuts"]
    for span in (SAINT_ESRB_HEAD, SAINT_BUNGIE_LOGO):
        for cut in cuts:
            assert cut["end_sec"] <= span[0] or cut["start_sec"] >= span[1], \
                f"cut {cut} removes kept opening span {span}"


def test_the_saint_14_takeover_starts_before_the_final_dissolve():
    """The CTA moves from 123.0 to 121.800 so the approved takeover picture
    is up before the final Destiny/Season of Dawn dissolve. After the six
    excisions (10.942s removed) that lands at output 110.858."""
    video = _batch_video(SAINT_SLUG)
    assert video["takeover"] == {"source_at": 121.8}
    assert SAINT_CUT_TOTAL == pytest.approx(10.942)
    assert standalone.source_to_output(
        121.8, video["cuts"]) == pytest.approx(110.858)


def test_the_saint_14_audio_probes_steer_clear_of_the_cuts():
    """The 115.0 probe fell inside the TIME TO CONQUER THE / SEASON OF DAWN
    excision (114.604-116.749), where it would compare the delivered audio
    against removed source; it moves to 113.0. The 125.0 probe stands."""
    video = _batch_video(SAINT_SLUG)
    assert video["audio_probes"] == [
        {"source_at": 113.0, "duration": 1.0},
        {"source_at": 125.0, "duration": 1.0},
    ]
    with pytest.raises(ValueError, match="inside removed source range"):
        standalone.source_to_output(115.0, video["cuts"])
    for probe in video["audio_probes"]:
        standalone.source_to_output(probe["source_at"], video["cuts"])


def test_the_saint_14_seats_map_through_the_cuts_without_collision():
    """Arithmetic only, no footage: every plate sits before the first cut,
    so its output seat equals its source seat; the activation title lands at
    output 97.203; and nothing collides, overruns, or falls under the
    takeover."""
    video = _batch_video(SAINT_SLUG)
    duration = max(
        [o["source_at"] + o["dur"] for o in video["overlays"]]
        + [video["takeover"]["source_at"]]
    ) + 10.0
    accepted, unresolved = standalone.mapped_overlays(video, duration)
    assert unresolved == []
    assert len(accepted) == len(video["overlays"]) == 4
    at = {o["id"]: o["at"] for o in accepted}
    for expected in SAINT_CONTRIBUTOR_PLATES:
        assert at[expected["id"]] == pytest.approx(expected["source_at"])
    assert at["activating-cncf-community"] == pytest.approx(97.203)
    assert standalone.expected_duration(video, 130.0) == \
        pytest.approx(130.0 - 10.942)


def test_aligned_correlation_finds_the_true_seat_not_a_period_away():
    """Bright, periodic content defeats a coarse-then-fine lag search: the
    Saint-14 mix at source 113.0 scored 0.72 at a seat one signal period
    from the true one, whose 0.9999 peak lay 11 samples from the best
    coarse point -- outside the +/-7 fine scan. This reproduces that shape:
    a 3 kHz tone over light noise autocorrelates at ~0.7 three samples off
    the peak, so the search must score every lag."""
    import math
    import random

    rate = standalone.PROBE_RATE
    span = int(0.1 * rate)  # the delivered window: reference plus the pads
    rng = random.Random(14)
    signal = [math.sin(2 * math.pi * 3000 * i / rate)
              + 0.35 * rng.uniform(-1, 1)
              for i in range(rate + span)]
    true_lag = 393  # deliberately not a multiple of the coarse step
    reference = signal[true_lag:true_lag + rate]
    score, lag = standalone.aligned_correlation(reference, signal)
    assert lag == pytest.approx((true_lag - span // 2) / rate, abs=1 / rate)
    assert score > standalone.AUDIO_CORRELATION_FLOOR


@pytest.mark.parametrize("start,end", SAINT_CARD_CUTS)
def test_splice_step_ratio_separates_a_clean_join_from_the_reviewed_defect(
        start, end):
    """Offline guard for the Saint-14 audio splice defect. The first-pass
    boundaries joined mid-oscillation and the reviewer measured step/p99
    slew ratios of 2.4-8.4 -- over the 1.8 blocker -- at all six excisions;
    the reseated boundaries all read <= 1.0. This pins the *measurement*
    against each pinned excision's span: over exactly that span, a
    phase-continuous join must pass the target and the same join carried
    half a cycle out -- the defect class -- must trip the blocker."""
    import math

    rate = 48000
    removed = end - start
    cycles = round(removed * 400)  # ~400 Hz, an integer count in the span
    frequency = cycles / removed
    # Seat the join at a peak, where a half-cycle slip is the loudest click.
    a = int(round(rate / (4 * frequency)))
    b = a + int(round(removed * rate))
    signal = [0.5 * math.sin(2 * math.pi * frequency * i / rate)
              for i in range(b + rate // 10)]
    before, after = signal[:a], signal[b:]
    assert standalone.splice_step_ratio(before, after) <= \
        standalone.SPLICE_STEP_TARGET
    half_cycle = int(round(rate / (2 * frequency)))
    clicked = standalone.splice_step_ratio(before, signal[b + half_cycle:])
    assert clicked > standalone.SPLICE_STEP_BLOCKER


def test_splice_step_ratio_edge_cases():
    """Digital silence slews nowhere: a silent join into silence is clean,
    any step out of it is an infinite ratio, and a one-sided window is not
    a join at all."""
    import math

    assert standalone.splice_step_ratio([0.0, 0.0], [0.0, 0.0]) == 0.0
    assert standalone.splice_step_ratio([0.0, 0.0], [0.5, 0.5]) == \
        pytest.approx(math.inf)
    with pytest.raises(ValueError, match="at least two samples"):
        standalone.splice_step_ratio([0.0], [0.0, 0.0])


def test_silence_pad_is_the_frame_quantization_remainder():
    """The pad is how much longer a kept segment's frame-quantized video
    runs past its sample-exact audio: zero when a boundary sits exactly on
    a frame, a whole frame minus epsilon just past one, and it can go
    frame -- the audio then covers the video and concat inserts nothing."""
    frame = standalone.FRAME_DURATION
    assert standalone.silence_pad(frame, 0.0) == pytest.approx(0.0)
    assert standalone.silence_pad(2 * frame + 0.001, 0.0) == \
        pytest.approx(frame - 0.001)
    # Segment start 5 ms below its first frame: 5 ms of cover credit.
    assert standalone.silence_pad(2 * frame, frame - 0.005) == \
        pytest.approx(-0.005)


def test_the_saint_14_joins_survive_concat_frame_quantization():
    """Offline guard for the delivered splice defect one layer down from the
    boundary pins. The concat filter pads a kept segment's audio with
    silence whenever its frame-quantized video runs longer than its
    sample-exact audio, so a join that reads click-safe on the source PCM
    can still ship as content -> silence -> content: the first reseated
    render measured step/p99 slew of 3.5 and 3.2 delivered at joins whose
    authored pairs read 0.37 and 0.31. Every Saint join must either ship
    its authored sample pair (pad <= 0) or pad under a frame -- cuts 1 and
    3 are the padded ones, seated on quiet edges (measured 0.81 and 0.94
    delivered against the 1.0 target and 1.8 blocker)."""
    video = _batch_video(SAINT_SLUG)
    cuts = sorted(video["cuts"], key=lambda cut: cut["start_sec"])
    padded = []
    prev_end = 0.0
    for cut in cuts:
        pad = standalone.silence_pad(cut["start_sec"], prev_end)
        if pad > 0:
            padded.append((cut["start_sec"], pad))
            assert pad < standalone.FRAME_DURATION, \
                f"join at {cut['start_sec']} pads a whole frame"
        prev_end = cut["end_sec"]
    assert [start for start, _ in padded] == [72.201, 80.468]
