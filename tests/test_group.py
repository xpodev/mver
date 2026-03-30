"""Tests for resver group commands."""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from resver.cli import app
from tests.conftest import read_registry


def test_group_create(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["group", "create", "staging"])
    assert result.exit_code == 0, result.output
    data = read_registry(monorepo)
    assert "staging" in data["groups"]


def test_group_create_duplicate_fails(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["group", "create", "production"])
    assert result.exit_code == 1
    assert "already exists" in result.output


def test_group_release(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(
        app,
        [
            "group", "release", "production", "2.0.0",
            "--description", "Next release",
            "--resource", "fraud-detector=2.1.0",
            "--resource", "embedder=0.9.4",
        ],
    )
    assert result.exit_code == 0, result.output
    data = read_registry(monorepo)
    assert "2.0.0" in data["groups"]["production"]["versions"]


def test_group_release_invalid_semver(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(
        app,
        ["group", "release", "production", "bad", "--resource", "fraud-detector=2.1.0", "--resource", "embedder=0.9.4"],
    )
    assert result.exit_code == 1
    assert "not a valid semver" in result.output


def test_group_release_not_greater_than_latest(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(
        app,
        [
            "group", "release", "production", "0.0.1",
            "--resource", "fraud-detector=2.1.0",
            "--resource", "embedder=0.9.4",
        ],
    )
    assert result.exit_code == 1
    assert "greater than" in result.output


def test_group_release_unknown_resource_version_fails(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(
        app,
        [
            "group", "release", "production", "2.0.0",
            "--resource", "fraud-detector=99.0.0",
            "--resource", "embedder=0.9.4",
        ],
    )
    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_group_release_duplicate_version_fails(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(
        app,
        [
            "group", "release", "production", "1.0.0",
            "--resource", "fraud-detector=2.1.0",
            "--resource", "embedder=0.9.4",
        ],
    )
    assert result.exit_code == 1
    assert "already exists" in result.output


def test_group_list(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["group", "list"])
    assert result.exit_code == 0
    assert "production" in result.output
    assert "1.0.0" in result.output


def test_group_show_all_versions(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["group", "show", "production"])
    assert result.exit_code == 0
    assert "1.0.0" in result.output
    assert "fraud-detector" in result.output


def test_group_show_specific_version(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["group", "show", "production@1.0.0"])
    assert result.exit_code == 0
    assert "fraud-detector" in result.output
    assert "2.1.0" in result.output


def test_group_show_missing_version_fails(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["group", "show", "production@9.9.9"])
    assert result.exit_code == 1
    assert "does not exist" in result.output
