"""Root Typer app for resver."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from resver.commands.app_cmd import app_cmd_app
from resver.commands.group import group_app
from resver.commands.resource import resource_app
from resver.config import find_config, load_config, save_config
from resver.executor import resolve_command, run_command, substitute_tokens
from resver.registry import find_registry, load_registry
from resver.schema import get_group, get_group_version, get_resource_version, get_resources
from resver.semver_util import validate_semver

app = typer.Typer(
    name="resver",
    help="Resource Group Manager — lock-file registry for resource versions.",
    no_args_is_help=True,
)
app.add_typer(resource_app, name="resource")
app.add_typer(group_app, name="group")
app.add_typer(app_cmd_app, name="app")

# ---------------------------------------------------------------------------
# resver where
# ---------------------------------------------------------------------------


@app.command("where")
def where() -> None:
    """Print the path to .resver/registry.yml being used."""
    reg_path = find_registry()
    typer.echo(str(reg_path))


# ---------------------------------------------------------------------------
# resver validate
# ---------------------------------------------------------------------------


@app.command("validate")
def validate() -> None:
    """Validate the entire .resver/registry.yml for consistency."""
    registry, reg_path = load_registry()
    global_cfg = load_config(reg_path)
    errors: list[str] = []

    resources = registry.get("resources") or {}
    groups = registry.get("groups") or {}

    # Validate resource version semver
    for rname, rdata in resources.items():
        for ver in (rdata.get("versions") or {}):
            try:
                validate_semver(str(ver))
            except ValueError as e:
                errors.append(f"Resource '{rname}' version '{ver}': {e}")

    # Validate group version semver + resource version references
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

            for rname, rversion in (vdata.get("resources") or {}).items():
                if rname not in resources:
                    errors.append(
                        f"Group '{gname}@{ver}': references unknown resource '{rname}'"
                    )
                elif get_resource_version(registry, rname, str(rversion)) is None:
                    errors.append(
                        f"Group '{gname}@{ver}': resource '{rname}@{rversion}' not in registry"
                    )
                else:
                    # Check command resolution
                    rv = get_resource_version(registry, rname, str(rversion))
                    has_pull = rv.get("pull_command") or global_cfg.get("pull_command")
                    has_push = rv.get("push_command") or global_cfg.get("push_command")
                    if not has_pull:
                        errors.append(
                            f"Group '{gname}@{ver}': resource '{rname}@{rversion}' has no pull_command "
                            "(no version override and no global config)"
                        )
                    if not has_push:
                        errors.append(
                            f"Group '{gname}@{ver}': resource '{rname}@{rversion}' has no push_command "
                            "(no version override and no global config)"
                        )

    if errors:
        typer.echo("Validation FAILED:\n" + "\n".join(f"  - {e}" for e in errors), err=True)
        raise typer.Exit(1)
    typer.echo(f"Validation OK — {reg_path}")


# ---------------------------------------------------------------------------
# resver diff
# ---------------------------------------------------------------------------


@app.command("diff")
def diff(
    ref_a: Annotated[str, typer.Argument(help="group@version-a")],
    ref_b: Annotated[str, typer.Argument(help="group@version-b")],
) -> None:
    """Show resource version changes between two group versions."""
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

    resources_a: dict = gv_a.get("resources") or {}
    resources_b: dict = gv_b.get("resources") or {}
    all_resources = sorted(set(list(resources_a.keys()) + list(resources_b.keys())))

    any_diff = False
    typer.echo(f"Diff {ref_a} -> {ref_b}:")
    for rname in all_resources:
        ver_a = resources_a.get(rname)
        ver_b = resources_b.get(rname)
        if ver_a == ver_b:
            continue
        any_diff = True
        if ver_a is None:
            typer.echo(f"  + {rname}: (added) -> {ver_b}")
        elif ver_b is None:
            typer.echo(f"  - {rname}: {ver_a} -> (removed)")
        else:
            typer.echo(f"  ~ {rname}: {ver_a} -> {ver_b}")

    if not any_diff:
        typer.echo("  (no changes)")


# ---------------------------------------------------------------------------
# resver pull
# ---------------------------------------------------------------------------


@app.command("pull")
def pull() -> None:
    """Pull all resource artifacts for the current app's declared resources or group version."""
    from ruamel.yaml import YAML

    cwd = Path.cwd()
    app_cfg_path = cwd / ".resver" / "app.yml"
    if not app_cfg_path.exists():
        typer.echo(
            "Error: '.resver/app.yml' not found in current directory.\n"
            "Run 'resver app use <group@version>' or 'resver app use --resource name=version'.",
            err=True,
        )
        raise typer.Exit(1)

    _yaml = YAML()
    with open(app_cfg_path, "r", encoding="utf-8") as f:
        app_cfg = _yaml.load(f) or {}

    reg_path = find_registry(cwd)
    registry, _ = load_registry(reg_path)
    global_cfg = load_config(reg_path)
    repo_root = reg_path.parent.parent

    # Resolve resource pins from either mode
    if "resources" in app_cfg:
        # Resource-pin mode
        resource_pins = {k: str(v) for k, v in (app_cfg["resources"] or {}).items()}
        group_label = "(direct)"
    else:
        # Group mode
        gname = app_cfg.get("group")
        ver = str(app_cfg.get("version", ""))
        if not gname or not ver:
            typer.echo(
                "Error: .resver/app.yml must contain either 'resources' or 'group'+'version'.",
                err=True,
            )
            raise typer.Exit(1)
        gv = get_group_version(registry, gname, ver)
        if gv is None:
            typer.echo(f"Error: '{gname}@{ver}' not found in registry.", err=True)
            raise typer.Exit(1)
        resource_pins = {k: str(v) for k, v in (gv.get("resources") or {}).items()}
        group_label = gname

    # Validate all commands before executing any
    for rname, rversion in resource_pins.items():
        rv = get_resource_version(registry, rname, rversion)
        resolve_command("pull", rname, rversion, rv or {}, global_cfg)

    # Execute
    for rname, rversion in resource_pins.items():
        rv = get_resource_version(registry, rname, rversion) or {}
        cmd_template = resolve_command("pull", rname, rversion, rv, global_cfg)
        cmd = substitute_tokens(
            cmd_template,
            path=rv.get("path", ""),
            resource=rname,
            version=rversion,
            group=group_label,
        )
        typer.echo(f"Pulling '{rname}@{rversion}': {cmd}")
        run_command(cmd, repo_root)

    typer.echo("Pull complete.")


