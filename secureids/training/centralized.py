"""Centralized training orchestration for SecureIDS V2.

This module provides the reusable building blocks for centralized training and
a single entry point, :func:`run_centralized_training`. Model construction is
deliberately separated from the training loop so the same pieces can be reused
later by the federated layer (per-client models, clean state-dict handling, no
centralized-only assumptions baked into the model).

Execution policy
----------------
* Nothing trains on import; there is no top-level execution.
* ``run_centralized_training(..., execute=False)`` returns a validation/plan
  summary only and touches no weights.
* ``run_centralized_training(..., execute=True)`` contains the real training
  path for the approved Task 8B run. It is intentionally *not* invoked during
  the implementation-readiness task (the CLI refuses ``--execute``).
* The test split is evaluated exactly once, only after the best validation
  checkpoint has been selected.
"""

from __future__ import annotations

import copy
import csv
import random
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

from secureids.models.secureids_net import SecureIDSNet
from secureids.preprocessing.artifacts import load_json, save_json, utc_timestamp
from secureids.training.checkpoints import build_checkpoint_payload, save_checkpoint
from secureids.training.config import (
    TrainingConfig,
    TrainingConfigError,
    load_training_config,
)
from secureids.training.datasets import create_data_loaders
from secureids.training.manifest import build_training_manifest, save_training_manifest
from secureids.training.metrics import compute_binary_metrics
from secureids.training.planning import (
    load_feature_names,
    load_label_mapping,
    load_numpy_split,
    run_centralized_dry_run,
)


# --------------------------------------------------------------------------- #
# Reproducibility and device helpers
# --------------------------------------------------------------------------- #
def set_global_seed(seed: int) -> None:
    """Seed Python, NumPy, and PyTorch RNGs before model init and shuffling."""

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def resolve_device(prefer_gpu: bool = True) -> torch.device:
    """Return the CUDA device when available and preferred, else CPU."""

    if prefer_gpu and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


# --------------------------------------------------------------------------- #
# Model / loss construction (reused by the federated layer later)
# --------------------------------------------------------------------------- #
def build_model_from_config(config: TrainingConfig) -> SecureIDSNet:
    """Construct SecureIDSNet using the dataset-specific config ``input_dim``."""

    return SecureIDSNet(
        input_dim=config.input_dim,
        hidden_dims=config.model.hidden_dims,
        dropout=config.model.dropout,
        output_dim=config.model.output_dim,
    )


def compute_pos_weight_from_train_labels(y_train: Any) -> float:
    """Return ``negatives / positives`` from the training labels.

    Falls back to ``1.0`` when there are no positives, so the loss stays valid.
    """

    y = np.asarray(y_train).reshape(-1)
    positives = int(np.sum(y == 1))
    negatives = int(np.sum(y == 0))
    if positives == 0:
        return 1.0
    return negatives / positives


def build_loss_from_config(
    config: TrainingConfig,
    y_train: Any,
    device: torch.device | None = None,
) -> nn.Module:
    """Build ``BCEWithLogitsLoss``, applying train-only ``pos_weight`` if enabled."""

    if not config.training.use_pos_weight:
        return nn.BCEWithLogitsLoss()
    pos_weight_value = compute_pos_weight_from_train_labels(y_train)
    pos_weight = torch.tensor([pos_weight_value], dtype=torch.float32)
    if device is not None:
        pos_weight = pos_weight.to(device)
    return nn.BCEWithLogitsLoss(pos_weight=pos_weight)


