"""Reproducible inference evidence view, separate from scientific conclusions."""

from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from insight import ORGAN_ROOT, campaigns, summary
from insight.theme import CSS, JS, theme

PAGES_URL = "https://pyautolabs.github.io/PyAutoInsight/"
REPO_URL = "https://github.com/PyAutoLabs/PyAutoInsight"
MARKER = re.compile(r"<!-- insight:instance name=(\S+) receipt=(\S+) outcome=(\S+) shown=(\S+) -->")


def _now():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def records(s):
    return (s.doc or {}).get("records", [])


def comparisons(s):
    return (s.doc or {}).get("comparisons", [])


def integrity(s):
    if s.source == "local":
        return f"local checkout {s.commit or 'unknown'} ({'dirty' if s.dirty else 'clean' if s.dirty is False else 'unknown state'})"
    return f"cached · latest fetch {s.outcome}" if s.cached else s.outcome


def freshness(s, now=None):
    d = s.doc or {}
    ev = d.get("evidence_updated_at")
    vu = d.get("valid_until")
    if vu:
        expired = now is not None and summary.parse_utc(now) > summary.parse_utc(vu)
        return f"{'stale' if expired else 'valid'} · deadline {vu}"
    return f"freshness policy unspecified · evidence {ev or 'time unknown'}"


def qualification(s):
    if not records(s):
        return "no measurements"
    return f"{summary.qualified_records(s.doc)}/{len(records(s))} accepted by producer; remaining assessments shown below"


def counts(views):
    return [
        ("Projects", len(views)),
        ("Records", sum(len(records(s)) for s in views)),
        ("Comparisons", sum(len(comparisons(s)) for s in views)),
        ("Cached", sum(s.cached for s in views)),
        ("Failed", sum(s.failed and not s.cached for s in views)),
    ]


def marker(s):
    return f"<!-- insight:instance name={s.instance.instance} receipt={s.attempt_commit or 'none'} outcome={s.outcome} shown={s.commit or 'none'} -->"


def markers(text):
    return {n: {"receipt": r, "outcome": o, "shown": s} for n, r, o, s in MARKER.findall(text)}


def input_marker(views, data):
    body = [
        {
            "instance": vars(s.instance),
            "outcome": s.outcome,
            "source": s.source,
            "doc": s.doc,
            "commit": s.commit,
            "fetched_at": s.fetched_at,
            "errors": s.errors,
            "cached": s.cached,
            "attempt_commit": s.attempt_commit,
            "attempt_at": s.attempt_at,
            "dirty": s.dirty,
            "source_branch": s.source_branch,
        }
        for s in views
    ]
    return (
        "<!-- insight-inputs:"
        + hashlib.sha256(json.dumps([body, data], sort_keys=True).encode()).hexdigest()
        + " -->"
    )


def e(v):
    return html.escape("unknown" if v is None else str(v), quote=True)


def md(v):
    return e(v).replace("|", "\\|").replace("\n", " ")


def _dump(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False)


def table(headers, rows):
    return (
        '<div class="tablewrap"><table><thead><tr>'
        + "".join("<th>" + e(x) + "</th>" for x in headers)
        + "</tr></thead><tbody>"
        + "".join("<tr>" + "".join("<td>" + x + "</td>" for x in row) + "</tr>" for row in rows)
        + "</tbody></table></div>"
    )


