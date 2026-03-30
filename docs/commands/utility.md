# Utility Commands

---

## `resver where`

Print the path to the `.resver/registry.yml` file being used. Resolved by walking up from the current working directory — the same convention as git.

```bash
resver where
```

Useful for verifying which registry is in scope when working in a deep subdirectory.

```bash
$ cd apps/fraud-service/src/handlers
$ resver where
/home/user/monorepo/.resver/registry.yml
```

---

## `resver validate`

Validate the entire `.resver/registry.yml` for correctness and consistency.

```bash
resver validate
```

**Checks performed:**

- All resource version strings are valid seresver
- All group version strings are valid seresver
- No duplicate group versions
- All resource versions referenced by groups exist in the registry
- Every resource version referenced by any group has a resolvable pull and push command (either a per-version override or via the global config)

**Example — passing:**

```
Validation OK — /home/user/monorepo/.resver/registry.yml
```

**Example — failing:**

```
Validation FAILED:
  - Group 'staging@0.2.0': resource 'embedder@1.0.0-beta' not in registry
  - Group 'production@1.3.0': resource 'embedder@0.9.0' has no pull_command
    (no version override and no global config)
```

Exit code is `1` on failure, making this suitable for CI.

---

## `resver diff`

Show which resource versions changed between two versions of the same group.

```bash
resver diff <group-name>@<version-a> <group-name>@<version-b>
```

**Example:**

```bash
resver diff production@1.3.0 production@1.4.0
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
| `+` | resource added to the group |
| `-` | resource removed from the group |

Both refs must be from the same group; the command fails if they are from different groups.
