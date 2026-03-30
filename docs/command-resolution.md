# Command Resolution

When executing `resver pull` or `resver push`, RESVER determines the command to run for each resource version using the following priority order.

---

## Resolution Order

```
1. pull_command / push_command on the resource version entry
        │
        │  (if absent)
        ▼
2. pull_command / push_command in .resver/config.yml
        │
        │  (if absent)
        ▼
3. Error — fail before executing anything
```

This means:

- **Per-version overrides always win.** If a resource version declares its own command, the global config is ignored for that version.
- **The global config is the fallback.** Most versions will inherit from `.resver/config.yml`, keeping the registry clean.
- **Neither present → hard failure.** RESVER will not silently skip a resource. It reports exactly which version has no command configured and stops before running anything.

---

## Validation Happens Upfront

For both `pull` and `push`, RESVER resolves **all** resource versions' commands before executing any of them. If any version has no resolvable command, the entire operation fails immediately with a list of affected versions.

This prevents partial pulls/pushes caused by misconfiguration discovered mid-run.

---

## Example

Registry entry for `fraud-detector@2.0.0`:

```yaml
2.0.0:
  path: "resources/fraud-detector/v2.0.0"
  pull_command: "aws s3 sync s3://legacy/{path} ./{path}"
```

Global config:

```yaml
pull_command: "dvc pull {path}"
push_command: "dvc push {path}"
```

| resource version | Pull command used | Source |
|---|---|---|
| `fraud-detector@2.0.0` | `aws s3 sync s3://legacy/{path} ./{path}` | Version override |
| `fraud-detector@2.1.0` | `dvc pull {path}` | Global config |
| `embedder@0.9.4` | `dvc pull {path}` | Global config |

---

## Changing the Global Config Retroactively

Because commands are resolved at **execution time**, updating `.resver/config.yml` automatically affects all resource versions that don't have their own override — including versions registered in the past. No registry rewrite is needed.
