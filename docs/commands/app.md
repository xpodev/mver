# App Commands

Manage an app's declared dependency on a model group. Run these from inside the app's directory.

---

## `mver app use`

Write or update `mver.yml` in the current directory to declare which group version this app depends on.

```bash
mver app use <group-name>@<version>
```

**Fails if:**

- The format is not `group@version`
- The group does not exist in the registry
- The version does not exist in that group
- The current directory is not inside the monorepo root

**Example:**

```bash
cd apps/fraud-service
mver app use production@1.4.0
# Writes mver.yml:
#   group: production
#   version: "1.4.0"
```

Commit the generated `mver.yml` to git so the declared version is tracked alongside the app's source code.

---

## `mver app show`

Read the local `mver.yml` and print the fully resolved model versions and artifact paths.

```bash
mver app show
```

**Example output:**

```
App uses group 'production@1.4.0':
  Model                          Version         Path
  ----------------------------------------------------------------------
  fraud-detector                 2.1.0           models/fraud-detector/v2.1.0
  embedder                       0.9.4           models/embedder/v0.9.4
```

**Fails if** no `mver.yml` is found in the current directory.

---

## `mver app check`

Validate that the group and version declared in `mver.yml` still exist in the registry. Exits with a non-zero code on failure.

```bash
mver app check
```

Intended for **CI pipelines** to catch stale `mver.yml` declarations early.

**Example — valid:**

```bash
mver app check
# OK: 'production@1.4.0' is valid.
# Exit code: 0
```

**Example — stale:**

```bash
mver app check
# Error: version '1.4.0' does not exist in group 'production' in registry.
# Exit code: 1
```
