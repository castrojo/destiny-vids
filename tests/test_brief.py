import json

import pytest


from tools.brief import (
    BriefError,
    extract_block,
    has_block,
    parse_brief,
    parse_issue_body,
    propose_brief,
    render_block,
)

MINIMAL = "automatable: yes\n"


def test_extracts_the_fenced_block_and_ignores_surrounding_prose():
    body = (
        "Drop her nameplate right after she removes her helmet 0:14\n\n"
        "```brief\n"
        "automatable: yes\n"
        "```\n\n"
        "more prose after\n"
    )
    assert has_block(body)
    assert extract_block(body).strip() == "automatable: yes"
    assert parse_brief(extract_block(body))["automatable"] == "yes"


def test_bare_yes_and_no_survive_yaml_boolean_coercion():
    # YAML 1.1 reads bare yes/no as booleans. The owner writes the natural
    # thing; the enum stays strings.
    assert parse_brief("automatable: yes\n")["automatable"] == "yes"
    brief = parse_brief("automatable: no\nblocked_on: owner must decide\n")
    assert brief["automatable"] == "no"


def test_yaml_info_string_is_accepted_too():
    body = "```yaml brief\nautomatable: yes\n```\n"
    assert has_block(body)


def test_no_block_is_not_an_error_until_you_ask_for_one():
    assert has_block("just some prose") is False
    with pytest.raises(BriefError, match="no ```brief block"):
        parse_issue_body("just some prose")


def test_automatable_is_required():
    with pytest.raises(BriefError, match="automatable"):
        parse_brief("title: a cut\n")


def test_stopping_must_name_what_would_unblock_it():
    with pytest.raises(BriefError, match="blocked_on is missing"):
        parse_brief("automatable: no\n")
    brief = parse_brief("automatable: no\nblocked_on: owner must supply the subclass\n")
    assert brief["blocked_on"] == "owner must supply the subclass"


@pytest.mark.parametrize("field", ["clean", "footage_tier", "traversal_hero", "casting"])
def test_a_brief_may_not_carry_a_derived_field(field):
    text = f"{MINIMAL}{field}: true\n"
    with pytest.raises(BriefError, match="derived field"):
        parse_brief(text)


def test_derived_field_error_names_the_tool_that_computes_it():
    with pytest.raises(BriefError, match="tools/derive.py"):
        parse_brief(MINIMAL + "clean: true\n")


def test_characters_normalize_to_canonical_casting_keys():
    brief = parse_brief(MINIMAL + "characters: [Saint-14, exo_stranger]\n")
    assert brief["characters"] == ["saint_14", "elsie_bray"]


def test_an_unknown_character_is_reported_not_fatal():
    # Blocking a whole request over one unrecognised word is how a pipeline
    # stops being used. The names that DO resolve still run.
    brief = parse_brief(MINIMAL + "characters: [saint_14, paris_pittman]\n")
    assert brief["characters"] == ["saint_14"]
    assert brief["unresolved"] == [{"field": "characters", "name": "paris_pittman"}]


def test_an_unknown_character_is_still_never_guessed():
    # Degrading is not the same as inventing: nothing may map an unknown name
    # onto the nearest key, because that casts a real person on the owner's
    # behalf.
    brief = parse_brief(MINIMAL + "characters: [osiris_the_second]\n")
    assert brief["characters"] == []
    assert brief["unresolved"][0]["name"] == "osiris_the_second"


def test_a_resolvable_brief_records_nothing_unresolved():
    brief = parse_brief(MINIMAL + "characters: [cayde]\n")
    assert brief["characters"] == ["cayde_6"]
    assert "unresolved" not in brief


def test_a_plate_keeps_owner_copy_when_the_character_is_uncast():
    # The copy is the one thing only the owner can supply -- dropping it
    # because the vocab has not caught up loses the irreplaceable half.
    brief = parse_brief(
        MINIMAL
        + "plates:\n  - character: Paris Pittman\n    copy:\n      name: Paris Pittman\n"
    )
    plate = brief["plates"][0]
    assert "character" not in plate
    assert plate["copy"]["name"] == "Paris Pittman"
    assert brief["unresolved"] == [{"field": "plates", "name": "Paris Pittman"}]


def test_a_known_plate_character_still_normalizes():
    brief = parse_brief(MINIMAL + "plates:\n  - character: cayde\n    at: '0:14'\n")
    assert brief["plates"][0]["character"] == "cayde_6"


