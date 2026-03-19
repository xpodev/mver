"""Tests for mgm diff command."""
from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML
from typer.testing import CliRunner

from mgm.cli import app

_yaml = YAML()


def _make_registry_with_two_versions(tmp_path: Path) -> Path:
    reg = {
        "models": {
            "fraud-detector": {
                "versions": {
                    "1.0.0": {"path": "p1"},
                    "2.0.0": {"path": "p2"},
                }
            },
            "embedder": {
                "versions": {
                    "0.9.0": {"path": "e1"},
                    "1.0.0": {"path": "e2"},
                }
            },
        },
        "groups": {
            "production": {
                "versions": {
                    "1.0.0": {
                        "models": {"fraud-detector": "1.0.0", "embedder": "0.9.0"},
                    },
                    "2.0.0": {
                        "models": {"fraud-detector": "2.0.0", "embedder": "0.9.0"},
                    },
                }
            }
        },
    }
    with open(tmp_path / "models.registry.yml", "w") as f:
        _yaml.dump(reg, f)
    return tmp_path


def test_diff_shows_changed_models(tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    _make_registry_with_two_versions(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["diff", "production@1.0.0", "production@2.0.0"])
    assert result.exit_code == 0, result.output
    assert "fraud-detector" in result.output
    assert "1.0.0" in result.output
    assert "2.0.0" in result.output
    # embedder is unchanged, should not appear
    assert "embedder" not in result.output


def test_diff_no_changes(tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    _make_registry_with_two_versions(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["diff", "production@1.0.0", "production@1.0.0"])
    assert result.exit_code == 0
    assert "no changes" in result.output


def test_diff_different_groups_fails(tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    reg = {
        "models": {},
        "groups": {
            "a": {"versions": {"1.0.0": {"models": {}}}},
            "b": {"versions": {"1.0.0": {"models": {}}}},
        },
    }
    with open(tmp_path / "models.registry.yml", "w") as f:
        _yaml.dump(reg, f)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["diff", "a@1.0.0", "b@1.0.0"])
    assert result.exit_code == 1
    assert "same group" in result.output


def test_diff_missing_version_fails(tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    _make_registry_with_two_versions(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["diff", "production@1.0.0", "production@9.9.9"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_diff_where(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    """mgm where should print the registry path."""
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["where"])
    assert result.exit_code == 0
    assert "models.registry.yml" in result.output
