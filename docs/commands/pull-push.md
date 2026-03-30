# Pull & Push

Execute storage commands for resource artifacts.

---

## `resver pull`

Pull all resource artifacts for the current app's declared group version.

```bash
resver pull
```

Must be run from an app directory containing a valid `.resver/app.yml`.

**Behavior:**

1. Reads `.resver/app.yml` from the current directory
2. Looks up the declared group version in the registry
3. Resolves the pull command for each pinned resource version (see [Command Resolution](../command-resolution.md))
4. **Validates all commands** before executing any — fails fast if any resource version has no resolvable pull command
5. Executes commands **sequentially** from the monorepo root
6. Halts on first failure; already-completed pulls are not rolled back

```bash
cd apps/fraud-service
resver pull
# Pulling 'fraud-detector@2.1.0': dvc pull resources/fraud-detector/v2.1.0
# Pulling 'embedder@0.9.4': dvc pull resources/embedder/v0.9.4
# Pull complete.
```

!!! warning "No rollback"
    If a pull fails midway, successfully pulled resources are not cleaned up. Re-run after fixing the issue.

---

## `resver push`

Push resource artifacts for a specific group version.

```bash
resver push <group-name>@<version>
```

Does **not** require a `.resver/app.yml` — operates directly on a named group version. Useful for CI pipelines that publish resources after training.

**Behavior:**

Same sequential execution and pre-validation as `resver pull`, using push commands instead.

```bash
resver push production@1.4.0
# Pushing 'fraud-detector@2.1.0': dvc push resources/fraud-detector/v2.1.0
# Pushing 'embedder@0.9.4': dvc push resources/embedder/v0.9.4
# Push complete.
```

---

## Error Conditions

| Situation | Behavior |
|---|---|
| No `.resver/app.yml` found (`pull`) | Fails with clear message before doing anything |
| Group/version not in registry | Fails before executing any commands |
| No resolvable command for a resource version | Fails before executing any commands, identifying the affected resource |
| A command exits with non-zero | Halts immediately, reports which resource failed and the exit code |
