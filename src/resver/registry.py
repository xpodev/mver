"""Registry file discovery, loading, and saving via ruamel.yaml."""
from __future__ import annotations

from pathlib import Path

import typer
from ruamel.yaml import YAML

RESVER_DIR = ".resver"
REGISTRY_FILENAME = "registry.yml"

_yaml = YAML()
_yaml.preserve_quotes = True
_yaml.default_flow_style = False
_yaml.width = 4096  # prevent line wrapping


def find_registry(start: Path | None = None) -> Path:
    """Walk up from start (default: cwd) to find .resver/registry.yml."""
    current = (start or Path.cwd()).resolve()
    for directory in [current, *current.parents]:
        candidate = directory / RESVER_DIR / REGISTRY_FILENAME
        if candidate.exists():
            return candidate
    typer.echo(
        "Error: '.resver/registry.yml' not found in this directory or any parent.\n"
        "Hint: run resver from inside your monorepo.",
        err=True,
    )
    raise typer.Exit(1)


def load_registry(path: Path | None = None) -> tuple[dict, Path]:
    """Return (registry_dict, registry_path). Discovers path if not given."""
    registry_path = path or find_registry()
    with open(registry_path, "r", encoding="utf-8") as f:
        data = _yaml.load(f)
    if data is None:
        data = {}
    if "resources" not in data:
        data["resources"] = {}
    if "groups" not in data:
        data["groups"] = {}
    return data, registry_path


def save_registry(data: dict, path: Path) -> None:
    """Write registry back to disk, preserving ruamel formatting."""
    with open(path, "w", encoding="utf-8") as f:
        _yaml.dump(data, f)


def init_empty_registry(path: Path) -> None:
    """Create a new empty registry file."""
    path.parent.mkdir(exist_ok=True)
    data = {"models": {}, "groups": {}}
    with open(path, "w", encoding="utf-8") as f:
        _yaml.dump(data, f)
