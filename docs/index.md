# MGM — Model Group Manager

**MGM** is a CLI tool for managing ML model version groups in a monorepo. It acts as a **lock-file registry** — mapping named group versions to specific model versions, and letting apps declare which group they depend on.

Model storage and retrieval is fully delegated to user-defined shell commands. MGM is agnostic to your backend: DVC, S3, Git LFS, custom scripts, or anything else.

---

## Quick Start

```bash
# 1. Set your global pull/push backend
mgm config set pull-command "dvc pull {path}"
mgm config set push-command "dvc push {path}"

# 2. Register models and versions
mgm model add fraud-detector --description "Fraud detection model"
mgm model version add fraud-detector 2.1.0 --path models/fraud-detector/v2.1.0

# 3. Create a group and pin model versions to it
mgm group create production
mgm group release production 1.0.0 \
  --description "Initial release" \
  --model fraud-detector=2.1.0

# 4. In your app, declare the group version you depend on
cd apps/my-service
mgm app use production@1.0.0

# 5. Pull all models locally
mgm pull
```

---

## How It Works

```
models.registry.yml        mgm.config.yml        apps/my-service/mgm.yml
─────────────────────      ──────────────────     ──────────────────────────
models:                    pull_command:          group: production
  fraud-detector:            dvc pull {path}      version: "1.0.0"
    versions:
      2.1.0: ...
groups:
  production:
    versions:
      1.0.0:
        models:
          fraud-detector: "2.1.0"
```

`mgm pull` reads `mgm.yml`, resolves the group version from the registry, and runs the configured command for each pinned model version.

---

## Key Properties

- **Backend-agnostic** — bring your own pull/push commands
- **Per-version overrides** — each model version can override the global command
- **Strict semver** — versions are enforced on both models and groups
- **Comment-preserving YAML** — `models.registry.yml` never loses hand-written comments
- **Git-friendly** — all files are plain text; MGM prints reminders to commit, never commits itself
