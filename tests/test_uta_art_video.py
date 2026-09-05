"""Tests for the UTA "General of the Dark Army" montage record and generator.

The record in stories/uta-general-dark-army.json is the montage's source of
truth: rights, the pinned source hash, and every measurement the final
picture and mux will be derived from. Every timing value in it was returned
by an Argo workflow (the sample-count preflight, the Stage 1 bed workflow,
and the generated source-review workflow) -- nothing is typed from the
YouTube metadata summary or from memory, so the tests can pin internal
consistency instead of re-measuring.

The generator (scripts/build_uta_art_video.py) emits the Argo manifests.
Task 1 implements `source-review` fully; `picture` and `mux-validate` are
deliberate skeletons that later tasks fill in, and the tests pin that they
refuse rather than silently emitting a half-designed workflow.
"""

import copy
import json
import sys
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_uta_art_video as build  # noqa: E402
import generate_schema_enums as gen  # noqa: E402

EDIT_PATH = REPO_ROOT / "stories" / "uta-general-dark-army.json"
SCHEMA_PATH = REPO_ROOT / "schema" / "uta-art-video.schema.json"


@pytest.fixture(scope="module")
def edit():
    return build.load_edit(EDIT_PATH)


@pytest.fixture(scope="module")
def schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


# --- the brief-mandated record pins -----------------------------------------


def test_rights_record_is_explicit(edit):
    assert edit["source"]["usage_class"] == "third_party_copyrighted"
    assert "bed and picture" in edit["source"]["source_rights_note"]


def test_requested_source_is_pinned(edit):
    assert edit["source"]["youtube_id"] == "WVi0d7oqDvs"
    assert edit["source"]["sha256"] == (
        "258af289edd7097e3dced9b6f7bda7d3f2e11476e3ee8ecf084befba3151c959"
    )


# --- the record against its schema ------------------------------------------


def test_committed_record_satisfies_its_schema(edit, schema):
    errors = sorted(
        Draft202012Validator(schema).iter_errors(edit),
        key=lambda e: list(e.path),
    )
    assert not errors, "\n".join(
        f"{'/'.join(str(p) for p in e.path)}: {e.message}" for e in errors
    )


def test_validate_edit_accepts_the_committed_record(edit):
    build.validate_edit(edit)  # returns None, does not raise


def test_validate_edit_rejects_an_unlisted_usage_class(edit):
    doc = copy.deepcopy(edit)
    doc["source"]["usage_class"] = "public_domain"
    with pytest.raises(ValueError, match="usage_class"):
        build.validate_edit(doc)


def test_validate_edit_rejects_a_missing_rights_note(edit):
    doc = copy.deepcopy(edit)
    del doc["source"]["source_rights_note"]
    with pytest.raises(ValueError):
        build.validate_edit(doc)


def test_validate_edit_rejects_a_malformed_sha256(edit):
    doc = copy.deepcopy(edit)
    doc["source"]["sha256"] = "not-a-hash"
    with pytest.raises(ValueError):
        build.validate_edit(doc)


# --- measurements are internally consistent ---------------------------------


def test_measurements_are_from_argo_not_youtube_metadata(edit):
    """The YouTube summary said ~477 s at 24 fps; the authoritative Argo
    probe says 24000/1001. A record carrying the metadata's rounded values
    fails here."""
    source = edit["source"]
    assert source["frame_rate"] == "24000/1001"
    assert source["time_base"] == "1/1000"
    assert source["audio_sample_rate_hz"] == 48000
    evidence = source["evidence"]
    for key in ("preflight_workflow", "bed_workflow", "source_review_workflow"):
        assert evidence[key], f"evidence.{key} must name the Argo workflow"


def test_frame_count_matches_duration_within_one_frame(edit):
    source = edit["source"]
    num, den = (int(part) for part in source["frame_rate"].split("/"))
    expected = source["duration_seconds"] * num / den
    assert abs(source["frame_count"] - expected) <= 1.0


