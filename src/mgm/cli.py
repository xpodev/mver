"""Root Typer app for mgm."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from mgm.commands.app_cmd import app_cmd_app
from mgm.commands.group import group_app
from mgm.commands.model import model_app
from mgm.config import find_config, load_config, save_config
from mgm.executor import resolve_command, run_command, substitute_tokens
from mgm.registry import find_registry, load_registry
from mgm.schema import get_group, get_group_version, get_model_version, get_models
from mgm.semver_util import validate_semver

app = typer.Typer(
    name="mgm",
    help="Model Group Manager — lock-file registry for ML model versions.",
    no_args_is_help=True,
)
app.add_typer(model_app, name="model")
app.add_typer(group_app, name="group")
app.add_typer(app_cmd_app, name="app")

# ---------------------------------------------------------------------------
# mgm where
# ---------------------------------------------------------------------------


@app.command("where")
def where() -> None:
    """Print the path to models.registry.yml being used."""
    reg_path = find_registry()
    typer.echo(str(reg_path))


# ---------------------------------------------------------------------------
# mgm validate
# ---------------------------------------------------------------------------


@app.command("validate")
def validate() -> None:
    """Validate the entire models.registry.yml for consistency."""
    registry, reg_path = load_registry()
    global_cfg = load_config(reg_path)
    errors: list[str] = []

    models = registry.get("models") or {}
    groups = registry.get("groups") or {}

    # Validate model version semver
    for mname, mdata in models.items():
        for ver in (mdata.get("versions") or {}):
            try:
                validate_semver(str(ver))
            except ValueError as e:
                errors.append(f"Model '{mname}' version '{ver}': {e}")

    # Validate group version semver + model version references
    for gname, gdata in groups.items():
        seen_versions: list[str] = []
        for ver, vdata in (gdata.get("versions") or {}).items():
            try:
                validate_semver(str(ver))
            except ValueError as e:
                errors.append(f"Group '{gname}' version '{ver}': {e}")

            if str(ver) in seen_versions:
                errors.append(f"Group '{gname}': duplicate version '{ver}'")
            seen_versions.append(str(ver))

            for mname, mver in (vdata.get("models") or {}).items():
                if mname not in models:
                    errors.append(
                        f"Group '{gname}@{ver}': references unknown model '{mname}'"
                    )
                elif get_model_version(registry, mname, str(mver)) is None:
                    errors.append(
                        f"Group '{gname}@{ver}': model '{mname}@{mver}' not in registry"
                    )
                else:
                    # Check command resolution
                    mv = get_model_version(registry, mname, str(mver))
                    has_pull = mv.get("pull_command") or global_cfg.get("pull_command")
                    has_push = mv.get("push_command") or global_cfg.get("push_command")
                    if not has_pull:
                        errors.append(
                            f"Group '{gname}@{ver}': model '{mname}@{mver}' has no pull_command "
                            "(no version override and no global config)"
                        )
                    if not has_push:
                        errors.append(
                            f"Group '{gname}@{ver}': model '{mname}@{mver}' has no push_command "
                            "(no version override and no global config)"
                        )

    if errors:
        typer.echo("Validation FAILED:\n" + "\n".join(f"  - {e}" for e in errors), err=True)
        raise typer.Exit(1)
    typer.echo(f"Validation OK — {reg_path}")


# ---------------------------------------------------------------------------
# mgm diff
# ---------------------------------------------------------------------------


@app.command("diff")
def diff(
    ref_a: Annotated[str, typer.Argument(help="group@version-a")],
    ref_b: Annotated[str, typer.Argument(help="group@version-b")],
) -> None:
    """Show model version changes between two group versions."""
    for ref in (ref_a, ref_b):
        if "@" not in ref:
            typer.echo(f"Error: expected 'group@version' format, got '{ref}'.", err=True)
            raise typer.Exit(1)

    ga, va = ref_a.split("@", 1)
    gb, vb = ref_b.split("@", 1)
    if ga != gb:
        typer.echo(
            f"Error: both refs must be from the same group (got '{ga}' and '{gb}').", err=True
        )
        raise typer.Exit(1)

    registry, _ = load_registry()

    gv_a = get_group_version(registry, ga, va)
    gv_b = get_group_version(registry, gb, vb)
    if gv_a is None:
        typer.echo(f"Error: '{ref_a}' not found in registry.", err=True)
        raise typer.Exit(1)
    if gv_b is None:
        typer.echo(f"Error: '{ref_b}' not found in registry.", err=True)
        raise typer.Exit(1)

    models_a: dict = gv_a.get("models") or {}
    models_b: dict = gv_b.get("models") or {}
    all_models = sorted(set(list(models_a.keys()) + list(models_b.keys())))

    any_diff = False
    typer.echo(f"Diff {ref_a} → {ref_b}:")
    for mname in all_models:
        ver_a = models_a.get(mname)
        ver_b = models_b.get(mname)
        if ver_a == ver_b:
            continue
        any_diff = True
        if ver_a is None:
            typer.echo(f"  + {mname}: (added) → {ver_b}")
        elif ver_b is None:
            typer.echo(f"  - {mname}: {ver_a} → (removed)")
        else:
            typer.echo(f"  ~ {mname}: {ver_a} → {ver_b}")

    if not any_diff:
        typer.echo("  (no changes)")


# ---------------------------------------------------------------------------
# mgm pull
# ---------------------------------------------------------------------------


@app.command("pull")
def pull() -> None:
    """Pull all model artifacts for the current app's declared group version."""
    from ruamel.yaml import YAML

    cwd = Path.cwd()
    app_cfg_path = cwd / "mgm.yml"
    if not app_cfg_path.exists():
        typer.echo(
            "Error: 'mgm.yml' not found in current directory.\n"
            "Run 'mgm app use <group@version>' first.",
            err=True,
        )
        raise typer.Exit(1)

    _yaml = YAML()
    with open(app_cfg_path, "r", encoding="utf-8") as f:
        app_cfg = _yaml.load(f) or {}

    gname = app_cfg.get("group")
    ver = str(app_cfg.get("version", ""))
    if not gname or not ver:
        typer.echo("Error: mgm.yml is missing 'group' or 'version'.", err=True)
        raise typer.Exit(1)

    reg_path = find_registry(cwd)
    registry, _ = load_registry(reg_path)
    global_cfg = load_config(reg_path)
    repo_root = reg_path.parent

    gv = get_group_version(registry, gname, ver)
    if gv is None:
        typer.echo(f"Error: '{gname}@{ver}' not found in registry.", err=True)
        raise typer.Exit(1)

    model_pins: dict = gv.get("models") or {}

    # Validate all commands before executing any
    for mname, mver in model_pins.items():
        mv = get_model_version(registry, mname, str(mver))
        resolve_command("pull", mname, str(mver), mv or {}, global_cfg)

    # Execute
    for mname, mver in model_pins.items():
        mv = get_model_version(registry, mname, str(mver)) or {}
        cmd_template = resolve_command("pull", mname, str(mver), mv, global_cfg)
        cmd = substitute_tokens(
            cmd_template,
            path=mv.get("path", ""),
            model=mname,
            version=str(mver),
            group=gname,
        )
        typer.echo(f"Pulling '{mname}@{mver}': {cmd}")
        run_command(cmd, repo_root)

    typer.echo("Pull complete.")


