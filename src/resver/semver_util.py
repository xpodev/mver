"""Semver validation helpers."""
from __future__ import annotations

import semver


def validate_semver(v: str) -> semver.VersionInfo:
    """Parse and return a VersionInfo, raising ValueError on invalid input."""
    try:
        return semver.VersionInfo.parse(v)
    except ValueError:
        raise ValueError(f"'{v}' is not a valid semver version (expected X.Y.Z)")


def is_greater_than(v_new: str, v_existing: str) -> bool:
    return semver.VersionInfo.parse(v_new) > semver.VersionInfo.parse(v_existing)
