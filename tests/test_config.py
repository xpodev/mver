"""Tests for resver config commands."""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from resver.cli import app


def test_config_set_pull_command(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["config", "set", "pull-command", "my-pull {path}"])
    assert result.exit_code == 0, result.output
    assert "Set pull_command" in result.output


def test_config_set_push_command(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["config", "set", "push-command", "my-push {path}"])
    assert result.exit_code == 0, result.output
    assert "Set push_command" in result.output


def test_config_show(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "pull_command" in result.output
    assert "dvc pull" in result.output


def test_config_show_empty(tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    # Registry without a config file
    resver_dir = tmp_path / ".resver"
    resver_dir.mkdir()
    (resver_dir / "registry.yml").write_text("models: {}\ngroups: {}\n")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "no global config" in result.output


def test_config_set_persists(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    runner.invoke(app, ["config", "set", "pull-command", "custom pull {path}"])
    result = runner.invoke(app, ["config", "show"])
    assert "custom pull {path}" in result.output
