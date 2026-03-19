"""mgm.config.yml read/write."""
from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML

CONFIG_FILENAME = "mgm.config.yml"

_yaml = YAML()
_yaml.preserve_quotes = True
_yaml.default_flow_style = False


def find_config(registry_path: Path) -> Path:
    return registry_path.parent / CONFIG_FILENAME


def load_config(registry_path: Path) -> dict:
    cfg_path = find_config(registry_path)
    if not cfg_path.exists():
        return {}
    with open(cfg_path, "r", encoding="utf-8") as f:
        data = _yaml.load(f)
    return data or {}


def save_config(registry_path: Path, data: dict) -> None:
    cfg_path = find_config(registry_path)
    with open(cfg_path, "w", encoding="utf-8") as f:
        _yaml.dump(data, f)
