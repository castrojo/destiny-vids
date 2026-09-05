#!/usr/bin/env python3
"""Generate the Argo workflows for the UTA "General of the Dark Army" montage.

The edit record is stories/uta-general-dark-army.json; every measurement in
it was returned by an Argo workflow, and every workflow this module emits is
derived from that record -- the pinned source SHA-256, the transport
endpoints, and the naming prefix travel together so a workflow can never
quietly run against a different source than the record describes.

    python3 scripts/build_uta_art_video.py --kind source-review \
        --work-dir ~/Videos/Wolves/Hero/.work-uta-general
    python3 -m pytest tests/test_uta_art_video.py -q

Three kinds exist (schema-local discriminators, not shared vocabulary):

* ``source-review`` -- IMPLEMENTED. Fetches and hash-pins the source, runs
  the authoritative FFprobe (source-probe.json), extracts scene-change times
  (scene-times.tsv), a contact sheet, and spaced review frames, and uploads
  every record with flat filenames (the PUT receiver flattens paths, so any
  local organization into ``review/`` afterwards is a documented move).
* ``picture`` -- skeleton. A later task designs the montage timeline.
* ``mux-validate`` -- skeleton. A later task designs delivery validation.

Farm policy is structural, not optional: no hostname pinning, every image
``imagePullPolicy: IfNotPresent`` (the registry mirror times out on plain
pulls), and an ``onExit`` uploader so records land even when a gate fails.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
EDIT = REPO_ROOT / "stories" / "uta-general-dark-army.json"
SCHEMA = REPO_ROOT / "schema" / "uta-art-video.schema.json"

WORKFLOW_KINDS = ("source-review", "picture", "mux-validate")

# Manifest fragments shared by every kind. serviceAccountName, podGC, the
# local-path PVC and IfNotPresent match the documented Stage 1 bed workflow;
# nodeSelector is deliberately absent everywhere (pods are never
# hostname-pinned).

_FETCH_TEMPLATE = {
    "name": "fetch",
    "securityContext": {"fsGroup": 100},
    "container": {
        "image": "curlimages/curl:8.17.0",
        "imagePullPolicy": "IfNotPresent",
        "resources": {
            "requests": {"cpu": "200m", "memory": "256Mi"},
            "limits": {"cpu": "1", "memory": "512Mi"},
        },
        "command": ["sh", "-c"],
        "args": [
            """\
mkdir -p /work
curl -fsSL '{{workflow.parameters.source-url}}' -o /work/source
fetch_status=$?
actual_sha256=""
hash_status=1
if [ "$fetch_status" -eq 0 ]; then
  actual_sha256="$(sha256sum /work/source | awk '{print $1}')"
  hash_status=$?
fi
source_match=false
if [ "$fetch_status" -eq 0 ] &&
   [ "$hash_status" -eq 0 ] &&
   [ "$actual_sha256" = '{{workflow.parameters.source-sha256}}' ]; then
  source_match=true
else
  fetch_status=1
fi
printf '%s\\n' \\
  "{\\"source_url\\":\\"{{workflow.parameters.source-url}}\\",\\"expected_sha256\\":\\"{{workflow.parameters.source-sha256}}\\",\\"actual_sha256\\":\\"$actual_sha256\\",\\"source_match\\":$source_match,\\"fetch_exit_status\\":$fetch_status}" \\
  > /work/source-fetch-status.json
exit "$fetch_status"
"""
        ],
        "volumeMounts": [{"name": "work", "mountPath": "/work"}],
    },
}

_REVIEW_SCRIPT = """\
work=/work
overall=0
run_to_file() {
  file=$1
  shift
  "$@" > "$work/$file" 2>&1
  command_status=$?
  printf '\\nexit_status=%s\\n' "$command_status" >> "$work/$file"
  if [ "$command_status" -ne 0 ]; then
    overall=1
  fi
  return 0
}
# The authoritative probe: frame rate, frame count, duration and time base
# for the record come from this file, never from the YouTube metadata
# summary. -count_frames decodes the whole video so the WebM's frame count
# is measured (nb_read_frames), not read from optional container metadata
# the source does not carry. JSON artifacts stay valid JSON: the exit
# status goes to the sidecar .stderr, never appended to the JSON itself.
ffprobe -v error -count_frames -show_format -show_streams -of json \\
  "$work/source" > "$work/source-probe.json" 2> "$work/source-probe.stderr"
