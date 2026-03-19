"""
fraud-service — example app using the mver Python API.

This app uses the 'production' model group. It reads mver.yml from its own
directory, discovers the models.registry.yml by walking up the directory tree,
and resolves the exact model paths declared for the pinned group version.

Run from this directory:
    python main.py
"""
from __future__ import annotations

from pathlib import Path

from mver import AppConfig, GlobalConfig, Registry

# The directory that contains this file — used as the app root so the example
# works regardless of the current working directory.
APP_DIR = Path(__file__).parent


def load_models():
    """Discover registry + config, load the app declaration, resolve models."""
    # --- 1. Load the registry (walks up from APP_DIR) ---
    registry = Registry.find(APP_DIR)
    print(f"Registry: {registry.path}")
    print(f"Monorepo root: {registry.root}\n")

    # --- 2. Load the global config (pull/push backend) ---
    config = GlobalConfig.load(APP_DIR)

    # --- 3. Load this app's declared group version ---
    app = AppConfig.load(APP_DIR)
    print(f"App declares: {app.group}@{app.version}\n")

    # --- 4. Resolve to concrete model versions and paths ---
    resolved = app.resolve(registry, config)
    print(f"Resolved models for {resolved.group_name}@{resolved.version}:")
    for name, model in resolved.models.items():
        print(f"  {name:25s} v{model.version:10s}  path={model.path}")
    print()

    return resolved


def run_inference(resolved):
    """Demonstrate accessing individual models from the resolved app."""
    fraud_model = resolved["fraud-detector"]

    print("--- Fraud Detector ---")
    print(f"  version : {fraud_model.version}")
    print(f"  path    : {fraud_model.path}")
    print(f"  pull cmd: {fraud_model.pull_command}")

    # In a real app you would load the artifact here, e.g.:
    #   import joblib
    #   clf = joblib.load(fraud_model.path + "/model.pkl")
    #   prediction = clf.predict(features)

    embedder = resolved["embedder"]

    print("\n--- Embedder ---")
    print(f"  version : {embedder.version}")
    print(f"  path    : {embedder.path}")
    print(f"  pull cmd: {embedder.pull_command}")

    # In a real app:
    #   from sentence_transformers import SentenceTransformer
    #   model = SentenceTransformer(embedder.path)
    #   embedding = model.encode(["hello world"])


if __name__ == "__main__":
    resolved = load_models()
    run_inference(resolved)
