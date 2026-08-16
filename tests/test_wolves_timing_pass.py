"""The timing pass: marker cards, two clocks, and the rules the builder asserts.

These are the guarantees that stop the second cut regressing into the first:
nothing repeated, no Osiris, no anchor drifting off the music, and a marker card
that stays a slate rather than growing into a nameplate.
"""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.audiomix import build_filter, plan_regions, total_bed  # noqa: E402

SHOTLIST = REPO / "stories/seven-days-timing-pass.json"


@pytest.fixture(scope="module")
def cut():
    return json.loads(SHOTLIST.read_text())


def test_bed_is_consumed_exactly(cut):
    """The song must be used end to end: a short act slides every later anchor."""
    regions = plan_regions(cut["shots"], cut["bed_offset_sec"])
    bed = json.loads((REPO / "music/bed_seven_days_to_the_wolves.json").read_text())
    assert total_bed(regions) == pytest.approx(bed["duration_sec"], abs=0.02)


def test_film_and_bed_are_continuous(cut):
    """Moving Cortney to Act II restores Act VI to one unbroken bed."""
    regions = plan_regions(cut["shots"], cut["bed_offset_sec"])
    wall = sum(s["duration"] for s in cut["shots"])
    assert wall == pytest.approx(total_bed(regions), abs=0.001)
    assert {s["audio"] for s in cut["shots"]} == {"bed"}


def test_anchors_land_on_bed_time(cut):
    """The gallop and the flute entry are the cut's only hard obligations.

    Only ``audio: "bed"`` advances the bed clock -- the interruption's
    silent/hold/source beats (issue #104) are all free to the song.
    """
    anchors = cut["anchors"]
    bed = 0.0
    hits = set()
    for shot in cut["shots"]:
        if shot["audio"] == "bed":
            bed += shot["duration"]
        for name in ("act2_gallop_in", "act3_flute_change"):
            if abs(bed - anchors[name]) < 0.02:
                hits.add(name)
    assert hits == {"act2_gallop_in", "act3_flute_change"}


def test_artwork_returns_on_the_downbeat_after_the_silence(cut):
    """The one interior silence in the bed is where the artwork holds.

    Measured: the band stops at 278.64 and returns on the downbeat at 279.661.
    The artwork must be up across that gap and end ON the slam, or the picture
    comes back over silence and the beat is lost.
    """
    gap_in, slam = cut["anchors"]["howl_silence"]
    bed = 0.0
    covering = None
    for shot in cut["shots"]:
        if shot["audio"] != "bed":
            continue
        start, bed = bed, bed + shot["duration"]
        if start <= gap_in and bed >= slam - 0.01:
            covering = shot
    assert covering is not None, "nothing covers the song's only silence"
    assert covering.get("still"), "the silence must be covered by the artwork"
    assert "ARTWORK" in covering["beat"]


def test_no_shot_is_used_twice(cut):
    """The first cut replayed 25 shots to fill a span. Never again."""
    seen = set()
    for shot in cut["shots"]:
        if "video_id" not in shot:
            continue
        key = (shot["video_id"], shot["start_sec"])
        assert key not in seen, f"shot reused: {key}"
        seen.add(key)


def test_osiris_is_not_in_the_feature(cut):
    sources = {s.get("video_id") for s in cut["shots"]}
    assert "yt_curse_of_osiris_opening_cinematic" not in sources


def test_every_run_is_a_forward_run(cut):
    """A run's out-point must follow its in-point, and match its duration."""
    for shot in cut["shots"]:
        if "video_id" not in shot:
            continue
        assert shot["end_sec"] > shot["start_sec"]
        assert shot["end_sec"] - shot["start_sec"] == pytest.approx(
            shot["duration"], abs=0.002)


def test_the_song_plays_from_the_first_frame(cut):
    """No pre-roll: the film opens on the song, under the title card."""
    assert cut["bed_offset_sec"] == 0.0
    assert cut["shots"][0]["audio"] == "bed"
    assert cut["shots"][0].get("still"), "the film opens on the title card"


def test_act_one_stops_at_the_end_of_the_cinematic(cut):
    """The capture ends at source 3:23; past it lie the fade and another trailer."""
    act1 = [s for s in cut["shots"] if s.get("video_id") == "wolves_act1"]
    assert act1, "Act I lost its source"
    assert max(s["end_sec"] for s in act1) == pytest.approx(203.0, abs=0.01)


