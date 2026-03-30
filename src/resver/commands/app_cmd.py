"""Commands: resver app ..."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated, List, Optional

import typer
from ruamel.yaml import YAML

from resver.registry import find_registry, load_registry
from resver.schema import get_group, get_group_version, get_resource, get_resource_version

app_cmd_app = typer.Typer(help="Manage app resource declarations.", no_args_is_help=True)

APP_CONFIG_FILENAME = ".resver/app.yml"
_yaml = YAML()
_yaml.default_flow_style = False


def _load_app_config(cwd: Path) -> dict:
    app_cfg = cwd / APP_CONFIG_FILENAME
    if not app_cfg.exists():
        typer.echo(
            f"Error: '{APP_CONFIG_FILENAME}' not found in {cwd}.\n"
            "Run 'resver app use <group@version>' or 'resver app use --resource name=version'.",
            err=True,
        )
        raise typer.Exit(1)
    with open(app_cfg, "r", encoding="utf-8") as f:
        data = _yaml.load(f)
    return data or {}


def _save_app_config(cwd: Path, data: dict) -> None:
    (cwd / ".resver").mkdir(exist_ok=True)
    with open(cwd / APP_CONFIG_FILENAME, "w", encoding="utf-8") as f:
        _yaml.dump(data, f)


def _parse_resource_flag(value: str) -> tuple[str, str]:
    """Parse 'name=version' into (name, version). Exits on bad format."""
    if "=" not in value:
        typer.echo(f"Error: --resource must be in 'name=version' format, got '{value}'.", err=True)
        raise typer.Exit(1)
    name, ver = value.split("=", 1)
    return name.strip(), ver.strip()


# ---------------------------------------------------------------------------
# resver app use
# ---------------------------------------------------------------------------


@app_cmd_app.command("use")
def app_use(
    group_version: Annotated[
        Optional[str],
        typer.Argument(help="group@version to lock to (group mode)"),
    ] = None,
    resource: Annotated[
        Optional[List[str]],
        typer.Option("--resource", help="name=version pin, repeatable (resource mode)"),
    ] = None,
) -> None:
    """Lock this app to a group version or to specific resource versions.

    Group mode:    resver app use production@2.0.0
    Resource mode: resver app use --resource fraud-detector=2.0.0 --resource embedder=1.0.0
    """
    cwd = Path.cwd()
    reg_path = find_registry(cwd)

    # Verify cwd is under the monorepo root
    repo_root = reg_path.parent.parent
    try:
        cwd.relative_to(repo_root)
    except ValueError:
        typer.echo(
            f"Error: current directory '{cwd}' is not inside the monorepo root '{repo_root}'.",
            err=True,
        )
        raise typer.Exit(1)

    # --- group mode ---
    if group_version is not None:
        if resource:
            typer.echo(
                "Error: cannot combine a positional group@version with --resource flags.", err=True
            )
            raise typer.Exit(1)
        if "@" not in group_version:
            typer.echo("Error: expected 'group@version' format.", err=True)
            raise typer.Exit(1)
        gname, ver = group_version.split("@", 1)

        data, _ = load_registry(reg_path)
        if get_group(data, gname) is None:
            typer.echo(f"Error: group '{gname}' does not exist.", err=True)
            raise typer.Exit(1)
        if get_group_version(data, gname, ver) is None:
            typer.echo(f"Error: version '{ver}' does not exist in group '{gname}'.", err=True)
            raise typer.Exit(1)

        _save_app_config(cwd, {"group": gname, "version": ver})
        typer.echo(f"Set app to use group '{gname}@{ver}'.")
        typer.echo("Reminder: commit .resver/app.yml to git.")
        return

    # --- resource-pin mode ---
    if resource:
        pins: dict[str, str] = {}
        for r in resource:
            rname, rversion = _parse_resource_flag(r)
            pins[rname] = rversion

        data, _ = load_registry(reg_path)
        for rname, rversion in pins.items():
            if get_resource(data, rname) is None:
                typer.echo(f"Error: resource '{rname}' does not exist in registry.", err=True)
                raise typer.Exit(1)
            if get_resource_version(data, rname, rversion) is None:
                typer.echo(
                    f"Error: version '{rversion}' does not exist for resource '{rname}'.", err=True
                )
                raise typer.Exit(1)

        _save_app_config(cwd, {"resources": pins})
        pins_str = ", ".join(f"{n}@{v}" for n, v in pins.items())
        typer.echo(f"Set app to use resources: {pins_str}.")
        typer.echo("Reminder: commit .resver/app.yml to git.")
        return

    typer.echo(
        "Error: provide either a group@version argument or one or more --resource name=version flags.",
        err=True,
    )
    raise typer.Exit(1)


# ---------------------------------------------------------------------------
# resver app show
# ---------------------------------------------------------------------------


@app_cmd_app.command("show")
def app_show() -> None:
    """Print fully resolved resource versions and paths for the current app."""
    cwd = Path.cwd()
    app_cfg = _load_app_config(cwd)

    reg_path = find_registry(cwd)
    registry, _ = load_registry(reg_path)

    # --- resource-pin mode ---
    if "resources" in app_cfg:
        pins: dict = app_cfg["resources"] or {}
        typer.echo("App uses direct resource pins:")
        typer.echo(f"  {'Resource':<30} {'Version':<15} {'Path'}")
        typer.echo("  " + "-" * 70)
        for rname, rversion in pins.items():
            rv = get_resource_version(registry, rname, str(rversion))
            path = (rv or {}).get("path", "(unknown)")
            typer.echo(f"  {rname:<30} {str(rversion):<15} {path}")
        return

    # --- group mode ---
    gname = app_cfg.get("group")
    ver = app_cfg.get("version")
    if not gname or not ver:
        typer.echo(
            "Error: .resver/app.yml must contain either 'resources' or 'group'+'version'.", err=True
        )
        raise typer.Exit(1)

    gv = get_group_version(registry, gname, str(ver))
    if gv is None:
        typer.echo(f"Error: '{gname}@{ver}' not found in registry.", err=True)
        raise typer.Exit(1)

    typer.echo(f"App uses group '{gname}@{ver}':")
    typer.echo(f"  {'Resource':<30} {'Version':<15} {'Path'}")
    typer.echo("  " + "-" * 70)
    for rname, rversion in (gv.get("resources") or {}).items():
        rv = get_resource_version(registry, rname, str(rversion))
        path = (rv or {}).get("path", "(unknown)")
        typer.echo(f"  {rname:<30} {str(rversion):<15} {path}")


# ---------------------------------------------------------------------------
# resver app check
# ---------------------------------------------------------------------------


@app_cmd_app.command("check")
def app_check() -> None:
    """Validate that the declared resources/group still exist in the registry. Exits 1 on failure."""
    cwd = Path.cwd()
    app_cfg = _load_app_config(cwd)

    reg_path = find_registry(cwd)
    registry, _ = load_registry(reg_path)

    ok = True

    # --- resource-pin mode ---
    if "resources" in app_cfg:
        for rname, rversion in (app_cfg["resources"] or {}).items():
            if get_resource_version(registry, rname, str(rversion)) is None:
                typer.echo(
                    f"Error: resource '{rname}@{rversion}' not found in registry.", err=True
                )
                ok = False
        if ok:
            pins = ", ".join(
                f"{n}@{v}" for n, v in (app_cfg["resources"] or {}).items()
            )
            typer.echo(f"OK: {pins}")
        else:
            raise typer.Exit(1)
        return

    # --- group mode ---
    gname = app_cfg.get("group")
    ver = app_cfg.get("version")

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