# Workflow Example

A complete end-to-end example of using MGM in a monorepo.

---

## Initial Setup

Run once at the monorepo root to configure the storage backend:

```bash
# Configure global commands (DVC in this example)
mgm config set pull-command "dvc pull {path}"
mgm config set push-command "dvc push {path}"

# Commit the config
git add mgm.config.yml
git commit -m "chore: add mgm global config"
```

---

## Registering Models

```bash
# Register models (no versions yet)
mgm model add fraud-detector --description "Detects fraudulent transactions"
mgm model add embedder --description "Text embedding model"

# Register the first versions after training
mgm model version add fraud-detector 1.0.0 \
  --path models/fraud-detector/v1.0.0 \
  --created-by jane@company.com

mgm model version add embedder 0.9.0 \
  --path models/embedder/v0.9.0 \
  --created-by jane@company.com

# Push model artifacts to storage
mgm push production@1.0.0   # (after creating the group below)

git add models.registry.yml
git commit -m "feat: register fraud-detector v1.0.0 and embedder v0.9.0"
```

---

## Creating the First Group Release

```bash
mgm group create production

mgm group release production 1.0.0 \
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
mgm app use production@1.0.0
git add mgm.yml
git commit -m "chore: use production@1.0.0 models"
```

To pull model files locally for development:

```bash
cd apps/fraud-service
mgm pull
```

---

## Releasing a New Model Version

When a new model is trained and ready:

```bash
# Register the new version
mgm model version add fraud-detector 2.0.0 \
  --path models/fraud-detector/v2.0.0 \
  --created-by jane@company.com

# Release a new group version that picks it up
mgm group release production 1.1.0 \
  --description "Upgraded fraud detector" \
  --model fraud-detector=2.0.0 \
  --model embedder=0.9.0        # unchanged

# Push the new model artifact
mgm push production@1.1.0

git add models.registry.yml
git commit -m "feat: release production@1.1.0 with fraud-detector v2.0.0"
```

---

## Apps Updating to the New Group

Each app opts in to the new version on its own schedule:

```bash
cd apps/fraud-service
mgm app use production@1.1.0
git add mgm.yml
git commit -m "chore: upgrade to production@1.1.0"
```

---

## Inspecting Changes

```bash
# See what changed between two group versions
mgm diff production@1.0.0 production@1.1.0
# Diff production@1.0.0 → production@1.1.0:
#   ~ fraud-detector: 1.0.0 → 2.0.0

# Validate the full registry
mgm validate

# See all group versions
mgm group show production
```
