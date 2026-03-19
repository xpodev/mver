# App Commands

Manage an app's declared dependency on a model group. Run these from inside the app's directory.

---

## `mgm app use`

Write or update `mgm.yml` in the current directory to declare which group version this app depends on.

```bash
mgm app use <group-name>@<version>
```

**Fails if:**

- The format is not `group@version`
- The group does not exist in the registry
- The version does not exist in that group
- The current directory is not inside the monorepo root

**Example:**

```bash
cd apps/fraud-service
mgm app use production@1.4.0
# Writes mgm.yml:
#   group: production
#   version: "1.4.0"
```

Commit the generated `mgm.yml` to git so the declared version is tracked alongside the app's source code.

---

## `mgm app show`

Read the local `mgm.yml` and print the fully resolved model versions and artifact paths.

```bash
mgm app show
```

**Example output:**

```
App uses group 'production@1.4.0':
  Model                          Version         Path
  ----------------------------------------------------------------------
  fraud-detector                 2.1.0           models/fraud-detector/v2.1.0
  embedder                       0.9.4           models/embedder/v0.9.4
```

**Fails if** no `mgm.yml` is found in the current directory.

---

## `mgm app check`

Validate that the group and version declared in `mgm.yml` still exist in the registry. Exits with a non-zero code on failure.

```bash
mgm app check
```

Intended for **CI pipelines** to catch stale `mgm.yml` declarations early.

**Example — valid:**

```bash
mgm app check
# OK: 'production@1.4.0' is valid.
# Exit code: 0
```

**Example — stale:**

```bash
mgm app check
# Error: version '1.4.0' does not exist in group 'production' in registry.
# Exit code: 1
```
