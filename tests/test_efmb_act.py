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
    anchor_film = build_efmb.edited_film_for_source(build_efmb.SYNC_ANCHOR_SRC)
    assert anchor_film == pytest.approx(
        build_efmb.SYNC_ANCHOR_FILM + build_efmb.INTERRUPTION_SHIFT_SEC,
        abs=1e-6)
    assert (plan["bed_lead_sec"] + plan["source_picture_sec"]
            + plan["bed_tail_sec"]
            == pytest.approx(plan["bed_duration_sec"], abs=0.001))
    assert plan["film_sec"] == pytest.approx(
        plan["bed_duration_sec"] + build_efmb.INTERRUPTION_SHIFT_SEC,
        abs=0.001)


def test_the_hallway_interruption_uses_two_darkened_holds_around_amber():
    sequence = build_efmb.picture_sequence()
    hallway = next(p for p in sequence if p["id"] == "hallway_freeze")
    amber = next(p for p in sequence if p["id"] == "amber_clip")
    after = next(p for p in sequence if p["id"] == "hallway_after_amber")
    returned = next(p for p in sequence if p["id"] == "hallway_return")

    assert hallway["at"] == pytest.approx(build_efmb.HALLWAY_AT, abs=1e-3)
    assert hallway["source_at"] == pytest.approx(323.933, abs=1e-3)
    assert hallway["duration"] == pytest.approx(22.0, abs=1e-3)
    assert hallway["darken"] > 0
    assert amber["source_id"] == build_efmb.AMBER_SOURCE_ID
    assert amber["at"] == pytest.approx(build_efmb.AMBER_AT, abs=1e-3)
    assert amber["source_in"] == pytest.approx(43.0, abs=1e-3)
    assert amber["source_out"] == pytest.approx(53.47, abs=1e-3)
    assert after["at"] == pytest.approx(build_efmb.HALLWAY_AFTER_AMBER_AT, abs=1e-3)
    assert after["duration"] == pytest.approx(21.5, abs=1e-3)
    assert after["darken"] > hallway["darken"]
    assert returned["at"] == pytest.approx(build_efmb.HALLWAY_RETURN_AT, abs=1e-3)
    assert returned["source_in"] == pytest.approx(325.933, abs=1e-3)


def test_kyle_and_eyecantcu_each_get_their_evidenced_picture():
    sequence = build_efmb.picture_sequence()
    eye = next(p for p in sequence if p["id"] == "eyecantcu_tail")
    assert build_efmb.edited_film_for_source(
        build_efmb.KYLE_REVEAL_SRC) == pytest.approx(
            build_efmb.KYLE_REVEAL_AT, abs=1e-3)
    assert eye["at"] == pytest.approx(351.97, abs=1e-3)
    assert eye["source_at"] == pytest.approx(354.6, abs=1e-3)
    assert eye["duration"] == pytest.approx(
        build_efmb.build()["film_sec"] - 351.97, abs=1e-3)
    assert sum(p["duration"] for p in sequence) == pytest.approx(
        build_efmb.build()["film_sec"], abs=1e-3)


def test_the_interruption_audio_uses_only_recorded_sources():
    audio = build_efmb.audio_sequence()
    assert [p["source_id"] for p in audio] == [
        build_efmb.BED_ID,
        build_efmb.HOLD_MUSIC_ID,
        build_efmb.AMBER_SOURCE_ID,
        build_efmb.HOLD_MUSIC_ID,
        build_efmb.BED_ID,
    ]
    assert audio[1]["at"] == pytest.approx(255.433, abs=1e-3)
    assert audio[1]["source_in"] == pytest.approx(6.5, abs=1e-3)
    assert audio[2]["at"] == pytest.approx(build_efmb.AMBER_AT, abs=1e-3)
    assert audio[3]["at"] == pytest.approx(
        build_efmb.HALLWAY_AFTER_AMBER_AT, abs=1e-3)
    assert audio[3]["duration"] == pytest.approx(21.5, abs=1e-3)
    assert audio[4]["at"] == pytest.approx(build_efmb.HALLWAY_RETURN_AT, abs=1e-3)
    assert sum(p["duration"] for p in audio) == pytest.approx(
        build_efmb.build()["film_sec"], abs=1e-3)


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


def test_the_opening_black_head_is_now_a_full_length_card():
    manifest = committed()
    card = manifest["plates"][0]
    assert card["id"] == "opening_black_head"
    assert card["at"] == 0.0
    assert card["dur"] == pytest.approx(build_efmb.build()["bed_lead_sec"], abs=1e-3)
    assert card["kind"] == "title"
    assert card["position"] == "center"
    assert card["title"] == "Eons later"
    assert card["subtitle"] == "Open Source has led us to the stars"
    assert card["body"] == [
        "Maintainer-Guardians hold the line for humanity",
        "Fighting against the Toilmaster and his Legion of Clankers",
        "It all started with Kubernetes.",
    ]
    assert "seen_at_src" not in card


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
        zone = (build_efmb.edited_film_for_source(src_in, lead),
                build_efmb.edited_film_for_source(src_out - 0.001, lead))
        for plate in committed()["plates"]:
            if plate.get("kind") == "banner":
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
    """Retiming may omit a plate; it may not rewrite its authored identity."""
    casting = build_efmb_plates.load_casting()
    assert build_efmb_plates.authored_copy("p5", casting)["name"] == "[ p5 ]"
    assert build_efmb_plates.authored_copy("EyeCantCU", casting)["name"] == \
        "[ EyeCantCU ]"
    names = {p.get("name") for p in committed()["plates"]}
    for banned in ("Robert Sturla", "RJ Trujillo"):
        assert banned not in names


