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


def route(instance, setup, implementation=None):
    params = {"view": "setup", "instance": instance, "setup": setup}
    if implementation:
        params["implementation"] = implementation
    return "?" + urlencode(params)


def implementation(row):
    backend = row.get("backend") or ""
    return (
        "numba"
        if backend in {"numba", "numba_cpu"}
        else "jax"
        if backend in {"jax", "jax_cpu", "jax_gpu"}
        else "unknown"
    )


def project_label(snapshot):
    return {"autolens_inference": "PyAutoLens", "autofit_inference": "PyAutoFit"}.get(
        snapshot.instance.repo, snapshot.instance.repo
    )


def model_label(model, impl):
    name = model.replace("_", " ").title()
    return name + (
        " (Numba)"
        if impl == "numba"
        else " (implementation unspecified)"
        if impl == "unknown"
        else ""
    )


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


def page(snapshot, setup, rows, now=None, impl=None, instruments=()):
    from insight.board import freshness, integrity, qualification

    doc = snapshot.doc
    sid = setup["id"]
    ref = next((r for r in rows if r["id"] == setup.get("reference_record_id")), None)
    problem_ids = {row.get("problem_id") for row in rows}
    problems = [
        p
        for p in doc["prepared_problems"]
        if p["setup_id"] == sid and (impl is None or p["id"] in problem_ids)
    ]
    baseline_ids = {p["baseline_record_id"] for p in problems if p.get("baseline_record_id")}
    out = [
        f'<details class="setup-page" data-instance="{e(snapshot.instance.instance)}" data-setup="{e(sid)}" data-implementation="{e(impl or "jax")}">',
        f'<summary>{e(setup["label"])}</summary><a href="?">← All inference setups</a>',
        f"<h1>{e(model_label(setup['model_family'], impl) if impl else setup['label'])}</h1>",
        f"<p>{e(project_label(snapshot))} / {e(setup['dataset_family'].replace('_', ' ').title())}</p>",
    ]
    if instruments:
        options = "".join(
            f'<option value="{e(route(snapshot.instance.instance, item["id"], impl))}"{" selected" if item["id"] == sid else ""}>{e((item.get("instrument") or "unspecified").upper())}</option>'
            for item in instruments
        )
        out.append(
            f'<div class="selectors"><label>Instrument<select data-instrument>{options}</select></label></div>'
        )
    evidence = (
        f"<p>Integrity: {e(integrity(snapshot))} · Freshness: {e(freshness(snapshot, now))} · Scientific qualification: {e(qualification(snapshot))}</p>"
        f"<p>Captured source branch: {e(snapshot.source_branch)}. Revision: {e(snapshot.commit)}. Capture time: {e(snapshot.fetched_at)}. Latest attempt: {e(snapshot.attempt_at)}.</p>"
    )
    if freshness(snapshot, now).startswith("stale"):
        out.append('<p class="warn">This evidence is past its declared freshness deadline.</p>')
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
    if impl and not rows:
        out.append(
            f"<p>No recorded {e(model_label(setup['model_family'], impl))} results for this instrument.</p>"
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
            f"<p>{e(setup.get('reference_record_id_reason') or 'No accepted reference for this implementation and instrument')}</p>",
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
            + e(json.dumps(problems, indent=2))
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
    out.append(disclosure("Evidence details", evidence))
    out.append("</details>")
    return "".join(out)


def render(snapshot, now=None):
    """Return project navigation and separate setup detail markup."""
    doc = snapshot.doc or {}
    if doc.get("version") != 2:
        return "", ""
    families = defaultdict(lambda: defaultdict(list))
    for setup in doc["setups"]:
        families[setup["dataset_family"]][setup["model_family"]].append(setup)
    choices, pages = [], []
    for family, models in sorted(families.items()):
        links = []
        for model, setups in sorted(models.items()):
            setups = sorted(
                setups,
                key=lambda item: (
                    item.get("instrument") != "hst",
                    item.get("instrument") or "",
                    item["id"],
                ),
            )
            ids = {item["id"] for item in setups}
            rows = [row for row in doc["records"] if row.get("setup_id") in ids]
            implementations = {implementation(row) for row in rows} or {"unknown"}
            # These are explicit result filters, not claims of measured support.
            if family == "imaging" and model in {"delaunay", "rectangular"}:
                implementations |= {"jax", "numba"}
            for impl in sorted(implementations):
                label = model_label(model, impl)
                links.append(
                    f'<a class="model-choice setup-choice" href="{e(route(snapshot.instance.instance, setups[0]["id"], impl))}" target="_blank" rel="noopener">{e(label)}<span class="sr-only"> (opens in a new tab)</span></a>'
                )
                for setup in setups:
                    selected = [
                        row
                        for row in rows
                        if row.get("setup_id") == setup["id"] and implementation(row) == impl
                    ]
                    pages.append(page(snapshot, setup, selected, now, impl, setups))
        choices.append(
            disclosure(
                family.replace("_", " ").title(),
                '<div class="setup-choices">' + "".join(links) + "</div>",
            )
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
    return '<div class="setup-navigation">' + disclosure(
        project_label(snapshot), "".join(choices)
    ) + "</div>", "".join(pages)


def assets():
    return (
        (ORGAN_ROOT / "insight/setup_browser.css").read_text(),
        (ORGAN_ROOT / "insight/setup_browser.js").read_text(),
    )
