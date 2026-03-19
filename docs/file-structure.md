# File Structure

MGM uses three file types, all plain YAML, all meant to be committed to git.

---

## `models.registry.yml`

Lives at the **monorepo root**. Single source of truth for all models, versions, and groups.

```yaml
models:
  fraud-detector:
    description: "Detects fraudulent transactions"
    versions:
      2.1.0:
        path: "models/fraud-detector/v2.1.0"      # (1)
        created_at: "2024-01-15T10:30:00Z"
        created_by: "jane@company.com"
      2.0.0:
        path: "models/fraud-detector/v2.0.0"
        created_at: "2023-12-01T09:00:00Z"
        created_by: "john@company.com"
        pull_command: "aws s3 sync s3://legacy/{path} ./{path}"  # (2)
        push_command: "aws s3 sync ./{path} s3://legacy/{path}"
  embedder:
    description: "Text embedding model"
    versions:
      0.9.4:
        path: "models/embedder/v0.9.4"
        pull_command: "./scripts/pull_from_hf.sh {model} {version}"  # (3)

groups:
  production:
    versions:
      1.4.0:
        created_at: "2024-01-15T10:30:00Z"
        created_by: "jane@company.com"
        description: "Q1 release"
        models:
          fraud-detector: "2.1.0"   # (4)
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

1. `path` is relative to the monorepo root and substituted into commands via `{path}`
2. Per-version command overrides take priority over the global config
3. A model can override only pull, only push, or both
4. Group versions pin exact model versions by name

!!! note
    MGM uses [ruamel.yaml](https://yaml.readthedocs.io/en/latest/) for all reads and writes, so hand-written YAML comments are preserved.

---

## `mgm.config.yml`

Lives at the **monorepo root**, alongside `models.registry.yml`. Defines the global fallback pull and push commands used by any model version that does not declare its own.

```yaml
pull_command: "dvc pull {path}"
push_command: "dvc push {path}"
```

**This file should be committed to git** so all team members share the same storage backend configuration.

If the file is absent, `mgm pull` and `mgm push` still work as long as every model version has its own command override.

---

## `mgm.yml`

Lives at the **app root** (one per app). Declares which group version this app depends on.

```yaml
group: production
version: "1.4.0"
```

Generated and updated by `mgm app use`. Should be committed to git.

---

## Discovery

MGM finds `models.registry.yml` by walking up from the current working directory, the same convention as git. All commands fail with a clear message if no registry is found.

```
$ cd apps/fraud-service/src/handlers
$ mgm where
/home/user/monorepo/models.registry.yml
```
