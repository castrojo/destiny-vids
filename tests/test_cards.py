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
    """The canonical order, from docs/running-order.md: intro (I) ->
    endlessformsmostbeautiful (II) -> mrbobbytables (III) -> kat (IV) -> nat (V)
    -> 7daystothewolves (VI) -> europa (VII) -> credits (VIII)."""
    cards = _load("megacut-cards.json")
    numerals = [p["act"] for p in cards["plates"]]
    # Acts IV and V share ONE slide -- the owner's call, because their films run
    # 34s and 25s and two 15s slides announced 59s of picture. The numerals are
    # still both there and still in order: this merged the announcement, not the
    # acts, and nothing renumbered around it.
    assert numerals == ["I", "II", "III", "IV\u2013V", "VI", "VII"]
    # VIII is absent DESPITE having a film: the owner wants the credits to
    # surprise ("no credits slide, go right to the metal"), so act VIII is the
    # one act the programme does not announce. It must stay recorded either
    # way, or the numbering silently closes up over it -- and so that a later
    # pass does not "fix" the gap by adding the slide back.
    unresolved = " ".join(u["what"] for u in cards["unresolved"])
    assert "act VIII" in unresolved
    assert "act II --" not in unresolved, (
        "act II has a film now; a gap that outlives its cause is a stale note")


def test_one_person_is_never_two_acts():
    """mrbobbytables was once an empty act AND another act's film, under his
    character's name. One subject, one act."""
    cards = _load("megacut-cards.json")
    subjects = [c.get("title") for c in cards["plates"]]
    assert len(subjects) == len(set(subjects))


def test_the_running_order_doc_is_the_source_of_truth_and_agrees_with_the_plan():
    doc = open(os.path.join(REPO, "docs", "running-order.md"), encoding="utf-8").read()
    assert "source of truth" in doc
    # Every act slide's chapter title must appear in the doc, or the two
    # descriptions of the show have drifted.
    import re
    plan = _load("megacut.json")
    for item in plan["items"]:
        if item["kind"] == "card":
            title = item["chapter"].split(". ", 1)[1]
            assert title in doc, title


def test_every_act_slide_carries_an_audience_facing_chapter_title():
    """`label` is a build note; `chapter` is what the viewer reads."""
    plan = _load("megacut.json")
    for item in plan["items"]:
        if item["kind"] == "card":
            assert item.get("chapter"), item.get("label")
            assert "held long" not in item["chapter"]


def test_the_programme_is_delivered_from_the_wolves_workspace():
    """Prod holds the highest-quality master of each act; the movie goes to
    megacut/. Reading anywhere else would ship a lossy copy of the same cut --
    which is what the retired UPLOAD/ staging folder held."""
    plan = _load("megacut.json")
    assert plan["output"].startswith("/var/home/jorge/Videos/Wolves/megacut/")
    for item in plan["items"]:
        if item["kind"] == "clip" and item["path"].startswith("/"):
            assert "/Videos/Wolves/Prod/" in item["path"], item["path"]


def test_act_slides_run_in_time_order_and_carry_a_chapters_field():
    cards = _load("megacut-cards.json")["plates"]
    ats = [p["at"] for p in cards]
    assert ats == sorted(ats)
    for card in cards:
        # The owner's instruction is that every act has chapters. Empty is the
        # honest state until somebody writes them; missing is a dropped field.
        assert "chapters" in card, card["id"]


def test_the_programme_plays_every_card_the_cards_manifest_authored():
    """Every authored card plays, and every played card is authored.

    A `retired` card is exempt from the first half and only the first half:
    its copy is kept because it was authored and may come back, but nothing
    may play a card the deck does not declare. The one retirement so far is
    act VII's title slide, dropped on the owner's instruction so movement 4
    could hard-cut into Europa (v2.1).
    """
    plan = _load("megacut.json")
    plates = _load("megacut-cards.json")["plates"]
    authored = {p["id"] for p in plates}
    live = {p["id"] for p in plates if not p.get("retired")}
    played = set()
    for item in plan["items"]:
        if item["kind"] != "card":
            continue
        match = re.search(r"plate_(.+)\.png$", item["image"])
        assert match, item["image"]
        played.add(match.group(1))
    assert played <= authored, (
        f"the programme plays undeclared card(s): {played - authored}")
    assert played == live, (
        f"authored-but-unplayed: {live - played}; played-but-not-live: "
        f"{played - live}. A card that should not play needs `retired` with "
        f"a reason, so the decision is recorded rather than inferred.")