def test_cayde_is_redacted_in_this_act_and_only_by_covering_a_known_name():
    """The joke needs the audience not to be told yet.

    A redaction only ever HIDES something this repo already knows -- the plate
    it covers is recorded beside it -- and it is scoped to act II, because he
    is revealed later in the programme.
    """
    assert "cayde_signoff" not in {p["id"] for p in committed()["plates"]}
    assert build_efmb_plates.CAYDE["redacted_speaker"] == "[ REDACTED ]"
    assert build_efmb_plates.CAYDE["reveals"] == "cayde_6"


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


def test_the_picture_chain_never_uses_filter_complex():
    """ISSUE #88: the same chain, spelled two ways, gives two lengths.

    As `-vf` the act runs 307.99 s. Wrapped in `-filter_complex` the same
    frames come out 299.48 s -- 2.8% fast, 505 frames discarded where the
    rescaled timestamps collide, and ffmpeg exits 0 while doing it.
    """
    source = (REPO_ROOT / "scripts" / "build_efmb.py").read_text()
    render_section = source[source.index("def render("):]
    assert '"-filter_complex", audio_filtergraph()' in render_section
    assert '"-c:v", "copy"' in render_section
    assert "filter_complex" not in build_efmb.NORMALISE_VF


def test_the_bed_is_corrected_with_static_gain_and_never_a_normaliser():
    """The fetched PCM is already safely gained; the mux does not process it."""
    assert build_efmb.MUX_GAIN_DB == 0
    source = (REPO_ROOT / "scripts" / "build_efmb.py").read_text()
    render_section = source[source.index("def render("):]
    for banned in ("loudnorm", "alimiter", "acompressor"):
        assert banned not in render_section


# --- the montage announcements (owner brief, issue #98) ---------------------

def _montage(manifest):
    return [p for p in manifest["plates"]
            if p["id"].startswith(("montage_chat_", "announce_"))]


def test_the_new_face_dialogue_replaces_the_old_montage_asides():
    manifest = build_efmb_plates.build()
    ids = {p["id"] for p in manifest["plates"]}
    assert _montage(manifest) == []
    assert {"late_jrsapi_learn", "late_rochaporto_move"} <= ids
    assert any("two montage asides" in u for u in manifest["unresolved"])


def test_the_announcer_is_gone_entirely():
    """Owner: "Remove all this anacheck stuff for now." All three of his
    blocks -- the ranked montage cards, the TOC payoff pair, and the eyebrow
    on Natewaddington's placard -- and nothing else."""
    manifest = build_efmb_plates.build()
    blob = json.dumps(manifest["plates"])
    assert "AN4-CH3CK" not in blob
    ids = {p["id"] for p in manifest["plates"]}
    assert not {i for i in ids if i.startswith(("announce_", "toc_announce_"))}
    # The placard his eyebrow rode on is gone too now -- the owner cut it out
    # of the climax in a later pass (test_natewaddington_is_out_of_the_climax).
    assert "timed_natewaddington" not in ids
    assert any("anacheck" in u.lower() for u in manifest["unresolved"])


def test_giklab_is_gone_and_nobody_moved_into_his_slot():
    """Owner: "03:16 get rid of giklab". Megacut 3:16 is film 74.4, and the
    only blueberry plate in the act was at 73.400. The SHOT came out, so the
    roster is not reshuffled behind him."""
    assert build_efmb_plates.BLUEBERRY_SHOTS == []
    ids = {p["id"] for p in build_efmb_plates.build()["plates"]}
    assert not {i for i in ids if i.startswith("blueberry_")}


def test_the_new_face_dialogue_hands_off_before_the_lead_in_banner():
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    cues = [by_id[i] for i in (
        "late_jrsapi_learn",
        "late_rochaporto_move",
        "late_metrics_cluster",
        "late_karena_cardio",
    )]
    assert max(p["at"] + p["dur"] for p in cues) <= build_efmb_plates.MONTAGE_OUT


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


def test_the_superseded_owner_typo_remains_in_the_authored_source():
    """Replacement removes scheduling, never rewrites the owner's copy."""
    assert build_efmb_plates.MONTAGE_CHATS[1][2] == (
        "Ready to the #FIGHTFORCONTRIBUTORS?")


def test_copy_the_card_has_no_row_for_is_recorded_not_dropped():
    """A fourth authored line on a three-row card is a punch-list item, not a
    licence to cram it into the class row."""
    unresolved = build_efmb_plates.build()["unresolved"]
    assert any("lead-in banner" in u for u in unresolved)


def test_the_owner_s_superseded_asides_remain_authored_verbatim():
    assert build_efmb_plates.MONTAGE_CHATS == [
        ("castrojo", "Jorge Castro", "Enjoying the metal?"),
        ("castrojo", "Jorge Castro",
         "Ready to the #FIGHTFORCONTRIBUTORS?"),
    ]


# --- "The Long Walk" (owner brief, this round) -----------------------------

def walk_plates():
    return {p["id"]: p for p in committed()["plates"]
            if p["id"].startswith("walk_")}


