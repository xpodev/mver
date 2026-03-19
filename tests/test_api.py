"""Tests for the public mver Python API."""
from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from mver import (
    AppConfig,
    GlobalConfig,
    Group,
    GroupVersion,
    Model,
    ModelVersion,
    Registry,
    ResolvedApp,
    ResolvedModel,
)

_yaml = YAML()
_yaml.default_flow_style = False

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REGISTRY_DATA = {
    "models": {
        "fraud-detector": {
            "description": "Fraud model",
            "versions": {
                "1.0.0": {"path": "models/fraud/v1.0.0", "created_by": "jane@co.com"},
                "2.0.0": {
                    "path": "models/fraud/v2.0.0",
                    "pull_command": "aws s3 sync s3://bucket/{path} ./{path}",
                },
            },
        },
        "embedder": {
            "description": "Embedding model",
            "versions": {
                "0.9.0": {"path": "models/embedder/v0.9.0"},
                "1.0.0": {"path": "models/embedder/v1.0.0"},
            },
        },
    },
    "groups": {
        "production": {
            "versions": {
                "1.0.0": {
                    "description": "First release",
                    "models": {"fraud-detector": "1.0.0", "embedder": "0.9.0"},
                },
                "2.0.0": {
                    "description": "Second release",
                    "models": {"fraud-detector": "2.0.0", "embedder": "1.0.0"},
                },
            }
        },
        "staging": {
            "versions": {
                "0.1.0": {
                    "models": {"fraud-detector": "2.0.0", "embedder": "1.0.0"},
                }
            }
        },
    },
}

CONFIG_DATA = {
    "pull_command": "dvc pull {path}",
    "push_command": "dvc push {path}",
}


def make_monorepo(tmp_path: Path) -> Path:
    with open(tmp_path / "models.registry.yml", "w") as f:
        _yaml.dump(REGISTRY_DATA, f)
    with open(tmp_path / "mver.config.yml", "w") as f:
        _yaml.dump(CONFIG_DATA, f)
    return tmp_path


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestRegistryFind:
    def test_finds_from_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        make_monorepo(tmp_path)
        monkeypatch.chdir(tmp_path)
        r = Registry.find()
        assert r.path == tmp_path / "models.registry.yml"

    def test_finds_from_subdir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        make_monorepo(tmp_path)
        sub = tmp_path / "apps" / "my-service"
        sub.mkdir(parents=True)
        monkeypatch.chdir(sub)
        r = Registry.find()
        assert r.path == tmp_path / "models.registry.yml"

    def test_raises_file_not_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError):
            Registry.find()

    def test_load_from_explicit_path(self, tmp_path: Path) -> None:
        make_monorepo(tmp_path)
        r = Registry.load(tmp_path / "models.registry.yml")
        assert r.path == tmp_path / "models.registry.yml"


class TestRegistryContents:
    @pytest.fixture()
    def registry(self, tmp_path: Path) -> Registry:
        make_monorepo(tmp_path)
        return Registry.load(tmp_path / "models.registry.yml")

    def test_root_property(self, registry: Registry, tmp_path: Path) -> None:
        assert registry.root == tmp_path

    def test_models_dict(self, registry: Registry) -> None:
        assert set(registry.models) == {"fraud-detector", "embedder"}

    def test_get_model(self, registry: Registry) -> None:
        m = registry.get_model("fraud-detector")
        assert isinstance(m, Model)
        assert m.name == "fraud-detector"
        assert m.description == "Fraud model"

    def test_get_model_missing_returns_none(self, registry: Registry) -> None:
        assert registry.get_model("nonexistent") is None

    def test_groups_dict(self, registry: Registry) -> None:
        assert set(registry.groups) == {"production", "staging"}

    def test_get_group(self, registry: Registry) -> None:
        g = registry.get_group("production")
        assert isinstance(g, Group)
        assert g.name == "production"

    def test_get_group_missing_returns_none(self, registry: Registry) -> None:
        assert registry.get_group("nonexistent") is None


# ---------------------------------------------------------------------------
# Model / ModelVersion
# ---------------------------------------------------------------------------


