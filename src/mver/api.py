"""Public Python API for reading the mver registry, config, and app declarations."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import semver as _semver


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelVersion:
    """A specific, registered version of a model."""

    version: str
    path: str
    created_at: Optional[str] = None
    created_by: Optional[str] = None
    pull_command: Optional[str] = None
    push_command: Optional[str] = None


@dataclass(frozen=True)
class Model:
    """A registered model with all its versions."""

    name: str
    description: Optional[str]
    versions: dict  # str -> ModelVersion

    def get_version(self, version: str) -> Optional[ModelVersion]:
        """Return the ModelVersion for *version*, or ``None`` if not found."""
        return self.versions.get(version)

    @property
    def latest(self) -> Optional[ModelVersion]:
        """The highest semver version registered for this model."""
        if not self.versions:
            return None
        best = max(self.versions.keys(), key=_semver.Version.parse)
        return self.versions[best]


@dataclass(frozen=True)
class GroupVersion:
    """A specific released version of a group, pinning model versions."""

    version: str
    models: dict  # model_name -> version_string
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
    """Contents of ``mver.config.yml`` — the global pull/push backend config."""

    pull_command: Optional[str] = None
    push_command: Optional[str] = None

    @classmethod
    def load(cls, directory: Optional[Path] = None) -> "GlobalConfig":
        """Load ``mver.config.yml`` found alongside the registry.

        *directory* is the starting point for registry discovery (default: cwd).
        Returns an empty config if ``mver.config.yml`` does not exist.
        """
        from mver.config import load_config as _load_config
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
class ResolvedModel:
    """A model as seen by a specific app — version pinned, path and commands resolved."""

    name: str
    version: str
    path: str
    pull_command: Optional[str]
    push_command: Optional[str]


@dataclass
class ResolvedApp:
    """All models resolved for a specific app, ready to load."""

    group_name: str
    version: str
    models: dict  # model_name -> ResolvedModel

    def __getitem__(self, model_name: str) -> ResolvedModel:
        try:
            return self.models[model_name]
        except KeyError:
            raise KeyError(f"Model '{model_name}' is not in group '{self.group_name}@{self.version}'")

    def __iter__(self):
        return iter(self.models)

    def __len__(self) -> int:
        return len(self.models)

    def __repr__(self) -> str:
        pins = ", ".join(f"{n}@{m.version}" for n, m in self.models.items())
        return f"ResolvedApp('{self.group_name}@{self.version}', models=[{pins}])"


# ---------------------------------------------------------------------------
# AppConfig
# ---------------------------------------------------------------------------


class AppConfig:
    """Contents of a local ``mver.yml`` file.

    Example::

        from mver import AppConfig, Registry, GlobalConfig

        registry = Registry.find()
        config   = GlobalConfig.load()
        app      = AppConfig.load()

        resolved = app.resolve(registry, config)
        print(resolved["fraud-detector"].path)
    """

    _FILENAME = "mver.yml"

    def __init__(self, group: str, version: str, directory: Path) -> None:
        self.group = group
        self.version = version
        self.directory = directory

    def __repr__(self) -> str:
        return f"AppConfig(group='{self.group}', version='{self.version}', directory='{self.directory}')"

    @classmethod
    def load(cls, directory: Optional[Path] = None) -> "AppConfig":
        """Read ``mver.yml`` from *directory* (default: current working directory).

        Raises ``FileNotFoundError`` if the file does not exist.
        Raises ``ValueError`` if ``group`` or ``version`` is missing.
        """
        from ruamel.yaml import YAML
        d = (directory or Path.cwd()).resolve()
        cfg_path = d / cls._FILENAME
        if not cfg_path.exists():
            raise FileNotFoundError(
                f"'{cls._FILENAME}' not found in {d}. "
                "Run 'mver app use <group@version>' first."
            )
        _yaml = YAML()
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = _yaml.load(f) or {}
        group = data.get("group")
        version = str(data.get("version", ""))
        if not group or not version:
            raise ValueError(f"'{cls._FILENAME}' must contain both 'group' and 'version'.")
        return cls(group=group, version=version, directory=d)

    def resolve(
        self,
        registry: "Registry",
        config: Optional[GlobalConfig] = None,
    ) -> ResolvedApp:
        """Resolve all model versions for this app's declared group version.

        Args:
            registry: The loaded :class:`Registry`.
            config:   Optional :class:`GlobalConfig` for command fallback.
                      When provided, pull/push commands inherit the global defaults
                      for any model version that has no per-version override.

        Raises:
            ``KeyError`` if the group, version, or any pinned model/version is missing.
        """
        group = registry.get_group(self.group)
        if group is None:
            raise KeyError(f"Group '{self.group}' not found in registry.")
        gv = group.get_version(self.version)
        if gv is None:
            raise KeyError(
                f"Version '{self.version}' not found in group '{self.group}'."
            )
        resolved: dict[str, ResolvedModel] = {}
        for mname, mver_str in gv.models.items():
            model = registry.get_model(mname)
            if model is None:
                raise KeyError(f"Model '{mname}' not found in registry.")
            mv = model.get_version(mver_str)
            if mv is None:
                raise KeyError(f"Model version '{mname}@{mver_str}' not found in registry.")
            resolved[mname] = ResolvedModel(
                name=mname,
                version=mver_str,
                path=mv.path,
                pull_command=mv.pull_command or (config.pull_command if config else None),
                push_command=mv.push_command or (config.push_command if config else None),
            )
        return ResolvedApp(group_name=self.group, version=self.version, models=resolved)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class Registry:
    """The loaded ``models.registry.yml``.

    Typical usage::

        from mver import Registry

        registry = Registry.find()           # walks up from cwd
        model    = registry.models["fraud-detector"]
        version  = model.latest
        print(version.path)
    """

    def __init__(self, path: Path, models: dict, groups: dict) -> None:
        self.path = path
        self.models: dict[str, Model] = models
        self.groups: dict[str, Group] = groups

    @property
    def root(self) -> Path:
        """The monorepo root — the directory that contains ``models.registry.yml``."""
        return self.path.parent

    def get_model(self, name: str) -> Optional[Model]:
        """Return the :class:`Model` named *name*, or ``None``."""
        return self.models.get(name)

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
            f"models={list(self.models)}, "
            f"groups={list(self.groups)})"
        )

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def find(cls, start: Optional[Path] = None) -> "Registry":
        """Walk up from *start* (default: cwd) to find and load the registry.

        Raises ``FileNotFoundError`` if ``models.registry.yml`` is not found.
        """
        reg_path = _find_registry_path(start or Path.cwd())
        return cls._from_path(reg_path)

    @classmethod
    def load(cls, path: Path) -> "Registry":
        """Load the registry from an explicit file path."""
        return cls._from_path(path)

    @classmethod
    def _from_path(cls, path: Path) -> "Registry":
        from mver.registry import load_registry as _load_registry
        data, _ = _load_registry(path)
        models: dict[str, Model] = {}
        for mname, mdata in (data.get("models") or {}).items():
            mdata = mdata or {}
            versions: dict[str, ModelVersion] = {}
            for ver, vdata in (mdata.get("versions") or {}).items():
                vdata = vdata or {}
                versions[str(ver)] = ModelVersion(
                    version=str(ver),
                    path=vdata.get("path", ""),
                    created_at=vdata.get("created_at"),
                    created_by=vdata.get("created_by"),
                    pull_command=vdata.get("pull_command"),
                    push_command=vdata.get("push_command"),
                )
            models[mname] = Model(
                name=mname,
                description=mdata.get("description"),
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
                    models={k: str(v) for k, v in (vdata.get("models") or {}).items()},
                )
            groups[gname] = Group(name=gname, versions=gv_dict)
        return cls(path=path, models=models, groups=groups)


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _find_registry_path(start: Path) -> Path:
    """Walk up from *start* to find models.registry.yml.

    Raises ``FileNotFoundError`` (not typer.Exit) so callers get a proper
    Python exception.
    """
    import click
    from mver.registry import find_registry as _find_registry
    try:
        return _find_registry(start)
    except click.exceptions.Exit:
        raise FileNotFoundError(
            f"'models.registry.yml' not found in '{start}' or any parent directory."
        )