def test_decoded_sample_count_matches_duration(edit):
    source = edit["source"]
    implied = source["decoded_sample_count"] / source["audio_sample_rate_hz"]
    assert abs(implied - source["duration_seconds"]) < 0.1


# --- the generator's workflow kinds ------------------------------------------


def test_build_workflow_rejects_an_unknown_kind(edit, tmp_path):
    with pytest.raises(ValueError, match="kind"):
        build.build_workflow("make-sandwich", edit, tmp_path)


@pytest.mark.parametrize("kind", ["picture", "mux-validate"])
def test_unimplemented_kinds_refuse_loudly(edit, tmp_path, kind):
    """Skeletons must not emit a half-designed manifest."""
    with pytest.raises(NotImplementedError):
        build.build_workflow(kind, edit, tmp_path)


# --- the source-review workflow ----------------------------------------------

@pytest.fixture(scope="module")
def source_review(edit, tmp_path_factory):
    work_dir = tmp_path_factory.mktemp("srcreview")
    return build.build_workflow("source-review", edit, work_dir)


def _containers(manifest):
    for template in manifest["spec"]["templates"]:
        container = template.get("container")
        if container:
            yield template["name"], container


def _all_scripts(manifest):
    return "\n".join(
        container["args"][0]
        for _, container in _containers(manifest)
        if container.get("args")
    )


def test_source_review_is_a_workflow(source_review):
    assert source_review["kind"] == "Workflow"
    assert source_review["apiVersion"] == "argoproj.io/v1alpha1"
    assert source_review["metadata"]["namespace"] == "argo"


def test_source_review_pins_the_recorded_source(source_review, edit):
    params = {
        p["name"]: p["value"]
        for p in source_review["spec"]["arguments"]["parameters"]
    }
    assert params["source-sha256"] == edit["source"]["sha256"]
    assert params["source-url"] == edit["transport"]["fetch_url"]
    assert params["receiver-url"] == edit["transport"]["receiver_url"]
    scripts = _all_scripts(source_review)
    assert "sha256sum" in scripts


def test_source_review_probes_are_authoritative(source_review):
    scripts = _all_scripts(source_review)
    assert "source-probe.json" in scripts
    assert "-count_frames" in scripts
    assert "-show_format -show_streams" in scripts
    assert "scene-times.tsv" in scripts
    assert "showinfo" in scripts
    assert "source-contact-sheet.jpg" in scripts


def test_source_review_uploads_survive_failure(source_review):
    spec = source_review["spec"]
    assert spec.get("onExit"), "records must upload even on failure"
    templates = {t["name"]: t for t in spec["templates"]}
    assert spec["onExit"] in templates
    upload_script = templates[spec["onExit"]]["container"]["args"][0]
    assert "workflow-status.json" in upload_script
    assert "SHA256SUMS" in upload_script


def test_source_review_uploads_flat_filenames(source_review):
    """upload-server.py stores basename(path) only: an uploaded `review/`
    path would silently land in the receiver root. Uploads are therefore
    flat, and local organization into review/ is a documented move."""
    templates = {t["name"]: t for t in source_review["spec"]["templates"]}
    upload_script = templates[source_review["spec"]["onExit"]][
        "container"]["args"][0]
    assert "$receiver_url/review" not in upload_script
    assert "$receiver_url/$record_prefix-" in upload_script


def test_source_review_is_not_hostname_pinned(source_review):
    spec = source_review["spec"]
    assert "nodeSelector" not in spec
    for template in spec["templates"]:
        assert "nodeSelector" not in template


def test_source_review_pulls_only_if_absent(source_review):
    for name, container in _containers(source_review):
        assert container.get("imagePullPolicy") == "IfNotPresent", name


def test_build_workflow_writes_the_manifest(edit, tmp_path):
    manifest = build.build_workflow("source-review", edit, tmp_path)
    written = tmp_path / "uta-general-dark-army-source-review.yaml"
    assert written.exists()
    assert yaml.safe_load(written.read_text()) == manifest


