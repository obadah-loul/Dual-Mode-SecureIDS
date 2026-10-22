"""Validation helpers shared by preprocessing dry runs and execution."""

from __future__ import annotations

from secureids.artifacts import load_numpy_readonly

from typing import Any

import numpy as np


def normalize_label_value(value: Any) -> str:
    return str(value).strip()


def map_binary_label(value: Any, mapping_config: dict[str, Any]) -> int:
    """Map a raw label value to the binary IDS target."""

    if "benign_values" in mapping_config:
        benign_values = {
            normalize_label_value(item)
            for item in mapping_config.get("benign_values", [])
        }
        return 0 if normalize_label_value(value) in benign_values else 1

    normal_value = mapping_config.get("normal_value", 0)
    attack_value = mapping_config.get("attack_value", 1)
    if value == normal_value or normalize_label_value(value) == str(normal_value):
        return 0
    if value == attack_value or normalize_label_value(value) == str(attack_value):
        return 1
    raise ValueError(f"Unsupported binary label value: {value!r}")


def target_column_status(columns: list[str], target_column: str) -> dict[str, Any]:
    stripped = [column.strip() for column in columns]
    return {
        "column": target_column,
        "present": target_column in stripped,
        "status": "present" if target_column in stripped else "missing",
    }


def drop_column_status(columns: list[str], drop_columns: list[str]) -> dict[str, str]:
    stripped = {column.strip() for column in columns}
    return {
        column: "present" if column in stripped else "not present"
        for column in drop_columns
    }


def separate_features_target(
    row: dict[str, Any],
    target_column: str,
    drop_columns: list[str],
) -> tuple[dict[str, Any], Any]:
    """Separate one sample row into features and target."""

    target = row.get(target_column)
    drop_set = set(drop_columns)
    features = {
        key: value
        for key, value in row.items()
        if key not in drop_set and key != target_column
    }
    return features, target


def check_no_target_leakage(
    feature_names: list[str],
    forbidden_columns: list[str],
) -> dict[str, Any]:
    leaked = [column for column in forbidden_columns if column in feature_names]
    return {
        "passed": not leaked,
        "leaked_columns": leaked,
    }


def label_distribution(labels: np.ndarray) -> dict[str, int]:
    """Return binary label counts as a JSON-friendly mapping."""

    unique, counts = np.unique(labels.astype(np.int64, copy=False), return_counts=True)
    return {str(int(label)): int(count) for label, count in zip(unique, counts)}


def verify_expected_outputs(
    output_dir,
    feature_names: list[str],
    forbidden_columns: list[str],
) -> dict[str, Any]:
    """Verify processed arrays without computing model metrics."""

    output_dir = str(output_dir)
    arrays = {
        "X_train": load_numpy_readonly(f"{output_dir}/X_train.npy", mmap_mode="r"),
        "X_val": load_numpy_readonly(f"{output_dir}/X_val.npy", mmap_mode="r"),
        "X_test": load_numpy_readonly(f"{output_dir}/X_test.npy", mmap_mode="r"),
        "y_train": load_numpy_readonly(f"{output_dir}/y_train.npy", mmap_mode="r"),
        "y_val": load_numpy_readonly(f"{output_dir}/y_val.npy", mmap_mode="r"),
        "y_test": load_numpy_readonly(f"{output_dir}/y_test.npy", mmap_mode="r"),
    }

    x_shapes = {name: tuple(array.shape) for name, array in arrays.items() if name.startswith("X_")}
    y_shapes = {name: tuple(array.shape) for name, array in arrays.items() if name.startswith("y_")}
    feature_dims = {shape[1] for shape in x_shapes.values()}

    finite = {
        name: bool(np.isfinite(array).all())
        for name, array in arrays.items()
        if name.startswith("X_")
    }
    label_values = {
        name: [int(value) for value in np.unique(array)]
        for name, array in arrays.items()
        if name.startswith("y_")
    }

    return {
        "x_shapes": {key: list(value) for key, value in x_shapes.items()},
        "y_shapes": {key: list(value) for key, value in y_shapes.items()},
        "x_arrays_are_2d": all(len(shape) == 2 for shape in x_shapes.values()),
        "y_arrays_are_1d": all(len(shape) == 1 for shape in y_shapes.values()),
        "consistent_feature_count": len(feature_dims) == 1,
        "feature_names_match_dimension": (
            len(feature_dims) == 1 and len(feature_names) == next(iter(feature_dims))
        ),
        "x_arrays_finite": finite,
        "labels": label_values,
        "labels_binary_only": all(set(values).issubset({0, 1}) for values in label_values.values()),
        "target_leakage": check_no_target_leakage(feature_names, forbidden_columns),
    }
