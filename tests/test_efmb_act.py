"""Act II -- *Endless Forms Most Beautiful*: the cut, the clocks, the plates.

Offline and dependency-free, like the rest of the suite: no ffmpeg, no media,
no network. What is pinned here is the arithmetic and the wiring, not pixels.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_efmb  # noqa: E402
import build_efmb_plates  # noqa: E402


# --- the two clocks --------------------------------------------------------

def test_source_and_film_time_round_trip():
    """The two clocks are exact inverses, not approximations.

    Everything downstream binds a person to a SOURCE timecode and lets film
    time be computed, because the film moves and the source does not. That is
    only safe if the conversion is lossless in both directions.
    """
    lead = build_efmb.derive_lead()
    for src in (0.0, 3.9, 30.0, 100.0, 244.0, 338.2, 360.4):
        film = build_efmb.film_for_source(src, lead)
        assert build_efmb.source_for_film(film, lead) == pytest.approx(src, abs=1e-6)


def test_a_splice_is_one_film_instant_and_two_source_instants():
    """At a cut the round trip is ambiguous, and that is the cut existing.

    Source 4.017 is the last frame of the cold open and 22.033 is the first
    frame of the moon battle; the removal between them is what makes the act
    one continuous scene. Both land on the same film second, so converting
    back yields the earlier one. Pinned so nobody 'fixes' the asymmetry and
    quietly shifts every binding after a splice by one shot.
    """
    lead = build_efmb.derive_lead()
    assert (build_efmb.film_for_source(4.017 - 1e-9, lead)
            == pytest.approx(build_efmb.film_for_source(22.033, lead), abs=1e-6))
    joined = build_efmb.film_for_source(22.033, lead)
    assert build_efmb.source_for_film(joined, lead) == pytest.approx(4.017, abs=1e-6)


def test_a_cut_frame_raises_instead_of_sliding_onto_its_neighbour():
    """Binding a name to a frame that no longer plays must be loud.

    The dance section is removed. Silently returning the film time of whatever
    now occupies that second is how a credit ends up on the wrong Guardian.
    """
    with pytest.raises(build_efmb.NotInPicture):
        build_efmb.film_for_source(260.0)          # inside the dance section
    with pytest.raises(build_efmb.NotInPicture):
        build_efmb.film_for_source(370.0)          # the publisher end cards


def test_the_head_is_derived_from_the_music_and_never_typed():
    """The lead-in is whatever puts the shield on the downbeat."""
    plan = build_efmb.build()
    assert build_efmb.BED_LEAD_SEC is None, "the head must not be a typed constant"
    anchor_film = build_efmb.film_for_source(build_efmb.SYNC_ANCHOR_SRC)
    assert anchor_film == pytest.approx(build_efmb.SYNC_ANCHOR_FILM, abs=1e-6)
    assert (plan["bed_lead_sec"] + plan["picture_sec"] + plan["bed_tail_sec"]
            == pytest.approx(plan["bed_duration_sec"], abs=0.001))


# --- the plate manifest ----------------------------------------------------

def committed():
    with open(REPO_ROOT / "stories" / "02-endless-forms-plates.json") as fh:
        return json.load(fh)


def test_the_committed_manifest_matches_its_generator():
    """It is an OUTPUT. A conflict in it is settled by re-running the tool."""
    assert committed() == build_efmb_plates.build()


def test_the_manifest_builds_from_committed_inputs_only():
    """Everything the generator reads must be in the repository.

    The roster decides which REAL PEOPLE this act credits, so it is an input to
    the cut, not a scratch artifact. It first lived in gitignored renders/,
    where tools/ensemble.py writes it, and CI failed on the file simply not
    being there -- a manifest generated from a file nobody else has cannot be
    checked, reproduced, or reviewed.
    """
    for path in (build_efmb_plates.ROSTER,
                 REPO_ROOT / "vocab" / "casting.yaml",
                 REPO_ROOT / "music" / "bed_endless_forms_most_beautiful.json"):
        assert path.exists(), f"{path} is missing"
        ignored = subprocess.run(["git", "check-ignore", str(path)],
                                 cwd=REPO_ROOT, capture_output=True, text=True)
        assert ignored.returncode != 0, (
            f"{path} is gitignored -- the generator cannot depend on it")


def test_every_plate_sits_on_a_frame_that_still_plays():
    for plate in committed()["plates"]:
        src = plate.get("seen_at_src")
        if src is None:
            continue
        build_efmb.film_for_source(src)      # raises if that frame was cut


def test_no_plate_is_laid_over_bungies_burned_in_title():
    """Source 356.500 -> 358.200 burns "NEW LEGENDS WILL RISE" across frame.

    The act removes every other title card in the source. This one is welded to
    picture the act keeps, so the plates clear it instead -- laying our credit
    over the publisher's is the one thing that would look deliberate.

    The zone guards the PICTURE. The letterbox banner lives on the bottom bar,
    below the picture entirely, so it never touches the burned-in title and is
    exempt by position -- this is a time-overlap check and cannot see that.
    """
    lead = build_efmb.derive_lead()
    for src_in, src_out, _why in build_efmb_plates.NO_PLATE_SRC:
        zone = (build_efmb.film_for_source(src_in, lead),
                build_efmb.film_for_source(src_out - 0.001, lead))
        for plate in committed()["plates"]:
            if plate.get("position") == "letterbox":
                continue
            start, end = plate["at"], plate["at"] + plate["dur"]
            # Touching is not overlapping. The chapter card is clamped to end
            # ON the first frame of Karena's jump, and 146.233 + 2.300 lands
            # 6e-14 past 148.533 in binary floating point -- the same
            # tolerance `space_plates` already carries, for the same reason.
            EPS = 1e-6
            assert not (start < zone[1] - EPS and end > zone[0] + EPS), (
                f"{plate['id']} overlaps the no-plate zone at {zone}")


def test_the_authored_handles_are_never_replaced_with_real_names():
    """`[ p5 ]` and `[ EyeCantCU ]` are copy the owner authored, not gaps."""
    names = {p.get("name") for p in committed()["plates"]}
    assert "[ p5 ]" in names and "[ EyeCantCU ]" in names
    for banned in ("Robert Sturla", "RJ Trujillo"):
        assert banned not in names


def test_cayde_is_redacted_in_this_act_and_only_by_covering_a_known_name():
    """The joke needs the audience not to be told yet.

    A redaction only ever HIDES something this repo already knows -- the plate
    it covers is recorded beside it -- and it is scoped to act II, because he
    is revealed later in the programme.
    """
    card = next(p for p in committed()["plates"] if p["id"] == "cayde_signoff")
    assert card["speaker"] == "[ REDACTED ]"
    assert card["redacts"] == "Jorge Castro"
    assert "act II only" in card["redaction_scope"]
    assert card["text_source"] == "owner_supplied", (
        "Bungie's Cayde never said this -- it must never read as recovered "
        "source dialogue")


def test_nobody_is_credited_twice_with_two_different_faces():
    """One name, two different cards, is the bug this guards. A card repeated
    VERBATIM -- the TOC payoff reprising the montage's emeritus announcement
    row for row, as a callback -- is the same face twice, which is allowed.
    """
    plates = committed()["plates"]
    by_name = {}
    for p in plates:
        if p.get("name"):
            by_name.setdefault(p["name"], []).append(p)
    for name, cards in by_name.items():
        copies = {(c.get("label"), c.get("class"), c.get("title"))
                  for c in cards}
        assert len(copies) == 1, (
            f"{name!r} is credited {len(cards)} times with DIFFERENT copy: "
            f"{copies} -- a reprise reproduces the card verbatim; anything "
            "else is two faces for one person")


def test_every_plate_can_be_read():
    for plate in committed()["plates"]:
        # An ANIMATION frame is not a credit. The choice screen is a run of
        # frames a fifteenth of a second each; MIN_HOLD exists so a NAME can
        # be read, and holding a frame for 2.2 s is a still, not a cursor.
        if plate.get("animation"):
            continue
        assert plate["dur"] >= build_efmb_plates.MIN_HOLD, (
            f"{plate['id']} holds {plate['dur']}s -- too brief to read")


def test_the_manifest_obeys_one_plate_at_a_time():
    from tools.plate import load_manifest_entries
    load_manifest_entries(committed()["plates"])


def test_copy_is_reproduced_rather_than_composed():
    """A missing key must raise, never fall back to the generic plate.

    Falling back would quietly overwrite an identity the owner authored with
    the anonymous blueberry copy, which is the one thing casting must not do.
    """
    casting = build_efmb_plates.load_casting()
    with pytest.raises(KeyError):
        build_efmb_plates.authored_copy("nobody_has_authored_this", casting)


def test_a_placeholder_carries_a_name_and_no_invented_rows():
    """Named, but nothing written for them yet: omit the rows, keep the name."""
    casting = build_efmb_plates.load_casting()
    copy = build_efmb_plates.placeholder_copy("dylan_taylor", casting)
    assert copy["name"] == "Dylan Taylor"
    assert "title" not in copy and "class" not in copy


def test_the_manifest_never_hands_the_renderer_a_url():
    """tools/plate.py never touches the network, so an avatar URL renders as
    the drawn crest with a warning -- which is how every wreathed plate in this
    act was quietly shipping without its portrait."""
    for plate in committed()["plates"]:
        avatar = plate.get("avatar")
        if avatar:
            assert not str(avatar).startswith("http"), plate["id"]


# --- the two ffmpeg spellings that have cost this act a rebuild ------------

def test_the_burn_filter_carries_no_shell_quotes():
    """REGRESSION, and it shipped: plates that silently did not burn.

    `enable='between(t,1,2)'` is the documented form -- on a command line,
    where the SHELL strips the quotes. tools/plate.py builds an argv list that
    never sees a shell, so ffmpeg got the quote characters as part of the
    expression, failed to parse it, disabled every overlay and exited 0. The
    output looked finished and carried no plates at all.
    """
    import tools.plate as plate

    seen = {}

    def fake_run(cmd, **kwargs):
        if any("ffprobe" in str(part) for part in cmd):
            return subprocess.CompletedProcess(cmd, 0, "307.998\n", "")
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, "", "")

    real_run = plate.subprocess.run
    plate.subprocess.run = fake_run
    try:
        plate.burn("in.mp4", [{"id": "x", "at": 1.0, "dur": 2.0}],
                   "plates", "out.mp4", ffmpeg=["ffmpeg"])
    finally:
        plate.subprocess.run = real_run

    graph = seen["cmd"][seen["cmd"].index("-filter_complex") + 1]
    assert "'" not in graph, f"shell quotes in an argv filtergraph: {graph}"
    assert "enable=between(t\\," in graph, (
        f"unquoted commas are argument separators to the filter parser: {graph}")


def test_every_plate_input_is_looped_for_the_length_of_the_picture():
    """REGRESSION, and it shipped: a plate gated late in a long cut never drew.

    A PNG is a ONE-FRAME input. Fed to overlay as-is it EOFs immediately, and
    `eof_action=repeat` does not hold the frame for five minutes: the identical
    plate gated to t=5 draws and gated to t=269 does not, same file, same
    graph. Act II came out fully credited on paper and completely unplated on
    screen, twice, before anyone looked at the frame instead of the manifest.
    """
    import tools.plate as plate

    seen = {}

    def fake_run(cmd, **kwargs):
        if any("ffprobe" in str(part) for part in cmd):
            return subprocess.CompletedProcess(cmd, 0, "307.998\n", "")
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, "", "")

    real_run = plate.subprocess.run
    plate.subprocess.run = fake_run
    try:
        plate.burn("in.mp4", [{"id": "x", "at": 269.0, "dur": 2.5}],
                   "plates", "out.mp4", ffmpeg=["ffmpeg"])
    finally:
        plate.subprocess.run = real_run

    cmd = [str(part) for part in seen["cmd"]]
    assert "-loop" in cmd, "the plate input is a single frame that EOFs at once"
    # ...and bounded, or the input is infinite and the encode never terminates.
    assert cmd.count("-t") >= 2, (
        "each looped input needs -t, and the output needs one too: with every "
        "input the same length there is no unambiguous shortest stream, and "
        "act II came out 318.767 s against a 307.998 s cut")


def test_the_render_chain_never_uses_filter_complex():
    """ISSUE #88: the same chain, spelled two ways, gives two lengths.

    As `-vf` the act runs 307.99 s. Wrapped in `-filter_complex` the same
    frames come out 299.48 s -- 2.8% fast, 505 frames discarded where the
    rescaled timestamps collide, and ffmpeg exits 0 while doing it.
    """
    source = (REPO_ROOT / "scripts" / "build_efmb.py").read_text()
    render_section = source[source.index("def render("):]
    assert '"-filter_complex"' not in render_section, (
        "the render chain passes -filter_complex to ffmpeg")
    assert "filter_complex" not in build_efmb.NORMALISE_VF


def test_the_bed_is_corrected_with_static_gain_and_never_a_normaliser():
    """The bed decodes above full scale; the fix only ever goes DOWN."""
    assert build_efmb.MUX_GAIN_DB < 0
    source = (REPO_ROOT / "scripts" / "build_efmb.py").read_text()
    render_section = source[source.index("def render("):]
    for banned in ("loudnorm", "alimiter", "acompressor"):
        assert banned not in render_section


# --- the montage announcements (owner brief, issue #98) ---------------------

def _montage(manifest):
    return [p for p in manifest["plates"]
            if p["id"].startswith(("montage_chat_", "announce_"))]


def test_the_montage_asides_keep_their_even_step():
    """"try to space them out evenly". Even means even: one step, no drift.

    The four RANKED cards are gone with AN4-CH3CK-12 (owner: "Remove all this
    anacheck stuff for now"), so what is left is the owner's own two asides.
    They no longer start at MONTAGE_IN because 1:38 is now where Joseph is
    talking -- the montage takes what the new dialogue leaves.
    """
    cues = _montage(build_efmb_plates.build())
    assert len(cues) == 2
    assert all(p["id"].startswith("montage_chat_") for p in cues)
    assert cues[0]["at"] >= build_efmb_plates.MONTAGE_IN
    steps = {round(b["at"] - a["at"], 3) for a, b in zip(cues, cues[1:])}
    assert steps == {build_efmb_plates.MONTAGE_STEP}


def test_the_announcer_is_gone_entirely():
    """Owner: "Remove all this anacheck stuff for now." All three of his
    blocks -- the ranked montage cards, the TOC payoff pair, and the eyebrow
    on Natewaddington's placard -- and nothing else."""
    manifest = build_efmb_plates.build()
    blob = json.dumps(manifest["plates"])
    assert "AN4-CH3CK" not in blob
    ids = {p["id"] for p in manifest["plates"]}
    assert not {i for i in ids if i.startswith(("announce_", "toc_announce_"))}
    # The placard itself STAYS -- only its eyebrow was his.
    placard = next(p for p in manifest["plates"]
                   if p["id"] == "timed_natewaddington")
    assert placard["name"] == "[ Natewaddington ]"
    assert "label" not in placard
    assert any("anacheck" in u.lower() for u in manifest["unresolved"])


def test_giklab_is_gone_and_nobody_moved_into_his_slot():
    """Owner: "03:16 get rid of giklab". Megacut 3:16 is film 74.4, and the
    only blueberry plate in the act was at 73.400. The SHOT came out, so the
    roster is not reshuffled behind him."""
    assert build_efmb_plates.BLUEBERRY_SHOTS == []
    ids = {p["id"] for p in build_efmb_plates.build()["plates"]}
    assert not {i for i in ids if i.startswith("blueberry_")}


def test_the_last_announcement_hands_off_before_the_lead_in_banner():
    """The cues exist to fill 1:38 -> 2:19 and then get out of the way; one
    running past 2:19 would be on top of the scene it is introducing."""
    cues = _montage(build_efmb_plates.build())
    assert cues[-1]["at"] + cues[-1]["dur"] <= build_efmb_plates.MONTAGE_OUT


def _retired_the_montage_never_stacks_a_cue_on_the_badge():
    """Dylan Taylor's badge sits at 130.267 inside the montage. An announcement
    trimmed to the 2.2s minimum by the collision guard is not what "evenly"
    means, so the schedule has to clear it on its own."""
    manifest = build_efmb_plates.build()
    dylan = next(p for p in manifest["plates"]
                 if p["id"] == "placeholder_dylan_taylor")
    last = _montage(manifest)[-1]
    assert last["at"] + last["dur"] <= dylan["at"]
    assert last["dur"] == build_efmb_plates.SOLO_HOLD  # never trimmed


def test_the_owners_own_typo_still_stands():
    """Authored copy is reproduced, never tidied."""
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    assert (by_id["montage_chat_2"]["text"]
            == "Ready to the #FIGHTFORCONTRIBUTORS?")


def test_copy_the_card_has_no_row_for_is_recorded_not_dropped():
    """A fourth authored line on a three-row card is a punch-list item, not a
    licence to cram it into the class row."""
    unresolved = build_efmb_plates.build()["unresolved"]
    assert any("lead-in banner" in u for u in unresolved)


def test_the_owner_s_asides_are_pfp_chats_and_carry_no_rank():
    chats = [p for p in build_efmb_plates.build()["plates"]
             if p["id"].startswith("montage_chat_")]
    assert [p["kind"] for p in chats] == ["chat", "chat"]
    assert all(p["speaker"] == "Jorge Castro" for p in chats)
    assert not any(p.get("variant") or p.get("trustee") for p in chats)


# --- "The Long Walk" (owner brief, this round) -----------------------------

def walk_plates():
    return {p["id"]: p for p in committed()["plates"]
            if p["id"].startswith("walk_")}


def test_the_owner_s_two_timed_lines_land_on_his_marks():
    """He gave these off the MEGACUT (act II film + 2:01.567), so both were
    converted to source before anything was scheduled. If the chain of cues
    before them ever pushes one late, this is what catches it."""
    walk = walk_plates()
    assert walk["walk_ge_stream"]["at"] == pytest.approx(
        build_efmb.film_for_source(build_efmb_plates.WALK_MARK_STREAM), abs=1e-3)
    assert walk["walk_ge_glorious"]["at"] == pytest.approx(
        build_efmb.film_for_source(build_efmb_plates.WALK_MARK_UPSTREAM),
        abs=1e-3)


def test_the_villain_arrives_with_the_villain():
    """The bar is on the shot the winged figure walks out of, not on the
    owner's 5:35 -- his mark is 0.9s before the cut, and a card that names
    what is on screen has to be on the frame it names."""
    walk = walk_plates()
    bar = walk["walk_villain"]
    assert bar["kind"] == "miniboss"
    assert bar["seen_at_src"] == build_efmb_plates.WALK_VILLAIN
    assert bar["name"] == "KERNEL REGRESSION"
    assert bar["title"] == "Enslaver of Maintainers | Ruiner of User Experience"


def test_nobody_else_is_credited_inside_the_walk():
    """Owner: 'No other guardians'. Rizzo, HuntedRaven7, hanthor and Ahmed
    Adan all held shots in this window and all four came out.

    The letterbox banner is exempt: it names nobody (a hashtag, a collective,
    a second hashtag), and its second window starts where the patch-queue HUD
    ends -- the duck is measured off the walk's own schedule.
    """
    walk_in = build_efmb.film_for_source(build_efmb_plates.WALK_IN)
    walk_out = build_efmb.film_for_source(build_efmb_plates.WALK_OUT)
    for p in committed()["plates"]:
        if p["id"].startswith("walk_"):
            continue
        if p.get("kind") == "banner":
            continue
        assert not (walk_in <= p["at"] < walk_out), (
            f"{p['id']} is still credited inside The Long Walk")


def test_the_patch_queue_holds_from_the_enemies_until_the_villain():
    """A queue that blinks once is a caption. It is the site's own HUD card,
    at the bottom because the owner said bottom."""
    walk = walk_plates()
    hud = walk["walk_patch_queue"]
    assert hud["kind"] == "status" and hud["position"] == "status-bottom"
    assert hud["detail"] == "UPSTREAM PATCH QUEUE"
    assert hud["at"] == pytest.approx(
        build_efmb.film_for_source(build_efmb_plates.WALK_ENEMIES), abs=1e-3)
    assert hud["at"] + hud["dur"] == pytest.approx(walk["walk_villain"]["at"],
                                                   abs=1e-3)


def test_the_achievement_gag_is_built_but_not_scheduled_until_it_is_approved():
    """The owner asked to approve the strings before anything is burned. Only
    'Mailing List Bullshit' is his; the rest are proposed, and a proposal that
    quietly rendered would be an invented line on screen."""
    assert build_efmb_plates.WALK_ACHIEVEMENTS_APPROVED is False
    assert not [p for p in committed()["plates"]
                if p.get("kind") == "achievement"]
    gaps = " ".join(committed()["unresolved"])
    assert "Mailing List Bullshit" in gaps
    owner_lines = [g for g in build_efmb_plates.WALK_ACHIEVEMENTS
                   if g["copy"] == "owner_supplied"]
    assert [g["name"] for g in owner_lines] == ["Mailing List Bullshit"]


def test_the_walk_never_rides_over_the_hard_cut_at_the_end_of_run_four():
    walk = walk_plates()
    end = max(p["at"] + p["dur"] for p in walk.values())
    assert end <= build_efmb.film_for_source(build_efmb_plates.WALK_OUT) + 1e-6


def test_the_chapter_replaces_rizzo_rather_than_pointing_at_a_gone_credit():
    chapters = {c["title"]: c for c in committed()["chapters"]}
    assert "Rizzo" not in chapters, "a marker points at a credit that is gone"
    assert chapters["The Long Walk"]["src"] == build_efmb_plates.WALK_IN


def test_every_walk_line_is_reproduced_verbatim():
    """Including the swearing, and the owner's own 'A1RMAX' inside his line
    while the CARD carries the channel's @A1RM4X."""
    walk = walk_plates()
    assert walk["walk_ge_stream"]["text"] == "Alright A1RMAX turn the stream on"
    assert walk["walk_ge_soundcard"]["text"] == (
        "You picked the shittiest sound card to impress them with")
    assert walk["walk_ge_lesson"]["text"] == "Here comes the lesson kids"
    assert walk["walk_A1RM4X"]["name"] == "A1RM4X"


def test_every_dialogue_pill_in_the_walk_carries_its_speaker_s_pfp():
    """The pill has an avatar slot and its fallback is the drawn crest --
    which is what every chat here silently rendered before, because the
    builder handed the avatar resolver an empty dict."""
    for pid, p in walk_plates().items():
        if p.get("kind") != "chat":
            continue
        assert p.get("avatar"), f"{pid} lost its pfp badge"
        assert not str(p["avatar"]).startswith("http")


# --- the TOC exchange and the endgame (owner brief, issue #98 §3-§4) ----------

def toc_plates():
    return {p["id"]: p for p in committed()["plates"]
            if p["id"].startswith(("toc_", "timed_", "quote_", "letterbox_"))}


def test_the_exchange_is_laid_out_around_the_walk_never_on_top_of_it():
    """Owner: the exchange belongs in the greenery; the greenery is where The
    Long Walk lives. So the questions go up in the pre-walk window and the
    answer lands after the walk's own last card has cleared."""
    lead = build_efmb.derive_lead()
    walk_in = build_efmb.film_for_source(build_efmb_plates.WALK_IN, lead)
    walk_out = build_efmb.film_for_source(build_efmb_plates.WALK_OUT, lead)
    toc = toc_plates()
    pre = [toc[k] for k in ("toc_karena", "toc_joseph_worth", "toc_ricardo")]
    # CHAINED BACKWARD FROM THE WALK, not forward from 2:19. Correcting
    # WALK_IN to the walking shot's real first frame left 7.033 s for three
    # cards that need 7.100, so the exchange moves earlier as a block rather
    # than squeezing Ricardo's question under the readable minimum. The floor
    # is Dylan Taylor's badge, which is out at 134.767.
    dylan = next(p for p in committed()["plates"]
                 if p["id"] == "placeholder_dylan_taylor")
    for p in pre:
        assert p["at"] >= dylan["at"] + dylan["dur"]
        assert p["at"] + p["dur"] <= walk_in + 1e-6
        assert p["dur"] >= build_efmb_plates.MIN_HOLD
    post = [toc[k] for k in ("toc_joseph_faith", "toc_ricardo_desktop",
                             "toc_joseph_lol")]
    for p in post:
        assert p["at"] >= walk_out


def test_josephs_five_oh_seven_is_retimed_off_the_black_tail():
    """"[JOSEPH] at 5:07" is inside the 16.065 s black tail -- the exchange
    plays over picture that exists, per the owner's own ruling."""
    card = toc_plates()["toc_joseph_faith"]
    assert card["text"] == "Dunno, how much faith DO we have in the CNCF?"
    picture_end = build_efmb.film_for_source(362.2 - 1e-6)   # the last frame
    assert card["at"] + card["dur"] < picture_end


def test_karena_s_jump_carries_no_card():
    """"Karena says nothing and jumps. No card on her here; the beat is the
    jump." The beat is clear screen between the DO line and Ricardo's answer.
    """
    toc = toc_plates()
    gap = (toc["toc_ricardo_desktop"]["at"]
           - (toc["toc_joseph_faith"]["at"] + toc["toc_joseph_faith"]["dur"]))
    assert gap == pytest.approx(build_efmb_plates.JUMP_BEAT, abs=1e-3)
    assert not any("jump" in p for p in toc), "the jump is a beat, not a card"


def test_the_toc_copy_is_reproduced_verbatim():
    toc = toc_plates()
    assert toc["toc_karena"]["text"] == (
        "One hundred thousand bootc volunteers, ready to power up")
    assert toc["toc_ricardo"]["text"] == (
        "You really think they can save open source?")
    assert toc["toc_ricardo_desktop"]["text"] == "Cloud native desktop? ..."
    assert toc["toc_joseph_lol"]["text"] == "LOL"
    # The brief's own speaker tags, not a casting.yaml lookup.
    assert toc["toc_karena"]["speaker"] == "Karena"
    # Emphasis markers are markup, not words: stripped, and recorded.
    assert "**" not in toc["quote_siosm"]["text"]
    assert any("powering up" in u for u in committed()["unresolved"])


def test_the_timed_cues_land_on_the_owners_marks():
    """All ACT II FILM time, anchored to source so a cut that moves raises."""
    toc = toc_plates()
    assert toc["timed_krook"]["at"] == pytest.approx(250.0, abs=1e-3)
    assert toc["timed_natewaddington"]["at"] == pytest.approx(260.0, abs=1e-3)
    assert toc["timed_jorge"]["at"] == pytest.approx(291.0, abs=1e-3)
    assert toc["timed_natewaddington"]["name"] == "[ Natewaddington ]"
    assert toc["timed_krook"]["text"] == (
        "Generational talent detected, call in the best")
    # The 4:01 Cayde speech bubble is the owner's call, and stays unscheduled.
    assert not any(p.get("at") == 241.0 for p in committed()["plates"])
    assert any("4:01" in u for u in committed()["unresolved"])


def test_the_closing_quotes_end_on_the_final_second():
    """The brief's preamble lands the last cue on the final second; its own
    proposal spread them 4:51 -> 5:07, over the black outro."""
    toc = toc_plates()
    quotes = [toc[f"quote_{s}"] for s in
              ("cgwalters", "siosm", "jberkus", "preethi", "castrojo")]
    starts = [q["at"] for q in quotes]
    steps = {round(b - a, 3) for a, b in zip(starts, starts[1:])}
    assert len(steps) == 1, f"not evenly spread: {steps}"
    last = quotes[-1]
    assert last["at"] + last["dur"] == pytest.approx(
        committed()["_film_sec"], abs=0.01)


def test_the_letterbox_callout_holds_for_the_rest_of_the_song():
    """"Keep it up for the whole song": up where the brief's scene starts
    (2:19, the montage's hand-off), down on the last frame, on the bottom bar
    where it shares no card's row. It ducks exactly one thing -- the walk's
    patch-queue HUD, whose card already occupies the bar's bottom-right."""
    toc = toc_plates()
    banners = [toc["letterbox_banner_1"], toc["letterbox_banner_2"]]
    assert all(b["kind"] == "banner" and b["position"] == "letterbox"
               for b in banners)
    assert all(b["text"] == build_efmb_plates.LETTERBOX_BANNER
               for b in banners)
    assert "Support Open Gaming Collective" in banners[0]["text"]
    # Up at the scene's start, down on the final frame...
    assert banners[0]["at"] == build_efmb_plates.MONTAGE_OUT
    assert banners[1]["at"] + banners[1]["dur"] == pytest.approx(
        committed()["_film_sec"], abs=1e-3)
    # ...and the duck is exactly the HUD's window, to the millisecond.
    hud = next(p for p in committed()["plates"] if p["id"] == "walk_patch_queue")
    assert banners[0]["at"] + banners[0]["dur"] == pytest.approx(hud["at"])
    assert banners[1]["at"] == pytest.approx(hud["at"] + hud["dur"])


def test_the_placeholder_speakers_are_recorded_never_guessed():
    """Nine names in the brief are in no vocab: they render as name-only
    placeholder badges with the drawn crest, and the punch-list names them."""
    gaps = " ".join(committed()["unresolved"])
    for name in ("krook", "Natewaddington", "cgwalters", "siosm", "jberkus",
                 "preethi"):
        assert name in gaps, f"{name} must stay on the punch-list"
    toc = toc_plates()
    for pid in ("timed_krook", "timed_bedazzle", "quote_cgwalters",
                "quote_siosm", "quote_jberkus", "quote_preethi"):
        assert "avatar" not in toc[pid], (
            f"{pid} carries an avatar nobody recorded -- the crest is the "
            "honest placeholder")


# --- this round: the OG Guardians, the team badge, and the choice screen ---

def test_the_owners_marks_are_megacut_time():
    """He timed this round off the PROGRAMME, not off act II standalone.

    The conversion is proved, not assumed: the same message names
    `blueberry_Giklab` at "03:16" and that plate was at film 73.400, which is
    megacut 3:14.97. No other reading lands, and act II's own 3:16 is inside
    "The Long Walk", whose brief is "No other guardians".
    """
    assert build_efmb_plates.MEGACUT_OFFSET == 121.567
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    # 02:57 / 02:59 / 03:03 -> 55.433 / 57.433 / 61.433
    assert by_id["trio_joseph_sandoval"]["at"] == pytest.approx(55.433, abs=1e-3)
    assert by_id["trio_rochaporto"]["at"] == pytest.approx(57.433, abs=1e-3)
    assert by_id["trio_mara_sov"]["at"] == pytest.approx(61.433, abs=1e-3)


def test_the_trio_staggers_and_then_holds_together():
    """"only show joseph sandoval, we're going to stagger these, keep them up
    for readability" -- one name, then a pair, then the row, and the row
    clears together a full TRIO_HOLD after the LAST arrival."""
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    cards = [by_id[f"trio_{k}"] for k, _, _ in build_efmb_plates.TRIO]
    outs = {round(c["at"] + c["dur"], 3) for c in cards}
    assert len(outs) == 1, "the row must clear together"
    assert outs.pop() == pytest.approx(
        max(c["at"] for c in cards) + build_efmb_plates.TRIO_HOLD, abs=1e-3)
    assert cards[0]["dur"] > cards[-1]["dur"], "Joseph is up longest"


def test_karena_is_angel_with_one_l():
    """Owner, twice: the README's spelling and "(Angel, one L)". The vocab is
    frozen (#167), so the correction is applied to this act's copy and
    recorded rather than edited into a committed input."""
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    assert by_id["trio_mara_sov"]["name"] == "Karena Angel"
    assert any("Angel" in u and "Angell" in u
               for u in build_efmb_plates.build()["unresolved"])


def test_the_og_guardians_are_bronze_and_on_the_owners_marks():
    """"02:15 ... 02:20 ... 02:28 ... 02:38 ... These are OG Guardians make
    them a proud bronze"."""
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    marks = {"og_dims": 13.433, "og_paganini": 18.433,
             "og_thockin": 26.433, "og_jbeda": 36.433}
    for pid, at in marks.items():
        assert by_id[pid]["at"] == pytest.approx(at, abs=1e-3)
        assert by_id[pid]["variant"] == "bronze"
        assert by_id[pid]["label"] == build_efmb_plates.OG_LABEL


def test_the_og_copy_is_the_owners_word_for_word():
    """Including the capitalised NOT, which is the joke."""
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    assert by_id["og_dims"]["title"] == "Comes in Peace"
    assert by_id["og_thockin"]["title"] == "Does NOT Come in Peace"
    assert by_id["og_jbeda"]["title"] == "Out of Retirement"


def test_catherine_paganinis_card_has_no_line_nobody_wrote():
    """The owner named her and wrote no title. Omitted, and recorded -- the
    other three OG cards having one is not a licence to compose hers."""
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    assert by_id["og_paganini"]["name"] == "Catherine Paganini"
    assert "title" not in by_id["og_paganini"]
    assert any("Paganini" in u for u in build_efmb_plates.build()["unresolved"])


def test_the_team_badge_captions_the_trio_rather_than_competing_with_it():
    """"Make a Team Badge: CNCF Community Leadership / Looking for Open
    Source's Brightest Future" -- after the row clears, before Joseph's next
    line."""
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    badge = by_id["team_cncf_leadership"]
    assert badge["name"] == "CNCF Community Leadership"
    assert badge["title"] == "Looking for Open Source's Brightest Future"
    trio_out = max(by_id[f"trio_{k}"]["at"] + by_id[f"trio_{k}"]["dur"]
                   for k, _, _ in build_efmb_plates.TRIO)
    assert badge["at"] >= trio_out
    assert badge["at"] + badge["dur"] <= by_id["chat_joseph_slop"]["at"]


def test_the_new_dialogue_lands_on_the_owners_seconds():
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    assert by_id["chat_joseph_slop"]["at"] == pytest.approx(70.433, abs=1e-3)
    assert by_id["chat_joseph_slop"]["text"] == "Here comes the slop"
    assert by_id["chat_karena_job"]["at"] == pytest.approx(77.433, abs=1e-3)
    assert by_id["chat_karena_job"]["text"] == "I love this job"
    assert by_id["chat_riaan_choices"]["speaker"] == "riaankleinhans"
    assert by_id["chat_riaan_choices"]["text"] == "Your choices are:"


def test_josephs_last_two_lines_keep_their_order_when_the_clock_cannot():
    """He marked them one second apart and a pill needs 2.2 s. The ORDER is
    his and is kept; only the gap is the timeline's, and it is recorded."""
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    first, second = by_id["chat_joseph_master"], by_id["chat_joseph_gotthis"]
    assert first["at"] == pytest.approx(97.433, abs=1e-3)
    assert second["at"] >= first["at"] + first["dur"]
    assert second["text"] == "You got this"
    assert any("You got this" in u
               for u in build_efmb_plates.build()["unresolved"])


def _choice_frames():
    return [p for p in build_efmb_plates.build()["plates"]
            if p["id"].startswith("choice_lfx_")]


def test_the_choice_screen_is_a_full_frame_pause_menu():
    frames = _choice_frames()
    assert frames, "the choice screen is not scheduled"
    assert all(f["kind"] == "choice" for f in frames)
    assert all(f["position"] == "full" for f in frames)
    assert all(f["animation"] for f in frames)
    assert all(f["group"] == "choice_lfx" for f in frames)


def test_the_menu_comes_up_on_riaans_line_and_is_a_quick_cut():
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    riaan = by_id["chat_riaan_choices"]
    frames = _choice_frames()
    assert frames[0]["at"] >= riaan["at"] + riaan["dur"]
    span = round(frames[-1]["at"] + frames[-1]["dur"] - frames[0]["at"], 3)
    assert span == pytest.approx(build_efmb_plates.CHOICE_HOLD, abs=0.05)


def test_the_frames_are_contiguous():
    """A gap between two frames of a cursor is a flicker."""
    frames = _choice_frames()
    for a, b in zip(frames, frames[1:]):
        assert b["at"] == pytest.approx(a["at"] + a["dur"], abs=2e-3)


def test_the_fighting_option_is_the_legendary_one():
    """"design it like the destiny legendary campaign screen -- the fight one
    should match 'legendary'"."""
    options = build_efmb_plates.CHOICE_OPTIONS
    assert options[0] == "Update your LFX Profile"
    assert options[1] == {"text": "Do it the hard way", "tier": "legendary"}
    from tools import plate
    assert plate.CHOICE_POINTER_TARGET == 1, \
        "the cursor must head for the legendary option"


def test_the_cursor_starts_in_the_centre_and_never_arrives():
    """"starting at the center and then moving towards the fighting choice but
    have it cut so it's a teaser quick cut". A pointer that lands has chosen,
    and the joke is that nobody gets to."""
    from tools import plate
    frames = _choice_frames()
    assert frames[0]["pointer"] == 0.0
    assert frames[-1]["pointer"] == pytest.approx(plate.CHOICE_POINTER_CUT)
    assert plate.CHOICE_POINTER_CUT < 1.0
    progress = [f["pointer"] for f in frames]
    assert progress == sorted(progress)


def test_nothing_on_the_menu_is_selected():
    """A highlight would answer the question, so the boxes never change.

    Checked on the pixels rather than on the source: between the first frame
    and the last, the ONLY thing that may differ is the cursor. A hover state
    on the box the pointer is heading for would light up here.
    """
    from tools import plate
    spec = {"kind": "choice", "label": "Your choices are:",
            "options": build_efmb_plates.CHOICE_OPTIONS}
    start = plate.render_plate({**spec, "pointer": 0.0})
    end = plate.render_plate({**spec, "pointer": plate.CHOICE_POINTER_CUT})
    cursor = plate._cursor()
    changed = sum(1 for a, b in zip(start.getdata(), end.getdata()) if a != b)
    # Two cursor footprints' worth of pixels, and no more: anything else is a
    # box that reacted to being approached.
    assert changed <= 2 * cursor.width * cursor.height



def test_no_card_rides_onto_karenas_jump():
    """"there's an erroneous long walk in the part with karena".

    The chapter card was anchored to source 165.567 -- 0.032 s before the
    walking shot's LAST frame, a whole shot late -- so it came up after the
    walk had cut away and held five seconds over Karena diving into the
    sinkhole, captioned "Glorious Eggroll and the new kids ...".

    The fix is not a nudge: her jump is a NO-PLATE ZONE now, so the guarantee
    is against every future cue rather than against the one that happened to
    hit it.
    """
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    lead = build_efmb.derive_lead()
    jump = next(z for z in build_efmb_plates.NO_PLATE_SRC if "Karena" in z[2])
    jump_in = build_efmb.film_for_source(jump[0], lead)

    card = by_id["walk_chapter"]
    assert card["at"] + card["dur"] <= jump_in + 1e-6, \
        "the chapter card is on Karena's jump again"
    # ... and it is on the walk it names, which is only 1.8 s long.
    walk_in = build_efmb.film_for_source(build_efmb_plates.WALK_IN, lead)
    assert card["at"] >= walk_in
    assert card["at"] - walk_in == pytest.approx(
        build_efmb_plates.WALK_CARD_LEAD, abs=1e-3)
    assert card["dur"] >= build_efmb_plates.MIN_HOLD
