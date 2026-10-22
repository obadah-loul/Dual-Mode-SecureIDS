"""Read-only planning checks for future hierarchical model training.

Task A6 prepares hierarchical training and smoke-training plans only. The
functions here inspect config structure, small JSON metadata, and NumPy array
headers with ``mmap_mode="r"``. They do not train, evaluate, create
DataLoaders, write metrics, or save checkpoints.
"""

from __future__ import annotations

from secureids.artifacts import load_numpy_readonly, read_artifact_path

import json
from pathlib import Path
from typing import Any

import numpy as np

from secureids.training.hierarchical_config import (
    HierarchicalSmokeConfig,
    HierarchicalTrainingConfig,
    load_hierarchical_smoke_config,
    load_hierarchical_training_config,
)

SPLITS: tuple[str, ...] = ("train", "val", "test")
ARRAY_STEMS: dict[str, str] = {
    "X": "X_{split}.npy",
    "y_binary": "y_binary_{split}.npy",
    "y_attack_family": "y_attack_family_{split}.npy",
    "attack_family_mask": "attack_family_mask_{split}.npy",
}
METADATA_FILENAMES: tuple[str, ...] = (
    "feature_names.json",
    "binary_label_mapping.json",
    "attack_family_label_mapping.json",
    "common_attack_superclass_mapping.json",
    "split_summary.json",
    "hierarchical_preprocessing_manifest.json",
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}.")
    return payload


def _feature_names_count(path: Path) -> int | None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        names = payload.get("feature_names")
    else:
        names = payload
    return len(names) if isinstance(names, list) else None


def _array_shape(path: Path) -> tuple[int, ...] | None:
    if not path.exists():
        return None
    array = load_numpy_readonly(path, mmap_mode="r")
    try:
        return tuple(int(dim) for dim in array.shape)
    finally:
        mmap = getattr(array, "_mmap", None)
        if mmap is not None:
            mmap.close()


def _check(checks: list[dict[str, str]], name: str, passed: bool, detail: str) -> None:
    checks.append(
        {
            "name": name,
            "status": "PASS" if passed else "FAIL",
            "detail": detail,
        }
    )


def _overall_status(checks: list[dict[str, str]]) -> str:
    return "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL"


def _path_status(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
    }


def _planned_final_outputs(config: HierarchicalTrainingConfig) -> dict[str, str]:
    return {
        key: str(config.resolve(value))
        for key, value in config.outputs.items()
        if key != "result_dir"
    }


def _final_output_files_absent(config: HierarchicalTrainingConfig) -> bool:
    return all(
        not config.resolve(value).exists()
        for key, value in config.outputs.items()
        if key != "result_dir"
    )


def _is_a11_protocol(payload: dict[str, Any]) -> bool:
    return str(payload.get("protocol_name")) == "UNSW A11 Enhanced Feature Protocol"


