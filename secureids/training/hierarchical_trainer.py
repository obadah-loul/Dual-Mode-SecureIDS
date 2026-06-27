"""Real centralized hierarchical training for SecureIDS-HierarchicalAdvancedNet.

Task A9 trains ONE dataset's hierarchical model (UNSW-NB15 first) with the masked
multi-task loss and the A8.5/A8.8 locked train-only class weights. Execution
policy mirrors the binary centralized trainer:

* Nothing trains on import.
* ``run_hierarchical_training(..., execute=False)`` returns a read-only plan.
* ``run_hierarchical_training(..., execute=True)`` validates preconditions and
  runs the real training, selecting the best checkpoint by validation only and
  evaluating the test split exactly once after that selection.
"""

from __future__ import annotations

import copy
import csv
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

try:  # pragma: no cover - environment dependent
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None

from secureids.models.secureids_hierarchical_advanced_net import (
    SecureIDSHierarchicalAdvancedNet,
    compute_hierarchical_loss,
)
from secureids.preprocessing.artifacts import save_json, utc_timestamp
from secureids.training.centralized import resolve_device, set_global_seed
from secureids.training.checkpoints import save_checkpoint
from secureids.training.hierarchical_class_weights import build_train_only_class_weights
from secureids.training.hierarchical_config import (
    HierarchicalTrainingConfig,
    load_hierarchical_training_config,
)
from secureids.training.hierarchical_evaluation import (
    collect_hierarchical_outputs,
    evaluate_hierarchical,
)
from secureids.training.hierarchical_planning import build_hierarchical_training_plan

SPLITS = ("train", "val", "test")


class HierarchicalExecutePreconditionError(RuntimeError):
    """Raised when a precondition for real hierarchical training is not met."""


def _log(message: str) -> None:
    print(message, flush=True)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _class_names(mapping: dict[str, Any], attack_head_dim: int) -> list[str]:
    id_to_class = mapping.get("id_to_class", {})
    names: list[str] = []
    for index in range(int(attack_head_dim)):
        key = str(index)
        if not isinstance(id_to_class, dict) or key not in id_to_class:
            raise HierarchicalExecutePreconditionError(
                f"attack_family mapping is missing id_to_class entry for class {index}."
            )
        names.append(str(id_to_class[key]))
    return names


def build_model(config: HierarchicalTrainingConfig) -> SecureIDSHierarchicalAdvancedNet:
    model_cfg = config.raw.get("model", {})
    # Head 2 capacity options are optional and backward-compatible: when absent,
    # attack_head_type defaults to "linear" (the A9 baseline architecture).
    attack_head_hidden_dim = model_cfg.get("attack_head_hidden_dim")
    attack_head_dropout = model_cfg.get("attack_head_dropout")
    return SecureIDSHierarchicalAdvancedNet(
        input_dim=config.input_dim,
        attack_head_dim=config.attack_head_dim,
        hidden_dims=tuple(model_cfg.get("hidden_dims", (256, 128, 128))),
        dropout=float(model_cfg.get("dropout", 0.20)),
        normalization=str(model_cfg.get("normalization", "layernorm")),
        attack_head_type=str(model_cfg.get("attack_head_type", "linear")),
        attack_head_hidden_dim=(
            int(attack_head_hidden_dim) if attack_head_hidden_dim is not None else None
        ),
        attack_head_norm=bool(model_cfg.get("attack_head_norm", True)),
        attack_head_dropout=(
            float(attack_head_dropout) if attack_head_dropout is not None else None
        ),
    )


# --------------------------------------------------------------------------- #
# Data loading (memory-safe: UNSW fits in RAM; loaded once as tensors)
# --------------------------------------------------------------------------- #
def _load_split_arrays(data_dir: Path, split: str) -> dict[str, np.ndarray]:
    return {
        "X": np.load(data_dir / f"X_{split}.npy"),
        "y_binary": np.load(data_dir / f"y_binary_{split}.npy"),
        "y_attack_family": np.load(data_dir / f"y_attack_family_{split}.npy"),
        "attack_family_mask": np.load(data_dir / f"attack_family_mask_{split}.npy"),
    }


def _validate_split_labels(
    arrays: dict[str, np.ndarray],
    split: str,
    input_dim: int,
    attack_head_dim: int,
) -> list[str]:
    issues: list[str] = []
    X = arrays["X"]
    yb = np.asarray(arrays["y_binary"]).reshape(-1).astype(np.int64)
    ya = np.asarray(arrays["y_attack_family"]).reshape(-1).astype(np.int64)
    mask = np.asarray(arrays["attack_family_mask"]).reshape(-1).astype(np.int64)
    rows = int(X.shape[0])
    if X.ndim != 2 or int(X.shape[1]) != int(input_dim):
        issues.append(f"{split}: X shape {X.shape} does not match input_dim {input_dim}.")
    if not (yb.shape[0] == ya.shape[0] == mask.shape[0] == rows):
        issues.append(f"{split}: label/mask lengths do not match X rows ({rows}).")
    if not np.isin(yb, [0, 1]).all():
        issues.append(f"{split}: y_binary has values outside {{0,1}}.")
    if not np.isin(mask, [0, 1]).all():
        issues.append(f"{split}: attack_family_mask has values outside {{0,1}}.")
    if not np.array_equal(yb, mask):
        issues.append(f"{split}: y_binary and attack_family_mask disagree.")
    benign = mask == 0
    attack = mask == 1
    if not np.all(ya[benign] == -1):
        issues.append(f"{split}: benign/mask-0 rows must have y_attack_family == -1.")
    if attack.any():
        valid = (ya[attack] >= 0) & (ya[attack] < int(attack_head_dim))
        if not np.all(valid):
            issues.append(f"{split}: attack rows have invalid Head 2 labels.")
    # Finite-check the features without upcasting to float64 (float32-safe). This
    # avoids a large transient copy for big arrays (e.g. CICIDS ~6.7M x 77 would
    # otherwise allocate ~4 GB of float64). Integer/bool feature arrays are always
    # finite, so only floating arrays need the np.isfinite scan.
    X_arr = np.asarray(X)
    if np.issubdtype(X_arr.dtype, np.floating) and not np.isfinite(X_arr).all():
        issues.append(f"{split}: X contains non-finite values.")
    return issues


