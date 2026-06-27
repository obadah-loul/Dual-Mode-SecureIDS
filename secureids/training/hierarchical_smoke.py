"""Smoke-only hierarchical training execution for Task A7.

This module runs a tiny, explicitly non-final training/evaluation pass for
``SecureIDSHierarchicalAdvancedNet``. It validates real hierarchical arrays,
forward/loss/optimizer plumbing, and small diagnostic metrics. It never saves
model weights, final checkpoints, final metrics, or ``results/final`` outputs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import DataLoader

from secureids.models.secureids_hierarchical_advanced_net import (
    SecureIDSHierarchicalAdvancedNet,
    compute_hierarchical_loss,
)
from secureids.preprocessing.artifacts import save_json, utc_timestamp
from secureids.training.centralized import resolve_device, set_global_seed
from secureids.training.hierarchical_class_weights import build_train_only_class_weights
from secureids.training.hierarchical_config import (
    HierarchicalSmokeConfig,
    HierarchicalTrainingConfig,
    HierarchicalTrainingConfigError,
    load_hierarchical_smoke_config,
    load_hierarchical_training_config,
)
from secureids.training.hierarchical_datasets import build_hierarchical_smoke_dataset
from secureids.training.hierarchical_metrics import compute_hierarchical_smoke_diagnostics
from secureids.training.hierarchical_planning import build_hierarchical_training_plan

PROJECT_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_SMOKE_JSON = {
    "cicids2018": "results/audits/hierarchical_smoke_training_cicids2018.json",
    "unsw_nb15": "results/audits/hierarchical_smoke_training_unsw_nb15.json",
}
SMOKE_REPORT = "docs/HIERARCHICAL_SMOKE_TRAINING_CHECK.md"


class HierarchicalSmokeTrainingError(RuntimeError):
    """Raised when A7 hierarchical smoke training cannot proceed safely."""


def _log(message: str) -> None:
    print(message, flush=True)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise HierarchicalSmokeTrainingError(f"Expected JSON object in {path}.")
    return payload


def _validate_readiness(base_cfg: HierarchicalTrainingConfig) -> dict[str, Any]:
    readiness_path = base_cfg.resolve(base_cfg.readiness_json)
    if not readiness_path.exists():
        raise HierarchicalSmokeTrainingError(f"Readiness JSON is missing: {readiness_path}")
    readiness = _load_json(readiness_path)
    status = readiness.get("status")
    ready = readiness.get("ready_for_hierarchical_model_implementation")
    if status != "PASS" or ready is not True:
        raise HierarchicalSmokeTrainingError(
            f"Readiness is not PASS/ready for {base_cfg.dataset}: "
            f"status={status!r}, ready={ready!r}."
        )
    return readiness


def _validate_smoke_safety(
    smoke_cfg: HierarchicalSmokeConfig,
    base_cfg: HierarchicalTrainingConfig,
) -> None:
    if smoke_cfg.dataset != base_cfg.dataset:
        raise HierarchicalSmokeTrainingError("Smoke config dataset does not match base config.")
    if smoke_cfg.input_dim != base_cfg.input_dim:
        raise HierarchicalSmokeTrainingError("Smoke input_dim does not match base config.")
    if smoke_cfg.attack_head_dim != base_cfg.attack_head_dim:
        raise HierarchicalSmokeTrainingError("Smoke attack_head_dim does not match base config.")
    if smoke_cfg.smoke.get("save_checkpoint") is not False:
        raise HierarchicalSmokeTrainingError("Smoke config must set save_checkpoint: false.")
    if smoke_cfg.smoke.get("final_metrics") is not False:
        raise HierarchicalSmokeTrainingError("Smoke config must set final_metrics: false.")
    if smoke_cfg.smoke.get("non_final") is not True:
        raise HierarchicalSmokeTrainingError("Smoke config must set non_final: true.")
    if smoke_cfg.safety.get("do_not_report_as_final") is not True:
        raise HierarchicalSmokeTrainingError(
            "Smoke config must set do_not_report_as_final: true."
        )
    if smoke_cfg.safety.get("no_full_training") is not True:
        raise HierarchicalSmokeTrainingError("Smoke config must set no_full_training: true.")

    expected_json = EXPECTED_SMOKE_JSON[smoke_cfg.dataset]
    if smoke_cfg.smoke.get("output_json") != expected_json:
        raise HierarchicalSmokeTrainingError(
            f"Smoke output_json must be {expected_json!r}, got "
            f"{smoke_cfg.smoke.get('output_json')!r}."
        )
    if smoke_cfg.smoke.get("report_md") != SMOKE_REPORT:
        raise HierarchicalSmokeTrainingError(
            f"Smoke report_md must be {SMOKE_REPORT!r}, got "
            f"{smoke_cfg.smoke.get('report_md')!r}."
        )


def _validate_no_final_outputs(base_cfg: HierarchicalTrainingConfig) -> None:
    existing = [
        str(base_cfg.resolve(value))
        for key, value in base_cfg.outputs.items()
        if key != "result_dir" and base_cfg.resolve(value).exists()
    ]
    if existing:
        raise HierarchicalSmokeTrainingError(
            "Refusing smoke run because future final outputs already exist: "
            f"{existing}"
        )


def _build_model(base_cfg: HierarchicalTrainingConfig) -> SecureIDSHierarchicalAdvancedNet:
    model_cfg = base_cfg.raw.get("model", {})
    return SecureIDSHierarchicalAdvancedNet(
        input_dim=base_cfg.input_dim,
        attack_head_dim=base_cfg.attack_head_dim,
        hidden_dims=tuple(model_cfg.get("hidden_dims", (256, 128, 128))),
        dropout=float(model_cfg.get("dropout", 0.20)),
        normalization=str(model_cfg.get("normalization", "layernorm")),
    )


def _make_loader(
    dataset,
    batch_size: int,
    shuffle: bool,
    seed: int,
) -> DataLoader:
    generator = torch.Generator()
    generator.manual_seed(int(seed))
    return DataLoader(
        dataset,
        batch_size=int(batch_size),
        shuffle=shuffle,
        drop_last=False,
        num_workers=0,
        generator=generator if shuffle else None,
    )


def _build_smoke_loaders(
    smoke_cfg: HierarchicalSmokeConfig,
    base_cfg: HierarchicalTrainingConfig,
) -> tuple[dict[str, DataLoader], dict[str, dict[str, Any]]]:
    data_dir = smoke_cfg.resolve(smoke_cfg.hierarchical_data_dir)
    seed = int(base_cfg.raw.get("training", {}).get("seed", 42))
    smoke = smoke_cfg.smoke
    split_limits = {
        "train": int(smoke["train_samples"]),
        "val": int(smoke["val_samples"]),
        "test": int(smoke["test_samples"]),
    }
    loaders: dict[str, DataLoader] = {}
    summaries: dict[str, dict[str, Any]] = {}
    for offset, (split, limit) in enumerate(split_limits.items()):
        dataset, summary = build_hierarchical_smoke_dataset(
            data_dir,
            split,
            max_samples=limit,
            seed=seed + offset,
        )
        if summary["X_shape"][1] != base_cfg.input_dim:
            raise HierarchicalSmokeTrainingError(
                f"{split} feature dim {summary['X_shape'][1]} does not match "
                f"config input_dim {base_cfg.input_dim}."
            )
        if split == "train":
            counts = summary["binary_class_counts"]
            if counts["0"] == 0 or counts["1"] == 0 or summary["attack_rows"] == 0:
                raise HierarchicalSmokeTrainingError(
                    "Train smoke subset must include benign rows and attack rows."
                )
        loaders[split] = _make_loader(
            dataset,
            batch_size=int(smoke["batch_size"]),
            shuffle=(split == "train"),
            seed=seed + offset,
        )
        summaries[split] = summary
    return loaders, summaries


@torch.no_grad()
def _evaluate_smoke(
    model: torch.nn.Module,
    loader: DataLoader,
    device: torch.device,
    max_batches: int,
) -> dict[str, Any]:
    model.eval()
    y_binary_chunks: list[torch.Tensor] = []
    binary_logit_chunks: list[torch.Tensor] = []
    y_attack_chunks: list[torch.Tensor] = []
    attack_logit_chunks: list[torch.Tensor] = []
    mask_chunks: list[torch.Tensor] = []

    batches = 0
    for features, y_binary, y_attack_family, attack_family_mask in loader:
        if batches >= int(max_batches):
            break
        features = features.to(device)
        outputs = model(features)
        y_binary_chunks.append(y_binary.cpu())
        binary_logit_chunks.append(outputs["binary_logit"].detach().cpu())
        y_attack_chunks.append(y_attack_family.cpu())
        attack_logit_chunks.append(outputs["attack_logits"].detach().cpu())
        mask_chunks.append(attack_family_mask.cpu())
        batches += 1

    if batches == 0:
        raise HierarchicalSmokeTrainingError("Smoke evaluation saw zero batches.")

    diagnostics = compute_hierarchical_smoke_diagnostics(
        y_binary=torch.cat(y_binary_chunks),
        binary_logits=torch.cat(binary_logit_chunks),
        y_attack_family=torch.cat(y_attack_chunks),
        attack_logits=torch.cat(attack_logit_chunks),
        attack_family_mask=torch.cat(mask_chunks),
        threshold=0.5,
    )
    diagnostics["batches_evaluated"] = batches
    return diagnostics


def _snapshot_trainable_parameters(model: torch.nn.Module) -> dict[str, torch.Tensor]:
    return {
        name: parameter.detach().cpu().clone()
        for name, parameter in model.named_parameters()
        if parameter.requires_grad
    }


def _parameters_updated(
    before: dict[str, torch.Tensor],
    model: torch.nn.Module,
) -> bool:
    for name, parameter in model.named_parameters():
        if name in before and not torch.equal(before[name], parameter.detach().cpu()):
            return True
    return False


def _run_training_batches(
    model: torch.nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    base_cfg: HierarchicalTrainingConfig,
    max_batches: int,
    binary_pos_weight: float | None = None,
    attack_class_weights: list[float] | None = None,
) -> dict[str, Any]:
    loss_cfg = base_cfg.raw.get("loss", {})
    binary_loss_weight = float(loss_cfg.get("binary_loss_weight", 1.0))
    attack_loss_weight = float(loss_cfg.get("attack_loss_weight", 1.0))
    ignore_index = int(loss_cfg.get("ignore_index", -1))
    pos_weight_tensor = (
        torch.tensor([float(binary_pos_weight)], dtype=torch.float32, device=device)
        if binary_pos_weight is not None
        else None
    )
    attack_weight_tensor = (
        torch.tensor(attack_class_weights, dtype=torch.float32, device=device)
        if attack_class_weights is not None
        else None
    )

    model.train()
    first_batch_shapes: dict[str, list[int]] | None = None
    first_output_shapes: dict[str, list[int]] | None = None
    batch_progress: list[dict[str, Any]] = []
    forward_pass_ok = False
    backward_pass_ok = False
    loss_finite = False
    binary_loss_finite = False
    attack_loss_finite_or_zero = False

    before = _snapshot_trainable_parameters(model)
    batches_run = 0
    for batch_idx, (features, y_binary, y_attack_family, attack_family_mask) in enumerate(loader, start=1):
        if batches_run >= int(max_batches):
            break
        features = features.to(device)
        y_binary = y_binary.to(device)
        y_attack_family = y_attack_family.to(device)
        attack_family_mask = attack_family_mask.to(device)

        optimizer.zero_grad()
        outputs = model(features)
        forward_pass_ok = True

        if first_batch_shapes is None:
            first_batch_shapes = {
                "X": list(features.shape),
                "y_binary": list(y_binary.shape),
                "y_attack_family": list(y_attack_family.shape),
                "attack_family_mask": list(attack_family_mask.shape),
            }
            first_output_shapes = {
                "binary_logit": list(outputs["binary_logit"].shape),
                "attack_logits": list(outputs["attack_logits"].shape),
                "embedding": list(outputs["embedding"].shape),
            }
            _log(f"First batch shapes: {first_batch_shapes}")
            _log(f"First model output shapes: {first_output_shapes}")

        loss_bundle = compute_hierarchical_loss(
            outputs,
            y_binary=y_binary,
            y_attack_family=y_attack_family,
            attack_family_mask=attack_family_mask,
            binary_loss_weight=binary_loss_weight,
            attack_loss_weight=attack_loss_weight,
            ignore_index=ignore_index,
            pos_weight=pos_weight_tensor,
            attack_class_weights=attack_weight_tensor,
        )
        total_loss = loss_bundle["total_loss"]
        binary_loss = loss_bundle["binary_loss"]
        attack_loss = loss_bundle["attack_loss"]
        attack_rows = int(loss_bundle["attack_rows"])
        loss_finite = loss_finite or bool(torch.isfinite(total_loss).item())
        binary_loss_finite = binary_loss_finite or bool(torch.isfinite(binary_loss).item())
        attack_loss_finite_or_zero = attack_loss_finite_or_zero or bool(
            torch.isfinite(attack_loss).item()
        )

        total_loss.backward()
        grad_exists = any(
            parameter.grad is not None and bool(torch.isfinite(parameter.grad).any())
            for parameter in model.parameters()
        )
        backward_pass_ok = backward_pass_ok or grad_exists
        optimizer.step()

        batches_run += 1
        progress = {
            "batch": batches_run,
            "total_loss": float(total_loss.item()),
            "binary_loss": float(binary_loss.item()),
            "attack_loss": float(attack_loss.item()),
            "attack_rows": attack_rows,
        }
        batch_progress.append(progress)
        _log(
            "Train batch "
            f"{batch_idx}: total_loss={progress['total_loss']:.6f}, "
            f"binary_loss={progress['binary_loss']:.6f}, "
            f"attack_loss={progress['attack_loss']:.6f}, "
            f"attack_rows={attack_rows}"
        )

    params_updated = _parameters_updated(before, model)
    _log(f"Optimizer step updated parameters: {params_updated}")

    return {
        "batches_run": batches_run,
        "first_batch_shapes": first_batch_shapes,
        "first_output_shapes": first_output_shapes,
        "forward_pass_ok": forward_pass_ok,
        "backward_pass_ok": backward_pass_ok,
        "loss_finite": loss_finite,
        "binary_loss_finite": binary_loss_finite,
        "attack_loss_finite_or_zero": attack_loss_finite_or_zero,
        "optimizer_step_updated_parameters": params_updated,
        "binary_pos_weight_applied": bool(pos_weight_tensor is not None),
        "attack_class_weights_applied": bool(attack_weight_tensor is not None),
        "batch_progress": batch_progress,
    }


def _write_smoke_report(project_root: Path) -> Path:
    report_path = project_root / SMOKE_REPORT
    results: list[dict[str, Any]] = []
    for dataset, rel_path in EXPECTED_SMOKE_JSON.items():
        path = project_root / rel_path
        if path.exists():
            result = _load_json(path)
            result["_path"] = str(path)
            results.append(result)
        else:
            results.append(
                {
                    "dataset": dataset,
                    "status": "NOT_RUN",
                    "_path": str(path),
                    "smoke_only": True,
                    "non_final": True,
                    "do_not_report_as_final": True,
                }
            )

    lines: list[str] = [
        "# Hierarchical Smoke Training Check",
        "",
        "Status: `Task A7 smoke-only execution report`",
        "",
        "This report contains NON-FINAL smoke diagnostics only. It is a",
        "technical validation of data loading, forward/loss/optimizer plumbing,",
        "and small evaluation diagnostics. It is not final model performance.",
        "",
        f"Last updated UTC: `{utc_timestamp()}`",
        "",
        "## Safety Markers",
        "",
        "- smoke_only: `true`",
        "- non_final: `true`",
        "- do_not_report_as_final: `true`",
        "- checkpoint_created: `false`",
        "- final_metrics_created: `false`",
        "- full_training_run: `false`",
        "- final_checkpoint: `false`",
        "- final_results: `false`",
        "",
        "## Dataset Results",
        "",
    ]
    for result in results:
        diagnostics = result.get("smoke_diagnostics_non_final", {})
        train = result.get("training", {})
        samples = result.get("sample_selection", {})
        val_binary = diagnostics.get("val", {}).get("binary", {})
        val_attack = diagnostics.get("val", {}).get("attack_family", {})
        lines.extend(
            [
                f"### {result.get('dataset')} - {result.get('status')}",
                "",
                f"- output JSON: `{result.get('_path')}`",
                f"- train samples selected: `{samples.get('train', {}).get('selected_rows')}`",
                f"- val samples selected: `{samples.get('val', {}).get('selected_rows')}`",
                f"- test samples selected: `{samples.get('test', {}).get('selected_rows')}`",
                f"- batches run: `{train.get('batches_run')}`",
                f"- forward pass ok: `{train.get('forward_pass_ok')}`",
                f"- backward pass ok: `{train.get('backward_pass_ok')}`",
                f"- masked loss finite: `{train.get('loss_finite')}`",
                f"- binary loss finite: `{train.get('binary_loss_finite')}`",
                f"- attack loss finite or zero: `{train.get('attack_loss_finite_or_zero')}`",
                f"- optimizer updated parameters: `{train.get('optimizer_step_updated_parameters')}`",
                f"- smoke binary validation F1: `{val_binary.get('smoke_binary_f1')}`",
                f"- smoke attack rows evaluated: `{val_attack.get('attack_rows_evaluated')}`",
                "",
            ]
        )

    lines.extend(
        [
            "## What Was Not Done",
            "",
            "- No full hierarchical training was run.",
            "- No final hierarchical checkpoint was created.",
            "- No final hierarchical metrics, histories, or confusion matrices were created.",
            "- No hierarchical FedAvg, security, attacks, Trimmed Mean, XAI, or dashboard work was started.",
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def _build_dataset_result(
    smoke_cfg: HierarchicalSmokeConfig,
    base_cfg: HierarchicalTrainingConfig,
    plan: dict[str, Any],
    readiness: dict[str, Any],
    sample_summaries: dict[str, dict[str, Any]],
    training: dict[str, Any],
    val_diagnostics: dict[str, Any],
    test_diagnostics: dict[str, Any],
    device: torch.device,
) -> dict[str, Any]:
    passed = (
        plan["status"] == "PASS"
        and training["batches_run"] > 0
        and training["forward_pass_ok"]
        and training["backward_pass_ok"]
        and training["loss_finite"]
        and training["binary_loss_finite"]
        and training["attack_loss_finite_or_zero"]
        and training["optimizer_step_updated_parameters"]
        and val_diagnostics["binary"]["n_samples"] > 0
        and test_diagnostics["binary"]["n_samples"] > 0
    )
    return {
        "schema_version": "task_a7_hierarchical_smoke_training_v1",
        "dataset": smoke_cfg.dataset,
        "status": "PASS" if passed else "BLOCKED",
        "created_at_utc": utc_timestamp(),
        "smoke_only": True,
        "non_final": True,
        "do_not_report_as_final": True,
        "checkpoint_created": False,
        "final_metrics_created": False,
        "full_training_run": False,
        "final_checkpoint": False,
        "final_results": False,
        "config": {
            "smoke_config_path": str(smoke_cfg.path),
            "base_config_path": str(base_cfg.path),
            "input_dim": smoke_cfg.input_dim,
            "attack_head_dim": smoke_cfg.attack_head_dim,
            "model_name": smoke_cfg.model_name,
            "hierarchical_data_dir": str(smoke_cfg.resolve(smoke_cfg.hierarchical_data_dir)),
            "save_checkpoint": bool(smoke_cfg.smoke["save_checkpoint"]),
            "final_metrics": bool(smoke_cfg.smoke["final_metrics"]),
        },
        "readiness": {
            "status": readiness.get("status"),
            "ready_for_hierarchical_model_implementation": readiness.get(
                "ready_for_hierarchical_model_implementation"
            ),
            "readiness_json": str(base_cfg.resolve(base_cfg.readiness_json)),
        },
        "planning": {
            "status": plan["status"],
            "feature_count": plan.get("feature_count"),
            "attack_family_class_count": plan.get("attack_family_class_count"),
            "checks_passed": all(check["status"] == "PASS" for check in plan["checks"]),
        },
        "sample_selection": sample_summaries,
        "training": training,
        "smoke_diagnostics_non_final": {
            "val": val_diagnostics,
            "test": test_diagnostics,
        },
        "safety": {
            "smoke_only": True,
            "non_final": True,
            "do_not_report_as_final": True,
            "checkpoint_created": False,
            "final_metrics_created": False,
            "full_training_run": False,
            "final_checkpoint": False,
            "final_results": False,
            "hierarchical_fedavg_started": False,
            "security_attack_xai_dashboard_started": False,
            "model_weights_saved": False,
            "device": str(device),
        },
    }


def run_hierarchical_smoke(
    smoke_config_path: Path | str,
    project_root: Path | None = None,
    expected_dataset: str | None = None,
) -> dict[str, Any]:
    """Run one A7 smoke-only hierarchical training check and write outputs."""

    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    smoke_cfg = load_hierarchical_smoke_config(smoke_config_path, project_root=root)
    if expected_dataset is not None and expected_dataset != smoke_cfg.dataset:
        raise HierarchicalSmokeTrainingError(
            f"--dataset resolves to {expected_dataset!r}, but config is "
            f"for {smoke_cfg.dataset!r}."
        )

    _log(f"Starting hierarchical smoke training for {smoke_cfg.dataset}.")
    _log(f"Config loaded: {smoke_cfg.path}")

    base_cfg = load_hierarchical_training_config(
        smoke_cfg.resolve(smoke_cfg.base_config),
        project_root=root,
    )
    _validate_smoke_safety(smoke_cfg, base_cfg)
    _validate_no_final_outputs(base_cfg)
    readiness = _validate_readiness(base_cfg)
    _log("Readiness checked: PASS")

    plan = build_hierarchical_training_plan(base_cfg)
    if plan["status"] != "PASS":
        raise HierarchicalSmokeTrainingError(
            f"Hierarchical training plan is not PASS for {smoke_cfg.dataset}."
        )
    _log(
        "Config dimensions checked: "
        f"input_dim={plan['feature_count']}, attack_head_dim={plan['attack_family_class_count']}"
    )

    seed = int(base_cfg.raw.get("training", {}).get("seed", 42))
    set_global_seed(seed)
    loaders, sample_summaries = _build_smoke_loaders(smoke_cfg, base_cfg)
    _log(f"Sample sizes selected: {sample_summaries}")

    device = resolve_device()
    model = _build_model(base_cfg).to(device)
    training_cfg = base_cfg.raw.get("training", {})
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(training_cfg.get("learning_rate", 0.001)),
        weight_decay=float(training_cfg.get("weight_decay", 0.0001)),
    )

    # Apply the locked A8.5 train-only class weights through the masked loss so the
    # smoke run exercises the real weighted-training path (still non-final).
    binary_pos_weight: float | None = None
    attack_class_weights: list[float] | None = None
    try:
        locked_weights = build_train_only_class_weights(base_cfg.dataset, project_root=root)
        binary_pos_weight = float(locked_weights["binary_pos_weight"])
        attack_class_weights = [float(w) for w in locked_weights["attack_class_weights"]]
        _log(
            "Applying locked train-only class weights: "
            f"binary_pos_weight={binary_pos_weight:.4f}, "
            f"attack_class_weights={[round(w, 4) for w in attack_class_weights]}"
        )
    except Exception as error:  # noqa: BLE001 - smoke must not hard-fail on weights
        _log(f"Proceeding without class weights (build failed): {error}")

    training = _run_training_batches(
        model=model,
        loader=loaders["train"],
        optimizer=optimizer,
        device=device,
        base_cfg=base_cfg,
        max_batches=int(smoke_cfg.smoke["max_train_batches"]),
        binary_pos_weight=binary_pos_weight,
        attack_class_weights=attack_class_weights,
    )

    _log("Running tiny validation diagnostics.")
    val_diagnostics = _evaluate_smoke(
        model,
        loaders["val"],
        device,
        max_batches=int(smoke_cfg.smoke["max_eval_batches"]),
    )
    _log(f"Validation smoke diagnostics: {val_diagnostics}")

    _log("Running tiny test diagnostics for plumbing only.")
    test_diagnostics = _evaluate_smoke(
        model,
        loaders["test"],
        device,
        max_batches=int(smoke_cfg.smoke["max_eval_batches"]),
    )
    _log(f"Test smoke diagnostics: {test_diagnostics}")

    result = _build_dataset_result(
        smoke_cfg=smoke_cfg,
        base_cfg=base_cfg,
        plan=plan,
        readiness=readiness,
        sample_summaries=sample_summaries,
        training=training,
        val_diagnostics=val_diagnostics,
        test_diagnostics=test_diagnostics,
        device=device,
    )

    json_path = smoke_cfg.resolve(str(smoke_cfg.smoke["output_json"]))
    save_json(json_path, result)
    report_path = _write_smoke_report(root)
    _log(f"Output JSON path: {json_path}")
    _log(f"Smoke report path: {report_path}")
    _log(f"Final smoke status for {smoke_cfg.dataset}: {result['status']}")

    return {
        "status": result["status"],
        "dataset_result": result,
        "json_path": str(json_path),
        "report_path": str(report_path),
    }
