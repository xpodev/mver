# Model Commands

Manage models and their versions in the registry.

---

## `mgm model add`

Register a new model with no versions yet.

```bash
mgm model add <name> [--description TEXT]
```

| Argument | Required | Description |
|---|---|---|
| `name` | Yes | Unique model name |
| `--description` | No | Short description of the model |

**Fails if** a model with that name already exists.

**Example:**

```bash
mgm model add fraud-detector --description "Detects fraudulent transactions"
mgm model add embedder --description "Text embedding model"
```

---

## `mgm model list`

List all registered models with descriptions and version counts.

```bash
mgm model list
```

**Example output:**

```
Model                          Description                              Versions
--------------------------------------------------------------------------------
fraud-detector                 Detects fraudulent transactions                 2
embedder                       Text embedding model                            1
```

---

## `mgm model remove`

Remove a model from the registry.

```bash
mgm model remove <name>
```

**Fails if** the model is referenced by any group version. The error lists all affected groups.

```bash
mgm model remove old-classifier
# Error: model 'old-classifier' is referenced by:
#   production@1.3.0
#   staging@0.2.0
```

---

## `mgm model version add`

Register a new version of an existing model.

```bash
mgm model version add <model-name> <version> \
  --path <path> \
  [--pull-command TEXT] \
  [--push-command TEXT] \
  [--created-by TEXT]
```

| Argument | Required | Description |
|---|---|---|
| `model-name` | Yes | Name of an existing model |
| `version` | Yes | Semver version string (e.g. `2.1.0`) |
| `--path` | Yes | Path to model artifacts (relative to monorepo root) |
| `--pull-command` | No | Override the global pull command for this version |
| `--push-command` | No | Override the global push command for this version |
| `--created-by` | No | Author identifier (email, username, etc.) |

**Fails if:**

- `model-name` does not exist in the registry
- `version` is not valid semver
- That version already exists for the model

**Examples:**

```bash
# Simple version using global config for pull/push
mgm model version add fraud-detector 2.1.0 \
  --path models/fraud-detector/v2.1.0 \
  --created-by jane@company.com

# Version with its own pull/push commands
mgm model version add embedder 1.0.0 \
  --path models/embedder/v1.0.0 \
  --pull-command "./scripts/pull_from_hf.sh {model} {version}" \
  --push-command "./scripts/push_to_hf.sh {model} {version}"
```

If `--pull-command` or `--push-command` are omitted, the version inherits from the global `mgm.config.yml` at runtime — nothing is written to the registry entry for those fields.

---

## `mgm model version list`

List all registered versions of a model.

```bash
mgm model version list <model-name>
```

**Example output:**

```
Versions of 'fraud-detector':
  2.1.0
    path:       models/fraud-detector/v2.1.0
    created_at: 2024-01-15T10:30:00Z
    created_by: jane@company.com
  2.0.0
    path:       models/fraud-detector/v2.0.0
    created_at: 2023-12-01T09:00:00Z
    created_by: john@company.com
    pull:       aws s3 sync s3://legacy/{path} ./{path}
    push:       aws s3 sync ./{path} s3://legacy/{path}
```

---

## `mgm model version remove`

Remove a model version from the registry.

```bash
mgm model version remove <model-name> <version>
```

**Fails if** the version is referenced by any group version. The error lists all affected groups.