def build_hierarchical_training_plan(
    config: HierarchicalTrainingConfig,
) -> dict[str, Any]:
    """Return a read-only plan for a future full hierarchical training run."""

    checks: list[dict[str, str]] = []
    data_dir = config.resolve(config.hierarchical_data_dir)
    feature_names_path = config.resolve(config.feature_names_path)
    mapping_path = config.resolve(config.attack_family_label_mapping_path)
    manifest_path = config.resolve(config.preprocessing_manifest_path)
    readiness_path = config.resolve(config.readiness_json)
    taxonomy_path = config.resolve(config.taxonomy_config)

    _check(checks, "hierarchical_data_dir_exists", data_dir.is_dir(), str(data_dir))
    _check(checks, "feature_names_exists", feature_names_path.is_file(), str(feature_names_path))
    _check(checks, "attack_family_mapping_exists", mapping_path.is_file(), str(mapping_path))
    _check(checks, "preprocessing_manifest_exists", manifest_path.is_file(), str(manifest_path))
    _check(checks, "readiness_json_exists", readiness_path.is_file(), str(readiness_path))
    _check(checks, "taxonomy_config_exists", taxonomy_path.is_file(), str(taxonomy_path))

    metadata_paths = {name: data_dir / name for name in METADATA_FILENAMES}
    missing_metadata = [name for name, path in metadata_paths.items() if not path.is_file()]
    _check(
        checks,
        "all_hierarchical_metadata_files_exist",
        not missing_metadata,
        f"missing={missing_metadata}",
    )

    feature_count: int | None = None
    if feature_names_path.exists():
        feature_count = _feature_names_count(feature_names_path)
    _check(
        checks,
        "feature_count_matches_input_dim",
        feature_count == config.input_dim,
        f"feature_count={feature_count}, input_dim={config.input_dim}",
    )

    attack_family_class_count: int | None = None
    rare_raw_labels: list[Any] = []
    if mapping_path.exists():
        mapping = _load_json(mapping_path)
        class_to_id = mapping.get("class_to_id")
        if isinstance(class_to_id, dict):
            attack_family_class_count = len(class_to_id)
        raw_rare = mapping.get("rare_raw_labels", [])
        rare_raw_labels = list(raw_rare) if isinstance(raw_rare, list) else []
    _check(
        checks,
        "attack_family_class_count_matches_head_dim",
        attack_family_class_count == config.attack_head_dim,
        (
            f"class_count={attack_family_class_count}, "
            f"attack_head_dim={config.attack_head_dim}"
        ),
    )

    readiness_status: str | None = None
    readiness_ready: bool | None = None
    if readiness_path.exists():
        readiness = _load_json(readiness_path)
        readiness_status = str(readiness.get("status"))
        readiness_ready = bool(readiness.get("ready_for_hierarchical_model_implementation", False))
        if _is_a11_protocol(readiness) and readiness_status == "PASS":
            readiness_ready = bool(
                readiness.get("train_only_fitting") is True
                and readiness.get("numeric_only_scaling") is True
                and readiness.get("one_hot_columns_not_scaled") is True
                and readiness.get("no_test_fitting") is True
                and readiness.get("no_test_label_feature_selection") is True
                and readiness.get("no_test_tuning") is True
            )
    _check(
        checks,
        "preprocessing_readiness_passed",
        readiness_status == "PASS" and readiness_ready is True,
        f"status={readiness_status}, ready={readiness_ready}",
    )

    manifest_status: str | None = None
    manifest_task: str | None = None
    manifest_feature_dim: int | None = None
    if manifest_path.exists():
        manifest = _load_json(manifest_path)
        manifest_status = str(manifest.get("status"))
        manifest_task = str(manifest.get("task"))
        if manifest.get("feature_dim") is not None:
            manifest_feature_dim = int(manifest["feature_dim"])
        elif manifest.get("feature_count") is not None:
            manifest_feature_dim = int(manifest["feature_count"])
        if _is_a11_protocol(manifest) and manifest_status == "A11_PREPROCESSING_EXECUTED":
            manifest_task = "hierarchical_preprocessing"
    _check(
        checks,
        "preprocessing_manifest_matches_hierarchical_task",
        (
            (manifest_status == "PASS" or manifest_status == "A11_PREPROCESSING_EXECUTED")
            and manifest_task == "hierarchical_preprocessing"
        ),
        f"status={manifest_status}, task={manifest_task}",
    )
    _check(
        checks,
        "preprocessing_manifest_feature_dim_matches",
        manifest_feature_dim == config.input_dim,
        f"feature_dim={manifest_feature_dim}, input_dim={config.input_dim}",
    )

    split_shapes: dict[str, dict[str, tuple[int, ...] | None]] = {}
    missing_arrays: list[str] = []
    for split in SPLITS:
        split_shapes[split] = {}
        for label, pattern in ARRAY_STEMS.items():
            path = read_artifact_path(data_dir / pattern.format(split=split))
            if not path.exists():
                missing_arrays.append(path.name)
            split_shapes[split][label] = _array_shape(path)

        X_shape = split_shapes[split]["X"]
        y_binary_shape = split_shapes[split]["y_binary"]
        y_attack_shape = split_shapes[split]["y_attack_family"]
        mask_shape = split_shapes[split]["attack_family_mask"]
        row_count = X_shape[0] if X_shape and len(X_shape) == 2 else None

        _check(
            checks,
            f"{split}_X_is_2d",
            X_shape is not None and len(X_shape) == 2,
            f"shape={X_shape}",
        )
        _check(
            checks,
            f"{split}_feature_dim_matches",
            X_shape is not None and len(X_shape) == 2 and X_shape[1] == config.input_dim,
            f"shape={X_shape}, input_dim={config.input_dim}",
        )
        _check(
            checks,
            f"{split}_label_and_mask_lengths_match_X",
            (
                row_count is not None
                and y_binary_shape == (row_count,)
                and y_attack_shape == (row_count,)
                and mask_shape == (row_count,)
            ),
            (
                f"X={X_shape}, y_binary={y_binary_shape}, "
                f"y_attack_family={y_attack_shape}, mask={mask_shape}"
            ),
        )

    _check(
        checks,
        "all_hierarchical_array_files_exist",
        not missing_arrays,
        f"missing={missing_arrays}",
    )

    final_outputs_absent = _final_output_files_absent(config)
    _check(
        checks,
        "future_final_outputs_absent",
        final_outputs_absent,
        str(_planned_final_outputs(config)),
    )
    _check(
        checks,
        "no_training_execution_in_plan",
        True,
        "planner is read-only and does not train or evaluate",
    )
    _check(
        checks,
        "no_checkpoint_or_metric_creation_in_plan",
        True,
        "planner writes no checkpoints, histories, metrics, or confusion matrices",
    )

    return {
        "dataset": config.dataset,
        "task": config.task,
        "status": _overall_status(checks),
        "config_path": str(config.path),
        "model_name": config.model_name,
        "input_dim": config.input_dim,
        "attack_head_dim": config.attack_head_dim,
        "hierarchical_data_dir": str(data_dir),
        "feature_count": feature_count,
        "attack_family_class_count": attack_family_class_count,
        "rare_raw_labels": rare_raw_labels,
        "split_shapes": split_shapes,
        "metadata": {
            "feature_names": _path_status(feature_names_path),
            "attack_family_label_mapping": _path_status(mapping_path),
            "preprocessing_manifest": _path_status(manifest_path),
            "readiness_json": _path_status(readiness_path),
            "taxonomy_config": _path_status(taxonomy_path),
        },
        "planned_outputs": {
            "checkpoint": str(config.resolve(config.outputs["checkpoint"])),
            "result_dir": str(config.resolve(config.outputs["result_dir"])),
            "files": _planned_final_outputs(config),
        },
        "safety": {
            "training_run": False,
            "evaluation_run": False,
            "checkpoint_created": False,
            "metrics_created": False,
            "fedavg_started": False,
            "security_attack_xai_dashboard_started": False,
            "array_loading_policy": "numpy mmap_mode='r' headers/shapes only",
        },
        "checks": checks,
    }


