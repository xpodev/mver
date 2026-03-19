"""Commands: mver model version ..."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Optional

import typer

from mver.registry import load_registry, save_registry
from mver.schema import get_model, get_model_version, group_versions_referencing_model_version
from mver.semver_util import validate_semver

version_app = typer.Typer(help="Manage model versions.", no_args_is_help=True)

_GIT_REMINDER = "Reminder: commit models.registry.yml to git."


@version_app.command("add")
def version_add(
    model_name: Annotated[str, typer.Argument(help="Model name")],
    version: Annotated[str, typer.Argument(help="Semver version string")],
    path: Annotated[str, typer.Option("--path", help="Path to model artifacts")] = "",
    pull_command: Annotated[Optional[str], typer.Option("--pull-command")] = None,
    push_command: Annotated[Optional[str], typer.Option("--push-command")] = None,
    created_by: Annotated[Optional[str], typer.Option("--created-by")] = None,
) -> None:
    """Register a new version of an existing model."""
    try:
        validate_semver(version)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    if not path:
        typer.echo("Error: --path is required.", err=True)
        raise typer.Exit(1)

    data, reg_path = load_registry()

    if get_model(data, model_name) is None:
        typer.echo(f"Error: model '{model_name}' does not exist in the registry.", err=True)
        raise typer.Exit(1)

    if get_model_version(data, model_name, version) is not None:
        typer.echo(
            f"Error: version '{version}' already exists for model '{model_name}'.", err=True
        )
        raise typer.Exit(1)

    entry: dict = {
        "path": path,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if created_by:
        entry["created_by"] = created_by
    if pull_command:
        entry["pull_command"] = pull_command
    if push_command:
        entry["push_command"] = push_command

    if data["models"][model_name].get("versions") is None:
        data["models"][model_name]["versions"] = {}
    data["models"][model_name]["versions"][version] = entry

    save_registry(data, reg_path)
    typer.echo(f"Added version '{version}' to model '{model_name}'.")
    typer.echo(_GIT_REMINDER)


@version_app.command("list")
def version_list(
    model_name: Annotated[str, typer.Argument(help="Model name")],
) -> None:
    """List all versions of a model."""
    data, _ = load_registry()

    if get_model(data, model_name) is None:
        typer.echo(f"Error: model '{model_name}' does not exist.", err=True)
        raise typer.Exit(1)

    versions = (data["models"][model_name].get("versions") or {})
    if not versions:
        typer.echo(f"No versions registered for '{model_name}'.")
        return

    typer.echo(f"Versions of '{model_name}':")
    for ver, vdata in versions.items():
        parts = [f"  {ver}", f"    path:       {vdata.get('path', '')}"]
        if vdata.get("created_at"):
            parts.append(f"    created_at: {vdata['created_at']}")
        if vdata.get("created_by"):
            parts.append(f"    created_by: {vdata['created_by']}")
        if vdata.get("pull_command"):
            parts.append(f"    pull:       {vdata['pull_command']}")
        if vdata.get("push_command"):
            parts.append(f"    push:       {vdata['push_command']}")
        typer.echo("\n".join(parts))


@version_app.command("remove")
def version_remove(
    model_name: Annotated[str, typer.Argument(help="Model name")],
    version: Annotated[str, typer.Argument(help="Version to remove")],
) -> None:
    """Remove a model version from the registry."""
    data, reg_path = load_registry()

    if get_model(data, model_name) is None:
        typer.echo(f"Error: model '{model_name}' does not exist.", err=True)
        raise typer.Exit(1)

    if get_model_version(data, model_name, version) is None:
        typer.echo(f"Error: version '{version}' does not exist for model '{model_name}'.", err=True)
        raise typer.Exit(1)

    refs = group_versions_referencing_model_version(data, model_name, version)
    if refs:
        typer.echo(
            f"Error: version '{version}' of '{model_name}' is referenced by:\n"
            + "\n".join(f"  {r}" for r in refs),
            err=True,
        )
        raise typer.Exit(1)

    del data["models"][model_name]["versions"][version]
    save_registry(data, reg_path)
    typer.echo(f"Removed version '{version}' from model '{model_name}'.")
    typer.echo(_GIT_REMINDER)
