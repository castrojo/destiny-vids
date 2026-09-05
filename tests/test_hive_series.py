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


def test_contributor_ledger_ids_never_repeat(manifest):
    doctored = json.loads(json.dumps(manifest))
    doctored["contributor_ledger"]["credited_github_ids"] = [42, 42]
    with pytest.raises(ValueError, match="repeat"):
        hive_series.load_manifest_data(doctored)

    # The ledger is the union of everyone credited: a dossier's ID belongs
    # in it exactly once, and on screen at most once.
    doctored = json.loads(json.dumps(manifest))
    doctored["contributor_ledger"]["credited_github_ids"] = [42]
    doctored["chapters"][0]["dossiers"] = [
        {"login": "someone", "github_id": 42, "name": "", "commits": 1}
    ]
    hive_series.load_manifest_data(doctored)

    doctored["chapters"][1]["dossiers"] = [
        {"login": "someone-renamed", "github_id": 42, "name": "",
         "commits": 1}
    ]
    with pytest.raises(ValueError, match="repeat"):
        hive_series.load_manifest_data(doctored)

    doctored = json.loads(json.dumps(manifest))
    doctored["chapters"][0]["dossiers"] = [
        {"login": "unledgered", "github_id": 43, "name": "", "commits": 1}
    ]
    with pytest.raises(ValueError, match="not in the no-repeat ledger"):
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
        "commits": 3,
    }


def test_dossier_fields_are_factual_github_data_only():
    fields = hive_series.dossier_fields(_fixture_snapshot())
    assert fields == {
        "name": "Fixture Contributor",
        "handle": "@test-fixture",
        "tasks": "COMMITS +3",
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
    """The warmed set is the fixed cast plus the authoring-pass chat
    speakers whose identity the season's own records prove -- castrojo is a
    contributor-ledger candidate and authors chat cues, so his face warms
    too. Unproven handles (ahmedbehbars, ncode, ...) warm nothing."""
    assert hive_series.declared_avatar_logins(manifest) == [
        "angiejones",
        "Swil78",
        "CortNick",
        "castrojo",
    ]
    # The CI warming path (tools/avatars.py) covers the same speakers.
    from tools import avatars
    assert "castrojo" in avatars.season_avatar_logins()


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
        "tasks": "COMMITS +1",
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

# Episode 1 is issued: the bootstrap selection seated these three dossiers
# between its title slide and chapter. An issued chapter is never rewritten,
# so this is stable.
EPISODE_ONE_DOSSIERS = ["clubanderson", "Danathar", "gregoryhunt"]


def test_episode_timeline_is_the_five_authored_beats(manifest):
    chapter = hive_series.chapter_by_number(manifest, 1)
    segments = hive_series.episode_segments(manifest, chapter)
    assert [s["kind"] for s in segments] == [
        "opening_cta", "title_slide", "dossier", "dossier", "dossier",
        "chapter", "closing_cta",
    ]
    assert segments[0]["dur"] == 10.0
    assert segments[1]["dur"] == 5.0
    dossiers = segments[2:5]
    assert all(s["dur"] == hive_series.DOSSIER_DURATION == 4.0
               for s in dossiers)
    assert [s["snapshot"]["login"] for s in dossiers] == EPISODE_ONE_DOSSIERS
    assert segments[5]["start"] == 0.0 and segments[5]["end"] == 125.0
    assert segments[5]["audio"] == "source"
    assert segments[6]["dur"] == 10.0
    # The silent cards carry no source audio.
    for still in (segments[0], segments[1], *dossiers, segments[6]):
        assert still["audio"] == "silent"


def test_zero_to_three_dossier_cards_sit_between_title_and_chapter(manifest):
    def add(d):
        d["chapters"][0]["dossiers"] = [
            {"login": "alice", "github_id": 11, "name": "Alice A", "commits": 2},
            {"login": "bob", "github_id": 22, "name": "", "commits": 1},
        ]
        d["contributor_ledger"]["credited_github_ids"] = [11, 22]
    doctored = _doctored(manifest, add)
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
    # ch1 front cards: cta + title + its three issued dossiers = 27s.
    assert hive_series.front_cards_duration(manifest, ch1) == 27.0
    assert hive_series.source_to_chapter_relative(36.0, ch1) == 36.0
    assert hive_series.source_to_episode_time(36.0, manifest, ch1) == 63.0
    assert hive_series.source_to_chapter_relative(687.0, ch8) == 108.0
    assert hive_series.source_to_episode_time(687.0, manifest, ch8) == 123.0
    # The owner overlays: ship at source 113.0 (ch1), review at 243.0 (ch3).
    ch3 = hive_series.chapter_by_number(manifest, 3)  # 218.0-309.0
    assert hive_series.source_to_episode_time(113.0, manifest, ch1) == 140.0
    assert hive_series.source_to_episode_time(243.0, manifest, ch3) == 40.0


def test_front_offset_counts_the_dossier_cards(manifest):
    def add(d):
        d["chapters"][0]["dossiers"] = [
            {"login": "alice", "github_id": 11, "name": "A", "commits": 1},
        ]
        d["contributor_ledger"]["credited_github_ids"] = [11]
    doctored = _doctored(manifest, add)
    chapter = hive_series.chapter_by_number(doctored, 1)
    assert hive_series.front_cards_duration(doctored, chapter) == 19.0
    assert hive_series.source_to_episode_time(36.0, doctored, chapter) == 55.0


def test_episode_expected_duration_includes_cards_and_chapter(manifest):
    ch1 = hive_series.chapter_by_number(manifest, 1)
    # 150.0 plus its three issued dossier cards at 4.0 each.
    assert hive_series.episode_expected_duration(manifest, ch1) == 162.0
    ch6 = hive_series.chapter_by_number(manifest, 6)  # 484-501, 17s
    assert hive_series.episode_expected_duration(manifest, ch6) == 42.0


def test_season_aggregate_duration_is_the_twelve_episodes(manifest):
    chapter_seconds = sum(end - start
                          for start, end, _title in CAPTURED_CHAPTERS)
    assert chapter_seconds == 1248.0
    expected = chapter_seconds + 12 * (10.0 + 5.0 + 10.0) \
        + 3 * hive_series.DOSSIER_DURATION  # episode 1's issued dossiers
    assert hive_series.cut_expected_duration(manifest) == expected == 1560.0


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
    assert "trim=duration=4" in graph  # the issued dossier cards
    assert graph.count("anullsrc=r=48000:cl=stereo") == 6  # + 3 dossiers
    # The chapter's own audio is carried, pinned to the delivery layout.
    assert "aformat=sample_fmts=fltp:channel_layouts=stereo" in graph
    # Chapter 1 seats, chapter-relative: ikora at 36, eris at 60, and the
    # ship overlay at 113 with the tooling default hold.
    assert "enable='between(t,36,40)'" in graph
    assert "enable='between(t,60,64)'" in graph
    assert f"enable='between(t,113,{113 + hive_series.LORE_OVERLAY_DUR:g})'" in graph
    # One concat joining every segment, picture and sound, out of the graph.
    assert "concat=n=7:v=1:a=1[outv][outa]" in graph


def test_episode_filtergraph_overlay_inputs_follow_the_stills(manifest):
    """Input order is fixed: 0 is the source, the stills follow in segment
    order, and the overlay PNGs come last -- the graph must index them so."""
    plan = hive_series.episode_plan(manifest, 1)
    graph = hive_series.episode_filtergraph(plan)
    # 6 stills (cta, title, closing + episode 1's three issued dossiers),
    # so overlay inputs start at 7.
    assert "[7:v]overlay=0:0:enable='between(t,36,40)'" in graph
    assert "[8:v]overlay=0:0:enable='between(t,60,64)'" in graph
    assert "[9:v]overlay=0:0" in graph
    assert "[10:v]" not in graph


def test_episode_filtergraph_resamples_only_a_non_delivery_rate(manifest):
    plan = hive_series.episode_plan(manifest, 1)
    at_48k = hive_series.episode_filtergraph(plan, source_rate=48000)
    assert "aresample" not in at_48k
    at_44k = hive_series.episode_filtergraph(plan, source_rate=44100)
    assert "aresample=48000" in at_44k


def test_episode_filtergraph_dossiers_grow_the_still_legs(manifest):
    def add(d):
        d["chapters"][0]["dossiers"] = [
            {"login": "alice", "github_id": 11, "name": "A", "commits": 1},
        ]
        d["contributor_ledger"]["credited_github_ids"] = [11]
    doctored = _doctored(manifest, add)
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
    """The yt-dlp fetch remains as an EXPLICIT non-Hive capability only
    (allow_fetch=True) -- the Hive build path never passes it, because the
    merge would run a local ffmpeg."""
    calls = []

    def fake_runner(argv, **kwargs):
        calls.append(argv)
        Path(argv[-2]).write_bytes(b"mkv")  # -o <out> precedes the url

        class _Done:
            returncode = 0
        return _Done()

    absent = tmp_path / "no-supplied-source.mp4"
    first = hive_series.ensure_source(manifest, cache_dir=tmp_path,
                                      runner=fake_runner, supplied=absent,
                                      allow_fetch=True)
    assert first == (tmp_path / "jlzQnXcUxqI.mkv").resolve()
    assert len(calls) == 1
    # A non-empty cache file is the evidence the fetch ran: never re-fetch.
    again = hive_series.ensure_source(manifest, cache_dir=tmp_path,
                                      runner=fake_runner, supplied=absent)
    assert again == first
    assert len(calls) == 1


def test_absent_source_fails_visibly_never_a_local_fetch_merge(
        manifest, tmp_path):
    """The strict Hive contract: with no supplied immutable source and no
    cache, the build refuses with staging instructions -- a local
    `yt-dlp ... --merge-output-format mkv` would invoke a LOCAL ffmpeg
    merge, which this workspace forbids. The fetch runner is never
    consulted."""
    def forbidden_runner(argv, **kwargs):
        raise AssertionError("a local fetch ran for a Hive build")

    absent = tmp_path / "no-supplied-source.mp4"
    with pytest.raises(FileNotFoundError) as excinfo:
        hive_series.ensure_source(manifest, cache_dir=tmp_path,
                                  runner=forbidden_runner, supplied=absent)
    message = str(excinfo.value)
    assert "no season source" in message
    assert str(absent) in message, "the error names the path to stage"
    assert "remote job" in message
    assert "local ffmpeg merge" in message


def test_ensure_source_prefers_the_supplied_immutable_source(
        manifest, tmp_path):
    """The Hive workspace supplies `source-<youtube_id>.mp4` by hand: the
    build uses it, never mutates it, and never downloads a duplicate."""
    supplied = tmp_path / "source-jlzQnXcUxqI.mp4"
    supplied.write_bytes(b"supplied-immutable-source")

    def forbidden_runner(argv, **kwargs):
        raise AssertionError("a fetch ran despite the supplied source")

    got = hive_series.ensure_source(manifest, cache_dir=tmp_path / "cache",
                                    runner=forbidden_runner,
                                    supplied=supplied)
    assert got == supplied.resolve()
    assert supplied.read_bytes() == b"supplied-immutable-source"
    assert not (tmp_path / "cache").exists(), "no fetch cache was created"
    # The default supplied path is the workspace's immutable file for the
    # manifest's own video id.
    assert hive_series.supplied_source_path(manifest) == Path.home() / (
        "Videos/Hive/source-jlzQnXcUxqI.mp4")


def test_ensure_source_checks_by_youtube_id_not_episode(manifest, tmp_path):
    """Twelve episodes, ONE cached file: the cache key is the source id."""
    assert hive_series.source_cache_path(manifest, tmp_path).name == \
        "jlzQnXcUxqI.mkv"


# --- farm-only execution (the Hive contract) ---------------------------------

def test_encode_episode_routes_farm_only_with_farm_side_verification(
        tmp_path, monkeypatch):
    """Hive's encode is farm.run_encode with the strict contract: no local
    fallback, and the post-fetch verification reads the pod's own probe,
    never the host's ffprobe."""
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
    assert captured["fallback"] is False, "no local fallback for Hive"
    assert captured["local_probe"] is False, "verification is the pod's own"


def test_encode_episode_fails_visibly_when_the_farm_is_unreachable(
        tmp_path, monkeypatch):
    """No local fallback exists for a Hive encode: an unreachable cluster is
    a FarmError before any render, never a quiet local encode."""
    monkeypatch.setattr(hive_series.farm, "cluster_available",
                        lambda *a, **k: (False, "kubectl not on PATH"))

    def forbidden(*a, **k):  # the capped local path must never run
        raise AssertionError("a local encode ran for a Hive build")

    monkeypatch.setattr(hive_series.farm, "run_capped_local", forbidden)
    with pytest.raises(hive_series.farm.FarmError,
                       match="not reachable"):
        hive_series.encode_episode(
            ["ffmpeg", "-i", "x"], inputs=[tmp_path / "x"],
            out=tmp_path / "ep.mp4", expected_duration=150.0)


def test_run_encode_fallback_false_never_runs_locally(monkeypatch):
    """The farm-level contract: fallback=False raises on an unreachable
    cluster (and on --local), while the legacy default still falls back."""
    farm = hive_series.farm
    monkeypatch.setattr(farm, "cluster_available",
                        lambda *a, **k: (False, "no nodes"))
    monkeypatch.setattr(farm, "run_capped_local",
                        lambda *a, **k: None)  # would be the fallback
    with pytest.raises(farm.FarmError, match="does not permit a local"):
        farm.run_encode(["ffmpeg"], inputs=[], out="o.mp4", fallback=False)
    with pytest.raises(farm.FarmError, match="does not permit a local"):
        farm.run_encode(["ffmpeg"], inputs=[], out="o.mp4", local=True,
                        fallback=False)
    # Legacy callers (other videos) keep the capped local fallback.
    assert farm.run_encode(["ffmpeg"], inputs=[], out="o.mp4") == "local"


def test_farm_side_verification_reads_the_pods_own_probe(monkeypatch):
    """local_probe=False verifies the fetched file from out/.done.json --
    probed by the pod -- and a missing pod probe is a visible failure, not
    a silent pass."""
    farm = hive_series.farm
    facts = farm._verify_fetched_on_farm("o.mp4", 162.0,
                                         {"duration": 162.03},
                                         label="t")
    assert facts["duration"] == 162.03
    with pytest.raises(farm.FarmError, match="re-time"):
        farm._verify_fetched_on_farm("o.mp4", 162.0, {"duration": 165.0},
                                     label="t")
    with pytest.raises(farm.FarmError, match="never probed"):
        farm._verify_fetched_on_farm("o.mp4", None, None, label="t")


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
        assert "rough" not in str(path), "the FINAL paths are promotion-only"


def test_rough_paths_are_the_final_names_under_the_rough_lane(manifest):
    """Rough-first (Hive AGENTS.md): builds write the reviewable artifacts.
    The rough paths are derived from the final ones -- the exact episode
    stem is identical across rough, final, and thumbnail."""
    first = hive_series.chapter_by_number(manifest, 1)
    rough = hive_series.episode_rough_path(first)
    assert rough == Path.home() / (
        "Videos/Hive/Season-of-the-Blueberries/rough/"
        "s01e01-the-enclave.mp4")
    assert rough.name == hive_series.episode_output_path(first).name
    rough_thumb = hive_series.thumbnail_rough_path(first)
    assert rough_thumb == Path.home() / (
        "Videos/Hive/Season-of-the-Blueberries/rough/"
        "s01e01-the-enclave-thumbnail.jpg")
    assert rough_thumb.name == hive_series.thumbnail_output_path(first).name
    rough_cut = hive_series.full_cut_rough_path(manifest)
    assert rough_cut == Path.home() / (
        "Videos/Hive/Season-of-the-Blueberries/season-01-full-rough.mp4")
    assert rough_cut.parent == hive_series.full_cut_path(manifest).parent


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
    # Select by id: doctoring the manifest record's anchor un-covers the
    # identical authoring-pass card (dedupe is exact), so the plan now
    # carries both lore cards.
    ship = next(o for o in plan["overlays"] if o["id"] == "savathuns-ship")
    assert ship["dur"] == 3.0


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
    monkeypatch.setattr(
        hive_series, "_source_preflight_farm",
        lambda *a, **k: (48000, None, "full-frame"))
    monkeypatch.setattr(hive_series, "verify_episode", lambda *a, **k: [])
    monkeypatch.setattr(hive_series, "ensure_source", lambda *a, **k: fake_source)
    # Deterministic offline faces: the avatar cache is local-only, so the
    # issued dossiers resolve the same way here and in CI.
    face = Image.new("RGBA", (512, 512), (32, 64, 96, 255))
    monkeypatch.setattr(hive_series, "resolve_face", lambda login: face)

    captured = {}

    def fake_run_encode(argv, **kwargs):
        captured["argv"] = [str(t) for t in argv]
        captured.update(kwargs)
        Path(kwargs["out"]).write_bytes(b"mp4")
        return "cluster"

    monkeypatch.setattr(hive_series.farm, "run_encode", fake_run_encode)

    out = hive_series.build_episode(manifest_path, 1, work_dir=tmp_path / "work")
    assert out == tmp_path / "rough" / "s01e01-the-enclave.mp4"
    assert out.exists(), "the encode wrote the ROUGH episode"
    assert not (tmp_path / "s01e01-the-enclave.mp4").exists(), \
        "a build must never create the top-level final"

    argv = captured["argv"]
    graph = argv[argv.index("-filter_complex") + 1]
    # cta, title, the three issued dossiers, chapter, closing.
    assert "concat=n=7:v=1:a=1" in graph
    # Every staged input is a real file: source + 6 stills + 3 overlays
    # (ikora-ch1, eris-ch1, the ship lore overlay).
    inputs = captured["inputs"]
    assert len(inputs) == 10
    assert inputs[0] == fake_source.resolve()
    for path in inputs:
        assert Path(path).exists(), f"staged input missing: {path}"
    assert captured["expected_duration"] == 162.0
    assert captured["fallback"] is False and captured["local_probe"] is False

    thumb = tmp_path / "rough" / "s01e01-the-enclave-thumbnail.jpg"
    assert thumb.exists()
    assert not (tmp_path / "s01e01-the-enclave-thumbnail.jpg").exists(), \
        "a build must never create the top-level thumbnail"
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
        "name": "Xe ".join(["Mr"] * 300), "commits": 1,
    }]
    data["contributor_ledger"]["credited_github_ids"] = [424242]
    manifest_path = tmp_path / "season.json"
    manifest_path.write_text(json.dumps(data))
    hive_series.load_manifest(manifest_path)  # the doctored record validates

    fake_source = tmp_path / "src.mkv"
    fake_source.write_bytes(b"mkv")
    monkeypatch.setattr(
        hive_series, "_source_preflight_farm",
        lambda *a, **k: (48000, None, "full-frame"))
    monkeypatch.setattr(hive_series, "verify_episode", lambda *a, **k: [])
    monkeypatch.setattr(hive_series, "ensure_source", lambda *a, **k: fake_source)
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


