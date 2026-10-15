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

Snapshots preserve capture history for unchanged input. Receipts separately
record ``refreshed_at`` for each successful observation, so real refreshes
can commit metadata even when evidence is unchanged. Offline replay retains
the recorded observation time; a failed attempt exposes no successful refresh.
A local
``--from`` read reports the checkout's revision and dirty state, is labelled
"local checkout", and writes no receipt or snapshot: it cannot masquerade as
a published capture.

An ``inference-summary@3`` summary is an index of record shards. Each shard is
read at the same resolved commit, verified against the index's sha256 and kept
beside the snapshot (``snapshots/<instance>/<shard path>``, bytes unchanged); a
refresh reuses every kept shard whose sha256 is unchanged and fetches only the
rest. Shards are written only after the whole capture validates, and shards the
new index no longer names are then removed.

While a registry row declares ``migrating_from``, a committed capture made
under that older schema stays valid as last-good evidence, labelled as awaiting
its first refresh under the new pin; a fresh fetch must return the pinned schema.
"""

from __future__ import annotations

import hashlib
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
    refreshed_at: str | None = None  # latest successful observation, independent of capture
    migrating: str | None = None  # shown capture predates the pin (registry migrating_from)
    shards_fetched: int | None = None  # v3 online ingest: shards fetched (rest reused)

    @property
    def failed(self) -> bool:
        return self.outcome != "ok"


def receipt_path(out_dir: Path, name: str) -> Path:
    return Path(out_dir) / "receipts" / f"{name}.json"


def snapshot_path(out_dir: Path, name: str) -> Path:
    return Path(out_dir) / "snapshots" / f"{name}.json"


def shard_dir(out_dir: Path, name: str) -> Path:
    """Where a v3 capture's shards are kept: ``snapshots/<instance>/``."""
    return Path(out_dir) / "snapshots" / name


def _kept_shards(out_dir: Path, name: str):
    """``read(path) -> bytes`` over the kept shards of a v3 capture."""
    base = shard_dir(out_dir, name)
    return lambda path: (base / path).read_bytes()


def _cached_classify(doc, inst):
    """Classify a committed capture: under the pin, or, while the row declares
    ``migrating_from``, under that older schema. Returns ``(outcome, errors,
    migrating note or None)``."""
    outcome, errors = summary_mod.classify(doc, (inst.schema_name, inst.schema_version))
    previous = inst.previous_schema
    if (
        outcome == "unsupported"
        and previous
        and isinstance(doc, dict)
        and (doc.get("schema"), doc.get("version")) == previous
    ):
        outcome, errors = summary_mod.classify(doc, previous)
        if outcome == "ok":
            return (
                "ok",
                [],
                f"captured under {inst.migrating_from}; the registry pins "
                f"{inst.supported_schema}, awaiting the first refresh under it",
            )
    return outcome, errors, None


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
            refreshed_at=receipt.get("refreshed_at") if receipt.get("outcome") == "ok" else None,
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
        doc, errors = snap["summary"], []
        if doc.get("version") == summary_mod.SHARDED:
            doc, errors = summary_mod.load_sharded(doc, _kept_shards(out_dir, inst.instance))
            errors = [f"cached {e}" for e in errors]
        if errors:
            view.outcome, view.errors = "invalid", errors
            return view
        outcome, errors, migrating = _cached_classify(doc, inst)
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
        view.doc = doc
        view.migrating = migrating
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
    index, shard_bytes, fetched = None, {}, None
    try:
        commit = resolve_commit(inst.github, inst.branch)
        raw = fetch_at(inst.github, commit, inst.summary_path)
        try:
            doc = json.loads(raw)
        except ValueError as exc:
            outcome, errors = "invalid", [f"{inst.summary_path} is not JSON ({exc})"]
        else:
            why = summary_mod.supported(doc, wanted)
            if why is None and doc.get("version") == summary_mod.SHARDED:
                index = doc
                shard_bytes, fetched, errors = _fetch_shards(inst, out_dir, commit, index)
                if errors:
                    outcome, doc = "invalid", None
                else:
                    doc, errors = summary_mod.load_sharded(index, shard_bytes.__getitem__)
                    outcome = "invalid" if errors else "ok"
            if outcome == "ok":
                outcome, errors = summary_mod.classify(doc, wanted)
            if outcome == "ok" and doc.get("project") != inst.repo:
                outcome, errors = "invalid", ["project identity differs from registry"]
    except FetchError as exc:
        outcome, errors = "unavailable", [str(exc)]

    snap_file = snapshot_path(out_dir, inst.instance)
    # Order: changed shards, then the index, then the pruning of shards the new index
    # no longer names. An interrupted refresh leaves a capture whose digests no longer
    # match (offline: invalid, never a silently mixed capture); the next refresh
    # re-fetches every mismatched shard and repairs it.
    if outcome == "ok" and index is not None:
        _keep_shards(out_dir, inst.instance, shard_bytes)
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
                "summary": summary_mod.index_of(doc),
            },
        )
    if outcome == "ok" and index is not None:
        _prune_shards(out_dir, inst.instance, shard_bytes)
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
        **(
            {"record_shards": len(index["record_shards"])}
            if outcome == "ok" and index is not None
            else {}
        ),
        "errors": errors,
        "cached_from": last_good.get("fetched_at") if last_good and outcome != "ok" else None,
    }
    # Preserve capture history while recording a real successful observation.
    prior = read_receipt(out_dir, inst.instance)
    strip = lambda d: {k: v for k, v in d.items() if k not in ("fetched_at", "refreshed_at")}  # noqa: E731
    if prior is not None and strip(prior) == strip(receipt):
        receipt["fetched_at"] = prior["fetched_at"]
    receipt["refreshed_at"] = now if outcome == "ok" else None
    _carry(receipt_path(out_dir, inst.instance), receipt, keys=())
    view = _from_files(inst, out_dir)
    view.shards_fetched = fetched
    return view


