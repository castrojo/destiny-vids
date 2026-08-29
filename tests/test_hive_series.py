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
from PIL import Image, ImageDraw
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
    assert {k: v for k, v in ikora["plate"].items() if k != "provenance"} == {
        "label": "TRUSTEE // GUARDIAN",
        "class": "Voidwalker Warlock",
        "name": "Angie Jones",
        "title": "Arbiter of the Agentic",
        "variant": "leader",
    }

    eris = cast["eris"]
    assert eris["character"] == "Eris Morn"
    assert eris["github_login"] == "Swil78"
    assert {k: v for k, v in eris["plate"].items() if k != "provenance"} == {
        "label": "TRUSTEE // AUTOMATON",
        "name": "Shellea Williams",
        "title": "I'm here for the 2x, I'm THAT good",
        "variant": "leader",
    }
    assert "class" not in eris["plate"], "no invented class row"

    player = cast["player"]
    assert player["character"] == "Player Guardian"
    assert player["github_login"] == "CortNick"
    assert {k: v for k, v in player["plate"].items() if k != "provenance"} == {
        "label": "HIVE // BLUEBERRY",
        "name": "Cortney",
        "title": "Knows Policy, Knows this is Preposterous",
    }
    assert "class" not in player["plate"], "no invented class row"


def test_every_fixed_cast_plate_carries_explicit_provenance(manifest):
    """Each plate records the owner instruction it came from and the GitHub
    profile fetch behind its name row -- the guard in test_plate_copy_drift
    recognizes this instead of forcing an empty global binding."""
    expected_names = {
        "ikora": ("angiejones", "Angie Jones"),
        "eris": ("Swil78", "Shellea Williams"),
        "player": ("CortNick", "Cortney"),
    }
    for member in manifest["fixed_cast"]:
        provenance = member["plate"].get("provenance")
        assert provenance, f"{member['id']}: plate has no provenance"
        assert provenance["copy_source"] == "owner_authored"
        assert "2026-08-29" in provenance["decided_by"]
        login, name = expected_names[member["id"]]
        assert member["plate"]["name"] == name
        assert f"/users/{login}" in provenance["name_source"]
        assert name in provenance["name_source"]


def test_cortneys_name_is_the_github_profile_name_not_the_wolves_plate(manifest):
    """KEEP `name: Cortney`: the owner explicitly required GitHub as the
    factual source of truth, and /users/CortNick's public name is 'Cortney'.
    The label/title are a deliberate one-video identity, not a reuse of the
    older Wolves plate for 'Cortney Nickerson' -- the provenance says so."""
    player = next(c for c in manifest["fixed_cast"] if c["id"] == "player")
    provenance = player["plate"]["provenance"]
    assert player["plate"]["name"] == "Cortney"
    assert "104345443" in provenance["name_source"]  # CortNick's github_id
    assert "Cortney Nickerson" in provenance["note"]
    assert "one-video identity" in provenance["note"]


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
    specs, unresolved = hive_series.plate_specs(manifest)
    assert unresolved == []
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

    specs, unresolved = hive_series.plate_specs(manifest)
    assert unresolved == []
    for spec in specs:
        spec = {k: v for k, v in spec.items() if k != "avatar"}
        img = plate.render_plate(spec)
        assert img.mode == "RGBA"
        assert img.width > 100 and img.height > 50


def test_loader_reports_schema_problems_without_a_semantic_keyerror(manifest):
    """A schema-invalid manifest raises ValueError listing the schema
    problems -- never a raw KeyError from the semantic checks that assume
    those fields exist."""
    for mutate, needle in [
        (lambda d: d["chapters"][0].pop("start"), "start"),
        (lambda d: d["fixed_cast"][0]["seats"][0].pop("source_at"), "source_at"),
        (lambda d: d.pop("chapters"), "chapters"),
        (lambda d: d["overlays"][0].pop("source_at"), "source_at"),
        (lambda d: d["fixed_cast"][0]["plate"].pop("label"), "label"),
    ]:
        doctored = json.loads(json.dumps(manifest))
        mutate(doctored)
        with pytest.raises(ValueError) as excinfo:
            hive_series.load_manifest_data(doctored)
        assert needle in str(excinfo.value)


def test_unsupported_plate_copy_is_omitted_and_recorded(manifest):
    """A cast member whose plate copy is incomplete is an unresolved entry,
    never a rendered plate. Omission degrades; a guessed plate would lie.

    `title` is OPTIONAL in the schema precisely so this gap degrades through
    the real path: the manifest validates, and the PLANNER -- not the loader
    -- omits the plate and records why."""
    doctored = json.loads(json.dumps(manifest))
    del doctored["fixed_cast"][0]["plate"]["title"]
    validated = hive_series.load_manifest_data(doctored)  # schema-clean
    plates, unresolved = hive_series.plan_chapter_plates(validated, 1)
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
    specs, _ = hive_series.plate_specs(manifest)
    assert sorted(planned) == sorted(s["id"] for s in specs)


