# Installation

## Requirements

- Python **3.11+**
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

---

## Install as a CLI Tool

The recommended way to install MGM globally is with `uv tool`:

```bash
uv tool install git+https://github.com/xpodev/mgm
```

After installation, `mgm` is available system-wide:

```bash
mgm --help
```

---

## Add to a Monorepo

To pin MGM as a dev dependency inside your monorepo:

```bash
uv add --dev mgm
```

Then run it via:

```bash
uv run mgm --help
```

---

## Install from Source

```bash
git clone https://github.com/xpodev/mgm
cd mgm
uv sync --all-groups
uv run mgm --help
```

---

## Verify Installation

```bash
# Should print the version
mgm --version

# From inside a monorepo with a registry file
mgm where
```