def _fetch_shards(inst: Instance, out_dir: Path, commit: str, index: dict):
    """``({shard path: bytes}, fetched count, errors)`` for a v3 index at
    ``commit``: a kept shard whose bytes match the declared sha256 is reused,
    every other shard is fetched at the same commit. Raises FetchError when a
    shard cannot be fetched (the capture is then unavailable)."""
    errors = summary_mod.validate_shard_index(index)
    if "records" in index:
        errors.append("a v3 index carries its records in record_shards, never inline")
    if errors:
        return {}, None, errors
    base = shard_dir(out_dir, inst.instance)
    out, fetched = {}, 0
    for entry in index["record_shards"]:
        kept = base / entry["path"]
        try:
            body = kept.read_bytes()
        except OSError:
            body = None
        if body is None or hashlib.sha256(body).hexdigest() != entry["sha256"]:
            body = fetch_at(
                inst.github, commit, summary_mod.shard_location(inst.summary_path, entry["path"])
            )
            fetched += 1
        out[entry["path"]] = body
    return out, fetched, []


def _keep_shards(out_dir: Path, name: str, shards: dict[str, bytes]) -> None:
    """Write a validated capture's shards (only those that changed)."""
    base = shard_dir(out_dir, name)
    for path, body in shards.items():
        target = base / path
        try:
            if target.read_bytes() == body:
                continue
        except OSError:
            pass
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_bytes(body)
        tmp.replace(target)


def _prune_shards(out_dir: Path, name: str, shards: dict[str, bytes]) -> None:
    """Remove kept shards (and emptied folders) the current index no longer names."""
    base = shard_dir(out_dir, name)
    if base.is_dir():
        wanted = {(base / p).resolve() for p in shards}
        for path in sorted(base.rglob("*"), reverse=True):
            if path.is_file() and path.resolve() not in wanted:
                path.unlink()
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()


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
    if (
        summary_mod.supported(view.doc, wanted) is None
        and view.doc.get("version") == summary_mod.SHARDED
    ):
        base = file.parent
        view.doc, errors = summary_mod.load_sharded(
            view.doc, lambda shard: (base / shard).read_bytes()
        )
        if errors:
            view.outcome, view.errors, view.doc = "invalid", errors, None
            return view
    view.outcome, view.errors = summary_mod.classify(view.doc, wanted)
    if view.outcome == "ok" and view.doc.get("project") != inst.repo:
        view.outcome, view.errors = "invalid", ["project identity differs from registry"]
    if view.failed:
        view.doc = None
    else:
        view.refreshed_at = view.fetched_at
    return view
