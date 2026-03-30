"""Tests for resver resource commands."""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from resver.cli import app
from tests.conftest import read_registry


def test_resource_add(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["resource", "add", "new-model", "--description", "A new model"])
    assert result.exit_code == 0, result.output
    data = read_registry(monorepo)
    assert "new-model" in data["resources"]
    assert data["resources"]["new-model"]["description"] == "A new model"


def test_resource_add_no_description(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["resource", "add", "bare-model"])
    assert result.exit_code == 0
    data = read_registry(monorepo)
    assert "bare-model" in data["resources"]


def test_resource_add_duplicate_fails(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["resource", "add", "fraud-detector"])
    assert result.exit_code == 1
    assert "already exists" in result.output


def test_resource_list(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["resource", "list"])
    assert result.exit_code == 0
    assert "fraud-detector" in result.output
    assert "embedder" in result.output


def test_resource_remove(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    # Add a model with no group references
    runner.invoke(app, ["resource", "add", "unused-model"])
    result = runner.invoke(app, ["resource", "remove", "unused-model"])
    assert result.exit_code == 0
    data = read_registry(monorepo)
    assert "unused-model" not in data["resources"]


def test_resource_remove_referenced_fails(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    # fraud-detector is referenced in production group
    result = runner.invoke(app, ["resource", "remove", "fraud-detector"])
    assert result.exit_code == 1
    assert "referenced by" in result.output


def test_resource_remove_nonexistent_fails(monorepo: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    result = runner.invoke(app, ["resource", "remove", "ghost-model"])
    assert result.exit_code == 1
    assert "does not exist" in result.output
