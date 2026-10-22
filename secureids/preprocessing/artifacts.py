"""Artifact helpers for preprocessing reports, manifests, and preprocessors."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_joblib(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also protects a preprocessor outside output_dir.
    with path.open('xb') as handle:
        joblib.dump(payload, handle)


def build_manifest(
    dataset: str,
    config_path: str,
    input_paths: list[str],
    output_paths: list[str],
    random_seed: int | None,
) -> dict[str, Any]:
    """Build a reproducibility manifest skeleton without writing model data."""

    return {
        "dataset": dataset,
        "config_path": config_path,
        "input_paths": input_paths,
        "output_paths": output_paths,
        "random_seed": random_seed,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
