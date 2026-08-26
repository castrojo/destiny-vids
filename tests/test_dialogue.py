"""Tests for the recovered-dialogue planner (tools/dialogue.py)."""
import json
from pathlib import Path

import pytest

from tools import dialogue, plate  # noqa: E402

LEADS = {
    "osiris": {"person": "mrbobbytables", "display_name": "mrbobbytables",
               "github": "mrbobbytables",
               "plate": {"label": "TRUSTEE // GUARDIAN", "name": "Bob Killen"}},
    "sagira": {"person": "clubanderson", "display_name": "clubanderson",
               "github": "clubanderson",
               "plate": {"label": "MAINTAINER // GUARDIAN",
                         "name": "Doctor Andy Anderson"}},
    "ikora_rey": {"person": None, "display_name": None, "plate": None},
}

CUES = [
    {"id": "d01", "start_sec": 10.0, "end_sec": 14.0, "character": "sagira",
     "evidence": "alternation", "text": "Aren't you tired of this?"},
    {"id": "d02", "start_sec": 14.0, "end_sec": 17.0, "character": "osiris",
     "evidence": "alternation", "text": "Fatigue is a distraction."},
    {"id": "d03", "start_sec": 40.0, "end_sec": 44.0, "character": "sagira",
     "evidence": "uncertain", "text": "Ouch."},
]

def shot(segment_id, start, end, role="none", character=None):
    return {"segment_id": segment_id, "start_sec": start, "end_sec": end,
            "casting": {"role": role, "character": character, "slots": 0,
                        "usable": True}}

# The cut holds the first cue's footage but not the third's.
SHOTS = [shot("a", 8.0, 18.0), shot("b", 60.0, 70.0)]

def test_speaker_is_the_login_not_the_character_and_not_the_legal_name():
    """Owner, 2026-08-24: "change the dialogue chat boxes to their github
    handles, @mrbobbytables and @clubanderson."

    A pill credits by login, the way the chat interface it imitates would.
    The Guardian reveal still carries the legal name -- the two are different
    treatments of the same binding, not a disagreement about it."""
    assert dialogue._speaker_for("osiris", LEADS) == "@mrbobbytables"
    assert dialogue._speaker_for("sagira", LEADS) == "@clubanderson"
    assert LEADS["osiris"]["plate"]["name"] == "Bob Killen", (
        "the reveal is untouched; only the pill changed")


def test_a_person_with_no_login_is_not_rendered_as_a_guessed_identity():
    """A real name is not a GitHub account and must not become one on screen."""
    leads = {"osiris": {"display_name": "somebody", "github": None,
                        "plate": {"name": "Real Name"}}}
    assert dialogue._speaker_for("osiris", leads) is None

def test_an_uncast_character_gets_no_card():
    assert dialogue._speaker_for("ikora_rey", LEADS) is None
    entries, dropped = dialogue.plan_chat(
        [{"id": "x", "start_sec": 9.0, "end_sec": 12.0, "character": "ikora_rey",
          "text": "..."}], SHOTS, LEADS)
    assert entries == []
    assert "not cast" in dropped[0]["reason"]

def test_anchored_lines_land_where_their_footage_landed():
    entries, _ = dialogue.plan_chat(CUES, SHOTS, LEADS)
    first = next(e for e in entries if e["id"] == "d01")
    # Shot "a" starts at 8.0 of source and at 0.0 of the cut, so the cue at
    # 10.0 lands 2.0s in.
    assert first["at"] == pytest.approx(2.0)
    assert first["speaker"] == "@clubanderson"
    assert first["kind"] == "chat"
    assert first["avatar"] == "renders/avatars/clubanderson.png"

def test_a_line_whose_footage_is_not_in_the_cut_is_reported_not_dropped_silently():
    # d03 is also the fixture's `uncertain` cue, and chat mode now drops that
    # at the earlier gate (see the attribution test below). This test is about
    # the FOOTAGE check, so keep the cue alive long enough to reach it.
    _, dropped = dialogue.plan_chat(CUES, SHOTS, LEADS, skip_uncertain=False)
    assert any(d["id"] == "d03" and "not in this cut" in d["reason"]
               for d in dropped)