# ---------------------------------------------------------------------------
# resver push
# ---------------------------------------------------------------------------


@app.command("push")
def push(
    group_version: Annotated[str, typer.Argument(help="group@version to push")],
) -> None:
    """Push resource artifacts for a specific group version."""
    if "@" not in group_version:
        typer.echo("Error: expected 'group@version' format.", err=True)
        raise typer.Exit(1)

    gname, ver = group_version.split("@", 1)

    reg_path = find_registry()
    registry, _ = load_registry(reg_path)
    global_cfg = load_config(reg_path)
    repo_root = reg_path.parent.parent

    gv = get_group_version(registry, gname, ver)
    if gv is None:
        typer.echo(f"Error: '{group_version}' not found in registry.", err=True)
        raise typer.Exit(1)

    resource_pins: dict = gv.get("resources") or {}

    # Validate all commands before executing any
    for rname, rversion in resource_pins.items():
        rv = get_resource_version(registry, rname, str(rversion))
        resolve_command("push", rname, str(rversion), rv or {}, global_cfg)

    # Execute
    for rname, rversion in resource_pins.items():
        rv = get_resource_version(registry, rname, str(rversion)) or {}
        cmd_template = resolve_command("push", rname, str(rversion), rv, global_cfg)
        cmd = substitute_tokens(
            cmd_template,
            path=rv.get("path", ""),
            resource=rname,
            version=str(rversion),
            group=gname,
        )
        typer.echo(f"Pushing '{rname}@{rversion}': {cmd}")
        run_command(cmd, repo_root)

    typer.echo("Push complete.")


# ---------------------------------------------------------------------------
# resver config (inline sub-commands)
# ---------------------------------------------------------------------------

config_app = typer.Typer(help="Manage global config.", no_args_is_help=True)
app.add_typer(config_app, name="config")

config_set_app = typer.Typer(help="Set config values.", no_args_is_help=True)
config_app.add_typer(config_set_app, name="set")


@config_set_app.command("pull-command")
def config_set_pull(
    command: Annotated[str, typer.Argument(help="The pull command template")],
) -> None:
    """Set the global pull_command in .resver/config.yml."""
    reg_path = find_registry()
    cfg = load_config(reg_path)
    cfg["pull_command"] = command
    save_config(reg_path, cfg)
    typer.echo(f"Set pull_command: {command}")
    typer.echo("Reminder: commit .resver/config.yml to git.")


@config_set_app.command("push-command")
def config_set_push(
    command: Annotated[str, typer.Argument(help="The push command template")],
) -> None:
    """Set the global push_command in .resver/config.yml."""
    reg_path = find_registry()
    cfg = load_config(reg_path)
    cfg["push_command"] = command
    save_config(reg_path, cfg)
    typer.echo(f"Set push_command: {command}")
    typer.echo("Reminder: commit .resver/config.yml to git.")


@config_app.command("show")
def config_show() -> None:
    """Print the current global config."""
    reg_path = find_registry()
    cfg = load_config(reg_path)
    if not cfg:
        typer.echo("(no global config — .resver/config.yml not found or empty)")
        return
    for key, val in cfg.items():
        typer.echo(f"{key}: {val}")