probe_status=$?
printf 'exit_status=%s\\n' "$probe_status" >> "$work/source-probe.stderr"
if [ "$probe_status" -ne 0 ]; then
  overall=1
fi
run_to_file scene-detect.log ffmpeg -hide_banner -i "$work/source" \\
  -vf "select='gt(scene,0.4)',showinfo" -f null -
{
  printf 'frame\\tpts_time_seconds\\n'
  grep 'Parsed_showinfo' "$work/scene-detect.log" | \\
    awk '{ n=""; t=""; for (i=1;i<=NF;i++) { \\
             if ($i=="n:") n=$(i+1); \\
             if ($i ~ /^pts_time:/) { sub(/^pts_time:/, "", $i); t=$i } } \\
           if (t != "") printf "%s\\t%s\\n", n, t }'
} > "$work/scene-times.tsv"
# One contact sheet: the whole source at one tile per 10 s.
run_to_file contact-sheet.log ffmpeg -hide_banner -y -i "$work/source" \\
  -vf "fps=1/10,scale=320:180,tile=5x10" -frames:v 1 \\
  "$work/source-contact-sheet.jpg"
# Spaced review frames, uploaded flat as <record-prefix>-review-NNN.jpg and
# organized into review/ locally afterwards (the receiver flattens paths).
run_to_file review-frames.log ffmpeg -hide_banner -y -i "$work/source" \\
  -vf fps=1/30 -q:v 3 "$work/review-%03d.jpg"
exit "$overall"
"""

_UPLOAD_SCRIPT = """\
work=/work
receiver_url='{{workflow.parameters.receiver-url}}'
record_prefix='{{workflow.parameters.record-prefix}}'
printf '%s\\n' \\
  "{\\"workflow_name\\":\\"{{workflow.name}}\\",\\"workflow_uid\\":\\"{{workflow.uid}}\\",\\"workflow_status\\":\\"{{workflow.status}}\\",\\"stage\\":\\"source-review\\"}" \\
  > "$work/workflow-status.json"
: > "$work/SHA256SUMS"
hashed="source-fetch-status.json source-probe.json source-probe.stderr scene-detect.log scene-times.tsv contact-sheet.log source-contact-sheet.jpg review-frames.log workflow-status.json"
for file in $hashed; do
  if [ -f "$work/$file" ]; then
    sha256sum "$work/$file" >> "$work/SHA256SUMS"
  fi
done
for file in "$work"/review-*.jpg; do
  if [ -f "$file" ]; then
    sha256sum "$file" >> "$work/SHA256SUMS"
  fi
done
upload_status=0
for file in $hashed SHA256SUMS; do
  if [ -f "$work/$file" ]; then
    curl -fsS -T "$work/$file" \\
      "$receiver_url/$record_prefix-$file" || upload_status=1
  fi
done
for file in "$work"/review-*.jpg; do
  if [ -f "$file" ]; then
    curl -fsS -T "$file" \\
      "$receiver_url/$record_prefix-$(basename "$file")" || upload_status=1
  fi
