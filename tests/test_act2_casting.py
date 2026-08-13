"""Act II (Endless Forms Most Beautiful) — the show's first plated act.

The live-action trailers' Guardians are anonymous, so the people the owner
cast onto them live in `ensemble.titles` (keyed by GitHub login), and the
re-authored Karena plate lives on her `mara_sov` lead binding. Every string
here is owner-supplied verbatim; these tests pin the copy so no later pass
"corrects" it, and pin the recorded GAPS so they stay gaps rather than being
filled by a guess — AGENTS.md: a missing word is omitted and recorded, an
invented word is forbidden.
"""

from pathlib import Path

import pytest
import yaml

from tools.derive import load_ensemble_titles, load_leads

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW = (REPO_ROOT / "vocab" / "casting.yaml").read_text(encoding="utf-8")
CASTING = yaml.safe_load(RAW)
TITLES = load_ensemble_titles()
LEADS = load_leads()

ACT2 = ["rochaporto", "joseph_sandoval", "KyleGospo", "p5", "EyeCantCU",
        "wrkode"]


def test_every_act2_identity_is_recorded():
    """A binding that is not written down is a person who goes uncredited."""
    for key in ACT2:
        assert key in TITLES, key


def test_ricardo_rocha_is_wreath_chrome_with_a_deliberately_bare_class():
    spec = TITLES["rochaporto"]
    assert (spec["label"], spec["class"], spec["name"], spec["title"]) == (
        "PRACTITIONER // GUARDIAN", "Hunter",
        "Ricardo Rocha", "Cloud Native Atom Smasher")
    # The owner wrote "Practioner"; the card spells it PRACTITIONER, and his
    # exact wording is recorded in the entry's comment in vocab/casting.yaml.
    assert "Practioner" in RAW, "the owner's exact wording stays recorded"
    # He and Karena are the two most senior: wreath + avatar, but NOT gold.
    assert spec["wreath"] is True
    assert spec["avatar"] == "https://avatars.githubusercontent.com/u/52753?v=4"
    assert "variant" not in spec
    # The class is bare ON PURPOSE: the figure is plainly a hooded Hunter, but
    # no shot shows his element, so no subclass word is authored. The gap is
    # recorded beside the entry; "Nightstalker" or any other is invented.
    assert spec["class"] == "Hunter", (
        "one word short is the authored state — never 'complete' it")


def test_joseph_sandoval_is_gold_without_a_class_row_or_wreath():
    spec = TITLES["joseph_sandoval"]
    assert (spec["label"], spec["name"], spec["title"]) == (
        "PRACTITIONER // GUARDIAN", "Joseph Sandoval",
        "Master Wielder | Uplifter of Users")
    # "He still has a gold badge he's just not the Chair like the other two."
    assert spec["variant"] == "leader"
    assert "wreath" not in spec
    # No subclass is authored, so the class row is OMITTED, never invented.
    assert "class" not in spec


def test_the_kyle_gospodnetich_role_swap_is_deliberate():
    """On screen he is a Sentinel Titan — Kat Cosgrove's authored class. The
    swap is scoped to act II and is NOT an error; the plate itself carries no
    class row and no explanation ("he is special but don't say why")."""
    spec = TITLES["KyleGospo"]
    assert (spec["label"], spec["name"], spec["title"]) == (
        "BLUEBERRY // MAINTAINER", "Kyle Gospodnetich", "The First Knife")
    assert spec["variant"] == "bazzite"
    assert spec["avatar"] == "https://avatars.githubusercontent.com/u/10704358?v=4"
    assert "class" not in spec and "wreath" not in spec


def test_the_bracketed_handles_are_the_name_rows():
    """p5 and EyeCantCU are plated under their HANDLES, exactly as authored —
    the owner chose the handle treatment, so their real names must not appear
    anywhere in this file, let alone on the cards."""
    assert TITLES["p5"]["name"] == "[ p5 ]"
    assert TITLES["EyeCantCU"]["name"] == "[ EyeCantCU ]"
    for key in ("p5", "EyeCantCU"):
        assert TITLES[key]["label"] == "BLUEBERRY // MAINTAINER"
        assert TITLES[key]["variant"] == "bazzite"
    assert TITLES["p5"]["title"] == "Herald of the Hummingbird"
    assert TITLES["EyeCantCU"]["title"] == "Seer of the Truth"
    assert "Sturla" not in RAW and "Trujillo" not in RAW