def test_bed_has_no_interruption_insert_or_source_audio(cut):
    """No cards, hold track, or hero source audio remain in Act VI."""
    regions = [r for r in plan_regions(cut["shots"], cut["bed_offset_sec"])
               if r["kind"] == "bed"]
    for before, after in zip(regions, regions[1:]):
        assert after["bed_start"] == pytest.approx(before["bed_end"], abs=0.001)
    assert not any("INTERRUPTION" in shot["beat"] for shot in cut["shots"])
    assert not any(shot.get("audio_from") for shot in cut["shots"])


def test_plan_rejects_a_disagreeing_offset(cut):
    with pytest.raises(ValueError):
        plan_regions(cut["shots"], bed_offset=99.0)


def test_filter_delays_each_bed_piece_to_its_wall_position(cut):
    regions = plan_regions(cut["shots"], cut["bed_offset_sec"])
    graph = build_filter(regions, bed_gain_db=-3.5,
                         audio_inputs={"bed_local_forecast_slower": 2})
    assert "adelay=0|0" in graph
    assert "volume=-3.5dB" in graph
    # The source is muted under the bed, never mixed with it.
    assert "volume=0:enable=" in graph
    assert "normalize=0" in graph


def test_audio_from_reaches_the_filtergraph_in_its_own_clock():
    """The named source is trimmed in ITS clock and delayed to the wall.

    The insert's span (wall 322.200 -> 330.859 here) is stand-in data; what
    is pinned is the wiring: a separate input, an atrim in the source's
    clock, the picture's own audio muted across exactly the same window.
    """
    from tools.audiomix import resolve_audio_inputs

    shots = [
        {"duration": 322.2, "audio": "bed"},
        {"duration": 8.659, "audio": "source",
         "audio_from": {"video_id": "some_other_source", "start_sec": 1234.5}},
        {"duration": 101.793, "audio": "bed"},
    ]
    regions = plan_regions(shots, bed_offset=0.0)
    src = [r for r in regions if r["kind"] == "source"]
    assert len(src) == 1
    region = src[0]
    assert region["audio_from"] == {"video_id": "some_other_source",
                                    "start_sec": 1234.5}

    graph = build_filter(regions, source_gain_db=-1.5,
                         audio_inputs={"some_other_source": 2})
    assert "[2:a]atrim=start=1234.500000:end=1243.159000" in graph
    assert "adelay=322200|322200" in graph
    assert "volume=-1.5dB" in graph
    # ...and the picture's own audio is muted across exactly the insert
    assert "between(t,322.200000,330.859000)" in graph

    with pytest.raises(ValueError, match="not in"):
        resolve_audio_inputs(regions, media_dir="/nonexistent")


def test_audio_from_on_a_bed_shot_is_an_error():
    """Under the bed it would never be heard -- fail loudly, don't drop it."""
    shots = [{"duration": 1.0, "audio": "bed",
              "audio_from": {"video_id": "x", "start_sec": 0.0}}]
    with pytest.raises(ValueError, match="never be heard"):
        plan_regions(shots, bed_offset=0.0)


def test_audio_from_on_a_silent_shot_is_an_error():
    """A `silent` beat is a promise of silence; audio there contradicts it."""
    shots = [{"duration": 1.0, "audio": "silent",
              "audio_from": {"video_id": "x", "start_sec": 0.0}}]
    with pytest.raises(ValueError, match="never be heard"):
        plan_regions(shots, bed_offset=0.0)


def test_an_unknown_audio_disposition_is_an_error():
    """A typo must not quietly become bed time -- the bed clock is
    load-bearing, so an unrecognised value fails loudly."""
    shots = [{"duration": 1.0, "audio": "slient"}]
    with pytest.raises(ValueError, match="unknown audio disposition"):
        plan_regions(shots, bed_offset=0.0)