def test_build_episode_still_encodes_when_the_source_is_undecodable(
        manifest, tmp_path, monkeypatch):
    """An undecodable source drops EVERY seat -- both plates and the lore
    overlay -- from the rendered PNG list. The filtergraph must be built
    from that same pruned list, or it indexes an overlay input the argv
    never loops (issue: `episode_filtergraph` indexed the PLANNED overlay
    count while `_render_overlay_pngs` could render fewer or none). The
    unplated episode must still encode."""
    data = _delivery_manifest(manifest, tmp_path)
    manifest_path = tmp_path / "season.json"
    manifest_path.write_text(json.dumps(data))

    fake_source = tmp_path / "src.mkv"
    fake_source.write_bytes(b"mkv")
    monkeypatch.setattr(
        hive_series, "_source_preflight_farm",
        lambda *a, **k: (None, None, "undecodable"))
    monkeypatch.setattr(hive_series, "verify_episode", lambda *a, **k: [])
    monkeypatch.setattr(hive_series, "ensure_source", lambda *a, **k: fake_source)
    monkeypatch.setattr(hive_series, "resolve_face", lambda login: None)

    captured = {}

    def fake_run_encode(argv, **kwargs):
        captured["argv"] = [str(t) for t in argv]
        captured.update(kwargs)
        Path(kwargs["out"]).write_bytes(b"mp4")
        return "cluster"

    monkeypatch.setattr(hive_series.farm, "run_encode", fake_run_encode)

    out = hive_series.build_episode(manifest_path, 1, work_dir=tmp_path / "work")
    assert out.exists(), "the unplated episode still ships"

    argv = captured["argv"]
    graph = argv[argv.index("-filter_complex") + 1]
    # No overlay was rendered: the graph carries no overlay filter, and the
    # argv loops no PNG input for one -- input and graph counts agree.
    assert "overlay=0:0" not in graph
    inputs = captured["inputs"]
    assert argv.count("-i") == len(inputs) == 7  # source + 6 stills only
    for path in inputs:
        assert Path(path).exists(), f"staged input missing: {path}"

    sidecar = json.loads(
        (tmp_path / "work" / "s01e01-the-enclave-unresolved.json").read_text())
    # Both fixed-cast plates and the lore overlay are recorded as unplaced.
    undecodable = [item for item in sidecar
                   if "could not be decoded" in item.get("reason", "")]
    assert {item["id"] for item in undecodable} == \
        {"ikora-ch1", "eris-ch1", "savathuns-ship"}


def test_build_episode_still_encodes_when_one_plate_png_is_missing(
        manifest, tmp_path, monkeypatch):
    """A single plate that fails to materialise as a PNG (tools/plate.py's
    own omission or a write failure) must drop ONLY that one seat from both
    the rendered PNG list and the graph -- the remaining plate, the lore
    overlay, and the episode's own encode must still land on the RIGHT
    input indices, not the planned ones."""
    data = _delivery_manifest(manifest, tmp_path)
    manifest_path = tmp_path / "season.json"
    manifest_path.write_text(json.dumps(data))

    fake_source = tmp_path / "src.mkv"
    fake_source.write_bytes(b"mkv")
    monkeypatch.setattr(
        hive_series, "_source_preflight_farm",
        lambda *a, **k: (48000, None, "full-frame"))
    monkeypatch.setattr(hive_series, "verify_episode", lambda *a, **k: [])
    monkeypatch.setattr(hive_series, "ensure_source", lambda *a, **k: fake_source)
    monkeypatch.setattr(hive_series, "resolve_face", lambda login: None)

    def fake_render_all(plates, out_dir, picture=None):
        # Every plate but "ikora-ch1" renders; that one silently produces
        # no file, as a real tools/plate.py omission would.
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        for spec in plates:
            if spec["id"] == "ikora-ch1":
                continue
            Image.new("RGBA", (64, 64), (1, 2, 3, 255)).save(
                out_dir / f"plate_{spec['id']}.png")

    monkeypatch.setattr(hive_series.plate, "render_all", fake_render_all)

    captured = {}

    def fake_run_encode(argv, **kwargs):
        captured["argv"] = [str(t) for t in argv]
        captured.update(kwargs)
        Path(kwargs["out"]).write_bytes(b"mp4")
        return "cluster"

    monkeypatch.setattr(hive_series.farm, "run_encode", fake_run_encode)

    out = hive_series.build_episode(manifest_path, 1, work_dir=tmp_path / "work")
    assert out.exists(), "the episode still ships missing one plate"

    argv = captured["argv"]
    graph = argv[argv.index("-filter_complex") + 1]
    # 6 stills (input 1-6), so the two SURVIVING overlays (eris, the ship
    # lore overlay) must seat at inputs 7 and 8 -- never at the planned
    # index 8/9 that assumed the dropped ikora plate still had an input.
    assert "[7:v]overlay=0:0" in graph
    assert "[8:v]overlay=0:0" in graph
    assert "[9:v]" not in graph
    inputs = captured["inputs"]
    assert argv.count("-i") == len(inputs) == 9  # source + 6 stills + 2
    for path in inputs:
        assert Path(path).exists(), f"staged input missing: {path}"

    sidecar = json.loads(
        (tmp_path / "work" / "s01e01-the-enclave-unresolved.json").read_text())
    assert any(
        item.get("id") == "ikora-ch1" and "no plate was rendered" in item["reason"]
        for item in sidecar)


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
        hive_series, "_source_preflight_farm",
        lambda *a, **k: (48000, None, "full-frame"))
    monkeypatch.setattr(
        hive_series, "ensure_source", lambda *a, **k: fake_source)
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


def test_episode_input_digest_tracks_the_encode_contract(
        manifest, tmp_path, monkeypatch):
    """The delivery spec and the audio recipe are freshness inputs: a codec,
    spec-version, or audio change with IDENTICAL content must still
    invalidate the digest, because the same pixels encode to a different
    episode under different settings."""
    plan = hive_series.episode_plan(manifest, 1)
    staged = [_png(tmp_path / "a.png", (1, 2, 3, 255))]
    base = hive_series.episode_input_digest(plan, staged)

    monkeypatch.setattr(hive_series.conform, "SPEC_VERSION", "delivery-v999")
    assert hive_series.episode_input_digest(plan, staged) != base

    monkeypatch.undo()
    monkeypatch.setattr(hive_series, "AUDIO_BITRATE", "128k")
    assert hive_series.episode_input_digest(plan, staged) != base

    monkeypatch.undo()
    monkeypatch.setattr(hive_series.conform, "video_encode_args",
                        lambda: ["-c:v", "libx264", "-crf", "20"])
    assert hive_series.episode_input_digest(plan, staged) != base

    monkeypatch.undo()
    assert hive_series.episode_input_digest(plan, staged) == base


def test_freshness_skip_logs_the_current_unresolved_items(
        manifest, tmp_path, monkeypatch):
    """The skip prints the unresolved items, not just rewrites the sidecar:
    an operator watching a no-change run still sees the gaps."""
    manifest_path, data = _stage_episode(manifest, tmp_path, monkeypatch)
    data["overlays"].append({
        "id": "mystery", "kind": "lower-third", "chapter": 1,
        "source_at": 40.0, "position": "somewhere-unspecified",
        "lines": ["Unplaced."], "copy_source": "owner_authored",
        "nature": "project_lore", "note": "fixture",
    })
    manifest_path.write_text(json.dumps(data))
    calls = []
    monkeypatch.setattr(hive_series.farm, "run_encode", _fake_encode(calls))
    work = tmp_path / "work"
    hive_series.build_episode(manifest_path, 1, work_dir=work)
    assert len(calls) == 1

    lines = []
    hive_series.build_episode(manifest_path, 1, work_dir=work,
                              log=lines.append)
    assert len(calls) == 1, "an omitted overlay changes no encoded pixel"
    assert any("unresolved" in line and "mystery" in line
               for line in lines), \
        "a skip must print the current unresolved items"


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
        "login": "fixture", "github_id": 424242, "name": "Ada", "commits": 1,
    }]
    data["contributor_ledger"]["credited_github_ids"] = [424242]
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
    assert json.loads(sidecar.read_text()) == [
        {"login": login, "reason": "no cached GitHub avatar"}
        for login in EPISODE_ONE_DOSSIERS
    ]


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


