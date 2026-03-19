# CI Integration

MVER is designed to work naturally inside CI pipelines.

---

## Validate the Registry

Run `mver validate` in CI to catch registry inconsistencies — broken model references, missing commands, or invalid semver — before they reach production.

```yaml
# GitHub Actions
- name: Validate model registry
  run: mver validate
```

Exits `1` on any validation failure, failing the pipeline.

---

## Check App Declarations

Run `mver app check` in each app's CI to verify its declared group version still exists in the registry. This catches stale `mver.yml` files after a group version is superseded.

```yaml
- name: Check model group declaration
  run: mver app check
  working-directory: apps/fraud-service
```

---

## Pull Models Before Tests

If your tests require actual model artifacts, run `mver pull` as a CI step before running tests. Ensure your storage backend credentials are available as environment variables.

```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws-region: us-east-1

- name: Pull model artifacts
  run: mver pull
  working-directory: apps/fraud-service
```

---

## Push After Training

After a model training job, register the new version and push artifacts in one pipeline:

```yaml
- name: Register new model version
  run: |
    mver model version add fraud-detector ${{ env.MODEL_VERSION }} \
      --path models/fraud-detector/v${{ env.MODEL_VERSION }} \
      --created-by ci@company.com

- name: Push model artifacts
  run: mver push production@${{ env.GROUP_VERSION }}
```

---

## Suggested CI Checks by Repo Location

| Location | Recommended checks |
|---|---|
| Monorepo root / any PR | `mver validate` |
| Each app that uses models | `mver app check` |
| Model training pipeline | `mver push <group@version>` after training |
| App that needs artifacts for tests | `mver pull` before test step |
