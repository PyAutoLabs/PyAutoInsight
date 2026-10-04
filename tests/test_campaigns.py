"""Ledger/migration integrity and actual editable-copy JavaScript behavior."""

import copy
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from insight import campaigns
from insight.theme import JS


def copied_ledger(tmp_path):
    root = Path(campaigns.ORGAN_ROOT)
    for file in ["campaigns.yaml", "migration.yaml"]:
        shutil.copy(root / file, tmp_path / file)
    shutil.copytree(root / "tasks", tmp_path / "tasks")
    return yaml.safe_load((tmp_path / "campaigns.yaml").read_text())


def test_current_ledger_and_migration_validate():
    data = campaigns.load()
    migration = campaigns.validate_migration()
    assert len(data["campaigns"]) >= 8 and len(migration["tasks"]) >= 6
    assert data["last_checkin"] is None
    assert any(c["status"] == "blocked" for c in data["campaigns"])
    assert any(c["status"] == "needs-decision" for c in data["campaigns"])
    assert all(c["job_status"].startswith("unknown") for c in data["campaigns"])


@pytest.mark.parametrize(
    "change", ["duplicate", "unknown-campaign", "path-traversal", "invalid-date"]
)
def test_invalid_ledgers_are_rejected(tmp_path, change):
    data = copied_ledger(tmp_path)
    if change == "duplicate":
        data["campaigns"].append(copy.deepcopy(data["campaigns"][0]))
    if change == "unknown-campaign":
        data["tasks"][0]["campaign"] = "missing"
    if change == "path-traversal":
        data["tasks"][0]["path"] = "tasks/../campaigns.yaml"
    if change == "invalid-date":
        data["campaigns"][0]["updated"] = "not-a-date"
    (tmp_path / "campaigns.yaml").write_text(yaml.safe_dump(data))
    with pytest.raises(campaigns.CampaignError):
        campaigns.load(tmp_path)


def test_migration_rejects_changed_original_bytes(tmp_path):
    copied_ledger(tmp_path)
    migration = yaml.safe_load((tmp_path / "migration.yaml").read_text())
    target = tmp_path / migration["tasks"][0]["destination"]
    target.write_text(target.read_text() + "altered")
    with pytest.raises(campaigns.CampaignError, match="original changed"):
        campaigns.validate_migration(tmp_path)


def test_closed_tasks_hidden_but_parked_stays_visible():
    data = copy.deepcopy(campaigns.load())
    task = data["tasks"][0]
    task["title"] = "UNIQUE_PARKED_TASK"
    task["status"] = "parked"
    assert "UNIQUE_PARKED_TASK" in campaigns.render_html(data)
    task["status"] = "complete"
    assert "UNIQUE_PARKED_TASK" not in campaigns.render_html(data)


@pytest.mark.parametrize("mode", ["clipboard", "fallback", "rejected", "failed-fallback"])
def test_copy_button_copies_edited_text_or_selects_manual_fallback(mode):
    node = os.environ.get("CODEX_PRIMARY_RUNTIME_NODE") or shutil.which("node")
    if not node:
        pytest.fail("Node runtime required to verify actual copy behavior")
    harness = r"""
const assert=require('node:assert/strict');
let callback,copied=null,focused=false,selected=false;
let field={value:'USER EDITED: focus seed 4',focus(){focused=true},select(){selected=true}};
let status={textContent:''};
let mode=MODE;
global.document={getElementById(id){return id==='copy-checkin'?{addEventListener(_,cb){callback=cb}}:id==='checkin-prompt'?field:status},querySelectorAll(){return []},execCommand(command){assert.equal(command,'copy');if(mode==='failed-fallback')return false;copied=field.value;return true}};
global.window={isSecureContext:mode!=='fallback'&&mode!=='failed-fallback'};
Object.defineProperty(global,'navigator',{value:{clipboard:{async writeText(t){if(mode==='rejected')throw Error('denied');copied=t}}},configurable:true});
SCRIPT
(async()=>{await callback(); if(mode==='rejected'||mode==='failed-fallback'){assert.equal(copied,null);assert.ok(focused&&selected);assert.match(status.textContent,/Select and copy/)}else{assert.equal(copied,field.value);assert.equal(status.textContent,'Copied')}})().catch(e=>{console.error(e);process.exitCode=1});
""".replace("MODE", json.dumps(mode)).replace("SCRIPT", JS)
    subprocess.run([node, "-e", harness], check=True, capture_output=True, text=True)
