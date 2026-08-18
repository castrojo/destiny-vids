"""Tests for the act II builder completion wiring (scripts/build_efmb.py)."""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_efmb  # noqa: E402


def test_plated_master_burns_then_gates_the_delivered_master(monkeypatch, tmp_path):
    """Issue #219: the completion route renders the picture, burns the plates
    at the delivery spec, and runs the shared peak gate on
    ``renders/efmb-plated.mp4``."""
    calls = []
    monkeypatch.setattr(
        build_efmb,
        "render",
        lambda out_path=None, work_dir=None, verbose=True, ffmpeg=None: Path(
            tmp_path / "efmb-hq.mp4"
        ),
    )
    monkeypatch.setattr(build_efmb.plate, "render_all", lambda _e, _d: [])
    monkeypatch.setattr(
        build_efmb.plate,
        "burn",
        lambda video, entries, plates_dir, out_path, ffmpeg=None, runner=None,
               encode_args=None: calls.append(("burn", out_path, encode_args)),
    )
    monkeypatch.setattr(
        build_efmb.peaks,
        "trim_master_peak",
        lambda path: calls.append(("trim", path)),
    )

    build_efmb.plated_master(render_plates=False)

    assert len(calls) == 2
    burn_call, trim_call = calls
    assert burn_call[0] == "burn"
    assert trim_call[0] == "trim"
    assert Path(burn_call[1]).resolve() == build_efmb.PLATED_MASTER.resolve()
    assert trim_call[1] == build_efmb.PLATED_MASTER.resolve()
    assert burn_call[2] == build_efmb.conform.video_encode_args()


def test_plated_master_resolves_a_relative_output_path(monkeypatch, tmp_path):
    """The trim gate needs an absolute path; a relative --out must be resolved
    against the cwd before peaks sees it."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        build_efmb,
        "render",
        lambda out_path=None, work_dir=None, verbose=True, ffmpeg=None: Path(
            tmp_path / "efmb-hq.mp4"
        ),
    )
    monkeypatch.setattr(build_efmb.plate, "render_all", lambda _e, _d: [])
    monkeypatch.setattr(build_efmb.plate, "burn", lambda *a, **k: None)
    trimmed = []
    monkeypatch.setattr(
        build_efmb.peaks,
        "trim_master_peak",
        lambda path: trimmed.append(path),
    )
    build_efmb.plated_master(out_path="custom-plated.mp4", render_plates=False)
    assert trimmed[0] == (tmp_path / "custom-plated.mp4").resolve()


def test_render_alone_runs_only_the_picture_only_route(monkeypatch):
    """``--render`` is the picture-only intermediate; it does not burn plates
    or run the peak gate."""
    render_calls = []
    plated_calls = []
    monkeypatch.setattr(
        build_efmb,
        "render",
        lambda out_path=None, work_dir=None, verbose=True, ffmpeg=None: (
            render_calls.append(out_path) or build_efmb.HQ_MASTER
        ),
    )
    monkeypatch.setattr(
        build_efmb,
        "plated_master",
        lambda out_path=None, ffmpeg=None, render_plates=True, verbose=False: (
            plated_calls.append(out_path) or build_efmb.PLATED_MASTER
        ),
    )
    build_efmb.main(["--render"])
    assert len(render_calls) == 1
    assert not plated_calls


def test_render_with_burn_runs_the_full_completion_route(monkeypatch):
    """``--render --burn`` is the delivered-master route: it burns plates and
    gates the result."""
    render_calls = []
    plated_calls = []
    monkeypatch.setattr(
        build_efmb,
        "render",
        lambda out_path=None, work_dir=None, verbose=True, ffmpeg=None: (
            render_calls.append(out_path) or build_efmb.HQ_MASTER
        ),
    )
    monkeypatch.setattr(
        build_efmb,
        "plated_master",
        lambda out_path=None, ffmpeg=None, render_plates=True, verbose=False: (
            plated_calls.append(out_path) or build_efmb.PLATED_MASTER
        ),
    )
    build_efmb.main(["--render", "--burn"])
    assert len(plated_calls) == 1
    assert not render_calls
