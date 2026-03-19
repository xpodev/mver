"""Tests for mgm model version commands."""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from mgm.cli import app
from tests.conftest import read_registry


def test_version_add(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(
        app,
        ["model", "version", "add", "fraud-detector", "3.0.0", "--path", "models/fd/v3.0.0"],
    )
    assert result.exit_code == 0, result.output
    data = read_registry(monorepo)
    assert "3.0.0" in data["models"]["fraud-detector"]["versions"]


def test_version_add_with_commands(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(
        app,
        [
            "model", "version", "add", "embedder", "1.0.0",
            "--path", "models/emb/v1.0.0",
            "--pull-command", "aws s3 sync s3://bucket/{path} ./{path}",
            "--push-command", "aws s3 sync ./{path} s3://bucket/{path}",
            "--created-by", "user@example.com",
        ],
    )
    assert result.exit_code == 0, result.output
    data = read_registry(monorepo)
    ver = data["models"]["embedder"]["versions"]["1.0.0"]
    assert ver["pull_command"] == "aws s3 sync s3://bucket/{path} ./{path}"
    assert ver["created_by"] == "user@example.com"


def test_version_add_invalid_semver(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(
        app,
        ["model", "version", "add", "fraud-detector", "not-a-version", "--path", "p"],
    )
    assert result.exit_code == 1
    assert "not a valid semver" in result.output


def test_version_add_missing_path(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["model", "version", "add", "fraud-detector", "3.0.0"])
    assert result.exit_code == 1
    assert "--path" in result.output


def test_version_add_duplicate_fails(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(
        app,
        ["model", "version", "add", "fraud-detector", "2.1.0", "--path", "p"],
    )
    assert result.exit_code == 1
    assert "already exists" in result.output


def test_version_add_unknown_model_fails(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(
        app,
        ["model", "version", "add", "ghost", "1.0.0", "--path", "p"],
    )
    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_version_list(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["model", "version", "list", "fraud-detector"])
    assert result.exit_code == 0
    assert "2.1.0" in result.output


def test_version_remove(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    # Add a version with no group reference first
    runner.invoke(app, ["model", "version", "add", "fraud-detector", "9.9.9", "--path", "p"])
    result = runner.invoke(app, ["model", "version", "remove", "fraud-detector", "9.9.9"])
    assert result.exit_code == 0
    data = read_registry(monorepo)
    assert "9.9.9" not in data["models"]["fraud-detector"]["versions"]


def test_version_remove_referenced_fails(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["model", "version", "remove", "fraud-detector", "2.1.0"])
    assert result.exit_code == 1
    assert "referenced by" in result.output
