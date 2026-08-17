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
        "YOU ARE THE DREAM OF MANY ANCESTORS", "RAFAEL CASTRO", "FIGHT"]
    assert [c["kind"] for c in cards] == ["cta", "birthday", "cta"]
    # "noticeably larger font" is a step somebody can see, in this order.
    # Two rungs rather than three since the owner dropped MAKE YOUR OWN FATE
    # and BECOME LEGEND: one cry, then FIGHT above it.
    scales = [C.CTA_SCALE[c["scale"]] for c in cards if c["kind"] == "cta"]
    assert scales == sorted(scales) and len(set(scales)) == 2
    # ...and FIGHT stays the biggest thing in the act.
    assert scales[-1] == C.CTA_SCALE["colossal"]


def test_dropping_two_cries_did_not_lengthen_the_cards_that_stayed(manifest):
    """Owner, 2026-08-16: drop MAKE YOUR OWN FATE and BECOME LEGEND, 'just
    have that one phrase'.

    ``cta_cards`` carry RELATIVE weights, so removing 4.0 + 4.5 without moving
    that 8.5 somewhere would have quietly stretched the birthday card and
    FIGHT. The surviving cry inherits the weight instead, and the pre-reveal
    total is what it always was.
    """
    assert sum(c["dur_sec"] for c in manifest["cta_cards"]) == 23.0


def test_fight_is_up_longer_than_everything_before_it(manifest):
    """Owner: 'FIGHT <--- I want this one up longer than the first 2'.

    The two cards that instruction named -- MAKE YOUR OWN FATE and BECOME
    LEGEND -- were dropped on 2026-08-16, so the literal comparison has nothing
    left to compare against. What the instruction was ASKING FOR survives it:
    FIGHT is the last thing before the cover and it is up longer than any
    single card ahead of it.
    """
    items, _ = B.schedule(manifest)
    cta = [i for i in items if i["kind"] in ("cta", "birthday")]
    fight = next(i for i in cta if i.get("text") == "FIGHT")
    before = [i for i in cta if i is not fight]
    assert before, "FIGHT is not the only card in the run"
    assert all(fight["dur"] > c["dur"] for c in before)


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


def test_laura_is_credited_once_and_the_credit_is_nimbatus(manifest):
    """Owner, 2026-08-16: "laura is as nimbatus".

    She used to hold two placards -- Elsie Bray and Nimbatus -- with the same
    authored identity copy on both, because the vocab binds her identity to one
    binding and her verified login to the other. Nobody is credited twice for
    one performance, and the name the credit prints is the owner's call.
    """
    laura = [c for c in manifest["cast"] if c["person"] == "Laura Santamaria"]
    assert len(laura) == 1
    assert laura[0]["character_id"] == "nimbatus"


def test_nobody_holds_two_placards(manifest):
    """A second card for one person reads as a mistake, not as a second role."""
    people = [c["person"] for c in manifest["cast"]]
    assert len(people) == len(set(people))


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
        assert member["person"]
        # The Destiny character is no longer PRINTED, but the binding it came
        # from is still recorded -- that is what a redaction is keyed on.
        assert member["character_id"]


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
    Santamaria. A placard shows a face only from an authored card, a login the
    manifest's own overlay verifies, or a login whose verification is WRITTEN
    DOWN beside it -- never from a login inferred off a person's name."""
    verified = {k for k in (manifest.get("cast_logins") or {}) if not k.startswith("_")}
    for member in manifest["cast"]:
        if not member.get("login"):
            continue
        assert (member["person"] in verified
                or member["login"] == "nimbinatus"
                or member.get("login_source")), member["person"]


def test_kats_login_is_the_one_that_was_checked_not_the_one_that_matched(manifest):
    """github.com/kat is named only "Kat" and is not confirmed to be Kat
    Cosgrove -- the nimbatus trap exactly. github.com/katcosgrove IS: the
    account's own name, its company and its bio all match the credit. The
    difference between the two is the note recorded beside the login."""
    kat = next(c for c in manifest["cast"] if c["person"] == "Kat Cosgrove")
    assert kat.get("card") == "kat"
    assert kat.get("login") == "katcosgrove"
    assert "kat" != kat["login"]
    assert kat.get("login_source")


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


def test_the_principals_play_in_the_order_the_show_introduces_them(manifest):
    """The manifest's order IS the show's order -- act II's people first, act
    VII's last -- and the schedule never re-sorts it by who happens to have a
    face or a bio."""
    items, _ = B.schedule(manifest)
    on_screen = [i["person"] for i in items if i["kind"] == "cast"]
    assert on_screen == [c["person"] for c in manifest["cast"]]
    acts = [c["seen_in"].split(" --")[0] for c in manifest["cast"]]
    order = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]
    assert acts == sorted(acts, key=order.index)


