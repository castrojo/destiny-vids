"""Trailer 1: the arithmetic, the excision, and the copy.

The render itself is not exercised here -- it needs footage, which is never
committed, and a browser. What IS pinned is everything a later change could
break silently: the runtime the owner asked for, the shot the owner asked to
skip, and the fact that every word on screen is one somebody wrote.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_trailer1 as T  # noqa: E402

@pytest.fixture(scope="module")
def manifest():
    return json.loads(T.MANIFEST.read_text())

def plate(manifest, plate_id):
    return next(p for p in manifest["plates"] if p["id"] == plate_id)

def on_screen_copy(manifest):
    """Only the fields that reach a pixel.

    A retired line still appears in the record -- in the `_owner` brief that
    asked for the change and in the `_copy` note that says what it replaced --
    and that history is the point of those fields. What must never come back is
    the line on SCREEN.
    """
    return json.dumps([{k: v for k, v in entry.items()
                        if k in ("title", "subtitle", "body")}
                       for entry in manifest["plates"]])

# --- the length ---------------------------------------------------------------

def test_the_music_stays_one_minute_fifty():
    assert T.MUSIC_END == pytest.approx(110.020, abs=1e-6)


def test_the_url_holds_five_seconds_after_the_music():
    assert T.URL_HOLD == pytest.approx(5.000, abs=1e-9)
    assert T.TOTAL == pytest.approx(115.020, abs=1e-6)
    assert T.TOTAL == pytest.approx(T.MUSIC_END + T.URL_HOLD, abs=1e-9)
    assert T.TOTAL < 150.0, "over the 2:30 trailer cap"

def test_the_budget_adds_up():
    assert T.PICTURE + T.BRIDGE + T.ENDCARD == pytest.approx(T.TOTAL, abs=1e-9)

def test_the_join_dissolve_is_paid_for_not_ignored():
    """`xfade` emits d1 + d2 - duration.

    The first build added the two trims and asked ffmpeg for a film 0.320 s
    longer than the filtergraph could produce. PICTURE is the real length, and
    the end card is where those 0.320 s are given back.
    """
    trims = T.CUT_OUT + (T.OUT_POINT - T.CUT_IN)
    assert T.PICTURE == pytest.approx(trims - T.JOIN_FADE, abs=1e-9)
    assert T.ENDCARD == pytest.approx(7.500 + T.JOIN_FADE + T.URL_HOLD, abs=1e-9)

# --- the tank -----------------------------------------------------------------

def test_the_tank_shot_is_excised_on_its_own_boundaries():
    """Owner: 'skip the shot of the tank and go right to the iguana'.

    Scene detection on the source puts the jar at 33.640 and the iguana at
    36.320. Both cuts are ON a detected boundary rather than on the owner's
    round ':36', so the join does not land a fifth of a second inside a shot.
    """
    assert T.CUT_OUT == 33.640
    assert T.CUT_IN == 36.320
    assert T.GAP == pytest.approx(2.680, abs=1e-9)

def test_film_time_maps_across_the_excision():
    assert T.source_at(10.0) == 10.0
    assert T.source_at(T.CUT_OUT) == T.CUT_OUT
    # everything after the join is GAP seconds later in the source
    assert T.source_at(T.CUT_OUT + 1) == pytest.approx(T.CUT_IN + 1)
    assert T.source_at(T.PICTURE) == pytest.approx(T.PICTURE + T.GAP)

def test_the_sound_is_not_cut_where_the_picture_is():
    """The music covers the picture edit, so it is taken as one continuous
    span of the source rather than being cut and joined with it."""
    graph = T.filtergraph(json.loads(T.MANIFEST.read_text()), scope="")
    assert f"[0:a]atrim=0:{T.MUSIC_END:.3f}" in graph
    assert graph.count("atrim") == 1

def test_the_title_staging_matches_the_authored_manifest():
    """Written from the failure it catches, twice over.

    stories/trailer-1-plates.json is the authority for this title, and the
    website's src/data/wolves-trailer-plates.ts carries the same window. Only
    TITLE_IN ever disagreed, at 2.000 against the manifest's 11.000, which put
    the card up nine seconds early: it rose on black, hung through the whole
    void, and was stale before the picture bloomed at 12.200 -- read on screen
    as the film starting over.

    The first repair guessed 7.000 and derived STAGE_SWAP from BURST instead of
    re-porting both from the manifest, which desynced three records to fix one.
    So this asserts the builder against the manifest itself rather than against
    any rule about the burst.
    """
    plates = {p["id"]: p for p in json.loads(
        (REPO_ROOT / "stories" / "trailer-1-plates.json").read_text())["plates"]}
    a, b = plates["maintitle-a"], plates["maintitle-b"]

    assert T.TITLE_IN == pytest.approx(a["at"])
    assert T.STAGE_SWAP == pytest.approx(a["at"] + a["dur"])
    assert T.STAGE_SWAP == pytest.approx(b["at"])
    assert T.TITLE_OUT == pytest.approx(b["at"] + b["dur"])
    assert T.TITLE_OUT < 24.880              # clear of the book cut


# --- the wolves fade ----------------------------------------------------------

def test_the_wolves_fade_is_longer_and_the_extra_time_went_to_the_drama():
    """Owner: 'make the wolves fade longer and more dramatic'.

    Longer is the easy half. 'More dramatic' is why the four extra seconds go
    to the TURN and the SINK and not to the holds -- a longer hold is a longer
    still, not a bigger moment.
    """
    assert T.BRIDGE == 14.0                      # the prologue's is 10.0
    assert T.BRIDGE_TURN > 2.600                 # the prologue's turn
    assert T.BRIDGE_DOWN > 3.200                 # the prologue's sink
    assert T.BRIDGE_DAY_HOLD <= 1.200
    assert T.BRIDGE_NIGHT_HOLD <= 1.600

def test_the_music_plays_out_past_where_the_prologue_faded():
    """Owner: 'let the music play out longer than the original video'."""
    assert T.AUDIO_FADE_START > 93.000           # the prologue's fade start
    assert T.AUDIO_FADE_START + T.AUDIO_FADE == pytest.approx(T.MUSIC_END)

def test_the_wolves_howl_lands_before_the_final_fade():
    """The 1:47 howl is the trailer's climax, not a quiet tail detail."""
    assert T.AUDIO_FADE_START == pytest.approx(107.000)
    assert T.AUDIO_FADE == pytest.approx(3.020)