done
exit "$upload_status"
"""


def load_edit(path):
    """The edit record as a dict. Parse only; validate separately."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_edit(doc):
    """Raise ValueError on any schema or internal-consistency violation.

    Consistency checks are what keep a hand-typed timing value out: the
    frame count must match the duration within one frame, and the decoded
    sample count must match the duration at the native rate.
    """
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(doc),
        key=lambda e: list(e.absolute_path),
    )
    if errors:
        raise ValueError(
            "edit record violates schema/uta-art-video.schema.json:\n"
            + "\n".join(
                f"  {'/'.join(str(p) for p in e.absolute_path)}: {e.message}"
                for e in errors
            )
        )
    source = doc["source"]
    num, den = (int(part) for part in source["frame_rate"].split("/"))
    expected_frames = source["duration_seconds"] * num / den
    if abs(source["frame_count"] - expected_frames) > 1.0:
        raise ValueError(
            f"source/frame_count {source['frame_count']} is more than one "
            f"frame from duration_seconds {source['duration_seconds']} at "
            f"{source['frame_rate']} ({expected_frames:.3f})"
        )
    implied = source["decoded_sample_count"] / source["audio_sample_rate_hz"]
    if abs(implied - source["duration_seconds"]) >= 0.1:
        raise ValueError(
            f"source/decoded_sample_count implies {implied:.6f}s but "
            f"source/duration_seconds is {source['duration_seconds']}"
        )

    comp = doc.get("composition")
    if comp:
        bounds = comp["transition_frames"]
        if bounds["min"] > bounds["max"]:
            raise ValueError(
                f"composition/transition_frames min {bounds['min']} exceeds "
                f"max {bounds['max']}"
            )
        intervals = sorted(
            (iv["start_seconds"], iv["end_seconds"]) for iv in comp["protected"]
        )
        for (a_start, a_end), (b_start, _) in zip(intervals, intervals[1:]):
            if b_start < a_end:
                raise ValueError(
                    f"composition/protected intervals overlap: "
                    f"{a_start}-{a_end} and {b_start}-..."
                )
        for iv in comp["protected"]:
            if iv["end_seconds"] <= iv["start_seconds"]:
                raise ValueError(
                    f"composition/protected interval ends before it starts: "
                    f"{iv['start_seconds']}-{iv['end_seconds']}"
                )

        assets = comp.get("assets", {})
        frame_w = doc["source"]["width"]
        frame_h = doc["source"]["height"]
        for i, seg in enumerate(comp.get("timeline", [])):
            kind = seg["kind"]
            overlays = seg.get("overlays", [])
            where = f"composition/timeline[{i}] ({kind})"
            if kind == "source-only" and overlays:
                raise ValueError(
                    f"{where}: source-only segments take no overlay"
                )
            if kind in ("overlay", "panel") and not overlays:
                raise ValueError(
                    f"{where}: a composed segment needs at least one overlay"
                )
            for j, ov in enumerate(overlays):
                asset = ov["art_asset"]
                if asset not in assets:
                    raise ValueError(
                        f"{where} overlays[{j}]: art_asset {asset!r} is not in "
                        f"composition/assets -- new art is never invented"
                    )
                box = ov.get("box")
                if box:
                    if (box["x"] + box["width"] > frame_w
                            or box["y"] + box["height"] > frame_h):
                        raise ValueError(
                            f"{where} overlays[{j}]: box "
                            f"{box['x']},{box['y']} "
                            f"{box['width']}x{box['height']} exceeds the "
                            f"{frame_w}x{frame_h} source frame"
                        )
            callout_ids = comp.get("callouts", {})
            for cid in seg.get("callouts", []):
                if kind == "source-only":
                    raise ValueError(
                        f"{where}: source-only segments take no callout"
                    )
                if cid not in callout_ids:
                    raise ValueError(
                        f"{where}: callout {cid!r} is not in "
                        f"composition/callouts"
                    )
            intro_end = comp["intro_clean_until_seconds"]
            if kind in ("overlay", "accent") and seg["start_seconds"] < intro_end:
                raise ValueError(
                    f"{where}: starts at {seg['start_seconds']}s, before the "
                    f"clean intro ends at {intro_end}s -- no artwork until "
                    f"the title/intro sequence has clearly finished"
                )

        canvas = comp.get("overlay_canvas")
        for cid, callout in comp.get("callouts", {}).items():
            validate_callout_copy(cid, callout["copy"])
            box = callout["label_box"]
            if (box["x"] + box["width"] > canvas["width"]
                    or box["y"] + box["height"] > canvas["height"]):
                raise ValueError(
                    f"composition/callouts/{cid}/label_box exceeds the "
                    f"{canvas['width']}x{canvas['height']} overlay canvas"
                )
            anchor = callout["leader_anchor"]
            if not (0 <= anchor["x"] <= canvas["width"]
                    and 0 <= anchor["y"] <= canvas["height"]):
                raise ValueError(
                    f"composition/callouts/{cid}/leader_anchor "
                    f"{anchor['x']},{anchor['y']} is off the "
                    f"{canvas['width']}x{canvas['height']} overlay canvas"
                )


