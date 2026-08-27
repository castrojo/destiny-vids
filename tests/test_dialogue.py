"""Tests for the recovered-dialogue planner (tools/dialogue.py)."""
import copy
import json
from pathlib import Path

import pytest

from tools import avatars, dialogue, plate, readtime  # noqa: E402
from tools.identity import UnknownPerson

RECOVERY_FIXTURE = Path(__file__).with_name("fixtures") / "acts_ii_iii_recovery.json"
VIDEO_ID = "yt_curse_of_osiris_opening_cinematic"

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


def recovery_fixture():
    return json.loads(RECOVERY_FIXTURE.read_text(encoding="utf-8"))


def recovery_by_id(act, bucket):
    return {item["id"]: item for item in recovery_fixture()[act][bucket]}


def source_tuples(record):
    return {
        cue["id"]: (
            cue["character"],
            cue["text"],
            cue["start_sec"],
            cue["end_sec"],
            cue.get("recovered_text"),
        )
        for cue in record["cues"]
    }

def test_speaker_is_the_login_not_the_character_and_not_the_legal_name():
    """Owner, 2026-08-24: "change the dialogue chat boxes to their github
    handles, mrbobbytables and clubanderson."

    A pill credits by login, the way the chat interface it imitates would.
    The Guardian reveal still carries the legal name -- the two are different
    treatments of the same binding, not a disagreement about it."""
    assert dialogue._speaker_for("osiris", LEADS) == "mrbobbytables"
    assert dialogue._speaker_for("sagira", LEADS) == "clubanderson"
    assert LEADS["osiris"]["plate"]["name"] == "Bob Killen", (
        "the reveal is untouched; only the pill changed")


def test_a_person_with_no_login_is_not_rendered_as_a_guessed_identity():
    """A real name is not a GitHub account and must not become one on screen."""
    leads = {"osiris": {"display_name": "somebody", "github": None,
                        "plate": {"name": "Real Name"}}}
    assert dialogue._speaker_for("osiris", leads) is None


@pytest.mark.parametrize("planner", [dialogue.plan_chat, dialogue.plan_script])
def test_an_unknown_lead_login_fails_explicitly(planner):
    """An invalid cast binding is not the same as an intentionally uncast lead."""
    leads = {"osiris": {"person": "definitely-not-a-github-login"}}
    cues = [{"id": "x", "start_sec": 9.0, "end_sec": 12.0,
             "character": "osiris", "text": "..."}]
    with pytest.raises(
        UnknownPerson,
        match=r"unknown GitHub login: 'definitely-not-a-github-login'",
    ):
        planner(cues, SHOTS, leads)


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
    assert first["speaker"] == "clubanderson"
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
    assert [e["speaker"] for e in entries] == ["clubanderson",
                                               "mrbobbytables"]
    assert [e["avatar"] for e in entries] == [
        "renders/avatars/clubanderson.png",
        "renders/avatars/mrbobbytables.png",
    ]
    assert all(e["avatar_required"] is True for e in entries)

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
    data = dialogue.load_dialogue(VIDEO_ID)
    plan = dialogue.load_presentation(VIDEO_ID)
    assert data["cues"], "no cues recovered"
    for cue in data["cues"]:
        assert cue["character"] in ("osiris", "sagira", "mara_sov")
        assert cue["evidence"] in ("vocative", "alternation", "uncertain",
                                   "owner_supplied")
        assert cue["end_sec"] > cue["start_sec"]
        assert cue["text"].strip()
        assert "pin_sec" not in cue
    assert data["text_source"]["method"] == "owner_supplied"
    assert data["speaker_source"]["method"] == "owner_supplied"
    assert plan["mode"] == "script"
    assert plan["start_sec"] == 32.56
    assert plan["standalone_leads"] is False


def test_source_cues_contain_no_presentation_fields():
    forbidden = {"pin_sec", "at", "dur", "position", "fade_in", "fade_out"}
    assert all(forbidden.isdisjoint(cue) for cue in dialogue.load_dialogue(VIDEO_ID)["cues"])


def test_presentation_names_every_live_cue_once():
    cues = dialogue.load_dialogue(VIDEO_ID)["cues"]
    plan = dialogue.load_presentation(VIDEO_ID)
    assert plan["sequence"] == [cue["id"] for cue in dialogue.ordered_cues(cues, plan)]
    assert set(plan["sequence"]) == {cue["id"] for cue in cues}


