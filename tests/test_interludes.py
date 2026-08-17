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
FLASH_CUT = 430.997   # act VI's last shot change; the 14-frame flash starts here


def _item(plan, needle):
    return next(i for i in plan["items"]
                if needle in (i.get("path") or i.get("image", "")))


def test_act_six_is_cut_before_its_closing_flash(plan):
    """One frame removes three things the owner asked to lose.

    The comic cover comes up at 431.267 and holds 12.2 s, the song's fade-out
    begins on the same frame, and the act's last 14 frames are a separate shot
    -- a pink tableau flashing to a dark Exo shot from 430.997 -- which is the
    "too janky" the owner named at programme 22:38.

    Cutting on 430.997 takes all three. The needle drop survives it: post-seam
    audio cross-correlates with the longer cut at lag 0.00 ms, r = 0.997, and
    movement 4 still opens on its own first hit +0.032 s past the seam.
    """
    assert _item(plan, ACT_VI)["trim_to"] == FLASH_CUT


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
    assert last < FLASH_CUT, (
        f"the trim at {FLASH_CUT} would cut a credit ending at {last}")


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


# --- movement 4's owner notes, 2026-08-17 ----------------------------------
#
# Four notes inside movement 4 (stories/00-perfume-thread.json): two ghost
# renditions swapped for bluefin-day, the CNCF summit photograph over the
# apparitions, and the band montage swapped for four artworks. Every swap is
# duration-locked to a measured shot, and the 22:52 "then resume here" is an
# INVARIANT: the source picture between the two ghost windows is not a gap
# that a snap-to-boundary may swallow.

from scripts import build_interludes


def _movement(movements, movement_id):
    return next(m for m in movements if m["id"] == movement_id)


def _fake_cache(monkeypatch, root):
    """Point the art rungs at an empty tmp cache (CI never has the real one;
    it is gitignored). Returns the two rung directories."""
    artwork = root / "renders" / "artwork"
    summit = root / "renders" / "summit-plates"
    artwork.mkdir(parents=True)
    summit.mkdir(parents=True)
    monkeypatch.setattr(build_interludes, "ARTWORK_DIR", artwork)
    monkeypatch.setattr(build_interludes, "SUMMIT_DIR", summit)
    monkeypatch.setattr(build_interludes, "REPO_ROOT", root)
    return artwork, summit


def test_movement_four_carries_seven_duration_locked_replacements(
        movements, monkeypatch, tmp_path):
    """Seven swaps, none overlapping, none past the end -- so the concat
    arithmetic holds and the movement stays exactly 115.560."""
    movement = _movement(movements, "perfume-4")
    repls = movement["replacements"]
    assert len(repls) == 7
    end = 0.0
    for repl in repls:
        assert float(repl["at"]) >= end - 1e-9, repl["id"]
        end = float(repl["at"]) + float(repl["dur"])
        assert end <= float(movement["duration"]) + 1e-6, repl["id"]
    # The same check the builder gates on: every artwork the record names
    # resolves through art_path, so nothing is silently skipped at render.
    artwork, _summit = _fake_cache(monkeypatch, tmp_path)
    for repl in repls:
        for name in repl["art"]:
            path = (tmp_path / name["file"] if isinstance(name, dict)
                    else artwork / f"{name}.png")
            path.touch()
    assert len(build_interludes.usable_replacements(movement)) == 7


def test_the_resume_at_2252_is_an_invariant_not_a_gap(movements, thread):
    """Owner: '22:50 overlay a bluefin day wallpaper instead of this ghosty
    man', then '22:52 then resume here'. The source picture MUST run
    untouched from 15.120 until the second ghost's measured start at 18.280
    -- a snap to the 292.520 shot boundary would hold the wallpaper over the
    very frames the owner asked back."""
    movement = _movement(movements, "perfume-4")
    by_id = {r["id"]: r for r in movement["replacements"]}
    tank, desk = by_id["ghost-tank"], by_id["ghost-desk"]
    resume = float(tank["at"]) + float(tank["dur"])
    assert resume == pytest.approx(15.12)
    assert float(desk["at"]) == pytest.approx(18.28)
    assert resume < float(desk["at"])
    # The graph itself keeps the window as source: a kept segment trimmed
    # 15.120 -> 18.280, concatenated between the two swaps. The graph is
    # built from the RECORD directly -- video_chain takes the replacements
    # it is given; the cache check belongs to the builder, not the string.
    graph = build_interludes.video_chain(
        thread, movement, movement["replacements"])
    assert "trim=15.120:18.280" in graph
    assert "[s0][ghost_tank_v][s1][ghost_desk_v]" in graph


