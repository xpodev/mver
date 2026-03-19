"""Tests for mgm pull and mgm push commands."""
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


def test_pull_executes_command(
    monorepo: Path,
    app_dir: Path,
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
    mocker,
) -> None:
    _write_app_cfg(app_dir, "production", "1.0.0")
    monkeypatch.chdir(app_dir)
    mock_run = mocker.patch("mgm.executor.subprocess.run", return_value=mocker.Mock(returncode=0))
    result = runner.invoke(app, ["pull"])
    assert result.exit_code == 0, result.output
    assert mock_run.call_count == 2  # two models


def test_pull_no_mgm_yml_fails(
    monorepo: Path,
    app_dir: Path,
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(app_dir)
    result = runner.invoke(app, ["pull"])
    assert result.exit_code == 1
    assert "mgm.yml" in result.output


def test_pull_uses_token_substitution(
    monorepo: Path,
    app_dir: Path,
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
    mocker,
) -> None:
    _write_app_cfg(app_dir, "production", "1.0.0")
    monkeypatch.chdir(app_dir)
    mock_run = mocker.patch("mgm.executor.subprocess.run", return_value=mocker.Mock(returncode=0))
    runner.invoke(app, ["pull"])
    calls = [str(c.args[0]) for c in mock_run.call_args_list]
    # The global config is "dvc pull {path}" — path should be substituted
    assert any("dvc pull models/fraud-detector/v2.1.0" in c for c in calls)


def test_pull_command_failure_halts(
    monorepo: Path,
    app_dir: Path,
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
    mocker,
) -> None:
    _write_app_cfg(app_dir, "production", "1.0.0")
    monkeypatch.chdir(app_dir)
    mocker.patch("mgm.executor.subprocess.run", return_value=mocker.Mock(returncode=1))
    result = runner.invoke(app, ["pull"])
    assert result.exit_code == 1
    assert "exited with code" in result.output


def test_push_executes_command(
    monorepo: Path,
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
    mocker,
) -> None:
    monkeypatch.chdir(monorepo)
    mock_run = mocker.patch("mgm.executor.subprocess.run", return_value=mocker.Mock(returncode=0))
    result = runner.invoke(app, ["push", "production@1.0.0"])
    assert result.exit_code == 0, result.output
    assert mock_run.call_count == 2


def test_push_unknown_group_fails(
    monorepo: Path,
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["push", "ghost@1.0.0"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_pull_no_command_fails_before_executing(
    tmp_path: Path,
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
    mocker,
) -> None:
    """Pull should validate all commands before executing any."""
    from ruamel.yaml import YAML as _YAML
    yml = _YAML()
    # Registry with a model that has no command (no global config either)
    reg = {
        "models": {
            "m1": {"versions": {"1.0.0": {"path": "p"}}},
        },
        "groups": {
            "g1": {"versions": {"1.0.0": {"models": {"m1": "1.0.0"}}}},
        },
    }
    (tmp_path / "models.registry.yml").write_text("")
    with open(tmp_path / "models.registry.yml", "w") as f:
        yml.dump(reg, f)
    app_subdir = tmp_path / "app"
    app_subdir.mkdir()
    with open(app_subdir / "mgm.yml", "w") as f:
        yml.dump({"group": "g1", "version": "1.0.0"}, f)
    monkeypatch.chdir(app_subdir)
    mock_run = mocker.patch("mgm.executor.subprocess.run")
    result = runner.invoke(app, ["pull"])
    assert result.exit_code == 1
    mock_run.assert_not_called()
