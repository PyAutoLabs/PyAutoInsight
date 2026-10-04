"""Scientific coverage survives ingestion without inventing acceptance."""

from copy import deepcopy

import pytest
from conftest import fixture_doc

from insight import summary


def test_current_project_fixture_is_valid_and_completion_is_not_acceptance():
    d = fixture_doc("lens_summary_v1.json")
    assert summary.classify(d) == ("ok", [])
    assert d["records"][0]["execution"]["status"] == "complete"
    assert summary.qualified_records(d) == 0


def test_empty_feed_is_valid_coverage_not_success():
    d = fixture_doc("valid_empty.json")
    assert summary.classify(d) == ("ok", [])
    assert summary.qualified_records(d) == 0


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_diagnostics_are_rejected(value):
    d = fixture_doc("lens_summary_v1.json")
    d["records"][0]["diagnostics"]["values"]["ess"] = value
    assert summary.classify(d)[0] == "invalid"


@pytest.mark.parametrize(
    "path",
    [
        "../secret",
        "/etc/passwd",
        "https://bad/a",
        "x/%2e%2e/a",
        "x\\secret",
        "x?query",
        "x#anchor",
        "x//y",
        "x/./y",
    ],
)
def test_unsafe_result_and_archive_paths_are_rejected(path):
    d = fixture_doc("lens_summary_v1.json")
    d["records"][0]["evidence_paths"] = [path]
    assert summary.classify(d)[0] == "invalid"
    d = fixture_doc("lens_summary_v1.json")
    d["records"][0]["samples"]["path"] = path
    assert summary.classify(d)[0] == "invalid"


@pytest.mark.parametrize(
    "field,value",
    [
        ("generated_at", "not-a-date"),
        ("evidence_updated_at", "2026-10-03"),
        ("producer_revision", "short"),
    ],
)
def test_dates_and_provenance_are_validated(field, value):
    d = fixture_doc("lens_summary_v1.json")
    d[field] = value
    assert summary.classify(d)[0] == "invalid"


def test_unknown_provenance_requires_explanation_not_fabrication():
    d = fixture_doc("lens_summary_v1.json")
    d["producer_revision"] = None
    d.pop("producer_revision_reason", None)
    assert summary.classify(d)[0] == "invalid"
    d["producer_revision_reason"] = "Not recorded by legacy producer"
    assert summary.classify(d)[0] == "ok"


def test_failed_seed_and_partial_pipeline_and_missing_archive_remain_visible():
    d = fixture_doc("lens_summary_v1.json")
    parent = d["records"][0]
    parent.update(pipeline="five-stage", execution={"status": "incomplete", "completed": False})
    stage = deepcopy(parent)
    stage.update(id="failed-stage", parent_run_id=parent["id"], stage="source_pix[1]", seed=1)
    stage["execution"]["status"] = "failed"
    stage["diagnostics"] = {
        "status": "missing",
        "values": {},
        "reason": "Job failed before diagnostics",
    }
    stage["samples"] = {
        "availability": "missing",
        "path": None,
        "reason": "Job failed before archive",
    }
    d["records"].append(stage)
    assert summary.classify(d) == ("ok", [])
    assert len(d["records"]) == 2 and summary.qualified_records(d) == 0
    stage["parent_run_id"] = "absent-parent"
    assert summary.classify(d)[0] == "invalid"


@pytest.mark.parametrize(
    "field,value",
    [
        ("target", "changed-target"),
        ("seed", 42),
        ("dataset", {"id": "changed"}),
        ("model", "changed-model"),
        ("stage", "different-stage"),
    ],
)
def test_changed_scientific_identity_refuses_comparison(field, value):
    d = fixture_doc("lens_summary_v1.json")
    a = d["records"][0]
    b = deepcopy(a)
    b["id"] = "second"
    b[field] = value
    d["records"].append(b)
    c = {"id": "pair", "records": [a["id"], b["id"]], "protocol": "fixed target parity"}
    d["comparisons"] = [c]
    assert summary.classify(d) == ("ok", [])
    assert any(field in reason for reason in summary.comparison_refusals(d, c))


def test_comparison_requires_real_endpoints_and_protocol():
    d = fixture_doc("lens_summary_v1.json")
    d["comparisons"] = [{"id": "pair", "records": ["missing", "also-missing"], "protocol": ""}]
    assert summary.classify(d)[0] == "invalid"


@pytest.mark.parametrize("value", [None, 123])
def test_exclusions_bad_type_returns_validation_error(value):
    d = fixture_doc("lens_summary_v1.json")
    d["coverage"]["excluded"] = value
    assert summary.classify(d)[0] == "invalid"


def test_producer_exclusion_path_shape_and_path_safety():
    d = fixture_doc("lens_summary_v1.json")
    d["coverage"]["excluded"] = [
        {"path": "results/broken.json", "reason": "Invalid source", "status": "invalid"}
    ]
    assert summary.classify(d) == ("ok", [])
    d["coverage"]["excluded"][0]["path"] = "../outside.json"
    assert summary.classify(d)[0] == "invalid"


@pytest.mark.parametrize("field,value", [("target", {})])
def test_record_target_and_optional_source_commit(field, value):
    d = fixture_doc("lens_summary_v1.json")
    d["records"][0][field] = value
    assert summary.classify(d)[0] == "invalid"


def test_completed_flag_is_boolean_when_present():
    d = fixture_doc("lens_summary_v1.json")
    d["records"][0]["execution"]["completed"] = "yes"
    assert summary.classify(d)[0] == "invalid"


def test_unknown_dataset_refuses_comparison_even_when_both_unknown():
    d = fixture_doc("lens_summary_v1.json")
    a = d["records"][0]
    a["dataset"]["id"] = None
    b = deepcopy(a)
    b["id"] = "second"
    d["records"].append(b)
    c = {"id": "pair", "records": [a["id"], b["id"]], "protocol": "parity"}
    assert any("dataset" in r for r in summary.comparison_refusals(d, c))


def test_optional_envelope_source_commit_is_full_sha():
    d = fixture_doc("lens_summary_v1.json")
    d["source_commit"] = "short"
    assert summary.classify(d)[0] == "invalid"