def _split_to_tensors(arrays: dict[str, np.ndarray]) -> tuple[torch.Tensor, ...]:
    X = torch.from_numpy(np.ascontiguousarray(arrays["X"], dtype=np.float32))
    yb = torch.from_numpy(np.ascontiguousarray(arrays["y_binary"]).astype(np.float32)).reshape(-1)
    ya = torch.from_numpy(np.ascontiguousarray(arrays["y_attack_family"]).astype(np.int64)).reshape(-1)
    mask = torch.from_numpy(np.ascontiguousarray(arrays["attack_family_mask"]).astype(np.int64)).reshape(-1)
    return X, yb, ya, mask


def _make_loader(tensors: tuple[torch.Tensor, ...], batch_size: int, shuffle: bool, seed: int) -> DataLoader:
    dataset = TensorDataset(*tensors)
    generator = None
    if shuffle:
        generator = torch.Generator()
        generator.manual_seed(int(seed))
    return DataLoader(
        dataset,
        batch_size=int(batch_size),
        shuffle=shuffle,
        drop_last=False,
        num_workers=0,
        generator=generator,
    )


# --------------------------------------------------------------------------- #
# Train / fit
# --------------------------------------------------------------------------- #
def _train_one_epoch(
    model: torch.nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    loss_weights: dict[str, Any],
    pos_weight: torch.Tensor,
    attack_class_weights: torch.Tensor,
) -> dict[str, float]:
    model.train()
    totals = {"total": 0.0, "binary": 0.0, "attack": 0.0}
    seen = 0
    for features, yb, ya, mask in loader:
        features = features.to(device)
        yb = yb.to(device)
        ya = ya.to(device)
        mask = mask.to(device)
        optimizer.zero_grad()
        outputs = model(features)
        bundle = compute_hierarchical_loss(
            outputs,
            y_binary=yb,
            y_attack_family=ya,
            attack_family_mask=mask,
            binary_loss_weight=float(loss_weights["binary_loss_weight"]),
            attack_loss_weight=float(loss_weights["attack_loss_weight"]),
            ignore_index=int(loss_weights["ignore_index"]),
            pos_weight=pos_weight,
            attack_class_weights=attack_class_weights,
        )
        total_loss = bundle["total_loss"]
        if not torch.isfinite(total_loss):
            raise HierarchicalExecutePreconditionError(
                "Training loss became non-finite (NaN/Inf); stopping."
            )
        total_loss.backward()
        optimizer.step()
        batch = features.size(0)
        totals["total"] += float(total_loss.item()) * batch
        totals["binary"] += float(bundle["binary_loss"].item()) * batch
        totals["attack"] += float(bundle["attack_loss"].item()) * batch
        seen += batch
    denom = max(seen, 1)
    return {key: value / denom for key, value in totals.items()}


def fit_hierarchical(
    config: HierarchicalTrainingConfig,
    class_names: list[str],
    rare_class_names: list[str],
    weights: dict[str, Any],
    device: torch.device,
    verbose: bool = True,
) -> dict[str, Any]:
    """Train the hierarchical model; select best checkpoint by validation only."""

    training_cfg = config.raw.get("training", {})
    loss_cfg = config.raw.get("loss", {})
    seed = int(training_cfg.get("seed", 42))
    batch_size = int(training_cfg.get("batch_size", 1024))
    max_epochs = int(training_cfg.get("max_epochs", 40))
    patience = int(training_cfg.get("early_stopping_patience", 6))
    threshold = 0.5

    set_global_seed(seed)
    data_dir = config.resolve(config.hierarchical_data_dir)

    arrays = {split: _load_split_arrays(data_dir, split) for split in SPLITS}
    tensors = {split: _split_to_tensors(arrays[split]) for split in SPLITS}
    train_loader = _make_loader(tensors["train"], batch_size, shuffle=True, seed=seed)
    val_loader = _make_loader(tensors["val"], batch_size, shuffle=False, seed=seed)
    test_loader = _make_loader(tensors["test"], batch_size, shuffle=False, seed=seed)

    train_binary = np.asarray(arrays["train"]["y_binary"]).reshape(-1).astype(np.int64)
    class_distribution_train = {
        "0": int(np.sum(train_binary == 0)),
        "1": int(np.sum(train_binary == 1)),
    }

    model = build_model(config).to(device)
    pos_weight = torch.tensor([float(weights["binary_pos_weight"])], dtype=torch.float32, device=device)
    attack_class_weights = torch.tensor(
        [float(w) for w in weights["attack_class_weights"]], dtype=torch.float32, device=device
    )
    loss_weights = {
        "binary_loss_weight": float(loss_cfg.get("binary_loss_weight", 1.0)),
        "attack_loss_weight": float(loss_cfg.get("attack_loss_weight", 1.0)),
        "ignore_index": int(loss_cfg.get("ignore_index", -1)),
    }
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(training_cfg.get("learning_rate", 0.001)),
        weight_decay=float(training_cfg.get("weight_decay", 0.0001)),
    )

    best_score = -float("inf")
    best_state: dict[str, Any] | None = None
    best_epoch = -1
    best_val_bundle: dict[str, Any] | None = None
    patience_counter = 0
    history: list[dict[str, Any]] = []

    for epoch in range(max_epochs):
        epoch_start = time.perf_counter()
        train_losses = _train_one_epoch(
            model, train_loader, optimizer, device, loss_weights, pos_weight, attack_class_weights
        )
        val_collected = collect_hierarchical_outputs(model, val_loader, device)
        val_bundle = evaluate_hierarchical(
            val_collected, class_names, rare_class_names, threshold=threshold
        )
        selection = val_bundle["selection"]
        score = float(selection["val_hierarchical_score"])
        epoch_seconds = time.perf_counter() - epoch_start

        improved = score > best_score
        if improved:
            best_score = score
            best_epoch = epoch + 1
            best_state = copy.deepcopy(model.state_dict())
            best_val_bundle = val_bundle
            patience_counter = 0
        else:
            patience_counter += 1

        history.append(
            {
                "epoch": epoch + 1,
                "train_total_loss": round(train_losses["total"], 6),
                "train_binary_loss": round(train_losses["binary"], 6),
                "train_attack_loss": round(train_losses["attack"], 6),
                "val_binary_macro_f1": round(selection["val_binary_macro_f1"], 6),
                "val_attack_family_macro_f1": round(selection["val_attack_family_macro_f1"], 6),
                "val_hierarchical_score": round(score, 6),
                "val_binary_accuracy": round(val_bundle["binary"]["accuracy"], 6),
                "val_binary_f1": round(val_bundle["binary"]["f1"], 6),
                "val_attack_family_accuracy": round(
                    val_bundle["attack_family"]["accuracy_on_attack_rows"], 6
                ),
                "val_rare_class_macro_f1": (
                    round(val_bundle["rare_class"]["rare_class_macro_f1"], 6)
                    if val_bundle["rare_class"]["rare_class_macro_f1"] is not None
                    else ""
                ),
                "learning_rate": float(optimizer.param_groups[0]["lr"]),
                "epoch_seconds": round(epoch_seconds, 4),
                "best_checkpoint_so_far": bool(improved),
            }
        )

        if verbose:
            marker = " *best" if improved else ""
            _log(
                f"[epoch {epoch + 1}/{max_epochs}] "
                f"train_total={train_losses['total']:.4f} "
                f"(bin={train_losses['binary']:.4f}, atk={train_losses['attack']:.4f}) "
                f"val_bin_macroF1={selection['val_binary_macro_f1']:.4f} "
                f"val_atk_macroF1={selection['val_attack_family_macro_f1']:.4f} "
                f"val_score={score:.4f} ({epoch_seconds:.1f}s){marker}"
            )

        if not improved and patience_counter >= patience:
            if verbose:
                _log(
                    f"Early stopping at epoch {epoch + 1} "
                    f"(no val improvement for {patience_counter} epochs)."
                )
            break

    if best_state is not None:
        model.load_state_dict(best_state)

    # Test evaluated exactly once, after best-validation-checkpoint selection.
    test_collected = collect_hierarchical_outputs(model, test_loader, device)
    test_bundle = evaluate_hierarchical(
        test_collected, class_names, rare_class_names, threshold=threshold
    )

    cpu_state = {key: value.detach().cpu() for key, value in (best_state or model.state_dict()).items()}

    return {
        "best_epoch": best_epoch,
        "best_val_hierarchical_score": best_score,
        "epochs_run": len(history),
        "history": history,
        "best_val_bundle": best_val_bundle,
        "test_bundle": test_bundle,
        "best_state_dict": cpu_state,
        "class_distribution_train": class_distribution_train,
        "threshold": threshold,
        "device": str(device),
        "architecture_metadata": model.architecture_metadata,
        "param_count": int(sum(p.numel() for p in model.parameters())),
    }


