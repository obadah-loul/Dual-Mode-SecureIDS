"""Future real hierarchical FedAvg runner for SecureIDS V2.

This module provides a dry-run-safe implementation surface plus a guarded
``execute`` path for later manual approval. Importing the module never trains,
evaluates, writes checkpoints, or creates metrics.
"""

from __future__ import annotations

import copy
import csv
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from secureids.federated.byzantine_attacks import (
    ByzantineAttackError,
    apply_gaussian_noise,
    apply_scaling_attack,
    apply_sign_flip,
    select_malicious_clients,
    summarize_attack_effect,
)
from secureids.federated.hierarchical_plan import (
    HierarchicalFederatedPlan,
    HierarchicalFederatedPlanError,
    load_hierarchical_federated_plan,
)
from secureids.federated.robust_aggregation import (
    AggregationValidationError,
    aggregate_fedavg,
    aggregate_trimmed_mean,
)
from secureids.federated.splitting import (
    ClientSplitError,
    plan_attack_family_aware_iid_client_indices,
    summarize_hierarchical_client_distribution,
)
from secureids.models.secureids_hierarchical_advanced_net import (
    SecureIDSHierarchicalAdvancedNet,
    compute_hierarchical_loss,
)
from secureids.security.update_integrity import (
    make_update_integrity_record,
    sha256_update,
    verify_update_integrity_records,
)
from secureids.training.centralized import resolve_device, set_global_seed
from secureids.training.hierarchical_class_weights import build_train_only_class_weights
from secureids.training.hierarchical_datasets import (
    HierarchicalNumpyDataset,
    load_hierarchical_split,
)
from secureids.training.hierarchical_evaluation import evaluate_hierarchical_model


class HierarchicalFedAvgTrainingError(RuntimeError):
    """Raised when hierarchical FedAvg cannot safely proceed."""


SUPPORTED_ATTACK_TYPES = {"none", "sign_flip", "gaussian", "scaling"}
SUPPORTED_AGGREGATION_STRATEGIES = {"fedavg", "trimmed_mean"}
SUPPORTED_MALICIOUS_FRACTIONS = (0.0, 0.25, 0.50)
LEGACY_SELECTION_STRATEGY = "hierarchical_score"
SAFETY_GATED_SELECTION_STRATEGY = "safety_gated_hierarchical_score"
SAFETY_SELECTION_METRIC = "val_attack_missed_as_benign_rate"
SUPPORTED_SELECTION_FALLBACKS = {"safest_round", "raise_error", "error"}
SUPPORTED_SELECTION_TIE_BREAKERS = {
    "val_attack_family_macro_f1",
    "val_rare_class_macro_f1",
    "earliest_round",
}


@dataclass(frozen=True)
class HierarchicalFedAvgOutcome:
    """Summary returned after a future actual run."""

    status: str
    dataset: str
    checkpoint_path: str
    metrics_path: str
    manifest_path: str
    report_path: str
    best_round: int
    rounds_run: int
    test_metrics: dict[str, Any]


def _torch():
    try:
        import torch
    except ModuleNotFoundError as error:  # pragma: no cover - environment specific
        raise HierarchicalFedAvgTrainingError(
            "PyTorch is required for hierarchical FedAvg execution."
        ) from error
    return torch


