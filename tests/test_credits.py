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

def test_the_reveal_lands_where_the_owner_asked(manifest):
    """':22 is when I want the comic book shot'.

    22.080 rather than a flat 22.000: a measured +5.01 dB onset sits there, so
    the cut lands on a hit instead of mid-bar. Under three frames from the
    time that was named, which is the point -- honour the instruction, then
    land it on the music.
    """
    at = B.reveal_at(manifest["bed"], manifest["reveal"])
    assert at == pytest.approx(22.08, abs=0.001)
    assert abs(at - 22.0) < 0.1, "the owner said :22; do not drift off it"


def test_the_reveal_accounts_for_the_crossfade():
    """The regression. Without the overlap the anchor is 0.25 s late."""
    bed = {"segments": [{"start_sec": 100.0, "end_sec": 150.0},
                        {"start_sec": 0.0, "end_sec": 60.0}],
           "crossfade_sec": 0.25}
    at = B.reveal_at(bed, {"segment": 1, "source_sec": 9.0})
    assert at == pytest.approx(50.0 - 0.25 + 9.0)


def test_the_musical_anchor_is_kept_as_the_fallback(manifest):
    """``at_sec`` wins, but segment+source_sec stays recorded.

    It is the reason the loop exists at all -- the song's opening crescendo --
    and it is what the reveal falls back to if the explicit time is removed.
    """
    assert manifest["reveal"]["segment"] == 1
    assert manifest["reveal"]["source_sec"] == 9.08
    without = {k: v for k, v in manifest["reveal"].items() if k != "at_sec"}
    assert B.reveal_at(manifest["bed"], without) == pytest.approx(56.19, abs=0.01)


def test_an_explicit_time_is_taken_literally():
    """A time named in the finished cut is a statement about the FILM, so no
    crossfade arithmetic is applied to it."""
    bed = {"segments": [{"start_sec": 100.0, "end_sec": 150.0},
                        {"start_sec": 0.0, "end_sec": 60.0}], "crossfade_sec": 0.25}
    assert B.reveal_at(bed, {"at_sec": 22.08, "segment": 1, "source_sec": 9.0}) == 22.08


def test_the_whole_cast_follows_the_cover(manifest):
    """'put the cast after' -- the reveal introduces the people."""
    items, _ = B.schedule(manifest)
    cover = next(i for i in items if i["kind"] == "cover")
    for item in items:
        if item["kind"] == "cast":
            assert item["t"] >= cover["t"] + cover["dur"] - 0.001


def test_the_fixed_cards_give_way_to_the_anchor(manifest):
    """Their dur_sec are relative weights: the cards fit the owner's time,
    not the other way round."""
    items, _ = B.schedule(manifest)
    roles = [i for i in items if i["kind"] == "role"]
    assert roles[0]["t"] == 0
    end = roles[-1]["t"] + roles[-1]["dur"]
    assert end == pytest.approx(B.reveal_at(manifest["bed"], manifest["reveal"]), abs=0.001)


# --- what is on screen -----------------------------------------------------

def test_the_bluefin_creators_open_the_credits(manifest):
    """The owner gave up the opening slot: 'Put jorge castro before
    contributions by you so the bluefin creators get credit.'

    The first card after the drum smash is the strongest in the sequence, and
    it goes to the people who created Bluefin. Do not 'fix' this back on the
    assumption that the director leads.
    """
    assert manifest["fixed_cards"][0]["role"] == "Bluefin Created by"
    assert manifest["fixed_cards"][0]["names"] == ["Jacob Schnurr", "Andy Frazer"]


def test_the_director_is_credited_immediately_before_the_audience(manifest):
    roles = [c["role"] for c in manifest["fixed_cards"]]
    assert roles.index("Directed by") == roles.index("Contributions by") - 1


def test_the_fixed_cards_are_in_the_owners_order(manifest):
    assert [c["role"] for c in manifest["fixed_cards"]] == [
        "Bluefin Created by", "Music by", "Directed by", "Contributions by"]


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


# --- capitalization, faces, and the wordmark -------------------------------

def test_nothing_on_screen_is_uppercased(manifest):
    """Capitalization is copy. 'Bazzite' is the project's name; 'BAZZITE' is a
    different word, and a GitHub login's case is chosen by its owner."""
    source = (REPO_ROOT / "tools" / "credits.py").read_text()
    assert ".upper()" not in source, \
        "a card is forcing case; print names as they are written"


def test_section_headings_keep_their_authored_case(manifest):
    assert [s["section"] for s in manifest["contributors"]] == [
        "Project Bluefin", "Aurora", "Bazzite", "Universal Blue"]


def test_a_cast_face_is_never_guessed(manifest):
    """Rule 3, and the vocab's own warning: github.com/nimbatus is NOT Laura
    Santamaria. A placard shows a face only from an authored card or a
    VERIFIED login -- never from a login inferred off a person's name."""
    verified = {k for k in (manifest.get("cast_logins") or {}) if not k.startswith("_")}
    for member in manifest["cast"]:
        if member.get("login"):
            assert member["login"] in {"nimbinatus"} or member["person"] in verified


def test_kat_is_credited_from_her_authored_card_not_a_lookalike_login(manifest):
    """github.com/kat is named only 'Kat' and is not confirmed to be Kat
    Cosgrove -- the nimbatus trap exactly. She has an authored card instead."""
    kat = next(c for c in manifest["cast"] if c["person"] == "Kat Cosgrove")
    assert kat.get("card") == "kat"
    assert kat.get("login") is None


def test_the_authored_cards_are_used_where_they_exist(manifest):
    cards = {c["person"]: c.get("card") for c in manifest["cast"]}
    assert cards["Bob Killen"] == "bob"
    assert cards["Laura Santamaria"] == "laura"


def test_verified_logins_survive_a_contributor_refresh(manifest):
    """cast_logins is hand-maintained; the schedule applies it every time, so
    a login added after the cast was generated still reaches its placard."""
    items, _ = B.schedule(manifest)
    jorge = next(i for i in items if i.get("person") == "Jorge Castro")
    assert jorge["login"] == "castrojo"


def test_the_wordmark_is_the_real_mark_not_typeset(manifest):
    """A brand mark set in the deck's mono is an invented mark."""
    assert manifest["wordmark"]["source"].startswith("ublue-os/universal-blue-org")


def test_the_wordmark_source_is_recorded_because_artwork_does_not_have_it(manifest):
    """Recorded so nobody re-derives it: ublue-os/artwork is wallpapers only."""
    assert "artwork" not in manifest["wordmark"]["source"]


def test_every_cast_placard_gets_a_readable_hold(manifest):
    """15 placards squeezed before the reveal gave each 2.15 s, which is not
    long enough to look at somebody's Guardian card. They straddle it now."""
    items, _ = B.schedule(manifest)
    for item in items:
        if item["kind"] == "cast":
            assert item["dur"] >= 3.5


def test_the_cast_order_survives_the_split(manifest):
    """The cast is split around the reveal; it must stay a prefix/suffix cut."""
    items, _ = B.schedule(manifest)
    on_screen = [i["person"] for i in items if i["kind"] == "cast"]
    assert on_screen == [c["person"] for c in manifest["cast"]]