class TestModel:
    @pytest.fixture()
    def model(self, tmp_path: Path) -> Model:
        make_monorepo(tmp_path)
        return Registry.load(tmp_path / "models.registry.yml").get_model("fraud-detector")

    def test_versions_keys(self, model: Model) -> None:
        assert set(model.versions) == {"1.0.0", "2.0.0"}

    def test_get_version(self, model: Model) -> None:
        mv = model.get_version("1.0.0")
        assert isinstance(mv, ModelVersion)
        assert mv.version == "1.0.0"
        assert mv.path == "models/fraud/v1.0.0"
        assert mv.created_by == "jane@co.com"

    def test_get_version_missing_returns_none(self, model: Model) -> None:
        assert model.get_version("9.9.9") is None

    def test_latest_returns_highest_semver(self, model: Model) -> None:
        assert model.latest.version == "2.0.0"

    def test_version_pull_command_override(self, model: Model) -> None:
        mv = model.get_version("2.0.0")
        assert mv.pull_command == "aws s3 sync s3://bucket/{path} ./{path}"

    def test_version_no_command(self, model: Model) -> None:
        mv = model.get_version("1.0.0")
        assert mv.pull_command is None
        assert mv.push_command is None


# ---------------------------------------------------------------------------
# Group / GroupVersion
# ---------------------------------------------------------------------------


class TestGroup:
    @pytest.fixture()
    def group(self, tmp_path: Path) -> Group:
        make_monorepo(tmp_path)
        return Registry.load(tmp_path / "models.registry.yml").get_group("production")

    def test_versions_keys(self, group: Group) -> None:
        assert set(group.versions) == {"1.0.0", "2.0.0"}

    def test_get_version(self, group: Group) -> None:
        gv = group.get_version("1.0.0")
        assert isinstance(gv, GroupVersion)
        assert gv.version == "1.0.0"
        assert gv.description == "First release"
        assert gv.models == {"fraud-detector": "1.0.0", "embedder": "0.9.0"}

    def test_get_version_missing_returns_none(self, group: Group) -> None:
        assert group.get_version("9.9.9") is None

    def test_latest_returns_highest_semver(self, group: Group) -> None:
        assert group.latest.version == "2.0.0"


# ---------------------------------------------------------------------------
# GlobalConfig
# ---------------------------------------------------------------------------


class TestGlobalConfig:
    def test_load_with_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        make_monorepo(tmp_path)
        monkeypatch.chdir(tmp_path)
        cfg = GlobalConfig.load()
        assert cfg.pull_command == "dvc pull {path}"
        assert cfg.push_command == "dvc push {path}"

    def test_load_missing_config_returns_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # registry exists but no config file
        with open(tmp_path / "models.registry.yml", "w") as f:
            _yaml.dump({"models": {}, "groups": {}}, f)
        monkeypatch.chdir(tmp_path)
        cfg = GlobalConfig.load()
        assert cfg.pull_command is None
        assert cfg.push_command is None


# ---------------------------------------------------------------------------
# AppConfig
# ---------------------------------------------------------------------------


class TestAppConfig:
    def _write_app_yml(self, directory: Path, group: str, version: str) -> None:
        with open(directory / "mver.yml", "w") as f:
            _yaml.dump({"group": group, "version": version}, f)

    def test_load(self, tmp_path: Path) -> None:
        self._write_app_yml(tmp_path, "production", "2.0.0")
        cfg = AppConfig.load(tmp_path)
        assert cfg.group == "production"
        assert cfg.version == "2.0.0"
        assert cfg.directory == tmp_path

    def test_load_missing_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            AppConfig.load(tmp_path)

    def test_load_invalid_raises(self, tmp_path: Path) -> None:
        with open(tmp_path / "mver.yml", "w") as f:
            _yaml.dump({"group": "production"}, f)  # missing version
        with pytest.raises(ValueError):
            AppConfig.load(tmp_path)


# ---------------------------------------------------------------------------
# AppConfig.resolve / ResolvedApp / ResolvedModel
# ---------------------------------------------------------------------------


