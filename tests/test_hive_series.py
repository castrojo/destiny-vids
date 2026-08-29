"""Season of the Blueberries: the season record and its generated cards.

The manifest (`stories/standalone/season-of-the-blueberries.json`) is the
committed record: twelve publisher chapter windows copied as factual source
data, the owner-authored CTA copy verbatim, the frozen candidate-1 lore
subtitles with their provenance, the fixed cast's source-evidenced seats, and
the no-repeat contributor ledger. `tools/hive_series.py` validates it and
renders the cards that need no footage: the Expansion Pack opening CTA, one
title slide per episode, and the Guardian dossier A contributor cards.

The fixed character plates are drawn by `tools/plate.py`, unmodified; these
tests only prove the season's specs go through it.
"""
import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image
from jsonschema import Draft202012Validator

from tools import hive_series

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "stories" / "standalone" / "season-of-the-blueberries.json"
SCHEMA_PATH = REPO_ROOT / "schema" / "hive-season.schema.json"

# The 12 publisher chapter windows, captured 2026-08-29 with
# `yt-dlp --dump-single-json --skip-download` from
# https://www.youtube.com/watch?v=jlzQnXcUxqI and copied into the season
# manifest as factual source data.
CAPTURED_CHAPTERS = [
    (0, 125, "The Enclave"),
    (125, 218, "On Mars"),
    (218, 309, "Savathun"),
    (309, 351, "The Relic"),
    (351, 484, "To Be Chosen"),
    (484, 501, "Remembering"),
    (501, 579, "Council"),
    (579, 744, "Worm"),
    (744, 1005, "Defeated"),
    (1005, 1085, "The Witness"),
    (1085, 1181, "With Mara"),
    (1181, 1248, "Raid"),
]

OWNER_CTA_LINES = [
    "Find out the Secrets of AI at Scale",
    "KubeCon + CloudNativeCon",
    "Sponsor the End User Summit",
    "Generous Consultations from the Minds Who Brought you this Madness",
    "The people in this series are the best at finding business value in your business.",
    "#HIREAWOLF",
]

# candidate 1 of each chapter, as printed by the lore supplier's
# `tools/titles.py --all` on 2026-08-29 and frozen into the episode records.
FROZEN_SUBTITLES = {
    1: "Where the work is shaped, not wished.",
    2: "A world returned, and nothing on it unchanged.",
    3: "Light in the brood, doubt in the court.",
    4: "Shape the tool, then trust it with the work.",
    5: "Chosen is a verdict, not a wish.",
    6: "The record is the memory; the memory is the proof.",
    7: "Many voices, one verdict.",
    8: "Every strength is a bargain with a hunger.",
    9: "In the sword logic, defeat is only data.",
    10: "It watches from the dark between the stars.",
    11: "Even queens keep allies beyond the reef.",
    12: "Six voices enter; the discipline holds them.",
}

EXPECTED_SEATS = {
    "ikora": [(1, 36.0, 4.0), (8, 687.0, 4.0), (9, 764.0, 4.0)],
    "eris": [(1, 60.0, 4.0), (8, 631.0, 4.0)],
    "player": [
        (2, 149.0, 4.0), (4, 313.0, 4.0), (7, 553.0, 4.0),
        (8, 611.0, 4.0), (9, 960.0, 4.0), (11, 1129.0, 4.0),
    ],
}


@pytest.fixture(scope="module")
def manifest():
    return hive_series.load_manifest(MANIFEST_PATH)


@pytest.fixture()
def raw():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _pixel_identical(a, b):
    """Pixel equality, not byte equality: `tools/thumbnail.py` raises
    PIL's global `ImageFile.MAXBLOCK` at import time, which changes the PNG
    encoder's byte output without changing a single pixel."""
    from PIL import ImageChops

    a, b = a.convert("RGB"), b.convert("RGB")
    return a.size == b.size and ImageChops.difference(a, b).getbbox() is None


# --- the record ------------------------------------------------------------

def test_the_committed_manifest_matches_its_own_schema(raw):
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(raw),
        key=lambda e: list(e.path),
    )
    assert not errors, "\n".join(
        f"{'/'.join(str(p) for p in e.path)}: {e.message}" for e in errors
    )


def test_twelve_contiguous_chapter_windows_match_the_captured_source(manifest):
    chapters = manifest["chapters"]
    assert [c["number"] for c in chapters] == list(range(1, 13))
    assert [
        (c["start"], c["end"], c["headline"]) for c in chapters
    ] == [(float(s), float(e), t) for s, e, t in CAPTURED_CHAPTERS]
    for prev, nxt in zip(chapters, chapters[1:]):
        assert prev["end"] == nxt["start"], "chapter windows must be contiguous"


