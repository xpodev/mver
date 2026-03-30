# File Structure

RESVER uses three file types, all plain YAML, all meant to be committed to git. All configuration files live inside a `.resver/` directory.

---

## `.resver/registry.yml`

Lives at the **monorepo root** inside the `.resver/` directory. Single source of truth for all resources, versions, and groups.

```yaml
resources:
  fraud-detector:
    description: "Detects fraudulent transactions"
    versions:
      2.1.0:
        path: "resources/fraud-detector/v2.1.0"      # (1)
        created_at: "2024-01-15T10:30:00Z"
        created_by: "jane@company.com"
      2.0.0:
        path: "resources/fraud-detector/v2.0.0"
        created_at: "2023-12-01T09:00:00Z"
        created_by: "john@company.com"
        pull_command: "aws s3 sync s3://legacy/{path} ./{path}"  # (2)
        push_command: "aws s3 sync ./{path} s3://legacy/{path}"
  embedder:
    description: "Text embedding resource"
    versions:
      0.9.4:
        path: "resources/embedder/v0.9.4"
        pull_command: "./scripts/pull_from_hf.sh {resource} {version}"  # (3)

groups:
  production:
    versions:
      1.4.0:
        created_at: "2024-01-15T10:30:00Z"
        created_by: "jane@company.com"
        description: "Q1 release"
        resources:
          fraud-detector: "2.1.0"   # (4)
          embedder: "0.9.4"
      1.3.0:
        created_at: "2024-01-01T09:00:00Z"
        created_by: "john@company.com"
        description: "Initial production group"
        resources:
          fraud-detector: "2.0.0"
          embedder: "0.9.0"
  staging:
    versions:
      0.2.0:
        created_at: "2024-01-20T14:00:00Z"
        created_by: "jane@company.com"
        description: "Testing new embedder"
        resources:
          fraud-detector: "2.1.0"
          embedder: "1.0.0-beta"
```

1. `path` is relative to the monorepo root and substituted into commands via `{path}`
2. Per-version command overrides take priority over the global config
3. A resource can override only pull, only push, or both
4. Group versions pin exact resource versions by name

!!! note
    RESVER uses [ruamel.yaml](https://yaml.readthedocs.io/en/latest/) for all reads and writes, so hand-written YAML comments are preserved.

---

## `.resver/config.yml`

Lives at the **monorepo root** inside the `.resver/` directory, alongside `registry.yml`. Defines the global fallback pull and push commands used by any resource version that does not declare its own.

```yaml
pull_command: "dvc pull {path}"
push_command: "dvc push {path}"
```

**This file should be committed to git** so all team members share the same storage backend configuration.

If the file is absent, `resver pull` and `resver push` still work as long as every resource version has its own command override.

---

## `.resver/app.yml`

Lives at the **app root** inside the app's `.resver/` directory (one per app). Declares which group version this app depends on.

```yaml
group: production
version: "1.4.0"
```

Generated and updated by `resver app use`. Should be committed to git.

---

## Directory Layout

```
monorepo-root/
  .resver/
    registry.yml      # resource + group registry
    config.yml        # global pull/push commands
  apps/
    fraud-service/
      .resver/
        app.yml       # declares: group production@1.4.0
      src/
        ...
    risk-scorer/
      .resver/
        app.yml       # declares: group staging@0.2.0
      src/
        ...
```

---

## Discovery

RESVER finds `.resver/registry.yml` by walking up from the current working directory, the same convention as git. All commands fail with a clear message if no registry is found.

```
$ cd apps/fraud-service/src/handlers
$ resver where
/home/user/monorepo/.resver/registry.yml
```
