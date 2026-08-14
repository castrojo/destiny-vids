"""Act VIII -- the credits: the bed's arithmetic, and what is on screen.

Offline and dependency-free like the rest of the suite: no ffmpeg, no media, no
network. What is pinned here is the arithmetic and the copy, not pixels.

The bug this file exists to catch already happened once. The reveal was a
hand-written credits-clock number (56.440) and the render put the comic cover
0.26 s -- eight frames -- past the transient it is supposed to hit, because
``acrossfade`` overlaps its inputs and nobody subtracted the overlap. The
anchor is now derived, and these tests hold it there.
"""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_credits as B  # noqa: E402
from tools import credits as C  # noqa: E402

MANIFEST = REPO_ROOT / "stories" / "08-credits.json"


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text())


# --- the bed ---------------------------------------------------------------

def test_the_bed_starts_on_the_measured_drum_smash(manifest):
    """193.420 is the measured re-entry (+12.98 dB), not a round number."""
    assert manifest["bed"]["segments"][0]["start_sec"] == 193.42


def test_the_bed_never_plays_the_breakdown(manifest):
    """The 'moaning' section (181.320 -> 193.420) is in no span.

    Span B stops at it and span A starts after it, so the 12.10 s the owner
    asked to cut cannot be reached from either end.
    """
    for span in manifest["bed"]["segments"]:
        start, end = span["start_sec"], span["end_sec"]
        assert not (start < 193.42 and end > 181.32), \
            f"span {start}-{end} overlaps the breakdown"


def test_the_bed_stops_before_the_digital_silence(manifest):
    """The file has ~4.4 s of digital silence after 240.780.

    Ending span A on the file's length instead would put the loop seam inside
    it -- which is issue #105, the thing every act join already gets wrong.
    """
    assert manifest["bed"]["segments"][0]["end_sec"] == 240.78
    assert manifest["bed"]["segments"][0]["end_sec"] < 245.211


def test_the_loop_returns_to_the_top_of_the_song(manifest):
    """'people miss that part of the song' -- span B starts at 0."""
    assert manifest["bed"]["segments"][1]["start_sec"] == 0.0


def test_bed_total_subtracts_the_crossfade_overlap():
    bed = {"segments": [{"start_sec": 0, "end_sec": 10},
                        {"start_sec": 0, "end_sec": 20}],
           "crossfade_sec": 0.25}
    assert B.bed_total(bed) == pytest.approx(29.75)


def test_bed_total_is_a_plain_sum_without_a_crossfade():
    bed = {"segments": [{"start_sec": 0, "end_sec": 10},
                        {"start_sec": 0, "end_sec": 20}], "crossfade_sec": 0}
    assert B.bed_total(bed) == pytest.approx(30.0)


# --- the reveal ------------------------------------------------------------

def test_the_reveal_lands_on_the_measured_crescendo(manifest):
    """9.080 s into span B, which is a +10.53 dB onset in the source.

    The rendered file was measured back: the biggest onset in the window is at
    56.180 s and the cover drops at 56.190 s -- 0.3 of a frame.
    """
    at = B.reveal_at(manifest["bed"], manifest["reveal"])
    assert at == pytest.approx(56.19, abs=0.01)


def test_the_reveal_accounts_for_the_crossfade():
    """The regression. Without the overlap the anchor is 0.25 s late."""
    bed = {"segments": [{"start_sec": 100.0, "end_sec": 150.0},
                        {"start_sec": 0.0, "end_sec": 60.0}],
           "crossfade_sec": 0.25}
    at = B.reveal_at(bed, {"segment": 1, "source_sec": 9.0})
    assert at == pytest.approx(50.0 - 0.25 + 9.0)


def test_the_reveal_is_pinned_to_the_source_not_the_clock(manifest):
    """Stored as segment+source_sec so a re-cut bed moves it automatically."""
    assert "at_sec" not in manifest["reveal"]
    assert manifest["reveal"]["segment"] == 1
    assert manifest["reveal"]["source_sec"] == 9.08


# --- what is on screen -----------------------------------------------------

def test_the_first_card_after_the_drums_is_directed_by(manifest):
    """The owner's revised running order starts here."""
    assert manifest["fixed_cards"][0]["role"] == "Directed by"
    assert manifest["fixed_cards"][0]["names"] == ["Jorge O. Castro"]


def test_the_fixed_cards_are_in_the_owners_order(manifest):
    assert [c["role"] for c in manifest["fixed_cards"]] == [
        "Directed by", "Bluefin Created by", "Music by", "Contributions by"]


def test_the_band_is_spelled_as_the_bed_record_spells_it(manifest):
    """The session note says 'Nightwise'; a band's name is copy, not a typo
    to pass through."""
    music = next(c for c in manifest["fixed_cards"] if c["role"] == "Music by")
    bed = json.loads((REPO_ROOT / "music" / "bed_wish_i_had_an_angel.json").read_text())
    assert music["names"] == [bed["artist"]] == ["Nightwish"]