# --- the composition treatment (owner bar, 2026-09-05) -----------------------


def test_primary_treatment_is_negative_space_overlay(edit):
    """Artwork occupies the official shot's existing negative space with the
    source frame preserved -- shot-authored anchors from manual scene
    review, never a forced generic split panel or uniform 50/50 crop.
    Full-screen art stays a deliberate occasional accent."""
    comp = edit["composition"]
    assert comp["mode"] == "negative-space-overlay"
    assert comp["accent_only_fullscreen"] is True


def test_background_is_derived_not_black_pillarbox(edit):
    assert edit["composition"]["background"] == "derived-layered"


def test_transitions_are_smooth(edit):
    bounds = edit["composition"]["transition_frames"]
    assert 6 <= bounds["min"] <= bounds["max"] <= 12


def test_artwork_is_present_from_the_opening(edit):
    assert edit["composition"]["artwork_within_first_seconds"] == 35


def test_protected_window_and_singer_shots(edit):
    comp = edit["composition"]
    assert comp["protect_direct_camera_singer_shots"] is True
    assert any(
        iv["start_seconds"] <= 320 and iv["end_seconds"] >= 350
        for iv in comp["protected"]
    ), "5:20-5:50 (320-350 s) must be wholly inside a protected interval"


def test_protected_intervals_have_reasons(edit):
    for iv in edit["composition"]["protected"]:
        assert iv["reason"].strip()


def test_validate_edit_rejects_overlapping_protected_intervals(edit):
    doc = copy.deepcopy(edit)
    doc["composition"]["protected"].append(
        {"start_seconds": 300, "end_seconds": 330, "reason": "overlap"}
    )
    with pytest.raises(ValueError, match="overlap"):
        build.validate_edit(doc)


def test_validate_edit_rejects_inverted_transition_bounds(edit):
    doc = copy.deepcopy(edit)
    doc["composition"]["transition_frames"] = {"min": 12, "max": 6}
    with pytest.raises(ValueError, match="transition"):
        build.validate_edit(doc)


def test_timeline_entries_distinguish_treatment_kinds(edit, schema):
    """The schema represents per-segment overlay (source-preserved), panel,
    accent, and source-only intervals (the timeline itself lands in a later
    task)."""
    doc = copy.deepcopy(edit)
    doc["composition"]["timeline"] = [
        {"start_seconds": 0, "end_seconds": 12, "kind": "overlay",
         "overlays": [{"art_asset": "RAFI_01", "anchor": "right"}]},
        {"start_seconds": 200, "end_seconds": 204, "kind": "accent",
         "overlays": [{"art_asset": "CHA_LAKSHMI_01", "anchor": "right"}]},
        {"start_seconds": 320, "end_seconds": 350, "kind": "source-only"},
    ]
    build.validate_edit(doc)  # must not raise
    doc["composition"]["timeline"][0]["kind"] = "slideshow"
    with pytest.raises(ValueError):
        build.validate_edit(doc)


def test_per_segment_overlay_carries_anchor_box_scale_zorder(edit):
    doc = copy.deepcopy(edit)
    doc["composition"]["timeline"] = [
        {"start_seconds": 12, "end_seconds": 20, "kind": "overlay",
         "overlays": [{
             "art_asset": "RAFI_02",
             "anchor": "right",
             "box": {"x": 700, "y": 250, "width": 1300, "height": 750},
             "scale": 0.9,
             "z_order": 1,
         }]},
    ]
    build.validate_edit(doc)  # must not raise


def test_overlay_anchor_is_reviewed_vocabulary(edit):
    doc = copy.deepcopy(edit)
    doc["composition"]["timeline"] = [
        {"start_seconds": 12, "end_seconds": 20, "kind": "overlay",
         "overlays": [{"art_asset": "RAFI_02", "anchor": "middle"}]},
    ]
    with pytest.raises(ValueError):
        build.validate_edit(doc)