def test_one_shared_source_block_for_the_whole_season(manifest):
    source = manifest["source"]
    assert source["youtube_id"] == "jlzQnXcUxqI"
    assert source["url"] == "https://www.youtube.com/watch?v=jlzQnXcUxqI"
    assert source["video_format_id"] == "137"
    assert source["audio_format_id"] == "251"
    assert source["usage_class"] == "third_party_copyrighted"
    assert "non-commercial" in source["source_rights_note"]
    # Every episode reuses the one source: no chapter may carry its own.
    for chapter in manifest["chapters"]:
        assert "source" not in chapter


def test_contributor_ledger_starts_empty_and_ids_never_repeat(manifest):
    assert manifest["contributor_ledger"]["credited_github_ids"] == []

    doctored = json.loads(json.dumps(manifest))
    doctored["contributor_ledger"]["credited_github_ids"] = [42, 42]
    with pytest.raises(ValueError, match="repeat"):
        hive_series.load_manifest_data(doctored)

    doctored = json.loads(json.dumps(manifest))
    doctored["contributor_ledger"]["credited_github_ids"] = [42]
    doctored["chapters"][0]["dossiers"] = [
        {"login": "someone", "github_id": 42, "name": "", "tasks": 1}
    ]
    with pytest.raises(ValueError, match="repeat"):
        hive_series.load_manifest_data(doctored)


def test_opening_cta_copy_is_exactly_the_owner_authored_lines(manifest):
    cta = manifest["opening_cta"]
    assert cta["lines"] == OWNER_CTA_LINES
    assert cta["duration"] == 10.0
    assert cta["copy_source"] == "owner_authored"
    assert cta["asset"] == "assets/hive/expansion-pack-cta.png"


def test_closing_cta_is_the_existing_training_card_unchanged(manifest):
    cta = manifest["closing_cta"]
    assert cta["asset"] == "assets/cta/linux-foundation-training-forest.png"
    assert cta["duration"] == 10.0
    assert (REPO_ROOT / cta["asset"]).exists()


def test_every_episode_has_a_frozen_candidate_one_subtitle(manifest):
    for chapter in manifest["chapters"]:
        sub = chapter["subtitle"]
        assert sub["text"] == FROZEN_SUBTITLES[chapter["number"]]
        assert sub["candidate_id"] == 1
        assert sub["copy_source"] == "generated_lore"
        assert sub["nature"] in ("canon_inspired", "extrapolation")
        assert "titles.py" in sub["supplier"]


def test_title_slide_eyebrow_uses_the_roman_episode_number(manifest):
    template = manifest["title_slide"]["eyebrow_template"]
    assert template == "SEASON OF THE BLUEBERRIES // EPISODE {roman}"
    assert manifest["title_slide"]["duration"] == 5.0
    first = manifest["chapters"][0]
    assert hive_series.eyebrow(manifest, first) == \
        "SEASON OF THE BLUEBERRIES // EPISODE I"
    last = manifest["chapters"][-1]
    assert hive_series.eyebrow(manifest, last) == \
        "SEASON OF THE BLUEBERRIES // EPISODE XII"


def test_fixed_cast_copy_is_the_owner_authored_copy_verbatim(manifest):
    cast = {c["id"]: c for c in manifest["fixed_cast"]}
    assert set(cast) == {"ikora", "eris", "player"}

    ikora = cast["ikora"]
    assert ikora["character"] == "Ikora Rey"
    assert ikora["github_login"] == "angiejones"
    assert ikora["plate"] == {
        "label": "TRUSTEE // GUARDIAN",
        "class": "Voidwalker Warlock",
        "name": "Angie Jones",
        "title": "Arbiter of the Agentic",
        "variant": "leader",
    }

    eris = cast["eris"]
    assert eris["character"] == "Eris Morn"
    assert eris["github_login"] == "Swil78"
    assert eris["plate"] == {
        "label": "TRUSTEE // AUTOMATON",
        "name": "Shellea Williams",
        "title": "I'm here for the 2x, I'm THAT good",
        "variant": "leader",
    }
    assert "class" not in eris["plate"], "no invented class row"

    player = cast["player"]
    assert player["character"] == "Player Guardian"
    assert player["github_login"] == "CortNick"
    assert player["plate"] == {
        "label": "HIVE // BLUEBERRY",
        "name": "Cortney",
        "title": "Knows Policy, Knows this is Preposterous",
    }
    assert "class" not in player["plate"], "no invented class row"


def test_fixed_cast_seats_are_exactly_the_evidenced_ones(manifest):
    seats = {
        c["id"]: [(s["chapter"], s["source_at"], s["dur"]) for s in c["seats"]]
        for c in manifest["fixed_cast"]
    }
    assert seats == EXPECTED_SEATS
    assert sum(len(s) for s in seats.values()) == 11