def test_owner_authored_plate_copy_survives_verbatim():
    brief = parse_brief(
        MINIMAL
        + "plates:\n"
        + "  - at: '0:14'\n"
        + "    copy:\n"
        + "      label: TRUSTEE // GUARDIAN\n"
        + "      name: Paris Pittman\n"
        + "      class: Harbringer Titan\n"
        + "      title: Kolossus of Kubernetes\n"
    )
    copy = brief["plates"][0]["copy"]
    assert copy["name"] == "Paris Pittman"
    assert copy["title"] == "Kolossus of Kubernetes"


def test_plate_copy_field_set_is_closed():
    with pytest.raises(BriefError, match="schema"):
        parse_brief(MINIMAL + "plates:\n  - copy:\n      pronouns: she/her\n")


def test_a_source_must_name_something():
    with pytest.raises(BriefError, match="schema"):
        parse_brief(MINIMAL + "sources:\n  - note: the good one\n")
    brief = parse_brief(MINIMAL + "sources:\n  - url: https://youtu.be/abc\n")
    assert brief["sources"][0]["url"] == "https://youtu.be/abc"


def test_timecodes_share_the_index_clock():
    with pytest.raises(BriefError, match="schema"):
        parse_brief(MINIMAL + "beats:\n  - at: 14 seconds in\n    note: here\n")
    brief = parse_brief(MINIMAL + "beats:\n  - at: '1:02:03'\n    note: here\n")
    assert brief["beats"][0]["at"] == "1:02:03"


def test_a_brief_is_a_mapping():
    with pytest.raises(BriefError, match="must be a mapping"):
        parse_brief("- just\n- a list\n")


def test_broken_yaml_says_so():
    with pytest.raises(BriefError, match="not valid YAML"):
        parse_brief("automatable: [unclosed\n")


# --- normalization ---------------------------------------------------------

ISSUE_1_BODY = """TRUSTEE // GUARDIAN
Paris Pittman
Harbringer Titan
Kolossus of Kubernetes

https://www.youtube.com/watch?v=9Yh23FKEGt4

Drop her nameplate right after she removes her helmet 0:14

We don't want space shots or any of that, just cinematics
"""


def test_proposal_picks_up_the_source_url():
    proposal = propose_brief("Paris/Jeefy", ISSUE_1_BODY)
    assert proposal["sources"] == [{"url": "https://www.youtube.com/watch?v=9Yh23FKEGt4"}]


def test_proposal_separates_music_from_footage():
    body = (
        "https://www.youtube.com/watch?v=0B9v8VoZrMU\n"
        "https://music.youtube.com/watch?v=oKXIo7EOgXY\n"
    )
    proposal = propose_brief("Harbringer", body)
    assert proposal["music"]["url"].startswith("https://music.youtube.com/")
    assert len(proposal["sources"]) == 1


def test_proposal_keeps_owner_direction_verbatim():
    proposal = propose_brief("Paris/Jeefy", ISSUE_1_BODY)
    assert "We don't want space shots" in proposal["notes"]
    assert any("removes her helmet" in b["note"] for b in proposal["beats"])
    assert any(b["at"] == "0:14" for b in proposal["beats"])


def test_proposal_never_casts_an_unknown_person():
    # "Paris Pittman" is not a lead binding, and a proposal must not invent one.
    proposal = propose_brief("Paris/Jeefy", ISSUE_1_BODY)
    assert "paris_pittman" not in proposal.get("characters", [])


def test_proposal_finds_a_character_that_really_is_cast():
    proposal = propose_brief("Kat", "This one stars Saint-14 throughout.")
    assert proposal["characters"] == ["saint_14"]


def test_a_proposal_is_not_executable_until_the_owner_confirms():
    proposal = propose_brief("Paris/Jeefy", ISSUE_1_BODY)
    assert proposal["automatable"] == "no"
    assert "confirm" in proposal["blocked_on"].lower()


def test_a_rendered_proposal_round_trips_through_the_parser():
    proposal = propose_brief("Kat", "Stars Saint-14. https://youtu.be/abc")
    block = render_block(proposal)
    assert block.startswith("```brief\n")
    assert parse_issue_body(block)["characters"] == ["saint_14"]


def test_schema_file_is_valid_json_schema():
    from jsonschema import Draft202012Validator

    from tools.brief import BRIEF_SCHEMA_PATH

    with BRIEF_SCHEMA_PATH.open(encoding="utf-8") as fh:
        schema = json.load(fh)
    Draft202012Validator.check_schema(schema)


