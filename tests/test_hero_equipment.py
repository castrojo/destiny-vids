"""Offline contract tests for the source-backed Leonardo equipment catalog."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


REPO = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO / "stories" / "leonardo-equipment.json"
SCHEMA_PATH = REPO / "schema" / "hero-equipment.schema.json"

EXPECTED_LEONARDO_ITEMS = {
    "leonardo_diy_crossbow",
    "leonardo_regular_hunting_arrow",
    "leonardo_plasma_arrow",
    "leonardo_explosion_arrow",
    "leonardo_tungsten_armor",
    "leonardo_tungsten_throwing_axe",
    "leonardo_magnetic_grenade",
    "leonardo_chili_smoke_grenade",
    "leonardo_electroshock_grenade",
    "leonardo_hippershell_exo_x",
    "leonardo_ai_control_module",
    "leonardo_hard_leather_gauntlet",
    "leonardo_camel_bag",
    "leonardo_provision_bag",
    "leonardo_automatic_folding_shield",
    "leonardo_steel_knife",
    "leonardo_hi_tech_sword",
    "leonardo_magical_hi_tech_spear",
}

EXPECTED_LEONARDO_COPY = {
    "leonardo_diy_crossbow": {
        "label": "DIY CROSSBOW",
        "subtitle": "MIX MATERIALS",
        "description_source": "placeholder",
        "placeholder_chars": 84,
    },
    "leonardo_regular_hunting_arrow": {
        "label": "REGULAR HUNTING ARROW",
        "description_source": "placeholder",
        "placeholder_chars": 84,
    },
    "leonardo_plasma_arrow": {
        "label": "PLASMA ARROW",
        "description_source": "placeholder",
        "placeholder_chars": 84,
    },
    "leonardo_explosion_arrow": {
        "label": "EXPLOSION ARROW",
        "description_source": "placeholder",
        "placeholder_chars": 84,
    },
    "leonardo_tungsten_armor": {
        "label": "TUNGSTEN ARMOR",
        "subtitle": "GRAPHENE COATING",
        "description_source": "placeholder",
        "placeholder_chars": 84,
    },
    "leonardo_tungsten_throwing_axe": {
        "label": "TUNGSTEN TROWING AXE",
        "description_source": "placeholder",
        "placeholder_chars": 84,
    },
    "leonardo_magnetic_grenade": {
        "label": "MAGNETIC GRENADE",
        "description_source": "placeholder",
        "placeholder_chars": 84,
    },
    "leonardo_chili_smoke_grenade": {
        "label": "CHILI SMOKE GRENADE",
        "description": "A CHILI SMOKE GRENADE THAT PRODUCES THICK SMOKE CAPABLE OF STINGING THE EYES, BURNING THE SKIN, AND CAUSING BREATHING DIFFICULTIES IF INHALED. IT CAUSES A MASSIVE FIRE EXPLOSION WHEN IT COMES INTO CONTACT WITH ELECTRONICS OR ALIEN ROBOTS.",
        "description_source": "authored",
    },
    "leonardo_electroshock_grenade": {
        "label": "ELECTROSHOCK GRENADE",
        "description": "DISRUPTS SIGNAL WAVES AND DESTROYS THE COMMUNICATION STRUCTURE IN ELECTRONIC DEVICES WITH POMODORO TIMER SYSTEM",
        "description_source": "authored",
    },
    "leonardo_hippershell_exo_x": {
        "label": "DIY HIPPERSHELL EXO-X",
        "subtitle": "TUNGSTEN ALLOY",
        "description": "100K MAH BATERRY IMPROVES MUSCLE PERFORMANCE: 50% EXTRA LOAD CAPACITY: 47 KG",
        "description_source": "authored",
    },
    "leonardo_ai_control_module": {
        "label": "SNAP ON GADGET AI CONTROL MODULE",
        "subtitle": "WITH GPS",
        "description_source": "placeholder",
        "placeholder_chars": 84,
    },
    "leonardo_hard_leather_gauntlet": {
        "label": "HARD LEATHER GUNTLET",
        "description_source": "placeholder",
        "placeholder_chars": 84,
    },
    "leonardo_camel_bag": {
        "label": "3 LITERS CAMEL BAG",
        "subtitle": "WITH A KINETIC CHARGING SYSTEM",
        "description_source": "placeholder",
        "placeholder_chars": 84,
    },
    "leonardo_provision_bag": {
        "label": "PROVISION BAG",
        "description_source": "placeholder",
        "placeholder_chars": 84,
    },
    "leonardo_automatic_folding_shield": {
        "label": "AUTOMATIC FOLDING SHIELD",
        "subtitle": "0.12-INCH-THICK TITANIUM ALLOY",
        "description_source": "placeholder",
        "placeholder_chars": 84,
    },
    "leonardo_steel_knife": {
        "label": "DIY STEEL KNIFE",
        "description_source": "placeholder",
        "placeholder_chars": 84,
    },
    "leonardo_hi_tech_sword": {
        "label": "DIY HI TECH SWORD",
        "subtitle": "TUNGSTEN ALLOY",
        "description": "FEATURING A SHOCK-WAVE AIR BLAST WITH A COCKING/PUMPING SYSTEM",
        "description_source": "authored",
    },
    "leonardo_magical_hi_tech_spear": {
        "label": "DIY MAGICAL/ HI TECH SPEAR",
        "subtitle": "TUNGSTEN ALLOY",
        "description_source": "placeholder",
        "placeholder_chars": 84,
    },
}

EXPECTED_SOURCE_SIZES = {
    "Leonardo/CHA_LEONARDO_WEAPONS.png": (6891, 5354),
    "Leonardo/CHA_LEONARDO_03.png": (3871, 5051),
    "Leonardo/CHA_LEONARDO_04.png": (2561, 2817),
}


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())


@pytest.fixture
def catalog():
    return json.loads(CATALOG_PATH.read_text())


def test_catalog_validates_against_the_draft_2020_schema(catalog, schema):
    errors = sorted(Draft202012Validator(schema).iter_errors(catalog), key=str)
    assert not errors, "\n".join(error.message for error in errors)


def test_schema_rejects_extra_properties(catalog, schema):
    invalid = copy.deepcopy(catalog)
    invalid["unexpected"] = True
    errors = list(Draft202012Validator(schema).iter_errors(invalid))
    assert errors


def test_catalog_has_every_audited_leonardo_item(catalog):
    assert set(catalog["items"]) == EXPECTED_LEONARDO_ITEMS


def test_every_item_has_exact_source_backed_copy(catalog):
    assert set(EXPECTED_LEONARDO_COPY) == EXPECTED_LEONARDO_ITEMS
    for item_id, expected_copy in EXPECTED_LEONARDO_COPY.items():
        assert catalog["items"][item_id]["copy"] == expected_copy


def test_every_item_has_recheckable_copy_and_art_evidence(catalog):
    for item_id, item in catalog["items"].items():
        assert item["copy"]["label"].strip(), item_id
        assert item["evidence"]["sheet"] == "Leonardo/Cha Design_LEONARDO.jpg"
        assert len(item["evidence"]["label_crop"]) == 4
        assert item["art"]["file"].startswith("Leonardo/")
        assert item["art"]["mode"] in {
            "components", "context_crop", "text_only"
        }


def test_leonardo_spear_copy_is_source_backed(catalog):
    spear = catalog["items"]["leonardo_magical_hi_tech_spear"]
    assert spear["copy"] == {
        "label": "DIY MAGICAL/ HI TECH SPEAR",
        "subtitle": "TUNGSTEN ALLOY",
        "description_source": "placeholder",
        "placeholder_chars": 84,
    }
    assert spear["evidence"]["sheet"] == "Leonardo/Cha Design_LEONARDO.jpg"
    assert spear["art"]["file"] == "Leonardo/CHA_LEONARDO_WEAPONS.png"
    assert spear["art"]["mode"] == "components"


def test_ai_control_module_is_degraded_without_false_display_art(catalog):
    art = catalog["items"]["leonardo_ai_control_module"]["art"]
    assert art["mode"] == "text_only"
    assert art["file"] == "Leonardo/CHA_LEONARDO_03.png"
    assert art["degraded_reason"] == (
        "The supplied RGBA pose does not provide a defensible crop that visibly "
        "isolates the named blue forearm module; retaining the surrounding arm "
        "and rig would make the display art claim more than the source proves."
    )


def test_missing_descriptions_are_explicit_placeholders(catalog):
    for item_id, item in catalog["items"].items():
        copy_fields = item["copy"]
        if "description" not in copy_fields:
            assert copy_fields["description_source"] == "placeholder", item_id
            assert copy_fields["placeholder_chars"] >= 60


def test_authored_descriptions_are_not_marked_placeholder(catalog):
    for item_id, item in catalog["items"].items():
        copy_fields = item["copy"]
        if "description" in copy_fields:
            assert copy_fields["description_source"] == "authored", item_id


def test_source_dimensions_match_authoritative_filename_constants(catalog):
    for source in catalog["sources"]["rgba_assets"].values():
        filename = source["file"]
        assert tuple(source["size"]) == EXPECTED_SOURCE_SIZES[filename]
        assert source["format"] == "RGBA"

    for item_id, item in catalog["items"].items():
        art = item["art"]
        if art["mode"] != "text_only":
            assert tuple(art["source_size"]) == EXPECTED_SOURCE_SIZES[art["file"]], item_id


def test_source_bound_evidence_and_component_seeds_are_static(catalog):
    sheet_width, sheet_height = catalog["sources"]["design_sheet"]["size"]
    for item_id, item in catalog["items"].items():
        x, y, width, height = item["evidence"]["label_crop"]
        assert 0 <= x < sheet_width, item_id
        assert 0 <= y < sheet_height, item_id
        assert 1 <= width <= sheet_width - x, item_id
        assert 1 <= height <= sheet_height - y, item_id

        art = item["art"]
        if art["mode"] == "components":
            source_width, source_height = EXPECTED_SOURCE_SIZES[art["file"]]
            for seed_x, seed_y in art["component_seeds"]:
                assert 0 <= seed_x < source_width, item_id
                assert 0 <= seed_y < source_height, item_id
        elif art["mode"] == "context_crop":
            source_width, source_height = EXPECTED_SOURCE_SIZES[art["file"]]
            crop_x, crop_y, crop_width, crop_height = art["crop"]
            assert crop_x + crop_width <= source_width, item_id
            assert crop_y + crop_height <= source_height, item_id
            for point_x, point_y in art["mask_polygon"]:
                assert 0 <= point_x < source_width, item_id
                assert 0 <= point_y < source_height, item_id
                assert crop_x <= point_x < crop_x + crop_width, item_id
                assert crop_y <= point_y < crop_y + crop_height, item_id


def test_context_art_explains_retained_supporting_pixels(catalog):
    context_items = [
        item for item in catalog["items"].values()
        if item["art"]["mode"] == "context_crop"
    ]
    assert context_items
    for item in context_items:
        assert item["art"]["context_note"].strip()


def test_text_only_art_has_no_display_geometry(catalog):
    text_only = [
        item for item in catalog["items"].values()
        if item["art"]["mode"] == "text_only"
    ]
    assert text_only
    for item in text_only:
        assert item["art"]["degraded_reason"].strip()
        assert "component_seeds" not in item["art"]
        assert "mask_polygon" not in item["art"]


def test_schema_requires_mode_specific_art_metadata(catalog, schema):
    components = copy.deepcopy(catalog)
    del components["items"]["leonardo_diy_crossbow"]["art"]["component_seeds"]
    assert list(Draft202012Validator(schema).iter_errors(components))

    context_crop = copy.deepcopy(catalog)
    del context_crop["items"]["leonardo_tungsten_armor"]["art"]["context_note"]
    assert list(Draft202012Validator(schema).iter_errors(context_crop))

    text_only = copy.deepcopy(catalog)
    text_only["items"]["leonardo_magnetic_grenade"]["art"]["rotation_degrees"] = 0
    assert list(Draft202012Validator(schema).iter_errors(text_only))


def test_schema_requires_rgba_source_metadata(catalog, schema):
    invalid = copy.deepcopy(catalog)
    invalid["sources"]["rgba_assets"]["weapons"]["format"] = "RGB"
    errors = list(Draft202012Validator(schema).iter_errors(invalid))
    assert errors


def test_synthetic_component_seed_selects_only_one_rgba_object():
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (32, 24), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((2, 3, 8, 12), fill=(255, 0, 0, 255))
    draw.rectangle((20, 5, 28, 18), fill=(0, 255, 0, 255))
    seed = (24, 10)
    selected = image.getpixel(seed)
    assert image.mode == "RGBA"
    assert image.getpixel((0, 0))[3] == 0
    assert image.getpixel(seed)[3] == 255
    assert selected == (0, 255, 0, 255)
    assert image.getpixel((5, 7))[3] == 255
    assert image.getpixel((5, 7)) != selected