def test_only_the_last_contributor_section_is_deduped(manifest):
    """'all the contributors to ever contribute to aurora' means all of them.

    Somebody who worked on both Bluefin and Aurora is credited under both.
    Only Universal Blue is 'deduped from above'.
    """
    sections = {s["section"]: {n.lower() for n in s["names"]}
                for s in manifest["contributors"]}
    assert sections["Project Bluefin"] & sections["Aurora"], \
        "Aurora was deduped against Bluefin; it should not be"
    earlier = (sections["Project Bluefin"] | sections["Aurora"]
               | sections["Bazzite"])
    assert not (sections["Universal Blue"] & earlier), \
        "Universal Blue must be deduped from the three above it"


def test_the_credits_name_the_human_not_the_login(manifest):
    """A credit names a real person. plate.name is what their own nameplate
    says; display_name is sometimes a login and sometimes the character."""
    by_character = {c["character_id"]: c for c in manifest["cast"]}
    assert by_character["cayde_6"]["person"] == "Jorge Castro"
    assert by_character["osiris"]["person"] == "Bob Killen"
    assert by_character["saint_14"]["person"] == "Kat Cosgrove"


def test_one_person_playing_two_roles_is_named_the_same_both_times(manifest):
    """Laura Santamaria is Elsie Bray AND Nimbatus; the nimbatus entry has no
    plate, so a naive fallback credited her as 'Nimbatus as Nimbatus'."""
    by_character = {c["character_id"]: c for c in manifest["cast"]}
    assert by_character["nimbatus"]["person"] == "Laura Santamaria"
    assert by_character["elsie_bray"]["person"] == "Laura Santamaria"


@pytest.mark.parametrize("raw,expected", [
    ("cayde_6", "Cayde-6"),
    ("saint_14", "Saint-14"),
    ("mara_sov", "Mara Sov"),
    ("the_speaker", "The Speaker"),
])
def test_character_names_print_as_destiny_writes_them(raw, expected):
    assert B.character_name(raw) == expected


def test_every_cast_member_is_bound_to_a_real_person(manifest):
    """Rule 3: a placard is a claim about somebody. An unbound lead is
    omitted, never guessed."""
    for member in manifest["cast"]:
        assert member["person"] and member["character"]


# --- the schedule ----------------------------------------------------------

def test_the_schedule_fills_the_bed_exactly(manifest):
    items, total = B.schedule(manifest)
    assert total == pytest.approx(B.bed_total(manifest["bed"]))
    end = items[-1]["t"] + items[-1]["dur"]
    assert end == pytest.approx(total, abs=0.001), "the last card must end with the music"


def test_the_schedule_has_no_gap_or_overlap(manifest):
    items, _ = B.schedule(manifest)
    for a, b in zip(items, items[1:]):
        assert a["t"] + a["dur"] == pytest.approx(b["t"], abs=0.001)


def test_the_cover_is_scheduled_on_the_anchor(manifest):
    items, _ = B.schedule(manifest)
    cover = next(i for i in items if i["kind"] == "cover")
    assert cover["t"] == pytest.approx(B.reveal_at(manifest["bed"], manifest["reveal"]))


def test_every_contributor_reaches_the_screen(manifest):
    """454 names are credited; a paginator that drops the tail of a section
    would silently uncredit somebody."""
    items, _ = B.schedule(manifest)
    on_screen = [n for i in items if i["kind"] == "wall" for n in i["names"]]
    expected = [n for s in manifest["contributors"] for n in s["names"]]
    assert on_screen == expected


def test_the_film_ends_on_the_wordmark(manifest):
    items, _ = B.schedule(manifest)
    assert items[-1]["kind"] == "wordmark"
    assert items[-1]["text"] == "Bluefin"


# --- the cards themselves --------------------------------------------------

def test_paginate_keeps_every_name_and_never_pads():
    pages = C.paginate(list(range(50)), 48)
    assert [len(p) for p in pages] == [48, 2]
    assert [n for p in pages for n in p] == list(range(50))


def test_paginate_of_nothing_is_one_empty_page():
    assert C.paginate([], 48) == [[]]


def test_bs_are_set_in_the_films_blue():
    """The owner's instruction, and it must be the film's existing accent --
    a second blue would read as a mistake beside acts I-VII."""
    from tools.plate import VARIANTS
    assert C.ACCENT == VARIANTS["default"]["accent"]


def test_a_wall_paints_its_bs_blue_and_the_rest_pale():
    img = C.render_name_wall("Project Bluefin", ["bbbbbb"], 1, 1)
    colours = {p[:3] for p in img.convert("RGBA").getdata() if p[3] > 200}
    assert C.ACCENT[:3] in colours


def test_the_cards_are_frame_sized():
    assert C.render_wordmark().size == (C.W, C.H) == (1920, 1080)
    assert C.render_role_card("Directed by", ["Jorge O. Castro"]).size == (C.W, C.H)
    assert C.render_cast_placard("Bob Killen", "Osiris").size == (C.W, C.H)