def test_the_band_montage_switches_land_on_measured_member_cuts(movements):
    """'sync so they switch matching the same pace as the individual band
    members switch out': SIX member shots were measured (351.600 / 351.960 /
    352.240 / 352.520 / 352.800 / 353.080, out 353.360), the owner named FOUR
    artworks, so each artwork is duration-locked to measured member
    boundaries and every switch is exactly the previous artwork's end."""
    movement = _movement(movements, "perfume-4")
    band = [r for r in movement["replacements"]
            if r["id"].startswith("band-")]
    assert [r["id"] for r in band] == [
        "band-huntress", "band-duality", "band-bluefin", "band-eyes"]
    assert [r["art"] for r in band] == [
        ["huntress"], ["duality-day"], ["bluefin-day"], ["eyes"]]
    assert [float(r["at"]) for r in band] == [
        pytest.approx(x) for x in (77.360, 78.000, 78.560, 78.840)]
    for earlier, later in zip(band, band[1:]):
        assert float(later["at"]) == pytest.approx(
            float(earlier["at"]) + float(earlier["dur"]))
    last_end = float(band[-1]["at"]) + float(band[-1]["dur"])
    assert last_end == pytest.approx(79.120)  # source 353.360: the explosion


def test_the_summit_photograph_is_an_explicit_cached_file(movements):
    """A JPEG photograph is not a wallpaper name: the contributor-summit
    replacement names its file, and the rights record stays in
    stories/summit-photos.json."""
    movement = _movement(movements, "perfume-4")
    summit = next(r for r in movement["replacements"]
                  if r["id"] == "contributor-summit")
    assert summit["art"] == [{"file": "renders/summit-plates/enemy_cu.jpg"}]


def test_art_path_rungs(monkeypatch, tmp_path):
    """Wallpaper cache first, then the summit plates, then nothing."""
    artwork, summit = _fake_cache(monkeypatch, tmp_path)

    assert build_interludes.art_path("missing") is None

    plate = summit / "enemy_cu.jpg"
    plate.touch()
    assert build_interludes.art_path("enemy_cu") == plate

    paper = artwork / "bluefin-day.png"
    paper.touch()
    assert build_interludes.art_path("bluefin-day") == paper

    explicit = summit / "group-002.jpg"
    explicit.touch()
    assert build_interludes.art_path(
        {"file": "renders/summit-plates/group-002.jpg"}) == explicit
    assert build_interludes.art_path({"file": "renders/nope.png"}) is None


# --- the movement 2 jump scare, 2026-08-17 ---------------------------------
#
# Owner: "4:17 keep this day mode version of dusk, the 'jump scare' is too
# early" / "4:21 put the jump scare here. Analyze the audio for maximum
# effect". The turn point is now authored (turn_at) rather than an emergent
# property of even division, and the flash sits on the largest MEASURED
# onset inside the 4:21 window.


def test_the_dusk_turn_point_is_authored_not_emergent(movements, thread):
    """turn_at 2.096: day holds until source 141.016 (past 4:17, as the
    owner asked), and the 2.2 s turn completes at source 143.216 -- the
    frame the scare lands. The legs still sum to exactly 5.600."""
    movement = _movement(movements, "perfume-2")
    repl = movement["replacements"][0]
    assert repl["id"] == "dusk-turn"
    assert repl["turn_at"] == pytest.approx(2.096)
    assert repl["turn_sec"] == pytest.approx(2.2)
    assert repl["dur"] == pytest.approx(5.6)
    graph = build_interludes.video_chain(thread, movement,
                                         movement["replacements"])
    # day leg: 2.096 + 2.2; night leg: 5.6 - 2.096; the turn at 2.096.
    assert "trim=0:4.296,setpts=PTS-STARTPTS[dusk_turn_a0]" in graph
    assert "trim=0:3.504,setpts=PTS-STARTPTS[dusk_turn_a1]" in graph
    assert "xfade=transition=fade:duration=2.200:offset=2.096" in graph
    # duration lock: 4.296 + 3.504 - 2.2 == 5.6, so movement 2 stays 66.400
    assert movement["duration"] == pytest.approx(66.4)


