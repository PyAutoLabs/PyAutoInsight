"""Ingest one instance's summary at one resolved commit, with a receipt.

An online ingest resolves the instance's branch to **one commit** through the
GitHub API and reads ``summary_path`` at that SHA from
``raw.githubusercontent.com`` — never at a moving branch name, so every value
the board shows traces to a captured commit. Each attempt writes a receipt
(``receipts/<instance>.json``: resolved commit, fetch time, outcome, errors).
A good read also writes the last-good snapshot (``snapshots/<instance>.json``:
the summary plus the commit and time it was captured). A failed read keeps
that snapshot and the board shows it labelled **cached**, with its original
evidence and fetch times and the new error: nothing re-ages it.

Receipts and snapshots are written only when their content changes (the
``fetched_at`` of an unchanged outcome at the same commit is carried), so a
nightly refresh against an unchanged project commits nothing. A local
``--from`` read reports the checkout's revision and dirty state, is labelled
"local checkout", and writes no receipt or snapshot: it cannot masquerade as
a published capture.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from insight import ORGAN_ROOT
from insight import summary as summary_mod
from insight.registry import Instance

API_COMMIT = "https://api.github.com/repos/{github}/commits/{branch}"
RAW_FILE = "https://raw.githubusercontent.com/{github}/{sha}/{path}"
TIMEOUT = 20
USER_AGENT = "PyAutoInsight-ingest (+https://github.com/PyAutoLabs/PyAutoInsight)"
OUTCOMES = ("ok", "invalid", "unavailable", "unsupported")
_SHA = re.compile(r"^[0-9a-f]{40}$")


class FetchError(Exception):
    """A transport failure: the API or the raw file could not be read."""


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------- network ---


def _get(url: str, accept: str | None = None) -> bytes:
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    token = os.environ.get("GH_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.read()
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise FetchError(f"GET {url}: {exc}") from exc


def resolve_commit(github: str, branch: str = "main") -> str:
    """The one commit ``branch`` points at now (40-hex SHA)."""
    body = _get(API_COMMIT.format(github=github, branch=branch), "application/vnd.github+json")
    try:
        sha = json.loads(body)["sha"]
    except (ValueError, KeyError, TypeError) as exc:
        raise FetchError(f"{github}@{branch}: unreadable commit response ({exc})") from exc
    if not (isinstance(sha, str) and _SHA.match(sha)):
        raise FetchError(f"{github}@{branch}: commit response has no 40-hex sha")
    return sha


def fetch_at(github: str, sha: str, path: str) -> bytes:
    """``path`` exactly as it is at commit ``sha``."""
    return _get(RAW_FILE.format(github=github, sha=sha, path=path))


# -------------------------------------------------------------- snapshot ---


@dataclass
class Snapshot:
    """What the board shows for one instance.

    ``outcome``/``errors``/``attempt_*`` describe the latest attempt;
    ``doc``/``commit``/``fetched_at`` describe the summary shown, which is the
    last good capture when the latest attempt failed (``cached``).
    """

    instance: Instance
    outcome: str
    source: str  # remote | local | none
    doc: dict | None = None
    commit: str | None = None
    fetched_at: str | None = None
    errors: list[str] = field(default_factory=list)
    cached: bool = False
    attempt_commit: str | None = None
    attempt_at: str | None = None
    dirty: bool | None = None
    checkout: str | None = None
    source_branch: str | None = None

    @property
    def failed(self) -> bool:
        return self.outcome != "ok"


def receipt_path(out_dir: Path, name: str) -> Path:
    return Path(out_dir) / "receipts" / f"{name}.json"


def snapshot_path(out_dir: Path, name: str) -> Path:
    return Path(out_dir) / "snapshots" / f"{name}.json"


def _read_json(path: Path) -> dict | None:
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def _write_json(path: Path, doc: dict, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=indent, ensure_ascii=False) + "\n")
    tmp.replace(path)


def read_receipt(out_dir: Path, name: str) -> dict | None:
    return _read_json(receipt_path(out_dir, name))


def read_snapshot(out_dir: Path, name: str) -> dict | None:
    snap = _read_json(snapshot_path(out_dir, name))
    return snap if snap and isinstance(snap.get("summary"), dict) else None


def _carry(path: Path, doc: dict, keys=("fetched_at",)) -> bool:
    """Write ``doc`` unless the file already holds it apart from ``keys``.

    Returns True when written. Carrying keeps re-ingests of an unchanged
    outcome at an unchanged commit from rewriting (and re-aging) the file.
    """
    prior = _read_json(path)
    if prior is not None:
        strip = lambda d: {k: v for k, v in d.items() if k not in keys}  # noqa: E731
        if strip(prior) == strip(doc):
            return False
    _write_json(path, doc)
    return True


# ---------------------------------------------------------------- ingest ---


def _from_files(inst: Instance, out_dir: Path) -> Snapshot:
    """The committed receipt + last-good snapshot, read with no network."""
    receipt = read_receipt(out_dir, inst.instance)
    snap = read_snapshot(out_dir, inst.instance)
    if receipt is None:
        view = Snapshot(inst, "unavailable", "none", errors=["no receipt yet (never fetched)"])
    else:
        view = Snapshot(
            inst,
            receipt.get("outcome") if receipt.get("outcome") in OUTCOMES else "invalid",
            "remote",
            errors=[str(e) for e in receipt.get("errors") or []],
            attempt_commit=receipt.get("resolved_commit"),
            attempt_at=receipt.get("fetched_at"),
            source_branch=receipt.get("branch"),
        )
    if receipt is not None:
        problems = []
        for key, expected in (
            ("instance", inst.instance),
            ("repo", inst.repo),
            ("github", inst.github),
            ("summary_path", inst.summary_path),
        ):
            if receipt.get(key) != expected:
                problems.append(f"receipt {key} differs from registry")
        if summary_mod.parse_utc(receipt.get("fetched_at")) is None:
            problems.append("receipt capture time is invalid")
        resolved = receipt.get("resolved_commit")
        if resolved is not None and (not isinstance(resolved, str) or not _SHA.fullmatch(resolved)):
            problems.append("receipt commit is invalid")
        if receipt.get("outcome") == "ok" and (snap is None or resolved != snap.get("commit")):
            problems.append("receipt does not match snapshot commit")
        if problems:
            view.outcome = "invalid"
            view.errors += problems
    if snap is not None:
        outcome, errors = summary_mod.classify(
            snap["summary"], (inst.schema_name, inst.schema_version)
        )
        if snap.get("repo") != inst.repo or snap["summary"].get("project") != inst.repo:
            errors.append("cached project identity differs from registry")
        if snap.get("github") != inst.github or snap.get("summary_path") != inst.summary_path:
            errors.append("cached source differs from registry")
        if not isinstance(snap.get("commit"), str) or not _SHA.fullmatch(snap["commit"]):
            errors.append("cached commit is invalid")
        if summary_mod.parse_utc(snap.get("fetched_at")) is None:
            errors.append("cached capture time is invalid")
        if outcome != "ok" or errors:
            view.outcome, view.errors = "invalid", errors
            return view
        view.doc = snap["summary"]
        view.commit = snap.get("commit")
        view.fetched_at = snap.get("fetched_at")
        view.source = "remote"
        view.cached = view.failed
    return view


def ingest(
    inst: Instance,
    out_dir: Path = ORGAN_ROOT,
    *,
    offline: bool = False,
    local_path: Path | str | None = None,
    now: str | None = None,
) -> Snapshot:
    """Read one instance and return what the board shows for it.

    ``offline``: the committed receipt + snapshot only (no network, no
    write). ``local_path``: a local checkout (or the summary file itself),
    labelled as such, writing nothing. Otherwise: resolve, fetch, validate,
    write the receipt (and the snapshot on success).
    """
    out_dir = Path(out_dir)
    wanted = (inst.schema_name, inst.schema_version)
    if local_path is not None:
        return _ingest_local(inst, Path(local_path).expanduser(), wanted)
    if offline:
        return _from_files(inst, out_dir)

    now = now or utc_now()
    commit, doc, errors, outcome = None, None, [], "ok"
    try:
        commit = resolve_commit(inst.github, inst.branch)
        raw = fetch_at(inst.github, commit, inst.summary_path)
        try:
            doc = json.loads(raw)
        except ValueError as exc:
            outcome, errors = "invalid", [f"{inst.summary_path} is not JSON ({exc})"]
        else:
            outcome, errors = summary_mod.classify(doc, wanted)
            if outcome == "ok" and doc.get("project") != inst.repo:
                outcome, errors = "invalid", ["project identity differs from registry"]
    except FetchError as exc:
        outcome, errors = "unavailable", [str(exc)]

    snap_file = snapshot_path(out_dir, inst.instance)
    if outcome == "ok":
        _carry(
            snap_file,
            {
                "instance": inst.instance,
                "repo": inst.repo,
                "github": inst.github,
                "summary_path": inst.summary_path,
                "commit": commit,
                "fetched_at": now,
                "summary": doc,
            },
        )
    last_good = read_snapshot(out_dir, inst.instance)
    receipt = {
        "instance": inst.instance,
        "repo": inst.repo,
        "github": inst.github,
        "branch": inst.branch,
        "resolved_commit": commit,
        "summary_path": inst.summary_path,
        "source": "remote",
        "fetched_at": now,
        "outcome": outcome,
        "schema": doc.get("schema") if isinstance(doc, dict) else None,
        "version": doc.get("version") if isinstance(doc, dict) else None,
        "record_count": len(doc["records"])
        if isinstance(doc, dict) and isinstance(doc.get("records"), list)
        else None,
        "errors": errors,
        "cached_from": last_good.get("fetched_at") if last_good and outcome != "ok" else None,
    }
    _carry(receipt_path(out_dir, inst.instance), receipt)
    return _from_files(inst, out_dir)


def _git(checkout: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(checkout), *args], capture_output=True, text=True, timeout=20
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout if proc.returncode == 0 else None


def _ingest_local(inst: Instance, path: Path, wanted) -> Snapshot:
    file = path / inst.summary_path if path.is_dir() else path
    view = Snapshot(inst, "ok", "local", checkout=str(file.parent), fetched_at=utc_now())
    view.attempt_at = view.fetched_at
    top = _git(file.parent, "rev-parse", "--show-toplevel")
    if top:
        checkout = Path(top.strip())
        view.checkout = str(checkout)
        head = _git(checkout, "rev-parse", "HEAD")
        view.commit = head.strip() if head else None
        status = _git(checkout, "status", "--porcelain")
        view.dirty = bool(status.strip()) if status is not None else None
    view.attempt_commit = view.commit
    try:
        view.doc = json.loads(file.read_text())
    except OSError as exc:
        view.outcome, view.errors = "unavailable", [f"{file}: {exc}"]
        return view
    except ValueError as exc:
        view.outcome, view.errors = "invalid", [f"{file} is not JSON ({exc})"]
        view.doc = None
        return view
    view.outcome, view.errors = summary_mod.classify(view.doc, wanted)
    if view.outcome == "ok" and view.doc.get("project") != inst.repo:
        view.outcome, view.errors = "invalid", ["project identity differs from registry"]
    if view.failed:
        view.doc = None
    return view