def test_wrkode_is_promoted_out_of_pending_with_basic_blue_chrome():
    """Issue #14 parked him; the owner authored his plate ("this is his moment
    to shine"). The promotion partially closes #14 — abangser and robertsirc
    are still pending, and his Destiny character stays unbound because the
    #14 source video is still not ingested."""
    assert "wrkode" not in (CASTING["leads"].get("pending") or {})
    assert "wrkode" not in LEADS, "an ensemble title binds no character"
    spec = TITLES["wrkode"]
    assert (spec["label"], spec["name"], spec["title"]) == (
        "MAINTAINER // GUARDIAN", "William Rizzo", "Hammer of Kairos")
    # Basic blue, exactly as authored: no chrome flags at all.
    for flag in ("variant", "trustee", "wreath", "avatar", "class"):
        assert flag not in spec, flag


def test_placeholders_are_recorded_but_render_nothing():
    """Dylan Taylor and Ahmed Adan were named by the owner with NO plate copy.
    Their entries live OUTSIDE `titles`, so the placeholder can never suppress
    the generic ensemble copy they are owed today — a name-only entry would
    silently replace it, which is the suppression the deck rules exist to
    prevent."""
    placeholders = CASTING["ensemble"]["placeholders"]
    assert placeholders["dylan_taylor"]["name"] == "Dylan Taylor"
    assert placeholders["dylan_taylor"]["github"] is None  # none recorded
    assert placeholders["ahmedadan"]["name"] == "Ahmed Adan"
    assert placeholders["ahmedadan"]["github"] == "ahmedadan"
    for key in ("dylan_taylor", "ahmedadan"):
        assert key not in TITLES, "a placeholder is a queue, not a plate"
    # The inertness contract at the vocab level: the roster login finds no
    # authored entry, so tools/plate.py falls through to the generic copy.
    assert TITLES.get("ahmedadan") is None


def test_titles_entries_carry_only_the_closed_field_set():
    """A titles value is splatted into the plate manifest verbatim, so a key
    outside the deck's set would flow onto a card that names a real person.
    Provenance lives in YAML comments beside each entry, never in a key."""
    allowed = {"label", "class", "name", "title", "trustee", "kind",
               "variant", "avatar", "wreath"}
    for login, copy in TITLES.items():
        assert copy, f"{login}: null-valued entries are placeholders and " \
                     "belong in ensemble.placeholders, not titles"
        assert set(copy) <= allowed, (login, set(copy) - allowed)


@pytest.mark.parametrize("key", ACT2)
def test_every_act2_plate_renders(key):
    """Copy that cannot render cannot credit anyone."""
    plate = pytest.importorskip("tools.plate")
    img = plate.render_plate(dict(TITLES[key]))
    assert img.width > 0 and img.height > 0


# --- "The Long Walk" (owner brief, this round) -------------------------------

WALK = ["GloriousEggroll", "HikariKnight", "A1RM4X"]


def test_the_walks_three_are_name_and_chrome_with_no_invented_title():
    """The owner gave each of them an AFFILIATION and no title. The
    affiliation rides as chrome the way Kyle's Bazzite purple does, and the
    title row is OMITTED -- a card with a row missing is the authored state."""
    for key in WALK:
        assert key in TITLES, key
        assert "title" not in TITLES[key], f"{key} was given a title nobody wrote"
        assert "class" not in TITLES[key], f"{key} was given a subclass"


def test_the_two_peers_carry_kyles_own_label():
    """Owner: "We want Eggroll to be a peer of kyle" and "Hikari, another peer
    ... bazzite affiliated like kyle". The label is reproduced from Kyle's
    entry rather than composed, and only the chrome differs."""
    for key in ("GloriousEggroll", "HikariKnight"):
        assert TITLES[key]["label"] == TITLES["KyleGospo"]["label"]
    assert TITLES["GloriousEggroll"]["variant"] == "nobara"
    assert TITLES["HikariKnight"]["variant"] == TITLES["KyleGospo"]["variant"]


def test_gloriouseggroll_is_credited_by_the_handle_the_owner_wrote():
    """GitHub records him as Thomas Crider. The owner wrote him into his own
    dialogue as GloriousEggroll, so that is what the card says and which of
    the two he wants is recorded as his call, not settled by an agent."""
    assert TITLES["GloriousEggroll"]["name"] == "GloriousEggroll"
    assert "Thomas Crider" in RAW, "the alternative stays recorded"


def test_a1rm4x_is_the_one_identity_here_that_is_not_a_github_login():
    """His affiliation IS his channel. The avatar is the channel's own
    picture, never YouTube's logo: a creator's brand is the person."""
    spec = TITLES["A1RM4X"]
    assert spec["label"] == "@A1RM4X // YOUTUBE"
    assert spec["variant"] == "youtube"
    assert spec["avatar"].startswith("https://yt3.googleusercontent.com/")
    # The owner typed "A1RMAX"; the channel is @A1RM4X. Both are recorded.
    assert "A1RMAX" in RAW


@pytest.mark.parametrize("key", WALK)
def test_every_walk_plate_renders(key):
    plate = pytest.importorskip("tools.plate")
    img = plate.render_plate(dict(TITLES[key]))
    assert img.width > 0 and img.height > 0
