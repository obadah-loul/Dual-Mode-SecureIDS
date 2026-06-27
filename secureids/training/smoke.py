"""Tiny, non-final centralized smoke-training check.

This module runs a minimal training/eval pass on small subsets of the processed
arrays to validate the real PyTorch training path *before* any full training. It
is technical validation only: the metrics it produces are NOT final results, and
no final checkpoint or results/final output is ever written.

Import policy
-------------
This module imports torch (smoke execution requires PyTorch). It must be
imported only inside the CLI smoke command handler, after ``--execute`` is
confirmed - never at CLI startup. The torch-free dry-run path and CLI help must
not import this module.

Smoke guarantees
----------------
* One architecture only: ``SecureIDSNet`` (config-driven ``input_dim``).
* Binary classification only; single logit output.
* Tiny capped subsets, capped batches, and capped epochs.
* No final checkpoint; an optional marked NON_FINAL checkpoint may be written
  only under ``models/checkpoints/smoke/`` when a config explicitly opts in.
* Outputs are clearly marked non-final and never written under ``results/final``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import DataLoader

from secureids.preprocessing.artifacts import save_json, utc_timestamp
from secureids.training.centralized import (
    build_loss_from_config,
    build_model_from_config,
    resolve_device,
    set_global_seed,
)
from secureids.training.config import (
    SmokeConfig,
    SmokeConfigError,
    TrainingConfig,
    load_smoke_config,
    load_training_config,
)
from secureids.training.datasets import BinaryNumpyDataset
from secureids.training.metrics import compute_binary_metrics
from secureids.training.planning import load_numpy_split

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SMOKE_MARKERS = {
    "non_final": True,
    "do_not_report": True,
    "do_not_use_for_dashboard": True,
}

SMOKE_CHECKPOINT_DIR = "models/checkpoints/smoke"
SMOKE_NOTE = (
    "NON-FINAL smoke check. Technical training-path validation only. "
    "Do not report these metrics as final model results."
)


# --------------------------------------------------------------------------- #
# Tiny data slicing
# --------------------------------------------------------------------------- #
def _tiny_slice(
    processed_dir: Path,
    split: str,
    max_samples: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Copy the first ``max_samples`` rows of a split into owned arrays.

    The feature matrix is read with mmap so only the small leading slice is
    materialized, even for the large CICIDS2018 arrays.
    """

    X, y = load_numpy_split(processed_dir, split, mmap=True)
    n = min(int(max_samples), int(X.shape[0]))
    X_slice = np.array(X[:n], dtype=np.float32, copy=True)
    y_slice = np.array(np.asarray(y).reshape(-1)[:n], copy=True)
    return X_slice, y_slice


@torch.no_grad()
def _smoke_eval(
    model: torch.nn.Module,
    loader: DataLoader,
    device: torch.device,
    threshold: float,
    max_batches: int,
) -> dict[str, Any] | None:
    """Run a capped evaluation pass and return a non-final metric bundle."""

    model.eval()
    logits_chunks: list[torch.Tensor] = []
    target_chunks: list[torch.Tensor] = []
    seen_batches = 0
    for features, targets in loader:
        if seen_batches >= max_batches:
            break
        features = features.to(device)
        logits = model(features)
        logits_chunks.append(logits.detach().cpu())
        target_chunks.append(targets.detach().cpu())
        seen_batches += 1

    if not logits_chunks:
        return None

    logits_np = torch.cat(logits_chunks).numpy().reshape(-1)
    targets_np = torch.cat(target_chunks).numpy().reshape(-1)
    return compute_binary_metrics(
        targets_np, logits_np, threshold=threshold, from_logits=True
    )


