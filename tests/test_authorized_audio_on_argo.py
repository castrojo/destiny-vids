from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = (
    REPO_ROOT
    / "docs"
    / "skills"
    / "hero-videos"
    / "references"
    / "authorized-audio-on-argo.md"
)


def _stage_one_manifest() -> dict[str, object]:
    text = RUNBOOK.read_text(encoding="utf-8")
    stage = text.index("## Stage 1 — bed workflow")
    start = text.index("```yaml", stage) + len("```yaml")
    end = text.index("```", start)
    manifest = yaml.safe_load(text[start:end])
    assert isinstance(manifest, dict)
    return manifest


def test_stage_one_final_bed_trim_is_sample_exact_and_gated():
    manifest = _stage_one_manifest()
    parameters = {
        parameter["name"]: parameter["value"]
        for parameter in manifest["spec"]["arguments"]["parameters"]
    }
    assert parameters["start-sample"] == "0"
    assert parameters["end-sample"] == "1440000"
    assert parameters["expected-sample-count"] == "1440000"

    templates = {template["name"]: template for template in manifest["spec"]["templates"]}
    script = templates["analyze-and-build-bed"]["container"]["args"][0]

    assert (
        "atrim=start_sample={{workflow.parameters.start-sample}}:"
        "end_sample={{workflow.parameters.end-sample}},asetpts=PTS-STARTPTS"
    ) in script
    assert not re.search(r"(?:^|\s)-ss(?:\s|$)", script)
    assert not re.search(r"(?:^|\s)-t(?:\s|$)", script)
    assert "[ \"$bed_duration_ts\" = \"$expected_sample_count\" ]" in script
    assert "[ \"$expected_sample_count\" -eq $(({{workflow.parameters.end-sample}} - {{workflow.parameters.start-sample}})) ]" in script
    assert '"$bed_codec" = "pcm_s24le"' in script
    assert '"$bed_rate" = "48000"' in script
    assert '"$bed_channels" = "2"' in script
    assert '"$bed_time_base" = "1/48000"' in script

    upload_script = templates["upload-results"]["container"]["args"][0]
    assert "bed-format.json" in upload_script
    assert "bed-format-gate.json" in upload_script