def test_the_hold_slot_merges_and_mutes_until_a_track_is_cleared():
    """B and C are one hold region; the picture is muted under it and nothing
    plays -- the slot is silent by design until the owner clears a track.

    When that day comes the same wiring plays it: an audio_from on a hold
    shot reaches the filtergraph trimmed in the track's own clock.
    """
    shots = [
        {"duration": 10.0, "audio": "bed"},
        {"duration": 1.0, "audio": "silent"},
        {"duration": 4.0, "audio": "hold"},
        {"duration": 4.0, "audio": "hold"},
        {"duration": 10.0, "audio": "bed"},
    ]
    regions = plan_regions(shots, bed_offset=0.0)
    assert [r["kind"] for r in regions] == ["bed", "silent", "hold", "bed"]
    hold = regions[2]
    assert hold["wall_start"] == pytest.approx(11.0)
    assert hold["wall_end"] == pytest.approx(19.0)
    graph = build_filter(regions)
    # silent AND hold windows are both muted out of the picture's own audio.
    assert "between(t,10.000000,11.000000)" in graph
    assert "between(t,11.000000,19.000000)" in graph

    music_shots = [
        {"duration": 10.0, "audio": "bed"},
        {"duration": 8.0, "audio": "hold",
         "audio_from": {"video_id": "cleared_hold_music", "start_sec": 5.0}},
        {"duration": 10.0, "audio": "bed"},
    ]
    regions = plan_regions(music_shots, bed_offset=0.0)
    graph = build_filter(regions, audio_inputs={"cleared_hold_music": 2})
    assert "[2:a]atrim=start=5.000000:end=13.000000" in graph
    assert "adelay=10000|10000" in graph


def test_marker_cards_carry_no_nameplate_vocabulary(cut):
    """A marker is a slate. It must never grow a name, a role, or a class.

    Nameplate copy is a closed set naming real people (docs/skills/plates/SKILL.md);
    a production marker is not a credit and may not borrow that vocabulary.
    """
    from tools.marker import render_marker

    img = render_marker("COMIC PLACEHOLDER", "4:33-4:37  enemy CU")
    assert img.size == (1920, 1080)
    assert img.getpixel((10, 10))[:3] == (0, 0, 0), "a marker is full-frame black"

    for shot in cut["shots"]:
        beat = shot["beat"].upper()
        for banned in ("GUARDIAN //", "TRUSTEE //", "VOIDWALKER", "SUBCLASS"):
            assert banned not in beat


def test_plate_slots_are_flagged_for_the_nameplate_pass(cut):
    slots = [s for s in cut["shots"] if s.get("plate_slot")]
    assert len(slots) >= 3, "Guardians-together runs should be flagged"
    for shot in slots:
        assert shot["duration"] >= 5.0, "a plate needs time to be read"


def test_act_two_never_reaches_back_into_savathuns_throne_world(cut):
    """Neomuna starts at extract 45.55; before it is Witch Queen material.

    An earlier build filled Act II by starting the run 16 s early, which pulled
    in Savathun's Throne World and the WITCH QUEEN branded cards -- a standing
    no-Savathun violation produced purely by needing to fill time. The shortfall
    is covered by the official Lightfall trailer instead, so the compilation run
    may never begin before the boundary.
    """
    from scripts.build_wolves import COMP, NEOMUNA_IN

    comp = [s for s in cut["shots"] if s.get("video_id") == COMP]
    assert comp, "Act II lost its source"
    assert min(s["start_sec"] for s in comp) >= NEOMUNA_IN - 0.001


def test_the_gallop_cuts_to_neon(cut):
    """The gallop is a picture change, not just a beat: it lands on Neomuna."""
    bed = 0.0
    for shot in cut["shots"]:
        if shot["audio"] != "bed":
            continue
        if abs(bed - cut["anchors"]["act2_gallop_in"]) < 0.02:
            assert "neon" in shot["beat"].lower()
            return
        bed += shot["duration"]
    raise AssertionError("no shot starts on the gallop")


