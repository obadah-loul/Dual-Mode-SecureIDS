"""Train-only hierarchical class-weight strategy lock for Task A8.5.

This module computes class-weight previews only. It reads train labels and the
train attack-family mask, writes audit JSONs and a strategy document, and never
trains, evaluates, saves checkpoints, or writes final metrics.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from secureids.preprocessing.artifacts import save_json, utc_timestamp
from secureids.training.hierarchical_config import (
    HierarchicalTrainingConfig,
    HierarchicalTrainingConfigError,
    load_hierarchical_training_config,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHUNK_SIZE = 1_000_000
WEIGHT_CAP = 10.0
EXPECTED_BINARY_STRATEGY = {
    "enabled": True,
    "source_split": "train",
    "method": "balanced",
    "normalize_mean": True,
    "max_weight": WEIGHT_CAP,
    "use_validation_labels": False,
    "use_test_labels": False,
}
EXPECTED_ATTACK_STRATEGY = {
    "enabled": True,
    "source_split": "train_attack_rows_only",
    "method": "sqrt_inverse_frequency",
    "normalize_mean": True,
    "max_weight": WEIGHT_CAP,
    "use_validation_labels": False,
    "use_test_labels": False,
    "oversampling": False,
}

DATASET_SPECS = {
    "cicids2018": {
        "short": "cicids",
        "config": "configs/training/cicids2018_hierarchical.yaml",
        "audit_json": "results/audits/hierarchical_class_weight_strategy_cicids2018.json",
    },
    "unsw_nb15": {
        "short": "unsw",
        "config": "configs/training/unsw_nb15_hierarchical.yaml",
        "audit_json": "results/audits/hierarchical_class_weight_strategy_unsw_nb15.json",
    },
}
STRATEGY_DOC = "docs/HIERARCHICAL_CLASS_WEIGHT_STRATEGY.md"


class HierarchicalClassWeightStrategyError(RuntimeError):
    """Raised when the A8.5 class-weight strategy cannot be locked safely."""


def _round(value: float) -> float:
    return round(float(value), 6)


def _normalize_mean(weights: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    mean_before = float(np.mean(weights))
    if not math.isfinite(mean_before) or mean_before <= 0.0:
        raise HierarchicalClassWeightStrategyError(
            f"Cannot mean-normalize weights with mean={mean_before!r}."
        )
    normalized = weights / mean_before
    return normalized, {
        "applied": True,
        "method": "arithmetic_mean_over_classes",
        "mean_before_normalization": _round(mean_before),
        "mean_after_normalization_before_cap": _round(float(np.mean(normalized))),
    }


def _cap_weights(weights: np.ndarray, cap: float) -> tuple[np.ndarray, bool]:
    capped = np.minimum(weights, float(cap))
    return capped, bool(np.any(capped < weights))


def compute_balanced_binary_weights(
    counts: dict[str, int],
    max_weight: float = WEIGHT_CAP,
) -> dict[str, Any]:
    """Compute mean-normalized balanced binary class weights."""

    class_counts = np.asarray([int(counts["0"]), int(counts["1"])], dtype=np.float64)
    if np.any(class_counts <= 0):
        raise HierarchicalClassWeightStrategyError(
            f"Binary class counts must be nonzero, got {counts}."
        )
    total = float(np.sum(class_counts))
    raw = total / (2.0 * class_counts)
    normalized, normalization = _normalize_mean(raw)
    final, cap_applied = _cap_weights(normalized, max_weight)
    pos_weight_equivalent = float(final[1] / final[0])
    return {
        "raw_balanced_weights": {"0": _round(raw[0]), "1": _round(raw[1])},
        "mean_normalized_weights": {
            "0": _round(normalized[0]),
            "1": _round(normalized[1]),
        },
        "final_weights": {"0": _round(final[0]), "1": _round(final[1])},
        "bce_pos_weight_equivalent": _round(pos_weight_equivalent),
        "max_weight": float(max_weight),
        "cap_applied": cap_applied,
        "normalization": {
            **normalization,
            "mean_after_cap": _round(float(np.mean(final))),
        },
    }


def compute_attack_family_weights(
    counts_by_id: dict[str, int],
    class_names: list[str],
    max_weight: float = WEIGHT_CAP,
) -> dict[str, Any]:
    """Compute raw comparison and final sqrt-normalized-capped attack weights."""

    counts = np.asarray(
        [int(counts_by_id[str(index)]) for index in range(len(class_names))],
        dtype=np.float64,
    )
    if np.any(counts <= 0):
        zero_classes = [
            class_names[index] for index, value in enumerate(counts.tolist()) if value <= 0
        ]
        raise HierarchicalClassWeightStrategyError(
            "All Head 2 classes need nonzero train support. "
            f"Missing: {zero_classes}"
        )

    total = float(np.sum(counts))
    class_count = float(len(class_names))
    raw_inverse = total / (class_count * counts)
    sqrt_inverse = np.sqrt(raw_inverse)
    normalized, normalization = _normalize_mean(sqrt_inverse)
    final, cap_applied = _cap_weights(normalized, max_weight)

    by_class: dict[str, Any] = {}
    for index, name in enumerate(class_names):
        by_class[name] = {
            "class_id": index,
            "train_support": int(counts[index]),
            "raw_inverse_frequency_weight_for_comparison": _round(raw_inverse[index]),
            "sqrt_inverse_frequency_before_normalization": _round(sqrt_inverse[index]),
            "sqrt_inverse_frequency_mean_normalized": _round(normalized[index]),
            "final_weight": _round(final[index]),
        }

    finite = bool(np.all(np.isfinite(final)))
    positive = bool(np.all(final > 0.0))
    return {
        "train_attack_rows": int(total),
        "raw_inverse_frequency_weight_preview_for_comparison": {
            name: by_class[name]["raw_inverse_frequency_weight_for_comparison"]
            for name in class_names
        },
        "sqrt_inverse_frequency_before_normalization": {
            name: by_class[name]["sqrt_inverse_frequency_before_normalization"]
            for name in class_names
        },
        "final_weights": {name: by_class[name]["final_weight"] for name in class_names},
        "by_class": by_class,
        "normalization": {
            **normalization,
            "mean_after_cap": _round(float(np.mean(final))),
        },
        "max_final_attack_weight": _round(float(np.max(final))),
        "min_final_attack_weight": _round(float(np.min(final))),
        "weight_cap": float(max_weight),
        "cap_applied": cap_applied,
        "all_final_weights_finite": finite,
        "all_final_weights_positive": positive,
    }


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise HierarchicalClassWeightStrategyError(f"Expected JSON object in {path}.")
    return payload


def _class_names(mapping: dict[str, Any], attack_head_dim: int) -> list[str]:
    id_to_class = mapping.get("id_to_class", {})
    names: list[str] = []
    for index in range(int(attack_head_dim)):
        if not isinstance(id_to_class, dict) or str(index) not in id_to_class:
            raise HierarchicalClassWeightStrategyError(
                f"Mapping is missing id_to_class entry for class {index}."
            )
        names.append(str(id_to_class[str(index)]))
    return names


def _count_train_labels(
    data_dir: Path,
    attack_head_dim: int,
) -> tuple[dict[str, int], dict[str, int], dict[str, Any]]:
    y_binary = np.load(data_dir / "y_binary_train.npy", mmap_mode="r")
    y_attack = np.load(data_dir / "y_attack_family_train.npy", mmap_mode="r")
    mask = np.load(data_dir / "attack_family_mask_train.npy", mmap_mode="r")
    try:
        if y_binary.ndim != 1 or y_attack.ndim != 1 or mask.ndim != 1:
            raise HierarchicalClassWeightStrategyError("Train labels/mask must be 1D.")
        if y_binary.shape[0] != y_attack.shape[0] or y_binary.shape[0] != mask.shape[0]:
            raise HierarchicalClassWeightStrategyError("Train label/mask lengths do not match.")

        binary_counts = np.zeros(2, dtype=np.int64)
        attack_counts = np.zeros(int(attack_head_dim), dtype=np.int64)
        invalid_binary = 0
        invalid_mask = 0
        invalid_attack_labels = 0
        attack_rows_seen = 0
        row_count = int(y_binary.shape[0])

        for start in range(0, row_count, CHUNK_SIZE):
            end = min(start + CHUNK_SIZE, row_count)
            yb = np.asarray(y_binary[start:end]).reshape(-1).astype(np.int64, copy=False)
            ya = np.asarray(y_attack[start:end]).reshape(-1).astype(np.int64, copy=False)
            m = np.asarray(mask[start:end]).reshape(-1).astype(np.int64, copy=False)

            binary_valid = np.isin(yb, [0, 1])
            mask_valid = np.isin(m, [0, 1])
            invalid_binary += int(np.sum(~binary_valid))
            invalid_mask += int(np.sum(~mask_valid))
            binary_counts += np.bincount(yb[binary_valid], minlength=2)[:2]

            attack_rows = m == 1
            attack_rows_seen += int(np.sum(attack_rows))
            valid_attack_label = (ya >= 0) & (ya < int(attack_head_dim))
            invalid_attack_labels += int(np.sum(attack_rows & ~valid_attack_label))
            valid_attack_rows = attack_rows & valid_attack_label
            if bool(np.any(valid_attack_rows)):
                attack_counts += np.bincount(
                    ya[valid_attack_rows],
                    minlength=int(attack_head_dim),
                )[: int(attack_head_dim)]

        diagnostics = {
            "source_files": [
                str(data_dir / "y_binary_train.npy"),
                str(data_dir / "y_attack_family_train.npy"),
                str(data_dir / "attack_family_mask_train.npy"),
            ],
            "validation_files_read": [],
            "test_files_read": [],
            "train_rows": row_count,
            "attack_rows_seen": attack_rows_seen,
            "invalid_binary_label_count": invalid_binary,
            "invalid_mask_value_count": invalid_mask,
            "invalid_attack_label_count": invalid_attack_labels,
        }
        if invalid_binary or invalid_mask or invalid_attack_labels:
            raise HierarchicalClassWeightStrategyError(
                f"Invalid train label/mask values: {diagnostics}"
            )
        return (
            {"0": int(binary_counts[0]), "1": int(binary_counts[1])},
            {
                str(index): int(count)
                for index, count in enumerate(attack_counts.tolist())
            },
            diagnostics,
        )
    finally:
        for array in (y_binary, y_attack, mask):
            mmap = getattr(array, "_mmap", None)
            if mmap is not None:
                mmap.close()


def _config_strategy_issues(config: HierarchicalTrainingConfig) -> list[str]:
    issues: list[str] = []
    class_weights = config.raw.get("class_weights", {})
    binary = class_weights.get("binary") if isinstance(class_weights, dict) else None
    attack = class_weights.get("attack_family") if isinstance(class_weights, dict) else None
    if binary != EXPECTED_BINARY_STRATEGY:
        issues.append("Config class_weights.binary does not match the A8.5 locked strategy.")
    if attack != EXPECTED_ATTACK_STRATEGY:
        issues.append("Config class_weights.attack_family does not match the A8.5 locked strategy.")
    imbalance = config.raw.get("class_imbalance", {})
    if imbalance.get("allow_test_based_weights") is not False:
        issues.append("class_imbalance.allow_test_based_weights must be false.")
    if imbalance.get("oversampling_enabled") is not False:
        issues.append("class_imbalance.oversampling_enabled must be false.")
    return issues


def _rare_summary(
    config: HierarchicalTrainingConfig,
    class_to_id: dict[str, Any],
    attack_counts: dict[str, int],
    final_weights: dict[str, float],
) -> dict[str, Any]:
    rare_names = [str(name) for name in config.raw.get("rare_classes", [])]
    rare_entries: list[dict[str, Any]] = []
    non_rare_weights = [
        float(weight)
        for name, weight in final_weights.items()
        if name not in set(rare_names)
    ]
    rare_weights: list[float] = []
    most_common_id = max(attack_counts, key=lambda key: int(attack_counts[key]))
    id_to_class = {int(value): key for key, value in class_to_id.items()}
    most_common_name = str(id_to_class[int(most_common_id)])
    most_common_weight = float(final_weights[most_common_name])

    for name in rare_names:
        class_id = class_to_id.get(name)
        if class_id is None:
            rare_entries.append(
                {
                    "class_name": name,
                    "class_id": None,
                    "train_support": None,
                    "final_weight": None,
                    "higher_than_most_common_class": False,
                }
            )
            continue
        final_weight = float(final_weights[name])
        rare_weights.append(final_weight)
        rare_entries.append(
            {
                "class_name": name,
                "class_id": int(class_id),
                "train_support": int(attack_counts[str(int(class_id))]),
                "final_weight": _round(final_weight),
                "higher_than_most_common_class": bool(final_weight > most_common_weight),
            }
        )

    rare_mean = float(np.mean(rare_weights)) if rare_weights else 0.0
    non_rare_mean = float(np.mean(non_rare_weights)) if non_rare_weights else 0.0
    return {
        "rare_classes": rare_entries,
        "most_common_class": {
            "class_name": most_common_name,
            "train_support": int(attack_counts[str(int(most_common_id))]),
            "final_weight": _round(most_common_weight),
        },
        "rare_mean_final_weight": _round(rare_mean),
        "non_rare_mean_final_weight": _round(non_rare_mean),
        "rare_mean_higher_than_non_rare_mean": bool(rare_mean > non_rare_mean),
        "all_rare_weights_within_cap": all(
            float(entry["final_weight"] or 0.0) <= WEIGHT_CAP for entry in rare_entries
        ),
    }


def _no_fake_results_check(root: Path) -> dict[str, Any]:
    final_hierarchical_checkpoints = {
        "models/final/final_cicids_hierarchical.pt": (
            root / "models/final/final_cicids_hierarchical.pt"
        ).exists(),
        "models/final/final_unsw_hierarchical.pt": (
            root / "models/final/final_unsw_hierarchical.pt"
        ).exists(),
        "models/federated/fedavg_cicids_hierarchical.pt": (
            root / "models/federated/fedavg_cicids_hierarchical.pt"
        ).exists(),
        "models/federated/fedavg_unsw_hierarchical.pt": (
            root / "models/federated/fedavg_unsw_hierarchical.pt"
        ).exists(),
    }
    final_metric_files = [
        str(path)
        for path in (root / "results/final/hierarchical").rglob("*")
        if path.is_file()
    ] if (root / "results/final/hierarchical").exists() else []
    binary_artifacts = {
        "models/final/final_cicids_binary.pt": (
            root / "models/final/final_cicids_binary.pt"
        ).exists(),
        "models/final/final_unsw_binary.pt": (
            root / "models/final/final_unsw_binary.pt"
        ).exists(),
        "models/federated/fedavg_cicids_binary.pt": (
            root / "models/federated/fedavg_cicids_binary.pt"
        ).exists(),
        "models/federated/fedavg_unsw_binary.pt": (
            root / "models/federated/fedavg_unsw_binary.pt"
        ).exists(),
        "results/final/centralized/cicids_test_metrics.json": (
            root / "results/final/centralized/cicids_test_metrics.json"
        ).exists(),
        "results/final/centralized/unsw_test_metrics.json": (
            root / "results/final/centralized/unsw_test_metrics.json"
        ).exists(),
    }
    return {
        "full_training_run": False,
        "model_evaluation_run": False,
        "final_checkpoints_created": False,
        "final_metrics_created": False,
        "final_hierarchical_checkpoints_exist": final_hierarchical_checkpoints,
        "final_hierarchical_metric_files": final_metric_files,
        "fedavg_security_attack_xai_dashboard_started": False,
        "validation_labels_used_for_weights": False,
        "test_labels_used_for_weights": False,
        "binary_baseline_artifacts_preserved": binary_artifacts,
    }


def _build_dataset_audit(dataset: str, root: Path) -> dict[str, Any]:
    spec = DATASET_SPECS[dataset]
    config = load_hierarchical_training_config(root / spec["config"], project_root=root)
    data_dir = config.resolve(config.hierarchical_data_dir)
    mapping = _load_json(config.resolve(config.attack_family_label_mapping_path))
    class_to_id = mapping.get("class_to_id", {})
    if not isinstance(class_to_id, dict):
        raise HierarchicalClassWeightStrategyError("attack_family mapping missing class_to_id.")
    class_names = _class_names(mapping, config.attack_head_dim)

    blocking_issues = _config_strategy_issues(config)
    warnings: list[str] = []
    binary_counts, attack_counts, read_diagnostics = _count_train_labels(
        data_dir,
        attack_head_dim=config.attack_head_dim,
    )
    binary_preview = compute_balanced_binary_weights(binary_counts, max_weight=WEIGHT_CAP)
    attack_preview = compute_attack_family_weights(
        attack_counts,
        class_names,
        max_weight=WEIGHT_CAP,
    )
    rare_summary = _rare_summary(
        config,
        class_to_id,
        attack_counts,
        attack_preview["final_weights"],
    )

    if not rare_summary["rare_mean_higher_than_non_rare_mean"]:
        warnings.append("Rare-class mean final weight is not higher than non-rare mean.")
    if not rare_summary["all_rare_weights_within_cap"]:
        blocking_issues.append("One or more rare-class final weights exceed the cap.")
    if attack_preview["max_final_attack_weight"] > WEIGHT_CAP:
        blocking_issues.append("Final attack weight exceeds configured cap.")
    if not attack_preview["all_final_weights_finite"]:
        blocking_issues.append("Final attack weights are not all finite.")
    if not attack_preview["all_final_weights_positive"]:
        blocking_issues.append("Final attack weights are not all positive.")
    if any(int(value) == 0 for value in attack_counts.values()):
        blocking_issues.append("One or more Head 2 classes have zero train support.")

    no_fake = _no_fake_results_check(root)
    if any(no_fake["final_hierarchical_checkpoints_exist"].values()):
        blocking_issues.append("A final hierarchical checkpoint already exists.")
    if no_fake["final_hierarchical_metric_files"]:
        blocking_issues.append("Final hierarchical metric files already exist.")
    if not all(no_fake["binary_baseline_artifacts_preserved"].values()):
        blocking_issues.append("One or more binary baseline artifacts are missing.")

    status = "PASS" if not blocking_issues else "BLOCKED"
    return {
        "schema_version": "task_a8_5_hierarchical_class_weight_strategy_v1",
        "created_at_utc": utc_timestamp(),
        "dataset": dataset,
        "status": status,
        "strategy_locked": status == "PASS",
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "binary_counts_train_only": binary_counts,
        "binary_weight_strategy": EXPECTED_BINARY_STRATEGY,
        "binary_weights_preview": binary_preview,
        "attack_family_counts_train_attack_rows_only": {
            class_names[index]: int(attack_counts[str(index)])
            for index in range(len(class_names))
        },
        "raw_inverse_frequency_weight_preview_for_comparison": attack_preview[
            "raw_inverse_frequency_weight_preview_for_comparison"
        ],
        "final_attack_weight_strategy": EXPECTED_ATTACK_STRATEGY,
        "final_attack_weights_preview": attack_preview["final_weights"],
        "max_final_attack_weight": attack_preview["max_final_attack_weight"],
        "min_final_attack_weight": attack_preview["min_final_attack_weight"],
        "weight_cap": WEIGHT_CAP,
        "normalization": attack_preview["normalization"],
        "rare_class_weight_summary": rare_summary,
        "validation_labels_used": False,
        "test_labels_used": False,
        "oversampling_enabled": False,
        "safe_for_full_training": status == "PASS",
        "train_only_read_diagnostics": read_diagnostics,
        "no_fake_results_check": no_fake,
    }


def build_train_only_class_weights(
    dataset: str,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Build train-only Head 1 / Head 2 class weights aligned to class ids.

    Returns the locked A8.5 weights ready to pass into
    ``compute_hierarchical_loss`` for the real trainer, readiness, and smoke:

    - ``binary_pos_weight``: scalar BCE positive-class weight for Head 1
      (balanced, mean-normalized, capped final-weight ratio ``w1 / w0``).
    - ``attack_class_weights``: a length-``attack_head_dim`` list ordered by
      class id 0..N-1 (so index ``i`` aligns with ``id_to_class[str(i)]``),
      using sqrt inverse-frequency, mean-normalized, capped at ``WEIGHT_CAP``.

    Only train labels are read; validation and test labels are never opened.
    """

    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    canonical = _normalize_dataset_selection(dataset)
    if len(canonical) != 1:
        raise HierarchicalClassWeightStrategyError(
            "build_train_only_class_weights requires a single dataset, got "
            f"{dataset!r}."
        )
    name = canonical[0]
    spec = DATASET_SPECS[name]
    config = load_hierarchical_training_config(root / spec["config"], project_root=root)
    data_dir = config.resolve(config.hierarchical_data_dir)
    mapping = _load_json(config.resolve(config.attack_family_label_mapping_path))
    class_names = _class_names(mapping, config.attack_head_dim)

    binary_counts, attack_counts, read_diagnostics = _count_train_labels(
        data_dir,
        attack_head_dim=config.attack_head_dim,
    )
    binary_preview = compute_balanced_binary_weights(binary_counts, max_weight=WEIGHT_CAP)
    attack_preview = compute_attack_family_weights(
        attack_counts,
        class_names,
        max_weight=WEIGHT_CAP,
    )
    attack_class_weights = [
        float(attack_preview["final_weights"][class_names[index]])
        for index in range(config.attack_head_dim)
    ]
    return {
        "dataset": name,
        "attack_head_dim": int(config.attack_head_dim),
        "binary_pos_weight": float(binary_preview["bce_pos_weight_equivalent"]),
        "binary_class_weights": {
            "0": float(binary_preview["final_weights"]["0"]),
            "1": float(binary_preview["final_weights"]["1"]),
        },
        "attack_class_weights": attack_class_weights,
        "attack_class_weights_by_name": {
            class_names[index]: attack_class_weights[index]
            for index in range(config.attack_head_dim)
        },
        "id_to_class": {
            str(index): class_names[index] for index in range(config.attack_head_dim)
        },
        "weight_cap": WEIGHT_CAP,
        "source_split": "train",
        "computed_from_train_only": True,
        "validation_labels_used": False,
        "test_labels_used": False,
        "train_only_read_diagnostics": read_diagnostics,
    }


