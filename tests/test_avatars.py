"""The avatar cache: what it asks for, what it refuses to ask twice.

Offline like the rest of the suite. Every request here goes through a fake
opener, every wait through a fake clock, so the whole file runs with no network
and no elapsed time.

What is pinned is the politeness, because that is what is expensive to
rediscover: a face already on disk costs a conditional request, a deleted
account costs nothing for a month, and a throttled run stops instead of firing
five hundred more requests at a server that just said no.
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_credits as B  # noqa: E402
from tools import avatars as A  # noqa: E402
from tools import credits as C  # noqa: E402

WORKFLOW = REPO_ROOT / ".github" / "workflows" / "avatars.yml"
PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * A.MIN_BYTES

class Clock:
    """Time that only moves when something sleeps."""

    def __init__(self, start=1_700_000_000.0):
        self.t = start
        self.slept = []

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.t += seconds

class Response:
    def __init__(self, payload, headers=None):
        self.payload = payload
        self.headers = headers or {}

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

class Opener:
    """A fake ``urlopen``: records every request, answers from a script."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.requests = []

    def __call__(self, req, timeout=None):
        self.requests.append(req)
        answer = self.answers.pop(0) if self.answers else self.answers
        if isinstance(answer, Exception):
            raise answer
        return answer

def http(code, headers=None):
    return urllib.error.HTTPError(
        "https://github.com/x.png", code, "no", headers or {}, None)

@pytest.fixture
def cache(tmp_path, monkeypatch):
    """Point the module at a throwaway directory, not the real cache."""
    monkeypatch.setattr(C, "AVATAR_DIR", tmp_path)
    return tmp_path

def budget(clock, total=A.MAX_SLEEP_TOTAL):
    return A.Budget(total=total, sleep=clock.sleep, clock=clock.now)

# --- conditional requests --------------------------------------------------

def test_a_cached_face_is_revalidated_not_refetched(cache):
    """The ETag goes out, the 304 comes back, and the bytes never move."""
    (cache / "ada.png").write_bytes(PNG)
    index = {"ada": {"status": "have", "etag": '"abc"', "checked": 0}}
    clock = Clock()
    opener = Opener(http(304))

    outcome = A.fetch_one("ada", index, budget(clock), opener=opener)

    assert outcome == "fresh"
    assert opener.requests[0].get_header("If-none-match") == '"abc"'
    assert (cache / "ada.png").read_bytes() == PNG

def test_an_etag_is_only_offered_when_there_is_a_file_to_back_it(cache):
    """An ETag with no image would earn a 304 and leave the cache empty."""
    index = {"ada": {"status": "have", "etag": '"abc"', "checked": 0}}
    clock = Clock()
    opener = Opener(Response(PNG, {"ETag": '"def"'}))

    outcome = A.fetch_one("ada", index, budget(clock), opener=opener)

    assert outcome == "fetched"
    assert opener.requests[0].get_header("If-none-match") is None
    assert (cache / "ada.png").read_bytes() == PNG
    assert index["ada"]["etag"] == '"def"'

def test_a_truncated_download_is_not_written_over_nothing(cache):
    """Half a PNG is not a face; the renderer's ring is the better answer."""
    clock = Clock()
    outcome = A.fetch_one("ada", {}, budget(clock),
                          opener=Opener(Response(b"\x89PNG")))

    assert outcome == "failed"
    assert not (cache / "ada.png").exists()

# --- negative caching ------------------------------------------------------

def test_a_deleted_account_is_asked_about_once_a_month(cache):
    """A 404 is an answer. Re-asking it 500 times a build is the bug."""
    index = {}
    clock = Clock()
    assert A.fetch_one("ghost", index, budget(clock),
                       opener=Opener(http(404))) == "gone"
    assert index["ghost"]["status"] == "gone"

    assert not A.due("ghost", index, now=clock.now())
    assert not A.due("ghost", index, now=clock.now() + A.GONE_TTL - 1)
    assert A.due("ghost", index, now=clock.now() + A.GONE_TTL + 1)

def test_a_fresh_face_is_skipped_and_a_stale_one_is_revalidated(cache):
    (cache / "ada.png").write_bytes(PNG)
    clock = Clock()
    index = {"ada": {"status": "have", "checked": clock.now()}}

    assert not A.due("ada", index, now=clock.now())
    assert A.due("ada", index, now=clock.now() + A.FRESH_FOR + 1)
    assert A.due("ada", index, now=clock.now(), revalidate=True)

def test_a_login_with_no_file_is_always_due(cache):
    clock = Clock()
    index = {"ada": {"status": "have", "checked": clock.now()}}
    assert A.due("ada", index, now=clock.now())

# --- throttling ------------------------------------------------------------

def test_a_rate_limit_reset_is_read_as_a_deadline_not_a_duration():
    """``x-ratelimit-reset`` is an epoch. Sleeping for it would be 54 years."""
    now = 1_700_000_000.0
    assert A._retry_after({"x-ratelimit-reset": str(now + 30)}, now) == 30
    assert A._retry_after({"Retry-After": "7"}, now) == 7
    # Retry-After wins: it is the direct instruction.
    assert A._retry_after(
        {"Retry-After": "7", "x-ratelimit-reset": str(now + 300)}, now) == 7
    assert A._retry_after({}, now) is None
    # A reset already in the past is not a negative sleep.
    assert A._retry_after({"x-ratelimit-reset": str(now - 300)}, now) == 0