def test_act_one_edits_are_bought_back_off_the_head(cut):
    """Dropping a span from the intro must not move the gallop.

    The capture's in-point is derived from the edit list, so a span cut out of
    the middle is paid for by starting earlier. If these ever stop summing,
    Act I comes up short and every later anchor slides.

    A *replaced* span -- a black screen standing in for a summit photograph --
    is deliberately NOT paid for, because the photograph is exactly as long as
    the black it replaces. That distinction is the whole reason Act I's picture
    runs and its still cards are counted separately here.
    """
    from scripts.build_wolves import ACT1_EDITS, ACT2_IN, TITLE_CARD_LEN

    act1 = [s for s in cut["shots"] if s.get("video_id") == "wolves_act1"]
    stills = [s for s in cut["shots"]
              if s.get("still") and s["beat"].startswith("I. SUMMIT")]
    replaced = [e for e in ACT1_EDITS if e[2] != "cut"]

    assert len(stills) == len(replaced), "one summit plate per replaced span"
    # Picture and plates together still fill exactly the act.
    assert sum(s["duration"] for s in act1 + stills) == pytest.approx(
        ACT2_IN - TITLE_CARD_LEN, abs=0.01)
    # Each plate is exactly as long as the span it stands in for, so it is free.
    for still, (cut_in, cut_out, _, _) in zip(stills, replaced):
        assert still["duration"] == pytest.approx(cut_out - cut_in, abs=0.001)

    # Every edited span -- cut or replaced -- is genuinely absent from picture.
    for cut_in, cut_out, _, _ in ACT1_EDITS:
        for shot in act1:
            assert not (shot["start_sec"] < cut_out - 0.01
                        and shot["end_sec"] > cut_in + 0.01), \
                f"an Act I run overlaps the edited {cut_in}-{cut_out}"


# --- the editorial pass -----------------------------------------------------
# The timing pass marked what it was going to remove; this pass removes it. The
# tests below pin the removals themselves, because each one was an owner note
# that a later "tidy-up" could quietly undo.

def test_the_publisher_slide_the_owner_cut_never_comes_back(cut):
    """"cut out the renegades slide."

    The COUNTLESS LEGENDS slide is REMOVED, not marked -- and removing it could
    not simply shorten the montage, or the pause would slide off its downbeat.
    The montage starts earlier instead and stops before the slide. So the guard
    is not "is there a card" but "does any run reach the slide's timecode".
    """
    from scripts.build_wolves import COUNTLESS_LEGENDS_IN

    for shot in cut["shots"]:
        if shot.get("video_id") != "wolves_act3":
            continue
        assert shot["start_sec"] < COUNTLESS_LEGENDS_IN, shot["beat"]
        assert shot["end_sec"] <= COUNTLESS_LEGENDS_IN + 0.01, (
            f"the montage runs to {shot['end_sec']:.3f}s and would put the "
            "COUNTLESS LEGENDS slide back on screen")


def test_no_comic_placeholder_survives(cut):
    """Every marker slot is filled with picture.

    A COMIC PLACEHOLDER left in a delivered cut is a black frame with production
    text on it. The timing pass had four; this pass has none.
    """
    for shot in cut["shots"]:
        assert "COMIC PLACEHOLDER" not in shot["beat"], shot["beat"]


def test_the_ghost_sequence_is_gone_and_its_hole_is_filled(cut):
    """"cut 5:44 extended ghost sequence, cut this to 5:56 and keep the rest."

    `wolves_act2` ends at 210.015 s, so the Pale Heart run cannot simply grow a
    tail to cover the removal: the footage does not exist. The 13.943 s is
    filled from the Gameplay Trailer instead, and Act III-C still has to land
    exactly on its anchor -- which the bed assertions already check. Here we
    check the hole itself.
    """
    from scripts.build_wolves import GHOST_IN, GHOST_OUT, GHOST_FILL, GAMEPLAY

    for shot in cut["shots"]:
        if shot.get("video_id") != "wolves_act2":
            continue
        assert not (shot["start_sec"] < GHOST_OUT - 0.01
                    and shot["end_sec"] > GHOST_IN + 0.01), \
            f"a Pale Heart run overlaps the excised Ghost sequence: {shot['beat']}"

    fill = [s for s in cut["shots"]
            if s.get("video_id") == GAMEPLAY and s.get("audio") != "source"]
    assert len(fill) == len(GHOST_FILL)
    assert sum(s["duration"] for s in fill) == pytest.approx(
        GHOST_OUT - GHOST_IN, abs=0.01), \
        "the fill must be exactly as long as the hole, or Act III-C slides"