def test_every_placard_is_somebody_who_is_on_screen(manifest):
    """Owner: 'ensure this list matches the readme for the characters ...
    remove some of these characters', and separately 'Remove cayde-6 redacted
    from the starring roles, he's fine in the credits with the rest.'

    That list has since been replaced by a stricter one -- owner, 2026-08-16:
    "Remove people not in the movie from here and only use the principal
    actors", "not jorge castro", "we want karena, bsherman, and kylegospo".
    So the rule is no longer "the README's table": it is that EVERY placard is
    somebody who is on screen in a delivered act, and each entry cites the act
    it can be found in.
    """
    items, _ = B.schedule(manifest)
    assert len([i for i in items if i["kind"] == "cast"]) == len(manifest["cast"]) == 9
    for member in manifest["cast"]:
        assert member.get("seen_in"), member["person"]
    people = {c["person"] for c in manifest["cast"]}
    # The two the owner took out, and the reason each went.
    assert "Jorge Castro" not in people      # "not jorge castro"
    assert "Lindsay Gendreau" not in people  # Bungie's voice of Sagira, not in this film

    # NOT compared against the README's table any more, and that is the point.
    # That table lists BINDINGS -- Destiny characters and who plays them -- and
    # three principals (Kyle Gospodnetich, Natali Vlatko, Benjamin Sherman) are
    # on screen without playing a Destiny character at all. The evidence a
    # placard needs is the act it can be found in, which is `seen_in` above.
    cited = [c["seen_in"].split(" --")[1].strip() for c in manifest["cast"]]
    assert all(cited), "every principal cites the record that puts them on screen"


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

@pytest.mark.parametrize("text", [
    "Bob Killen", "Jacob Schnurr", "Project Bluefin",
    "Jeefy", "Rafael Castro", "cflewis", "Kat Cosgrove",
])
def test_every_b_and_every_f_is_blue(text):
    """The owner's rule, 2026-08-15: *"Ensure every b is blue, and every f is
    blue in all the dialogue except the chat bubbles and nameplates."*

    It used to be an either/or -- every B, *or* F instead for a string with no
    B in it -- so that somebody who already had blue did not get more of it.
    The owner superseded that: both letters, always.
    """
    assert C.blue_letters(text) == "BbFf"


def test_the_rule_is_case_insensitive_both_ways():
    for text in ("BOB", "bob", "FRED", "fred"):
        assert C.blue_letters(text) == "BbFf"


def test_a_name_with_no_b_paints_its_f_blue():
    img = C.render_role_card("Introducing", ["ffff"])
    colours = {p[:3] for p in img.convert("RGBA").getdata() if p[3] > 200}
    assert C.ACCENT[:3] in colours


def test_a_name_with_a_b_now_lights_its_f_too():
    """'bf' lights BOTH -- the change the owner asked for on 2026-08-15."""
    lit = C.blue_letters("bf")
    assert "f" in lit and "b" in lit


def test_the_rule_has_one_home():
    """The definition lives in tools.blueletters; credits.py delegates.

    It used to live only inside credits.py while three other surfaces drew
    burned copy of their own. One rule, one definition.
    """
    from tools import blueletters
    assert C.blue_letters("anything") == blueletters.BLUE


