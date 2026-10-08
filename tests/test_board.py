"""Reproducibility, honesty, and the single editable control-room entry point."""

import json
from pathlib import Path

from conftest import fixture_doc

from insight import board, campaigns, ingest, registry


def view(registry_file, fake_mind, name="lens_summary_v1.json"):
    inst = registry.load(registry_file, mind=fake_mind)[0]
    return ingest.Snapshot(
        inst,
        "ok",
        "remote",
        doc=fixture_doc(name),
        commit="a" * 40,
        fetched_at="2026-10-04T00:00:00Z",
        refreshed_at="2026-10-04T00:00:00Z",
    )


def test_controlroom_order_and_domain_labels(registry_file, fake_mind):
    s = view(registry_file, fake_mind)
    html = board.render_html([s], now="2026-10-04T00:00:00Z")
    assert (
        html.index('id="orchestration-insight-prompt"')
        < html.index('id="campaigns"')
        < html.index('id="tasks"')
        < html.index('id="evidence"')
    )
    assert "Inference Results" in html
    assert "Profiling evidence" not in html
    assert "Recent progress" in html and "Next steps" in html
    assert "<th>Blockers</th>" not in html and "<th>Job status</th>" not in html
    assert "Last check-in: not recorded yet" not in html


def test_cached_stale_evidence_keeps_age_and_separate_qualification(registry_file, fake_mind):
    s = view(registry_file, fake_mind)
    s.cached = True
    s.outcome = "unavailable"
    s.doc["evidence_updated_at"] = "2026-09-01T00:00:00Z"
    s.doc["valid_until"] = "2026-09-02T00:00:00Z"
    assert "cached" in board.integrity(s)
    assert "stale" in board.freshness(s, "2026-10-04T00:00:00Z")
    assert "0/1 accepted" in board.qualification(s)
    assert board.render_state([s], now="2026-10-04T00:00:00Z")["status"] == "yellow"
    assert (
        s.fetched_at == "2026-10-04T00:00:00Z"
        and s.doc["evidence_updated_at"] == "2026-09-01T00:00:00Z"
    )


def test_empty_and_unavailable_do_not_become_green(registry_file, fake_mind):
    s = view(registry_file, fake_mind, "valid_empty.json")
    assert board.render_state([s])["status"] == "yellow"
    assert "No measurements" in board.render_html([s])
    s.doc = None
    s.outcome = "unavailable"
    assert board.render_state([s])["status"] == "red"


def test_repeat_render_is_byte_identical_and_does_not_stamp_checkin(
    tmp_path, registry_file, fake_mind
):
    s = view(registry_file, fake_mind)
    ledger = Path(campaigns.ORGAN_ROOT) / "campaigns.yaml"
    before = ledger.read_bytes()
    board.write([s], tmp_path, now="2026-10-04T00:00:00Z")
    files = {p.name: p.read_bytes() for p in tmp_path.glob("*") if p.is_file()}
    board.write([s], tmp_path, now="2026-10-04T00:00:00Z")
    assert {p.name: p.read_bytes() for p in tmp_path.glob("*") if p.is_file()} == files
    assert ledger.read_bytes() == before
    assert json.loads((tmp_path / "state.json").read_text())["organ"] == "insight"


def test_render_respects_supplied_clock_for_freshness(registry_file, fake_mind):
    s = view(registry_file, fake_mind)
    s.doc["evidence_updated_at"] = "2020-01-01T00:00:00Z"
    s.doc["valid_until"] = "2020-01-03T00:00:00Z"
    assert "valid · deadline" in board.render_html([s], now="2020-01-02T00:00:00Z")
    assert "stale · deadline" in board.render_html([s], now="2020-01-04T00:00:00Z")


def test_capture_freshness_is_conservative(registry_file, fake_mind):
    s = view(registry_file, fake_mind)
    html = board.render_html([s])
    assert 'data-refreshed-at="' + s.refreshed_at + '"' in html
    assert (
        "https://github.com/PyAutoLabs/PyAutoInsight/actions/workflows/dashboard_refresh.yml"
        in html
    )
    s.outcome = "unavailable"
    s.cached = True
    assert "Last updated unavailable" in board.render_html([s])
    s.outcome = "ok"
    s.refreshed_at = None
    assert "Last updated unavailable" in board.render_html([s])
