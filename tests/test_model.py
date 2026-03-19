"""Tests for mver model commands."""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from mver.cli import app
from tests.conftest import read_registry


def test_model_add(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["model", "add", "new-model", "--description", "A new model"])
    assert result.exit_code == 0, result.output
    data = read_registry(monorepo)
    assert "new-model" in data["models"]
    assert data["models"]["new-model"]["description"] == "A new model"


def test_model_add_no_description(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["model", "add", "bare-model"])
    assert result.exit_code == 0
    data = read_registry(monorepo)
    assert "bare-model" in data["models"]


def test_model_add_duplicate_fails(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["model", "add", "fraud-detector"])
    assert result.exit_code == 1
    assert "already exists" in result.output


def test_model_list(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["model", "list"])
    assert result.exit_code == 0
    assert "fraud-detector" in result.output
    assert "embedder" in result.output


def test_model_remove(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    # Add a model with no group references
    runner.invoke(app, ["model", "add", "unused-model"])
    result = runner.invoke(app, ["model", "remove", "unused-model"])
    assert result.exit_code == 0
    data = read_registry(monorepo)
    assert "unused-model" not in data["models"]


def test_model_remove_referenced_fails(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    # fraud-detector is referenced in production group
    result = runner.invoke(app, ["model", "remove", "fraud-detector"])
    assert result.exit_code == 1
    assert "referenced by" in result.output


def test_model_remove_nonexistent_fails(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["model", "remove", "ghost-model"])
    assert result.exit_code == 1
    assert "does not exist" in result.output
