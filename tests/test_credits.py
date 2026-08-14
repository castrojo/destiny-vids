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
from PIL import Image, ImageDraw

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


def manifest_grid_beats():
    """The bed record's own tracked beat grid, to a millisecond."""
    bed = json.loads(
        (REPO_ROOT / "music" / "bed_wish_i_had_an_angel.json").read_text())
    return {round(b, 6) for b in bed["grid"]["beats"]}


def test_the_bed_never_plays_the_breakdown(manifest):
    """The 'moaning' section (181.320 -> 193.420) is in no span.

    Span B stops at it and span A starts after it, so the 12.10 s the owner
    asked to cut cannot be reached from either end.
    """
    for span in manifest["bed"]["segments"]:
        start, end = span["start_sec"], span["end_sec"]
        assert not (start < 193.42 and end > 181.32), \
            f"span {start}-{end} overlaps the breakdown"


def test_the_bed_stops_before_the_song_ends(manifest):
    """A loop must not contain an ENDING.

    Owner: ':46 - cut all of this part and go right to the drums so the entire
    song sounds like a loop.' The song's decay starts at 240.08 -- the level
    falls -11 -> -17 dB and keeps falling to digital silence at 241.95 -- and
    the out point used to be 240.780, which is 0.7 s INSIDE it. So the loop
    seam played a fade-out and then the drums, which is the one thing it must
    not do.

    239.653152 is the nearest beat in the bed's own tracked grid to the
    owner's :46 (source 239.420), and it clears the decay by 0.43 s. The
    digital-silence bound (#105) still holds, by a much wider margin.
    """
    end = manifest["bed"]["segments"][0]["end_sec"]
    assert end == 239.653152
    assert end in manifest_grid_beats(), \
        "the out point must be a measured beat, not an eyeballed one"
    assert end < 240.08, "the song's decay must not be in the loop"
    assert end < 245.211


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
    # The fallback MOVES when the bed is re-cut, which is the point of keeping
    # it: span A lost 1.127 s when its ending came off, so the musical anchor
    # is that much earlier on the credits clock.
    span_a = manifest["bed"]["segments"][0]
    expected = ((span_a["end_sec"] - span_a["start_sec"])
                - manifest["bed"]["crossfade_sec"]
                + manifest["reveal"]["source_sec"])
    assert B.reveal_at(manifest["bed"], without) == pytest.approx(expected, abs=0.01)


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


def test_the_call_to_action_gives_way_to_the_anchor(manifest):
    """The CTA cards' dur_sec are relative weights: they fit the owner's time,
    not the other way round.

    Owner, 2026-08-14: "Move the existing credits to after the comic reveal,
    instead let's make this part leading up to it a call to action."
    """
    items, _ = B.schedule(manifest)
    cta = [i for i in items if i["kind"] in ("cta", "birthday")]
    assert cta[0]["t"] == 0
    end = cta[-1]["t"] + cta[-1]["dur"]
    assert end == pytest.approx(B.reveal_at(manifest["bed"], manifest["reveal"]),
                                abs=0.001)


def test_the_call_to_action_is_the_owners_words_in_his_order(manifest):
    cards = manifest["cta_cards"]
    assert [c.get("text") or c["name"] for c in cards] == [
        "WE MAKE OUR OWN FATE", "BECOME LEGEND", "RAFAEL CASTRO", "FIGHT"]
    assert [c["kind"] for c in cards] == ["cta", "cta", "birthday", "cta"]
    # "noticeably larger font" is a step somebody can see, in this order.
    scales = [C.CTA_SCALE[c["scale"]] for c in cards if c["kind"] == "cta"]
    assert scales == sorted(scales) and len(set(scales)) == 3


def test_fight_is_up_longer_than_the_first_two(manifest):
    """Owner: 'FIGHT <--- I want this one up longer than the first 2'."""
    items, _ = B.schedule(manifest)
    cta = [i for i in items if i["kind"] == "cta"]
    fight = next(i for i in cta if i["text"] == "FIGHT")
    first_two = [i for i in cta if i["text"] != "FIGHT"][:2]
    assert fight["dur"] > sum(c["dur"] for c in first_two)


