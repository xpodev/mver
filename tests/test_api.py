"""Tests for the public resver Python API."""
from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from resver import (
    AppConfig,
    GlobalConfig,
    Group,
    GroupVersion,
    Resource,
    ResourceVersion,
    Registry,
    ResolvedApp,
    ResolvedResource,
)

_yaml = YAML()
_yaml.default_flow_style = False

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REGISTRY_DATA = {
    "resources": {
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
                    "resources": {"fraud-detector": "1.0.0", "embedder": "0.9.0"},
                },
                "2.0.0": {
                    "description": "Second release",
                    "resources": {"fraud-detector": "2.0.0", "embedder": "1.0.0"},
                },
            }
        },
        "staging": {
            "versions": {
                "0.1.0": {
                    "resources": {"fraud-detector": "2.0.0", "embedder": "1.0.0"},
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
    resver_dir = tmp_path / ".resver"
    resver_dir.mkdir(exist_ok=True)
    with open(resver_dir / "registry.yml", "w") as f:
        _yaml.dump(REGISTRY_DATA, f)
    with open(resver_dir / "config.yml", "w") as f:
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
        assert r.path == tmp_path / ".resver" / "registry.yml"

    def test_finds_from_subdir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        make_monorepo(tmp_path)
        sub = tmp_path / "apps" / "my-service"
        sub.mkdir(parents=True)
        monkeypatch.chdir(sub)
        r = Registry.find()
        assert r.path == tmp_path / ".resver" / "registry.yml"

    def test_raises_file_not_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError):
            Registry.find()

    def test_load_from_explicit_path(self, tmp_path: Path) -> None:
        make_monorepo(tmp_path)
        r = Registry.load(tmp_path / ".resver" / "registry.yml")
        assert r.path == tmp_path / ".resver" / "registry.yml"


class TestRegistryContents:
    @pytest.fixture()
    def registry(self, tmp_path: Path) -> Registry:
        make_monorepo(tmp_path)
        return Registry.load(tmp_path / ".resver" / "registry.yml")

    def test_root_property(self, registry: Registry, tmp_path: Path) -> None:
        assert registry.root == tmp_path

    def test_resources_dict(self, registry: Registry) -> None:
        assert set(registry.resources) == {"fraud-detector", "embedder"}

    def test_get_resource(self, registry: Registry) -> None:
        m = registry.get_resource("fraud-detector")
        assert isinstance(m, Resource)
        assert m.name == "fraud-detector"
        assert m.description == "Fraud model"

    def test_get_resource_missing_returns_none(self, registry: Registry) -> None:
        assert registry.get_resource("nonexistent") is None

    def test_groups_dict(self, registry: Registry) -> None:
        assert set(registry.groups) == {"production", "staging"}

    def test_get_group(self, registry: Registry) -> None:
        g = registry.get_group("production")
        assert isinstance(g, Group)
        assert g.name == "production"

    def test_get_group_missing_returns_none(self, registry: Registry) -> None:
        assert registry.get_group("nonexistent") is None


# ---------------------------------------------------------------------------
# Resource / ResourceVersion
# ---------------------------------------------------------------------------


class TestResource:
    @pytest.fixture()
    def resource(self, tmp_path: Path) -> Resource:
        make_monorepo(tmp_path)
        return Registry.load(tmp_path / ".resver" / "registry.yml").get_resource("fraud-detector")

    def test_versions_keys(self, resource: Resource) -> None:
        assert set(resource.versions) == {"1.0.0", "2.0.0"}

    def test_get_version(self, resource: Resource) -> None:
        mv = resource.get_version("1.0.0")
        assert isinstance(mv, ResourceVersion)
        assert mv.version == "1.0.0"
        assert mv.path == "models/fraud/v1.0.0"
        assert mv.created_by == "jane@co.com"

    def test_get_version_missing_returns_none(self, resource: Resource) -> None:
        assert resource.get_version("9.9.9") is None

    def test_latest_returns_highest_semver(self, resource: Resource) -> None:
        assert resource.latest.version == "2.0.0"

    def test_version_pull_command_override(self, resource: Resource) -> None:
        mv = resource.get_version("2.0.0")
        assert mv.pull_command == "aws s3 sync s3://bucket/{path} ./{path}"

    def test_version_no_command(self, resource: Resource) -> None:
        mv = resource.get_version("1.0.0")
        assert mv.pull_command is None
        assert mv.push_command is None


# ---------------------------------------------------------------------------
# Group / GroupVersion
# ---------------------------------------------------------------------------


class TestGroup:
    @pytest.fixture()
    def group(self, tmp_path: Path) -> Group:
        make_monorepo(tmp_path)
        return Registry.load(tmp_path / ".resver" / "registry.yml").get_group("production")

    def test_versions_keys(self, group: Group) -> None:
        assert set(group.versions) == {"1.0.0", "2.0.0"}

    def test_get_version(self, group: Group) -> None:
        gv = group.get_version("1.0.0")
        assert isinstance(gv, GroupVersion)
        assert gv.version == "1.0.0"
        assert gv.description == "First release"
        assert gv.resources == {"fraud-detector": "1.0.0", "embedder": "0.9.0"}

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
        resver_dir = tmp_path / ".resver"
        resver_dir.mkdir()
        with open(resver_dir / "registry.yml", "w") as f:
            _yaml.dump({"resources": {}, "groups": {}}, f)
        monkeypatch.chdir(tmp_path)
        cfg = GlobalConfig.load()
        assert cfg.pull_command is None
        assert cfg.push_command is None


# ---------------------------------------------------------------------------
# AppConfig
# ---------------------------------------------------------------------------


class TestAppConfig:
    def _write_app_yml(self, directory: Path, group: str, version: str) -> None:
        resver_dir = directory / ".resver"
        resver_dir.mkdir(exist_ok=True)
        with open(resver_dir / "app.yml", "w") as f:
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
        resver_dir = tmp_path / ".resver"
        resver_dir.mkdir(exist_ok=True)
        with open(resver_dir / "app.yml", "w") as f:
            _yaml.dump({"group": "production"}, f)  # missing version
        with pytest.raises(ValueError):
            AppConfig.load(tmp_path)


# ---------------------------------------------------------------------------
# AppConfig.resolve / ResolvedApp / ResolvedResource
# ---------------------------------------------------------------------------


class TestResolve:
    @pytest.fixture()
    def setup(self, tmp_path: Path):
        make_monorepo(tmp_path)
        registry = Registry.load(tmp_path / ".resver" / "registry.yml")
        config = GlobalConfig.load(tmp_path)
        return registry, config, tmp_path

    def test_resolve_returns_resolved_app(self, setup) -> None:
        registry, config, tmp_path = setup
        app_cfg = AppConfig(directory=tmp_path, group="production", version="2.0.0")
        resolved = app_cfg.resolve(registry, config)
        assert isinstance(resolved, ResolvedApp)
        assert resolved.group_name == "production"
        assert resolved.version == "2.0.0"

    def test_resolved_models_keys(self, setup) -> None:
        registry, config, tmp_path = setup
        resolved = AppConfig(directory=tmp_path, group="production", version="2.0.0").resolve(registry, config)
        assert set(resolved.resources) == {"fraud-detector", "embedder"}

    def test_resolved_model_path(self, setup) -> None:
        registry, config, tmp_path = setup
        resolved = AppConfig(directory=tmp_path, group="production", version="2.0.0").resolve(registry, config)
        fraud = resolved["fraud-detector"]
        assert isinstance(fraud, ResolvedResource)
        assert fraud.path == "models/fraud/v2.0.0"
        assert fraud.version == "2.0.0"

    def test_command_resolution_version_override_wins(self, setup) -> None:
        """Per-version pull_command takes priority over global config."""
        registry, config, tmp_path = setup
        resolved = AppConfig(directory=tmp_path, group="production", version="2.0.0").resolve(registry, config)
        fraud = resolved["fraud-detector"]
        # version 2.0.0 has its own pull_command
        assert fraud.pull_command == "aws s3 sync s3://bucket/{path} ./{path}"

    def test_command_resolution_global_fallback(self, setup) -> None:
        """Global config is used when version has no override."""
        registry, config, tmp_path = setup
        resolved = AppConfig(directory=tmp_path, group="production", version="1.0.0").resolve(registry, config)
        fraud = resolved["fraud-detector"]
        # version 1.0.0 has no override → falls back to global
        assert fraud.pull_command == "dvc pull {path}"
        assert fraud.push_command == "dvc push {path}"

    def test_command_none_without_config(self, setup) -> None:
        """Commands are None when no version override and no GlobalConfig passed."""
        registry, _, tmp_path = setup
        resolved = AppConfig(directory=tmp_path, group="production", version="1.0.0").resolve(registry)
        assert resolved["fraud-detector"].pull_command is None

    def test_getitem(self, setup) -> None:
        registry, config, tmp_path = setup
        resolved = AppConfig(directory=tmp_path, group="production", version="2.0.0").resolve(registry, config)
        resource = resolved["embedder"]
        assert resource.name == "embedder"

    def test_getitem_missing_raises(self, setup) -> None:
        registry, config, tmp_path = setup
        resolved = AppConfig(directory=tmp_path, group="production", version="2.0.0").resolve(registry, config)
        with pytest.raises(KeyError):
            _ = resolved["nonexistent"]

    def test_len_and_iter(self, setup) -> None:
        registry, config, tmp_path = setup
        resolved = AppConfig(directory=tmp_path, group="production", version="2.0.0").resolve(registry, config)
        assert len(resolved) == 2
        assert set(resolved) == {"fraud-detector", "embedder"}

    def test_resolve_unknown_group_raises(self, setup) -> None:
        registry, config, tmp_path = setup
        with pytest.raises(KeyError, match="Group 'nonexistent'"):
            AppConfig(directory=tmp_path, group="nonexistent", version="1.0.0").resolve(registry, config)

    def test_resolve_unknown_version_raises(self, setup) -> None:
        registry, config, tmp_path = setup
        with pytest.raises(KeyError, match="Version '9.9.9'"):
            AppConfig(directory=tmp_path, group="production", version="9.9.9").resolve(registry, config)

    def test_registry_config_helper(self, setup) -> None:
        registry, _, tmp_path = setup
        cfg = registry.config()
        assert cfg.pull_command == "dvc pull {path}"

    def test_registry_app_config_helper(self, setup) -> None:
        registry, _, tmp_path = setup
        resver_dir = tmp_path / ".resver"
        resver_dir.mkdir(exist_ok=True)
        with open(resver_dir / "app.yml", "w") as f:
            _yaml.dump({"group": "staging", "version": "0.1.0"}, f)
        app = registry.app_config(tmp_path)
        assert app.group == "staging"


# ---------------------------------------------------------------------------
# AppConfig resource-pin mode
# ---------------------------------------------------------------------------


class TestAppConfigResourcePin:
    def test_load_resource_pin_mode(self, tmp_path: Path) -> None:
        resver_dir = tmp_path / ".resver"
        resver_dir.mkdir()
        with open(resver_dir / "app.yml", "w") as f:
            _yaml.dump({"resources": {"fraud-detector": "2.0.0", "embedder": "1.0.0"}}, f)
        cfg = AppConfig.load(tmp_path)
        assert cfg.group is None
        assert cfg.version is None
        assert cfg.resources == {"fraud-detector": "2.0.0", "embedder": "1.0.0"}

    def test_resolve_resource_pin_mode(self, tmp_path: Path) -> None:
        make_monorepo(tmp_path)
        registry = Registry.load(tmp_path / ".resver" / "registry.yml")
        cfg = AppConfig(directory=tmp_path, resources={"fraud-detector": "2.0.0", "embedder": "1.0.0"})
        resolved = cfg.resolve(registry)
        assert isinstance(resolved, ResolvedApp)
        assert resolved.group_name is None
        assert resolved.version is None
        assert set(resolved.resources) == {"fraud-detector", "embedder"}
        assert resolved["fraud-detector"].path == "models/fraud/v2.0.0"
        assert resolved["embedder"].path == "models/embedder/v1.0.0"

    def test_resolve_resource_pin_with_global_fallback(self, tmp_path: Path) -> None:
        make_monorepo(tmp_path)
        registry = Registry.load(tmp_path / ".resver" / "registry.yml")
        config = GlobalConfig.load(tmp_path)
        cfg = AppConfig(directory=tmp_path, resources={"fraud-detector": "1.0.0"})
        resolved = cfg.resolve(registry, config)
        # version 1.0.0 has no override → global fallback
        assert resolved["fraud-detector"].pull_command == "dvc pull {path}"

    def test_resolve_resource_pin_unknown_resource_raises(self, tmp_path: Path) -> None:
        make_monorepo(tmp_path)
        registry = Registry.load(tmp_path / ".resver" / "registry.yml")
        cfg = AppConfig(directory=tmp_path, resources={"ghost-model": "1.0.0"})
        with pytest.raises(KeyError, match="ghost-model"):
            cfg.resolve(registry)

    def test_resolve_resource_pin_unknown_version_raises(self, tmp_path: Path) -> None:
        make_monorepo(tmp_path)
        registry = Registry.load(tmp_path / ".resver" / "registry.yml")
        cfg = AppConfig(directory=tmp_path, resources={"fraud-detector": "9.9.9"})
        with pytest.raises(KeyError, match="9.9.9"):
            cfg.resolve(registry)

    def test_getitem_missing_in_resource_pin_mode(self, tmp_path: Path) -> None:
        make_monorepo(tmp_path)
        registry = Registry.load(tmp_path / ".resver" / "registry.yml")
        cfg = AppConfig(directory=tmp_path, resources={"fraud-detector": "2.0.0"})
        resolved = cfg.resolve(registry)
        with pytest.raises(KeyError, match="direct resource pins"):
            _ = resolved["nonexistent"]

    def test_repr_pin_mode(self, tmp_path: Path) -> None:
        cfg = AppConfig(directory=tmp_path, resources={"fraud-detector": "2.0.0"})
        assert "direct pins" not in repr(cfg)  # __repr__ shows resources=
        assert "fraud-detector" in repr(cfg)

    def test_repr_resolved_app_pin_mode(self, tmp_path: Path) -> None:
        make_monorepo(tmp_path)
        registry = Registry.load(tmp_path / ".resver" / "registry.yml")
        cfg = AppConfig(directory=tmp_path, resources={"fraud-detector": "2.0.0"})
        resolved = cfg.resolve(registry)
        r = repr(resolved)
        assert "(direct pins)" in r
        assert "fraud-detector" in r