# ---------------------------------------------------------------------------
# mgm push
# ---------------------------------------------------------------------------


@app.command("push")
def push(
    group_version: Annotated[str, typer.Argument(help="group@version to push")],
) -> None:
    """Push model artifacts for a specific group version."""
    if "@" not in group_version:
        typer.echo("Error: expected 'group@version' format.", err=True)
        raise typer.Exit(1)

    gname, ver = group_version.split("@", 1)

    reg_path = find_registry()
    registry, _ = load_registry(reg_path)
    global_cfg = load_config(reg_path)
    repo_root = reg_path.parent

    gv = get_group_version(registry, gname, ver)
    if gv is None:
        typer.echo(f"Error: '{group_version}' not found in registry.", err=True)
        raise typer.Exit(1)

    model_pins: dict = gv.get("models") or {}

    # Validate all commands before executing any
    for mname, mver in model_pins.items():
        mv = get_model_version(registry, mname, str(mver))
        resolve_command("push", mname, str(mver), mv or {}, global_cfg)

    # Execute
    for mname, mver in model_pins.items():
        mv = get_model_version(registry, mname, str(mver)) or {}
        cmd_template = resolve_command("push", mname, str(mver), mv, global_cfg)
        cmd = substitute_tokens(
            cmd_template,
            path=mv.get("path", ""),
            model=mname,
            version=str(mver),
            group=gname,
        )
        typer.echo(f"Pushing '{mname}@{mver}': {cmd}")
        run_command(cmd, repo_root)

    typer.echo("Push complete.")


# ---------------------------------------------------------------------------
# mgm config (inline sub-commands)
# ---------------------------------------------------------------------------

config_app = typer.Typer(help="Manage global config.", no_args_is_help=True)
app.add_typer(config_app, name="config")

config_set_app = typer.Typer(help="Set config values.", no_args_is_help=True)
config_app.add_typer(config_set_app, name="set")


@config_set_app.command("pull-command")
def config_set_pull(
    command: Annotated[str, typer.Argument(help="The pull command template")],
) -> None:
    """Set the global pull_command in mgm.config.yml."""
    reg_path = find_registry()
    cfg = load_config(reg_path)
    cfg["pull_command"] = command
    save_config(reg_path, cfg)
    typer.echo(f"Set pull_command: {command}")
    typer.echo("Reminder: commit mgm.config.yml to git.")


@config_set_app.command("push-command")
def config_set_push(
    command: Annotated[str, typer.Argument(help="The push command template")],
) -> None:
    """Set the global push_command in mgm.config.yml."""
    reg_path = find_registry()
    cfg = load_config(reg_path)
    cfg["push_command"] = command
    save_config(reg_path, cfg)
    typer.echo(f"Set push_command: {command}")
    typer.echo("Reminder: commit mgm.config.yml to git.")


@config_app.command("show")
def config_show() -> None:
    """Print the current global config."""
    reg_path = find_registry()
    cfg = load_config(reg_path)
    if not cfg:
        typer.echo("(no global config — mgm.config.yml not found or empty)")
        return
    for key, val in cfg.items():
        typer.echo(f"{key}: {val}")
