"""Tests for mgm app commands."""
from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML
from typer.testing import CliRunner

from mgm.cli import app

_yaml = YAML()


def _write_app_cfg(path: Path, group: str, version: str) -> None:
    with open(path / "mgm.yml", "w") as f:
        _yaml.dump({"group": group, "version": version}, f)


def test_app_use(monorepo: Path, app_dir: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(app_dir)
    result = runner.invoke(app, ["app", "use", "production@1.0.0"])
    assert result.exit_code == 0, result.output
    assert (app_dir / "mgm.yml").exists()
    with open(app_dir / "mgm.yml") as f:
        data = _yaml.load(f)
    assert data["group"] == "production"
    assert str(data["version"]) == "1.0.0"


def test_app_use_unknown_group_fails(monorepo: Path, app_dir: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(app_dir)
    result = runner.invoke(app, ["app", "use", "ghost@1.0.0"])
    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_app_use_unknown_version_fails(monorepo: Path, app_dir: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(app_dir)
    result = runner.invoke(app, ["app", "use", "production@9.9.9"])
    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_app_show(monorepo: Path, app_dir: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_app_cfg(app_dir, "production", "1.0.0")
    monkeypatch.chdir(app_dir)
    result = runner.invoke(app, ["app", "show"])
    assert result.exit_code == 0, result.output
    assert "fraud-detector" in result.output
    assert "2.1.0" in result.output
    assert "models/fraud-detector/v2.1.0" in result.output


def test_app_show_no_mgm_yml_fails(monorepo: Path, app_dir: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(app_dir)
    result = runner.invoke(app, ["app", "show"])
    assert result.exit_code == 1
    assert "mgm.yml" in result.output


def test_app_check_valid(monorepo: Path, app_dir: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_app_cfg(app_dir, "production", "1.0.0")
    monkeypatch.chdir(app_dir)
    result = runner.invoke(app, ["app", "check"])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_app_check_stale_version(monorepo: Path, app_dir: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_app_cfg(app_dir, "production", "9.9.9")
    monkeypatch.chdir(app_dir)
    result = runner.invoke(app, ["app", "check"])
    assert result.exit_code == 1
    assert "does not exist" in result.output
