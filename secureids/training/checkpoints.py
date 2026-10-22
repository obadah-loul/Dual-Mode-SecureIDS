"""Checkpoint payload helpers for centralized (and later federated) training.

The payload bundles the model weights with enough metadata for the dashboard,
XAI, and reproducibility layers to load a model without re-deriving anything:
dataset name, input dimension, feature names, label mapping, the preprocessing
manifest path, a config snapshot, and an optional metrics summary.

IMPORTANT: this module only *builds* payloads and provides save/load helpers.
No checkpoint is written during the implementation-readiness task; saving is
deferred to the approved Task 8B training run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import torch

from secureids.preprocessing.artifacts import utc_timestamp

CHECKPOINT_FORMAT_VERSION = 1


def build_checkpoint_payload(
    *,
    model_state_dict: dict[str, Any],
    config_snapshot: dict[str, Any],
    dataset: str,
    input_dim: int,
    feature_names: list[str],
    label_mapping: dict[str, Any],
    preprocessing_manifest_path: str | Path,
    task: str = "binary",
    architecture_metadata: dict[str, Any] | None = None,
    metrics_summary: dict[str, Any] | None = None,
    safety: dict[str, Any] | None = None,
    run_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble a serializable checkpoint payload.

    ``metrics_summary`` stays ``None`` until real evaluation has produced
    metrics; this function never fabricates results. ``safety`` carries the
    run-scope safety flags (final_checkpoint, test_set_used_for_tuning,
    no_federated_training, ...) and ``run_metadata`` carries reproducibility
    fields (feature_count, class distribution, pos_weight, device, seed).
    """

    return {
        "format_version": CHECKPOINT_FORMAT_VERSION,
        "architecture": "SecureIDSNet",
        "dataset": dataset,
        "task": task,
        "input_dim": int(input_dim),
        "model_state_dict": model_state_dict,
        "architecture_metadata": architecture_metadata,
        "config_snapshot": config_snapshot,
        "feature_names": list(feature_names),
        "label_mapping": label_mapping,
        "preprocessing_manifest_path": str(preprocessing_manifest_path),
        "metrics_summary": metrics_summary,
        "safety": safety,
        "run_metadata": run_metadata,
        "created_utc": utc_timestamp(),
    }


def save_checkpoint(payload: dict[str, Any], path: Path | str) -> Path:
    """Persist a checkpoint payload with ``torch.save``.

    Not called during Task 8A. Parent directories are created on demand.
    """

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, target)
    return target


def load_checkpoint(path: Path | str, map_location: str = "cpu") -> dict[str, Any]:
    """Load tensors and primitive metadata with PyTorch's restricted loader.

    Unsupported legacy objects fail closed. Never retry with unrestricted
    pickle or automatically allowlist classes from an artifact.
    """
    payload = torch.load(Path(path), map_location=map_location, weights_only=True)
    if not isinstance(payload, dict):
        raise ValueError('Checkpoint must contain a dictionary payload.')
    return payload