def _save_smoke_checkpoint(
    model: torch.nn.Module,
    smoke_cfg: SmokeConfig,
    base_cfg: TrainingConfig,
) -> Path:
    """Save a clearly marked NON-FINAL smoke checkpoint under the smoke dir.

    Only reached when a smoke config explicitly sets ``save_checkpoint: true``.
    Never writes under ``models/final``.
    """

    ckpt_dir = smoke_cfg.project_root / SMOKE_CHECKPOINT_DIR
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    path = ckpt_dir / f"smoke_{smoke_cfg.dataset}_NON_FINAL.pt"
    payload = {
        "NON_FINAL": True,
        "DO_NOT_REPORT": True,
        "DO_NOT_USE_FOR_DASHBOARD": True,
        "dataset": smoke_cfg.dataset,
        "input_dim": base_cfg.input_dim,
        "model_state_dict": {k: v.cpu() for k, v in model.state_dict().items()},
        "note": "Smoke-test weights only. Not a trained model. Do not use.",
        "created_utc": utc_timestamp(),
    }
    torch.save(payload, path)
    return path


# --------------------------------------------------------------------------- #
# Single-dataset smoke run
# --------------------------------------------------------------------------- #
def _run_single_dataset_smoke(
    smoke_cfg: SmokeConfig,
    base_cfg: TrainingConfig,
    device: torch.device | None = None,
) -> dict[str, Any]:
    """Execute one tiny training+eval pass and return a non-final result dict."""

    set_global_seed(base_cfg.training.seed)
    device = device or resolve_device()
    processed = smoke_cfg.resolve(smoke_cfg.processed_dir)

    X_train, y_train = _tiny_slice(processed, "train", smoke_cfg.max_train_samples)
    X_val, y_val = _tiny_slice(processed, "val", smoke_cfg.max_val_samples)
    X_test, y_test = _tiny_slice(processed, "test", smoke_cfg.max_test_samples)

    detected_input_dim = int(X_train.shape[1])
    if detected_input_dim != base_cfg.input_dim:
        raise SmokeConfigError(
            f"Detected input_dim ({detected_input_dim}) does not match base "
            f"config input_dim ({base_cfg.input_dim})."
        )

    train_loader = DataLoader(
        BinaryNumpyDataset(X_train, y_train),
        batch_size=smoke_cfg.batch_size,
        shuffle=True,
        drop_last=False,
    )
    val_loader = DataLoader(
        BinaryNumpyDataset(X_val, y_val),
        batch_size=smoke_cfg.batch_size,
        shuffle=False,
    )
    test_loader = DataLoader(
        BinaryNumpyDataset(X_test, y_test),
        batch_size=smoke_cfg.batch_size,
        shuffle=False,
    )

    model = build_model_from_config(base_cfg).to(device)
    loss_fn = build_loss_from_config(base_cfg, y_train, device=device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=base_cfg.training.learning_rate,
        weight_decay=base_cfg.training.weight_decay,
    )

    forward_pass_ok = False
    backward_pass_ok = False
    loss_computed = False
    logits_shape_ok = False
    dataloader_ok = False
    last_train_loss: float | None = None
    epochs_run = 0
    batches_run = 0

    # Snapshot a parameter to confirm the optimizer actually updates weights.
    _, reference_param = next(iter(model.named_parameters()))
    param_before = reference_param.detach().clone()

    model.train()
    for _ in range(smoke_cfg.max_epochs):
        epoch_batches = 0
        for features, targets in train_loader:
            if epoch_batches >= smoke_cfg.max_batches_per_epoch:
                break
            dataloader_ok = True
            features = features.to(device)
            targets = targets.to(device)

            optimizer.zero_grad()
            logits = model(features)
            forward_pass_ok = True
            if tuple(logits.shape) == (features.size(0), 1):
                logits_shape_ok = True

            loss = loss_fn(logits, targets)
            loss_value = float(loss.item())
            last_train_loss = loss_value
            loss_computed = bool(np.isfinite(loss_value))

            loss.backward()
            grad_exists = any(
                param.grad is not None and bool(torch.isfinite(param.grad).any())
                for param in model.parameters()
            )
            backward_pass_ok = backward_pass_ok or grad_exists

            optimizer.step()
            epoch_batches += 1
            batches_run += 1
        epochs_run += 1

    param_after = reference_param.detach().clone()
    params_updated = bool(torch.any(param_before != param_after).item())

    val_metrics = _smoke_eval(
        model, val_loader, device, base_cfg.evaluation.threshold,
        smoke_cfg.evaluation_batches,
    )
    test_metrics = _smoke_eval(
        model, test_loader, device, base_cfg.evaluation.threshold,
        smoke_cfg.evaluation_batches,
    )
    metrics_computed = val_metrics is not None

    checkpoint_created = False
    checkpoint_path: str | None = None
    if smoke_cfg.save_checkpoint:
        saved = _save_smoke_checkpoint(model, smoke_cfg, base_cfg)
        checkpoint_created = True
        checkpoint_path = str(saved)

    passed = (
        dataloader_ok
        and forward_pass_ok
        and backward_pass_ok
        and loss_computed
        and logits_shape_ok
        and metrics_computed
    )

    return {
        "dataset": smoke_cfg.dataset,
        "status": "PASS" if passed else "BLOCKED",
        "input_dim": detected_input_dim,
        "train_samples_used": int(X_train.shape[0]),
        "val_samples_used": int(X_val.shape[0]),
        "test_samples_used": int(X_test.shape[0]),
        "epochs_run": epochs_run,
        "batches_run": batches_run,
        "dataloader_ok": dataloader_ok,
        "forward_pass_ok": forward_pass_ok,
        "backward_pass_ok": backward_pass_ok,
        "params_updated": params_updated,
        "loss_computed": loss_computed,
        "logits_shape_ok": logits_shape_ok,
        "metrics_computed": metrics_computed,
        "last_train_loss": last_train_loss,
        "val_metrics_non_final": val_metrics,
        "test_metrics_non_final": test_metrics,
        "checkpoint_created": checkpoint_created,
        "checkpoint_path": checkpoint_path,
        "device": str(device),
        "timestamp_utc": utc_timestamp(),
    }


