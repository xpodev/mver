"""Tests for registry discovery and load/save."""
from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from mver.registry import find_registry, init_empty_registry, load_registry, save_registry

_yaml = YAML()


def test_find_registry_in_cwd(monorepo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(monorepo)
    found = find_registry()
    assert found == monorepo / "models.registry.yml"


def test_find_registry_from_subdir(monorepo: Path, app_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(app_dir)
    found = find_registry()
    assert found == monorepo / "models.registry.yml"


def test_find_registry_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import click
    monkeypatch.chdir(tmp_path)
    with pytest.raises(click.exceptions.Exit):
        find_registry()


def test_load_registry_returns_data(monorepo: Path) -> None:
    data, path = load_registry(monorepo / "models.registry.yml")
    assert "models" in data
    assert "groups" in data
    assert path == monorepo / "models.registry.yml"


def test_load_registry_empty_file(tmp_path: Path) -> None:
    reg = tmp_path / "models.registry.yml"
    reg.write_text("")
    data, _ = load_registry(reg)
    assert data == {"models": {}, "groups": {}}


def test_save_registry_round_trip(monorepo: Path) -> None:
    data, path = load_registry(monorepo / "models.registry.yml")
    data["models"]["new-model"] = {"description": "test", "versions": {}}
    save_registry(data, path)
    data2, _ = load_registry(path)
    assert "new-model" in data2["models"]


def test_init_empty_registry(tmp_path: Path) -> None:
    reg = tmp_path / "models.registry.yml"
    init_empty_registry(reg)
    data, _ = load_registry(reg)
    assert data == {"models": {}, "groups": {}}
