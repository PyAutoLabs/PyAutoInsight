"""Offline check catches stale evidence and registry/receipt mismatch."""

import json

from conftest import SHA_A, SHA_B, fixture_doc

from insight import cli, ingest, registry


def test_offline_roundtrip_and_stale_dashboard_detection(tmp_path, registry_file, fake_mind, web):
    inst = registry.load(registry_file, mind=fake_mind)[0]
    web.publish(inst.github, SHA_A, inst.summary_path, fixture_doc("lens_summary_v1.json"))
    ingest.ingest(inst, tmp_path, now="2026-10-04T00:00:00Z")
    base = ["--registry", str(registry_file)]
    flags = ["--mind", str(fake_mind), "--out", str(tmp_path), "--offline"]
    assert cli.main([*base, "board", *flags]) == 0
    assert cli.main([*base, "check", *flags]) == 0
    web.publish(inst.github, SHA_B, inst.summary_path, fixture_doc("lens_summary_v1.json"))
    ingest.ingest(inst, tmp_path, now="2026-10-05T00:00:00Z")
    assert cli.main([*base, "check", *flags]) == 1
    assert cli.main([*base, "board", *flags]) == 0
    assert cli.main([*base, "check", *flags]) == 0


def test_check_rejects_receipt_revision_different_from_snapshot(
    tmp_path, registry_file, fake_mind, web
):
    inst = registry.load(registry_file, mind=fake_mind)[0]
    web.publish(inst.github, SHA_A, inst.summary_path, fixture_doc("lens_summary_v1.json"))
    ingest.ingest(inst, tmp_path, now="2026-10-04T00:00:00Z")
    base = ["--registry", str(registry_file)]
    flags = ["--mind", str(fake_mind), "--out", str(tmp_path), "--offline"]
    assert cli.main([*base, "board", *flags]) == 0
    path = tmp_path / "receipts/lens.json"
    doc = json.loads(path.read_text())
    doc["resolved_commit"] = SHA_B
    path.write_text(json.dumps(doc))
    assert cli.main([*base, "check", *flags]) == 1
