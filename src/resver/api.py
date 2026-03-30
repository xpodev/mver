"""Public Python API for reading the resver registry, config, and app declarations."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import semver as _semver


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResourceVersion:
    """A specific, registered version of a resource."""

    version: str
    path: str
    created_at: Optional[str] = None
    created_by: Optional[str] = None
    pull_command: Optional[str] = None
    push_command: Optional[str] = None


@dataclass(frozen=True)
class Resource:
    """A registered resource with all its versions."""

    name: str
    description: Optional[str]
    versions: dict  # str -> ResourceVersion

    def get_version(self, version: str) -> Optional[ResourceVersion]:
        """Return the ResourceVersion for *version*, or ``None`` if not found."""
        return self.versions.get(version)

    @property
    def latest(self) -> Optional[ResourceVersion]:
        """The highest semver version registered for this resource."""
        if not self.versions:
            return None
        best = max(self.versions.keys(), key=_semver.Version.parse)
        return self.versions[best]


@dataclass(frozen=True)
class GroupVersion:
    """A specific released version of a group, pinning resource versions."""

    version: str
    resources: dict  # resource_name -> version_string
    description: Optional[str] = None
    created_at: Optional[str] = None
    created_by: Optional[str] = None


@dataclass(frozen=True)
class Group:
    """A named group with all its released versions."""

    name: str
    versions: dict  # str -> GroupVersion

    def get_version(self, version: str) -> Optional[GroupVersion]:
        """Return the GroupVersion for *version*, or ``None`` if not found."""
        return self.versions.get(version)

    @property
    def latest(self) -> Optional[GroupVersion]:
        """The highest semver version released for this group."""
        if not self.versions:
            return None
        best = max(self.versions.keys(), key=_semver.Version.parse)
        return self.versions[best]


@dataclass(frozen=True)
class GlobalConfig:
    """Contents of ``.resver/config.yml`` — the global pull/push backend config."""

    pull_command: Optional[str] = None
    push_command: Optional[str] = None

    @classmethod
    def load(cls, directory: Optional[Path] = None) -> "GlobalConfig":
        """Load ``.resver/config.yml`` found alongside the registry.

        *directory* is the starting point for registry discovery (default: cwd).
        Returns an empty config if ``.resver/config.yml`` does not exist.
        """
        from resver.config import load_config as _load_config
        reg_path = _find_registry_path(directory or Path.cwd())
        data = _load_config(reg_path)
        return cls(
            pull_command=data.get("pull_command"),
            push_command=data.get("push_command"),
        )


# ---------------------------------------------------------------------------
# Resolved objects (produced by AppConfig.resolve)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolvedResource:
    """A resource as seen by a specific app — version pinned, path and commands resolved."""

    name: str
    version: str
    path: str
    pull_command: Optional[str]
    push_command: Optional[str]


@dataclass
class ResolvedApp:
    """All resources resolved for a specific app, ready to load."""

    group_name: Optional[str]
    version: Optional[str]
    resources: dict  # resource_name -> ResolvedResource

    def __getitem__(self, resource_name: str) -> ResolvedResource:
        try:
            return self.resources[resource_name]
        except KeyError:
            if self.group_name:
                ctx = f"group '{self.group_name}@{self.version}'"
            else:
                ctx = "direct resource pins"
            raise KeyError(f"Resource '{resource_name}' is not in {ctx}")

    def __iter__(self):
        return iter(self.resources)

    def __len__(self) -> int:
        return len(self.resources)

    def __repr__(self) -> str:
        pins = ", ".join(f"{n}@{r.version}" for n, r in self.resources.items())
        if self.group_name:
            label = f"'{self.group_name}@{self.version}'"
        else:
            label = "(direct pins)"
        return f"ResolvedApp({label}, resources=[{pins}])"


# ---------------------------------------------------------------------------
# AppConfig
# ---------------------------------------------------------------------------


class AppConfig:
    """Contents of a local ``.resver/app.yml`` file.

    Example::

        from resver import AppConfig, Registry, GlobalConfig

        registry = Registry.find()
        config   = GlobalConfig.load()
        app      = AppConfig.load()

        resolved = app.resolve(registry, config)
        print(resolved["fraud-detector"].path)
    """

    _RESVER_DIR = ".resver"
    _FILENAME = "app.yml"

    def __init__(
        self,
        directory: Path,
        group: Optional[str] = None,
        version: Optional[str] = None,
        resources: Optional[dict] = None,
    ) -> None:
        self.group = group
        self.version = version
        self.resources = resources  # resource-pin mode: {name -> version_str}
        self.directory = directory

    def __repr__(self) -> str:
        if self.resources is not None:
            pins = ", ".join(f"{n}@{v}" for n, v in self.resources.items())
            return f"AppConfig(resources=[{pins}], directory='{self.directory}')"
        return f"AppConfig(group='{self.group}', version='{self.version}', directory='{self.directory}')"

    @classmethod
    def load(cls, directory: Optional[Path] = None) -> "AppConfig":
        """Read ``.resver/app.yml`` from *directory* (default: current working directory).

        Raises ``FileNotFoundError`` if the file does not exist.
        Raises ``ValueError`` if the file is neither a valid group-mode nor resource-pin-mode config.
        """
        from ruamel.yaml import YAML
        d = (directory or Path.cwd()).resolve()
        cfg_path = d / cls._RESVER_DIR / cls._FILENAME
        if not cfg_path.exists():
            raise FileNotFoundError(
                f"'{cls._RESVER_DIR}/{cls._FILENAME}' not found in {d}. "
                "Run 'resver app use <group@version>' or 'resver app use --resource name=version' first."
            )
        _yaml = YAML()
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = _yaml.load(f) or {}

        if "resources" in data:
            # resource-pin mode
            raw = data.get("resources") or {}
            return cls(directory=d, resources={k: str(v) for k, v in raw.items()})

        # group mode
        group = data.get("group")
        version = str(data.get("version", ""))
        if not group or not version:
            raise ValueError(
                f"'{cls._RESVER_DIR}/{cls._FILENAME}' must contain either 'resources' "
                "or both 'group' and 'version'."
            )
        return cls(directory=d, group=group, version=version)

    def resolve(
        self,
        registry: "Registry",
        config: Optional[GlobalConfig] = None,
    ) -> ResolvedApp:
        """Resolve all resource versions for this app.

        Supports two modes depending on ``.resver/app.yml`` contents:

        * **Group mode** — resolves all resources pinned in the declared group version.
        * **Resource-pin mode** — resolves each directly-pinned resource version.

        Args:
            registry: The loaded :class:`Registry`.
            config:   Optional :class:`GlobalConfig` for command fallback.
                      When provided, pull/push commands inherit the global defaults
                      for any resource version that has no per-version override.

        Raises:
            ``KeyError`` if any group, version, resource, or resource version is missing.
        """
        def _resolve_resource(rname: str, rver_str: str) -> ResolvedResource:
            resource = registry.get_resource(rname)
            if resource is None:
                raise KeyError(f"Resource '{rname}' not found in registry.")
            rv = resource.get_version(rver_str)
            if rv is None:
                raise KeyError(f"Resource version '{rname}@{rver_str}' not found in registry.")
            return ResolvedResource(
                name=rname,
                version=rver_str,
                path=rv.path,
                pull_command=rv.pull_command or (config.pull_command if config else None),
                push_command=rv.push_command or (config.push_command if config else None),
            )

        # --- resource-pin mode ---
        if self.resources is not None:
            resolved: dict[str, ResolvedResource] = {}
            for rname, rver_str in self.resources.items():
                resolved[rname] = _resolve_resource(rname, rver_str)
            return ResolvedApp(group_name=None, version=None, resources=resolved)

        # --- group mode ---
        group = registry.get_group(self.group)
        if group is None:
            raise KeyError(f"Group '{self.group}' not found in registry.")
        gv = group.get_version(self.version)
        if gv is None:
            raise KeyError(f"Version '{self.version}' not found in group '{self.group}'.")
        resolved = {}
        for rname, rver_str in gv.resources.items():
            resolved[rname] = _resolve_resource(rname, rver_str)
        return ResolvedApp(group_name=self.group, version=self.version, resources=resolved)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class Registry:
    """The loaded ``.resver/registry.yml``.

    Typical usage::

        from resver import Registry

        registry = Registry.find()           # walks up from cwd
        resource = registry.resources["fraud-detector"]
        version  = resource.latest
        print(version.path)
    """

    def __init__(self, path: Path, resources: dict, groups: dict) -> None:
        self.path = path
        self.resources: dict[str, Resource] = resources
        self.groups: dict[str, Group] = groups

    @property
    def root(self) -> Path:
        """The monorepo root — the directory that contains the ``.resver/`` directory with ``registry.yml``."""
        return self.path.parent.parent

    def get_resource(self, name: str) -> Optional[Resource]:
        """Return the :class:`Resource` named *name*, or ``None``."""
        return self.resources.get(name)

    def get_group(self, name: str) -> Optional[Group]:
        """Return the :class:`Group` named *name*, or ``None``."""
        return self.groups.get(name)

    def config(self) -> GlobalConfig:
        """Load the :class:`GlobalConfig` for this registry's monorepo root."""
        return GlobalConfig.load(self.root)

    def app_config(self, directory: Optional[Path] = None) -> AppConfig:
        """Load the :class:`AppConfig` from *directory* (default: cwd)."""
        return AppConfig.load(directory)

    def __repr__(self) -> str:
        return (
            f"Registry(path='{self.path}', "
            f"resources={list(self.resources)}, "
            f"groups={list(self.groups)})"
        )

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def find(cls, start: Optional[Path] = None) -> "Registry":
        """Walk up from *start* (default: cwd) to find and load the registry.

        Raises ``FileNotFoundError`` if ``.resver/registry.yml`` is not found.
        """
        reg_path = _find_registry_path(start or Path.cwd())
        return cls._from_path(reg_path)

    @classmethod
    def load(cls, path: Path) -> "Registry":
        """Load the registry from an explicit file path."""
        return cls._from_path(path)

    @classmethod
    def _from_path(cls, path: Path) -> "Registry":
        from resver.registry import load_registry as _load_registry
        data, _ = _load_registry(path)
        resources: dict[str, Resource] = {}
        for rname, rdata in (data.get("resources") or {}).items():
            rdata = rdata or {}
            versions: dict[str, ResourceVersion] = {}
            for ver, vdata in (rdata.get("versions") or {}).items():
                vdata = vdata or {}
                versions[str(ver)] = ResourceVersion(
                    version=str(ver),
                    path=vdata.get("path", ""),
                    created_at=vdata.get("created_at"),
                    created_by=vdata.get("created_by"),
                    pull_command=vdata.get("pull_command"),
                    push_command=vdata.get("push_command"),
                )
            resources[rname] = Resource(
                name=rname,
                description=rdata.get("description"),
                versions=versions,
            )
        groups: dict[str, Group] = {}
        for gname, gdata in (data.get("groups") or {}).items():
            gdata = gdata or {}
            gv_dict: dict[str, GroupVersion] = {}
            for ver, vdata in (gdata.get("versions") or {}).items():
                vdata = vdata or {}
                gv_dict[str(ver)] = GroupVersion(
                    version=str(ver),
                    description=vdata.get("description"),
                    created_at=vdata.get("created_at"),
                    created_by=vdata.get("created_by"),
                    resources={k: str(v) for k, v in (vdata.get("resources") or {}).items()},
                )
            groups[gname] = Group(name=gname, versions=gv_dict)
        return cls(path=path, resources=resources, groups=groups)


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _find_registry_path(start: Path) -> Path:
    """Walk up from *start* to find .resver/registry.yml.

    Raises ``FileNotFoundError`` (not typer.Exit) so callers get a proper
    Python exception.
    """
    import click
    from resver.registry import find_registry as _find_registry
    try:
        return _find_registry(start)
    except click.exceptions.Exit:
        raise FileNotFoundError(
            f"'.resver/registry.yml' not found in '{start}' or any parent directory."
        )
