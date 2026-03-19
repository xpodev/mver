"""
risk-scorer — example app using the mver Python API.

This app uses the 'staging' model group to test pre-release model versions.
It demonstrates using registry.app_config() and registry.config() as
convenience helpers instead of the standalone AppConfig/GlobalConfig calls.

Run from this directory:
    python main.py
"""
from __future__ import annotations

from pathlib import Path

from mver import Registry

APP_DIR = Path(__file__).parent


def load_models():
    """Use Registry as the single entry point for everything."""
    # Registry exposes helpers so you don't need to import every class.
    registry = Registry.find(APP_DIR)

    # Convenience helpers on the registry object
    config = registry.config()                     # loads mver.config.yml
    app = registry.app_config(APP_DIR)             # loads mver.yml

    print(f"Registry : {registry.path}")
    print(f"App      : {app.group}@{app.version}\n")

    resolved = app.resolve(registry, config)

    print(f"Models for {resolved}:")
    for name, model in resolved.models.items():
        print(f"  {name:25s} v{model.version}")

    return resolved


def iterate_all_models(resolved):
    """Show that ResolvedApp supports standard iteration."""
    print("\n--- Iterating resolved app ---")
    print(f"Total models: {len(resolved)}")
    for model_name in resolved:
        m = resolved[model_name]
        print(f"  {model_name}: path={m.path}")


def inspect_registry():
    """Show how to browse the registry directly, without an app config."""
    registry = Registry.find(APP_DIR)

    print("\n--- All registered models ---")
    for name, model in registry.models.items():
        latest = model.latest
        print(f"  {name}: {len(model.versions)} version(s), latest={latest.version if latest else 'none'}")

    print("\n--- All groups ---")
    for name, group in registry.groups.items():
        latest = group.latest
        print(f"  {name}: {len(group.versions)} version(s), latest={latest.version if latest else 'none'}")
        if latest:
            for mname, mver in latest.models.items():
                print(f"    {mname} @ {mver}")


if __name__ == "__main__":
    resolved = load_models()
    iterate_all_models(resolved)
    inspect_registry()
