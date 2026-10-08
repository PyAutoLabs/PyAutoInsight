"""Server-rendered setup pages with progressive navigation and pinned evidence."""

from __future__ import annotations

import html
import json
from collections import defaultdict
from urllib.parse import urlencode

from insight import ORGAN_ROOT, summary


def e(value):
    return html.escape("unknown" if value is None else str(value), quote=True)


def disclosure(title, content, *, opened=False):
    return f"<details{' open' if opened else ''}><summary>{e(title)}</summary>{content}</details>"


def link(snapshot, path, label="Original evidence"):
    if not summary.safe_relative_path(path):
        return ""
    return f'<a href="{e(snapshot.instance.blob_url(snapshot.commit, path))}">{e(label)}</a>'


def route(instance, setup):
    return "?" + urlencode({"view": "setup", "instance": instance, "setup": setup})


def metrics(items):
    return (
        '<dl class="setup-metrics">'
        + "".join(f"<div><dt>{e(label)}</dt><dd>{e(value)}</dd></div>" for label, value in items)
        + "</dl>"
    )


def seconds(value):
    if value is None:
        return "unknown"
    return f"{value:,.3g} s" if value < 60 else f"{value / 60:,.3g} min ({value:,.3g} s)"


def record(snapshot, row):
    init = row.get("initialization", {})
    env = row.get("environment", {})
    timing = row["timings"]
    work = row.get("work", {})
    heading = " · ".join(
        str(x)
        for x in (
            row.get("stage") or "single search / pipeline parent",
            init.get("mode", "unknown start"),
            row.get("backend") or "unknown backend",
            f"seed {row.get('seed')}",
            "archived" if row["archived"] else row["execution"]["status"],
        )
    )
    body = metrics(
        [
            ("Sampling", seconds(timing["sampling_s"])),
            ("Fit call", seconds(timing["total_s"])),
            ("Preparation", seconds(timing.get("preparation_s"))),
            ("Initialization", seconds(timing.get("initialization_s"))),
            ("Compilation", seconds(timing["compile_s"])),
            ("Likelihood evaluations", work.get("likelihood_evaluations")),
            ("Sampler iterations", work.get("iterations")),
            ("ESS", work.get("effective_sample_size")),
            ("Free parameters", row["configuration"].get("free_parameters")),
            ("Maximum log likelihood", row["diagnostics"]["values"].get("max_log_likelihood")),
        ]
    )
    body += f"<p>Convergence: {e(row['scientific']['convergence'])} · acceptance: {e(row['scientific']['acceptance'])}. Samples: {e(row['samples']['availability'])}.</p>"
    body += f"<p>Sampler start: {e(init.get('mode'))} · compilation: {e(env.get('compilation'))} · cache: {e(env.get('cache'))}. Hardware: {e(env.get('hardware_id'))}.</p>"
    body += "<p>" + " · ".join(link(snapshot, p) for p in row["evidence_paths"]) + "</p>"
    body += disclosure(
        "Configuration, clock definitions and provenance",
        "<pre>" + e(json.dumps(row, indent=2)) + "</pre>",
    )
    return disclosure(heading, body)


