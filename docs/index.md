# RESVER — resource Group Manager

**RESVER** is a CLI tool for managing ML resource version groups in a monorepo. It acts as a **lock-file registry** — mapping named group versions to specific resource versions, and letting apps declare which group they depend on.

resource storage and retrieval is fully delegated to user-defined shell commands. RESVER is agnostic to your backend: DVC, S3, Git LFS, custom scripts, or anything else.

---

## Quick Start

```bash
# 1. Set your global pull/push backend
resver config set pull-command "dvc pull {path}"
resver config set push-command "dvc push {path}"

# 2. Register resources and versions
resver resource add fraud-detector --description "Fraud detection resource"
resver resource version add fraud-detector 2.1.0 --path resources/fraud-detector/v2.1.0

# 3. Create a group and pin resource versions to it
resver group create production
resver group release production 1.0.0 \
  --description "Initial release" \
  --resource fraud-detector=2.1.0

# 4. In your app, declare the group version you depend on
cd apps/my-service
resver app use production@1.0.0

# 5. Pull all resources locally
resver pull
```

---

## How It Works

```
.resver/registry.yml         .resver/config.yml       apps/my-service/.resver/app.yml
──────────────────         ────────────────        ─────────────────────────────
resources:                    pull_command:           group: production
  fraud-detector:            dvc pull {path}       version: "1.0.0"
    versions:
      2.1.0: ...
groups:
  production:
    versions:
      1.0.0:
        resources:
          fraud-detector: "2.1.0"
```

`resver pull` reads `.resver/app.yml`, resolves the group version from the registry, and runs the configured command for each pinned resource version.

---

## Key Properties

- **Backend-agnostic** — bring your own pull/push commands
- **Per-version overrides** — each resource version can override the global command
- **Strict seresver** — versions are enforced on both resources and groups
- **Comment-preserving YAML** — `.resver/registry.yml` never loses hand-written comments
- **Git-friendly** — all files are plain text; RESVER prints reminders to commit, never commits itself
