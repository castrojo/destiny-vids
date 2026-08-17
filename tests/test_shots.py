"""The contact-sheet tool: timecodes, layout, and the AV1 trap."""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import shots  # noqa: E402


def test_timecode_is_the_act_clock_spelling():
    """`M:SS.mmm` -- what stories/*-plates.json uses for an `at`.

    The label exists so a plate's mark can be read straight off the sheet, so
    it has to be the same spelling; a sheet in H:MM:SS would need converting
    by eye, which is how a card lands on the wrong shot.
    """
    assert shots.tc(0) == "0:00.000"
    assert shots.tc(9.5) == "0:09.500"
    assert shots.tc(69.7) == "1:09.700"
    assert shots.tc(269.700) == "4:29.700"


def test_the_detector_matches_the_one_the_cuts_were_measured_with():
    """27.0 is scripts/build_efmb.py's threshold.

    A sheet found at a different threshold is a different shot list, and then
    a note taken off the sheet cites a boundary the cut does not have.
    """
    assert shots.THRESHOLD == 27.0


def test_a_single_scene_result_is_returned_whole(monkeypatch):
    """An act with no detected cut still yields one span, not an empty sheet.

    scenedetect returns [] for a video it finds no boundary in. That is the
    honest answer for a continuous take -- and it is ALSO what AV1 through
    OpenCV looks like (docs/skills/indexing.md), so the count is reported and
    a human decides which it was, rather than the tool guessing.
    """
    class FakeTime:
        def __init__(self, s): self._s = s
        def get_seconds(self): return self._s
        @property
        def seconds(self): return self._s

    class FakeVideo:
        duration = FakeTime(42.0)

    class FakeManager:
        def add_detector(self, d): pass
        def detect_scenes(self, v, show_progress=False): pass
        def get_scene_list(self): return []

    fake = type(sys)("scenedetect")
    fake.open_video = lambda p: FakeVideo()
    fake.SceneManager = FakeManager
    detectors = type(sys)("scenedetect.detectors")
    detectors.ContentDetector = lambda threshold=None: object()
    monkeypatch.setitem(sys.modules, "scenedetect", fake)
    monkeypatch.setitem(sys.modules, "scenedetect.detectors", detectors)

    assert shots.detect("whatever.mp4") == [(0.0, 42.0)]


def test_labels_are_drawn_with_pillow_not_drawtext():
    """The container ffmpeg has no fontconfig, so `drawtext` fails on it.

    This is not hypothetical: the first build of this tool died with
    "Fontconfig error: Cannot load default config file" on every frame. Pillow
    is already a dependency for tools/plate.py, so the labels use it.
    """
    source = Path(shots.__file__).read_text()
    assert "drawtext" not in source.split('"""')[0] + source.split('"""')[-1]
    assert "ImageDraw" in source
    font = shots._label_font()
    assert font is not None