def test_the_reveal_length_was_not_touched(manifest):
    """Owner, in the same breath: '(do not touch the comic book reveal
    length.)' -- so the cover's own hold is what it always was."""
    assert manifest["reveal"]["hold_sec"] == 14.0
    assert manifest["reveal"]["at_sec"] == 22.08


def test_the_credits_follow_the_comic_reveal(manifest):
    """Owner: 'Move the existing credits to after the comic reveal'."""
    items, _ = B.schedule(manifest)
    cover = next(i for i in items if i["kind"] == "cover")
    roles = [i for i in items if i["kind"] == "role"]
    assert roles, "the fixed credits still play"
    assert all(r["t"] >= cover["t"] + cover["dur"] - 0.001 for r in roles)
    # And their dur_sec are seconds now, not weights.
    for item, card in zip(roles, manifest["fixed_cards"]):
        assert item["dur"] == pytest.approx(card["dur_sec"], abs=1e-6)


def test_the_birthday_card_is_the_owners_copy(manifest):
    """The owner's own words, reproduced. Nothing added: no age row, and no
    second name -- the redacted one went with the card that carried it."""
    card = next(c for c in manifest["cta_cards"] if c["kind"] == "birthday")
    assert card["eyebrow"] == "Happy Tenth Birthday"
    assert card["name"] == "RAFAEL CASTRO"
    assert card["body"] == '"We love you" - Mom and Dad'
    assert "names" not in card


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


def test_the_introducing_card_became_the_birthday_card(manifest):
    """Owner, 2026-08-14: 'Change introducing Rafael to Happy Tenth Birthday'.

    The card left the fixed credits entirely -- it is a call-to-action card
    now -- and the fixed credits are the three that remain.
    """
    roles = [c["role"] for c in manifest["fixed_cards"]]
    assert "Introducing" not in roles
    assert roles[-1] == "Directed by"


def test_the_fixed_cards_are_in_the_owners_order(manifest):
    assert [c["role"] for c in manifest["fixed_cards"]] == [
        "Bluefin Created by", "Music by", "Directed by"]


def test_the_second_introduced_name_stays_redacted(manifest):
    """The owner redacted it, and then removed the card it rode on. Either
    way the name is deliberately absent from this repo, which is what a
    redaction is for.

    EVERYTHING THIS REPO WROTE is scanned, and nothing GitHub returned. The
    contributor walls are a frozen API snapshot of other people's LOGINS, and
    the Fedora CoreOS list contains `lakshmiravichandran1` -- a real,
    different person whose login happens to contain the string. Scanning it
    would assert that no contributor may share a substring with a redacted
    name, which is a rule about strangers' usernames, not about the
    redaction.
    """
    authored = {k: v for k, v in manifest.items() if k != "contributors"}
    blob = json.dumps(authored).lower()
    assert "mehta" not in blob and "lakshmi" not in blob and "laskshmi" not in blob, \
        "the redacted name must not survive anywhere in the authored manifest"


def test_the_redaction_treatment_survives_the_card_that_used_it(manifest):
    """`[ REDACTED ]` is AUTHORED COPY, not a placeholder awaiting resolution
    (docs/skills/plates/references/plate-chrome.md). The Introducing card is
    gone, but the cast redactions still use the deck's own form, so the
    convention is still enforced somewhere."""
    assert C.REDACTED == "[ REDACTED ]"
    assert manifest["cast_redactions"]


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
        "Fedora CoreOS", "bootc", "GNOME OS", "KDE Linux",
        "Universal Blue", "Bazzite", "Aurora", "Project Bluefin"]


def test_the_upstream_projects_lead_and_are_marked_as_upstream(manifest):
    """Owner: 'have them top tier in the credits before bluefin'.

    The order is enforced in `schedule`, not left to how the manifest happens
    to be written, so an edit that reorders the file cannot demote them.
    """
    upstream = [s["section"] for s in manifest["contributors"]
                if s.get("tier") == "upstream"]
    assert upstream == ["Fedora CoreOS", "bootc", "GNOME OS", "KDE Linux"]

    items, _ = B.schedule(manifest)
    walls = [i for i in items if i["kind"] == "wall"]
    seen_ublue = False
    for wall in walls:
        if wall.get("tier") == "upstream":
            assert not seen_ublue, \
                f"{wall['section']} plays after a Bluefin-family wall"
        else:
            seen_ublue = True


