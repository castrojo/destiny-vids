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


def test_the_prologue_gates_its_delivered_master_peak():
    source = (REPO_ROOT / "scripts" / "build_prologue.py").read_text()
    assert "peaks.trim_master_peak(OUT.resolve())" in source


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
    assert item["fade_out"] == 0, "the 4:36 join is a hard cut"


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


# --- the owner's join pass, 2026-08-14 (v2.1) -------------------------------
#
# Four notes taken while watching v2.0. They are asserted here rather than
# left in the plan alone because three of them are ZEROES -- a fade that is
# absent looks identical to a fade nobody thought about, and the next person
# to "tidy up" the plan would put them back.

ACT_VI = "06-7daystothewolves"
COMIC_CUT = 431.231   # 36 ms ahead of the 431.243 hit; the comic comes up at 431.267


def _item(plan, needle):
    return next(i for i in plan["items"]
                if needle in (i.get("path") or i.get("image", "")))


def test_act_six_is_cut_at_the_comic(plan):
    """One frame removes the comic cover and the song's fade-out together.

    Measured: 431.267 is act VI's last shot change. The cover comes up on it
    and holds 12.2 s to the end, and the audio is at full level right up to
    it (-12.6 dB) and decaying immediately after. The owner asked for both to
    go, and both go with one cut.

    The cut sits 36 ms EARLIER than that shot change, at 431.231, and the 36 ms
    are the owner's 'hot mess' note (2026-08-15): there is a hit at 431.243, so
    cutting on the shot change played the attack of a drum and took the rest
    away. 431.231 is the frame boundary ahead of the transient. The comic is
    still never seen -- it starts 36 ms after the cut.
    """
    assert _item(plan, ACT_VI)["trim_to"] == COMIC_CUT


def test_the_trim_keeps_every_tail_credit(plan):
    """A dropped credit is not recoverable by a revert.

    Act VI's tail plates -- the Cayde-6 reveal, the three gold credits, and
    castrojo's six spoken lines -- all end before the cut. This reads the
    plate manifest rather than trusting a number copied into a comment, and
    the margin is now 1.25 s rather than 21.6 s: the six pills were seated
    into the empty tail this cut used to have to spare.
    """
    plates = json.loads(
        (REPO_ROOT / "stories" / "06-wolves-cayde-plates.json").read_text())
    last = max(p["at"] + p.get("dur", 0) for p in plates["plates"])
    assert last < COMIC_CUT, (
        f"the trim at {COMIC_CUT} would cut a credit ending at {last}")


def test_the_wolves_join_is_hard_on_both_sides(plan):
    """'go right into the next song' -- no fade either side of the join."""
    assert _item(plan, ACT_VI).get("fade_out", 0) == 0
    assert _item(plan, "perfume-4")["fade_in"] == 0


def test_europa_has_no_slide_and_takes_a_quick_cut(plan):
    """'make it a quick cut to europa get rid of the title slide.'"""
    images = [i.get("image", "") for i in plan["items"]]
    assert not any("plate_act7" in img for img in images), (
        "act VII's title slide is meant to be gone")
    assert _item(plan, "perfume-4")["fade_out"] == 0
    assert _item(plan, "07-europa")["fade_in"] == 0


def test_act_seven_therefore_has_no_chapter_marker(plan):
    """The cost of the instruction, asserted so it cannot be re-added quietly.

    chapters() derives markers from slides. No slide means no marker, exactly
    as for act VIII. If somebody restores a VII card they must decide about
    the hard cut too, and this test is where they find that out.
    """
    chapters = [i.get("chapter") for i in plan["items"] if i.get("chapter")]
    assert not any(c.startswith("II.") for c in chapters)
    assert not any(c.startswith("VII.") for c in chapters)
    assert len(chapters) == 4


def test_the_two_dramatic_joins_carry_no_audio_dip(plan):
    """Where the picture does the work, the sound must not duck under it.

    12:43 -- act III blooms to white and movement 3 falls out of the sky.
    27:03 -- Europa fades to black and movement 5 opens on a dark Earth limb
    that holds 3.5 s before the sunrise. Both had a fade-out meeting a
    fade-in, which is a hole in the sound at the exact moment the cut lands.
    """
    assert _item(plan, "03-mrbobbytables")["fade_out"] == 0
    assert _item(plan, "perfume-3")["fade_in"] == 0
    assert _item(plan, "perfume-5")["fade_in"] == 0
