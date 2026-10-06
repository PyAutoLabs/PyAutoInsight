"""Ledger/migration integrity and actual editable-copy JavaScript behavior."""

import copy
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from insight import board, campaigns
from insight.theme import theme


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
def test_checkin_copies_complete_shared_preview_or_selects_manual_fallback(mode):
    node = os.environ.get("CODEX_PRIMARY_RUNTIME_NODE") or shutil.which("node")
    if not node:
        pytest.fail("Node runtime required to verify actual copy behavior")
    harness = r"""
const assert=require('node:assert/strict');
let callback,copied=null,focused=false,selected=false;
let field={value:'',defaultValue:'BASE\n\nWork on GitHub:\n- Trusted: https://github.com/example/work',focus(){focused=true},select(){selected=true}};
let status={textContent:''},details={open:false},direction={value:'focus seed 4\nUnicode α'};
let mode=MODE;
let panel={querySelector(s){return s==='[data-orchestration-prompt]'?field:s==='[data-orchestration-direction]'?direction:s==='[data-orchestration-preview]'?details:status}};
let button={closest(){return panel}};
global.document={addEventListener(event,cb){if(event==='click')callback=cb},execCommand(){if(mode==='failed-fallback'||mode==='rejected')return false;copied=field.value;return true}};
global.guardPrompt=()=>true;
Object.defineProperty(global,'navigator',{value:{clipboard:{async writeText(t){if(mode!=='clipboard')throw Error('denied');copied=t}}},configurable:true});
SCRIPT
(async()=>{await callback({target:{closest(){return button}}});assert.ok(field.value.startsWith(field.defaultValue));assert.ok(field.value.endsWith(direction.value));if(mode==='rejected'||mode==='failed-fallback'){assert.equal(copied,null);assert.ok(focused&&selected&&details.open);assert.match(status.textContent,/copy it manually/)}else{assert.equal(copied,field.value);assert.match(status.textContent,/Prompt copied/);if(mode==='fallback')assert.ok(focused&&selected&&details.open)}})().catch(e=>{console.error(e);process.exitCode=1});
""".replace("MODE", json.dumps(mode)).replace("SCRIPT", theme().ORCHESTRATION_JS)
    subprocess.run([node, "-e", harness], check=True, capture_output=True, text=True)


def test_shared_panel_keeps_owner_prompt_and_all_trusted_destinations():
    import html
    import re

    links = [
        {"label": "First project", "href": "https://github.com/example/first"},
        {"label": "Second project", "href": "https://github.com/example/second"},
    ]
    page = campaigns.render_html(campaigns.load(), work_links=links)
    preview = html.unescape(
        re.search(r'data-orchestration-prompt readonly rows="8">(.*?)</textarea>', page, re.S)[1]
    )
    assert preview.startswith(campaigns.PROMPT + "\n\nWork on GitHub:\n")
    for link in links:
        assert f"- {link['label']}: {link['href']}" in preview
    assert page.count("data-orchestration-panel") == 1
    assert "data-orchestration-direction" in page
    assert "orchestrationSync" in board.render_html([])