def _detail(s, now=None):
    d = s.doc or {}
    inst = s.instance
    parts = [
        marker(s),
        f'<h2 id="{e(inst.instance)}">{e(inst.repo)}</h2>',
        f"<p><b>Integrity:</b> {e(integrity(s))} · <b>Freshness:</b> {e(freshness(s, now))} · <b>Scientific qualification:</b> {e(qualification(s))}</p>",
        f'<p>Captured source branch: {e(s.source_branch)}. Revision: <a href="{e(inst.tree_url(s.commit))}">{e(s.commit)}</a>. Capture time: {e(s.fetched_at)}. Latest attempt: {e(s.attempt_at)}.</p>',
    ]
    if s.errors:
        parts.append('<p class="warn">' + e("; ".join(s.errors)) + "</p>")
    if s.cached:
        parts.append(
            '<p class="warn">Cached evidence: original capture and evidence times retained. This refresh has not made the evidence newer.</p>'
        )
    if s.source == "local":
        parts.append(
            '<p class="warn">Local preview, not a published capture. No receipt written.</p>'
        )
    if not d:
        return "".join(parts)
    parts += [
        f"<p>Scope: {e(d['scope'])}. Producer revision: {e(d.get('producer_revision'))}. Generated: {e(d['generated_at'])}. {e(d.get('generation_basis', 'Producer-declared generation time'))}</p>",
        f'<p><a href="{e(inst.dashboard_url)}">Project dashboard</a> · <a href="{REPO_URL}/blob/main/receipts/{e(inst.instance)}.json">Ingest receipt</a></p>',
        "<h3>Coverage and limitations</h3><pre>"
        + e(_dump(d["coverage"]))
        + "</pre><ul>"
        + "".join("<li>" + e(x) + "</li>" for x in d["limitations"])
        + "</ul>",
    ]
    if not records(s):
        parts.append("<p>No measurements. An empty feed does not mean scientific success.</p>")
    for archived, label in [(False, "Current results"), (True, "Historical project results")]:
        rows = []
        for r in records(s):
            if r["archived"] != archived:
                continue
            paths = " · ".join(
                f'<a href="{e(inst.blob_url(s.commit, p))}">result</a>' for p in r["evidence_paths"]
            )
            rows.append(
                [
                    e(r["target"]),
                    e(r["stage"] or ("pipeline parent" if r["pipeline"] else "single search")),
                    e(r["sampler"]),
                    e(r["configuration"].get("config_name")),
                    e(r["seed"]),
                    e(r["execution"]["status"]),
                    e(r["scientific"]["convergence"]) + " / " + e(r["scientific"]["acceptance"]),
                    e(r["timings"]["sampling_s"]),
                    e(r["timings"]["total_s"]),
                    e(r["diagnostics"]["status"]),
                    e(r["samples"]["availability"]),
                    paths,
                ]
            )
        parts += [
            f"<h3>{label}</h3>",
            table(
                [
                    "Target",
                    "Stage",
                    "Sampler",
                    "Configuration",
                    "Seed",
                    "Execution",
                    "Convergence / acceptance",
                    "Sampler clock (s)",
                    "Fit call (s)",
                    "Diagnostics",
                    "Samples",
                    "Evidence",
                ],
                rows,
            ),
        ]
    parts.append(
        "<h3>Comparisons and parity groups</h3><p>Targets, seeds and stages are retained. No best-seed selection, cross-target ranking or automatic convergence threshold. Declared groups do not themselves certify parity.</p>"
    )
    if not comparisons(s):
        parts.append("<p>No certified comparison pairs supplied by this producer.</p>")
    for c in comparisons(s):
        reasons = summary.comparison_refusals(d, c)
        parts.append(
            "<p>"
            + e(c["id"])
            + ": "
            + e(
                "refused: " + "; ".join(reasons)
                if reasons
                else "producer-declared protocol " + c["protocol"]
            )
            + "</p>"
        )
    parts.append("<h3>Diagnostics, timing definitions and provenance</h3>")
    for r in records(s):
        parts.append("<details><summary>" + e(r["id"]) + "</summary><dl>")
        for k in (
            "parent_run_id",
            "stage",
            "target",
            "dataset",
            "model",
            "pipeline",
            "sampler",
            "configuration",
            "backend",
            "hardware",
            "precision",
            "seed",
            "dependency_revisions",
            "library_version",
            "execution",
            "scientific",
            "timings",
            "diagnostics",
            "comparison",
            "samples",
            "measured_at",
            "unknown_reasons",
        ):
            parts.append("<dt>" + e(k) + "</dt><dd><pre>" + e(_dump(r.get(k))) + "</pre></dd>")
        parts.append("</dl></details>")
    return "".join(parts)


def _captured_at(views):
    """Oldest successful observation of displayed inputs; failed or missing inputs stay unknown.

    Capture time is separate from producer evidence and content-only state.updated.
    """
    if not views or any(v.outcome != "ok" or not v.refreshed_at for v in views):
        return None
    times = [summary.parse_utc(v.refreshed_at) for v in views]
    return min(times) if all(times) else None


def render_html(views, now=None, campaign_data=None):
    data = campaign_data if campaign_data is not None else campaigns.load()
    shared = theme()
    return shared.section_layout(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>PyAutoInsight dashboard</title><style>"
        + shared.css("insight")
        + CSS
        + "pre{white-space:pre-wrap;overflow-wrap:anywhere}details{margin:1rem 0}dd{margin-left:1rem}</style></head><body>"
        + shared.hero(
            "insight",
            "Inference dashboard",
            navigation=[
                {"href": "#campaigns", "label": "Active campaigns"},
                {"href": "#evidence", "label": "Inference evidence"},
                *(
                    {
                        "href": "#" + v.instance.instance,
                        "label": v.instance.instance.title() + " project",
                    }
                    for v in views
                ),
            ],
        )
        + "<main>"
        + input_marker(views, data)
        + campaigns.render_html(
            data,
            refreshed_at=_captured_at(views),
            work_links=[
                {"label": "PyAutoInsight", "href": REPO_URL},
                *({"label": v.instance.repo, "href": v.instance.github_url} for v in views),
            ],
        )
        + "<p>Execution completion is separate from convergence and scientific acceptance. Cortex retains scientific conclusions. Evidence remains in project storage.</p>"
        + "".join(_detail(s, now) for s in views)
        + "</main><script>"
        + shared.JS
        + JS
        + "</script></body></html>\n"
    )