def test_every_seat_sits_inside_its_chapter_window(manifest):
    windows = {c["number"]: (c["start"], c["end"]) for c in manifest["chapters"]}
    for member in manifest["fixed_cast"]:
        for seat in member["seats"]:
            start, end = windows[seat["chapter"]]
            assert start <= seat["source_at"]
            assert seat["source_at"] + seat["dur"] <= end
            assert seat["why"], "a seat without evidence is not a seat"


def test_loader_rejects_a_seat_outside_its_chapter(manifest):
    doctored = json.loads(json.dumps(manifest))
    doctored["fixed_cast"][0]["seats"][0]["source_at"] = 124.5  # ch1 ends 125
    with pytest.raises(ValueError, match="outside chapter"):
        hive_series.load_manifest_data(doctored)


def test_owner_authored_overlays_are_verbatim(manifest):
    overlays = {o["id"]: o for o in manifest["overlays"]}
    assert set(overlays) == {"savathuns-ship", "business-value-review"}

    ship = overlays["savathuns-ship"]
    assert ship["chapter"] == 1
    assert ship["source_at"] == 113.0
    assert ship["position"] == "bottom-right"
    assert ship["lines"] == [
        "Palace of AI Expectations",
        "Tomb of Platform Teams",
    ]
    assert ship["nature"] == "project_lore", "project lore, not canon"

    review = overlays["business-value-review"]
    assert review["chapter"] == 3
    assert review["source_at"] == 243.0
    assert review["position"] == "top-third"
    assert review["lines"] == ["Business Value Review"]
    assert review["note"] == (
        "This is the cataclysm: the great fear of the intended audience."
    )


def test_the_ship_overlay_keeps_clear_of_the_heroes(manifest):
    """The lower third shares no window with any fixed plate seat."""
    ship = next(o for o in manifest["overlays"] if o["id"] == "savathuns-ship")
    for member in manifest["fixed_cast"]:
        for seat in member["seats"]:
            if seat["chapter"] != ship["chapter"]:
                continue
            assert not (
                seat["source_at"] <= ship["source_at"] < seat["source_at"] + seat["dur"]
            ), f"{member['id']} plate overlaps the ship lower third"


# --- plate planning --------------------------------------------------------

def test_plate_specs_are_one_per_seat_and_plate_py_shaped(manifest):
    specs = hive_series.plate_specs(manifest)
    assert len(specs) == 11
    ids = [s["id"] for s in specs]
    assert len(set(ids)) == 11
    ikora = next(s for s in specs if s["id"] == "ikora-ch1")
    assert ikora["at"] == 36.0
    assert ikora["dur"] == 4.0
    assert ikora["label"] == "TRUSTEE // GUARDIAN"
    assert ikora["class"] == "Voidwalker Warlock"
    assert ikora["name"] == "Angie Jones"
    assert ikora["title"] == "Arbiter of the Agentic"
    assert ikora["variant"] == "leader"


def test_plate_specs_render_through_plate_py_unmodified(manifest):
    """The fixed plates are tools/plate.py's job; the season only specs them.

    Avatars are deliberately not set here: face bytes are never committed, so
    the drawn crest stands in -- exactly what plate.py renders for a missing
    avatar file.
    """
    from tools import plate

    for spec in hive_series.plate_specs(manifest):
        spec = {k: v for k, v in spec.items() if k != "avatar"}
        img = plate.render_plate(spec)
        assert img.mode == "RGBA"
        assert img.width > 100 and img.height > 50


def test_unsupported_plate_copy_is_omitted_and_recorded(manifest):
    """A cast member whose plate copy is incomplete is an unresolved entry,
    never a rendered plate. Omission degrades; a guessed plate would lie."""
    doctored = json.loads(json.dumps(manifest))
    del doctored["fixed_cast"][0]["plate"]["title"]
    plates, unresolved = hive_series.plan_chapter_plates(doctored, 1)
    assert [p["id"] for p in plates] == ["eris-ch1"]
    assert len(unresolved) == 1
    assert unresolved[0]["cast"] == "ikora"
    assert "title" in unresolved[0]["reason"]


def test_plate_planning_covers_every_seated_chapter(manifest):
    planned = []
    for chapter in manifest["chapters"]:
        plates, unresolved = hive_series.plan_chapter_plates(
            manifest, chapter["number"]
        )
        planned.extend(p["id"] for p in plates)
        assert unresolved == []
    assert sorted(planned) == sorted(s["id"] for s in hive_series.plate_specs(manifest))


# --- generated cards -------------------------------------------------------

