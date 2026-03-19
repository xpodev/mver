# MVER — Model Group Manager

**MVER** is a CLI tool for managing ML model version groups in a monorepo. It acts as a **lock-file registry** — mapping named group versions to specific model versions, and letting apps declare which group they depend on.

Model storage and retrieval is fully delegated to user-defined shell commands. MVER is agnostic to your backend: DVC, S3, Git LFS, custom scripts, or anything else.

---

## Quick Start

```bash
# 1. Set your global pull/push backend
mver config set pull-command "dvc pull {path}"
mver config set push-command "dvc push {path}"

# 2. Register models and versions
mver model add fraud-detector --description "Fraud detection model"
mver model version add fraud-detector 2.1.0 --path models/fraud-detector/v2.1.0

# 3. Create a group and pin model versions to it
mver group create production
mver group release production 1.0.0 \
  --description "Initial release" \
  --model fraud-detector=2.1.0

# 4. In your app, declare the group version you depend on
cd apps/my-service
mver app use production@1.0.0

# 5. Pull all models locally
mver pull
```

---

## How It Works

```
models.registry.yml        mver.config.yml        apps/my-service/mver.yml
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

`mver pull` reads `mver.yml`, resolves the group version from the registry, and runs the configured command for each pinned model version.

---

## Key Properties

- **Backend-agnostic** — bring your own pull/push commands
- **Per-version overrides** — each model version can override the global command
- **Strict semver** — versions are enforced on both models and groups
- **Comment-preserving YAML** — `models.registry.yml` never loses hand-written comments
- **Git-friendly** — all files are plain text; MVER prints reminders to commit, never commits itself
