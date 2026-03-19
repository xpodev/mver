# Model Group Manager (MGM) — Specification

## Overview

A CLI tool that manages model version groups in a monorepo. It acts as a lock-file registry: mapping named group versions to specific model versions, and allowing apps to declare which group they depend on.

Storage and retrieval of actual model files is fully delegated to user-defined shell commands — the tool is agnostic to how models are stored (DVC, S3, Git LFS, custom scripts, etc.).

---

## Core Concepts

- **Model** — A named ML artifact (e.g. `fraud-detector`, `embedder`).
- **Model Version** — A specific version of a model (e.g. `2.1.0`), registered with its own path and optional storage commands.
- **Model Group** — A named, versioned snapshot that pins multiple model versions (e.g. `production@1.4.0` contains `fraud-detector@2.1.0` and `embedder@0.9.4`).
- **App** — Any package in the monorepo that declares a dependency on a model group.

---

## File Structure

### `models.registry.yml` — monorepo root, one file, source of truth

```yaml
models:
  fraud-detector:
    description: "Detects fraudulent transactions"
    versions:
      2.1.0:
        path: "models/fraud-detector/v2.1.0"
        created_at: "2024-01-15T10:30:00Z"
        created_by: "jane@company.com"
      2.0.0:
        path: "models/fraud-detector/v2.0.0"
        created_at: "2023-12-01T09:00:00Z"
        created_by: "john@company.com"
        pull_command: "aws s3 sync s3://legacy-bucket/{path} ./{path}"
        push_command: "aws s3 sync ./{path} s3://legacy-bucket/{path}"
  embedder:
    description: "Text embedding model"
    versions:
      0.9.4:
        path: "models/embedder/v0.9.4"
        created_at: "2024-01-10T11:00:00Z"
        created_by: "jane@company.com"
        pull_command: "./scripts/pull_from_hf.sh {model} {version}"

groups:
  production:
    versions:
      1.4.0:
        created_at: "2024-01-15T10:30:00Z"
        created_by: "jane@company.com"
        description: "Q1 release"
        models:
          fraud-detector: "2.1.0"
          embedder: "0.9.4"
      1.3.0:
        created_at: "2024-01-01T09:00:00Z"
        created_by: "john@company.com"
        description: "Initial production group"
        models:
          fraud-detector: "2.0.0"
          embedder: "0.9.0"
  staging:
    versions:
      0.2.0:
        created_at: "2024-01-20T14:00:00Z"
        created_by: "jane@company.com"
        description: "Testing new embedder"
        models:
          fraud-detector: "2.1.0"
          embedder: "1.0.0-beta"
```

### `mgm.config.yml` — monorepo root, alongside the registry

Defines the global fallback pull and push commands. Per-version overrides in the registry take precedence.

```yaml
pull_command: "dvc pull {path}"
push_command: "dvc push {path}"
```

### `mgm.yml` — per app, at the app root

```yaml
group: production
version: "1.4.0"
```

---

## Command Tokens

These tokens are substituted at runtime in both global config commands and per-version command overrides.

| Token | Resolves to |
|---|---|
| `{path}` | The `path` field from the specific model version entry |
| `{model}` | The model's name |
| `{version}` | The pinned model version for the current operation |
| `{group}` | The group name being pulled or pushed |

---

## Command Resolution Order

When executing pull or push for a given model version, the tool resolves the command using this priority:

1. `pull_command` / `push_command` on the specific model version entry in the registry
2. `pull_command` / `push_command` in `mgm.config.yml`
3. If neither exists — fail with a clear message identifying which model version has no command configured

---

## CLI Commands

### Registry Discovery

**`mgm where`**
Prints the path to the `models.registry.yml` file being used. Resolved by walking up from cwd, same convention as git.

---

### Model Management

**`mgm model add <name>`**
Registers a new model with no versions yet.
- Flags: `--description`
- Fails if model name already exists

**`mgm model list`**
Lists all registered models with their descriptions and version count.

**`mgm model remove <name>`**
Removes a model from the registry.
- Fails if the model is referenced in any group version

---

### Model Version Management

**`mgm model version add <model-name> <version>`**
Registers a new version of an existing model.
- Flags: `--path` (required), `--pull-command`, `--push-command`, `--created-by`
- If `--pull-command` or `--push-command` are omitted, the version inherits from the global config at runtime — nothing is written to the registry entry for those fields
- Validates that `<version>` is valid semver
- Fails if that version already exists for the model
- Fails if `<model-name>` does not exist in the registry

**`mgm model version list <model-name>`**
Lists all registered versions of a model with their paths, commands (if overridden), and metadata.

