# Pull & Push

Execute storage commands for model artifacts.

---

## `mgm pull`

Pull all model artifacts for the current app's declared group version.

```bash
mgm pull
```

Must be run from an app directory containing a valid `mgm.yml`.

**Behavior:**

1. Reads `mgm.yml` from the current directory
2. Looks up the declared group version in the registry
3. Resolves the pull command for each pinned model version (see [Command Resolution](../command-resolution.md))
4. **Validates all commands** before executing any — fails fast if any model version has no resolvable pull command
5. Executes commands **sequentially** from the monorepo root
6. Halts on first failure; already-completed pulls are not rolled back

```bash
cd apps/fraud-service
mgm pull
# Pulling 'fraud-detector@2.1.0': dvc pull models/fraud-detector/v2.1.0
# Pulling 'embedder@0.9.4': dvc pull models/embedder/v0.9.4
# Pull complete.
```

!!! warning "No rollback"
    If a pull fails midway, successfully pulled models are not cleaned up. Re-run after fixing the issue.

---

## `mgm push`

Push model artifacts for a specific group version.

```bash
mgm push <group-name>@<version>
```

Does **not** require an `mgm.yml` — operates directly on a named group version. Useful for CI pipelines that publish models after training.

**Behavior:**

Same sequential execution and pre-validation as `mgm pull`, using push commands instead.

```bash
mgm push production@1.4.0
# Pushing 'fraud-detector@2.1.0': dvc push models/fraud-detector/v2.1.0
# Pushing 'embedder@0.9.4': dvc push models/embedder/v0.9.4
# Push complete.
```

---

## Error Conditions

| Situation | Behavior |
|---|---|
| No `mgm.yml` found (`pull`) | Fails with clear message before doing anything |
| Group/version not in registry | Fails before executing any commands |
| No resolvable command for a model version | Fails before executing any commands, identifying the affected model |
| A command exits with non-zero | Halts immediately, reports which model failed and the exit code |
