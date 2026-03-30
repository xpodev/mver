"""Tests for resver app commands."""
from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML
from typer.testing import CliRunner

from resver.cli import app

_yaml = YAML()


def _write_app_cfg(path: Path, group: str, version: str) -> None:
    resver_dir = path / ".resver"
    resver_dir.mkdir(exist_ok=True)
    with open(resver_dir / "app.yml", "w") as f:
        _yaml.dump({"group": group, "version": version}, f)


def test_app_use(monorepo: Path, app_dir: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(app_dir)
    result = runner.invoke(app, ["app", "use", "production@1.0.0"])
    assert result.exit_code == 0, result.output
    assert (app_dir / ".resver" / "app.yml").exists()
    with open(app_dir / ".resver" / "app.yml") as f:
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


def test_app_use_resource_pin(monorepo: Path, app_dir: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(app_dir)
    result = runner.invoke(app, ["app", "use", "--resource", "fraud-detector=2.1.0", "--resource", "embedder=0.9.4"])
    assert result.exit_code == 0, result.output
    with open(app_dir / ".resver" / "app.yml") as f:
        data = _yaml.load(f)
    assert "resources" in data
    assert str(data["resources"]["fraud-detector"]) == "2.1.0"
    assert str(data["resources"]["embedder"]) == "0.9.4"


def test_app_use_resource_pin_unknown_resource_fails(monorepo: Path, app_dir: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(app_dir)
    result = runner.invoke(app, ["app", "use", "--resource", "ghost-model=1.0.0"])
    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_app_use_resource_pin_unknown_version_fails(monorepo: Path, app_dir: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(app_dir)
    result = runner.invoke(app, ["app", "use", "--resource", "fraud-detector=9.9.9"])
    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_app_use_resource_pin_bad_format_fails(monorepo: Path, app_dir: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(app_dir)
    result = runner.invoke(app, ["app", "use", "--resource", "fraud-detector"])
    assert result.exit_code == 1
    assert "name=version" in result.output


def test_app_use_combine_group_and_model_fails(monorepo: Path, app_dir: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(app_dir)
    result = runner.invoke(app, ["app", "use", "production@1.0.0", "--resource", "fraud-detector=2.1.0"])
    assert result.exit_code == 1


def test_app_show(monorepo: Path, app_dir: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_app_cfg(app_dir, "production", "1.0.0")
    monkeypatch.chdir(app_dir)
    result = runner.invoke(app, ["app", "show"])
    assert result.exit_code == 0, result.output
    assert "fraud-detector" in result.output
    assert "2.1.0" in result.output
    assert "models/fraud-detector/v2.1.0" in result.output


def test_app_show_resource_pin(monorepo: Path, app_dir: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    resver_dir = app_dir / ".resver"
    resver_dir.mkdir(exist_ok=True)
    with open(resver_dir / "app.yml", "w") as f:
        _yaml.dump({"resources": {"fraud-detector": "2.1.0"}}, f)
    monkeypatch.chdir(app_dir)
    result = runner.invoke(app, ["app", "show"])
    assert result.exit_code == 0, result.output
    assert "fraud-detector" in result.output
    assert "2.1.0" in result.output
    assert "models/fraud-detector/v2.1.0" in result.output


def test_app_show_no_resver_yml_fails(monorepo: Path, app_dir: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(app_dir)
    result = runner.invoke(app, ["app", "show"])
    assert result.exit_code == 1
    assert ".resver/app.yml" in result.output


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


def test_app_check_valid_resource_pin(monorepo: Path, app_dir: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    resver_dir = app_dir / ".resver"
    resver_dir.mkdir(exist_ok=True)
    with open(resver_dir / "app.yml", "w") as f:
        _yaml.dump({"resources": {"fraud-detector": "2.1.0", "embedder": "0.9.4"}}, f)
    monkeypatch.chdir(app_dir)
    result = runner.invoke(app, ["app", "check"])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_app_check_stale_resource_pin(monorepo: Path, app_dir: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    resver_dir = app_dir / ".resver"
    resver_dir.mkdir(exist_ok=True)
    with open(resver_dir / "app.yml", "w") as f:
        _yaml.dump({"resources": {"fraud-detector": "9.9.9"}}, f)
    monkeypatch.chdir(app_dir)
    result = runner.invoke(app, ["app", "check"])
    assert result.exit_code == 1
    assert "not found" in result.output
