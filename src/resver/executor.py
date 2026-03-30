"""Token substitution and shell command execution."""
from __future__ import annotations

import subprocess
from pathlib import Path

import typer


def resolve_command(
    action: str,
    resource_name: str,
    resource_version_str: str,
    version_entry: dict,
    global_config: dict,
) -> str:
    """
    Resolve pull_command or push_command for a resource version.
    Priority: version_entry override > global_config > error.
    """
    key = f"{action}_command"
    cmd = (version_entry or {}).get(key) or global_config.get(key)
    if not cmd:
        typer.echo(
            f"Error: no {key} configured for resource '{resource_name}@{resource_version_str}' "
            f"and no global fallback in .resver/config.yml.",
            err=True,
        )
        raise typer.Exit(1)
    return cmd


def substitute_tokens(cmd: str, *, path: str, resource: str, version: str, group: str) -> str:
    return (
        cmd.replace("{path}", path)
        .replace("{resource}", resource)
        .replace("{version}", version)
        .replace("{group}", group)
    )


def run_command(cmd: str, cwd: Path) -> None:
    """Run a shell command, streaming output. Raises typer.Exit(1) on failure."""
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        typer.echo(f"Error: command exited with code {result.returncode}: {cmd}", err=True)
        raise typer.Exit(1)