**`mgm model version remove <model-name> <version>`**
Removes a model version from the registry.
- Fails if the version is referenced by any group version, with a list of affected groups

---

### Group Management

**`mgm group create <group-name>`**
Creates a new named group with no versions yet.
- Fails if group name already exists

**`mgm group release <group-name> <version>`**
Creates a new version of a group. Prompts the user to specify a model version for each registered model.
- Flags: `--description`, `--model <name>=<version>` (repeatable, skips prompt for that model)
- Validates that all specified model versions exist in the registry
- Validates that `<version>` is valid semver and greater than the latest existing version of this group
- Fails if the version already exists in that group
- Fails before writing anything if any validation fails

**`mgm group list`**
Lists all groups and their latest version.

**`mgm group show <group-name>`**
Lists all versions of a group with their model pins, timestamps, and descriptions.

**`mgm group show <group-name>@<version>`**
Shows details of a specific group version.

---

### App Management

**`mgm app use <group-name>@<version>`**
Writes or updates `mgm.yml` in the current working directory.
- Fails if the group or version does not exist in the registry
- Fails if not run from within a subdirectory of the monorepo root

**`mgm app show`**
Reads the local `mgm.yml` and prints the fully resolved model versions and paths for the current app.

**`mgm app check`**
Validates that the group and version declared in the local `mgm.yml` still exist in the registry. Intended for CI use. Exits with a non-zero code on failure.

---

### Pull / Push

**`mgm pull`**
Executes the resolved pull command for each model in the group version declared in the local `mgm.yml`.
- Must be run from an app directory containing a valid `mgm.yml`
- Resolves each model version's command using the resolution order above
- Executes commands sequentially from the monorepo root
- Halts on first failure and reports which model failed; already-completed pulls are not rolled back

**`mgm push <group-name>@<version>`**
Executes the resolved push command for each model in the specified group version.
- Does not require an `mgm.yml` — operates directly on a group version
- Same sequential execution and failure behavior as `mgm pull`

---

### Config Management

**`mgm config set pull-command <command>`**
Sets the global `pull_command` in `mgm.config.yml`.

**`mgm config set push-command <command>`**
Sets the global `push_command` in `mgm.config.yml`.

**`mgm config show`**
Prints the current global config.

---

### Utility

**`mgm validate`**
Validates the entire `models.registry.yml` for:
- Structural correctness
- All model versions referenced by groups exist in the registry
- All semver values are valid
- No duplicate group or model versions
- Every model version referenced by any group has a resolvable command (either its own or via the global config). Reports specifically which versions would have no command if global config is absent.

**`mgm diff <group-name>@<version-a> <group-name>@<version-b>`**
Shows which model versions changed between two group versions of the same group.

---

## Behavioral Rules

- The registry file is resolved by walking up from cwd until `models.registry.yml` is found, same convention as git. All commands fail clearly if no registry is found.
- All writes to the registry file must preserve existing formatting and comments.
- All commands that mutate the registry print a reminder to commit the changed files to git.
- No command automatically runs git operations.
- Semver is strictly enforced on both group versions and model versions.
- Pull and push commands are resolved per model version at execution time, not at registration time. Changing `mgm.config.yml` retroactively affects all versions that don't have their own override.
- Commands are executed as shell subprocesses from the monorepo root, not the app directory.
- The tool does not validate or interpret the content of pull/push commands — it executes them as-is and forwards stdout/stderr to the terminal.
- `mgm.config.yml` should be committed to git so all team members share the same backend config. If absent, `mgm pull` and `mgm push` still work as long as every model version has its own command override.

---

## Error Conditions

| Situation | Behavior |
|---|---|
| `models.registry.yml` not found anywhere up the directory tree | Exit with clear message and hint to run from inside monorepo |
| Model referenced in a group doesn't exist in the registry | `validate` catches it; `group release` blocks it |
| Model version referenced in a group doesn't exist under that model | `validate` catches it; `group release` blocks it |
| App `mgm.yml` references a group/version not in the registry | `app check` fails with details of what's missing |
| Semver violation on `group release` or `model version add` | Fail with explanation before writing anything |
| `mgm pull` run outside an app directory | Fail with clear message |
| `mgm pull` or `mgm push` with no resolvable command for a model version | Fail before executing any commands, listing all affected model versions |
| `model version remove` on a version referenced by a group | Fail with list of affected group versions |
| `model remove` on a model referenced by any group | Fail with list of affected group versions |
| A pull/push command exits with non-zero | Halt, surface the error and which model failed |

---

## Out of Scope

- Authentication or access control
- Model training or evaluation
- Automatically creating git commits or tags
- Any UI beyond the CLI
- Any opinion on the storage backend
- Rollback of partial pulls