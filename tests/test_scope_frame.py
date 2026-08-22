"""The authored scope frame, which stopped being a constant.

Both perfume builders were written against a source that arrived at exactly
the delivery width, so they padded it into 16:9 and scaled nothing. That made
1920x804 look like a property of the acts, and both hardcoded it as one.

It was a property of the FILE. When the 4K re-upload replaced it the builds
died on `pad` -- you cannot pad a frame down -- and the fix was to resolve the
scope frame from the source instead of assuming it, in ONE place both
builders share. These tests hold that distinction: the seat is authored and
must never move, the resampling is whatever the source of the day requires.

Offline: ffprobe is faked, no footage is read.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import conform  # noqa: E402
from scripts import build_prologue  # noqa: E402
from scripts import build_interludes  # noqa: E402


def fake_probe(monkeypatch, width, height, pix_fmt="yuv420p"):
    """ffprobe's answer, without ffprobe -- or an ffmpeg to find it beside.

    The suite is offline and CI has no ffmpeg at all, so the resolver is faked
    too. That is not test scaffolding around a wart: scope_filter resolves
    ffmpeg lazily and only when it actually probes, precisely so asking a
    question about a file does not require an encoder.
    """
    monkeypatch.setattr(conform, "_find_ffmpeg", lambda: ["ffmpeg"])
    monkeypatch.setattr(conform, "ffprobe_for", lambda ffmpeg: ["ffprobe"])
    monkeypatch.setattr(
        conform, "probe_video",
        lambda path, ffprobe: {"width": width, "height": height,
                               "pix_fmt": pix_fmt})


def test_a_source_at_the_authored_scope_is_not_resampled(monkeypatch):
    # The 1080p source's behaviour, preserved exactly: no scale filter at all.
    # A downscale that is a no-op is still a generation, so it must be absent
    # rather than merely harmless.
    fake_probe(monkeypatch, 1920, 804)
    scope, note = build_prologue.source_scope(Path("perfume.mkv"))
    assert scope == ""
    assert "no resampling" in note
    assert "scale=" not in build_prologue.filtergraph(scope)


def test_a_larger_source_is_downscaled_to_the_authored_scope(monkeypatch):
    # The 4K re-upload: 3840x1608 is the same 2.388:1 scope at twice the
    # linear size, so it downscales cleanly to the seat the act was cut for.
    fake_probe(monkeypatch, 3840, 1608, "yuv420p10le")
    scope, note = build_prologue.source_scope(Path("perfume.mkv"))
    assert scope == "scale=1920:804:flags=lanczos,"
    assert "3840x1608 -> 1920x804" in note
    assert "yuv420p10le" in note


def test_the_downscale_runs_before_the_pad(monkeypatch):
    # Order is the whole bug: padding first asks pad to shrink a frame, which
    # is "Padded dimensions cannot be smaller than input dimensions".
    fake_probe(monkeypatch, 3840, 1608)
    scope, _ = build_prologue.source_scope(Path("perfume.mkv"))
    graph = build_prologue.filtergraph(scope)
    assert "scale=1920:804:flags=lanczos,pad=1920:1080:0:138" in graph


@pytest.mark.parametrize("scope", ["", "scale=1920:804:flags=lanczos,"])
def test_the_authored_seat_is_138px_whatever_the_source(scope):
    # The title cards and the bookline are rendered against this seat, so it
    # is authored geometry. A source swap may change what is resampled; it may
    # never move the picture inside the frame.
    assert "pad=1920:1080:0:138:color=black" in build_prologue.filtergraph(scope)


def test_the_seat_is_derived_from_the_scope_constant_not_retyped():
    # Guards the regression directly: an agent "fixing" a future source by
    # editing one of these two numbers and not the other silently shifts the
    # picture off the seat the cards were composed against.
    assert (build_prologue.H - build_prologue.SCOPE_H) // 2 == 138
    assert f"(H - SCOPE_H) // 2" in (
        REPO_ROOT / "scripts" / "build_prologue.py").read_text()


def test_a_source_of_the_wrong_shape_stops_rather_than_stretching(monkeypatch):
    # 16:9 footage is not this act's scope. Scaling it to 1920x804 would
    # squash the picture -- moving every frame -- so it is refused.
    fake_probe(monkeypatch, 1920, 1080)
    with pytest.raises(SystemExit) as exc:
        build_prologue.source_scope(Path("wrong.mkv"))
    assert "stretch" in str(exc.value)


def test_a_smaller_source_is_reported_rather_than_silently_upscaled(
        monkeypatch, capsys):
    # Degrade, never block: an upscale still builds a video, but it adds no
    # detail and the operator should know a better source is wanted.
    fake_probe(monkeypatch, 1280, 536)
    scope, _ = build_prologue.source_scope(Path("small.mkv"))
    assert scope == "scale=1920:804:flags=lanczos,"
    assert "SMALLER" in capsys.readouterr().err


# --- the two builders that cut this same source must not drift -------------

def test_both_perfume_builders_resolve_the_scope_the_same_way(monkeypatch):
    # build_prologue and build_interludes broke on the 4K swap for ONE reason.
    # A second copy of the fix is a second thing to get wrong next time, so
    # they share conform.scope_filter and this proves they still do.
    fake_probe(monkeypatch, 3840, 1608)
    build_interludes._SCOPE_CACHE.clear()
    monkeypatch.setattr(Path, "exists", lambda self: True)
    spec = {"source": "media/perfume.mkv", "source_height": 804}
    assert (build_interludes.scope_for(spec)
            == build_prologue.source_scope(Path("perfume.mkv"))[0]
            == "scale=1920:804:flags=lanczos,")
    build_interludes._SCOPE_CACHE.clear()


def test_the_interlude_scope_is_resolved_inside_the_shared_chain(monkeypatch):
    # scripts/build_ending_overlays.py builds its derivative FROM video_chain
    # so the two can never drift. Resolving the scale in each caller instead
    # would be exactly that drift -- the overlaid movement seated differently
    # from the clean one -- so it is resolved inside the shared chain.
    fake_probe(monkeypatch, 3840, 1608)
    build_interludes._SCOPE_CACHE.clear()
    monkeypatch.setattr(Path, "exists", lambda self: True)
    spec = {"source": "media/perfume.mkv", "source_height": 804,
            "movements": []}
    chain = build_interludes.video_chain(
        spec, {"duration": 10.0}, out_label="base")
    assert chain.startswith(
        "[0:v]scale=1920:804:flags=lanczos,pad=1920:1080:0:138:color=black,")
    build_interludes._SCOPE_CACHE.clear()


def test_the_chain_stays_constructible_without_footage(monkeypatch):
    # Footage is never committed, so the graph must still be readable — and
    # the tests must still run — on a checkout with no media/ at all.
    build_interludes._SCOPE_CACHE.clear()
    monkeypatch.setattr(Path, "exists", lambda self: False)
    spec = {"source": "media/gone.mkv", "source_height": 804}
    assert build_interludes.scope_for(spec) == ""
    build_interludes._SCOPE_CACHE.clear()


def test_a_mismatched_source_raises_rather_than_exits_in_the_library():
    # conform is a library: it raises a typed error and lets each builder
    # decide. build_prologue turns it into a clean exit; a caller that wanted
    # to try another rung could catch it instead.
    assert issubclass(conform.ScopeMismatch, RuntimeError)


def test_no_builder_resolves_ffmpeg_merely_to_ask_about_a_file():
    # These tests failed on CI first time out: both callers passed
    # ffmpeg=find_ffmpeg(), evaluated eagerly, and the runner has no ffmpeg.
    # Resolution belongs inside scope_filter, where it happens only if a probe
    # actually runs -- so the guard is that the callers pass nothing.
    for script in ("build_prologue.py", "build_interludes.py"):
        text = (REPO_ROOT / "scripts" / script).read_text()
        call = text.split("conform.scope_filter", 1)[1].split(")", 1)[0]
        assert "find_ffmpeg" not in call, (
            f"{script} resolves ffmpeg to call scope_filter; let conform do "
            f"it lazily or the offline suite cannot reach this path")