def test_even_division_remains_the_default(movements, thread):
    """Movements 3 and 4 author no turn_at: their legs are still divided
    evenly, byte for byte."""
    movement = _movement(movements, "perfume-3")
    graph = build_interludes.video_chain(thread, movement,
                                         movement["replacements"])
    # ghost-singer: dur 3.2, turn 0.5, two arts -> legs 1.850, offset 1.350.
    assert "trim=0:1.850,setpts=PTS-STARTPTS[ghost_singer_a0]" in graph
    assert "xfade=transition=fade:duration=0.500:offset=1.350" in graph


def test_turn_at_out_of_range_is_a_record_bug_not_a_render(thread):
    movement = _movement(thread["movements"], "perfume-2")
    bad = dict(movement["replacements"][0])
    bad["turn_at"] = 5.9  # past dur: the night leg would be negative
    with pytest.raises(SystemExit):
        build_interludes.video_chain(thread, movement, [bad])


def test_the_flash_sits_on_the_measured_onset_in_the_owners_window(movements):
    """4:21 +/- the stamp tolerance is source 142.983 -> 143.483; the best
    measured onset inside it is 143.216 (replacement-relative 4.296). The
    record's honesty stands: it is 23% of the shot's strongest onset."""
    movement = _movement(movements, "perfume-2")
    flash = movement["replacements"][0]["flash"]
    assert flash["art"] == "roar"
    assert flash["at"] == pytest.approx(4.296)
    source_at = movement["in"] + movement["replacements"][0]["at"] \
        + flash["at"]
    assert 142.983 <= source_at <= 143.483
    assert flash["at"] + flash["dur"] <= movement["replacements"][0]["dur"]


# --- the frame must never change shape, 2026-08-17 -------------------------
#
# Owner on the derivative, at file-local 38.5: the summit photograph filled
# the whole 1920x1080 frame for its two seconds -- "the picture changes
# SHAPE ... that reads as a mistake rather than a cut to a photograph". The
# plate is exactly 1920x1080, so the default fit had no remainder. The fix
# is an authored rung, "fit": "scope", and these pins make the class of bug
# -- any asset that happens to be exactly 16:9 silently filling the frame --
# a test failure instead of a screening note.


def test_the_summit_photo_sits_in_the_scope_window(movements, thread):
    """fit "scope": fill 1920x804 on the asset's own aspect, crop the
    overflow, and let the shared pad seat it at the film's own 138 px bars
    -- letterboxed exactly like the artwork around it."""
    movement = _movement(movements, "perfume-4")
    summit = next(r for r in movement["replacements"]
                  if r["id"] == "contributor-summit")
    assert summit["fit"] == "scope"
    graph = build_interludes.video_chain(thread, movement,
                                         movement["replacements"])
    assert ("scale=1920:804:force_original_aspect_ratio=increase:"
            "flags=lanczos,crop=1920:804,pad=1920:1080") in graph


def test_a_full_frame_asset_cannot_be_used_without_an_authored_fit(movements):
    """The summit plates are 1920x1080 BY CONSTRUCTION -- the one asset
    class in this repo whose native aspect fills the delivery frame exactly.
    Naming one in a replacement without authoring "fit" is the bug the
    owner caught; the record must carry the decision."""
    for movement in movements:
        for repl in movement.get("replacements", []):
            names = list(repl["art"])
            if repl.get("flash"):
                names.append(repl["flash"]["art"])
            for name in names:
                is_summit = (isinstance(name, dict)
                             and "summit-plates" in name["file"])
                if is_summit:
                    assert repl.get("fit") == "scope", (
                        f"{repl['id']}: a 1920x1080 plate would fill the "
                        "frame -- author 'fit' (see scope_fit)")


def test_the_drawings_keep_the_never_cropped_default(movements, thread):
    """The scope rung changes nothing for the wallpapers: no crop, the
    decrease fit, the shared pad -- byte for byte, per replacement chain."""
    import re
    for movement_id in ("perfume-2", "perfume-3", "perfume-4"):
        movement = _movement(movements, movement_id)
        graph = build_interludes.video_chain(thread, movement,
                                             movement["replacements"])
        for repl in movement.get("replacements", []):
            if repl.get("fit"):
                continue
            label = f"{repl['id']}_a0".replace("-", "_")
            match = re.search(r"\[\d+:v\]([^;]*?)\[" + re.escape(label)
                              + r"\]", graph)
            assert match, repl["id"]
            chain = match.group(1)
            assert "scale=1920:1080:force_original_aspect_ratio=decrease" \
                in chain, repl["id"]
            assert "crop=" not in chain, repl["id"]
