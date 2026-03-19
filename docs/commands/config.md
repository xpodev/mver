# Config Commands

Manage the global pull and push command configuration.

---

## `mver config set pull-command`

Set the global `pull_command` in `mver.config.yml`.

```bash
mver config set pull-command <command>
```

The command string may contain [tokens](../tokens.md) that are substituted at runtime.

**Examples:**

```bash
# DVC
mver config set pull-command "dvc pull {path}"

# AWS S3
mver config set pull-command "aws s3 sync s3://my-bucket/{path} ./{path}"

# Git LFS
mver config set pull-command "git lfs pull --include={path}"

# Custom script
mver config set pull-command "./scripts/pull_model.sh {model} {version} {path}"
```

---

## `mver config set push-command`

Set the global `push_command` in `mver.config.yml`.

```bash
mver config set push-command <command>
```

**Example:**

```bash
mver config set push-command "dvc push {path}"
```

---

## `mver config show`

Print the current global config.

```bash
mver config show
```

**Example output:**

```
pull_command: dvc pull {path}
push_command: dvc push {path}
```

If `mver.config.yml` is absent or empty:

```
(no global config — mver.config.yml not found or empty)
```

---

!!! tip "Commit `mver.config.yml`"
    Commit `mver.config.yml` to git so all team members share the same storage backend configuration without extra setup.
