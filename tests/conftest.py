"""Shared fixtures for resver tests."""
from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML
from typer.testing import CliRunner

from resver.cli import app

_yaml = YAML()
_yaml.default_flow_style = False

MINIMAL_REGISTRY = {
    "resources": {
        "fraud-detector": {
            "description": "Detects fraud",
            "versions": {
                "2.1.0": {
                    "path": "models/fraud-detector/v2.1.0",
                    "created_at": "2024-01-15T10:30:00Z",
                }
            },
        },
        "embedder": {
            "description": "Text embedding model",
            "versions": {
                "0.9.4": {
                    "path": "models/embedder/v0.9.4",
                    "created_at": "2024-01-10T11:00:00Z",
                }
            },
        },
    },
    "groups": {
        "production": {
            "versions": {
                "1.0.0": {
                    "created_at": "2024-01-15T10:30:00Z",
                    "description": "Initial production",
                    "resources": {
                        "fraud-detector": "2.1.0",
                        "embedder": "0.9.4",
                    },
                }
            }
        }
    },
}

MINIMAL_CONFIG = {
    "pull_command": "dvc pull {path}",
    "push_command": "dvc push {path}",
}


@pytest.fixture()
def monorepo(tmp_path: Path) -> Path:
    """Create a temp monorepo root with registry and global config."""
    resver_dir = tmp_path / ".resver"
    resver_dir.mkdir()

    reg_path = resver_dir / "registry.yml"
    with open(reg_path, "w") as f:
        _yaml.dump(MINIMAL_REGISTRY, f)

    cfg_path = resver_dir / "config.yml"
    with open(cfg_path, "w") as f:
        _yaml.dump(MINIMAL_CONFIG, f)

    return tmp_path


@pytest.fixture()
def app_dir(monorepo: Path) -> Path:
    """An app subdirectory inside the monorepo."""
    d = monorepo / "apps" / "my-service"
    d.mkdir(parents=True)
    return d


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def write_registry(path: Path, data: dict) -> None:
    resver_dir = path / ".resver"
    resver_dir.mkdir(exist_ok=True)
    with open(resver_dir / "registry.yml", "w") as f:
        _yaml.dump(data, f)


def read_registry(path: Path) -> dict:
    with open(path / ".resver" / "registry.yml") as f:
        return _yaml.load(f)