def test_the_blue_rule_does_not_reach_chat_bubbles_or_nameplates():
    """The owner drew the boundary and it is the part letters cannot imply.

    Enforced by which renderers call the helper, so this asserts the two
    excluded families do not import or use it.
    """
    import inspect
    from tools import plate
    for fn in (plate._render_chat, plate.render_plate):
        assert "blueletters" not in inspect.getsource(fn)


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
    """Owner: 'make them go through the entire calendar order and keep
    switching', now on the light set.

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


def test_the_cycle_is_the_day_set_and_never_mixes_the_two():
    """Owner: 'I just want light colored wallpapers.'

    The night frames still sit in the same directory under their bare NN.png
    names, because the prologue's bridge reads them. A glob that picked up
    both would deal a night frame into the roll every other card.
    """
    walls = C.wallpapers()
    if not walls:
        pytest.skip("no wallpapers cached; run scripts/fetch_wallpapers.py")
    assert all(p.stem.endswith("-day") for p in walls), \
        f"act VIII runs on the day set; got {[p.name for p in walls]}"


def _relative_luminance(rgb):
    """WCAG relative luminance of an 8-bit RGB triple."""
    def channel(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(v) for v in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a, b):
    la, lb = _relative_luminance(a), _relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# WCAG's large-text threshold. Every credit here is display type and none of
# it is body copy, so this is the floor -- most months clear it comfortably.
CONTRAST_FLOOR = 3.0


def test_the_type_can_be_read_off_every_month():
    """The light wallpapers' real regression guard, measured in pixels.

    The cycle test passes whether the roll is legible or not: it only checks
    which file is picked. This measures the deck's white type against the
    graded wallpaper in the band every card sets its name in, on EVERY month,
    which is what lets the grade leave the day art's exposure alone -- the
    centre scrim is carrying the type, and this is the proof.
    """
    walls = C.wallpapers()
    if not walls:
        pytest.skip("no wallpapers cached; run scripts/fetch_wallpapers.py")
    for i in range(len(walls)):
        frame = C.backdrop(i).convert("RGB")
        band = frame.crop((0, int(C.H * 0.34), C.W, int(C.H * 0.66)))
        small = band.resize((32, 12), Image.LANCZOS)
        worst = min(_contrast(px, C.TEXT) for px in small.get_flattened_data())
        assert worst >= CONTRAST_FLOOR, (
            f"{walls[i].name} only reaches {worst:.2f}:1 in the name band; "
            f"the scrim is not carrying the type")


def test_a_login_is_never_shortened_to_something_nobody_is_called():
    """Owner: 'fix the ellipsis.'

    A wide login used to be cut to 'angelcerverarold...'. Rule 3 is about
    crediting a real person correctly, and a name is not a string you may trim
    to fit -- it comes down in SIZE instead.
    """
    import inspect
    src = inspect.getsource(C.render_name_wall)
    assert "\\u2026" not in src and "…" not in src, \
        "a login is set whole; the ellipsis is gone"
    assert "CELL_MIN_SIZE" in src, "the fitter shrinks the type instead"


def test_a_placard_reproduces_the_authored_identity_and_never_the_splash():
    """Owner: 'get rid of those hero splashes they suck.'

    The 1200x630 card is a splash composite. What was AUTHORED is the copy --
    label, class, name, title -- and that is what the placard reproduces, so
    dropping the art costs nobody their identity. A row nobody wrote is not
    drawn, and nothing here composes one.
    """
    import inspect
    src = inspect.getsource(C.render_cast_placard)
    assert "cast_identity" in src
    assert not hasattr(C, "cast_card"), \
        "the splash-card loader is gone, not merely unused"
    assert C.cast_identity(None) is None
    assert C.cast_identity("nobody-authored-this") is None


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


def test_the_credits_gate_the_delivered_master_peak():
    source = (REPO_ROOT / "scripts" / "build_credits.py").read_text()
    assert "peaks.trim_master_peak(out_path.resolve())" in source


# --- the second pass of the bed --------------------------------------------

def test_storytime_follows_the_whole_instrumental_loop(manifest):
    """Storytime replaces only the former vocal pass after the entire
    instrumental loop.

    'the ENTIRE instrumental' is load-bearing: the loop is not cut short to
    make room for the vocal. Pass one keeps both of its measured spans.
    """
    passes = B.bed_passes(manifest["bed"])
    assert len(passes) == 2
    assert passes[0]["bed_id"] == "bed_wish_i_had_an_angel"
    assert passes[1]["bed_id"] == "bed_storytime"
    assert len(passes[0]["segments"]) == 2
    assert passes[0]["segments"][0]["start_sec"] == 193.42


def test_storytime_pass_skips_its_own_intro(manifest):
    """Storytime enters on its full-band vocal entry, not its quiet intro.

    14.512472 is Storytime's beat 0.368 s ahead of the measured +6.23 dB
    re-entry at 14.880, so the 0.25 s crossfade clears the hit.
    """
    storytime = B.bed_passes(manifest["bed"])[1]
    start = storytime["segments"][0]["start_sec"]
    assert start > 0.0, "Storytime must not restart from its quiet intro"
    assert start == 14.512472
    grid = json.loads((REPO_ROOT / "music" /
                       "bed_storytime.json").read_text())["grid"]
    assert any(abs(b - start) < 1e-6 for b in grid["beats"]), (
        "the in point must sit on Storytime's tracked beat, not a round number")
    xf = manifest["bed"].get("crossfade_sec", 0.0)
    assert start + xf < 14.880, (
        "the 0.25 s crossfade has to CLEAR before the band arrives at 14.880, "
        "or the hand-over shaves the transient it exists to land on")


def test_storytime_pass_stops_at_its_natural_ending(manifest):
    """Storytime decays naturally to its file end, with no digital padding."""
    storytime = B.bed_passes(manifest["bed"])[1]
    record = json.loads((REPO_ROOT / "music" /
                         "bed_storytime.json").read_text())
    end = storytime["segments"][0]["end_sec"]
    assert end == record["duration_sec"]


def test_every_span_of_both_passes_reaches_the_filtergraph(manifest):
    """Storytime is a SECOND ffmpeg input; binding it to input 1
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
            req = a[0] if a else k.get("url")
            seen.append(getattr(req, "full_url", req))
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


# --- the hero credits ------------------------------------------------------

