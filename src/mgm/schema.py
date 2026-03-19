"""
Schema: TypedDicts and helper accessors for registry structures.
"""
from __future__ import annotations

from typing import Any


def get_models(registry: dict) -> dict[str, Any]:
    return registry.get("models") or {}


def get_groups(registry: dict) -> dict[str, Any]:
    return registry.get("groups") or {}


def get_model(registry: dict, name: str) -> dict[str, Any] | None:
    return get_models(registry).get(name)


def get_group(registry: dict, name: str) -> dict[str, Any] | None:
    return get_groups(registry).get(name)


def get_model_version(registry: dict, model_name: str, version: str) -> dict[str, Any] | None:
    model = get_model(registry, model_name)
    if model is None:
        return None
    return (model.get("versions") or {}).get(version)


def get_group_version(registry: dict, group_name: str, version: str) -> dict[str, Any] | None:
    group = get_group(registry, group_name)
    if group is None:
        return None
    return (group.get("versions") or {}).get(version)


def group_versions_referencing_model(registry: dict, model_name: str) -> list[str]:
    """Return list of 'group@version' strings that reference the given model."""
    refs = []
    for gname, gdata in get_groups(registry).items():
        for ver, vdata in (gdata.get("versions") or {}).items():
            if model_name in (vdata.get("models") or {}):
                refs.append(f"{gname}@{ver}")
    return refs


def group_versions_referencing_model_version(
    registry: dict, model_name: str, model_version: str
) -> list[str]:
    """Return list of 'group@version' strings that pin the given model version."""
    refs = []
    for gname, gdata in get_groups(registry).items():
        for ver, vdata in (gdata.get("versions") or {}).items():
            if (vdata.get("models") or {}).get(model_name) == model_version:
                refs.append(f"{gname}@{ver}")
    return refs


def latest_group_version(registry: dict, group_name: str) -> str | None:
    """Return the latest semver version string of a group, or None."""
    import semver

    group = get_group(registry, group_name)
    if not group:
        return None
    versions = list((group.get("versions") or {}).keys())
    if not versions:
        return None
    return str(max(semver.VersionInfo.parse(v) for v in versions))