def apply_copyedits(verbatim, copyedits):
    """Apply the recorded corrections, in order, to a verbatim string.

    Each edit is a literal substring replacement. An edit whose ``from`` does
    not occur is a stale record -- it is raised rather than skipped, because a
    correction nobody can point at in the source is indistinguishable from
    invented copy.
    """
    text = verbatim
    for i, edit in enumerate(copyedits or []):
        if edit["from"] not in text:
            raise ValueError(
                f"copyedit[{i}] {edit['from']!r} does not occur in the "
                f"verbatim copy {text!r} -- a correction must point at real "
                f"text on the sheet"
            )
        text = text.replace(edit["from"], edit["to"])
    return text


def validate_callout_copy(cid, copy):
    """The rendered wording must be the sheet's wording plus recorded fixes.

    The owner authorized correcting the design sheets ("correct the spelling
    and copyedit too", 2026-09-05), so a callout may put different characters
    on screen than the sheet carries. What it may never do is put words on
    screen that nobody can trace: every difference has to be a listed
    correction with a reason. Rebuilding each rendered string from its
    verbatim one is what makes that auditable instead of asserted.
    """
    where = f"composition/callouts/{cid}/copy"
    edits = copy.get("copyedits", [])
    fields = ("label", "subtitle", "description")

    for field in fields:
        if field not in copy:
            continue
        rendered = f"{field}_render"
        if rendered not in copy:
            raise ValueError(
                f"{where}: verbatim {field!r} needs {rendered!r}, so what is "
                f"drawn on screen is recorded next to what the sheet says"
            )
        verbatim = copy[field]
        applicable = [e for e in edits if e["from"] in verbatim]
        rebuilt = apply_copyedits(verbatim, applicable)
        if rebuilt != copy[rendered]:
            raise ValueError(
                f"{where}/{rendered} is not the verbatim {field} with its "
                f"recorded copyedits applied. Verbatim {verbatim!r} plus "
                f"those edits gives {rebuilt!r}, but the record renders "
                f"{copy[rendered]!r} -- rendered copy must be traceable to "
                f"the sheet"
            )

    for i, edit in enumerate(edits):
        if not any(edit["from"] in copy.get(f, "") for f in fields):
            raise ValueError(
                f"{where}/copyedits[{i}]: {edit['from']!r} occurs in none of "
                f"the verbatim label, subtitle or description -- a correction "
                f"must point at real text on the sheet"
            )


def _record_prefix(edit, kind):
    """`uta-general-dark-army-srcreview-v1` style: stable per kind+version."""
    short = {"source-review": "srcreview"}[kind]
    return f"{edit['edit_id']}-{short}-v1"