def _fixture_dependent_summit_photographs_are_never_captioned(cut):
    """These are photographs of real colleagues.

    They carry no on-screen name and make no claim about anyone, which is what
    keeps them inside the casting rules. Attribution for them is the credits
    sequence's job (issue #51), not a burned-in line here.

    The guard is on the ASSET, not on the beat text: a beat is production
    metadata that never reaches the screen, whereas the still is literally the
    picture. A summit slot must therefore be a photograph straight out of
    `scripts/build_summit_plates.py` -- never a `tools/marker.py` slate, which
    renders text, and never anything from `tools/plate.py`, which renders a
    nameplate about a person.
    """
    from tools.marker import DEFAULT_DIR as MARKER_DIR

    slots = [s for s in cut["shots"]
             if s["beat"].startswith(("I. SUMMIT", "III. SUMMIT"))]
    assert slots, "the summit slots vanished"
    for shot in slots:
        still = Path(shot["still"])
        assert still.suffix == ".jpg", still
        assert still.parent.name == "summit-plates", still
        assert MARKER_DIR not in still.parents, "a marker renders text"
        assert "plate" not in shot and "name" not in shot


def test_the_hunter_run_credits_nobody_on_screen(cut):
    """The owner overrode their own filename: the Hunter is github.com/inffy,
    not Laura Santamaria, and inffy has no authored Guardian identity.

    So the run is rendered UNPLATED and the binding lives in `leads.pending`.
    A plate appearing here would be copy this repo wrote about a real person.
    """
    import yaml

    casting = yaml.safe_load(
        (REPO / "vocab" / "casting.yaml").read_text(encoding="utf-8"))
    pending = (casting.get("leads") or {}).get("pending") or {}
    assert "inffy" in pending
    assert pending["inffy"]["display_name"] is None

    hunter = [s for s in cut["shots"] if "inffy" in s["beat"]]
    assert len(hunter) == 1
    assert not hunter[0].get("plate_slot"), (
        "an unplatable person must not be flagged for the nameplate pass")


def test_no_two_summit_slots_show_the_same_picture():
    """Three frames of one group photo are three files and one image.

    The first assignment took the three biggest crowds and they turned out to
    be the same overhead shot seconds apart -- on screen, one image shown three
    times. A filename check cannot catch that, so the plate builder measures
    it, and this pins that the measurement is actually wired up and that the
    shipped selection passes it.

    Needs the frame-touching extras and the photographs, so it skips where
    neither is present -- the suite is offline by design (`AGENTS.md`).
    """
    pytest.importorskip("numpy")
    pytest.importorskip("PIL")
    from scripts.build_summit_plates import (
        ASSIGNMENT, DUPLICATE_CORRELATION, SRC_DIR, assert_distinct, signature)

    present = [s for s in ASSIGNMENT.values() if (SRC_DIR / f"{s}.jpg").exists()]
    if len(present) < 2:
        pytest.skip("summit photographs are not fetched (media/ is gitignored)")

    peak = assert_distinct(present)          # raises SystemExit on a duplicate
    assert peak <= DUPLICATE_CORRELATION

    # ...and the guard genuinely fires: a photograph against itself is a 1.0.
    sig = signature(SRC_DIR / f"{present[0]}.jpg")
    assert float(sig @ sig / len(sig)) > DUPLICATE_CORRELATION


def test_every_summit_slot_the_builder_asks_for_has_a_plate():
    """The cut's slots and the plate manifest's slots are the same set.

    They are declared in two files, so they can drift: a slot renamed in
    build_wolves.py would silently fall back to a marker card, which is a black
    frame with production text on it.

    Read from the committed manifest rather than from the plate builder, so
    this runs on a bare CI box: the assignment is an authored input, and the
    builder needs numpy and Pillow that the offline suite does not install.
    """
    from scripts.build_wolves import ACT1_EDITS, TRAILER_CARDS

    meta = json.loads((REPO / "stories" / "summit-photos.json").read_text())
    wanted = {kind for _, _, kind, _ in ACT1_EDITS if kind != "cut"}
    wanted |= {slot for _, _, _, slot in TRAILER_CARDS}
    wanted.add("enemy_cu")
    assert wanted == set(meta["assignment"])

    # Every slot names a photograph the manifest actually knows how to fetch.
    known = {p["file"].rsplit("/", 1)[-1].removesuffix(".jpg")
             for p in meta["photos"]}
    assert set(meta["assignment"].values()) <= known