# --------------------------------------------------------------------------- #
# Preconditions
# --------------------------------------------------------------------------- #
def _dataset_precondition_errors(
    config: HierarchicalTrainingConfig,
    project_root: Path,
) -> list[str]:
    """Dataset-aware non-data preconditions (uses the canonical ``config.dataset``).

    UNSW-NB15 must have its split-protocol / A8.8 high-findings-resolution evidence
    in place (preserved exactly). CICIDS2018 has **no** UNSW/A8.8 file dependency:
    it relies on the dataset-agnostic checks in ``validate_execute_preconditions``
    (config validation, the read-only plan, the per-dataset class-weight strategy
    PASS, the overwrite guard, and the per-split finite label/data checks). Any
    other dataset fails clearly. This never reads a CLI alias.
    """

    errors: list[str] = []
    if config.dataset == "unsw_nb15":
        decision_doc = project_root / "docs" / "UNSW_SPLIT_PROTOCOL_DECISION.md"
        resolution_json = (
            project_root / "results" / "audits" / "pre_training_high_findings_resolution.json"
        )
        if not decision_doc.exists():
            errors.append(f"UNSW: missing UNSW split protocol decision doc: {decision_doc}.")
        if not resolution_json.exists():
            errors.append(f"UNSW: missing A8.8 high-findings resolution json: {resolution_json}.")
        else:
            resolution = _load_json(resolution_json)
            if resolution.get("ready_for_unsw_training") is not True:
                errors.append(
                    "UNSW: pre_training_high_findings_resolution.json "
                    "ready_for_unsw_training is not true."
                )
    elif config.dataset == "cicids2018":
        # CICIDS2018 has no UNSW/A8.8 dependency; dataset-agnostic checks suffice.
        pass
    else:
        errors.append(
            "unsupported dataset for hierarchical training preconditions: "
            f"{config.dataset!r}."
        )
    return errors