def page(snapshot, setup, rows, now=None):
    from insight.board import freshness, integrity, qualification

    doc = snapshot.doc
    sid = setup["id"]
    ref = next((r for r in rows if r["id"] == setup.get("reference_record_id")), None)
    baseline_ids = {
        p["baseline_record_id"]
        for p in doc["prepared_problems"]
        if p["setup_id"] == sid and p.get("baseline_record_id")
    }
    out = [
        f'<details class="setup-page" data-instance="{e(snapshot.instance.instance)}" data-setup="{e(sid)}">',
        f'<summary>{e(setup["label"])}</summary><a href="?">← All inference setups</a>',
        f"<h1>{e(setup['label'])}</h1>",
        f"<p>{e(snapshot.instance.repo.removesuffix('_inference'))} / {e(setup['dataset_family'])} / {e(setup['model_family'])} · {e(setup.get('instrument'))}</p>",
        f'<p class="muted">Captured revision {e(snapshot.commit)} · evidence {e(doc.get("evidence_updated_at"))} · {"cached evidence" if snapshot.cached else e(snapshot.outcome)}.</p>',
    ]
    out.append(
        f"<p><b>Integrity:</b> {e(integrity(snapshot))} · <b>Freshness:</b> {e(freshness(snapshot, now))} · <b>Scientific qualification:</b> {e(qualification(snapshot))}</p>"
    )
    out.append(
        f"<p>Capture time: {e(snapshot.fetched_at)} · latest attempt: {e(snapshot.attempt_at)} · branch: {e(snapshot.source_branch)}.</p>"
    )
    if snapshot.errors:
        out.append('<p class="warn">' + e("; ".join(snapshot.errors)) + "</p>")
    if snapshot.cached:
        out.append(
            '<p class="warn">Cached evidence: original capture and evidence times retained. This refresh has not made the evidence newer.</p>'
        )
    if snapshot.source == "local":
        out.append(
            f'<p class="warn">Local preview, not a published capture. No receipt written. Dirty checkout: {e(snapshot.dirty)}.</p>'
        )
    if ref:
        out += [
            "<h3>Accepted baseline</h3>",
            metrics(
                [
                    ("Sampler / stage", f"{ref['sampler']} / {ref['stage'] or 'single search'}"),
                    ("Start", ref["initialization"]["mode"]),
                    ("Hardware", ref["environment"]["hardware_id"]),
                    ("Backend / precision", f"{ref['backend']} / {ref['precision']}"),
                    ("Sampling", seconds(ref["timings"]["sampling_s"])),
                    ("Fit call", seconds(ref["timings"]["total_s"])),
                    ("Likelihood evaluations", ref["work"]["likelihood_evaluations"]),
                    ("Sampler iterations", ref["work"]["iterations"]),
                    ("Free parameters", ref["configuration"].get("free_parameters")),
                    (
                        "Maximum log likelihood",
                        ref["diagnostics"]["values"].get("max_log_likelihood"),
                    ),
                ]
            ),
            "<p>Recorded baseline measurement; applicability and seed coverage must be checked before estimating a new fit.</p>",
        ]
    else:
        out += [
            "<h3>No accepted baseline selected</h3>",
            f"<p>{e(setup.get('reference_record_id_reason'))}</p>",
        ]
    image = setup.get("image_path")
    if (
        image
        and summary.safe_relative_path(image)
        and snapshot.commit
        and snapshot.source == "remote"
    ):
        from urllib.parse import quote

        url = f"https://raw.githubusercontent.com/{snapshot.instance.github}/{snapshot.commit}/{quote(image, safe='/')}"
        out.append(
            f'<figure><img class="setup-image" src="{e(url)}" alt="{e(setup["label"])} dataset and model" loading="lazy"></figure>'
        )
    baseline = [r for r in rows if r["id"] in baseline_ids]
    out.append(
        disclosure(
            "Baseline runs and prepared problems",
            "".join(record(snapshot, r) for r in baseline)
            + "<pre>"
            + e(json.dumps([p for p in doc["prepared_problems"] if p["setup_id"] == sid], indent=2))
            + "</pre>",
        )
    )
    samplers = defaultdict(list)
    for row in rows:
        if not row["archived"]:
            samplers[row["sampler"] or "Sampler unknown"].append(row)
    out.append("<h3>Sampler results</h3>")
    if not samplers:
        out.append("<p>No current sampler measurements for this setup.</p>")
    for sampler, group in sorted(samplers.items()):
        out.append(
            disclosure(
                f"{sampler} · {len(group)} records", "".join(record(snapshot, r) for r in group)
            )
        )
    history = [r for r in rows if r["archived"]]
    out.append(
        disclosure(
            f"Historical project results · {len(history)} records",
            "".join(record(snapshot, r) for r in history) or "<p>No historical results.</p>",
        )
    )
    ids = {r["id"] for r in rows}
    groups = [c for c in doc["comparisons"] if set(c["records"]).issubset(ids)]
    comparisons = ""
    for c in groups:
        reasons = summary.comparison_refusals(doc, c)
        comparisons += f"<p>{e(c['id'])}: {e('refused: ' + '; '.join(reasons) if reasons else 'producer-declared protocol ' + c['protocol'])}</p>"
    out.append(
        disclosure(
            "Comparisons and parity groups",
            comparisons or "<p>No comparison groups supplied for this setup.</p>",
        )
    )
    out.append(
        disclosure(
            "Coverage and limitations",
            "<pre>"
            + e(json.dumps(doc["coverage"], indent=2))
            + "</pre><ul>"
            + "".join(f"<li>{e(x)}</li>" for x in doc["limitations"])
            + "</ul>",
        )
    )
    out.append("</details>")
    return "".join(out)


def render(snapshot, now=None):
    """Return project navigation and separate setup detail markup."""
    doc = snapshot.doc or {}
    if doc.get("version") != 2:
        return "", ""
    project = snapshot.instance.repo.removesuffix("_inference")
    families = defaultdict(list)
    for setup in doc["setups"]:
        families[setup["dataset_family"]].append(setup)
    choices, pages = [], []
    for family, setups in sorted(families.items()):
        links = []
        for setup in sorted(setups, key=lambda s: (s["model_family"], s["label"])):
            label = f"{setup['model_family']} · {setup.get('instrument') or 'instrument unspecified'} · {setup['label']}"
            links.append(
                f'<a class="setup-choice" href="{e(route(snapshot.instance.instance, setup["id"]))}" target="_blank" rel="noopener">{e(label)} ↗<span class="sr-only"> (opens in a new tab)</span></a>'
            )
            pages.append(
                page(
                    snapshot,
                    setup,
                    [r for r in doc["records"] if r.get("setup_id") == setup["id"]],
                    now,
                )
            )
        choices.append(
            disclosure(family, '<div class="setup-choices">' + "".join(links) + "</div>")
        )
    unmapped = [r for r in doc["records"] if r.get("setup_id") is None]
    if unmapped:
        choices.append(
            disclosure(
                f"Unmapped historical evidence · {len(unmapped)} records",
                "".join(record(snapshot, r) for r in unmapped),
            )
        )
    if not doc["records"]:
        choices.append("<p>No measurements. Declared setups may still be explored.</p>")
    return disclosure(project, "".join(choices)), "".join(pages)


def assets():
    return (
        (ORGAN_ROOT / "insight/setup_browser.css").read_text(),
        (ORGAN_ROOT / "insight/setup_browser.js").read_text(),
    )
