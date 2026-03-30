# Group Commands

Manage resource groups and their released versions.

---

## `resver group create`

Create a new named group with no versions yet.

```bash
resver group create <group-name>
```

**Fails if** a group with that name already exists.

```bash
resver group create production
resver group create staging
```

---

## `resver group release`

Create a new version of a group, pinning specific resource versions.

```bash
resver group release <group-name> <version> \
  [--description TEXT] \
  [--resource name=version] ...
```

| Argument | Required | Description |
|---|---|---|
| `group-name` | Yes | Name of an existing group |
| `version` | Yes | Semver version string |
| `--description` | No | Description of this release |
| `--resource name=version` | No | Pin a resource version (repeatable) |

For any registered resource not covered by a `--resource` flag, RESVER prompts interactively.

**Validates before writing:**

- `version` is valid semver and strictly greater than the current latest version for the group
- `version` does not already exist in the group
- All specified resource versions exist in the registry
- All validations pass before anything is written

**Examples:**

```bash
# Fully specified (good for scripts and CI)
resver group release production 1.4.0 \
  --description "Q1 release" \
  --resource fraud-detector=2.1.0 \
  --resource embedder=0.9.4

# Interactive — prompts for each resource not specified
resver group release staging 0.3.0
# > Version for 'fraud-detector': 2.1.0
# > Version for 'embedder': 1.0.0-beta
```

---

## `resver group list`

List all groups and their latest version.

```bash
resver group list
```

**Example output:**

```
Group                          Latest Version
--------------------------------------------
production                     1.4.0
staging                        0.2.0
```

---

## `resver group show`

Show all versions of a group, or the details of a specific version.

```bash
# All versions
resver group show <group-name>

# Specific version
resver group show <group-name>@<version>
```

**Example — all versions:**

```bash
resver group show production
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
resver group show production@1.4.0
```

```
Group version: production@1.4.0
  created_at:  2024-01-15T10:30:00Z
  created_by:  jane@company.com
  description: Q1 release

  resource           Version
  fraud-detector  2.1.0
  embedder        0.9.4
```
