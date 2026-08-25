import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(autouse=True)
def _farm_is_offline_in_tests(monkeypatch):
    """The suite is offline BY CONSTRUCTION: no test may reach the cluster,
    and no test's result may depend on this host having systemd-run.

    Every farm-first entry point probes ``tools.farm.cluster_available()``;
    with the kubectl layer stubbed the probe answers (False, ...) in
    microseconds, so code under test takes its documented local fallback
    everywhere the suite runs. Tests that exercise the farm path itself
    monkeypatch ``farm.cluster_available``/``farm.run_ffmpeg_on_cluster``
    (overriding this fixture), and tools/farm.py's own tests monkeypatch
    ``farm.Kubectl`` the same way. ``_systemd_run_prefix`` stubbed to "no
    cap" keeps wrapped-vs-unwrapped argv shape out of every assertion; the
    cap has its own tests, which stub the prefix explicitly.
    """
    from tools import farm

    class _OfflineKubectl:
        def __init__(self, *a, **k):
            pass

        def run(self, args, **k):
            import subprocess
            return subprocess.CompletedProcess(
                args, 1, "", "the test suite is offline (tests/conftest.py)")

    monkeypatch.setattr(farm, "Kubectl", _OfflineKubectl)
    monkeypatch.setattr(farm, "_systemd_run_prefix", lambda: [])
