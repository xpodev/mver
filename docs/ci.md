# CI Integration

RESVER is designed to work naturally inside CI pipelines.

---

## Validate the Registry

Run `resver validate` in CI to catch registry inconsistencies — broken resource references, missing commands, or invalid semver — before they reach production.

```yaml
# GitHub Actions
- name: Validate resource registry
  run: resver validate
```

Exits `1` on any validation failure, failing the pipeline.

---

## Check App Declarations

Run `resver app check` in each app's CI to verify its declared group version still exists in the registry. This catches stale `.resver/app.yml` files after a group version is superseded.

```yaml
- name: Check resource group declaration
  run: resver app check
  working-directory: apps/fraud-service
```

---

## Pull resources Before Tests

If your tests require actual resource artifacts, run `resver pull` as a CI step before running tests. Ensure your storage backend credentials are available as environment variables.

```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws-region: us-east-1

- name: Pull resource artifacts
  run: resver pull
  working-directory: apps/fraud-service
```

---

## Push After Training

After a resource training job, register the new version and push artifacts in one pipeline:

```yaml
- name: Register new resource version
  run: |
    resver resource version add fraud-detector ${{ env.MODEL_VERSION }} \
      --path resources/fraud-detector/v${{ env.MODEL_VERSION }} \
      --created-by ci@company.com

- name: Push resource artifacts
  run: resver push production@${{ env.GROUP_VERSION }}
```

---

## Suggested CI Checks by Repo Location

| Location | Recommended checks |
|---|---|
| Monorepo root / any PR | `resver validate` |
| Each app that uses resources | `resver app check` |
| resource training pipeline | `resver push <group@version>` after training |
| App that needs artifacts for tests | `resver pull` before test step |
