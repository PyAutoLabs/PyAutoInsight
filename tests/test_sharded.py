"""inference-summary@3: record shards, sha256-verified, refreshed shard by shard."""

import copy
import hashlib
import json

import pytest
import yaml
from conftest import LENS_ROW, SHA_A, SHA_B, fixture_doc

from insight import board, ingest, registry, summary

GH = "PyAutoLabs/autolens_inference"
PATH = "dashboard/summary.json"


def shard_text(project, sid, protocol, records):
    head = {
        "schema": summary.SHARD_SCHEMA,
        "version": 3,
        "project": project,
        "shard": sid,
        "protocol_id": protocol,
        "records": records,
    }
    return json.dumps(head, sort_keys=True).encode()


def make_v3(records_per_shard=(1, 2), tweak=None):
    """``(index, {shard path: bytes})`` from the v1 lens fixture's record."""
    v1 = fixture_doc("lens_summary_v1.json")
    (base,) = v1["records"]
    index = {k: v for k, v in v1.items() if k != "records"}
    index["version"] = 3
    entries, files, n = [], {}, 0
    for i, count in enumerate(records_per_shard):
        protocol = f"proto@{i + 1}"
        recs = []
        for _ in range(count):
            r = copy.deepcopy(base)
            r["id"] = f"{base['id']}#{n}"
            r["scientific"]["protocol_id"] = protocol
            n += 1
            recs.append(r)
        path = f"records/{protocol}/leg{i}.json"
        body = shard_text(index["project"], f"{protocol}/leg{i}", protocol, recs)
        files[path] = body
        entries.append(
            {
                "id": f"{protocol}/leg{i}",
                "protocol_id": protocol,
                "path": path,
                "records": count,
                "sha256": hashlib.sha256(body).hexdigest(),
            }
        )
    index["record_shards"] = entries
    if tweak:
        tweak(index, files)
    return index, files


def publish(web, sha, index, files):
    web.publish(GH, sha, PATH, index)
    for path, body in files.items():
        web.files[(GH, sha, f"dashboard/{path}")] = body


@pytest.fixture
def lens3(tmp_path, fake_mind):
    path = tmp_path / "registry3.yaml"
    row = dict(LENS_ROW, supported_schema="inference-summary@3")
    path.write_text(yaml.safe_dump({"schema": 1, "instances": [row]}))
    return registry.get(registry.load(path, mind=fake_mind), "lens")


def test_assembled_v3_validates_like_v1():
    index, files = make_v3()
    doc, errors = summary.load_sharded(index, files.__getitem__)
    assert errors == [] and len(doc["records"]) == 3
    assert summary.classify(doc, ("inference-summary", 3)) == ("ok", [])
    assert "records" not in summary.index_of(doc)
    # the index alone is not a summary: its records live in the shards
    assert summary.classify(index, ("inference-summary", 3))[0] == "invalid"


@pytest.mark.parametrize(
    "tweak, needle",
    [
        (lambda i, f: f.update({"records/proto@1/leg0.json": b"{}"}), "sha256 differs"),
        (lambda i, f: i["record_shards"][1].update(records=5), "index declares 5"),
        (lambda i, f: i["record_shards"][1].update(path="../x.json"), "unsafe"),
        (lambda i, f: i["record_shards"][1].update(id="proto@1/leg0"), "duplicate record shard"),
        (lambda i, f: i.update(records=[]), "never inline"),
    ],
)
def test_shard_problems_are_refused(tweak, needle):
    index, files = make_v3(tweak=tweak)
    doc, errors = summary.load_sharded(index, files.__getitem__)
    assert doc is None and any(needle in e for e in errors), errors


def test_a_record_naming_another_protocol_is_refused():
    index, files = make_v3()
    path = "records/proto@2/leg1.json"
    shard = json.loads(files[path])
    shard["records"][0]["scientific"]["protocol_id"] = "proto@1"
    files[path] = json.dumps(shard).encode()
    index["record_shards"][1]["sha256"] = hashlib.sha256(files[path]).hexdigest()
    doc, errors = summary.load_sharded(index, files.__getitem__)
    assert doc is None and "not the shard's" in errors[0]