def test_an_upstream_wall_is_larger_and_holds_longer(manifest):
    """'make theirs larger and more distinguished' -- fewer faces per screen,
    and more time on each screen."""
    assert C.UPSTREAM_PER_WALL < C.NAMES_PER_WALL
    items, _ = B.schedule(manifest)
    walls = [i for i in items if i["kind"] == "wall"]
    up = [w["dur"] for w in walls if w.get("tier") == "upstream"]
    plain = [w["dur"] for w in walls if not w.get("tier")]
    assert min(up) > max(plain)


def test_a_credit_roll_names_people_not_machines(manifest):
    """`type == "User"` does not catch a project's own bot account."""
    logins = {n.lower() for s in manifest["contributors"] for n in s["names"]}
    assert not (logins & {l.lower() for l in B.BOT_LOGINS})


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
    a login added after the cast was generated still reaches its placard.

    Checked on Jeefy rather than Jorge: Jorge's placard is redacted, which
    correctly strips his login before it can reach the card.
    """
    items, _ = B.schedule(manifest)
    jeefy = next(i for i in items if i.get("person") == "Jeefy")
    assert jeefy["login"] == "jeefy"


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


def test_the_cast_plays_in_the_vocabularys_order(manifest):
    """Ordered by the binding, not by whoever happens to have a face.

    Compared on the CHARACTER, because a redacted placard deliberately no
    longer carries its person's name.
    """
    items, _ = B.schedule(manifest)
    on_screen = [i["character"] for i in items if i["kind"] == "cast"]
    assert on_screen == [c["character"] for c in manifest["cast"]]


def test_the_cast_is_the_readmes_table(manifest):
    """Owner: 'ensure this list matches the readme for the characters ...
    remove some of these characters', and separately 'Remove cayde-6 redacted
    from the starring roles, he's fine in the credits with the rest.'

    So the placards are the README's nine rows MINUS Cayde-6: eight. The six
    the vocab binds but the README does not list keep their bindings; only
    act VIII's placards went.
    """
    items, _ = B.schedule(manifest)
    assert len([i for i in items if i["kind"] == "cast"]) == len(manifest["cast"]) == 8

    readme = (REPO_ROOT / "README.md").read_text()
    for member in manifest["cast"]:
        assert member["character"] in readme or member["person"] in readme, \
            f"{member['person']} as {member['character']} is not in the README"


def test_cayde_is_not_in_the_starring_roles(manifest):
    """'he's fine in the credits with the rest' -- his reveal is the Directed
    by card, and castrojo is on three contributor walls."""
    assert not any(c["character_id"] == "cayde_6" for c in manifest["cast"])
    directed = next(c for c in manifest["fixed_cards"]
                    if c["role"] == "Directed by")
    assert directed["names"] == ["Jorge O. Castro"]
    assert any("castrojo" in s["names"] for s in manifest["contributors"])


def test_karenas_surname_carries_one_l(manifest):
    """The README and the owner both say 'Angel'. vocab/casting.yaml still
    says 'Angell' and is frozen (#167), so the credits print the correction
    and it is recorded in `unresolved`."""
    mara = next(c for c in manifest["cast"] if c["character_id"] == "mara_sov")
    assert mara["person"] == "Karena Angel"
    assert any("Angel" in u for u in manifest["unresolved"])


# --- the Cayde redaction ---------------------------------------------------

def test_the_redaction_treatment_is_still_available(manifest):
    """Cayde's placard is gone, but the mechanism that redacted it is not:
    act II still redacts him, and bringing the placard back is one entry in
    `cast_redactions`. Exercised directly rather than through the manifest.
    """
    fake = dict(manifest)
    fake["cast"] = [{"person": "Jorge Castro", "character": "Cayde-6",
                     "character_id": "cayde_6", "card": "bob",
                     "login": "castrojo"}]
    fake["cast_redactions"] = ["cayde_6"]
    items, _ = B.schedule(fake)
    cayde = next(i for i in items if i["kind"] == "cast")
    assert cayde["person"] == "[ REDACTED ]"
    assert cayde["character"] == "Cayde-6"
    assert cayde["login"] is None and cayde["card"] is None


def _retired_caydes_placard_redacts_the_person_not_the_character(manifest):
    """The owner's README: '[Redacted] Cayde-6 ... we only reveal jorge's name
    once.' His one reveal in act VIII is the Directed by card.

    Which half is redacted is not a coin toss: act II's authored treatment
    (scripts/build_efmb_plates.py, CAYDE) carries redacted_speaker
    '[ REDACTED ]' with redacts=<real name> and reveals='cayde_6'. The famous
    character is the known half; the person behind it is the secret.
    """
    items, _ = B.schedule(manifest)
    cayde = next(i for i in items
                 if i["kind"] == "cast" and i["character"] == "Cayde-6")
    assert cayde["person"] == "[ REDACTED ]"
    assert cayde["character"] == "Cayde-6"


def _retired_a_redacted_placard_shows_no_face(manifest):
    """A card that hides the name and shows the avatar has revealed him."""
    items, _ = B.schedule(manifest)
    cayde = next(i for i in items
                 if i["kind"] == "cast" and i["character"] == "Cayde-6")
    assert cayde["login"] is None and cayde["card"] is None


def test_the_renderer_refuses_a_face_beside_a_redacted_name():
    """Belt and braces: even asked directly, the placard drops the art."""
    with_face = C.render_cast_placard(C.REDACTED, "Cayde-6",
                                      card="bob", login="castrojo")
    without = C.render_cast_placard(C.REDACTED, "Cayde-6")
    assert list(with_face.getdata()) == list(without.getdata())


def test_the_director_card_is_still_jorges_one_reveal(manifest):
    """He is named exactly once in the credits.

    The Introducing card used to name him a second time; it became the
    birthday card, which names Rafael and credits nobody as a role.
    """
    named = [c for c in manifest["fixed_cards"]
             if any("Castro" in n for n in c["names"])]
    assert [c["role"] for c in named] == ["Directed by"]


# --- the blue letters ------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("Bob Killen", "Bb"),        # already has blue; the F rule does not apply
    ("Jacob Schnurr", "Bb"),
    ("Project Bluefin", "Bb"),   # 'Bluefin' has an f, but its B wins
    ("Jeefy", "Ff"),             # no B anywhere -> the f lights up
    ("Rafael Castro", "Ff"),
    ("cflewis", "Ff"),
    ("Kat Cosgrove", "Ff"),      # neither letter present: nothing is lit
])
def test_a_name_with_a_b_does_not_also_get_its_fs(text, expected):
    """The owner's rule: F is blue only for a name with no B in it, so
    somebody who already has blue does not get more of it."""
    assert C.blue_letters(text) == expected


def test_the_rule_is_case_insensitive_both_ways():
    assert C.blue_letters("BOB") == "Bb"
    assert C.blue_letters("bob") == "Bb"
    assert C.blue_letters("FRED") == "Ff"
    assert C.blue_letters("fred") == "Ff"


def test_a_name_with_no_b_paints_its_f_blue():
    img = C.render_role_card("Introducing", ["ffff"])
    colours = {p[:3] for p in img.convert("RGBA").getdata() if p[3] > 200}
    assert C.ACCENT[:3] in colours


def test_a_name_with_a_b_leaves_its_f_alone():
    """'bf' must light the b and NOT the f -- the whole point of the rule."""
    from PIL import ImageDraw
    from tools.plate import _font
    lit = C.blue_letters("bf")
    assert "f" not in lit and "b" in lit


# --- Adwaita, the wallpapers, and the wordmark's dropped sub-line ----------

def test_act_viii_is_set_in_adwaita():
    """Owner: 'Change all the fonts to adwaita.'

    Act VIII resolves it HERE and nowhere else. `plate.FONT_CANDIDATES` is
    deliberately DejaVu -- it reproduces the browser that baked the reference
    plates -- and changing it would silently restyle acts I-VII.
    """
    assert "Adwaita" in C.ADWAITA_SANS
    assert all("Adwaita" in p for p in C.ADWAITA_MONO.values())
    from tools import plate
    assert not any("Adwaita" in p
                   for paths in plate.FONT_CANDIDATES.values() for p in paths)


def test_a_weight_is_an_axis_not_a_second_file():
    """Adwaita Sans ships as one variable file; asking for bold must actually
    get bold rather than silently returning the regular face."""
    if not Path(C.ADWAITA_SANS).exists():
        pytest.skip("Adwaita is not installed on this host")
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    regular = probe.textlength("Bluefin", font=C._font("regular", 80))
    bold = probe.textlength("Bluefin", font=C._font("bold", 80))
    assert bold > regular


def test_the_wallpapers_cycle_the_calendar_and_keep_switching():
    """Owner: 'use the dark mode wallpapers, make them go through the entire
    calendar order and keep switching.'

    Consecutive cards get consecutive months, and the cycle wraps rather than
    stopping on December.
    """
    walls = C.wallpapers()
    if not walls:
        pytest.skip("no wallpapers cached; run scripts/fetch_wallpapers.py")
    assert [p.stem for p in walls] == sorted(p.stem for p in walls), \
        "the cycle must run in calendar order"
    n = len(walls)
    picked = [walls[i % n] for i in range(n * 2 + 3)]
    assert picked[0] != picked[1], "consecutive cards must not share a month"
    assert picked[n] == picked[0], "the cycle must wrap"


def test_the_wordmark_no_longer_says_an_ublue_project(manifest):
    """Owner: 'get rid of "an ublue project" on the logo'."""
    assert "sub" not in manifest["wordmark"]
    blob = json.dumps(manifest["wordmark"]["_what"])
    assert "an ublue project" in blob, \
        "the note must still say what was removed, or the next agent restores it"


def test_a_summit_portrait_needs_a_box_somebody_drew(tmp_path):
    """AGENTS.md: a visual judgement about a frame AND a claim about a real
    person. The feed is group photographs, so the crop is the owner's to draw
    and the placard degrades to the verified avatar until it exists.
    """
    assert C.summit_portrait(None, 300) is None
    assert C.summit_portrait({"file": "media/summit/group-001.jpg"}, 300) is None
    photos = manifest_cast_photos()
    assert not [k for k in photos if not k.startswith("_")], \
        "a crop box appeared without an owner drawing it"


def manifest_cast_photos():
    return json.loads(
        (REPO_ROOT / "stories" / "08-credits.json").read_text()
    ).get("cast_photos", {})


def test_the_picture_is_padded_so_it_outlasts_the_music():
    """The regression the megacut's join check found, and nobody's eyes did.

    Act VIII muxed 227.303 s of audio over **222.956 s** of picture: the
    concat demuxer lands short of the durations it is handed, 4.347 s short
    over 38 cards, so four and a half seconds of the wordmark were simply not
    there. Holding the last card longer in `concat.txt` does NOT fix it --
    the shortfall is in the demuxer's output timeline. Cloning the last frame
    AFTER the demuxer does, and `-t` then cuts both streams on one frame.
    """
    source = (REPO_ROOT / "scripts" / "build_credits.py").read_text()
    assert "tpad=stop_mode=clone:stop_duration=" in source
    assert B.CONCAT_TAIL_SEC > 0


# --- the second pass of the bed --------------------------------------------

def test_the_vocal_version_follows_the_whole_instrumental_loop(manifest):
    """Owner: 'switch to the album version with vocals after the entire
    instrumental loops once'.

    'the ENTIRE instrumental' is load-bearing: the loop is not cut short to
    make room for the vocal. Pass one keeps both of its measured spans.
    """
    passes = B.bed_passes(manifest["bed"])
    assert len(passes) == 2
    assert passes[0]["bed_id"] == "bed_wish_i_had_an_angel"
    assert passes[1]["bed_id"] == "bed_wish_i_had_an_angel_album"
    assert len(passes[0]["segments"]) == 2
    assert passes[0]["segments"][0]["start_sec"] == 193.42
    assert passes[1]["segments"][0]["start_sec"] == 0.0


def test_the_album_pass_stops_before_the_file_runs_out(manifest):
    """243.400 is measured -- the recording is at -54 dB by 243 -- so the film
    ends on the song's own ending rather than on digital silence."""
    album = B.bed_passes(manifest["bed"])[1]
    record = json.loads((REPO_ROOT / "music" /
                         "bed_wish_i_had_an_angel_album.json").read_text())
    end = album["segments"][0]["end_sec"]
    assert end < record["duration_sec"]
    assert record["duration_sec"] - end < 1.0


def test_every_span_of_both_passes_reaches_the_filtergraph(manifest):
    """The album version is a SECOND ffmpeg input; binding it to input 1
    would silently play the instrumental twice."""
    graph = B.audio_filter(manifest["bed"], stream=1)
    assert graph.count("atrim") == len(B.bed_spans(manifest["bed"]))
    assert "[1:a]" in graph and "[2:a]" in graph
    # Every seam is crossfaded, including the hand-over between passes.
    assert graph.count("acrossfade") == len(B.bed_spans(manifest["bed"])) - 1
    assert graph.endswith("[aout]")


def test_the_bed_total_pays_for_every_seam(manifest):
    """acrossfade OVERLAPS, so three spans cost two fades, not one."""
    spans = B.bed_spans(manifest["bed"])
    raw = sum(s["end_sec"] - s["start_sec"] for s in spans)
    xf = manifest["bed"]["crossfade_sec"]
    assert B.bed_total(manifest["bed"]) == pytest.approx(
        raw - (len(spans) - 1) * xf, abs=1e-9)


# --- the upstream tier, the badges and the call-outs ------------------------

def test_gnome_os_is_the_project_not_the_whole_org(manifest):
    """Owner: 'Only have GNOME OS since it's such a large org'."""
    gnome = next(s for s in manifest["contributors"]
                 if s["section"] == "GNOME OS")
    assert gnome["repo"] == "GNOME/gnome-build-meta"
    assert gnome["tier"] == "upstream"


def test_the_gitlab_sections_carry_names_and_never_emails(manifest):
    """GitLab answers with a commit author's name AND email. An email is
    somebody's contact detail, not copy, and a credit roll harvested into a
    committed manifest is the wrong place for a few hundred of them."""
    for label in ("GNOME OS", "KDE Linux"):
        section = next(s for s in manifest["contributors"]
                       if s["section"] == label)
        assert section["host"] in ("gitlab.gnome.org", "invent.kde.org")
        assert not any("@" in n for n in section["names"])


def test_the_gitlab_names_are_never_fetched_as_github_logins(manifest, tmp_path):
    """github.com/'Harald Sitter'.png is not a missing avatar, it is a
    category error -- and whatever answered would be a face beside somebody
    else's name."""
    seen = []

    class Recorder:
        def __init__(self, *a, **k):
            seen.append(a[0] if a else k.get("url"))
            raise OSError("no network in tests")

    import urllib.request
    orig = urllib.request.urlopen
    urllib.request.urlopen = Recorder
    orig_dir, C.AVATAR_DIR = C.AVATAR_DIR, tmp_path
    try:
        B.fetch_avatars(manifest, verbose=False)
    finally:
        urllib.request.urlopen = orig
        C.AVATAR_DIR = orig_dir
    gitlab_names = [n for s in manifest["contributors"]
                    if s.get("host") for n in s["names"]]
    assert gitlab_names, "the GitLab sections are populated"
    # EXACT urls, not a substring scan: the GitLab name "Sam" is a substring
    # of the GitHub login "SamD2021", and asserting on substrings would fail
    # on a real, correctly-fetched face.
    asked = {url.rsplit("/", 1)[-1].split(".png")[0] for url in seen if url}
    assert not (asked & set(gitlab_names))


def test_the_named_kde_maintainers_are_on_screen(manifest):
    """Owner: 'put at least aleixpol and harald sitter'. GitLab spellings
    vary between a person's own commits, so 'at least' is enforced."""
    kde = next(s for s in manifest["contributors"]
               if s["section"] == "KDE Linux")
    lowered = [n.lower() for n in kde["names"]]
    assert "aleix pol" in lowered
    assert "harald sitter" in lowered


def test_the_deduped_section_is_named_not_positional(manifest):
    """Universal Blue is 'deduped from above' and now plays FIRST of the
    ublue family. A rule that said 'the last section' would have deduped
    Project Bluefin instead and taken every shared name off its wall."""
    assert B.DEDUPED_SECTION == "Universal Blue"
    by = {s["section"]: set(n.lower() for n in s["names"])
          for s in manifest["contributors"]}
    others = by["Project Bluefin"] | by["Aurora"] | by["Bazzite"]
    assert not (by["Universal Blue"] & others)
    # ...and the sections it was deduped against kept everybody.
    assert by["Project Bluefin"] & by["Aurora"], \
        "somebody who worked on both is credited under both"


def test_the_ublue_family_plays_in_the_owners_order(manifest):
    """Owner: 'Put universal blue and aurora ahead of bluefin'."""
    order = [s["section"] for s in manifest["contributors"]
             if not s.get("tier")]
    assert order == ["Universal Blue", "Bazzite", "Aurora", "Project Bluefin"]


def test_the_ghost_maintainer_is_not_a_contributor(manifest):
    """An easter egg, and a call for a volunteer. There is no such person, so
    there is no login, no avatar, and it is never counted as a credit."""
    kde = next(s for s in manifest["contributors"]
               if s["section"] == "KDE Linux")
    assert kde["ghost"] == {"name": "The Next KyleGospo",
                            "title": "Curse of Maintainership"}
    assert "The Next KyleGospo" not in kde["names"]

    items, _ = B.schedule(manifest)
    walls = [i for i in items if i["kind"] == "wall"]
    ghosted = [w for w in walls if w.get("ghost")]
    assert len(ghosted) == 1, "the ghost appears once, on one wall"
    assert ghosted[0]["section"] == "KDE Linux"
    assert ghosted[0]["page"] == ghosted[0]["pages"], "it closes the section"


def test_the_call_outs_reach_the_frame():
    """#UPSTREAMFIRST at the top of an upstream wall, #linuxforever along the
    bottom of every one."""
    assert C.UPSTREAM_EYEBROW == "#UPSTREAMFIRST"
    assert C.WALL_HASHTAG == "#linuxforever"
    up = C.render_name_wall("bootc", ["cgwalters"], 1, 1, tier="upstream")
    plain = C.render_name_wall("Aurora", ["castrojo"], 1, 1)
    assert up.size == plain.size == (C.W, C.H)


def test_the_metal3_bubble_dissolves_once_across_the_tier(manifest):
    """Owner: 'have that fade to Deploying CNCF Metal3'. A still cannot fade
    by itself, so the dissolve is spread over the walls it rides -- and it
    plays ONCE over the tier, not once per wall."""
    items, _ = B.schedule(manifest)
    mixes = [i["bubble_mix"] for i in items
             if i["kind"] == "wall" and "bubble_mix" in i]
    assert mixes, "the gag rides the upstream walls"
    assert mixes == sorted(mixes), "it never fades back"
    assert mixes[0] == 0.0 and mixes[-1] == 1.0
    assert 0.5 in mixes, "a genuine half-and-half card is the dissolve"
    # It is on the upstream walls only.
    for item in items:
        if item["kind"] == "wall" and "bubble_mix" in item:
            assert item.get("tier") == "upstream"


def test_a_brand_mark_is_never_taken_off_this_host():
    """Bluefin REBRANDS /usr/share/pixmaps: `fedora_whitelogo_med.png` and
    `gnome-boot-logo.png` on this machine are both the Bluefin wordmark, and
    the first build credited Fedora CoreOS under one of them."""
    import fetch_brand_marks
    assert not hasattr(fetch_brand_marks, "LOCAL_MARKS")
    for url in fetch_brand_marks.MARKS.values():
        assert url.startswith("https://")
        assert "/usr/share" not in url
