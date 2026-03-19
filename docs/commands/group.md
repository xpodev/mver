# Group Commands

Manage model groups and their released versions.

---

## `mver group create`

Create a new named group with no versions yet.

```bash
mver group create <group-name>
```

**Fails if** a group with that name already exists.

```bash
mver group create production
mver group create staging
```

---

## `mver group release`

Create a new version of a group, pinning specific model versions.

```bash
mver group release <group-name> <version> \
  [--description TEXT] \
  [--model name=version] ...
```

| Argument | Required | Description |
|---|---|---|
| `group-name` | Yes | Name of an existing group |
| `version` | Yes | Semver version string |
| `--description` | No | Description of this release |
| `--model name=version` | No | Pin a model version (repeatable) |

For any registered model not covered by a `--model` flag, MVER prompts interactively.

**Validates before writing:**

- `version` is valid semver and strictly greater than the current latest version for the group
- `version` does not already exist in the group
- All specified model versions exist in the registry
- All validations pass before anything is written

**Examples:**

```bash
# Fully specified (good for scripts and CI)
mver group release production 1.4.0 \
  --description "Q1 release" \
  --model fraud-detector=2.1.0 \
  --model embedder=0.9.4

# Interactive — prompts for each model not specified
mver group release staging 0.3.0
# > Version for 'fraud-detector': 2.1.0
# > Version for 'embedder': 1.0.0-beta
```

---

## `mver group list`

List all groups and their latest version.

```bash
mver group list
```

**Example output:**

```
Group                          Latest Version
--------------------------------------------
production                     1.4.0
staging                        0.2.0
```

---

## `mver group show`

Show all versions of a group, or the details of a specific version.

```bash
# All versions
mver group show <group-name>

# Specific version
mver group show <group-name>@<version>
```

**Example — all versions:**

```bash
mver group show production
```

```
Group: production

  1.4.0  (2024-01-15T10:30:00Z)  Q1 release
    fraud-detector  2.1.0
    embedder        0.9.4

  1.3.0  (2024-01-01T09:00:00Z)  Initial production group
    fraud-detector  2.0.0
    embedder        0.9.0
```

**Example — specific version:**

```bash
mver group show production@1.4.0
```

```
Group version: production@1.4.0
  created_at:  2024-01-15T10:30:00Z
  created_by:  jane@company.com
  description: Q1 release

  Model           Version
  fraud-detector  2.1.0
  embedder        0.9.4
```
