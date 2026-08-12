"""The full-frame cards: act slides and the comic title card.

Offline. Nothing here launches a browser -- `cards/render-cards.mjs` needs
playwright and a checkout of the website beside it, neither of which CI has.
What is checked is everything that can rot without one: the manifests the
driver reads, the templates it renders, and `tools/plate.py` refusing to draw a
card it is not the renderer for.
"""
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools import plate  # noqa: E402

REPO = os.path.join(os.path.dirname(__file__), "..")
CARDS = os.path.join(REPO, "cards")
MEGACUT = os.path.join(REPO, "stories", "megacut")


def _load(name):
    with open(os.path.join(MEGACUT, name), encoding="utf-8") as fh:
        return json.load(fh)


def test_every_card_kind_has_a_template():
    """A kind with no template renders nothing and fails at burn time."""
    kinds = set()
    for name in ("megacut-cards.json", "megacut-hero-plates.json"):
        kinds |= {p["kind"] for p in _load(name)["plates"] if p.get("kind") in plate.CARD_KINDS}
    assert kinds, "the megacut manifests carry no full-frame cards any more"
    for kind in kinds:
        assert os.path.exists(os.path.join(CARDS, f"{kind}.html")), kind


def test_plate_py_refuses_to_draw_a_card_and_says_what_does():
    with pytest.raises(ValueError) as excinfo:
        plate.render_plate({"id": "act1", "kind": "act", "act": "I"})
    assert "cards/render-cards.mjs" in str(excinfo.value)


def test_render_all_skips_cards_instead_of_drawing_them(tmp_path):
    """One plates-dir, two renderers: the Python one leaves the cards alone."""
    entries = [
        {"id": "act1", "kind": "act", "at": 0.0, "dur": 5.0, "act": "I"},
        {"id": "kat", "at": 10.0, "dur": 5.0, "position": "left",
         "label": "MAINTAINER // GUARDIAN", "class": "Sentinel Titan",
         "name": "Kat Cosgrove", "title": "Defender Queen of the Lost"},
    ]
    written = plate.render_all(entries, tmp_path)
    assert [p.name for p in written] == ["plate_kat.png"]


def test_the_act_slides_are_numbered_in_the_owners_canonical_order():
    """intro -> endlessdaysmostbeautiful -> mrbobbytables -> kat -> nat ->
    osiris -> 7daystothewolves -> europa -> end credits, numbered I..IX."""
    cards = _load("megacut-cards.json")
    numerals = [p["act"] for p in cards["plates"]]
    assert numerals == ["I", "IV", "V", "VI", "VII", "VIII"]
    # II, III and IX are absent because they have no film; they must stay
    # recorded, or the numbering silently closes up over them.
    unresolved = " ".join(u["what"] for u in cards["unresolved"])
    for missing in ("act II", "act III", "act IX"):
        assert missing in unresolved, missing


def test_act_slides_run_in_time_order_and_carry_a_chapters_field():
    cards = _load("megacut-cards.json")["plates"]
    ats = [p["at"] for p in cards]
    assert ats == sorted(ats)
    for card in cards:
        # The owner's instruction is that every act has chapters. Empty is the
        # honest state until somebody writes them; missing is a dropped field.
        assert "chapters" in card, card["id"]


def test_the_programme_plays_every_card_the_cards_manifest_authored():
    plan = _load("megacut.json")
    authored = {p["id"] for p in _load("megacut-cards.json")["plates"]}
    played = set()
    for item in plan["items"]:
        if item["kind"] != "card":
            continue
        match = re.search(r"plate_(.+)\.png$", item["image"])
        assert match, item["image"]
        played.add(match.group(1))
    assert played == authored


def test_the_comic_card_covers_one_unbroken_window_beside_the_guardian_plates():
    entries = plate.load_manifest(os.path.join(MEGACUT, "megacut-hero-plates.json"))
    comics = sorted((e for e in entries if e.get("kind") == "comic"),
                    key=lambda e: e["at"])
    assert comics, "the comic title card is gone from the hero segment"
    for a, b in zip(comics, comics[1:]):
        # Back to back: a gap would flash the cinematic through the card.
        assert abs((a["at"] + a["dur"]) - b["at"]) < 1e-6
    # load_manifest already refused an overlap against the Guardian plates.
    plates = [e for e in entries if e.get("kind") != "comic"]
    assert all(p["at"] + p["dur"] <= comics[0]["at"] + 1e-6
               or p["at"] >= comics[-1]["at"] + comics[-1]["dur"] - 1e-6
               for p in plates)


def test_a_recast_plate_carries_a_name_and_no_inherited_rows():
    """Cortney and Orlin have no authored identity: name only, never Bob's or
    Laura's label, subclass and title."""
    entries = plate.load_manifest(os.path.join(MEGACUT, "megacut-hero-plates.json"))
    recast = {e["id"]: e for e in entries if e["id"] in ("cortney", "orlin")}
    assert set(recast) == {"cortney", "orlin"}
    for entry in recast.values():
        assert entry["name"]
        for row in ("label", "class", "title", "trustee"):
            assert row not in entry, f"{entry['id']} inherited {row}"
    manifest = _load("megacut-hero-plates.json")
    gaps = " ".join(u["what"] for u in manifest["unresolved"])
    assert "Cortney Nickerson" in gaps and "Orlin" in gaps


def test_the_card_templates_copy_the_sites_own_rules():
    """The cards are a reproduction of the website's CSS, not a new design.

    Each template must say where its rules came from, and carry the tokens the
    site defines -- if somebody rewrites one by hand, this is what notices.
    """
    act = open(os.path.join(CARDS, "act.html"), encoding="utf-8").read()
    assert "CinematicTransition.vue" in act
    assert "wolves-cinematic.scss" in act
    for token in ("--wc-gold", "--wc-white", "--wc-grey", "--wc-line"):
        assert token in act, token

    comic = open(os.path.join(CARDS, "comic.html"), encoding="utf-8").read()
    assert "WolvesIntroOverlay.vue" in comic
    assert "amber-quote" in comic
    # A CSS comment that contains */ silently truncates the stylesheet, and the
    # card then renders as unstyled text on white. This actually happened.
    for name, source in (("act.html", act), ("comic.html", comic)):
        style = source.split("<style>", 1)[1].split("</style>", 1)[0]
        assert style.count("/*") == style.count("*/"), name