def test_the_lossless_master_is_true_peak_gated_before_delivery():
    """A fresh visual render must not reintroduce a clipping audio master."""
    source = (REPO_ROOT / "scripts" / "build_trailer1.py").read_text()
    assert "peaks.correct_delivered_peak(" in source
    assert "def rerun_with_gain(gain):" in source
    assert "command(manifest, day, night, gain, scope=scope)" in source
    assert source.index("peaks.correct_delivered_peak") < source.index("shutil.copy2")

# --- the copy -----------------------------------------------------------------

OWNER_COPY = {
    "book-a": [
        "Two Generations of Contributors",
        "One at their beginning",
        "One at their end",
        "These are their Real Stories",
    ],
    "book-b": [],
}

@pytest.mark.parametrize("plate_id,lines", OWNER_COPY.items())
def test_the_book_lines_are_the_owners_words_verbatim(manifest, plate_id, lines):
    """Including the punctuation the owner did or did not type.

    Not one of the four lines ends in a full stop, and they keep it that way:
    a mark nobody wrote is still a mark nobody wrote.
    """
    assert plate(manifest, plate_id)["body"] == lines

def test_the_retired_book_line_does_not_come_back(manifest):
    """Owner, 2026-08-17: 'The text box for the message is too wide'.

    The 52-character line is what drove the box to its max width. A later copy
    pass must not quietly restore it.
    """
    screen = on_screen_copy(manifest)
    assert "One, new, one old" not in screen
    assert "Dreaming to build a better future" not in screen

