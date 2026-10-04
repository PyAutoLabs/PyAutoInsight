"""One-commit ingest, receipts, last-good snapshots and cached semantics."""

import json
import subprocess

import pytest
from conftest import SHA_A, SHA_B, fixture_doc

from insight import ingest, registry

GH = "PyAutoLabs/autolens_inference"
PATH = "dashboard/summary.json"


@pytest.fixture
def lens(registry_file, fake_mind):
    return registry.get(registry.load(registry_file, mind=fake_mind), "lens")


def test_ok_reads_the_file_at_the_resolved_commit(lens, web, tmp_path, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "t0k")
    web.publish(GH, SHA_A, PATH, fixture_doc("lens_summary_v1.json"))
    s = ingest.ingest(lens, tmp_path, now="2026-10-02T00:00:00Z")
    assert s.outcome == "ok" and not s.cached and s.commit == SHA_A
    api, raw = (r.full_url for r in web.requests)
    assert api == f"https://api.github.com/repos/{GH}/commits/main"
    assert raw == f"https://raw.githubusercontent.com/{GH}/{SHA_A}/{PATH}"
    assert web.requests[0].get_header("Authorization") == "Bearer t0k"
    assert web.requests[1].get_header("Authorization") is None  # the token never leaves the API
    assert web.requests[0].get_header("User-agent") == ingest.USER_AGENT
    receipt = ingest.read_receipt(tmp_path, "lens")
    assert receipt["resolved_commit"] == SHA_A and receipt["outcome"] == "ok"
    assert receipt["record_count"] == 1 and receipt["errors"] == []
    assert receipt["cached_from"] is None
    snap = ingest.read_snapshot(tmp_path, "lens")
    assert snap["commit"] == SHA_A and snap["fetched_at"] == "2026-10-02T00:00:00Z"


def test_unchanged_reingest_rewrites_nothing(lens, web, tmp_path):
    web.publish(GH, SHA_A, PATH, fixture_doc("lens_summary_v1.json"))
    ingest.ingest(lens, tmp_path, now="2026-10-02T00:00:00Z")
    before = {p: p.read_bytes() for p in tmp_path.glob("*s/lens.json")}
    ingest.ingest(lens, tmp_path, now="2026-10-03T00:00:00Z")
    assert {p: p.read_bytes() for p in tmp_path.glob("*s/lens.json")} == before
    web.publish(GH, SHA_B, PATH, fixture_doc("lens_summary_v1.json"))
    s = ingest.ingest(lens, tmp_path, now="2026-10-04T00:00:00Z")
    assert s.commit == SHA_B and s.fetched_at == "2026-10-04T00:00:00Z"


def test_unavailable_keeps_the_cached_snapshot_with_its_original_times(lens, web, tmp_path):
    web.publish(GH, SHA_A, PATH, fixture_doc("lens_summary_v1.json"))
    good = ingest.ingest(lens, tmp_path, now="2026-10-02T00:00:00Z")
    web.down = True
    s = ingest.ingest(lens, tmp_path, now="2026-10-09T00:00:00Z")
    assert s.outcome == "unavailable" and s.cached
    assert s.commit == SHA_A and s.fetched_at == "2026-10-02T00:00:00Z"
    assert s.doc["evidence_updated_at"] == good.doc["evidence_updated_at"]
    assert "connection reset" in s.errors[0]
    receipt = ingest.read_receipt(tmp_path, "lens")
    assert receipt["outcome"] == "unavailable" and receipt["resolved_commit"] is None
    assert receipt["fetched_at"] == "2026-10-09T00:00:00Z"
    assert receipt["cached_from"] == "2026-10-02T00:00:00Z"


def test_unavailable_with_no_snapshot_has_nothing_to_show(lens, tmp_path):
    s = ingest.ingest(lens, tmp_path, now="2026-10-02T00:00:00Z")  # no_network refuses
    assert s.outcome == "unavailable" and s.doc is None and not s.cached
    assert ingest.read_snapshot(tmp_path, "lens") is None


