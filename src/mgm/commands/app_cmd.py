"""Commands: mgm app ..."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from ruamel.yaml import YAML

from mgm.registry import find_registry, load_registry
from mgm.schema import get_group, get_group_version, get_model_version

app_cmd_app = typer.Typer(help="Manage app model group declarations.", no_args_is_help=True)

APP_CONFIG_FILENAME = "mgm.yml"
_yaml = YAML()
_yaml.default_flow_style = False


def _load_app_config(cwd: Path) -> dict:
    app_cfg = cwd / APP_CONFIG_FILENAME
    if not app_cfg.exists():
        typer.echo(
            f"Error: '{APP_CONFIG_FILENAME}' not found in {cwd}.\n"
            "Run 'mgm app use <group@version>' first.",
            err=True,
        )
        raise typer.Exit(1)
    with open(app_cfg, "r", encoding="utf-8") as f:
        data = _yaml.load(f)
    return data or {}


def _save_app_config(cwd: Path, data: dict) -> None:
    with open(cwd / APP_CONFIG_FILENAME, "w", encoding="utf-8") as f:
        _yaml.dump(data, f)


@app_cmd_app.command("use")
def app_use(
    group_version: Annotated[str, typer.Argument(help="group@version to use")],
) -> None:
    """Write or update mgm.yml in the current directory."""
    if "@" not in group_version:
        typer.echo("Error: expected 'group@version' format.", err=True)
        raise typer.Exit(1)
    gname, ver = group_version.split("@", 1)

    cwd = Path.cwd()
    reg_path = find_registry(cwd)

    # Verify cwd is under the monorepo root
    repo_root = reg_path.parent
    try:
        cwd.relative_to(repo_root)
    except ValueError:
        typer.echo(
            f"Error: current directory '{cwd}' is not inside the monorepo root '{repo_root}'.",
            err=True,
        )
        raise typer.Exit(1)

    data, _ = load_registry(reg_path)

    if get_group(data, gname) is None:
        typer.echo(f"Error: group '{gname}' does not exist.", err=True)
        raise typer.Exit(1)
    if get_group_version(data, gname, ver) is None:
        typer.echo(f"Error: version '{ver}' does not exist in group '{gname}'.", err=True)
        raise typer.Exit(1)

    _save_app_config(cwd, {"group": gname, "version": ver})
    typer.echo(f"Set app to use '{gname}@{ver}'.")
    typer.echo("Reminder: commit mgm.yml to git.")


@app_cmd_app.command("show")
def app_show() -> None:
    """Print fully resolved model versions and paths for the current app."""
    cwd = Path.cwd()
    app_cfg = _load_app_config(cwd)
    gname = app_cfg.get("group")
    ver = app_cfg.get("version")
    if not gname or not ver:
        typer.echo("Error: mgm.yml is missing 'group' or 'version'.", err=True)
        raise typer.Exit(1)

    reg_path = find_registry(cwd)
    registry, _ = load_registry(reg_path)

    gv = get_group_version(registry, gname, str(ver))
    if gv is None:
        typer.echo(f"Error: '{gname}@{ver}' not found in registry.", err=True)
        raise typer.Exit(1)

    typer.echo(f"App uses group '{gname}@{ver}':")
    typer.echo(f"  {'Model':<30} {'Version':<15} {'Path'}")
    typer.echo("  " + "-" * 70)
    for mname, mver in (gv.get("models") or {}).items():
        mv = get_model_version(registry, mname, str(mver))
        path = (mv or {}).get("path", "(unknown)")
        typer.echo(f"  {mname:<30} {str(mver):<15} {path}")


@app_cmd_app.command("check")
def app_check() -> None:
    """Validate that the group/version in mgm.yml exists in the registry. Exits 1 on failure."""
    cwd = Path.cwd()
    app_cfg = _load_app_config(cwd)
    gname = app_cfg.get("group")
    ver = app_cfg.get("version")

    reg_path = find_registry(cwd)
    registry, _ = load_registry(reg_path)

    ok = True
    if get_group(registry, gname) is None:
        typer.echo(f"Error: group '{gname}' does not exist in registry.", err=True)
        ok = False
    elif get_group_version(registry, gname, str(ver)) is None:
        typer.echo(
            f"Error: version '{ver}' does not exist in group '{gname}' in registry.", err=True
        )
        ok = False

    if not ok:
        raise typer.Exit(1)
    typer.echo(f"OK: '{gname}@{ver}' is valid.")