# --------------------------------------------------------------------------- #
# Train / evaluate primitives
# --------------------------------------------------------------------------- #
def train_one_epoch(
    model: nn.Module,
    loader: Any,
    loss_fn: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> float:
    """Run one training epoch and return the sample-weighted mean loss."""

    model.train()
    running_loss = 0.0
    seen = 0
    for features, targets in loader:
        features = features.to(device)
        targets = targets.to(device)
        optimizer.zero_grad()
        logits = model(features)
        loss = loss_fn(logits, targets)
        loss.backward()
        optimizer.step()
        batch_size = features.size(0)
        running_loss += float(loss.item()) * batch_size
        seen += batch_size
    return running_loss / max(seen, 1)


@torch.no_grad()
def evaluate_model(
    model: nn.Module,
    loader: Any,
    device: torch.device,
    threshold: float = 0.5,
    loss_fn: nn.Module | None = None,
) -> dict[str, Any]:
    """Evaluate ``model`` over ``loader`` and return the binary metric bundle.

    Logits and labels are gathered on CPU and scored once via
    :func:`compute_binary_metrics`. When ``loss_fn`` is provided, the mean loss
    is included under the ``"loss"`` key.
    """

    model.eval()
    all_logits: list[torch.Tensor] = []
    all_targets: list[torch.Tensor] = []
    running_loss = 0.0
    seen = 0
    for features, targets in loader:
        features = features.to(device)
        targets_device = targets.to(device)
        logits = model(features)
        if loss_fn is not None:
            loss = loss_fn(logits, targets_device)
            running_loss += float(loss.item()) * features.size(0)
            seen += features.size(0)
        all_logits.append(logits.detach().cpu())
        all_targets.append(targets.detach().cpu())

    logits_np = torch.cat(all_logits).numpy().reshape(-1)
    targets_np = torch.cat(all_targets).numpy().reshape(-1)
    metrics = compute_binary_metrics(
        targets_np, logits_np, threshold=threshold, from_logits=True
    )
    metrics["loss"] = (running_loss / max(seen, 1)) if loss_fn is not None else None
    return metrics


def _monitor_key(early_stopping_metric: str) -> tuple[str, bool]:
    """Map an early-stopping metric name to a metric key and direction."""

    key = early_stopping_metric.replace("val_", "")
    higher_is_better = key != "loss"
    return key, higher_is_better


def fit_centralized(
    config: TrainingConfig,
    device: torch.device | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Train SecureIDSNet with early stopping; evaluate the test split once.

    Returns the best validation metrics, the best-epoch state dict, the per-epoch
    history, the test metrics, and the class distribution / pos_weight used. With
    ``verbose=True`` it prints a concise per-epoch progress line so a manual run
    can be monitored.
    """

    set_global_seed(config.training.seed)
    device = device or resolve_device()

    processed = config.resolve(config.processed_dir)
    _, y_train = load_numpy_split(processed, "train", mmap=False)
    class_distribution = {
        "0": int(np.sum(np.asarray(y_train).reshape(-1) == 0)),
        "1": int(np.sum(np.asarray(y_train).reshape(-1) == 1)),
    }
    pos_weight_value = (
        compute_pos_weight_from_train_labels(y_train)
        if config.training.use_pos_weight
        else None
    )

    loaders = create_data_loaders(config)
    model = build_model_from_config(config).to(device)
    loss_fn = build_loss_from_config(config, y_train, device=device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.training.learning_rate,
        weight_decay=config.training.weight_decay,
    )

    monitor_metric, higher_is_better = _monitor_key(
        config.training.early_stopping_metric
    )
    best_score = -float("inf") if higher_is_better else float("inf")
    best_state: dict[str, Any] | None = None
    best_epoch = -1
    patience_counter = 0
    history: list[dict[str, Any]] = []

    for epoch in range(config.training.max_epochs):
        epoch_start = time.perf_counter()
        train_loss = train_one_epoch(model, loaders["train"], loss_fn, optimizer, device)
        val_metrics = evaluate_model(
            model,
            loaders["val"],
            device,
            threshold=config.evaluation.threshold,
            loss_fn=loss_fn,
        )
        epoch_seconds = time.perf_counter() - epoch_start

        current = val_metrics.get(monitor_metric, val_metrics["macro_f1"])
        improved = (
            current > best_score if higher_is_better else current < best_score
        )
        if improved:
            best_score = current
            best_epoch = epoch + 1
            best_state = copy.deepcopy(model.state_dict())
            patience_counter = 0
        else:
            patience_counter += 1

        learning_rate = float(optimizer.param_groups[0]["lr"])
        history.append(
            {
                "epoch": epoch + 1,
                "train_loss": train_loss,
                "val_loss": val_metrics["loss"],
                "val_accuracy": val_metrics["accuracy"],
                "val_precision": val_metrics["precision"],
                "val_recall": val_metrics["recall"],
                "val_f1": val_metrics["f1"],
                "val_macro_f1": val_metrics["macro_f1"],
                "learning_rate": learning_rate,
                "epoch_seconds": round(epoch_seconds, 4),
                "best_checkpoint_so_far": bool(improved),
            }
        )

        if verbose:
            marker = " *best" if improved else ""
            print(
                f"[epoch {epoch + 1}/{config.training.max_epochs}] "
                f"train_loss={train_loss:.4f} val_loss={val_metrics['loss']:.4f} "
                f"val_macro_f1={val_metrics['macro_f1']:.4f} "
                f"({epoch_seconds:.1f}s){marker}"
            )

        if not improved and patience_counter >= config.training.early_stopping_patience:
            if verbose:
                print(
                    f"Early stopping at epoch {epoch + 1} "
                    f"(no improvement for {patience_counter} epochs)."
                )
            break

    if best_state is not None:
        model.load_state_dict(best_state)

    # Test is evaluated exactly once, after best-checkpoint selection.
    test_metrics = evaluate_model(
        model,
        loaders["test"],
        device,
        threshold=config.evaluation.threshold,
        loss_fn=None,
    )

    return {
        "best_epoch": best_epoch,
        "best_monitor_metric": config.training.early_stopping_metric,
        "best_monitor_value": best_score,
        "epochs_run": len(history),
        "history": history,
        "test_metrics": test_metrics,
        "best_state_dict": best_state if best_state is not None else model.state_dict(),
        "class_distribution_train": class_distribution,
        "pos_weight": pos_weight_value,
        "device": str(device),
    }


# --------------------------------------------------------------------------- #
# Output writers and the guarded execution entry point
# --------------------------------------------------------------------------- #
# Dry-run planning lives in the torch-free secureids.training.planning module
# (build_training_plan / run_centralized_dry_run) so it can run without torch.
# Stable, explicit column order for the training-history CSV. Any extra keys a
# row carries (now or in future) are appended after these, sorted, so the writer
# never raises on unexpected fields and the output stays deterministic.
HISTORY_FIELDNAMES: tuple[str, ...] = (
    "epoch",
    "train_loss",
    "val_loss",
    "val_accuracy",
    "val_precision",
    "val_recall",
    "val_f1",
    "val_macro_f1",
    "learning_rate",
    "epoch_seconds",
    "best_checkpoint_so_far",
)


def _write_history_csv(path: Path, history: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    # Collect any keys present in the rows but not in the stable order, and append
    # them (sorted) so future harmless fields are written rather than crashing.
    known = set(HISTORY_FIELDNAMES)
    extra_keys = sorted(
        {key for row in history for key in row.keys()} - known
    )
    fieldnames = [*HISTORY_FIELDNAMES, *extra_keys]

    with path.open("w", encoding="utf-8", newline="") as handle:
        # restval="" writes a blank cell when a row omits a declared field.
        writer = csv.DictWriter(handle, fieldnames=fieldnames, restval="")
        writer.writeheader()
        for row in history:
            writer.writerow(row)


def _write_confusion_matrix_csv(path: Path, cm: dict[str, int]) -> None:
    """Write the confusion matrix as readable (true, predicted, count) rows.

    Consistent with the ``confusion_matrix`` block (tp/fp/fn/tn) in the metrics
    JSON: label 0 = Benign/Normal, label 1 = Attack.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["true_label", "predicted_label", "count"])
        writer.writerow([0, 0, cm["tn"]])
        writer.writerow([0, 1, cm["fp"]])
        writer.writerow([1, 0, cm["fn"]])
        writer.writerow([1, 1, cm["tp"]])


SAFETY_CHECK_RELATIVE = "results/audits/preprocessing_safety_check.json"


class ExecutePreconditionError(RuntimeError):
    """Raised when a precondition for full training execution is not met."""


def _run_safety_flags() -> dict[str, bool]:
    """The single authoritative run-scope safety block embedded everywhere."""

    return {
        "final_checkpoint": True,
        "test_set_used_for_tuning": False,
        "preprocessing_safety_check_passed": True,
        "no_federated_training": True,
        "no_attack_simulation": True,
        "no_xai": True,
    }


def _safety_check_path(project_root: Path) -> Path:
    return Path(project_root) / SAFETY_CHECK_RELATIVE


def _safety_status_for_dataset(safety_doc: dict[str, Any], dataset: str) -> str | None:
    for entry in safety_doc.get("datasets", []):
        if entry.get("dataset") == dataset:
            return entry.get("status")
    return None


def validate_execute_preconditions(
    config: TrainingConfig,
    project_root: Path,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Validate everything required before real training and return preflight info.

    Raises :class:`ExecutePreconditionError` (without starting training) if any
    check fails. On success it returns the resolved device, CUDA info, detected
    split shapes, and the safety-check path/status, and ensures the output
    directories exist.
    """

    errors: list[str] = []
    device = resolve_device()
    cuda_available = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if cuda_available else None

    if config.task != "binary":
        errors.append(f"task must be 'binary', got {config.task!r}.")
    if config.input_dim <= 0:
        errors.append(f"input_dim must be > 0, got {config.input_dim}.")

    processed = config.resolve(config.processed_dir)
    if not processed.exists():
        errors.append(f"processed_dir does not exist: {processed}.")

    feature_count: int | None = None
    feature_names_path = config.resolve(config.feature_names_path)
    if not feature_names_path.exists():
        errors.append(f"feature_names.json missing: {feature_names_path}.")
    else:
        feature_count = len(load_feature_names(feature_names_path))
        if feature_count != config.input_dim:
            errors.append(
                f"feature_names length ({feature_count}) != input_dim "
                f"({config.input_dim})."
            )

    split_shapes: dict[str, Any] = {}
    for split in ("train", "val", "test"):
        x_path = processed / f"X_{split}.npy"
        y_path = processed / f"y_{split}.npy"
        if not x_path.exists():
            errors.append(f"missing array: {x_path}.")
        else:
            x_header = np.load(x_path, mmap_mode="r")
            split_shapes.setdefault(split, {})["X"] = list(x_header.shape)
            if int(x_header.shape[1]) != config.input_dim:
                errors.append(
                    f"X_{split} feature dim ({x_header.shape[1]}) != input_dim "
                    f"({config.input_dim})."
                )
        if not y_path.exists():
            errors.append(f"missing array: {y_path}.")
        else:
            y_arr = np.load(y_path)
            split_shapes.setdefault(split, {})["y"] = list(np.asarray(y_arr).shape)
            unique_labels = {int(value) for value in np.unique(y_arr)}
            if not unique_labels.issubset({0, 1}):
                errors.append(
                    f"y_{split} is not binary (labels {sorted(unique_labels)})."
                )

    safety_path = _safety_check_path(project_root)
    safety_status: str | None = None
    if not safety_path.exists():
        errors.append(f"preprocessing safety check missing: {safety_path}.")
    else:
        try:
            safety_doc = load_json(safety_path)
        except (ValueError, OSError):
            safety_doc = {}
        safety_status = _safety_status_for_dataset(safety_doc, config.dataset)
        overall_status = safety_doc.get("overall_status")
        if safety_status != "PASS" and overall_status != "PASS":
            errors.append(
                f"preprocessing safety check is not PASS for {config.dataset} "
                f"(dataset status={safety_status}, overall={overall_status})."
            )

    checkpoint_path = config.resolve(config.output_checkpoint)
    if (
        checkpoint_path.parent.name != "final"
        or checkpoint_path.parent.parent.name != "models"
    ):
        errors.append(
            f"output_checkpoint should live under models/final, got {checkpoint_path}."
        )

    final_outputs = {
        "checkpoint": checkpoint_path,
        "history_csv": config.resolve(config.outputs.history_csv),
        "metrics_json": config.resolve(config.outputs.metrics_json),
        "confusion_matrix_csv": config.resolve(config.outputs.confusion_matrix_csv),
        "manifest_json": config.resolve(config.outputs.manifest_json),
    }
    existing = [str(path) for path in final_outputs.values() if path.exists()]
    if existing and not overwrite:
        errors.append(
            "refusing to overwrite existing final outputs; back them up manually "
            f"or re-run with --overwrite. Existing: {existing}"
        )

    if errors:
        raise ExecutePreconditionError(
            "Pre-run validation failed:\n- " + "\n- ".join(errors)
        )

    # Validation passed: ensure output directories exist.
    for directory in {path.parent for path in final_outputs.values()}:
        directory.mkdir(parents=True, exist_ok=True)

    return {
        "device": device,
        "cuda_available": cuda_available,
        "gpu_name": gpu_name,
        "feature_count": feature_count,
        "split_shapes": split_shapes,
        "safety_check_path": str(safety_path),
        "safety_status": safety_status,
    }


def _build_test_metrics_payload(
    config: TrainingConfig,
    test_metrics: dict[str, Any],
    checkpoint_path: Path,
) -> dict[str, Any]:
    """Wrap the once-only test metrics with dataset/safety context for the JSON."""

    return {
        "dataset": config.dataset,
        "task": config.task,
        "model": "SecureIDSNet",
        "checkpoint_path": str(checkpoint_path),
        "input_dim": config.input_dim,
        "threshold": test_metrics.get("threshold", config.evaluation.threshold),
        "test_set_used_for_tuning": False,
        "final_checkpoint": True,
        "metrics": {
            "accuracy": test_metrics["accuracy"],
            "precision": test_metrics["precision"],
            "recall": test_metrics["recall"],
            "f1": test_metrics["f1"],
            "macro_f1": test_metrics["macro_f1"],
            "confusion_matrix": test_metrics["confusion_matrix"],
            "n_samples": test_metrics["n_samples"],
        },
        "safety_notes": {
            "no_fake_metrics": True,
            "test_evaluated_once_after_best_validation_checkpoint": True,
            "no_federated_training": True,
            "no_security_or_attack_simulation": True,
            "no_xai": True,
        },
        "created_utc": utc_timestamp(),
    }


# The centralized report aggregates one section per dataset, each rendered from
# that dataset's real on-disk artifacts (test-metrics JSON + training manifest).
# This keeps the report a faithful function of the actual result files: a dataset
# that has already trained is preserved verbatim when the other dataset trains,
# and no section is ever fabricated. A dataset with no result files yet is shown
# as "ENABLED - NOT YET RUN" with its expected (not-yet-created) output paths.
REPORT_DATASET_CONFIGS: tuple[tuple[str, str], ...] = (
    ("UNSW-NB15", "configs/training/unsw_nb15_binary.yaml"),
    ("CICIDS2018", "configs/training/cicids2018_binary.yaml"),
)


def _short_dataset(dataset: str) -> str:
    """Short CLI ``--dataset`` token for a canonical dataset name."""

    return "cicids" if dataset == "cicids2018" else "unsw"


def _safe_load_json(path: Path) -> dict[str, Any] | None:
    """Load JSON if the file exists and parses; otherwise return ``None``."""

    try:
        if not path.exists():
            return None
        return load_json(path)
    except (ValueError, OSError):
        return None


def _load_report_config(root: Path, config_rel: str) -> TrainingConfig | None:
    """Load a dataset's training config for reporting; ``None`` if unavailable."""

    try:
        return load_training_config(root / config_rel, project_root=root)
    except (TrainingConfigError, OSError):
        return None


def _render_completed_section(
    title: str,
    config: TrainingConfig,
    metrics_doc: dict[str, Any],
    manifest_doc: dict[str, Any],
) -> list[str]:
    """Render a COMPLETED dataset section from its real metrics + manifest."""

    metrics = metrics_doc["metrics"]
    cm = metrics["confusion_matrix"]
    shapes = manifest_doc.get("split_shapes", {})
    early = manifest_doc.get("early_stopping", {})
    device = manifest_doc.get("device", "unknown")
    cuda_available = str(device).startswith("cuda")
    return [
        f"## {title} (input_dim {config.input_dim})",
        "",
        "### Status: COMPLETED (real results)",
        "",
        f"Dataset: {metrics_doc.get('dataset', config.dataset)}",
        f"Task: {metrics_doc.get('task', config.task)}",
        "Model: SecureIDSNet (single shared binary architecture)",
        f"Input dim: {metrics_doc.get('input_dim', config.input_dim)}",
        f"Training config: {manifest_doc.get('config_path')}",
        f"Device: {device} (cuda_available={cuda_available})",
        f"Seed: {manifest_doc.get('seed', config.training.seed)}",
        f"Best epoch: {early.get('best_epoch')} (epochs run: {early.get('epochs_run')})",
        f"Created (UTC): {metrics_doc.get('created_utc')}",
        "",
        "### Data Sizes",
        "",
        f"- train: X {shapes.get('train', {}).get('X')}, y {shapes.get('train', {}).get('y')}",
        f"- val:   X {shapes.get('val', {}).get('X')}, y {shapes.get('val', {}).get('y')}",
        f"- test:  X {shapes.get('test', {}).get('X')}, y {shapes.get('test', {}).get('y')}",
        f"- train class distribution: {manifest_doc.get('class_distribution_train')}",
        f"- pos_weight: {manifest_doc.get('pos_weight')}",
        "",
        "### Final Test Metrics (evaluated once, after best validation checkpoint)",
        "",
        f"- accuracy:  {metrics['accuracy']:.6f}",
        f"- precision: {metrics['precision']:.6f}",
        f"- recall:    {metrics['recall']:.6f}",
        f"- f1:        {metrics['f1']:.6f}",
        f"- macro_f1:  {metrics['macro_f1']:.6f}",
        f"- n_samples: {metrics['n_samples']}",
        "",
        "### Confusion Matrix (label 0 = Benign/Normal, 1 = Attack)",
        "",
        f"- true 0 / pred 0 (tn): {cm['tn']}",
        f"- true 0 / pred 1 (fp): {cm['fp']}",
        f"- true 1 / pred 0 (fn): {cm['fn']}",
        f"- true 1 / pred 1 (tp): {cm['tp']}",
        "",
        "### Output Artifacts",
        "",
        f"- checkpoint: {config.resolve(config.output_checkpoint)}",
        f"- history csv: {config.resolve(config.outputs.history_csv)}",
        f"- test metrics json: {config.resolve(config.outputs.metrics_json)}",
        f"- confusion matrix csv: {config.resolve(config.outputs.confusion_matrix_csv)}",
        f"- training manifest: {config.resolve(config.outputs.manifest_json)}",
        "",
        "### Safety Confirmation",
        "",
        "- final_checkpoint: true",
        "- test_set_used_for_tuning: false (test evaluated once after best",
        "  validation checkpoint selection)",
        "- preprocessing_safety_check_passed: true",
        "- no fake metrics; all values above are from this real run",
        "",
    ]


def _render_pending_section(
    title: str,
    config: TrainingConfig,
    config_rel: str,
) -> list[str]:
    """Render an ENABLED-but-not-yet-run dataset section (no metrics)."""

    short = _short_dataset(config.dataset)
    return [
        f"## {title} (input_dim {config.input_dim})",
        "",
        "### Status: ENABLED - NOT YET RUN",
        "",
        f"Dataset: {config.dataset}",
        f"Task: {config.task}",
        "Model: SecureIDSNet (single shared binary architecture)",
        f"Input dim: {config.input_dim}",
        f"Training config: {config_rel}",
        "",
        "Full centralized training is ENABLED for this dataset but has not been run",
        "yet, so no checkpoint or metrics exist. Do not report any numbers for this",
        "dataset until the user runs the command below and it completes.",
        "",
        "Enabled command (real run when executed manually):",
        "",
        f"    python -m secureids.cli train-centralized --dataset {short} "
        f"--config {config_rel} --execute",
        "",
        "### Expected Output Artifacts (created only after the run completes)",
        "",
        f"- checkpoint: {config.resolve(config.output_checkpoint)}",
        f"- history csv: {config.resolve(config.outputs.history_csv)}",
        f"- test metrics json: {config.resolve(config.outputs.metrics_json)}",
        f"- confusion matrix csv: {config.resolve(config.outputs.confusion_matrix_csv)}",
        f"- training manifest: {config.resolve(config.outputs.manifest_json)}",
        "",
    ]


def _report_footer_lines() -> list[str]:
    """Scope limitation, manual pre-run checklist, and monitoring advice."""

    return [
        "## Scope (what these runs are NOT)",
        "",
        "- No federated learning yet.",
        "- No secure communication / gradient trust / Byzantine / robust aggregation",
        "  yet.",
        "- No XAI yet.",
        "- No dashboard model demo yet.",
        "- No GitHub push.",
        "",
        "## Manual Pre-Run Checklist (CICIDS2018 full centralized training)",
        "",
        "Before running CICIDS full training, confirm:",
        "",
        "- the local .venv is active",
        "- PyTorch is installed and CUDA is available",
        "- processed CICIDS files exist under data/processed/cicids2018/binary",
        "- config input_dim is 77 and feature_names length is 77",
        "- final CICIDS checkpoint models/final/final_cicids_binary.pt does not",
        "  already exist, or pass --overwrite intentionally",
        "- the UNSW checkpoint/results still exist and must not be overwritten",
        "- results/final/centralized exists or will be created cleanly",
        "- no GitHub push is planned for generated artifacts",
        "",
        "## Monitoring Advice (CICIDS2018)",
        "",
        "- CICIDS is much larger than UNSW (~6.7M training rows); expect a longer run.",
        "- Monitor GPU use in another terminal: nvidia-smi -l 5",
        "- Watch free disk space for the checkpoint and result files.",
        "- Do not close the terminal while training is running.",
        "- If training crashes, inspect partial files before re-running, and do not",
        "  report partial outputs as final.",
        "",
    ]


def _write_combined_training_report(report_path: Path, root: Path) -> None:
    """Write the combined centralized report from each dataset's real artifacts.

    One section per dataset is rendered from its on-disk test-metrics JSON and
    training manifest when both exist; otherwise the dataset is shown as enabled
    but not yet run. Already-completed datasets are therefore preserved when a
    different dataset is trained, and nothing is fabricated.
    """

    status_lines: list[str] = []
    sections: list[str] = []
    for title, config_rel in REPORT_DATASET_CONFIGS:
        config = _load_report_config(root, config_rel)
        if config is None:
            status_lines.append(f"- {title}: CONFIG UNAVAILABLE")
            sections.extend(
                [
                    f"## {title}",
                    "",
                    f"Training config {config_rel} could not be loaded; section "
                    "unavailable.",
                    "",
                    "---",
                    "",
                ]
            )
            continue
        metrics_doc = _safe_load_json(config.resolve(config.outputs.metrics_json))
        manifest_doc = _safe_load_json(config.resolve(config.outputs.manifest_json))
        if metrics_doc and manifest_doc and "metrics" in metrics_doc:
            status_lines.append(f"- {title}: COMPLETED (real results)")
            sections.extend(
                _render_completed_section(title, config, metrics_doc, manifest_doc)
            )
        else:
            status_lines.append(f"- {title}: ENABLED - NOT YET RUN")
            sections.extend(_render_pending_section(title, config, config_rel))
        sections.append("---")
        sections.append("")

    header = [
        "# CENTRALIZED_TRAINING_REPORT.md",
        "",
        "## Status: COMBINED CENTRALIZED BASELINE",
        "",
        "Centralized (non-federated) baseline training on the shared SecureIDSNet",
        "binary architecture. Each dataset keeps its own preprocessing, input_dim,",
        "checkpoint, and result files; only the model architecture is shared.",
        "",
        *status_lines,
        "",
        f"Report generated (UTC): {utc_timestamp()}",
        "",
        "---",
        "",
    ]
    lines = [*header, *sections, *_report_footer_lines()]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def _execute_centralized_training(
    config: TrainingConfig,
    config_path: Path | str,
    overwrite: bool = False,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Run real full centralized training and persist all final outputs.

    Reached only via ``run_centralized_training(..., execute=True)``. The CLI
    gates which dataset may reach this (UNSW enabled; CICIDS refused).
    """

    root = Path(project_root) if project_root is not None else config.project_root

    print(
        f"[execute] Centralized training for dataset={config.dataset}, "
        f"input_dim={config.input_dim}."
    )
    preflight = validate_execute_preconditions(config, project_root=root, overwrite=overwrite)
    gpu_suffix = f", gpu={preflight['gpu_name']}" if preflight["gpu_name"] else ""
    print(
        f"[execute] Device: {preflight['device']} "
        f"(cuda_available={preflight['cuda_available']}{gpu_suffix})."
    )
    if not preflight["cuda_available"]:
        print(
            "[execute] WARNING: CUDA is not available; training will run on CPU "
            "and may be slow."
        )
    print("[execute] Pre-run validation passed. Starting training...")

    result = fit_centralized(config, device=preflight["device"], verbose=True)

    safety = _run_safety_flags()
    feature_names = load_feature_names(config.resolve(config.feature_names_path))
    label_mapping = load_label_mapping(config.resolve(config.label_mapping_path))

    model = build_model_from_config(config)  # CPU model for a portable checkpoint
    model.load_state_dict(result["best_state_dict"])
    cpu_state_dict = model.state_dict()

    run_metadata = {
        "feature_count": len(feature_names),
        "class_distribution_train": result["class_distribution_train"],
        "pos_weight": result["pos_weight"],
        "device": result["device"],
        "seed": config.training.seed,
        "best_epoch": result["best_epoch"],
        "epochs_run": result["epochs_run"],
    }

    checkpoint_path = config.resolve(config.output_checkpoint)
    payload = build_checkpoint_payload(
        model_state_dict=cpu_state_dict,
        config_snapshot=config.raw,
        dataset=config.dataset,
        input_dim=config.input_dim,
        feature_names=feature_names,
        label_mapping=label_mapping,
        preprocessing_manifest_path=config.preprocessing_manifest_path,
        task=config.task,
        architecture_metadata=model.architecture_metadata,
        metrics_summary=result["test_metrics"],
        safety=safety,
        run_metadata=run_metadata,
    )
    save_checkpoint(payload, checkpoint_path)

    history_csv = config.resolve(config.outputs.history_csv)
    metrics_json = config.resolve(config.outputs.metrics_json)
    confusion_csv = config.resolve(config.outputs.confusion_matrix_csv)
    manifest_json = config.resolve(config.outputs.manifest_json)

    _write_history_csv(history_csv, result["history"])
    save_json(
        metrics_json,
        _build_test_metrics_payload(config, result["test_metrics"], checkpoint_path),
    )
    _write_confusion_matrix_csv(
        confusion_csv, result["test_metrics"]["confusion_matrix"]
    )

    output_paths = {
        "history_csv": str(history_csv),
        "metrics_json": str(metrics_json),
        "confusion_matrix_csv": str(confusion_csv),
    }

    processed = config.resolve(config.processed_dir)
    processed_paths = {
        f"{prefix}_{split}": str(processed / f"{prefix}_{split}.npy")
        for split in ("train", "val", "test")
        for prefix in ("X", "y")
    }

    manifest = build_training_manifest(
        dataset=config.dataset,
        task=config.task,
        model_metadata=model.architecture_metadata,
        config_path=str(config_path),
        processed_dir=str(processed),
        processed_paths=processed_paths,
        preprocessing_manifest_path=str(
            config.resolve(config.preprocessing_manifest_path)
        ),
        preprocessing_safety_check_path=preflight["safety_check_path"],
        feature_names_path=str(config.resolve(config.feature_names_path)),
        label_mapping_path=str(config.resolve(config.label_mapping_path)),
        checkpoint_path=str(checkpoint_path),
        output_paths=output_paths,
        input_dim=config.input_dim,
        feature_count=len(feature_names),
        split_shapes=preflight["split_shapes"],
        class_distribution=result["class_distribution_train"],
        pos_weight=result["pos_weight"],
        seed=config.training.seed,
        device=result["device"],
        max_epochs=config.training.max_epochs,
        early_stopping={
            "metric": config.training.early_stopping_metric,
            "patience": config.training.early_stopping_patience,
            "best_epoch": result["best_epoch"],
            "epochs_run": result["epochs_run"],
        },
        training_params=self_training_params(config),
        safety=safety,
    )
    save_training_manifest(manifest_json, manifest)

    # Regenerate the combined report from every dataset's real on-disk artifacts
    # (the just-written metrics JSON + manifest for this dataset are already on
    # disk at this point). Any already-completed dataset section is preserved.
    report_path = root / "docs" / "CENTRALIZED_TRAINING_REPORT.md"
    _write_combined_training_report(report_path, root)

    test_metrics = result["test_metrics"]
    print(
        f"[execute] Done. Best epoch={result['best_epoch']}. "
        f"Test macro_f1={test_metrics['macro_f1']:.4f}, "
        f"accuracy={test_metrics['accuracy']:.4f}."
    )
    print(f"[execute] Checkpoint: {checkpoint_path}")

    return {
        "executed": True,
        "dataset": config.dataset,
        "best_epoch": result["best_epoch"],
        "test_metrics": test_metrics,
        "checkpoint": str(checkpoint_path),
        "history_csv": str(history_csv),
        "metrics_json": str(metrics_json),
        "confusion_matrix_csv": str(confusion_csv),
        "manifest_json": str(manifest_json),
        "report_md": str(report_path),
        "device": result["device"],
        "cuda_available": preflight["cuda_available"],
    }


def self_training_params(config: TrainingConfig) -> dict[str, Any]:
    """Return the training hyperparameters as a plain dict for the manifest."""

    return {
        "seed": config.training.seed,
        "batch_size": config.training.batch_size,
        "max_epochs": config.training.max_epochs,
        "learning_rate": config.training.learning_rate,
        "optimizer": config.training.optimizer,
        "weight_decay": config.training.weight_decay,
        "early_stopping_metric": config.training.early_stopping_metric,
        "early_stopping_patience": config.training.early_stopping_patience,
        "use_pos_weight": config.training.use_pos_weight,
        "threshold": config.evaluation.threshold,
    }


def run_centralized_training(
    config_path: Path | str,
    execute: bool = False,
    project_root: Path | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Validate a config and either return a plan (dry-run) or run training.

    With ``execute=False`` this delegates to the torch-free
    :func:`secureids.training.planning.run_centralized_dry_run` and creates
    nothing. With ``execute=True`` it validates preconditions and runs the real
    centralized training, writing all final outputs. ``overwrite`` allows
    replacing existing final outputs. Which datasets may execute is gated by the
    CLI (UNSW enabled in Task 8B-1; CICIDS still refused).
    """

    if not execute:
        return run_centralized_dry_run(config_path, project_root=project_root)
    config = load_training_config(config_path, project_root=project_root)
    return _execute_centralized_training(
        config, config_path, overwrite=overwrite, project_root=project_root
    )
