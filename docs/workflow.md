# Workflow Example

A complete end-to-end example of using MVER in a monorepo.

---

## Initial Setup

Run once at the monorepo root to configure the storage backend:

```bash
# Configure global commands (DVC in this example)
mver config set pull-command "dvc pull {path}"
mver config set push-command "dvc push {path}"

# Commit the config
git add mver.config.yml
git commit -m "chore: add mver global config"
```

---

## Registering Models

```bash
# Register models (no versions yet)
mver model add fraud-detector --description "Detects fraudulent transactions"
mver model add embedder --description "Text embedding model"

# Register the first versions after training
mver model version add fraud-detector 1.0.0 \
  --path models/fraud-detector/v1.0.0 \
  --created-by jane@company.com

mver model version add embedder 0.9.0 \
  --path models/embedder/v0.9.0 \
  --created-by jane@company.com

# Push model artifacts to storage
mver push production@1.0.0   # (after creating the group below)

git add models.registry.yml
git commit -m "feat: register fraud-detector v1.0.0 and embedder v0.9.0"
```

---

## Creating the First Group Release

```bash
mver group create production

mver group release production 1.0.0 \
  --description "Initial production group" \
  --model fraud-detector=1.0.0 \
  --model embedder=0.9.0

git add models.registry.yml
git commit -m "feat: release production@1.0.0"
```

---

## Apps Consuming the Group

Each app that needs model artifacts declares which group version it depends on:

```bash
cd apps/fraud-service
mver app use production@1.0.0
git add mver.yml
git commit -m "chore: use production@1.0.0 models"
```

To pull model files locally for development:

```bash
cd apps/fraud-service
mver pull
```

---

## Releasing a New Model Version

When a new model is trained and ready:

```bash
# Register the new version
mver model version add fraud-detector 2.0.0 \
  --path models/fraud-detector/v2.0.0 \
  --created-by jane@company.com

# Release a new group version that picks it up
mver group release production 1.1.0 \
  --description "Upgraded fraud detector" \
  --model fraud-detector=2.0.0 \
  --model embedder=0.9.0        # unchanged

# Push the new model artifact
mver push production@1.1.0

git add models.registry.yml
git commit -m "feat: release production@1.1.0 with fraud-detector v2.0.0"
```

---

## Apps Updating to the New Group

Each app opts in to the new version on its own schedule:

```bash
cd apps/fraud-service
mver app use production@1.1.0
git add mver.yml
git commit -m "chore: upgrade to production@1.1.0"
```

---

## Inspecting Changes

```bash
# See what changed between two group versions
mver diff production@1.0.0 production@1.1.0
# Diff production@1.0.0 → production@1.1.0:
#   ~ fraud-detector: 1.0.0 → 2.0.0

# Validate the full registry
mver validate

# See all group versions
mver group show production
```
