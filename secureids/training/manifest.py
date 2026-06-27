"""Training manifest helpers for reproducibility and auditing.

A training manifest records exactly how a checkpoint was produced: data paths,
input dimension, class distribution computed from the training split only, the
applied ``pos_weight``, the model architecture, hyperparameters, output paths,
and explicit safety flags. This feeds the reproducibility and reporting layers.

IMPORTANT: no manifest file is written during the implementation-readiness task.
:func:`save_training_manifest` exists for the approved Task 8B run only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from secureids.preprocessing.artifacts import load_json, save_json, utc_timestamp


def build_training_manifest(
    *,
    dataset: str,
    task: str,
    model_metadata: dict[str, Any],
    config_path: str | Path,
    processed_dir: str | Path,
    processed_paths: dict[str, str],
    preprocessing_manifest_path: str | Path,
    preprocessing_safety_check_path: str | Path,
    feature_names_path: str | Path,
    label_mapping_path: str | Path,
    checkpoint_path: str | Path,
    output_paths: dict[str, str],
    input_dim: int,
    feature_count: int,
    split_shapes: dict[str, Any],
    class_distribution: dict[str, int],
    pos_weight: float | None,
    seed: int,
    device: str,
    max_epochs: int,
    early_stopping: dict[str, Any],
    training_params: dict[str, Any],
    safety: dict[str, Any],
) -> dict[str, Any]:
    """Assemble a reproducibility manifest for a centralized training run.

    ``class_distribution`` and ``pos_weight`` must be derived from the training
    split only. ``safety`` carries the run-scope flags (final_checkpoint,
    test_set_used_for_tuning, preprocessing_safety_check_passed, and the
    not-in-this-run markers) so every consumer reads one authoritative block.
    """

    return {
        "dataset": dataset,
        "task": task,
        "model": model_metadata,
        "config_path": str(config_path),
        "processed_dir": str(processed_dir),
        "processed_paths": processed_paths,
        "preprocessing_manifest_path": str(preprocessing_manifest_path),
        "preprocessing_safety_check_path": str(preprocessing_safety_check_path),
        "feature_names_path": str(feature_names_path),
        "label_mapping_path": str(label_mapping_path),
        "checkpoint_path": str(checkpoint_path),
        "output_paths": output_paths,
        "input_dim": int(input_dim),
        "feature_count": int(feature_count),
        "split_shapes": split_shapes,
        "class_distribution_train": class_distribution,
        "pos_weight": pos_weight,
        "seed": int(seed),
        "device": device,
        "max_epochs": int(max_epochs),
        "early_stopping": early_stopping,
        "training": training_params,
        "safety": safety,
        "created_utc": utc_timestamp(),
    }


def save_training_manifest(path: Path | str, manifest: dict[str, Any]) -> Path:
    """Write a training manifest as pretty JSON. Not called during Task 8A."""

    target = Path(path)
    save_json(target, manifest)
    return target


def load_training_manifest(path: Path | str) -> dict[str, Any]:
    """Load a previously saved training manifest."""

    return load_json(Path(path))
