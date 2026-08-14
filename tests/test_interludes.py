"""The Perfume thread: one song, contiguous, seated between the acts.

The failure these guard against is not a crash. It is a thread that quietly
stops being a thread -- a movement retimed by a frame, a gap opened between
two of them, or a fade burned into a render that is supposed to stay clean for
the dinosaur pass. All three would render fine and exit 0.
"""

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "stories" / "00-perfume-thread.json"
PLAN = REPO_ROOT / "stories" / "megacut" / "megacut.json"

# Where the prologue's SONG leaves off, and where movement 2 picks it up.
# scripts/build_prologue.py fades from 93.000 over 6.200 s.
PROLOGUE_FADE_START = 93.000
PROLOGUE_FADE = 6.200


@pytest.fixture(scope="module")
def thread():
    return json.loads(MANIFEST.read_text())


@pytest.fixture(scope="module")
def plan():
    return json.loads(PLAN.read_text())


@pytest.fixture(scope="module")
def movements(thread):
    return thread["movements"]


def test_the_thread_has_no_gaps(movements):
    """Movement N ends exactly where movement N+1 begins.

    The whole idea is one song the acts interrupt. A gap of even a few frames
    is heard as a mistake rather than as an edit, and it would never be caught
    by watching an act on its own.
    """
    for earlier, later in zip(movements, movements[1:]):
        assert earlier["out"] == later["in"], (
            f"{earlier['id']} ends at {earlier['out']} but "
            f"{later['id']} starts at {later['in']}")


def test_every_duration_is_its_own_span(movements):
    for movement in movements:
        span = round(movement["out"] - movement["in"], 3)
        assert span == pytest.approx(movement["duration"], abs=1e-6), (
            f"{movement['id']}: {movement['in']} -> {movement['out']} is "
            f"{span}s, but duration says {movement['duration']}")


def test_movement_two_resumes_where_the_prologue_faded(movements):
    """93.000, not 91.200 -- the owner's 'wherever the last cut left off'.

    The prologue leaves off in two places: picture at 91.200, song at 99.200
    after fading from 93.000. Movement 2 picks up the fade's own start so the
    6.2 s that went down comes back up, instead of the song restarting.
    """
    assert movements[0]["id"] == "perfume-2"
    assert movements[0]["in"] == PROLOGUE_FADE_START


def test_the_thread_runs_to_the_end_of_the_source(thread, movements):
    assert movements[-1]["out"] == thread["source_duration"], (
        "the owner asked to 'hold until the end of this'; the last movement "
        "must reach EOF")


def test_the_renders_stay_clean(movements):
    """No fade, no overlay, no card in the manifest -- treatment is the plan's.

    Two reasons pointing the same way: this repo keeps join treatment in
    megacut.json in act-film time, and the owner wants these snippets
    editable ('we will be editing them in the future with dino artwork').
    A burned dip would have to be un-baked.
    """
    burned = {"fade_in", "fade_out", "fade", "plates", "overlay", "cards"}
    for movement in movements:
        assert not burned & set(movement), (
            f"{movement['id']} declares burned-in treatment; fades belong in "
            f"stories/megacut/megacut.json, in act-film time")


def test_every_movement_renders_to_the_render_folder(movements):
    """renders/, never Prod/. Prod means 'a finished act'; these are not."""
    for movement in movements:
        assert movement["out_file"].startswith("renders/"), movement["id"]
        assert "Prod" not in movement["out_file"], movement["id"]


def _clip_paths(plan):
    return [item.get("path", item.get("image", ""))
            for item in plan["items"]]


def test_the_programme_seats_every_movement(plan, movements):
    paths = _clip_paths(plan)
    for movement in movements:
        assert movement["out_file"] in paths, (
            f"{movement['id']} is built but never plays")


def test_the_movements_sit_where_the_owner_put_them(plan):
    """The seats, by the act each one follows or precedes.

    Asserted as ORDER, not as index: inserting another act must move these
    rather than silently reseat them.
    """
    paths = _clip_paths(plan)

    def seat(needle):
        return next(i for i, p in enumerate(paths) if needle in p)

    assert seat("01-intro") < seat("renders/perfume-2.mp4") < seat("02-endless")
    assert seat("03-mrbobbytables") < seat("renders/perfume-3.mp4") < seat("04-kat")
    assert seat("06-7daystothewolves") < seat("renders/perfume-4.mp4") < seat("07-europa")
    assert seat("07-europa") < seat("renders/perfume-5.mp4") < seat("08-credits")


def test_movement_two_fades_up_over_the_prologues_fade_down(plan):
    """6.2 s is not a default -- it is the prologue's own fade, reversed."""
    item = next(i for i in plan["items"]
                if i.get("path") == "renders/perfume-2.mp4")
    assert item["fade_in"] == pytest.approx(PROLOGUE_FADE)


def test_no_movement_announces_itself(plan, movements):
    """No slide, no chapter marker: the numerals are load-bearing.

    chapters() derives markers from cards, so a movement that ever acquired a
    `chapter` key would put an unnumbered entry on the scrub bar between two
    numbered acts.
    """
    built = {m["out_file"] for m in movements}
    for item in plan["items"]:
        if item.get("path") in built:
            assert "chapter" not in item, item["path"]
            assert item.get("kind") == "clip", item["path"]


def test_the_source_is_never_committed(thread):
    source = REPO_ROOT / thread["source"]
    assert source.parent.name == "media", (
        "footage lives in gitignored media/; the manifest carries timecodes")