def test_build_episode_rebuilds_when_the_digest_sidecar_is_missing(
        manifest, tmp_path, monkeypatch):
    """Freshness fails closed: a verified delivery with NO digest on record
    is re-encoded, not adopted -- the sidecar's absence can never be read
    as freshness. The rebuild writes the digest, and THEN the skip works."""
    manifest_path, _data = _stage_episode(manifest, tmp_path, monkeypatch)
    out = tmp_path / "rough" / "s01e01-the-enclave.mp4"
    out.parent.mkdir(parents=True)
    out.write_bytes(b"mp4")  # a prior rough build; verification is faked clean
    calls = []
    monkeypatch.setattr(hive_series.farm, "run_encode", _fake_encode(calls))
    work = tmp_path / "work"

    assert hive_series.build_episode(manifest_path, 1, work_dir=work) == out
    assert len(calls) == 1, "a missing digest sidecar must re-encode"
    digest = json.loads((work / "s01e01-the-enclave-inputs.json").read_text())
    assert digest["sha256"] and digest["inputs"]
    assert json.loads(
        (work / "s01e01-the-enclave-unresolved.json").read_text()) == [
        {"login": login, "reason": "no cached GitHub avatar"}
        for login in EPISODE_ONE_DOSSIERS
    ]

    hive_series.build_episode(manifest_path, 1, work_dir=work)
    assert len(calls) == 1, "the freshly written digest skips the rebuild"


