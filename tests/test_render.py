"""ffmpeg resolution order for tools/render.py.

The order matters more than it looks: on Bluefin the ffmpeg on PATH is
``ffmpeg-free``, which has no H.264 decoder and fails only once decoding
starts. PATH must therefore rank last, and the container must rank first.
See docs/rendering.md.
"""

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import render  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for var in ("DESTINY_FFMPEG", "DESTINY_FFMPEG_CONTAINER", "DESTINY_FFMPEG_IMAGE"):
        monkeypatch.delenv(var, raising=False)


def test_find_ffmpeg_returns_argv_prefix_list(monkeypatch):
    """A list, never a bare string: a container ffmpeg is multiple argv words."""
    monkeypatch.setenv("DESTINY_FFMPEG", "/usr/bin/ffmpeg")
    assert render.find_ffmpeg() == ["/usr/bin/ffmpeg"]


def test_env_override_is_shell_split_and_wins(monkeypatch):
    monkeypatch.setattr(render, "_container_running", lambda name: True)
    monkeypatch.setenv("DESTINY_FFMPEG", "podman exec other ffmpeg")
    assert render.find_ffmpeg() == ["podman", "exec", "other", "ffmpeg"]


def test_running_container_is_preferred_over_path(monkeypatch):
    monkeypatch.setattr(render.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(render, "_container_running", lambda name: True)
    assert render.find_ffmpeg() == ["podman", "exec", render.DEFAULT_CONTAINER, "ffmpeg"]


def test_container_name_is_configurable(monkeypatch):
    monkeypatch.setattr(render.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(render, "_container_running", lambda name: name == "custom-ff")
    monkeypatch.setenv("DESTINY_FFMPEG_CONTAINER", "custom-ff")
    assert render.find_ffmpeg() == ["podman", "exec", "custom-ff", "ffmpeg"]


def test_no_container_flag_skips_podman(monkeypatch):
    monkeypatch.setattr(render.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(render, "_container_running", lambda name: True)
    assert render.find_ffmpeg(prefer_container=False)[0] != "podman"


def test_ephemeral_run_used_when_image_set_and_no_container(monkeypatch):
    monkeypatch.setattr(render.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(render, "_container_running", lambda name: False)
    monkeypatch.setenv("DESTINY_FFMPEG_IMAGE", "example.org/ffmpeg:1")
    cmd = render.find_ffmpeg()
    assert cmd[:3] == ["podman", "run", "--rm"]
    assert "example.org/ffmpeg:1" in cmd
    home = str(Path.home())
    assert f"{home}:{home}" in cmd, "home must be bind-mounted at the same path"


def test_path_ffmpeg_is_last_resort(monkeypatch):
    monkeypatch.setattr(render.shutil, "which",
                        lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None)
    monkeypatch.setitem(sys.modules, "imageio_ffmpeg", None)
    assert render.find_ffmpeg() == ["/usr/bin/ffmpeg"]


def test_raises_when_nothing_available(monkeypatch):
    monkeypatch.setattr(render.shutil, "which", lambda name: None)
    monkeypatch.setitem(sys.modules, "imageio_ffmpeg", None)
    with pytest.raises(RuntimeError, match="no ffmpeg found"):
        render.find_ffmpeg()


def test_resolve_media_returns_absolute_path(tmp_path, monkeypatch):
    """Relative paths break under `podman exec`: it has a different cwd."""
    media = tmp_path / "media"
    media.mkdir()
    (media / "yt_x.mp4").write_bytes(b"")
    monkeypatch.chdir(tmp_path)
    found = render.resolve_media("yt_x", "media")
    assert found.is_absolute()
    assert found == (media / "yt_x.mp4").resolve()


def test_resolve_media_missing_returns_none(tmp_path):
    assert render.resolve_media("nope", tmp_path) is None


def test_concat_list_is_written_beside_output_not_tmp(tmp_path, monkeypatch):
    """A containerized ffmpeg only sees the bind-mounted home, never /tmp."""
    seen = {}

    def fake_run(cmd, check=False):
        idx = cmd.index("-i")
        list_path = Path(cmd[idx + 1])
        seen["dir"] = list_path.parent
        seen["contents"] = list_path.read_text()
        return None

    monkeypatch.setattr(render.subprocess, "run", fake_run)
    workdir = tmp_path / "work"
    workdir.mkdir()
    clips = [tmp_path / "a.mp4", tmp_path / "b.mp4"]
    render.concat(["ffmpeg"], clips, tmp_path / "out.mp4", workdir=workdir)

    assert seen["dir"] == workdir
    assert seen["dir"] != Path(os.environ.get("TMPDIR", "/tmp"))
    assert str(clips[0].resolve()) in seen["contents"]
    assert not list(workdir.glob("concat_list.txt")), "list file must be cleaned up"


def test_cap_holds_trims_from_the_tail_only():
    """The in-point is what the index worked to find; trims come off the end."""
    shots = [
        {"segment_id": "a", "start_sec": 10.0, "end_sec": 35.0, "duration": 25.0},
        {"segment_id": "b", "start_sec": 4.0, "end_sec": 6.0, "duration": 2.0},
    ]
    capped = render.cap_holds(shots, 8.0)
    assert capped[0]["start_sec"] == 10.0
    assert capped[0]["end_sec"] == 18.0
    assert capped[0]["duration"] == 8.0
    assert capped[1] == shots[1]          # under the cap, untouched
    assert shots[0]["duration"] == 25.0   # input list is not mutated


def test_cap_holds_without_a_cap_is_a_passthrough():
    shots = [{"segment_id": "a", "start_sec": 0.0, "end_sec": 30.0, "duration": 30.0}]
    assert render.cap_holds(shots, None) == shots


def test_cap_holds_derives_duration_when_absent():
    shots = [{"segment_id": "a", "start_sec": 2.0, "end_sec": 22.0}]
    assert render.cap_holds(shots, 5.0)[0]["end_sec"] == 7.0
