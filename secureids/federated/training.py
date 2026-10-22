"""UNSW-only FedAvg training runner.

This module enables real FedAvg training only for UNSW-NB15 after an explicit
CLI ``--execute``. CICIDS execution is intentionally refused until separately
approved. The runner never warm-starts from centralized checkpoints; centralized
artifacts are references only.
"""

from __future__ import annotations

from secureids.artifacts import load_numpy_readonly

import csv
import inspect
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from secureids.federated.config import (
    FederatedConfig,
    FederatedConfigError,
    load_federated_config,
    normalize_dataset_alias,
)
from secureids.federated.fedavg import aggregate_state_dicts_weighted
from secureids.federated.splitting import plan_stratified_iid_client_indices
from secureids.training.metrics import compute_binary_metrics


UNSW_DATASET = "unsw_nb15"
CICIDS_DATASET = "cicids2018"
APPROVED_FEDAVG_DATASETS = {
    UNSW_DATASET: {
        "display_name": "UNSW-NB15",
        "input_dim": 190,
        "checkpoint_name": "fedavg_unsw_binary.pt",
        "forbidden_output_token": "cicids",
        "already_completed_peer_note": "no_cicids_fedavg_training",
    },
    CICIDS_DATASET: {
        "display_name": "CICIDS2018",
        "input_dim": 77,
        "checkpoint_name": "fedavg_cicids_binary.pt",
        "forbidden_output_token": "unsw",
        "already_completed_peer_note": "no_unsw_fedavg_rerun",
    },
}

GUARDED_OUTPUT_KEYS = (
    "checkpoint",
    "round_history",
    "client_distribution",
    "client_logs",
    "test_metrics",
    "confusion_matrix",
    "manifest",
)


class FederatedTrainingError(RuntimeError):
    """Raised when approved FedAvg training cannot safely start or finish."""


@dataclass(frozen=True)
class FederatedTrainingOutcome:
    status: str
    dataset: str
    checkpoint_path: str
    metrics_path: str
    manifest_path: str
    report_path: str
    best_round: int
    rounds_run: int
    device: str
    cuda_available: bool
    test_metrics: dict[str, Any]


class IndexedNumpyDataset:
    """Small Dataset-like wrapper over processed NumPy arrays and indices."""

    def __init__(self, x: np.ndarray, y: np.ndarray, indices: np.ndarray):
        self.x = x
        self.y = y
        self.indices = np.asarray(indices, dtype=np.int64)

    def __len__(self) -> int:
        return int(self.indices.shape[0])

    def __getitem__(self, item: int) -> tuple[object, object]:
        import torch

        index = int(self.indices[item])
        features_np = np.asarray(self.x[index], dtype=np.float32).copy()
        features = torch.from_numpy(features_np)
        label = torch.tensor(float(self.y[index]), dtype=torch.float32)
        return features, label


class FullNumpyDataset:
    """Dataset wrapper for validation/test arrays."""

    def __init__(self, x: np.ndarray, y: np.ndarray):
        self.x = x
        self.y = y

    def __len__(self) -> int:
        return int(self.y.shape[0])

    def __getitem__(self, item: int) -> tuple[object, object]:
        import torch

        features_np = np.asarray(self.x[item], dtype=np.float32).copy()
        features = torch.from_numpy(features_np)
        label = torch.tensor(float(self.y[item]), dtype=torch.float32)
        return features, label


def ensure_fedavg_training_enabled(dataset: str | None) -> str:
    """Return canonical approved dataset or raise before training-side effects."""

    canonical = normalize_dataset_alias(dataset)
    if canonical not in APPROVED_FEDAVG_DATASETS:
        raise FederatedTrainingError(
            "Only UNSW-NB15 and CICIDS2018 FedAvg training are approved through "
            "their explicit task gates."
        )
    return canonical


def ensure_unsw_training_enabled(dataset: str | None) -> str:
    """Backward-compatible UNSW gate used by earlier tests/tasks."""

    canonical = normalize_dataset_alias(dataset)
    if canonical != UNSW_DATASET:
        raise FederatedTrainingError(
            "Only UNSW-NB15 FedAvg training is approved through this helper."
        )
    return canonical