def test_build_episode_rebuilds_when_the_digest_sidecar_is_corrupt(
        manifest, tmp_path, monkeypatch):
    """A sidecar that exists but cannot be read as a digest is corrupt, not
    current: the episode is re-encoded and the sidecar rewritten. Both
    malformed shapes fail closed -- unparseable JSON and JSON with no
    digest in it."""
    manifest_path, _data = _stage_episode(manifest, tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(hive_series.farm, "run_encode", _fake_encode(calls))
    work = tmp_path / "work"
    hive_series.build_episode(manifest_path, 1, work_dir=work)
    assert len(calls) == 1
    digest_path = work / "s01e01-the-enclave-inputs.json"

    digest_path.write_text("{not json\n")
    hive_series.build_episode(manifest_path, 1, work_dir=work)
    assert len(calls) == 2, "an unparseable sidecar must re-encode"

    digest_path.write_text(json.dumps({"inputs": []}) + "\n")
    hive_series.build_episode(manifest_path, 1, work_dir=work)
    assert len(calls) == 3, "a digest-less sidecar must re-encode"

    hive_series.build_episode(manifest_path, 1, work_dir=work)
    assert len(calls) == 3, "the rewritten sidecar skips again"


def test_build_episode_rebuilds_when_dossier_copy_changes_at_same_duration(
        manifest, tmp_path, monkeypatch):
    data = _delivery_manifest(manifest, tmp_path)
    data["chapters"][0]["dossiers"] = [{
        "login": "fixture", "github_id": 424242, "name": "Ada", "commits": 1,
    }]
    data["contributor_ledger"]["credited_github_ids"] = [424242]
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
    """Judge already-probed facts through the pure delivery check -- the
    probing itself is the farm's job (`_probe_delivery_streams_farm`), so
    these tests need no ffprobe seam at all."""
    return hive_series._delivery_stream_problems(
        "ep.mp4", duration, video,
        {"codec_name": "aac", "sample_rate": "48000",
         "channels": 2, "channel_layout": "stereo"},
        150.0, 0.5)


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


def test_delivery_probe_never_launders_a_wrong_average_through_r_frame_rate(
        tmp_path, monkeypatch):
    """A correct ``r_frame_rate`` must never excuse a genuinely wrong
    ``avg_frame_rate``: the average is the number actually encoded, and
    accepting on the nominal/declared rate instead would let a real 30 fps
    encode (muxed with a 60000/1001 container rate) verify as delivery
    cadence."""
    problems = _probe_with(tmp_path, monkeypatch, _conformant_video(
        avg_frame_rate="30/1", r_frame_rate="60000/1001"))
    assert any("frame rate" in p for p in problems)


def test_delivery_probe_still_accepts_the_measured_container_rounding(
        tmp_path, monkeypatch):
    """The known rounding case keeps working when the fix is scoped to
    ``avg_frame_rate`` alone: the measured average itself, not the nominal
    rate, is what has to fall inside the documented slack."""
    problems = _probe_with(tmp_path, monkeypatch, _conformant_video(
        avg_frame_rate="32640000/544621", r_frame_rate="60000/1001"))
    assert problems == []


def test_delivery_probe_reports_a_duration_mismatch(tmp_path, monkeypatch):
    problems = _probe_with(tmp_path, monkeypatch, _conformant_video(),
                           duration=149.0)
    assert any("duration" in p for p in problems)


def test_conform_for_join_reads_container_rounded_fps_as_delivery(
        tmp_path, monkeypatch):
    """32640000/544621 is the container-rounded 60000/1001: the join probe
    must hand conform.ensure props with no mismatch, or every delivered
    episode would pay a conform encode on every cut."""
    video = _conformant_video(avg_frame_rate="32640000/544621",
                              r_frame_rate="32640000/544621")
    monkeypatch.setattr(
        hive_series, "_probe_streams_farm",
        lambda *a, **k: {"format": {"duration": "150.0"},
                         "streams": [dict(video, codec_type="video"),
                                     {"codec_type": "audio",
                                      "codec_name": "aac",
                                      "sample_rate": "48000"}]})
    seen = {}

    def fake_ensure(path, _probe=None, **kwargs):
        seen["mismatches"] = hive_series.conform.mismatches(_probe(path))
        seen["kwargs"] = kwargs
        return path, "conforms" if not seen["mismatches"] else "conformed"

    monkeypatch.setattr(hive_series.conform, "ensure", fake_ensure)
    target = tmp_path / "ep.mp4"
    target.write_bytes(b"mp4")
    joined, status = hive_series._conform_for_join(target, lambda *a: None)
    assert seen["mismatches"] == [], \
        "container rounding must not trigger a conform encode"
    assert (joined, status) == (target, "conforms")
    # The conform probe came from the farm seam, and a repair encode would
    # be farm-only -- never a local fallback.
    assert seen["kwargs"]["use_farm"] is True
    assert seen["kwargs"]["allow_local"] is False
    assert seen["kwargs"]["local_probe"] is False


# --- the cut's one interface ---------------------------------------------------


def _fake_episode_files(data, skip=()):
    """A built ROUGH 'mp4' for every chapter not in ``skip`` -- the cut
    joins roughs, so the fakes live under rough/."""
    for chapter in data["chapters"]:
        if chapter["number"] in skip:
            continue
        final = Path(chapter["output"])
        rough = final.parent / "rough" / final.name
        rough.parent.mkdir(parents=True, exist_ok=True)
        rough.write_bytes(b"mp4")


def _stage_cut(manifest, tmp_path, monkeypatch, skip=()):
    """A full season offline: redirected outputs, faked build/verify/probe,
    and conform.ensure pinned to 'conforms'. Returns (manifest_path, data)."""
    data = _delivery_manifest(manifest, tmp_path)
    manifest_path = tmp_path / "season.json"
    manifest_path.write_text(json.dumps(data))
    _fake_episode_files(data, skip=skip)
    monkeypatch.setattr(hive_series, "build_all", lambda *a, **k: [])
    monkeypatch.setattr(hive_series, "verify_episode", lambda *a, **k: [])
    monkeypatch.setattr(hive_series.conform, "ensure",
                        lambda path, **k: (path, "conforms"))
    monkeypatch.setattr(hive_series, "_probe_delivery_streams_farm",
                        lambda *a, **k: [])
    monkeypatch.setattr(
        hive_series, "_probe_audio_farm",
        lambda *a, **k: {"codec_name": "aac", "sample_rate": "48000",
                         "channels": 2, "channel_layout": "stereo"})
    return manifest_path, data


def test_build_cut_ships_the_cut_when_one_episode_is_bad(
        manifest, tmp_path, monkeypatch):
    """One bad episode is a finding, never a veto: the other eleven join,
    the cut ships, and the report names the missing episode. Verification
    findings never withhold the season cut."""
    manifest_path, data = _stage_cut(manifest, tmp_path, monkeypatch,
                                     skip={4})
    monkeypatch.setattr(
        hive_series, "verify_episode",
        lambda m, number, **k: ["s01e04-the-relic.mp4: missing or empty"]
        if number == 4 else [])
    joined = []

    def fake_concat(manifest, out_path=None, paths=None, **kwargs):
        joined.extend(Path(p).name for p in paths)
        out_path = Path(out_path) if out_path else             hive_series.full_cut_path(manifest)
        out_path.write_bytes(b"mp4")
        return out_path

    monkeypatch.setattr(hive_series, "concat_episodes", fake_concat)
    probed = {}

    def fake_probe(path, expected, tolerance):
        probed[Path(path).name] = expected
        return []

    monkeypatch.setattr(hive_series, "_probe_delivery_streams_farm", fake_probe)
    out, problems = hive_series.build_cut(manifest_path)
    assert out.exists(), "one bad episode must not prevent the cut"
    assert len(joined) == 11
    assert "s01e04-the-relic.mp4" not in joined
    assert any("s01e04" in problem for problem in problems)
    expected_joined = sum(
        hive_series.episode_expected_duration(data, c)
        for c in data["chapters"] if c["number"] != 4)
    assert probed[Path(out).name] == expected_joined, \
        "the cut is verified against the episodes actually joined"
    assert probed[Path(out).name] != \
        hive_series.cut_expected_duration(data), \
        "the joined sum is not the full manifest's duration"


def test_build_cut_omits_an_episode_whose_audio_cannot_join(
        manifest, tmp_path, monkeypatch):
    """The concat stream-copies sound, so an episode whose audio is not the
    delivery codec/rate/layout is reported and left out of the best
    reachable cut -- never joined blind, never re-encoded on a second
    audio path."""
    manifest_path, data = _stage_cut(manifest, tmp_path, monkeypatch)

    def fake_audio(path, *a, **k):
        if "s01e04" in Path(path).name:
            return {"codec_name": "mp3", "sample_rate": "44100",
                    "channels": 2, "channel_layout": "stereo"}
        return {"codec_name": "aac", "sample_rate": "48000",
                "channels": 2, "channel_layout": "stereo"}

    monkeypatch.setattr(hive_series, "_probe_audio_farm", fake_audio)
    joined = []

    def fake_concat(manifest, out_path=None, paths=None, **kwargs):
        joined.extend(Path(p).name for p in paths)
        out_path = Path(out_path) if out_path else             hive_series.full_cut_path(manifest)
        out_path.write_bytes(b"mp4")
        return out_path

    monkeypatch.setattr(hive_series, "concat_episodes", fake_concat)
    out, problems = hive_series.build_cut(manifest_path)
    assert out.exists(), "bad audio on one episode must not prevent the cut"
    assert len(joined) == 11
    assert "s01e04-the-relic.mp4" not in joined
    finding = next(p for p in problems if "s01e04" in p)
    assert "audio codec 'mp3' is not aac" in finding
    assert "sample rate '44100' is not 48000" in finding
    assert "joins without it" in finding


def test_build_cut_substitutes_a_conformed_copy_before_the_blind_join(
        manifest, tmp_path, monkeypatch):
    """A delivered episode that is not join-compatible goes through
    conform.ensure and the CONFORMED copy is what joins -- the substitution
    is logged, the cut still ships, and a repaired input is not a problem."""
    manifest_path, data = _stage_cut(manifest, tmp_path, monkeypatch)
    substitute = tmp_path / "conformed" / "s01e04-the-relic.mp4"
    substitute.parent.mkdir()
    substitute.write_bytes(b"mp4")

    def fake_ensure(path, **kwargs):
        if "s01e04" in Path(path).name:
            return substitute, "conformed"
        return path, "conforms"

    monkeypatch.setattr(hive_series.conform, "ensure", fake_ensure)
    joined = []

    def fake_concat(manifest, out_path=None, paths=None, **kwargs):
        joined.extend(Path(p) for p in paths)
        out_path = Path(out_path) if out_path else             hive_series.full_cut_path(manifest)
        out_path.write_bytes(b"mp4")
        return out_path

    monkeypatch.setattr(hive_series, "concat_episodes", fake_concat)
    lines = []
    out, problems = hive_series.build_cut(manifest_path, log=lines.append)
    assert problems == []
    assert len(joined) == 12 and substitute in joined
    assert any("conformed copy" in line and "s01e04" in line
               for line in lines)


def test_build_cut_reports_an_undecodable_episode_and_joins_the_rest(
        manifest, tmp_path, monkeypatch):
    """An episode that cannot even be probed is reported explicitly and left
    out; the best reachable cut still ships from the decodable episodes."""
    manifest_path, data = _stage_cut(manifest, tmp_path, monkeypatch)

    def fake_ensure(path, **kwargs):
        if "s01e07" in Path(path).name:
            raise RuntimeError("no video stream in it")
        return path, "conforms"

    monkeypatch.setattr(hive_series.conform, "ensure", fake_ensure)
    joined = []

    def fake_concat(manifest, out_path=None, paths=None, **kwargs):
        joined.extend(Path(p).name for p in paths)
        out_path = Path(out_path) if out_path else             hive_series.full_cut_path(manifest)
        out_path.write_bytes(b"mp4")
        return out_path

    monkeypatch.setattr(hive_series, "concat_episodes", fake_concat)
    out, problems = hive_series.build_cut(manifest_path)
    assert out.exists()
    assert len(joined) == 11 and "s01e07-council.mp4" not in joined
    assert any("s01e07" in problem and "joins without it" in problem
               for problem in problems)


def test_build_cut_joins_verified_episodes_and_reports_the_cut(
        manifest, tmp_path, monkeypatch):
    manifest_path, data = _stage_cut(manifest, tmp_path, monkeypatch)
    cut = tmp_path / "season-01-full-rough.mp4"

    def fake_concat(manifest, out_path=None, **kwargs):
        cut.write_bytes(b"mp4")
        return cut

    monkeypatch.setattr(hive_series, "concat_episodes", fake_concat)
    probed = []

    def fake_probe(path, expected, tolerance):
        probed.append(Path(path).name)
        return []

    monkeypatch.setattr(hive_series, "_probe_delivery_streams_farm", fake_probe)
    out, problems = hive_series.build_cut(manifest_path)
    assert out == cut
    assert problems == []
    assert probed == ["season-01-full-rough.mp4"], \
        "episodes were verified pre-concat; the post-join probe is the " \
        "ROUGH cut's"
    assert not (tmp_path / "season-01-full.mp4").exists(), \
        "the review assembly must never write the final cut"


def test_cut_command_goes_through_build_cut(tmp_path, monkeypatch):
    monkeypatch.setattr(hive_series, "build_cut",
                        lambda *a, **k: (tmp_path / "season-01-full.mp4", []))
    assert hive_series.main(["cut"]) == 0


def test_cut_command_reports_problems_and_still_returns_the_cut(
        tmp_path, monkeypatch):
    """Findings never withhold the film: the cut ships, and the exit code
    carries the report's cleanliness."""
    cut = tmp_path / "season-01-full.mp4"
    cut.write_bytes(b"mp4")
    monkeypatch.setattr(hive_series, "build_cut",
                        lambda *a, **k: (cut, ["s01e07: probe failed"]))
    assert hive_series.main(["cut"]) == 1


# --- Task 4: weekly contributor recognition ---------------------------------
#
# Offline like the rest of the suite: every GitHub call goes through a fake
# runner, so pagination, exclusion, sorting and the ledger update are all
# exercised without a network.

RECOGNITION_REPOS = [
    "kubestellar/kubestellar",
    "kubestellar/kubeflex",
    "kubestellar/console",
    "kubestellar/docs",
    "kubestellar/hive",
]

FIXED_CAST_IDS = {15972783, 98050010, 104345443}

SINCE = "2026-08-22T00:00:00Z"
UNTIL = "2026-08-29T12:00:00Z"


def _commit(sha, login, account_id, type_="User"):
    return {
        "sha": sha,
        "author": {
            "id": account_id,
            "login": login,
            "type": type_,
            "node_id": f"U_kgDO{account_id}",
            "html_url": f"https://github.com/{login}",
            "avatar_url": f"https://avatars.githubusercontent.com/u/{account_id}?v=4",
        },
    }


def _profile(login, account_id, name=None, type_="User"):
    return {
        "id": account_id,
        "node_id": f"U_kgDO{account_id}",
        "login": login,
        "name": name,
        "html_url": f"https://github.com/{login}",
        "avatar_url": f"https://avatars.githubusercontent.com/u/{account_id}?v=4",
        "type": type_,
    }


def _fake_gh(commits_by_repo, profiles=None):
    """A runner over canned API responses. ``commits_by_repo`` maps a repo to
    a list of PAGES (each page a list of commit objects) so the paginated
    parser is exercised; ``profiles`` maps a numeric account ID to the
    user-by-ID API body. A repo or ID with no entry raises -- the
    failed-read case."""
    profiles = profiles or {}

    def run(cmd):
        text = " ".join(cmd)
        for repo, pages in commits_by_repo.items():
            if f"repos/{repo}/commits" in text:
                return "".join(json.dumps(p) for p in pages)
        for account_id, body in profiles.items():
            # The profile command is exactly `gh api user/{id}`: match the
            # whole final token so id 8100 can never answer for 81000.
            if text.endswith(f"user/{account_id}"):
                return json.dumps(body)
        raise hive_series.RecognitionError(f"no canned response: {text}")

    return run


def _recognition_manifest(raw, credited=()):
    """A valid manifest copy with no chapter issued and a primed ledger."""
    data = json.loads(json.dumps(raw))
    for chapter in data["chapters"]:
        chapter.pop("dossiers", None)
        chapter.pop("dossier_note", None)
    data["contributor_ledger"] = {
        "credited_github_ids": list(credited),
        "repositories": list(RECOGNITION_REPOS),
        "snapshots": [],
    }
    return data


def test_commits_command_is_paginated_and_windowed():
    cmd = hive_series.commits_command("kubestellar/hive", SINCE, UNTIL)
    assert cmd[:3] == ["gh", "api", "--paginate"]
    assert cmd[3] == (f"repos/kubestellar/hive/commits?since={SINCE}"
                      f"&until={UNTIL}&per_page=100")


def test_parse_paginated_json_reads_concatenated_pages():
    text = json.dumps([{"sha": "a"}]) + json.dumps([{"sha": "b"},
                                                    {"sha": "c"}])
    assert [c["sha"] for c in hive_series.parse_paginated_json(text)] == \
        ["a", "b", "c"]
    assert hive_series.parse_paginated_json("") == []


def test_fixture_runner_replays_pages_and_fails_unknown_repos():
    fixture = {
        "repos/kubestellar/hive/commits": {"pages": [[{"sha": "x"}],
                                                     [{"sha": "y"}]]},
        "user/583231": {"body": {"id": 583231, "login": "octocat"}},
    }
    runner = hive_series.fixture_runner(fixture)
    out = runner(hive_series.commits_command("kubestellar/hive", SINCE, UNTIL))
    assert [c["sha"] for c in hive_series.parse_paginated_json(out)] == \
        ["x", "y"]
    assert json.loads(runner(hive_series.profile_command(583231))) == \
        {"id": 583231, "login": "octocat"}
    with pytest.raises(hive_series.RecognitionError):
        runner(hive_series.commits_command("kubestellar/docs", SINCE, UNTIL))


def _activity(commits_by_repo, profiles=None, credited=(), raw=None):
    manifest = _recognition_manifest(
        raw if raw is not None else json.loads(MANIFEST_PATH.read_text()),
        credited=credited)
    # The unit fixture fakes exactly these repos; the selection must read
    # every configured repo, so configure the faked set.
    manifest["contributor_ledger"]["repositories"] = list(commits_by_repo)
    return hive_series.recognition_snapshot(
        manifest, SINCE, UNTIL,
        runner=_fake_gh(commits_by_repo, profiles), now=UNTIL)


def test_bots_and_non_user_accounts_are_excluded():
    pages = [[
        _commit("a1", "dependabot[bot]", 1001, type_="Bot"),
        _commit("a2", "some-org", 1002, type_="Organization"),
        _commit("a3", "real-person", 1003),
    ]]
    snapshot = _activity(
        {"kubestellar/hive": pages},
        profiles={1003: _profile("real-person", 1003, "Real Person")})
    by_login = {c["login"]: c for c in snapshot["candidates"]}
    assert "not a User" in by_login["dependabot[bot]"]["excluded"]
    assert "not a User" in by_login["some-org"]["excluded"]
    assert "excluded" not in by_login["real-person"]
    assert snapshot["selected_github_ids"] == [1003]


def test_fixed_cast_is_excluded_by_numeric_id():
    pages = [[_commit("c1", "angiejones", 15972783),
              _commit("c2", "newcomer", 2002)]]
    snapshot = _activity(
        {"kubestellar/hive": pages},
        profiles={2002: _profile("newcomer", 2002)})
    by_login = {c["login"]: c for c in snapshot["candidates"]}
    assert by_login["angiejones"]["excluded"] == "fixed cast"
    assert snapshot["selected_github_ids"] == [2002]


def test_a_renamed_login_is_excluded_by_the_same_numeric_id():
    """The ledger keys on the durable numeric ID: an already-credited account
    that has since renamed is still excluded."""
    pages = [[_commit("r1", "renamed-login", 3003)]]
    snapshot = _activity({"kubestellar/hive": pages}, credited=[3003])
    candidate = snapshot["candidates"][0]
    assert candidate["login"] == "renamed-login"
    assert candidate["excluded"] == "already credited in the no-repeat ledger"
    assert snapshot["selected_github_ids"] == []


def test_commits_deduplicate_by_sha_across_pages_and_repos():
    dup = _commit("dddd", "dev", 4004)
    snapshot = _activity(
        {"kubestellar/hive": [[dup], [dup, _commit("e1", "dev", 4004)]],
         "kubestellar/docs": [[_commit("dddd", "dev", 4004)]]},
        profiles={4004: _profile("dev", 4004)})
    candidate = snapshot["candidates"][0]
    assert candidate["commits"] == 2
    # "dddd" is one commit however many pages or repos return it; it is
    # evidence in the first configured repo that reported it.
    assert candidate["evidence"] == [
        {"repo": "kubestellar/hive", "shas": ["dddd", "e1"]},
    ]


def test_unlinked_commits_have_no_durable_id_and_are_skipped():
    pages = [[{"sha": "x1", "author": None},
              {"sha": "x2", "author": {"login": "ghost"}},
              _commit("x3", "dev", 5005)]]
    snapshot = _activity({"kubestellar/hive": pages},
                         profiles={5005: _profile("dev", 5005)})
    assert [c["login"] for c in snapshot["candidates"]] == ["dev"]


def test_selection_orders_by_commits_then_login_then_id():
    commits = [
        _commit("t1", "zed", 9001),      # 1 commit
        _commit("t2", "bravo", 9002),    # 2 commits
        _commit("t3", "bravo", 9002),
        _commit("t4", "Alpha", 9003),    # 2 commits, ties bravo, login wins
        _commit("t5", "Alpha", 9003),
        _commit("t6", "charlie", 9004),  # 2 commits
        _commit("t7", "charlie", 9004),
        _commit("t8", "delta", 9005),    # 2 commits; over the limit
        _commit("t9", "delta", 9005),
    ]
    profiles = {cid: _profile(login, cid)
                for login, cid in [("zed", 9001), ("bravo", 9002),
                                   ("Alpha", 9003), ("charlie", 9004),
                                   ("delta", 9005)]}
    snapshot = _activity({"kubestellar/hive": [commits]}, profiles=profiles)
    assert snapshot["selected_github_ids"] == [9003, 9002, 9004]
    # The selected profile snapshots carry the full factual field set.
    alpha = next(c for c in snapshot["candidates"] if c["id"] == 9003)
    assert alpha["login"] == "Alpha"
    for field in ("node_id", "html_url", "avatar_url", "type",
                  "fetched_at", "commits", "evidence"):
        assert alpha[field] is not None


def test_profile_command_resolves_by_durable_numeric_id():
    assert hive_series.profile_command(583231) == \
        ["gh", "api", "user/583231"]


def test_a_recycled_login_cannot_attach_the_new_owners_identity():
    """Account 8100 authored commits under a login it has since freed, and
    account 8200 recycled that login. Resolving by login would hang the NEW
    owner's name, PFP and profile URL on the ORIGINAL author's commits --
    a false claim about a real person. Resolving by durable numeric ID
    (``user/{id}``) keeps every account on its own identity, and the two
    same-login candidates still order stably by numeric ID."""
    commits = [_commit("u1", "same-login", 8100),
               _commit("u2", "same-login", 8200)]
    snapshot = _activity({"kubestellar/hive": [commits]}, profiles={
        8100: _profile("freed-the-login", 8100, name="Original Owner"),
        8200: _profile("same-login", 8200, name="New Owner"),
    })
    by_id = {c["id"]: c for c in snapshot["candidates"]}
    original, new = by_id[8100], by_id[8200]
    assert original["login"] == "freed-the-login"
    assert original["name"] == "Original Owner"
    assert original["avatar_url"] == \
        "https://avatars.githubusercontent.com/u/8100?v=4"
    assert original["html_url"] == "https://github.com/freed-the-login"
    assert new["name"] == "New Owner"
    assert new["avatar_url"] == \
        "https://avatars.githubusercontent.com/u/8200?v=4"
    # Two accounts that shared one login string stay two distinct,
    # correctly-identified candidates in a stable order.
    eligible = [c for c in snapshot["candidates"] if "excluded" not in c]
    assert [c["id"] for c in eligible] == [8100, 8200]


def test_a_profile_returned_for_the_wrong_id_fails_the_selection():
    """The resolved profile's id must exactly match the commit-author ID;
    anything else is another person's identity and aborts the run."""
    pages = [[_commit("m1", "someone", 8100)]]
    with pytest.raises(hive_series.RecognitionError, match="8100"):
        _activity({"kubestellar/hive": pages},
                  profiles={8100: _profile("someone", 9999)})


def test_a_profile_read_failure_fails_the_selection_not_the_candidate():
    """A transient API failure never silently demotes a candidate: the
    whole selection fails, like an unreadable repository."""
    pages = [[_commit("f1", "dev", 6001)]]
    with pytest.raises(hive_series.RecognitionError,
                       match="could not be resolved"):
        _activity({"kubestellar/hive": pages})  # no canned profile for 6001


def test_fixture_runner_profile_matching_is_exact():
    """The canned profile endpoint matches the whole final token:
    ``user/8100`` must never answer for ``user/81000``."""
    runner = hive_series.fixture_runner({
        "user/8100": {"body": {"id": 8100, "login": "octocat"}},
    })
    assert json.loads(runner(hive_series.profile_command(8100))) == \
        {"id": 8100, "login": "octocat"}
    with pytest.raises(hive_series.RecognitionError):
        runner(hive_series.profile_command(81000))


def test_a_definitive_404_is_a_recorded_exclusion_not_a_failure(raw):
    """A suspended or deleted account -- GitHub answers user/{id} with a
    definitive HTTP 404 -- cannot wedge every future weekly snapshot: the
    candidate is recorded with the exclusion "profile no longer exists"
    and the selection proceeds with the rest."""
    fixture = {
        "repos/kubestellar/hive/commits": {"pages": [[
            _commit("d1", "suspended-user", 7001),
            _commit("d2", "present-user", 7002),
        ]]},
        "user/7001": {"status": 404},
        "user/7002": {"body": _profile("present-user", 7002)},
    }
    manifest = _recognition_manifest(raw)
    manifest["contributor_ledger"]["repositories"] = ["kubestellar/hive"]
    snapshot = hive_series.recognition_snapshot(
        manifest, SINCE, UNTIL,
        runner=hive_series.fixture_runner(fixture), now=UNTIL)
    by_id = {c["id"]: c for c in snapshot["candidates"]}
    assert by_id[7001]["excluded"] == "profile no longer exists"
    assert by_id[7001]["name"] is None
    assert "excluded" not in by_id[7002]
    assert snapshot["selected_github_ids"] == [7002]


def test_a_transient_profile_failure_is_retried_once(raw):
    """One ambiguous failure (a 5xx, not a definitive 404) is retried
    exactly once; when the retry succeeds the candidate is resolved and
    selected normally."""
    base = hive_series.fixture_runner({
        "repos/kubestellar/hive/commits": {"pages": [[
            _commit("r1", "dev", 7001)]]},
        "user/7001": {"body": _profile("dev", 7001, "Dev Somebody")},
    })
    calls = []

    def flaky(cmd):
        if cmd[-1] == "user/7001":
            calls.append(cmd)
            if len(calls) == 1:
                raise hive_series.RecognitionError(
                    "gh api user/7001 failed: gh: Bad Gateway (HTTP 502)")
        return base(cmd)

    manifest = _recognition_manifest(raw)
    manifest["contributor_ledger"]["repositories"] = ["kubestellar/hive"]
    snapshot = hive_series.recognition_snapshot(
        manifest, SINCE, UNTIL, runner=flaky, now=UNTIL)
    assert len(calls) == 2
    assert snapshot["selected_github_ids"] == [7001]
    assert snapshot["candidates"][0]["name"] == "Dev Somebody"


def test_a_persistent_transient_failure_aborts_before_any_write(
        raw, tmp_path):
    """The retry is exactly once: a profile read that keeps failing
    ambiguously aborts the whole selection BEFORE the manifest or ledger is
    touched -- a candidate is never silently demoted, nothing half-written.
    """
    data = _recognition_manifest(raw)
    path = tmp_path / "season.json"
    original = json.dumps(data, indent=2)
    path.write_text(original)
    commits = {repo: [[]] for repo in RECOGNITION_REPOS}
    commits["kubestellar/hive"] = [[_commit("w1", "flaky", 7009)]]
    attempts = []

    def failing(cmd):
        if cmd[-1] == "user/7009":
            attempts.append(cmd)
            raise hive_series.RecognitionError(
                "gh api user/7009 failed: gh: Service Unavailable (HTTP 503)")
        return _fake_gh(commits)(cmd)

    with pytest.raises(hive_series.RecognitionError,
                       match="could not be resolved"):
        hive_series.select_next_episode(
            path, since=SINCE, runner=failing, now=UNTIL, log=lambda m: None)
    assert len(attempts) == 2  # one retry, never a silent skip
    assert path.read_text() == original


def test_empty_activity_still_issues_the_episode_with_a_note(raw, tmp_path):
    data = _recognition_manifest(raw)
    path = tmp_path / "season.json"
    path.write_text(json.dumps(data))
    empty = {repo: [[]] for repo in RECOGNITION_REPOS}
    snapshot, chapter = hive_series.select_next_episode(
        path, since=SINCE, runner=_fake_gh(empty), now=UNTIL, log=lambda m: None)
    assert chapter["number"] == 1
    assert chapter["dossiers"] == []
    assert "no eligible contributors" in chapter["dossier_note"]
    saved = json.loads(path.read_text())
    assert saved["chapters"][0]["dossiers"] == []
    assert "no eligible contributors" in saved["chapters"][0]["dossier_note"]
    assert saved["contributor_ledger"]["credited_github_ids"] == []
    assert saved["contributor_ledger"]["snapshots"][0]["episode"] == 1
    assert snapshot["selected_github_ids"] == []


def test_a_failed_repo_read_leaves_the_manifest_untouched(raw, tmp_path):
    data = _recognition_manifest(raw)
    path = tmp_path / "season.json"
    original = json.dumps(data, indent=2)
    path.write_text(original)
    commits = {repo: [[]] for repo in RECOGNITION_REPOS}
    del commits["kubestellar/docs"]  # unreadable
    with pytest.raises(hive_series.RecognitionError, match="kubestellar/docs"):
        hive_series.select_next_episode(
            path, since=SINCE, runner=_fake_gh(commits), now=UNTIL,
            log=lambda m: None)
    assert path.read_text() == original


def test_a_failed_profile_resolution_leaves_the_manifest_untouched(
        raw, tmp_path):
    """An API failure mid-selection is not a quieter selection: the run
    raises BEFORE any manifest or ledger mutation, exactly like a failed
    repository read, so no candidate is silently demoted and nothing is
    half-written."""
    data = _recognition_manifest(raw)
    path = tmp_path / "season.json"
    original = json.dumps(data, indent=2)
    path.write_text(original)
    commits = {repo: [[]] for repo in RECOGNITION_REPOS}
    commits["kubestellar/hive"] = [[_commit("p1", "ghosted", 7001)]]
    # No canned profile for account 7001: the profile read fails.
    with pytest.raises(hive_series.RecognitionError,
                       match="could not be resolved"):
        hive_series.select_next_episode(
            path, since=SINCE, runner=_fake_gh(commits), now=UNTIL,
            log=lambda m: None)
    assert path.read_text() == original


def test_select_next_fills_the_next_chapter_and_the_ledger(raw, tmp_path):
    data = _recognition_manifest(raw)
    path = tmp_path / "season.json"
    path.write_text(json.dumps(data))
    commits = {repo: [[]] for repo in RECOGNITION_REPOS}
    commits["kubestellar/hive"] = [[
        _commit("s1", "winner", 7001), _commit("s2", "winner", 7001),
        _commit("s3", "second", 7002),
    ]]
    profiles = {7001: _profile("winner", 7001, "Win Somebody"),
                7002: _profile("second", 7002)}
    snapshot, chapter = hive_series.select_next_episode(
        path, since=SINCE, runner=_fake_gh(commits, profiles), now=UNTIL,
        log=lambda m: None)
    assert chapter["number"] == 1
    assert snapshot["selected_github_ids"] == [7001, 7002]
    assert chapter["dossiers"] == [
        {"login": "winner", "github_id": 7001, "name": "Win Somebody",
         "commits": 2, "node_id": "U_kgDO7001",
         "html_url": "https://github.com/winner",
         "avatar_url": "https://avatars.githubusercontent.com/u/7001?v=4",
         "type": "User", "fetched_at": UNTIL},
        {"login": "second", "github_id": 7002, "name": None,
         "commits": 1, "node_id": "U_kgDO7002",
         "html_url": "https://github.com/second",
         "avatar_url": "https://avatars.githubusercontent.com/u/7002?v=4",
         "type": "User", "fetched_at": UNTIL},
    ]
    saved = hive_series.load_manifest(path)
    assert saved["contributor_ledger"]["credited_github_ids"] == [7001, 7002]
    assert saved["contributor_ledger"]["snapshots"][0]["window"] == \
        {"since": SINCE, "until": UNTIL}

    # The next run with the same activity cannot re-credit them: the ledger
    # now holds both IDs, so the week issues empty, not a repeat.
    snapshot2, chapter2 = hive_series.select_next_episode(
        path, runner=_fake_gh(commits, profiles), now="2026-09-05T00:00:00Z",
        log=lambda m: None)
    assert chapter2["number"] == 2
    assert chapter2["dossiers"] == []
    assert snapshot2["window"]["since"] == UNTIL
    assert snapshot2["selected_github_ids"] == []
    saved = hive_series.load_manifest(path)
    assert saved["contributor_ledger"]["credited_github_ids"] == [7001, 7002]


def test_select_next_never_overwrites_a_filled_chapter(raw, tmp_path):
    data = _recognition_manifest(raw)
    data["chapters"][0]["dossiers"] = [
        {"login": "already", "github_id": 6001, "name": "", "commits": 2}
    ]
    data["contributor_ledger"]["credited_github_ids"] = [6001]
    path = tmp_path / "season.json"
    path.write_text(json.dumps(data))
    commits = {repo: [[]] for repo in RECOGNITION_REPOS}
    commits["kubestellar/hive"] = [[_commit("n1", "newbie", 6002)]]
    profiles = {6002: _profile("newbie", 6002)}
    _snapshot, chapter = hive_series.select_next_episode(
        path, since=SINCE, runner=_fake_gh(commits, profiles), now=UNTIL,
        log=lambda m: None)
    assert chapter["number"] == 2
    saved = json.loads(path.read_text())
    assert saved["chapters"][0]["dossiers"] == [
        {"login": "already", "github_id": 6001, "name": "", "commits": 2}
    ], "an issued chapter is never rewritten"
    assert saved["chapters"][1]["dossiers"][0]["github_id"] == 6002


def test_select_next_with_every_chapter_issued_records_the_window_only(
        raw, tmp_path):
    data = _recognition_manifest(raw)
    for chapter in data["chapters"]:
        chapter["dossiers"] = []
    path = tmp_path / "season.json"
    path.write_text(json.dumps(data))
    empty = {repo: [[]] for repo in RECOGNITION_REPOS}
    snapshot, chapter = hive_series.select_next_episode(
        path, since=SINCE, runner=_fake_gh(empty), now=UNTIL,
        log=lambda m: None)
    assert chapter is None
    assert snapshot["episode"] is None
    assert "already issued" in snapshot["note"]


def test_select_next_without_a_prior_snapshot_needs_an_explicit_since(
        raw, tmp_path):
    path = tmp_path / "season.json"
    path.write_text(json.dumps(_recognition_manifest(raw)))
    with pytest.raises(hive_series.RecognitionError, match="--since"):
        hive_series.select_next_episode(path, runner=_fake_gh({}),
                                        log=lambda m: None)


def test_status_reports_issued_and_delivered(raw):
    data = _recognition_manifest(raw)
    data["chapters"][0]["dossiers"] = []
    rows = hive_series.recognition_status(data)
    assert rows[0]["issued"] is True and rows[0]["dossiers"] == 0
    assert rows[1]["issued"] is False and rows[1]["dossiers"] is None
    assert all("delivered" in row and "output" in row for row in rows)


def test_the_committed_manifest_configures_the_five_repositories(manifest):
    assert manifest["contributor_ledger"]["repositories"] == \
        RECOGNITION_REPOS


def test_fixed_cast_carries_the_durable_numeric_ids(manifest):
    assert {m["github_login"]: m["github_id"]
            for m in manifest["fixed_cast"]} == {
        "angiejones": 15972783,
        "Swil78": 98050010,
        "CortNick": 104345443,
    }


# --- the weekly workflow and the avatar refresh --------------------------------

WEEKLY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "hive-weekly.yml"
AVATARS_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "avatars.yml"


def test_weekly_workflow_schedule_dispatch_permissions_and_serialization():
    text = WEEKLY_WORKFLOW.read_text()
    assert "23 17 * * 6" in text, "Saturday at a non-zero UTC minute"
    assert "workflow_dispatch" in text
    assert "contents: write" in text
    assert "pull-requests: write" in text
    assert "cancel-in-progress: false" in text


def test_weekly_workflow_proposes_and_never_renders_or_self_merges():
    """Scheduled runs open a PR; they never encode footage, never push to
    main, and never merge -- the human merge IS the approval for putting a
    real person on screen."""
    text = WEEKLY_WORKFLOW.read_text()
    assert "select-next" in text
    for forbidden in ("build-all", " hive-cut", "tools/hive_series.py cut",
                      "gh pr merge", "push origin main", "secrets."):
        assert forbidden not in text
    # The GITHUB_TOKEN caveat must be written where the operator reads it.
    assert "does not trigger CI" in text


def test_weekly_workflow_proposal_branches_are_unique_per_run():
    """Two runs can never race or clobber the same proposal ref: the branch
    name carries the unique github.run_id, not just the date."""
    text = WEEKLY_WORKFLOW.read_text()
    assert 'branch="hive/weekly-$(date -u +%Y%m%d)-${{ github.run_id }}"' \
        in text


def test_weekly_workflow_fails_visibly_while_a_proposal_pr_awaits_review():
    """An open hive/weekly- proposal PR means a human has not reviewed the
    last proposal yet: the run FAILS before selecting or pushing, naming the
    blocking PR on the step summary, so a stalled season is red on the
    schedule -- never a silently green skip. The listing is capped at 100
    (not the default 30) so an older proposal cannot hide behind newer
    unrelated PRs."""
    text = WEEKLY_WORKFLOW.read_text()
    assert "gh pr list --state open --limit 100" in text
    assert 'startswith("hive/weekly-")' in text
    assert "$GITHUB_STEP_SUMMARY" in text
    assert "exit 1" in text
    # The gate fails the run outright, so no later step is conditional on
    # it; and every proposal branch carries the unique run ID, so two runs
    # can never race the same ref.
    assert "steps.gate.outputs" not in text
    assert "hive/weekly-$(date -u +%Y%m%d)-${{ github.run_id }}" in text


def test_avatars_workflow_refreshes_the_season_manifest_logins():
    text = AVATARS_WORKFLOW.read_text()
    assert "stories/standalone/season-of-the-blueberries.json" in text


def test_avatars_tool_includes_the_season_logins():
    from tools import avatars
    logins = avatars.season_avatar_logins()
    assert {"angiejones", "Swil78", "CortNick"} <= set(logins)

# --- the Expansion Pack authoring pass --------------------------------------
#
# The owner-authored cue files under
# stories/standalone/authoring/season-of-the-blueberries/ (commit 32bd741)
# were previously parsed by nothing: the roughs omitted every chat card they
# author, most visibly Cortney's. These tests pin the parser grammar, the
# supported-placement mapping, and the non-overlapping chat schedule, all
# offline -- no ffmpeg, no media.

from tools import hive_authoring

AUTHORING = REPO_ROOT / "stories" / "standalone" / "authoring" / \
    "season-of-the-blueberries"

# The lore lanes the renderer knows how to seat (hive_series.LORE_POSITIONS).
LORE_LANES = ("bottom-right", "top-third")


def test_without_the_authoring_pass_the_cortney_chats_are_absent(
        manifest, tmp_path, monkeypatch):
    """The original defect: with the authoring docs not wired in, the
    episode 2 plan carries no chat cards at all -- the Cortney cues the
    owner wrote simply vanish from the rough, and nothing records them."""
    monkeypatch.setattr(hive_series, "AUTHORING_DIR", tmp_path)  # empty
    plan = hive_series.episode_plan(manifest, 2)
    assert plan["chats"] == []
    assert plan["overlays"] == []
    assert plan["unresolved"] == []


def test_authoring_parser_reads_the_committed_grammar():
    entries = hive_authoring.parse_authoring(
        (AUTHORING / "02-on-mars.md").read_text(encoding="utf-8"),
        "02-on-mars.md")
    assert [e["slug"] for e in entries] == [
        "scale-without-cncf", "seventh-loop", "cortney-losing-money",
        "save-the-day", "open-source-sigh", "flex-our-skills",
    ], "document order is preserved"
    cue = entries[2]
    assert cue["source_at"] == 152.0  # 02:32.00 absolute source seconds
    assert cue["placement"] == "chat-cortney"  # backticks stripped
    assert cue["copy"] == "Why do we keep losing SO much money"
    assert cue["next_line"] == "My face hurts"
    assert cue["direction"].startswith("Owner-authored two-line Cortney cue.")
    lone = entries[4]
    assert lone["next_line"] is None
    assert lone["source_at"] == 208.0  # 03:28.00


def test_authoring_parser_preserves_copy_verbatim():
    """Backticks, underscore emphasis, apostrophes and ellipses all survive
    -- the parser never normalises owner copy."""
    worm = hive_authoring.parse_authoring(
        (AUTHORING / "08-worm.md").read_text(encoding="utf-8"), "08")
    clone = next(e for e in worm if e["slug"] == "worm-cortney-reference-architectures")
    assert clone["copy"] == "I just read Reference Architectures."
    defeated = hive_authoring.parse_authoring(
        (AUTHORING / "09-defeated.md").read_text(encoding="utf-8"), "09")
    ra = next(e for e in defeated if e["slug"] == "defeated-capture-ra")
    assert ra["copy"] == "Capture _this_ moment as an RA"
    mara = hive_authoring.parse_authoring(
        (AUTHORING / "11-with-mara.md").read_text(encoding="utf-8"), "11")
    green = next(e for e in mara if e["slug"] == "mara-save-green")
    assert green["copy"] == "Ok wow ... go save me the green then."


def test_authoring_parser_never_makes_cards_from_prose():
    text = """# Title

Owner-authored copy. Times are absolute source time. A paragraph of prose
with a colon: and a `mention` is not a cue.

## 01:05.00 — `a-real-cue`

- Placement: `top-third`
- Copy: The only card here
- Direction: A note with a - dash and a fake `- Placement:` mention.

- Stray bullet outside any grammar field is owner commentary, not a field.
"""
    entries = hive_authoring.parse_authoring(text, "prose.md")
    assert len(entries) == 1
    assert entries[0]["copy"] == "The only card here"
    assert entries[0]["source_at"] == 65.0


def test_authoring_parser_fails_intelligibly_on_malformed_entries():
    """A recognized cue that breaks the grammar is a loud error naming the
    file and line -- never a silently skipped card."""
    with pytest.raises(hive_authoring.AuthoringError, match=r"bad\.md:1"):
        # timecode-led heading that misses the backticked slug
        hive_authoring.parse_authoring("## 01:28 model plate\n", "bad.md")
    with pytest.raises(hive_authoring.AuthoringError,
                       match=r"bad\.md:1.*no `- Copy:`"):
        hive_authoring.parse_authoring(
            "## 01:05.00 — `x`\n\n- Placement: `top-third`\n", "bad.md")
    with pytest.raises(hive_authoring.AuthoringError,
                       match=r"bad\.md:1.*no `- Placement:`"):
        hive_authoring.parse_authoring(
            "## 01:05.00 — `x`\n\n- Copy: words\n", "bad.md")
    with pytest.raises(hive_authoring.AuthoringError, match="timecode"):
        hive_authoring.parse_authoring(
            "## 01:75.00 — `x`\n\n- Placement: `top-third`\n- Copy: w\n",
            "bad.md")


def test_episode2_plan_carries_the_exact_cortney_chat_sequence(manifest):
    """The defect's fix: episode 2 seats every Cortney cue, verbatim, in the
    owner's order, first pill pinned at the authored anchor and the
    Next line sequenced after it (anchor + MIN_HOLD + TAIL_OUT)."""
    plan = hive_series.episode_plan(manifest, 2)
    cortney = [(c["id"], c["text"], c["at"]) for c in plan["chats"]]
    assert cortney == [
        ("cortney-losing-money",
         "Why do we keep losing SO much money", 27.0),
        ("cortney-losing-money-next",
         "My face hurts", 27.0 + hive_series.plate.MIN_HOLD
         + hive_series.plate.TAIL_OUT),
        ("open-source-sigh",
         "sigh, it's Open Source of course they have it.", 83.0),
        ("flex-our-skills",
         "Let's go flex our skills", 87.0),
    ]
    for spec in plan["chats"]:
        assert spec["kind"] == "chat"
        assert spec["speaker"] == "Cortney"
        assert spec["avatar"] == "renders/avatars/CortNick.png"
        assert spec["source_at"] == spec["at"] + 125.0 or \
            spec["id"] == "cortney-losing-money-next", \
            "the authored absolute anchor is recorded, never mutated"
        assert spec["dur"] >= hive_series.plate.MIN_HOLD


def test_episode2_lore_cards_are_verbatim_and_unsupported_is_recorded(
        manifest):
    plan = hive_series.episode_plan(manifest, 2)
    lore = {o["id"]: o for o in plan["overlays"]}
    assert lore["scale-without-cncf"]["lines"] == \
        ["Trying to scale without the CNCF"]
    assert lore["scale-without-cncf"]["position"] == "top-third"
    assert lore["scale-without-cncf"]["at"] == 9.0  # 134.0 - 125.0
    assert lore["seventh-loop"]["lines"] == \
        ["When You Realize Your Org is on it's 7th Loop"]
    # `top-right` is not a supported lane: recorded, never drawn.
    assert [u["id"] for u in plan["unresolved"]] == ["save-the-day"]
    assert "top-right" in plan["unresolved"][0]["reason"]


def test_episode9_chat_records_and_the_schedule_never_overlaps(manifest):
    plan = hive_series.episode_plan(manifest, 9)
    chats = {c["id"]: c for c in plan["chats"]}
    cortney = {cid: c["text"] for cid, c in chats.items()
               if c["speaker"] == "Cortney"}
    assert cortney == {
        "defeated-cha-ching": "Cha-ching!",
        # defeated-skip-part cannot clear the 13:37 protected gap and is
        # recorded unresolved instead -- see the protected-gap tests.
        "defeated-math-easy": "Math is easy!",
        "defeated-money-goods":
            "Money can be exchanged for goods and services.",
        "defeated-77-phippy":
            "Or ignore it, I have 77 Golden Phippy Awards",
        "defeated-barcelona": "Is that Barcelona?",
        "defeated-going-beach": "I am going to the beach",
    }
    # The first pill at each distinct anchor sits exactly at the authored
    # mark (chapter-relative): 12:46, 13:12, 13:26, 14:54, 15:07, 16:00.
    assert chats["defeated-components-fail"]["at"] == 766.0 - 744.0
    assert chats["defeated-angie-agent"]["at"] == 792.0 - 744.0
    assert chats["defeated-ahmed-sun"]["at"] == 806.0 - 744.0
    assert chats["defeated-math-easy"]["at"] == 894.0 - 744.0
    assert chats["defeated-money-goods"]["at"] == 907.0 - 744.0
    assert chats["defeated-77-phippy"]["at"] == 960.0 - 744.0
    # A same-anchor conversation cascades with the project's minimum
    # readable hold and tail gap: capture-ra pinned at 13:20, cha-ching
    # right after it.
    assert chats["defeated-capture-ra"]["at"] == 800.0 - 744.0
    assert chats["defeated-cha-ching"]["at"] == pytest.approx(
        800.0 - 744.0 + hive_series.plate.MIN_HOLD
        + hive_series.plate.TAIL_OUT)
    # No two chat windows overlap, every hold is readable, every window
    # stays inside the chapter.
    window = 1005.0 - 744.0
    ordered = sorted(chats.values(), key=lambda c: (c["at"], c["id"]))
    for prev, nxt in zip(ordered, ordered[1:]):
        assert nxt["at"] >= prev["at"] + prev["dur"] - 1e-6, \
            (prev["id"], nxt["id"])
    for spec in ordered:
        assert spec["dur"] >= hive_series.plate.MIN_HOLD
        assert 0 <= spec["at"] and spec["at"] + spec["dur"] <= window + 1e-6


def test_same_anchor_lines_follow_the_owner_sequence_markers(manifest):
    """Direction markers -- never slug or document accident -- order a
    multi-line beat: absolute pins (`sequence line N`), speaker-scoped
    numbers, `follows the X cue`, `sequence after X`, and the Final line.
    """
    # The 05:17 relic beat is authored out of order in the file; the
    # explicit line numbers 1-5 define the sequence.
    plan4 = hive_series.episode_plan(manifest, 4)
    beat = [c["id"] for c in plan4["chats"] if c["source_at"] == 317.0]
    assert beat == [
        "relic-savings-everywhere",   # sequence line 1
        "relic-know-how-look",        # sequence line 2
        "relic-relearn",              # sequence line 3
        "relic-more-expensive",       # sequence line 4
        "relic-each-time",            # Sequence line 5
    ]

    plan9 = hive_series.episode_plan(manifest, 9)
    at_894 = [c["id"] for c in plan9["chats"] if c["source_at"] == 894.0]
    # "sequence after Cortney": library-burn follows math-easy although the
    # file lists it first.
    assert at_894 == ["defeated-math-easy", "defeated-library-burn"]
    finale = [c["id"] for c in plan9["chats"] if c["source_at"] == 966.0]
    # "finale sequence line 1" pins the first slot; "Cortney finale line 2"
    # orders barcelona within Cortney's lines; the unmarked angellk cue
    # precedes the quote that "follows the angellk cue"; the "Final
    # owner-authored line" closes.
    assert finale[0] == "defeated-going-beach"
    assert finale.index("defeated-going-beach") < \
        finale.index("defeated-barcelona")
    assert finale.index("defeated-angellk-jorge") < \
        finale.index("defeated-angellk-hate-job")
    assert finale[-1] == "defeated-rochaporto-lazy"

    plan8 = hive_series.episode_plan(manifest, 8)
    # "Taylor sequence line 1/2": longterm precedes email-meantime although
    # the file lists them the other way around.
    at_728 = [c["id"] for c in plan8["chats"] if c["source_at"] == 728.0]
    assert at_728 == ["worm-taylor-longterm", "worm-taylor-email-meantime"]
    # "sequence after Cortney" swaps the file order at 11:46 as well.
    at_706 = [c["id"] for c in plan8["chats"] if c["source_at"] == 706.0]
    assert at_706 == ["worm-expensive-crowd", "worm-clap-worth-it"]


def test_unmarked_lines_keep_document_order(manifest):
    """The 13:26 block carries no sequence markers, so it renders exactly
    as written -- except the last line, which the 13:37 protected gap
    excludes (see the protected-gap tests)."""
    plan = hive_series.episode_plan(manifest, 9)
    at_806 = [c["id"] for c in plan["chats"] if c["source_at"] == 806.0]
    assert at_806 == [
        "defeated-ahmed-sun", "defeated-angie-expensive",
        "defeated-cvs-beach", "defeated-ncode-madrid",
    ]


def test_unsupported_cues_form_no_phantom_boundary(manifest):
    """The 13:33 cue (`top-third-as-cortney-chat`) is unsupported and never
    renders, so it constrains nothing: cvs-beach and ncode-madrid seat
    PAST its anchor (811.2s and 813.7s > 813s), proving no phantom
    boundary. Only the genuinely protective 13:37 `protected-gap` binds
    (see the next test)."""
    plan = hive_series.episode_plan(manifest, 9)
    chats = {c["id"]: c for c in plan["chats"]}
    assert "defeated-give-back-reveal" not in chats
    for slug in ("defeated-cvs-beach", "defeated-ncode-madrid"):
        assert slug in chats, f"{slug} dropped by a phantom boundary"
    assert chats["defeated-cvs-beach"]["source_at"] == 806.0
    assert chats["defeated-ncode-madrid"]["at"] > 813.0 - 744.0, \
        "seats past the unsupported 13:33 anchor: it constrained nothing"
    # The owner-speaker directive held: the explicit label, no identity.
    assert chats["defeated-cvs-beach"]["speaker"] == "CVS Health"
    assert "avatar" not in chats["defeated-cvs-beach"]


def test_protected_gap_is_a_no_draw_barrier(manifest):
    """The 13:37 `protected-gap` is never drawn AND is a scheduling
    barrier: the protected window runs to the next authored cue (the 14:04
    reveal), no rendered chat or lore card covers any part of it, and the
    one line that could not clear it (defeated-skip-part) is recorded
    unresolved rather than drawn over the protected beat."""
    plan = hive_series.episode_plan(manifest, 9)
    gaps = plan["protected_gaps"]
    assert gaps == [(73.0, 100.0)]  # source 817.0 to 844.0, ch9-relative
    by_id = {u["id"]: u["reason"] for u in plan["unresolved"]}
    assert "protected-gap" in by_id["defeated-protected-reveal-gap"], \
        "the gap itself is a no-draw record"
    assert "protected gap" in by_id["defeated-skip-part"], \
        "skip-part could not clear 817.0: recorded, never drawn"
    assert "defeated-skip-part" not in {c["id"] for c in plan["chats"]}
    g0, g1 = gaps[0]
    for card in plan["chats"]:
        end = card["at"] + card["dur"]
        assert end <= g0 + 1e-6 or card["at"] >= g1 - 1e-6, \
            f"{card['id']} covers the protected gap"
    for overlay in plan["overlays"]:
        end = overlay["at"] + overlay["dur"]
        assert end <= g0 + 1e-6 or overlay["at"] >= g1 - 1e-6, \
            f"{overlay['id']} covers the protected gap"
    # The lines that do render before it clear the gap completely.
    ncode = next(c for c in plan["chats"] if c["id"] == "defeated-ncode-madrid")
    assert ncode["at"] + ncode["dur"] <= g0


def test_a_lore_card_covering_the_gap_is_recorded_not_drawn(
        manifest, tmp_path, monkeypatch):
    """The barrier binds lore lanes too: a top-third whose window
    intersects the protected window is unresolved; a later card seated
    after the gap renders."""
    authoring = tmp_path / "authoring"
    authoring.mkdir()
    (authoring / "02-on-mars.md").write_text(
        "# On Mars\n\n"
        "## 02:14.00 — `card-before`\n\n"
        "- Placement: `top-third`\n"
        "- Copy: Before the gap\n\n"
        "## 02:15.00 — `gap`\n\n"
        "- Placement: `protected-gap`\n"
        "- Copy: Leave the picture alone\n\n"
        "## 02:40.00 — `card-after`\n\n"
        "- Placement: `top-third`\n"
        "- Copy: After the gap\n",
        encoding="utf-8")
    monkeypatch.setattr(hive_series, "AUTHORING_DIR", authoring)
    plan = hive_series.episode_plan(manifest, 2)
    # The gap runs 02:15 -> 02:40 (the next authored cue), i.e. ch2-relative
    # 10.0-35.0; card-before's 6s window (9.0-15.0) covers its start.
    assert plan["protected_gaps"] == [(10.0, 35.0)]
    lore_ids = [o["id"] for o in plan["overlays"]]
    assert "card-after" in lore_ids
    assert "card-before" not in lore_ids
    by_id = {u["id"]: u["reason"] for u in plan["unresolved"]}
    assert "protected gap" in by_id["card-before"]


def test_a_chat_that_cannot_fit_is_unresolved_never_overlapped(manifest):
    """A real packing failure: the 12:16 pair must clear the next RENDERED
    chat anchor (12:18, worm-marketing-help) -- 2.2s + 0.25s tail does not
    fit in 2.0s, so both lines are recorded, never squeezed or dropped.
    And the last line of a chapter must clear the chapter end itself."""
    plan8 = hive_series.episode_plan(manifest, 8)
    by_id = {u["id"]: u["reason"] for u in plan8["unresolved"]}
    assert "does not fit before the next owner anchor" in \
        by_id["worm-save-so-much"]
    assert "does not fit before the next owner anchor" in \
        by_id["worm-bobonomics"]
    plan3 = hive_series.episode_plan(manifest, 3)
    by_id3 = {u["id"]: u["reason"] for u in plan3["unresolved"]}
    assert "does not fit before the chapter end" in \
        by_id3["cortney-git-clone-next"]


def test_fixed_cast_chat_speakers_use_the_verified_plate_name(manifest):
    """Known fixed-cast speakers carry the manifest's verified plate.name,
    never the raw login; speakers with no fixed-cast match keep the owner's
    supplied label."""
    plan9 = hive_series.episode_plan(manifest, 9)
    speakers = {c["id"]: c["speaker"] for c in plan9["chats"]}
    assert speakers["defeated-angie-agent"] == "Angie Jones"
    assert speakers["defeated-cha-ching"] == "Cortney"
    # Ledger-proven but not fixed cast: the raw owner token stands.
    assert speakers["defeated-components-fail"] == "castrojo"
    assert speakers["defeated-ahmed-sun"] == "ahmedbehbars"
    plan8 = hive_series.episode_plan(manifest, 8)
    swil = {c["id"]: c["speaker"] for c in plan8["chats"]}
    assert swil["worm-marketing-help"] == "Shellea Williams"


def test_lore_lanes_never_overlap_and_clamp_deterministically(manifest):
    """A lore card's hold ends when the next card in the SAME lane begins;
    chapter 3's dense top-thirds clamp instead of stacking."""
    plan3 = hive_series.episode_plan(manifest, 3)
    top_thirds = [o for o in plan3["overlays"] if o["position"] == "top-third"]
    review = next(o for o in top_thirds if o["id"] == "business-value-review")
    assert review["at"] == 25.0 and review["dur"] == 3.0  # next at 28.0
    for chapter in manifest["chapters"]:
        plan = hive_series.episode_plan(manifest, chapter["number"])
        for lane in LORE_LANES:
            cards = sorted((o for o in plan["overlays"]
                            if o["position"] == lane),
                           key=lambda o: o["at"])
            for prev, nxt in zip(cards, cards[1:]):
                assert prev["at"] + prev["dur"] <= nxt["at"] + 1e-6, \
                    (chapter["number"], prev["id"], nxt["id"])
                assert prev["dur"] >= hive_series.plate.MIN_HOLD


def test_unsupported_placements_are_recorded_with_precise_reasons(manifest):
    plan = hive_series.episode_plan(manifest, 9)
    by_id = {u["id"]: u["reason"] for u in plan["unresolved"]}
    assert "episode-start" in by_id["defeated-episode-start"]
    assert "red-boss-overlay" in by_id["defeated-tech-debt-boss"]
    assert "protected-gap" in by_id["defeated-protected-reveal-gap"]
    assert "chat-sequence-start" in by_id["defeated-finale-chat-start"]
    assert "full-screen transmission" in by_id["defeated-finale-chat-start"]
    assert "top-third-as-cortney-chat" in by_id["defeated-give-back-reveal"]
    assert "character-nameplate-immaru" in by_id["defeated-immaru-ship"]
    # Nothing unsupported was rendered: no chat spec carries those ids.
    rendered_ids = {c["id"] for c in plan["chats"]} | \
        {o["id"] for o in plan["overlays"]}
    assert not (set(by_id) & rendered_ids)


def test_role_bond_chats_are_unresolved_not_rendered(manifest):
    plan = hive_series.episode_plan(manifest, 8)
    by_id = {u["id"]: u["reason"] for u in plan["unresolved"]}
    assert "role bond" in by_id["worm-count-high"]
    assert "chat-left-castrojo-as-saint14" in by_id["worm-count-high"]
    assert all(c["speaker"] != "left-castrojo-as-saint14"
               for c in plan["chats"])


def test_owner_speaker_label_comes_only_from_the_explicit_directive():
    chapter = {"number": 99, "slug": "x", "start": 0.0, "end": 60.0}
    entries = [{
        "slug": "c", "source_at": 10.0, "placement": "chat-owner-speaker",
        "copy": "Hey, we're on the beach!", "next_line": None,
        "direction": "Owner-authored speaker label is exactly `CVS Health`; "
                     "do not infer a GitHub identity.", "line": 1,
    }]
    chats, _lore, unresolved, _gaps = hive_authoring.plan_authoring(
        entries, {"fixed_cast": [], "contributor_ledger": {}}, chapter)
    assert unresolved == []
    assert chats[0]["speaker"] == "CVS Health"
    assert "avatar" not in chats[0], "no GitHub identity, no avatar"
    entries[0]["direction"] = "No label directive here."
    _c, _l, unresolved, _g = hive_authoring.plan_authoring(
        entries, {"fixed_cast": [], "contributor_ledger": {}}, chapter)
    assert unresolved and "speaker is never invented" in \
        unresolved[0]["reason"]


def test_avatar_is_attached_only_where_identity_data_proves_it(manifest):
    plan = hive_series.episode_plan(manifest, 9)
    by_id = {c["id"]: c for c in plan["chats"]}
    assert by_id["defeated-components-fail"]["avatar"] == \
        "renders/avatars/castrojo.png"  # contributor-ledger candidate
    assert by_id["defeated-angie-agent"]["avatar"] == \
        "renders/avatars/angiejones.png"  # fixed cast
    assert "avatar" not in by_id["defeated-ahmed-sun"]
    assert "avatar" not in by_id["defeated-rochaporto-lazy"]


def test_authoring_lore_cards_dedupe_against_the_manifest(manifest):
    """The two cues the manifest already carries verbatim (same position,
    same absolute mark, same lines) are rendered once by the manifest's
    overlay record, not double-drawn by the authoring pass."""
    plan1 = hive_series.episode_plan(manifest, 1)
    assert [o["id"] for o in plan1["overlays"]] == ["savathuns-ship"]
    plan3 = hive_series.episode_plan(manifest, 3)
    reviews = [o for o in plan3["overlays"] if o["id"] == "business-value-review"]
    assert len(reviews) == 1
    assert reviews[0]["at"] == 243.0 - 218.0


def test_overlay_descriptors_order_plates_then_chats_then_lore(manifest):
    plan = hive_series.episode_plan(manifest, 2)
    kinds = [d["overlay_kind"]
             for d in hive_series._plan_overlay_descriptors(plan)]
    assert kinds == ["plate"] + ["chat"] * 4 + ["lore"] * 2
    graph = hive_series.episode_filtergraph(plan)
    # Three stills (cta, title, closing), so overlay inputs start at 4:
    # the fixed player plate, then the four chat pills, then the lore.
    assert "enable='between(t,24,28)'" in graph      # player-ch2 plate
    assert "enable='between(t,27,29.2)'" in graph    # cortney-losing-money
    assert "enable='between(t,29.45,31.65)'" in graph  # its Next line
    assert "enable='between(t,83,85.706)'" in graph  # open-source-sigh
    assert "enable='between(t,9,15)'" in graph       # scale-without-cncf


def test_chat_specs_render_through_plate_py_unmodified(manifest):
    """The authoring chat pills are plate.py's `kind: chat` renderer's own
    input shape; the crest stands in offline because avatar bytes are never
    committed."""
    from tools import plate

    plan = hive_series.episode_plan(manifest, 2)
    for spec in plan["chats"]:
        img = plate.render_plate({k: v for k, v in spec.items()
                                  if k != "avatar"})
        assert img.mode == "RGBA" and img.width > 100


def test_authoring_copy_change_moves_the_episode_input_digest(
        manifest, tmp_path, monkeypatch):
    """Freshness covers the authoring pass: an edited Copy line is a new
    episode even though every duration stays the same."""
    staged = [_png(tmp_path / "a.png", (1, 2, 3, 255))]
    plan = hive_series.episode_plan(manifest, 2)
    base = hive_series.episode_input_digest(plan, staged)

    doctored_dir = tmp_path / "authoring"
    doctored_dir.mkdir()
    text = (AUTHORING / "02-on-mars.md").read_text(encoding="utf-8")
    (doctored_dir / "02-on-mars.md").write_text(text.replace(
        "Why do we keep losing SO much money",
        "Why do we keep losing SO much money?"))
    monkeypatch.setattr(hive_series, "AUTHORING_DIR", doctored_dir)
    changed = hive_series.episode_input_digest(
        hive_series.episode_plan(manifest, 2), staged)
    assert changed != base

    # Same content again -> same digest (the skip case still holds).
    assert hive_series.episode_input_digest(
        hive_series.episode_plan(manifest, 2), staged) == changed


def test_build_episode_stages_the_authoring_chat_pills(
        manifest, tmp_path, monkeypatch):
    """Episode 2 end to end offline: the fixed plate and the four Cortney
    pills render through plate.py, the lore cards here, and the encode
    stages every PNG in the same lockstep order the graph indexes."""
    manifest_path, _data = _stage_episode(manifest, tmp_path, monkeypatch)
    captured = {}

    def fake_run_encode(argv, **kwargs):
        captured["argv"] = [str(t) for t in argv]
        captured.update(kwargs)
        Path(kwargs["out"]).write_bytes(b"mp4")
        return "cluster"

    monkeypatch.setattr(hive_series.farm, "run_encode", fake_run_encode)
    work = tmp_path / "work"
    out = hive_series.build_episode(manifest_path, 2, work_dir=work)
    assert out.exists()

    argv = captured["argv"]
    graph = argv[argv.index("-filter_complex") + 1]
    # source + 3 stills + 7 overlays (1 plate, 4 chats, 2 lore).
    inputs = captured["inputs"]
    assert argv.count("-i") == len(inputs) == 11
    assert graph.count("overlay=0:0") == 7
    names = [Path(p).name for p in inputs]
    assert names.index("plate_player-ch2.png") < \
        names.index("plate_cortney-losing-money.png") < \
        names.index("s01e02-on-mars-overlay-scale-without-cncf.png")
    for path in inputs:
        assert Path(path).exists(), f"staged input missing: {path}"

    sidecar = json.loads(
        (work / "s01e02-on-mars-unresolved.json").read_text())
    by_id = {item["id"]: item["reason"] for item in sidecar}
    assert "save-the-day" in by_id and "top-right" in by_id["save-the-day"]
    # Avatar bytes are never committed, so offline the identity-proven
    # Cortney pills render the drawn crest AND record the gap -- one entry
    # per chat spec with a declared avatar.
    avatar_gaps = {item_id: reason for item_id, reason in by_id.items()
                   if "cached avatar" in reason}
    assert set(avatar_gaps) == {c["id"] for c in
                                hive_series.episode_plan(
                                    hive_series.load_manifest(manifest_path),
                                    2)["chats"]}
    assert all("CortNick" in reason for reason in avatar_gaps.values())

    # A content-identical rebuild is skipped on the digest.
    calls = []
    monkeypatch.setattr(hive_series.farm, "run_encode", _fake_encode(calls))
    hive_series.build_episode(manifest_path, 2, work_dir=work)
    assert calls == [], "an unchanged authoring pass must not re-encode"

# --- rough-first delivery safety ----------------------------------------------
#
# Hive AGENTS.md: builds write `rough/s01eNN-<slug>.mp4` (and the season
# assembly `season-01-full-rough.mp4`) for local review; the top-level
# final MP4s, their `-thumbnail.jpg` pairs, and `season-01-full.mp4` are
# promotion-only. These tests pin that no build path creates or replaces a
# final, and that `promote` is the single explicit boundary.


def test_build_never_creates_or_replaces_a_delivered_final(
        manifest, tmp_path, monkeypatch):
    """The safety property: a released final sitting at the top-level path
    keeps its exact bytes through any build -- builds write rough/ only."""
    manifest_path, _data = _stage_episode(manifest, tmp_path, monkeypatch)
    final = tmp_path / "s01e01-the-enclave.mp4"
    final.write_bytes(b"released-episode")
    final_thumb = tmp_path / "s01e01-the-enclave-thumbnail.jpg"
    final_thumb.write_bytes(b"released-thumbnail")
    calls = []
    monkeypatch.setattr(hive_series.farm, "run_encode", _fake_encode(calls))

    hive_series.build_episode(manifest_path, 1, work_dir=tmp_path / "work")
    assert len(calls) == 1
    assert final.read_bytes() == b"released-episode"
    assert final_thumb.read_bytes() == b"released-thumbnail"
    assert (tmp_path / "rough" / "s01e01-the-enclave.mp4").exists()
    assert (tmp_path / "rough"
            / "s01e01-the-enclave-thumbnail.jpg").exists()


def test_promote_is_the_only_write_path_to_the_final(
        manifest, tmp_path, monkeypatch):
    """Promotion is explicit, no-media (a pure copy), and refuses without a
    reviewed rough pair; a later rebuild moves the rough and leaves the
    promoted final byte-identical."""
    manifest_path, data = _stage_episode(manifest, tmp_path, monkeypatch)
    calls = []

    def counted_encode(argv, **kwargs):
        calls.append(kwargs)
        Path(kwargs["out"]).write_bytes(f"encode-{len(calls)}".encode())
        return "cluster"

    monkeypatch.setattr(hive_series.farm, "run_encode", counted_encode)
    loaded = hive_series.load_manifest(manifest_path)

    with pytest.raises(FileNotFoundError, match="rough"):
        hive_series.promote_episode(loaded, 1)

    work = tmp_path / "work"
    hive_series.build_episode(manifest_path, 1, work_dir=work)
    final = hive_series.promote_episode(loaded, 1, log=lambda m: None)
    assert final == tmp_path / "s01e01-the-enclave.mp4"
    assert final.read_bytes() == b"encode-1"
    assert (tmp_path / "s01e01-the-enclave-thumbnail.jpg").read_bytes() == \
        (tmp_path / "rough"
         / "s01e01-the-enclave-thumbnail.jpg").read_bytes(), \
        "a released episode always carries its paired thumbnail"

    # New copy arrives; the rebuild rewrites the ROUGH, the final stands.
    data["overlays"][0]["lines"] = ["Revised after review."]
    manifest_path.write_text(json.dumps(data))
    hive_series.build_episode(manifest_path, 1, work_dir=work)
    assert len(calls) == 2, "changed copy rebuilds the rough"
    assert (tmp_path / "rough" / "s01e01-the-enclave.mp4").read_bytes() == \
        b"encode-2"
    assert final.read_bytes() == b"encode-1", \
        "a rebuild must never replace a promoted final"


def test_promote_cut_copies_only_an_approved_rough_cut(manifest, tmp_path):
    data = _delivery_manifest(manifest, tmp_path)
    loaded = hive_series.load_manifest_data(data)
    with pytest.raises(FileNotFoundError, match="rough cut"):
        hive_series.promote_cut(loaded)
    rough_cut = tmp_path / "season-01-full-rough.mp4"
    rough_cut.write_bytes(b"reviewed-cut")
    final = hive_series.promote_cut(loaded, log=lambda m: None)
    assert final == tmp_path / "season-01-full.mp4"
    assert final.read_bytes() == b"reviewed-cut"


def test_promote_command_goes_through_the_explicit_boundary(
        manifest, tmp_path, monkeypatch):
    data = _delivery_manifest(manifest, tmp_path)
    monkeypatch.setattr(hive_series, "load_manifest", lambda *a, **k: data)
    rough = tmp_path / "rough" / "s01e01-the-enclave.mp4"
    rough.parent.mkdir(parents=True)
    rough.write_bytes(b"mp4")
    (tmp_path / "rough" / "s01e01-the-enclave-thumbnail.jpg").write_bytes(
        b"jpg")
    assert hive_series.main(["promote", "1"]) == 0
    assert (tmp_path / "s01e01-the-enclave.mp4").read_bytes() == b"mp4"
    assert (tmp_path
            / "s01e01-the-enclave-thumbnail.jpg").read_bytes() == b"jpg"


def test_verify_targets_roughs_unless_final_is_explicit(manifest,
                                                        monkeypatch):
    stages = []
    monkeypatch.setattr(
        hive_series, "verify_episode",
        lambda m, n, **k: stages.append(k["stage"]) or [])
    monkeypatch.setattr(hive_series, "load_manifest", lambda *a, **k: manifest)
    assert hive_series.main(["verify", "1"]) == 0
    assert stages == ["rough"], "review verifies what the build produced"
    assert hive_series.main(["verify", "1", "--final"]) == 0
    assert stages == ["rough", "final"]

# --- farm-side preflight and validation (NO local ffmpeg/ffprobe) ------------
#
# The Hive workspace contract: the host never runs a media tool -- not for
# the encode, not for preflight probes, not for picture detection, not for
# validation. These tests pin the seams with fakes; nothing here reaches
# the cluster or a media binary.


def test_source_preflight_probes_on_the_farm(tmp_path, monkeypatch):
    """The audio rate comes from the farm's ffprobe JSON; the picture rect
    from the farm's cropdetect output, judged by the same parsing the
    legacy local detection uses. The host only parses text."""
    src = tmp_path / "source.mp4"
    src.write_bytes(b"m")
    calls = []

    def fake_analysis(argvs, *, inputs, **kwargs):
        calls.append((argvs, inputs))
        if argvs[0][0] == "ffprobe":
            return json.dumps({
                "format": {"duration": "1248.0"},
                "streams": [{"codec_type": "video", "codec_name": "h264"},
                            {"codec_type": "audio", "sample_rate": "44100"}]})
        assert argvs[0][0] == "ffmpeg"
        return "crop=1920:800:0:140\n" * len(argvs)

    monkeypatch.setattr(hive_series.farm, "run_analysis_on_cluster",
                        fake_analysis)
    rate, picture, status = hive_series._source_preflight_farm(src)
    assert rate == 44100
    assert picture == (0, 140, 1920, 800)
    assert status == "letterboxed"
    assert len(calls) == 2, "one stream probe, one cropdetect pass"
    assert all(inputs == [src.resolve()] for _a, inputs in calls)
    # The cropdetect windows are computed from the farm-probed duration,
    # exactly like the legacy local detection's probe_windows.
    detect = calls[1][0]
    assert any("cropdetect" in token for argv in detect for token in argv)
    assert all(str(src.resolve()) in argv for argv in detect)


def test_source_preflight_reports_undecodable_and_missing_audio(
        tmp_path, monkeypatch):
    src = tmp_path / "source.mp4"
    src.write_bytes(b"m")

    def fake_analysis(argvs, *, inputs, **kwargs):
        if argvs[0][0] == "ffprobe":
            return json.dumps({"format": {"duration": "10.0"},
                               "streams": [{"codec_type": "video"}]})
        return "frames decoded but no crop= lines\n"

    monkeypatch.setattr(hive_series.farm, "run_analysis_on_cluster",
                        fake_analysis)
    rate, picture, status = hive_series._source_preflight_farm(src)
    assert rate is None, "no audio stream: the graph pins the rate itself"
    assert picture is None and status == "undecodable"


def test_verify_probes_the_rough_on_the_farm(manifest, tmp_path,
                                             monkeypatch):
    """Validation never touches a host ffprobe: the rough is staged and
    probed in a pod, and the returned JSON is what gets judged."""
    data = _delivery_manifest(manifest, tmp_path)
    loaded = hive_series.load_manifest_data(data)
    rough = tmp_path / "rough" / "s01e01-the-enclave.mp4"
    rough.parent.mkdir(parents=True)
    rough.write_bytes(b"mp4")
    probed = []

    def good_doc(path, **kwargs):
        probed.append(Path(path).name)
        return {"format": {"duration": "162.0"},
                "streams": [dict(_conformant_video(), codec_type="video"),
                            {"codec_type": "audio", "codec_name": "aac",
                             "sample_rate": "48000", "channels": 2,
                             "channel_layout": "stereo"}]}

    monkeypatch.setattr(hive_series, "_probe_streams_farm", good_doc)
    assert hive_series.verify_episode(loaded, 1) == []
    assert probed == ["s01e01-the-enclave.mp4"]

    def bad_audio(path, **kwargs):
        doc = good_doc(path)
        doc["streams"][1] = {"codec_type": "audio", "codec_name": "mp3",
                             "sample_rate": "44100", "channels": 2,
                             "channel_layout": "stereo"}
        return doc

    monkeypatch.setattr(hive_series, "_probe_streams_farm", bad_audio)
    problems = hive_series.verify_episode(loaded, 1)
    assert any("mp3" in p for p in problems)
    assert any("44100" in p for p in problems)


def test_verify_fails_visibly_when_the_farm_cannot_probe(
        manifest, tmp_path, monkeypatch):
    """An unreachable farm is a visible verification failure, never a local
    ffprobe fallback."""
    data = _delivery_manifest(manifest, tmp_path)
    loaded = hive_series.load_manifest_data(data)
    rough = tmp_path / "rough" / "s01e01-the-enclave.mp4"
    rough.parent.mkdir(parents=True)
    rough.write_bytes(b"mp4")

    def down(path, **kwargs):
        raise hive_series.farm.FarmError("the cluster is not reachable")

    monkeypatch.setattr(hive_series, "_probe_streams_farm", down)
    problems = hive_series.verify_episode(loaded, 1)
    assert len(problems) == 1
    assert "remote validation failed" in problems[0]
    assert "never on the host" in problems[0]


def test_concat_episodes_runs_the_join_on_the_farm(manifest, tmp_path,
                                                   monkeypatch):
    """Even the stream-copy join is a media command under the Hive
    contract: it ships to the farm with the concat list as a pod-side text
    file, farm-only and farm-verified, writing the ROUGH cut."""
    data = _delivery_manifest(manifest, tmp_path)
    loaded = hive_series.load_manifest_data(data)
    captured = {}

    def fake_run_encode(argv, **kwargs):
        captured["argv"] = [str(t) for t in argv]
        captured.update(kwargs)
        return "cluster"

    monkeypatch.setattr(hive_series.farm, "run_encode", fake_run_encode)
    out = hive_series.concat_episodes(loaded, work_dir=tmp_path / "work")
    assert out == tmp_path / "season-01-full-rough.mp4"
    assert captured["fallback"] is False
    assert captured["local_probe"] is False
    inputs = [str(p) for p in captured["inputs"]]
    assert len(inputs) == 12
    assert all("/rough/" in p for p in inputs), \
        "the join reads the rough episodes, never the finals"
    [(list_name, content)] = list(captured["text_files"].items())
    assert "rough/s01e01-the-enclave.mp4" in content
    assert "rough/s01e12-raid.mp4" in content
    assert list_name in captured["argv"], \
        "the argv reads the concat list (rewritten pod-side by the farm)"
    assert not (tmp_path / "season-01-full.mp4").exists()


def test_build_fails_before_the_render_when_the_farm_is_unreachable(
        manifest, tmp_path, monkeypatch):
    """End to end through build_episode: with preflight faked and the
    encode's farm call down, the build raises and no rough is written."""
    manifest_path, _data = _stage_episode(manifest, tmp_path, monkeypatch)

    def farm_down(argv, **kwargs):
        raise hive_series.farm.FarmError(
            "the cluster is not reachable (kubectl not on PATH); this "
            "build does not permit a local encode")

    monkeypatch.setattr(hive_series.farm, "run_encode", farm_down)
    with pytest.raises(hive_series.farm.FarmError, match="not reachable"):
        hive_series.build_episode(manifest_path, 1, work_dir=tmp_path / "work")
    assert not (tmp_path / "rough" / "s01e01-the-enclave.mp4").exists()


def test_run_analysis_on_cluster_stages_inputs_and_captures_output(
        tmp_path, monkeypatch):
    """The analysis seam: pod-side argv carries the STAGED input path, the
    captured text comes back, and an input no command reads is rejected
    before any pod exists."""
    farm = hive_series.farm
    src = tmp_path / "src.mp4"
    src.write_bytes(b"m")
    captured = {}

    def fake_execute(**kwargs):
        captured.update(kwargs)
        Path(kwargs["out"]).write_text("analysis-output")
        return {"output": "out/analysis.txt", "duration": None}

    monkeypatch.setattr(farm, "_execute_on_cluster", fake_execute)
    text = farm.run_analysis_on_cluster(
        [["ffprobe", "-v", "error", str(src)]], inputs=[src])
    assert text == "analysis-output"
    script = captured["script"]
    assert "ffprobe" in script
    assert "/work/in/00-src.mp4" in script, "the pod reads the staged path"
    assert str(src) not in script, "the pod never sees the host path"
    assert captured["out_rel"] == "out/analysis.txt"

    with pytest.raises(farm.FarmError, match="never read"):
        farm.run_analysis_on_cluster([["ffprobe", "-v", "error"]],
                                     inputs=[src])

# --- regression: garbled farm output and the protected gap --------------------


def test_garbled_farm_probe_output_is_a_visible_problem_not_an_abort(
        manifest, tmp_path, monkeypatch):
    """`_probe_streams_farm` json-parses the farm's capture; garbage there
    used to escape as a raw JSONDecodeError past the FarmError guard. It is
    normalized to FarmError at the seam, so verification reports a visible
    problem entry instead of aborting the run."""
    data = _delivery_manifest(manifest, tmp_path)
    loaded = hive_series.load_manifest_data(data)
    rough = tmp_path / "rough" / "s01e01-the-enclave.mp4"
    rough.parent.mkdir(parents=True)
    rough.write_bytes(b"mp4")

    monkeypatch.setattr(hive_series.farm, "run_analysis_on_cluster",
                        lambda *a, **k: "{not json -- truncated capture")
    problems = hive_series.verify_episode(loaded, 1)
    assert len(problems) == 1
    assert "remote validation failed" in problems[0]
    assert "unreadable output" in problems[0]

    # And the preflight path raises a proper FarmError (a build fails
    # visibly before render), not a bare JSONDecodeError.
    with pytest.raises(hive_series.farm.FarmError, match="unreadable"):
        hive_series._source_preflight_farm(rough)
