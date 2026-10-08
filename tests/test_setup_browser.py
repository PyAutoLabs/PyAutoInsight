"""Setup navigation keeps evidence scoped, qualified and escaped."""

from copy import deepcopy
from pathlib import Path

import pytest
from test_board import view

from insight import board, candidates, setup_browser


def test_setup_links_open_new_tab_and_have_no_script_interpolation(registry_file, fake_mind):
    snapshot = view(registry_file, fake_mind, "lens_summary_v2.json")
    snapshot.doc["setups"][0]["label"] = '<script>alert("unsafe")</script>'
    nav, pages = setup_browser.render(snapshot)
    assert 'target="_blank" rel="noopener"' in nav
    assert "view=setup&amp;instance=lens&amp;setup=imaging%2Fdelaunay%2Fhst" in nav
    assert "<script>alert" not in pages
    assert "&lt;script&gt;" in pages
    assert "No accepted baseline selected" in pages


def test_pages_only_contain_their_own_records_and_comparisons(registry_file, fake_mind):
    snapshot = view(registry_file, fake_mind, "lens_summary_v2.json")
    other = deepcopy(snapshot.doc["setups"][0])
    other.update(id="other", label="Other setup")
    snapshot.doc["setups"].append(other)
    rows = [r for r in snapshot.doc["records"] if r["setup_id"] == other["id"]]
    rendered = setup_browser.page(snapshot, other, rows)
    assert "baseline-mass" not in rendered
    assert "cold-pair" not in rendered
    assert "No current sampler measurements" in rendered


def test_unknown_bindings_and_archives_stay_accessible(registry_file, fake_mind):
    snapshot = view(registry_file, fake_mind, "lens_summary_v2.json")
    snapshot.doc["records"][0].update(setup_id=None, archived=True)
    nav, _ = setup_browser.render(snapshot)
    assert "Unmapped historical evidence" in nav and "baseline-mass" in nav


def test_headline_uses_only_selected_reference(registry_file, fake_mind):
    snapshot = view(registry_file, fake_mind, "lens_summary_v2.json")
    setup = snapshot.doc["setups"][0]
    setup["reference_record_id"] = "baseline-mass"
    snapshot.doc["records"][0]["scientific"]["acceptance"] = "accepted"
    _, pages = setup_browser.render(snapshot)
    assert "Accepted baseline" in pages and "Maximum log likelihood" in pages
    assert "Recorded baseline measurement" in pages


def test_candidate_data_changes_invalidate_board_digest(registry_file, fake_mind, monkeypatch):
    snapshot = view(registry_file, fake_mind)
    before = board.input_marker([snapshot], {})
    data = candidates.load()
    data[0]["reviewed_at"] = "2026-10-09"
    monkeypatch.setattr(candidates, "load", lambda: data)
    assert board.input_marker([snapshot], {}) != before


@pytest.mark.parametrize(
    "key,value",
    [
        ("paper_url", "javascript:alert(1)"),
        ("code_url", "//evil"),
        ("expected_uses", "not a list"),
        ("reviewed_at", "not a date"),
    ],
)
def test_invalid_candidate_feed_fails_closed(tmp_path, key, value):
    import json

    data = candidates.load()
    data[0][key] = value
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        candidates.load(path)


def test_assets_and_candidate_copy_use_live_editable_value():
    css, js = setup_browser.assets()
    assert "text.value" in js
    assert "text.select()" in js
    assert "[hidden]" in css
    assert Path(setup_browser.ORGAN_ROOT / "sampler_candidates.json").exists()


def test_direct_page_retains_failed_refresh_and_local_preview_qualifications(
    registry_file, fake_mind
):
    snapshot = view(registry_file, fake_mind, "lens_summary_v2.json")
    snapshot.cached = True
    snapshot.errors = ["latest refresh failed <network>"]
    snapshot.doc["valid_until"] = "2026-01-01T00:00:00Z"
    _, pages = setup_browser.render(snapshot, now="2026-10-08T00:00:00Z")
    assert "stale · deadline" in pages
    assert "Freshness:" in pages and "Integrity:" in pages
    assert "latest refresh failed &lt;network&gt;" in pages
    assert "original capture and evidence times retained" in pages
    snapshot.source = "local"
    snapshot.dirty = True
    _, pages = setup_browser.render(snapshot)
    assert "Local preview, not a published capture" in pages
    assert "Dirty checkout: True" in pages


def test_likelihood_choices_group_instruments_and_keep_implementations_separate(
    registry_file, fake_mind
):
    snapshot = view(registry_file, fake_mind, "lens_summary_v2.json")
    setup = deepcopy(snapshot.doc["setups"][0])
    setup.update(id="imaging/delaunay/euclid", instrument="euclid")
    snapshot.doc["setups"].append(setup)
    nav, pages = setup_browser.render(snapshot)
    assert nav.count('class="model-choice setup-choice"') == 2
    assert "PyAutoLens" in nav and ">Imaging<" in nav
    assert "Delaunay (Numba)" in nav
    assert "EUCLID" in pages
    row = snapshot.doc["records"][0]
    assert setup_browser.implementation(row) == "jax"
    assert setup_browser.implementation({"backend": None}) == "unknown"
    assert setup_browser.implementation({"backend": "jax_unrecognized"}) == "unknown"
    assert setup_browser.implementation({"backend": "numba_cpu"}) == "numba"
    original = snapshot.doc["setups"][0]
    original["reference_record_id"] = row["id"]
    numba = setup_browser.page(snapshot, original, [], impl="numba", instruments=[original, setup])
    assert "<h3>Accepted baseline</h3>" not in numba
    assert row["id"] not in numba
    assert "No recorded Delaunay (Numba) results" in numba


def test_home_keeps_actionable_warnings_outside_collapsed_provenance(registry_file, fake_mind):
    snapshot = view(registry_file, fake_mind, "lens_summary_v2.json")
    snapshot.cached = True
    snapshot.errors = ["transport error"]
    snapshot.doc["valid_until"] = "2026-01-01T00:00:00Z"
    detail = board._detail(snapshot, "2026-10-08T00:00:00Z")
    prefix = detail.split("<details>")[0]
    assert "Showing cached evidence" in prefix
    assert "past its declared freshness" in prefix
    assert "Integrity:" not in prefix
    assert '<h2 id="lens">' not in detail