def _project_path(project_root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_root / path


def planned_output_paths(
    config: FederatedConfig,
    project_root: Path,
) -> dict[str, Path]:
    """Return guarded planned FedAvg final output paths for the config dataset."""

    return {
        key: _project_path(project_root, config.raw["outputs"][key])
        for key in GUARDED_OUTPUT_KEYS
    }


def planned_unsw_output_paths(
    config: FederatedConfig,
    project_root: Path,
) -> dict[str, Path]:
    """Backward-compatible alias for guarded output path planning."""

    return planned_output_paths(config, project_root)


def existing_guarded_outputs(
    config: FederatedConfig,
    project_root: Path,
) -> list[Path]:
    """Return guarded FedAvg outputs that already exist."""

    return [
        path
        for path in planned_output_paths(config, project_root).values()
        if path.exists()
    ]


def _require_no_existing_outputs(
    config: FederatedConfig,
    project_root: Path,
    overwrite: bool,
) -> None:
    existing = existing_guarded_outputs(config, project_root)
    if existing and not overwrite:
        display = APPROVED_FEDAVG_DATASETS[config.dataset]["display_name"]
        lines = [
            f"{display} FedAvg final outputs already exist. Refusing before training.",
            "Re-run with --overwrite only if you intentionally want to replace "
            f"{display} FedAvg outputs.",
            "Existing guarded outputs:",
        ]
        lines.extend(f"- {path}" for path in existing)
        raise FederatedTrainingError("\n".join(lines))


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise FederatedTrainingError(f"Expected JSON object: {path}")
    return payload


def _find_key(payload: Any, key: str) -> Any:
    if isinstance(payload, dict):
        if key in payload:
            return payload[key]
        for value in payload.values():
            found = _find_key(value, key)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = _find_key(value, key)
            if found is not None:
                return found
    return None


def _validate_manifest_safety(manifest_path: Path) -> None:
    manifest = _read_json(manifest_path)
    expected = {
        "test_set_used_for_tuning": False,
        "preprocessing_safety_check_passed": True,
        "final_checkpoint": True,
        "no_federated_training": True,
        "no_attack_simulation": True,
        "no_xai": True,
    }
    failures = []
    for key, expected_value in expected.items():
        actual = _find_key(manifest, key)
        if actual is not expected_value:
            failures.append(f"{key}: expected {expected_value!r}, found {actual!r}")
    if failures:
        raise FederatedTrainingError(
            "Centralized manifest safety validation failed: " + "; ".join(failures)
        )


def _load_feature_names(path: Path) -> list[str]:
    payload = _read_json(path)
    feature_names = payload.get("feature_names")
    if not isinstance(feature_names, list):
        raise FederatedTrainingError(
            f"{path} must contain a list at JSON key 'feature_names'."
        )
    return [str(name) for name in feature_names]


def _validate_pre_run(
    config: FederatedConfig,
    project_root: Path,
    overwrite: bool,
) -> dict[str, Any]:
    """Validate all safe preconditions before importing torch/training."""

    if config.dataset not in APPROVED_FEDAVG_DATASETS:
        raise FederatedTrainingError(
            "Only UNSW-NB15 and CICIDS2018 FedAvg configs are approved."
        )
    policy = APPROVED_FEDAVG_DATASETS[config.dataset]
    if config.task != "binary":
        raise FederatedTrainingError("FedAvg training requires binary task.")
    if config.architecture != "SecureIDSNet":
        raise FederatedTrainingError("FedAvg training requires SecureIDSNet.")
    if config.input_dim != int(policy["input_dim"]):
        raise FederatedTrainingError(
            f"{policy['display_name']} FedAvg input_dim must be {policy['input_dim']}."
        )
    if config.algorithm != "FedAvg":
        raise FederatedTrainingError("Task 9C supports FedAvg only.")
    federation = config.raw["federation"]
    if federation["client_split"] != "stratified_iid":
        raise FederatedTrainingError("Task 9C supports stratified_iid only.")
    if int(federation["num_clients"]) != 5:
        raise FederatedTrainingError("Task 9C requires exactly 5 UNSW clients.")
    if float(federation["client_fraction"]) != 1.0:
        raise FederatedTrainingError("Task 9C requires client_fraction=1.0.")
    if int(federation["local_epochs"]) != 1:
        raise FederatedTrainingError("Task 9C requires local_epochs=1.")

    _require_no_existing_outputs(config, project_root, overwrite=overwrite)

    data = config.raw["data"]
    processed_dir = _project_path(project_root, data["processed_dir"])
    if not processed_dir.exists():
        raise FederatedTrainingError(f"Processed directory missing: {processed_dir}")

    paths = {
        "X_train": processed_dir / data["train_split"]["x"],
        "y_train": processed_dir / data["train_split"]["y"],
        "X_val": processed_dir / data["val_split"]["x"],
        "y_val": processed_dir / data["val_split"]["y"],
        "X_test": processed_dir / data["test_split"]["x"],
        "y_test": processed_dir / data["test_split"]["y"],
        "feature_names": processed_dir / "feature_names.json",
        "label_mapping": processed_dir / "label_mapping.json",
        "preprocessing_manifest": processed_dir / "preprocessing_manifest.json",
    }
    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise FederatedTrainingError(
            "Required processed files are missing: " + ", ".join(missing)
        )

    feature_names = _load_feature_names(paths["feature_names"])
    if len(feature_names) != config.input_dim:
        raise FederatedTrainingError(
            f"Feature count {len(feature_names)} does not match input_dim {config.input_dim}."
        )

    references = {
        key: _project_path(project_root, value)
        for key, value in config.raw["centralized_reference"].items()
    }
    missing_refs = [str(path) for path in references.values() if not path.exists()]
    if missing_refs:
        raise FederatedTrainingError(
            "Centralized reference files are missing: " + ", ".join(missing_refs)
        )
    _validate_manifest_safety(references["manifest"])

    output_paths = planned_output_paths(config, project_root)
    for key, path in output_paths.items():
        if key == "checkpoint" and not str(path).endswith(str(policy["checkpoint_name"])):
            raise FederatedTrainingError(
                f"{policy['display_name']} checkpoint path is not the approved FedAvg path."
            )
        if str(policy["forbidden_output_token"]) in str(path).lower():
            raise FederatedTrainingError(
                f"Refusing cross-dataset output path for {policy['display_name']}: {path}"
            )
        path.parent.mkdir(parents=True, exist_ok=True)

    report_path = _project_path(project_root, config.raw["outputs"]["report"])
    report_path.parent.mkdir(parents=True, exist_ok=True)

    return {
        "processed_dir": processed_dir,
        "paths": paths,
        "feature_names": feature_names,
        "references": references,
        "output_paths": output_paths,
        "report_path": report_path,
    }


def _set_seeds(seed: int) -> None:
    import torch

    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _build_model(config: FederatedConfig) -> object:
    from secureids.models.secureids_net import SecureIDSNet

    model_config = config.raw["model"]
    kwargs = {
        "input_dim": int(model_config["input_dim"]),
        "hidden_dims": list(model_config["hidden_dims"]),
        "dropout": float(model_config["dropout"]),
        "output_dim": int(model_config["output_dim"]),
    }
    signature = inspect.signature(SecureIDSNet)
    filtered = {
        name: value
        for name, value in kwargs.items()
        if name in signature.parameters
    }
    try:
        return SecureIDSNet(**filtered)
    except TypeError:
        return SecureIDSNet(input_dim=kwargs["input_dim"])


def _clone_state_dict(state_dict: dict[str, object]) -> dict[str, object]:
    import torch

    cloned = {}
    for key, value in state_dict.items():
        cloned[key] = value.detach().cpu().clone() if torch.is_tensor(value) else value
    return cloned


def _client_distribution_rows(
    client_indices: list[np.ndarray],
    y_train: np.ndarray,
) -> list[dict[str, Any]]:
    rows = []
    for client_id, indices in enumerate(client_indices):
        labels = y_train[indices]
        class_0 = int(np.sum(labels == 0))
        class_1 = int(np.sum(labels == 1))
        total = int(indices.shape[0])
        rows.append(
            {
                "client_id": f"client_{client_id:02d}",
                "total_samples": total,
                "class_0_count": class_0,
                "class_1_count": class_1,
                "class_0_fraction": float(class_0) / float(total) if total else 0.0,
                "class_1_fraction": float(class_1) / float(total) if total else 0.0,
            }
        )
    return rows


def _make_loader(
    dataset: object,
    batch_size: int,
    shuffle: bool,
    seed: int,
) -> object:
    import torch
    from torch.utils.data import DataLoader

    generator = torch.Generator()
    generator.manual_seed(seed)
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        generator=generator,
        num_workers=0,
    )


