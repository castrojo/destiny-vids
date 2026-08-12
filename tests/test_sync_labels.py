"""Tests for the owned label set (scripts/sync_labels.py).

Offline: drift is a pure comparison, so these tests never touch gh or the
network. The gh-touching paths are exercised by feeding _gh a stub, which is
also how --check's skip-with-exit-0 contract (CI without a token must not
fail spuriously) gets covered.
"""
import json
import os
import sys

import pytest  # noqa: F401  (only used implicitly via monkeypatch/capsys)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import sync_labels  # noqa: E402


def _json_of(labels):
    return json.dumps(labels)


def test_the_owned_set_is_the_four_states_plus_the_triage_axes():
    assert [label["name"] for label in sync_labels.LABELS] == [
        "triage", "agent-ready", "blocked", "automatable/no",
        "area/indexing", "area/cut", "area/casting", "area/plates",
        "area/rights", "area/tooling",
        "size/S", "size/M", "size/L", "size/XL",
        "priority/now", "priority/next", "priority/later"]


def test_every_area_names_a_pipeline_stage_not_a_person():
    """An area is a routing hint. A label that named a person or a character
    would be a second source of truth about a real person, which the brief
    block and vocab/casting.yaml already own."""
    areas = [label["name"].split("/", 1)[1]
             for label in sync_labels.LABELS
             if label["name"].startswith("area/")]
    assert areas == ["indexing", "cut", "casting", "plates", "rights",
                     "tooling"]


def test_every_label_has_a_hex_color_and_a_description():
    for label in sync_labels.LABELS:
        assert len(label["color"]) == 6
        int(label["color"], 16)  # raises ValueError if not hex
        assert label["description"].strip()


def test_characters_are_not_labels():
    """Casting lives in the issue body's `brief` block, keyed by the leads
    in vocab/casting.yaml. A character/* label would be a second, diverging
    source of truth about a real person."""
    assert not any(label["name"].startswith("character/")
                   for label in sync_labels.LABELS)


def test_a_repo_in_sync_has_no_drift():
    actual = [dict(label) for label in sync_labels.LABELS]
    assert sync_labels.drift(sync_labels.LABELS, actual) == []


def test_a_missing_label_is_drift():
    actual = [l for l in sync_labels.LABELS if l["name"] != "blocked"]
    assert sync_labels.drift(sync_labels.LABELS, actual) == [
        {"name": "blocked", "kind": "missing"}]


def test_a_changed_color_or_description_is_drift():
    actual = [dict(label) for label in sync_labels.LABELS]
    actual[0]["color"] = "ffffff"
    actual[1]["description"] = "something else entirely"
    problems = sync_labels.drift(sync_labels.LABELS, actual)
    assert {(p["name"], p["kind"]) for p in problems} == {
        ("triage", "changed"), ("agent-ready", "changed")}
    by_name = {p["name"]: p for p in problems}
    assert "color" in by_name["triage"]["diffs"]
    assert "description" in by_name["agent-ready"]["diffs"]


def test_color_comparison_ignores_case():
    """gh and this file may disagree on hex case; that is not drift."""
    actual = [dict(l, color=l["color"].upper()) for l in sync_labels.LABELS]
    assert sync_labels.drift(sync_labels.LABELS, actual) == []


def test_unowned_labels_are_not_drift():
    """The script owns four labels, not the whole namespace: GitHub's
    defaults (bug, documentation, ...) are left alone."""
    actual = [dict(label) for label in sync_labels.LABELS]
    actual.append({"name": "bug", "color": "d73a4a",
                   "description": "GitHub default"})
    assert sync_labels.drift(sync_labels.LABELS, actual) == []


def test_check_passes_when_the_repo_is_in_sync(monkeypatch):
    monkeypatch.setattr(sync_labels, "_gh",
                        lambda args: _json_of(sync_labels.LABELS))
    assert sync_labels.main(["--check"]) == 0


def test_check_reports_drift_as_exit_1(monkeypatch, capsys):
    monkeypatch.setattr(sync_labels, "_gh", lambda args: "[]")
    assert sync_labels.main(["--check"]) == 1
    assert "MISSING: triage" in capsys.readouterr().out


def test_check_skips_with_exit_0_when_gh_is_unusable(monkeypatch, capsys):
    """No gh, no token, no network: a skip, not a failure — CI without a
    token must not go red over a label check it cannot perform."""
    def boom(args):
        raise sync_labels.GhUnavailable("no gh here")
    monkeypatch.setattr(sync_labels, "_gh", boom)
    assert sync_labels.main(["--check"]) == 0
    assert "SKIP" in capsys.readouterr().out


def test_write_fails_when_gh_is_unusable(monkeypatch):
    """A write was explicitly asked for, so a broken gh is an error."""
    def boom(args):
        raise sync_labels.GhUnavailable("no gh here")
    monkeypatch.setattr(sync_labels, "_gh", boom)
    assert sync_labels.main(["--write"]) == 1
