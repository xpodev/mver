# Python API

RESVER ships a Python API for reading the registry, config, and app declarations from within your own code — no subprocess calls needed.

```python
from resver import Registry, AppConfig, GlobalConfig

registry = Registry.find()
config   = GlobalConfig.load()
app      = AppConfig.load()

resolved = app.resolve(registry, config)

for name, resource in resolved.resources.items():
    print(f"{name} @ {resource.version}: {resource.path}")
```

---

## Installation

The API is part of the `resver` package — no extra install required.

```bash
uv add resver
```

---

## Quick Reference

| Class | Purpose |
|---|---|
| [`Registry`](#registry) | Load and query `.resver/registry.yml` |
| [`GlobalConfig`](#globalconfig) | Load `.resver/config.yml` |
| [`AppConfig`](#appconfig) | Load `.resver/app.yml` and resolve resources |
| [`ResolvedApp`](#resolvedapp) | Resolved resource set for a specific app |
| [`ResolvedModel`](#resolvedmodel) | A single resolved resource with path and commands |
| [`resource`](#resource) | A registered resource entry |
| [`ModelVersion`](#modelversion) | A specific version of a resource |
| [`Group`](#group) | A registered group entry |
| [`GroupVersion`](#groupversion) | A specific released version of a group |

---

## Registry

The main entry point. Loads and parses `.resver/registry.yml`.

```python
from resver import Registry

# Walk up from current working directory (like git)
registry = Registry.find()

# Walk up from a specific directory (useful in scripts)
registry = Registry.find(Path(__file__).parent)

# Load from an explicit path
registry = Registry.load(Path("/monorepo/.resver/registry.yml"))
```

### Properties

| Name | Type | Description |
|---|---|---|
| `path` | `Path` | Absolute path to `.resver/registry.yml` |
| `root` | `Path` | Monorepo root (parent of the `.resver/` directory) |
| `resources` | `dict[str, resource]` | All registered resources, keyed by name |
| `groups` | `dict[str, Group]` | All registered groups, keyed by name |

### Methods

```python
registry.get_model("fraud-detector")   # -> resource | None
registry.get_group("production")       # -> Group | None

# Convenience helpers — load .resver/config.yml and .resver/app.yml
config = registry.config()             # -> GlobalConfig
app    = registry.app_config()         # -> AppConfig (reads cwd/.resver/app.yml)
app    = registry.app_config(app_dir)  # -> AppConfig (reads app_dir/.resver/app.yml)
```

### Raises

`FileNotFoundError` — if no `.resver/registry.yml` is found walking up from `start`.

---

## GlobalConfig

Reads `.resver/config.yml` from the monorepo root.

```python
from resver import GlobalConfig

config = GlobalConfig.load()           # walks up from cwd
config = GlobalConfig.load(app_dir)    # walks up from app_dir
```

| Attribute | Type | Description |
|---|---|---|
| `pull_command` | `str \| None` | Global fallback pull command template |
| `push_command` | `str \| None` | Global fallback push command template |

Returns an instance with `None` values if `.resver/config.yml` does not exist.

---

## AppConfig

Reads `.resver/app.yml` from an app directory. Supports two modes depending on the file contents.

```python
from resver import AppConfig

app = AppConfig.load()           # reads cwd/.resver/app.yml
app = AppConfig.load(app_dir)    # reads app_dir/.resver/app.yml
```

**Group mode attributes** (when `.resver/app.yml` contains `group` + `version`):

| Attribute | Type | Description |
|---|---|---|
| `group` | `str \| None` | The declared group name |
| `version` | `str \| None` | The declared group version |
| `resources` | `None` | Always `None` in group mode |
| `directory` | `Path` | The directory the file was loaded from |

**resource-pin mode attributes** (when `.resver/app.yml` contains `resources`):

| Attribute | Type | Description |
|---|---|---|
| `group` | `None` | Always `None` in resource-pin mode |
| `version` | `None` | Always `None` in resource-pin mode |
| `resources` | `dict[str, str]` | `{model_name: version_string}` direct pins |
| `directory` | `Path` | The directory the file was loaded from |

### `resolve(registry, config=None) -> ResolvedApp`

Resolve full resource versions and paths. Works in both modes.

```python
resolved = app.resolve(registry)           # commands may be None
resolved = app.resolve(registry, config)   # commands inherit global fallback
```

### Raises

- `FileNotFoundError` — `.resver/app.yml` not found
- `ValueError` — `.resver/app.yml` has neither a `resources` key nor both `group` and `version`
- `KeyError` — group, version, resource, or resource version not found in registry

---

## ResolvedApp

The result of `AppConfig.resolve()`. Contains all resource versions pinned for the app, with paths and commands already resolved.

```python
resolved = app.resolve(registry, config)

resolved.group_name   # "production" (group mode) or None (resource-pin mode)
resolved.version      # "2.0.0" (group mode) or None (resource-pin mode)
resolved.resources       # dict[str, ResolvedModel]

# Dict-like access
resource = resolved["fraud-detector"]

# Iteration
for name in resolved:
    print(resolved[name].path)

# Length
print(len(resolved))
```

---

## ResolvedModel

A single resource as seen by an app — version pinned, path resolved, pull/push commands resolved from version override or global fallback.

| Attribute | Type | Description |
|---|---|---|
| `name` | `str` | resource name |
| `version` | `str` | Pinned version string |
| `path` | `str` | Artifact path (relative to monorepo root) |
| `pull_command` | `str \| None` | Resolved pull command (version override → global → `None`) |
| `push_command` | `str \| None` | Resolved push command (version override → global → `None`) |

---

## resource

A registered resource with all its versions.

```python
resource = registry.resources["fraud-detector"]
# or
resource = registry.get_model("fraud-detector")  # returns None if missing

resource.name          # "fraud-detector"
resource.description   # "Binary classifier for transaction fraud"
resource.versions      # dict[str, ModelVersion]
resource.latest        # ModelVersion with the highest semver

version = resource.get_version("2.0.0")   # ModelVersion | None
```

---

## ModelVersion

A specific registered version of a resource.

| Attribute | Type | Description |
|---|---|---|
| `version` | `str` | Semver version string |
| `path` | `str` | Artifact path |
| `created_at` | `str \| None` | ISO 8601 timestamp |
| `created_by` | `str \| None` | Author identifier |
| `pull_command` | `str \| None` | Per-version pull override (or `None`) |
| `push_command` | `str \| None` | Per-version push override (or `None`) |

---

## Group

A registered group with all its released versions.

```python
group = registry.groups["production"]
# or
group = registry.get_group("production")  # returns None if missing

group.name       # "production"
group.versions   # dict[str, GroupVersion]
group.latest     # GroupVersion with the highest semver

gv = group.get_version("2.0.0")   # GroupVersion | None
```

---

## GroupVersion

A specific released version of a group.

| Attribute | Type | Description |
|---|---|---|
| `version` | `str` | Semver version string |
| `resources` | `dict[str, str]` | `{model_name: version_string}` pins |
| `description` | `str \| None` | Release description |
| `created_at` | `str \| None` | ISO 8601 timestamp |
| `created_by` | `str \| None` | Author identifier |

---

## Usage Patterns

### Load everything from an app directory

```python
from pathlib import Path
from resver import Registry, AppConfig, GlobalConfig

APP_DIR = Path(__file__).parent

registry = Registry.find(APP_DIR)
config   = GlobalConfig.load(APP_DIR)
app      = AppConfig.load(APP_DIR)
resolved = app.resolve(registry, config)

clf_path = resolved["fraud-detector"].path
emb_path = resolved["embedder"].path
```

### Use Registry as the single entry point

```python
from pathlib import Path
from resver import Registry

APP_DIR = Path(__file__).parent

registry = Registry.find(APP_DIR)
resolved = registry.app_config(APP_DIR).resolve(registry, registry.config())
```

### Browse the registry without an app config

```python
from resver import Registry

registry = Registry.find()

# Inspect resources
for name, resource in registry.resources.items():
    print(f"{name}: latest={resource.latest.version}")

# Inspect groups
production = registry.get_group("production")
latest_gv  = production.latest
print(latest_gv.resources)   # {'fraud-detector': '2.0.0', 'embedder': '1.0.0'}
```

### Load a specific group version directly

```python
registry = Registry.find()
gv = registry.groups["production"].get_version("1.0.0")
for model_name, model_version in gv.resources.items():
    mv = registry.resources[model_name].get_version(model_version)
    print(f"{model_name}@{model_version}: {mv.path}")
```