def render_markdown(views, now=None, campaign_data=None):
    data = campaign_data if campaign_data is not None else campaigns.load()
    out = [
        "# PyAutoInsight — inference control room",
        "",
        input_marker(views, data),
        "",
        "| Where | Count |",
        "|---|---:|",
    ]
    out += [f"| [{label}](#evidence) | {n} |" for label, n in counts(views)]
    out += ["", campaigns.markdown(data)]
    for s in views:
        out += [
            "",
            marker(s),
            f"## {s.instance.repo}",
            f"Integrity: {integrity(s)}. Freshness: {freshness(s, now)}. Qualification: {qualification(s)}.",
            f"Capture source branch: {s.source_branch}; revision: {s.commit}; fetched {s.fetched_at}; latest attempt {s.attempt_at}.",
            *s.errors,
        ]
        if s.cached:
            out.append("Cached: original evidence and capture times retained.")
        if not s.doc:
            continue
        out += [
            "",
            "Coverage: " + _dump(s.doc["coverage"]),
            *s.doc["limitations"],
            "",
            "| Target | Stage | Seed | Execution | Convergence | Acceptance | Sampling s | Total s | Archive | Evidence |",
            "|---|---|---|---|---|---|---:|---:|---|---|",
        ]
        for r in records(s):
            path = r["evidence_paths"][0]
            vals = [
                r["target"],
                r["stage"],
                r["seed"],
                r["execution"]["status"],
                r["scientific"]["convergence"],
                r["scientific"]["acceptance"],
                r["timings"]["sampling_s"],
                r["timings"]["total_s"],
                r["archived"],
            ]
            out.append(
                "| "
                + " | ".join(md(v) for v in vals)
                + f" | [result]({s.instance.blob_url(s.commit, path)}) |"
            )
            out += [
                "",
                f"<details><summary>Provenance: {md(r['id'])}</summary>",
                "",
                "```json",
                json.dumps(r, indent=2, ensure_ascii=False),
                "```",
                "",
                "</details>",
                "",
            ]
        for c in comparisons(s):
            out.append(
                f"Comparison {md(c['id'])}: "
                + md(summary.comparison_refusals(s.doc, c) or c["protocol"])
            )
    return "\n".join(out) + "\n"


def render_state(views, updated=None, now=None):
    items = []
    for s in views:
        severity = (
            "red"
            if s.failed and not s.cached
            else "yellow"
            if s.cached or not records(s) or summary.qualified_records(s.doc) < len(records(s))
            else "info"
        )
        if (
            s.doc
            and s.doc.get("valid_until")
            and summary.parse_utc(now or _now()) > summary.parse_utc(s.doc["valid_until"])
        ):
            severity = "yellow" if severity != "red" else severity
        items.append(
            {
                "id": f"insight:{s.instance.instance}",
                "severity": severity,
                "text": f"{s.instance.instance}: {integrity(s)} · {len(records(s))} records · {qualification(s)} · {freshness(s, now)}",
                "url": PAGES_URL + "#" + s.instance.instance,
                "prompt": None,
            }
        )
    status = (
        "red"
        if any(i["severity"] == "red" for i in items)
        else "yellow"
        if not items or any(i["severity"] == "yellow" for i in items)
        else "green"
    )
    return {
        "schema_version": 1,
        "organ": "insight",
        "repo": "PyAutoInsight",
        "status": status,
        "headline": f"{len(views)} projects · {sum(len(records(s)) for s in views)} records · {sum(s.cached for s in views)} cached",
        "updated": updated or _now(),
        "pages_url": PAGES_URL,
        "items": items,
    }


def render_badge(views, state=None):
    state = state or render_state(views)
    return {
        "schemaVersion": 1,
        "label": "insight",
        "message": state["headline"],
        "color": {"red": "red", "yellow": "yellow", "green": "brightgreen"}[state["status"]],
    }


def write(views, out_dir=ORGAN_ROOT, updated=None, now=None):
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    state = render_state(views, updated, now)
    try:
        prior = json.loads((root / "state.json").read_text())
    except (OSError, ValueError):
        prior = {}
    if updated is None and {k: v for k, v in prior.items() if k != "updated"} == {
        k: v for k, v in state.items() if k != "updated"
    }:
        state["updated"] = prior["updated"]
    files = {
        "dashboard.md": render_markdown(views, now),
        "dashboard.html": render_html(views, now),
        "state.json": json.dumps(state, indent=2) + "\n",
        "badge.json": json.dumps(render_badge(views, state), indent=2) + "\n",
    }
    for name, body in files.items():
        (root / name).write_text(body)
    return [root / name for name in files]
