"""Commands: mver model ..."""
from __future__ import annotations

from typing import Annotated, Optional

import typer

from mver.commands.version import version_app
from mver.registry import load_registry, save_registry
from mver.schema import get_model, get_models, group_versions_referencing_model

model_app = typer.Typer(help="Manage models.", no_args_is_help=True)
model_app.add_typer(version_app, name="version")

_GIT_REMINDER = "Reminder: commit models.registry.yml to git."


@model_app.command("add")
def model_add(
    name: Annotated[str, typer.Argument(help="Model name")],
    description: Annotated[Optional[str], typer.Option("--description", "-d")] = None,
) -> None:
    """Register a new model with no versions yet."""
    data, reg_path = load_registry()

    if get_model(data, name) is not None:
        typer.echo(f"Error: model '{name}' already exists.", err=True)
        raise typer.Exit(1)

    entry: dict = {}
    if description:
        entry["description"] = description
    entry["versions"] = {}

    data["models"][name] = entry
    save_registry(data, reg_path)
    typer.echo(f"Added model '{name}'.")
    typer.echo(_GIT_REMINDER)


@model_app.command("list")
def model_list() -> None:
    """List all registered models."""
    data, _ = load_registry()
    models = get_models(data)

    if not models:
        typer.echo("No models registered.")
        return

    typer.echo(f"{'Model':<30} {'Description':<40} {'Versions':>8}")
    typer.echo("-" * 80)
    for name, mdata in models.items():
        desc = (mdata or {}).get("description") or ""
        vcount = len((mdata or {}).get("versions") or {})
        typer.echo(f"{name:<30} {desc:<40} {vcount:>8}")


@model_app.command("remove")
def model_remove(
    name: Annotated[str, typer.Argument(help="Model name")],
) -> None:
    """Remove a model from the registry."""
    data, reg_path = load_registry()

    if get_model(data, name) is None:
        typer.echo(f"Error: model '{name}' does not exist.", err=True)
        raise typer.Exit(1)

    refs = group_versions_referencing_model(data, name)
    if refs:
        typer.echo(
            f"Error: model '{name}' is referenced by:\n" + "\n".join(f"  {r}" for r in refs),
            err=True,
        )
        raise typer.Exit(1)

    del data["models"][name]
    save_registry(data, reg_path)
    typer.echo(f"Removed model '{name}'.")
    typer.echo(_GIT_REMINDER)