def test_planning_does_not_mutate_source_records():
    from tools.derive import load_leads

    record = dialogue.load_dialogue(VIDEO_ID)
    before = copy.deepcopy(record)
    dialogue.plan_script(
        record["cues"],
        [shot("long", 0.0, 200.0)],
        load_leads(),
        presentation=dialogue.load_presentation(VIDEO_ID),
    )
    assert record == before


def test_act3_contains_every_recovered_cue_exactly_once():
    record = dialogue.load_dialogue(VIDEO_ID)
    plan = dialogue.load_presentation(VIDEO_ID)
    expected = recovery_by_id("act_iii", "active")
    assert plan["sequence"] == list(expected)
    assert source_tuples(record) == {
        cue_id: tuple(item["source_tuple"])
        for cue_id, item in expected.items()
    }


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
    """d22 follows d28's approved readable hold without overlapping it."""
    plan = dialogue.load_presentation("yt_curse_of_osiris_opening_cinematic")
    assert dialogue.presentation_pin("d13", plan) == 90.0
    assert dialogue.presentation_pin("d20a", plan) == 117.0
    assert dialogue.presentation_pin("d21", plan) == 124.0
    assert dialogue.presentation_pin("d22", plan) == 135.21


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
    d22, d23a and d23b. d22 is reworded to name the CNCF rather than
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
    assert by_id["d23a"] == {
        "id": "d23a",
        "start_sec": 134.64,
        "end_sec": 136.11,
        "character": "mara_sov",
        "evidence": "owner_supplied",
        "text": "Check your email smartass",
        "text_source": "owner_supplied",
        "recovered_text": "The open rate of maintainer emails is 7%",
    }
    assert by_id["d23b"]["text"] == "I don't like this plan"
    for restored in ("d22", "d23a", "d23b"):
        assert by_id[restored]["character"] in ("osiris", "sagira", "mara_sov")

    ids = dialogue.load_presentation(VIDEO_ID)["sequence"]
    assert ids.index("d21") < ids.index("d27") < ids.index("d22")
    assert ids.index("d22") < ids.index("d23a") < ids.index("d23b")
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
         "text": "pinned"},
        {"id": "d03", "start_sec": 6.0, "end_sec": 9.0, "character": "osiris",
         "text": "flows after the pin"},
    ]
    plan = {
        "video_id": "vid",
        "mode": "script",
        "start_sec": 10.0,
        "sequence": ["d01", "d02", "d03"],
        "pins": {"d02": 40.0},
    }
    entries, dropped = dialogue.plan_script(
        cues, [shot("long", 0.0, 100.0)], LEADS,
        presentation=plan, start_at=10.0)
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
    assert 'record = Path("dialogue") / sys.argv[1] / "presentation.json"' in builder
    assert 'presentation.get("standalone_leads", True)' in builder
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
    ids = dialogue.load_presentation(VIDEO_ID)["sequence"]
    assert ids.index("d20a") < ids.index("d20b") < ids.index("d21")


def test_act3_bob_barks_at_the_maintainers_before_asking_for_them():
    """Owner, 2026-08-24: 'add 2 new lines, at 2:13 "mrbobbytables: You need
    to apply, check your email, focus!" then leave everything else.'

    The later readable-hold pass keeps d28 unpinned and moves the maintainer
    exchange to 2:15.21, after d28's required 2.53-second hold.
    """
    data = dialogue.load_dialogue("yt_curse_of_osiris_opening_cinematic")
    cues = data["cues"]
    by_id = {cue["id"]: cue for cue in cues}

    assert by_id["d28"]["text"] == "You need to apply, check your email, focus!"
    assert by_id["d28"]["character"] == "osiris", "Bob Killen's character"
    assert by_id["d28"]["text_source"] == "owner_supplied"
    assert dialogue.presentation_pin("d28", dialogue.load_presentation(VIDEO_ID)) is None, (
        "d28 flows before the separately reseated d22 pin")

    ids = dialogue.load_presentation(VIDEO_ID)["sequence"]
    assert ids.index("d27") < ids.index("d28") < ids.index("d22")
    assert dialogue.presentation_pin("d22", dialogue.load_presentation(VIDEO_ID)) == 135.21, (
        "the exchange follows d28")