def test_chat_mode_skips_a_speaker_the_anchors_do_not_settle():
    """An unsettled line names one of two real people; it must not be shown.

    `plan_script` has always dropped these. `plan_chat` -- the DEFAULT mode,
    and the one the skill docs recommend -- did not check at all, so a cue the
    recovered record explicitly says it cannot attribute was burned on screen
    crediting whichever person the character happened to be bound to.
    """
    entries, dropped = dialogue.plan_chat(CUES, SHOTS, LEADS)
    assert all(e["id"] != "d03" for e in entries)
    assert any(d["id"] == "d03" and "not settled" in d["reason"] for d in dropped)

def test_chat_mode_still_places_the_settled_lines():
    """The fix drops the unsettled line only -- not the conversation."""
    entries, _ = dialogue.plan_chat(CUES, SHOTS, LEADS)
    assert [e["id"] for e in entries] == ["d01", "d02"]
    assert [e["speaker"] for e in entries] == ["@clubanderson",
                                               "@mrbobbytables"]
    assert [e["avatar"] for e in entries] == [
        "renders/avatars/clubanderson.png",
        "renders/avatars/mrbobbytables.png",
    ]

def test_dialogue_never_double_books_the_screen():
    entries, _ = dialogue.plan_chat(CUES, SHOTS, LEADS)
    plate.load_manifest_entries(entries)  # raises if any two overlap

def test_a_reveal_already_holding_the_screen_wins():
    """Reveals are planned first: an anchored line cannot slide, so it drops."""
    entries, dropped = dialogue.plan_chat(CUES, SHOTS, LEADS,
                                          busy=[(1.5, 6.0)])
    assert all(e["id"] != "d01" for e in entries)
    assert any(d["id"] == "d01" and "reveal" in d["reason"] for d in dropped)

def test_script_mode_keeps_the_exchange_in_spoken_order():
    entries, _ = dialogue.plan_script(CUES, SHOTS, LEADS)
    assert [e["id"] for e in entries] == ["d01", "d02"]
    assert entries[0]["at"] < entries[1]["at"]

def test_script_mode_skips_a_speaker_the_anchors_do_not_settle():
    entries, dropped = dialogue.plan_script(CUES, SHOTS, LEADS)
    assert all(e["id"] != "d03" for e in entries)
    assert any(d["id"] == "d03" and "not settled" in d["reason"] for d in dropped)
    kept, _ = dialogue.plan_script(CUES, SHOTS, LEADS, skip_uncertain=False)
    assert any(e["id"] == "d03" for e in kept)

def test_script_mode_flows_around_a_reveal():
    busy = [(0.0, 6.0)]
    entries, _ = dialogue.plan_script(CUES, SHOTS, LEADS, busy=busy)
    assert entries[0]["at"] >= 6.0
    plate.load_manifest_entries(entries)

def test_script_mode_can_begin_at_the_first_authored_display_cue():
    entries, _ = dialogue.plan_script(
        CUES, [shot("long", 0.0, 100.0)], LEADS, start_at=32.56)
    assert entries[0]["at"] == pytest.approx(32.56)

def test_the_indexed_dialogue_file_is_loadable_and_attributed():
    """The checked-in recovery must stay machine-readable and fully attributed."""
    data = dialogue.load_dialogue("yt_curse_of_osiris_opening_cinematic")
    assert data["cues"], "no cues recovered"
    for cue in data["cues"]:
        assert cue["character"] in ("osiris", "sagira")
        assert cue["evidence"] in ("vocative", "alternation", "uncertain",
                                   "owner_supplied")
        assert cue["end_sec"] > cue["start_sec"]
        assert cue["text"].strip()
    assert data["text_source"]["method"] == "owner_supplied"
    assert data["speaker_source"]["method"] == "owner_supplied"
    assert data["display"]["mode"] == "script"
    assert data["display"]["start_sec"] == 32.56
    assert data["display"]["standalone_leads"] is False
    # The note COUNTS the lines, so pinning it verbatim let it go stale every
    # time one was added or retired -- and it did, silently, because a
    # verbatim assertion of a wrong string still passes. Derive the number
    # instead: the note can only be right or the test red.
    assert data["display"]["note"] == (
        f"Script layout keeps all {len(data['cues'])} lines readable in "
        "order; standalone lead plates are omitted because every dialogue "
        "pill identifies its speaker by github handle (@mrbobbytables, "
        "@clubanderson), and both people are named in full by their own "
        "Guardian reveal cards."
    )