class TestResolve:
    @pytest.fixture()
    def setup(self, tmp_path: Path):
        make_monorepo(tmp_path)
        registry = Registry.load(tmp_path / "models.registry.yml")
        config = GlobalConfig.load(tmp_path)
        return registry, config, tmp_path

    def test_resolve_returns_resolved_app(self, setup) -> None:
        registry, config, tmp_path = setup
        app_cfg = AppConfig("production", "2.0.0", tmp_path)
        resolved = app_cfg.resolve(registry, config)
        assert isinstance(resolved, ResolvedApp)
        assert resolved.group_name == "production"
        assert resolved.version == "2.0.0"

    def test_resolved_models_keys(self, setup) -> None:
        registry, config, tmp_path = setup
        resolved = AppConfig("production", "2.0.0", tmp_path).resolve(registry, config)
        assert set(resolved.models) == {"fraud-detector", "embedder"}

    def test_resolved_model_path(self, setup) -> None:
        registry, config, tmp_path = setup
        resolved = AppConfig("production", "2.0.0", tmp_path).resolve(registry, config)
        fraud = resolved["fraud-detector"]
        assert isinstance(fraud, ResolvedModel)
        assert fraud.path == "models/fraud/v2.0.0"
        assert fraud.version == "2.0.0"

    def test_command_resolution_version_override_wins(self, setup) -> None:
        """Per-version pull_command takes priority over global config."""
        registry, config, tmp_path = setup
        resolved = AppConfig("production", "2.0.0", tmp_path).resolve(registry, config)
        fraud = resolved["fraud-detector"]
        # version 2.0.0 has its own pull_command
        assert fraud.pull_command == "aws s3 sync s3://bucket/{path} ./{path}"

    def test_command_resolution_global_fallback(self, setup) -> None:
        """Global config is used when version has no override."""
        registry, config, tmp_path = setup
        resolved = AppConfig("production", "1.0.0", tmp_path).resolve(registry, config)
        fraud = resolved["fraud-detector"]
        # version 1.0.0 has no override → falls back to global
        assert fraud.pull_command == "dvc pull {path}"
        assert fraud.push_command == "dvc push {path}"

    def test_command_none_without_config(self, setup) -> None:
        """Commands are None when no version override and no GlobalConfig passed."""
        registry, _, tmp_path = setup
        resolved = AppConfig("production", "1.0.0", tmp_path).resolve(registry)
        assert resolved["fraud-detector"].pull_command is None

    def test_getitem(self, setup) -> None:
        registry, config, tmp_path = setup
        resolved = AppConfig("production", "2.0.0", tmp_path).resolve(registry, config)
        model = resolved["embedder"]
        assert model.name == "embedder"

    def test_getitem_missing_raises(self, setup) -> None:
        registry, config, tmp_path = setup
        resolved = AppConfig("production", "2.0.0", tmp_path).resolve(registry, config)
        with pytest.raises(KeyError):
            _ = resolved["nonexistent"]

    def test_len_and_iter(self, setup) -> None:
        registry, config, tmp_path = setup
        resolved = AppConfig("production", "2.0.0", tmp_path).resolve(registry, config)
        assert len(resolved) == 2
        assert set(resolved) == {"fraud-detector", "embedder"}

    def test_resolve_unknown_group_raises(self, setup) -> None:
        registry, config, tmp_path = setup
        with pytest.raises(KeyError, match="Group 'nonexistent'"):
            AppConfig("nonexistent", "1.0.0", tmp_path).resolve(registry, config)

    def test_resolve_unknown_version_raises(self, setup) -> None:
        registry, config, tmp_path = setup
        with pytest.raises(KeyError, match="Version '9.9.9'"):
            AppConfig("production", "9.9.9", tmp_path).resolve(registry, config)

    def test_registry_config_helper(self, setup) -> None:
        registry, _, tmp_path = setup
        cfg = registry.config()
        assert cfg.pull_command == "dvc pull {path}"

    def test_registry_app_config_helper(self, setup) -> None:
        registry, _, tmp_path = setup
        with open(tmp_path / "mver.yml", "w") as f:
            _yaml.dump({"group": "staging", "version": "0.1.0"}, f)
        app = registry.app_config(tmp_path)
        assert app.group == "staging"
