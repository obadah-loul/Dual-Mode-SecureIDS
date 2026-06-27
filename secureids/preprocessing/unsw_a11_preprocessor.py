"""UNSW A11 Enhanced Feature Protocol preprocessing support.

The public entry point supports a safe dry-run that writes nothing and an
execution path for a future main-control-approved preprocessing run. The tests
exercise the validation and transformation helpers without running project A11
preprocessing.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from secureids.preprocessing.artifacts import save_joblib, save_json, utc_timestamp
from secureids.preprocessing.cleaning import clean_numeric_frame, strip_column_whitespace
from secureids.preprocessing.hierarchical import (
    build_binary_mapping,
    build_mapping_payloads,
    build_taxonomy_info,
    load_yaml,
)
from secureids.preprocessing.splitting import split_train_validation
from secureids.preprocessing.unsw_a11_config import (
    A11_PROCESSED_PREFIX,
    UNSWA11ConfigError,
    UNSWA11PreprocessingConfig,
    load_unsw_a11_preprocessing_config,
)
from secureids.preprocessing.validation import check_no_target_leakage, map_binary_label


class UNSWA11PreprocessingError(ValueError):
    """Raised when A11 preprocessing refuses to proceed safely."""


@dataclass(frozen=True)
class CategoryGroupingRule:
    column: str
    enabled: bool
    method: str
    kept_values: tuple[str, ...]
    other_bucket: str | None
    train_category_counts: dict[str, int]
    min_frequency: int | None = None
    top_k: int | None = None


@dataclass
class A11FeatureTransformer:
    numeric_columns: list[str]
    categorical_columns: list[str]
    imputer: SimpleImputer
    scaler: StandardScaler
    encoder: OneHotEncoder
    grouping_rules: dict[str, CategoryGroupingRule]
    feature_names: list[str]


def run_unsw_a11_preprocessing(
    config_path: str | Path,
    *,
    execute: bool,
    project_root: Path,
) -> dict[str, Any]:
    """Validate or execute the A11 preprocessing protocol.

    ``execute=False`` is a dry-run and writes nothing. ``execute=True`` is for a
    future approved manual run only.
    """

    config = load_unsw_a11_preprocessing_config(config_path, project_root=project_root)
    if not execute:
        return build_dry_run_plan(config)
    return execute_unsw_a11_preprocessing(config)


def build_dry_run_plan(config: UNSWA11PreprocessingConfig) -> dict[str, Any]:
    outputs = planned_output_paths(config)
    partial_state = inspect_partial_output_state(config)
    return {
        "status": "DRY_RUN_NOT_EXECUTED",
        "protocol_name": config.protocol_name,
        "dataset": config.dataset,
        "config_path": str(config.path),
        "planned_outputs": {key: str(path) for key, path in outputs.items()},
        "planned_outputs_exist": {key: path.exists() for key, path in outputs.items()},
        "partial_outputs": partial_state,
        "would_write": False,
        "preprocessing_run": False,
        "training_run": False,
        "evaluation_run": False,
        "checkpoint_created": False,
        "final_paths_targeted": False,
        "next_step": "Pass --execute only after main-control approval to create A11 preprocessing outputs.",
    }


def planned_output_paths(config: UNSWA11PreprocessingConfig) -> dict[str, Path]:
    paths = {
        key: config.resolve(value)
        for key, value in config.planned_outputs.items()
    }
    paths.update(
        {
            "x_train": config.resolve(config.planned_outputs["hierarchical_data_dir"]) / "X_train.npy",
            "x_val": config.resolve(config.planned_outputs["hierarchical_data_dir"]) / "X_val.npy",
            "x_test": config.resolve(config.planned_outputs["hierarchical_data_dir"]) / "X_test.npy",
            "y_binary_train": config.resolve(config.planned_outputs["hierarchical_data_dir"]) / "y_binary_train.npy",
            "y_binary_val": config.resolve(config.planned_outputs["hierarchical_data_dir"]) / "y_binary_val.npy",
            "y_binary_test": config.resolve(config.planned_outputs["hierarchical_data_dir"]) / "y_binary_test.npy",
            "y_attack_family_train": config.resolve(config.planned_outputs["hierarchical_data_dir"]) / "y_attack_family_train.npy",
            "y_attack_family_val": config.resolve(config.planned_outputs["hierarchical_data_dir"]) / "y_attack_family_val.npy",
            "y_attack_family_test": config.resolve(config.planned_outputs["hierarchical_data_dir"]) / "y_attack_family_test.npy",
            "attack_family_mask_train": config.resolve(config.planned_outputs["hierarchical_data_dir"]) / "attack_family_mask_train.npy",
            "attack_family_mask_val": config.resolve(config.planned_outputs["hierarchical_data_dir"]) / "attack_family_mask_val.npy",
            "attack_family_mask_test": config.resolve(config.planned_outputs["hierarchical_data_dir"]) / "attack_family_mask_test.npy",
            "binary_x_train": config.resolve(config.planned_outputs["binary_data_dir"]) / "X_train.npy",
            "binary_x_val": config.resolve(config.planned_outputs["binary_data_dir"]) / "X_val.npy",
            "binary_x_test": config.resolve(config.planned_outputs["binary_data_dir"]) / "X_test.npy",
            "binary_y_train": config.resolve(config.planned_outputs["binary_data_dir"]) / "y_train.npy",
            "binary_y_val": config.resolve(config.planned_outputs["binary_data_dir"]) / "y_val.npy",
            "binary_y_test": config.resolve(config.planned_outputs["binary_data_dir"]) / "y_test.npy",
        }
    )
    return paths


def ensure_output_paths_are_clear(config: UNSWA11PreprocessingConfig) -> None:
    """Refuse execution when any A11 output already exists."""

    partial_state = inspect_partial_output_state(config)
    if partial_state["detected"]:
        raise UNSWA11PreprocessingError(
            "A11 preprocessing refuses to run because existing A11 partial outputs "
            f"were detected under {partial_state['processed_dir']} "
            f"(classification={partial_state['classification']}). Cleanup or rerun "
            "approval must come from main control; no overwrite is allowed by default."
        )

    outputs = planned_output_paths(config)
    existing = [str(path) for path in outputs.values() if path.exists()]
    if existing:
        raise UNSWA11PreprocessingError(
            "A11 preprocessing refuses overwrite by default; existing paths: "
            + ", ".join(sorted(existing))
        )

    processed_dir = config.resolve(config.planned_outputs["processed_data_dir"])
    if A11_PROCESSED_PREFIX not in str(processed_dir).replace("\\", "/"):
        raise UNSWA11PreprocessingError("A11 processed output directory is not A11-specific.")


def inspect_partial_output_state(config: UNSWA11PreprocessingConfig) -> dict[str, Any]:
    """Classify existing A11 output state without reading full arrays."""

    processed_dir = config.resolve(config.planned_outputs["processed_data_dir"])
    hierarchical_dir = config.resolve(config.planned_outputs["hierarchical_data_dir"])
    binary_dir = config.resolve(config.planned_outputs["binary_data_dir"])
    required_validators = [
        hierarchical_dir / "split_summary.json",
        hierarchical_dir / "hierarchical_preprocessing_manifest.json",
        config.resolve(config.planned_outputs["preprocessing_audit"]),
        config.resolve(config.planned_outputs["preprocessor_artifact"]),
    ]
    expected_arrays_and_mappings = [
        binary_dir / "X_train.npy",
        binary_dir / "X_val.npy",
        binary_dir / "X_test.npy",
        binary_dir / "y_train.npy",
        binary_dir / "y_val.npy",
        binary_dir / "y_test.npy",
        hierarchical_dir / "X_train.npy",
        hierarchical_dir / "X_val.npy",
        hierarchical_dir / "X_test.npy",
        hierarchical_dir / "y_binary_train.npy",
        hierarchical_dir / "y_binary_val.npy",
        hierarchical_dir / "y_binary_test.npy",
        hierarchical_dir / "y_attack_family_train.npy",
        hierarchical_dir / "y_attack_family_val.npy",
        hierarchical_dir / "y_attack_family_test.npy",
        hierarchical_dir / "attack_family_mask_train.npy",
        hierarchical_dir / "attack_family_mask_val.npy",
        hierarchical_dir / "attack_family_mask_test.npy",
        hierarchical_dir / "feature_names.json",
        hierarchical_dir / "binary_label_mapping.json",
        hierarchical_dir / "attack_family_label_mapping.json",
        hierarchical_dir / "common_attack_superclass_mapping.json",
    ]

    files_checked = [
        {
            "path": str(path),
            "exists": path.exists(),
            "size_bytes": int(path.stat().st_size) if path.exists() and path.is_file() else None,
        }
        for path in [*expected_arrays_and_mappings, *required_validators]
    ]
    detected = processed_dir.exists() or any(row["exists"] for row in files_checked)
    expected_present = all(path.exists() for path in expected_arrays_and_mappings)
    validators_present = all(path.exists() for path in required_validators)
    if not detected:
        classification = "none"
    elif validators_present and expected_present:
        classification = "complete_but_unvalidated"
    elif expected_present and not validators_present:
        classification = "incomplete"
    else:
        classification = "incomplete"

    return {
        "processed_dir": str(processed_dir),
        "detected": bool(detected),
        "classification": classification,
        "expected_arrays_and_mappings_present": bool(expected_present),
        "completion_validators_present": bool(validators_present),
        "safe_to_use_for_training": False,
        "requires_cleanup_approval": bool(detected),
        "files_checked": files_checked,
    }


def execute_unsw_a11_preprocessing(config: UNSWA11PreprocessingConfig) -> dict[str, Any]:
    """Run the future approved A11 preprocessing execution."""

    ensure_output_paths_are_clear(config)

    train_file = config.resolve(config.canonical_split["train_source"]["local_file"])
    test_file = config.resolve(config.canonical_split["test_source"]["local_file"])
    if not train_file.exists() or not test_file.exists():
        raise FileNotFoundError(f"UNSW raw files missing: {train_file}, {test_file}")

    raw_train = pd.read_csv(train_file)
    raw_test = pd.read_csv(test_file)
    raw_train.columns = strip_column_whitespace(list(raw_train.columns))
    raw_test.columns = strip_column_whitespace(list(raw_test.columns))

    required_columns = set(config.drop_columns) | set(config.categorical_columns)
    missing_train = sorted(required_columns - set(raw_train.columns))
    missing_test = sorted(required_columns - set(raw_test.columns))
    if missing_train or missing_test:
        raise UNSWA11PreprocessingError(
            f"Missing UNSW columns. train={missing_train}, test={missing_test}"
        )

    binary_mapping = {"normal_value": 0, "attack_value": 1}
    binary_column = config.target_columns["binary_label"]
    y_official_train = raw_train[binary_column].map(
        lambda value: map_binary_label(value, binary_mapping)
    ).to_numpy(dtype=np.int64)
    y_test = raw_test[binary_column].map(
        lambda value: map_binary_label(value, binary_mapping)
    ).to_numpy(dtype=np.int64)

    validation = config.canonical_split["validation"]
    train_frame, val_frame, y_train, y_val = split_train_validation(
        raw_train,
        y_official_train,
        val_size=float(validation["val_size_from_train"]),
        random_seed=int(validation["random_seed"]),
    )
    test_frame = raw_test

    transformer, x_train, transform_summaries = fit_transform_a11_features(
        train_frame=train_frame,
        val_frame=val_frame,
        test_frame=test_frame,
        config=config,
    )
    x_val, val_summary = transform_a11_features(transformer, val_frame, split_name="val")
    x_test, test_summary = transform_a11_features(transformer, test_frame, split_name="test")
    transform_summaries["val"] = val_summary
    transform_summaries["test"] = test_summary

    taxonomy = load_yaml(config.resolve(config.taxonomy_config_path))
    taxonomy_info = build_taxonomy_info(taxonomy)
    labels = build_hierarchical_labels(
        splits={
            "train": (train_frame, y_train),
            "val": (val_frame, y_val),
            "test": (test_frame, y_test),
        },
        taxonomy_info=taxonomy_info,
        attack_column=config.target_columns["attack_family_label"],
    )

    hierarchical_dir = config.resolve(config.planned_outputs["hierarchical_data_dir"])
    binary_dir = config.resolve(config.planned_outputs["binary_data_dir"])
    hierarchical_dir.mkdir(parents=True, exist_ok=True)
    binary_dir.mkdir(parents=True, exist_ok=True)

    save_feature_arrays(hierarchical_dir, x_train, x_val, x_test, labels)
    save_binary_arrays(binary_dir, x_train, x_val, x_test, y_train, y_val, y_test)

    mappings = build_mapping_payloads("unsw_nb15", taxonomy, taxonomy_info)
    save_json(hierarchical_dir / "feature_names.json", {"feature_names": transformer.feature_names})
    save_json(hierarchical_dir / "binary_label_mapping.json", build_binary_mapping("unsw_nb15", taxonomy))
    save_json(hierarchical_dir / "attack_family_label_mapping.json", mappings["attack_family"])
    save_json(hierarchical_dir / "common_attack_superclass_mapping.json", mappings["common"])

    split_summary = build_a11_split_summary(x_train, x_val, x_test, labels, taxonomy_info)
    save_json(hierarchical_dir / "split_summary.json", split_summary)

    manifest = build_a11_manifest(config, transformer, split_summary, transform_summaries)
    save_json(hierarchical_dir / "hierarchical_preprocessing_manifest.json", manifest)
    save_json(binary_dir / "feature_names.json", {"feature_names": transformer.feature_names})
    save_json(binary_dir / "label_mapping.json", {"0": "Benign / Normal", "1": "Attack"})
    save_json(binary_dir / "split_summary.json", split_summary["binary"])

    save_joblib(
        config.resolve(config.planned_outputs["preprocessor_artifact"]),
        {
            "protocol_name": config.protocol_name,
            "numeric_columns": transformer.numeric_columns,
            "categorical_columns": transformer.categorical_columns,
            "feature_names": transformer.feature_names,
            "imputer": transformer.imputer,
            "scaler": transformer.scaler,
            "encoder": transformer.encoder,
            "grouping_rules": transformer.grouping_rules,
            "config_snapshot": config.raw,
            "created_timestamp": utc_timestamp(),
        },
    )
    write_feature_inventory(config, transformer)
    write_category_inventory(config, transformer)
    write_separability_placeholder(config, labels, taxonomy_info)
    audit = build_preprocessing_audit(config, transformer, split_summary, transform_summaries)
    save_json(config.resolve(config.planned_outputs["preprocessing_audit"]), audit)

    return {
        "status": "EXECUTED",
        "protocol_name": config.protocol_name,
        "feature_count": len(transformer.feature_names),
        "split_summary": split_summary,
        "outputs": {key: str(path) for key, path in planned_output_paths(config).items()},
    }


def fit_transform_a11_features(
    *,
    train_frame: pd.DataFrame,
    val_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    config: UNSWA11PreprocessingConfig,
) -> tuple[A11FeatureTransformer, np.ndarray, dict[str, dict[str, Any]]]:
    """Fit train-only A11 feature transforms and transform the train split."""

    transformer = fit_a11_feature_transformer(train_frame, config)
    x_train, train_summary = transform_a11_features(transformer, train_frame, split_name="train")
    # Build summaries here so callers can inspect unknown category behavior
    # without writing output files.
    _, val_summary = transform_a11_features(transformer, val_frame, split_name="val")
    _, test_summary = transform_a11_features(transformer, test_frame, split_name="test")
    return transformer, x_train, {"train": train_summary, "val": val_summary, "test": test_summary}


def fit_a11_feature_transformer(
    train_frame: pd.DataFrame,
    config: UNSWA11PreprocessingConfig,
) -> A11FeatureTransformer:
    """Fit numeric imputer/scaler and categorical grouping/encoder on train only."""

    numeric_columns = [
        column
        for column in train_frame.columns
        if column not in set(config.drop_columns)
        and column not in set(config.categorical_columns)
    ]
    leakage = check_no_target_leakage(numeric_columns + config.categorical_columns, ["label", "id", "attack_cat"])
    if not leakage["passed"]:
        raise UNSWA11PreprocessingError(f"Leakage columns remain in A11 features: {leakage['leaked_columns']}")

    numeric_train = clean_numeric_frame(train_frame, numeric_columns)
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    scaler.fit(imputer.fit_transform(numeric_train))

    grouping_rules = fit_category_grouping(
        train_frame=train_frame,
        categorical_columns=config.categorical_columns,
        grouping_config=config.feature_protocol["categorical_grouping"],
    )
    grouped_train, _summary = apply_category_grouping(
        train_frame,
        config.categorical_columns,
        grouping_rules,
        split_name="train",
    )

    categories = [
        list(grouping_rules[column].kept_values)
        + ([grouping_rules[column].other_bucket] if grouping_rules[column].other_bucket else [])
        for column in config.categorical_columns
    ]
    encoder = OneHotEncoder(categories=categories, handle_unknown="ignore", sparse_output=False)
    encoder.fit(grouped_train.loc[:, config.categorical_columns])

    feature_names = numeric_columns + list(encoder.get_feature_names_out(config.categorical_columns))
    return A11FeatureTransformer(
        numeric_columns=numeric_columns,
        categorical_columns=list(config.categorical_columns),
        imputer=imputer,
        scaler=scaler,
        encoder=encoder,
        grouping_rules=grouping_rules,
        feature_names=feature_names,
    )


def transform_a11_features(
    transformer: A11FeatureTransformer,
    frame: pd.DataFrame,
    *,
    split_name: str,
) -> tuple[np.ndarray, dict[str, Any]]:
    numeric = clean_numeric_frame(frame, transformer.numeric_columns)
    x_numeric = transformer.scaler.transform(transformer.imputer.transform(numeric))
    grouped, grouping_summary = apply_category_grouping(
        frame,
        transformer.categorical_columns,
        transformer.grouping_rules,
        split_name=split_name,
    )
    x_cat = transformer.encoder.transform(grouped.loc[:, transformer.categorical_columns])
    x = np.hstack([x_numeric, x_cat]).astype(np.float32, copy=False)
    return x, {
        "split": split_name,
        "numeric_columns": len(transformer.numeric_columns),
        "categorical_encoded_columns": int(x_cat.shape[1]),
        "feature_count": int(x.shape[1]),
        "one_hot_values_are_binary": bool(np.isin(x_cat, [0.0, 1.0]).all()),
        "grouping": grouping_summary,
    }


def fit_category_grouping(
    *,
    train_frame: pd.DataFrame,
    categorical_columns: list[str],
    grouping_config: dict[str, Any],
) -> dict[str, CategoryGroupingRule]:
    rules: dict[str, CategoryGroupingRule] = {}
    for column in categorical_columns:
        column_config = grouping_config.get(column, {})
        values = normalize_category_series(train_frame[column])
        counts = values.value_counts(dropna=False).sort_index()
        enabled = bool(column_config.get("enabled", False))
        other_bucket = str(column_config.get("other_bucket_name", "__other__")) if enabled else None
        method = str(column_config.get("method", "none"))
        min_frequency: int | None = None
        top_k: int | None = None
        if enabled and method == "min_frequency_other_bucket":
            min_frequency = int(column_config.get("min_frequency", 10))
            kept = sorted(str(category) for category, count in counts.items() if int(count) >= min_frequency)
        elif enabled and method == "top_k_other_bucket":
            top_k = int(column_config.get("top_k", 20))
            kept = [
                str(category)
                for category in counts.sort_values(ascending=False).head(top_k).index.tolist()
            ]
        elif enabled:
            raise UNSWA11PreprocessingError(f"Unsupported grouping method for {column}: {method}")
        else:
            kept = sorted(str(category) for category in counts.index.tolist())
            method = "disabled_keep_train_categories"
        if other_bucket and other_bucket in kept:
            kept = [value for value in kept if value != other_bucket]
        rules[column] = CategoryGroupingRule(
            column=column,
            enabled=enabled,
            method=method,
            kept_values=tuple(kept),
            other_bucket=other_bucket,
            train_category_counts={str(category): int(count) for category, count in counts.items()},
            min_frequency=min_frequency,
            top_k=top_k,
        )
    return rules


def apply_category_grouping(
    frame: pd.DataFrame,
    categorical_columns: list[str],
    rules: dict[str, CategoryGroupingRule],
    *,
    split_name: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    grouped = pd.DataFrame(index=frame.index)
    summary: dict[str, Any] = {}
    for column in categorical_columns:
        rule = rules[column]
        values = normalize_category_series(frame[column])
        kept = set(rule.kept_values)
        train_categories = set(rule.train_category_counts)
        if rule.enabled and rule.other_bucket:
            unknown_mask = ~values.isin(train_categories)
            grouped_mask = ~values.isin(kept)
            grouped[column] = values.where(~grouped_mask, rule.other_bucket)
            summary[column] = {
                "split": split_name,
                "enabled": True,
                "kept_category_count": len(rule.kept_values),
                "other_bucket": rule.other_bucket,
                "unknown_categories_mapped_to_other": int(unknown_mask.sum()),
                "total_values_mapped_to_other": int(grouped_mask.sum()),
            }
        else:
            grouped[column] = values
            summary[column] = {
                "split": split_name,
                "enabled": False,
                "kept_category_count": len(rule.kept_values),
                "other_bucket": None,
                "unknown_categories_mapped_to_other": 0,
                "total_values_mapped_to_other": 0,
            }
    return grouped, summary


def normalize_category_series(series: pd.Series) -> pd.Series:
    return series.fillna("__missing__").astype(str).str.strip()


def build_hierarchical_labels(
    *,
    splits: dict[str, tuple[pd.DataFrame, np.ndarray]],
    taxonomy_info: dict[str, Any],
    attack_column: str,
) -> dict[str, dict[str, np.ndarray]]:
    labels: dict[str, dict[str, np.ndarray]] = {}
    for split_name, (frame, y_binary) in splits.items():
        y_attack = np.full(y_binary.shape[0], taxonomy_info["ignore_index"], dtype=np.int64)
        mask = np.full(y_binary.shape[0], taxonomy_info["mask_benign"], dtype=np.int64)
        attack_mask = y_binary == 1
        raw_attack = frame.loc[attack_mask, attack_column].astype(str).str.strip()
        mapped = raw_attack.map(taxonomy_info["raw_to_id"])
        if mapped.isna().any():
            missing = sorted(raw_attack[mapped.isna()].unique().tolist())
            raise UNSWA11PreprocessingError(f"Unmapped attack labels in {split_name}: {missing}")
        y_attack[attack_mask] = mapped.to_numpy(dtype=np.int64)
        mask[attack_mask] = taxonomy_info["mask_attack"]
        labels[split_name] = {
            "y_binary": y_binary.astype(np.int64, copy=False),
            "y_attack_family": y_attack,
            "attack_family_mask": mask,
        }
    return labels


def save_feature_arrays(
    output_dir: Path,
    x_train: np.ndarray,
    x_val: np.ndarray,
    x_test: np.ndarray,
    labels: dict[str, dict[str, np.ndarray]],
) -> None:
    np.save(output_dir / "X_train.npy", x_train)
    np.save(output_dir / "X_val.npy", x_val)
    np.save(output_dir / "X_test.npy", x_test)
    for split_name in ("train", "val", "test"):
        np.save(output_dir / f"y_binary_{split_name}.npy", labels[split_name]["y_binary"])
        np.save(output_dir / f"y_attack_family_{split_name}.npy", labels[split_name]["y_attack_family"])
        np.save(output_dir / f"attack_family_mask_{split_name}.npy", labels[split_name]["attack_family_mask"])


def save_binary_arrays(
    output_dir: Path,
    x_train: np.ndarray,
    x_val: np.ndarray,
    x_test: np.ndarray,
    y_train: np.ndarray,
    y_val: np.ndarray,
    y_test: np.ndarray,
) -> None:
    np.save(output_dir / "X_train.npy", x_train)
    np.save(output_dir / "X_val.npy", x_val)
    np.save(output_dir / "X_test.npy", x_test)
    np.save(output_dir / "y_train.npy", y_train.astype(np.int64, copy=False))
    np.save(output_dir / "y_val.npy", y_val.astype(np.int64, copy=False))
    np.save(output_dir / "y_test.npy", y_test.astype(np.int64, copy=False))


def build_a11_split_summary(
    x_train: np.ndarray,
    x_val: np.ndarray,
    x_test: np.ndarray,
    labels: dict[str, dict[str, np.ndarray]],
    taxonomy_info: dict[str, Any],
) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    x_by_split = {"train": x_train, "val": x_val, "test": x_test}
    for split_name, x_array in x_by_split.items():
        y_binary = labels[split_name]["y_binary"]
        y_attack = labels[split_name]["y_attack_family"]
        mask = labels[split_name]["attack_family_mask"]
        attack_only = y_attack[y_attack != taxonomy_info["ignore_index"]]
        attack_counts = unique_count_dict(attack_only)
        summary[split_name] = {
            "X_shape": list(x_array.shape),
            "y_binary_shape": list(y_binary.shape),
            "y_attack_family_shape": list(y_attack.shape),
            "attack_family_mask_shape": list(mask.shape),
            "binary_class_counts": unique_count_dict(y_binary),
            "attack_family_class_counts_excluding_ignore": attack_counts,
            "attack_family_class_counts_excluding_ignore_named": {
                resolve_class_name(taxonomy_info["id_to_class"], class_id): count
                for class_id, count in attack_counts.items()
            },
            "benign_or_normal_rows_count": int((y_binary == 0).sum()),
            "attack_rows_count": int((y_binary == 1).sum()),
            "mask_valid": bool(
                np.all(y_attack[mask == taxonomy_info["mask_benign"]] == taxonomy_info["ignore_index"])
                and np.all(y_attack[mask == taxonomy_info["mask_attack"]] >= 0)
            ),
        }
    summary["binary"] = {
        split_name: {
            "rows": int(labels[split_name]["y_binary"].shape[0]),
            "binary_class_counts": unique_count_dict(labels[split_name]["y_binary"]),
        }
        for split_name in ("train", "val", "test")
    }
    return summary


def resolve_class_name(id_to_class: dict[Any, str], class_id: Any) -> str:
    """Resolve class names from int-key, string-key, or mixed mappings."""

    candidates: list[Any] = [class_id, str(class_id)]
    try:
        candidates.append(int(class_id))
    except (TypeError, ValueError):
        pass
    for candidate in candidates:
        if candidate in id_to_class:
            return str(id_to_class[candidate])
    available = ", ".join(repr(key) for key in sorted(id_to_class, key=lambda item: str(item)))
    raise UNSWA11PreprocessingError(
        f"Unable to resolve attack-family class id {class_id!r}; "
        f"available id_to_class keys: [{available}]"
    )


def unique_count_dict(values: np.ndarray) -> dict[int, int]:
    unique, counts = np.unique(values.astype(np.int64, copy=False), return_counts=True)
    return {int(value): int(count) for value, count in zip(unique, counts)}


def build_a11_manifest(
    config: UNSWA11PreprocessingConfig,
    transformer: A11FeatureTransformer,
    split_summary: dict[str, Any],
    transform_summaries: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "dataset": "unsw_nb15",
        "protocol_name": config.protocol_name,
        "config_path": str(config.path),
        "created_at_utc": utc_timestamp(),
        "status": "A11_PREPROCESSING_EXECUTED",
        "feature_count": len(transformer.feature_names),
        "numeric_feature_count": len(transformer.numeric_columns),
        "categorical_encoded_feature_count": len(transformer.feature_names) - len(transformer.numeric_columns),
        "numeric_only_scaling": True,
        "one_hot_columns_scaled": False,
        "train_only_fitting": True,
        "no_test_fitting": True,
        "no_test_label_feature_selection": True,
        "no_test_tuning": True,
        "split_summary": split_summary,
        "transform_summaries": transform_summaries,
        "config_snapshot": config.raw,
        "no_training_performed": True,
        "no_evaluation_performed": True,
        "no_model_metrics_created": True,
    }


def build_preprocessing_audit(
    config: UNSWA11PreprocessingConfig,
    transformer: A11FeatureTransformer,
    split_summary: dict[str, Any],
    transform_summaries: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "audit_name": "unsw_a11_enhanced_feature_protocol_preprocessing_audit",
        "status": "PASS",
        "protocol_name": config.protocol_name,
        "feature_count": len(transformer.feature_names),
        "numeric_only_scaling": True,
        "one_hot_columns_not_scaled": True,
        "train_only_fitting": True,
        "no_test_fitting": True,
        "no_test_label_feature_selection": True,
        "no_test_tuning": True,
        "a9_artifacts_modified": False,
        "models_final_modified": False,
        "results_final_modified": False,
        "split_summary": split_summary,
        "transform_summaries": transform_summaries,
    }


def write_feature_inventory(config: UNSWA11PreprocessingConfig, transformer: A11FeatureTransformer) -> None:
    path = config.resolve(config.planned_outputs["feature_inventory_csv"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["feature_group", "feature_name", "position"])
        writer.writeheader()
        for index, feature in enumerate(transformer.feature_names):
            group = "numeric" if index < len(transformer.numeric_columns) else "categorical_onehot_unscaled"
            writer.writerow({"feature_group": group, "feature_name": feature, "position": index})


def write_category_inventory(config: UNSWA11PreprocessingConfig, transformer: A11FeatureTransformer) -> None:
    path = config.resolve(config.planned_outputs["category_inventory_csv"])
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["column", "category", "train_count", "kept", "mapped_to_other", "method"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for rule in transformer.grouping_rules.values():
            kept = set(rule.kept_values)
            for category, count in sorted(rule.train_category_counts.items()):
                writer.writerow(
                    {
                        "column": rule.column,
                        "category": category,
                        "train_count": count,
                        "kept": category in kept,
                        "mapped_to_other": rule.enabled and category not in kept,
                        "method": rule.method,
                    }
                )


def write_separability_placeholder(
    config: UNSWA11PreprocessingConfig,
    labels: dict[str, dict[str, np.ndarray]],
    taxonomy_info: dict[str, Any],
) -> None:
    path = config.resolve(config.planned_outputs["separability_diagnostics_csv"])
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["split", "class_id", "class_name", "rows", "diagnostic_scope"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for split_name in ("train", "val", "test"):
            counts = unique_count_dict(
                labels[split_name]["y_attack_family"][
                    labels[split_name]["y_attack_family"] != taxonomy_info["ignore_index"]
                ]
            )
            for class_id, count in counts.items():
                writer.writerow(
                    {
                        "split": split_name,
                        "class_id": class_id,
                        "class_name": resolve_class_name(taxonomy_info["id_to_class"], class_id),
                        "rows": count,
                        "diagnostic_scope": "label_count_only_no_model_evaluation",
                    }
                )


def assert_dry_run_wrote_nothing(paths: dict[str, Path]) -> bool:
    """Helper used by tests and CLI checks."""

    return not any(path.exists() for path in paths.values())
