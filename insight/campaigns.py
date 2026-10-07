"""Human-maintained inference intent; never infer scientific outcomes from timings."""

from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import yaml

from insight import ORGAN_ROOT
from insight.theme import theme

URL = "https://github.com/PyAutoLabs/PyAutoInsight/blob/main/"
STATUSES = {
    "active",
    "ready",
    "running",
    "blocked",
    "parked",
    "needs-decision",
    "needs-slicing",
    "complete",
    "superseded",
}
CLOSED = {"complete", "superseded"}
PROMPT = (
    "Use PyAutoInsight as the home for inference work in this ongoing chat. Read "
    "PyAutoInsight/AGENTS.md and CHECKIN.md, then the campaign ledger, relevant tasks and "
    "registered project evidence. Use the existing Brain samplers faculty when advice on "
    "sampler coverage or selection would help, and project-owned drivers for execution.\n\n"
    "When I give no particular direction, review every open campaign and task for changes "
    "since the last check-in: results, jobs, PRs, releases, blockers and recorded next steps. "
    "Give me a concise campaign-by-campaign summary and a proposed priority order. "
    "Distinguish verified updates from stale, missing or unavailable evidence.\n\n"
    "When I name a campaign, sampler, result or idea, make that the main focus. Help me "
    "inspect diagnostics, understand an unsuccessful run, compare inference methods, identify "
    "missing evidence, design a benchmark or develop a new campaign. Bring in related work "
    "where useful; do not repeat the full campaign review on every follow-up.\n\n"
    "Assess comparisons against the campaign’s stated objectives and acceptance criteria. "
    "Consider convergence, sampling quality, agreement with reference results, robustness and "
    "computational cost where relevant. Make differences in models, priors, datasets, "
    "hardware, precision, stopping rules and resource budgets explicit. Do not rank "
    "incompatible runs or treat speed alone as success.\n\n"
    "Discuss proposed experiments with me, explaining what they would establish and the "
    "resources they need. Help turn agreed direction into concrete campaign tasks. Keep "
    "inference intent and pending domain work in Insight, execution and raw results in "
    "project repositories, scientific observations and my conclusions in Cortex, and bounded "
    "implementation work in Mind.\n\n"
    "Update the Insight ledger with verified facts and dated source links, regenerate the "
    "board and persist changes through the repository workflow. Keep review dates separate "
    "from evidence freshness. Distinguish completed execution from scientific acceptance, and "
    "proposed interpretations from conclusions I have accepted.\n\n"
    "Carry clearly authorized work through the appropriate procedure, retaining decisions and "
    "approvals already given in this conversation. Launch compute or change defaults, "
    "baselines or campaign direction only when authorized; a general check-in does not "
    "authorize those actions.\n\n"
    "After taking action, report what changed, what the evidence supports and what remains "
    "unresolved. Continue subsequent inference work in this chat and stop at the session "
    "deliverable without scheduling background follow-up."
)


class CampaignError(ValueError):
    """The control-room ledger is invalid or incomplete."""


def load(root: Path = ORGAN_ROOT) -> dict:
    root = Path(root)
    path = root / "campaigns.yaml"
    if not path.is_file():
        raise CampaignError(f"{path}: missing campaign ledger")
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise CampaignError(str(exc)) from exc
    if not isinstance(data, dict) or data.get("version") != 1:
        raise CampaignError("campaign ledger must have version 1")
    for kind in ("campaigns", "tasks"):
        rows = data.get(kind)
        if not isinstance(rows, list):
            raise CampaignError(f"{kind} must be a list")
        seen = set()
        for row in rows:
            if not isinstance(row, dict):
                raise CampaignError(f"{kind}: expected a mapping")
            for field in ("id", "title", "status", "updated", "next"):
                if not isinstance(row.get(field), str) or not row[field].strip():
                    raise CampaignError(f"{kind}: missing text {field}")
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", row["id"]) or row["id"] in seen:
                raise CampaignError(f"{kind}: invalid/duplicate id {row['id']}")
            seen.add(row["id"])
            try:
                date.fromisoformat(row["updated"])
            except ValueError as exc:
                raise CampaignError(f"{row['id']}: invalid review date") from exc
            if row["status"] not in STATUSES:
                raise CampaignError(f"{row['id']}: unknown status")
            for field in ("evidence", "issue"):
                if field in row and (
                    not isinstance(row[field], str)
                    or urlparse(row[field]).scheme != "https"
                    or not urlparse(row[field]).netloc
                ):
                    raise CampaignError(f"{row['id']}: {field} must be an HTTPS URL")
    ids = {c["id"] for c in data["campaigns"]}
    for task in data["tasks"]:
        if task.get("campaign") not in ids:
            raise CampaignError(f"{task['id']}: unknown campaign")
        relative = task.get("path", "")
        if not isinstance(relative, str):
            raise CampaignError(f"{task['id']}: task path must be text")
        path = root / relative
        if (
            not isinstance(relative, str)
            or not relative.startswith("tasks/")
            or not path.resolve().is_relative_to((root / "tasks").resolve())
            or not path.is_file()
        ):
            raise CampaignError(f"{task['id']}: missing or unsafe task path")
    stamp = data.get("last_checkin")
    if stamp is not None:
        from insight.summary import parse_utc

        if parse_utc(stamp) is None:
            raise CampaignError("last_checkin must be UTC or null")
        report = data.get("last_checkin_report", "")
        if not isinstance(report, str):
            raise CampaignError("last_checkin_report must be text")
        target = root / report
        if (
            not report.startswith("checkins/")
            or not target.resolve().is_relative_to((root / "checkins").resolve())
            or not target.is_file()
        ):
            raise CampaignError("last_checkin requires durable report")
    return data


