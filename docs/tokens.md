# Command Tokens

Tokens are substituted at runtime in pull and push command strings — both in `mver.config.yml` and in per-version overrides.

---

## Token Reference

| Token | Resolves to |
|---|---|
| `{path}` | The `path` field from the specific model version entry |
| `{model}` | The model's name |
| `{version}` | The pinned model version string |
| `{group}` | The group name being pulled or pushed |

---

## Examples

### DVC (path only)

```yaml
pull_command: "dvc pull {path}"
push_command: "dvc push {path}"
```

For `fraud-detector@2.1.0` with `path: models/fraud-detector/v2.1.0`:

```
dvc pull models/fraud-detector/v2.1.0
```

---

### AWS S3 (path only)

```yaml
pull_command: "aws s3 sync s3://my-bucket/{path} ./{path}"
push_command: "aws s3 sync ./{path} s3://my-bucket/{path}"
```

Resolves to:

```
aws s3 sync s3://my-bucket/models/fraud-detector/v2.1.0 ./models/fraud-detector/v2.1.0
```

---

### Custom script (model + version)

```yaml
pull_command: "./scripts/pull_model.sh {model} {version}"
```

Resolves to:

```
./scripts/pull_model.sh fraud-detector 2.1.0
```

---

### Group-aware script

```yaml
pull_command: "./scripts/pull.sh {group} {model} {version} {path}"
```

Resolves to:

```
./scripts/pull.sh production fraud-detector 2.1.0 models/fraud-detector/v2.1.0
```

---

## Notes

- Token substitution is purely textual — no escaping or quoting is applied
- Tokens that are not present in the command string are silently ignored
- Commands are executed as shell subprocesses from the **monorepo root**
- MVER does not validate or interpret command content — it executes as-is and forwards all stdout/stderr to the terminal
