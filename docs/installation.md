# Installation

## Requirements

- Python **3.11+**
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

---

## Install as a CLI Tool

The recommended way to install MVER globally is with `uv tool`:

```bash
uv tool install git+https://github.com/xpodev/mver
```

After installation, `mver` is available system-wide:

```bash
mver --help
```

---

## Add to a Monorepo

To pin MVER as a dev dependency inside your monorepo:

```bash
uv add --dev mver
```

Then run it via:

```bash
uv run mver --help
```

---

## Install from Source

```bash
git clone https://github.com/xpodev/mver
cd mver
uv sync --all-groups
uv run mver --help
```

---

## Verify Installation

```bash
# Should print the version
mver --version

# From inside a monorepo with a registry file
mver where
```