def test_act3_priority_dialogue_reseats_stay_in_film_order_and_use_people_logins():
    """Readable film seats live in presentation planning, not source evidence."""
    from tools.derive import load_leads

    data = dialogue.load_dialogue("yt_curse_of_osiris_opening_cinematic")
    cues = {cue["id"]: cue for cue in data["cues"]}
    expected = {
        "d02": (42.00, 45.55, "mrbobbytables",
                "This training repository is the best place to hone their craft"),
        "d03": (45.56, 47.51, "mrbobbytables",
                "Iteration 7: Students serialize instead of parallize"),
        "d06": (52.52, 53.99, "clubanderson",
                "Bluefin's Hive is reprogramming them all as we speak"),
        "d28": (133.20, 135.40, "mrbobbytables",
                "You need to apply, check your email, focus!"),
        "d22": (133.96, 134.63, "mrbobbytables",
                "We need to get a message to the CNCF Maintainers"),
        "d23a": (134.64, 136.11, "angellk",
                 "Check your email smartass"),
    }
    for cue_id, (start, end, speaker, text) in expected.items():
        cue = cues[cue_id]
        assert (cue["start_sec"], cue["end_sec"], cue["text"]) == (
            start, end, text)

    fixed = {"id": "clubanderson-ghost", "at": 80.4, "dur": 2.8}
    plan = dialogue.load_presentation(VIDEO_ID)
    entries, dropped = dialogue.plan_script(
        data["cues"], [shot("long", 0.0, 200.0)], load_leads(),
        busy=[(fixed["at"], fixed["at"] + fixed["dur"])],
        presentation=plan, start_at=plan["start_sec"])
    assert not dropped
    plate.load_manifest_entries([*entries, fixed])
    planned = {entry["id"]: entry for entry in entries}
    for cue_id, (_, _, speaker, _) in expected.items():
        assert planned[cue_id]["speaker"] == speaker
        assert planned[cue_id]["avatar"] == (
            f"renders/avatars/{speaker}.png")
        assert planned[cue_id]["avatar_required"] is True
    assert planned["d22"]["at"] == pytest.approx(135.21)
    assert planned["d23a"]["position"] == "center"
    assert planned["d23a"]["at"] == pytest.approx(
        planned["d22"]["at"] + planned["d22"]["dur"] + dialogue.TAIL_OUT)
    assert planned["d23b"]["at"] == pytest.approx(
        planned["d23a"]["at"] + planned["d23a"]["dur"] + dialogue.TAIL_OUT)
    assert plan["sequence"].index("d28") < plan["sequence"].index("d22")


def test_act3_priority_dialogue_preserves_pre_recovery_delivered_holds():
    """These exact holds come from git ref 90d4124, the last post-#397
    delivered record before Task 4 restored the source windows."""
    from tools.derive import load_leads

    data = dialogue.load_dialogue(VIDEO_ID)
    plan = dialogue.load_presentation(VIDEO_ID)
    entries, dropped = dialogue.plan_script(
        data["cues"],
        [shot("long", 0.0, 200.0)],
        load_leads(),
        presentation=plan,
        start_at=plan["start_sec"],
    )
    assert not dropped
    by_id = {entry["id"]: entry for entry in entries}
    assert {
        cue_id: by_id[cue_id]["dur"]
        for cue_id in ("d02", "d03", "d06", "d28", "d22")
    } == pytest.approx({
        "d02": 3.65,
        "d03": 3.06,
        "d06": 3.06,
        "d28": 2.53,
        "d22": 2.83,
    })


def test_act3_d10_preserves_the_post_397_readable_display_hold():
    """The recovered source window stays evidence; only its old display hold returns."""
    data = dialogue.load_dialogue(VIDEO_ID)
    plan = dialogue.load_presentation(VIDEO_ID)
    d10 = next(cue for cue in data["cues"] if cue["id"] == "d10")

    assert (d10["start_sec"], d10["end_sec"]) == (72.44, 80.87)
    assert dialogue.presentation_hold("d10", plan) == pytest.approx(4.89)
    assert dialogue.planned_hold(d10, plan) == pytest.approx(4.89)
    assert dialogue.planned_hold(d10, plan) >= readtime.required_hold(d10["text"])
    assert dialogue.presentation_pin("d13", plan) == 90.0