def test_ingest_keeps_shards_and_refetches_only_what_changed(lens3, web, tmp_path):
    index, files = make_v3()
    publish(web, SHA_A, index, files)
    s = ingest.ingest(lens3, tmp_path, now="2026-10-02T00:00:00Z")
    assert s.outcome == "ok" and len(s.doc["records"]) == 3 and s.shards_fetched == 2
    kept = ingest.shard_dir(tmp_path, "lens")
    assert sorted(p.relative_to(kept).as_posix() for p in kept.rglob("*.json")) == sorted(files)
    snap = ingest.read_snapshot(tmp_path, "lens")
    assert "records" not in snap["summary"] and snap["summary"]["record_shards"]
    receipt = ingest.read_receipt(tmp_path, "lens")
    assert receipt["record_count"] == 3 and receipt["record_shards"] == 2

    # a new commit that changes one shard and drops the other: one fetch, one removal
    def change(i, f):
        body = shard_text(
            i["project"],
            "proto@2/leg1",
            "proto@2",
            json.loads(f["records/proto@2/leg1.json"])["records"][:1],
        )
        f["records/proto@2/leg1.json"] = body
        i["record_shards"][1].update(records=1, sha256=hashlib.sha256(body).hexdigest())

    index2, files2 = make_v3(tweak=change)
    publish(web, SHA_B, index2, files2)
    web.requests.clear()
    s = ingest.ingest(lens3, tmp_path, now="2026-10-03T00:00:00Z")
    assert s.outcome == "ok" and s.shards_fetched == 1 and len(s.doc["records"]) == 2
    raw = [r.full_url for r in web.requests if "raw.githubusercontent" in r.full_url]
    assert raw[-1].endswith("/dashboard/records/proto@2/leg1.json")

    del index2["record_shards"][0]
    publish(web, SHA_A, index2, {"records/proto@2/leg1.json": files2["records/proto@2/leg1.json"]})
    s = ingest.ingest(lens3, tmp_path, now="2026-10-04T00:00:00Z")
    assert s.outcome == "ok" and s.shards_fetched == 0
    assert not (kept / "records/proto@1/leg0.json").exists()
    assert not (kept / "records/proto@1").exists()

    offline = ingest.ingest(lens3, tmp_path, offline=True)
    assert offline.outcome == "ok" and len(offline.doc["records"]) == 1


def test_a_failed_shard_keeps_the_whole_last_good_capture(lens3, web, tmp_path):
    index, files = make_v3()
    publish(web, SHA_A, index, files)
    ingest.ingest(lens3, tmp_path, now="2026-10-02T00:00:00Z")
    before = {p: p.read_bytes() for p in ingest.shard_dir(tmp_path, "lens").rglob("*.json")}
    bad_index, bad_files = make_v3(records_per_shard=(2, 2))
    bad_files["records/proto@2/leg1.json"] = b"tampered"
    publish(web, SHA_B, bad_index, bad_files)
    s = ingest.ingest(lens3, tmp_path, now="2026-10-03T00:00:00Z")
    assert s.outcome == "invalid" and s.cached and s.commit == SHA_A
    after = {p: p.read_bytes() for p in ingest.shard_dir(tmp_path, "lens").rglob("*.json")}
    assert after == before


def test_a_missing_shard_is_unavailable(lens3, web, tmp_path):
    index, files = make_v3()
    files.pop("records/proto@2/leg1.json")
    publish(web, SHA_A, index, files)
    s = ingest.ingest(lens3, tmp_path, now="2026-10-02T00:00:00Z")
    assert s.outcome == "unavailable" and s.doc is None


