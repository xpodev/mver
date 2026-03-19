# Python API

MVER ships a Python API for reading the registry, config, and app declarations from within your own code — no subprocess calls needed.

```python
from mver import Registry, AppConfig, GlobalConfig

registry = Registry.find()
config   = GlobalConfig.load()
app      = AppConfig.load()

resolved = app.resolve(registry, config)

for name, model in resolved.models.items():
    print(f"{name} @ {model.version}: {model.path}")
```

---

## Installation

The API is part of the `mver` package — no extra install required.

```bash
uv add mver
```

---

## Quick Reference

| Class | Purpose |
|---|---|
| [`Registry`](#registry) | Load and query `models.registry.yml` |
| [`GlobalConfig`](#globalconfig) | Load `mver.config.yml` |
| [`AppConfig`](#appconfig) | Load `mver.yml` and resolve models |
| [`ResolvedApp`](#resolvedapp) | Resolved model set for a specific app |
| [`ResolvedModel`](#resolvedmodel) | A single resolved model with path and commands |
| [`Model`](#model) | A registered model entry |
| [`ModelVersion`](#modelversion) | A specific version of a model |
| [`Group`](#group) | A registered group entry |
| [`GroupVersion`](#groupversion) | A specific released version of a group |

---

## Registry

The main entry point. Loads and parses `models.registry.yml`.

```python
from mver import Registry

# Walk up from current working directory (like git)
registry = Registry.find()

# Walk up from a specific directory (useful in scripts)
registry = Registry.find(Path(__file__).parent)

# Load from an explicit path
registry = Registry.load(Path("/monorepo/models.registry.yml"))
```

### Properties

| Name | Type | Description |
|---|---|---|
| `path` | `Path` | Absolute path to `models.registry.yml` |
| `root` | `Path` | Monorepo root (parent of `models.registry.yml`) |
| `models` | `dict[str, Model]` | All registered models, keyed by name |
| `groups` | `dict[str, Group]` | All registered groups, keyed by name |

### Methods

```python
registry.get_model("fraud-detector")   # -> Model | None
registry.get_group("production")       # -> Group | None

# Convenience helpers — load mver.config.yml and mver.yml
config = registry.config()             # -> GlobalConfig
app    = registry.app_config()         # -> AppConfig (reads cwd/mver.yml)
app    = registry.app_config(app_dir)  # -> AppConfig (reads app_dir/mver.yml)
```

### Raises

`FileNotFoundError` — if no `models.registry.yml` is found walking up from `start`.

---

## GlobalConfig

Reads `mver.config.yml` from the monorepo root.

```python
from mver import GlobalConfig

config = GlobalConfig.load()           # walks up from cwd
config = GlobalConfig.load(app_dir)    # walks up from app_dir
```

| Attribute | Type | Description |
|---|---|---|
| `pull_command` | `str \| None` | Global fallback pull command template |
| `push_command` | `str \| None` | Global fallback push command template |

Returns an instance with `None` values if `mver.config.yml` does not exist.

---

## AppConfig

Reads `mver.yml` from an app directory.

```python
from mver import AppConfig

app = AppConfig.load()           # reads cwd/mver.yml
app = AppConfig.load(app_dir)    # reads app_dir/mver.yml
```

| Attribute | Type | Description |
|---|---|---|
| `group` | `str` | The declared group name |
| `version` | `str` | The declared group version |
| `directory` | `Path` | The directory the file was loaded from |

### `resolve(registry, config=None) -> ResolvedApp`

Resolve full model versions and paths for the declared group version.

```python
resolved = app.resolve(registry)           # commands may be None
resolved = app.resolve(registry, config)   # commands inherit global fallback
```

### Raises

- `FileNotFoundError` — `mver.yml` not found
- `ValueError` — `mver.yml` missing `group` or `version`
- `KeyError` — group, version, model, or model version not found in registry

---

## ResolvedApp

The result of `AppConfig.resolve()`. Contains all model versions pinned to the declared group version, with paths and commands already resolved.

```python
resolved = app.resolve(registry, config)

resolved.group_name   # "production"
resolved.version      # "2.0.0"
resolved.models       # dict[str, ResolvedModel]

# Dict-like access
model = resolved["fraud-detector"]

# Iteration
for name in resolved:
    print(resolved[name].path)

# Length
print(len(resolved))
```

---

## ResolvedModel

A single model as seen by an app — version pinned, path resolved, pull/push commands resolved from version override or global fallback.

| Attribute | Type | Description |
|---|---|---|
| `name` | `str` | Model name |
| `version` | `str` | Pinned version string |
| `path` | `str` | Artifact path (relative to monorepo root) |
| `pull_command` | `str \| None` | Resolved pull command (version override → global → `None`) |
| `push_command` | `str \| None` | Resolved push command (version override → global → `None`) |

---

## Model

A registered model with all its versions.

```python
model = registry.models["fraud-detector"]
# or
model = registry.get_model("fraud-detector")  # returns None if missing

model.name          # "fraud-detector"
model.description   # "Binary classifier for transaction fraud"
model.versions      # dict[str, ModelVersion]
model.latest        # ModelVersion with the highest semver

version = model.get_version("2.0.0")   # ModelVersion | None
```

---

## ModelVersion

A specific registered version of a model.

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
| `models` | `dict[str, str]` | `{model_name: version_string}` pins |
| `description` | `str \| None` | Release description |
| `created_at` | `str \| None` | ISO 8601 timestamp |
| `created_by` | `str \| None` | Author identifier |

---

## Usage Patterns

### Load everything from an app directory

```python
from pathlib import Path
from mver import Registry, AppConfig, GlobalConfig

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
from mver import Registry

APP_DIR = Path(__file__).parent

registry = Registry.find(APP_DIR)
resolved = registry.app_config(APP_DIR).resolve(registry, registry.config())
```

### Browse the registry without an app config

```python
from mver import Registry

registry = Registry.find()

# Inspect models
for name, model in registry.models.items():
    print(f"{name}: latest={model.latest.version}")

# Inspect groups
production = registry.get_group("production")
latest_gv  = production.latest
print(latest_gv.models)   # {'fraud-detector': '2.0.0', 'embedder': '1.0.0'}
```

### Load a specific group version directly

```python
registry = Registry.find()
gv = registry.groups["production"].get_version("1.0.0")
for model_name, model_version in gv.models.items():
    mv = registry.models[model_name].get_version(model_version)
    print(f"{model_name}@{model_version}: {mv.path}")
```