@pytest.mark.parametrize(
    "cue_id, expected",
    [
        ("d20a", (121.44, 124.91, "osiris")),
        ("d20b", (124.92, 127.95, "osiris")),
        ("d21", (127.96, 132.99, "osiris")),
    ],
)
def test_act3_review_cues_pin_exact_timing_and_speaker(cue_id, expected):
    data = dialogue.load_dialogue("yt_curse_of_osiris_opening_cinematic")
    cue = next(cue for cue in data["cues"] if cue["id"] == cue_id)
    assert (cue["start_sec"], cue["end_sec"], cue["character"]) == expected


def test_act3_owner_placed_pins_are_recorded_in_film_seconds():
    """Owner, 2026-08-24: d20a at 1:57, d21 at 2:04 (on the red portal),
    d22 at 2:14.82 -- the seat it held before the sign-punchline cut retired
    it, and the seat the owner named when asking for it back."""
    data = dialogue.load_dialogue("yt_curse_of_osiris_opening_cinematic")
    cues = {cue["id"]: cue for cue in data["cues"]}
    assert cues["d13"]["pin_sec"] == 90.0
    assert cues["d20a"]["pin_sec"] == 117.0
    assert cues["d21"]["pin_sec"] == 124.0
    assert cues["d22"]["pin_sec"] == 134.82


def test_act3_toilmaster_line_is_dropped_and_replaced():
    """Owner, 2026-08-24: d24 is removed entirely; d26 takes its slot.
    Later the same day the tail goes too: 'then that concludes the
    dialogue'. d26 and d25 stay retired; d23b came back with the maintainer
    exchange and is asserted in that test."""
    data = dialogue.load_dialogue("yt_curse_of_osiris_opening_cinematic")
    cues = {cue["id"]: cue for cue in data["cues"]}
    for gone in ("d24", "d26", "d25"):
        assert gone not in cues
    dropped = {cue["id"]: cue for cue in data["dropped"]}
    assert dropped["d24"]["raw"].startswith("If I don't stop the Toilmaster")
    assert dropped["d26"]["raw"] == "Don't worry Maintainers read their emails"
    assert dropped["d25"]["raw"].startswith("I'm sure one of them")


def test_act3_the_maintainer_exchange_is_restored_after_the_hive_line():
    """Owner, 2026-08-24: 'the "we need to get a message to CNCF maintainers"
    discussion is missing at around 2:14 fix that.'

    The exchange was retired the same day (#357 took d23b, d26 and d25; #358
    took d22 and the 7% line) and the owner asked for three of the five back:
    d22 and d23b. d22 is reworded to name the CNCF rather than
    Kubernetes -- 'We need', not 'You need' -- and keeps its old wording as
    recovered_text. d26 and d25 stay retired.

    The Hive quip is no longer the closer, but it still follows the sandbox
    breakout and still precedes the maintainer exchange.
    """
    data = dialogue.load_dialogue("yt_curse_of_osiris_opening_cinematic")
    cues = data["cues"]
    by_id = {cue["id"]: cue for cue in cues}
    assert by_id["d27"]["character"] == "sagira"
    assert by_id["d27"]["text"] == "Hive is the one stuck in the CNCF Sandbox!"
    assert by_id["d27"]["text_source"] == "owner_supplied"

    assert by_id["d22"]["character"] == "osiris"
    assert by_id["d22"]["text"] == (
        "We need to get a message to the CNCF Maintainers")
    assert by_id["d22"]["text_source"] == "owner_supplied"
    assert by_id["d22"]["recovered_text"] == (
        "You need to get a message to the Kubernetes Maintainers")
    assert by_id["d23b"]["text"] == "I don't like this plan"
    for restored in ("d22", "d23b"):
        assert by_id[restored]["character"] in ("osiris", "sagira")

    ids = [c["id"] for c in cues]
    assert ids.index("d21") < ids.index("d27") < ids.index("d22")
    assert ids.index("d22") < ids.index("d23b")
    assert ids[-1] == "d23b", "the 'I don't like this plan' line closes"


def test_act3_restored_lines_are_not_also_recorded_as_dropped():
    """A line cannot be both spoken and retired. Restoring one has to be as
    complete as dropping it, or the record contradicts itself about words
    put in a real person's mouth."""
    data = dialogue.load_dialogue("yt_curse_of_osiris_opening_cinematic")
    live = {cue["id"] for cue in data["cues"]}
    retired = {cue["id"] for cue in data["dropped"]}
    assert not (live & retired)


