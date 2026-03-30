"""Commands: resver resource ..."""
from __future__ import annotations

from typing import Annotated, Optional

import typer

from resver.commands.version import version_app
from resver.registry import load_registry, save_registry
from resver.schema import get_resource, get_resources, group_versions_referencing_resource

resource_app = typer.Typer(help="Manage resources.", no_args_is_help=True)
resource_app.add_typer(version_app, name="version")

_GIT_REMINDER = "Reminder: commit .resver/registry.yml to git."


@resource_app.command("add")
def resource_add(
    name: Annotated[str, typer.Argument(help="Resource name")],
    description: Annotated[Optional[str], typer.Option("--description", "-d")] = None,
) -> None:
    """Register a new resource with no versions yet."""
    data, reg_path = load_registry()

    if get_resource(data, name) is not None:
        typer.echo(f"Error: resource '{name}' already exists.", err=True)
        raise typer.Exit(1)

    entry: dict = {}
    if description:
        entry["description"] = description
    entry["versions"] = {}

    data["resources"][name] = entry
    save_registry(data, reg_path)
    typer.echo(f"Added resource '{name}'.")
    typer.echo(_GIT_REMINDER)


@resource_app.command("list")
def resource_list() -> None:
    """List all registered resources."""
    data, _ = load_registry()
    resources = get_resources(data)

    if not resources:
        typer.echo("No resources registered.")
        return

    typer.echo(f"{'Resource':<30} {'Description':<40} {'Versions':>8}")
    typer.echo("-" * 80)
    for name, rdata in resources.items():
        desc = (rdata or {}).get("description") or ""
        vcount = len((rdata or {}).get("versions") or {})
        typer.echo(f"{name:<30} {desc:<40} {vcount:>8}")


@resource_app.command("remove")
def resource_remove(
    name: Annotated[str, typer.Argument(help="Resource name")],
) -> None:
    """Remove a resource from the registry."""
    data, reg_path = load_registry()

    if get_resource(data, name) is None:
        typer.echo(f"Error: resource '{name}' does not exist.", err=True)
        raise typer.Exit(1)

    refs = group_versions_referencing_resource(data, name)
    if refs:
        typer.echo(
            f"Error: resource '{name}' is referenced by:\n" + "\n".join(f"  {r}" for r in refs),
            err=True,
        )
        raise typer.Exit(1)

    del data["resources"][name]
    save_registry(data, reg_path)
    typer.echo(f"Removed resource '{name}'.")
    typer.echo(_GIT_REMINDER)