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
from scripts import build_trailer1  # noqa: E402


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
    assert "scale=" not in build_prologue.filtergraph(scope=scope)


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
    graph = build_prologue.filtergraph(scope=scope)
    assert "scale=1920:804:flags=lanczos,pad=1920:1080:0:138" in graph


@pytest.mark.parametrize("scope", ["", "scale=1920:804:flags=lanczos,"])
def test_the_authored_seat_is_138px_whatever_the_source(scope):
    # The title cards and the bookline are rendered against this seat, so it
    # is authored geometry. A source swap may change what is resampled; it may
    # never move the picture inside the frame.
    assert "pad=1920:1080:0:138:color=black" in build_prologue.filtergraph(scope=scope)


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


PERFUME_ID = "yt_nightwish_perfume_of_the_timeless"


def perfume_builders():
    """Every script that cuts the perfume source, found rather than listed.

    This is deliberately DISCOVERED. The first version of this guard carried a
    hand-written list of two builders, and scripts/build_trailer1.py -- a third
    builder with the identical unscaled `pad`, which would have hard-failed
    against the replacement source -- was simply not on it. A list only guards
    the files somebody remembered; the failure mode is the file they did not.
    """
    found = sorted(p for p in (REPO_ROOT / "scripts").glob("build_*.py")
                   if PERFUME_ID in p.read_text())
    assert found, "no perfume builders found -- has the source id changed?"
    return found


def test_every_perfume_builder_resolves_the_scope_from_its_source():
    # The seat (1920x804) is authored and must never move. The SOURCE's own
    # size is a property of a file, and that file has already been replaced
    # once -- by a 3840x1608 master that `pad` cannot shrink. A builder that
    # pads without first resolving the scope dies the day a better source
    # arrives, which is the whole bug this module exists for.
    for path in perfume_builders():
        text = path.read_text()
        assert "conform.scope_filter" in text, (
            f"{path.name} cuts the perfume source but never calls "
            f"conform.scope_filter, so it assumes the source's shape. Seat it "
            f"with scope_filter the way build_prologue.py does.")


def test_no_perfume_builder_pads_footage_without_scaling_it_first(monkeypatch):
    # `pad` cannot shrink a frame: a larger source fails outright with
    # "Padded dimensions cannot be smaller than input dimensions". So the
    # ASSEMBLED chain -- not the source line, which may hold `pad` in a
    # constant spliced in later -- must put the scale first.
    #
    # This is checked behaviourally for every builder that has a chain we can
    # construct offline. The discovery test above is what catches a builder
    # that skips scope_filter entirely.
    fake_probe(monkeypatch, 3840, 1608)

    scope, _ = build_prologue.source_scope(Path("perfume.mkv"))
    for graph in (build_prologue.filtergraph(scope=scope),
                  build_trailer1.filtergraph(build_trailer1.load(), 1.0, scope=scope)):
        assert "scale=" in graph, "the 4K source is not resampled at all"
        assert graph.index("scale=") < graph.index("pad="), (
            "pad runs before scale, so ffmpeg is asked to shrink a frame")


def test_no_builder_resolves_ffmpeg_merely_to_ask_about_a_file():
    # These tests failed on CI first time out: the callers passed
    # ffmpeg=find_ffmpeg(), evaluated eagerly, and the runner has no ffmpeg.
    # Resolution belongs inside scope_filter, where it happens only if a probe
    # actually runs -- so the guard is that the callers pass nothing.
    for path in perfume_builders() + [REPO_ROOT / "scripts" / "build_interludes.py"]:
        text = path.read_text()
        if "conform.scope_filter" not in text:
            continue
        call = text.split("conform.scope_filter", 1)[1].split(")", 1)[0]
        assert "find_ffmpeg" not in call, (
            f"{path.name} resolves ffmpeg to call scope_filter; let conform do "
            f"it lazily or the offline suite cannot reach this path")


def test_no_perfume_call_site_can_omit_the_scope_filter():
    """Every call that BUILDS a chain must hand it the scope filter.

    Written from the failure it catches. `build_trailer1` threaded `scope` into
    the FIRST render and then rebuilt the same command for the loudness
    correction without it -- `command(manifest, day, night, gain)` -- so the
    rerun fell back to `scope=""` and emitted a bare `pad=1920:1080:0:138`
    against the 3840x1608 master. The first pass encoded fine and the retry died
    on "Padded dimensions cannot be smaller than input dimensions", which is the
    worst shape for this bug: it only appears when the audio happens to be hot
    enough to need a second pass.

    This asserts the CALL SITES, not the signatures. An earlier version of this
    guard flagged any defaulted `scope` parameter, which condemned
    `build_prologue` for a default no call site actually relies on -- it has no
    rerun path at all, it trims the finished master with `peaks.trim_master_peak`.
    A default is only a bug when somebody omits it, so that is what is measured,
    for the same reason the sibling test checks the built chain rather than the
    source line: what reaches ffmpeg is the only thing that can be wrong.
    """
    import ast

    builders = perfume_builders()
    assert builders, "discovery found no perfume builders; the guard is vacuous"

    checked = 0
    for path in builders:
        tree = ast.parse(path.read_text())
        # Where does `scope` sit in each chain-building signature?
        position = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in {"filtergraph", "command"}:
                names = [a.arg for a in node.args.args]
                if "scope" in names:
                    position[node.name] = names.index("scope")   # positional
                elif any(a.arg == "scope" for a in node.args.kwonlyargs):
                    position[node.name] = "kwonly"               # must be named
                else:
                    position[node.name] = None                   # takes no scope

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name not in position:
                continue
            idx = position[name]
            # A builder that takes no `scope` at all splices it in elsewhere --
            # `build_interludes` holds it in a constant that `video_chain`
            # inserts after the scope. There is no parameter to omit, and the
            # sibling scale-before-pad test already checks its built chain.
            if idx is None:
                continue
            by_keyword = any(k.arg == "scope" for k in node.keywords)
            by_position = idx != "kwonly" and len(node.args) > idx
            assert by_keyword or by_position, (
                f"{path.name} line {node.lineno}: {name}(...) is built without a "
                f"scope filter, so the chain pads a source it never resampled")
            checked += 1

    assert checked, "no filtergraph/command call sites were found to check"
