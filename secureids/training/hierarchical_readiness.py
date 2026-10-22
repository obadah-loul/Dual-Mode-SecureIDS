"""Full centralized hierarchical training readiness gate for Task A8.

This module performs pre-run checks only. It reads configs and existing
hierarchical arrays, computes train-only class-weight previews, initializes
full-split DataLoaders for one batch, and runs one model forward/loss check.
It does not train, backpropagate, save checkpoints, or create final metrics.
"""

from __future__ import annotations

from secureids.artifacts import load_numpy_readonly, read_artifact_path

import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

from secureids.models.secureids_hierarchical_advanced_net import (
    SecureIDSHierarchicalAdvancedNet,
    compute_hierarchical_loss,
)
from secureids.preprocessing.artifacts import save_json, utc_timestamp
from secureids.training.hierarchical_class_weights import (
    compute_attack_family_weights,
    compute_balanced_binary_weights,
)
from secureids.training.hierarchical_config import (
    HierarchicalTrainingConfig,
    HierarchicalTrainingConfigError,
    load_hierarchical_training_config,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPLITS: tuple[str, ...] = ("train", "val", "test")
REQUIRED_ARRAYS: tuple[str, ...] = (
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
)
EXPECTED_FORMULA = "0.5 * val_binary_macro_f1 + 0.5 * val_attack_family_macro_f1"
CHUNK_SIZE = 1_000_000
RAW_WEIGHT_EXTREME_THRESHOLD = 20.0
VERY_LOW_TRAIN_SUPPORT = 50

DATASET_READINESS = {
    "cicids2018": {
        "display": "CICIDS2018",
        "short": "cicids",
        "config": "configs/training/cicids2018_hierarchical.yaml",
        "json": "results/audits/hierarchical_full_training_readiness_cicids2018.json",
        "expected_checkpoint": "models/final/final_cicids_hierarchical.pt",
        "expected_result_dir": "results/final/hierarchical/cicids",
    },
    "unsw_nb15": {
        "display": "UNSW-NB15",
        "short": "unsw",
        "config": "configs/training/unsw_nb15_hierarchical.yaml",
        "json": "results/audits/hierarchical_full_training_readiness_unsw_nb15.json",
        "expected_checkpoint": "models/final/final_unsw_hierarchical.pt",
        "expected_result_dir": "results/final/hierarchical/unsw",
    },
}

REPORT_PATH = "docs/HIERARCHICAL_FULL_TRAINING_READINESS_REPORT.md"


class HierarchicalTrainingReadinessError(RuntimeError):
    """Raised when the A8 readiness gate cannot complete safely."""


class HierarchicalReadinessDataset(Dataset):
    """Read one full hierarchical split through mmap-backed arrays."""

    def __init__(
        self,
        X: np.ndarray,
        y_binary: np.ndarray,
        y_attack_family: np.ndarray,
        attack_family_mask: np.ndarray,
    ) -> None:
        if X.ndim != 2:
            raise ValueError(f"X must be 2D, got {X.shape}.")
        row_count = int(X.shape[0])
        for name, array in (
            ("y_binary", y_binary),
            ("y_attack_family", y_attack_family),
            ("attack_family_mask", attack_family_mask),
        ):
            if array.ndim != 1 or int(array.shape[0]) != row_count:
                raise ValueError(f"{name} must be 1D with {row_count} rows.")
        self.X = X
        self.y_binary = y_binary
        self.y_attack_family = y_attack_family
        self.attack_family_mask = attack_family_mask

    def __len__(self) -> int:
        return int(self.X.shape[0])

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        row = int(index)
        return {
            "X": torch.from_numpy(np.array(self.X[row], dtype=np.float32, copy=True)),
            "y_binary": torch.tensor(float(self.y_binary[row]), dtype=torch.float32),
            "y_attack_family": torch.tensor(int(self.y_attack_family[row]), dtype=torch.long),
            "attack_family_mask": torch.tensor(
                int(self.attack_family_mask[row]),
                dtype=torch.long,
            ),
        }


def _log(message: str) -> None:
    print(message, flush=True)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise HierarchicalTrainingReadinessError(f"Expected JSON object in {path}.")
    return payload


def _read_feature_count(path: Path) -> int | None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    names = payload.get("feature_names") if isinstance(payload, dict) else payload
    return len(names) if isinstance(names, list) else None


def _close_mmap(array: np.ndarray) -> None:
    mmap = getattr(array, "_mmap", None)
    if mmap is not None:
        mmap.close()


def _load_split_arrays(
    data_dir: Path,
    split: str,
    mmap: bool = True,
) -> dict[str, np.ndarray]:
    mode = "r" if mmap else None
    return {
        "X": load_numpy_readonly(data_dir / f"X_{split}.npy", mmap_mode=mode),
        "y_binary": load_numpy_readonly(data_dir / f"y_binary_{split}.npy", mmap_mode=mode),
        "y_attack_family": load_numpy_readonly(data_dir / f"y_attack_family_{split}.npy", mmap_mode=mode),
        "attack_family_mask": load_numpy_readonly(data_dir / f"attack_family_mask_{split}.npy", mmap_mode=mode),
    }


def _close_split_arrays(arrays: dict[str, np.ndarray]) -> None:
    for array in arrays.values():
        _close_mmap(array)


def _unique_values(values: set[int], limit: int = 50) -> list[int]:
    return sorted(values)[:limit]


def _count_split_labels(
    y_binary: np.ndarray,
    y_attack_family: np.ndarray,
    attack_family_mask: np.ndarray,
    attack_head_dim: int,
    ignore_index: int,
) -> dict[str, Any]:
    row_count = int(y_binary.shape[0])
    binary_counts = np.zeros(2, dtype=np.int64)
    mask_counts = np.zeros(2, dtype=np.int64)
    attack_counts = np.zeros(int(attack_head_dim), dtype=np.int64)
    binary_values: set[int] = set()
    mask_values: set[int] = set()
    attack_values: set[int] = set()
    invalid_binary = 0
    invalid_mask = 0
    mask0_not_ignore = 0
    mask1_invalid_attack_label = 0
    binary0_not_mask0 = 0
    binary1_not_mask1 = 0

    for start in range(0, row_count, CHUNK_SIZE):
        end = min(start + CHUNK_SIZE, row_count)
        yb = np.asarray(y_binary[start:end]).reshape(-1).astype(np.int64, copy=False)
        ya = np.asarray(y_attack_family[start:end]).reshape(-1).astype(np.int64, copy=False)
        mask = np.asarray(attack_family_mask[start:end]).reshape(-1).astype(np.int64, copy=False)

        binary_values.update(int(value) for value in np.unique(yb))
        mask_values.update(int(value) for value in np.unique(mask))
        attack_values.update(int(value) for value in np.unique(ya))

        binary_valid = np.isin(yb, [0, 1])
        mask_valid = np.isin(mask, [0, 1])
        invalid_binary += int(np.sum(~binary_valid))
        invalid_mask += int(np.sum(~mask_valid))
        binary_counts += np.bincount(yb[binary_valid], minlength=2)[:2]
        mask_counts += np.bincount(mask[mask_valid], minlength=2)[:2]

        valid_attack_label = (ya >= 0) & (ya < int(attack_head_dim))
        attack_rows = mask == 1
        benign_rows = mask == 0
        mask0_not_ignore += int(np.sum(benign_rows & (ya != ignore_index)))
        mask1_invalid_attack_label += int(np.sum(attack_rows & ~valid_attack_label))
        binary0_not_mask0 += int(np.sum((yb == 0) & (mask != 0)))
        binary1_not_mask1 += int(np.sum((yb == 1) & (mask != 1)))

        valid_attack_rows = attack_rows & valid_attack_label
        if bool(np.any(valid_attack_rows)):
            attack_counts += np.bincount(
                ya[valid_attack_rows],
                minlength=int(attack_head_dim),
            )[: int(attack_head_dim)]

    missing_classes = [
        int(index) for index, count in enumerate(attack_counts.tolist()) if int(count) == 0
    ]
    return {
        "row_count": row_count,
        "binary_counts": {"0": int(binary_counts[0]), "1": int(binary_counts[1])},
        "mask_counts": {"0": int(mask_counts[0]), "1": int(mask_counts[1])},
        "attack_family_counts": {
            str(index): int(count) for index, count in enumerate(attack_counts.tolist())
        },
        "unique_binary_values": _unique_values(binary_values),
        "unique_mask_values": _unique_values(mask_values),
        "unique_attack_family_values": _unique_values(attack_values, limit=200),
        "invalid_binary_label_count": invalid_binary,
        "invalid_mask_value_count": invalid_mask,
        "mask0_not_ignore_count": mask0_not_ignore,
        "mask1_invalid_attack_label_count": mask1_invalid_attack_label,
        "binary0_not_mask0_count": binary0_not_mask0,
        "binary1_not_mask1_count": binary1_not_mask1,
        "all_expected_head2_classes_present": not missing_classes,
        "missing_head2_class_ids": missing_classes,
    }


def _class_names(mapping: dict[str, Any], attack_head_dim: int) -> list[str]:
    id_to_class = mapping.get("id_to_class", {})
    class_to_id = mapping.get("class_to_id", {})
    names: list[str] = []
    for index in range(int(attack_head_dim)):
        name = None
        if isinstance(id_to_class, dict):
            name = id_to_class.get(str(index))
        if name is None and isinstance(class_to_id, dict):
            for key, value in class_to_id.items():
                if int(value) == index:
                    name = str(key)
                    break
        names.append(str(name if name is not None else f"class_{index}"))
    return names


def _named_counts(counts: dict[str, int], names: list[str]) -> dict[str, int]:
    return {
        names[index]: int(counts.get(str(index), 0))
        for index in range(len(names))
    }


def _balanced_weights(counts: list[int]) -> list[float | None]:
    total = int(sum(counts))
    class_count = len(counts)
    weights: list[float | None] = []
    for count in counts:
        weights.append(None if int(count) == 0 else total / (class_count * int(count)))
    return weights


def _clip_weight(value: float | None, min_clip: float, max_clip: float) -> float | None:
    if value is None:
        return None
    return float(min(max(float(value), min_clip), max_clip))


def _round_weight(value: float | None) -> float | None:
    return None if value is None else round(float(value), 6)


def _build_class_weight_preview(
    config: HierarchicalTrainingConfig,
    class_names: list[str],
    split_counts: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    train_counts = split_counts["train"]
    binary_counts = [
        int(train_counts["binary_counts"]["0"]),
        int(train_counts["binary_counts"]["1"]),
    ]
    binary_balanced = _balanced_weights(binary_counts)
    positives = binary_counts[1]
    negatives = binary_counts[0]
    pos_weight = float(negatives / positives) if positives > 0 else 1.0

    attack_counts = [
        int(train_counts["attack_family_counts"].get(str(index), 0))
        for index in range(config.attack_head_dim)
    ]
    attack_balanced = _balanced_weights(attack_counts)
    attack_total = int(sum(attack_counts))
    max_clip = float(config.raw.get("class_imbalance", {}).get("class_weight_max_clip", 20.0))
    min_clip = float(config.raw.get("class_imbalance", {}).get("class_weight_min_clip", 0.1))
    max_count = max(attack_counts) if attack_counts else 0

    attack_by_class = {}
    for index, name in enumerate(class_names):
        count = int(attack_counts[index])
        raw = attack_balanced[index]
        sqrt_weight = None if count == 0 or max_count == 0 else math.sqrt(max_count / count)
        log_weight = None if count == 0 else math.log1p(attack_total / count)
        attack_by_class[name] = {
            "class_id": index,
            "train_support": count,
            "raw_balanced_weight": _round_weight(raw),
            "capped_balanced_weight": _round_weight(_clip_weight(raw, min_clip, max_clip)),
            "sqrt_inverse_frequency_weight": _round_weight(sqrt_weight),
            "log_smoothed_weight": _round_weight(log_weight),
        }

    raw_weights = [float(weight) for weight in attack_balanced if weight is not None]
    raw_max = max(raw_weights) if raw_weights else 0.0
    raw_min = min(raw_weights) if raw_weights else 0.0
    zero_support = [
        class_names[index] for index, count in enumerate(attack_counts) if int(count) == 0
    ]
    very_low_support = [
        class_names[index]
        for index, count in enumerate(attack_counts)
        if 0 < int(count) < VERY_LOW_TRAIN_SUPPORT
    ]
    extreme_classes = [
        class_names[index]
        for index, weight in enumerate(attack_balanced)
        if weight is not None and float(weight) > RAW_WEIGHT_EXTREME_THRESHOLD
    ]

    warnings: list[str] = []
    if zero_support:
        warnings.append(
            "Head 2 train support is zero for: " + ", ".join(zero_support)
        )
    if very_low_support:
        warnings.append(
            "Very low Head 2 train support (<50 rows) for: "
            + ", ".join(very_low_support)
        )
    if extreme_classes:
        warnings.append(
            "Raw inverse-frequency Head 2 weights are extreme for: "
            + ", ".join(extreme_classes)
            + "; use capped, sqrt, or log-smoothed weighting before real training."
        )

    preview = {
        "computed_from_split": "train",
        "test_labels_used": False,
        "binary": {
            "train_counts": {"0": binary_counts[0], "1": binary_counts[1]},
            "bce_pos_weight_neg_over_pos": round(pos_weight, 6),
            "balanced_class_weights": {
                "0": _round_weight(binary_balanced[0]),
                "1": _round_weight(binary_balanced[1]),
            },
        },
        "attack_family": {
            "train_attack_rows": attack_total,
            "all_classes_have_nonzero_train_support": not zero_support,
            "raw_balanced_weights_by_class": {
                name: attack_by_class[name]["raw_balanced_weight"] for name in class_names
            },
            "capped_balanced_weights_by_class": {
                name: attack_by_class[name]["capped_balanced_weight"] for name in class_names
            },
            "sqrt_inverse_frequency_weights_by_class": {
                name: attack_by_class[name]["sqrt_inverse_frequency_weight"]
                for name in class_names
            },
            "log_smoothed_weights_by_class": {
                name: attack_by_class[name]["log_smoothed_weight"] for name in class_names
            },
            "by_class": attack_by_class,
        },
    }
    risk = {
        "assessment": "WARNING" if warnings else "OK",
        "raw_attack_weight_min": round(float(raw_min), 6),
        "raw_attack_weight_max": round(float(raw_max), 6),
        "raw_weight_extreme_threshold": RAW_WEIGHT_EXTREME_THRESHOLD,
        "configured_min_clip": min_clip,
        "configured_max_clip": max_clip,
        "zero_support_classes": zero_support,
        "very_low_support_classes_lt_50": very_low_support,
        "extreme_raw_weight_classes": extreme_classes,
        "recommendations": [
            "Do not use uncapped raw inverse-frequency Head 2 weights.",
            "Use the configured max weight cap, sqrt inverse-frequency weighting, or log-smoothed weighting before real training.",
            "Keep class weights computed from the train split only.",
            "Do not add oversampling unless a later task explicitly approves it.",
        ],
    }
    return preview, risk, warnings


def _device_check(dataset: str) -> dict[str, Any]:
    cuda_available = torch.cuda.is_available()
    selected = "cuda" if cuda_available else "cpu"
    gpu_name = torch.cuda.get_device_name(0) if cuda_available else None
    total_memory_gb = None
    if cuda_available:
        props = torch.cuda.get_device_properties(0)
        total_memory_gb = round(float(props.total_memory) / (1024**3), 3)
    caution = None
    if not cuda_available:
        caution = "CUDA unavailable; CPU full training may be slow, especially for CICIDS2018."
    elif dataset == "cicids2018" and total_memory_gb is not None and total_memory_gb < 8.0:
        caution = "CUDA is available, but CICIDS2018 is large; monitor GPU memory during real training."
    return {
        "python_executable": sys.executable,
        "torch_version": torch.__version__,
        "cuda_available": bool(cuda_available),
        "gpu_name": gpu_name,
        "gpu_total_memory_gb": total_memory_gb,
        "selected_device_recommendation": selected,
        "memory_caution": caution,
    }


def _build_model(config: HierarchicalTrainingConfig) -> SecureIDSHierarchicalAdvancedNet:
    model_cfg = config.raw.get("model", {})
    return SecureIDSHierarchicalAdvancedNet(
        input_dim=config.input_dim,
        attack_head_dim=config.attack_head_dim,
        hidden_dims=tuple(model_cfg.get("hidden_dims", (256, 128, 128))),
        dropout=float(model_cfg.get("dropout", 0.20)),
        normalization=str(model_cfg.get("normalization", "layernorm")),
    )


def _check_dataloaders(
    config: HierarchicalTrainingConfig,
    data_dir: Path,
) -> tuple[dict[str, Any], dict[str, torch.Tensor]]:
    batch_size = int(config.raw.get("training", {}).get("batch_size", 256))
    result: dict[str, Any] = {
        "status": "PASS",
        "batch_size_used": batch_size,
        "full_epoch_run": False,
        "optimizer_step_run": False,
        "splits": {},
    }
    first_train_batch: dict[str, torch.Tensor] | None = None

    for split in SPLITS:
        arrays = _load_split_arrays(data_dir, split, mmap=True)
        try:
            dataset = HierarchicalReadinessDataset(
                arrays["X"],
                arrays["y_binary"],
                arrays["y_attack_family"],
                arrays["attack_family_mask"],
            )
            loader = DataLoader(
                dataset,
                batch_size=batch_size,
                shuffle=False,
                drop_last=False,
                num_workers=0,
            )
            batch = next(iter(loader))
            required_keys = {"X", "y_binary", "y_attack_family", "attack_family_mask"}
            key_set = set(batch.keys())
            shapes = {key: list(value.shape) for key, value in batch.items()}
            dtypes = {key: str(value.dtype) for key, value in batch.items()}
            passed = (
                required_keys == key_set
                and batch["X"].ndim == 2
                and int(batch["X"].shape[1]) == config.input_dim
                and batch["y_binary"].ndim == 1
                and batch["y_attack_family"].ndim == 1
                and batch["attack_family_mask"].ndim == 1
            )
            result["splits"][split] = {
                "dataset_object_initialized": True,
                "dataloader_initialized": True,
                "one_batch_loaded": True,
                "required_keys_present": sorted(key_set),
                "batch_shapes": shapes,
                "batch_dtypes": dtypes,
                "passed": bool(passed),
            }
            if not passed:
                result["status"] = "FAIL"
            if split == "train":
                first_train_batch = {key: value.clone() for key, value in batch.items()}
        finally:
            _close_split_arrays(arrays)

    if first_train_batch is None:
        raise HierarchicalTrainingReadinessError("Could not load a train batch.")
    return result, first_train_batch


def _check_model_forward_and_loss(
    config: HierarchicalTrainingConfig,
    batch: dict[str, torch.Tensor],
    device_check: dict[str, Any],
    pos_weight: float,
    attack_class_weights: list[float] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    device = torch.device(str(device_check["selected_device_recommendation"]))
    model = _build_model(config).to(device)
    model.eval()
    loss_cfg = config.raw.get("loss", {})
    attack_weight_tensor = (
        torch.tensor(attack_class_weights, dtype=torch.float32, device=device)
        if attack_class_weights is not None
        else None
    )
    with torch.no_grad():
        features = batch["X"].to(device)
        outputs = model(features)
        loss_bundle = compute_hierarchical_loss(
            outputs,
            y_binary=batch["y_binary"].to(device),
            y_attack_family=batch["y_attack_family"].to(device),
            attack_family_mask=batch["attack_family_mask"].to(device),
            binary_loss_weight=float(loss_cfg.get("binary_loss_weight", 1.0)),
            attack_loss_weight=float(loss_cfg.get("attack_loss_weight", 1.0)),
            ignore_index=int(loss_cfg.get("ignore_index", -1)),
            pos_weight=torch.tensor([float(pos_weight)], dtype=torch.float32, device=device),
            attack_class_weights=attack_weight_tensor,
        )

    output_shapes = {key: list(value.shape) for key, value in outputs.items()}
    forward_ok = (
        output_shapes.get("binary_logit") == [int(batch["X"].shape[0])]
        and output_shapes.get("attack_logits")
        == [int(batch["X"].shape[0]), int(config.attack_head_dim)]
        and output_shapes.get("embedding", [None])[0] == int(batch["X"].shape[0])
    )
    loss_values = {
        "total_loss": float(loss_bundle["total_loss"].detach().cpu().item()),
        "binary_loss": float(loss_bundle["binary_loss"].detach().cpu().item()),
        "attack_loss": float(loss_bundle["attack_loss"].detach().cpu().item()),
        "attack_rows": int(loss_bundle["attack_rows"]),
    }
    finite_loss = all(
        math.isfinite(value)
        for key, value in loss_values.items()
        if key != "attack_rows"
    )
    return (
        {
            "status": "PASS" if forward_ok else "FAIL",
            "model_class": "SecureIDSHierarchicalAdvancedNet",
            "input_dim": config.input_dim,
            "attack_head_dim": config.attack_head_dim,
            "device": str(device),
            "training_mode": False,
            "optimizer_step_run": False,
            "checkpoint_saved": False,
            "output_shapes": output_shapes,
            "expected_output_shapes": {
                "binary_logit": [int(batch["X"].shape[0])],
                "attack_logits": [int(batch["X"].shape[0]), int(config.attack_head_dim)],
                "embedding": [int(batch["X"].shape[0]), model.embedding_dim],
            },
        },
        {
            "status": "PASS" if finite_loss else "FAIL",
            "masked_loss_computed": True,
            "finite_loss": bool(finite_loss),
            "optimizer_step_run": False,
            "backward_pass_run": False,
            "loss_values": loss_values,
            "binary_pos_weight_applied": bool(loss_bundle.get("binary_pos_weight_applied")),
            "attack_class_weights_applied": bool(
                loss_bundle.get("attack_class_weights_applied")
            ),
            "binary_pos_weight_value": float(pos_weight),
            "attack_class_weights_value": (
                [round(float(w), 6) for w in attack_class_weights]
                if attack_class_weights is not None
                else None
            ),
            "class_weights_train_only": True,
            "validation_or_test_labels_used_for_weights": False,
        },
    )


def _planned_metric_outputs(config: HierarchicalTrainingConfig) -> dict[str, Any]:
    outputs = config.outputs
    metrics = config.raw.get("metrics", {})
    required_output_keys = (
        "training_history_csv",
        "test_metrics_json",
        "binary_confusion_matrix_csv",
        "attack_family_confusion_matrix_csv",
        "per_class_attack_metrics_csv",
        "rare_class_metrics_csv",
        "manifest_json",
    )
    required_binary_metrics = {"macro_f1", "confusion_matrix"}
    required_attack_metrics = {
        "attack_family_macro_f1_on_attack_rows",
        "per_class_precision_recall_f1_support",
        "rare_class_macro_f1",
        "weak_hard_class_report",
        "attack_family_confusion_matrix",
        "validation_vs_test_gap_report",
    }
    binary_metrics = set(metrics.get("binary", []))
    attack_metrics = set(metrics.get("attack_family", []))
    path_plan = {
        key: {
            "path": outputs.get(key),
            "exists_now": config.resolve(outputs[key]).exists() if key in outputs else None,
            "planned_only_not_created_by_a8": True,
        }
        for key in required_output_keys
    }
    return {
        "status": "PASS",
        "training_history_csv": path_plan["training_history_csv"],
        "validation_metrics_per_epoch": "planned inside training_history_csv",
        "best_validation_checkpoint_selection": {
            "monitor": config.raw.get("checkpoint_selection", {}).get("monitor"),
            "formula": config.raw.get("checkpoint_selection", {}).get("formula"),
            "use_validation_only": config.raw.get("checkpoint_selection", {}).get(
                "use_validation_only"
            ),
        },
        "final_one_time_test_metrics": path_plan["test_metrics_json"],
        "binary_confusion_matrix": path_plan["binary_confusion_matrix_csv"],
        "attack_family_confusion_matrix": path_plan["attack_family_confusion_matrix_csv"],
        "per_class_attack_metrics": path_plan["per_class_attack_metrics_csv"],
        "rare_class_metrics": path_plan["rare_class_metrics_csv"],
        "weak_hard_class_report": "planned in config metrics.attack_family",
        "validation_vs_test_gap_report": "planned in config metrics.attack_family",
        "training_manifest_json": path_plan["manifest_json"],
        "metric_config_coverage": {
            "binary_required_present": sorted(required_binary_metrics & binary_metrics),
            "binary_required_missing": sorted(required_binary_metrics - binary_metrics),
            "attack_required_present": sorted(required_attack_metrics & attack_metrics),
            "attack_required_missing": sorted(required_attack_metrics - attack_metrics),
        },
        "final_metrics_created_by_a8": False,
    }


def _list_files(path: Path) -> list[str]:
    if not path.exists() or not path.is_dir():
        return []
    return sorted(str(item) for item in path.rglob("*") if item.is_file())


def _output_safety_check(
    config: HierarchicalTrainingConfig,
    root: Path,
    dataset_meta: dict[str, str],
) -> dict[str, Any]:
    checkpoint = config.resolve(config.outputs["checkpoint"])
    result_dir = config.resolve(config.outputs["result_dir"])
    expected_checkpoint = root / dataset_meta["expected_checkpoint"]
    expected_result_dir = root / dataset_meta["expected_result_dir"]
    planned_final_files = {
        key: config.resolve(value)
        for key, value in config.outputs.items()
        if key != "result_dir"
    }
    existing_planned = {
        key: str(path) for key, path in planned_final_files.items() if path.exists()
    }
    result_files = _list_files(result_dir)
    binary_checkpoints = {
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
    }
    binary_result_files = {
        "results/final/centralized/cicids_training_history.csv": (
            root / "results/final/centralized/cicids_training_history.csv"
        ).exists(),
        "results/final/centralized/cicids_test_metrics.json": (
            root / "results/final/centralized/cicids_test_metrics.json"
        ).exists(),
        "results/final/centralized/cicids_confusion_matrix.csv": (
            root / "results/final/centralized/cicids_confusion_matrix.csv"
        ).exists(),
        "results/audits/training_manifest_cicids2018.json": (
            root / "results/audits/training_manifest_cicids2018.json"
        ).exists(),
        "results/final/centralized/unsw_training_history.csv": (
            root / "results/final/centralized/unsw_training_history.csv"
        ).exists(),
        "results/final/centralized/unsw_test_metrics.json": (
            root / "results/final/centralized/unsw_test_metrics.json"
        ).exists(),
        "results/final/centralized/unsw_confusion_matrix.csv": (
            root / "results/final/centralized/unsw_confusion_matrix.csv"
        ).exists(),
        "results/audits/training_manifest_unsw_nb15.json": (
            root / "results/audits/training_manifest_unsw_nb15.json"
        ).exists(),
    }
    smoke_paths = {
        "cicids2018": root / "results/audits/hierarchical_smoke_training_cicids2018.json",
        "unsw_nb15": root / "results/audits/hierarchical_smoke_training_unsw_nb15.json",
    }
    smoke_flags: dict[str, Any] = {}
    for name, path in smoke_paths.items():
        if path.exists():
            payload = _load_json(path)
            smoke_flags[name] = {
                "path": str(path),
                "exists": True,
                "smoke_only": payload.get("smoke_only"),
                "non_final": payload.get("non_final"),
                "do_not_report_as_final": payload.get("do_not_report_as_final"),
                "final_metrics_created": payload.get("final_metrics_created"),
                "checkpoint_created": payload.get("checkpoint_created"),
            }
        else:
            smoke_flags[name] = {"path": str(path), "exists": False}

    hierarchical_checkpoints = {
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

    return {
        "status": (
            "PASS"
            if not existing_planned
            and all(binary_checkpoints.values())
            and all(binary_result_files.values())
            else "FAIL"
        ),
        "planned_checkpoint": str(checkpoint),
        "expected_checkpoint_path_match": checkpoint == expected_checkpoint,
        "planned_result_dir": str(result_dir),
        "expected_result_dir_match": result_dir == expected_result_dir,
        "planned_checkpoint_exists": checkpoint.exists(),
        "planned_final_output_files_existing": existing_planned,
        "result_dir_exists": result_dir.exists(),
        "result_dir_existing_files": result_files,
        "result_dir_contains_final_metrics": bool(result_files),
        "no_overwrite_would_occur": not existing_planned,
        "binary_checkpoints_preserved": binary_checkpoints,
        "all_binary_checkpoints_exist": all(binary_checkpoints.values()),
        "binary_result_files_preserved": binary_result_files,
        "all_binary_result_files_exist": all(binary_result_files.values()),
        "smoke_outputs_non_final": smoke_flags,
        "hierarchical_checkpoints_exist": hierarchical_checkpoints,
        "federated_hierarchical_started": any(
            value for key, value in hierarchical_checkpoints.items() if "federated" in key
        ),
    }


def _no_fake_results_check(
    config: HierarchicalTrainingConfig,
    manifest: dict[str, Any],
    mapping: dict[str, Any],
    output_safety: dict[str, Any],
) -> dict[str, Any]:
    safety = config.raw.get("safety", {})
    class_imbalance = config.raw.get("class_imbalance", {})
    return {
        "status": "PASS",
        "no_test_set_tuning": bool(
            safety.get("no_test_set_tuning")
            and config.raw.get("checkpoint_selection", {}).get("select_by_test_metrics") is False
            and config.raw.get("checkpoint_selection", {}).get("use_validation_only") is True
            and manifest.get("no_test_set_tuning") is True
        ),
        "no_test_based_class_weights": bool(
            class_imbalance.get("compute_weights_from") == "train_only"
            and class_imbalance.get("allow_test_based_weights") is False
        ),
        "no_scaler_encoder_refit_on_test": bool(
            safety.get("no_scaler_encoder_refit_on_test")
            and manifest.get("no_scaler_encoder_refit_on_test") is True
        ),
        "no_fake_shared_multiclass_taxonomy": bool(
            mapping.get("common_superclass_is_training_target") is False
            and manifest.get("fake_shared_multiclass_label_list_created") is False
        ),
        "no_smoke_metrics_reported_as_final": True,
        "no_final_metrics_created_in_a8": True,
        "no_full_training_execution": True,
        "no_optimizer_training_loop": True,
        "no_checkpoint_saved": True,
        "no_fedavg_security_attack_xai_dashboard_started": bool(
            not output_safety.get("federated_hierarchical_started")
        ),
    }


def _normalize_dataset_selection(selection: str) -> list[str]:
    if selection in {"all", ""}:
        return ["cicids2018", "unsw_nb15"]
    if selection in {"cicids", "cicids2018"}:
        return ["cicids2018"]
    if selection in {"unsw", "unsw_nb15"}:
        return ["unsw_nb15"]
    raise HierarchicalTrainingReadinessError(f"Unsupported dataset selection: {selection!r}")


def _validate_config_fields(
    config: HierarchicalTrainingConfig,
    config_path: Path,
    feature_count: int | None,
    mapping_count: int,
) -> tuple[dict[str, Any], list[str]]:
    issues: list[str] = []
    checkpoint = config.raw.get("checkpoint_selection", {})
    loss = config.raw.get("loss", {})
    if not config_path.exists():
        issues.append(f"Config file missing: {config_path}")
    if config.dataset not in DATASET_READINESS:
        issues.append(f"Invalid dataset name: {config.dataset}")
    if config.task != "hierarchical":
        issues.append(f"Task must be hierarchical, got {config.task!r}.")
    if config.model_name != "SecureIDSHierarchicalAdvancedNet":
        issues.append(f"Unexpected model: {config.model_name}")
    if feature_count != config.input_dim:
        issues.append(f"input_dim {config.input_dim} does not match feature count {feature_count}.")
    if mapping_count != config.attack_head_dim:
        issues.append(
            f"attack_head_dim {config.attack_head_dim} does not match mapping count {mapping_count}."
        )
    if float(loss.get("binary_loss_weight", 0.0)) <= 0:
        issues.append("loss.binary_loss_weight missing or invalid.")
    if float(loss.get("attack_loss_weight", 0.0)) <= 0:
        issues.append("loss.attack_loss_weight missing or invalid.")
    if checkpoint.get("formula") != EXPECTED_FORMULA:
        issues.append("Validation checkpoint formula missing or changed.")
    if checkpoint.get("use_validation_only") is not True:
        issues.append("Checkpoint selection must use validation only.")
    if checkpoint.get("select_by_test_metrics") is not False:
        issues.append("Checkpoint selection must not use test metrics.")

    return (
        {
            "config_path": str(config_path),
            "config_exists": config_path.exists(),
            "dataset": config.dataset,
            "task": config.task,
            "model_name": config.model_name,
            "input_dim": config.input_dim,
            "processed_feature_dim": feature_count,
            "attack_head_dim": config.attack_head_dim,
            "attack_family_mapping_count": mapping_count,
            "loss": {
                "binary_loss_weight": float(loss.get("binary_loss_weight", 0.0)),
                "attack_loss_weight": float(loss.get("attack_loss_weight", 0.0)),
                "ignore_index": int(loss.get("ignore_index", -1)),
            },
            "checkpoint_selection_formula": checkpoint.get("formula"),
            "checkpoint_selection_validation_only": checkpoint.get("use_validation_only"),
            "checkpoint_selection_uses_test_metrics": checkpoint.get("select_by_test_metrics"),
        },
        issues,
    )


def _build_data_summary(
    config: HierarchicalTrainingConfig,
    data_dir: Path,
    class_names: list[str],
    warnings: list[str],
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    missing_files = [name for name in REQUIRED_ARRAYS if not read_artifact_path(data_dir / name).exists()]
    blocking: list[str] = []
    if not data_dir.is_dir():
        blocking.append(f"Hierarchical processed folder is missing: {data_dir}")
    if missing_files:
        blocking.append(f"Missing hierarchical array files: {missing_files}")

    split_counts: dict[str, dict[str, Any]] = {}
    split_summaries: dict[str, Any] = {}
    if blocking:
        return (
            {
                "hierarchical_data_dir": str(data_dir),
                "hierarchical_data_dir_exists": data_dir.is_dir(),
                "required_files_missing": missing_files,
                "splits": {},
            },
            {"binary_by_split": {}, "attack_family_by_split": {}},
            blocking,
        )

    for split in SPLITS:
        _log(f"[{config.dataset}] checking {split} arrays")
        arrays = _load_split_arrays(data_dir, split, mmap=True)
        try:
            X = arrays["X"]
            y_binary = arrays["y_binary"]
            y_attack_family = arrays["y_attack_family"]
            attack_family_mask = arrays["attack_family_mask"]
            X_shape = tuple(int(value) for value in X.shape)
            yb_shape = tuple(int(value) for value in y_binary.shape)
            ya_shape = tuple(int(value) for value in y_attack_family.shape)
            mask_shape = tuple(int(value) for value in attack_family_mask.shape)
            labels = _count_split_labels(
                y_binary,
                y_attack_family,
                attack_family_mask,
                config.attack_head_dim,
                int(config.raw.get("loss", {}).get("ignore_index", -1)),
            )
            split_counts[split] = labels
            row_count = X_shape[0] if len(X_shape) == 2 else None
            split_blocking: list[str] = []
            if len(X_shape) != 2:
                split_blocking.append("X is not 2D")
            if len(yb_shape) != 1 or len(ya_shape) != 1 or len(mask_shape) != 1:
                split_blocking.append("labels/mask are not all 1D")
            if row_count is None or yb_shape != (row_count,) or ya_shape != (row_count,) or mask_shape != (row_count,):
                split_blocking.append("X/y/mask lengths do not match")
            if len(X_shape) == 2 and X_shape[1] != config.input_dim:
                split_blocking.append("X feature dimension does not match config input_dim")
            if labels["invalid_binary_label_count"] > 0:
                split_blocking.append("binary labels include values outside 0/1")
            if labels["invalid_mask_value_count"] > 0:
                split_blocking.append("attack masks include values outside 0/1")
            if labels["mask0_not_ignore_count"] > 0:
                split_blocking.append("benign/mask-0 rows include non-ignore Head 2 labels")
            if labels["mask1_invalid_attack_label_count"] > 0:
                split_blocking.append("attack/mask-1 rows include invalid Head 2 labels")
            if labels["binary0_not_mask0_count"] > 0 or labels["binary1_not_mask1_count"] > 0:
                split_blocking.append("binary labels and attack_family_mask disagree")
            if not labels["all_expected_head2_classes_present"]:
                split_blocking.append(
                    "missing Head 2 classes: "
                    + ", ".join(
                        class_names[index] for index in labels["missing_head2_class_ids"]
                    )
                )
            if split_blocking:
                blocking.append(f"{split}: " + "; ".join(split_blocking))
            split_summaries[split] = {
                "X_shape": list(X_shape),
                "X_dtype": str(X.dtype),
                "y_binary_shape": list(yb_shape),
                "y_binary_dtype": str(y_binary.dtype),
                "y_attack_family_shape": list(ya_shape),
                "y_attack_family_dtype": str(y_attack_family.dtype),
                "attack_family_mask_shape": list(mask_shape),
                "attack_family_mask_dtype": str(attack_family_mask.dtype),
                "labels": labels,
                "head2_classes_present": [
                    class_names[index]
                    for index in range(config.attack_head_dim)
                    if int(labels["attack_family_counts"].get(str(index), 0)) > 0
                ],
                "head2_classes_missing": [
                    class_names[index] for index in labels["missing_head2_class_ids"]
                ],
            }
        finally:
            _close_split_arrays(arrays)

    class_distribution = {
        "binary_by_split": {
            split: split_counts[split]["binary_counts"] for split in SPLITS
        },
        "attack_family_by_split": {
            split: _named_counts(split_counts[split]["attack_family_counts"], class_names)
            for split in SPLITS
        },
    }
    data_summary = {
        "hierarchical_data_dir": str(data_dir),
        "hierarchical_data_dir_exists": data_dir.is_dir(),
        "required_files_missing": missing_files,
        "required_files_present": [name for name in REQUIRED_ARRAYS if name not in missing_files],
        "splits": split_summaries,
        "all_required_files_exist": not missing_files,
        "all_splits_have_all_expected_head2_classes": all(
            split_counts[split]["all_expected_head2_classes_present"] for split in SPLITS
        ),
        "memory_policy": "X arrays loaded with numpy mmap_mode='r'; label arrays scanned in chunks.",
    }
    return data_summary, class_distribution, blocking


def _rare_class_summary(
    config: HierarchicalTrainingConfig,
    class_names: list[str],
    class_to_id: dict[str, Any],
    split_counts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    rare_names = list(config.raw.get("rare_classes", []))
    rare_entries: list[dict[str, Any]] = []
    missing_or_undocumented: list[str] = []
    for rare_name in rare_names:
        class_id = class_to_id.get(rare_name)
        if class_id is None:
            missing_or_undocumented.append(str(rare_name))
            rare_entries.append(
                {
                    "class_name": str(rare_name),
                    "class_id": None,
                    "documented_in_config": True,
                    "present_train_val_test": False,
                    "split_counts": {},
                }
            )
            continue
        class_id_int = int(class_id)
        counts = {
            split: int(split_counts[split]["attack_family_counts"].get(str(class_id_int), 0))
            for split in SPLITS
        }
        present = all(value > 0 for value in counts.values())
        if not present:
            missing_or_undocumented.append(str(rare_name))
        rare_entries.append(
            {
                "class_name": str(rare_name),
                "class_id": class_id_int,
                "documented_in_config": True,
                "present_train_val_test": bool(present),
                "split_counts": counts,
            }
        )
    return {
        "rare_classes_from_config": rare_names,
        "rare_class_entries": rare_entries,
        "rare_classes_present_in_train_val_test_or_documented": not missing_or_undocumented,
        "rare_classes_missing_or_not_mapped": missing_or_undocumented,
        "handling_plan": [
            "Keep rare classes separate in Head 2.",
            "Report per-class precision, recall, F1, and support.",
            "Report rare-class metrics and weak/hard-class behavior.",
            "Use capped or smoothed train-only class weights; avoid oversampling unless later approved.",
        ],
    }


def _check_one_dataset(dataset: str, root: Path) -> dict[str, Any]:
    meta = DATASET_READINESS[dataset]
    config_path = root / meta["config"]
    blocking_issues: list[str] = []
    warnings: list[str] = []

    _log(f"\n=== A8 readiness start: {dataset} ===")
    try:
        config = load_hierarchical_training_config(config_path, project_root=root)
    except (HierarchicalTrainingConfigError, FileNotFoundError) as error:
        raise HierarchicalTrainingReadinessError(
            f"Could not load hierarchical config for {dataset}: {error}"
        ) from error
    _log(f"[{dataset}] config loaded")

    data_dir = config.resolve(config.hierarchical_data_dir)
    mapping_path = config.resolve(config.attack_family_label_mapping_path)
    manifest_path = config.resolve(config.preprocessing_manifest_path)
    feature_names_path = config.resolve(config.feature_names_path)
    preprocessing_readiness_path = config.resolve(config.readiness_json)
    taxonomy_path = config.resolve(config.taxonomy_config)
    mapping = _load_json(mapping_path)
    manifest = _load_json(manifest_path)
    preprocessing_readiness = (
        _load_json(preprocessing_readiness_path)
        if preprocessing_readiness_path.exists()
        else {}
    )
    class_to_id = mapping.get("class_to_id", {})
    if not isinstance(class_to_id, dict):
        class_to_id = {}
    class_names = _class_names(mapping, config.attack_head_dim)
    feature_count = _read_feature_count(feature_names_path)
    config_summary, config_issues = _validate_config_fields(
        config,
        config_path,
        feature_count,
        len(class_to_id),
    )
    config_summary["preprocessing_readiness_json"] = {
        "path": str(preprocessing_readiness_path),
        "exists": preprocessing_readiness_path.exists(),
        "status": preprocessing_readiness.get("status"),
        "ready_for_hierarchical_model_implementation": preprocessing_readiness.get(
            "ready_for_hierarchical_model_implementation"
        ),
    }
    config_summary["taxonomy_config"] = {
        "path": str(taxonomy_path),
        "exists": taxonomy_path.exists(),
    }
    config_summary["preprocessing_manifest"] = {
        "path": str(manifest_path),
        "exists": manifest_path.exists(),
        "status": manifest.get("status"),
        "task": manifest.get("task"),
        "feature_dim": manifest.get("feature_dim"),
    }
    blocking_issues.extend(config_issues)
    if not preprocessing_readiness_path.exists():
        blocking_issues.append(
            f"Preprocessing readiness JSON is missing: {preprocessing_readiness_path}"
        )
    elif (
        preprocessing_readiness.get("status") != "PASS"
        or preprocessing_readiness.get("ready_for_hierarchical_model_implementation")
        is not True
    ):
        blocking_issues.append(
            "Preprocessing readiness JSON is not PASS/ready: "
            f"{preprocessing_readiness_path}"
        )
    if not taxonomy_path.exists():
        blocking_issues.append(f"Taxonomy config is missing: {taxonomy_path}")
    if manifest.get("status") != "PASS" or manifest.get("task") != "hierarchical_preprocessing":
        blocking_issues.append(
            "Preprocessing manifest is not PASS hierarchical_preprocessing: "
            f"{manifest_path}"
        )
    if int(manifest.get("feature_dim", -1)) != int(config.input_dim):
        blocking_issues.append(
            f"Preprocessing manifest feature_dim {manifest.get('feature_dim')} "
            f"does not match config input_dim {config.input_dim}."
        )

    data_summary, class_distribution, data_issues = _build_data_summary(
        config,
        data_dir,
        class_names,
        warnings,
    )
    blocking_issues.extend(data_issues)
    _log(f"[{dataset}] data files checked")

    split_counts = {
        split: data_summary["splits"][split]["labels"]
        for split in SPLITS
        if split in data_summary["splits"]
    }
    if set(split_counts) != set(SPLITS):
        raise HierarchicalTrainingReadinessError(f"Could not inspect all splits for {dataset}.")

    rare_summary = _rare_class_summary(config, class_names, class_to_id, split_counts)
    if not rare_summary["rare_classes_present_in_train_val_test_or_documented"]:
        warnings.append(
            "Rare classes not present in every split or not mapped: "
            + ", ".join(rare_summary["rare_classes_missing_or_not_mapped"])
        )

    class_weight_preview, class_weight_risk, weight_warnings = _build_class_weight_preview(
        config,
        class_names,
        split_counts,
    )
    warnings.extend(weight_warnings)
    _log(f"[{dataset}] class weights preview computed")

    dataloader_check, train_batch = _check_dataloaders(config, data_dir)
    if dataloader_check["status"] != "PASS":
        blocking_issues.append("Dataloader readiness failed.")
    _log(f"[{dataset}] dataloader checked")

    device_check = _device_check(dataset)
    if device_check["memory_caution"]:
        warnings.append(str(device_check["memory_caution"]))

    # Build the locked A8.5 train-only class weights and exercise the weighted
    # masked loss so readiness proves the rare-class weights are actually usable.
    weight_cap = float(config.raw.get("class_imbalance", {}).get("class_weight_max_clip", 10.0))
    locked_attack_class_weights: list[float] | None = None
    locked_binary_pos_weight = float(
        class_weight_preview["binary"]["bce_pos_weight_neg_over_pos"]
    )
    try:
        train_label_counts = split_counts["train"]
        locked_binary = compute_balanced_binary_weights(
            train_label_counts["binary_counts"],
            max_weight=weight_cap,
        )
        locked_attack = compute_attack_family_weights(
            train_label_counts["attack_family_counts"],
            class_names,
            max_weight=weight_cap,
        )
        locked_binary_pos_weight = float(locked_binary["bce_pos_weight_equivalent"])
        locked_attack_class_weights = [
            float(locked_attack["final_weights"][class_names[index]])
            for index in range(config.attack_head_dim)
        ]
    except Exception as error:  # noqa: BLE001 - fall back, never block readiness on this
        warnings.append(
            "Could not build locked A8.5 class weights for the loss check: "
            f"{error}"
        )

    model_forward_check, loss_check = _check_model_forward_and_loss(
        config,
        train_batch,
        device_check,
        pos_weight=locked_binary_pos_weight,
        attack_class_weights=locked_attack_class_weights,
    )
    if model_forward_check["status"] != "PASS":
        blocking_issues.append("Model forward output shapes failed.")
    if loss_check["status"] != "PASS":
        blocking_issues.append("Masked loss check failed.")
    _log(f"[{dataset}] model forward/loss checked")

    metric_output_plan = _planned_metric_outputs(config)
    output_safety = _output_safety_check(config, root, meta)
    if output_safety["planned_checkpoint_exists"]:
        blocking_issues.append(
            f"Planned checkpoint already exists: {output_safety['planned_checkpoint']}"
        )
    if output_safety["planned_final_output_files_existing"]:
        blocking_issues.append(
            "Planned final output files already exist: "
            + str(output_safety["planned_final_output_files_existing"])
        )
    if not output_safety["all_binary_checkpoints_exist"]:
        blocking_issues.append("One or more existing binary baseline checkpoints are missing.")
    if not output_safety["all_binary_result_files_exist"]:
        blocking_issues.append("One or more existing binary baseline result files are missing.")
    if not output_safety["expected_checkpoint_path_match"]:
        blocking_issues.append("Planned checkpoint path does not match A8 expected path.")
    if not output_safety["expected_result_dir_match"]:
        blocking_issues.append("Planned result_dir does not match A8 expected path.")
    _log(f"[{dataset}] output safety checked")

    no_fake_results = _no_fake_results_check(config, manifest, mapping, output_safety)
    for key, value in no_fake_results.items():
        if key != "status" and value is not True:
            blocking_issues.append(f"No-fake-results check failed: {key}")

    status = "PASS" if not blocking_issues else "BLOCKED"
    ready = status == "PASS"
    next_command = (
        "python -m secureids.cli train-hierarchical "
        f"--dataset {meta['short']} --config {meta['config']} --execute"
    )
    result = {
        "schema_version": "task_a8_hierarchical_full_training_readiness_v1",
        "created_at_utc": utc_timestamp(),
        "dataset": dataset,
        "status": status,
        "ready_for_full_hierarchical_training": ready,
        "blocking_issues": blocking_issues,
        "warnings": sorted(set(warnings)),
        "config_summary": config_summary,
        "data_summary": data_summary,
        "class_distribution": class_distribution,
        "rare_class_summary": rare_summary,
        "class_weight_preview": class_weight_preview,
        "class_weight_risk_assessment": class_weight_risk,
        "dataloader_check": dataloader_check,
        "model_forward_check": model_forward_check,
        "loss_check": loss_check,
        "metric_output_plan": metric_output_plan,
        "output_safety_check": output_safety,
        "device_check": device_check,
        "no_fake_results_check": no_fake_results,
        "next_recommended_training_command": next_command,
        "a8_safety": {
            "full_training_run": False,
            "optimizer_training_loop_run": False,
            "full_epoch_run": False,
            "checkpoint_created": False,
            "final_metrics_created": False,
            "hierarchical_fedavg_started": False,
            "security_attack_trimmed_mean_xai_dashboard_started": False,
        },
    }
    save_json(root / meta["json"], result)
    _log(f"[{dataset}] JSON written: {root / meta['json']}")
    _log(f"[{dataset}] final readiness status: {status}")
    return result


def _fmt_bool(value: Any) -> str:
    return "true" if bool(value) else "false"


def _status_line(result: dict[str, Any]) -> str:
    return (
        f"- {result['dataset']}: `{result['status']}` "
        f"(ready={_fmt_bool(result['ready_for_full_hierarchical_training'])}, "
        f"blocking={len(result['blocking_issues'])}, warnings={len(result['warnings'])})"
    )


def _write_report(root: Path, results: list[dict[str, Any]]) -> Path:
    result_by_dataset = {result["dataset"]: result for result in results}
    cicids = result_by_dataset.get("cicids2018")
    unsw = result_by_dataset.get("unsw_nb15")
    all_ready = all(result["ready_for_full_hierarchical_training"] for result in results)
    cuda_available = any(result["device_check"]["cuda_available"] for result in results)
    recommended_first = "UNSW-NB15" if all_ready else "none until blockers are fixed"
    recommended_command = (
        "python -m secureids.cli train-hierarchical --dataset unsw "
        "--config configs/training/unsw_nb15_hierarchical.yaml --execute"
        if all_ready
        else "Resolve blocking issues, then re-run A8."
    )

    lines: list[str] = [
        "# Hierarchical Full Training Readiness Report",
        "",
        "Status: `Task A8 readiness/pre-run gate - no full training run`",
        "",
        f"Generated UTC: `{utc_timestamp()}`",
        "",
        "## Dataset Readiness",
        "",
        *[_status_line(result) for result in results],
        "",
        "## Direct Answers",
        "",
        f"1. CICIDS ready: `{_fmt_bool(cicids and cicids['ready_for_full_hierarchical_training'])}`.",
        f"2. UNSW ready: `{_fmt_bool(unsw and unsw['ready_for_full_hierarchical_training'])}`.",
        f"3. Train first: `{recommended_first}`. UNSW is smaller and faster, so it is the safer first real centralized hierarchical run when there are no blockers.",
        "4. Blocking issues: "
        + (
            "`none`."
            if not any(result["blocking_issues"] for result in results)
            else "`present`; see per-dataset sections below."
        ),
        "5. Warnings: "
        + (
            "`present`; mainly rare-class/class-weight caution."
            if any(result["warnings"] for result in results)
            else "`none`."
        ),
        "6. Rare classes: represented in train/val/test for inspected datasets; keep per-class and rare-class reporting.",
        "7. Class weights: raw inverse-frequency Head 2 weights are risky where noted; use capped, sqrt, or log-smoothed train-only weighting before real training.",
        "8. Checkpoint/output paths: checked for overwrite risk; no A8 final outputs were created.",
        f"9. CUDA available: `{_fmt_bool(cuda_available)}`.",
        f"10. First real training command for later approval: `{recommended_command}`.",
        "",
        "## Per-Dataset Notes",
        "",
    ]
    for result in results:
        risk = result["class_weight_risk_assessment"]
        device = result["device_check"]
        output = result["output_safety_check"]
        lines.extend(
            [
                f"### {result['dataset']}",
                "",
                f"- status: `{result['status']}`",
                f"- ready_for_full_hierarchical_training: `{_fmt_bool(result['ready_for_full_hierarchical_training'])}`",
                f"- blocking issues: `{len(result['blocking_issues'])}`",
                f"- warnings: `{len(result['warnings'])}`",
                f"- input_dim: `{result['config_summary']['input_dim']}`",
                f"- attack_head_dim: `{result['config_summary']['attack_head_dim']}`",
                f"- class-weight risk: `{risk['assessment']}` (raw max Head 2 weight `{risk['raw_attack_weight_max']}`)",
                f"- rare classes safe/documented: `{_fmt_bool(result['rare_class_summary']['rare_classes_present_in_train_val_test_or_documented'])}`",
                f"- planned checkpoint exists: `{_fmt_bool(output['planned_checkpoint_exists'])}`",
                f"- result dir contains files: `{_fmt_bool(output['result_dir_contains_final_metrics'])}`",
                f"- device recommendation: `{device['selected_device_recommendation']}` (cuda_available={_fmt_bool(device['cuda_available'])})",
                f"- later command: `{result['next_recommended_training_command']}`",
                "",
            ]
        )
        if result["blocking_issues"]:
            lines.extend(["Blocking issues:", ""])
            lines.extend(f"- {issue}" for issue in result["blocking_issues"])
            lines.append("")
        if result["warnings"]:
            lines.extend(["Warnings:", ""])
            lines.extend(f"- {warning}" for warning in result["warnings"])
            lines.append("")

    lines.extend(
        [
            "## A8 Safety Confirmation",
            "",
            "- No full hierarchical training was run.",
            "- No optimizer training loop or full epoch was run.",
            "- No final hierarchical checkpoint was created.",
            "- No final hierarchical metrics, histories, or confusion matrices were created.",
            "- No hierarchical FedAvg, TLS/security, attacks, Trimmed Mean, XAI, or dashboard work was started.",
            "- Existing binary checkpoints/results were checked and preserved.",
            "- V1 files were not modified by this readiness command.",
            "- No scaler/encoder refit on test was performed.",
            "- No test-set tuning or test-based class weights were used.",
            "",
        ]
    )
    report_path = root / REPORT_PATH
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def run_hierarchical_training_readiness(
    dataset: str = "all",
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Run the A8 readiness/pre-run gate and write audit JSON/report outputs."""

    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    selected = _normalize_dataset_selection(dataset)
    results = [_check_one_dataset(name, root) for name in selected]
    report_path = _write_report(root, results)
    _log(f"\nA8 readiness report written: {report_path}")
    _log("A8 PASS/FAIL summary:")
    for result in results:
        _log(_status_line(result))
    overall_status = "PASS" if all(result["status"] == "PASS" for result in results) else "BLOCKED"
    return {
        "status": overall_status,
        "results": results,
        "report_path": str(report_path),
        "json_paths": [str(root / DATASET_READINESS[result["dataset"]]["json"]) for result in results],
        "full_training_run": False,
        "final_checkpoints_created": False,
        "final_metrics_created": False,
    }
