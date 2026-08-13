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
    """
    lead = build_efmb.derive_lead()
    for src_in, src_out, _why in build_efmb_plates.NO_PLATE_SRC:
        zone = (build_efmb.film_for_source(src_in, lead),
                build_efmb.film_for_source(src_out - 0.001, lead))
        for plate in committed()["plates"]:
            start, end = plate["at"], plate["at"] + plate["dur"]
            assert not (start < zone[1] and end > zone[0]), (
                f"{plate['id']} overlaps the burned-in title at {zone}")


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
    plates = committed()["plates"]
    names = [p["name"] for p in plates if p.get("name")]
    assert len(names) == len(set(names)), f"duplicate credit: {names}"


def test_every_plate_can_be_read():
    for plate in committed()["plates"]:
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


def test_the_montage_cues_are_evenly_spaced_across_the_owner_s_window():
    """"spaced out over this montage until the 02:19 - try to space them out
    evenly". Even means even: one step, no drift."""
    cues = _montage(build_efmb_plates.build())
    assert len(cues) == 6
    starts = [p["at"] for p in cues]
    assert starts[0] == build_efmb_plates.MONTAGE_IN
    steps = {round(b - a, 3) for a, b in zip(starts, starts[1:])}
    assert steps == {build_efmb_plates.MONTAGE_STEP}


def test_the_last_announcement_hands_off_before_the_lead_in_banner():
    """The cues exist to fill 1:38 -> 2:19 and then get out of the way; one
    running past 2:19 would be on top of the scene it is introducing."""
    cues = _montage(build_efmb_plates.build())
    assert cues[-1]["at"] + cues[-1]["dur"] <= build_efmb_plates.MONTAGE_OUT


def test_the_montage_never_stacks_a_cue_on_the_badge_already_in_that_window():
    """Dylan Taylor's badge sits at 130.267 inside the montage. An announcement
    trimmed to the 2.2s minimum by the collision guard is not what "evenly"
    means, so the schedule has to clear it on its own."""
    manifest = build_efmb_plates.build()
    dylan = next(p for p in manifest["plates"]
                 if p["id"] == "placeholder_dylan_taylor")
    last = _montage(manifest)[-1]
    assert last["at"] + last["dur"] <= dylan["at"]
    assert last["dur"] == build_efmb_plates.SOLO_HOLD  # never trimmed


def test_the_ranks_escalate_bronze_silver_gold():
    """The escalation is the joke: bronze greets the newcomer, silver flatters
    the incumbent, gold is kept for the ones who left and for the payoff."""
    ranked = [p for p in build_efmb_plates.build()["plates"]
              if p["id"].startswith("announce_")]
    chrome = [(p["id"], p.get("variant"), p.get("trustee")) for p in ranked]
    assert chrome == [
        ("announce_new", "bronze", None),
        ("announce_current", None, True),      # `trustee` IS the silver
        ("announce_emeritus", "leader", None),
        ("announce_all", "leader", None),
    ]


def test_the_announcement_copy_is_reproduced_bracket_spacing_and_all():
    """The owner wrote `[ NEW CONTRIBUTORS ]` with spaces and `[ALL
    CONTRIBUTORS]` without. Authored copy is reproduced, never tidied."""
    by_id = {p["id"]: p for p in build_efmb_plates.build()["plates"]}
    assert by_id["announce_new"]["name"] == "TO [ NEW CONTRIBUTORS ]"
    assert by_id["announce_all"]["name"] == "[ALL CONTRIBUTORS]"
    assert by_id["announce_emeritus"]["name"] == "[ EMERITUS CONTRIBUTORS ]"
    # ... and the typo in the owner's own aside stands until they change it.
    assert (by_id["montage_chat_2"]["text"]
            == "Ready to the #FIGHTFORCONTRIBUTORS?")
    assert all(p["label"] == "AN4-CH3CK-12"
               for p in build_efmb_plates.build()["plates"]
               if p["id"].startswith("announce_"))


def test_copy_the_card_has_no_row_for_is_recorded_not_dropped():
    """A fourth authored line on a three-row card is a punch-list item, not a
    licence to cram it into the class row."""
    unresolved = build_efmb_plates.build()["unresolved"]
    assert any("Look how good you look!" in u for u in unresolved)
    assert any("lead-in banner" in u for u in unresolved)


def test_the_owner_s_asides_are_pfp_chats_and_carry_no_rank():
    chats = [p for p in build_efmb_plates.build()["plates"]
             if p["id"].startswith("montage_chat_")]
    assert [p["kind"] for p in chats] == ["chat", "chat"]
    assert all(p["speaker"] == "Jorge Castro" for p in chats)
    assert not any(p.get("variant") or p.get("trustee") for p in chats)