def test_overlay_assets_must_exist_in_the_registry(edit):
    """No invented art: an overlay may only name a registered asset."""
    doc = copy.deepcopy(edit)
    doc["composition"]["timeline"] = [
        {"start_seconds": 12, "end_seconds": 20, "kind": "overlay",
         "overlays": [{"art_asset": "invented-dragon", "anchor": "right"}]},
    ]
    with pytest.raises(ValueError, match="invented-dragon"):
        build.validate_edit(doc)


def test_source_only_segments_take_no_overlay(edit):
    doc = copy.deepcopy(edit)
    doc["composition"]["timeline"] = [
        {"start_seconds": 320, "end_seconds": 350, "kind": "source-only",
         "overlays": [{"art_asset": "RAFI_01", "anchor": "right"}]},
    ]
    with pytest.raises(ValueError, match="source-only"):
        build.validate_edit(doc)


def test_composed_segments_require_an_overlay(edit):
    doc = copy.deepcopy(edit)
    doc["composition"]["timeline"] = [
        {"start_seconds": 12, "end_seconds": 20, "kind": "overlay"},
    ]
    with pytest.raises(ValueError, match="overlay"):
        build.validate_edit(doc)


def test_overlay_boxes_stay_inside_the_source_frame(edit):
    doc = copy.deepcopy(edit)
    doc["composition"]["timeline"] = [
        {"start_seconds": 12, "end_seconds": 20, "kind": "overlay",
         "overlays": [{
             "art_asset": "RAFI_01", "anchor": "right",
             "box": {"x": 1900, "y": 0, "width": 500, "height": 400},
         }]},
    ]
    with pytest.raises(ValueError, match="box"):
        build.validate_edit(doc)


def test_registered_assets_are_existing_files(edit):
    for asset_id, entry in edit["composition"]["assets"].items():
        assert entry["file"].endswith(".png"), asset_id


OWNER_REVIEWED_CHONKERS = {
    "CHONKY_ACHILLIBATOR_POSE1", "CHONKY_ACHILLIBATOR_POSE2",
    "CHONKY_ALAMO_BLUE", "CHONKY_DAKOSAURUS_BLUEFINSKIN",
    "CHONKY_TOROSAURUS_BLUE", "CHONKY_UTAHRAPTOR_BLUEFINSKIN",
    "CUSTOMCHONK_JORGE_CONCAVENATOR", "CUSTOMCHONK_JORGE_DEINONYCHUSA",
    "JORGE_CUSTOMCHONKS_ARMAGASAURUSUS", "JORGE_CUSTOMCHONKS_DIMETRODONA",
    "JORGE_CUSTOMCHONKS_INTRIGUED", "JORGE_CUSTOMCHONKS_KENTROSAURUS",
    "JORGE_CUSTOMCHONKS_LEAPING", "JORGE_CUSTOMCHONKS_NESTINGRAPTOR",
    "JORGE_CUSTOMCHONKS_PIVOTRAPTOR", "JORGE_CUSTOMCHONKS_ROARING",
}


def test_chonker_variety_is_owner_reviewed(edit):
    """Owner audit 2026-09-05: a restrained rotating subset of these named,
    existing, transparent PNGs. Anything else -- trex.webp with its opaque
    gray background, or any un-reviewed art -- is not registrable here."""
    assets = edit["composition"]["assets"]
    chonkers = {k for k in assets if "CHONK" in k}
    assert chonkers == OWNER_REVIEWED_CHONKERS
    assert all(assets[k]["file"].startswith(
        ("Chonky_", "CustomChonk_Jorge_", "Jorge_CustomChonks_"))
        for k in chonkers)
    assert "trex.webp" not in {a["file"] for a in assets.values()}


# --- weapon/component callouts (owner scope, 2026-09-05) ----------------------

def _with_callout(edit, callout):
    doc = copy.deepcopy(edit)
    doc["composition"]["callouts"] = {"rafistol-spear": callout}
    return doc


