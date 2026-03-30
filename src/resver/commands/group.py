"""Commands: resver group ..."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, List, Optional

import typer

from resver.registry import load_registry, save_registry
from resver.schema import (
    get_group,
    get_group_version,
    get_resource_version,
    get_resources,
    latest_group_version,
)
from resver.semver_util import is_greater_than, validate_semver

group_app = typer.Typer(help="Manage resource groups.", no_args_is_help=True)

_GIT_REMINDER = "Reminder: commit .resver/registry.yml to git."


@group_app.command("create")
def group_create(
    group_name: Annotated[str, typer.Argument(help="Group name")],
) -> None:
    """Create a new named group with no versions yet."""
    data, reg_path = load_registry()

    if get_group(data, group_name) is not None:
        typer.echo(f"Error: group '{group_name}' already exists.", err=True)
        raise typer.Exit(1)

    data["groups"][group_name] = {"versions": {}}
    save_registry(data, reg_path)
    typer.echo(f"Created group '{group_name}'.")
    typer.echo(_GIT_REMINDER)


@group_app.command("release")
def group_release(
    group_name: Annotated[str, typer.Argument(help="Group name")],
    version: Annotated[str, typer.Argument(help="New semver version")],
    description: Annotated[Optional[str], typer.Option("--description", "-d")] = None,
    resource_pins: Annotated[
        Optional[List[str]],
        typer.Option("--resource", help="Pin as name=version (repeatable)"),
    ] = None,
) -> None:
    """Create a new version of a group, pinning resource versions."""
    try:
        validate_semver(version)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    data, reg_path = load_registry()

    if get_group(data, group_name) is None:
        typer.echo(f"Error: group '{group_name}' does not exist.", err=True)
        raise typer.Exit(1)

    if get_group_version(data, group_name, version) is not None:
        typer.echo(f"Error: version '{version}' already exists in group '{group_name}'.", err=True)
        raise typer.Exit(1)

    # Validate semver is greater than the current latest
    latest = latest_group_version(data, group_name)
    if latest and not is_greater_than(version, latest):
        typer.echo(
            f"Error: version '{version}' must be greater than current latest '{latest}'.",
            err=True,
        )
        raise typer.Exit(1)

    # Parse --resource flags
    pinned: dict[str, str] = {}
    for pin in (resource_pins or []):
        if "=" not in pin:
            typer.echo(f"Error: --resource value must be 'name=version', got '{pin}'.", err=True)
            raise typer.Exit(1)
        rname, rversion = pin.split("=", 1)
        pinned[rname.strip()] = rversion.strip()

    # For each registered resource, prompt if not supplied
    resources = get_resources(data)
    final_pins: dict[str, str] = {}
    for rname in resources:
        if rname in pinned:
            final_pins[rname] = pinned[rname]
        else:
            chosen = typer.prompt(f"Version for resource '{rname}'")
            final_pins[rname] = chosen.strip()

    # Validate all pinned versions exist
    errors = []
    for rname, rversion in final_pins.items():
        if get_resource_version(data, rname, rversion) is None:
            errors.append(f"  '{rname}@{rversion}' does not exist in the registry")
    if errors:
        typer.echo("Error: invalid resource versions:\n" + "\n".join(errors), err=True)
        raise typer.Exit(1)

    entry: dict = {
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "resources": final_pins,
    }
    if description:
        entry["description"] = description

    data["groups"][group_name]["versions"][version] = entry
    save_registry(data, reg_path)
    typer.echo(f"Released group '{group_name}@{version}'.")
    typer.echo(_GIT_REMINDER)


@group_app.command("list")
def group_list() -> None:
    """List all groups and their latest version."""
    data, _ = load_registry()
    groups = data.get("groups") or {}

    if not groups:
        typer.echo("No groups registered.")
        return

    typer.echo(f"{'Group':<30} {'Latest Version':<20}")
    typer.echo("-" * 50)
    for gname in groups:
        latest = latest_group_version(data, gname) or "(none)"
        typer.echo(f"{gname:<30} {latest:<20}")


@group_app.command("show")
def group_show(
    group_ref: Annotated[
        str, typer.Argument(help="Group name or 'group@version'")
    ],
) -> None:
    """List all versions of a group, or a specific version's details."""
    data, _ = load_registry()

    if "@" in group_ref:
        gname, ver = group_ref.split("@", 1)
        if get_group(data, gname) is None:
            typer.echo(f"Error: group '{gname}' does not exist.", err=True)
            raise typer.Exit(1)
        vdata = get_group_version(data, gname, ver)
        if vdata is None:
            typer.echo(f"Error: version '{ver}' does not exist in group '{gname}'.", err=True)
            raise typer.Exit(1)
        typer.echo(f"Group '{gname}@{ver}':")
        if vdata.get("description"):
            typer.echo(f"  description: {vdata['description']}")
        if vdata.get("created_at"):
            typer.echo(f"  created_at:  {vdata['created_at']}")
        if vdata.get("created_by"):
            typer.echo(f"  created_by:  {vdata['created_by']}")
        typer.echo("  resources:")
        for rname, rversion in (vdata.get("resources") or {}).items():
            typer.echo(f"    {rname}: {rversion}")
    else:
        gname = group_ref
        if get_group(data, gname) is None:
            typer.echo(f"Error: group '{gname}' does not exist.", err=True)
            raise typer.Exit(1)
        versions = (data["groups"][gname].get("versions") or {})
        if not versions:
            typer.echo(f"Group '{gname}' has no versions.")
            return
        typer.echo(f"Group '{gname}' versions:")
        for ver, vdata in versions.items():
            desc = vdata.get("description") or ""
            created = vdata.get("created_at") or ""
            typer.echo(f"  {ver}  {created}  {desc}")
            for rname, rversion in (vdata.get("resources") or {}).items():
                typer.echo(f"    {rname}: {rversion}")