@pytest.mark.parametrize(
    "fixture, outcome",
    [("unsupported_schema.json", "unsupported"), ("duplicate_id.json", "invalid")],
)
def test_bad_feeds_fail_and_keep_the_last_good_snapshot(lens, web, tmp_path, fixture, outcome):
    web.publish(GH, SHA_A, PATH, fixture_doc("lens_summary_v1.json"))
    ingest.ingest(lens, tmp_path, now="2026-10-02T00:00:00Z")
    web.publish(GH, SHA_B, PATH, fixture_doc(fixture))
    s = ingest.ingest(lens, tmp_path, now="2026-10-03T00:00:00Z")
    assert s.outcome == outcome and s.cached
    assert s.commit == SHA_A and s.attempt_commit == SHA_B
    assert ingest.read_snapshot(tmp_path, "lens")["commit"] == SHA_A


def test_not_json_is_invalid(lens, web, tmp_path):
    web.publish(GH, SHA_A, PATH, b"<html>404</html>")
    s = ingest.ingest(lens, tmp_path, now="2026-10-02T00:00:00Z")
    assert s.outcome == "invalid" and "not JSON" in s.errors[0]


def test_offline_reads_committed_files_and_writes_nothing(lens, web, tmp_path):
    web.publish(GH, SHA_A, PATH, fixture_doc("lens_summary_v1.json"))
    ingest.ingest(lens, tmp_path, now="2026-10-02T00:00:00Z")
    web.requests.clear()
    s = ingest.ingest(lens, tmp_path, offline=True)
    assert s.outcome == "ok" and s.commit == SHA_A and web.requests == []


def test_a_local_read_reports_revision_and_dirty_state_and_writes_nothing(lens, tmp_path):
    checkout = tmp_path / "autolens_inference"
    (checkout / "dashboard").mkdir(parents=True)
    (checkout / PATH).write_text(json.dumps(fixture_doc("valid_empty.json")))
    git = ["git", "-C", str(checkout), "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", "."], check=True)
    subprocess.run([*git, "commit", "-qm", "x"], check=True)
    out = tmp_path / "organ"
    s = ingest.ingest(lens, out, local_path=checkout)
    assert s.source == "local" and s.dirty is False and len(s.commit) == 40
    (checkout / "scratch.txt").write_text("edit")
    assert ingest.ingest(lens, out, local_path=checkout).dirty is True
    assert not (out / "receipts").exists() and not (out / "snapshots").exists()


def test_project_identity_mismatch_is_invalid(lens, web, tmp_path):
    web.publish(GH, SHA_A, PATH, fixture_doc("galaxy_summary_v1.json"))
    s = ingest.ingest(lens, tmp_path)
    assert s.outcome == "invalid" and s.doc is None


def test_second_producer_uses_same_reader(two_registry_file, fake_mind, web, tmp_path):
    instances = registry.load(two_registry_file, mind=fake_mind)
    web.publish(GH, SHA_A, PATH, fixture_doc("lens_summary_v1.json"))
    web.publish(
        "PyAutoLabs/autogalaxy_inference",
        SHA_B,
        "out/inference_summary.json",
        fixture_doc("galaxy_summary_v1.json"),
    )
    views = [ingest.ingest(i, tmp_path) for i in instances]
    assert [s.outcome for s in views] == ["ok", "ok"]
    assert [s.doc["project"] for s in views] == ["autolens_inference", "autogalaxy_inference"]
    assert len(list((tmp_path / "receipts").glob("*.json"))) == 2


def test_offline_rejects_corrupt_snapshot_identity(lens, web, tmp_path):
    web.publish(GH, SHA_A, PATH, fixture_doc("lens_summary_v1.json"))
    ingest.ingest(lens, tmp_path)
    path = tmp_path / "snapshots/lens.json"
    d = json.loads(path.read_text())
    d["summary"]["project"] = "other_project"
    path.write_text(json.dumps(d))
    s = ingest.ingest(lens, tmp_path, offline=True)
    assert s.outcome == "invalid" and s.doc is None
