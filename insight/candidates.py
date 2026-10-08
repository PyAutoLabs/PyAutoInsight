"""Curated public literature handoff; expectations are not benchmark evidence."""

import json
from datetime import date
from urllib.parse import urlparse

from insight import ORGAN_ROOT
from insight.setup_browser import disclosure, e


def load(path=None):
    data = json.loads((path or ORGAN_ROOT / "sampler_candidates.json").read_text())
    if not isinstance(data, list):
        raise ValueError("sampler candidates must be a list")
    ids = set()
    for row in data:
        if not isinstance(row, dict):
            raise ValueError("sampler candidate must be object")
        for key in (
            "id",
            "name",
            "family",
            "integration_status",
            "benchmark_status",
            "investigation_prompt",
            "reviewed_at",
        ):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f"candidate needs {key}")
        if row["id"] in ids:
            raise ValueError("duplicate sampler candidate id")
        ids.add(row["id"])
        for key in ("paper_url", "code_url"):
            value = row.get(key)
            url = urlparse(value) if isinstance(value, str) else None
            if not url or url.scheme != "https" or not url.netloc or url.username or url.password:
                raise ValueError(f"candidate needs public HTTPS {key}")
        for key in ("expected_uses", "limitations"):
            if (
                not isinstance(row.get(key), list)
                or not row[key]
                or not all(isinstance(v, str) and v.strip() for v in row[key])
            ):
                raise ValueError(f"candidate needs {key} list")
        date.fromisoformat(row["reviewed_at"])
    return data


def render(data):
    out = [
        '<h2 id="sampler-candidates">Sampler candidates</h2>',
        "<p>Literature expectations, not measured PyAuto recommendations. Review a candidate and copy its investigation prompt.</p>",
    ]
    for i, row in enumerate(data):
        body = f"<p>{e(row['family'])} · reviewed {e(row['reviewed_at'])}</p>"
        body += f'<p><a href="{e(row["paper_url"])}" target="_blank" rel="noopener">Paper ↗</a> · <a href="{e(row["code_url"])}" target="_blank" rel="noopener">Official code ↗</a></p>'
        for label, key in (("Expected uses", "expected_uses"), ("Limitations", "limitations")):
            body += (
                f"<h3>{label}</h3><ul>" + "".join(f"<li>{e(v)}</li>" for v in row[key]) + "</ul>"
            )
        body += f"<p>Integration: {e(row['integration_status'])}</p><p>Benchmark evidence: {e(row['benchmark_status'])}</p>"
        prompt = (
            row["investigation_prompt"]
            + "\n\nUse the existing sampler pipeline and setup catalogue. Preserve the baseline-prepared model and priors. Distinguish cold/warm/resume starts from compilation/cache state. Propose a bounded implementation or benchmark plan before executing compute. Paper: "
            + row["paper_url"]
            + "\nCode: "
            + row["code_url"]
        )
        body += '<div data-candidate><button type="button" data-candidate-copy aria-label="Copy investigation prompt">⧉ Copy investigation prompt</button><span role="status" aria-live="polite"></span>'
        body += (
            disclosure(
                "Investigation prompt",
                f'<label for="candidate-{i}">Editable prompt</label><textarea class="candidate-prompt" id="candidate-{i}">{e(prompt)}</textarea>',
            )
            + "</div>"
        )
        out.append(disclosure(row["name"], body))
    return "".join(out)
