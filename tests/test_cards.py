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


def test_maintitle_has_a_poster_variant_for_the_existing_body_shape():
    template = open(os.path.join(CARDS, "maintitle.html"), encoding="utf-8").read()
    assert 'body[data-variant="poster"] .credits' in template
    assert "poster-cta" in template
    assert "poster-tag" in template
    assert "host.classList.contains('poster')" in template
    assert "if (ch === '.')" in template
    assert "BLUE_LETTERS.includes(ch) || ch === '.'" not in template
    assert 'data-stage="cta"' in template
    assert 'body[data-variant="poster"] .poster-cta .accent' in template
    assert "0 0 2px 0 rgb(196 226 255 / 95%)" in template
    assert "0 0 7px 1px rgb(147 197 253 / 85%)" in template
    assert "0 0 16px 2px rgb(37 99 235 / 45%)" in template


def test_daycard_uses_the_poster_cta_hierarchy_and_an_authored_glyph():
    template = open(os.path.join(CARDS, "daycard.html"), encoding="utf-8").read()
    assert "font-size: clamp(2.8rem, 5vw, 5.2rem)" in template
    assert "font-weight: 900" in template
    assert "letter-spacing: .045em" in template
    assert "line-height: 1.05" in template
    assert ".line:empty { display: none; }" in template
    assert "background:" not in template.split(".card", 1)[1].split("</style>", 1)[0]
    assert "className = 'k8s-o'" in template
    # The glyph that stands in for a letter is placed by the RECORD -- the same
    # `glyph` / `glyph_src` pair cards/ending.html reads -- rather than by this
    # template matching a word. It was hard-coded to 'evolve', so rewriting the
    # copy made the mark vanish silently.
    assert "JSON.parse(p.get('glyph') || 'null')" in template
    assert "p.get('glyph_src')" in template
    assert "lastIndexOf('evolve')" not in template
    assert "mark.onerror = () => mark.replaceWith(document.createTextNode(glyph.token))" in template


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
    numerals = [p["act"] for p in cards["plates"]
                if p.get("kind") != "interstitial"]
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
    # descriptions of the show have drifted. A declared interstitial announces
    # nothing, so it has no chapter title -- but its copy must still be in the
    # doc, or the doc no longer describes what plays.
    import re
    plan = _load("megacut.json")
    for item in plan["items"]:
        if item["kind"] == "card":
            if item.get("interstitial"):
                assert "No one can hear you scream" in doc
                continue
            title = item["chapter"].split(". ", 1)[1]
            assert title in doc, title


def test_every_act_slide_carries_an_audience_facing_chapter_title():
    """`label` is a build note; `chapter` is what the viewer reads.

    A card declared `interstitial` is the sanctioned exception both ways: it
    is a beat inside the programme, not an announcement, so it must NOT carry
    a chapter -- a scrub-bar entry would spoil it (the act VIII ambush rule,
    applied to a gag).
    """
    plan = _load("megacut.json")
    for item in plan["items"]:
        if item["kind"] == "card":
            if item.get("interstitial"):
                assert not item.get("chapter"), item.get("label")
                continue
            assert item.get("chapter"), item.get("label")
            assert "held long" not in item["chapter"]


def test_act_i_megacut_clip_keeps_the_cinematic_tail():
    plan = _load("megacut.json")
    act_i = next(
        item for item in plan["items"]
        if item.get("path", "").endswith("01-intro.mp4")
    )
    assert act_i["trim_from"] == pytest.approx(2.0)
    assert act_i["trim_to"] == pytest.approx(118.2)
    assert act_i["trim_to"] >= 114.2 + 4.0


def test_act_ii_megacut_clip_keeps_its_now_carded_black_head():
    plan = _load("megacut.json")
    act_ii = next(
        item for item in plan["items"]
        if item.get("path", "").endswith("02-endlessformsmostbeautiful.mp4")
    )
    assert act_ii["audio"] == "source"
    assert act_ii["fade_in"] == 0.0
    assert "trim_from" not in act_ii
    assert "approved authored copy for Act II's derived black head" in act_ii["_head_card"]
    assert act_ii["sub_chapters"] == "stories/02-endless-forms-plates.json"


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
    cards = [p for p in _load("megacut-cards.json")["plates"]
             if p.get("kind") != "interstitial"]
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


def test_the_title_card_covers_one_unbroken_window_beside_the_guardian_plates():
    entries = plate.load_manifest(os.path.join(MEGACUT, "megacut-hero-plates.json"))
    covers = sorted((e for e in entries if e["id"] == "title-cover"),
                    key=lambda e: e["at"])
    assert covers, "the title cover is gone from the hero segment"
    assert len(covers) == 1, "one cover, one window -- a second full-frame card would overlap it"
    cover = covers[0]
    # The whole 22.5 - 36.0 window, unbroken: a gap would flash the cinematic
    # through the card.
    assert abs(cover["at"] - 22.5) < 1e-6
    assert abs(cover["at"] + cover["dur"] - 36.0) < 1e-6
    # load_manifest already refused an overlap against the Guardian plates.
    # Chrome rows (caption/context/warning) intentionally coexist with the
    # full-frame cover by occupying their own screen lanes.
    plates = [e for e in entries if e["id"] != "title-cover"
              and e.get("kind") not in plate.CHROME_ROWS]
    assert all(p["at"] + p["dur"] <= cover["at"] + 1e-6
               or p["at"] >= cover["at"] + cover["dur"] - 1e-6
               for p in plates)


