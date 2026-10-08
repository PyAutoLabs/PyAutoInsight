"""registry.yaml: schema, body-map resolution, disjoint scopes."""

import pytest
import yaml
from conftest import LENS_ROW, SECOND_ROW

from insight import ORGAN_ROOT, registry


def _doc(*rows):
    return {"schema": 1, "instances": [dict(r) for r in rows]}


def test_the_committed_registry_is_valid_against_a_body_map(body_map):
    data = yaml.safe_load((ORGAN_ROOT / "registry.yaml").read_text())
    body_map.update(
        {
            "PyAutoArray": {"github": "PyAutoLabs/PyAutoArray"},
            "autofit_inference": {
                "path": "fit/autofit_inference",
                "github": "PyAutoLabs/autofit_inference",
            },
        }
    )
    assert registry.validate(data, body_map) == []
    assert [r["instance"] for r in data["instances"]] == ["lens", "fit"]


def test_load_resolves_path_and_github_from_the_body_map(registry_file, fake_mind):
    (inst,) = registry.load(registry_file, mind=fake_mind)
    assert inst.github == "PyAutoLabs/autolens_inference"
    assert inst.path == "lens/autolens_inference"
    assert inst.schema_name == "inference-summary" and inst.schema_version == 1
    assert inst.blob_url("f" * 40, "results/x.json").endswith(
        "/blob/" + "f" * 40 + "/results/x.json"
    )


def test_a_registry_row_may_not_carry_its_own_path_or_github(body_map):
    row = dict(LENS_ROW, path="lens/autolens_inference", github="PyAutoLabs/autolens_inference")
    problems = registry.validate(_doc(row), body_map)
    assert any("unknown field(s) github, path" in p for p in problems)


def test_repo_must_be_a_body_map_identity(body_map):
    problems = registry.validate(_doc(dict(LENS_ROW, repo="nowhere_inference")), body_map)
    assert any("not in the body map" in p for p in problems)
    problems = registry.validate(_doc(dict(LENS_ROW, library_refs=["PyAutoNope"])), body_map)
    assert any("library_refs not in the body map: PyAutoNope" in p for p in problems)


def test_the_same_summary_cannot_be_registered_twice(body_map):
    twin = dict(LENS_ROW, instance="lens2")
    problems = registry.validate(_doc(LENS_ROW, twin), body_map)
    assert any("already registered as 'lens'" in p for p in problems)
    assert registry.validate(_doc(LENS_ROW, SECOND_ROW), body_map) == []


@pytest.mark.parametrize(
    "field, value, needle",
    [
        ("summary_path", "../outside.json", "summary_path"),
        ("summary_path", "/abs/summary.json", "summary_path"),
        ("supported_schema", "inference-summary", "supported_schema"),
        ("dashboard_url", "http://insecure.invalid/", "dashboard_url"),
        ("instance", "Lens", "instance must match"),
    ],
)
def test_malformed_rows_are_refused(body_map, field, value, needle):
    problems = registry.validate(_doc(dict(LENS_ROW, **{field: value})), body_map)
    assert any(needle in p for p in problems), problems


def test_explicit_mind_wins_over_the_environment(tmp_path, fake_mind, monkeypatch):
    elsewhere = tmp_path / "other" / "PyAutoMind"
    elsewhere.mkdir(parents=True)
    (elsewhere / "repos.yaml").write_text("repos: {}\n")
    monkeypatch.setenv("PYAUTO_MIND", str(elsewhere))
    assert registry.body_map_path(fake_mind) == fake_mind / "repos.yaml"
    assert registry.body_map_path() == elsewhere / "repos.yaml"


def test_pyauto_root_grouped_and_flat_layouts_resolve(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "ORGAN_ROOT", tmp_path / "x" / "y" / "PyAutoInsight")
    for layout in ("organs/PyAutoMind", "PyAutoMind"):
        root = tmp_path / layout.replace("/", "_")
        (root / layout).mkdir(parents=True)
        (root / layout / "repos.yaml").write_text("repos: {}\n")
        monkeypatch.setenv("PYAUTO_ROOT", str(root))
        assert registry.body_map_path() == root / layout / "repos.yaml"


def test_no_body_map_is_an_error_not_a_guess(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "ORGAN_ROOT", tmp_path / "x" / "y" / "PyAutoInsight")
    with pytest.raises(registry.RegistryError, match="cannot find PyAutoMind/repos.yaml"):
        registry.body_map_path()
    with pytest.raises(registry.RegistryError, match="no repos.yaml there"):
        registry.body_map_path(tmp_path)


def test_get_names_the_known_instances(registry_file, fake_mind):
    instances = registry.load(registry_file, mind=fake_mind)
    assert registry.get(instances, "lens").repo == "autolens_inference"
    with pytest.raises(registry.RegistryError, match="known: lens"):
        registry.get(instances, "nope")


def test_evidence_urls_quote_spaces_and_parentheses(registry_file, fake_mind):
    inst = registry.load(registry_file, mind=fake_mind)[0]
    result = inst.blob_url("a" * 40, "results/a (1).json")
    assert result.endswith("/results/a%20%281%29.json")