def _train_client(
    model: object,
    loader: object,
    criterion: object,
    optimizer: object,
    device: object,
    local_epochs: int,
) -> float:
    import torch

    model.train()
    total_loss = 0.0
    total_samples = 0
    for _epoch in range(local_epochs):
        for features, labels in loader:
            features = features.to(device)
            labels = labels.to(device).view(-1)
            optimizer.zero_grad(set_to_none=True)
            logits = model(features).view(-1)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            batch_size = int(labels.shape[0])
            total_loss += float(loss.detach().cpu().item()) * batch_size
            total_samples += batch_size
    return total_loss / float(total_samples) if total_samples else 0.0


def _evaluate(
    model: object,
    loader: object,
    criterion: object,
    device: object,
    threshold: float,
) -> tuple[float, dict[str, Any]]:
    import torch

    model.eval()
    losses = []
    sample_counts = []
    logits_parts = []
    label_parts = []
    with torch.no_grad():
        for features, labels in loader:
            features = features.to(device)
            labels = labels.to(device).view(-1)
            logits = model(features).view(-1)
            loss = criterion(logits, labels)
            batch_size = int(labels.shape[0])
            losses.append(float(loss.detach().cpu().item()) * batch_size)
            sample_counts.append(batch_size)
            logits_parts.append(logits.detach().cpu().numpy())
            label_parts.append(labels.detach().cpu().numpy())
    avg_loss = sum(losses) / float(sum(sample_counts)) if sample_counts else 0.0
    scores = np.concatenate(logits_parts) if logits_parts else np.array([], dtype=np.float64)
    y_true = np.concatenate(label_parts).astype(np.int64) if label_parts else np.array([], dtype=np.int64)
    return avg_loss, compute_binary_metrics(
        y_true=y_true,
        scores=scores,
        threshold=threshold,
        from_logits=True,
    )


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(rows)


