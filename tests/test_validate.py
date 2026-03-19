"""Tests for mgm validate command."""
from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML
from typer.testing import CliRunner

from mgm.cli import app

_yaml = YAML()


def test_validate_ok(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0, result.output
    assert "OK" in result.output


def test_validate_missing_model_version(tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    reg = {
        "models": {
            "m1": {"versions": {"1.0.0": {"path": "p"}}},
        },
        "groups": {
            "g1": {
                "versions": {
                    "1.0.0": {
                        "models": {"m1": "2.0.0"},  # 2.0.0 doesn't exist
                    }
                }
            }
        },
    }
    (tmp_path / "mgm.config.yml").write_text("pull_command: dvc pull {path}\npush_command: dvc push {path}\n")
    with open(tmp_path / "models.registry.yml", "w") as f:
        _yaml.dump(reg, f)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1
    assert "not in registry" in result.output


def test_validate_no_command(tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    reg = {
        "models": {
            "m1": {"versions": {"1.0.0": {"path": "p"}}},
        },
        "groups": {
            "g1": {"versions": {"1.0.0": {"models": {"m1": "1.0.0"}}}},
        },
    }
    # No config file — no commands
    with open(tmp_path / "models.registry.yml", "w") as f:
        _yaml.dump(reg, f)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1
    assert "no pull_command" in result.output or "pull_command" in result.output


def test_validate_invalid_semver(tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    reg = {
        "models": {
            "m1": {"versions": {"not-semver": {"path": "p"}}},
        },
        "groups": {},
    }
    with open(tmp_path / "models.registry.yml", "w") as f:
        _yaml.dump(reg, f)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1
    assert "not a valid semver" in result.output