def test_the_book_box_reads_four_lines_over_the_book(manifest):
    """Four short lines need longer than two long ones, so the window opens
    earlier -- but it still has to be over the BOOK, which runs 24.880 ->
    33.640, and it holds to the end of that shot."""
    box = plate(manifest, "book-a")
    assert box["at"] >= 24.880, "the box would open before the book shot"
    assert box["dur"] >= 6.0, "four lines were given less read time than two"
    assert box["at"] + box["dur"] == pytest.approx(T.CUT_OUT, abs=1e-9)

def test_the_end_card_is_the_owners_words_in_the_owners_order(manifest):
    event = plate(manifest, "endcard-event")
    cta = plate(manifest, "endcard-cta")
    assert event["variant"] == cta["variant"] == "poster"
    assert event["stage"] == "title"
    assert cta["stage"] == "cta"
    assert event["title"] == cta["title"] == "KubeCon | CloudNativeCon North America"
    assert event["subtitle"] == cta["subtitle"] == "Salt Lake City, Utah"
    assert event["body"] == cta["body"] == [
        "wolves.projectbluefin.io",
        "#KubeCon",
        "#CloudNativeCon",
        "#7wolves",
    ]

def test_the_end_card_poster_uses_no_new_copy_field(manifest):
    """The title card's shape is `title` / `subtitle` / `body[]`.

    A venue card is exactly the sort of thing somebody adds a row to. Nobody
    did.
    """
    for plate_id in ("endcard-event", "endcard-cta"):
        card = plate(manifest, plate_id)
        copy_fields = {k for k in card
                       if not k.startswith(("_", "note")) and k not in
                       {"id", "kind", "at", "dur", "stage", "variant",
                        "angle", "size", "anchor", "anchor_out", "walk"}}
        assert copy_fields == {"title", "subtitle", "body"}

def test_the_day_cards_are_two_messages_in_the_owners_words(manifest):
    """Owner, 2026-08-17: 'Change the evolve or die into two messages ...
    have the text be Extinction is the Rule / Survival is the Exception'."""
    cards = T.day_cards(manifest)
    assert [c["title"] for c in cards] == [
        "Extinction is the Rule",
        "Survival is the Exception",
    ]
    for card in cards:
        assert "subtitle" not in card
        assert "body" not in card

def test_the_retired_day_lines_do_not_come_back(manifest):
    """The marquee line has now been rewritten three times; each retired line
    must stay retired."""
    screen = on_screen_copy(manifest)
    for retired in ("Evolve or Die",
                    "The Final Shape is Kindness",
                    "Wolves aren't Evil"):
        assert retired not in screen

def test_the_two_day_cards_lead_into_the_kubecon_reveal(manifest):
    """Owner: 'lengthem them to show them lead to the kubecon text ... all
    three text messages should floow smoothly into one reveal'.

    Longer than the single card they replace, adjacent rather than separated by
    a hold, both finished before the end card so the reveal lands on empty
    night wolves -- and all of it inside the existing bridge, which is why the
    music-timed end card never had to move.
    """
    first, second = T.day_cards(manifest)
    assert first["dur"] > 3.4 and second["dur"] > 3.4, "not lengthened"
    assert first["at"] >= T.PICTURE, "a day card starts before the bridge"
    gap = second["at"] - (first["at"] + first["dur"])
    assert 0 <= gap <= 1.0, f"the two messages do not flow: {gap:.3f} s apart"
    endcard_at = T.PICTURE + T.BRIDGE
    assert second["at"] + second["dur"] <= endcard_at
    assert plate(manifest, "endcard-event")["at"] == pytest.approx(endcard_at)

