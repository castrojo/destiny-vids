"""Tests for the act I builder (scripts/build_act1.py)."""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_act1  # noqa: E402


def _patch_stages(monkeypatch):
    """Make the first half of the build a no-op; we only care about burn/trim."""
    monkeypatch.setattr(build_act1, "cover_art", lambda: None)
    monkeypatch.setattr(build_act1, "render_cards", lambda: None)
    monkeypatch.setattr(build_act1.plate, "render_all", lambda _entries, _out: [])
    monkeypatch.setattr(
        build_act1.subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, "", ""),
    )


def test_burn_completes_before_peak_trim(monkeypatch):
    """Issue #219: the final-master gate runs AFTER the plate burn, not on a
    partial intermediate."""
    _patch_stages(monkeypatch)
    calls = []
    monkeypatch.setattr(
        build_act1.plate,
        "burn",
        lambda *args, ffmpeg=None, runner=None, **kwargs: calls.append("burn"),
    )
    monkeypatch.setattr(
        build_act1.peaks,
        "trim_master_peak",
        lambda path: calls.append(("trim", path)),
    )
    build_act1.build_act1(skip_encode=False, use_farm=False)
    assert calls == ["burn", ("trim", Path(build_act1.MASTER).resolve())]


def test_peak_trim_receives_the_resolved_master_path(monkeypatch):
    """The gate needs an absolute path so a containerized ffmpeg can see the
    file; the builder must resolve MASTER before handing it to peaks."""
    _patch_stages(monkeypatch)
    trimmed = []
    monkeypatch.setattr(build_act1.plate, "burn", lambda *a, **k: None)
    monkeypatch.setattr(
        build_act1.peaks, "trim_master_peak", lambda path: trimmed.append(path)
    )
    build_act1.build_act1(skip_encode=False, use_farm=False)
    (path,) = trimmed
    assert path.is_absolute()
    assert path == (REPO_ROOT / build_act1.MASTER).resolve()


def test_skip_encode_never_trims(monkeypatch):
    """--skip-encode stops after plates; no encode means no delivered file to
    gate, so peaks.trim_master_peak must not run."""
    _patch_stages(monkeypatch)
    burn_calls = []
    trim_calls = []
    monkeypatch.setattr(build_act1.plate, "burn", lambda *a, **k: burn_calls.append(1))
    monkeypatch.setattr(
        build_act1.peaks, "trim_master_peak", lambda path: trim_calls.append(path)
    )
    build_act1.build_act1(skip_encode=True, use_farm=False)
    assert not burn_calls
    assert not trim_calls