def _project_path(project_root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_root / path


def planned_output_paths(
    plan: HierarchicalFederatedPlan,
    project_root: Path,
) -> dict[str, Path]:
    """Return all guarded future output paths for a hierarchical FL plan."""

    outputs = plan.raw["outputs"]
    paths = {
        "checkpoint": _project_path(project_root, outputs["checkpoint"]),
        "result_dir": _project_path(project_root, outputs["result_dir"]),
        "round_history": _project_path(project_root, outputs["round_history"]),
        "client_distribution": _project_path(project_root, outputs["client_distribution"]),
        "test_metrics": _project_path(project_root, outputs["test_metrics"]),
        "audit_json": _project_path(project_root, outputs["audit_json"]),
        "report_md": _project_path(project_root, outputs["report_md"]),
    }
    selection = plan.raw.get("selection")
    if isinstance(selection, dict) and selection.get("save_per_round_checkpoints") is True:
        checkpoint_dir = selection.get("per_round_checkpoint_dir")
        if checkpoint_dir is None:
            checkpoint_dir = Path(outputs["result_dir"]) / "round_checkpoints"
        paths["per_round_checkpoint_dir"] = _project_path(project_root, checkpoint_dir)
    return paths


def existing_planned_outputs(
    plan: HierarchicalFederatedPlan,
    project_root: Path,
) -> list[Path]:
    """Return planned output files/dirs that already exist."""

    paths = planned_output_paths(plan, project_root)
    return [path for path in paths.values() if path.exists()]


def _require_finite_float(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise HierarchicalFedAvgTrainingError(f"{name} must be a finite number.")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as error:
        raise HierarchicalFedAvgTrainingError(f"{name} must be a finite number.") from error
    if not math.isfinite(numeric):
        raise HierarchicalFedAvgTrainingError(f"{name} must be a finite number.")
    return numeric


def _canonical_attack_type(value: Any) -> str:
    attack_type = str(value or "none").strip().lower().replace("-", "_")
    if attack_type == "signflip":
        attack_type = "sign_flip"
    if attack_type not in SUPPORTED_ATTACK_TYPES:
        raise HierarchicalFedAvgTrainingError(
            f"Unsupported attack type {value!r}. Supported attacks: "
            f"{sorted(SUPPORTED_ATTACK_TYPES)}."
        )
    return attack_type


def _validate_attack_config(plan: HierarchicalFederatedPlan) -> dict[str, Any]:
    raw_attack = dict(plan.raw.get("attack", {}) or {})
    enabled = bool(raw_attack.get("enabled", False))
    attack_type = _canonical_attack_type(raw_attack.get("type", "none"))
    malicious_fraction = _require_finite_float(
        raw_attack.get("malicious_fraction", 0.0),
        "attack.malicious_fraction",
    )
    if not any(
        abs(malicious_fraction - supported) < 1e-12
        for supported in SUPPORTED_MALICIOUS_FRACTIONS
    ):
        raise HierarchicalFedAvgTrainingError(
            "attack.malicious_fraction must be one of 0.0, 0.25, or 0.50."
        )
    if isinstance(raw_attack.get("seed", 42), bool):
        raise HierarchicalFedAvgTrainingError("attack.seed must be an integer.")
    try:
        seed = int(raw_attack.get("seed", 42))
    except (TypeError, ValueError) as error:
        raise HierarchicalFedAvgTrainingError("attack.seed must be an integer.") from error

    if not enabled or attack_type == "none":
        if malicious_fraction != 0.0:
            raise HierarchicalFedAvgTrainingError(
                "Disabled/no-op attacks must use attack.malicious_fraction: 0.0."
            )
        enabled = False
        attack_type = "none"

    parameters: dict[str, Any] = {}
    if attack_type == "sign_flip":
        parameters["scale"] = _require_finite_float(raw_attack.get("scale", -1.0), "attack.scale")
    elif attack_type == "gaussian":
        parameters["gaussian_std"] = _require_finite_float(
            raw_attack.get("gaussian_std", raw_attack.get("std", 0.1)),
            "attack.gaussian_std",
        )
        if parameters["gaussian_std"] < 0.0:
            raise HierarchicalFedAvgTrainingError("attack.gaussian_std must be >= 0.")
    elif attack_type == "scaling":
        parameters["scaling_factor"] = _require_finite_float(
            raw_attack.get("scaling_factor", raw_attack.get("scale", 10.0)),
            "attack.scaling_factor",
        )

    return {
        "enabled": enabled,
        "type": attack_type,
        "configured_type": raw_attack.get("type", "none"),
        "malicious_fraction": malicious_fraction,
        "seed": seed,
        "parameters": parameters,
    }


def _validate_aggregation_config(plan: HierarchicalFederatedPlan) -> dict[str, Any]:
    raw_aggregation = dict(plan.raw.get("aggregation", {}) or {})
    strategy = str(raw_aggregation.get("strategy", "fedavg")).strip().lower().replace("-", "_")
    if strategy not in SUPPORTED_AGGREGATION_STRATEGIES:
        raise HierarchicalFedAvgTrainingError(
            f"Unsupported aggregation strategy {strategy!r}. Supported strategies: "
            f"{sorted(SUPPORTED_AGGREGATION_STRATEGIES)}."
        )
    trim_ratio: float | None = None
    if strategy == "trimmed_mean":
        trim_ratio = _require_finite_float(
            raw_aggregation.get("trim_ratio", 0.2),
            "aggregation.trim_ratio",
        )
        if trim_ratio < 0.0 or trim_ratio >= 0.5:
            raise HierarchicalFedAvgTrainingError(
                "aggregation.trim_ratio must satisfy 0 <= ratio < 0.5."
            )
    return {
        "strategy": strategy,
        "trim_ratio": trim_ratio,
        "sample_count_weighted": strategy == "fedavg",
    }


def _require_bool_value(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise HierarchicalFedAvgTrainingError(f"{name} must be true or false.")
    return bool(value)


def _validate_selection_config(
    plan: HierarchicalFederatedPlan,
    project_root: Path,
) -> dict[str, Any]:
    raw_selection = plan.raw.get("selection")
    if raw_selection is None:
        return {
            "configured": False,
            "strategy": LEGACY_SELECTION_STRATEGY,
            "safety_metric": None,
            "relative_margin": None,
            "absolute_max_missed_as_benign": None,
            "fallback": None,
            "tie_breakers": [],
            "save_per_round_checkpoints": False,
            "per_round_checkpoint_dir": None,
        }
    if not isinstance(raw_selection, dict):
        raise HierarchicalFedAvgTrainingError("selection must be a mapping.")

    strategy = str(raw_selection.get("strategy", "")).strip().lower().replace("-", "_")
    if strategy != SAFETY_GATED_SELECTION_STRATEGY:
        raise HierarchicalFedAvgTrainingError(
            f"Unsupported selection strategy {strategy!r}. Supported strategy: "
            f"{SAFETY_GATED_SELECTION_STRATEGY!r}."
        )

    safety_metric = str(
        raw_selection.get("safety_metric", SAFETY_SELECTION_METRIC)
    ).strip()
    if safety_metric != SAFETY_SELECTION_METRIC:
        raise HierarchicalFedAvgTrainingError(
            f"Unsupported selection.safety_metric {safety_metric!r}. Supported "
            f"metric: {SAFETY_SELECTION_METRIC!r}."
        )

    relative_margin = _require_finite_float(
        raw_selection.get("relative_margin", 0.0),
        "selection.relative_margin",
    )
    if relative_margin < 0.0:
        raise HierarchicalFedAvgTrainingError("selection.relative_margin must be >= 0.")

    absolute_raw = raw_selection.get("absolute_max_missed_as_benign")
    absolute_max = None
    if absolute_raw is not None:
        absolute_max = _require_finite_float(
            absolute_raw,
            "selection.absolute_max_missed_as_benign",
        )
        if absolute_max < 0.0 or absolute_max > 1.0:
            raise HierarchicalFedAvgTrainingError(
                "selection.absolute_max_missed_as_benign must be in [0, 1]."
            )

    fallback = str(raw_selection.get("fallback", "safest_round")).strip().lower().replace("-", "_")
    if fallback not in SUPPORTED_SELECTION_FALLBACKS:
        raise HierarchicalFedAvgTrainingError(
            f"Unsupported selection.fallback {fallback!r}. Supported fallbacks: "
            f"{sorted(SUPPORTED_SELECTION_FALLBACKS)}."
        )

    tie_breakers = raw_selection.get(
        "tie_breakers",
        ["val_attack_family_macro_f1", "val_rare_class_macro_f1", "earliest_round"],
    )
    if not isinstance(tie_breakers, list) or not all(
        isinstance(value, str) for value in tie_breakers
    ):
        raise HierarchicalFedAvgTrainingError("selection.tie_breakers must be a string list.")
    unsupported = [
        value for value in tie_breakers if value not in SUPPORTED_SELECTION_TIE_BREAKERS
    ]
    if unsupported:
        raise HierarchicalFedAvgTrainingError(
            f"Unsupported selection.tie_breakers: {unsupported}. Supported tie "
            f"breakers: {sorted(SUPPORTED_SELECTION_TIE_BREAKERS)}."
        )

    save_per_round = _require_bool_value(
        raw_selection.get("save_per_round_checkpoints", False),
        "selection.save_per_round_checkpoints",
    )
    checkpoint_dir = None
    if save_per_round:
        output_dir = plan.raw["outputs"]["result_dir"]
        checkpoint_dir_value = raw_selection.get("per_round_checkpoint_dir")
        if checkpoint_dir_value is None:
            checkpoint_dir_value = Path(output_dir) / "round_checkpoints"
        checkpoint_dir = str(_project_path(project_root, checkpoint_dir_value))

    return {
        "configured": True,
        "strategy": strategy,
        "safety_metric": safety_metric,
        "relative_margin": relative_margin,
        "absolute_max_missed_as_benign": absolute_max,
        "fallback": fallback,
        "tie_breakers": list(tie_breakers),
        "save_per_round_checkpoints": save_per_round,
        "per_round_checkpoint_dir": checkpoint_dir,
    }


def _select_malicious_client_indices(
    attack_config: dict[str, Any],
    num_clients: int,
) -> list[int]:
    if not attack_config["enabled"] or attack_config["type"] == "none":
        return []
    try:
        return select_malicious_clients(
            num_clients=num_clients,
            malicious_fraction=float(attack_config["malicious_fraction"]),
            seed=int(attack_config["seed"]),
        )
    except ByzantineAttackError as error:
        raise HierarchicalFedAvgTrainingError(str(error)) from error


def _apply_attack_to_client_updates(
    client_updates: list[dict[str, Any]],
    client_ids: list[str],
    attack_config: dict[str, Any],
    malicious_indices: list[int],
    round_id: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    malicious_client_ids = [client_ids[index] for index in malicious_indices]
    attack_round = {
        "round": int(round_id),
        "enabled": bool(attack_config["enabled"]),
        "type": attack_config["type"],
        "configured_type": attack_config["configured_type"],
        "malicious_fraction": float(attack_config["malicious_fraction"]),
        "seed": int(attack_config["seed"]),
        "parameters": dict(attack_config["parameters"]),
        "malicious_client_indices": [int(index) for index in malicious_indices],
        "malicious_client_ids": malicious_client_ids,
        "attack_applied": False,
        "warnings": [],
    }

    if not attack_config["enabled"] or attack_config["type"] == "none":
        return client_updates, attack_round
    if not malicious_indices:
        attack_round["warnings"].append(
            "No malicious clients selected; attack transform was not applied."
        )
        return client_updates, attack_round

    try:
        if attack_config["type"] == "sign_flip":
            attacked_updates = apply_sign_flip(
                client_updates,
                malicious_indices,
                scale=float(attack_config["parameters"].get("scale", -1.0)),
            )
        elif attack_config["type"] == "gaussian":
            attacked_updates = apply_gaussian_noise(
                client_updates,
                malicious_indices,
                std=float(attack_config["parameters"]["gaussian_std"]),
                seed=int(attack_config["seed"]) + int(round_id),
            )
            attack_round["transform_seed"] = int(attack_config["seed"]) + int(round_id)
        elif attack_config["type"] == "scaling":
            attacked_updates = apply_scaling_attack(
                client_updates,
                malicious_indices,
                scale=float(attack_config["parameters"]["scaling_factor"]),
            )
        else:  # Defensive guard; validation should reject first.
            raise HierarchicalFedAvgTrainingError(
                f"Unsupported attack type {attack_config['type']!r}."
            )
        attack_round["attack_applied"] = True
        attack_round["effect_summary"] = summarize_attack_effect(
            client_updates,
            attacked_updates,
            malicious_indices,
        )
        return attacked_updates, attack_round
    except ByzantineAttackError as error:
        raise HierarchicalFedAvgTrainingError(str(error)) from error


def _aggregate_client_updates(
    client_updates: list[dict[str, Any]],
    sample_counts: list[int],
    aggregation_config: dict[str, Any],
) -> dict[str, Any]:
    try:
        if aggregation_config["strategy"] == "fedavg":
            return aggregate_fedavg(client_updates, weights=sample_counts)
        if aggregation_config["strategy"] == "trimmed_mean":
            return aggregate_trimmed_mean(
                client_updates,
                trim_ratio=float(aggregation_config["trim_ratio"]),
            )
    except AggregationValidationError as error:
        raise HierarchicalFedAvgTrainingError(str(error)) from error
    raise HierarchicalFedAvgTrainingError(
        f"Unsupported aggregation strategy {aggregation_config['strategy']!r}."
    )


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise HierarchicalFedAvgTrainingError(f"Expected JSON object: {path}")
    return payload


def _class_names(mapping: dict[str, Any], attack_head_dim: int) -> list[str]:
    id_to_class = mapping.get("id_to_class", {})
    names: list[str] = []
    for index in range(int(attack_head_dim)):
        if not isinstance(id_to_class, dict) or str(index) not in id_to_class:
            raise HierarchicalFedAvgTrainingError(
                f"attack family mapping missing class id {index}."
            )
        names.append(str(id_to_class[str(index)]))
    return names


def build_model_from_plan(plan: HierarchicalFederatedPlan) -> SecureIDSHierarchicalAdvancedNet:
    """Build a hierarchical model from scratch from a validated plan."""

    model_cfg = plan.raw["model"]
    hidden_dims = tuple(int(v) for v in model_cfg.get("hidden_dims", (256, 128, 128)))
    return SecureIDSHierarchicalAdvancedNet(
        input_dim=int(model_cfg["input_dim"]),
        attack_head_dim=int(model_cfg["attack_head_dim"]),
        hidden_dims=hidden_dims,
        dropout=float(model_cfg.get("dropout", 0.20)),
        normalization=str(model_cfg.get("normalization", "layernorm")),
        attack_head_type=str(model_cfg.get("attack_head_type", "linear")),
        attack_head_hidden_dim=model_cfg.get("attack_head_hidden_dim"),
        attack_head_norm=bool(model_cfg.get("attack_head_norm", True)),
        attack_head_dropout=model_cfg.get("attack_head_dropout"),
    )


def load_train_arrays_for_split_audit(plan: HierarchicalFederatedPlan) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load train labels/mask only for client split planning."""

    data_dir = Path(plan.checked_paths["processed_dir"])
    _, y_binary, y_attack_family, attack_family_mask = load_hierarchical_split(
        data_dir,
        "train",
        mmap=True,
    )
    return y_binary, y_attack_family, attack_family_mask


def plan_hierarchical_client_split(
    plan: HierarchicalFederatedPlan,
) -> dict[str, Any]:
    """Plan attack-family-aware IID client indices and distribution audit."""

    y_binary, y_attack_family, attack_family_mask = load_train_arrays_for_split_audit(plan)
    federation = plan.raw["federation"]
    indices = plan_attack_family_aware_iid_client_indices(
        y_binary=y_binary,
        y_attack_family=y_attack_family,
        attack_family_mask=attack_family_mask,
        num_clients=int(federation["num_clients"]),
        seed=int(federation["seed"]),
    )
    rows, warnings = summarize_hierarchical_client_distribution(
        y_binary=y_binary,
        y_attack_family=y_attack_family,
        attack_family_mask=attack_family_mask,
        client_indices=indices,
        min_attack_family_support_per_client=int(
            federation.get("min_attack_family_support_per_client", 1)
        ),
    )
    return {
        "client_indices": indices,
        "client_distribution": rows,
        "warnings": warnings,
        "train_rows": int(np.asarray(y_binary).reshape(-1).shape[0]),
    }


def validate_aggregation_with_integrity(
    client_updates: list[dict[str, Any]],
    sample_counts: list[int],
    client_ids: list[str],
    round_id: int,
    aggregation_config: dict[str, Any] | None = None,
    attack_round: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Hash, verify, and aggregate client updates for one future round."""

    if len(client_updates) != len(sample_counts) or len(client_updates) != len(client_ids):
        raise HierarchicalFedAvgTrainingError(
            "client_updates, sample_counts, and client_ids must have equal length."
        )
    effective_aggregation = aggregation_config or {
        "strategy": "fedavg",
        "trim_ratio": None,
        "sample_count_weighted": True,
    }
    effective_attack = attack_round or {
        "enabled": False,
        "type": "none",
        "malicious_client_ids": [],
        "attack_applied": False,
    }
    malicious_client_ids = set(str(value) for value in effective_attack["malicious_client_ids"])
    records = [
        make_update_integrity_record(
            client_id=client_id,
            round_id=round_id,
            update_hash=sha256_update(update),
            metadata={
                "sample_count": int(sample_count),
                "aggregation_strategy": effective_aggregation["strategy"],
                "attack_type": effective_attack["type"],
                "attack_applied": bool(effective_attack["attack_applied"]),
                "malicious_client": str(client_id) in malicious_client_ids,
            },
        )
        for client_id, update, sample_count in zip(client_ids, client_updates, sample_counts)
    ]
    verification = verify_update_integrity_records(records, client_updates)
    if not verification["all_verified"]:
        raise HierarchicalFedAvgTrainingError("Client update hash verification failed.")
    aggregated = _aggregate_client_updates(
        client_updates,
        sample_counts,
        effective_aggregation,
    )
    return {
        "aggregated_state_dict": aggregated,
        "integrity_records": records,
        "verification": verification,
        "aggregation_audit": {
            "round": int(round_id),
            "algorithm": effective_aggregation["strategy"],
            "strategy": effective_aggregation["strategy"],
            "trim_ratio": effective_aggregation["trim_ratio"],
            "sample_count_weighted": bool(effective_aggregation["sample_count_weighted"]),
            "client_ids": list(client_ids),
            "sample_counts": [int(value) for value in sample_counts],
            "total_samples": int(sum(sample_counts)),
            "integrity_verified": bool(verification["all_verified"]),
            "attack_type": effective_attack["type"],
            "attack_applied": bool(effective_attack["attack_applied"]),
            "malicious_client_ids": list(effective_attack["malicious_client_ids"]),
        },
    }


def verify_client_update_integrity(
    integrity_records: list[dict[str, Any]],
    client_updates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Verify pre-existing update integrity records before aggregation."""

    verification = verify_update_integrity_records(integrity_records, client_updates)
    if not verification["all_verified"]:
        raise HierarchicalFedAvgTrainingError("Client update hash verification failed.")
    return verification


def _make_loader(
    dataset: Any,
    batch_size: int,
    shuffle: bool,
    seed: int,
) -> Any:
    torch = _torch()
    generator = None
    if shuffle:
        generator = torch.Generator()
        generator.manual_seed(int(seed))
    return torch.utils.data.DataLoader(
        dataset,
        batch_size=int(batch_size),
        shuffle=bool(shuffle),
        drop_last=False,
        num_workers=0,
        generator=generator,
    )


def _train_local_model(
    global_model: Any,
    train_dataset: HierarchicalNumpyDataset,
    plan: HierarchicalFederatedPlan,
    weights: dict[str, Any],
    device: Any,
    seed: int,
) -> tuple[dict[str, Any], float]:
    torch = _torch()
    local_model = build_model_from_plan(plan).to(device)
    local_model.load_state_dict(copy.deepcopy(global_model.state_dict()))
    training_cfg = plan.raw["training"]
    loader = _make_loader(
        train_dataset,
        batch_size=int(training_cfg["batch_size"]),
        shuffle=True,
        seed=seed,
    )
    optimizer = torch.optim.AdamW(
        local_model.parameters(),
        lr=float(training_cfg["learning_rate"]),
        weight_decay=float(training_cfg.get("weight_decay", 0.0001)),
    )
    pos_weight = torch.tensor([float(weights["binary_pos_weight"])], device=device)
    attack_class_weights = torch.tensor(
        [float(v) for v in weights["attack_class_weights"]],
        dtype=torch.float32,
        device=device,
    )
    loss_cfg = plan.raw.get("loss", {})
    total_loss = 0.0
    rows_seen = 0
    local_model.train()
    for _ in range(int(plan.raw["federation"]["local_epochs"])):
        for features, yb, ya, mask in loader:
            features = features.to(device)
            yb = yb.to(device)
            ya = ya.to(device)
            mask = mask.to(device)
            optimizer.zero_grad()
            bundle = compute_hierarchical_loss(
                local_model(features),
                y_binary=yb,
                y_attack_family=ya,
                attack_family_mask=mask,
                binary_loss_weight=float(loss_cfg.get("binary_loss_weight", 1.0)),
                attack_loss_weight=float(loss_cfg.get("attack_loss_weight", 1.0)),
                ignore_index=int(loss_cfg.get("ignore_index", -1)),
                pos_weight=pos_weight,
                attack_class_weights=attack_class_weights,
            )
            loss = bundle["total_loss"]
            if not torch.isfinite(loss):
                raise HierarchicalFedAvgTrainingError("Local client loss became non-finite.")
            loss.backward()
            optimizer.step()
            batch = int(features.shape[0])
            total_loss += float(loss.item()) * batch
            rows_seen += batch
    average_loss = total_loss / float(max(rows_seen, 1))
    return copy.deepcopy(local_model.state_dict()), average_loss


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), restval="")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _metric_if_present(value: Any, integer: bool = False) -> Any:
    if value is None:
        return ""
    if integer:
        return int(value)
    return float(value)


def _validation_selection_fields(val_metrics: dict[str, Any]) -> dict[str, Any]:
    binary = val_metrics.get("binary", {})
    selection = val_metrics.get("selection", {})
    routing = val_metrics.get("hierarchical_routing", {})
    rare_class = val_metrics.get("rare_class", {})
    return {
        "val_binary_macro_f1": _metric_if_present(selection.get("val_binary_macro_f1")),
        "val_attack_family_macro_f1": _metric_if_present(
            selection.get("val_attack_family_macro_f1")
        ),
        "val_hierarchical_score": _metric_if_present(
            selection.get("val_hierarchical_score")
        ),
        "val_binary_recall": _metric_if_present(binary.get("recall")),
        "val_attack_false_negatives": _metric_if_present(
            binary.get("attack_false_negatives"),
            integer=True,
        ),
        "val_attack_missed_as_benign_rate": _metric_if_present(
            routing.get("attack_missed_as_benign_rate")
        ),
        "val_rare_class_macro_f1": _metric_if_present(
            rare_class.get("rare_class_macro_f1")
        ),
    }


def _round_metric(row: dict[str, Any], metric_name: str) -> float:
    value = row.get(metric_name)
    if value == "":
        raise HierarchicalFedAvgTrainingError(
            f"Round {row.get('round')} is missing required selection metric "
            f"{metric_name!r}."
        )
    return _require_finite_float(value, f"round_history.{metric_name}")


def _selected_round_safety_metrics(row: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "val_binary_recall",
        "val_attack_false_negatives",
        "val_attack_missed_as_benign_rate",
        "val_binary_macro_f1",
        "val_attack_family_macro_f1",
        "val_rare_class_macro_f1",
        "val_hierarchical_score",
    )
    return {key: row.get(key, "") for key in keys}


def _legacy_selection_result(
    round_rows: list[dict[str, Any]],
    best_round: int,
) -> dict[str, Any]:
    selected_row = next(row for row in round_rows if int(row["round"]) == int(best_round))
    return {
        "strategy": LEGACY_SELECTION_STRATEGY,
        "configured": False,
        "safety_metric": None,
        "relative_margin": None,
        "absolute_max_missed_as_benign": None,
        "selected_round": int(best_round),
        "safety_gate_satisfied": None,
        "number_eligible_rounds": None,
        "selected_round_safety_metrics": _selected_round_safety_metrics(selected_row),
        "save_per_round_checkpoints": False,
        "per_round_checkpoint_dir": None,
    }


def _safety_tie_key(
    row: dict[str, Any],
    tie_breakers: list[str],
) -> tuple[float, ...]:
    values: list[float] = [_round_metric(row, "val_hierarchical_score")]
    for tie_breaker in tie_breakers:
        if tie_breaker == "earliest_round":
            values.append(-float(int(row["round"])))
        else:
            values.append(_round_metric(row, tie_breaker))
    return tuple(values)


def _select_safety_gated_round(
    round_rows: list[dict[str, Any]],
    selection_config: dict[str, Any],
) -> dict[str, Any]:
    if not round_rows:
        raise HierarchicalFedAvgTrainingError("No validation rounds were available.")

    safety_metric = str(selection_config["safety_metric"])
    margin = float(selection_config["relative_margin"])
    metric_values = [_round_metric(row, safety_metric) for row in round_rows]
    minimum_safety_metric = min(metric_values)
    relative_limit = minimum_safety_metric + margin
    absolute_limit = selection_config["absolute_max_missed_as_benign"]

    eligible_rows: list[dict[str, Any]] = []
    for row in round_rows:
        metric_value = _round_metric(row, safety_metric)
        relative_ok = metric_value <= relative_limit
        absolute_ok = absolute_limit is None or metric_value <= float(absolute_limit)
        eligible = relative_ok and absolute_ok
        row["safety_gate_eligible"] = eligible
        row["selected_by_safety_gate"] = False
        if eligible:
            eligible_rows.append(row)

    safety_gate_satisfied = bool(eligible_rows)
    if eligible_rows:
        candidate_rows = eligible_rows
    else:
        if selection_config["fallback"] in {"raise_error", "error"}:
            raise HierarchicalFedAvgTrainingError(
                "No validation round satisfied the configured safety gate."
            )
        candidate_rows = [
            row
            for row in round_rows
            if _round_metric(row, safety_metric) == minimum_safety_metric
        ]

    selected_row = max(
        candidate_rows,
        key=lambda row: _safety_tie_key(row, selection_config["tie_breakers"]),
    )
    selected_row["selected_by_safety_gate"] = safety_gate_satisfied
    return {
        "strategy": selection_config["strategy"],
        "configured": True,
        "safety_metric": safety_metric,
        "relative_margin": margin,
        "absolute_max_missed_as_benign": absolute_limit,
        "minimum_safety_metric": minimum_safety_metric,
        "relative_safety_limit": relative_limit,
        "selected_round": int(selected_row["round"]),
        "safety_gate_satisfied": safety_gate_satisfied,
        "number_eligible_rounds": len(eligible_rows),
        "selected_round_safety_metrics": _selected_round_safety_metrics(selected_row),
        "fallback": selection_config["fallback"],
        "tie_breakers": list(selection_config["tie_breakers"]),
        "save_per_round_checkpoints": bool(selection_config["save_per_round_checkpoints"]),
        "per_round_checkpoint_dir": selection_config["per_round_checkpoint_dir"],
    }


def _save_round_checkpoint(
    torch: Any,
    path: Path,
    global_model: Any,
    plan: HierarchicalFederatedPlan,
    round_id: int,
    val_metrics: dict[str, Any],
    attack_config: dict[str, Any],
    aggregation_config: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": copy.deepcopy(global_model.state_dict()),
            "dataset": plan.dataset,
            "protocol_label": plan.raw["protocol_label"],
            "round": int(round_id),
            "validation_selection": val_metrics.get("selection", {}),
            "validation_safety": _validation_selection_fields(val_metrics),
            "centralized_reference": plan.raw["centralized_reference"],
            "initialization": "from_scratch",
            "attack": attack_config,
            "aggregation": aggregation_config,
        },
        path,
    )


def _write_report(
    path: Path,
    plan: HierarchicalFederatedPlan,
    outcome: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Hierarchical Federated Experiment Report",
        "",
        f"Dataset: `{plan.dataset}`",
        f"Protocol: `{plan.raw['protocol_label']}`",
        f"Aggregation: `{outcome['aggregation']['strategy']}`",
        f"Attack: `{outcome['attack']['type']}`",
        f"Malicious fraction: `{outcome['attack']['malicious_fraction']}`",
        f"Selected malicious clients: `{outcome['attack']['malicious_client_ids']}`",
        "",
        "Status: future actual run completed under explicit main-control approval.",
        "",
        "Safety notes:",
        "",
        "- Centralized final checkpoint was reference-only.",
        "- Initialization was from scratch.",
        "- No `models/final/` or `results/final/` path was written.",
        "- This FL checkpoint is experimental and not promoted.",
        "",
        "Results:",
        "",
        f"- Best round: `{outcome['best_round']}`",
        f"- Rounds run: `{outcome['rounds_run']}`",
        f"- Test metrics path: `{outcome['metrics_path']}`",
        f"- Manifest path: `{outcome['manifest_path']}`",
        f"- SHA-256 update integrity verified: `{outcome['integrity_verified']}`",
    ]
    selection = outcome.get("selection")
    if selection:
        selected_metrics = selection.get("selected_round_safety_metrics", {})
        lines.extend(
            [
                "",
                "Selection:",
                "",
                f"- Strategy: `{selection.get('strategy')}`",
                f"- Safety metric: `{selection.get('safety_metric')}`",
                f"- Relative margin: `{selection.get('relative_margin')}`",
                "- Absolute missed-as-benign max: "
                f"`{selection.get('absolute_max_missed_as_benign')}`",
                f"- Selected round: `{selection.get('selected_round')}`",
                f"- Safety gate satisfied: `{selection.get('safety_gate_satisfied')}`",
                f"- Eligible rounds: `{selection.get('number_eligible_rounds')}`",
                "- Selected round missed-as-benign rate: "
                f"`{selected_metrics.get('val_attack_missed_as_benign_rate')}`",
                "- Selected round binary recall: "
                f"`{selected_metrics.get('val_binary_recall')}`",
                "- Per-round checkpoints saved: "
                f"`{selection.get('save_per_round_checkpoints')}`",
                "- Per-round checkpoint folder: "
                f"`{selection.get('per_round_checkpoint_dir')}`",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_hierarchical_fedavg_dry_run(
    config_path: str | Path,
    project_root: Path,
) -> dict[str, Any]:
    """Validate a hierarchical FedAvg config and write nothing."""

    plan = load_hierarchical_federated_plan(config_path, project_root=project_root)
    attack_config = _validate_attack_config(plan)
    aggregation_config = _validate_aggregation_config(plan)
    selection_config = _validate_selection_config(plan, project_root)
    outputs = planned_output_paths(plan, project_root)
    path_checks = [
        {"name": name, "path": str(path), "exists": Path(path).exists()}
        for name, path in plan.checked_paths.items()
    ]
    planned_output_checks = [
        {"name": name, "path": str(path), "exists": path.exists()}
        for name, path in outputs.items()
    ]
    return {
        "status": "PASS",
        "dataset": plan.dataset,
        "config_path": str(plan.path),
        "protocol_label": plan.raw["protocol_label"],
        "initialization": plan.raw.get("initialization", "from_scratch"),
        "centralized_reference": plan.raw["centralized_reference"],
        "aggregation": aggregation_config,
        "attack": attack_config,
        "selection": selection_config,
        "integrity": plan.raw["integrity"],
        "path_checks": path_checks,
        "expected_outputs": {name: str(path) for name, path in outputs.items()},
        "planned_output_checks": planned_output_checks,
        "writes_outputs": False,
        "training_run": False,
        "evaluation_run": False,
        "checkpoint_created": False,
        "metrics_created": False,
    }


def run_hierarchical_fedavg_training(
    config_path: str | Path,
    project_root: Path,
    execute: bool = False,
    overwrite: bool = False,
) -> dict[str, Any] | HierarchicalFedAvgOutcome:
    """Dry-run or execute future hierarchical FedAvg training."""

    if not execute:
        return run_hierarchical_fedavg_dry_run(config_path, project_root)

    plan = load_hierarchical_federated_plan(config_path, project_root=project_root)
    attack_config = _validate_attack_config(plan)
    aggregation_config = _validate_aggregation_config(plan)
    selection_config = _validate_selection_config(plan, project_root)
    outputs = planned_output_paths(plan, project_root)
    existing = existing_planned_outputs(plan, project_root)
    if existing and not overwrite:
        raise HierarchicalFedAvgTrainingError(
            "planned hierarchical FedAvg outputs already exist: "
            + "; ".join(str(path) for path in existing)
        )

    torch = _torch()
    training_cfg = plan.raw["training"]
    seed = int(training_cfg["seed"])
    set_global_seed(seed)
    device = resolve_device()

    data_dir = Path(plan.checked_paths["processed_dir"])
    X_train, y_binary_train, y_attack_train, mask_train = load_hierarchical_split(
        data_dir, "train", mmap=True
    )
    X_val, y_binary_val, y_attack_val, mask_val = load_hierarchical_split(
        data_dir, "val", mmap=True
    )
    X_test, y_binary_test, y_attack_test, mask_test = load_hierarchical_split(
        data_dir, "test", mmap=True
    )

    split_plan = plan_hierarchical_client_split(plan)
    client_indices = split_plan["client_indices"]
    client_distribution = split_plan["client_distribution"]
    weights = build_train_only_class_weights(plan.dataset, project_root=project_root)

    mapping = _load_json(Path(plan.checked_paths["attack_family_label_mapping"]))
    class_names = _class_names(mapping, int(plan.raw["model"]["attack_head_dim"]))
    rare_class_names = [str(name) for name in plan.raw.get("rare_classes", [])]

    global_model = build_model_from_plan(plan).to(device)
    val_dataset = HierarchicalNumpyDataset(
        X_val,
        y_binary_val,
        y_attack_val,
        mask_val,
        np.arange(int(X_val.shape[0]), dtype=np.int64),
    )
    test_dataset = HierarchicalNumpyDataset(
        X_test,
        y_binary_test,
        y_attack_test,
        mask_test,
        np.arange(int(X_test.shape[0]), dtype=np.int64),
    )
    val_loader = _make_loader(
        val_dataset, int(training_cfg["batch_size"]), shuffle=False, seed=seed
    )
    test_loader = _make_loader(
        test_dataset, int(training_cfg["batch_size"]), shuffle=False, seed=seed
    )

    best_round = -1
    best_score = float("-inf")
    best_state: dict[str, Any] | None = None
    round_states: dict[int, dict[str, Any]] = {}
    round_rows: list[dict[str, Any]] = []
    integrity_rounds: list[dict[str, Any]] = []
    aggregation_rounds: list[dict[str, Any]] = []
    attack_rounds: list[dict[str, Any]] = []
    malicious_client_indices = _select_malicious_client_indices(
        attack_config,
        num_clients=len(client_indices),
    )
    malicious_client_ids = [f"client_{index:02d}" for index in malicious_client_indices]

    for round_id in range(1, int(plan.raw["federation"]["rounds"]) + 1):
        client_updates: list[dict[str, Any]] = []
        sample_counts: list[int] = []
        client_ids: list[str] = []
        client_losses: list[float] = []
        for client_id, indices in enumerate(client_indices):
            dataset = HierarchicalNumpyDataset(
                X_train,
                y_binary_train,
                y_attack_train,
                mask_train,
                indices,
            )
            state, loss = _train_local_model(
                global_model,
                dataset,
                plan,
                weights,
                device,
                seed + round_id + client_id,
            )
            client_updates.append(state)
            sample_counts.append(int(len(dataset)))
            client_ids.append(f"client_{client_id:02d}")
            client_losses.append(float(loss))

        updates_for_aggregation, attack_round = _apply_attack_to_client_updates(
            client_updates,
            client_ids,
            attack_config,
            malicious_client_indices,
            round_id=round_id,
        )
        attack_rounds.append(attack_round)
        aggregation = validate_aggregation_with_integrity(
            updates_for_aggregation,
            sample_counts,
            client_ids,
            round_id=round_id,
            aggregation_config=aggregation_config,
            attack_round=attack_round,
        )
        global_model.load_state_dict(aggregation["aggregated_state_dict"])
        integrity_rounds.extend(aggregation["integrity_records"])
        aggregation_rounds.append(aggregation["aggregation_audit"])

        val_metrics = evaluate_hierarchical_model(
            global_model,
            val_loader,
            device,
            class_names=class_names,
            rare_class_names=rare_class_names,
            threshold=float(training_cfg.get("threshold", 0.5)),
        )
        score = float(val_metrics["selection"]["val_hierarchical_score"])
        validation_fields = _validation_selection_fields(val_metrics)
        round_rows.append(
            {
                "round": round_id,
                "mean_client_loss": float(np.mean(client_losses)),
                "aggregation_strategy": aggregation_config["strategy"],
                "aggregation_trim_ratio": (
                    ""
                    if aggregation_config["trim_ratio"] is None
                    else aggregation_config["trim_ratio"]
                ),
                "attack_enabled": attack_config["enabled"],
                "attack_type": attack_config["type"],
                "malicious_fraction": attack_config["malicious_fraction"],
                "malicious_client_ids": json.dumps(attack_round["malicious_client_ids"]),
                "attack_applied": attack_round["attack_applied"],
                **validation_fields,
                "safety_gate_eligible": "",
                "selected_by_safety_gate": "",
            }
        )
        if selection_config["configured"]:
            round_states[round_id] = copy.deepcopy(global_model.state_dict())
            if selection_config["save_per_round_checkpoints"]:
                round_checkpoint_path = (
                    Path(str(selection_config["per_round_checkpoint_dir"]))
                    / f"round_{round_id:02d}.pt"
                )
                _save_round_checkpoint(
                    torch,
                    round_checkpoint_path,
                    global_model,
                    plan,
                    round_id,
                    val_metrics,
                    {
                        **attack_config,
                        "malicious_client_ids": malicious_client_ids,
                    },
                    aggregation_config,
                )
        elif score > best_score:
            best_score = score
            best_round = round_id
            best_state = copy.deepcopy(global_model.state_dict())

    if selection_config["configured"]:
        selection_result = _select_safety_gated_round(round_rows, selection_config)
        best_round = int(selection_result["selected_round"])
        best_score = _round_metric(
            next(row for row in round_rows if int(row["round"]) == best_round),
            "val_hierarchical_score",
        )
        best_state = round_states.get(best_round)
    else:
        selection_result = _legacy_selection_result(round_rows, best_round)

    if best_state is None:
        raise HierarchicalFedAvgTrainingError("No best validation round was selected.")
    global_model.load_state_dict(best_state)
    selection_payload = selection_result if selection_config["configured"] else None
    test_metrics = evaluate_hierarchical_model(
        global_model,
        test_loader,
        device,
        class_names=class_names,
        rare_class_names=rare_class_names,
        threshold=float(training_cfg.get("threshold", 0.5)),
    )

    outputs["checkpoint"].parent.mkdir(parents=True, exist_ok=True)
    checkpoint_payload = {
        "model_state_dict": global_model.state_dict(),
        "dataset": plan.dataset,
        "protocol_label": plan.raw["protocol_label"],
        "best_round": best_round,
        "centralized_reference": plan.raw["centralized_reference"],
        "initialization": "from_scratch",
        "attack": {
            **attack_config,
            "malicious_client_ids": malicious_client_ids,
        },
        "aggregation": aggregation_config,
    }
    if selection_payload is not None:
        checkpoint_payload["selection"] = selection_payload
    torch.save(checkpoint_payload, outputs["checkpoint"])
    outputs["result_dir"].mkdir(parents=True, exist_ok=True)
    _write_csv(outputs["round_history"], round_rows, round_rows[0].keys())
    _write_csv(
        outputs["client_distribution"],
        client_distribution,
        ("client_id", "total_samples", "binary_class_counts", "attack_family_counts", "attack_rows", "benign_rows"),
    )
    metrics_payload = {
        "dataset": plan.dataset,
        "task": "hierarchical_federated",
        "protocol_label": plan.raw["protocol_label"],
        "best_round": best_round,
        "test_metrics": test_metrics,
        "centralized_reference_metrics": plan.raw["centralized_reference"].get("metrics"),
        "attack": {
            **attack_config,
            "malicious_client_ids": malicious_client_ids,
        },
        "aggregation": aggregation_config,
        "integrity": {
            "sha256_update_hashing": True,
            "verify_before_aggregation": True,
            "all_rounds_verified": all(
                audit.get("integrity_verified") is True for audit in aggregation_rounds
            ),
        },
        "safety": {
            "centralized_checkpoint_reference_only": True,
            "initialization": "from_scratch",
            "test_evaluated_once_after_best_validation_round": True,
            "final_checkpoint": False,
        },
    }
    if selection_payload is not None:
        metrics_payload["selection"] = selection_payload
    _write_json(outputs["test_metrics"], metrics_payload)
    manifest = {
        "schema_version": "hierarchical_fedavg_manifest_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": plan.dataset,
        "config_path": str(plan.path),
        "checkpoint_path": str(outputs["checkpoint"]),
        "result_dir": str(outputs["result_dir"]),
        "best_round": best_round,
        "rounds_run": int(plan.raw["federation"]["rounds"]),
        "client_distribution_warnings": split_plan["warnings"],
        "attack_config": {
            **attack_config,
            "malicious_client_ids": malicious_client_ids,
        },
        "attack_audit": attack_rounds,
        "aggregation_config": aggregation_config,
        "aggregation_audit": aggregation_rounds,
        "update_integrity_records": integrity_rounds,
        "centralized_reference": plan.raw["centralized_reference"],
        "initialization": "from_scratch",
        "safety": {
            "models_final_modified": False,
            "results_final_modified": False,
            "a11_used_as_final": False,
            "fake_metrics": False,
        },
    }
    if selection_payload is not None:
        manifest["selection"] = selection_payload
    _write_json(outputs["audit_json"], manifest)
    report_payload = {
        "best_round": best_round,
        "rounds_run": int(plan.raw["federation"]["rounds"]),
        "metrics_path": str(outputs["test_metrics"]),
        "manifest_path": str(outputs["audit_json"]),
        "attack": {
            **attack_config,
            "malicious_client_ids": malicious_client_ids,
        },
        "aggregation": aggregation_config,
        "integrity_verified": all(
            audit.get("integrity_verified") is True for audit in aggregation_rounds
        ),
    }
    if selection_payload is not None:
        report_payload["selection"] = selection_payload
    _write_report(outputs["report_md"], plan, report_payload)
    return HierarchicalFedAvgOutcome(
        status="complete",
        dataset=plan.dataset,
        checkpoint_path=str(outputs["checkpoint"]),
        metrics_path=str(outputs["test_metrics"]),
        manifest_path=str(outputs["audit_json"]),
        report_path=str(outputs["report_md"]),
        best_round=best_round,
        rounds_run=int(plan.raw["federation"]["rounds"]),
        test_metrics=test_metrics,
    )