def test_every_retired_card_says_why_it_was_retired():
    for card in _load("megacut-cards.json")["plates"]:
        if card.get("retired"):
            assert card.get("retired_note"), card["id"]


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
    """Orlin has no authored identity: name only, never Laura's label, subclass
    and title. Cortney's identity WAS authored (issue #90), so hers is checked
    the other way -- every row present, and the one row nobody wrote absent."""
    entries = plate.load_manifest(os.path.join(MEGACUT, "megacut-hero-plates.json"))
    orlin = next(e for e in entries if e["id"] == "orlin")
    assert orlin["name"]
    for row in ("label", "class", "title", "trustee"):
        assert row not in orlin, f"orlin inherited {row}"

    cortney = next(e for e in entries if e["id"] == "cortney")
    assert cortney["name"] == "Cortney Nickerson"
    # 'whatever the Void subclass is' is not a subclass: Void is Voidwalker,
    # Sentinel or Nightstalker depending on her class, which nobody has said.
    assert "class" not in cortney, "a subclass nobody authored was guessed"

    manifest = _load("megacut-hero-plates.json")
    gaps = " ".join(u["what"] for u in manifest["unresolved"])
    assert "Cortney Nickerson" in gaps and "Orlin" in gaps


def test_the_cover_identities_are_captions_because_a_plate_would_cover_the_art():
    """The owner ruled out nameplates over the cover art. The art is square, so
    a 16:9 frame leaves 420px either side and a 561px Guardian plate cannot fit
    -- the authored identities are carried as caption boxes on the card itself.
    A `cover-*` plate reappearing means somebody has put one back over the ink.
    """
    entries = plate.load_manifest(os.path.join(MEGACUT, "megacut-hero-plates.json"))
    assert not [e for e in entries if e["id"].startswith("cover-")]

    cover = next(e for e in entries if e.get("kind") == "comic")
    captions = cover["captions"]
    assert {c["side"] for c in captions} == {"left", "right"}
    # Every authored string the owner wrote for the cover, still on the card.
    text = json.dumps(captions)
    for authored in ("Introducing Rafael and Lakshmi", "Have you met Bluefin?",
                     "BLUEBERRY // HUMAN", "Rafael Castro", "Blueberry Hunter",
                     "Happy 10th Birthday!", "Blueberry Warlock",
                     "Wielder of the Kube", "BLUEFIN", "Really Hungry "):
        assert authored in text, authored
    # The child's name is not on her own box: see `unresolved`.
    warlock = next(c for c in captions if "Blueberry Warlock" in c.get("lines", []))
    assert "Lakshmi" not in json.dumps(warlock)


def test_the_cover_wallpaper_roll_is_recorded_so_a_frame_is_reproducible():
    """A random wallpaper per render is the owner's instruction. A random
    render nobody wrote down cannot be rebuilt, so the driver records the roll
    and can replay it."""
    cover = next(e for e in _load("megacut-hero-plates.json")["plates"]
                 if e.get("kind") == "comic")
    assert cover["wallpaper_dir"]
    # The directory holds aurora wallpapers too; the owner asked for Bluefin.
    assert re.search(r"bluefin", cover["wallpaper_match"], re.I)
    driver = open(os.path.join(CARDS, "render-cards.mjs"), encoding="utf-8").read()
    assert "wallpapers.json" in driver
    assert "--wallpaper-seed" in driver or "wallpaper-seed" in driver


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


def test_every_act_slide_holds_the_same_length():
    """One house length for slides, so none of them reads as a stall.

    The IV-V slide used to hold 15.0 s -- deliberate pacing while it was the
    one card announcing two acts. Once the Perfume thread ran through the
    show, what sat either side of it changed: movement 3 ends on a dark,
    static shot and the card then froze in silence, so the transition was
    about twenty seconds of nothing moving. Owner, 2026-08-14: "15:31 entire
    transition is too weird and long, make it all fit."

    Asserted as "all equal" rather than "== 5.0" because the house length is
    a choice; having two different ones by accident is the bug.
    """
    plan = _load("megacut.json")
    durs = {round(float(i["dur"]), 3)
            for i in plan["items"] if i["kind"] == "card"}
    assert len(durs) == 1, f"act slides hold different lengths: {sorted(durs)}"
