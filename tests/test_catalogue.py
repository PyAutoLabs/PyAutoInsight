"""Prepared scientific problems survive migration without invented start state."""

from copy import deepcopy
from dataclasses import replace

import pytest
from conftest import LENS_ROW, SHA_A, SHA_B, fixture_doc

from insight import ingest, registry, summary


def document():
    return fixture_doc("lens_summary_v2.json")


def test_baseline_cold_warm_and_resume_are_valid_but_not_automatically_accepted():
    doc = document()
    assert summary.classify(doc) == ("ok", [])
    assert summary.qualified_records(doc) == 0
    assert summary.comparison_refusals(doc, doc["comparisons"][0]) == []
    assert doc["records"][0]["timings"]["initialization_s"] is None


@pytest.mark.parametrize("version", [True, 0, 3, "2", None])
def test_unsupported_versions(version):
    doc = document()
    doc["version"] = version
    assert summary.classify(doc)[0] == "unsupported"


def test_registry_pins_exact_version_and_old_feed_remains_valid(body_map):
    row = dict(LENS_ROW, supported_schema="inference-summary@2")
    assert registry.validate({"schema": 1, "instances": [row]}, body_map) == []
    assert summary.classify(document(), ("inference-summary", 1))[0] == "unsupported"
    assert summary.classify(document(), ("inference-summary", 2)) == ("ok", [])
    assert summary.classify(fixture_doc("lens_summary_v1.json")) == ("ok", [])


@pytest.mark.parametrize("key", ["setups", "prepared_problems"])
@pytest.mark.parametrize("value", [None, {}, "wrong", [None], [{"id": []}]])
def test_bad_catalogue_shapes_return_errors(key, value):
    doc = document()
    doc[key] = value
    assert summary.classify(doc)[0] == "invalid"


@pytest.mark.parametrize("key", ["setups", "prepared_problems"])
def test_duplicate_id(key):
    doc = document()
    doc[key].append(deepcopy(doc[key][0]))
    assert any("duplicate" in e for e in summary.validate(doc))


@pytest.mark.parametrize(
    "key,value",
    [
        ("setup_id", "absent"),
        ("problem_id", []),
        ("problem_id", "absent"),
        ("stage", "source_pix[1]"),
        ("dataset", {"class": "point_source", "id": "other"}),
    ],
)
def test_wrong_problem_binding(key, value):
    doc = document()
    doc["records"][2][key] = value
    assert summary.classify(doc)[0] == "invalid"


@pytest.mark.parametrize("key", ["model_id", "priors_id", "dataset_id"])
def test_unknown_prepared_identity_remains_explicit(key):
    doc = document()
    doc["prepared_problems"][0][key] = None
    assert summary.classify(doc)[0] == "invalid"


@pytest.mark.parametrize(
    "key,value",
    [
        ("path", "../escape"),
        ("path", "x/%2e%2e/y"),
        ("sha256", "short"),
        ("revision", "main"),
        ("record_id", "absent"),
        ("record_id", []),
    ],
)
def test_prepared_and_initialization_artifact_provenance(key, value):
    for artifacts in ("prepared", "initialization"):
        doc = document()
        artifact = (
            doc["prepared_problems"][0]["artifacts"][0]
            if artifacts == "prepared"
            else doc["records"][3]["initialization"]["sources"][0]
        )
        artifact[key] = value
        assert summary.classify(doc)[0] == "invalid"


def test_cold_does_not_mean_no_adapt_images_but_cannot_reuse_posterior():
    doc = document()
    assert doc["prepared_problems"][0]["artifacts"]
    doc["records"][2]["initialization"]["sources"] = doc["records"][3]["initialization"]["sources"]
    assert any("cold initialization" in e for e in summary.validate(doc))


@pytest.mark.parametrize("index", [3, 4])
def test_warm_and_resume_require_source(index):
    doc = document()
    doc["records"][index]["initialization"]["sources"] = []
    assert summary.classify(doc)[0] == "invalid"


def test_resume_requires_checkpoint_and_source_cannot_be_self():
    doc = document()
    source = doc["records"][4]["initialization"]["sources"][0]
    source["kind"] = "posterior_samples"
    assert any("checkpoint" in e for e in summary.validate(doc))
    source["kind"] = "checkpoint"
    source["record_id"] = "experiment-resume"
    assert summary.classify(doc)[0] == "invalid"


@pytest.mark.parametrize("field", ["initialization", "environment", "work"])
@pytest.mark.parametrize("value", [None, [], 7])
def test_malformed_run_conditions(field, value):
    doc = document()
    doc["records"][0][field] = value
    assert summary.classify(doc)[0] == "invalid"


def test_archive_and_unreviewed_baselines_are_retained_but_not_selected():
    doc = document()
    doc["records"][0]["archived"] = True
    assert summary.classify(doc) == ("ok", [])
    doc["setups"][0]["reference_record_id"] = "baseline-mass"
    assert summary.classify(doc)[0] == "invalid"
    doc["records"][0]["archived"] = False
    assert summary.classify(doc)[0] == "invalid"
    doc["records"][0]["scientific"]["acceptance"] = "accepted"
    assert summary.classify(doc) == ("ok", [])