def test_the_day_cards_sit_in_the_wallpapers_dark_band(manifest):
    """Owner, 2026-08-17: 'lower the extinction and other line to be more in
    the dark area for readability'.

    The seat is authored on the plate rather than baked into the template,
    which is a real distinction here: the default 38% is right for a card over
    a different image, and this pair is over one whose horizon is its brightest
    band. 58% is measured, not nudged: it is the dark meadow, and it is not the
    66% of the first pass, which covered the foreground wolf's head."""
    for card in T.day_cards(manifest):
        assert card["placement"] == "low"
    template = (REPO_ROOT / "cards" / "daycard.html").read_text()
    assert 'body[data-placement="low"] .card { top: 58%; }' in template
    assert "dataset.placement = p.get('placement')" in template

def test_the_day_cards_are_overlaid_from_the_record(manifest):
    """Their windows are authored copy timing, so the graph takes them from the
    manifest. The first build hard-coded one card's fades in the script, which
    is how a second card becomes a code change instead of a plate."""
    graph = T.filtergraph(manifest, scope="")
    for card in T.day_cards(manifest):
        at = card["at"] - T.PICTURE
        assert f"enable=between(t\\,{at:.3f}\\," in graph
    assert graph.count("[bridgepre]") == 2, "one in, one consumed by card one"
    assert "[bridge]" in graph

def test_the_kubernetes_helm_is_placed_by_the_record_not_by_a_word(manifest):
    """The mark used to be hard-coded to the letter 'o' of 'evolve', so the
    copy could not change without it silently vanishing. It now travels as the
    `glyph` / `glyph_src` pair cards/ending.html already defines."""
    first, second = T.day_cards(manifest)
    assert first["glyph"] == {"token": "o", "word": "Extinction"}
    assert first["glyph_src"] == "renders/marks/kubernetes.svg"
    assert "glyph" not in second, "one mark across the pair, on the first line"
    card = (REPO_ROOT / "cards" / "daycard.html").read_text()
    assert "lastIndexOf('evolve')" not in card
    assert "JSON.parse(p.get('glyph')" in card

def test_the_trailer_credit_diverges_from_the_prologue_deliberately(manifest):
    """These two records used to be pinned together so they could not drift.
    They now differ on purpose, so this asserts the divergence instead.

    Owner, 2026-08-22: "Make it 'Music by Nightwish | Action by Destiny' keep
    the sear. Underneath in the same font, centered and in the same font...
    'Open Source Fights Back'". That instruction was given for the TRAILER. The
    prologue is the film's own opening and changing it is a separate decision
    the owner has not made, so it keeps its line until they say otherwise.

    The pipe survives in row one because the sear is drawn from it. Row two has
    no pipe, so `sear` falls through to `blueify` in cards/maintitle.html and it
    renders as a plain centred row in the same face.
    """
    trailer_body = [
        "Music by Nightwish | Action by Destiny",
        "Open Source Fights Back",
    ]
    for plate_id in ("maintitle-a", "maintitle-b"):
        assert plate(manifest, plate_id)["body"] == trailer_body, (
            "both staged cards carry the same body, so the rows hold their "
            "space and the two PNGs are identical above them")

    assert " | " in trailer_body[0], "the sear is drawn from the pipe"
    assert " | " not in trailer_body[1], "row two is plain, not seared"

    prologue = json.loads(
        (REPO_ROOT / "stories" / "00-prologue-plates.json").read_text())
    prologue_bodies = {
        entry["id"]: entry["body"] for entry in prologue["plates"]
        if entry["id"] in ("maintitle-a", "maintitle-b")
    }
    prologue_line = "Music by Nightwish | Action by Bungie"
    assert prologue_bodies == {
        "maintitle-a": [prologue_line],
        "maintitle-b": [prologue_line],
    }, "the prologue is untouched; changing the film's opening needs its own yes"