def test_act3_wait_slow_down_is_dropped_and_d13_stands_alone():
    """Owner, 2026-08-24: 'remove the wait slow down' -- d12 goes entirely.
    Later the same day: the 'Wait.' belongs to d13 after all -- 'the "wait
    that's not our local model" should be in this scene when the ghost
    realizes that the robots can move' -- so d13 keeps its full text, pinned
    to 1:30."""
    data = dialogue.load_dialogue("yt_curse_of_osiris_opening_cinematic")
    cues = {cue["id"]: cue for cue in data["cues"]}
    assert "d12" not in cues
    assert cues["d13"]["text"] == "Wait. That's not our local model."
    dropped = {cue["id"]: cue for cue in data["dropped"]}
    assert dropped["d12"]["raw"] == "Slow down."


def test_act3_tophee_disaster_is_its_own_line():
    """Owner, 2026-08-24: 'We don't want a repeat of the Tophee Disaster'
    should be its own line -- d09 splits into d09a/d09b, d09 retired."""
    data = dialogue.load_dialogue("yt_curse_of_osiris_opening_cinematic")
    cues = {cue["id"]: cue for cue in data["cues"]}
    assert "d09" not in cues
    assert cues["d09a"]["text"] == "You better get that context right"
    assert cues["d09b"]["text"] == "We don't want a repeat of the Tophee Disaster"
    assert cues["d09a"]["character"] == cues["d09b"]["character"] == "sagira"
    dropped = {cue["id"]: cue for cue in data["dropped"]}
    assert "Tophee Disaster" in dropped["d09"]["raw"]


def test_a_pinned_cue_lands_exactly_in_script_mode():
    cues = [
        {"id": "d01", "start_sec": 0.0, "end_sec": 3.0, "character": "osiris",
         "text": "flowing"},
        {"id": "d02", "start_sec": 3.0, "end_sec": 6.0, "character": "sagira",
         "text": "pinned", "pin_sec": 40.0},
        {"id": "d03", "start_sec": 6.0, "end_sec": 9.0, "character": "osiris",
         "text": "flows after the pin"},
    ]
    entries, dropped = dialogue.plan_script(
        cues, [shot("long", 0.0, 100.0)], LEADS, start_at=10.0)
    assert not dropped
    by_id = {e["id"]: e for e in entries}
    assert by_id["d01"]["at"] == pytest.approx(10.0)
    assert by_id["d02"]["at"] == pytest.approx(40.0)
    assert by_id["d03"]["at"] == pytest.approx(40.0 + 3.0 + dialogue.TAIL_OUT)


def test_act3_review_cue_splits_keep_the_owner_marked_hundredth_adjacency():
    data = dialogue.load_dialogue("yt_curse_of_osiris_opening_cinematic")
    cues = {cue["id"]: cue for cue in data["cues"]}
    for earlier, later in (("d09a", "d09b"), ("d20a", "d20b"),
                           ("d20b", "d21")):
        assert cues[later]["start_sec"] == pytest.approx(
            cues[earlier]["end_sec"] + 0.01, abs=1e-9)


def test_act3_fixed_gold_bob_plate_matches_complete_authored_entry():
    manifest = json.loads(
        Path("stories/yt_curse_of_osiris_opening_cinematic-fixed-plates.json")
        .read_text(encoding="utf-8")
    )
    gold = next(plate for plate in manifest["plates"] if plate["id"] == "mrbobbytables-gold")
    assert gold == {
        "id": "mrbobbytables-gold",
        "at": 30.23,
        "dur": 4.0,
        "position": "left",
        "copy_source": "casting",
        "label": "TRUSTEE // GUARDIAN",
        "class": "Voidwalker Warlock",
        "name": "Bob Killen",
        "title": "Reconciler of the Plane",
        "trustee": True,
        "variant": "leader",
    }


