# Workflow Example

A complete end-to-end example of using RESVER in a monorepo.

---

## Initial Setup

Run once at the monorepo root to configure the storage backend:

```bash
# Configure global commands (DVC in this example)
resver config set pull-command "dvc pull {path}"
resver config set push-command "dvc push {path}"

# Commit the config
git add .resver/config.yml
git commit -m "chore: add resver global config"
```

---

## Registering resources

```bash
# Register resources (no versions yet)
resver resource add fraud-detector --description "Detects fraudulent transactions"
resver resource add embedder --description "Text embedding resource"

# Register the first versions after training
resver resource version add fraud-detector 1.0.0 \
  --path resources/fraud-detector/v1.0.0 \
  --created-by jane@company.com

resver resource version add embedder 0.9.0 \
  --path resources/embedder/v0.9.0 \
  --created-by jane@company.com

# Push resource artifacts to storage
resver push production@1.0.0   # (after creating the group below)

git add .resver/registry.yml
git commit -m "feat: register fraud-detector v1.0.0 and embedder v0.9.0"
```

---

## Creating the First Group Release

```bash
resver group create production

resver group release production 1.0.0 \
  --description "Initial production group" \
  --resource fraud-detector=1.0.0 \
  --resource embedder=0.9.0

git add .resver/registry.yml
git commit -m "feat: release production@1.0.0"
```

---

## Apps Consuming the Group

Each app that needs resource artifacts declares which group version it depends on:

```bash
cd apps/fraud-service
resver app use production@1.0.0
git add .resver/app.yml
git commit -m "chore: use production@1.0.0 resources"
```

To pull resource files locally for development:

```bash
cd apps/fraud-service
resver pull
```

---

## Releasing a New resource Version

When a new resource is trained and ready:

```bash
# Register the new version
resver resource version add fraud-detector 2.0.0 \
  --path resources/fraud-detector/v2.0.0 \
  --created-by jane@company.com

# Release a new group version that picks it up
resver group release production 1.1.0 \
  --description "Upgraded fraud detector" \
  --resource fraud-detector=2.0.0 \
  --resource embedder=0.9.0        # unchanged

# Push the new resource artifact
resver push production@1.1.0

git add .resver/registry.yml
git commit -m "feat: release production@1.1.0 with fraud-detector v2.0.0"
```

---

## Apps Updating to the New Group

Each app opts in to the new version on its own schedule:

```bash
cd apps/fraud-service
resver app use production@1.1.0
git add .resver/app.yml
git commit -m "chore: upgrade to production@1.1.0"
```

---

## Inspecting Changes

```bash
# See what changed between two group versions
resver diff production@1.0.0 production@1.1.0
# Diff production@1.0.0 → production@1.1.0:
#   ~ fraud-detector: 1.0.0 → 2.0.0

# Validate the full registry
resver validate

# See all group versions
resver group show production
```