def test_no_plate_here_names_a_person(manifest):
    """The owner chose an unattributed plate over a chat pill, and a chat pill
    is the only card in this deck that carries a speaker. Nothing here credits
    anybody with saying anything."""
    for entry in manifest["plates"]:
        assert "speaker" not in entry
        assert "name" not in entry
        assert entry["kind"] in ("maintitle", "bookline", "daycard")

# --- the motion ---------------------------------------------------------------

def test_both_book_lines_are_fixed_fancy_subtitles(manifest):
    """Owner: 'dont make the boxes move ... think of it as a fancy subtitle'."""
    for plate_id in ("book-a", "book-b"):
        assert plate(manifest, plate_id)["anchor"] == plate(manifest, plate_id)["anchor_out"]

def test_the_book_lines_use_the_simple_box_treatment(manifest):
    """Owner: 'I just want a simple box overlay'."""
    for plate_id in ("book-a", "book-b"):
        assert plate(manifest, plate_id)["variant"] == "box"

def test_the_book_box_is_set_at_the_size_the_owner_chose(manifest):
    """Owner, 2026-08-17: 'the box in the first part is too small, increase
    text size and the vertical space inbetween each sentence', then 'D is the
    best' of four mockups rendered over the book frame itself."""
    card = (REPO_ROOT / "cards" / "bookline.html").read_text()
    box = card.split('body[data-variant="box"] .line')[1]
    assert "font-size: 3.8rem;" in box
    assert "line-height: 1.7;" in box

def test_the_box_leaves_with_the_page_and_never_before_it(manifest):
    """Owner, 2026-08-17: "HIDE THE WORDS ON THE BOOK PAGE WITH THIS SLIDE AND
    THEN FADE INTO THE IGUANA", after "you fade the box differently than the
    book page so the words 'you needed' show up".

    The box is composited onto the HEAD LEG, so the join dissolve carries the
    page and the box out as one picture. Any overlay on the joined film has an
    out of its own, and the page goes on printing underneath -- so every frame
    between the box leaving and the picture cutting reveals the words the box
    was there to cover.
    """
    box = plate(manifest, "book-a")
    assert box["fade"] == 0
    graph = T.filtergraph(manifest, scope="")
    chunk = next(c for c in graph.split(";") if c.endswith("[bk0]"))
    assert "fade=" not in chunk, "the box has a ramp of its own again"
    seat = next(c for c in graph.split(";") if c.endswith("[headbox]"))
    assert seat.startswith("[head][bk0]overlay="), "the box left the head leg"
    assert f"\\,{T.CUT_OUT:.3f})" in seat, "the box stops before the head does"
    join = next(c for c in graph.split(";") if "xfade" in c and "[tail]" in c)
    assert join.startswith("[headbox][tail]"), "the join no longer carries it"

def test_the_box_covers_the_page_for_the_whole_time_it_prints(manifest):
    """The page keeps printing under the box -- 'In order to be born', then
    'you needed' in close-up -- and every one of those words is inside the
    box's footprint. That is what the box is for, so it may not open late or
    close early."""
    box = plate(manifest, "book-a")
    assert box["at"] + box["dur"] >= T.CUT_OUT - 1e-9, \
        "the box closes before the picture leaves the book"

def test_the_box_panel_is_opaque(manifest):
    """At 90% the page's printed lyric was legible through the panel even at
    full card opacity -- a second set of words behind ours."""
    card = (REPO_ROOT / "cards" / "bookline.html").read_text()
    box = card.split('body[data-variant="box"] .line')[1]
    assert "background: rgb(4 10 20);" in box
    assert "rgb(4 10 20 / 90%)" not in box

def test_the_book_box_asks_for_no_blue_letters(manifest):
    """Owner, 2026-08-17: 'get rid of the blue here'.

    The project's b/f rule stands everywhere it was not switched off; this card
    opts in the same way cards/ending.html does, and does not opt in.
    """
    assert "blue_letters" not in plate(manifest, "book-a")
    card = (REPO_ROOT / "cards" / "bookline.html").read_text()
    assert "if (params.get('blue_letters') === 'true') {" in card