def test_the_retirement_conversation_no_longer_opens_act_three():
    """Moved verbatim to act II on 2026-08-24 at the owner's word; the
    verbatim act II copy is pinned in test_efmb_act.py."""
    path = Path("stories/yt_curse_of_osiris_opening_cinematic-fixed-plates.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    plate.load_manifest_entries(data["plates"])
    assert not [p for p in data["plates"] if p["id"].startswith("retirement-")]
    assert data["_anchor"] == (
        "the gold card rides the camera's reveal of Osiris -- the ECU that "
        "opens the reveal (source 33.633 = film 30.233 after the 3.4s PEGI "
        "cut) and settles face-on with Sagira beside him by film 32.6"
    )

    builder = Path("scripts/build_uncut_credited.sh").read_text(encoding="utf-8")
    assert 'FIXED_MANIFEST="stories/$VIDEO_ID-fixed-plates.json"' in builder
    assert 'FIXED_INPUTS+=("$FIXED_MANIFEST")' in builder
    assert 'display.get("standalone_leads", True)' in builder
    assert 'python3 tools/plate.py merge "${FIXED_INPUTS[@]}" --out "$WORK/fixed.json"' in builder
    assert '    --around "$WORK/fixed.json"' in builder


def test_act_three_review_copy_and_splits_are_exact():
    data = dialogue.load_dialogue("yt_curse_of_osiris_opening_cinematic")
    by_id = {c["id"]: c for c in data["cues"]}
    assert by_id["d01"]["text"] == "What a shitshow"
    assert by_id["d20a"]["text"] == "Everyone forgot how to use KVM! We need to split up"
    assert by_id["d20b"]["text"] == "Everyone's making their own and they're all awful"
    assert by_id["d21"]["text"] == "They've broken out of the sandbox"
    assert by_id["d27"]["text"] == "Hive is the one stuck in the CNCF Sandbox!"
    ids = [c["id"] for c in data["cues"]]
    assert ids.index("d20a") < ids.index("d20b") < ids.index("d21")


def test_act3_bob_barks_at_the_maintainers_before_asking_for_them():
    """Owner, 2026-08-24: 'add 2 new lines, at 2:13 "mrbobbytables: You need
    to apply, check your email, focus!" then leave everything else.'

    Only one line of copy was supplied, so one was added. It is seated in the
    2.64 s of pill-free picture between the Hive quip and the maintainer
    exchange -- the gap the owner was looking at -- and it is UNPINNED on
    purpose. A pin at 2:13.00 exactly would run to 2:15.20 and overlap d22,
    whose 2:14.82 seat the owner pinned and then said to leave; flowing puts
    the line as early as it can go without touching a beat that was already
    placed. It lands at 2:12.43 and clears d22 by 0.19 s.
    """
    data = dialogue.load_dialogue("yt_curse_of_osiris_opening_cinematic")
    cues = data["cues"]
    by_id = {cue["id"]: cue for cue in cues}

    assert by_id["d28"]["text"] == "You need to apply, check your email, focus!"
    assert by_id["d28"]["character"] == "osiris", "Bob Killen's character"
    assert by_id["d28"]["text_source"] == "owner_supplied"
    assert "pin_sec" not in by_id["d28"], (
        "pinning it at 2:13.00 would overlap d22, and d22 does not move")

    ids = [cue["id"] for cue in cues]
    assert ids.index("d27") < ids.index("d28") < ids.index("d22")
    assert by_id["d22"]["pin_sec"] == 134.82, "the exchange did not move"


# -- lanes ------------------------------------------------------------------

def _cues(*characters):
    return [{"id": f"c{i}", "character": who} for i, who in enumerate(characters)]


def test_a_two_hander_gets_two_sides_in_first_appearance_order():
    """Sides tell a reply from the same person carrying on before the words
    are read at all. First appearance, so a rebuild cannot swap them."""
    assert dialogue.lanes_for(_cues("osiris", "sagira", "osiris")) == {
        "osiris": "left", "sagira": "right"}
    assert dialogue.lanes_for(_cues("sagira", "osiris")) == {
        "sagira": "left", "osiris": "right"}


def test_a_third_voice_takes_the_centre_and_does_not_disturb_the_other_two():
    """Karena interrupts act III once. Collapsing all 27 pills into one lane
    to accommodate her would reintroduce the exact stacking fault this act
    was fixed for -- so the two-hander keeps its sides and the interloper
    takes the middle, which reads as exactly what she is."""
    lanes = dialogue.lanes_for(_cues("osiris", "sagira", "mara_sov", "osiris"))
    assert lanes == {"osiris": "left", "sagira": "right", "mara_sov": "center"}


def test_beyond_three_voices_a_position_identifies_nobody_so_nobody_gets_one():
    assert dialogue.lanes_for(_cues("a", "b", "c", "d")) == {}


def test_one_voice_is_not_a_conversation_and_needs_no_side():
    assert dialogue.lanes_for(_cues("osiris", "osiris")) == {}
    assert dialogue.lanes_for([]) == {}


def test_act3_lanes_stay_a_two_hander():
    """The committed record, not a fixture: Bob stays left, Doc stays right."""
    data = dialogue.load_dialogue("yt_curse_of_osiris_opening_cinematic")
    lanes = dialogue.lanes_for(data["cues"])
    assert lanes == {"osiris": "left", "sagira": "right"}
