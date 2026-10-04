"""Hermetic fixtures: a fabricated body map, registry and GitHub, no network."""

import json
import sys
import urllib.request
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_G = "c" * 40

LENS_ROW = {
    "instance": "lens",
    "repo": "autolens_inference",
    "summary_path": "dashboard/summary.json",
    "supported_schema": "inference-summary@1",
    "dashboard_url": "https://pyautolabs.github.io/autolens_inference/",
    "library_refs": ["PyAutoLens", "PyAutoFit"],
    "cortex_project": None,
}
SECOND_ROW = {
    "instance": "galaxy",
    "repo": "autogalaxy_inference",
    "summary_path": "out/inference_summary.json",
    "supported_schema": "inference-summary@1",
    "dashboard_url": "https://example.invalid/autogalaxy_inference/",
    "library_refs": ["PyAutoGalaxy"],
    "cortex_project": None,
}
BODY_MAP = {
    "repos": {
        "autolens_inference": {
            "path": "lens/autolens_inference",
            "github": "PyAutoLabs/autolens_inference",
            "category": "project",
        },
        "autogalaxy_inference": {
            "path": "galaxy/autogalaxy_inference",
            "github": "PyAutoLabs/autogalaxy_inference",
            "category": "project",
        },
        "PyAutoLens": {"path": "lens/PyAutoLens", "github": "PyAutoLabs/PyAutoLens"},
        "PyAutoGalaxy": {"path": "galaxy/PyAutoGalaxy", "github": "PyAutoLabs/PyAutoGalaxy"},
        "PyAutoFit": {"path": "fit/PyAutoFit", "github": "PyAutoLabs/PyAutoFit"},
    }
}


def fixture_doc(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """No test may reach the network; tests that need GitHub use ``web``."""

    def refuse(request, *a, **k):
        url = getattr(request, "full_url", request)
        raise OSError(f"network disabled in tests: {url}")

    monkeypatch.setattr(urllib.request, "urlopen", refuse)


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    """No test resolves the real PyAutoMind or a token from the shell."""
    monkeypatch.delenv("PYAUTO_MIND", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setenv("PYAUTO_ROOT", str(tmp_path / "no-workspace-here"))


@pytest.fixture
def fake_mind(tmp_path):
    """A fabricated PyAutoMind checkout holding a minimal repos.yaml."""
    root = tmp_path / "PyAutoMind"
    root.mkdir()
    (root / "repos.yaml").write_text(yaml.safe_dump(BODY_MAP))
    return root


@pytest.fixture
def body_map():
    return {k: dict(v) for k, v in BODY_MAP["repos"].items()}


@pytest.fixture
def registry_file(tmp_path):
    path = tmp_path / "registry.yaml"
    path.write_text(yaml.safe_dump({"schema": 1, "instances": [dict(LENS_ROW)]}))
    return path


@pytest.fixture
def two_registry_file(tmp_path):
    path = tmp_path / "registry2.yaml"
    path.write_text(yaml.safe_dump({"schema": 1, "instances": [dict(LENS_ROW), dict(SECOND_ROW)]}))
    return path


class _Response:
    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeGitHub:
    """Serves the commits API and raw files from a dict; logs every request.

    ``branches[github] = sha`` answers the commits API; ``files[(github, sha,
    path)] = bytes`` answers raw.githubusercontent.com. ``down = True`` makes
    every request fail like a dropped connection.
    """

    def __init__(self):
        self.branches: dict[str, str] = {}
        self.files: dict[tuple[str, str, str], bytes] = {}
        self.requests: list = []
        self.down = False

    def publish(self, github, sha, path, doc):
        self.branches[github] = sha
        body = doc if isinstance(doc, bytes) else json.dumps(doc).encode()
        self.files[(github, sha, path)] = body

    def __call__(self, request, timeout=None):
        url = request.full_url
        self.requests.append(request)
        if self.down:
            raise OSError("connection reset by peer")
        api = "https://api.github.com/repos/"
        raw = "https://raw.githubusercontent.com/"
        if url.startswith(api):
            rest = url[len(api) :]
            github, _, branch = rest.partition("/commits/")
            if github in self.branches:
                return _Response(json.dumps({"sha": self.branches[github]}).encode())
        elif url.startswith(raw):
            owner, repo, sha, path = url[len(raw) :].split("/", 3)
            body = self.files.get((f"{owner}/{repo}", sha, path))
            if body is not None:
                return _Response(body)
        raise OSError(f"404 {url}")


@pytest.fixture
def web(monkeypatch):
    fake = FakeGitHub()
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    return fake
