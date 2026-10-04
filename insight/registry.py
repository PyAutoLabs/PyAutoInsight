"""Read and validate ``registry.yaml``, the one-row-per-instance registry.

A row names its project by a PyAutoMind body-map identity (``repo``). The
project's location (``path``) and GitHub home (``github``) are read from
``PyAutoMind/repos.yaml`` when the registry is loaded, so the organ never keeps
a second catalogue of repositories (the spec's "Proposed project registry").
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlparse

import yaml

from insight import ORGAN_ROOT
from insight.summary import safe_relative_path

REGISTRY_PATH = ORGAN_ROOT / "registry.yaml"
REGISTRY_SCHEMA = 1
MIND_REPO = "PyAutoMind"  # an organ name, not an instance fact
BODY_MAP = "repos.yaml"
BRANCH = "main"  # the branch every ingest resolves to one commit

REQUIRED = ("instance", "repo", "summary_path", "supported_schema", "dashboard_url")
FIELDS = (*REQUIRED, "library_refs", "cortex_project")

_KEY = re.compile(r"^[a-z][a-z0-9_-]*$")
_GITHUB = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_SCHEMA = re.compile(r"^([a-z][a-z0-9-]*)@([1-9][0-9]*)$")


class RegistryError(ValueError):
    """``registry.yaml`` (or the body map it resolves through) is malformed;
    the message lists every problem."""


@dataclass(frozen=True)
class Instance:
    instance: str
    repo: str
    summary_path: str
    supported_schema: str
    dashboard_url: str
    library_refs: tuple[str, ...] = ()
    cortex_project: str | None = None
    # Resolved from the body map, never written in registry.yaml.
    path: str = ""
    github: str = ""
    branch: str = BRANCH

    @property
    def name(self) -> str:
        return self.instance

    @property
    def github_url(self) -> str:
        return f"https://github.com/{self.github}"

    @property
    def schema_name(self) -> str:
        return _SCHEMA.match(self.supported_schema)[1]

    @property
    def schema_version(self) -> int:
        return int(_SCHEMA.match(self.supported_schema)[2])

    def blob_url(self, commit: str | None, path: str) -> str:
        """The GitHub page of ``path`` at ``commit`` (the branch when unknown)."""
        return f"{self.github_url}/blob/{quote(commit or self.branch, safe='')}/{quote(path, safe='/')}"

    def tree_url(self, commit: str | None) -> str:
        return f"{self.github_url}/tree/{quote(commit or self.branch, safe='')}"


# ------------------------------------------------------------- body map ---


def workspace_roots(root: Path | None = None) -> list[Path]:
    """Candidate workspace roots, most specific first."""
    if root is not None:
        return [Path(root)]
    roots = []
    env = os.environ.get("PYAUTO_ROOT")
    if env:
        roots.append(Path(env).expanduser())
    # organs/PyAutoInsight (grouped canonical) or <bundle>/PyAutoInsight (flat bundle).
    roots += [ORGAN_ROOT.parent.parent, ORGAN_ROOT.parent]
    return roots


def mind_candidates(mind: Path | str | None = None) -> list[Path]:
    """Where the PyAutoMind checkout is looked for, in order.

    An explicit ``--mind PATH`` first, then ``$PYAUTO_MIND``, then
    ``$PYAUTO_ROOT/organs/PyAutoMind`` and ``$PYAUTO_ROOT/PyAutoMind``, then
    beside this organ (grouped ``organs/`` or flat bundle layout).
    """
    out: list[Path] = []
    if mind is not None:
        out.append(Path(mind).expanduser())
    env = os.environ.get("PYAUTO_MIND")
    if env:
        out.append(Path(env).expanduser())
    for base in workspace_roots():
        out += [base / "organs" / MIND_REPO, base / MIND_REPO]
    return out


def body_map_path(mind: Path | str | None = None) -> Path:
    """``PyAutoMind/repos.yaml``; raise RegistryError when none is found.

    An explicit ``mind`` that holds no body map is an error, never a silent
    fall-through to another checkout.
    """
    if mind is not None:
        path = Path(mind).expanduser() / BODY_MAP
        if path.is_file():
            return path
        raise RegistryError(f"--mind {mind}: no {BODY_MAP} there")
    for candidate in mind_candidates():
        path = candidate / BODY_MAP
        if path.is_file():
            return path
    raise RegistryError(
        f"cannot find {MIND_REPO}/{BODY_MAP} (the body map that resolves each instance's "
        "repo); pass --mind PATH or set PYAUTO_MIND"
    )


def load_body_map(mind: Path | str | None = None) -> dict[str, dict]:
    """``{repo name: {path, github, …}}`` from the Mind body map."""
    path = body_map_path(mind)
    try:
        doc = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as exc:
        raise RegistryError(f"{path}: {exc}") from exc
    repos = doc.get("repos") if isinstance(doc, dict) else None
    if not isinstance(repos, dict):
        raise RegistryError(f"{path}: no `repos:` mapping")
    return {str(k): v for k, v in repos.items() if isinstance(v, dict)}


# ------------------------------------------------------------- registry ---


def _safe_relative(value: str) -> bool:
    return safe_relative_path(value)


def _https_url(value):
    try:
        parsed = urlparse(value)
        return parsed.scheme == "https" and bool(parsed.netloc)
    except ValueError:
        return False


def validate(data, body_map: dict[str, dict] | None = None) -> list[str]:
    """Return every problem with a parsed registry document (empty = valid).

    With ``body_map`` (``load_body_map()``), each ``repo`` and every
    ``library_refs`` entry must also be a body-map identity, and each repo must
    carry a ``github`` home there.
    """
    if not isinstance(data, dict):
        return ["registry is not a mapping"]
    problems = []
    if type(data.get("schema")) is not int or data.get("schema") != REGISTRY_SCHEMA:
        problems.append(f"schema must be {REGISTRY_SCHEMA}, got {data.get('schema')!r}")
    rows = data.get("instances")
    if not isinstance(rows, list) or not rows:
        return problems + ["instances must be a non-empty list"]
    seen: set[str] = set()
    scopes: dict[tuple[str, str], str] = {}
    for i, row in enumerate(rows):
        where = f"instances[{i}]"
        if not isinstance(row, dict):
            problems.append(f"{where} is not a mapping")
            continue
        where = f"instance {row.get('instance', i)!r}"
        for key in REQUIRED:
            value = row.get(key)
            if not isinstance(value, str) or not value.strip():
                problems.append(f"{where}: {key} is missing or empty")
        unknown = sorted(str(k) for k in set(row) - set(FIELDS))
        if unknown:
            problems.append(f"{where}: unknown field(s) {', '.join(unknown)}")
        key = row.get("instance")
        if isinstance(key, str):
            if not _KEY.match(key):
                problems.append(f"{where}: instance must match {_KEY.pattern}")
            if key in seen:
                problems.append(f"{where}: duplicate instance")
            seen.add(key)
        path = row.get("summary_path")
        if isinstance(path, str) and not _safe_relative(path):
            problems.append(f"{where}: summary_path must be a relative path inside the repo")
        schema = row.get("supported_schema")
        if isinstance(schema, str) and not _SCHEMA.match(schema):
            problems.append(f"{where}: supported_schema must be <name>@<integer version>")
        url = row.get("dashboard_url")
        if isinstance(url, str) and not _https_url(url):
            problems.append(f"{where}: dashboard_url must be an https:// URL")
        refs = row.get("library_refs", [])
        if refs is None:
            refs = []
        if not isinstance(refs, list) or not all(isinstance(r, str) and r for r in refs):
            problems.append(f"{where}: library_refs must be a list of body-map repo names")
            refs = []
        cortex = row.get("cortex_project")
        if cortex is not None and not (isinstance(cortex, str) and cortex.strip()):
            problems.append(f"{where}: cortex_project must be a Cortex key or null")
        repo = row.get("repo")
        if isinstance(repo, str) and isinstance(path, str):
            # Disjoint scopes: one summary is registered once, never twice under
            # two names to inflate coverage.
            other = scopes.get((repo, path))
            if other is not None:
                problems.append(f"{where}: {repo}:{path} is already registered as {other!r}")
            scopes[(repo, path)] = str(key)
        if body_map is not None:
            if isinstance(repo, str) and repo:
                entry = body_map.get(repo)
                if not isinstance(entry, dict):
                    problems.append(f"{where}: repo {repo!r} is not in the body map")
                else:
                    gh = entry.get("github")
                    if not (isinstance(gh, str) and _GITHUB.match(gh)):
                        problems.append(f"{where}: body map has no github owner/repo for {repo!r}")
            missing = [r for r in refs if r not in body_map]
            if missing:
                problems.append(f"{where}: library_refs not in the body map: {', '.join(missing)}")
    return problems


def load(
    path: Path | str = REGISTRY_PATH,
    mind: Path | str | None = None,
    body_map: dict[str, dict] | None = None,
) -> list[Instance]:
    """Parse and validate the registry, resolving each repo through the body
    map; raise RegistryError on any problem."""
    path = Path(path)
    try:
        data = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as exc:
        raise RegistryError(f"{path}: {exc}") from exc
    if body_map is None:
        body_map = load_body_map(mind)
    problems = validate(data, body_map)
    if problems:
        raise RegistryError(f"{path}:\n  " + "\n  ".join(problems))
    out = []
    for row in data["instances"]:
        entry = body_map[row["repo"]]
        out.append(
            Instance(
                instance=row["instance"],
                repo=row["repo"],
                summary_path=row["summary_path"],
                supported_schema=row["supported_schema"],
                dashboard_url=row["dashboard_url"],
                library_refs=tuple(row.get("library_refs") or ()),
                cortex_project=row.get("cortex_project"),
                path=str(entry.get("path") or row["repo"]),
                github=str(entry["github"]),
            )
        )
    return out


def get(instances: list[Instance], name: str) -> Instance:
    for instance in instances:
        if instance.instance == name:
            return instance
    known = ", ".join(i.instance for i in instances)
    raise RegistryError(f"no instance {name!r} in the registry (known: {known})")