def build_hierarchical_smoke_plan(config: HierarchicalSmokeConfig) -> dict[str, Any]:
    """Return a read-only plan for a future non-final smoke training command."""

    checks: list[dict[str, str]] = []
    base_config = load_hierarchical_training_config(
        config.resolve(config.base_config),
        project_root=config.project_root,
    )
    data_dir = config.resolve(config.hierarchical_data_dir)
    output_json = config.resolve(str(config.smoke["output_json"]))
    report_md = config.resolve(str(config.smoke["report_md"]))

    _check(checks, "base_config_loads", True, str(base_config.path))
    _check(
        checks,
        "smoke_dataset_matches_base_config",
        config.dataset == base_config.dataset,
        f"smoke={config.dataset}, base={base_config.dataset}",
    )
    _check(
        checks,
        "smoke_input_dim_matches_base_config",
        config.input_dim == base_config.input_dim,
        f"smoke={config.input_dim}, base={base_config.input_dim}",
    )
    _check(
        checks,
        "smoke_attack_head_dim_matches_base_config",
        config.attack_head_dim == base_config.attack_head_dim,
        f"smoke={config.attack_head_dim}, base={base_config.attack_head_dim}",
    )
    _check(checks, "hierarchical_data_dir_exists", data_dir.is_dir(), str(data_dir))
    _check(
        checks,
        "smoke_limits_one_epoch",
        int(config.smoke["max_epochs"]) == 1,
        f"max_epochs={config.smoke['max_epochs']}",
    )
    _check(
        checks,
        "smoke_limits_train_batches",
        int(config.smoke["max_train_batches"]) <= 4,
        f"max_train_batches={config.smoke['max_train_batches']}",
    )
    _check(
        checks,
        "smoke_limits_eval_batches",
        int(config.smoke["max_eval_batches"]) <= 2,
        f"max_eval_batches={config.smoke['max_eval_batches']}",
    )
    _check(
        checks,
        "smoke_disables_checkpoint",
        config.smoke["save_checkpoint"] is False,
        f"save_checkpoint={config.smoke['save_checkpoint']}",
    )
    _check(
        checks,
        "smoke_disables_final_metrics",
        config.smoke["final_metrics"] is False,
        f"final_metrics={config.smoke['final_metrics']}",
    )
    _check(
        checks,
        "smoke_outputs_are_non_final",
        "results\\final" not in str(output_json).lower()
        and "results/final" not in str(output_json).lower()
        and "results\\final" not in str(report_md).lower()
        and "results/final" not in str(report_md).lower(),
        f"output_json={output_json}, report_md={report_md}",
    )
    _check(
        checks,
        "smoke_safety_flags_locked",
        all(bool(value) for value in config.safety.values()),
        str(config.safety),
    )
    _check(
        checks,
        "no_training_execution_in_plan",
        True,
        "planner describes a future smoke run only",
    )
    _check(
        checks,
        "no_checkpoint_or_metric_creation_in_plan",
        True,
        "planner writes no checkpoints or final metrics",
    )

    return {
        "dataset": config.dataset,
        "task": config.task,
        "status": _overall_status(checks),
        "config_path": str(config.path),
        "base_config_path": str(base_config.path),
        "model_name": config.model_name,
        "input_dim": config.input_dim,
        "attack_head_dim": config.attack_head_dim,
        "hierarchical_data_dir": str(data_dir),
        "sample_limits": {
            "train_samples": int(config.smoke["train_samples"]),
            "val_samples": int(config.smoke["val_samples"]),
            "test_samples": int(config.smoke["test_samples"]),
            "batch_size": int(config.smoke["batch_size"]),
            "max_epochs": int(config.smoke["max_epochs"]),
            "max_train_batches": int(config.smoke["max_train_batches"]),
            "max_eval_batches": int(config.smoke["max_eval_batches"]),
        },
        "planned_non_final_outputs": {
            "output_json": str(output_json),
            "report_md": str(report_md),
        },
        "safety": {
            "training_run": False,
            "evaluation_run": False,
            "checkpoint_created": False,
            "metrics_created": False,
            "save_checkpoint": bool(config.smoke["save_checkpoint"]),
            "final_metrics": bool(config.smoke["final_metrics"]),
            "do_not_report_as_final": bool(config.safety["do_not_report_as_final"]),
        },
        "checks": checks,
    }


def run_hierarchical_training_plan(
    config_path: Path | str,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Load a full hierarchical config and return its read-only plan."""

    config = load_hierarchical_training_config(config_path, project_root=project_root)
    return build_hierarchical_training_plan(config)


def run_hierarchical_smoke_plan(
    config_path: Path | str,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Load a smoke hierarchical config and return its read-only plan."""

    config = load_hierarchical_smoke_config(config_path, project_root=project_root)
    return build_hierarchical_smoke_plan(config)
