"""Torch-free planning and data-availability validation for centralized training.

This module deliberately avoids importing torch so the
``train-centralized --dry-run`` path can validate configs and processed
artifacts even in an environment without PyTorch installed. It owns the pure
NumPy/JSON loaders (re-exported by :mod:`secureids.training.datasets`) and the
dry-run planner.

Nothing here trains, builds a model, creates DataLoaders, or writes files. Array
feature dimensions are read with NumPy ``mmap_mode="r"`` so no full array is
materialized.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from secureids.training.config import TrainingConfig, load_training_config

SPLITS: tuple[str, ...] = ("train", "val", "test")


def load_numpy_split(
    processed_dir: Path | str,
    split: str,
    mmap: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Load ``X_<split>.npy`` and ``y_<split>.npy`` from a processed directory.

    Feature matrices use ``mmap_mode="r"`` when ``mmap`` is True. Labels are
    small and always loaded fully. Torch is not required.
    """

    if split not in SPLITS:
        raise ValueError(f"split must be one of {SPLITS}, got {split!r}.")

    base = Path(processed_dir)
    x_path = base / f"X_{split}.npy"
    y_path = base / f"y_{split}.npy"
    if not x_path.exists():
        raise FileNotFoundError(f"Missing feature array: {x_path}.")
    if not y_path.exists():
        raise FileNotFoundError(f"Missing label array: {y_path}.")

    X = np.load(x_path, mmap_mode="r" if mmap else None)
    y = np.load(y_path)
    return X, y


def load_feature_names(path: Path | str) -> list[str]:
    """Load feature names stored as ``{"feature_names": [...]}``.

    A bare top-level list is tolerated for robustness.
    """

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        names = payload.get("feature_names")
        if not isinstance(names, list):
            raise ValueError(f"{path} must contain a 'feature_names' list.")
        return list(names)
    if isinstance(payload, list):
        return list(payload)
    raise ValueError(f"Unsupported feature_names format in {path}.")


def load_label_mapping(path: Path | str) -> dict[str, Any]:
    """Load the binary label mapping JSON as a dict."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def get_input_dim_from_processed(processed_dir: Path | str) -> int:
    """Return the feature count from ``X_train.npy`` without loading it fully."""

    X, _ = load_numpy_split(processed_dir, "train", mmap=True)
    return int(X.shape[1])


def build_training_plan(config: TrainingConfig) -> dict[str, Any]:
    """Validate processed-artifact availability and summarize the planned run.

    Reads only array headers (via mmap) and small JSON files; no full arrays are
    materialized, no torch is imported, and no training is performed. The
    detected feature dimension of every available split is compared against the
    config ``input_dim``.
    """

    processed = config.resolve(config.processed_dir)
    splits: dict[str, dict[str, Any]] = {}
    split_dims: dict[str, int] = {}
    for split in SPLITS:
        x_path = processed / f"X_{split}.npy"
        y_path = processed / f"y_{split}.npy"
        x_exists = x_path.exists()
        y_exists = y_path.exists()
        detected = None
        if x_exists:
            detected = int(np.load(x_path, mmap_mode="r").shape[1])
            split_dims[split] = detected
        splits[split] = {
            "X_path": str(x_path),
            "X_exists": x_exists,
            "y_path": str(y_path),
            "y_exists": y_exists,
            "detected_input_dim": detected,
            "input_dim_matches": (
                detected == config.input_dim if detected is not None else None
            ),
        }

    detected_input_dim = split_dims.get("train")
    input_dim_matches: bool | None = None
    if split_dims:
        input_dim_matches = all(dim == config.input_dim for dim in split_dims.values())

    feature_names_path = config.resolve(config.feature_names_path)
    feature_count: int | None = None
    feature_names_match: bool | None = None
    if feature_names_path.exists():
        feature_count = len(load_feature_names(feature_names_path))
        feature_names_match = feature_count == config.input_dim

    label_mapping_path = config.resolve(config.label_mapping_path)
    preprocessing_manifest_path = config.resolve(config.preprocessing_manifest_path)

    all_inputs_available = all(
        split["X_exists"] and split["y_exists"] for split in splits.values()
    )

    return {
        "dataset": config.dataset,
        "task": config.task,
        "processed_dir": str(processed),
        "processed_dir_exists": processed.exists(),
        "config_input_dim": config.input_dim,
        "detected_input_dim": detected_input_dim,
        "input_dim_matches": input_dim_matches,
        "feature_count": feature_count,
        "feature_names_match": feature_names_match,
        "feature_names_path": str(feature_names_path),
        "feature_names_exists": feature_names_path.exists(),
        "label_mapping_path": str(label_mapping_path),
        "label_mapping_exists": label_mapping_path.exists(),
        "preprocessing_manifest_path": str(preprocessing_manifest_path),
        "preprocessing_manifest_exists": preprocessing_manifest_path.exists(),
        "splits": splits,
        "all_inputs_available": all_inputs_available,
        "training": {
            "seed": config.training.seed,
            "batch_size": config.training.batch_size,
            "max_epochs": config.training.max_epochs,
            "learning_rate": config.training.learning_rate,
            "optimizer": config.training.optimizer,
            "weight_decay": config.training.weight_decay,
            "early_stopping_metric": config.training.early_stopping_metric,
            "early_stopping_patience": config.training.early_stopping_patience,
            "use_pos_weight": config.training.use_pos_weight,
        },
        "model": {
            "architecture": config.model.architecture,
            "hidden_dims": config.model.hidden_dims,
            "dropout": config.model.dropout,
            "output_dim": config.model.output_dim,
        },
        "would_create": {
            "checkpoint": str(config.resolve(config.output_checkpoint)),
            "history_csv": str(config.resolve(config.outputs.history_csv)),
            "metrics_json": str(config.resolve(config.outputs.metrics_json)),
            "confusion_matrix_csv": str(
                config.resolve(config.outputs.confusion_matrix_csv)
            ),
            "manifest_json": str(config.resolve(config.outputs.manifest_json)),
        },
    }


def run_centralized_dry_run(
    config_path: Path | str,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Load/validate a config and return a torch-free dry-run plan.

    Creates nothing. Raises ``TrainingConfigError`` or ``FileNotFoundError`` on
    invalid configs or missing required artifacts.
    """

    config = load_training_config(config_path, project_root=project_root)
    plan = build_training_plan(config)
    plan["executed"] = False
    plan["note"] = (
        "Dry-run validation only. No training, checkpoints, or metrics were created."
    )
    return plan
