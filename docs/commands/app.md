# App Commands

Manage an app's declared dependency on resource versions. Run these from inside the app's directory.

An app can declare its resource dependencies in two ways:

| Mode | Description |
|---|---|
| **Group mode** | Pin the app to a named group version (`production@1.4.0`) |
| **resource-pin mode** | Pin individual resource versions directly (`--resource name=version`) |

---

## `resver app use`

Write or update `.resver/app.yml` in the current directory.

### Group mode

```bash
resver app use <group-name>@<version>
```

Locks the app to a specific group version. All resource versions are resolved through the group.

```bash
cd apps/fraud-service
resver app use production@1.4.0
# Writes .resver/app.yml:
#   group: production
#   version: "1.4.0"
```

### resource-pin mode

```bash
resver app use --resource <name>=<version> [--resource <name>=<version> ...]
```

Locks the app to individual resource versions directly, without using a group.

```bash
cd apps/fraud-service
resver app use --resource fraud-detector=2.1.0 --resource embedder=0.9.4
# Writes .resver/app.yml:
#   resources:
#     fraud-detector: "2.1.0"
#     embedder: "0.9.4"
```

**Fails if:**

- The group or version does not exist in the registry (group mode)
- Any resource or version does not exist in the registry (resource-pin mode)
- A `--resource` flag is not in `name=version` format
- Both a positional `group@version` and `--resource` flags are supplied together
- The current directory is not inside the monorepo root

Commit the generated `.resver/app.yml` to git so the declared versions are tracked alongside the app's source code.

---

## `resver app show`

Read the local `.resver/app.yml` and print the fully resolved resource versions and artifact paths.

```bash
resver app show
```

**Group mode output:**

```
App uses group 'production@1.4.0':
  resource                          Version         Path
  ----------------------------------------------------------------------
  fraud-detector                 2.1.0           resources/fraud-detector/v2.1.0
  embedder                       0.9.4           resources/embedder/v0.9.4
```

**resource-pin mode output:**

```
App uses direct resource pins:
  resource                          Version         Path
  ----------------------------------------------------------------------
  fraud-detector                 2.1.0           resources/fraud-detector/v2.1.0
  embedder                       0.9.4           resources/embedder/v0.9.4
```

**Fails if** no `.resver/app.yml` is found in the current directory.

---

## `resver app check`

Validate that the declared resources/group still exist in the registry. Exits with a non-zero code on failure.

```bash
resver app check
```

Intended for **CI pipelines** to catch stale `.resver/app.yml` declarations early.

**Example — valid (group mode):**

```bash
resver app check
# OK: 'production@1.4.0' is valid.
# Exit code: 0
```

**Example — valid (resource-pin mode):**

```bash
resver app check
# OK: fraud-detector@2.1.0, embedder@0.9.4
# Exit code: 0
```

**Example — stale:**

```bash
resver app check
# Error: version '1.4.0' does not exist in group 'production' in registry.
# Exit code: 1
```