def _normalize_dataset_selection(selection: str) -> list[str]:
    if selection == "all":
        return ["cicids2018", "unsw_nb15"]
    if selection in {"cicids", "cicids2018"}:
        return ["cicids2018"]
    if selection in {"unsw", "unsw_nb15"}:
        return ["unsw_nb15"]
    raise HierarchicalClassWeightStrategyError(f"Unsupported dataset: {selection!r}")


def _write_strategy_doc(root: Path, results: list[dict[str, Any]]) -> Path:
    by_dataset = {result["dataset"]: result for result in results}
    cicids = by_dataset.get("cicids2018")
    unsw = by_dataset.get("unsw_nb15")
    lines = [
        "# Hierarchical Class-Weight Strategy",
        "",
        "Status: `Task A8.5 complete - class-weight strategy locked before full training`",
        "",
        f"Generated UTC: `{utc_timestamp()}`",
        "",
        "## Decision",
        "",
        "Full centralized hierarchical training must use train-split-only class weights with smoothing and a cap.",
        "",
        "- Binary Head 1: balanced class weights from `y_binary_train.npy`, mean-normalized, capped at `10.0`.",
        "- Attack Head 2: sqrt inverse-frequency weights from train attack rows only, mean-normalized, capped at `10.0`.",
        "- No validation labels, test labels, oversampling, manual rare-class duplication, or all-split balancing may be used.",
        "",
        "## Why Raw Inverse-Frequency Was Rejected",
        "",
        "Task A8 showed that raw inverse-frequency Head 2 weights would be dangerously large.",
        "",
        f"- CICIDS raw max Head 2 weight: `{cicids['raw_inverse_frequency_weight_preview_for_comparison']['SQL-Injection'] if cicids else 'n/a'}` for `SQL-Injection`.",
        f"- UNSW raw max Head 2 weight: `{unsw['raw_inverse_frequency_weight_preview_for_comparison']['Worms'] if unsw else 'n/a'}` for `Worms`.",
        "",
        "Those values would let a handful of rare rows dominate the attack-family loss and destabilize early training.",
        "",
        "## Why Sqrt Inverse-Frequency",
        "",
        "Sqrt inverse-frequency keeps the ranking that rare classes need, but compresses the gap between common and rare classes. Mean normalization keeps the class-weight scale close to the unweighted loss, and the cap prevents a single rare class from dominating the optimizer.",
        "",
        "## Train-Only Rule",
        "",
        "Weights are computed only from the training split. Validation remains reserved for model selection and early stopping, and the test split remains reserved for one final evaluation after the best validation checkpoint is selected. This avoids test-set tuning and fake performance claims.",
        "",
        "## Oversampling",
        "",
        "Oversampling is disabled. No rows are duplicated and no manual rare-class balancing is introduced in A8.5. If sampling changes are needed later, they require a separate approval task.",
        "",
        "## Locked Config Values",
        "",
        "```yaml",
        "class_weights:",
        "  binary:",
        "    enabled: true",
        "    source_split: train",
        "    method: balanced",
        "    normalize_mean: true",
        "    max_weight: 10.0",
        "    use_validation_labels: false",
        "    use_test_labels: false",
        "  attack_family:",
        "    enabled: true",
        "    source_split: train_attack_rows_only",
        "    method: sqrt_inverse_frequency",
        "    normalize_mean: true",
        "    max_weight: 10.0",
        "    use_validation_labels: false",
        "    use_test_labels: false",
        "    oversampling: false",
        "```",
        "",
        "## Dataset Effects",
        "",
    ]
    for result in results:
        rare = result["rare_class_weight_summary"]
        lines.extend(
            [
                f"### {result['dataset']}",
                "",
                f"- status: `{result['status']}`",
                f"- safe_for_full_training: `{str(result['safe_for_full_training']).lower()}`",
                f"- max final attack weight: `{result['max_final_attack_weight']}`",
                f"- cap: `{result['weight_cap']}`",
                f"- validation labels used: `{str(result['validation_labels_used']).lower()}`",
                f"- test labels used: `{str(result['test_labels_used']).lower()}`",
                f"- oversampling enabled: `{str(result['oversampling_enabled']).lower()}`",
                f"- rare mean final weight: `{rare['rare_mean_final_weight']}`",
                f"- non-rare mean final weight: `{rare['non_rare_mean_final_weight']}`",
                "",
                "| Rare class | Train support | Final weight |",
                "| --- | ---: | ---: |",
            ]
        )
        for entry in rare["rare_classes"]:
            lines.append(
                f"| `{entry['class_name']}` | {entry['train_support']} | {entry['final_weight']} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Compatibility",
            "",
            "The locked strategy is compatible with centralized training because it produces deterministic tensors from each dataset's train split. It is also compatible with future same-dataset FedAvg because every client in a dataset-specific run uses the same Head 2 label space and the global train-derived weighting policy can be documented in the federated manifest.",
            "",
            "## Safety Boundary",
            "",
            "- No full hierarchical training was run.",
            "- No model evaluation was run.",
            "- No final checkpoints or final metrics were created.",
            "- No hierarchical FedAvg, security, attacks, Trimmed Mean, XAI, or dashboard work was started.",
            "",
        ]
    )
    path = root / STRATEGY_DOC
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_hierarchical_class_weight_lock(
    dataset: str = "all",
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Compute and write A8.5 class-weight strategy audits."""

    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    selected = _normalize_dataset_selection(dataset)
    results: list[dict[str, Any]] = []
    for name in selected:
        print(f"\n=== A8.5 class-weight strategy: {name} ===", flush=True)
        result = _build_dataset_audit(name, root)
        save_json(root / DATASET_SPECS[name]["audit_json"], result)
        print(
            f"[{name}] status={result['status']}, "
            f"max_final_attack_weight={result['max_final_attack_weight']}",
            flush=True,
        )
        results.append(result)

    doc_path = _write_strategy_doc(root, results)
    overall_status = "PASS" if all(result["status"] == "PASS" for result in results) else "BLOCKED"
    print(f"\nA8.5 class-weight strategy doc written: {doc_path}", flush=True)
    print(f"A8.5 overall status: {overall_status}", flush=True)
    return {
        "status": overall_status,
        "results": results,
        "json_paths": [str(root / DATASET_SPECS[result["dataset"]]["audit_json"]) for result in results],
        "doc_path": str(doc_path),
        "full_training_run": False,
        "final_checkpoints_created": False,
        "final_metrics_created": False,
    }
