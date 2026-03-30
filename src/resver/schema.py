"""
Schema: TypedDicts and helper accessors for registry structures.
"""
from __future__ import annotations

from typing import Any


def get_resources(registry: dict) -> dict[str, Any]:
    return registry.get("resources") or {}


def get_groups(registry: dict) -> dict[str, Any]:
    return registry.get("groups") or {}


def get_resource(registry: dict, name: str) -> dict[str, Any] | None:
    return get_resources(registry).get(name)


def get_group(registry: dict, name: str) -> dict[str, Any] | None:
    return get_groups(registry).get(name)


def get_resource_version(registry: dict, resource_name: str, version: str) -> dict[str, Any] | None:
    resource = get_resource(registry, resource_name)
    if resource is None:
        return None
    return (resource.get("versions") or {}).get(version)


def get_group_version(registry: dict, group_name: str, version: str) -> dict[str, Any] | None:
    group = get_group(registry, group_name)
    if group is None:
        return None
    return (group.get("versions") or {}).get(version)


def group_versions_referencing_resource(registry: dict, resource_name: str) -> list[str]:
    """Return list of 'group@version' strings that reference the given resource."""
    refs = []
    for gname, gdata in get_groups(registry).items():
        for ver, vdata in (gdata.get("versions") or {}).items():
            if resource_name in (vdata.get("resources") or {}):
                refs.append(f"{gname}@{ver}")
    return refs


def group_versions_referencing_resource_version(
    registry: dict, resource_name: str, resource_version: str
) -> list[str]:
    """Return list of 'group@version' strings that pin the given resource version."""
    refs = []
    for gname, gdata in get_groups(registry).items():
        for ver, vdata in (gdata.get("versions") or {}).items():
            if (vdata.get("resources") or {}).get(resource_name) == resource_version:
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