def test_a_403_backs_off_the_way_the_server_asked(cache):
    clock = Clock()
    opener = Opener(http(403, {"Retry-After": "3"}),
                    Response(PNG, {"ETag": '"z"'}))

    outcome = A.fetch_one("ada", {}, budget(clock), opener=opener)

    assert outcome == "fetched"
    assert clock.slept == [3.0]

def test_a_403_with_no_instruction_still_waits(cache):
    """Silence is not permission to retry immediately."""
    clock = Clock()
    opener = Opener(http(403), Response(PNG, {"ETag": '"z"'}))

    assert A.fetch_one("ada", {}, budget(clock), opener=opener) == "fetched"
    assert clock.slept and clock.slept[0] > 0

def test_an_exhausted_budget_ends_the_run_instead_of_hammering(cache):
    """The failure this stops: 500 logins x 4 attempts against a closed door."""
    clock = Clock()
    opener = Opener(*[http(403, {"Retry-After": "30"}) for _ in range(20)])
    logins = [f"user{n}" for n in range(20)]

    tally, missing = A.fetch(logins, verbose=False, opener=opener,
                             budget=budget(clock, total=60.0),
                             spacing=0, sleep=clock.sleep)

    assert tally["throttled"] == 1
    assert sum(clock.slept) <= 60.0
    # Two waits fit in the budget, so three requests went out -- not twenty.
    assert len(opener.requests) < len(logins)
    assert len(missing) == len(logins)

def test_one_wait_is_capped_however_long_the_server_asks_for(cache):
    """An hour-long reset is not an hour of sleeping, and it still costs budget."""
    clock = Clock()
    b = budget(clock, total=A.MAX_SLEEP_TOTAL)
    assert b.wait(10_000) is True
    assert clock.slept == [A.MAX_SLEEP]
    # And a wait longer than what is left is refused outright.
    assert b.wait(A.MAX_SLEEP) is True
    b.left = 1.0
    assert b.wait(A.MAX_SLEEP) is False
    assert clock.slept == [A.MAX_SLEEP, A.MAX_SLEEP]

def test_a_run_that_writes_nothing_still_leaves_a_readable_index(cache):
    clock = Clock()
    A.fetch(["ghost"], verbose=False, opener=Opener(http(404)),
            budget=budget(clock), spacing=0, sleep=clock.sleep)

    assert json.loads(A.index_path().read_text())["ghost"]["status"] == "gone"
    assert A.load_index()["ghost"]["status"] == "gone"

def test_a_corrupt_index_is_a_cold_cache_not_a_crash(cache):
    A.index_path().write_text("{ this is not json")
    assert A.load_index() == {}

# --- who is asked about at all ---------------------------------------------

def test_a_gitlab_section_is_never_asked_of_github():
    """A display name is not a login. "Harald Sitter.png" fetches a stranger."""
    manifest = {
        "contributors": [
            {"host": "gitlab.gnome.org", "names": ["Harald Sitter"]},
            {"names": ["castrojo"]},
        ],
    }
    logins = B.avatar_logins(manifest)
    assert "castrojo" in logins
    assert "Harald Sitter" not in logins
    assert all(" " not in login for login in logins)

def test_the_real_manifest_asks_only_for_things_that_look_like_logins():
    manifest = json.loads((REPO_ROOT / "stories" / "08-credits.json").read_text())
    logins = B.avatar_logins(manifest)
    assert logins
    # A ``_comment`` in ``cast_logins`` is prose, not a person.
    assert all(" " not in login for login in logins)
    assert len(logins) == len(set(logins))

# --- the CI bridge ---------------------------------------------------------

def test_a_missing_gh_is_a_note_not_a_failure(cache):
    def runner(*_a, **_k):
        raise FileNotFoundError("gh")

    assert A.pull_from_actions(verbose=False, runner=runner) is False

def test_a_failed_download_falls_back_to_fetching_directly(cache):
    class Done:
        returncode = 1
        stderr = "no artifact matches"
        stdout = ""

    assert A.pull_from_actions(verbose=False, runner=lambda *a, **k: Done()) is False

def test_the_download_asks_for_the_artifact_the_workflow_uploads(cache):
    seen = {}

    class Done:
        returncode = 0
        stderr = ""
        stdout = ""

    def runner(cmd, **_k):
        seen["cmd"] = cmd
        return Done()

    assert A.pull_from_actions(verbose=False, runner=runner) is True
    assert seen["cmd"][:3] == ["gh", "run", "download"]
    assert A.ARTIFACT in seen["cmd"]

def test_the_workflow_uploads_the_name_the_downloader_asks_for():
    """The upload and the download drift apart silently. This is the tie."""
    text = WORKFLOW.read_text()
    assert f"name: {A.ARTIFACT}" in text
    assert WORKFLOW.name == A.WORKFLOW

def test_the_workflow_runs_on_the_runner_token_and_never_a_pat():
    """The owner's instruction, pinned: built-in token only, no secrets."""
    text = WORKFLOW.read_text()
    assert "${{ github.token }}" in text
    assert "secrets." not in text
    assert "permissions:" in text and "contents: read" in text