def test_offline_detects_a_corrupted_kept_shard(lens3, web, tmp_path):
    index, files = make_v3()
    publish(web, SHA_A, index, files)
    ingest.ingest(lens3, tmp_path, now="2026-10-02T00:00:00Z")
    (ingest.shard_dir(tmp_path, "lens") / "records/proto@1/leg0.json").write_text("{}")
    s = ingest.ingest(lens3, tmp_path, offline=True)
    assert s.outcome == "invalid" and "sha256" in s.errors[0]


def test_a_local_read_assembles_shards_beside_the_index(lens3, tmp_path):
    index, files = make_v3()
    checkout = tmp_path / "autolens_inference"
    (checkout / "dashboard").mkdir(parents=True)
    (checkout / PATH).write_text(json.dumps(index))
    for path, body in files.items():
        (checkout / "dashboard" / path).parent.mkdir(parents=True, exist_ok=True)
        (checkout / "dashboard" / path).write_bytes(body)
    s = ingest.ingest(lens3, tmp_path / "organ", local_path=checkout)
    assert s.outcome == "ok" and s.source == "local" and len(s.doc["records"]) == 3


def test_migrating_from_keeps_an_older_capture_valid_until_refreshed(tmp_path, fake_mind, web):
    v1_reg = tmp_path / "r1.yaml"
    v1_reg.write_text(yaml.safe_dump({"schema": 1, "instances": [dict(LENS_ROW)]}))
    (old,) = registry.load(v1_reg, mind=fake_mind)
    web.publish(GH, SHA_A, PATH, fixture_doc("lens_summary_v1.json"))
    ingest.ingest(old, tmp_path, now="2026-10-02T00:00:00Z")
    row = dict(LENS_ROW, supported_schema="inference-summary@3")
    strict, moving = tmp_path / "r3.yaml", tmp_path / "r3m.yaml"
    strict.write_text(yaml.safe_dump({"schema": 1, "instances": [row]}))
    moving.write_text(
        yaml.safe_dump(
            {"schema": 1, "instances": [dict(row, migrating_from="inference-summary@1")]}
        )
    )
    (pinned,) = registry.load(strict, mind=fake_mind)
    assert ingest.ingest(pinned, tmp_path, offline=True).outcome == "invalid"
    (migrating,) = registry.load(moving, mind=fake_mind)
    s = ingest.ingest(migrating, tmp_path, offline=True)
    assert s.outcome == "ok" and "awaiting the first refresh" in s.migrating
    # a fresh fetch must return the pinned schema: the old capture is shown cached
    s = ingest.ingest(migrating, tmp_path, now="2026-10-03T00:00:00Z")
    assert s.outcome == "unsupported" and s.cached
    index, files = make_v3()
    publish(web, SHA_B, index, files)
    s = ingest.ingest(migrating, tmp_path, now="2026-10-04T00:00:00Z")
    assert s.outcome == "ok" and s.migrating is None and s.commit == SHA_B


@pytest.mark.parametrize(
    "value", ["inference-summary@3", "inference-summary@4", "other@1", "nonsense"]
)
def test_migrating_from_must_be_an_older_version_of_the_pin(body_map, value):
    row = dict(LENS_ROW, supported_schema="inference-summary@3", migrating_from=value)
    problems = registry.validate({"schema": 1, "instances": [row]}, body_map)
    assert any("migrating_from" in p for p in problems)


def test_board_lists_shards_not_every_record(lens3, web, tmp_path):
    index, files = make_v3()
    publish(web, SHA_A, index, files)
    s = ingest.ingest(lens3, tmp_path, now="2026-10-02T00:00:00Z")
    page = board.render_html([s], campaign_data={"campaigns": [], "tasks": []})
    text = board.render_markdown([s], campaign_data={"campaigns": [], "tasks": []})
    for out in (page, text):
        assert "proto@1/leg0" in out and "proto@2/leg1" in out
        assert "Provenance:" not in out
    assert "dashboard/records/proto%402/leg1.json" in text  # blob URL, quoted at the commit
    assert board.render_state([s])["headline"].startswith("1 projects · 3 records")