def test_act3_full_prepared_manifest_keeps_all_27_cues(tmp_path, monkeypatch):
    """The real fixed-card windows leave the complete recovered exchange buildable."""
    from PIL import Image
    from tools.derive import load_leads

    data = dialogue.load_dialogue(VIDEO_ID)
    plan = dialogue.load_presentation(VIDEO_ID)
    fixed = plate.load_manifest(
        Path("stories/yt_curse_of_osiris_opening_cinematic-fixed-plates.json")
    )
    busy = [
        (float(entry["at"]), float(entry["at"]) + float(entry["dur"]))
        for entry in fixed
    ]
    entries, dropped = dialogue.plan_script(
        data["cues"],
        [shot("long", 0.0, 200.0)],
        load_leads(),
        busy=busy,
        presentation=plan,
        start_at=plan["start_sec"],
    )

    assert not dropped
    assert [entry["id"] for entry in entries] == plan["sequence"]
    assert len(entries) == 27
    planned = {entry["id"]: entry for entry in entries}
    assert planned["d10"]["dur"] == pytest.approx(4.89)
    assert planned["d11"]["at"] < planned["d13"]["at"]
    assert planned["d11"]["at"] + planned["d11"]["dur"] <= planned["d13"]["at"]
    assert planned["d13"]["at"] == 90.0

    manifest = {"plates": [*fixed, *entries], "unresolved": []}
    plate.load_manifest_entries(manifest["plates"])

    monkeypatch.setattr(avatars, "REPO_ROOT", tmp_path)
    avatar_dir = tmp_path / "renders" / "avatars"
    avatar_dir.mkdir(parents=True)
    for login in ("mrbobbytables", "clubanderson", "angellk"):
        Image.effect_noise((256, 256), 64).convert("RGBA").save(
            avatar_dir / f"{login}.png"
        )

    prepared, findings = avatars.prepare_manifest_avatars(manifest)
    assert findings == []
    assert [
        entry["id"] for entry in prepared["plates"] if entry.get("kind") == "chat"
    ] == plan["sequence"]
    plate.load_manifest_entries(prepared["plates"])


def test_act3_dialogue_required_avatar_logins_follow_live_cues():
    assert set(avatars.required_avatar_logins_for_dialogue(VIDEO_ID)) == {
        "mrbobbytables", "clubanderson", "angellk",
    }


def test_build_uncut_credited_fetches_and_prepares_a_persistent_burn_manifest():
    builder = Path("scripts/build_uncut_credited.sh").read_text(encoding="utf-8")
    assert 'python3 -m tools.avatars --manifest "$MANIFEST" --from-actions' in builder
    assert '--prepare "renders/$VIDEO_ID-burn-manifest.json"' in builder
    assert 'python3 tools/plate.py render --manifest "$PREPARED_MANIFEST"' in builder
    assert 'python3 tools/plate.py burn --video "$BASE" --manifest "$PREPARED_MANIFEST"' in builder


def test_act_three_delivery_tracks_the_plate_renderer_that_reaches_pixels():
    delivery = json.loads(
        Path("stories/megacut/delivery.json").read_text(encoding="utf-8")
    )
    assert "tools/plate.py" in delivery["masters"]["III"]["sources"]


def test_target_act_three_rebuild_prints_its_non_blocking_frame_audit_command_last():
    builder = Path("scripts/build_uncut_credited.sh").read_text(encoding="utf-8")
    target_guard = (
        'if [ "$VIDEO_ID" = "yt_curse_of_osiris_opening_cinematic" ]; then'
    )
    audit = (
        "python3 tools/plate_frame_audit.py "
        "--delivered $FINAL --manifest $PREPARED_MANIFEST "
        "--plates-dir $PLATES_DIR "
        "--expected tests/fixtures/acts_ii_iii_recovery.json "
        "--act III --out renders/recovery/act-III --check"
    )
    assert target_guard in builder
    assert f'echo "{audit}"' in builder
    assert builder.index("ffprobe -v error") < builder.index(target_guard)
    assert builder.index(target_guard) < builder.index(f'echo "{audit}"')


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


def test_act3_committed_lanes_include_karena_in_the_center():
    record = dialogue.load_dialogue(VIDEO_ID)
    assert dialogue.lanes_for(record["cues"]) == {
        "osiris": "left",
        "sagira": "right",
        "mara_sov": "center",
    }