@pytest.mark.parametrize(
    "key,value",
    [("initialization_s", -1), ("preparation_s", True), ("initialization_s", float("nan"))],
)
def test_new_clocks_are_nonnegative_seconds(key, value):
    doc = document()
    doc["records"][0]["timings"][key] = value
    assert summary.classify(doc)[0] == "invalid"


@pytest.mark.parametrize(
    "key,value",
    [
        ("iterations", 1.5),
        ("retained_samples", True),
        ("effective_sample_size", -1),
        ("likelihood_evaluations", float("inf")),
    ],
)
def test_work_counts_do_not_conflate_iterations_samples_and_ess(key, value):
    doc = document()
    doc["records"][0]["work"][key] = value
    assert summary.classify(doc)[0] == "invalid"


@pytest.mark.parametrize("other", ["experiment-warm", "experiment-resume"])
def test_different_starts_refuse_cost_comparison(other):
    doc = document()
    pair = dict(doc["comparisons"][0], records=["experiment-cold", other])
    assert any("initialization" in e for e in summary.comparison_refusals(doc, pair))


@pytest.mark.parametrize(
    "key,value", [("hardware_id", "a100-host"), ("compilation", "warm"), ("cache", "warm")]
)
def test_sampler_cold_start_is_separate_from_environment(key, value):
    doc = document()
    doc["records"][2]["environment"][key] = value
    assert summary.classify(doc) == ("ok", [])
    assert "environment differs" in summary.comparison_refusals(doc, doc["comparisons"][0])


def test_v2_ingest_cache_and_offline_replay(registry_file, fake_mind, web, tmp_path):
    instance = replace(
        registry.load(registry_file, mind=fake_mind)[0], supported_schema="inference-summary@2"
    )
    doc = document()
    web.publish(instance.github, SHA_A, instance.summary_path, doc)
    good = ingest.ingest(instance, tmp_path, now="2026-10-08T00:00:00Z")
    assert good.outcome == "ok" and good.doc == doc
    doc["records"][3]["initialization"]["sources"] = []
    web.publish(instance.github, SHA_B, instance.summary_path, doc)
    bad = ingest.ingest(instance, tmp_path, now="2026-10-08T01:00:00Z")
    assert bad.outcome == "invalid" and bad.cached and bad.commit == SHA_A
    replay = ingest.ingest(instance, tmp_path, offline=True)
    assert replay.doc == good.doc


def test_cycle_of_initialization_sources_is_invalid():
    doc = document()
    doc["records"][3]["initialization"]["sources"][0]["record_id"] = "experiment-resume"
    assert "initialization source cycle" in summary.validate(doc)


def test_unknown_start_is_retained_and_never_compared_as_cold():
    doc = document()
    for row in (doc["records"][0], doc["records"][2]):
        row["initialization"].update(
            mode="unknown", reason="Legacy source did not record initialization"
        )
        row["environment"].update(compilation="unknown", compilation_reason="Not recorded")
    assert summary.classify(doc) == ("ok", [])
    reasons = summary.comparison_refusals(doc, doc["comparisons"][0])
    assert any("initialization" in r for r in reasons)
    assert any("compilation" in r for r in reasons)


@pytest.mark.parametrize("key", ["model_id", "priors_id"])
def test_unknown_problem_identity_is_visible_but_never_a_comparison(key):
    doc = document()
    doc["prepared_problems"][0].update({key: None, key + "_reason": "Legacy metadata absent"})
    assert summary.classify(doc) == ("ok", [])
    assert f"prepared {key} unknown" in summary.comparison_refusals(doc, doc["comparisons"][0])


@pytest.mark.parametrize("key", ["dependency_revisions", "precision", "experiment_protocol"])
def test_changed_run_controls_refuse_comparison(key):
    doc = document()
    doc["records"][2][key] = (
        {"PyAutoLens": "b" * 40} if key == "dependency_revisions" else "changed"
    )
    assert summary.classify(doc) == ("ok", [])
    assert f"{key} changed" in summary.comparison_refusals(doc, doc["comparisons"][0])


@pytest.mark.parametrize("key", ["scientific", "execution", "diagnostics"])
@pytest.mark.parametrize("value", [None, [], 5])
def test_malformed_selected_reference_does_not_raise(key, value):
    doc = document()
    doc["setups"][0]["reference_record_id"] = "baseline-mass"
    doc["records"][0]["scientific"]["acceptance"] = "accepted"
    doc["records"][0][key] = value
    assert summary.classify(doc)[0] == "invalid"


def test_selected_reference_needs_likelihood_and_parameters():
    doc = document()
    doc["setups"][0]["reference_record_id"] = "baseline-mass"
    doc["records"][0]["scientific"]["acceptance"] = "accepted"
    doc["records"][0]["diagnostics"]["values"] = {}
    assert any("maximum likelihood" in e for e in summary.validate(doc))


def test_v2_empty_and_unmapped_legacy_records_are_valid():
    doc = document()
    doc["setups"] = []
    doc["prepared_problems"] = []
    doc["comparisons"] = []
    row = doc["records"][0]
    doc["records"] = [row]
    row.update(
        setup_id=None,
        setup_id_reason="Unmapped legacy source",
        problem_id=None,
        problem_id_reason="Prepared state unavailable",
        archived=True,
    )
    assert summary.classify(doc) == ("ok", [])
    doc["records"] = []
    assert summary.classify(doc) == ("ok", [])