def test_plate_specs_omit_incomplete_copy_through_the_validated_path(manifest):
    """`plate_specs` is the path Task 3 renders, so it holds the same line
    as the per-chapter planner: a seat whose copy is incomplete is withheld
    from plate.py and recorded, never drawn with a guessed row. `title` is
    optional in the schema precisely so the gap flows through the real
    validated load -> spec path."""
    doctored = json.loads(json.dumps(manifest))
    del doctored["fixed_cast"][0]["plate"]["title"]
    validated = hive_series.load_manifest_data(doctored)  # schema-clean
    specs, unresolved = hive_series.plate_specs(validated)
    assert specs, "the complete plates still spec"
    assert all(not s["id"].startswith("ikora-") for s in specs)
    assert len(unresolved) == 1
    assert unresolved[0] == {
        "cast": "ikora",
        "reason": "plate copy incomplete: missing title",
    }
    # Every emitted spec really is drawable: nothing incomplete reaches
    # plate.py through this path.
    from tools import plate

    for spec in specs:
        drawn = plate.render_plate(
            {k: v for k, v in spec.items() if k != "avatar"}
        )
        assert drawn.width > 100


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
    so a crop anywhere in the pipeline is visible to the test. The markers
    are blocks, not single pixels, so they survive the dossier's Lanczos
    upscale to the tile size exactly as a real PFP's corners would."""
    img = Image.new("RGB", (size, size), (32, 48, 80))
    draw = ImageDraw.Draw(img)
    marker = max(8, size // 24)
    colours = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
    corners = [
        (0, 0),
        (size - marker, 0),
        (0, size - marker),
        (size - marker, size - marker),
    ]
    for (cx, cy), colour in zip(corners, colours):
        draw.rectangle([cx, cy, cx + marker - 1, cy + marker - 1], fill=colour)
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


# --- dossier text fitting (C1) and PFP fit (C2) ------------------------------

def test_dossier_text_stays_inside_the_panel_for_long_identities():
    """A long display name and a long login shrink and wrap so every row's
    bounding box stays inside the glass panel. Nothing is clipped or
    truncated: every character of the real identity survives across rows."""
    snapshot = _fixture_snapshot()
    snapshot["name"] = (
        "Alexandra Maximiliana Featherstonehaugh-Contributingworth the Third"
    )
    snapshot["login"] = "a-very-long-github-login-that-just-keeps-going-on"
    fields = hive_series.dossier_fields(snapshot)
    px, py, pw, ph = hive_series.DOSSIER_PANEL
    draw = ImageDraw.Draw(Image.new("RGBA", (1920, 1080)))
    layout = hive_series.dossier_text_layout(fields)
    assert len(layout) >= 3, "the long identity should wrap to multiple rows"
    for x, y, text, font, _fill in layout:
        assert text, "a wrapped row is never blank"
        assert font.size >= min(
            hive_series.DOSSIER_NAME_MIN, hive_series.DOSSIER_HANDLE_MIN
        )
        x0, y0, x1, y1 = draw.textbbox((x, y), text, font=font)
        assert x0 >= px and x1 <= px + pw, f"{text!r} escapes the panel horizontally"
        assert y0 >= py and y1 <= py + ph, f"{text!r} escapes the panel vertically"
    joined = "".join(row[2] for row in layout).replace(" ", "")
    whole = (fields["name"] + fields["handle"]).replace(" ", "")
    assert joined == whole, "a real identity is never clipped or truncated"


def test_dossier_text_keeps_full_size_for_normal_identities():
    """The fitting contract only engages when it has to: an identity that
    fits the panel renders at the display sizes on one line each, exactly as
    before."""
    snapshot = _fixture_snapshot()
    snapshot["name"] = "Sam Rivera"
    snapshot["login"] = "srivera"
    fields = hive_series.dossier_fields(snapshot)
    layout = hive_series.dossier_text_layout(fields)
    assert [row[2] for row in layout] == ["Sam Rivera", "@srivera"]
    name_font, handle_font = layout[0][3], layout[1][3]
    assert name_font.size == hive_series.DOSSIER_NAME_SIZE
    assert handle_font.size == hive_series.DOSSIER_HANDLE_SIZE


def test_dossier_text_shrinks_before_it_wraps():
    """A name slightly too wide for the panel shrinks to a size that fits on
    one line rather than wrapping -- shrink first, wrap when shrinking hits
    the floor of legibility."""
    fields = hive_series.dossier_fields(_fixture_snapshot())
    layout = hive_series.dossier_text_layout(fields)
    assert [row[2] for row in layout] == ["Fixture Contributor", "@test-fixture"]
    name_font = layout[0][3]
    assert hive_series.DOSSIER_NAME_MIN <= name_font.size < hive_series.DOSSIER_NAME_SIZE


def test_dossier_text_fit_never_shrinks_below_the_tested_floor():
    """Even an absurd identity stops shrinking at the floor and hard-wraps
    instead -- the font floor is the guarantee, not a hope."""
    draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    absurd = "X" * 500
    font, lines = hive_series._fit_text(
        draw, absurd, "bold",
        hive_series.DOSSIER_NAME_SIZE, hive_series.DOSSIER_NAME_MIN,
        hive_series.DOSSIER_TEXT_WIDTH,
    )
    assert font.size == hive_series.DOSSIER_NAME_MIN
    assert len(lines) > 1
    for line in lines:
        assert draw.textlength(line, font=font) <= hive_series.DOSSIER_TEXT_WIDTH
    assert "".join(lines) == absurd, "hard wrap drops no characters"


def test_dossier_text_stays_above_the_hairline_for_whitespace_heavy_names():
    """The vertical budget, not only the width: a 60+ char display name of
    ordinary words wraps at the DISPLAY size into more lines than the area
    above the hairline can hold, so the fit must shrink until the whole
    name+handle block clears the hairline -- never spill over the task row
    or escape the panel."""
    snapshot = _fixture_snapshot()
    snapshot["name"] = (
        "Maria de la Cruz Hernandez von Trapp Smythe Worthington the Third"
    )
    snapshot["login"] = "maria-de-la-cruz-hernandez"
    fields = hive_series.dossier_fields(snapshot)
    px, py, pw, ph = hive_series.DOSSIER_PANEL
    hairline = py + hive_series.DOSSIER_HAIRLINE
    draw = ImageDraw.Draw(Image.new("RGBA", (1920, 1080)))

    # The premise: at the display size this name alone stacks taller than
    # the area above the hairline, so a width-only fit overflows.
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    display = hive_series._font("bold", hive_series.DOSSIER_NAME_SIZE)
    display_lines = hive_series._wrap_hard(
        probe, fields["name"], display, hive_series.DOSSIER_TEXT_WIDTH
    )
    display_h = hive_series._line_height(display) * len(display_lines)
    budget = hive_series.DOSSIER_HAIRLINE - 6 - hive_series.DOSSIER_TEXT_AREA_TOP
    assert display_h > budget, (
        "the fixture no longer overflows at display size -- it stops "
        "exercising the vertical budget")

    layout = hive_series.dossier_text_layout(fields)
    assert len(layout) >= 3, "the long identity still wraps to multiple rows"
    assert layout[0][3].size < hive_series.DOSSIER_NAME_SIZE, (
        "the name shrank to buy the vertical budget")
    for x, y, text, font, _fill in layout:
        assert text, "a wrapped row is never blank"
        x0, y0, x1, y1 = draw.textbbox((x, y), text, font=font)
        assert x0 >= px and x1 <= px + pw, f"{text!r} escapes the panel horizontally"
        assert y0 >= py, f"{text!r} escapes the panel top"
        assert y1 <= hairline, f"{text!r} crosses the hairline into the task row"
    joined = "".join(row[2] for row in layout).replace(" ", "")
    whole = (fields["name"] + fields["handle"]).replace(" ", "")
    assert joined == whole, "a real identity is never clipped or truncated"


def test_dossier_text_layout_fails_loudly_past_the_minimum_sizes():
    """The floor is a guard, not a clip: an identity that cannot fit above
    the hairline even at the minimum sizes raises -- it never renders
    overlapping the task row or escaping the panel."""
    fields = {
        "name": "Xe ".join(["Mr"] * 300),  # ~900 chars of short tokens
        "handle": "@" + "x" * 300,
        "tasks": "HIVE TASKS +1",
    }
    with pytest.raises(ValueError, match="cannot fit"):
        hive_series.dossier_text_layout(fields)


def test_dossier_fit_entire_upscales_a_small_face_to_cover_the_tile():
    """A small GitHub PFP is UPSCALED to cover the avatar tile in at least
    one dimension, aspect preserved -- never left floating small, never
    cropped."""
    tile = 720
    square = hive_series._fit_entire(_fixture_face(120), tile)
    assert square.size == (720, 720)
    wide = hive_series._fit_entire(Image.new("RGB", (400, 100)), tile)
    assert wide.size == (720, 180)
    tall = hive_series._fit_entire(Image.new("RGB", (100, 400)), tile)
    assert tall.size == (180, 720)
    for fitted in (square, wide, tall):
        assert max(fitted.size) == tile, "covers the tile in at least one dimension"
        assert min(fitted.size) <= tile


def test_dossier_renders_a_wide_face_letterboxed_and_uncropped():
    """Render-level proof for a non-square PFP: the whole image is padded
    into the tile (letterbox), and all four corner colours survive."""
    face = Image.new("RGB", (400, 100), (32, 48, 80))
    draw = ImageDraw.Draw(face)
    colours = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
    for (cx, cy), colour in zip(
        [(0, 0), (384, 0), (0, 84), (384, 84)], colours
    ):
        draw.rectangle([cx, cy, cx + 15, cy + 15], fill=colour)
    img, unresolved = hive_series.render_dossier(_fixture_snapshot(), face=face)
    assert unresolved == []
    raw = img.convert("RGB").tobytes()
    pixels = {raw[i:i + 3] for i in range(0, len(raw), 3)}
    for colour in colours:
        assert bytes(colour) in pixels, f"corner {colour} cropped out"


# --- Task 3: episode and season builds ---------------------------------------
#
# The episode is ONE encode: opening CTA (10s, silent), title slide (5s,
# silent), zero-to-three dossier cards (4s each, silent), the manifest's
# source chapter with its own audio and the fixed/source-authored overlays at
# chapter-relative times, and the closing training CTA (10s, silent). The
# source is fetched once and reused; the encode goes through farm.run_encode;
# the full cut concatenates the twelve episodes without re-encoding.


def _doctored(manifest, mutate):
    data = json.loads(json.dumps(manifest))
    mutate(data)
    return hive_series.load_manifest_data(data)


# --- the timeline ------------------------------------------------------------

def test_episode_timeline_is_the_five_authored_beats(manifest):
    chapter = hive_series.chapter_by_number(manifest, 1)
    segments = hive_series.episode_segments(manifest, chapter)
    assert [s["kind"] for s in segments] == [
        "opening_cta", "title_slide", "chapter", "closing_cta",
    ]
    assert segments[0]["dur"] == 10.0
    assert segments[1]["dur"] == 5.0
    assert segments[2]["start"] == 0.0 and segments[2]["end"] == 125.0
    assert segments[2]["audio"] == "source"
    assert segments[3]["dur"] == 10.0
    # The silent cards carry no source audio.
    for still in (segments[0], segments[1], segments[3]):
        assert still["audio"] == "silent"


def test_zero_to_three_dossier_cards_sit_between_title_and_chapter(manifest):
    doctored = _doctored(manifest, lambda d: d["chapters"][0].__setitem__(
        "dossiers",
        [
            {"login": "alice", "github_id": 11, "name": "Alice A", "tasks": 2},
            {"login": "bob", "github_id": 22, "name": "", "tasks": 1},
        ],
    ))
    chapter = hive_series.chapter_by_number(doctored, 1)
    segments = hive_series.episode_segments(doctored, chapter)
    assert [s["kind"] for s in segments] == [
        "opening_cta", "title_slide", "dossier", "dossier",
        "chapter", "closing_cta",
    ]
    dossiers = [s for s in segments if s["kind"] == "dossier"]
    assert all(s["dur"] == hive_series.DOSSIER_DURATION == 4.0
               for s in dossiers)
    assert all(s["audio"] == "silent" for s in dossiers)
    assert [s["snapshot"]["login"] for s in dossiers] == ["alice", "bob"]


def test_source_marks_convert_to_chapter_relative_never_move(manifest):
    """Absolute source seats become chapter-relative content time, then the
    front cards offset them into episode time. The authored source mark
    itself is never adjusted."""
    ch1 = hive_series.chapter_by_number(manifest, 1)
    ch8 = hive_series.chapter_by_number(manifest, 8)  # 579.0-744.0
    assert hive_series.front_cards_duration(manifest, ch1) == 15.0
    assert hive_series.source_to_chapter_relative(36.0, ch1) == 36.0
    assert hive_series.source_to_episode_time(36.0, manifest, ch1) == 51.0
    assert hive_series.source_to_chapter_relative(687.0, ch8) == 108.0
    assert hive_series.source_to_episode_time(687.0, manifest, ch8) == 123.0
    # The owner overlays: ship at source 113.0 (ch1), review at 243.0 (ch3).
    ch3 = hive_series.chapter_by_number(manifest, 3)  # 218.0-309.0
    assert hive_series.source_to_episode_time(113.0, manifest, ch1) == 128.0
    assert hive_series.source_to_episode_time(243.0, manifest, ch3) == 40.0


def test_front_offset_counts_the_dossier_cards(manifest):
    doctored = _doctored(manifest, lambda d: d["chapters"][0].__setitem__(
        "dossiers",
        [{"login": "alice", "github_id": 11, "name": "A", "tasks": 1}],
    ))
    chapter = hive_series.chapter_by_number(doctored, 1)
    assert hive_series.front_cards_duration(doctored, chapter) == 19.0
    assert hive_series.source_to_episode_time(36.0, doctored, chapter) == 55.0


def test_episode_expected_duration_includes_cards_and_chapter(manifest):
    ch1 = hive_series.chapter_by_number(manifest, 1)
    assert hive_series.episode_expected_duration(manifest, ch1) == 150.0
    ch6 = hive_series.chapter_by_number(manifest, 6)  # 484-501, 17s
    assert hive_series.episode_expected_duration(manifest, ch6) == 42.0


def test_season_aggregate_duration_is_the_twelve_episodes(manifest):
    chapter_seconds = sum(end - start
                          for start, end, _title in CAPTURED_CHAPTERS)
    assert chapter_seconds == 1248.0
    expected = chapter_seconds + 12 * (10.0 + 5.0 + 10.0)
    assert hive_series.cut_expected_duration(manifest) == expected == 1548.0


# --- the one-pass graph ------------------------------------------------------

def test_episode_filtergraph_is_one_pass_with_one_source_decode(manifest):
    plan = hive_series.episode_plan(manifest, 1)
    graph = hive_series.episode_filtergraph(plan)
    # One source decode, trimmed to the chapter window exactly once.
    assert graph.count("[0:v]trim=start=0:end=125") == 1
    assert graph.count("[0:a]atrim=start=0:end=125") == 1
    # Every still leg holds its authored duration on generated silence.
    assert "trim=duration=10" in graph
    assert "trim=duration=5" in graph
    assert graph.count("anullsrc=r=48000:cl=stereo") == 3  # cta, title, closing
    # The chapter's own audio is carried, pinned to the delivery layout.
    assert "aformat=sample_fmts=fltp:channel_layouts=stereo" in graph
    # Chapter 1 seats, chapter-relative: ikora at 36, eris at 60, and the
    # ship overlay at 113 with the tooling default hold.
    assert "enable='between(t,36,40)'" in graph
    assert "enable='between(t,60,64)'" in graph
    assert f"enable='between(t,113,{113 + hive_series.LORE_OVERLAY_DUR:g})'" in graph
    # One concat joining every segment, picture and sound, out of the graph.
    assert "concat=n=4:v=1:a=1[outv][outa]" in graph


def test_episode_filtergraph_overlay_inputs_follow_the_stills(manifest):
    """Input order is fixed: 0 is the source, the stills follow in segment
    order, and the overlay PNGs come last -- the graph must index them so."""
    plan = hive_series.episode_plan(manifest, 1)
    graph = hive_series.episode_filtergraph(plan)
    # 3 stills (cta, title, closing), so overlay inputs start at 4.
    assert "[4:v]overlay=0:0:enable='between(t,36,40)'" in graph
    assert "[5:v]overlay=0:0:enable='between(t,60,64)'" in graph
    assert "[6:v]overlay=0:0" in graph
    assert "[7:v]" not in graph


def test_episode_filtergraph_resamples_only_a_non_delivery_rate(manifest):
    plan = hive_series.episode_plan(manifest, 1)
    at_48k = hive_series.episode_filtergraph(plan, source_rate=48000)
    assert "aresample" not in at_48k
    at_44k = hive_series.episode_filtergraph(plan, source_rate=44100)
    assert "aresample=48000" in at_44k


def test_episode_filtergraph_dossiers_grow_the_still_legs(manifest):
    doctored = _doctored(manifest, lambda d: d["chapters"][0].__setitem__(
        "dossiers",
        [{"login": "alice", "github_id": 11, "name": "A", "tasks": 1}],
    ))
    plan = hive_series.episode_plan(doctored, 1)
    graph = hive_series.episode_filtergraph(plan)
    assert graph.count("anullsrc=r=48000:cl=stereo") == 4
    assert "trim=duration=4" in graph
    assert "concat=n=5:v=1:a=1[outv][outa]" in graph
    # The chapter trim itself never moves: only the concat count grows.
    assert graph.count("[0:v]trim=start=0:end=125") == 1


def test_encode_episode_command_uses_the_delivery_encode_recipe(tmp_path):
    out = tmp_path / "ep.mp4"
    argv = hive_series.encode_episode_command(
        ["ffmpeg"], tmp_path / "src.mkv",
        [tmp_path / "a.png", tmp_path / "b.png"], [tmp_path / "p.png"],
        "GRAPH", out)
    text = " ".join(map(str, argv))
    # Still inputs loop at the delivery rate; the source is input 0.
    assert argv[:4] == ["ffmpeg", "-v", "error", "-y"]
    assert text.count("-loop 1 -framerate 60000/1001 -i") == 3
    # The delivery x264 recipe comes from conform, and AAC 48 kHz stereo.
    for token in ("libx264", "-crf 16", "high", "4.2", "+cgop", "bt709"):
        assert token in text
    assert "-c:a aac" in text and "-b:a 320k" in text and "-ar 48000" in text
    assert "+faststart" in text
    assert "-map [outv]" in text and "-map [outa]" in text


# --- the source is fetched once ------------------------------------------------

def test_source_fetch_command_uses_the_manifests_pinned_formats(manifest, tmp_path):
    out = tmp_path / "jlzQnXcUxqI.mkv"
    argv = hive_series.source_fetch_command(manifest, out)
    text = " ".join(map(str, argv))
    assert argv[0] == "yt-dlp"
    assert "-f 137+251" in text
    assert "https://www.youtube.com/watch?v=jlzQnXcUxqI" in text
    assert "--merge-output-format mkv" in text
    assert "player_client" in text
    assert "best" not in text.split("-f")[1].split()[0]


def test_ensure_source_fetches_once_and_reuses_the_cache(manifest, tmp_path):
    calls = []

    def fake_runner(argv, **kwargs):
        calls.append(argv)
        Path(argv[-2]).write_bytes(b"mkv")  # -o <out> precedes the url

        class _Done:
            returncode = 0
        return _Done()

    first = hive_series.ensure_source(manifest, cache_dir=tmp_path,
                                      runner=fake_runner)
    assert first == (tmp_path / "jlzQnXcUxqI.mkv").resolve()
    assert len(calls) == 1
    # A non-empty cache file is the evidence the fetch ran: never re-fetch.
    again = hive_series.ensure_source(manifest, cache_dir=tmp_path,
                                      runner=fake_runner)
    assert again == first
    assert len(calls) == 1


def test_ensure_source_checks_by_youtube_id_not_episode(manifest, tmp_path):
    """Twelve episodes, ONE cached file: the cache key is the source id."""
    assert hive_series.source_cache_path(manifest, tmp_path).name == \
        "jlzQnXcUxqI.mkv"


# --- farm-first execution ------------------------------------------------------

def test_encode_episode_routes_through_farm_run_encode(tmp_path, monkeypatch):
    captured = {}

    def fake_run_encode(argv, **kwargs):
        captured["argv"] = argv
        captured.update(kwargs)
        return "cluster"

    monkeypatch.setattr(hive_series.farm, "run_encode", fake_run_encode)
    out = tmp_path / "ep.mp4"
    where = hive_series.encode_episode(
        ["ffmpeg", "-i", "x"], inputs=[tmp_path / "x"], out=out,
        expected_duration=150.0, label="test")
    assert where == "cluster"
    assert captured["out"] == out
    assert captured["expected_duration"] == 150.0
    assert captured["local"] is False


def test_encode_episode_passes_the_local_flag_through(tmp_path, monkeypatch):
    captured = {}

    def fake_run_encode(argv, **kwargs):
        captured.update(kwargs)
        return "local"

    monkeypatch.setattr(hive_series.farm, "run_encode", fake_run_encode)
    where = hive_series.encode_episode(
        ["ffmpeg"], inputs=[], out=tmp_path / "ep.mp4",
        expected_duration=1.0, local=True)
    assert where == "local"
    assert captured["local"] is True


# --- stable output paths ---------------------------------------------------------

def test_delivery_paths_come_straight_from_the_manifest(manifest):
    first = hive_series.chapter_by_number(manifest, 1)
    out = hive_series.episode_output_path(first)
    assert out == Path.home() / (
        "Videos/Hive/Season-of-the-Blueberries/s01e01-the-enclave.mp4")
    thumb = hive_series.thumbnail_output_path(first)
    assert thumb == Path.home() / (
        "Videos/Hive/Season-of-the-Blueberries/"
        "s01e01-the-enclave-thumbnail.jpg")
    cut = hive_series.full_cut_path(manifest)
    assert cut == Path.home() / (
        "Videos/Hive/Season-of-the-Blueberries/season-01-full.mp4")
    for path in (out, thumb, cut):
        assert "review" not in str(path), "no review folder: these ARE delivery"


# --- the project-lore overlays ---------------------------------------------------

def test_lore_overlay_seats_bottom_right_clear_of_the_heroes(manifest):
    ship = next(o for o in manifest["overlays"] if o["id"] == "savathuns-ship")
    card = hive_series.render_lore_overlay(ship)
    assert card.mode == "RGBA" and card.width < 1920
    frame = hive_series.place_lore_overlay(card, "bottom-right")
    assert frame.size == (1920, 1080)
    x0, y0, x1, y1 = frame.getbbox()
    # Bottom-right safe area, measured like the plate lane's margins: 5%
    # side inset, 10% bottom margin -- and never in the lower-left lane the
    # hero plates hold.
    assert x1 >= 1920 - 0.05 * 1920 - 1
    assert x1 <= 1920 - 40
    assert y1 >= 1080 - 0.10 * 1080 - 1
    assert y1 <= 1080 - 20
    assert x0 > 960, "the ship overlay must not reach the heroes' left lane"


def test_lore_overlay_top_third_stays_in_the_top_third(manifest):
    review = next(
        o for o in manifest["overlays"] if o["id"] == "business-value-review")
    card = hive_series.render_lore_overlay(review)
    frame = hive_series.place_lore_overlay(card, "top-third")
    x0, y0, x1, y1 = frame.getbbox()
    assert y1 <= 1080 / 3, "the cataclysm note stays in the top third"
    assert abs((x0 + x1) / 2 - 960) < 40, "centred on the picture"


def test_lore_overlay_renders_verbatim_lines_and_nothing_else(manifest):
    ship = next(o for o in manifest["overlays"] if o["id"] == "savathuns-ship")
    two = hive_series.render_lore_overlay(ship)
    one = hive_series.render_lore_overlay(
        {**ship, "lines": ["Palace of AI Expectations"]})
    assert two.height > one.height, "every authored line is drawn"
    # Deterministic: the same overlay renders the same card twice.
    again = hive_series.render_lore_overlay(ship)
    assert _pixel_identical(two, again)


def test_an_unknown_overlay_position_is_unresolved_never_invented(manifest):
    plan = hive_series.episode_plan(manifest, 1)
    bad = {"id": "mystery", "kind": "lower-third", "chapter": 1,
           "source_at": 10.0, "position": "diagonal",
           "lines": ["Somewhere"], "copy_source": "owner_authored",
           "nature": "project_lore", "note": ""}
    doctored = _doctored(manifest, lambda d: d["overlays"].append(bad))
    plan = hive_series.episode_plan(doctored, 1)
    assert [o["id"] for o in plan["overlays"]] == ["savathuns-ship"]
    assert any(u.get("id") == "mystery" and "position" in u["reason"]
               for u in plan["unresolved"])


def test_lore_overlay_hold_defaults_and_clamps_to_the_chapter(manifest):
    """Overlay durations are unauthored; the tooling default holds the card,
    clamped to the chapter window it must not outrun."""
    plan = hive_series.episode_plan(manifest, 1)
    ship = plan["overlays"][0]
    assert ship["at"] == 113.0
    assert ship["dur"] == hive_series.LORE_OVERLAY_DUR
    late = _doctored(manifest, lambda d: d["overlays"][0].__setitem__(
        "source_at", 122.0))  # ch1 ends at 125
    plan = hive_series.episode_plan(late, 1)
    assert plan["overlays"][0]["dur"] == 3.0


# --- the dossier safe fallback ----------------------------------------------------

def test_a_pathological_display_name_falls_back_to_the_verified_login():
    """The deferred safe fallback: a display name that cannot fit the panel
    is not clipped and never aborts the build -- the card carries the
    verified login and the gap is recorded."""
    snapshot = _fixture_snapshot()
    snapshot["name"] = "Xe ".join(["Mr"] * 300)  # provably cannot fit
    fields = hive_series.dossier_fields(snapshot)
    with pytest.raises(ValueError, match="cannot fit"):
        hive_series.dossier_text_layout(fields)  # the premise
    img, unresolved = hive_series.render_dossier_safely(snapshot, face=None)
    assert img.size == (1920, 1080)
    assert any(u["login"] == "test-fixture" and "login" in u["reason"]
               for u in unresolved)


# --- the thumbnail -----------------------------------------------------------------

def test_thumbnail_is_a_1080p_jpeg_under_two_megabytes(tmp_path):
    slide = REPO_ROOT / "assets/hive/titles/s01e01-the-enclave.png"
    out = hive_series.make_thumbnail(slide, tmp_path / "thumb.jpg")
    assert out.stat().st_size < hive_series.THUMBNAIL_MAX_BYTES
    assert out.stat().st_size < 2 * 1024 * 1024
    with Image.open(out) as img:
        assert img.format == "JPEG"
        assert img.size == (1920, 1080)


# --- the full-season cut --------------------------------------------------------------

def test_concat_command_copies_matching_streams_without_reencoding(tmp_path):
    argv = hive_series.concat_command(
        ["ffmpeg"], tmp_path / "list.txt", tmp_path / "season-01-full.mp4")
    text = " ".join(map(str, argv))
    assert "-f concat" in text
    assert "-c:v copy" in text and "-c:a copy" in text
    assert "libx264" not in text and "libx265" not in text


def test_concat_list_is_the_twelve_episodes_in_chapter_order(manifest):
    lines = hive_series.concat_list_lines(manifest)
    assert len(lines) == 12
    for index, line in enumerate(lines, start=1):
        assert line.startswith("file '")
        assert f"s01e{index:02d}-" in line
    assert "s01e01-the-enclave" in lines[0]
    assert "s01e12-raid" in lines[-1]


# --- offline orchestration -------------------------------------------------------------


def _delivery_manifest(manifest, tmp_path):
    """The committed manifest with its delivery paths redirected into the
    test's tmp_path -- the path STRINGS change, the record's shape does not."""
    data = json.loads(json.dumps(manifest))
    for chapter in data["chapters"]:
        slug = f"s01e{chapter['number']:02d}-{chapter['slug']}"
        chapter["output"] = str(tmp_path / f"{slug}.mp4")
        chapter["thumbnail_output"] = str(tmp_path / f"{slug}-thumbnail.jpg")
    return data


def test_build_episode_orchestrates_cards_encode_and_thumbnail(
        manifest, tmp_path, monkeypatch):
    """One episode, offline: the source is ensured once, the plates and the
    lore overlay render to PNG, ONE farm-routed encode carries them all, and
    the title slide becomes the delivered JPEG thumbnail."""
    data = _delivery_manifest(manifest, tmp_path)
    manifest_path = tmp_path / "season.json"
    manifest_path.write_text(json.dumps(data))

    fake_source = tmp_path / "src.mkv"
    fake_source.write_bytes(b"mkv")
    monkeypatch.setattr(hive_series, "ensure_source", lambda *a, **k: fake_source)
    monkeypatch.setattr(
        hive_series.render, "detect_picture_status",
        lambda *a, **k: (None, "full-frame"))

    captured = {}

    def fake_run_encode(argv, **kwargs):
        captured["argv"] = [str(t) for t in argv]
        captured.update(kwargs)
        Path(kwargs["out"]).write_bytes(b"mp4")
        return "cluster"

    monkeypatch.setattr(hive_series.farm, "run_encode", fake_run_encode)

    out = hive_series.build_episode(manifest_path, 1, work_dir=tmp_path / "work")
    assert out == tmp_path / "s01e01-the-enclave.mp4"
    assert out.exists(), "the encode wrote the episode"

    argv = captured["argv"]
    graph = argv[argv.index("-filter_complex") + 1]
    assert "concat=n=4:v=1:a=1" in graph  # cta, title, chapter, closing
    # Every staged input is a real file: source + 3 stills + 3 overlays
    # (ikora-ch1, eris-ch1, the ship lore overlay).
    inputs = captured["inputs"]
    assert len(inputs) == 7
    assert inputs[0] == fake_source.resolve()
    for path in inputs:
        assert Path(path).exists(), f"staged input missing: {path}"
    assert captured["expected_duration"] == 150.0
    assert captured["local"] is False

    thumb = tmp_path / "s01e01-the-enclave-thumbnail.jpg"
    assert thumb.exists()
    assert thumb.stat().st_size < 2 * 1024 * 1024
    with Image.open(thumb) as img:
        assert img.format == "JPEG" and img.size == (1920, 1080)

    sidecar = json.loads(
        (tmp_path / "work" / "s01e01-the-enclave-unresolved.json").read_text())
    assert sidecar == []


def test_build_episode_records_the_dossier_fallback_in_unresolved(
        manifest, tmp_path, monkeypatch):
    data = _delivery_manifest(manifest, tmp_path)
    data["chapters"][0]["dossiers"] = [{
        "login": "fixture", "github_id": 424242,
        "name": "Xe ".join(["Mr"] * 300), "tasks": 1,
    }]
    manifest_path = tmp_path / "season.json"
    manifest_path.write_text(json.dumps(data))
    hive_series.load_manifest(manifest_path)  # the doctored record validates

    fake_source = tmp_path / "src.mkv"
    fake_source.write_bytes(b"mkv")
    monkeypatch.setattr(hive_series, "ensure_source", lambda *a, **k: fake_source)
    monkeypatch.setattr(
        hive_series.render, "detect_picture_status",
        lambda *a, **k: (None, "full-frame"))
    monkeypatch.setattr(
        hive_series, "resolve_face", lambda login: None)

    def fake_run_encode(argv, **kwargs):
        Path(kwargs["out"]).write_bytes(b"mp4")
        return "cluster"

    monkeypatch.setattr(hive_series.farm, "run_encode", fake_run_encode)

    out = hive_series.build_episode(manifest_path, 1, work_dir=tmp_path / "work")
    assert out.exists()
    sidecar = json.loads(
        (tmp_path / "work" / "s01e01-the-enclave-unresolved.json").read_text())
    assert any("fixture" in json.dumps(entry) for entry in sidecar)


# --- content-derived freshness ---------------------------------------------


def _stage_episode(manifest, tmp_path, monkeypatch, data=None):
    """The committed manifest redirected into tmp_path, with the network,
    the picture probe, the avatar cache, and media verification faked
    offline. Returns (manifest_path, data) so a test can doctor the record
    between builds."""
    data = data if data is not None else _delivery_manifest(manifest, tmp_path)
    manifest_path = tmp_path / "season.json"
    manifest_path.write_text(json.dumps(data))
    fake_source = tmp_path / "src.mkv"
    fake_source.write_bytes(b"mkv")
    monkeypatch.setattr(
        hive_series, "ensure_source", lambda *a, **k: fake_source)
    monkeypatch.setattr(
        hive_series.render, "detect_picture_status",
        lambda *a, **k: (None, "full-frame"))
    monkeypatch.setattr(hive_series, "resolve_face", lambda login: None)
    monkeypatch.setattr(hive_series, "verify_episode", lambda *a, **k: [])
    return manifest_path, data


def _fake_encode(calls):
    def fake_run_encode(argv, **kwargs):
        calls.append(kwargs)
        Path(kwargs["out"]).write_bytes(b"mp4")
        return "cluster"
    return fake_run_encode


def _png(path, color):
    Image.new("RGBA", (64, 64), color).save(path)
    return path


def test_episode_input_digest_is_deterministic_over_identical_content(
        manifest, tmp_path):
    plan = hive_series.episode_plan(manifest, 1)
    staged = [_png(tmp_path / "a.png", (1, 2, 3, 255)),
              _png(tmp_path / "b.png", (4, 5, 6, 255))]
    first = hive_series.episode_input_digest(plan, staged)
    second = hive_series.episode_input_digest(plan, staged)
    assert first == second


def test_episode_input_digest_tracks_every_content_class(manifest, tmp_path):
    """Same-duration changes to the title card's pixels, the dossier copy,
    the overlay copy, and the chapter bounds must EACH move the digest --
    duration stays put, so only content can catch them."""
    plan = hive_series.episode_plan(manifest, 1)
    staged = [_png(tmp_path / "a.png", (1, 2, 3, 255))]
    base = hive_series.episode_input_digest(plan, staged)

    _png(tmp_path / "a.png", (9, 9, 9, 255))  # same size, new pixels
    changed_pixels = hive_series.episode_input_digest(plan, staged)
    assert changed_pixels != base

    data = json.loads(json.dumps(manifest))
    data["chapters"][0]["dossiers"] = [{
        "login": "fixture", "github_id": 424242, "name": "Ada", "tasks": 1,
    }]
    changed_copy = hive_series.episode_input_digest(
        hive_series.episode_plan(hive_series.load_manifest_data(data), 1),
        staged)
    assert changed_copy != base

    data = json.loads(json.dumps(manifest))
    data["overlays"][0]["lines"] = ["Same hold, different words."]
    changed_overlay = hive_series.episode_input_digest(
        hive_series.episode_plan(hive_series.load_manifest_data(data), 1),
        staged)
    assert changed_overlay != base

    data = json.loads(json.dumps(manifest))
    data["chapters"][0]["end"] = data["chapters"][0]["end"] - 1
    data["chapters"][1]["start"] = data["chapters"][0]["end"]
    changed_bounds = hive_series.episode_input_digest(
        hive_series.episode_plan(hive_series.load_manifest_data(data), 1),
        staged)
    assert changed_bounds != base

    # Unchanged content on the same plan and the same staged pixels is the
    # skip case -- the digest holds.
    assert hive_series.episode_input_digest(plan, staged) == changed_pixels


def test_build_episode_skips_the_encode_when_the_digest_matches(
        manifest, tmp_path, monkeypatch):
    manifest_path, _data = _stage_episode(manifest, tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(hive_series.farm, "run_encode", _fake_encode(calls))
    work = tmp_path / "work"

    hive_series.build_episode(manifest_path, 1, work_dir=work)
    assert len(calls) == 1
    digest_path = work / "s01e01-the-enclave-inputs.json"
    assert json.loads(digest_path.read_text())["sha256"]

    # A stale sidecar is rewritten from the CURRENT plan even on a skip.
    sidecar = work / "s01e01-the-enclave-unresolved.json"
    sidecar.write_text('[{"stale": true}]\n')
    out = hive_series.build_episode(manifest_path, 1, work_dir=work)
    assert out.exists()
    assert len(calls) == 1, "a matching digest must not re-encode"
    assert json.loads(sidecar.read_text()) == []


def test_freshness_skip_rewrites_unresolved_from_the_current_plan(
        manifest, tmp_path, monkeypatch):
    """The skip rewrites the sidecar even when the plan's unresolved list
    changed WITHOUT touching any encoded content: an overlay with an
    unknown position is recorded and omitted, so the digest stands, the
    encode is skipped, and the sidecar still reflects the current plan."""
    manifest_path, data = _stage_episode(manifest, tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(hive_series.farm, "run_encode", _fake_encode(calls))
    work = tmp_path / "work"
    hive_series.build_episode(manifest_path, 1, work_dir=work)
    assert len(calls) == 1

    data["overlays"].append({
        "id": "mystery", "kind": "lower-third", "chapter": 1,
        "source_at": 40.0, "position": "somewhere-unspecified",
        "lines": ["Unplaced."], "copy_source": "owner_authored",
        "nature": "project_lore", "note": "fixture",
    })
    manifest_path.write_text(json.dumps(data))
    hive_series.build_episode(manifest_path, 1, work_dir=work)
    assert len(calls) == 1, "an omitted overlay changes no encoded pixel"
    sidecar = json.loads(
        (work / "s01e01-the-enclave-unresolved.json").read_text())
    assert any(entry.get("id") == "mystery" for entry in sidecar)


def test_build_episode_adopts_a_verified_delivery_with_no_digest_on_record(
        manifest, tmp_path, monkeypatch):
    """Deliveries from before the digest existed are initialized safely: a
    verified output with no sidecar is ADOPTED, not re-encoded -- the digest
    is written from the current content and the build returns."""
    manifest_path, _data = _stage_episode(manifest, tmp_path, monkeypatch)
    out = tmp_path / "s01e01-the-enclave.mp4"
    out.write_bytes(b"mp4")  # a prior delivery; verification is faked clean

    def forbidden(argv, **kwargs):
        raise AssertionError("a verified delivery with no digest must not "
                             "be re-encoded -- the digest is adopted")

    monkeypatch.setattr(hive_series.farm, "run_encode", forbidden)
    work = tmp_path / "work"
    assert hive_series.build_episode(manifest_path, 1, work_dir=work) == out
    digest = json.loads((work / "s01e01-the-enclave-inputs.json").read_text())
    assert digest["sha256"] and digest["inputs"]
    assert json.loads(
        (work / "s01e01-the-enclave-unresolved.json").read_text()) == []


def test_build_episode_rebuilds_when_dossier_copy_changes_at_same_duration(
        manifest, tmp_path, monkeypatch):
    data = _delivery_manifest(manifest, tmp_path)
    data["chapters"][0]["dossiers"] = [{
        "login": "fixture", "github_id": 424242, "name": "Ada", "tasks": 1,
    }]
    manifest_path, data = _stage_episode(
        manifest, tmp_path, monkeypatch, data=data)
    calls = []
    monkeypatch.setattr(hive_series.farm, "run_encode", _fake_encode(calls))
    work = tmp_path / "work"
    hive_series.build_episode(manifest_path, 1, work_dir=work)
    assert len(calls) == 1
    duration_before = calls[0]["expected_duration"]

    data["chapters"][0]["dossiers"][0]["name"] = "Ada Byron"
    manifest_path.write_text(json.dumps(data))
    hive_series.build_episode(manifest_path, 1, work_dir=work)
    assert len(calls) == 2, "same-duration dossier copy change must rebuild"
    assert calls[1]["expected_duration"] == duration_before


def test_build_episode_rebuilds_when_overlay_copy_changes_at_same_duration(
        manifest, tmp_path, monkeypatch):
    manifest_path, data = _stage_episode(manifest, tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(hive_series.farm, "run_encode", _fake_encode(calls))
    work = tmp_path / "work"
    hive_series.build_episode(manifest_path, 1, work_dir=work)
    assert len(calls) == 1
    duration_before = calls[0]["expected_duration"]

    data["overlays"][0]["lines"] = ["Same hold.", "Different words."]
    manifest_path.write_text(json.dumps(data))
    hive_series.build_episode(manifest_path, 1, work_dir=work)
    assert len(calls) == 2, "same-duration overlay copy change must rebuild"
    assert calls[1]["expected_duration"] == duration_before


def test_build_episode_rebuilds_when_a_title_slide_changes_at_same_duration(
        manifest, tmp_path, monkeypatch):
    data = _delivery_manifest(manifest, tmp_path)
    slides = tmp_path / "slides"
    slides.mkdir()
    data["title_slide"]["output_dir"] = str(slides)
    manifest_path, _data = _stage_episode(
        manifest, tmp_path, monkeypatch, data=data)
    loaded = hive_series.load_manifest(manifest_path)
    chapter = hive_series.chapter_by_number(loaded, 1)
    slide = slides / hive_series.title_slide_filename(chapter)
    hive_series.render_title_slide(loaded, chapter).save(slide)

    calls = []
    monkeypatch.setattr(hive_series.farm, "run_encode", _fake_encode(calls))
    work = tmp_path / "work"
    hive_series.build_episode(manifest_path, 1, work_dir=work)
    assert len(calls) == 1
    duration_before = calls[0]["expected_duration"]

    with Image.open(slide) as img:
        changed = img.convert("RGB")
    ImageDraw.Draw(changed).rectangle([0, 0, 40, 40], fill=(255, 0, 0))
    changed.save(slide)  # same canvas, same 5.0s hold, new pixels
    hive_series.build_episode(manifest_path, 1, work_dir=work)
    assert len(calls) == 2, "same-duration title slide change must rebuild"
    assert calls[1]["expected_duration"] == duration_before


# --- delivery stream verification -------------------------------------------


def _conformant_video(**overrides):
    props = {
        "codec_name": "h264",
        "width": hive_series.FRAME_W,
        "height": hive_series.FRAME_H,
        "avg_frame_rate": "60000/1001",
        "r_frame_rate": "60000/1001",
        "pix_fmt": "yuv420p",
        "color_primaries": "bt709",
        "color_transfer": "bt709",
        "color_space": "bt709",
        "profile": "High",
        "level": "42",
    }
    props.update(overrides)
    return props


def _probe_with(tmp_path, monkeypatch, video, duration=150.0):
    monkeypatch.setattr(hive_series, "_probe_duration",
                        lambda *a, **k: duration)
    monkeypatch.setattr(hive_series.conform, "probe_video",
                        lambda *a, **k: video)
    monkeypatch.setattr(
        hive_series, "_probe_audio",
        lambda *a, **k: {"codec_name": "aac", "sample_rate": "48000",
                         "channels": 2})
    target = tmp_path / "ep.mp4"
    target.write_bytes(b"mp4")
    return hive_series._probe_delivery_streams(
        target, 150.0, ["ffmpeg"], 0.5)


def test_delivery_probe_keeps_conforms_pix_fmt_color_profile_level_checks(
        tmp_path, monkeypatch):
    problems = _probe_with(tmp_path, monkeypatch, _conformant_video(
        pix_fmt="yuv444p", color_primaries="bt2020", profile="Main",
        level="51"))
    text = "\n".join(problems)
    assert "pixel format" in text
    assert "color_primaries" in text
    assert "profile" in text
    assert "level" in text
    assert "frame rate" not in text, "the fps verdict stands -- only the " \
        "rounding case is overridden"


def test_delivery_probe_overrides_only_the_fps_container_rounding(
        tmp_path, monkeypatch):
    """The known verdict: whole-second card durations never divide 60000/1001
    evenly, so the container's avg_frame_rate lands ~0.008 fps off -- past
    conform's 1e-3 but inside the delivery rounding slack."""
    problems = _probe_with(tmp_path, monkeypatch, _conformant_video(
        avg_frame_rate="32640000/544621", r_frame_rate="32640000/544621"))
    assert problems == []


def test_delivery_probe_reports_a_real_fps_mismatch(tmp_path, monkeypatch):
    problems = _probe_with(tmp_path, monkeypatch, _conformant_video(
        avg_frame_rate="30/1", r_frame_rate="30/1"))
    assert any("frame rate" in p for p in problems)


def test_delivery_probe_reports_a_duration_mismatch(tmp_path, monkeypatch):
    problems = _probe_with(tmp_path, monkeypatch, _conformant_video(),
                           duration=149.0)
    assert any("duration" in p for p in problems)


# --- the cut's one interface ---------------------------------------------------


def test_build_cut_enforces_episode_verification_before_concat(
        manifest, tmp_path, monkeypatch):
    manifest_path = tmp_path / "season.json"
    manifest_path.write_text(json.dumps(_delivery_manifest(manifest, tmp_path)))
    monkeypatch.setattr(hive_series, "build_all", lambda *a, **k: [])
    monkeypatch.setattr(
        hive_series, "verify_episode",
        lambda m, number, **k: ["s01e04: duration off"] if number == 4 else [])

    def forbidden(*a, **k):
        raise AssertionError("unverified episodes must never be concatenated")

    monkeypatch.setattr(hive_series, "concat_episodes", forbidden)
    with pytest.raises(hive_series.UnverifiedEpisodes) as caught:
        hive_series.build_cut(manifest_path)
    assert caught.value.problems == ["s01e04: duration off"]


def test_build_cut_joins_verified_episodes_and_reports_the_cut(
        manifest, tmp_path, monkeypatch):
    manifest_path = tmp_path / "season.json"
    manifest_path.write_text(json.dumps(_delivery_manifest(manifest, tmp_path)))
    monkeypatch.setattr(hive_series, "build_all", lambda *a, **k: [])
    monkeypatch.setattr(hive_series, "verify_episode", lambda *a, **k: [])
    cut = tmp_path / "season-01-full.mp4"

    def fake_concat(manifest, out_path=None, **kwargs):
        cut.write_bytes(b"mp4")
        return cut

    monkeypatch.setattr(hive_series, "concat_episodes", fake_concat)
    probed = []

    def fake_probe(path, expected, ffmpeg, tolerance):
        probed.append(Path(path).name)
        return []

    monkeypatch.setattr(hive_series, "_probe_delivery_streams", fake_probe)
    out, problems = hive_series.build_cut(manifest_path)
    assert out == cut
    assert problems == []
    assert probed == ["season-01-full.mp4"], \
        "episodes were verified pre-concat; the post-join probe is the cut's"


def test_cut_command_goes_through_build_cut(tmp_path, monkeypatch):
    monkeypatch.setattr(hive_series, "build_cut",
                        lambda *a, **k: (tmp_path / "season-01-full.mp4", []))
    assert hive_series.main(["cut"]) == 0


def test_cut_command_reports_unverified_episodes_without_joining(
        tmp_path, monkeypatch):
    def refuse(*a, **k):
        raise hive_series.UnverifiedEpisodes(["s01e07: probe failed"])

    monkeypatch.setattr(hive_series, "build_cut", refuse)
    assert hive_series.main(["cut"]) == 1