# --------------------------------------------------------------------------- #
# Output writers (JSON append/update + Markdown report)
# --------------------------------------------------------------------------- #
def _update_smoke_json(json_path: Path, dataset_result: dict[str, Any]) -> dict[str, Any]:
    """Merge a dataset result into the smoke JSON, replacing any prior entry.

    Running one dataset updates only that dataset's entry; the other dataset's
    entry (if present) is preserved.
    """

    existing: dict[str, Any] = {}
    if json_path.exists():
        try:
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                existing = loaded
        except (json.JSONDecodeError, OSError):
            existing = {}

    datasets = existing.get("datasets", [])
    if not isinstance(datasets, list):
        datasets = []
    datasets = [
        entry
        for entry in datasets
        if entry.get("dataset") != dataset_result["dataset"]
    ]
    datasets.append(dataset_result)

    payload = {
        **SMOKE_MARKERS,
        "note": SMOKE_NOTE,
        "datasets": datasets,
        "safety_confirmation": {
            "final_checkpoint_created": False,
            "final_metrics_created": False,
            "full_training_run": False,
        },
        "last_updated_utc": utc_timestamp(),
    }
    save_json(json_path, payload)
    return payload


def _write_smoke_report(report_path: Path, payload: dict[str, Any]) -> None:
    """Write the human-readable, clearly non-final smoke report."""

    lines: list[str] = [
        "# CENTRALIZED_TRAINING_SMOKE_CHECK.md",
        "",
        "## Status: NON-FINAL TECHNICAL SMOKE TEST",
        "",
        "This is a technical smoke test of the centralized training path. It is",
        "**not** a final training result and **not** a final model performance",
        "claim. No final checkpoint was created and no `results/final/centralized`",
        "outputs were created.",
        "",
        "Markers: non_final=true, do_not_report=true, do_not_use_for_dashboard=true.",
        "",
        f"Last updated (UTC): {payload.get('last_updated_utc', 'unknown')}",
        "",
        "## Datasets Tested",
        "",
    ]

    for entry in payload.get("datasets", []):
        lines.extend(
            [
                f"### {entry.get('dataset')} - {entry.get('status')}",
                "",
                f"- input_dim: {entry.get('input_dim')}",
                f"- train samples used: {entry.get('train_samples_used')}",
                f"- val samples used: {entry.get('val_samples_used')}",
                f"- test samples used: {entry.get('test_samples_used')}",
                f"- epochs run: {entry.get('epochs_run')}",
                f"- batches run: {entry.get('batches_run')}",
                f"- dataloader ok: {entry.get('dataloader_ok')}",
                f"- forward pass ok: {entry.get('forward_pass_ok')}",
                f"- backward pass ok: {entry.get('backward_pass_ok')}",
                f"- params updated: {entry.get('params_updated')}",
                f"- loss computed: {entry.get('loss_computed')}",
                f"- logits shape [batch, 1] ok: {entry.get('logits_shape_ok')}",
                f"- metrics computed: {entry.get('metrics_computed')}",
                f"- checkpoint created: {entry.get('checkpoint_created')}",
                "",
                "Non-final smoke metrics (do not report):",
                f"- val (non-final): {entry.get('val_metrics_non_final')}",
                "",
            ]
        )

    safety = payload.get("safety_confirmation", {})
    lines.extend(
        [
            "## Safety Confirmation",
            "",
            f"- final checkpoint created: {safety.get('final_checkpoint_created')}",
            f"- final metrics created: {safety.get('final_metrics_created')}",
            f"- full training run: {safety.get('full_training_run')}",
            "",
            "## Next Recommended Step",
            "",
            "If every dataset above is PASS, the centralized training path is",
            "validated on tiny subsets. The next step is to seek approval to enable",
            "full `train-centralized --execute` (Task 8B), starting with UNSW-NB15",
            "(smaller) before CICIDS2018. If any dataset is BLOCKED, fix the cause",
            "and re-run the smoke check before any full training.",
            "",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Entry point used by the CLI smoke handler
# --------------------------------------------------------------------------- #
def run_smoke(
    smoke_config_path: Path | str,
    project_root: Path | None = None,
    expected_dataset: str | None = None,
) -> dict[str, Any]:
    """Validate, run a tiny smoke pass, and write the non-final JSON + report.

    ``expected_dataset`` (already normalized, e.g. ``"cicids2018"``) is checked
    against the config before any training so a mismatch fails fast.
    """

    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    smoke_cfg = load_smoke_config(smoke_config_path, project_root=root)

    if expected_dataset is not None and expected_dataset != smoke_cfg.dataset:
        raise SmokeConfigError(
            f"--dataset resolves to {expected_dataset!r} but the smoke config is "
            f"for {smoke_cfg.dataset!r}."
        )

    base_cfg = load_training_config(
        smoke_cfg.resolve(smoke_cfg.base_config), project_root=root
    )
    if smoke_cfg.input_dim != base_cfg.input_dim:
        raise SmokeConfigError(
            f"Smoke input_dim ({smoke_cfg.input_dim}) does not match base config "
            f"input_dim ({base_cfg.input_dim})."
        )

    dataset_result = _run_single_dataset_smoke(smoke_cfg, base_cfg)

    json_path = smoke_cfg.resolve(smoke_cfg.output_json)
    report_path = smoke_cfg.resolve(smoke_cfg.report_md)
    payload = _update_smoke_json(json_path, dataset_result)
    _write_smoke_report(report_path, payload)

    return {
        "status": dataset_result["status"],
        "dataset_result": dataset_result,
        "json_path": str(json_path),
        "report_path": str(report_path),
    }