def test_one_stationary_box_holds_the_lines_and_never_covers_the_iguana(manifest):
    """Owner: "do NOT cover the iguana".

    The box lives on the head leg, so the iguana is only ever under it while
    the dissolve is running -- and at the end of that dissolve the head's
    weight is zero, which is the same instant the iguana is clean. There is no
    frame of clean iguana with a panel on it.
    """
    box = plate(manifest, "book-a")
    empty = plate(manifest, "book-b")
    assert box["body"] == OWNER_COPY["book-a"]
    assert empty["body"] == []
    assert box["at"] + box["dur"] == pytest.approx(T.CUT_OUT, abs=1e-9)
    graph = T.filtergraph(manifest, scope="")
    assert "[head][bk0]overlay=" in graph
    assert "[headbox][tail]xfade=" in graph

def test_one_forty_seven_is_the_documented_wolves_fade_climax(manifest):
    climax = manifest["_climax"]
    assert climax.startswith("1:47.000")
    assert "wolves" in climax
    assert "no wolf sound is added" in climax

def test_book_b_holds_across_the_join_without_tracking(manifest):
    """It remains readable over the iguana instead of drifting with the book."""
    entry = plate(manifest, "book-b")
    assert entry["at"] + entry["dur"] > T.CUT_OUT, "book-b crosses the join"
    assert "walk" not in entry
    assert entry["anchor"] == entry["anchor_out"]

def test_every_overlay_still_is_bounded_to_the_picture(manifest):
    """`loop=loop=-1` is infinite and `overlay`'s framesync keeps producing
    output after the main input ends. The prologue shipped eight seconds of
    frozen final frame that way, and ffmpeg exited 0."""
    graph = T.filtergraph(manifest, scope="")
    for chunk in graph.split(";"):
        if "loop=loop=-1" in chunk:
            assert "trim=" in chunk, chunk

def test_the_enable_windows_use_escaped_commas(manifest):
    """The quoted spelling the ffmpeg docs show fails to parse here, disables
    the overlay, and still exits 0 -- a silent no-op."""
    graph = T.filtergraph(manifest, scope="")
    assert "enable=between(t\\," in graph
    assert "enable='between" not in graph

def test_the_end_card_uses_the_resolved_day_wallpaper(manifest):
    graph = T.filtergraph(manifest, scope="")
    assert "[6:v]split=2[bridgenightsrc][endnightsrc]" in graph
    assert (
        f"[day][bridgenight]xfade=transition=fade:"
        f"duration={T.BRIDGE - T.BRIDGE_DAY_SETTLE:.3f}:"
        f"offset={T.BRIDGE_DAY_SETTLE:.3f}[bridgepre]"
    ) in graph
    assert "color=c=black" not in graph

def test_the_end_card_wallpaper_is_bounded_to_its_own_window(manifest):
    graph = T.filtergraph(manifest, scope="")
    assert (
        f"trim=0:{T.ENDCARD:.3f},setpts=PTS-STARTPTS,"
        f"format=yuv420p[endnight]"
        in graph
    )

def test_the_end_card_text_lands_in_two_music_timed_beats(manifest):
    graph = T.filtergraph(manifest, scope="")
    assert (
        f"fade=t=in:st={T.ENDCARD_EVENT_IN:.3f}:"
        f"d={T.ENDCARD_EVENT_FADE:.3f}:alpha=1"
        in graph
    )
    assert (
        f"fade=t=in:st={T.ENDCARD_CTA_IN:.3f}:"
        f"d={T.ENDCARD_CTA_FADE:.3f}:alpha=1"
        in graph
    )
    assert T.ENDCARD_EVENT_IN < T.ENDCARD_CTA_IN
