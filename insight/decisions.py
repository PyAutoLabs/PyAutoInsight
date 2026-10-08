"""Flat links to human-authored campaign decisions; never infer conclusions."""

import hashlib
import html
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from insight import ORGAN_ROOT

REPO = "PyAutoInsight"


def load(root: Path = ORGAN_ROOT) -> list[dict]:
    """Validate the index and locally owned records; remote records stay links."""
    try:
        document = yaml.safe_load((root / "decisions.yaml").read_text())
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"Decision history: {exc}") from exc
    if (
        not isinstance(document, dict)
        or set(document) != {"decisions"}
        or not isinstance(document["decisions"], list)
    ):
        raise ValueError("Decision history requires a decisions list")
    seen = set()
    rows = []
    for row in document["decisions"]:
        if not isinstance(row, dict) or set(row) != {"id", "title", "date", "url"}:
            raise ValueError("Decision requires id, title, date and url")
        if any(
            not isinstance(v, str) or not v.strip() or any(ord(c) < 32 for c in v)
            for v in row.values()
        ):
            raise ValueError("Decision fields must be nonempty single-line strings; quote dates")
        key = row["id"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key) or key in seen:
            raise ValueError(f"Invalid or duplicate decision id: {key}")
        seen.add(key)
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["date"]):
            raise ValueError("Decision date must be YYYY-MM-DD")
        date.fromisoformat(row["date"])
        url = urlsplit(row["url"])
        match = re.fullmatch(
            r"/PyAutoLabs/(PyAutoPulse|PyAutoInsight)/blob/main/decisions/([a-z0-9-]+)\.md",
            url.path,
        )
        if (
            url.scheme != "https"
            or url.netloc != "github.com"
            or url.query
            or url.fragment
            or not match
            or match[2] != key
        ):
            raise ValueError(
                "Decision URL must link to its canonical GitHub decisions/<id>.md record"
            )
        if match[1] == REPO:
            path = root / "decisions" / f"{key}.md"
            if not path.is_file():
                raise ValueError(f"Missing decision record: {path}")
            content = path.read_text()
            if (
                not content.startswith(f"# {row['title']}\n")
                or f"Date: {row['date']}\n" not in content
            ):
                raise ValueError(f"Decision title/date differ from index: {key}")
        rows.append(dict(row))
    return sorted(rows, key=lambda row: (row["date"], row["id"]), reverse=True)


def marker(rows):
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
    return f"<!-- decision-history:{digest} -->"


def render_html(rows=None):
    rows = load() if rows is None else rows
    links = "".join(
        f'<a class="model-choice" href="{html.escape(row["url"], quote=True)}" target="_blank" rel="noopener" title="Opens in a new tab">'
        f"{html.escape(row['title'])}</a>"
        for row in rows
    )
    return (
        marker(rows)
        + '<section id="decision-history"><h2>Decision History</h2>'
        + (links or "<p>No decisions recorded yet.</p>")
        + "</section>"
    )


def markdown(rows=None):
    rows = load() if rows is None else rows
    # HTML anchors also work in GitHub Markdown and safely escape arbitrary titles.
    links = [
        f'- <a href="{html.escape(row["url"], quote=True)}">{html.escape(row["title"])}</a>'
        for row in rows
    ]
    return "\n".join(
        [marker(rows), "## Decision History", "", *(links or ["No decisions recorded yet."]), ""]
    )