def test_opening_cta_is_a_committed_1080p_asset_with_a_pinned_digest():
    path = REPO_ROOT / "assets/hive/expansion-pack-cta.png"
    assert Image.open(path).size == (1920, 1080)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == hive_series.OPENING_CTA_SHA256


def test_opening_cta_regenerates_pixel_identical(manifest):
    img = hive_series.render_opening_cta(manifest["opening_cta"]["lines"])
    committed = Image.open(REPO_ROOT / "assets/hive/expansion-pack-cta.png")
    assert _pixel_identical(img, committed)


def test_title_slides_regenerate_pixel_identical(manifest):
    out_dir = REPO_ROOT / manifest["title_slide"]["output_dir"]
    for chapter in manifest["chapters"]:
        committed = out_dir / hive_series.title_slide_filename(chapter)
        assert committed.exists(), f"missing committed slide {committed.name}"
        with Image.open(committed) as saved:
            assert saved.size == (1920, 1080)
            img = hive_series.render_title_slide(manifest, chapter)
            assert _pixel_identical(img, saved), committed.name


def test_title_slide_filename_carries_episode_number_and_slug(manifest):
    first = manifest["chapters"][0]
    assert hive_series.title_slide_filename(first) == "s01e01-the-enclave.png"
    last = manifest["chapters"][-1]
    assert hive_series.title_slide_filename(last) == "s01e12-raid.png"


# --- Guardian dossier A ----------------------------------------------------

def _fixture_face(size=460):
    """A deterministic square 'PFP' whose four corners are distinct colours,
    so a crop anywhere in the pipeline is visible to the test."""
    img = Image.new("RGB", (size, size), (32, 48, 80))
    px = img.load()
    colours = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
    for (cx, cy), colour in zip(
        [(0, 0), (size - 1, 0), (0, size - 1), (size - 1, size - 1)], colours
    ):
        px[cx, cy] = colour
    return img


def _fixture_snapshot():
    return {
        "login": "test-fixture",
        "github_id": 424242,
        "name": "Fixture Contributor",
        "tasks": 3,
    }


def test_dossier_fields_are_factual_github_data_only():
    fields = hive_series.dossier_fields(_fixture_snapshot())
    assert fields == {
        "name": "Fixture Contributor",
        "handle": "@test-fixture",
        "tasks": "HIVE TASKS +3",
    }


def test_dossier_name_falls_back_to_login_when_display_name_is_empty():
    snapshot = _fixture_snapshot()
    snapshot["name"] = ""
    assert hive_series.dossier_fields(snapshot)["name"] == "test-fixture"


def test_dossier_renders_the_full_uncropped_square_face():
    img, unresolved = hive_series.render_dossier(
        _fixture_snapshot(), face=_fixture_face()
    )
    assert unresolved == []
    assert img.size == (1920, 1080)
    raw = img.convert("RGB").tobytes()
    pixels = {raw[i:i + 3] for i in range(0, len(raw), 3)}
    # All four corner colours survive: the face was padded, never cropped.
    for colour in [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]:
        assert bytes(colour) in pixels, f"corner {colour} cropped out"


def test_dossier_render_is_deterministic():
    a, _ = hive_series.render_dossier(_fixture_snapshot(), face=_fixture_face())
    b, _ = hive_series.render_dossier(_fixture_snapshot(), face=_fixture_face())
    assert _pixel_identical(a, b)


def test_dossier_with_no_face_is_an_unresolved_entry_not_an_invented_one():
    img, unresolved = hive_series.render_dossier(_fixture_snapshot(), face=None)
    assert img.size == (1920, 1080)
    assert unresolved == [
        {"login": "test-fixture", "reason": "no cached GitHub avatar"}
    ]


def test_resolve_face_reads_the_square_cache_without_cropping(tmp_path, monkeypatch):
    from tools import avatars

    monkeypatch.setattr(avatars.C, "AVATAR_DIR", tmp_path)
    face = _fixture_face()
    face.save(tmp_path / "someone.png")
    loaded = hive_series.resolve_face("someone")
    assert loaded is not None
    assert loaded.size == face.size
    # credits.avatar() would circle-crop; the dossier needs the raw square.
    assert loaded.convert("RGB").getpixel((0, 0)) == (255, 0, 0)


def test_resolve_face_returns_none_for_a_login_with_no_cached_face(tmp_path, monkeypatch):
    from tools import avatars

    monkeypatch.setattr(avatars.C, "AVATAR_DIR", tmp_path)
    assert hive_series.resolve_face("nobody") is None


def test_declared_avatar_logins_are_the_fixed_cast(manifest):
    assert hive_series.declared_avatar_logins(manifest) == [
        "angiejones",
        "Swil78",
        "CortNick",
    ]
