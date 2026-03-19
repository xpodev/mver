# Utility Commands

---

## `mver where`

Print the path to the `models.registry.yml` file being used. Resolved by walking up from the current working directory — the same convention as git.

```bash
mver where
```

Useful for verifying which registry is in scope when working in a deep subdirectory.

```bash
$ cd apps/fraud-service/src/handlers
$ mver where
/home/user/monorepo/models.registry.yml
```

---

## `mver validate`

Validate the entire `models.registry.yml` for correctness and consistency.

```bash
mver validate
```

**Checks performed:**

- All model version strings are valid semver
- All group version strings are valid semver
- No duplicate group versions
- All model versions referenced by groups exist in the registry
- Every model version referenced by any group has a resolvable pull and push command (either a per-version override or via the global config)

**Example — passing:**

```
Validation OK — /home/user/monorepo/models.registry.yml
```

**Example — failing:**

```
Validation FAILED:
  - Group 'staging@0.2.0': model 'embedder@1.0.0-beta' not in registry
  - Group 'production@1.3.0': model 'embedder@0.9.0' has no pull_command
    (no version override and no global config)
```

Exit code is `1` on failure, making this suitable for CI.

---

## `mver diff`

Show which model versions changed between two versions of the same group.

```bash
mver diff <group-name>@<version-a> <group-name>@<version-b>
```

**Example:**

```bash
mver diff production@1.3.0 production@1.4.0
```

```
Diff production@1.3.0 → production@1.4.0:
  ~ fraud-detector: 2.0.0 → 2.1.0
  ~ embedder: 0.9.0 → 0.9.4
```

**Change indicators:**

| Symbol | Meaning |
|---|---|
| `~` | Version changed |
| `+` | Model added to the group |
| `-` | Model removed from the group |

Both refs must be from the same group; the command fails if they are from different groups.