def test_a_recast_plate_carries_a_name_and_no_inherited_rows():
    """OrliX has an owner-supplied GitHub identity but no Guardian rows; never
    inherit Laura's label, subclass, or title."""
    entries = plate.load_manifest(os.path.join(MEGACUT, "megacut-hero-plates.json"))
    orlix = next(e for e in entries if e["id"] == "orlix")
    assert orlix["name"] == "OrliX"
    assert orlix["avatar"] == "renders/avatars/orlix.png"
    for row in ("label", "class", "title", "trustee"):
        assert row not in orlix, f"orlix inherited {row}"

    cortney = next(e for e in entries if e["id"] == "cortney")
    assert cortney["name"] == "Cortney Nickerson"
    # 'whatever the Void subclass is' is not a subclass: Void is Voidwalker,
    # Sentinel or Nightstalker depending on her class, which nobody has said.
    assert "class" not in cortney, "a subclass nobody authored was guessed"

    manifest = _load("megacut-hero-plates.json")
    gaps = " ".join(u["what"] for u in manifest["unresolved"])
    assert "Cortney Nickerson" in gaps
    assert "Orlin" not in gaps and "OrliX" not in gaps


def test_the_cover_is_a_full_frame_photo_and_nobody_is_captioned_into_it():
    """Owner, 2026-08-15: '2:14 remove the comic book cover for this segment and
    use a group picture from kubecon contributor summit'. The cover is now a
    Maintainer Summit group photograph, full-frame -- so it carries NO caption
    boxes: a caption over a photograph claims the named person is pictured, and
    the retired captions name people this photograph does not picture. A
    `cover-*` plate reappearing means somebody has put a nameplate over the
    picture, which is the same claim in other chrome.
    """
    entries = plate.load_manifest(os.path.join(MEGACUT, "megacut-hero-plates.json"))
    assert not [e for e in entries if e["id"].startswith("cover-")]

    cover = next(e for e in entries if e["id"] == "title-cover")
    assert cover["kind"] == "photo"
    assert cover["art"] and cover["art_source"]
    # The summit record must be the named source, and the licence lives there.
    assert "summit-photos.json" in cover["art_source"]
    for field in ("captions", "wallpaper_dir", "wallpaper_match", "wallpaper"):
        assert field not in cover, (
            f"{field}: the comic treatment retired with the comic; a "
            "full-frame photograph has no margins and no caption boxes")


def test_the_retired_cover_captions_are_kept_verbatim_in_the_record():
    """The caption copy was owner-authored, so retirement KEEPS it -- the way
    every retired card's strings are kept -- with the reason recorded. Deleting
    it would make restoring the comic cover mean rewriting authored copy.
    """
    cover = next(p for p in _load("megacut-hero-plates.json")["plates"]
                 if p["id"] == "title-cover")
    retired = cover.get("retired")
    assert retired, "the comic cover's copy was retired, not deleted"
    assert retired.get("retired_note"), "a retirement without its reason"
    assert retired["kind"] == "comic"
    assert "wolves.jpg" in retired["art"]

    captions = retired["captions"]
    assert {c["side"] for c in captions} == {"left", "right"}
    # Every authored string the owner wrote for the cover, still in the record.
    text = json.dumps(captions)
    for authored in ("Introducing Rafael and Lakshmi", "Have you met Bluefin?",
                     "BLUEBERRY // HUMAN", "Rafael Castro", "Blueberry Hunter",
                     "Happy 10th Birthday!", "Blueberry Warlock",
                     "Wielder of the Kube", "BLUEFIN", "Really Hungry "):
        assert authored in text, authored
    # The child's name is not on her own box, in the retired copy either.
    warlock = next(c for c in captions if "Blueberry Warlock" in c.get("lines", []))
    assert "Lakshmi" not in json.dumps(warlock)
    # The questions that were open when the copy retired are recorded WITH it,
    # so they come back if the copy ever does.
    note = retired["retired_note"] + retired.get("note", "")
    assert "speciesname" in note
    assert "#90" in note


def test_the_wallpaper_roll_is_recorded_so_a_frame_is_reproducible():
    """A random wallpaper per render is the owner's instruction. A random
    render nobody wrote down cannot be rebuilt, so the driver records the roll
    and can replay it. The title cover no longer rolls one -- a full-frame
    photograph has no margins -- but the comic treatment that did is kept in
    its `retired` record, and the driver's roll-logging stays for every card
    that still carries `wallpaper_dir`.
    """
    cover = next(p for p in _load("megacut-hero-plates.json")["plates"]
                 if p["id"] == "title-cover")
    retired = cover["retired"]
    assert retired["wallpaper_dir"]
    # The directory holds aurora wallpapers too; the owner asked for Bluefin.
    assert re.search(r"bluefin", retired["wallpaper_match"], re.I)
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


def test_the_photo_card_is_full_bleed_and_honours_the_driver_handshake():
    """The photo card is the one template that is NOT a site reproduction --
    the site has no full-frame photo component -- so its contract is pinned
    here instead: the art covers the whole 1920x1080 frame (never a
    square-with-margins), and the render-cards.mjs handshake is honoured or the
    screenshot races the image load."""
    photo = open(os.path.join(CARDS, "photo.html"), encoding="utf-8").read()
    assert "width: 1920px; height: 1080px" in photo
    assert "object-fit: cover" in photo
    assert "__renderReady" in photo
    assert "params.get('art')" in photo
    # No caption or wallpaper MACHINERY: a full-frame photograph has no
    # margins, and copy over a photograph claims the named person is pictured.
    # (The words may appear in the header comment that says why they are out.)
    assert "params.get('captions')" not in photo
    assert "params.get('wallpaper')" not in photo


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
