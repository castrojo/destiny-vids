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
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_trailer1 as T  # noqa: E402


@pytest.fixture(scope="module")
def manifest():
    return json.loads(T.MANIFEST.read_text())


def plate(manifest, plate_id):
    return next(p for p in manifest["plates"] if p["id"] == plate_id)


# --- the length ---------------------------------------------------------------

def test_the_trailer_is_one_minute_fifty():
    """Owner: 'let's shoot for 1:50'.

    The MPA and NATO cap a theatrical trailer at 2:30, so this is inside the
    convention as well as inside the brief.
    """
    assert T.TOTAL == pytest.approx(110.020, abs=1e-6)
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
    assert T.ENDCARD == pytest.approx(7.500 + T.JOIN_FADE, abs=1e-9)


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
    graph = T.filtergraph(json.loads(T.MANIFEST.read_text()))
    assert f"[0:a]atrim=0:{T.TOTAL:.3f}" in graph
    assert graph.count("atrim") == 1


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
    assert T.AUDIO_FADE_START + T.AUDIO_FADE == pytest.approx(T.TOTAL)


# --- the copy -----------------------------------------------------------------

OWNER_COPY = {
    "book-a": ["Two Generations of Contributors"],
    "book-b": ["One, new, one old.", "Dreaming to build a better future"],
}


@pytest.mark.parametrize("plate_id,lines", OWNER_COPY.items())
def test_the_book_lines_are_the_owners_words_verbatim(manifest, plate_id, lines):
    """Including the punctuation the owner did or did not type.

    'Dreaming to build a better future' arrived without a full stop and keeps
    it that way: a mark nobody wrote is still a mark nobody wrote.
    """
    assert plate(manifest, plate_id)["body"] == lines


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


def test_the_credit_line_is_one_seared_line_here_and_in_the_prologue(manifest):
    """The same authored string in both records, so the two cannot drift."""
    line = "Music by Nightwish | Action by Bungie"
    for plate_id in ("maintitle-a", "maintitle-b"):
        assert plate(manifest, plate_id)["body"] == [line]
    prologue = json.loads(
        (REPO_ROOT / "stories" / "00-prologue-plates.json").read_text())
    for entry in prologue["plates"]:
        assert entry["body"] == [line]


def test_no_plate_here_names_a_person(manifest):
    """The owner chose an unattributed plate over a chat pill, and a chat pill
    is the only card in this deck that carries a speaker. Nothing here credits
    anybody with saying anything."""
    for entry in manifest["plates"]:
        assert "speaker" not in entry
        assert "name" not in entry
        assert entry["kind"] in ("maintitle", "bookline")


# --- the motion ---------------------------------------------------------------

def test_both_book_lines_actually_move(manifest):
    """'account for the movement' -- a line seated on a drifting page and left
    static is the failure this is here to catch."""
    for plate_id in ("book-a", "book-b"):
        entry = plate(manifest, plate_id)
        assert entry["anchor"] != entry["anchor_out"]


def test_the_book_lines_use_the_simple_box_treatment(manifest):
    """Owner: 'I just want a simple box overlay'."""
    for plate_id in ("book-a", "book-b"):
        assert plate(manifest, plate_id)["variant"] == "box"


def test_one_forty_seven_is_the_documented_wolves_fade_climax(manifest):
    climax = manifest["_climax"]
    assert climax.startswith("1:47.000")
    assert "wolves" in climax
    assert "no wolf sound is added" in climax


def test_a_line_may_stop_tracking_when_its_page_is_gone(manifest):
    """book-b holds across the tank join and is still up over the iguana, so
    it tracks the page only until the cut."""
    entry = plate(manifest, "book-b")
    assert entry["at"] + entry["dur"] > T.CUT_OUT, "book-b crosses the join"
    assert entry["at"] + entry["walk"] == pytest.approx(T.CUT_OUT - T.JOIN_FADE,
                                                        abs=0.01)


def test_the_walk_expression_is_clamped_at_both_ends():
    expr = T._walk(0.0, 100.0, 10.0, 2.0)
    assert "max(0\\,min(1\\," in expr


def test_every_overlay_still_is_bounded_to_the_picture(manifest):
    """`loop=loop=-1` is infinite and `overlay`'s framesync keeps producing
    output after the main input ends. The prologue shipped eight seconds of
    frozen final frame that way, and ffmpeg exited 0."""
    graph = T.filtergraph(manifest)
    for chunk in graph.split(";"):
        if "loop=loop=-1" in chunk:
            assert "trim=" in chunk, chunk


def test_the_enable_windows_use_escaped_commas(manifest):
    """The quoted spelling the ffmpeg docs show fails to parse here, disables
    the overlay, and still exits 0 -- a silent no-op."""
    graph = T.filtergraph(manifest)
    assert "enable=between(t\\," in graph
    assert "enable='between" not in graph


def test_the_end_card_uses_the_resolved_day_wallpaper(manifest):
    graph = T.filtergraph(manifest)
    assert "[5:v]split=3[daysrc][bridgedarksrc][enddarksrc]" in graph
    assert "[bridgedarkraw]eq=brightness=-0.55[bridgedark]" in graph
    assert (
        f"[day][bridgedark]xfade=transition=fade:"
        f"duration={T.BRIDGE:.3f}:offset=0[bridge]"
    ) in graph
    assert "color=c=black" not in graph


def test_the_end_card_wallpaper_is_bounded_to_its_own_window(manifest):
    graph = T.filtergraph(manifest)
    assert (
        f"trim=0:{T.ENDCARD - T.ENDCARD_DAY_HOLD:.3f},"
        f"setpts=PTS-STARTPTS,format=yuv420p[enddarkraw]"
        in graph
    )


def test_the_end_card_text_lands_in_two_music_timed_beats(manifest):
    graph = T.filtergraph(manifest)
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