def test_the_mapped_walk_lines_land_on_their_owner_marks():
    """The mapped 7:25 and 7:34 lines stay on their Act II film seconds."""
    walk = walk_plates()
    assert walk["walk_ge_stream"]["at"] == pytest.approx(178.5, abs=1e-3)
    assert walk["walk_ge_glorious"]["at"] == pytest.approx(187.5, abs=1e-3)


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

    The letterbox banner is exempt: it names nobody. The mapped 7:03 -> 8:26
    pass is exempt too: those are the new owner-authored replacements for the
    walk window, not stray leftover credits from an older pass.
    """
    walk_in = build_efmb.film_for_source(build_efmb_plates.WALK_IN)
    walk_out = build_efmb.film_for_source(build_efmb_plates.WALK_OUT)
    for p in committed()["plates"]:
        if p["id"].startswith("walk_"):
            continue
        if p["id"].startswith("mapped_"):
            continue
        if p.get("kind") in ("banner", "title"):
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


def test_the_mapped_megacut_pass_rewrites_the_walk_window_verbatim():
    """The mapped 7:03 -> 8:26 pass owns this whole window now."""
    by_id = {p["id"]: p for p in committed()["plates"]}

    assert by_id["mapped_saturn_title"]["at"] == pytest.approx(156.666, abs=1e-3)
    assert by_id["mapped_saturn_title"]["title"] == "SATURN"
    assert by_id["mapped_saturn_title"]["subtitle"] == (
        "Nobara Contributor LionHeartP and A1RMAX")
    assert by_id["mapped_kernel_bump"]["text"] == "Time to bump the kernel"

    lionheart = by_id["walk_lionheartp"]
    assert lionheart["label"] == "NOBARA CONTRIBUTOR"
    assert lionheart["class"] == "Sunbreaker Titan"
    assert lionheart["name"] == "LionHeartP"
    assert lionheart["title"] == "Nessus of Nobara"
    assert lionheart["variant"] == "nobara"

    airmax = by_id["walk_A1RM4X"]
    assert airmax["kind"] == "ghost"
    assert airmax["label"] == "NEW CONTRIBUTOR"
    assert airmax["name"] == "A1RM4X"
    assert airmax["title"] == "Useful Youtuber (UNCOMMON)"
    assert airmax["variant"] == "youtube"

    assert by_id["mapped_a1rmax_intro"]["text"] == (
        "Thank you I never thought I could help! "
        "I'm not like you I'm just a lowly user")
    assert by_id["walk_ge_stream"]["text"] == "It's your patch, turn the stream on"
    assert by_id["walk_a1rm4x"]["speaker"] == "LionHeartP"
    assert by_id["walk_a1rm4x"]["text"] == "Let's get these numbers up"
    assert by_id["mapped_lionheartp_hardware"]["text"] == (
        "Why spend the extra dollar to support Linux hardware")
    assert by_id["walk_ge_glorious"]["text"] == (
        "There's nothing glorious about this job")
    assert by_id["walk_ge_lesson"]["speaker"] == "LionHeartP"
    assert by_id["walk_ge_lesson"]["text"] == "Let's go!"
    for i in range(1, 11):
        assert f"mapped_skill_banner_{i}" not in by_id

    for removed in (
        "walk_ge_1", "walk_ge_2", "walk_ge_3",
        "walk_ge_soundcard", "walk_ge_upstream",
    ):
        assert removed not in by_id


def test_the_recovered_828_to_914_copy_is_emitted_verbatim():
    by_id = {p["id"]: p for p in committed()["plates"]}

    expected = {
        "mapped_redacted_blow": ("[redacted]", "Or go blow some shit up"),
        "mapped_owen_slay": ("Owen", "Slay out, Queen!"),
        "mapped_akgraner_kyle": ("akgraner", "Hi sugar, I'm looking for Kyle"),
        "mapped_kyle_sup": ("kylegospo", "Sup"),
        "mapped_kolunmi_disco": ("kolunmi", "Disco!"),
    }
    for plate_id, (speaker, text) in expected.items():
        assert by_id[plate_id]["speaker"] == speaker
        assert by_id[plate_id]["text"] == text

    assert by_id["mapped_hikari_ouch"]["text"] == "Ouch man wtf!"
    assert by_id["mapped_owen_sorry"]["text"] == "Oh sorry my bad"
    assert by_id["mapped_kolunmi_pvp"]["text"] == "Who turned PvP on?"
    assert by_id["mapped_karena_pve"]["text"] == \
        "Don't look at me I only put PvE on Legendary"
    assert by_id["mapped_cam_noone"]["text"] == "Mom no one plays this game"
    assert by_id["mapped_hikari_wait"]["text"] == "Hey wait?!"
    assert by_id["mapped_kolunmi_users"]["text"] == \
        "Are those ... other linux users?"
    assert all(by_id[pid]["kind"] == "chat" for pid, *_ in
               build_efmb_plates.BLACK_CONVERSATION)
    assert by_id["mapped_amber_reveal"]["name"] == "Amber Graner"
    assert by_id["mapped_amber_reveal"]["class"] == "Striker Titan"
    assert by_id["mapped_amber_reveal"]["title"] == "The Iron Standard"
    assert [by_id[f"mapped_akgraner_kindness_{i}"]["text"]
            for i in range(1, 7)] == [
        "Kindness is doing what's right", "For the ecosystem.",
        "For our users.", "And for our maintainers.",
        "Don't be nice.", "Be kind.",
    ]
    assert by_id["mapped_haters"]["name"] == "HATERS"
    assert "solo_EyeCantCU" not in by_id


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


def late_plates():
    return {p["id"]: p for p in committed()["plates"]
            if p["id"].startswith(("late_", "top_banner_", "letterbox_"))}


def test_the_exchange_is_laid_out_around_the_walk_never_on_top_of_it():
    """The greenery exchange keeps its pre-walk questions and loses its old
    post-walk answers to the later mapped pass."""
    lead = build_efmb.derive_lead()
    walk_in = build_efmb.film_for_source(build_efmb_plates.WALK_IN, lead)
    toc = toc_plates()
    pre = [toc[k] for k in ("toc_karena", "toc_joseph_worth", "toc_ricardo")]
    # CHAINED BACKWARD FROM THE WALK, not forward from 2:19. Correcting
    # WALK_IN to the walking shot's real first frame left 7.033 s for three
    # cards that need 7.100, so the exchange moves earlier as a block rather
    # than squeezing Ricardo's question under the readable minimum.
    for p in pre:
        assert p["at"] + p["dur"] <= walk_in + 1e-6
        assert p["dur"] >= build_efmb_plates.MIN_HOLD
    ids = {p["id"] for p in committed()["plates"]}
    for removed in ("toc_joseph_faith", "toc_ricardo_desktop", "toc_joseph_lol"):
        assert removed not in ids


def test_the_remaining_pre_walk_toc_copy_is_reproduced_verbatim():
    toc = toc_plates()
    assert toc["toc_karena"]["text"] == (
        "One hundred thousand bootc volunteers, ready to power up")
    assert toc["toc_ricardo"]["text"] == (
        "You really think they can save open source?")
    # The brief's own speaker tags, not a casting.yaml lookup.
    assert toc["toc_karena"]["speaker"] == "Karena"


def test_the_post_walk_dialogue_is_replaced_by_the_mapped_pass():
    by_id = {p["id"]: p for p in committed()["plates"]}
    assert by_id["mapped_eggroll_didyou"]["at"] == pytest.approx(212.5, abs=1e-3)
    assert by_id["mapped_eggroll_didyou"]["text"] == (
        "You didn't test any of this did you.")
    assert by_id["mapped_pastaq_what_tests"]["at"] == pytest.approx(216.5, abs=1e-3)
    assert by_id["mapped_pastaq_what_tests"]["text"] == "Hey man WHAT tests?"
    assert by_id["mapped_redacted_unlearning"]["speaker"] == "[redacted]"
    assert by_id["mapped_redacted_unlearning"]["at"] == pytest.approx(221.5, abs=1e-3)
    assert by_id["mapped_redacted_options"]["text"] == (
        "Your options are success "
        "Or a lifetime of servitude in the Toilmaster's Packaging Mines")


def test_the_owner_conversation_replaces_the_skill_banners():
    """The 8:18 skill banners are replaced by the owner-supplied conversation."""
    by_id = {p["id"]: p for p in committed()["plates"]}
    ids = {p["id"] for p in committed()["plates"]}
    for i in range(1, 11):
        assert f"mapped_skill_banner_{i}" not in ids

    convo = [
        ("owner_convo_karena", "karena",
         "The Kube always seeks open source potential", 231.500, 2.867),
        ("owner_convo_joseph", "joseph",
         "We can't let The Toilmaster enslave another generation",
         234.617, 3.600),
    ]
    expected_ids = {pid for pid, *_ in convo}
    assert {pid for pid in ids if pid.startswith("owner_convo_")} == expected_ids
    assert not any(pid.startswith("mapped_skill_banner_") for pid in ids)
    for pid, speaker, text, at, dur in convo:
        p = by_id[pid]
        assert p["kind"] == "chat"
        assert p["speaker"] == speaker
        assert p["text"] == text
        assert p["at"] == pytest.approx(at, abs=1e-3)
        assert p["dur"] == pytest.approx(dur, abs=1e-3)
        if speaker == "karena":
            assert p["avatar"].endswith("/karena.png")
        else:
            assert "avatar" not in p and "avatar_url" not in p

    kyle = by_id["mapped_kyle_titanfall"]
    assert kyle["at"] == pytest.approx(239.95, abs=1e-3)
    assert kyle["dur"] == pytest.approx(2.2, abs=1e-3)
    assert kyle["speaker"] == "KyleGospo"
    assert kyle["text"] == "FOR TITANFALL!"

    blow = by_id["mapped_redacted_blow"]
    assert blow["at"] == pytest.approx(242.4, abs=1e-3)
    assert blow["dur"] == pytest.approx(2.6, abs=1e-3)
    assert blow["at"] + blow["dur"] < build_efmb.AMBER_AT


def test_latest_owner_notes_remove_the_wrong_people_and_update_the_lines():
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    assert "owner_convo_krook" not in by_id
    assert "owner_convo_rochaporta_1" not in by_id
    assert "owner_convo_rochaporta_2" not in by_id
    assert by_id["mapped_kyle_titanfall"]["text"] == "FOR TITANFALL!"
    assert by_id["mapped_kyle_titanfall"]["at"] == pytest.approx(239.95, abs=1e-3)
    assert by_id["mapped_redacted_blow"]["text"] == "Or go blow some shit up"
    assert by_id["mapped_redacted_blow"]["at"] == pytest.approx(242.4, abs=1e-3)
    assert by_id["late_rochaporto_cern"]["text"] == (
        "One reference architecture coming up!")


def test_mars_intro_owns_clankers_context_and_red_warning():
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    context = by_id["late_clankers_context"]
    mars = by_id["late_mars_title"]
    warning = by_id["late_poor_technical_decisions"]
    assert context["title"] == "Clankers and Contributors"
    assert context["at"] == pytest.approx(45.2, abs=1e-3)
    assert context["at"] < mars["at"]
    assert warning["kind"] == "miniboss"  # owner: match the kernel bar
    assert warning["position"] == "boss"  # the kernel bar's own position
    assert warning["name"] == "POOR TECHNICAL DECISIONS"


def test_hallway_sequence_uses_authored_order_and_sentence_sized_pills():
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    removed = {
        "mapped_amber_ready", "mapped_reaction_hell",
        "mapped_reaction_yyes_1", "mapped_reaction_yyes_2",
    }
    assert removed.isdisjoint(by_id)
    assert by_id["mapped_akgraner_kyle"]["at"] < by_id["mapped_kolunmi_pvp"]["at"]
    assert by_id["mapped_kolunmi_users"]["at"] < build_efmb.AMBER_AT
    assert by_id["mapped_owen_slay"]["at"] >= build_efmb.HALLWAY_AFTER_AMBER_AT
    kindness = [by_id[f"mapped_akgraner_kindness_{i}"] for i in range(1, 7)]
    assert [p["text"] for p in kindness] == [
        "Kindness is doing what's right",
        "For the ecosystem.",
        "For our users.",
        "And for our maintainers.",
        "Don't be nice.",
        "Be kind.",
    ]
    assert all(p["scale"] > 1 for p in kindness)
    assert kindness[-1]["at"] + kindness[-1]["dur"] < \
        by_id["mapped_which_kyle"]["at"]
    assert by_id["mapped_which_kyle"]["text"] == "Which one of you is Kyle?"


def test_endfight_warnings_and_speakers_match_owner_copy():
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    haters = by_id["mapped_haters"]
    assert haters["kind"] == "miniboss"  # owner: match the kernel bar
    assert haters["name"] == "HATERS"
    assert haters["at"] == pytest.approx(308.2, abs=1e-3)
    assert by_id["mapped_kyle_sup"]["speaker"] == "kylegospo"
    assert by_id["mapped_kyle_sup"]["text"] == "Sup"
    # Owner, 2026-08-19: "sup is a purple titan ... put it when it's zoomed
    # into his face." Film 317.0 is the Titan close-up behind the purple Void
    # shield -- programme 10:00.8, the "around 10:00" he asked for.
    assert by_id["mapped_kyle_sup"]["at"] == pytest.approx(310.4, abs=1e-3)
    assert by_id["mapped_kolunmi_disco"]["speaker"] == "kolunmi"
    assert by_id["mapped_kolunmi_disco"]["at"] == pytest.approx(313.2, abs=1e-3)
    assert by_id["owner_convo_karena"]["avatar"].endswith("/karena.png")


def test_the_owner_conversation_hands_to_kyle_without_overlap():
    by_id = {p["id"]: p for p in committed()["plates"]}
    last = by_id["owner_convo_joseph"]
    kyle = by_id["mapped_kyle_titanfall"]
    blow = by_id["mapped_redacted_blow"]
    assert last["at"] + last["dur"] < kyle["at"]
    assert round(blow["at"] - (kyle["at"] + kyle["dur"]), 3) == pytest.approx(
        0.250, abs=1e-3)


def test_the_owner_conversation_records_unverified_handles():
    gaps = " ".join(committed()["unresolved"])
    assert "owner conversation" in gaps.lower()
    for handle in ("karena", "joseph", "krook", "rochaporta"):
        assert handle in gaps


def test_the_remaining_older_timed_cue_is_still_on_its_mark():
    """The later owner pass replaced the older 4:10/4:20 and tail block, but
    the newer mapped pass replaces the old 4:51 gaslighting seat."""
    assert "timed_jorge" not in {p["id"] for p in committed()["plates"]}
    assert any(p["id"] == "mapped_redacted_blow" and p["at"] == pytest.approx(242.4, abs=1e-3)
               for p in committed()["plates"])


def test_the_late_owner_question_uses_the_current_programme_clock():
    late = late_plates()
    question = late["late_final_question"]
    assert question["at"] == pytest.approx(150.0, abs=1e-3)
    assert question["title"] == "Do we even know who they are?"
    assert not any(p["id"].startswith("quote_") for p in committed()["plates"])
    assert any("6:56 question replaces the earlier five closing quotes" in u
               for u in committed()["unresolved"])


def test_the_ogc_banner_keeps_its_top_lane_over_the_owner_conversation():
    late = late_plates()
    assert not any(key.startswith("letterbox_banner_") for key in late)
    top = [late[f"top_banner_ogc_{i}"] for i in (1, 2)]
    assert all(b["kind"] == "banner" and b["position"] == "boss" for b in top)
    assert all(b["text"] == (
        "#UPSTREAMFIRST | Support the Open Gaming Collective(OGC) | "
        "#UPSTREAMFIRST") for b in top)
    assert top[0]["at"] == pytest.approx(138.5, abs=1e-3)
    assert top[0]["at"] + top[0]["dur"] == pytest.approx(231.5, abs=1e-3)
    assert top[1]["at"] == pytest.approx(239.5, abs=1e-3)
    assert top[1]["at"] + top[1]["dur"] == pytest.approx(
        build_efmb.HALLWAY_AT, abs=1e-3)


def test_the_late_pass_records_only_the_precise_remaining_gaps():
    late_gaps = " ".join(committed()["unresolved"])
    assert "brandtkeller" in late_gaps
    assert "Your Bad Decisions" in late_gaps
    assert "Greg Kroah-Hartman" in late_gaps
    assert "Shuah Khan" in late_gaps
    assert "Tulip Blossom" in late_gaps
    assert "krook" in late_gaps
    assert "kolunmi" in late_gaps
    assert "rare drop in a game" in late_gaps
    assert "hallway-and-dogs frame, Amber's owner-identified" in late_gaps
    assert "EyeCantCU's owner-timed megacut 9:31 seat" in late_gaps
    assert "requested flashing red boss treatment is still missing" in late_gaps
    assert "exact owner-authored words" not in late_gaps


def test_present_day_lands_on_the_owner_mark_with_outro_title_chrome():
    late = late_plates()
    card = late["late_present_day"]
    assert card["kind"] == "title"
    assert card["position"] == "boss"
    assert card["at"] == pytest.approx(46.5, abs=1e-3)
    assert card["title"] == "PRESENT DAY"
    lead = build_efmb.derive_lead()
    assert card["seen_at_src"] == pytest.approx(
        build_efmb.source_for_film(card["at"], lead), abs=1e-3)


def test_the_828_redacted_line_replaces_the_old_gaslighting_seat():
    by_id = {p["id"]: p for p in committed()["plates"]}
    clue = by_id["mapped_redacted_blow"]
    assert clue["at"] == pytest.approx(242.4, abs=1e-3)
    assert clue["speaker"] == "[redacted]"
    assert clue["text"] == "Or go blow some shit up"
    assert "timed_jorge" not in by_id


def test_the_endfight_reseats_kyle_and_eyecantcu_on_evidenced_picture():
    by_id = {p["id"]: p for p in committed()["plates"]}
    kyle = by_id["mapped_kyle_reveal"]
    eye = by_id["mapped_eyecantcu_reveal"]
    assert kyle["at"] == pytest.approx(build_efmb.KYLE_REVEAL_AT, abs=1e-3)
    assert kyle["name"] == "Kyle Gospodnetich"
    assert eye["at"] == pytest.approx(351.97, abs=1e-3)
    assert eye["name"] == "[ EyeCantCU ]"
    assert "solo_EyeCantCU" not in by_id
    assert "stale old 283.666 plate seat remains removed" in \
        " ".join(committed()["unresolved"])


def test_the_remaining_face_shot_dialogue_cards_still_land():
    late = late_plates()
    cluster = [
        late["late_mfahlandt_clean"],
        late["late_kfaseela_gamers"],
        late["late_markmandel_online"],
        late["late_riaankleinhans_close"],
    ]
    learn = late["late_jrsapi_learn"]
    move = late["late_rochaporto_move"]
    metrics = late["late_metrics_cluster"]
    cardio = late["late_karena_cardio"]

    assert all(p["kind"] == "chat" for p in cluster)
    assert [p["speaker"] for p in cluster] == [
        "mfahlandt", "kfaseela", "markmandel", "riaankleinhans"]
    assert [p["at"] for p in cluster] == pytest.approx(
        [88.883, 91.583, 94.283, 96.983], abs=1e-3)
    assert all(p["avatar"].startswith("renders/avatars/") for p in cluster)
    assert learn["at"] == pytest.approx(99.5, abs=1e-3)
    assert learn["speaker"] == "jrsapi"
    assert learn["text"] == "They learn quickly"
    assert move["speaker"] == "rochaporto"
    assert move["text"] == "We need to move!"
    assert move["at"] == pytest.approx(101.95, abs=1e-3)
    assert metrics["kind"] == "chat"
    assert metrics["speaker"] == "jrsapi"
    assert metrics["text"] == (
        "Projects Teams Metrics are strong "
        "They just need mentoring in the right skills")
    assert metrics["avatar"] == "renders/avatars/jrsapi.png"
    assert metrics["at"] == pytest.approx(104.5, abs=1e-3)
    assert cardio["speaker"] == "karena"
    assert cardio["text"] == "Like cardio!"
    assert cardio["at"] == pytest.approx(107.5, abs=1e-3)


def test_the_long_form_speaker_cards_use_chat_chrome_and_verified_avatars():
    by_id = {p["id"]: p for p in committed()["plates"]}
    expected = {
        "mapped_a1rmax_intro": ("A1RM4X", "renders/avatars/A1RM4X.png"),
        "mapped_lionheartp_together": (
            "LionHeartP", "renders/avatars/LionHeartP.png"),
        "mapped_eggroll_title": (
            "GloriousEggroll", "renders/avatars/GloriousEggroll.png"),
        "mapped_redacted_options": ("[redacted]", None),
        "mapped_akgraner_kindness_1": (
            "akgraner", "renders/avatars/akgraner.png"),
    }
    for plate_id, (speaker, avatar) in expected.items():
        entry = by_id[plate_id]
        assert entry["kind"] == "chat"
        assert entry["speaker"] == speaker
        assert entry.get("avatar") == avatar


def test_amber_conversation_fills_the_black_pause_before_sup():
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    conversation = [by_id[pid] for pid, *_ in build_efmb_plates.BLACK_CONVERSATION]
    assert all(p["kind"] == "chat" for p in conversation)
    assert conversation[0]["at"] >= build_efmb.BLACK_CONVERSATION_AT
    assert conversation[-1]["at"] + conversation[-1]["dur"] <= \
        build_efmb.HALLWAY_RETURN_AT
    assert by_id["mapped_kyle_sup"]["at"] > build_efmb.HALLWAY_RETURN_AT
    assert "mapped_amber_ready" not in by_id
    assert "mapped_reaction_hell" not in by_id


def test_the_late_titles_and_last_chats_replace_the_old_conflicting_windows():
    late = late_plates()
    assert late["late_mars_title"]["kind"] == "title"
    assert late["late_mars_title"]["title"] == "Mars"
    assert late["late_mars_title"]["at"] == pytest.approx(116.5, abs=1e-3)
    assert late["late_jrsapi_notes"]["at"] == pytest.approx(134.5, abs=1e-3)
    assert late["late_jrsapi_notes"]["text"] == "Shit are you taking notes?"

    ids = {p["id"] for p in committed()["plates"]}
    for removed in (
        "walk_ge_upstream", "trustee_gregkh", "trustee_shuah_khan",
        "solo_tulilirockz", "timed_krook", "timed_bedazzle",
        "solo_kolunmi",
    ):
        assert removed not in ids
    assert "late_rochaporto_cern" in ids
    assert "late_karena_lessons" in ids
    assert "mapped_kyle_reveal" in ids

def test_out_of_picture_replacements_are_recorded_and_existing_walk_lines_stay():
    manifest = committed()
    ids = {p["id"] for p in manifest["plates"]}
    assert "walk_ge_stream" in ids
    assert "walk_a1rm4x" in ids
    assert "mapped_saturn_title" in ids
    assert "mapped_kyle_titanfall" in ids
    assert "mapped_redacted_blow" in ids
    assert "mapped_kyle_reveal" in ids
    gaps = " ".join(manifest["unresolved"])
    assert "rare drop in a game" in gaps
    assert "hallway-and-dogs frame, Amber's owner-identified" in gaps
    assert "late_saturn_title" not in ids
    assert "late_kernel_bump" not in ids


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


def test_the_correct_opening_guardians_are_on_the_owners_marks():
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    marks = {"opening_sarahnovotny": 13.433, "opening_bdburns": 18.433,
             "og_thockin": 26.433, "og_jbeda": 36.433}
    for pid, at in marks.items():
        assert by_id[pid]["at"] == pytest.approx(at, abs=1e-3)
    assert "og_dims" not in by_id
    assert "og_paganini" not in by_id


def test_the_og_copy_is_the_owners_word_for_word():
    """Including the capitalised NOT, which is the joke."""
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    assert by_id["og_thockin"]["title"] == "Does NOT Come in Peace"
    assert by_id["og_jbeda"]["title"] == "Out of Retirement"


def test_thockin_is_evidenced_on_the_opening_revolver_shot():
    """The approved opening thockin note is the hooded Hunter revolver shot."""
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    thockin = by_id["og_thockin"]
    start = build_efmb.film_for_source(32.800)
    end = build_efmb.film_for_source(34.067)
    assert thockin["seen_at_src"] == pytest.approx(32.800, abs=1e-3)
    assert "revolver" in thockin["why"]
    assert start <= thockin["at"] <= end


def test_removed_opening_people_do_not_remain_in_the_manifest():
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    assert "og_dims" not in by_id
    assert "og_paganini" not in by_id


def test_the_wrong_cncf_community_leadership_card_is_absent():
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    assert "team_cncf_leadership" not in by_id


def test_the_new_dialogue_lands_on_the_owners_seconds():
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    assert by_id["chat_joseph_slop"]["at"] == pytest.approx(70.433, abs=1e-3)
    assert by_id["chat_joseph_slop"]["text"] == "Here comes the slop"
    assert by_id["chat_karena_job"]["at"] == pytest.approx(77.433, abs=1e-3)
    assert by_id["chat_karena_job"]["text"] == "I love this job"
    assert all(p["label"] == "Your choices are:" for p in _choice_frames())


def test_the_new_face_shot_copy_replaces_josephs_old_pair():
    manifest = build_efmb_plates.build()
    by_id = {p["id"]: p for p in manifest["plates"]}
    assert "chat_joseph_master" not in by_id
    assert "chat_joseph_gotthis" not in by_id
    assert by_id["late_jrsapi_learn"]["at"] == pytest.approx(99.5, abs=1e-3)
    assert by_id["late_jrsapi_learn"]["text"] == "They learn quickly"
    assert any("Joseph master/got-this pair" in u
               for u in manifest["unresolved"])


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


def test_the_menu_owns_riaans_line_and_has_room_to_read():
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    frames = _choice_frames()
    assert "chat_riaan_choices" not in by_id
    assert frames[0]["at"] == pytest.approx(
        206.0 - build_efmb_plates.MEGACUT_OFFSET, abs=1e-3)
    assert all(frame["label"] == "Your choices are:" for frame in frames)
    span = round(frames[-1]["at"] + frames[-1]["dur"] - frames[0]["at"], 3)
    assert span == pytest.approx(build_efmb_plates.CHOICE_HOLD, abs=0.05)
    assert span >= 4.0


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



def test_the_long_walk_has_a_marker_but_no_title_card():
    manifest = build_efmb_plates.build()
    assert any(c["title"] == "The Long Walk" for c in manifest["chapters"])
    assert not any(p["id"] == "walk_chapter" for p in manifest["plates"])


def test_bdburns_and_sarah_are_verified_and_scheduled_in_the_opening_gap():
    manifest = build_efmb_plates.build()
    by_id = {p["id"]: p for p in manifest["plates"]}
    bdburns = by_id["opening_bdburns"]
    sarah = by_id["opening_sarahnovotny"]

    assert bdburns["name"] == "Brent D Burns"
    assert bdburns["avatar"] == "renders/avatars/bdburns.png"
    assert bdburns["avatar_url"] == "https://avatars.githubusercontent.com/u/4357134?v=4"
    assert sarah["name"] == "Sarah Novotny"
    assert sarah["avatar"] == "renders/avatars/sarahnovotny.png"
    assert sarah["avatar_url"] == "https://avatars.githubusercontent.com/u/127370?v=4"

    og_thockin = by_id["og_thockin"]
    og_jbeda = by_id["og_jbeda"]
    assert sarah["at"] + sarah["dur"] <= bdburns["at"]
    assert bdburns["at"] + bdburns["dur"] <= og_thockin["at"]
    assert og_thockin["at"] + og_thockin["dur"] <= og_jbeda["at"]
    assert "seen_at_src" not in bdburns
    assert "seen_at_src" not in sarah
    assert bdburns["dur"] == sarah["dur"] == pytest.approx(4.0, abs=1e-3)


def test_opening_three_no_longer_stay_unresolved():
    gaps = " ".join(build_efmb_plates.build()["unresolved"])
    assert "bdburns" not in gaps
    assert "sarahnovotny" not in gaps
    assert "Hunter revolver shot" not in gaps


def test_no_cue_anywhere_ends_inside_a_no_plate_zone():
    """The zone guarantee, for every cue rather than for the one that broke.

    `clamp_hold` shortened a cue to end at `zone_start - at`, which lands its
    LAST FRAME on the zone's FIRST frame. `_zones` already backs the zone's end
    off by a hair; the start had no such guard, so a clamped cue was still on
    the protected shot. Asserting it for the whole manifest is what stops the
    next cue rediscovering it.
    """
    plates = build_efmb_plates.build()["plates"]
    lead = build_efmb.derive_lead()
    # The module's own zone conversion: it backs each zone's END off by a hair
    # because some zone ends on a frame the act cuts (film_for_source raises
    # NotInPicture on those).
    zones = build_efmb_plates._zones(
        lambda src: build_efmb.edited_film_for_source(src, lead))

    for p in plates:
        start = p["at"]
        end = p["at"] + p["dur"]
        for z_in, z_out, why in zones:
            assert not (z_in <= start <= z_out), (
                f"{p['id']} starts inside {why}")
            assert not (z_in <= end <= z_out), (
                f"{p['id']} ends at {end:.3f}s, inside {why} "
                f"({z_in:.3f}-{z_out:.3f})")


def test_gloriouseggroll_has_no_nameplate_over_someone_elses_face():
    """His card was anchored to a shot he is not in (#192).

    src 180.533 is film ~156.7: a ship, then a hangar interior, then an extreme
    close-up of a woman's face at 160.5 -- and the card held across all three
    reading "BLUEBERRY // MAINTAINER / GloriousEggroll". That is a real
    person's name over a different person, which AGENTS.md rule 3 forbids.

    The walking shot the chapter card names is 1.8 s, under MIN_HOLD, so no
    shot in this chapter can carry his credit. Omission credits nobody, so the
    card comes out; his seven lines still name him as the speaker.
    """
    plates = build_efmb_plates.build()["plates"]
    named = [p for p in plates
             if p.get("kind") not in ("chat",)
             and "Glorious" in str(p.get("name", ""))]
    assert named == [], (
        "GloriousEggroll has a nameplate again -- it has no shot to sit on "
        "in this chapter")
    # He is still in the film: his dialogue is untouched.
    spoken = [p for p in plates if p.get("speaker") == "GloriousEggroll"]
    assert len(spoken) >= 3, "his remaining owner-timed dialogue was dropped"



def test_hikariknight_is_out_of_the_eggroll_scene():
    """Owner: "remove hikari from the eggroll scene."

    Only the SCHEDULING goes -- his authored copy stays in the vocab, the way
    Rizzo's and Ahmed Adan's did when this chapter took their shots -- and
    nothing slides up into the hole, because every other cue in the walk is
    pinned to its own source anchor.
    """
    manifest = build_efmb_plates.build()
    ids = {p["id"] for p in manifest["plates"]}
    assert "walk_HikariKnight" not in ids
    assert "walk_HikariKnight" not in ids
    assert any("hikari" in u.lower() for u in manifest["unresolved"]), \
        "a dropped credit is recorded, never silently gone"

    casting = build_efmb_plates.load_casting()
    build_efmb_plates.authored_copy("HikariKnight", casting)  # raises if gone

    # The replacement line now lands on the mapped 7:25 seat instead.
    by_id = {p["id"]: p for p in manifest["plates"]}
    assert by_id["walk_ge_stream"]["at"] == pytest.approx(178.5, abs=1e-3)
    assert by_id["walk_ge_stream"]["text"] == "It's your patch, turn the stream on"


def test_natewaddington_is_out_of_the_climax():
    """Owner: "get rid of the nate wassington in the endless climax in endless."

    His placard stood at film 260.000 -- centre frame, the last card before
    the 269.700 downbeat the act climaxes on. Only the SCHEDULING goes: the
    copy survives in git, the drop is recorded, and nothing slides up into the
    hole, because krook and Jorge are pinned to their own anchors.
    """
    manifest = build_efmb_plates.build()
    ids = {p["id"] for p in manifest["plates"]}
    assert "timed_natewaddington" not in ids
    assert not any("waddington" in i.lower() for i in ids)
    blob = json.dumps(manifest["plates"]).lower()
    assert "waddington" not in blob, "no row of his copy reaches the frame"
    assert any("waddington" in u.lower() for u in manifest["unresolved"]), \
        "a dropped credit is recorded, never silently gone"

    # The later owner-timed pass now spends this stretch on "Mars", but not on
    # Nate. His copy is still gone from the frame.
    assert any(
        p["id"] == "late_mars_title" and 116.0 <= p["at"] <= 119.0
        for p in manifest["plates"])


def test_the_arc_hunter_stays_out_but_kyle_s_reveal_is_restored():
    """kolunmi stays displaced; Kyle's authored reveal card comes back."""
    manifest = build_efmb_plates.build()
    ids = {p["id"] for p in manifest["plates"]}
    assert "solo_kolunmi" not in ids
    assert "mapped_kyle_reveal" in ids
    gap = " ".join(manifest["unresolved"])
    assert "kolunmi" in gap
    assert "KyleGospo's mapped reveal sits on" in gap
    kyle = next(
        p for p in manifest["plates"] if p["id"] == "mapped_kyle_reveal")
    assert kyle["at"] == pytest.approx(build_efmb.KYLE_REVEAL_AT, abs=1e-3)
    assert kyle["name"] == "Kyle Gospodnetich"
    assert kyle["title"] == "The First Knife"
    assert kyle["dur"] >= build_efmb_plates.MIN_HOLD


def test_act_ii_encodes_to_the_delivery_spec_not_a_private_one():
    """Act II's picture is encoded at the repo's DELIVERY rung, with a VUI.

    This act shipped its standalone master with color_space, color_transfer
    and color_primaries all `unknown` -- the only act besides VI that did --
    because both its own builder and the plate burn rolled a private
    `-c:v libx264 -preset medium -crf 18` argv. `conform.video_encode_args`
    is the single place that writes the BT.709 VUI, so anything that does not
    call it cannot tag what it produces, and tools/megacut.py already records
    why "untagged is assumed 709 by most players" is not good enough.

    The same private argv also encoded a delivery master a rung BELOW
    DELIVERY (crf 18/medium against crf 16/slow) on the act issue #86
    measured as the most exposed to it: fog, smoke and dark gradients.
    """
    from tools import conform

    assert build_efmb.X264 == conform.video_encode_args(), \
        "act II must encode to the shared DELIVERY spec, not a private argv"

    argv = " ".join(build_efmb.X264)
    for field in ("-color_primaries", "-color_trc", "-colorspace"):
        assert field in argv, f"{field} missing: the master would ship untagged"
    assert "colorprim=bt709:transfer=bt709:colormatrix=bt709" in argv, \
        "the -x264-params VUI write is what actually lands in the bitstream"
    assert "-crf 16" in argv and "-preset slow" in argv


def test_the_discarded_tail_absorbs_the_rung_change():
    """Every frame of the source is accounted for, on the rung on disk.

    The 2160p VP9 rung is 376.186 s where the 1080p AVC rung this act was
    first cut from was 376.134 s. That 0.052 s must fall in the publisher
    slates the act discards -- if it ever falls inside a kept run, the picture
    moved under a bed that did not, which is the swap SOURCE_SEC guards.
    """
    assert build_efmb.REMOVED[-1][1] == build_efmb.SOURCE_SEC, \
        "the discarded tail must run to the end of the source"
    last_kept = max(b for _, b, _ in build_efmb.RUNS)
    assert last_kept <= build_efmb.REMOVED[-1][0], \
        "no kept run may reach into the tail the rung change lands in"
    assert build_efmb.SOURCE_RUNG, "which rung this act is cut from is recorded"
