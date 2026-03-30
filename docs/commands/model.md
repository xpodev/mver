# resource Commands

Manage resources and their versions in the registry.

---

## `resver resource add`

Register a new resource with no versions yet.

```bash
resver resource add <name> [--description TEXT]
```

| Argument | Required | Description |
|---|---|---|
| `name` | Yes | Unique resource name |
| `--description` | No | Short description of the resource |

**Fails if** a resource with that name already exists.

**Example:**

```bash
resver resource add fraud-detector --description "Detects fraudulent transactions"
resver resource add embedder --description "Text embedding resource"
```

---

## `resver resource list`

List all registered resources with descriptions and version counts.

```bash
resver resource list
```

**Example output:**

```
resource                          Description                              Versions
--------------------------------------------------------------------------------
fraud-detector                 Detects fraudulent transactions                 2
embedder                       Text embedding resource                            1
```

---

## `resver resource remove`

Remove a resource from the registry.

```bash
resver resource remove <name>
```

**Fails if** the resource is referenced by any group version. The error lists all affected groups.

```bash
resver resource remove old-classifier
# Error: resource 'old-classifier' is referenced by:
#   production@1.3.0
#   staging@0.2.0
```

---

## `resver resource version add`

Register a new version of an existing resource.

```bash
resver resource version add <resource-name> <version> \
  --path <path> \
  [--pull-command TEXT] \
  [--push-command TEXT] \
  [--created-by TEXT]
```

| Argument | Required | Description |
|---|---|---|
| `resource-name` | Yes | Name of an existing resource |
| `version` | Yes | Seresver version string (e.g. `2.1.0`) |
| `--path` | Yes | Path to resource artifacts (relative to monorepo root) |
| `--pull-command` | No | Override the global pull command for this version |
| `--push-command` | No | Override the global push command for this version |
| `--created-by` | No | Author identifier (email, username, etc.) |

**Fails if:**

- `resource-name` does not exist in the registry
- `version` is not valid seresver
- That version already exists for the resource

**Examples:**

```bash
# Simple version using global config for pull/push
resver resource version add fraud-detector 2.1.0 \
  --path resources/fraud-detector/v2.1.0 \
  --created-by jane@company.com

# Version with its own pull/push commands
resver resource version add embedder 1.0.0 \
  --path resources/embedder/v1.0.0 \
  --pull-command "./scripts/pull_from_hf.sh {resource} {version}" \
  --push-command "./scripts/push_to_hf.sh {resource} {version}"
```

If `--pull-command` or `--push-command` are omitted, the version inherits from the global `.resver/config.yml` at runtime — nothing is written to the registry entry for those fields.

---

## `resver resource version list`

List all registered versions of a resource.

```bash
resver resource version list <resource-name>
```

**Example output:**

```
Versions of 'fraud-detector':
  2.1.0
    path:       resources/fraud-detector/v2.1.0
    created_at: 2024-01-15T10:30:00Z
    created_by: jane@company.com
  2.0.0
    path:       resources/fraud-detector/v2.0.0
    created_at: 2023-12-01T09:00:00Z
    created_by: john@company.com
    pull:       aws s3 sync s3://legacy/{path} ./{path}
    push:       aws s3 sync ./{path} s3://legacy/{path}
```

---

## `resver resource version remove`

Remove a resource version from the registry.

```bash
resver resource version remove <resource-name> <version>
```

**Fails if** the version is referenced by any group version. The error lists all affected groups.
