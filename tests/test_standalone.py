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


def test_the_bazzite_hud_is_seated_in_the_pictures_top_right():
    """The approved player-card direction fixes this HUD top-RIGHT.

    `position: "status"` is the site's top-LEFT nameplate rail
    (`.wc-intro-nameplate { top: 3rem; left: 3rem }`), and the manifest shipped
    it once by copying a brief that had quietly lost the corner. Both seats are
    measured against the picture, so this is purely which corner the design
    approved -- and the design is the authority, not the brief.
    """
    hud = _batch_overlay("bluefin-your-final-trial", "john-bazzite-expert")
    assert hud["position"] == "top-right"
    # Everything else about the card is unchanged: the chrome row exemption is
    # keyed on `kind`, and the purple/tile crest come from `variant`.
    assert hud["kind"] == "status"
    assert hud["variant"] == "bazzite"
    assert hud["label"] == "John Bazzite"
    assert hud["detail"] == "FIRETEAM // EXPERT"
    assert (hud["source_at"], hud["dur"]) == (3.35, 106.35)


def test_the_top_right_hud_stays_inside_the_letterboxed_picture():
    """Final Trial is 2.39:1 inside a 16:9 file: measured picture rows
    140-939. A HUD measured against the FRAME lands on the matte, which is the
    failure the picture probe exists to prevent -- so assert the seat the
    manifest asks for is inside the rect that source actually measures."""
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


# The Blueberries Cayde-6 hero shot, measured on the source at 0.3s steps:
# 68.800/69.100 are the preceding fog two-shot, 69.400 through 72.100 are all
# Cayde, and 72.400 has cut to the crowd. Shot bounds are therefore 69.20 and
# 72.13. The frame after the ORIGINAL 14.05-15.75 seat's shot -- 16.400 -- is
# Zavala addressing the crowd, with no Cayde anywhere in it.
BLUEBERRIES_CAYDE_SHOT = (69.20, 72.13)


def test_the_blueberries_jorge_plate_holds_only_on_evidenced_cayde():
    """A `Jorge Castro` plate credits a real person, so every frame it is up
    for has to support the credit -- AGENTS.md, "Casting names real people".

    The manifest first seated it at 14.4, Cayde's FIRST clear appearance. That
    shot ends at 15.75 and the next one is Zavala-only, so the 2.2s hold spent
    0.85s crediting Jorge over footage Cayde is not in. First appearance is a
    preference; a window that supports the whole readable hold is the rule,
    and this pins the seat that satisfies it.
    """
    plate = _batch_overlay("bluefin-and-the-blueberries", "jorge-cayde")
    start = plate["source_at"]
    end = start + plate["dur"]
    shot_in, shot_out = BLUEBERRIES_CAYDE_SHOT

    assert (start, plate["dur"]) == (69.6, 2.2)
    assert shot_in <= start, "the hold starts before the evidenced shot does"
    assert end <= shot_out, "the hold outlives the evidenced shot"
    assert plate["name"] == "Jorge Castro"
    assert plate["kind"] == "guardian"
    # Nothing may quietly return the plate to the old first-appearance seat.
    assert end <= 16.4 or start >= 16.4


def test_the_blueberries_plate_clears_plate_pys_lead_in_and_tail_out():
    """`tools/standalone.py` hard-cuts this overlay on `between(t,61.6,63.8)`,
    but `tools/plate.py`'s envelope (`LEAD_IN` before, `TAIL_OUT` after) is
    the wider span the same seat would be visible for under the film
    renderer. Requiring the evidenced shot to cover that wider span keeps the
    seat honest under either path, and leaves margin for a frame-boundary
    rounding at the edges."""
    from tools import plate as plate_module

    seat = _batch_overlay("bluefin-and-the-blueberries", "jorge-cayde")
    shot_in, shot_out = BLUEBERRIES_CAYDE_SHOT
    visible_from = seat["source_at"] - plate_module.LEAD_IN
    visible_to = seat["source_at"] + seat["dur"] + plate_module.TAIL_OUT

    assert visible_from >= shot_in - 1e-6, visible_from
    assert visible_to <= shot_out + 1e-6, visible_to


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
