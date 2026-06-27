"""Dry-run preprocessing validation pipeline."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from numpy.lib.format import open_memmap
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

from secureids.preprocessing.artifacts import (
    build_manifest,
    save_joblib,
    save_json,
    utc_timestamp,
)
from secureids.preprocessing.base import (
    DryRunFileCheck,
    PreprocessingConfig,
    discover_csv_files,
    load_preprocessing_config,
    project_path,
    read_csv_header_and_sample_count,
    validate_preprocessing_config,
)
from secureids.preprocessing.cleaning import (
    clean_numeric_frame,
    replace_nonfinite_with_values,
    strip_column_whitespace,
)
from secureids.preprocessing.encoding import (
    build_onehot_encoder,
    encode_categorical_frame,
    prepare_categorical_frame,
    validate_categorical_columns,
)
from secureids.preprocessing.splitting import (
    SPLIT_NAMES,
    SPLIT_TEST,
    SPLIT_TRAIN,
    SPLIT_VAL,
    describe_split_policy,
    make_class_split_codes,
    split_train_validation,
)
from secureids.preprocessing.validation import (
    check_no_target_leakage,
    drop_column_status,
    label_distribution,
    map_binary_label,
    target_column_status,
    verify_expected_outputs,
)


CONFIG_BY_DATASET = {
    "cicids2018": "configs/preprocessing/cicids2018_binary.yaml",
    "unsw_nb15": "configs/preprocessing/unsw_nb15_binary.yaml",
}

NEXT_STEP_RECOMMENDATION = (
    "Review this dry-run report, then approve the preprocessing implementation "
    "phase before running real preprocessing."
)

EXECUTION_CHUNK_ROWS = 100_000
ARRAY_CHUNK_ROWS = 100_000


def normalize_dataset_selection(selection: str) -> list[str]:
    if selection in {"cicids", "cicids2018"}:
        return ["cicids2018"]
    if selection in {"unsw", "unsw_nb15"}:
        return ["unsw_nb15"]
    if selection == "all":
        return ["cicids2018", "unsw_nb15"]
    raise ValueError(f"Unsupported dataset selection: {selection}")


def run_preprocessing_dry_run(
    dataset: str,
    project_root: Path,
) -> list[dict[str, Any]]:
    """Run dry-run validation for one dataset selection."""

    reports = []
    for dataset_name in normalize_dataset_selection(dataset):
        config_path = project_path(project_root, CONFIG_BY_DATASET[dataset_name])
        config = load_preprocessing_config(config_path)
        reports.append(run_dataset_dry_run(config, project_root))

    write_dry_run_outputs(project_root, reports)
    return reports


def run_preprocessing_execute(
    dataset: str,
    project_root: Path,
) -> list[dict[str, Any]]:
    """Run real preprocessing for one dataset selection."""

    reports = []
    for dataset_name in normalize_dataset_selection(dataset):
        config_path = project_path(project_root, CONFIG_BY_DATASET[dataset_name])
        config = load_preprocessing_config(config_path)
        if dataset_name == "cicids2018":
            reports.append(execute_cicids_preprocessing(config, project_root))
        else:
            reports.append(execute_unsw_preprocessing(config, project_root))

    write_preprocessing_report(project_root, reports)
    return reports


def run_dataset_dry_run(
    config: PreprocessingConfig,
    project_root: Path,
) -> dict[str, Any]:
    errors = validate_preprocessing_config(config)
    if config.dataset == "cicids2018":
        report = run_cicids_dry_run(config, project_root)
    elif config.dataset == "unsw_nb15":
        report = run_unsw_dry_run(config, project_root)
    else:
        report = {
            "dataset": config.dataset,
            "config_path": str(config.path),
            "status": "config_error",
        }

    report["config_validation_errors"] = errors
    if errors and report.get("status") == "ok":
        report["status"] = "config_error"
    return report


def run_cicids_dry_run(
    config: PreprocessingConfig,
    project_root: Path,
) -> dict[str, Any]:
    values = config.values
    raw_dir = project_path(project_root, values["raw_dir"])
    csv_files = discover_csv_files(raw_dir)
    file_checks = [read_csv_header_and_sample_count(path) for path in csv_files]
    reference = first_ok_file_check(file_checks)
    columns = strip_column_whitespace(reference.columns) if reference else []

    target_status = target_column_status(columns, str(values["target_column"]))
    drop_status = drop_column_status(columns, list(values.get("drop_columns", [])))
    output_dir = project_path(project_root, values["output_dir"])
    artifact_path = project_path(project_root, values["artifact_path"])
    leakage_check = check_no_target_leakage(
        feature_names=[
            column
            for column in columns
            if column not in set(values.get("drop_columns", []))
        ],
        forbidden_columns=[str(values["target_column"])],
    )

    status = "ok"
    if not raw_dir.exists():
        status = "missing_raw_dir"
    elif not csv_files:
        status = "no_csv_files"
    elif not target_status["present"]:
        status = "target_missing"

    input_paths = [str(raw_dir)]
    return {
        "dataset": values["dataset"],
        "config_path": str(config.path),
        "status": status,
        "raw_input_paths_checked": input_paths,
        "raw_dir_exists": raw_dir.exists(),
        "files_found": [str(path) for path in csv_files],
        "file_count": len(csv_files),
        "detected_columns": columns,
        "detected_column_count": len(columns),
        "file_checks": [compact_file_check(check) for check in file_checks],
        "target_column_status": target_status,
        "configured_drop_column_status": drop_status,
        "categorical_column_status": {},
        "split_policy": describe_split_policy(dict(values.get("split", {}))),
        "processed_outputs_created": False,
        "processed_output_dir": str(output_dir),
        "processed_output_dir_exists": output_dir.exists(),
        "artifact_path": str(artifact_path),
        "artifact_created": artifact_path.exists(),
        "target_leakage_check_on_configured_features": leakage_check,
        "manifest_preview": build_manifest(
            dataset=str(values["dataset"]),
            config_path=str(config.path),
            input_paths=input_paths,
            output_paths=[str(output_dir), str(artifact_path)],
            random_seed=get_random_seed(values),
        ),
        "next_step_recommendation": NEXT_STEP_RECOMMENDATION,
    }


def run_unsw_dry_run(
    config: PreprocessingConfig,
    project_root: Path,
) -> dict[str, Any]:
    values = config.values
    train_file = project_path(project_root, values["train_file"])
    test_file = project_path(project_root, values["test_file"])
    file_checks = [
        read_csv_header_and_sample_count(train_file),
        read_csv_header_and_sample_count(test_file),
    ]
    reference = first_ok_file_check(file_checks)
    columns = strip_column_whitespace(reference.columns) if reference else []

    target_status = target_column_status(columns, str(values["target_column"]))
    drop_status = drop_column_status(columns, list(values.get("drop_columns", [])))
    categorical_status = validate_categorical_columns(
        columns,
        list(values.get("categorical_columns", [])),
    )
    output_dir = project_path(project_root, values["output_dir"])
    artifact_path = project_path(project_root, values["artifact_path"])
    leakage_check = check_no_target_leakage(
        feature_names=[
            column
            for column in columns
            if column not in set(values.get("drop_columns", []))
        ],
        forbidden_columns=[str(values["target_column"]), "attack_cat"],
    )

    status = "ok"
    if not train_file.exists() or not test_file.exists():
        status = "missing_raw_file"
    elif not target_status["present"]:
        status = "target_missing"
    elif any(value == "missing" for value in categorical_status.values()):
        status = "categorical_missing"

    input_paths = [str(train_file), str(test_file)]
    return {
        "dataset": values["dataset"],
        "config_path": str(config.path),
        "status": status,
        "raw_input_paths_checked": input_paths,
        "files_found": [
            str(path)
            for path in (train_file, test_file)
            if path.exists()
        ],
        "file_count": sum(1 for path in (train_file, test_file) if path.exists()),
        "detected_columns": columns,
        "detected_column_count": len(columns),
        "file_checks": [compact_file_check(check) for check in file_checks],
        "target_column_status": target_status,
        "configured_drop_column_status": drop_status,
        "categorical_column_status": categorical_status,
        "split_policy": describe_split_policy(dict(values.get("split", {}))),
        "processed_outputs_created": False,
        "processed_output_dir": str(output_dir),
        "processed_output_dir_exists": output_dir.exists(),
        "artifact_path": str(artifact_path),
        "artifact_created": artifact_path.exists(),
        "target_leakage_check_on_configured_features": leakage_check,
        "manifest_preview": build_manifest(
            dataset=str(values["dataset"]),
            config_path=str(config.path),
            input_paths=input_paths,
            output_paths=[str(output_dir), str(artifact_path)],
            random_seed=get_random_seed(values),
        ),
        "next_step_recommendation": NEXT_STEP_RECOMMENDATION,
    }


def execute_cicids_preprocessing(
    config: PreprocessingConfig,
    project_root: Path,
) -> dict[str, Any]:
    """Preprocess CICIDS2018 with chunked raw CSV passes."""

    config_errors = validate_preprocessing_config(config)
    if config_errors:
        raise ValueError(f"Invalid CICIDS2018 preprocessing config: {config_errors}")

    values = config.values
    raw_dir = project_path(project_root, values["raw_dir"])
    output_dir = project_path(project_root, values["output_dir"])
    artifact_path = project_path(project_root, values["artifact_path"])
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)

    csv_files = discover_csv_files(raw_dir)
    if not csv_files:
        raise FileNotFoundError(f"No CICIDS2018 CSV files found under {raw_dir}")

    headers = [strip_column_whitespace(read_csv_header_and_sample_count(path, 0).columns) for path in csv_files]
    reference_columns = headers[0]
    incompatible = [
        str(path)
        for path, columns in zip(csv_files, headers)
        if columns != reference_columns
    ]
    if incompatible:
        raise ValueError(f"CICIDS2018 schemas are not compatible: {incompatible}")

    target_column = str(values["target_column"])
    drop_columns = list(values.get("drop_columns", []))
    if target_column not in reference_columns:
        raise ValueError(f"Target column not found in CICIDS2018 schema: {target_column}")
    feature_names = [
        column
        for column in reference_columns
        if column not in set(drop_columns)
    ]
    leakage = check_no_target_leakage(feature_names, [target_column])
    if not leakage["passed"]:
        raise ValueError(f"CICIDS2018 leakage columns remain: {leakage['leaked_columns']}")

    label_counts = count_cicids_labels(csv_files, target_column, values["binary_mapping"])
    split_config = dict(values["split"])
    split_codes = make_class_split_codes(
        label_counts=label_counts,
        train_size=float(split_config["train_size"]),
        val_size=float(split_config["val_size"]),
        random_seed=int(split_config["random_seed"]),
    )
    split_counts = count_split_codes(split_codes)

    x_arrays, y_arrays = create_output_memmaps(output_dir, split_counts, len(feature_names))
    write_cicids_raw_split_arrays(
        csv_files=csv_files,
        feature_names=feature_names,
        target_column=target_column,
        mapping_config=dict(values["binary_mapping"]),
        split_codes=split_codes,
        x_arrays=x_arrays,
        y_arrays=y_arrays,
    )

    medians = compute_nan_medians(x_arrays["train"])
    impute_memmaps_in_place(x_arrays, medians)
    means, scales = compute_mean_scale(x_arrays["train"])
    scale_memmaps_in_place(x_arrays, means, scales)
    flush_arrays(x_arrays, y_arrays)

    imputer, scaler = build_numeric_transformers(feature_names, medians, means, scales, split_counts["train"])
    label_mapping = {
        "benign_values": list(values["binary_mapping"].get("benign_values", [])),
        "attack_rule": values["binary_mapping"].get("attack_rule", "all_non_benign_are_attack"),
        "output_labels": {"0": "Benign / Normal", "1": "Attack"},
    }
    split_summary = build_split_summary(y_arrays)
    manifest = build_execution_manifest(
        dataset=str(values["dataset"]),
        config=config,
        input_paths=[str(path) for path in csv_files],
        output_dir=output_dir,
        artifact_path=artifact_path,
        feature_names=feature_names,
        split_summary=split_summary,
        memory_strategy=(
            "Chunked CSV reading with .npy memmap outputs; train-fitted median "
            "imputation and standard scaling applied in place."
        ),
    )

    save_common_dataset_outputs(output_dir, feature_names, label_mapping, split_summary, manifest)
    save_json(project_root / "results" / "audits" / "preprocessing_manifest_cicids2018.json", manifest)
    save_joblib(
        artifact_path,
        {
            "dataset": values["dataset"],
            "target_column": target_column,
            "feature_names": feature_names,
            "drop_columns": drop_columns,
            "label_mapping": label_mapping,
            "imputer": imputer,
            "scaler": scaler,
            "numeric_columns": feature_names,
            "split_policy": split_config,
            "config_path": str(config.path),
            "config_snapshot": values,
            "created_timestamp": utc_timestamp(),
        },
    )

    verification = verify_expected_outputs(output_dir, feature_names, [target_column])
    audit = build_audit_record(
        dataset=str(values["dataset"]),
        output_dir=output_dir,
        artifact_path=artifact_path,
        feature_count=len(feature_names),
        split_summary=split_summary,
        verification=verification,
        memory_strategy=manifest["memory_strategy"],
    )
    write_audit_csv(project_root / "results" / "audits" / "preprocessing_audit_cicids2018.csv", audit)
    return {
        "dataset": values["dataset"],
        "output_dir": str(output_dir),
        "artifact_path": str(artifact_path),
        "feature_names": feature_names,
        "feature_count": len(feature_names),
        "split_summary": split_summary,
        "manifest": manifest,
        "verification": verification,
        "audit": audit,
    }


def execute_unsw_preprocessing(
    config: PreprocessingConfig,
    project_root: Path,
) -> dict[str, Any]:
    """Preprocess UNSW-NB15 using official train/test files."""

    config_errors = validate_preprocessing_config(config)
    if config_errors:
        raise ValueError(f"Invalid UNSW-NB15 preprocessing config: {config_errors}")

    values = config.values
    train_file = project_path(project_root, values["train_file"])
    test_file = project_path(project_root, values["test_file"])
    output_dir = project_path(project_root, values["output_dir"])
    artifact_path = project_path(project_root, values["artifact_path"])
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)

    target_column = str(values["target_column"])
    drop_columns = list(values["drop_columns"])
    categorical_columns = list(values["categorical_columns"])

    raw_train = pd.read_csv(train_file)
    raw_test = pd.read_csv(test_file)
    raw_train.columns = strip_column_whitespace(list(raw_train.columns))
    raw_test.columns = strip_column_whitespace(list(raw_test.columns))

    required_columns = {target_column, *drop_columns, *categorical_columns}
    missing_columns = sorted(required_columns - set(raw_train.columns))
    if missing_columns:
        raise ValueError(f"UNSW-NB15 training file is missing columns: {missing_columns}")
    test_missing_columns = sorted(required_columns - set(raw_test.columns))
    if test_missing_columns:
        raise ValueError(f"UNSW-NB15 testing file is missing columns: {test_missing_columns}")

    y_official_train = raw_train[target_column].map(
        lambda value: map_binary_label(value, dict(values["binary_mapping"]))
    ).to_numpy(dtype=np.int64)
    y_test = raw_test[target_column].map(
        lambda value: map_binary_label(value, dict(values["binary_mapping"]))
    ).to_numpy(dtype=np.int64)

    train_features, val_features, y_train, y_val = split_train_validation(
        raw_train,
        y_official_train,
        val_size=float(values["split"]["val_size_from_train"]),
        random_seed=int(values["split"]["random_seed"]),
    )
    test_features = raw_test

    numeric_columns = [
        column
        for column in train_features.columns
        if column not in set(drop_columns) and column not in set(categorical_columns)
    ]
    if check_no_target_leakage(numeric_columns + categorical_columns, [target_column, "id", "attack_cat"])["passed"] is False:
        raise ValueError("UNSW-NB15 leakage columns remain in configured features")

    numeric_train = clean_numeric_frame(train_features, numeric_columns)
    numeric_val = clean_numeric_frame(val_features, numeric_columns)
    numeric_test = clean_numeric_frame(test_features, numeric_columns)

    imputer = SimpleImputer(strategy=str(values["imputation"]["numeric_strategy"]))
    scaler = StandardScaler()
    x_train_numeric = scaler.fit_transform(imputer.fit_transform(numeric_train))
    x_val_numeric = scaler.transform(imputer.transform(numeric_val))
    x_test_numeric = scaler.transform(imputer.transform(numeric_test))

    encoder = build_onehot_encoder(str(values["encoding"]["handle_unknown"]))
    encoder.fit(prepare_categorical_frame(train_features, categorical_columns))
    x_train_cat = encode_categorical_frame(encoder, train_features, categorical_columns)
    x_val_cat = encode_categorical_frame(encoder, val_features, categorical_columns)
    x_test_cat = encode_categorical_frame(encoder, test_features, categorical_columns)

    x_train = np.hstack([x_train_numeric, x_train_cat]).astype(np.float32, copy=False)
    x_val = np.hstack([x_val_numeric, x_val_cat]).astype(np.float32, copy=False)
    x_test = np.hstack([x_test_numeric, x_test_cat]).astype(np.float32, copy=False)

    feature_names = numeric_columns + list(encoder.get_feature_names_out(categorical_columns))
    save_numpy_arrays(output_dir, x_train, y_train, x_val, y_val, x_test, y_test)

    label_mapping = {
        "normal_value": values["binary_mapping"]["normal_value"],
        "attack_value": values["binary_mapping"]["attack_value"],
        "output_labels": {"0": "Benign / Normal", "1": "Attack"},
    }
    y_arrays = {
        "train": np.load(output_dir / "y_train.npy", mmap_mode="r"),
        "val": np.load(output_dir / "y_val.npy", mmap_mode="r"),
        "test": np.load(output_dir / "y_test.npy", mmap_mode="r"),
    }
    split_summary = build_split_summary(y_arrays)
    manifest = build_execution_manifest(
        dataset=str(values["dataset"]),
        config=config,
        input_paths=[str(train_file), str(test_file)],
        output_dir=output_dir,
        artifact_path=artifact_path,
        feature_names=feature_names,
        split_summary=split_summary,
        memory_strategy=(
            "Official UNSW training/testing files processed in memory; validation "
            "split created only from official training data."
        ),
    )

    save_common_dataset_outputs(output_dir, feature_names, label_mapping, split_summary, manifest)
    save_json(project_root / "results" / "audits" / "preprocessing_manifest_unsw_nb15.json", manifest)
    save_joblib(
        artifact_path,
        {
            "dataset": values["dataset"],
            "target_column": target_column,
            "feature_names": feature_names,
            "drop_columns": drop_columns,
            "categorical_columns": categorical_columns,
            "numeric_columns": numeric_columns,
            "label_mapping": label_mapping,
            "encoder": encoder,
            "imputer": imputer,
            "scaler": scaler,
            "split_policy": dict(values["split"]),
            "config_path": str(config.path),
            "config_snapshot": values,
            "created_timestamp": utc_timestamp(),
        },
    )

    verification = verify_expected_outputs(output_dir, feature_names, [target_column, "id", "attack_cat"])
    audit = build_audit_record(
        dataset=str(values["dataset"]),
        output_dir=output_dir,
        artifact_path=artifact_path,
        feature_count=len(feature_names),
        split_summary=split_summary,
        verification=verification,
        memory_strategy=manifest["memory_strategy"],
    )
    write_audit_csv(project_root / "results" / "audits" / "preprocessing_audit_unsw_nb15.csv", audit)
    return {
        "dataset": values["dataset"],
        "output_dir": str(output_dir),
        "artifact_path": str(artifact_path),
        "feature_names": feature_names,
        "feature_count": len(feature_names),
        "split_summary": split_summary,
        "manifest": manifest,
        "verification": verification,
        "audit": audit,
    }


def first_ok_file_check(file_checks: list[DryRunFileCheck]) -> DryRunFileCheck | None:
    for check in file_checks:
        if check.status == "ok":
            return check
    return None


def compact_file_check(check: DryRunFileCheck) -> dict[str, Any]:
    """Keep per-file dry-run output readable while columns are reported once."""

    return {
        "path": check.path,
        "exists": check.exists,
        "status": check.status,
        "column_count": check.column_count,
        "sample_rows_inspected": check.sample_rows_inspected,
        "error": check.error,
    }


def get_random_seed(values: dict[str, Any]) -> int | None:
    split = values.get("split", {})
    if isinstance(split, dict):
        seed = split.get("random_seed")
        return int(seed) if seed is not None else None
    return None


def count_cicids_labels(
    csv_files: list[Path],
    target_column: str,
    mapping_config: dict[str, Any],
) -> dict[int, int]:
    counts = {0: 0, 1: 0}
    for csv_file in csv_files:
        for chunk in pd.read_csv(csv_file, usecols=[target_column], chunksize=EXECUTION_CHUNK_ROWS):
            labels = map_label_series(chunk[target_column], mapping_config)
            unique, label_counts = np.unique(labels, return_counts=True)
            for label, count in zip(unique, label_counts):
                counts[int(label)] += int(count)
    return counts


def map_label_series(series: pd.Series, mapping_config: dict[str, Any]) -> np.ndarray:
    if "benign_values" in mapping_config:
        benign = {str(value).strip() for value in mapping_config.get("benign_values", [])}
        return np.where(series.astype(str).str.strip().isin(benign), 0, 1).astype(np.int64)
    return series.map(lambda value: map_binary_label(value, mapping_config)).to_numpy(dtype=np.int64)


def count_split_codes(split_codes: dict[int, np.ndarray]) -> dict[str, int]:
    counts = {"train": 0, "val": 0, "test": 0}
    for codes in split_codes.values():
        for code, name in SPLIT_NAMES.items():
            counts[name] += int((codes == code).sum())
    return counts


def create_output_memmaps(
    output_dir: Path,
    split_counts: dict[str, int],
    feature_count: int,
) -> tuple[dict[str, np.memmap], dict[str, np.memmap]]:
    x_arrays = {
        split: open_memmap(
            output_dir / f"X_{split}.npy",
            mode="w+",
            dtype=np.float32,
            shape=(count, feature_count),
        )
        for split, count in split_counts.items()
    }
    y_arrays = {
        split: open_memmap(
            output_dir / f"y_{split}.npy",
            mode="w+",
            dtype=np.int64,
            shape=(count,),
        )
        for split, count in split_counts.items()
    }
    return x_arrays, y_arrays


def write_cicids_raw_split_arrays(
    csv_files: list[Path],
    feature_names: list[str],
    target_column: str,
    mapping_config: dict[str, Any],
    split_codes: dict[int, np.ndarray],
    x_arrays: dict[str, np.memmap],
    y_arrays: dict[str, np.memmap],
) -> None:
    class_offsets = {0: 0, 1: 0}
    split_offsets = {"train": 0, "val": 0, "test": 0}
    split_code_to_name = {
        SPLIT_TRAIN: "train",
        SPLIT_VAL: "val",
        SPLIT_TEST: "test",
    }

    for csv_file in csv_files:
        for chunk in pd.read_csv(csv_file, chunksize=EXECUTION_CHUNK_ROWS):
            chunk.columns = strip_column_whitespace(list(chunk.columns))
            labels = map_label_series(chunk[target_column], mapping_config)
            row_split_codes = np.empty(len(labels), dtype=np.uint8)
            for label in (0, 1):
                mask = labels == label
                count = int(mask.sum())
                if count:
                    start = class_offsets[label]
                    end = start + count
                    row_split_codes[mask] = split_codes[label][start:end]
                    class_offsets[label] = end

            numeric = clean_numeric_frame(chunk, feature_names).to_numpy(dtype=np.float32, copy=True)
            for split_code, split_name in split_code_to_name.items():
                mask = row_split_codes == split_code
                count = int(mask.sum())
                if not count:
                    continue
                start = split_offsets[split_name]
                end = start + count
                x_arrays[split_name][start:end, :] = numeric[mask]
                y_arrays[split_name][start:end] = labels[mask]
                split_offsets[split_name] = end


def compute_nan_medians(train_array: np.ndarray) -> np.ndarray:
    medians = np.empty(train_array.shape[1], dtype=np.float64)
    for column_index in range(train_array.shape[1]):
        column = np.asarray(train_array[:, column_index], dtype=np.float64)
        finite = np.isfinite(column)
        if not finite.any():
            medians[column_index] = 0.0
        else:
            medians[column_index] = float(np.median(column[finite]))
    return medians


def impute_memmaps_in_place(
    x_arrays: dict[str, np.memmap],
    medians: np.ndarray,
) -> None:
    medians32 = medians.astype(np.float32)
    for array in x_arrays.values():
        for start in range(0, array.shape[0], ARRAY_CHUNK_ROWS):
            end = min(start + ARRAY_CHUNK_ROWS, array.shape[0])
            block = array[start:end]
            replace_nonfinite_with_values(block, medians32)


def compute_mean_scale(train_array: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    sums = np.zeros(train_array.shape[1], dtype=np.float64)
    squared_sums = np.zeros(train_array.shape[1], dtype=np.float64)
    count = 0
    for start in range(0, train_array.shape[0], ARRAY_CHUNK_ROWS):
        end = min(start + ARRAY_CHUNK_ROWS, train_array.shape[0])
        block = np.asarray(train_array[start:end], dtype=np.float64)
        sums += block.sum(axis=0)
        squared_sums += np.square(block).sum(axis=0)
        count += block.shape[0]
    means = sums / max(count, 1)
    variances = np.maximum((squared_sums / max(count, 1)) - np.square(means), 0.0)
    scales = np.sqrt(variances)
    scales[scales == 0] = 1.0
    return means, scales


def scale_memmaps_in_place(
    x_arrays: dict[str, np.memmap],
    means: np.ndarray,
    scales: np.ndarray,
) -> None:
    means32 = means.astype(np.float32)
    scales32 = scales.astype(np.float32)
    for array in x_arrays.values():
        for start in range(0, array.shape[0], ARRAY_CHUNK_ROWS):
            end = min(start + ARRAY_CHUNK_ROWS, array.shape[0])
            array[start:end] = (array[start:end] - means32) / scales32


def flush_arrays(
    x_arrays: dict[str, np.memmap],
    y_arrays: dict[str, np.memmap],
) -> None:
    for array in [*x_arrays.values(), *y_arrays.values()]:
        array.flush()


def build_numeric_transformers(
    feature_names: list[str],
    medians: np.ndarray,
    means: np.ndarray,
    scales: np.ndarray,
    train_count: int,
) -> tuple[SimpleImputer, StandardScaler]:
    dummy = np.vstack([medians, medians])
    imputer = SimpleImputer(strategy="median")
    imputer.fit(dummy)
    imputer.statistics_ = medians.astype(np.float64)

    scaler = StandardScaler()
    scaler.fit(dummy)
    scaler.mean_ = means.astype(np.float64)
    scaler.scale_ = scales.astype(np.float64)
    scaler.var_ = np.square(scales.astype(np.float64))
    scaler.n_samples_seen_ = int(train_count)

    imputer.feature_names_in_ = np.asarray(feature_names, dtype=object)
    scaler.feature_names_in_ = np.asarray(feature_names, dtype=object)
    return imputer, scaler


def save_numpy_arrays(
    output_dir: Path,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    x_test: np.ndarray,
    y_test: np.ndarray,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    np.save(output_dir / "X_train.npy", x_train.astype(np.float32, copy=False))
    np.save(output_dir / "y_train.npy", y_train.astype(np.int64, copy=False))
    np.save(output_dir / "X_val.npy", x_val.astype(np.float32, copy=False))
    np.save(output_dir / "y_val.npy", y_val.astype(np.int64, copy=False))
    np.save(output_dir / "X_test.npy", x_test.astype(np.float32, copy=False))
    np.save(output_dir / "y_test.npy", y_test.astype(np.int64, copy=False))


def build_split_summary(y_arrays: dict[str, np.ndarray]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for split_name, labels in y_arrays.items():
        summary[split_name] = {
            "rows": int(labels.shape[0]),
            "label_distribution": label_distribution(np.asarray(labels)),
        }
    summary["total_rows"] = int(sum(split["rows"] for split in summary.values()))
    return summary


def build_execution_manifest(
    dataset: str,
    config: PreprocessingConfig,
    input_paths: list[str],
    output_dir: Path,
    artifact_path: Path,
    feature_names: list[str],
    split_summary: dict[str, Any],
    memory_strategy: str,
) -> dict[str, Any]:
    manifest = build_manifest(
        dataset=dataset,
        config_path=str(config.path),
        input_paths=input_paths,
        output_paths=[
            str(output_dir / "X_train.npy"),
            str(output_dir / "y_train.npy"),
            str(output_dir / "X_val.npy"),
            str(output_dir / "y_val.npy"),
            str(output_dir / "X_test.npy"),
            str(output_dir / "y_test.npy"),
            str(output_dir / "feature_names.json"),
            str(output_dir / "label_mapping.json"),
            str(output_dir / "split_summary.json"),
            str(output_dir / "preprocessing_manifest.json"),
            str(artifact_path),
        ],
        random_seed=get_random_seed(config.values),
    )
    manifest.update({
        "task": config.values.get("task"),
        "feature_count": len(feature_names),
        "split_summary": split_summary,
        "memory_strategy": memory_strategy,
        "config_snapshot": config.values,
        "no_training_performed": True,
        "no_model_metrics_created": True,
    })
    return manifest


def save_common_dataset_outputs(
    output_dir: Path,
    feature_names: list[str],
    label_mapping: dict[str, Any],
    split_summary: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    save_json(output_dir / "feature_names.json", {"feature_names": feature_names})
    save_json(output_dir / "label_mapping.json", label_mapping)
    save_json(output_dir / "split_summary.json", split_summary)
    save_json(output_dir / "preprocessing_manifest.json", manifest)


def build_audit_record(
    dataset: str,
    output_dir: Path,
    artifact_path: Path,
    feature_count: int,
    split_summary: dict[str, Any],
    verification: dict[str, Any],
    memory_strategy: str,
) -> dict[str, Any]:
    return {
        "dataset": dataset,
        "output_dir": str(output_dir),
        "artifact_path": str(artifact_path),
        "feature_count": feature_count,
        "train_rows": split_summary["train"]["rows"],
        "val_rows": split_summary["val"]["rows"],
        "test_rows": split_summary["test"]["rows"],
        "train_label_distribution": split_summary["train"]["label_distribution"],
        "val_label_distribution": split_summary["val"]["label_distribution"],
        "test_label_distribution": split_summary["test"]["label_distribution"],
        "x_train_shape": verification["x_shapes"]["X_train"],
        "x_val_shape": verification["x_shapes"]["X_val"],
        "x_test_shape": verification["x_shapes"]["X_test"],
        "labels_binary_only": verification["labels_binary_only"],
        "x_arrays_finite": verification["x_arrays_finite"],
        "target_leakage_passed": verification["target_leakage"]["passed"],
        "artifact_exists": artifact_path.exists(),
        "memory_strategy": memory_strategy,
        "model_metrics_created": False,
    }


def write_audit_csv(path: Path, audit: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit.keys()))
        writer.writeheader()
        writer.writerow(audit)


def write_preprocessing_report(project_root: Path, reports: list[dict[str, Any]]) -> None:
    report_path = project_root / "docs" / "PREPROCESSING_REPORT.md"
    lines = [
        "# PREPROCESSING_REPORT.md",
        "",
        "## 1. Purpose",
        "",
        "This report documents the completed preprocessing execution for the binary",
        "IDS datasets. It records dataset-specific decisions, output artifacts,",
        "split sizes, label distributions, leakage checks, and safety boundaries.",
        "",
        "## 2. Preprocessing Policy",
        "",
        "- CICIDS2018 and UNSW-NB15 use dataset-specific preprocessing pipelines.",
        "- Scalers, imputers, and encoders are fitted only on training data.",
        "- Validation and test splits are transformed only with train-fitted artifacts.",
        "- No model training or model evaluation is performed by preprocessing.",
        "- No model performance metrics are produced here.",
        "",
    ]
    section_number = 3
    for report in reports:
        split = report["split_summary"]
        verification = report["verification"]
        manifest = report["manifest"]
        lines.extend([
            f"## {section_number}. {report['dataset']} Outputs",
            "",
            "Input files:",
            "",
        ])
        lines.extend(f"- `{path}`" for path in manifest["input_paths"])
        lines.extend([
            "",
            f"- Output directory: `{report['output_dir']}`",
            f"- Preprocessor artifact: `{report['artifact_path']}`",
            f"- Feature count: {report['feature_count']}",
            f"- Memory strategy: {manifest['memory_strategy']}",
            "",
            "Split sizes and label distributions:",
            "",
            "| Split | Rows | Label 0 | Label 1 |",
            "| --- | ---: | ---: | ---: |",
        ])
        for split_name in ("train", "val", "test"):
            labels = split[split_name]["label_distribution"]
            lines.append(
                f"| {split_name} | {split[split_name]['rows']} | "
                f"{labels.get('0', 0)} | {labels.get('1', 0)} |"
            )
        lines.extend([
            "",
            "Verification:",
            "",
            f"- X arrays are 2D: `{str(verification['x_arrays_are_2d']).lower()}`",
            f"- y arrays are 1D: `{str(verification['y_arrays_are_1d']).lower()}`",
            f"- Feature counts are consistent: `{str(verification['consistent_feature_count']).lower()}`",
            f"- Feature names match array dimension: `{str(verification['feature_names_match_dimension']).lower()}`",
            f"- Labels contain only 0 and 1: `{str(verification['labels_binary_only']).lower()}`",
            f"- Target/leakage columns removed: `{str(verification['target_leakage']['passed']).lower()}`",
            "",
            "Output files:",
            "",
        ])
        lines.extend(f"- `{path}`" for path in manifest["output_paths"])
        lines.append("")
        section_number += 1

    lines.extend([
        f"## {section_number}. Downstream Compatibility",
        "",
        "- Training can load NumPy arrays, feature names, label mapping, split",
        "  summaries, manifests, and dataset-specific preprocessor artifacts.",
        "- Federated learning can consume dataset-specific train/validation/test",
        "  arrays and class-distribution metadata.",
        "- XAI can use stable `feature_names.json` ordering for each dataset.",
        "- The dashboard can read manifests, split summaries, label mappings, and",
        "  later model/XAI artifacts without converting preprocessing outputs.",
        "",
        f"## {section_number + 1}. Safety Confirmation",
        "",
        "- No training was run.",
        "- No model checkpoints were created.",
        "- No model performance metrics were created.",
        "- V1 was not modified.",
        "- No Git commit was created.",
        "- No GitHub push occurred.",
        "",
    ])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def write_dry_run_outputs(project_root: Path, reports: list[dict[str, Any]]) -> None:
    audits_dir = project_root / "results" / "audits"
    docs_dir = project_root / "docs"
    for report in reports:
        dataset = report["dataset"]
        output_path = audits_dir / f"preprocessing_dry_run_{dataset}.json"
        save_json(output_path, report)

    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "PREPROCESSING_DRY_RUN_REPORT.md").write_text(
        build_dry_run_markdown(reports),
        encoding="utf-8",
    )


def build_dry_run_markdown(reports: list[dict[str, Any]]) -> str:
    lines = [
        "# PREPROCESSING_DRY_RUN_REPORT.md",
        "",
        "## Purpose",
        "",
        "This report records preprocessing dry-run validation only. It",
        "inspects configs, raw input paths, CSV headers, and tiny samples. It does",
        "not create processed arrays, model artifacts, checkpoints, training",
        "outputs, or performance metrics.",
        "",
    ]

    for report in reports:
        lines.extend([
            f"## {report['dataset']}",
            "",
            f"- Status: `{report['status']}`",
            f"- Config path: `{report['config_path']}`",
            f"- Files found: {report['file_count']}",
            f"- Detected column count: {report['detected_column_count']}",
            "- Target column status: "
            f"`{report['target_column_status']['status']}`",
            "- Processed outputs created: "
            f"`{str(report['processed_outputs_created']).lower()}`",
            "- Artifact created: "
            f"`{str(report['artifact_created']).lower()}`",
            "",
            "Raw input paths checked:",
            "",
        ])
        lines.extend(f"- `{path}`" for path in report["raw_input_paths_checked"])
        lines.extend([
            "",
            "Configured drop-column status:",
            "",
        ])
        for column, status in report["configured_drop_column_status"].items():
            lines.append(f"- `{column}`: {status}")
        if report["categorical_column_status"]:
            lines.extend([
                "",
                "Categorical column status:",
                "",
            ])
            for column, status in report["categorical_column_status"].items():
                lines.append(f"- `{column}`: {status}")
        lines.extend([
            "",
            "Detected columns:",
            "",
            ", ".join(f"`{column}`" for column in report["detected_columns"]),
            "",
            "Next step recommendation:",
            "",
            report["next_step_recommendation"],
            "",
        ])

    return "\n".join(lines)