def test_a_placard_never_prints_the_destiny_character(manifest):
    """Owner, 2026-08-16: "drop the Destiny names, do it like 'Kat Cosgrove as
    Defender Queen... blah'". The binding is still recorded -- a redaction is
    keyed on it -- but the character name is not drawn, even when a caller
    passes one."""
    img = C.render_cast_placard("Kat Cosgrove", "Saint-14", card="kat",
                                guardian_title="Defender Queen of the Lost")
    plain = C.render_cast_placard("Kat Cosgrove", card="kat",
                                  guardian_title="Defender Queen of the Lost")
    assert list(img.getdata()) == list(plain.getdata())


def test_a_seal_nobody_authored_is_omitted_not_filled():
    """Jeefy's binding carries no plate, so his placard has no `as` row at all.
    Inventing a Guardian title for a real person is the forbidden move."""
    with_seal = C.render_cast_placard("Jeefy", guardian_title="Iron Lord")
    without = C.render_cast_placard("Jeefy")
    assert list(with_seal.getdata()) != list(without.getdata())


def test_the_github_title_is_reproduced_whole_and_its_breaks_are_honoured():
    """`<br><br>` is a paragraph the author asked for, not markup to strip.
    Natali's title is five rows including the break; a three-row cap dropped
    "Archaeologist and Egyptologist" off the end of her credit."""
    from PIL import ImageDraw
    probe = ImageDraw.Draw(C.backdrop(0))
    text = ("Director of Open Source Software Engineering at Cisco, SIG Docs "
            "Co-Chair for Kubernetes TODO Group Steering Committee member."
            "<br><br>Archaeologist and Egyptologist")
    lines = C.title_lines(text, probe, C._font("regular", C.TITLE_SIZE))
    assert "" in lines, "the paragraph break survives"
    assert lines[-1] == "Archaeologist and Egyptologist"
    assert "<br>" not in " ".join(lines)


def test_the_lower_third_is_ink_where_the_type_is(manifest):
    """The reason this is a lower third at all: centred type over the day
    wallpapers measured 1.02:1 at its worst. Under the band it is dark on every
    month, so the same card reads the same on all eleven."""
    for index in range(11):
        img = C.render_cast_placard("Kat Cosgrove", card="kat",
                                    guardian_title="Defender Queen of the Lost",
                                    index=index).convert("RGB")
        # The left margin: inside the band, never under a glyph or a face.
        band = img.crop((0, C.LOWER_TOP + 20,
                         C.LOWER_PAD - 20, C.LOWER_TOP + C.LOWER_HEIGHT - 20))
        px = list(band.getdata())
        assert max(_relative_luminance(p) for p in px) < 0.18, index


def test_a_title_nobody_wrote_is_lorem_and_is_recorded(manifest):
    """Owner: "placeholder for jeefy". A row nobody has authored renders as
    Latin -- visibly not approved English -- and the manifest records who it is
    owed to, so it turns up in the punch list instead of being forgotten."""
    pending = [c for c in manifest["cast"] if c.get("title_pending")]
    assert pending, "somebody is still owed a title"
    for member in pending:
        assert not member.get("title")
        drawn = B.cast_title(member)
        assert drawn and drawn != member["title_pending"]
        # Latin, deterministic, and the same on every machine.
        assert drawn == B.cast_title(member)


def test_a_supplied_title_is_never_replaced_by_a_placeholder(manifest):
    for member in manifest["cast"]:
        if member.get("title"):
            assert B.cast_title(member) == member["title"]
            assert member.get("title_source"), member["person"]


def test_an_authored_seal_reaches_the_placard(manifest):
    """A seal is authored in two places, and both have to arrive.

    The website carded four of the principals, so their `as` row resolves
    through `card`. The other three -- Karena, Kyle, Kelsey -- are authored in
    the manifest's own `guardian_title`, and the first build dropped that field
    on the way to the renderer: three placards silently lost a row that had
    been written for them, and every gate stayed green because an unauthored
    seal is *supposed* to be omitted.
    """
    items, _ = B.schedule(manifest)
    seats = {i["person"]: i for i in items if i["kind"] == "cast"}
    authored = [c for c in manifest["cast"] if c.get("guardian_title")]
    assert authored
    for member in authored:
        seat = seats[member["person"]]
        assert seat["guardian_title"] == member["guardian_title"], member["person"]
        assert member.get("guardian_title_source"), member["person"]


def test_a_seal_nobody_authored_stays_off_the_card(manifest):
    """The generic fallback is as invented as an invention."""
    items, _ = B.schedule(manifest)
    seats = {i["person"]: i for i in items if i["kind"] == "cast"}
    for member in manifest["cast"]:
        if member.get("guardian_title") or member.get("card"):
            continue
        assert not seats[member["person"]]["guardian_title"], member["person"]