def _source_review(edit):
    return {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Workflow",
        "metadata": {
            "generateName": f"{edit['edit_id']}-srcreview-",
            "namespace": "argo",
            "labels": {"hero-video": edit["edit_id"], "run-type": "source-review"},
        },
        "spec": {
            "entrypoint": "review",
            "onExit": "upload-results",
            "serviceAccountName": "argo",
            "arguments": {
                "parameters": [
                    {"name": "source-url", "value": edit["transport"]["fetch_url"]},
                    {"name": "source-sha256", "value": edit["source"]["sha256"]},
                    {"name": "receiver-url", "value": edit["transport"]["receiver_url"]},
                    {"name": "record-prefix", "value": _record_prefix(edit, "source-review")},
                ]
            },
            "podGC": {"strategy": "OnWorkflowCompletion"},
            "ttlStrategy": {"secondsAfterSuccess": 3600, "secondsAfterFailure": 3600},
            "volumeClaimTemplates": [
                {
                    "metadata": {"name": "work"},
                    "spec": {
                        "accessModes": ["ReadWriteOnce"],
                        "storageClassName": "local-path",
                        "resources": {"requests": {"storage": "8Gi"}},
                    },
                }
            ],
            "templates": [
                {
                    "name": "review",
                    "dag": {
                        "tasks": [
                            {"name": "fetch", "template": "fetch"},
                            {
                                "name": "probe-and-frames",
                                "template": "probe-and-frames",
                                "dependencies": ["fetch"],
                            },
                        ]
                    },
                },
                _FETCH_TEMPLATE,
                {
                    "name": "probe-and-frames",
                    "securityContext": {"fsGroup": 100},
                    "container": {
                        "image": "lscr.io/linuxserver/ffmpeg:8.1.2-cli-ls76",
                        "imagePullPolicy": "IfNotPresent",
                        "resources": {
                            "requests": {"cpu": "2", "memory": "2Gi"},
                            "limits": {"cpu": "8", "memory": "8Gi"},
                        },
                        "command": ["sh", "-c"],
                        "args": [_REVIEW_SCRIPT],
                        "volumeMounts": [{"name": "work", "mountPath": "/work"}],
                    },
                },
                {
                    "name": "upload-results",
                    "securityContext": {"fsGroup": 100},
                    "container": {
                        "image": "curlimages/curl:8.17.0",
                        "imagePullPolicy": "IfNotPresent",
                        "resources": {
                            "requests": {"cpu": "200m", "memory": "256Mi"},
                            "limits": {"cpu": "1", "memory": "512Mi"},
                        },
                        "command": ["sh", "-c"],
                        "args": [_UPLOAD_SCRIPT],
                        "volumeMounts": [{"name": "work", "mountPath": "/work"}],
                    },
                },
            ],
        },
    }


def build_workflow(kind, doc, work_dir):
    """The Argo manifest for `kind`, written to work_dir and returned.

    `picture` and `mux-validate` are skeletons on purpose: a later task
    designs them, and until then they refuse rather than emit a
    half-designed manifest.
    """
    if kind not in WORKFLOW_KINDS:
        raise ValueError(
            f"unknown workflow kind {kind!r} (known: {', '.join(WORKFLOW_KINDS)})"
        )
    if kind in ("picture", "mux-validate"):
        raise NotImplementedError(
            f"workflow kind {kind!r} is a skeleton: a later task designs it"
        )
    validate_edit(doc)
    manifest = _source_review(doc)
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    out = work_dir / f"{doc['edit_id']}-{kind}.yaml"
    out.write_text(
        yaml.safe_dump(manifest, sort_keys=False, width=100), encoding="utf-8"
    )
    return manifest


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--edit", type=Path, default=EDIT,
                    help="edit record (default: %(default)s)")
    ap.add_argument("--kind", required=True, choices=WORKFLOW_KINDS)
    ap.add_argument("--work-dir", type=Path, required=True,
                    help="directory the manifest YAML is written to")
    args = ap.parse_args(argv)

    doc = load_edit(args.edit)
    try:
        manifest = build_workflow(args.kind, doc, args.work_dir)
    except NotImplementedError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    out = args.work_dir / f"{doc['edit_id']}-{args.kind}.yaml"
    print(f"wrote {out} ({len(manifest['spec']['templates'])} templates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