def build_safety_notes(dataset: str = UNSW_DATASET) -> dict[str, bool]:
    """Return required FedAvg safety notes for the dataset."""

    notes = {
        "no_fake_metrics": True,
        "final_test_after_best_validation_round_only": True,
        "no_security_or_attack_simulation": True,
        "no_robust_aggregation": True,
        "no_xai": True,
        "no_dashboard_model_demo": True,
    }
    if dataset == CICIDS_DATASET:
        notes["no_unsw_fedavg_rerun"] = True
    else:
        notes["no_cicids_fedavg_training"] = True
    return notes


def build_manifest_payload(
    *,
    config: FederatedConfig,
    config_path: Path,
    validation: dict[str, Any],
    client_distribution: list[dict[str, Any]],
    device_name: str,
    cuda_available: bool,
    best_round: int,
    output_paths: dict[str, Path],
    created_at_utc: str,
) -> dict[str, Any]:
    """Build the final FedAvg manifest payload."""

    return {
        "dataset": config.dataset,
        "task": config.task,
        "model": config.architecture,
        "input_dim": config.input_dim,
        "algorithm": config.algorithm,
        "config_path": str(config_path),
        "processed_data_paths": {
            key: str(path)
            for key, path in validation["paths"].items()
        },
        "feature_names_path": str(validation["paths"]["feature_names"]),
        "label_mapping_path": str(validation["paths"]["label_mapping"]),
        "preprocessing_manifest_path": str(validation["paths"]["preprocessing_manifest"]),
        "centralized_reference_paths": {
            key: str(path)
            for key, path in validation["references"].items()
        },
        "client_split_policy": config.raw["federation"]["client_split"],
        "seed": config.seed,
        "num_clients": config.num_clients,
        "client_fraction": config.raw["federation"]["client_fraction"],
        "local_epochs": config.raw["federation"]["local_epochs"],
        "rounds": config.raw["federation"]["rounds"],
        "best_round": best_round,
        "early_selection_metric": "val_macro_f1",
        "class_distribution_per_client": client_distribution,
        "training_settings": config.raw["training"],
        "device": device_name,
        "cuda_available": cuda_available,
        "checkpoint_path": str(output_paths["checkpoint"]),
        "output_paths": {key: str(path) for key, path in output_paths.items()},
        "final_checkpoint": True,
        "test_set_used_for_tuning": False,
        "final_test_after_best_validation_round_only": True,
        APPROVED_FEDAVG_DATASETS[config.dataset]["already_completed_peer_note"]: True,
        "no_security_or_attack_simulation": True,
        "no_robust_aggregation": True,
        "no_xai": True,
        "no_dashboard_model_demo": True,
        "created_at_utc": created_at_utc,
    }