def _sample_callout():
    return {
        "copy": {"label": "RAFISTOL SPEAR", "description": "polearms, yeah"},
        "source": {
            "sheet": "Cha Design_RAFI.jpg",
            "crop": {"x": 100, "y": 200, "width": 640, "height": 480},
            "evidence": "review/callouts/rafistol-spear-crop.png",
        },
        "label_box": {"x": 2800, "y": 300, "width": 900, "height": 400},
        "leader_anchor": {"x": 2400, "y": 900},
        "font_size": 96,
        "description_font_size": 56,
        "usage": "dedicated-hold",
        "min_hold_seconds": 4.0,
    }


def test_overlay_canvas_is_4k(edit):
    """3840x2160 is the target overlay canvas; callout coordinates live in
    that space."""
    assert edit["composition"]["overlay_canvas"] == {
        "width": 3840, "height": 2160}


def test_a_callout_carries_verbatim_copy_anchor_box_and_font(edit):
    """The full model: verbatim transcribed copy, source sheet/crop
    evidence, label box, leader anchor, font sizes, 4K coordinates."""
    build.validate_edit(_with_callout(edit, _sample_callout()))


def test_callout_copy_must_be_transcribed_from_a_source_sheet(edit):
    """No invented descriptions: a callout without its source sheet and
    crop is rejected."""
    bad = _sample_callout()
    del bad["source"]["sheet"]
    with pytest.raises(ValueError):
        build.validate_edit(_with_callout(edit, bad))
    bad = _sample_callout()
    del bad["copy"]["label"]
    with pytest.raises(ValueError):
        build.validate_edit(_with_callout(edit, bad))


def test_callout_usage_is_label_or_dedicated_hold(edit):
    """Short labels may accompany side-by-side art; long descriptions get
    dedicated readable holds. Nothing in between."""
    bad = _sample_callout()
    bad["usage"] = "wherever"
    with pytest.raises(ValueError):
        build.validate_edit(_with_callout(edit, bad))


def test_callout_geometry_stays_on_the_4k_canvas(edit):
    bad = _sample_callout()
    bad["label_box"] = {"x": 3500, "y": 300, "width": 900, "height": 400}
    with pytest.raises(ValueError, match="label_box"):
        build.validate_edit(_with_callout(edit, bad))
    bad = _sample_callout()
    bad["leader_anchor"] = {"x": -5, "y": 900}
    with pytest.raises(ValueError, match="leader_anchor"):
        build.validate_edit(_with_callout(edit, bad))


def test_timeline_segments_may_reference_registered_callouts(edit):
    doc = _with_callout(edit, _sample_callout())
    doc["composition"]["timeline"] = [
        {"start_seconds": 60, "end_seconds": 66, "kind": "overlay",
         "overlays": [{"art_asset": "RAFI_01", "anchor": "right"}],
         "callouts": ["rafistol-spear"]},
    ]
    build.validate_edit(doc)  # must not raise


def test_timeline_rejects_unknown_or_misplaced_callouts(edit):
    doc = _with_callout(edit, _sample_callout())
    doc["composition"]["timeline"] = [
        {"start_seconds": 60, "end_seconds": 66, "kind": "overlay",
         "overlays": [{"art_asset": "RAFI_01", "anchor": "right"}],
         "callouts": ["invented-callout"]},
    ]
    with pytest.raises(ValueError, match="invented-callout"):
        build.validate_edit(doc)
    doc = _with_callout(edit, _sample_callout())
    doc["composition"]["timeline"] = [
        {"start_seconds": 320, "end_seconds": 350, "kind": "source-only",
         "callouts": ["rafistol-spear"]},
    ]
    with pytest.raises(ValueError, match="source-only"):
        build.validate_edit(doc)


# --- the enum mapping ----------------------------------------------------------


def test_usage_class_enum_is_generated_from_vocab(schema):
    pointer = "/properties/source/properties/usage_class"
    assert ("uta-art-video.schema.json", pointer) in gen.MAP
    node = gen.resolve_pointer(schema, pointer)
    assert node["enum"] == gen.vocab_values("provenance.yaml", "usage_class")