def validate_execute_preconditions(
    config: HierarchicalTrainingConfig,
    project_root: Path,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Validate everything required before real hierarchical training."""

    errors: list[str] = []
    device = resolve_device()
    cuda_available = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if cuda_available else None

    if config.task != "hierarchical":
        errors.append(f"task must be 'hierarchical', got {config.task!r}.")
    if config.model_name != "SecureIDSHierarchicalAdvancedNet":
        errors.append(f"unexpected model_name {config.model_name!r}.")

    # Read-only plan covers data dir, feature/class counts, readiness/manifest PASS,
    # and array shapes/feature-dim. We ignore only the "future outputs absent" check
    # when --overwrite is given.
    plan = build_hierarchical_training_plan(config)
    for check in plan["checks"]:
        if check["status"] == "PASS":
            continue
        if check["name"] == "future_final_outputs_absent" and overwrite:
            continue
        errors.append(f"plan check failed [{check['name']}]: {check['detail']}")

    # Dataset-aware precondition gate: UNSW requires its split-protocol/A8.8
    # evidence; CICIDS (and the canonical-dataset check) do not depend on UNSW
    # files. The dataset-agnostic checks below still apply to every dataset.
    errors.extend(_dataset_precondition_errors(config, project_root))

    # Class-weight strategy PASS for this dataset (applies to every dataset).
    cw_json = project_root / "results" / "audits" / f"hierarchical_class_weight_strategy_{config.dataset}.json"
    if not cw_json.exists():
        errors.append(f"missing class-weight strategy json: {cw_json}.")
    else:
        cw = _load_json(cw_json)
        if cw.get("status") != "PASS":
            errors.append(f"class-weight strategy is not PASS for {config.dataset}.")

    # Checkpoint / result overwrite guard.
    checkpoint_path = config.resolve(config.outputs["checkpoint"])
    result_dir = config.resolve(config.outputs["result_dir"])
    if checkpoint_path.exists() and not overwrite:
        errors.append(
            f"planned checkpoint already exists: {checkpoint_path}. Re-run with --overwrite to replace."
        )
    existing_final = [
        str(config.resolve(value))
        for key, value in config.outputs.items()
        if key != "result_dir" and config.resolve(value).exists()
    ]
    if existing_final and not overwrite:
        errors.append(
            "refusing to overwrite existing final outputs (use --overwrite): " + str(existing_final)
        )

    # Label/mask validity per split (no leakage, masks consistent).
    data_dir = config.resolve(config.hierarchical_data_dir)
    split_label_issues: list[str] = []
    for split in SPLITS:
        arrays = _load_split_arrays(data_dir, split)
        split_label_issues.extend(
            _validate_split_labels(arrays, split, config.input_dim, config.attack_head_dim)
        )
    errors.extend(split_label_issues)

    if errors:
        raise HierarchicalExecutePreconditionError(
            "Pre-run validation failed:\n- " + "\n- ".join(errors)
        )

    # Ensure output dirs exist.
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)
    config.resolve(config.outputs["manifest_json"]).parent.mkdir(parents=True, exist_ok=True)

    return {
        "device": device,
        "cuda_available": cuda_available,
        "gpu_name": gpu_name,
        "plan_status": plan["status"],
        "feature_count": plan["feature_count"],
        "attack_family_class_count": plan["attack_family_class_count"],
        "split_shapes": plan["split_shapes"],
    }


# --------------------------------------------------------------------------- #
# Output writers
# --------------------------------------------------------------------------- #
HISTORY_FIELDNAMES: tuple[str, ...] = (
    "epoch",
    "train_total_loss",
    "train_binary_loss",
    "train_attack_loss",
    "val_binary_macro_f1",
    "val_attack_family_macro_f1",
    "val_hierarchical_score",
    "val_binary_accuracy",
    "val_binary_f1",
    "val_attack_family_accuracy",
    "val_rare_class_macro_f1",
    "learning_rate",
    "epoch_seconds",
    "best_checkpoint_so_far",
)


def _configured_output_path(
    config: HierarchicalTrainingConfig,
    key: str,
    default_path: Path,
) -> Path:
    configured = config.outputs.get(key)
    return config.resolve(configured) if configured else default_path


def _write_history_csv(path: Path, history: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(HISTORY_FIELDNAMES), restval="")
        writer.writeheader()
        for row in history:
            writer.writerow(row)


def _write_binary_confusion_csv(path: Path, cm: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["true_label", "predicted_label", "count"])
        writer.writerow([0, 0, cm["tn"]])
        writer.writerow([0, 1, cm["fp"]])
        writer.writerow([1, 0, cm["fn"]])
        writer.writerow([1, 1, cm["tp"]])


def _write_attack_confusion_csv(path: Path, cm: list[list[int]], class_names: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["true\\pred", *class_names])
        for index, row in enumerate(cm):
            writer.writerow([class_names[index], *row])


def _write_per_class_csv(path: Path, per_class: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["class_id", "class_name", "precision", "recall", "f1", "support"])
        for entry in per_class:
            writer.writerow(
                [
                    entry["class_id"],
                    entry["class_name"],
                    round(float(entry["precision"]), 6),
                    round(float(entry["recall"]), 6),
                    round(float(entry["f1"]), 6),
                    int(entry["support"]),
                ]
            )


def _write_rare_class_csv(path: Path, rare: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["class_name", "precision", "recall", "f1", "support"])
        rare_support = 0
        for entry in rare.get("per_rare_class", []):
            if entry.get("present"):
                rare_support += int(entry["support"])
                writer.writerow(
                    [
                        entry["class_name"],
                        round(float(entry["precision"]), 6),
                        round(float(entry["recall"]), 6),
                        round(float(entry["f1"]), 6),
                        int(entry["support"]),
                    ]
                )
            else:
                writer.writerow([entry["class_name"], "", "", "", 0])
        macro = rare.get("rare_class_macro_f1")
        writer.writerow(
            ["rare_class_macro_f1", "", "", round(float(macro), 6) if macro is not None else "", rare_support]
        )


def _dataset_report_metadata(config: HierarchicalTrainingConfig) -> dict[str, Any]:
    """Dataset-aware wording for reports / manifests / metrics payloads.

    H2 fix: removes hardcoded UNSW/A8.8 text so CICIDS runs are labeled CICIDS2018
    (and never mention UNSW/A8.8), while UNSW runs keep their exact prior wording.
    This is metadata only; it does not change any metric computation.
    """

    dataset = config.dataset
    if dataset == "unsw_nb15":
        return {
            "display_name": "UNSW-NB15",
            "report_title": "Hierarchical Training Report (UNSW-NB15)",
            "report_status": (
                "Real centralized hierarchical training "
                "(UNSW-NB15, A8.8 corrected benchmark protocol)"
            ),
            "protocol": (
                "A8.8 corrected UNSW benchmark protocol "
                "(train 175,341-row partition; test 82,332-row partition)"
            ),
            "protocol_short": "A8.8 corrected UNSW benchmark protocol",
            "scope_lines": [
                "- This is the **corrected UNSW-NB15 benchmark protocol** (A8.8): train/val on the",
                "  175,341-row canonical training partition, final test on the 82,332-row canonical",
                "  testing partition.",
                "- The old UNSW binary centralized/FedAvg baselines are **legacy / pre-correction**",
                "  and are NOT final hierarchical results.",
            ],
            "safety_confirmation_lines": [
                "- Old UNSW pre-correction baselines preserved as legacy, not used as final.",
                "- No FedAvg / security / Byzantine / Trimmed Mean / XAI / dashboard started.",
                "- CICIDS hierarchical training not run. V1 not modified. No Git operations.",
            ],
            "safety_notes": {
                "old_unsw_pre_correction_baselines_used_as_final": False,
                "cicids_hierarchical_training_run": False,
            },
            "manifest_safety": {
                "old_unsw_pre_correction_baselines_used_as_final": False,
                "cicids_hierarchical_training_run": False,
            },
        }
    if dataset == "cicids2018":
        return {
            "display_name": "CICIDS2018",
            "report_title": "Hierarchical Training Report (CICIDS2018)",
            "report_status": "Real centralized hierarchical training (CICIDS2018)",
            "protocol": (
                "CICIDS2018 hierarchical benchmark protocol "
                "(stratified train/validation/test split)"
            ),
            "protocol_short": "CICIDS2018 hierarchical benchmark protocol",
            "scope_lines": [
                "- This is the **CICIDS2018 hierarchical benchmark protocol**: a stratified",
                "  train/validation/test split of the processed CICIDS2018 flows.",
                "- The CICIDS2018 binary centralized/FedAvg baselines are separate prior",
                "  artifacts and are NOT these final hierarchical results.",
            ],
            "safety_confirmation_lines": [
                "- Prior CICIDS2018 binary baselines preserved; not used as final hierarchical results.",
                "- No FedAvg / security / Byzantine / Trimmed Mean / XAI / dashboard started.",
                "- V1 not modified. No Git operations.",
            ],
            "safety_notes": {
                "other_dataset_pre_correction_baselines_used_as_final": False,
                "single_dataset_hierarchical_run": True,
            },
            "manifest_safety": {
                "other_dataset_pre_correction_baselines_used_as_final": False,
                "single_dataset_hierarchical_run": True,
            },
        }
    name = str(dataset)
    return {
        "display_name": name,
        "report_title": f"Hierarchical Training Report ({name})",
        "report_status": f"Real centralized hierarchical training ({name})",
        "protocol": f"{name} hierarchical training protocol",
        "protocol_short": f"{name} hierarchical training protocol",
        "scope_lines": [
            f"- This is the **{name} hierarchical training protocol**.",
        ],
        "safety_confirmation_lines": [
            "- Prior binary baselines preserved; not used as final hierarchical results.",
            "- No FedAvg / security / Byzantine / Trimmed Mean / XAI / dashboard started.",
            "- V1 not modified. No Git operations.",
        ],
        "safety_notes": {"single_dataset_hierarchical_run": True},
        "manifest_safety": {"single_dataset_hierarchical_run": True},
    }


def _build_test_metrics_payload(
    config: HierarchicalTrainingConfig,
    result: dict[str, Any],
    checkpoint_path: Path,
) -> dict[str, Any]:
    test = result["test_bundle"]
    best_val = result["best_val_bundle"] or {}
    val_selection = best_val.get("selection", {})
    meta = _dataset_report_metadata(config)
    return {
        "dataset": config.dataset,
        "task": config.task,
        "model": "SecureIDSHierarchicalAdvancedNet",
        "protocol": meta["protocol"],
        "checkpoint_path": str(checkpoint_path),
        "input_dim": config.input_dim,
        "attack_head_dim": config.attack_head_dim,
        "threshold": result["threshold"],
        "checkpoint_selected_by": "validation_only (val_hierarchical_score = 0.5*val_binary_macro_f1 + 0.5*val_attack_family_macro_f1)",
        "best_epoch": result["best_epoch"],
        "best_val_hierarchical_score": round(float(result["best_val_hierarchical_score"]), 6),
        "validation_at_best_epoch": {
            "val_binary_macro_f1": val_selection.get("val_binary_macro_f1"),
            "val_attack_family_macro_f1": val_selection.get("val_attack_family_macro_f1"),
            "val_hierarchical_score": val_selection.get("val_hierarchical_score"),
        },
        "test_metrics": {
            "binary": test["binary"],
            "attack_family": {
                "accuracy_on_attack_rows": test["attack_family"]["accuracy_on_attack_rows"],
                "macro_f1_on_attack_rows": test["attack_family"]["macro_f1_on_attack_rows"],
                "attack_rows_evaluated": test["attack_family"]["attack_rows_evaluated"],
                "per_class": test["attack_family"]["per_class"],
            },
            "rare_class": test["rare_class"],
            "hierarchical_routing": test["hierarchical_routing"],
        },
        "safety_notes": {
            "no_fake_metrics": True,
            "test_evaluated_once_after_best_validation_checkpoint": True,
            "checkpoint_not_selected_by_test_metrics": True,
            "class_weights_train_only": True,
            "validation_or_test_labels_used_for_weights": False,
            "no_federated_training": True,
            "no_security_or_attack_simulation": True,
            "no_xai_or_dashboard": True,
            **meta["safety_notes"],
        },
        "created_utc": utc_timestamp(),
    }


def _write_extra_result_files(
    config: HierarchicalTrainingConfig,
    result: dict[str, Any],
    weights: dict[str, Any],
    result_dir: Path,
) -> dict[str, str]:
    routing_path = _configured_output_path(
        config,
        "hierarchical_routing_summary_json",
        result_dir / "hierarchical_routing_summary.json",
    )
    save_json(
        routing_path,
        {
            "dataset": config.dataset,
            "test_routing": result["test_bundle"]["hierarchical_routing"],
            "validation_routing_at_best_epoch": (result["best_val_bundle"] or {}).get(
                "hierarchical_routing"
            ),
            "definitions": {
                "benign_correctly_stopped": "true benign predicted benign by Head 1",
                "attack_detected_and_correctly_attributed": "true attack predicted attack and Head 2 family correct",
                "attack_detected_wrong_family": "true attack predicted attack but Head 2 family wrong",
                "attack_missed_as_benign": "true attack predicted benign by Head 1",
            },
            "created_utc": utc_timestamp(),
        },
    )

    weight_snapshot_path = _configured_output_path(
        config,
        "class_weight_snapshot_json",
        result_dir / "class_weight_snapshot.json",
    )
    save_json(
        weight_snapshot_path,
        {
            "dataset": config.dataset,
            "source_split": "train",
            "computed_from_train_only": True,
            "validation_labels_used": False,
            "test_labels_used": False,
            "weight_cap": weights.get("weight_cap"),
            "binary_pos_weight": weights["binary_pos_weight"],
            "binary_class_weights": weights["binary_class_weights"],
            "attack_class_weights": weights["attack_class_weights"],
            "attack_class_weights_by_name": weights["attack_class_weights_by_name"],
            "id_to_class": weights["id_to_class"],
            "created_utc": utc_timestamp(),
        },
    )

    model_summary_path = _configured_output_path(
        config,
        "model_summary_json",
        result_dir / "model_summary.json",
    )
    save_json(
        model_summary_path,
        {
            "architecture": "SecureIDSHierarchicalAdvancedNet",
            "architecture_metadata": result["architecture_metadata"],
            "param_count": result["param_count"],
            "input_dim": config.input_dim,
            "attack_head_dim": config.attack_head_dim,
            "created_utc": utc_timestamp(),
        },
    )

    config_snapshot_path = _configured_output_path(
        config,
        "training_config_snapshot_yaml",
        result_dir / "training_config_snapshot.yaml",
    )
    if yaml is not None:
        config_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        config_snapshot_path.write_text(
            yaml.safe_dump(config.raw, sort_keys=False), encoding="utf-8"
        )
    else:  # pragma: no cover
        config_snapshot_json = _configured_output_path(
            config,
            "training_config_snapshot_json",
            result_dir / "training_config_snapshot.json",
        )
        save_json(config_snapshot_json, config.raw)
        config_snapshot_path = config_snapshot_json

    return {
        "hierarchical_routing_summary": str(routing_path),
        "class_weight_snapshot": str(weight_snapshot_path),
        "model_summary": str(model_summary_path),
        "training_config_snapshot": str(config_snapshot_path),
    }


def _write_report(
    config: HierarchicalTrainingConfig,
    result: dict[str, Any],
    checkpoint_path: Path,
    project_root: Path,
) -> Path:
    test = result["test_bundle"]
    binary = test["binary"]
    cm = binary["confusion_matrix"]
    af = test["attack_family"]
    rare = test["rare_class"]
    routing = test["hierarchical_routing"]
    best_val = (result["best_val_bundle"] or {}).get("selection", {})
    meta = _dataset_report_metadata(config)

    lines = [
        f"# {meta['report_title']}",
        "",
        f"Status: `{meta['report_status']}`",
        "",
        f"Generated UTC: `{utc_timestamp()}`",
        "",
        "## Scope and protocol",
        "",
        *meta["scope_lines"],
        f"- `input_dim` = **{config.input_dim}**; `attack_head_dim` = **{config.attack_head_dim}**.",
        "- Model: `SecureIDSHierarchicalAdvancedNet` (shared encoder + binary Head 1 +",
        "  dataset-aware attack-family Head 2).",
        "- Checkpoint selected by **validation only**",
        "  (`val_hierarchical_score = 0.5*val_binary_macro_f1 + 0.5*val_attack_family_macro_f1`).",
        "- Test evaluated **once** after the best validation checkpoint was selected.",
        "- Class weights computed from the **train split only** (no validation/test labels);",
        "  no test-set tuning.",
        "- Not started yet: hierarchical FedAvg, security/SHA-256, Byzantine attacks,",
        "  Trimmed Mean, XAI, dashboard.",
        "",
        "## Training",
        "",
        f"- Device: `{result['device']}`",
        f"- Best epoch: `{result['best_epoch']}` (epochs run: `{result['epochs_run']}`)",
        f"- Best validation hierarchical score: `{round(float(result['best_val_hierarchical_score']), 6)}`",
        f"- Validation binary macro-F1 (best epoch): `{best_val.get('val_binary_macro_f1')}`",
        f"- Validation attack-family macro-F1 (best epoch): `{best_val.get('val_attack_family_macro_f1')}`",
        f"- Train class distribution (binary): `{result['class_distribution_train']}`",
        f"- Model parameters: `{result['param_count']:,}`",
        "",
        "## Final test - Head 1 (binary)",
        "",
        f"- accuracy: `{binary['accuracy']:.6f}`",
        f"- precision: `{binary['precision']:.6f}`",
        f"- recall: `{binary['recall']:.6f}`",
        f"- f1: `{binary['f1']:.6f}`",
        f"- macro_f1: `{binary['macro_f1']:.6f}`",
        f"- attack false negatives (attacks predicted benign): `{binary['attack_false_negatives']}`",
        f"- confusion (tn,fp,fn,tp): `{cm['tn']}, {cm['fp']}, {cm['fn']}, {cm['tp']}`",
        f"- n_samples: `{binary['n_samples']}`",
        "",
        "## Final test - Head 2 (attack-family, attack rows only)",
        "",
        f"- accuracy on attack rows: `{af['accuracy_on_attack_rows']:.6f}`",
        f"- macro-F1 on attack rows (all {config.attack_head_dim} classes): `{af['macro_f1_on_attack_rows']:.6f}`",
        f"- attack rows evaluated: `{af['attack_rows_evaluated']}`",
        "",
        "| Class | Precision | Recall | F1 | Support |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for entry in af["per_class"]:
        lines.append(
            f"| `{entry['class_name']}` | {entry['precision']:.4f} | {entry['recall']:.4f} | "
            f"{entry['f1']:.4f} | {entry['support']} |"
        )
    lines.extend(
        [
            "",
            "## Final test - rare classes",
            "",
            f"- rare-class macro-F1 ({', '.join(rare.get('rare_classes', [])) or 'rare classes'}): "
            f"`{rare['rare_class_macro_f1'] if rare['rare_class_macro_f1'] is not None else 'n/a'}`",
            "",
            "| Rare class | Precision | Recall | F1 | Support |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for entry in rare["per_rare_class"]:
        if entry.get("present"):
            lines.append(
                f"| `{entry['class_name']}` | {entry['precision']:.4f} | {entry['recall']:.4f} | "
                f"{entry['f1']:.4f} | {entry['support']} |"
            )
        else:
            lines.append(f"| `{entry['class_name']}` | n/a | n/a | n/a | 0 |")
    lines.extend(
        [
            "",
            "## Final test - end-to-end routing",
            "",
            f"- benign correctly stopped: `{routing['benign_correctly_stopped']}` "
            f"({routing['benign_correctly_stopped_rate']:.4f} of {routing['benign_total']} benign)",
            f"- attack detected and correctly attributed: `{routing['attack_detected_and_correctly_attributed']}` "
            f"({routing['attack_detected_and_correctly_attributed_rate']:.4f} of {routing['attack_total']} attacks)",
            f"- attack detected but wrong family: `{routing['attack_detected_wrong_family']}` "
            f"({routing['attack_detected_wrong_family_rate']:.4f})",
            f"- attack missed as benign: `{routing['attack_missed_as_benign']}` "
            f"({routing['attack_missed_as_benign_rate']:.4f})",
            "",
            "## Output artifacts",
            "",
            f"- checkpoint: `{checkpoint_path}`",
            f"- result dir: `{config.resolve(config.outputs['result_dir'])}`",
            f"- training manifest: `{config.resolve(config.outputs['manifest_json'])}`",
            "",
            "## Safety confirmation",
            "",
            "- Checkpoint selected by validation only; test evaluated once after selection.",
            "- No test-set tuning; class weights from train split only.",
            *meta["safety_confirmation_lines"],
            "",
        ]
    )
    report_path = _configured_output_path(
        config,
        "report_md",
        project_root / "docs" / "HIERARCHICAL_TRAINING_REPORT.md",
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def _build_manifest(
    config: HierarchicalTrainingConfig,
    config_path: Path | str,
    result: dict[str, Any],
    weights: dict[str, Any],
    preflight: dict[str, Any],
    checkpoint_path: Path,
    output_paths: dict[str, str],
) -> dict[str, Any]:
    training_cfg = config.raw.get("training", {})
    meta = _dataset_report_metadata(config)
    return {
        "schema_version": "task_a9_hierarchical_training_manifest_v1",
        "dataset": config.dataset,
        "task": config.task,
        "model": "SecureIDSHierarchicalAdvancedNet",
        "protocol": meta["protocol_short"],
        "created_utc": utc_timestamp(),
        "config_path": str(config_path),
        "input_dim": config.input_dim,
        "attack_head_dim": config.attack_head_dim,
        "feature_count": preflight["feature_count"],
        "attack_family_class_count": preflight["attack_family_class_count"],
        "hierarchical_data_dir": str(config.resolve(config.hierarchical_data_dir)),
        "split_shapes": preflight["split_shapes"],
        "class_distribution_train": result["class_distribution_train"],
        "device": result["device"],
        "cuda_available": preflight["cuda_available"],
        "gpu_name": preflight["gpu_name"],
        "seed": int(training_cfg.get("seed", 42)),
        "training_params": {
            "batch_size": int(training_cfg.get("batch_size", 1024)),
            "max_epochs": int(training_cfg.get("max_epochs", 40)),
            "learning_rate": float(training_cfg.get("learning_rate", 0.001)),
            "optimizer": str(training_cfg.get("optimizer", "adamw")),
            "weight_decay": float(training_cfg.get("weight_decay", 0.0001)),
            "early_stopping_metric": training_cfg.get("early_stopping_metric"),
            "early_stopping_patience": int(training_cfg.get("early_stopping_patience", 6)),
            "threshold": result["threshold"],
        },
        "checkpoint_selection": {
            "monitor": "val_hierarchical_score",
            "formula": "0.5 * val_binary_macro_f1 + 0.5 * val_attack_family_macro_f1",
            "use_validation_only": True,
            "select_by_test_metrics": False,
            "best_epoch": result["best_epoch"],
            "epochs_run": result["epochs_run"],
            "best_val_hierarchical_score": round(float(result["best_val_hierarchical_score"]), 6),
        },
        "class_weights": {
            "source_split": "train",
            "computed_from_train_only": True,
            "validation_labels_used": False,
            "test_labels_used": False,
            "binary_pos_weight": weights["binary_pos_weight"],
            "attack_class_weights": weights["attack_class_weights"],
            "weight_cap": weights.get("weight_cap"),
        },
        "checkpoint_path": str(checkpoint_path),
        "output_paths": output_paths,
        "test_summary": {
            "binary_macro_f1": result["test_bundle"]["binary"]["macro_f1"],
            "binary_accuracy": result["test_bundle"]["binary"]["accuracy"],
            "attack_family_macro_f1_on_attack_rows": result["test_bundle"]["attack_family"][
                "macro_f1_on_attack_rows"
            ],
            "rare_class_macro_f1": result["test_bundle"]["rare_class"]["rare_class_macro_f1"],
        },
        "safety": {
            "final_checkpoint": True,
            "test_set_used_for_tuning": False,
            "checkpoint_selected_by_test_metrics": False,
            "class_weights_train_only": True,
            "no_federated_training": True,
            "no_security_attack_trimmed_mean_xai_dashboard": True,
            **meta["manifest_safety"],
        },
    }


# --------------------------------------------------------------------------- #
# Execute entry point
# --------------------------------------------------------------------------- #
def _execute(
    config: HierarchicalTrainingConfig,
    config_path: Path | str,
    project_root: Path,
    overwrite: bool,
) -> dict[str, Any]:
    _log(
        f"[execute] Hierarchical training for dataset={config.dataset}, "
        f"input_dim={config.input_dim}, attack_head_dim={config.attack_head_dim}."
    )
    preflight = validate_execute_preconditions(config, project_root=project_root, overwrite=overwrite)
    gpu_suffix = f", gpu={preflight['gpu_name']}" if preflight["gpu_name"] else ""
    _log(f"[execute] Device: {preflight['device']} (cuda_available={preflight['cuda_available']}{gpu_suffix}).")
    if not preflight["cuda_available"]:
        _log("[execute] WARNING: CUDA not available; training on CPU may be slower.")

    mapping = _load_json(config.resolve(config.attack_family_label_mapping_path))
    class_names = _class_names(mapping, config.attack_head_dim)
    rare_class_names = [str(name) for name in config.raw.get("rare_classes", [])]

    weights = build_train_only_class_weights(config.dataset, project_root=project_root)
    _log(
        f"[execute] Locked train-only weights: binary_pos_weight={weights['binary_pos_weight']:.4f}, "
        f"attack_class_weights={[round(w, 4) for w in weights['attack_class_weights']]}"
    )

    _log("[execute] Pre-run validation passed. Starting training...")
    start = time.perf_counter()
    result = fit_hierarchical(
        config, class_names, rare_class_names, weights, device=preflight["device"], verbose=True
    )
    duration = time.perf_counter() - start

    checkpoint_path = config.resolve(config.outputs["checkpoint"])
    result_dir = config.resolve(config.outputs["result_dir"])
    feature_names = _load_json(config.resolve(config.feature_names_path)).get("feature_names", [])

    checkpoint_payload = {
        "format_version": 1,
        "architecture": "SecureIDSHierarchicalAdvancedNet",
        "dataset": config.dataset,
        "task": config.task,
        "input_dim": config.input_dim,
        "attack_head_dim": config.attack_head_dim,
        "model_state_dict": result["best_state_dict"],
        "architecture_metadata": result["architecture_metadata"],
        "config_snapshot": config.raw,
        "feature_names": feature_names,
        "attack_family_label_mapping": mapping,
        "preprocessing_manifest_path": str(config.resolve(config.preprocessing_manifest_path)),
        "class_weights": {
            "binary_pos_weight": weights["binary_pos_weight"],
            "attack_class_weights": weights["attack_class_weights"],
            "source_split": "train",
        },
        "metrics_summary": {
            "best_epoch": result["best_epoch"],
            "best_val_hierarchical_score": result["best_val_hierarchical_score"],
            "test_binary_macro_f1": result["test_bundle"]["binary"]["macro_f1"],
            "test_attack_family_macro_f1_on_attack_rows": result["test_bundle"]["attack_family"][
                "macro_f1_on_attack_rows"
            ],
        },
        "safety": {
            "test_set_used_for_tuning": False,
            "checkpoint_selected_by_test_metrics": False,
            "class_weights_train_only": True,
        },
        "created_utc": utc_timestamp(),
    }
    save_checkpoint(checkpoint_payload, checkpoint_path)

    # Result files
    history_csv = config.resolve(config.outputs["training_history_csv"])
    metrics_json = config.resolve(config.outputs["test_metrics_json"])
    binary_cm_csv = config.resolve(config.outputs["binary_confusion_matrix_csv"])
    attack_cm_csv = config.resolve(config.outputs["attack_family_confusion_matrix_csv"])
    per_class_csv = config.resolve(config.outputs["per_class_attack_metrics_csv"])
    rare_csv = config.resolve(config.outputs["rare_class_metrics_csv"])
    manifest_json = config.resolve(config.outputs["manifest_json"])

    _write_history_csv(history_csv, result["history"])
    save_json(metrics_json, _build_test_metrics_payload(config, result, checkpoint_path))
    _write_binary_confusion_csv(binary_cm_csv, result["test_bundle"]["binary"]["confusion_matrix"])
    _write_attack_confusion_csv(
        attack_cm_csv,
        result["test_bundle"]["attack_family"]["confusion_matrix"],
        result["test_bundle"]["attack_family"]["class_names"],
    )
    _write_per_class_csv(per_class_csv, result["test_bundle"]["attack_family"]["per_class"])
    _write_rare_class_csv(rare_csv, result["test_bundle"]["rare_class"])
    extra_paths = _write_extra_result_files(config, result, weights, result_dir)

    output_paths = {
        "training_history_csv": str(history_csv),
        "test_metrics_json": str(metrics_json),
        "binary_confusion_matrix_csv": str(binary_cm_csv),
        "attack_family_confusion_matrix_csv": str(attack_cm_csv),
        "per_class_attack_metrics_csv": str(per_class_csv),
        "rare_class_metrics_csv": str(rare_csv),
        **extra_paths,
    }
    output_paths["report_md"] = str(config.resolve(config.outputs["report_md"]))

    manifest = _build_manifest(
        config, config_path, result, weights, preflight, checkpoint_path, output_paths
    )
    save_json(manifest_json, manifest)
    report_path = _write_report(config, result, checkpoint_path, project_root)

    test = result["test_bundle"]
    _log(
        f"[execute] Done in {duration:.1f}s. best_epoch={result['best_epoch']}. "
        f"Test binary macro_f1={test['binary']['macro_f1']:.4f}, "
        f"attack-family macro_f1={test['attack_family']['macro_f1_on_attack_rows']:.4f}."
    )
    _log(f"[execute] Checkpoint: {checkpoint_path}")

    return {
        "executed": True,
        "dataset": config.dataset,
        "duration_seconds": round(duration, 3),
        "device": result["device"],
        "cuda_available": preflight["cuda_available"],
        "best_epoch": result["best_epoch"],
        "best_val_hierarchical_score": result["best_val_hierarchical_score"],
        "best_val_bundle": result["best_val_bundle"],
        "test_bundle": test,
        "checkpoint": str(checkpoint_path),
        "metrics_json": str(metrics_json),
        "manifest_json": str(manifest_json),
        "report_md": str(report_path),
        "output_paths": output_paths,
        "epochs_run": result["epochs_run"],
    }


def run_hierarchical_training(
    config_path: Path | str,
    execute: bool = False,
    project_root: Path | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Validate a hierarchical config and either plan (dry) or train it for real."""

    root = Path(project_root) if project_root is not None else Path(__file__).resolve().parents[2]
    config = load_hierarchical_training_config(config_path, project_root=root)
    if not execute:
        return {"executed": False, "plan": build_hierarchical_training_plan(config)}
    return _execute(config, config_path, project_root=root, overwrite=overwrite)