def marker(data: dict) -> str:
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    return f"<!-- insight-campaigns:{digest} -->"


def _md(value) -> str:
    return html.escape(str(value)).replace("|", "\\|").replace("\n", " ")


def markdown(data: dict) -> str:
    rows = [
        marker(data),
        "## Check in on all inference work",
        "",
        "Copy this into one chat. Add a campaign focus or idea before or after it, or leave it unchanged.",
        "",
        "```text",
        PROMPT,
        "```",
        "",
        f"Last check-in: {data.get('last_checkin') or 'not recorded yet'}. Ledger dates are review dates, not measurement freshness.",
        "",
        "## Active campaigns",
        "",
        "| Campaign | Status | Open tasks | Recent progress | Blockers | Job status | Next step | Reviewed |",
        "|---|---|---:|---|---|---|---|---|",
    ]
    for c in data["campaigns"]:
        if c["status"] in CLOSED:
            continue
        n = sum(t["campaign"] == c["id"] and t["status"] not in CLOSED for t in data["tasks"])
        title = f"[{_md(c['title'])}]({c['evidence']})" if c.get("evidence") else _md(c["title"])
        rows.append(
            f"| {title} | {c['status']} | {n} | {_md(c.get('recent_progress', 'unknown'))} | {_md(c.get('blockers', 'unknown'))} | {_md(c.get('job_status', 'unknown'))} | {_md(c['next'])} | {c['updated']} |"
        )
    rows += [
        "",
        "## Active tasks",
        "",
        "| Task | Campaign | Status | Priority | Next step |",
        "|---|---|---|---|---|",
    ]
    for t in data["tasks"]:
        if t["status"] not in CLOSED:
            rows.append(
                f"| [{_md(t['title'])}]({URL}{t['path']}) | {t['campaign']} | {t['status']} | {_md(t.get('priority', 'normal'))} | {_md(t['next'])} |"
            )
    rows += [
        "",
        "[Ledger](" + URL + "campaigns.yaml)",
        "",
        "## Inference evidence",
        "",
    ]
    return "\n".join(rows)


def render_html(data: dict, work_links=()) -> str:
    def e(value):
        return html.escape(str(value), quote=True)

    campaigns = []
    for c in data["campaigns"]:
        if c["status"] in CLOSED:
            continue
        n = sum(t["campaign"] == c["id"] and t["status"] not in CLOSED for t in data["tasks"])
        title = (
            f'<a href="{e(c["evidence"])}">{e(c["title"])}</a>'
            if c.get("evidence")
            else e(c["title"])
        )
        campaigns.append(
            f"<tr><td>{title}</td><td>{e(c['status'])}</td><td>{n}</td><td>{e(c.get('recent_progress', 'unknown'))}</td><td>{e(c.get('blockers', 'unknown'))}</td><td>{e(c.get('job_status', 'unknown'))}</td><td>{e(c['next'])}</td><td>{e(c['updated'])}</td></tr>"
        )
    tasks = []
    for t in data["tasks"]:
        if t["status"] in CLOSED:
            continue
        issue = f' · <a href="{e(t["issue"])}">issue</a>' if t.get("issue") else ""
        tasks.append(
            f'<tr><td><a href="{URL}{e(t["path"])}">{e(t["title"])}</a>{issue}</td><td>{e(t["campaign"])}</td><td>{e(t["status"])}</td><td>{e(t.get("priority", "normal"))}</td><td>{e(t["next"])}</td></tr>'
        )

    def table(headers, rows):
        return (
            '<div class="tablewrap"><table><thead><tr>'
            + "".join(f"<th>{h}</th>" for h in headers)
            + "</tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table></div>"
        )

    return (
        marker(data)
        + theme().orchestration_panel(
            "insight", "", "", PROMPT, work_links=work_links, organ="insight"
        )
        + f'<p class="muted">Last check-in: {e(data.get("last_checkin") or "not recorded yet")}.</p>'
        '<h2 id="campaigns">Active campaigns</h2>'
        + table(
            [
                "Campaign",
                "Status",
                "Open tasks",
                "Recent progress",
                "Blockers",
                "Job status",
                "Next step",
                "Reviewed",
            ],
            campaigns,
        )
        + '<h2 id="tasks">Active tasks</h2>'
        + table(["Task", "Campaign", "Status", "Priority", "Next step"], tasks)
        + f'<p><a href="{URL}campaigns.yaml">Ledger</a></p><h2 id="evidence">Inference evidence</h2>'
    )


def validate_migration(root=ORGAN_ROOT):
    root = Path(root)
    try:
        data = yaml.safe_load((root / "migration.yaml").read_text())
    except (OSError, yaml.YAMLError) as exc:
        raise CampaignError(f"migration cannot be read: {exc}") from exc
    if (
        not isinstance(data, dict)
        or data.get("version") != 1
        or not isinstance(data.get("tasks"), list)
    ):
        raise CampaignError("migration requires version 1 and tasks list")
    seen = set()
    for row in data.get("tasks", []):
        if not isinstance(row, dict) or not isinstance(row.get("destination"), str):
            raise CampaignError("migration destination must be text")
        dest = row["destination"]
        path = root / dest
        if (
            dest in seen
            or not dest.startswith("tasks/")
            or not path.resolve().is_relative_to((root / "tasks").resolve())
        ):
            raise CampaignError("unsafe or duplicate migration destination")
        seen.add(dest)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row.get("sha256"):
            raise CampaignError(f"migration original changed: {dest}")
    return data