def test_proposal_reads_a_person_the_owner_names():
    # "Starring Kat" -- Kat is cast as Saint-14 in vocab/casting.yaml, so this
    # is a lookup of an existing binding, not a new casting decision.
    proposal = propose_brief("Harbringer", "Starring Kat\nThis one is melancholy.")
    assert proposal["characters"] == ["saint_14"]


def test_proposal_reads_music_the_owner_labelled_as_music():
    body = (
        "https://www.youtube.com/watch?v=dOdPT9fLKEA\n"
        "Start at 6:23\n"
        "Music: https://www.youtube.com/watch?v=IyMHU1D0_Lc\n"
    )
    proposal = propose_brief("Dance", body)
    assert proposal["music"]["url"].endswith("IyMHU1D0_Lc")
    assert [s["url"] for s in proposal["sources"]] == [
        "https://www.youtube.com/watch?v=dOdPT9fLKEA"
    ]


def test_a_persons_name_in_passing_is_not_a_credit():
    # Demonstrated false positives. A one-word owner confirmation must never be
    # able to ratify a colleague into a cut they are not in.
    assert propose_brief("x", "Thanks to Kat for the idea").get("characters") is None
    assert propose_brief("x", "Ask Lenka about the music").get("characters") is None
    assert propose_brief(
        "x", "Paris Pittman suggested this one"
    ).get("characters") is None


def test_a_person_named_as_cast_still_reads():
    assert propose_brief("x", "Starring Kat")["characters"] == ["saint_14"]
    assert propose_brief("x", "Kat plays the lead here")["characters"] == ["saint_14"]
    assert propose_brief(
        "x", "0:14 nameplate for Kat"
    )["characters"] == ["saint_14"]


def test_a_destiny_character_is_read_anywhere():
    # Naming a role is not a claim about a person, so it needs no cue.
    assert propose_brief("x", "The Osiris stairwell shot")["characters"] == ["osiris"]


def test_a_person_mentioned_only_outside_a_casting_line_stays_out():
    body = "Kat filed this one.\nStarring Osiris throughout.\n"
    assert propose_brief("x", body)["characters"] == ["osiris"]


def test_only_yes_and_no_are_forgiven_their_yaml_type():
    # `on` and `off` are YAML 1.1 booleans too, but they are not the enum, and
    # silently translating them would accept a spelling the schema rejects.
    assert parse_brief("automatable: yes\n")["automatable"] == "yes"
    with pytest.raises(BriefError, match="schema"):
        parse_brief("automatable: on\n")
    with pytest.raises(BriefError, match="schema"):
        parse_brief("automatable: true\n")


# --- ensemble direction in a beat (issue #18) --------------------------------

def test_a_proposal_marks_ensemble_direction_as_a_request():
    """"put a bluefin maintainer in here" is a request for a SLOT, so the
    proposal flags it -- for the owner to confirm, as with everything else."""
    proposal = propose_brief("Paris/Jeefy", "4:03 put a bluefin maintainer in here")
    beat = proposal["beats"][0]
    assert beat["at"] == "4:03"
    assert beat["ensemble"] is True
    assert beat["note"] == "4:03 put a bluefin maintainer in here"


def test_a_nameplate_eyebrow_is_not_read_as_an_ensemble_request():
    """The deck's own eyebrow says MAINTAINER; matching that word alone would
    turn somebody's authored credit into an anonymous slot."""
    proposal = propose_brief("x", "0:35 MAINTAINER // GUARDIAN Jeffrey Sica")
    assert "ensemble" not in proposal["beats"][0]


def test_an_ensemble_beat_survives_the_parser():
    brief = parse_brief(
        "automatable: partly\n"
        "blocked_on: the source is not indexed yet\n"
        "beats:\n"
        "  - at: '4:03'\n"
        "    note: put a bluefin maintainer in here\n"
        "    ensemble: true\n"
    )
    assert brief["beats"][0]["ensemble"] is True


def test_an_ensemble_beat_may_not_carry_an_unknown_field():
    """The beat asks for a slot; a field naming who fills it would be a casting
    decision smuggled into a brief."""
    with pytest.raises(BriefError, match="schema"):
        parse_brief(
            "automatable: yes\n"
            "beats:\n"
            "  - at: '4:03'\n"
            "    note: a maintainer here\n"
            "    ensemble: true\n"
            "    person: castrojo\n"
        )
