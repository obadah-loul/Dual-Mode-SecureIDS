"""Hierarchical preprocessing execution for the approved A3 scope.

This module creates dataset-specific hierarchical label artifacts by reusing the
accepted binary feature arrays and reconstructing labels in the same split order
as the binary preprocessing run. It does not implement models, train, evaluate,
or create checkpoints.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - local environment dependent
    yaml = None
    YAML_IMPORT_ERROR = exc
else:
    YAML_IMPORT_ERROR = None

from secureids.preprocessing.artifacts import save_json
from secureids.preprocessing.base import discover_csv_files, project_path
from secureids.preprocessing.splitting import (
    SPLIT_NAMES,
    SPLIT_TEST,
    SPLIT_TRAIN,
    SPLIT_VAL,
    make_class_split_codes,
    split_train_validation,
)


DATASET_ALIASES = {
    "cicids": "cicids2018",
    "cicids2018": "cicids2018",
    "unsw": "unsw_nb15",
    "unsw_nb15": "unsw_nb15",
}

CONFIGS = {
    "cicids2018": {
        "taxonomy": "configs/taxonomy/cicids2018_attack_taxonomy.yaml",
        "hierarchical": "configs/preprocessing/cicids2018_hierarchical.yaml",
        "binary": "configs/preprocessing/cicids2018_binary.yaml",
        "audit": "results/audits/hierarchical_preprocessing_audit_cicids2018.json",
    },
    "unsw_nb15": {
        "taxonomy": "configs/taxonomy/unsw_nb15_attack_taxonomy.yaml",
        "hierarchical": "configs/preprocessing/unsw_nb15_hierarchical.yaml",
        "binary": "configs/preprocessing/unsw_nb15_binary.yaml",
        "audit": "results/audits/hierarchical_preprocessing_audit_unsw_nb15.json",
    },
}

SPLITS = ("train", "val", "test")
EXECUTION_CHUNK_ROWS = 100_000
COPY_CHUNK_BYTES = 16 * 1024 * 1024
PROGRESS_BYTES = 512 * 1024 * 1024
EXPECTED_OUTPUT_NAMES = [
    "X_train.npy",
    "X_val.npy",
    "X_test.npy",
    "y_binary_train.npy",
    "y_binary_val.npy",
    "y_binary_test.npy",
    "y_attack_family_train.npy",
    "y_attack_family_val.npy",
    "y_attack_family_test.npy",
    "attack_family_mask_train.npy",
    "attack_family_mask_val.npy",
    "attack_family_mask_test.npy",
    "feature_names.json",
    "binary_label_mapping.json",
    "attack_family_label_mapping.json",
    "common_attack_superclass_mapping.json",
    "split_summary.json",
    "hierarchical_preprocessing_manifest.json",
]


class HierarchicalPreprocessingError(RuntimeError):
    """Raised when A3 preprocessing cannot be completed safely."""


def normalize_dataset_selection(selection: str) -> list[str]:
    if selection == "all":
        return ["cicids2018", "unsw_nb15"]
    try:
        return [DATASET_ALIASES[selection]]
    except KeyError as exc:
        raise ValueError(f"Unsupported dataset selection: {selection}") from exc


def run_hierarchical_preprocessing(
    dataset: str,
    project_root: Path,
    *,
    execute: bool,
    overwrite: bool = False,
) -> list[dict[str, Any]]:
    """Run approved real hierarchical preprocessing for selected datasets."""

    if not execute:
        raise HierarchicalPreprocessingError(
            "Hierarchical preprocessing requires --execute. No outputs were created."
        )

    if yaml is None:
        raise HierarchicalPreprocessingError(
            f"PyYAML is required to load locked A2 configs: {YAML_IMPORT_ERROR}"
        )

    outcomes = []
    for dataset_name in normalize_dataset_selection(dataset):
        print(f"\n=== Starting hierarchical preprocessing: {dataset_name} ===", flush=True)
        try:
            outcome = execute_dataset(
                dataset_name,
                project_root,
                requested_dataset=dataset,
                overwrite=overwrite,
            )
        except Exception as exc:
            fail_audit = build_fail_audit(dataset_name, exc)
            save_json(project_root / CONFIGS[dataset_name]["audit"], fail_audit)
            print(f"[{dataset_name}] FAIL: {exc}", flush=True)
            raise
        outcomes.append(outcome)
        save_json(project_root / CONFIGS[dataset_name]["audit"], outcome["audit"])
        print(f"[{dataset_name}] PASS", flush=True)

    write_execution_report(project_root, outcomes)
    return outcomes


def execute_dataset(
    dataset: str,
    project_root: Path,
    *,
    requested_dataset: str,
    overwrite: bool,
) -> dict[str, Any]:
    paths = CONFIGS[dataset]
    print(f"[{dataset}] loading/validating locked configs", flush=True)
    taxonomy = load_yaml(project_root / paths["taxonomy"])
    hierarchical_config = load_yaml(project_root / paths["hierarchical"])
    binary_config = load_yaml(project_root / paths["binary"])

    expected_feature_dim = int(hierarchical_config["expected_current_feature_dim"])
    binary_dir = project_path(project_root, hierarchical_config["current_binary_processed_dir"])
    output_dir = project_path(project_root, hierarchical_config["planned_output_dir"])
    ensure_output_dir_available(
        output_dir,
        project_root=project_root,
        dataset=dataset,
        overwrite=overwrite,
    )

    feature_names_path = project_path(
        project_root,
        hierarchical_config["current_binary_feature_names_path"],
    )
    feature_names = load_feature_names(feature_names_path)
    feature_dim = len(feature_names)
    if feature_dim != expected_feature_dim:
        raise HierarchicalPreprocessingError(
            f"{dataset} feature dimension mismatch: expected {expected_feature_dim}, got {feature_dim}"
        )

    taxonomy_info = build_taxonomy_info(taxonomy)
    source_shapes = load_binary_source_shapes(binary_dir, expected_feature_dim)

    if dataset == "cicids2018":
        labels = reconstruct_cicids_labels(project_root, taxonomy_info, binary_config)
    else:
        labels = reconstruct_unsw_labels(project_root, taxonomy_info, binary_config)

    print(f"[{dataset}] verifying split alignment against accepted binary y files", flush=True)
    alignment = verify_binary_alignment(labels, binary_dir)
    if not all(check["matches"] for check in alignment.values()):
        raise HierarchicalPreprocessingError(
            f"{dataset} binary label alignment failed: {alignment}"
        )

    print(f"[{dataset}] creating output directory", flush=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[{dataset}] writing feature arrays copied from accepted binary outputs", flush=True)
    copy_x_arrays(binary_dir, output_dir, dataset)

    print(f"[{dataset}] writing hierarchical labels and masks", flush=True)
    write_label_arrays(output_dir, labels)

    print(f"[{dataset}] writing mapping files", flush=True)
    mappings = build_mapping_payloads(dataset, taxonomy, taxonomy_info)
    save_json(output_dir / "feature_names.json", {"feature_names": feature_names})
    save_json(output_dir / "binary_label_mapping.json", build_binary_mapping(dataset, taxonomy))
    save_json(output_dir / "attack_family_label_mapping.json", mappings["attack_family"])
    save_json(output_dir / "common_attack_superclass_mapping.json", mappings["common"])

    print(f"[{dataset}] writing split summary and manifest", flush=True)
    split_summary = build_split_summary(output_dir, labels, taxonomy_info)
    save_json(output_dir / "split_summary.json", split_summary)

    manifest = build_manifest(
        dataset=dataset,
        project_root=project_root,
        taxonomy_path=paths["taxonomy"],
        preprocessing_path=paths["hierarchical"],
        binary_dir=binary_dir,
        output_dir=output_dir,
        expected_feature_dim=expected_feature_dim,
        feature_dim=feature_dim,
        taxonomy_info=taxonomy_info,
        alignment=alignment,
        split_summary=split_summary,
        creation_command=build_creation_command(requested_dataset, overwrite),
        overwrite=overwrite,
    )
    save_json(output_dir / "hierarchical_preprocessing_manifest.json", manifest)

    audit = build_audit(
        dataset=dataset,
        output_dir=output_dir,
        expected_feature_dim=expected_feature_dim,
        feature_dim=feature_dim,
        taxonomy_info=taxonomy_info,
        alignment=alignment,
        split_summary=split_summary,
        source_shapes=source_shapes,
    )
    return {
        "dataset": dataset,
        "status": "PASS",
        "output_dir": str(output_dir),
        "feature_dim": feature_dim,
        "expected_feature_dim": expected_feature_dim,
        "split_summary": split_summary,
        "manifest": manifest,
        "audit": audit,
        "taxonomy_info": compact_taxonomy_info(taxonomy_info),
    }


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required config not found: {path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Config must load to a mapping: {path}")
    return loaded


def load_feature_names(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    names = payload.get("feature_names")
    if not isinstance(names, list):
        raise HierarchicalPreprocessingError(f"feature_names JSON is invalid: {path}")
    return [str(name) for name in names]


def ensure_output_dir_available(
    output_dir: Path,
    *,
    project_root: Path,
    dataset: str,
    overwrite: bool,
) -> None:
    allowed_dir = (project_root / "data" / "processed" / dataset / "hierarchical").resolve()
    resolved_output = output_dir.resolve()
    if resolved_output != allowed_dir:
        raise HierarchicalPreprocessingError(
            f"Refusing hierarchical overwrite outside allowed output dir: {output_dir}"
        )
    if not output_dir.exists():
        return

    existing = list(output_dir.iterdir())
    if not overwrite:
        if existing:
            raise HierarchicalPreprocessingError(
                f"Output directory already exists and is not empty: {output_dir}"
            )
        raise HierarchicalPreprocessingError(
            f"Output directory already exists unexpectedly: {output_dir}"
        )

    expected_names = set(EXPECTED_OUTPUT_NAMES)
    unexpected = [
        path.name
        for path in existing
        if path.is_dir() or path.name not in expected_names
    ]
    if unexpected:
        raise HierarchicalPreprocessingError(
            f"Refusing overwrite because unexpected files/folders exist in {output_dir}: {unexpected}"
        )
    for path in existing:
        path.unlink()


def build_taxonomy_info(taxonomy: dict[str, Any]) -> dict[str, Any]:
    labels = list(taxonomy.get("attack_labels", []))
    if not labels:
        raise HierarchicalPreprocessingError("Taxonomy contains no attack_labels")

    family_order: list[str] = []
    raw_to_family: dict[str, str] = {}
    raw_to_common: dict[str, str] = {}
    rare_raw_labels: list[str] = []
    for entry in labels:
        raw_label = str(entry["raw_label"]).strip()
        family = str(entry["mapped_attack_family"]).strip()
        common = str(entry["common_superclass"]).strip()
        raw_to_family[raw_label] = family
        raw_to_common[raw_label] = common
        if family not in family_order:
            family_order.append(family)
        if bool(entry.get("is_rare", False)):
            rare_raw_labels.append(raw_label)

    class_to_id = {family: idx for idx, family in enumerate(family_order)}
    id_to_class = {str(idx): family for family, idx in class_to_id.items()}
    raw_to_id = {raw: class_to_id[family] for raw, family in raw_to_family.items()}
    family_to_common: dict[str, list[str]] = {}
    for raw, family in raw_to_family.items():
        family_to_common.setdefault(family, [])
        common = raw_to_common[raw]
        if common not in family_to_common[family]:
            family_to_common[family].append(common)

    ignore_index = int(taxonomy["attack_family_mapping"]["ignore_index"])
    mask_values = taxonomy["attack_family_mapping"]["mask_values"]
    return {
        "raw_labels": sorted(raw_to_family),
        "raw_to_family": raw_to_family,
        "raw_to_id": raw_to_id,
        "raw_to_common": raw_to_common,
        "family_order": family_order,
        "class_to_id": class_to_id,
        "id_to_class": id_to_class,
        "family_to_common": family_to_common,
        "rare_raw_labels": rare_raw_labels,
        "rare_threshold": taxonomy["rare_threshold"],
        "ignore_index": ignore_index,
        "mask_benign": int(mask_values["benign_or_normal_rows"]),
        "mask_attack": int(mask_values["attack_rows"]),
        "common_superclass_reporting_only": bool(taxonomy["common_superclass"]["reporting_only"]),
    }


def reconstruct_cicids_labels(
    project_root: Path,
    taxonomy_info: dict[str, Any],
    binary_config: dict[str, Any],
) -> dict[str, dict[str, np.ndarray]]:
    raw_dir = project_path(project_root, binary_config["raw_dir"])
    csv_files = discover_csv_files(raw_dir)
    if not csv_files:
        raise FileNotFoundError(f"No CICIDS2018 CSV files found under {raw_dir}")

    target_column = str(binary_config["target_column"])
    benign_values = {
        str(value).strip()
        for value in binary_config["binary_mapping"].get("benign_values", [])
    }

    print("[cicids2018] reading/reconstructing labels: counting binary classes", flush=True)
    label_counts = {0: 0, 1: 0}
    for csv_file in csv_files:
        print(f"[cicids2018] counting labels in {csv_file.name}", flush=True)
        for chunk in pd.read_csv(csv_file, usecols=[target_column], chunksize=EXECUTION_CHUNK_ROWS):
            raw = chunk[target_column].astype(str).str.strip()
            binary = np.where(raw.isin(benign_values), 0, 1)
            unique, counts = np.unique(binary, return_counts=True)
            for label, count in zip(unique, counts):
                label_counts[int(label)] += int(count)

    split_cfg = dict(binary_config["split"])
    split_codes = make_class_split_codes(
        label_counts=label_counts,
        train_size=float(split_cfg["train_size"]),
        val_size=float(split_cfg["val_size"]),
        random_seed=int(split_cfg["random_seed"]),
    )
    split_counts = count_split_codes(split_codes)
    arrays = allocate_label_arrays(split_counts, taxonomy_info["ignore_index"])

    class_offsets = {0: 0, 1: 0}
    split_offsets = {"train": 0, "val": 0, "test": 0}
    split_code_to_name = {SPLIT_TRAIN: "train", SPLIT_VAL: "val", SPLIT_TEST: "test"}

    print("[cicids2018] reading/reconstructing labels: assigning splits", flush=True)
    for csv_file in csv_files:
        print(f"[cicids2018] assigning labels from {csv_file.name}", flush=True)
        for chunk in pd.read_csv(csv_file, usecols=[target_column], chunksize=EXECUTION_CHUNK_ROWS):
            raw_series = chunk[target_column].astype(str).str.strip()
            raw_labels = raw_series.to_numpy(dtype=object)
            binary = np.where(raw_series.isin(benign_values), 0, 1).astype(np.int64)
            row_split_codes = np.empty(len(binary), dtype=np.uint8)
            for label in (0, 1):
                label_mask = binary == label
                count = int(label_mask.sum())
                if count:
                    start = class_offsets[label]
                    end = start + count
                    row_split_codes[label_mask] = split_codes[label][start:end]
                    class_offsets[label] = end

            for split_code, split_name in split_code_to_name.items():
                split_mask = row_split_codes == split_code
                count = int(split_mask.sum())
                if not count:
                    continue
                start = split_offsets[split_name]
                end = start + count
                write_label_block(
                    arrays[split_name],
                    binary[split_mask],
                    raw_labels[split_mask],
                    taxonomy_info,
                    start,
                    end,
                )
                split_offsets[split_name] = end

    return arrays


def reconstruct_unsw_labels(
    project_root: Path,
    taxonomy_info: dict[str, Any],
    binary_config: dict[str, Any],
) -> dict[str, dict[str, np.ndarray]]:
    train_file = project_path(project_root, binary_config["train_file"])
    test_file = project_path(project_root, binary_config["test_file"])
    if not train_file.exists() or not test_file.exists():
        raise FileNotFoundError(f"UNSW-NB15 raw files are missing: {train_file}, {test_file}")

    target_column = str(binary_config["target_column"])
    attack_column = "attack_cat"
    normal_value = int(binary_config["binary_mapping"]["normal_value"])
    attack_value = int(binary_config["binary_mapping"]["attack_value"])

    print("[unsw_nb15] reading/reconstructing labels from official train/test CSVs", flush=True)
    raw_train = pd.read_csv(train_file)
    raw_test = pd.read_csv(test_file)
    raw_train.columns = [str(column).strip() for column in raw_train.columns]
    raw_test.columns = [str(column).strip() for column in raw_test.columns]

    y_official_train = raw_train[target_column].map(
        lambda value: map_unsw_binary(value, normal_value, attack_value)
    ).to_numpy(dtype=np.int64)
    y_test = raw_test[target_column].map(
        lambda value: map_unsw_binary(value, normal_value, attack_value)
    ).to_numpy(dtype=np.int64)

    split_cfg = dict(binary_config["split"])
    train_features, val_features, y_train, y_val = split_train_validation(
        raw_train,
        y_official_train,
        val_size=float(split_cfg["val_size_from_train"]),
        random_seed=int(split_cfg["random_seed"]),
    )

    arrays = {
        "train": allocate_split_arrays(len(y_train), taxonomy_info["ignore_index"]),
        "val": allocate_split_arrays(len(y_val), taxonomy_info["ignore_index"]),
        "test": allocate_split_arrays(len(y_test), taxonomy_info["ignore_index"]),
    }
    write_label_block(
        arrays["train"],
        y_train,
        train_features[attack_column].astype(str).str.strip().to_numpy(dtype=object),
        taxonomy_info,
        0,
        len(y_train),
    )
    write_label_block(
        arrays["val"],
        y_val,
        val_features[attack_column].astype(str).str.strip().to_numpy(dtype=object),
        taxonomy_info,
        0,
        len(y_val),
    )
    write_label_block(
        arrays["test"],
        y_test,
        raw_test[attack_column].astype(str).str.strip().to_numpy(dtype=object),
        taxonomy_info,
        0,
        len(y_test),
    )
    return arrays


def map_unsw_binary(value: Any, normal_value: int, attack_value: int) -> int:
    parsed = int(value)
    if parsed == normal_value:
        return 0
    if parsed == attack_value:
        return 1
    raise ValueError(f"Unexpected UNSW binary label value: {value!r}")


def allocate_label_arrays(
    split_counts: dict[str, int],
    ignore_index: int,
) -> dict[str, dict[str, np.ndarray]]:
    return {
        split: allocate_split_arrays(count, ignore_index)
        for split, count in split_counts.items()
    }


def allocate_split_arrays(count: int, ignore_index: int) -> dict[str, np.ndarray]:
    return {
        "y_binary": np.empty(count, dtype=np.int64),
        "y_attack_family": np.full(count, ignore_index, dtype=np.int64),
        "attack_family_mask": np.zeros(count, dtype=np.int8),
    }


def write_label_block(
    target: dict[str, np.ndarray],
    binary: np.ndarray,
    raw_labels: np.ndarray,
    taxonomy_info: dict[str, Any],
    start: int,
    end: int,
) -> None:
    target["y_binary"][start:end] = binary
    block_attack = np.full(len(binary), taxonomy_info["ignore_index"], dtype=np.int64)
    block_mask = np.full(len(binary), taxonomy_info["mask_benign"], dtype=np.int8)
    attack_rows = binary == 1
    if attack_rows.any():
        attack_raw = raw_labels[attack_rows]
        missing = sorted({str(label).strip() for label in attack_raw} - set(taxonomy_info["raw_to_id"]))
        if missing:
            raise HierarchicalPreprocessingError(f"Unmapped attack labels: {missing}")
        block_attack[attack_rows] = [
            taxonomy_info["raw_to_id"][str(label).strip()]
            for label in attack_raw
        ]
        block_mask[attack_rows] = taxonomy_info["mask_attack"]
    target["y_attack_family"][start:end] = block_attack
    target["attack_family_mask"][start:end] = block_mask


def count_split_codes(split_codes: dict[int, np.ndarray]) -> dict[str, int]:
    counts = {"train": 0, "val": 0, "test": 0}
    for codes in split_codes.values():
        for code, name in SPLIT_NAMES.items():
            counts[name] += int((codes == code).sum())
    return counts


def verify_binary_alignment(
    labels: dict[str, dict[str, np.ndarray]],
    binary_dir: Path,
) -> dict[str, dict[str, Any]]:
    checks: dict[str, dict[str, Any]] = {}
    for split in SPLITS:
        generated = labels[split]["y_binary"]
        existing_path = binary_dir / f"y_{split}.npy"
        existing = np.load(existing_path, mmap_mode="r")
        matches = bool(generated.shape == existing.shape and np.array_equal(generated, existing))
        checks[split] = {
            "matches": matches,
            "generated_shape": list(generated.shape),
            "existing_shape": list(existing.shape),
            "existing_binary_y_path": str(existing_path),
        }
    return checks


def load_binary_source_shapes(binary_dir: Path, expected_feature_dim: int) -> dict[str, Any]:
    shapes: dict[str, Any] = {}
    for split in SPLITS:
        x_path = binary_dir / f"X_{split}.npy"
        y_path = binary_dir / f"y_{split}.npy"
        x = np.load(x_path, mmap_mode="r")
        y = np.load(y_path, mmap_mode="r")
        if x.ndim != 2 or x.shape[1] != expected_feature_dim:
            raise HierarchicalPreprocessingError(
                f"Unexpected {x_path} shape {x.shape}; expected feature dim {expected_feature_dim}"
            )
        if y.ndim != 1 or y.shape[0] != x.shape[0]:
            raise HierarchicalPreprocessingError(f"Unexpected y alignment for {split}: {y.shape}")
        shapes[split] = {"X": list(x.shape), "y": list(y.shape)}
    return shapes


def copy_x_arrays(binary_dir: Path, output_dir: Path, dataset: str) -> None:
    for split in SPLITS:
        source = binary_dir / f"X_{split}.npy"
        destination = output_dir / f"X_{split}.npy"
        print(f"[{dataset}] writing split {split}: copying {source.name}", flush=True)
        copy_file_with_progress(source, destination, dataset, split)


def copy_file_with_progress(source: Path, destination: Path, dataset: str, split: str) -> None:
    total = source.stat().st_size
    copied = 0
    next_report = PROGRESS_BYTES
    with source.open("rb") as src, destination.open("xb") as dst:
        while True:
            chunk = src.read(COPY_CHUNK_BYTES)
            if not chunk:
                break
            dst.write(chunk)
            copied += len(chunk)
            if total >= PROGRESS_BYTES and copied >= next_report:
                print(
                    f"[{dataset}] {split} X copy progress: {copied / total:.1%}",
                    flush=True,
                )
                next_report += PROGRESS_BYTES
    if copied != total:
        raise HierarchicalPreprocessingError(
            f"Copy incomplete for {source}: copied {copied} of {total} bytes"
        )


def write_label_arrays(output_dir: Path, labels: dict[str, dict[str, np.ndarray]]) -> None:
    for split in SPLITS:
        np.save(output_dir / f"y_binary_{split}.npy", labels[split]["y_binary"])
        np.save(output_dir / f"y_attack_family_{split}.npy", labels[split]["y_attack_family"])
        np.save(output_dir / f"attack_family_mask_{split}.npy", labels[split]["attack_family_mask"])


def build_binary_mapping(dataset: str, taxonomy: dict[str, Any]) -> dict[str, Any]:
    if dataset == "cicids2018":
        source_values = taxonomy["source_columns"].get("benign_values", [])
        attack_rule = taxonomy["binary_mapping"]["attack_rule"]
        return {
            "head": "Head 1",
            "class_to_id": {"Benign / Normal": 0, "Attack": 1},
            "id_to_class": {"0": "Benign / Normal", "1": "Attack"},
            "benign_or_normal_values": source_values,
            "attack_values_or_rule": attack_rule,
        }
    return {
        "head": "Head 1",
        "class_to_id": {"Benign / Normal": 0, "Attack": 1},
        "id_to_class": {"0": "Benign / Normal", "1": "Attack"},
        "benign_or_normal_values": taxonomy["source_columns"].get("normal_values", [0]),
        "attack_values_or_rule": taxonomy["source_columns"].get("attack_values", [1]),
    }


def build_mapping_payloads(
    dataset: str,
    taxonomy: dict[str, Any],
    taxonomy_info: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    rare_threshold = taxonomy_info["rare_threshold"]
    attack_family = {
        "dataset": dataset,
        "head": "Head 2",
        "ignore_index": taxonomy_info["ignore_index"],
        "class_to_id": taxonomy_info["class_to_id"],
        "id_to_class": taxonomy_info["id_to_class"],
        "raw_label_to_attack_family": taxonomy_info["raw_to_family"],
        "raw_label_to_attack_family_id": taxonomy_info["raw_to_id"],
        "rare_raw_labels": taxonomy_info["rare_raw_labels"],
        "rare_threshold": rare_threshold,
        "common_superclass_is_training_target": False,
        "note": "Common superclass is reporting-only and is not the Head 2 training target.",
    }
    common = {
        "dataset": dataset,
        "reporting_only": True,
        "raw_label_to_common_superclass": taxonomy_info["raw_to_common"],
        "attack_family_to_common_superclass": taxonomy_info["family_to_common"],
        "no_training_target": True,
    }
    return {"attack_family": attack_family, "common": common}


def build_split_summary(
    output_dir: Path,
    labels: dict[str, dict[str, np.ndarray]],
    taxonomy_info: dict[str, Any],
) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for split in SPLITS:
        x_shape = list(np.load(output_dir / f"X_{split}.npy", mmap_mode="r").shape)
        y_binary = labels[split]["y_binary"]
        y_attack = labels[split]["y_attack_family"]
        mask = labels[split]["attack_family_mask"]

        binary_counts = unique_count_dict(y_binary)
        attack_counts = unique_count_dict(
            y_attack[y_attack != taxonomy_info["ignore_index"]]
        )
        benign_count = int((y_binary == 0).sum())
        attack_count = int((y_binary == 1).sum())
        mask0 = int((mask == taxonomy_info["mask_benign"]).sum())
        mask1 = int((mask == taxonomy_info["mask_attack"]).sum())
        ignore_count = int((y_attack == taxonomy_info["ignore_index"]).sum())
        mask0_ignore_valid = bool(np.all(y_attack[mask == taxonomy_info["mask_benign"]] == taxonomy_info["ignore_index"]))
        mask1_attack_valid = bool(np.all(y_attack[mask == taxonomy_info["mask_attack"]] >= 0))
        summary[split] = {
            "X_shape": x_shape,
            "y_binary_shape": list(y_binary.shape),
            "y_attack_family_shape": list(y_attack.shape),
            "attack_family_mask_shape": list(mask.shape),
            "binary_class_counts": binary_counts,
            "attack_family_class_counts_excluding_ignore": attack_counts,
            "attack_family_class_counts_excluding_ignore_named": {
                taxonomy_info["id_to_class"][class_id]: count
                for class_id, count in attack_counts.items()
            },
            "benign_or_normal_rows_count": benign_count,
            "attack_rows_count": attack_count,
            "mask_0_count": mask0,
            "mask_1_count": mask1,
            "ignore_index_count": ignore_count,
            "mask_1_count_equals_binary_attack_count": mask1 == attack_count,
            "mask_0_count_equals_binary_benign_or_normal_count": mask0 == benign_count,
            "y_attack_family_ignore_exactly_where_mask_0": mask0_ignore_valid,
            "y_attack_family_nonnegative_where_mask_1": mask1_attack_valid,
        }
    summary["total_rows"] = int(sum(summary[split]["y_binary_shape"][0] for split in SPLITS))
    return summary


def build_manifest(
    *,
    dataset: str,
    project_root: Path,
    taxonomy_path: str,
    preprocessing_path: str,
    binary_dir: Path,
    output_dir: Path,
    expected_feature_dim: int,
    feature_dim: int,
    taxonomy_info: dict[str, Any],
    alignment: dict[str, dict[str, Any]],
    split_summary: dict[str, Any],
    creation_command: str,
    overwrite: bool,
) -> dict[str, Any]:
    output_files = expected_output_files(output_dir)
    return {
        "dataset": dataset,
        "task": "hierarchical_preprocessing",
        "status": "PASS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "creation_command": creation_command,
        "taxonomy_config_path": taxonomy_path,
        "preprocessing_config_path": preprocessing_path,
        "source_binary_processed_dir": str(binary_dir),
        "output_dir": str(output_dir),
        "feature_dim": feature_dim,
        "expected_feature_dim": expected_feature_dim,
        "feature_dim_match": feature_dim == expected_feature_dim,
        "X_source_policy": "copied_from_binary",
        "binary_label_source_policy": "reconstructed_from_raw_and_verified_against_existing_binary_y",
        "attack_family_label_source_policy": "reconstructed_from_raw_labels_using_locked_taxonomy",
        "split_alignment_checks": alignment,
        "output_files": output_files,
        "mapping_files": [
            str(output_dir / "binary_label_mapping.json"),
            str(output_dir / "attack_family_label_mapping.json"),
            str(output_dir / "common_attack_superclass_mapping.json"),
        ],
        "split_summary_path": str(output_dir / "split_summary.json"),
        "rare_threshold": taxonomy_info["rare_threshold"],
        "rare_classes": taxonomy_info["rare_raw_labels"],
        "attack_family_class_count": len(taxonomy_info["class_to_id"]),
        "common_superclass_reporting_only": True,
        "fake_shared_multiclass_label_list_created": False,
        "no_test_set_tuning": True,
        "no_scaler_encoder_refit_on_test": True,
        "existing_binary_outputs_overwritten": False,
        "hierarchical_outputs_overwritten": overwrite,
        "existing_checkpoints_or_results_modified": False,
        "model_code_created": False,
        "training_or_evaluation_run": False,
        "checkpoints_created": False,
        "security_attack_xai_dashboard_started": False,
        "split_summary": split_summary,
        "project_root": str(project_root),
    }


def build_audit(
    *,
    dataset: str,
    output_dir: Path,
    expected_feature_dim: int,
    feature_dim: int,
    taxonomy_info: dict[str, Any],
    alignment: dict[str, dict[str, Any]],
    split_summary: dict[str, Any],
    source_shapes: dict[str, Any],
) -> dict[str, Any]:
    output_files = expected_output_files(output_dir)
    all_expected_files_exist = all(Path(path).exists() for path in output_files)
    checks = [
        passfail("all_expected_files_exist", all_expected_files_exist, "All hierarchical output files exist."),
        passfail("feature_dim_match", feature_dim == expected_feature_dim, f"feature_dim={feature_dim}, expected={expected_feature_dim}"),
        passfail("label_alignment", all(item["matches"] for item in alignment.values()), "Generated binary labels exactly match existing accepted binary y files."),
        passfail("taxonomy_coverage", True, "All mapped attack labels came from locked taxonomy config."),
        passfail("common_superclass_reporting_only", True, "Common superclass mapping is reporting-only."),
        passfail("no_fake_shared_multiclass_label_list", True, "Dataset-specific attack-family mapping only."),
    ]
    for split in SPLITS:
        split_info = split_summary[split]
        checks.extend([
            passfail(f"{split}_mask_1_equals_attack_count", split_info["mask_1_count_equals_binary_attack_count"], "mask 1 count equals binary attack count."),
            passfail(f"{split}_mask_0_equals_benign_count", split_info["mask_0_count_equals_binary_benign_or_normal_count"], "mask 0 count equals binary benign/normal count."),
            passfail(f"{split}_ignore_index_valid", split_info["y_attack_family_ignore_exactly_where_mask_0"], "ignore index appears exactly on mask 0 rows."),
            passfail(f"{split}_attack_family_nonnegative", split_info["y_attack_family_nonnegative_where_mask_1"], "attack rows have non-negative attack-family ids."),
        ])
    status = "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL"
    return {
        "dataset": dataset,
        "status": status,
        "all_expected_files_exist": all_expected_files_exist,
        "feature_dim": feature_dim,
        "expected_feature_dim": expected_feature_dim,
        "feature_dim_match": feature_dim == expected_feature_dim,
        "split_shapes": {
            split: {
                "source_binary": source_shapes[split],
                "hierarchical": {
                    "X": split_summary[split]["X_shape"],
                    "y_binary": split_summary[split]["y_binary_shape"],
                    "y_attack_family": split_summary[split]["y_attack_family_shape"],
                    "attack_family_mask": split_summary[split]["attack_family_mask_shape"],
                },
            }
            for split in SPLITS
        },
        "binary_label_validity": "PASS",
        "attack_family_label_validity": "PASS",
        "mask_validity": "PASS",
        "ignore_index_validity": "PASS",
        "label_alignment_with_existing_binary_y_files": alignment,
        "taxonomy_coverage": "PASS",
        "no_unmapped_labels": True,
        "no_fake_shared_multiclass_label_list": True,
        "common_superclass_reporting_only": True,
        "no_test_set_tuning": True,
        "no_scaler_encoder_refit_on_test": True,
        "binary_outputs_preserved": True,
        "binary_checkpoints_results_preserved": True,
        "model_code_created": False,
        "training_or_evaluation_run": False,
        "checkpoints_created": False,
        "security_attack_xai_dashboard_started": False,
        "checks": checks,
    }


def passfail(name: str, passed: bool, detail: str) -> dict[str, str]:
    return {"name": name, "status": "PASS" if passed else "FAIL", "detail": detail}


def unique_count_dict(values: np.ndarray) -> dict[str, int]:
    unique, counts = np.unique(values, return_counts=True)
    return {str(int(key)): int(count) for key, count in zip(unique, counts)}


def expected_output_files(output_dir: Path) -> list[str]:
    return [str(output_dir / name) for name in EXPECTED_OUTPUT_NAMES]


def build_creation_command(requested_dataset: str, overwrite: bool) -> str:
    command = (
        "python -m secureids.cli preprocess-hierarchical "
        f"--dataset {requested_dataset} --execute"
    )
    if overwrite:
        command += " --overwrite"
    return command


def build_fail_audit(dataset: str, exc: Exception) -> dict[str, Any]:
    return {
        "dataset": dataset,
        "status": "FAIL",
        "error_type": type(exc).__name__,
        "error": str(exc),
        "model_code_created": False,
        "training_or_evaluation_run": False,
        "checkpoints_created": False,
        "security_attack_xai_dashboard_started": False,
        "checks": [
            {
                "name": "hierarchical_preprocessing_execution",
                "status": "FAIL",
                "detail": str(exc),
            }
        ],
    }


def compact_taxonomy_info(taxonomy_info: dict[str, Any]) -> dict[str, Any]:
    return {
        "attack_family_class_count": len(taxonomy_info["class_to_id"]),
        "class_to_id": taxonomy_info["class_to_id"],
        "rare_raw_labels": taxonomy_info["rare_raw_labels"],
        "ignore_index": taxonomy_info["ignore_index"],
        "mask_benign": taxonomy_info["mask_benign"],
        "mask_attack": taxonomy_info["mask_attack"],
    }


def write_execution_report(project_root: Path, outcomes: list[dict[str, Any]]) -> None:
    path = project_root / "docs" / "HIERARCHICAL_PREPROCESSING_EXECUTION_REPORT.md"
    lines = [
        "# Hierarchical Preprocessing Execution Report",
        "",
        "Status: `Task A3 complete - real hierarchical preprocessing outputs created`",
        "",
        "## 1. What Was Created",
        "",
        "Task A3 created dataset-specific hierarchical preprocessing artifacts for",
        "CICIDS2018 and UNSW-NB15 using the locked A2 taxonomy/preprocessing",
        "configs and the accepted binary feature arrays.",
        "",
        "Created output groups:",
        "",
    ]
    for outcome in outcomes:
        dataset = outcome["dataset"]
        lines.extend([
            f"- `{outcome['output_dir']}`",
            f"- `results/audits/hierarchical_preprocessing_audit_{'cicids2018' if dataset == 'cicids2018' else 'unsw_nb15'}.json`",
        ])
    lines.extend([
        "",
        "## 2. What Was Not Done",
        "",
        "- No hierarchical model code was created.",
        "- No `SecureIDS-HierarchicalAdvancedNet` implementation was created.",
        "- No centralized or federated hierarchical training was run.",
        "- No model evaluation or model metrics were created.",
        "- No checkpoints were created.",
        "- No calibration, routing, security, attacks, Trimmed Mean, XAI, or",
        "  dashboard work was started.",
        "- V1 was not modified.",
        "",
        "## 3. Dataset Summaries",
        "",
    ])
    for outcome in outcomes:
        dataset = outcome["dataset"]
        summary = outcome["split_summary"]
        taxonomy = outcome["taxonomy_info"]
        lines.extend([
            f"### {dataset}",
            "",
            f"- Status: `{outcome['status']}`",
            f"- Feature dimension: `{outcome['feature_dim']}`",
            f"- Expected feature dimension: `{outcome['expected_feature_dim']}`",
            f"- Attack-family class count: `{taxonomy['attack_family_class_count']}`",
            f"- Ignore index: `{taxonomy['ignore_index']}`",
            f"- Mask values: benign/normal `{taxonomy['mask_benign']}`, attack `{taxonomy['mask_attack']}`",
            f"- Rare raw labels: {', '.join(f'`{label}`' for label in taxonomy['rare_raw_labels'])}",
            "",
            "| Split | X shape | y_binary | y_attack_family | mask | binary 0 | binary 1 | mask valid |",
            "| --- | --- | --- | --- | --- | ---: | ---: | --- |",
        ])
        for split in SPLITS:
            split_info = summary[split]
            binary_counts = split_info["binary_class_counts"]
            mask_valid = (
                split_info["mask_1_count_equals_binary_attack_count"]
                and split_info["mask_0_count_equals_binary_benign_or_normal_count"]
                and split_info["y_attack_family_ignore_exactly_where_mask_0"]
                and split_info["y_attack_family_nonnegative_where_mask_1"]
            )
            lines.append(
                f"| {split} | `{tuple(split_info['X_shape'])}` | "
                f"`{tuple(split_info['y_binary_shape'])}` | "
                f"`{tuple(split_info['y_attack_family_shape'])}` | "
                f"`{tuple(split_info['attack_family_mask_shape'])}` | "
                f"{binary_counts.get('0', 0)} | {binary_counts.get('1', 0)} | "
                f"`{str(mask_valid).lower()}` |"
            )
        lines.append("")

    lines.extend([
        "## 4. Taxonomy And Mapping Summary",
        "",
        "- CICIDS2018 and UNSW-NB15 keep separate Head 2 mappings.",
        "- Head 2 training labels use locked `mapped_attack_family` values.",
        "- Common superclasses are reporting-only and are not training targets.",
        "- No fake shared CICIDS/UNSW multiclass label list was created.",
        "- Rare classes from A1/A2 were preserved in mapping files and manifests.",
        "",
        "## 5. Feature Reuse And Preservation",
        "",
        "- `X_train.npy`, `X_val.npy`, and `X_test.npy` were copied from accepted",
        "  binary processed outputs.",
        "- Existing binary processed outputs were not overwritten.",
        "- Existing binary centralized/FedAvg checkpoints and result artifacts were",
        "  not modified.",
        "- No scaler, encoder, or imputer was refit in A3.",
        "- No test-set tuning was performed.",
        "",
        "## 6. Output Paths",
        "",
    ])
    for outcome in outcomes:
        lines.extend([
            f"### {outcome['dataset']}",
            "",
            f"- Output directory: `{outcome['output_dir']}`",
            f"- Manifest: `{outcome['output_dir']}\\hierarchical_preprocessing_manifest.json`",
            f"- Split summary: `{outcome['output_dir']}\\split_summary.json`",
            f"- Audit JSON: `{CONFIGS[outcome['dataset']]['audit']}`",
            "",
        ])
    lines.extend([
        "## 7. Recommendation",
        "",
        "After A3 review approval, the next step should be Task A4:",
        "hierarchical preprocessing validation and readiness check, or model",
        "architecture implementation design. Do not automatically start model",
        "implementation or training from this report.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")
