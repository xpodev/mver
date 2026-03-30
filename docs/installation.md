# Installation

## Requirements

- Python **3.11+**
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

---

## Install as a CLI Tool

The recommended way to install RESVER globally is with `uv tool`:

```bash
uv tool install git+https://github.com/xpodev/resver
```

After installation, `resver` is available system-wide:

```bash
resver --help
```

---

## Add to a Monorepo

To pin RESVER as a dev dependency inside your monorepo:

```bash
uv add --dev resver
```

Then run it via:

```bash
uv run resver --help
```

---

## Install from Source

```bash
git clone https://github.com/xpodev/resver
cd resver
uv sync --all-groups
uv run resver --help
```

---

## Verify Installation

```bash
# Should print the version
resver --version

# From inside a monorepo with a registry file
resver where
```