def _write_test_metrics_json(
    path: Path,
    *,
    config: FederatedConfig,
    checkpoint_path: Path,
    best_round: int,
    rounds_run: int,
    test_metrics: dict[str, Any],
) -> None:
    payload = {
        "dataset": config.dataset,
        "task": config.task,
        "model": config.architecture,
        "input_dim": config.input_dim,
        "algorithm": config.algorithm,
        "checkpoint_path": str(checkpoint_path),
        "threshold": float(config.raw["training"]["threshold"]),
        "test_set_used_for_tuning": False,
        "final_checkpoint": True,
        "best_round": best_round,
        "rounds_run": rounds_run,
        "metrics": {
            key: value
            for key, value in test_metrics.items()
            if key in {
                "accuracy",
                "precision",
                "recall",
                "f1",
                "macro_f1",
                "confusion_matrix",
                "n_samples",
            }
        },
        "centralized_reference": config.raw["centralized_reference"],
        "safety_notes": build_safety_notes(config.dataset),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_confusion_matrix_csv(path: Path, metrics: dict[str, Any]) -> None:
    cm = metrics["confusion_matrix"]
    rows = [
        {"true_label": 0, "predicted_label": 0, "count": cm["tn"]},
        {"true_label": 0, "predicted_label": 1, "count": cm["fp"]},
        {"true_label": 1, "predicted_label": 0, "count": cm["fn"]},
        {"true_label": 1, "predicted_label": 1, "count": cm["tp"]},
    ]
    _write_csv(path, rows, ("true_label", "predicted_label", "count"))


def _extract_metric(payload: Any, name: str) -> Any:
    if isinstance(payload, dict):
        if name in payload:
            return payload[name]
        for value in payload.values():
            found = _extract_metric(value, name)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = _extract_metric(value, name)
            if found is not None:
                return found
    return None


def _write_report(
    path: Path,
    *,
    config: FederatedConfig,
    project_root: Path,
    centralized_metrics_path: Path,
    output_paths: dict[str, Path],
    round_history: list[dict[str, Any]],
    client_distribution: list[dict[str, Any]],
    test_metrics: dict[str, Any],
    best_round: int,
) -> None:
    centralized_metrics = _read_json(centralized_metrics_path)
    display_name = APPROVED_FEDAVG_DATASETS[config.dataset]["display_name"]
    if config.dataset == CICIDS_DATASET:
        status = "UNSW FedAvg completed; CICIDS FedAvg completed"
    else:
        status = "UNSW FedAvg completed; CICIDS FedAvg not run"
    lines = [
        "# Federated Learning Report",
        "",
        f"Status: `{status}`",
        "",
        f"## {display_name} FedAvg",
        "",
        f"- Config: `{config.path}`",
        f"- Algorithm: `{config.algorithm}`",
        f"- Model: `{config.architecture}`",
        f"- Input dimension: `{config.input_dim}`",
        f"- Clients: `{config.num_clients}`",
        f"- Best round by validation macro-F1: `{best_round}`",
        f"- Final test accuracy: `{test_metrics['accuracy']}`",
        f"- Final test macro-F1: `{test_metrics['macro_f1']}`",
        "",
        "## Client Setup",
        "",
    ]
    for row in client_distribution:
        lines.append(
            f"- `{row['client_id']}`: total={row['total_samples']}, "
            f"class_0={row['class_0_count']}, class_1={row['class_1_count']}"
        )
    lines.extend(
        [
            "",
            "## Confusion Matrix",
            "",
            f"- TP: `{test_metrics['confusion_matrix']['tp']}`",
            f"- FP: `{test_metrics['confusion_matrix']['fp']}`",
            f"- FN: `{test_metrics['confusion_matrix']['fn']}`",
            f"- TN: `{test_metrics['confusion_matrix']['tn']}`",
            "",
            "## Centralized Reference Comparison",
            "",
            f"- Centralized {display_name} accuracy: `{_extract_metric(centralized_metrics, 'accuracy')}`",
            f"- Centralized {display_name} macro-F1: `{_extract_metric(centralized_metrics, 'macro_f1')}`",
            f"- FedAvg {display_name} accuracy: `{test_metrics['accuracy']}`",
            f"- FedAvg {display_name} macro-F1: `{test_metrics['macro_f1']}`",
            "",
            "## Output Artifacts",
            "",
        ]
    )
    for key, value in output_paths.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            f"- report: `{path}`",
            "",
            "## Safety Confirmation",
            "",
            "- No CICIDS FedAvg training was run.",
            "- No centralized checkpoint, metric, history, confusion matrix, or manifest was modified.",
            "- Test data was evaluated once after selecting the best validation round.",
            "- No security, attack simulation, Trimmed Mean, XAI, or dashboard model demo was run.",
            "",
            "## Scope Limitations",
            "",
            "- TLS/security, SHA-256 integrity, attack simulation, Trimmed Mean, XAI, and dashboard integration remain future work.",
        ]
    )
    if config.dataset == CICIDS_DATASET:
        unsw_metrics_path = (
            project_root / "results" / "federated" / "unsw" / "fedavg_test_metrics.json"
        )
        unsw_checkpoint_path = project_root / "models" / "federated" / "fedavg_unsw_binary.pt"
        if unsw_metrics_path.exists():
            unsw_metrics_payload = _read_json(unsw_metrics_path)
            unsw_metrics = unsw_metrics_payload.get("metrics", {})
            lines.extend(
                [
                    "",
                    "## UNSW FedAvg Preserved Result",
                    "",
                    f"- Checkpoint: `{unsw_checkpoint_path}`",
                    f"- Metrics: `{unsw_metrics_path}`",
                    f"- Accuracy: `{unsw_metrics.get('accuracy')}`",
                    f"- Macro-F1: `{unsw_metrics.get('macro_f1')}`",
                    "- This result was not rerun or overwritten by CICIDS FedAvg training.",
                ]
            )
        lines[lines.index("- No CICIDS FedAvg training was run.")] = (
            "- UNSW FedAvg outputs were not rerun or overwritten."
        )
        lines.insert(
            lines.index("## Scope Limitations"),
            "- UNSW FedAvg was previously completed and remains a separate preserved result.",
        )
    else:
        lines.insert(
            lines.index("## Scope Limitations"),
            "- CICIDS FedAvg training remains pending separate approval.",
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_fedavg_training(
    *,
    dataset: str,
    config_path: str | Path,
    project_root: Path,
    execute: bool,
    overwrite: bool = False,
) -> FederatedTrainingOutcome:
    """Run approved FedAvg training after explicit execution."""

    if not execute:
        raise FederatedTrainingError(
            "FedAvg training requires --execute. No training was started."
        )
    requested_dataset = ensure_fedavg_training_enabled(dataset)
    config = load_federated_config(config_path, project_root=project_root)
    if config.dataset != requested_dataset:
        raise FederatedTrainingError(
            f"--dataset {dataset!r} does not match config dataset {config.dataset!r}."
        )
    validation = _validate_pre_run(config, project_root, overwrite=overwrite)

    try:
        import torch
        from torch.utils.data import DataLoader
    except ModuleNotFoundError as error:
        raise FederatedTrainingError(
            f"PyTorch is required for FedAvg training: {error}"
        ) from error

    seed = int(config.raw["federation"]["seed"])
    _set_seeds(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device_name = str(device)
    cuda_available = bool(torch.cuda.is_available())

    paths = validation["paths"]
    x_train = load_numpy_readonly(paths["X_train"], mmap_mode="r")
    y_train = load_numpy_readonly(paths["y_train"], mmap_mode="r")
    x_val = load_numpy_readonly(paths["X_val"], mmap_mode="r")
    y_val = load_numpy_readonly(paths["y_val"], mmap_mode="r")
    x_test = load_numpy_readonly(paths["X_test"], mmap_mode="r")
    y_test = load_numpy_readonly(paths["y_test"], mmap_mode="r")

    client_indices = plan_stratified_iid_client_indices(
        y_train=y_train,
        num_clients=config.num_clients,
        seed=seed,
    )
    client_distribution = _client_distribution_rows(client_indices, y_train)

    training = config.raw["training"]
    batch_size = int(training["batch_size"])
    learning_rate = float(training["learning_rate"])
    weight_decay = float(training["weight_decay"])
    threshold = float(training["threshold"])
    local_epochs = int(config.raw["federation"]["local_epochs"])
    rounds = int(config.raw["federation"]["rounds"])

    if training["use_pos_weight"]:
        class_0 = float(np.sum(y_train == 0))
        class_1 = float(np.sum(y_train == 1))
        pos_weight_value = class_0 / class_1 if class_1 else 1.0
        pos_weight = torch.tensor([pos_weight_value], dtype=torch.float32, device=device)
    else:
        pos_weight = None
    criterion = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    global_model = _build_model(config).to(device)
    val_loader = DataLoader(
        FullNumpyDataset(x_val, y_val),
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
    )
    test_loader = DataLoader(
        FullNumpyDataset(x_test, y_test),
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
    )

    round_history: list[dict[str, Any]] = []
    client_logs: list[dict[str, Any]] = []
    best_macro_f1 = -1.0
    best_round = 0
    best_state = _clone_state_dict(global_model.state_dict())

    total_train_samples = int(y_train.shape[0])
    for round_index in range(1, rounds + 1):
        round_started = time.perf_counter()
        global_state = _clone_state_dict(global_model.state_dict())
        client_states = []
        client_sample_counts = []

        for client_id, indices in enumerate(client_indices):
            client_started = time.perf_counter()
            client_model = _build_model(config).to(device)
            client_model.load_state_dict(global_state)
            client_dataset = IndexedNumpyDataset(x_train, y_train, indices)
            client_loader = _make_loader(
                client_dataset,
                batch_size=batch_size,
                shuffle=True,
                seed=seed + round_index * 100 + client_id,
            )
            optimizer = torch.optim.AdamW(
                client_model.parameters(),
                lr=learning_rate,
                weight_decay=weight_decay,
            )
            train_loss = _train_client(
                client_model,
                client_loader,
                criterion,
                optimizer,
                device,
                local_epochs,
            )
            client_states.append(_clone_state_dict(client_model.state_dict()))
            client_sample_counts.append(int(indices.shape[0]))
            dist = client_distribution[client_id]
            client_logs.append(
                {
                    "round": round_index,
                    "client_id": dist["client_id"],
                    "train_samples": int(indices.shape[0]),
                    "class_0_count": dist["class_0_count"],
                    "class_1_count": dist["class_1_count"],
                    "local_epochs": local_epochs,
                    "train_loss": train_loss,
                    "client_seconds": time.perf_counter() - client_started,
                }
            )

        aggregated_state = aggregate_state_dicts_weighted(
            client_states,
            client_sample_counts,
        )
        global_model.load_state_dict(aggregated_state)
        val_loss, val_metrics = _evaluate(global_model, val_loader, criterion, device, threshold)
        if float(val_metrics["macro_f1"]) > best_macro_f1:
            best_macro_f1 = float(val_metrics["macro_f1"])
            best_round = round_index
            best_state = _clone_state_dict(global_model.state_dict())
        round_history.append(
            {
                "round": round_index,
                "val_loss": val_loss,
                "val_accuracy": val_metrics["accuracy"],
                "val_precision": val_metrics["precision"],
                "val_recall": val_metrics["recall"],
                "val_f1": val_metrics["f1"],
                "val_macro_f1": val_metrics["macro_f1"],
                "best_round_so_far": best_round,
                "round_seconds": time.perf_counter() - round_started,
                "participating_clients": len(client_indices),
                "total_train_samples": total_train_samples,
            }
        )

    global_model.load_state_dict(best_state)
    checkpoint_path = validation["output_paths"]["checkpoint"]
    torch.save(
        {
            "model_state_dict": best_state,
            "dataset": config.dataset,
            "task": config.task,
            "model": config.architecture,
            "input_dim": config.input_dim,
            "algorithm": config.algorithm,
            "best_round": best_round,
            "threshold": threshold,
            "config_path": str(config.path),
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        },
        checkpoint_path,
    )

    _test_loss, test_metrics = _evaluate(global_model, test_loader, criterion, device, threshold)
    output_paths = validation["output_paths"]
    _write_csv(
        output_paths["round_history"],
        round_history,
        (
            "round",
            "val_loss",
            "val_accuracy",
            "val_precision",
            "val_recall",
            "val_f1",
            "val_macro_f1",
            "best_round_so_far",
            "round_seconds",
            "participating_clients",
            "total_train_samples",
        ),
    )
    _write_csv(
        output_paths["client_distribution"],
        client_distribution,
        (
            "client_id",
            "total_samples",
            "class_0_count",
            "class_1_count",
            "class_0_fraction",
            "class_1_fraction",
        ),
    )
    _write_csv(
        output_paths["client_logs"],
        client_logs,
        (
            "round",
            "client_id",
            "train_samples",
            "class_0_count",
            "class_1_count",
            "local_epochs",
            "train_loss",
            "client_seconds",
        ),
    )
    _write_test_metrics_json(
        output_paths["test_metrics"],
        config=config,
        checkpoint_path=checkpoint_path,
        best_round=best_round,
        rounds_run=rounds,
        test_metrics=test_metrics,
    )
    _write_confusion_matrix_csv(output_paths["confusion_matrix"], test_metrics)

    created_at_utc = datetime.now(timezone.utc).isoformat()
    manifest = build_manifest_payload(
        config=config,
        config_path=config.path,
        validation=validation,
        client_distribution=client_distribution,
        device_name=device_name,
        cuda_available=cuda_available,
        best_round=best_round,
        output_paths=output_paths,
        created_at_utc=created_at_utc,
    )
    output_paths["manifest"].write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_report(
        validation["report_path"],
        config=config,
        project_root=project_root,
        centralized_metrics_path=validation["references"]["metrics"],
        output_paths=output_paths,
        round_history=round_history,
        client_distribution=client_distribution,
        test_metrics=test_metrics,
        best_round=best_round,
    )

    return FederatedTrainingOutcome(
        status="PASS",
        dataset=config.dataset,
        checkpoint_path=str(checkpoint_path),
        metrics_path=str(output_paths["test_metrics"]),
        manifest_path=str(output_paths["manifest"]),
        report_path=str(validation["report_path"]),
        best_round=best_round,
        rounds_run=rounds,
        device=device_name,
        cuda_available=cuda_available,
        test_metrics=test_metrics,
    )


def run_unsw_fedavg_training(
    *,
    dataset: str,
    config_path: str | Path,
    project_root: Path,
    execute: bool,
    overwrite: bool = False,
) -> FederatedTrainingOutcome:
    """Backward-compatible wrapper for the approved FedAvg runner."""

    return run_fedavg_training(
        dataset=dataset,
        config_path=config_path,
        project_root=project_root,
        execute=execute,
        overwrite=overwrite,
    )
