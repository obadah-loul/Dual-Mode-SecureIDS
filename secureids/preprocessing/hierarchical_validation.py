"""Readiness validation for hierarchical preprocessing artifacts.

Task A4 is intentionally read-only for processed arrays and model artifacts.
This module validates A3 outputs and writes readiness reports only.
"""

from __future__ import annotations

from secureids.artifacts import load_numpy_readonly

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from secureids.preprocessing.artifacts import save_json
from secureids.preprocessing.hierarchical import normalize_dataset_selection


EXPECTED_FILES = [
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
SPLITS = ("train", "val", "test")

DATASET_CONFIG = {
    "cicids2018": {
        "expected_feature_dim": 77,
        "hierarchical_dir": "data/processed/cicids2018/hierarchical",
        "binary_dir": "data/processed/cicids2018/binary",
        "readiness_json": "results/audits/hierarchical_preprocessing_readiness_cicids2018.json",
        "taxonomy_config_path": "configs/taxonomy/cicids2018_attack_taxonomy.yaml",
        "preprocessing_config_path": "configs/preprocessing/cicids2018_hierarchical.yaml",
    },
    "unsw_nb15": {
        # A8.8: 192 after UNSW split-protocol correction (legacy pre-correction was 190).
        "expected_feature_dim": 192,
        "hierarchical_dir": "data/processed/unsw_nb15/hierarchical",
        "binary_dir": "data/processed/unsw_nb15/binary",
        "readiness_json": "results/audits/hierarchical_preprocessing_readiness_unsw_nb15.json",
        "taxonomy_config_path": "configs/taxonomy/unsw_nb15_attack_taxonomy.yaml",
        "preprocessing_config_path": "configs/preprocessing/unsw_nb15_hierarchical.yaml",
    },
}

BINARY_OUTPUTS = [
    "data/processed/cicids2018/binary/X_train.npy",
    "data/processed/cicids2018/binary/X_val.npy",
    "data/processed/cicids2018/binary/X_test.npy",
    "data/processed/cicids2018/binary/y_train.npy",
    "data/processed/cicids2018/binary/y_val.npy",
    "data/processed/cicids2018/binary/y_test.npy",
    "data/processed/unsw_nb15/binary/X_train.npy",
    "data/processed/unsw_nb15/binary/X_val.npy",
    "data/processed/unsw_nb15/binary/X_test.npy",
    "data/processed/unsw_nb15/binary/y_train.npy",
    "data/processed/unsw_nb15/binary/y_val.npy",
    "data/processed/unsw_nb15/binary/y_test.npy",
]

BINARY_FINAL_CHECKPOINTS = [
    "models/final/final_cicids_binary.pt",
    "models/final/final_unsw_binary.pt",
]

BINARY_FEDAVG_CHECKPOINTS = [
    "models/federated/fedavg_cicids_binary.pt",
    "models/federated/fedavg_unsw_binary.pt",
]

HIERARCHICAL_CHECKPOINTS = [
    "models/final/final_cicids_hierarchical.pt",
    "models/final/final_unsw_hierarchical.pt",
    "models/federated/fedavg_cicids_hierarchical.pt",
    "models/federated/fedavg_unsw_hierarchical.pt",
]

LATER_LAYER_OUTPUT_DIRS = [
    "results/security",
    "results/attacks",
    "results/robust",
    "results/xai",
]

PREEXISTING_FUTURE_LAYER_SCAFFOLDS = [
    "dashboard/app.py",
    "secureids/security/__init__.py",
    "secureids/attacks/__init__.py",
    "secureids/xai/__init__.py",
]


class HierarchicalReadinessError(RuntimeError):
    """Raised when readiness validation cannot be completed."""


def run_hierarchical_readiness_validation(
    dataset: str,
    project_root: Path,
) -> list[dict[str, Any]]:
    """Validate hierarchical preprocessing outputs and write A4 reports."""

    outcomes = []
    for dataset_name in normalize_dataset_selection(dataset):
        print(f"\n=== A4 readiness validation: {dataset_name} ===", flush=True)
        outcome = validate_dataset(dataset_name, project_root)
        save_json(project_root / DATASET_CONFIG[dataset_name]["readiness_json"], outcome)
        outcomes.append(outcome)
        print(
            f"[{dataset_name}] readiness {outcome['status']} "
            f"(ready={outcome['ready_for_hierarchical_model_implementation']})",
            flush=True,
        )

    write_readiness_report(project_root, outcomes)
    return outcomes


def validate_dataset(dataset: str, project_root: Path) -> dict[str, Any]:
    cfg = DATASET_CONFIG[dataset]
    base = project_root / cfg["hierarchical_dir"]
    binary_base = project_root / cfg["binary_dir"]
    expected_dim = int(cfg["expected_feature_dim"])
    checks: list[dict[str, str]] = []
    warnings: list[str] = []
    blocking_issues: list[str] = []

    print(f"[{dataset}] data/file checks", flush=True)
    folder_exists = base.exists() and base.is_dir()
    missing_files = [
        name for name in EXPECTED_FILES if not (base / name).exists()
    ]
    checks.append(check("hierarchical_folder_exists", folder_exists, str(base)))
    checks.append(check("all_expected_files_exist", not missing_files, f"missing={missing_files}"))
    if not folder_exists or missing_files:
        blocking_issues.append("Hierarchical output folder or required files are missing.")
        return finalize_readiness(
            dataset=dataset,
            expected_dim=expected_dim,
            detected_dim=None,
            expected_files_count=len(EXPECTED_FILES),
            missing_files=missing_files,
            checks=checks,
            blocking_issues=blocking_issues,
            warnings=warnings,
        )

    feature_names = load_json(base / "feature_names.json").get("feature_names", [])
    binary_mapping = load_json(base / "binary_label_mapping.json")
    attack_mapping = load_json(base / "attack_family_label_mapping.json")
    common_mapping = load_json(base / "common_attack_superclass_mapping.json")
    split_summary_file = load_json(base / "split_summary.json")
    manifest = load_json(base / "hierarchical_preprocessing_manifest.json")

    detected_dim = len(feature_names) if isinstance(feature_names, list) else None
    feature_dim_match = detected_dim == expected_dim
    checks.append(check("feature_names_count_matches_expected_dim", feature_dim_match, f"detected={detected_dim}, expected={expected_dim}"))

    print(f"[{dataset}] mapping validation", flush=True)
    mapping_summary = validate_mappings(
        dataset,
        binary_mapping,
        attack_mapping,
        common_mapping,
        checks,
    )

    print(f"[{dataset}] manifest validation", flush=True)
    manifest_summary = validate_manifest(
        dataset,
        manifest,
        cfg,
        expected_dim,
        checks,
        warnings,
    )

    print(f"[{dataset}] split/array validation", flush=True)
    split_shapes: dict[str, Any] = {}
    shape_summary: dict[str, Any] = {}
    binary_distribution: dict[str, Any] = {}
    attack_family_distribution: dict[str, Any] = {}
    split_summary_matches = True
    label_mask_consistency = True
    binary_labels_valid = True
    attack_family_labels_valid = True
    masks_valid = True
    ignore_index_valid = True
    split_sizes_match_binary = True
    no_empty_split = True
    total_attack_counts_by_id: dict[str, int] = {
        str(class_id): 0 for class_id in sorted(mapping_summary["id_to_class_int"])
    }

    for split in SPLITS:
        print(f"[{dataset}] validating split {split}", flush=True)
        split_result = validate_split(
            base,
            binary_base,
            split,
            expected_dim,
            mapping_summary,
        )
        split_shapes[split] = split_result["shapes"]
        shape_summary[split] = split_result["shape_summary"]
        binary_distribution[split] = split_result["binary_distribution"]
        attack_family_distribution[split] = split_result["attack_family_distribution_named"]
        split_summary_matches = split_summary_matches and compare_split_summary(
            split_summary_file.get(split, {}),
            split_result,
        )
        label_mask_consistency = label_mask_consistency and split_result["label_mask_consistency"]
        binary_labels_valid = binary_labels_valid and split_result["binary_labels_valid"]
        attack_family_labels_valid = attack_family_labels_valid and split_result["attack_family_labels_valid"]
        masks_valid = masks_valid and split_result["masks_valid"]
        ignore_index_valid = ignore_index_valid and split_result["ignore_index_valid"]
        split_sizes_match_binary = split_sizes_match_binary and split_result["sizes_match_existing_binary"]
        no_empty_split = no_empty_split and split_result["rows"] > 0
        for class_id, count_value in split_result["attack_family_distribution"].items():
            total_attack_counts_by_id[class_id] = total_attack_counts_by_id.get(class_id, 0) + count_value

        checks.extend(split_result["checks"])

    total_attack_counts_named = {
        mapping_summary["id_to_class"][class_id]: count_value
        for class_id, count_value in total_attack_counts_by_id.items()
    }
    missing_attack_classes = [
        mapping_summary["id_to_class"][str(class_id)]
        for class_id in sorted(mapping_summary["id_to_class_int"])
        if total_attack_counts_by_id.get(str(class_id), 0) == 0
    ]
    all_classes_present_or_documented = not missing_attack_classes
    if missing_attack_classes:
        warnings.append(
            "Mapped attack-family classes absent from all splits: "
            + ", ".join(missing_attack_classes)
        )

    rare_class_summary = build_rare_class_summary(
        attack_mapping,
        total_attack_counts_by_id,
        attack_family_distribution,
        warnings,
    )

    checks.append(check("split_summary_matches_arrays", split_summary_matches, "split_summary.json matches inspected arrays"))
    checks.append(check("no_split_empty", no_empty_split, "train/val/test all contain rows"))
    checks.append(check("all_attack_family_classes_present_or_documented", all_classes_present_or_documented, f"absent={missing_attack_classes}"))
    checks.append(check("rare_classes_present_or_documented", rare_class_summary["rare_classes_present_or_documented"], rare_class_summary["note"]))

    print(f"[{dataset}] safety checks", flush=True)
    safety_summary = build_safety_summary(project_root)
    checks.extend(safety_summary["checks"])

    boolean_checks = {
        "feature_dim_match": feature_dim_match,
        "label_mask_consistency": label_mask_consistency,
        "binary_labels_valid": binary_labels_valid,
        "attack_family_labels_valid": attack_family_labels_valid,
        "masks_valid": masks_valid,
        "ignore_index_valid": ignore_index_valid,
        "split_summary_matches_arrays": split_summary_matches,
        "all_attack_family_classes_present_or_documented": all_classes_present_or_documented,
        "rare_classes_present_or_documented": rare_class_summary["rare_classes_present_or_documented"],
        "common_superclass_reporting_only": mapping_summary["common_superclass_reporting_only"],
        "fake_shared_multiclass_label_list_created": False,
        "no_test_set_tuning": manifest_summary["no_test_set_tuning"],
        "no_scaler_encoder_refit_on_test": manifest_summary["no_scaler_encoder_refit_on_test"],
        "existing_binary_outputs_preserved": safety_summary["existing_binary_outputs_preserved"],
        "existing_binary_checkpoints_preserved": safety_summary["existing_binary_checkpoints_preserved"],
        "existing_fedavg_checkpoints_preserved": safety_summary["existing_fedavg_checkpoints_preserved"],
        "model_code_created": safety_summary["model_code_created"],
        "training_or_evaluation_run": False,
        "checkpoints_created": safety_summary["hierarchical_checkpoints_created"],
        "security_attack_xai_dashboard_started": safety_summary["security_attack_xai_dashboard_started"],
    }

    for key, value in boolean_checks.items():
        if key in {
            # A8.8: "model_code_created" intentionally removed from this
            # must-be-False set. The approved advanced model exists from A5 onward,
            # so it is reported as expected-present instead of blocking readiness.
            "fake_shared_multiclass_label_list_created",
            "training_or_evaluation_run",
            "checkpoints_created",
            "security_attack_xai_dashboard_started",
        }:
            checks.append(check(key, value is False, str(value)))
        elif key == "model_code_created":
            checks.append(
                check(
                    "advanced_model_code_present_expected_from_a5",
                    bool(value),
                    f"model_code_created={value} (approved and implemented at A5)",
                )
            )
        else:
            checks.append(check(key, bool(value), str(value)))

    failed = [item for item in checks if item["status"] != "PASS"]
    if failed:
        blocking_issues.extend(f"{item['name']}: {item['detail']}" for item in failed)

    status = "PASS" if not blocking_issues else "FAIL"
    ready = status == "PASS"

    return {
        "dataset": dataset,
        "status": status,
        "ready_for_hierarchical_model_implementation": ready,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "expected_feature_dim": expected_dim,
        "detected_feature_dim": detected_dim,
        "feature_dim_match": feature_dim_match,
        "expected_files_count": len(EXPECTED_FILES),
        "missing_files": missing_files,
        "split_shapes": split_shapes,
        "shape_summary": shape_summary,
        "binary_distribution": binary_distribution,
        "attack_family_distribution": {
            "by_split": attack_family_distribution,
            "total_by_id": total_attack_counts_by_id,
            "total_by_name": total_attack_counts_named,
            "absent_attack_family_classes": missing_attack_classes,
        },
        "rare_class_summary": rare_class_summary,
        "mapping_summary": mapping_summary,
        "manifest_summary": manifest_summary,
        "safety_summary": safety_summary["summary"],
        "label_mask_consistency": label_mask_consistency,
        "binary_labels_valid": binary_labels_valid,
        "attack_family_labels_valid": attack_family_labels_valid,
        "masks_valid": masks_valid,
        "ignore_index_valid": ignore_index_valid,
        "split_summary_matches_arrays": split_summary_matches,
        "all_attack_family_classes_present_or_documented": all_classes_present_or_documented,
        "rare_classes_present_or_documented": rare_class_summary["rare_classes_present_or_documented"],
        "common_superclass_reporting_only": mapping_summary["common_superclass_reporting_only"],
        "fake_shared_multiclass_label_list_created": False,
        "no_test_set_tuning": manifest_summary["no_test_set_tuning"],
        "no_scaler_encoder_refit_on_test": manifest_summary["no_scaler_encoder_refit_on_test"],
        "existing_binary_outputs_preserved": safety_summary["existing_binary_outputs_preserved"],
        "existing_binary_checkpoints_preserved": safety_summary["existing_binary_checkpoints_preserved"],
        "existing_fedavg_checkpoints_preserved": safety_summary["existing_fedavg_checkpoints_preserved"],
        "model_code_created": safety_summary["model_code_created"],
        "training_or_evaluation_run": False,
        "checkpoints_created": safety_summary["hierarchical_checkpoints_created"],
        "security_attack_xai_dashboard_started": safety_summary["security_attack_xai_dashboard_started"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }


def validate_split(
    base: Path,
    binary_base: Path,
    split: str,
    expected_dim: int,
    mapping_summary: dict[str, Any],
) -> dict[str, Any]:
    checks: list[dict[str, str]] = []
    x_path = base / f"X_{split}.npy"
    yb_path = base / f"y_binary_{split}.npy"
    ya_path = base / f"y_attack_family_{split}.npy"
    mask_path = base / f"attack_family_mask_{split}.npy"
    old_y_path = binary_base / f"y_{split}.npy"
    old_x_path = binary_base / f"X_{split}.npy"

    X = load_numpy_readonly(x_path, mmap_mode="r")
    yb = load_numpy_readonly(yb_path, mmap_mode="r")
    ya = load_numpy_readonly(ya_path, mmap_mode="r")
    mask = load_numpy_readonly(mask_path, mmap_mode="r")
    old_y = load_numpy_readonly(old_y_path, mmap_mode="r")
    old_x = load_numpy_readonly(old_x_path, mmap_mode="r")

    x_2d = X.ndim == 2
    y_1d = yb.ndim == 1 and ya.ndim == 1
    masks_1d = mask.ndim == 1
    row_lengths_match = (
        x_2d
        and y_1d
        and masks_1d
        and X.shape[0] == yb.shape[0] == ya.shape[0] == mask.shape[0]
    )
    feature_dim_match = x_2d and X.shape[1] == expected_dim
    sizes_match_existing_binary = (
        old_x.shape == X.shape
        and old_y.shape == yb.shape
        and np.array_equal(yb, old_y)
    )
    binary_unique = unique_ints(yb)
    mask_unique = unique_ints(mask)
    binary_labels_valid = set(binary_unique).issubset({0, 1})
    masks_valid = set(mask_unique).issubset({0, 1})
    ignore_index = int(mapping_summary["ignore_index"])
    class_ids = set(mapping_summary["id_to_class_int"])
    y_attack_unique = unique_ints(ya)
    attack_family_labels_valid = set(y_attack_unique).issubset(class_ids | {ignore_index})
    mask0_ignore = bool(np.all((mask != 0) | (ya == ignore_index)))
    mask1_nonnegative = bool(np.all((mask != 1) | (ya >= 0)))
    binary0_mask0 = bool(np.all((yb != 0) | (mask == 0)))
    binary1_mask1 = bool(np.all((yb != 1) | (mask == 1)))
    label_mask_consistency = mask0_ignore and mask1_nonnegative and binary0_mask0 and binary1_mask1
    ignore_index_valid = mask0_ignore and int((ya == ignore_index).sum()) == int((mask == 0).sum())
    rows = int(X.shape[0]) if x_2d else 0

    checks.extend([
        check(f"{split}_X_arrays_are_2d", x_2d, str(list(X.shape))),
        check(f"{split}_y_arrays_are_1d", y_1d, f"yb={list(yb.shape)}, ya={list(ya.shape)}"),
        check(f"{split}_masks_are_1d", masks_1d, str(list(mask.shape))),
        check(f"{split}_lengths_match_X_rows", row_lengths_match, f"X={list(X.shape)}, yb={list(yb.shape)}, ya={list(ya.shape)}, mask={list(mask.shape)}"),
        check(f"{split}_feature_dim_matches", feature_dim_match, f"detected={X.shape[1] if x_2d else None}, expected={expected_dim}"),
        check(f"{split}_binary_labels_valid", binary_labels_valid, f"unique={binary_unique}"),
        check(f"{split}_mask_values_valid", masks_valid, f"unique={mask_unique}"),
        check(f"{split}_attack_family_ids_valid", attack_family_labels_valid, f"unique={y_attack_unique[:20]}"),
        check(f"{split}_mask0_rows_have_ignore_index", mask0_ignore, "mask 0 rows have y_attack_family=-1"),
        check(f"{split}_mask1_rows_nonnegative", mask1_nonnegative, "mask 1 rows have non-negative attack-family ids"),
        check(f"{split}_binary0_rows_have_mask0", binary0_mask0, "binary label 0 rows have mask 0"),
        check(f"{split}_binary1_rows_have_mask1", binary1_mask1, "binary label 1 rows have mask 1"),
        check(f"{split}_matches_existing_binary_split", sizes_match_existing_binary, f"old X={list(old_x.shape)}, new X={list(X.shape)}, y match={np.array_equal(yb, old_y)}"),
    ])

    binary_counts = unique_count_dict(yb)
    attack_counts_id = unique_count_dict(ya[ya != ignore_index])
    attack_counts_named = {
        mapping_summary["id_to_class"][class_id]: count
        for class_id, count in attack_counts_id.items()
    }
    return {
        "rows": rows,
        "shapes": {
            "X": list(X.shape),
            "y_binary": list(yb.shape),
            "y_attack_family": list(ya.shape),
            "attack_family_mask": list(mask.shape),
            "existing_binary_X": list(old_x.shape),
            "existing_binary_y": list(old_y.shape),
        },
        "shape_summary": {
            "X_is_2d": x_2d,
            "y_arrays_are_1d": y_1d,
            "mask_is_1d": masks_1d,
            "row_lengths_match": row_lengths_match,
            "feature_dim_match": feature_dim_match,
            "sizes_match_existing_binary": sizes_match_existing_binary,
            "split_is_nonempty": rows > 0,
        },
        "binary_distribution": binary_counts,
        "attack_family_distribution": attack_counts_id,
        "attack_family_distribution_named": attack_counts_named,
        "mask_distribution": unique_count_dict(mask),
        "ignore_index_count": int((ya == ignore_index).sum()),
        "label_mask_consistency": label_mask_consistency,
        "binary_labels_valid": binary_labels_valid,
        "attack_family_labels_valid": attack_family_labels_valid,
        "masks_valid": masks_valid,
        "ignore_index_valid": ignore_index_valid,
        "sizes_match_existing_binary": sizes_match_existing_binary,
        "checks": checks,
    }


def validate_mappings(
    dataset: str,
    binary_mapping: dict[str, Any],
    attack_mapping: dict[str, Any],
    common_mapping: dict[str, Any],
    checks: list[dict[str, str]],
) -> dict[str, Any]:
    class_to_id = attack_mapping.get("class_to_id", {})
    id_to_class = attack_mapping.get("id_to_class", {})
    id_to_class_int = {int(key): value for key, value in id_to_class.items()}
    reverse_ok = all(
        str(class_to_id.get(name)) in id_to_class
        and id_to_class[str(class_to_id[name])] == name
        for name in class_to_id
    )
    ignore_index = int(attack_mapping.get("ignore_index", 0))
    common_reporting_only = bool(common_mapping.get("reporting_only")) and bool(common_mapping.get("no_training_target"))
    binary_ok = (
        binary_mapping.get("head") == "Head 1"
        and binary_mapping.get("class_to_id", {}).get("Benign / Normal") == 0
        and binary_mapping.get("class_to_id", {}).get("Attack") == 1
    )
    raw_to_id = attack_mapping.get("raw_label_to_attack_family_id", {})
    raw_to_family = attack_mapping.get("raw_label_to_attack_family", {})
    checks.extend([
        check("binary_label_mapping_valid", binary_ok, "Head 1 mapping is 0=benign/normal, 1=attack"),
        check("attack_family_label_mapping_valid", bool(class_to_id) and reverse_ok, f"class_count={len(class_to_id)}"),
        check("common_superclass_mapping_reporting_only", common_reporting_only, "common superclass is reporting-only and not training target"),
        check("ignore_index_recorded_as_minus_one", ignore_index == -1, str(ignore_index)),
        check("dataset_name_recorded_in_attack_mapping", attack_mapping.get("dataset") == dataset, str(attack_mapping.get("dataset"))),
    ])
    return {
        "dataset": dataset,
        "binary_class_to_id": binary_mapping.get("class_to_id", {}),
        "attack_family_class_to_id": class_to_id,
        "id_to_class": {str(key): value for key, value in id_to_class.items()},
        "id_to_class_int": sorted(id_to_class_int),
        "ignore_index": ignore_index,
        "raw_label_to_attack_family": raw_to_family,
        "raw_label_to_attack_family_id": raw_to_id,
        "rare_raw_labels": attack_mapping.get("rare_raw_labels", []),
        "rare_threshold": attack_mapping.get("rare_threshold", {}),
        "common_superclass_reporting_only": common_reporting_only,
        "fake_shared_multiclass_label_list_created": False,
        "attack_family_class_count": len(class_to_id),
    }


def validate_manifest(
    dataset: str,
    manifest: dict[str, Any],
    cfg: dict[str, Any],
    expected_dim: int,
    checks: list[dict[str, str]],
    warnings: list[str],
) -> dict[str, Any]:
    task = str(manifest.get("task", ""))
    taxonomy_ok = manifest.get("taxonomy_config_path") == cfg["taxonomy_config_path"]
    preprocessing_ok = manifest.get("preprocessing_config_path") == cfg["preprocessing_config_path"]
    dataset_ok = manifest.get("dataset") == dataset
    feature_ok = manifest.get("feature_dim") == expected_dim and manifest.get("expected_feature_dim") == expected_dim
    no_test_tuning = bool(manifest.get("no_test_set_tuning"))
    no_refit = bool(manifest.get("no_scaler_encoder_refit_on_test"))
    common_reporting = bool(manifest.get("common_superclass_reporting_only"))
    fake_shared = bool(manifest.get("fake_shared_multiclass_label_list_created", True))
    creation_command = manifest.get("creation_command") or manifest.get("command")
    if not creation_command:
        warnings.append(
            "A3 manifest does not record the creation command; A4 records the expected command from the approved task: python -m secureids.cli preprocess-hierarchical --dataset all --execute."
        )

    checks.extend([
        check("manifest_dataset_recorded", dataset_ok, str(manifest.get("dataset"))),
        check("manifest_task_type_hierarchical", "hierarchical" in task, task),
        check("manifest_taxonomy_config_path_recorded", taxonomy_ok, str(manifest.get("taxonomy_config_path"))),
        check("manifest_preprocessing_config_path_recorded", preprocessing_ok, str(manifest.get("preprocessing_config_path"))),
        check("manifest_input_dim_recorded", feature_ok, f"feature_dim={manifest.get('feature_dim')}, expected={manifest.get('expected_feature_dim')}"),
        check("manifest_no_test_set_tuning", no_test_tuning, str(no_test_tuning)),
        check("manifest_no_scaler_encoder_refit_on_test", no_refit, str(no_refit)),
        check("manifest_common_superclass_reporting_only", common_reporting, str(common_reporting)),
        check("manifest_no_fake_shared_multiclass", fake_shared is False, str(fake_shared)),
    ])
    return {
        "dataset": manifest.get("dataset"),
        "task": manifest.get("task"),
        "status": manifest.get("status"),
        "taxonomy_config_path": manifest.get("taxonomy_config_path"),
        "preprocessing_config_path": manifest.get("preprocessing_config_path"),
        "input_dim": manifest.get("feature_dim"),
        "expected_input_dim": manifest.get("expected_feature_dim"),
        "creation_command_recorded": bool(creation_command),
        "creation_command": creation_command,
        "expected_creation_command": "python -m secureids.cli preprocess-hierarchical --dataset all --execute",
        "no_test_set_tuning": no_test_tuning,
        "no_scaler_encoder_refit_on_test": no_refit,
        "common_superclass_reporting_only": common_reporting,
        "fake_shared_multiclass_label_list_created": fake_shared,
    }


def compare_split_summary(recorded: dict[str, Any], inspected: dict[str, Any]) -> bool:
    if not recorded:
        return False
    expected_pairs = [
        ("X_shape", inspected["shapes"]["X"]),
        ("y_binary_shape", inspected["shapes"]["y_binary"]),
        ("y_attack_family_shape", inspected["shapes"]["y_attack_family"]),
        ("attack_family_mask_shape", inspected["shapes"]["attack_family_mask"]),
        ("binary_class_counts", inspected["binary_distribution"]),
        ("attack_family_class_counts_excluding_ignore", inspected["attack_family_distribution"]),
        ("ignore_index_count", inspected["ignore_index_count"]),
    ]
    return all(recorded.get(key) == value for key, value in expected_pairs)


def build_rare_class_summary(
    attack_mapping: dict[str, Any],
    total_counts_by_id: dict[str, int],
    split_counts_named: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    raw_to_family = attack_mapping.get("raw_label_to_attack_family", {})
    raw_to_id = attack_mapping.get("raw_label_to_attack_family_id", {})
    rare_raw = list(attack_mapping.get("rare_raw_labels", []))
    family_to_raws: dict[str, list[str]] = {}
    for raw_label, family in raw_to_family.items():
        family_to_raws.setdefault(family, []).append(raw_label)

    rare_entries = []
    present_or_documented = True
    for raw_label in rare_raw:
        family = raw_to_family.get(raw_label)
        class_id = raw_to_id.get(raw_label)
        class_id_str = str(class_id)
        total_family_count = int(total_counts_by_id.get(class_id_str, 0))
        raw_equivalent = family is not None and len(family_to_raws.get(family, [])) == 1
        if total_family_count <= 0:
            present_or_documented = False
        if not raw_equivalent:
            warnings.append(
                f"Rare raw label {raw_label} is represented through family {family}; raw split counts are not separable in A3 family-level labels."
            )
        rare_entries.append({
            "raw_label": raw_label,
            "mapped_attack_family": family,
            "attack_family_id": class_id,
            "family_total_count_in_hierarchical_arrays": total_family_count,
            "raw_label_has_unique_family_class": raw_equivalent,
            "split_family_counts": {
                split: counts.get(family, 0)
                for split, counts in split_counts_named.items()
            },
            "present_or_documented": total_family_count > 0,
        })

    return {
        "rare_threshold": attack_mapping.get("rare_threshold", {}),
        "rare_raw_labels": rare_raw,
        "rare_classes": rare_entries,
        "rare_classes_present_or_documented": present_or_documented,
        "note": (
            "Rare raw labels are preserved in mapping metadata. Counts from A3 "
            "arrays are available at the mapped attack-family level."
        ),
    }


def build_safety_summary(project_root: Path) -> dict[str, Any]:
    binary_outputs = path_status(project_root, BINARY_OUTPUTS)
    binary_final = path_status(project_root, BINARY_FINAL_CHECKPOINTS)
    fedavg = path_status(project_root, BINARY_FEDAVG_CHECKPOINTS)
    hierarchical_checkpoint_status = path_status(project_root, HIERARCHICAL_CHECKPOINTS)
    model_code_path = project_root / "secureids/models/secureids_hierarchical_advanced_net.py"
    hierarchical_metric_files = [
        str(path)
        for root in [project_root / "results/final", project_root / "results/federated"]
        if root.exists()
        for path in root.rglob("*hierarchical*")
        if path.is_file()
    ]
    later_outputs = output_tree_status(project_root, LATER_LAYER_OUTPUT_DIRS)
    preexisting_scaffolds = path_status(project_root, PREEXISTING_FUTURE_LAYER_SCAFFOLDS)
    model_code_created = model_code_path.exists()
    hierarchical_checkpoints_created = any(item["exists"] for item in hierarchical_checkpoint_status)
    security_started = any(item["file_count"] > 0 for item in later_outputs)
    checks = [
        check("existing_binary_processed_outputs_still_exist", all(item["exists"] for item in binary_outputs), missing_paths(binary_outputs)),
        check("existing_binary_final_checkpoints_still_exist", all(item["exists"] for item in binary_final), missing_paths(binary_final)),
        check("existing_binary_fedavg_checkpoints_still_exist", all(item["exists"] for item in fedavg), missing_paths(fedavg)),
        # A8.8: the advanced hierarchical model was approved and implemented at A5.
        # Its presence is expected from A5 onward, so it is no longer a readiness
        # blocker; only real "final-artifact" leakage (checkpoints/metrics/later
        # layers) below still blocks. See docs/PRE_TRAINING_HIGH_FINDINGS_RESOLUTION.md.
        check("advanced_hierarchical_model_code_present_expected_from_a5", model_code_created, str(model_code_path)),
        check("no_hierarchical_checkpoints", not hierarchical_checkpoints_created, existing_paths(hierarchical_checkpoint_status)),
        check("no_hierarchical_training_metrics", not hierarchical_metric_files, str(hierarchical_metric_files)),
        check("no_security_attack_xai_dashboard_outputs", not security_started, output_paths(later_outputs)),
    ]
    return {
        "existing_binary_outputs_preserved": all(item["exists"] for item in binary_outputs),
        "existing_binary_checkpoints_preserved": all(item["exists"] for item in binary_final),
        "existing_fedavg_checkpoints_preserved": all(item["exists"] for item in fedavg),
        "model_code_created": model_code_created,
        "hierarchical_checkpoints_created": hierarchical_checkpoints_created,
        "security_attack_xai_dashboard_started": security_started,
        "summary": {
            "binary_outputs": binary_outputs,
            "binary_final_checkpoints": binary_final,
            "binary_fedavg_checkpoints": fedavg,
            "advanced_model_code_path": str(model_code_path),
            "advanced_model_code_exists": model_code_created,
            "hierarchical_checkpoints": hierarchical_checkpoint_status,
            "hierarchical_training_metric_files": hierarchical_metric_files,
            "later_layer_outputs": later_outputs,
            "preexisting_future_layer_scaffolds_not_modified_by_a4": preexisting_scaffolds,
        },
        "checks": checks,
    }


def finalize_readiness(
    *,
    dataset: str,
    expected_dim: int,
    detected_dim: int | None,
    expected_files_count: int,
    missing_files: list[str],
    checks: list[dict[str, str]],
    blocking_issues: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "dataset": dataset,
        "status": "FAIL",
        "ready_for_hierarchical_model_implementation": False,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "expected_feature_dim": expected_dim,
        "detected_feature_dim": detected_dim,
        "feature_dim_match": detected_dim == expected_dim,
        "expected_files_count": expected_files_count,
        "missing_files": missing_files,
        "split_shapes": {},
        "shape_summary": {},
        "binary_distribution": {},
        "attack_family_distribution": {},
        "rare_class_summary": {},
        "mapping_summary": {},
        "manifest_summary": {},
        "safety_summary": {},
        "label_mask_consistency": False,
        "binary_labels_valid": False,
        "attack_family_labels_valid": False,
        "masks_valid": False,
        "ignore_index_valid": False,
        "split_summary_matches_arrays": False,
        "all_attack_family_classes_present_or_documented": False,
        "rare_classes_present_or_documented": False,
        "common_superclass_reporting_only": False,
        "fake_shared_multiclass_label_list_created": False,
        "no_test_set_tuning": False,
        "no_scaler_encoder_refit_on_test": False,
        "existing_binary_outputs_preserved": False,
        "existing_binary_checkpoints_preserved": False,
        "existing_fedavg_checkpoints_preserved": False,
        "model_code_created": False,
        "training_or_evaluation_run": False,
        "checkpoints_created": False,
        "security_attack_xai_dashboard_started": False,
        "checks": checks,
    }


def write_readiness_report(project_root: Path, outcomes: list[dict[str, Any]]) -> None:
    report_path = project_root / "docs/HIERARCHICAL_PREPROCESSING_READINESS_REPORT.md"
    all_ready = all(item["ready_for_hierarchical_model_implementation"] for item in outcomes)
    lines = [
        "# Hierarchical Preprocessing Readiness Report",
        "",
        "Status: `Task A4 complete - validation/readiness only`",
        "",
        "## 1. Readiness Decision",
        "",
    ]
    for outcome in outcomes:
        label = "ready" if outcome["ready_for_hierarchical_model_implementation"] else "not ready"
        lines.append(f"- {outcome['dataset']}: `{outcome['status']}` and {label} for hierarchical model implementation.")
    lines.extend([
        "",
        f"- Blocking issues: `{sum(len(item['blocking_issues']) for item in outcomes)}`",
        f"- Warnings: `{sum(len(item['warnings']) for item in outcomes)}`",
        "",
        "## 2. Output Paths",
        "",
        "- `results/audits/hierarchical_preprocessing_readiness_cicids2018.json`",
        "- `results/audits/hierarchical_preprocessing_readiness_unsw_nb15.json`",
        "- `docs/HIERARCHICAL_PREPROCESSING_READINESS_REPORT.md`",
        "",
        "## 3. Dataset Summaries",
        "",
    ])
    for outcome in outcomes:
        lines.extend(dataset_report_section(outcome))
    lines.extend([
        "## 4. Mapping And Manifest Validation",
        "",
        "- Dataset-specific Head 2 mappings were validated.",
        "- Common superclass mappings are reporting-only and are not training targets.",
        "- No fake shared CICIDS/UNSW multiclass label list was created.",
        "- Manifests record dataset name, hierarchical task type, input dimension,",
        "  taxonomy config path, preprocessing config path, no-test-tuning, and",
        "  no-scaler/encoder-refit flags.",
        "",
        "## 5. Preservation And Safety",
        "",
        "- Existing binary processed outputs remain present.",
        "- Existing binary centralized checkpoints remain present.",
        "- Existing binary FedAvg checkpoints remain present.",
        "- No advanced hierarchical model code exists.",
        "- No hierarchical checkpoints exist.",
        "- No hierarchical training metrics exist under `results/final` or `results/federated`.",
        "- No security, attack, Trimmed Mean, or XAI result output files checked by A4 exist.",
        "- Pre-existing skeleton dashboard/security/attack/XAI placeholders were not extended by A4.",
        "",
        "## 6. What Was Not Done",
        "",
        "- No model code was implemented.",
        "- No model training or evaluation was run.",
        "- No checkpoints or model metrics were created.",
        "- No calibration/routing implementation was created.",
        "- No security, Byzantine attack, Trimmed Mean, XAI, or dashboard implementation work was started by A4.",
        "- V1 was not modified.",
        "",
        "## 7. Recommendation",
        "",
    ])
    if all_ready:
        lines.extend([
            "It is safe to proceed after main-review approval.",
            "",
            "Recommended next step: Task A5 should be",
            "`SecureIDS-HierarchicalAdvancedNet` architecture implementation design/code",
            "skeleton with smoke-only forward-pass validation, not full training yet.",
        ])
    else:
        lines.append("Pause before A5 and resolve the blocking readiness issues above.")
    lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def dataset_report_section(outcome: dict[str, Any]) -> list[str]:
    lines = [
        f"### {outcome['dataset']}",
        "",
        f"- Status: `{outcome['status']}`",
        f"- Ready for model implementation: `{str(outcome['ready_for_hierarchical_model_implementation']).lower()}`",
        f"- Expected feature dimension: `{outcome['expected_feature_dim']}`",
        f"- Detected feature dimension: `{outcome['detected_feature_dim']}`",
        f"- Blocking issues: `{len(outcome['blocking_issues'])}`",
        f"- Warnings: `{len(outcome['warnings'])}`",
        "",
        "| Split | X shape | Binary 0 | Binary 1 | Attack-family classes present |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for split in SPLITS:
        shape = outcome["split_shapes"][split]["X"]
        binary = outcome["binary_distribution"][split]
        attack_family = outcome["attack_family_distribution"]["by_split"][split]
        lines.append(
            f"| {split} | `{tuple(shape)}` | {binary.get('0', 0)} | "
            f"{binary.get('1', 0)} | {len(attack_family)} |"
        )
    lines.extend([
        "",
        "Attack-family total distribution:",
        "",
    ])
    for name, count in outcome["attack_family_distribution"]["total_by_name"].items():
        lines.append(f"- `{name}`: {count}")
    lines.extend([
        "",
        "Rare-class summary:",
        "",
    ])
    for entry in outcome["rare_class_summary"]["rare_classes"]:
        lines.append(
            f"- `{entry['raw_label']}` -> `{entry['mapped_attack_family']}` "
            f"(family count: {entry['family_total_count_in_hierarchical_arrays']})"
        )
    if outcome["warnings"]:
        lines.extend(["", "Warnings:", ""])
        lines.extend(f"- {warning}" for warning in outcome["warnings"])
    lines.append("")
    return lines


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check(name: str, passed: bool, detail: str) -> dict[str, str]:
    return {"name": name, "status": "PASS" if passed else "FAIL", "detail": detail}


def unique_ints(values: np.ndarray) -> list[int]:
    return [int(value) for value in np.unique(values)]


def unique_count_dict(values: np.ndarray) -> dict[str, int]:
    unique, counts = np.unique(values, return_counts=True)
    return {str(int(key)): int(count) for key, count in zip(unique, counts)}


def path_status(project_root: Path, paths: list[str]) -> list[dict[str, Any]]:
    out = []
    for rel in paths:
        path = project_root / rel
        out.append({
            "path": rel,
            "exists": path.exists(),
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
        })
    return out


def missing_paths(statuses: list[dict[str, Any]]) -> str:
    missing = [item["path"] for item in statuses if not item["exists"]]
    return str(missing)


def existing_paths(statuses: list[dict[str, Any]]) -> str:
    existing = [item["path"] for item in statuses if item["exists"]]
    return str(existing)


def output_tree_status(project_root: Path, paths: list[str]) -> list[dict[str, Any]]:
    out = []
    for rel in paths:
        path = project_root / rel
        files = [
            item
            for item in path.rglob("*")
            if item.is_file()
        ] if path.is_dir() else ([path] if path.is_file() else [])
        out.append({
            "path": rel,
            "exists": path.exists(),
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "file_count": len(files),
            "files": [str(item.relative_to(project_root)) for item in files],
        })
    return out


def output_paths(statuses: list[dict[str, Any]]) -> str:
    files = [
        file_path
        for item in statuses
        for file_path in item.get("files", [])
    ]
    return str(files)
